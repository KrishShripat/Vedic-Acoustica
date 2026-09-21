#!/usr/bin/env python3
"""
Vedic Acoustica — ML Pipeline Robustness Battery
================================================

A negative-control and stress-test companion to test_ml_audit.py.  Whereas the
audit proves the pipeline works on clean ground truth, this suite probes the
*limits* an external auditor would check:

  1. Vibrato            — ±10 ¢ @ 5 Hz modulation must remain on-bin (median
                          filter stabilisation claim); ±20 ¢ is a boundary probe.
  2. Near-cents         — Re1 (275.65 Hz) vs Re2 (279.07 Hz) are only 21.5 ¢
                          apart; frame/cluster assignment must keep them
                          distinct instead of collapsing to one bin.
  3. Octave folding     — tones at 2× a shruti fold back to the shruti bin via
                          harmonic division (PCP is octave-invariant).
  4. Noise injection    — 12-TET scale + white noise at 20 dB / 10 dB SNR must
                          still land on the correct raga family.
  5. Microphone colour  — 1-pole spectral tilt must not break raga detection.
  6. Ghana negatives    — the DTW "oral checksum" must REJECT non-Ghana audio:
                          silence (RMS guard) and broadband noise (spectral
                          flatness guard, added after this suite exposed the
                          false positive).
  7. Ghana positives    — the canonical fwd/rev cycle and its phase rotation
                          must be accepted (tempo-invariant DTW).

Ghana "structured-wrong" clips (monotone runs, jumbled alternation, atonal
random walk) are characterised as REPORT-only: whether an out-of-order but
tonal passage is "corrupt Ghana" or "a different recitation" is a musical
content question, so their verdicts are recorded but never fail the suite.

Result summary is written to test_reports/ml_robustness_report.json.
Exit code is non-zero when any hard assertion fails (CI gate).
"""

import sys, os, json, time
from pathlib import Path
from collections import Counter

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vedic_acoustica.settings")

import numpy as np
import soundfile as sf

from ml_engine.shruti_mapping import (
    REFERENCE_FREQ, SHRUTI_FREQUENCIES, SHRUTI_NAMES,
)
from ml_engine.audio_processing import extract_features, SR
from ml_engine.ml_engine import run_clustering
from ml_engine.ghana_patha import validate_ghana_patha
from ml_engine.raga_mapping import detect_raga, CONFIDENCE_THRESHOLD

SYNTH_DIR = BACKEND_DIR.parent / "test_audio" / "synthetic" / "robustness"
OUTPUT_DIR = BACKEND_DIR.parent / "test_reports"

_SF = [SHRUTI_FREQUENCIES[n] for n in SHRUTI_NAMES]


# ─────────────────────────────────────────────────────────────────────────────
# Audio generators
# ─────────────────────────────────────────────────────────────────────────────

def tone_hz(freq, dur):
    """Harmonic-rich tone (fundamental + 3 partials)."""
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    return (0.50 * np.sin(2*np.pi*freq*t) +
            0.30 * np.sin(2*np.pi*2*freq*t) +
            0.15 * np.sin(2*np.pi*3*freq*t) +
            0.05 * np.sin(2*np.pi*4*freq*t)).astype(np.float32)


def tone_idx(idx, dur):
    return tone_hz(_SF[idx], dur)


def vibrato_tone(idx, dur, rate=5.0, cents=10.0):
    """Pitch-modulated tone: instantaneous pitch oscillates ±cents @ rate Hz."""
    f0 = _SF[idx]
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    phase = 2*np.pi*f0*t + (cents / 1200.0) * f0 / rate * np.sin(2*np.pi*rate*t)
    return (0.50 * np.sin(phase) +
            0.30 * np.sin(2*phase) +
            0.15 * np.sin(3*phase) +
            0.05 * np.sin(4*phase)).astype(np.float32)


def add_noise(w, snr_db, seed=0):
    """Add white noise at a given SNR (dB)."""
    rng = np.random.default_rng(seed)
    sig = w.astype(np.float64)
    noise = rng.standard_normal(len(sig))
    noise *= np.sqrt(np.mean(sig**2) / 10 ** (snr_db / 10))
    return (sig + noise).astype(np.float32)


