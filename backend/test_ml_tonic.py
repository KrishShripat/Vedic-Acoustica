#!/usr/bin/env python3
"""
Vedic Acoustica — Dynamic Tonic (Sa) Verification
==================================================

Every other harness renders its material with Sa = C4 (261.626 Hz) so the fixed
23-bin Shruti grid and the audio share one reference.  This suite is the missing
half: it renders canonical raga scales at several *non-C* tonics and proves the
pipeline recovers the same raga once the grid is transposed onto the
performance's own Sa.

Two independent guarantees are checked per (scale, tonic) pair:

  1. Mechanism  — with the true tonic supplied explicitly, the transposed run
                  must return exactly the same raga as the C4 reference.  This
                  isolates the transposition arithmetic from any estimation
                  error.
  2. Auto-detect— with ``auto_tonic=True`` the estimator must recover the tonic
                  to within a quarter-tone AND still land on the correct raga
                  (or an accepted sibling), i.e. the end-to-end capability.

The tonic estimator is also run (report-only) over the real recordings in
``test_audio/`` to document what tonic they are actually keyed to.

Result summary is written to test_reports/ml_tonic_report.json.  Exit code is
non-zero when any hard assertion fails (CI gate).
"""

import sys, os, json, tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vedic_acoustica.settings")

import numpy as np
import soundfile as sf

from ml_engine.audio_processing import extract_features, SR
from ml_engine.ml_engine import run_clustering
from ml_engine.raga_mapping import detect_raga
from ml_engine.tonic import estimate_tonic_cents

AUDIO_DIR = BACKEND_DIR.parent / "test_audio"
OUTPUT_DIR = BACKEND_DIR.parent / "test_reports"
REFERENCE_FREQ = 261.626

# Semitone offsets from Sa for the 12-TET note vocabulary used to render scales.
_NOTE = {
    'Sa': 0, 'Re_b': 1, 'Re': 2, 'Ga_b': 3, 'Ga': 4, 'Ma': 5,
    'Ma_s': 6, 'Pa': 7, 'Dha_b': 8, 'Dha': 9, 'Ni_b': 10, 'Ni': 11,
}

# Non-circular 12-TET scales (same note sets the audit suite uses) and the
# ragas they are allowed to resolve to.
SCALES = {
    'kalyani':  (['Sa', 'Re', 'Ga', 'Ma_s', 'Pa', 'Dha', 'Ni'],
                 ['Kalyani', 'Mechakalyani', 'Yaman']),
    'bhairav':  (['Sa', 'Re_b', 'Ga', 'Ma', 'Pa', 'Dha_b', 'Ni'],
                 ['Bhairav', 'Mayamalavagowla']),
    'malkauns': (['Sa', 'Ga_b', 'Ma', 'Dha_b', 'Ni_b'],
                 ['Malkauns']),
    'bhupali':  (['Sa', 'Re', 'Ga', 'Pa', 'Dha'],
                 ['Bhupali']),
    'shankara': (['Sa', 'Ga', 'Pa', 'Ni'],
                 ['Shankara']),
}

# Performance tonics to test (Hz).  C4 is the reference; the rest are shifts.
TONICS = {
    'C4': 261.626,
    'D4': 293.665,
    'G3': 195.998,
    'F4': 349.228,
}

REFERENCE_TONIC = 'C4'


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────

def _tone(freq, dur):
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    return (0.50 * np.sin(2 * np.pi * freq * t) +
            0.30 * np.sin(2 * np.pi * 2 * freq * t) +
            0.15 * np.sin(2 * np.pi * 3 * freq * t)).astype(np.float32)


def render_scale(notes, tonic_hz, note_dur=0.30, sa_long=0.90):
    """Ghana-free scale with a sustained Sa at head and tail so the tonic
    dominates the pitch histogram (as it does in real recitation)."""
    parts = [_tone(tonic_hz, sa_long)]
    semis = [_NOTE[n] for n in notes]
    for _ in range(2):
        for s in semis:
            parts.append(_tone(tonic_hz * 2 ** (s / 12.0), note_dur))
    for s in reversed(semis):
        parts.append(_tone(tonic_hz * 2 ** (s / 12.0), note_dur))
    parts.append(_tone(tonic_hz, sa_long))
    return np.concatenate(parts).astype(np.float32)


