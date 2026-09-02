#!/usr/bin/env python3
"""
Vedic Acoustica — ML Pipeline Quick Test (synthetic + small files)
Runs fast on 5s synthetic clips; skips large real audio for targeted runs.
"""
import sys, os, json, time, traceback
from pathlib import Path
from collections import Counter

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vedic_acoustica.settings")

import numpy as np
import soundfile as sf
import librosa

# Quick-test cap: skip real audio files longer than this many seconds.
# Synthetic clips are always short, so only real files are affected.
MAX_QUICK_DURATION = 60.0

from ml_engine.shruti_mapping import REFERENCE_FREQ, SHRUTI_FREQUENCIES, SHRUTI_NAMES
from ml_engine.audio_processing import extract_features, SR
from ml_engine.ml_engine import run_clustering
from ml_engine.ghana_patha import validate_ghana_patha
from ml_engine.raga_mapping import detect_raga

SYNTH_DIR = BACKEND_DIR.parent / "test_audio" / "synthetic"
OUTPUT_DIR = BACKEND_DIR.parent / "test_reports"

def tone(freq, dur=5.0):
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    w = (0.5*np.sin(2*np.pi*freq*t) + 0.3*np.sin(2*np.pi*2*freq*t) +
         0.15*np.sin(2*np.pi*3*freq*t) + 0.05*np.sin(2*np.pi*4*freq*t))
    return w.astype(np.float32)

def scale(indices, note_dur=0.5):
    return np.concatenate([tone(SHRUTI_FREQUENCIES[SHRUTI_NAMES[i]], note_dur) for i in indices])

def make_synthetic():
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    tests = [
        ("sa_261", tone(261.63, 5.0), "Sa pure tone 261.63 Hz"),
        ("pa_392", tone(392.44, 5.0), "Pa pure tone 392.44 Hz"),
        ("ni2_436", tone(436.05, 5.0), "Ni2 pure tone 436.05 Hz"),
        ("dha__697", tone(697.66, 5.0), "Dha_ high shruti 697.66 Hz"),
        ("ascending", scale([0,2,4,6,9,11,13,15], 0.5), "Ascending Sa->Sa' 8 notes"),
        ("descending", scale([15,13,11,9,6,4,2,0], 0.5), "Descending Sa'->Sa 8 notes"),
        ("bilawal_3x", scale([0,2,4,6,9,11,13,15]*3, 0.4), "Bilawal major scale x3"),
        ("kalyani_3x", scale([0,2,4,7,9,11,13,15]*3, 0.4), "Kalyani Lydian scale x3"),
        ("bhairav_3x", scale([0,1,4,6,9,10,12,15]*3, 0.4), "Bhairav scale x3"),
        ("malkauns_3x", scale([0,3,6,8,10]*3, 0.4), "Malkauns pentatonic x3"),
    ]
    files = []
    for name, audio, desc in tests:
        p = SYNTH_DIR / f"{name}.wav"
        sf.write(str(p), audio, SR)
        files.append({"name": name, "path": str(p), "desc": desc, "synth": True})
    return files

