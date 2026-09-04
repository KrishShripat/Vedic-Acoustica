#!/usr/bin/env python3
"""
Vedic Acoustica — ML Pipeline End-to-End Test Suite

Generates synthetic audio at known Shruti frequencies, runs the full 4-stage
ML pipeline on all test audio files, and outputs structured JSON results
for report generation.
"""

import sys
import os
import json
import time
import traceback
from pathlib import Path

# ── Setup paths ──────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
TEST_AUDIO_DIR = PROJECT_DIR / "test_audio"
SYNTH_DIR = PROJECT_DIR / "test_audio" / "synthetic"
OUTPUT_DIR = PROJECT_DIR / "test_reports"

sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vedic_acoustica.settings")

# ── Imports ──────────────────────────────────────────────────────────────────
import numpy as np
import soundfile as sf

from ml_engine.shruti_mapping import (
    REFERENCE_FREQ, SHRUTI_FREQUENCIES, SHRUTI_NAMES, SHRUTI_RATIOS
)
from ml_engine.audio_processing import extract_features, SR
from ml_engine.ml_engine import run_clustering
from ml_engine.ghana_patha import validate_ghana_patha
from ml_engine.raga_mapping import detect_raga, RAGA_DATABASE


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic Audio Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_sine_tone(freq_hz, duration=5.0, sr=SR):
    """Pure sine with harmonics to simulate a simple vocal tone."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = (
        np.sin(2 * np.pi * freq_hz * t) * 0.50 +
        np.sin(2 * np.pi * freq_hz * 2 * t) * 0.30 +
        np.sin(2 * np.pi * freq_hz * 3 * t) * 0.15 +
        np.sin(2 * np.pi * freq_hz * 4 * t) * 0.05
    )
    return wave.astype(np.float32)


def generate_ascending_scale(sr=SR):
    """Generate an ascending scale: Sa Re2 Ga2 Ma1 Pa Dha2 Ni2 Sa' (12s)."""
    # Correct SHRUTI_NAMES indices: Pa=10, Dha2=12, Ni2=14, Sa'=19
    shruti_indices = [0, 2, 4, 6, 10, 12, 14, 19]  # Sa Re2 Ga2 Ma1 Pa Dha2 Ni2 Sa'
    note_dur = 1.5
    waves = []
    for idx in shruti_indices:
        freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]
        waves.append(generate_sine_tone(freq, note_dur, sr))
    return np.concatenate(waves).astype(np.float32)


def generate_descending_scale(sr=SR):
    """Generate a descending scale: Sa' Ni2 Dha2 Pa Ma1 Ga2 Re2 Sa (12s)."""
    shruti_indices = [19, 14, 12, 10, 6, 4, 2, 0]  # Sa'=19 Ni2=14 Dha2=12 Pa=10 Ma1 Ga2 Re2 Sa
    note_dur = 1.5
    waves = []
    for idx in shruti_indices:
        freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]
        waves.append(generate_sine_tone(freq, note_dur, sr))
    return np.concatenate(waves).astype(np.float32)


def generate_ghana_pattern(sr=SR):
    """
    Simulate Ghana Patha: forward-reverse-forward-reverse-forward (20s).
    Uses ascending/descending sine sequences with pitch glides.
    """
    cycle_parts = ['fwd', 'rev', 'fwd', 'rev', 'fwd']
    ascending = [0, 2, 4, 6, 10]     # Sa Re2 Ga2 Ma1 Pa (Pa=10)
    descending = [10, 6, 4, 2, 0]    # Pa Ma1 Ga2 Re2 Sa (Pa=10)

    all_waves = []
    for part in cycle_parts:
        seq = ascending if part == 'fwd' else descending
        for idx in seq:
            freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]
            all_waves.append(generate_sine_tone(freq, 0.4, sr))

    return np.concatenate(all_waves).astype(np.float32)


def generate_bilawal_scale(sr=SR):
    """
    Bilawal-like pattern (major scale): Sa Re2 Ga2 Ma1 Pa Dha2 Ni2 Sa'
    with repeated phrases — 15s.
    Pa=10, Dha2=12, Ni2=14, Sa'=19
    """
    notes = [0, 2, 4, 6, 10, 12, 14, 19]
    waves = []
    for _ in range(3):  # repeat 3 times
        for idx in notes:
            freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]
            waves.append(generate_sine_tone(freq, 0.5, sr))
    return np.concatenate(waves).astype(np.float32)