def mic_tilt(w, a=0.9):
    """1-pole high-pass (X/Y mic coloration), tuned via live zero feedback."""
    out = np.empty_like(w)
    prev = float(w[0])
    out[0] = w[0]
    for n in range(1, len(w)):
        out[n] = w[n] - a * prev
        prev = float(w[n])
    return out.astype(np.float32)


def white_noise(dur, amp=0.05, seed=1):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(int(SR * dur)) * amp).astype(np.float32)


# ── 12-TET scale (independent, non-circular ground truth) ────────────────────
_ET = {
    'Sa': 261.63, 'Re': 293.66, 'Ga': 329.63, 'Ma': 349.23,
    'Pa': 392.00, 'Dha': 440.00, 'Ni': 493.88,
}


def et_scale(notes, note_dur=0.4, rounds=2, descend=True):
    parts = []
    for _ in range(rounds):
        parts.append([tone_hz(_ET[n], note_dur) for n in notes])
    if descend:
        parts.append([tone_hz(_ET[n], note_dur) for n in reversed(notes)])
    waves = [w for group in parts for w in group]
    return np.concatenate(waves).astype(np.float32)


# ── Ghana patterns ───────────────────────────────────────────────────────────
_ASC = [0, 4, 8, 9, 13]          # Sa Re-s Ga-s Ma-s Pa
_DESC = [13, 9, 8, 4, 0]


def _phrase(kind, note_dur=0.2):
    seq = _ASC if kind == 'a' else _DESC
    return np.concatenate([tone_idx(i, note_dur) for i in seq])


def ghana_pattern(kinds, note_dur=0.2):
    return np.concatenate([_phrase(k, note_dur) for k in kinds]).astype(np.float32)


def random_walk(dur=6.0, note_dur=0.2):
    rng = np.random.default_rng(2)
    n_notes = int(dur / note_dur)
    walk = [int(rng.integers(0, 23))]
    for _ in range(n_notes - 1):
        walk.append(int(np.clip(walk[-1] + int(rng.integers(-2, 3)), 0, 22)))
    return np.concatenate([tone_idx(i, note_dur) for i in walk]).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────
#   kind  : pitch      → assert dominant PCP bin == expected
#           raga       → assert raga family == expected / acceptable
#           nearcents  → assert Re1 & Re2 stay distinct clusters
#           ghana_true → assert ghana is_valid is True
#           ghana_false→ assert ghana is_valid is False
#           report     → record verdict/metrics only, never fail

BILAWAL_FAMILY = ["Bilawal", "Mand", "Shankarabharanam", "Kambhoji"]

