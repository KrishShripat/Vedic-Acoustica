#!/usr/bin/env python3
"""
Vedic Acoustica — ML Pipeline Audit Test Suite (Corrected v2)
=============================================================

Cross-references shruti_mapping.py and raga_mapping.py as single source of
truth. Reports PASS/FAIL on:
  1. Pitch detection — does the dominant PCP bin match the known tone?
  2. Raga detection  — is the expected raga (or an acceptable sibling) the
     best match at or above the confidence threshold?
  3. Ghana Patha     — does the pipeline produce valid output?
  4. Pipeline health — do all 4 stages complete without error?

Anti-circularity
----------------
Pure-tone pitch tests are generated AT the Shruti frequencies (that is exactly
the mapping being validated).  Raga scale tests, however, are generated with an
INDEPENDENT 12-TET piano tuning so the detector can never "recognise" a raga
just because the audio was synthesised from the same JI table.  Raga scales are
therefore judged honestly: some 12-TET scales lock on to a single raga, while
others (e.g. the plain major scale) genuinely fit several ragas of the same
family, so an ``acceptable_ragas`` list is used there instead of pretending an
ambiguous result is deterministic.

Ground truth is derived from RAGA_DATABASE and SHRUTI_FREQUENCIES at runtime.
"""

import sys, os, json, time, traceback
from pathlib import Path
from collections import Counter

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vedic_acoustica.settings")

import numpy as np
import soundfile as sf

from ml_engine.shruti_mapping import (
    REFERENCE_FREQ, SHRUTI_FREQUENCIES, SHRUTI_NAMES, SHRUTI_RATIOS
)
from ml_engine.audio_processing import extract_features, SR
from ml_engine.ml_engine import run_clustering
from ml_engine.ghana_patha import validate_ghana_patha
from ml_engine.raga_mapping import detect_raga, RAGA_DATABASE, CONFIDENCE_THRESHOLD

SYNTH_DIR = BACKEND_DIR.parent / "test_audio" / "synthetic"
OUTPUT_DIR = BACKEND_DIR.parent / "test_reports"


# ─────────────────────────────────────────────────────────────────────────────
# Audio generation
# ─────────────────────────────────────────────────────────────────────────────

def _freq(idx):
    """Frequency in Hz for a Shruti bin index (0-based) from SHRUTI_FREQUENCIES."""
    return SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]


def tone(idx, dur=5.0):
    """Harmonic-rich sine tone at the frequency of Shruti bin `idx` (for pitch ground truth)."""
    freq = _freq(idx)
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    w = (0.50 * np.sin(2*np.pi*freq*t) +
         0.30 * np.sin(2*np.pi*2*freq*t) +
         0.15 * np.sin(2*np.pi*3*freq*t) +
         0.05 * np.sin(2*np.pi*4*freq*t))
    return w.astype(np.float32)


def tone_hz(freq, dur):
    """Harmonic-rich sine tone at an arbitrary Hz (independent 12-TET ground truth)."""
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    w = (0.50 * np.sin(2*np.pi*freq*t) +
         0.30 * np.sin(2*np.pi*2*freq*t) +
         0.15 * np.sin(2*np.pi*3*freq*t) +
         0.05 * np.sin(2*np.pi*4*freq*t))
    return w.astype(np.float32)


