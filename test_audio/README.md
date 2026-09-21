# Field-Recording Checklist

How to make a Vedic/Ghana recitation recording that the Vedic Acoustica ML
pipeline can actually trust. The synthetic gates in `test_ml_robustness.py` and
the curated clips ingested via `manage.py ingest_corpus` define the envelope
this checklist keeps recordings inside.

## Signal chain

- [ ] Record WAV at **≥ 44.1 kHz / 24-bit** (mono). The pipeline decimates to
      22.05 kHz internally; record high, never upsample.
- [ ] Fixed **cardioid condenser mic ~15–20 cm** from the reciter, pop filter
      between, one speaker per session (Vāgdhenu protocol).
- [ ] Noise floor **≤ −60 dBFS**, peaks around **−6 dBFS** — stay off
      clipping and off compressor/limiter (they flatten the PCP envelope the
      pYIN F0 track depends on).
- [ ] **No music, drone, or tanpura mixed into the recording.** The pipeline
      analyses in isolation; a drone Sa low in the take becomes a harmonic the
      spectral-flatness and PCP folds must ignore.
- [ ] No room reverb/echo: close-mic in a quiet, soft room. High reverb
      flattens the spectrum and drags spectral flatness toward the noise
      rejection threshold (`NOISE_FLATNESS_THRESHOLD = 0.35`).

## Recitation delivery

- [ ] Natural pārāyaṇa pace, **steady register** (no octave jumps mid-take).
- [ ] Hold each word to its metrical duration; **pause only at a daṇḍa (।/॥)**
      and never mid-pāda.
- [ ] If capturing a Ghana-style sequence, use the **canonical cycle**
      (`forward, reverse, forward, reverse, forward`) — the DTW validator
      accepts the cycle and its phase rotation; random walks and monotone runs
      are rejected/characterised as corrupt in the robustness report.
- [ ] Keep takes **≤ 60 s** (pipeline and queue are tuned for ≤ 60 s clips;
      longer takes hit the greedy segmentation budget).

## Before accepting a take

- [ ] Visual check: RMS in the 0.01–0.7 window (near-silence is rejected by the
      RMS guard; hot clipping over ~0.7 distorts the PCP).
- [ ] Voice check: `voiced_ratio` ≥ 0.7 in the analysis metadata; well below
      that is noise/music bleed.
- [ ] Ghana check: `ghana_patha_valid = true` and `ghana_patha_confidence`
      ≥ 0.6 for a genuine recitation (see `test_ml_robustness.py` — pure noise
      is now rejected by the spectral-flatness guard).

## Provenance before uploading

- [ ] File name: `<source>_<text_id>_<take>.wav` (e.g. `vedavani-rigveda_47_0259.wav`).
- [ ] Record who recites, where, licence (allowlist: **CC-BY-4.0 / Apache-2.0**),
      home URL and the text — put it in `test_audio/manifest.json` and ingest
      with `python backend/manage.py ingest_corpus --dry-run` first.

Then: `python backend/manage.py ingest_corpus` (add `--analyze` on a shared-DB
deployment) and the clip lands in `/api/recordings/` with provenance in
`corpus_metadata`.