def analyze_one(path, name):
    t_start = time.time()
    r = {"name": name, "path": str(path), "stages": {}, "errors": []}

    # Stage 1
    t0 = time.time()
    try:
        feat = extract_features(str(path))
        r["stages"]["feature_extraction"] = {
            "time_s": round(time.time()-t0, 3), "ok": True,
            "duration": round(feat["duration"],3), "sr": feat["sr"],
            "frames": int(feat["pcp"].shape[1]),
            "voiced_ratio": round(feat["voiced_ratio"],4),
            "tempo": round(feat["tempo"],2),
            "f0_voiced": int(feat["voiced_flag"].sum()) if feat["voiced_flag"] is not None else 0,
            "mean_pcp_top5": sorted(
                [(SHRUTI_NAMES[i], round(float(v),6)) for i,v in enumerate(feat["mean_pcp"])],
                key=lambda x: -x[1])[:5],
        }
    except Exception as e:
        r["stages"]["feature_extraction"] = {"ok": False, "error": str(e)}
        r["errors"].append(str(e))
        return r

    # Stage 2
    t0 = time.time()
    try:
        cl = run_clustering(feat)
        freq_a = cl["freq_assignments"]
        counts = Counter(freq_a)
        r["stages"]["clustering"] = {
            "time_s": round(time.time()-t0, 3), "ok": True,
            "frames": len(freq_a), "unique_shrutis": len(counts),
            "top5": dict(counts.most_common(5)),
        }
    except Exception as e:
        r["stages"]["clustering"] = {"ok": False, "error": str(e)}
        r["errors"].append(str(e))
        return r

    # Stage 3
    t0 = time.time()
    try:
        gh = validate_ghana_patha(feat)
        r["stages"]["ghana_patha"] = {
            "time_s": round(time.time()-t0, 3), "ok": True,
            "valid": gh["is_valid"], "confidence": gh["confidence"],
            "repetition": gh["repetition_score"], "n_segments": gh.get("n_segments",0),
            "dtw": gh.get("dtw_details"),
        }
    except Exception as e:
        r["stages"]["ghana_patha"] = {"ok": False, "error": str(e)}
        r["errors"].append(str(e))

    # Stage 4
    t0 = time.time()
    try:
        ra = detect_raga(cl, features=feat)
        r["stages"]["raga_detection"] = {
            "time_s": round(time.time()-t0, 3), "ok": True,
            "inconclusive": ra["is_inconclusive"],
            "threshold": ra["confidence_threshold"],
            "frames": ra["total_frames_analyzed"],
            "source": ra["detection_source"],
            "directional": ra.get("directional_scoring", False),
            "n_swaras": len(ra["detected_swaras"]),
            "swaras": [s["swara"] for s in ra["detected_swaras"][:10]],
            "best": {"name": ra["best_match"]["raga_name"],
                     "conf": ra["best_match"]["confidence"],
                     "tradition": ra["best_match"]["tradition"]}
                     if ra["best_match"] else None,
            "top3": [{"name":m["raga_name"],"conf":m["confidence"],"trad":m["tradition"]}
                     for m in ra.get("matches",[])[:3]],
            "inconcl_reason": ra.get("inconclusive_reason"),
        }
    except Exception as e:
        r["stages"]["raga_detection"] = {"ok": False, "error": str(e)}
        r["errors"].append(str(e))

    r["total_time_s"] = round(time.time()-t_start, 3)
    return r

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== VEDIC ACOUSTICA ML TEST ===")
    print("Generating synthetic audio...")
    synth = make_synthetic()

    # Also find small real files (< 15MB) that are short enough to be quick
    real = []
    for ext in ("*.wav","*.mp3","*.ogg"):
        for p in sorted((BACKEND_DIR.parent/"test_audio").glob(ext)):
            if "synthetic" in str(p): continue
            if p.stat().st_size >= 15_000_000:
                continue
            try:
                dur = librosa.get_duration(path=str(p))
            except Exception:
                dur = 0.0
            if dur > MAX_QUICK_DURATION:
                print(f"  [SKIP] {p.name} ({dur:.0f}s > {MAX_QUICK_DURATION:.0f}s cap)")
                continue
            real.append({"name":p.stem, "path":str(p), "desc":f"Real: {p.name}", "synth":False})

    all_files = synth + real
    print(f"Files to test: {len(all_files)}")

    results = []
    for i, f in enumerate(all_files, 1):
        print(f"\n[{i}/{len(all_files)}] {f['name']} — {f['desc']}")
        r = analyze_one(f["path"], f["name"])
        r["desc"] = f["desc"]
        r["synth"] = f["synth"]
        results.append(r)
        ok = sum(1 for s in r["stages"].values() if s.get("ok",False))
        print(f"  {ok}/4 stages OK | {r.get('total_time_s','?')}s | errors={len(r['errors'])}")

    # Save
    out = OUTPUT_DIR / "pipeline_results.json"
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2, default=str)

    print(f"\n{'='*50}")
    print("RESULTS SUMMARY")
    print(f"{'='*50}")
    for r in results:
        ok = sum(1 for s in r["stages"].values() if s.get("ok",False))
        gp = r["stages"].get("ghana_patha",{})
        rd = r["stages"].get("raga_detection",{})
        gp_str = f"GP={gp.get('confidence','?')}" if gp.get("ok") else "GP=ERR"
        rd_str = f"Raga={rd['best']['name'] if rd.get('best') else 'Inconclusive'}" if rd.get("ok") else "Raga=ERR"
        print(f"  {r['name']:25s} | {ok}/4 | {gp_str:15s} | {rd_str}")

    print(f"\nJSON: {out}")

if __name__ == "__main__":
    main()