# ── Independent 12-TET tuning (A4=440, Sa = C4) ─────────────────────────────
# Raga scale tests are generated with this tuning so detection is never
# circular with the JI Shruti table the detector is built on.
_ET = {
    'Sa':    261.63,
    'Re_b':  261.63 * 2 ** (1 / 12),    # 100 ¢  komal Re
    'Re':    261.63 * 2 ** (2 / 12),    # 200 ¢  shuddha Re
    'Ga_b':  261.63 * 2 ** (3 / 12),    # 300 ¢  komal Ga
    'Ga':    261.63 * 2 ** (4 / 12),    # 400 ¢  shuddha Ga
    'Ma':    261.63 * 2 ** (5 / 12),    # 500 ¢  shuddha Ma
    'Ma_s':  261.63 * 2 ** (6 / 12),    # 600 ¢  tivra Ma
    'Pa':    261.63 * 2 ** (7 / 12),    # 700 ¢  Pa
    'Dha_b': 261.63 * 2 ** (8 / 12),    # 800 ¢  komal Dha
    'Dha':   261.63 * 2 ** (9 / 12),    # 900 ¢  shuddha Dha
    'Ni_b':  261.63 * 2 ** (10 / 12),   # 1000 ¢ komal Ni
    'Ni':    261.63 * 2 ** (11 / 12),   # 1100 ¢ shuddha Ni
    'Sa2':   261.63 * 2,                # 1200 ¢ octave Sa'
}


def et_scale(notes, note_dur=0.4, rounds=3, descend=True):
    """12-TET note sequence (rounds× ascending, then descending if ``descend``)."""
    parts = []
    for _ in range(rounds):
        parts.append([tone_hz(_ET[n], note_dur) for n in notes])
    if descend:
        parts.append([tone_hz(_ET[n], note_dur) for n in reversed(notes)])
    waves = [w for group in parts for w in group]
    return np.concatenate(waves).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# Test definitions
# ─────────────────────────────────────────────────────────────────────────────
# Each test has:
#   name            : identifier
#   gen             : lambda → (np.ndarray, SR) audio
#   expected_shruti : Shruti bin (0-22) expected to dominate PCP, or None
#   expected_raga   : raga name from RAGA_DATABASE, or None
#   acceptable_ragas: list of ragas that genuinely share the scale (ties)
#   check_ghana     : bool — require Ghana Patha valid
#   notes           : description
#   raga_known_limitation : documented reason the match may be ambiguous