def generate_kalyani_scale(sr=SR):
    """
    Kalyani-like pattern (Carnatic Lydian): Sa Re2 Ga2 Ma2 Pa Dha2 Ni2 Sa'
    RAGA_DATABASE Kalyani swaras: [0,2,4,7,10,12,14] — Ma2=7, Pa=10, Dha2=12, Ni2=14, Sa'=19
    """
    notes = [0, 2, 4, 7, 10, 12, 14, 19]
    waves = []
    for _ in range(3):
        for idx in notes:
            freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]
            waves.append(generate_sine_tone(freq, 0.5, sr))
    return np.concatenate(waves).astype(np.float32)


def generate_bhairav_scale(sr=SR):
    """
    Bhairav-like: Sa Re1 Ga2 Ma1 Pa Dha1 Ni1 Sa'
    RAGA_DATABASE Bhairav swaras: [0,1,4,6,10,11,13] — Pa=10, Dha1=11, Ni1=13, Sa'=19
    """
    notes = [0, 1, 4, 6, 10, 11, 13, 19]
    waves = []
    for _ in range(3):
        for idx in notes:
            freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]
            waves.append(generate_sine_tone(freq, 0.5, sr))
    return np.concatenate(waves).astype(np.float32)


def generate_silence(duration=5.0, sr=SR):
    """Pure silence / noise floor."""
    return np.random.normal(0, 0.001, int(sr * duration)).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# Real-world robustness: Gamaka, Vibrato, Breath-gap generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_vibrato_note(freq_hz, duration=2.0, sr=SR,
                          vibrato_rate=6.5, vibrato_depth_cents=35.0):
    """
    Generate a single note with sinusoidal vibrato (5–8 Hz FM).

    Vedic chanting often has 5–8 Hz pitch oscillations.  This exercises the
    pYIN F0 extractor to ensure it tracks the mean pitch rather than locking
    onto the vibrato sidebands.

    Parameters
    ----------
    vibrato_rate   : float — oscillation frequency in Hz (5–8 Hz typical)
    vibrato_depth_cents : float — peak deviation in cents (±30–50 cents typical)
    """
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Convert cents deviation to frequency multiplier
    cents_mod = vibrato_depth_cents * np.sin(2 * np.pi * vibrato_rate * t)
    freq_mod = freq_hz * (2 ** (cents_mod / 1200.0))
    # Instantaneous phase from cumulative frequency
    phase = 2 * np.pi * np.cumsum(freq_mod) / sr
    wave = (
        np.sin(phase) * 0.50 +
        np.sin(2 * phase) * 0.30 +
        np.sin(3 * phase) * 0.15 +
        np.sin(4 * phase) * 0.05
    )
    return wave.astype(np.float32)


def generate_vibrato_scale(sr=SR):
    """
    Bilawal-like scale where every note is delivered with 6.5 Hz vibrato.
    Tests that pYIN still assigns the correct Shruti despite continuous FM.
    """
    notes = [0, 2, 4, 6, 10, 12, 14, 19]  # Sa Re2 Ga2 Ma1 Pa Dha2 Ni2 Sa'  (Pa=10)
    waves = []
    for idx in notes:
        freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]
        waves.append(generate_vibrato_note(freq, duration=1.5, sr=sr))
    return np.concatenate(waves).astype(np.float32)


def generate_gamaka_slide(freq_start, freq_end, duration=0.3, sr=SR):
    """
    Generate a continuous pitch glide (Gamaka / meend) between two Shruti frequencies.

    The slide is a smooth exponential frequency interpolation, mimicking the
    continuous microtonal transitions common in Vedic and Carnatic singing.
    """
    n = int(sr * duration)
    t = np.linspace(0, 1, n, endpoint=False)
    # Exponential glide: linear in log-frequency (musical pitch space)
    freq_glide = freq_start * ((freq_end / freq_start) ** t)
    phase = 2 * np.pi * np.cumsum(freq_glide) / sr
    wave = (
        np.sin(phase) * 0.50 +
        np.sin(2 * phase) * 0.30 +
        np.sin(3 * phase) * 0.15 +
        np.sin(4 * phase) * 0.05
    )
    return wave.astype(np.float32)