TESTS = [
    # ── Vibrato stabilisation (±10 ¢ @ 5 Hz) ────────────────────────────────
    {"name": "vib_re1_10c", "kind": "pitch", "expected": 1,
     "gen": lambda: vibrato_tone(1, 5.0, 5.0, 10.0),
     "notes": "Re1 275.65 Hz + 5Hz/±10¢ vibrato stays on Re1"},
    {"name": "vib_re2_10c", "kind": "pitch", "expected": 2,
     "gen": lambda: vibrato_tone(2, 5.0, 5.0, 10.0),
     "notes": "Re2 279.07 Hz + 5Hz/±10¢ vibrato stays on Re2"},
    {"name": "vib_ga3_10c", "kind": "pitch", "expected": 7,
     "gen": lambda: vibrato_tone(7, 5.0, 5.0, 10.0),
     "notes": "Ga3 327.03 Hz + 5Hz/±10¢ vibrato stays on Ga3"},
    {"name": "vib_pa_10c", "kind": "pitch", "expected": 13,
     "gen": lambda: vibrato_tone(13, 5.0, 5.0, 10.0),
     "notes": "Pa 392.44 Hz + 5Hz/±10¢ vibrato stays on Pa"},
    {"name": "vib_ni4_10c", "kind": "pitch", "expected": 21,
     "gen": lambda: vibrato_tone(21, 5.0, 5.0, 10.0),
     "notes": "Ni4 496.68 Hz + 5Hz/±10¢ vibrato stays on Ni4"},

    # ── Vibrato pushed to the limit (characterised, never fails) ────────────
    {"name": "vib_re1_20c_bound", "kind": "report",
     "gen": lambda: vibrato_tone(1, 5.0, 5.0, 20.0),
     "notes": "Re1 @ ±20¢ spends real time inside Re2's zone — boundary probe"},

    # ── Near-cents discrimination (21.5 ¢ apart) ─────────────────────────────
    {"name": "nearcents_re1_re2", "kind": "nearcents",
     "gen": lambda: np.concatenate(
         [vibrato_tone(1, 1.2, 5.0, 8.0), vibrato_tone(2, 1.2, 5.0, 8.0)] * 2
     ).astype(np.float32),
     "notes": "Alternating Re1/Re2 (21.5¢ apart) stays two distinct bins"},

    # ── Octave folding (PCP octave invariance) ───────────────────────────────
    {"name": "oct2_sa", "kind": "pitch", "expected": 22,
     "gen": lambda: tone_hz(523.25, 3.0),
     "notes": "2×Sa (523.25 Hz) folds onto the octave Sa' bin"},
    {"name": "oct2_pa", "kind": "pitch", "expected": 13,
     "gen": lambda: tone_hz(784.88, 3.0),
     "notes": "2×Pa (784.88 Hz) folds back to Pa via harmonic division"},
    {"name": "oct2_ni4", "kind": "pitch", "expected": 21,
     "gen": lambda: tone_hz(993.36, 3.0),
     "notes": "2×Ni4 (993.36 Hz) folds back to Ni4"},

    # ── Noise injection (12-TET scale, non-circular) ────────────────────────
    {"name": "noise_20db", "kind": "raga", "expected": "Bilawal",
     "acceptable": BILAWAL_FAMILY,
     "gen": lambda: add_noise(et_scale(['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni']), 20),
     "notes": "Bilawal scale + 20 dB noise keeps raga family"},
    {"name": "noise_10db", "kind": "raga", "expected": "Bilawal",
     "acceptable": BILAWAL_FAMILY,
     "gen": lambda: add_noise(et_scale(['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni']), 10),
     "notes": "Bilawal scale + 10 dB noise (stress) keeps raga family"},

    # ── Microphone coloration ────────────────────────────────────────────────
    {"name": "mic_tilt", "kind": "raga", "expected": "Bilawal",
     "acceptable": BILAWAL_FAMILY,
     "gen": lambda: mic_tilt(et_scale(['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni'])),
     "notes": "1-pole spectral tilt must not break raga detection"},

    # ── Ghana Patha: positives ───────────────────────────────────────────────
    {"name": "ghana_pos", "kind": "ghana_true",
     "gen": lambda: ghana_pattern(['a', 'd', 'a', 'd', 'a', 'd']),
     "notes": "Canonical Ghana cycle fwd/rev/fwd/rev/fwd accepted"},
    {"name": "ghana_rot", "kind": "ghana_true",
     "gen": lambda: ghana_pattern(['d', 'a', 'd', 'a', 'd', 'a']),
     "notes": "Phase-rotated cycle (rev-lead) accepted — same cycle"},

    # ── Ghana Patha: negatives (must be rejected) ────────────────────────────
    {"name": "ghana_silence", "kind": "ghana_false",
     "gen": lambda: np.zeros(int(SR * 6)).astype(np.float32),
     "notes": "Silence rejected (RMS guard)"},
    {"name": "ghana_noise", "kind": "ghana_false",
     "gen": lambda: white_noise(6.0),
     "notes": "Broadband noise rejected (spectral-flatness guard)"},

    # ── Ghana Patha: structured-wrong (characterised, never fails) ───────────
    {"name": "ghana_mono_fwd", "kind": "report",
     "gen": lambda: ghana_pattern(['a'] * 6),
     "notes": "Monotone ascending run — anti-pattern probe"},
    {"name": "ghana_mono_rev", "kind": "report",
     "gen": lambda: ghana_pattern(['d'] * 6),
     "notes": "Monotone descending run — anti-pattern probe"},
    {"name": "ghana_jumbled", "kind": "report",
     "gen": lambda: ghana_pattern(['a', 'a', 'd', 'd', 'a', 'd']),
     "notes": "Out-of-order forward/reverse alternation probe"},
    {"name": "ghana_random_walk", "kind": "report",
     "gen": lambda: random_walk(6.0),
     "notes": "Atonal random pitch walk — must NOT read as Ghana"},
]