TESTS = [
    # ── Pitch detection tests (pure tones at the JI Shruti frequencies) ──────
    {
        "name": "pitch_sa_261",
        "gen": lambda: (tone(0), SR),
        "expected_shruti": 0,  # Sa
        "expected_raga": None,
        "notes": "Pure Sa tone (261.63 Hz) — pitch detection ground truth",
    },
    {
        "name": "pitch_pa_392",
        "gen": lambda: (tone(13), SR),
        "expected_shruti": 13,  # Pa
        "expected_raga": None,
        "notes": "Pure Pa tone (392.44 Hz) — pitch detection ground truth",
    },
    {
        "name": "pitch_re1_276",
        "gen": lambda: (tone(1), SR),
        "expected_shruti": 1,  # Re1 komal (256/243)
        "expected_raga": None,
        "notes": "Pure Re1 (275.65 Hz) — komal Re limb",
    },
    {
        "name": "pitch_re2_279",
        "gen": lambda: (tone(2), SR),
        "expected_shruti": 2,  # Re2 komal (16/15)
        "expected_raga": None,
        "notes": "Pure Re2 (279.07 Hz) — komal Re limb",
    },
    {
        "name": "pitch_ga4_331",
        "gen": lambda: (tone(8), SR),
        "expected_shruti": 8,  # Ga4 shuddha (81/64)
        "expected_raga": None,
        "notes": "Pure Ga4 (331.14 Hz) — shuddha Ga limb",
    },
    {
        "name": "pitch_dha1_413",
        "gen": lambda: (tone(14), SR),
        "expected_shruti": 14,  # Dha1 komal (128/81)
        "expected_raga": None,
        "notes": "Pure Dha1 (413.43 Hz) — komal Dha limb",
    },
    {
        "name": "pitch_ma_oct_698",
        "gen": lambda: (tone_hz(697.66, 5.0), SR),
        "expected_shruti": 9,  # 698 Hz ≈ 2×Ma1 → folds to the same PCP bin
        "expected_raga": None,
        "notes": "High tone (697.66 Hz) — octave-invariance of PCP folds it to Ma1 bin",
    },

    # ── Scale/raga detection tests (12-TET, non-circular) ──────────────────
    {
        "name": "scale_major",
        "gen": lambda: (et_scale(['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni']), SR),
        "expected_raga": "Bilawal",
        "acceptable_ragas": ["Bilawal", "Mand", "Shankarabharanam", "Kambhoji"],
        "expected_shruti": None,
        "notes": "12-TET major scale — shared by several heptatonic ragas",
        "raga_known_limitation": (
            "A plain 12-TET major scale is genuinely shared by Bilawal, Mand, "
            "Shankarabharanam and Kambhoji (same swara zones). Detection should "
            "pick one of them at ≥40%."
        ),
    },
    {
        "name": "scale_kalyani",
        "gen": lambda: (et_scale(['Sa', 'Re', 'Ga', 'Ma_s', 'Pa', 'Dha', 'Ni']), SR),
        "expected_raga": "Kalyani",
        "acceptable_ragas": ["Kalyani", "Mechakalyani", "Yaman"],
        "expected_shruti": None,
        "notes": "12-TET Lydian scale — distinguishes via tivra Ma",
        "raga_known_limitation": (
            "Kalyani and Mechakalyani are the same (Carnatic) Lydian scale; the "
            "Hindustani raga Yaman shares that scale so all three are acceptable. "
            "Yaman can win because it owns a Pakad template used as a tiebreak."
        ),
    },
    {
        "name": "scale_bhairav",
        "gen": lambda: (et_scale(['Sa', 'Re_b', 'Ga', 'Ma', 'Pa', 'Dha_b', 'Ni']), SR),
        "expected_raga": "Bhairav",
        "acceptable_ragas": ["Bhairav", "Mayamalavagowla"],
        "expected_shruti": None,
        "notes": "12-TET Bhairav scale (komal Re & Dha, shuddha Ga & Ni)",
        "raga_known_limitation": (
            "Mayamalavagowla shares Bhairav's swara set; either may win the tie."
        ),
    },
    {
        "name": "scale_malkauns",
        "gen": lambda: (et_scale(['Sa', 'Ga_b', 'Ma', 'Dha_b', 'Ni_b']), SR),
        "expected_raga": "Malkauns",
        "acceptable_ragas": [],
        "expected_shruti": None,
        "notes": "12-TET Malkauns pentatonic — unique swara combination",
        "raga_known_limitation": None,
    },
    {
        "name": "scale_khamaj",
        "gen": lambda: (et_scale(['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni_b']), SR),
        "expected_raga": "Khamaj",
        "acceptable_ragas": ["Khamaj", "Jhinjhoti"],
        "expected_shruti": None,
        "notes": "12-TET Khamaj scale (komal Ni)",
        "raga_known_limitation": (
            "Jhinjhoti shares Khamaj's swara zones; either may win."
        ),
    },
    {
        "name": "scale_bhupali",
        "gen": lambda: (et_scale(['Sa', 'Re', 'Ga', 'Pa', 'Dha']), SR),
        "expected_raga": "Bhupali",
        "acceptable_ragas": ["Bhupali"],
        "expected_shruti": None,
        "notes": "12-TET Bhupali pentatonic (Sa Re Ga Pa Dha)",
        "raga_known_limitation": None,
    },
    {
        "name": "scale_shankara",
        "gen": lambda: (et_scale(['Sa', 'Ga', 'Pa', 'Ni']), SR),
        "expected_raga": "Shankara",
        "acceptable_ragas": ["Shankara"],
        "expected_shruti": None,
        "notes": "12-TET Shankara audav scale (Sa Ga Pa Ni)",
        "raga_known_limitation": None,
    },

    # ── Ghana Patha structure test ─────────────────────────────────────────
    {
        "name": "ghana_sim",
        "gen": lambda: (_make_ghana_sim(), SR),
        "expected_raga": None,
        "expected_shruti": None,
        "check_ghana": True,
        "notes": "Ghana Patha simulation — fwd/rev/fwd/rev/fwd pattern",
    },
]