def generate_gamaka_scale(sr=SR):
    """
    Ascending scale with Gamaka (meend) slides between every note pair.

    Each note is held for 0.8 s then glides into the next over 0.3 s,
    producing continuous pitch trajectories instead of discrete steps.
    Exercises the segmentation logic and pYIN’s ability to track glides.
    """
    note_indices = [0, 2, 4, 6, 10, 12, 14, 19]  # Sa Re2 Ga2 Ma1 Pa Dha2 Ni2 Sa'  (Pa=10)
    hold_dur = 0.8
    slide_dur = 0.3
    waves = []
    freqs = [SHRUTI_FREQUENCIES[SHRUTI_NAMES[i]] for i in note_indices]
    for k, freq in enumerate(freqs):
        waves.append(generate_sine_tone(freq, hold_dur, sr))
        if k < len(freqs) - 1:
            waves.append(generate_gamaka_slide(freq, freqs[k + 1], slide_dur, sr))
    return np.concatenate(waves).astype(np.float32)


def generate_breath_gap_scale(sr=SR,
                              note_dur=1.2,
                              breath_dur=0.25,
                              noise_level=0.001):
    """
    Scale with short breath-gap silences between each note.

    Real vocal recordings have micro-silences (0.1–0.4 s) between phrases
    where the singer breathes.  These unvoiced frames should be correctly
    marked by pYIN as NaN and not misidentified as spurious Shrutis.
    """
    # Ascending then descending: Pa=10, Dha2=12, Ni2=14, Sa'=19
    note_indices = [0, 2, 4, 6, 10, 12, 14, 19, 14, 12, 10, 6, 4, 2, 0]
    waves = []
    for idx in note_indices:
        freq = SHRUTI_FREQUENCIES[SHRUTI_NAMES[idx]]
        waves.append(generate_sine_tone(freq, note_dur, sr))
        # Breath gap: near-silence with low Gaussian noise
        gap = np.random.normal(0, noise_level, int(sr * breath_dur)).astype(np.float32)
        waves.append(gap)
    return np.concatenate(waves).astype(np.float32)


def generate_all_synthetic():
    """Generate all synthetic test files."""
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)

    tests = [
        ("sa_pure_261hz", generate_sine_tone(261.63, 5.0), "Sa (261.63 Hz) — pitch ground truth"),
        ("pa_pure_392hz", generate_sine_tone(392.44, 5.0), "Pa (392.44 Hz) — pitch ground truth"),
        ("dha1_pure_413hz", generate_sine_tone(413.43, 5.0), "Dha1 (413.43 Hz) — test Dha1 detection"),
        ("high_ni_697hz", generate_sine_tone(697.66, 5.0), "Dha_ (697.66 Hz) — high Shruti"),
        ("ascending_scale", generate_ascending_scale(), "8-note ascending scale — Sa→Sa'"),
        ("descending_scale", generate_descending_scale(), "8-note descending scale — Sa'→Sa"),
        ("ghana_pattern_sim", generate_ghana_pattern(), "Ghana Patha simulation (20s)"),
        ("bilawal_scale", generate_bilawal_scale(), "Bilawal-like major scale ×3"),
        ("kalyani_scale", generate_kalyani_scale(), "Kalyani-like Lydian scale ×3"),
        ("bhairav_scale", generate_bhairav_scale(), "Bhairav-like scale ×3"),
        ("silence_5s", generate_silence(5.0), "Near-silence baseline"),
        # ── Real-world robustness tests (Gamaka, Vibrato, Breath-gap) ────────────
        ("vibrato_scale",    generate_vibrato_scale(),
         "Bilawal scale with 6.5 Hz vibrato — tests pYIN under FM"),
        ("gamaka_scale",     generate_gamaka_scale(),
         "Ascending scale with meend (pitch glide) ornaments — tests segmentation"),
        ("breath_gap_scale", generate_breath_gap_scale(),
         "Scale with 250 ms breath-gap silences — tests unvoiced frame handling"),
    ]

    files = []
    for name, audio, description in tests:
        path = SYNTH_DIR / f"{name}.wav"
        sf.write(str(path), audio, SR)
        files.append({"name": name, "path": str(path), "description": description, "synthetic": True})
        print(f"  Generated: {path.name} ({len(audio)/SR:.1f}s)")

    return files