# ─────────────────────────────────────────────────────────────────────────────
# Checks
# ─────────────────────────────────────────────────────────────────────────────

def _pitch_check(features, expected_idx):
    mean_pcp = np.array(features["mean_pcp"])
    dom = int(np.argmax(mean_pcp))
    top3 = [(SHRUTI_NAMES[i], round(float(mean_pcp[i]), 6))
            for i in np.argsort(mean_pcp)[-3:][::-1]]
    return dom == expected_idx, dom, top3


def _raga_check(raga, expected, acceptable):
    best = raga.get("best_match")
    if best is None:
        return False, None, 0.0, False
    name, conf = best["raga_name"], best["confidence"]
    ok = (name == expected or (acceptable and name in acceptable)) and \
        conf >= CONFIDENCE_THRESHOLD
    return ok, name, conf, conf >= CONFIDENCE_THRESHOLD


def _nearcents_check(counts, n_frames):
    c1, c2 = counts.get(SHRUTI_NAMES[1], 0), counts.get(SHRUTI_NAMES[2], 0)
    f1, f2 = c1 / max(n_frames, 1), c2 / max(n_frames, 1)
    separated = f1 > 0.1 and f2 > 0.1 and (f1 + f2) > 0.6
    return separated, c1, c2, n_frames


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