def _make_ghana_sim():
    """Ghana-like pattern: 6 phrases of [asc, desc, asc, desc, asc, desc].
    Each phrase is exactly 1s (5 notes × 0.2s) so the validation's 1-second
    segment grid lands one phrase per segment and repetition is measurable."""
    ascending = [0, 4, 8, 9, 13]      # Sa Re-s Ga-s Ma-s Pa
    descending = [13, 9, 8, 4, 0]
    parts = [ascending, descending, ascending,
             descending, ascending, descending]
    waves = []
    for part in parts:
        for idx in part:
            waves.append(tone(idx, 0.2))
    return np.concatenate(waves).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# Checks
# ─────────────────────────────────────────────────────────────────────────────

def check_pitch_accuracy(features, expected_idx):
    """Check if the dominant PCP bin matches the expected Shruti index."""
    mean_pcp = np.array(features["mean_pcp"])
    dominant_idx = int(np.argmax(mean_pcp))
    dominant_name = SHRUTI_NAMES[dominant_idx]

    top3_idx = np.argsort(mean_pcp)[-3:][::-1]
    top3 = [(SHRUTI_NAMES[i], round(float(mean_pcp[i]), 6)) for i in top3_idx]

    passed = dominant_idx == expected_idx
    return passed, dominant_idx, dominant_name, top3