def _write_tmp(y):
    fd, path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    sf.write(path, y, SR)
    return path


def _best_raga(features):
    clustering = run_clustering(features)
    result = detect_raga(clustering, features=features)
    best = result.get('best_match')
    return best['raga_name'] if best else None


def _true_cents(tonic_hz):
    return 1200.0 * np.log2(tonic_hz / REFERENCE_FREQ)


def _circular_cents_error(a, b):
    return abs(((a - b + 600.0) % 1200.0) - 600.0)


# ─────────────────────────────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────────────────────────────

def main():
    results = []
    hard_fails = 0

    references = {}
    for name, (notes, _ok) in SCALES.items():
        path = _write_tmp(render_scale(notes, TONICS[REFERENCE_TONIC]))
        feats = extract_features(path)
        os.unlink(path)
        references[name] = _best_raga(feats)

    for name, (notes, acceptable) in SCALES.items():
        ref_raga = references[name]
        for tonic_name, tonic_hz in TONICS.items():
            if tonic_name == REFERENCE_TONIC:
                continue

            path = _write_tmp(render_scale(notes, tonic_hz))

            feats_manual = extract_features(path, tonic_hz=tonic_hz)
            manual_raga = _best_raga(feats_manual)

            feats_auto = extract_features(path, auto_tonic=True)
            os.unlink(path)
            auto_raga = _best_raga(feats_auto)

            est_err = _circular_cents_error(
                feats_auto.get('tonic_cents', 0.0), _true_cents(tonic_hz),
            )

            mechanism_ok = (manual_raga == ref_raga)
            auto_ok = (est_err <= 25.0) and (auto_raga in acceptable) \
                and (auto_raga == manual_raga)

            if not (mechanism_ok and auto_ok):
                hard_fails += 1

            results.append({
                'scale': name,
                'tonic': tonic_name,
                'tonic_hz': round(tonic_hz, 3),
                'reference_raga': ref_raga,
                'manual_raga': manual_raga,
                'auto_raga': auto_raga,
                'tonic_error_cents': round(float(est_err), 2),
                'tonic_confidence': round(float(feats_auto.get('tonic_confidence', 0.0)), 3),
                'mechanism': 'PASS' if mechanism_ok else 'FAIL',
                'auto': 'PASS' if auto_ok else 'FAIL',
            })
            mark = 'PASS' if (mechanism_ok and auto_ok) else 'FAIL'
            print(f"  {name:10s} @ {tonic_name:3s} ({tonic_hz:7.2f} Hz)  "
                  f"ref={str(ref_raga):12s} manual={str(manual_raga):12s} "
                  f"auto={str(auto_raga):12s} err={est_err:5.1f}c "
                  f"conf={feats_auto.get('tonic_confidence', 0.0):.2f}  {mark}")

    # ── Real recordings: report the tonic actually being used (report-only) ──
    real = []
    for path in sorted(str(p) for p in AUDIO_DIR.glob("*.wav")):
        try:
            feats = extract_features(path, auto_tonic=True)
        except Exception as exc:  # pragma: no cover
            real.append({'file': Path(path).name, 'error': str(exc)})
            continue
        real.append({
            'file': Path(path).name,
            'tonic_hz': round(float(feats.get('tonic_hz', 0.0)), 2),
            'tonic_cents': round(float(feats.get('tonic_cents', 0.0)), 1),
            'tonic_confidence': round(float(feats.get('tonic_confidence', 0.0)), 3),
            'tonic_source': feats.get('tonic_source'),
        })

    report = {
        'reference_tonic': REFERENCE_FREQ,
        'reference_ragas': references,
        'tonic_trials': results,
        'real_recordings': real,
        'hard_fails': hard_fails,
        'summary': {
            'trials': len(results),
            'passed': sum(1 for r in results
                          if r['mechanism'] == 'PASS' and r['auto'] == 'PASS'),
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "ml_tonic_report.json"
    out.write_text(json.dumps(report, indent=2))

    print("\n" + "=" * 72)
    print(f"  Trials: {report['summary']['passed']}/{report['summary']['trials']} passed")
    print(f"  Hard fails: {hard_fails}")
    print(f"  Detailed JSON: {out}")
    print("=" * 72)

    return 1 if hard_fails else 0


if __name__ == "__main__":
    sys.exit(main())