# ─────────────────────────────────────────────────────────────────────────────
# ML Pipeline Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(audio_path, audio_name):
    """Run the full 4-stage ML pipeline and return structured results."""
    result = {
        "name": audio_name,
        "path": str(audio_path),
        "stages": {},
        "errors": [],
    }

    # ── Stage 1: Feature Extraction ──
    t0 = time.time()
    try:
        features = extract_features(str(audio_path))
        t1 = time.time()
        result["stages"]["feature_extraction"] = {
            "duration_s": round(t1 - t0, 3),
            "success": True,
            "audio_duration_s": round(features["duration"], 3),
            "sample_rate": features["sr"],
            "total_frames": int(features["pcp"].shape[1]),
            "voiced_ratio": round(features["voiced_ratio"], 4),
            "tempo_bpm": round(features["tempo"], 2),
            "mean_pcp": [round(float(x), 6) for x in features["mean_pcp"]],
            "f0_track_length": len(features["f0_track"]),
            "f0_voiced_count": int(features["voiced_flag"].sum()) if features["voiced_flag"] is not None else 0,
            "mfcc_shape": list(features["mfcc"].shape),
            "pcp_shape": list(features["pcp"].shape),
        }
    except Exception as e:
        result["stages"]["feature_extraction"] = {"success": False, "error": str(e)}
        result["errors"].append(f"Stage 1 failed: {e}")
        traceback.print_exc()
        return result

    # ── Stage 2: K-Means Clustering ──
    t0 = time.time()
    try:
        clustering = run_clustering(features)
        t1 = time.time()

        # Analyze cluster assignments
        freq_assignments = clustering["freq_assignments"]
        from collections import Counter
        assignment_counts = Counter(freq_assignments)

        # Shruti distribution
        shruti_dist = {}
        for name, count in sorted(assignment_counts.items(), key=lambda x: -x[1]):
            shruti_dist[name] = count

        result["stages"]["clustering"] = {
            "duration_s": round(t1 - t0, 3),
            "success": True,
            "n_clusters": 22,
            "total_frames": len(freq_assignments),
            "unique_shrutis_assigned": len(assignment_counts),
            "top_5_shrutis": dict(list(shruti_dist.items())[:5]),
            "mean_pcp_top_5": sorted(
                [(SHRUTI_NAMES[i], round(float(v), 6)) for i, v in enumerate(clustering["mean_pcp"])],
                key=lambda x: -x[1]
            )[:5],
        }
    except Exception as e:
        result["stages"]["clustering"] = {"success": False, "error": str(e)}
        result["errors"].append(f"Stage 2 failed: {e}")
        traceback.print_exc()
        return result

    # ── Stage 3: Ghana Patha Validation ──
    t0 = time.time()
    try:
        ghana = validate_ghana_patha(features)
        t1 = time.time()

        result["stages"]["ghana_patha"] = {
            "duration_s": round(t1 - t0, 3),
            "success": True,
            "is_valid": ghana["is_valid"],
            "confidence": ghana["confidence"],
            "repetition_score": ghana["repetition_score"],
            "n_segments": ghana.get("n_segments", 0),
            "detected_pattern": ghana.get("detected_pattern", []),
            "expected_pattern": ghana.get("expected_pattern", []),
            "dtw_details": ghana.get("dtw_details"),
        }
    except Exception as e:
        result["stages"]["ghana_patha"] = {"success": False, "error": str(e)}
        result["errors"].append(f"Stage 3 failed: {e}")
        traceback.print_exc()

    # ── Stage 4: Raga Detection ──
    t0 = time.time()
    try:
        raga = detect_raga(clustering, features=features)
        t1 = time.time()

        result["stages"]["raga_detection"] = {
            "duration_s": round(t1 - t0, 3),
            "success": True,
            "is_inconclusive": raga["is_inconclusive"],
            "confidence_threshold": raga["confidence_threshold"],
            "total_frames_analyzed": raga["total_frames_analyzed"],
            "detection_source": raga["detection_source"],
            "directional_scoring": raga.get("directional_scoring", False),
            "n_detected_swaras": len(raga["detected_swaras"]),
            "detected_swaras": [
                {"swara": s["swara"], "index": s["index"], "weight": s["weight"]}
                for s in raga["detected_swaras"][:10]
            ],
            "best_match": (
                {
                    "raga_name": raga["best_match"]["raga_name"],
                    "tradition": raga["best_match"]["tradition"],
                    "confidence": raga["best_match"]["confidence"],
                    "vadi": raga["best_match"]["vadi"],
                    "samvadi": raga["best_match"]["samvadi"],
                    "time": raga["best_match"]["time"],
                    "mood": raga["best_match"]["mood"],
                }
                if raga["best_match"]
                else None
            ),
            "top_3_matches": [
                {
                    "raga_name": m["raga_name"],
                    "tradition": m["tradition"],
                    "confidence": m["confidence"],
                }
                for m in raga.get("matches", [])[:3]
            ],
            "inconclusive_reason": raga.get("inconclusive_reason"),
        }
    except Exception as e:
        result["stages"]["raga_detection"] = {"success": False, "error": str(e)}
        result["errors"].append(f"Stage 4 failed: {e}")
        traceback.print_exc()

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("VEDIC ACOUSTICA — ML PIPELINE TEST SUITE")
    print("=" * 70)

    # ── Step 1: Generate synthetic audio ──
    print("\n[1/4] Generating synthetic test audio...")
    synth_files = generate_all_synthetic()

    # ── Step 2: Collect real test audio ──
    print("\n[2/4] Collecting real test audio...")
    real_files = []
    for p in sorted(TEST_AUDIO_DIR.glob("*.wav")):
        if "synthetic" in str(p):
            continue
        real_files.append({"name": p.stem, "path": str(p), "description": f"Real audio: {p.name}", "synthetic": False})
        print(f"  Found: {p.name}")
    for p in sorted(TEST_AUDIO_DIR.glob("*.mp3")):
        real_files.append({"name": p.stem, "path": str(p), "description": f"Real audio: {p.name}", "synthetic": False})
        print(f"  Found: {p.name}")
    for p in sorted(TEST_AUDIO_DIR.glob("*.ogg")):
        real_files.append({"name": p.stem, "path": str(p), "description": f"Real audio: {p.name}", "synthetic": False})
        print(f"  Found: {p.name}")

    all_files = synth_files + real_files
    print(f"\n  Total files to analyze: {len(all_files)}")

    # ── Step 3: Run ML pipeline ──
    print("\n[3/4] Running ML pipeline on all files...")
    all_results = []
    for i, f in enumerate(all_files, 1):
        print(f"\n  [{i}/{len(all_files)}] {f['name']} ({f['description']})")
        try:
            result = run_pipeline(f["path"], f["name"])
            result["description"] = f["description"]
            result["synthetic"] = f["synthetic"]
            all_results.append(result)
            status = "OK" if not result["errors"] else f"ERRORS: {len(result['errors'])}"
            print(f"    → {status}")
        except Exception as e:
            print(f"    → FATAL: {e}")
            traceback.print_exc()
            all_results.append({
                "name": f["name"],
                "description": f["description"],
                "synthetic": f["synthetic"],
                "stages": {},
                "errors": [str(e)],
            })

    # ── Step 4: Save results ──
    print("\n[4/4] Saving results...")
    results_path = OUTPUT_DIR / "pipeline_results.json"
    with open(results_path, "w") as fh:
        json.dump(all_results, fh, indent=2, default=str)
    print(f"  Results saved to: {results_path}")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for r in all_results:
        errors = len(r["errors"])
        stages_ok = sum(1 for s in r["stages"].values() if s.get("success", False))
        status = f"{stages_ok}/4 stages OK" if errors == 0 else f"{errors} error(s)"
        print(f"  {r['name']:30s} → {status}")

    print(f"\nFull results: {results_path}")
    return all_results


if __name__ == "__main__":
    main()