def check_raga_accuracy(raga_result, expected_name, acceptable=None):
    """
    Check the detected raga.

    Passes when the best match equals ``expected_name`` OR is a member of
    ``acceptable`` (genuinely identical-scale siblings).  Confidence must
    clear CONFIDENCE_THRESHOLD for the match to be conclusive either way.
    """
    best = raga_result.get("best_match")
    if best is None:
        return False, None, 0.0, [], False

    detected_name = best["raga_name"]
    detected_conf = best["confidence"]

    top3 = [
        {"name": m["raga_name"], "conf": m["confidence"], "tradition": m["tradition"]}
        for m in raga_result.get("matches", [])[:3]
    ]

    exact = detected_name == expected_name
    acceptable_match = bool(acceptable) and detected_name in acceptable
    above_threshold = detected_conf >= CONFIDENCE_THRESHOLD
    passed = (exact or acceptable_match) and above_threshold
    return passed, detected_name, detected_conf, top3, above_threshold


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("VEDIC ACOUSTICA — ML PIPELINE AUDIT TEST (CORRECTED v2)")
    print("=" * 72)
    print(f"Reference freq: {REFERENCE_FREQ} Hz (Sa)")
    print(f"Total Shrutis: {len(SHRUTI_NAMES)}")
    print(f"Total ragas in database: {len(RAGA_DATABASE)}")
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print()

    all_results = []

    for i, test in enumerate(TESTS, 1):
        print(f"\n{'─'*72}")
        print(f"[{i}/{len(TESTS)}] {test['name']}: {test['notes']}")
        print(f"{'─'*72}")

        result = {
            "name": test["name"],
            "notes": test["notes"],
            "expected_raga": test.get("expected_raga"),
            "acceptable_ragas": test.get("acceptable_ragas"),
            "expected_shruti": test.get("expected_shruti"),
            "raga_known_limitation": test.get("raga_known_limitation"),
            "check_ghana": test.get("check_ghana", False),
            "tests": {},
            "pipeline_ok": False,
        }

        # Generate audio
        audio, sr = test["gen"]()
        audio_path = SYNTH_DIR / f"{test['name']}.wav"
        sf.write(str(audio_path), audio, SR)
        duration = len(audio) / SR
        print(f"  Audio: {duration:.1f}s, {SR} Hz, {len(audio)} samples")

        # ── Stage 1: Feature Extraction ──
        t0 = time.time()
        try:
            features = extract_features(str(audio_path))
            t1 = time.time()
            result["tests"]["feature_extraction"] = {
                "pass": True, "time_s": round(t1 - t0, 3),
                "duration": round(features["duration"], 3),
                "frames": int(features["pcp"].shape[1]),
                "voiced_ratio": round(features["voiced_ratio"], 4),
            }
            print(f"  Feature Extraction: OK ({t1-t0:.3f}s) | "
                  f"frames={features['pcp'].shape[1]} voiced={features['voiced_ratio']:.2%}")
        except Exception as e:
            result["tests"]["feature_extraction"] = {"pass": False, "error": str(e)}
            print(f"  Feature Extraction: FAIL — {e}")
            all_results.append(result)
            continue

        # ── Stage 2: Clustering ──
        t0 = time.time()
        try:
            clustering = run_clustering(features)
            t1 = time.time()
            result["tests"]["clustering"] = {
                "pass": True, "time_s": round(t1 - t0, 3),
                "frames": len(clustering["freq_assignments"]),
                "unique_shrutis": len(Counter(clustering["freq_assignments"])),
            }
            print(f"  Clustering: OK ({t1-t0:.3f}s) | "
                  f"unique_shrutis={result['tests']['clustering']['unique_shrutis']}")
        except Exception as e:
            result["tests"]["clustering"] = {"pass": False, "error": str(e)}
            print(f"  Clustering: FAIL — {e}")
            all_results.append(result)
            continue

        # ── Pitch accuracy check ──
        if test.get("expected_shruti") is not None:
            pitch_ok, dom_idx, dom_name, top3 = check_pitch_accuracy(
                features, test["expected_shruti"]
            )
            expected_name = SHRUTI_NAMES[test["expected_shruti"]]
            expected_freq = _freq(test["expected_shruti"])
            result["tests"]["pitch_accuracy"] = {
                "pass": pitch_ok,
                "expected": {"index": test["expected_shruti"], "name": expected_name,
                             "freq_hz": expected_freq},
                "detected": {"index": dom_idx, "name": dom_name},
                "top3_pcp": top3,
            }
            status = "PASS" if pitch_ok else "FAIL"
            print(f"  Pitch Accuracy: {status} | expected={expected_name} "
                  f"({expected_freq:.2f} Hz) detected={dom_name}")
            print(f"    Top 3 PCP: {top3}")

        # ── Stage 3: Ghana Patha ──
        t0 = time.time()
        try:
            ghana = validate_ghana_patha(features)
            t1 = time.time()
            ghana_pass = not test.get("check_ghana") or ghana["is_valid"]
            result["tests"]["ghana_patha"] = {
                "pass": ghana_pass, "time_s": round(t1 - t0, 3),
                "is_valid": ghana["is_valid"],
                "confidence": ghana["confidence"],
                "repetition": ghana["repetition_score"],
                "n_segments": ghana.get("n_segments", 0),
                "detected_pattern": ghana.get("detected_pattern", []),
            }
            status = "PASS" if ghana_pass else "FAIL"
            print(f"  Ghana Patha: {status} ({t1-t0:.3f}s) | "
                  f"valid={ghana['is_valid']} conf={ghana['confidence']:.4f} "
                  f"rep={ghana['repetition_score']:.4f}")
        except Exception as e:
            result["tests"]["ghana_patha"] = {"pass": False, "error": str(e)}
            print(f"  Ghana Patha: FAIL — {e}")

        # ── Stage 4: Raga Detection ──
        t0 = time.time()
        try:
            raga = detect_raga(clustering, features=features)
            t1 = time.time()
            if test.get("expected_raga"):
                rag_pass, det_name, det_conf, top3, above_thresh = check_raga_accuracy(
                    raga, test["expected_raga"], test.get("acceptable_ragas")
                )
                result["tests"]["raga_detection"] = {
                    "pass": rag_pass, "time_s": round(t1 - t0, 3),
                    "expected_raga": test["expected_raga"],
                    "acceptable_ragas": test.get("acceptable_ragas"),
                    "detected_raga": det_name,
                    "detected_confidence": det_conf,
                    "above_threshold": above_thresh,
                    "top3": top3,
                    "is_inconclusive": raga["is_inconclusive"],
                    "detected_swaras": [s["swara"] for s in raga["detected_swaras"][:12]],
                    "raga_known_limitation": test.get("raga_known_limitation"),
                }
                status = "PASS" if rag_pass else "FAIL"
                lim_note = " (known limitation)" if test.get("raga_known_limitation") else ""
                print(f"  Raga Detection: {status}{lim_note} ({t1-t0:.3f}s) | "
                      f"expected={test['expected_raga']} detected={det_name} "
                      f"conf={det_conf:.4f} (above_thr={above_thresh})")
                top3_str = ", ".join(f"{m['name']}({m['conf']:.3f})" for m in top3)
                print(f"    Top 3: [{top3_str}]")
            else:
                result["tests"]["raga_detection"] = {
                    "pass": True, "time_s": round(t1 - t0, 3),
                    "is_inconclusive": raga["is_inconclusive"],
                    "best": (raga["best_match"]["raga_name"]
                             if raga["best_match"] else None),
                    "detected_swaras": [s["swara"] for s in raga["detected_swaras"][:12]],
                }
                best_name = raga["best_match"]["raga_name"] if raga["best_match"] else "None"
                print(f"  Raga Detection: INFO ({t1-t0:.3f}s) | "
                      f"best={best_name} inconclusive={raga['is_inconclusive']}")
        except Exception as e:
            result["tests"]["raga_detection"] = {"pass": False, "error": str(e)}
            print(f"  Raga Detection: FAIL — {e}")

        result["pipeline_ok"] = all(
            t.get("pass", False) for t in result["tests"].values()
        )
        all_results.append(result)

    # ── Summary ──
    print(f"\n{'='*72}")
    print("RESULTS SUMMARY")
    print(f"{'='*72}")

    total = len(all_results)
    pipeline_pass = sum(1 for r in all_results if r["pipeline_ok"])
    pitch_tests = [r for r in all_results if "pitch_accuracy" in r["tests"]]
    pitch_pass = sum(1 for r in pitch_tests if r["tests"]["pitch_accuracy"]["pass"])
    raga_tests = [r for r in all_results if r["tests"].get("raga_detection", {}).get("expected_raga")]
    raga_pass = sum(1 for r in raga_tests if r["tests"]["raga_detection"]["pass"])

    print(f"\n  Pipeline Health:     {pipeline_pass}/{total} passed")
    print(f"  Pitch Accuracy:      {pitch_pass}/{len(pitch_tests)} passed")
    print(f"  Raga Accuracy:       {raga_pass}/{len(raga_tests)} passed")
    print()

    for r in all_results:
        pipe = "OK" if r["pipeline_ok"] else "FAIL"
        pitch = r["tests"].get("pitch_accuracy")
        rag = r["tests"].get("raga_detection", {})
        gh = r["tests"].get("ghana_patha", {})

        parts = [f"{r['name']:25s} pipeline={pipe:4s}"]
        if pitch:
            parts.append(f"pitch={'PASS' if pitch['pass'] else 'FAIL'}")
        if rag.get("expected_raga"):
            parts.append(f"raga={'PASS' if rag['pass'] else 'FAIL'}")
        if gh:
            parts.append(f"ghana_conf={gh.get('confidence',0):.3f}")
        print(f"  {' | '.join(parts)}")

    # Save results
    out = OUTPUT_DIR / "audit_results.json"
    with open(out, "w") as fh:
        json.dump(all_results, fh, indent=2, default=str)
    print(f"\nDetailed JSON: {out}")

    return all_results


if __name__ == "__main__":
    main()