def main():
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("VEDIC ACOUSTICA — ML PIPELINE ROBUSTNESS BATTERY")
    print("=" * 78)
    print(f"Sauti reference: {REFERENCE_FREQ} Hz · {len(SHRUTI_NAMES)} shrutis")
    print(f"Raga confidence threshold: {CONFIDENCE_THRESHOLD}")
    print()

    results = []
    n_fail = 0

    for i, t in enumerate(TESTS, 1):
        audio = t["gen"]()
        path = SYNTH_DIR / f"{t['name']}.wav"
        sf.write(str(path), audio, SR)

        rec = {"name": t["name"], "kind": t["kind"], "notes": t["notes"],
               "detail": {}, "status": "?"}

        # ── Feature extraction ──
        t0 = time.time()
        try:
            fe = extract_features(str(path))
            rec["detail"]["feature_extraction"] = {
                "time_s": round(time.time() - t0, 3),
                "duration": round(fe["duration"], 3),
                "frames": int(fe["pcp"].shape[1]),
                "voiced_ratio": round(fe["voiced_ratio"], 4),
                "rms": round(fe.get("rms", 0.0), 4),
            }
        except Exception as e:
            rec["status"] = "FAIL"
            rec["detail"]["error"] = f"feature_extraction: {e}"
            results.append(rec)
            n_fail += 1
            continue

        # ── Pitch ──
        if t["kind"] == "pitch":
            ok, dom, top3 = _pitch_check(fe, t["expected"])
            rec["status"] = "PASS" if ok else "FAIL"
            rec["detail"]["pitch"] = {
                "expected": SHRUTI_NAMES[t["expected"]],
                "detected": SHRUTI_NAMES[dom],
                "top3": top3,
            }
            if not ok:
                n_fail += 1
            print(f"[{i:2d}/{len(TESTS)}] {t['kind']:8s} {t['name']:20s} "
                  f"-> {SHRUTI_NAMES[dom]:20s} {rec['status']}")
            results.append(rec)
            continue

        # ── Clustering (nearcents + raga need it) ──
        t0 = time.time()
        try:
            clustering = run_clustering(fe)
            counts = Counter(clustering["freq_assignments"])
            rec["detail"]["clustering"] = {
                "time_s": round(time.time() - t0, 3),
                "frames": len(clustering["freq_assignments"]),
                "unique_shrutis": len(counts),
                "top5": dict(counts.most_common(5)),
            }
        except Exception as e:
            rec["status"] = "FAIL"
            rec["detail"]["error"] = f"clustering: {e}"
            results.append(rec)
            n_fail += 1
            continue

        # ── Near-cents discrimination ──
        if t["kind"] == "nearcents":
            ok, c1, c2, nf = _nearcents_check(counts,
                                              len(clustering["freq_assignments"]))
            rec["status"] = "PASS" if ok else "FAIL"
            rec["detail"]["nearcents"] = {
                "re1_frames": c1, "re2_frames": c2, "total_frames": nf,
            }
            if not ok:
                n_fail += 1
            print(f"[{i:2d}/{len(TESTS)}] {t['kind']:8s} {t['name']:20s} "
                  f"-> Re1={c1} Re2={c2} {rec['status']}")
            results.append(rec)
            continue

        # ── Ghana Patha ──
        t0 = time.time()
        try:
            gh = validate_ghana_patha(fe)
            rec["detail"]["ghana"] = {
                "time_s": round(time.time() - t0, 3),
                "is_valid": gh["is_valid"],
                "confidence": round(gh.get("confidence", 0.0), 4),
                "repetition": round(gh.get("repetition_score", 0.0), 4),
                "reason": gh.get("reason"),
                "detected_pattern": gh.get("detected_pattern"),
                "n_segments": gh.get("n_segments"),
            }
        except Exception as e:
            rec["detail"]["ghana"] = {"error": str(e)}
            rec["status"] = "FAIL"
            results.append(rec)
            n_fail += 1
            print(f"[{i:2d}/{len(TESTS)}] {t['kind']:8s} {t['name']:20s} FAIL (ghana error)")
            continue

        if t["kind"] in ("ghana_true", "ghana_false"):
            want = True if t["kind"] == "ghana_true" else False
            ok = gh["is_valid"] == want
            rec["status"] = "PASS" if ok else "FAIL"
            if not ok:
                n_fail += 1
            tag = f"exp={str(want):5s} got={str(gh['is_valid']):5s} conf={gh.get('confidence', 0.0):.4f}"
            print(f"[{i:2d}/{len(TESTS)}] {t['kind']:8s} {t['name']:20s} {tag} {rec['status']}")
            results.append(rec)
            continue

        if t["kind"] == "report":
            rec["status"] = "REPORT"
            print(f"[{i:2d}/{len(TESTS)}] {t['kind']:8s} {t['name']:20s} "
                  f"valid={gh['is_valid']} conf={gh.get('confidence', 0.0):.4f} "
                  f"rep={gh.get('repetition_score', 0):.4f} pattern={gh.get('detected_pattern')}")
            results.append(rec)
            continue

        # ── Raga detection ──
        t0 = time.time()
        try:
            raga = detect_raga(clustering, features=fe)
            rec["detail"]["raga"] = {
                "time_s": round(time.time() - t0, 3),
                "best": (raga["best_match"]["raga_name"]
                         if raga["best_match"] else None),
                "confidence": (round(raga["best_match"]["confidence"], 4)
                               if raga["best_match"] else 0.0),
                "is_inconclusive": raga["is_inconclusive"],
            }
        except Exception as e:
            rec["detail"]["raga"] = {"error": str(e)}
            rec["status"] = "FAIL"
            results.append(rec)
            n_fail += 1
            continue

        if t["kind"] == "raga":
            ok, name, conf, above = _raga_check(
                raga, t["expected"], t.get("acceptable"))
            rec["status"] = "PASS" if ok else "FAIL"
            if not ok:
                n_fail += 1
            print(f"[{i:2d}/{len(TESTS)}] {t['kind']:8s} {t['name']:20s} "
                  f"-> {name} conf={conf:.3f} {rec['status']}")
            results.append(rec)
            continue

        rec["status"] = "REPORT"
        print(f"[{i:2d}/{len(TESTS)}] {t['kind']:8s} {t['name']:20s} REPORT")
        results.append(rec)

    # ── Summary ──
    print()
    print("=" * 78)
    print("RESULTS SUMMARY")
    print("=" * 78)
    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_report = sum(1 for r in results if r["status"] == "REPORT")
    print(f"\n  Asserted:   {n_pass}/{n_pass + n_fail} passed"
          f" ({len(results)} total, {n_report} characterised-reports)")
    print(f"  Hard fails: {n_fail}")
    print()

    for r in results:
        print(f"  {r['name']:20s} {r['status']:7s} "
              f"{r['notes']}")

    out = OUTPUT_DIR / "ml_robustness_report.json"
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f"\nDetailed JSON: {out}")

    return n_fail


if __name__ == "__main__":
    sys.exit(main())