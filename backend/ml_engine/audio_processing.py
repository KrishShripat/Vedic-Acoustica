import librosa
import numpy as np
from .shruti_mapping import SHRUTI_FREQUENCIES, SHRUTI_NAMES

SR = 22050
HOP_LENGTH = 512
N_MFCC = 13
N_CHROMA = 22

# ── PCP constants ────────────────────────────────────────────────────────────
_N_HARMONICS = 5          # harmonics to accumulate (h = 1..5)
_HARMONIC_WEIGHTS = np.array(  # weight decays with harmonic number
    [1.0 / h for h in range(1, _N_HARMONICS + 1)], dtype=np.float32
)
# log-frequency half-width that counts as "hitting" a Shruti bin (in cents)
_THRESHOLD_CENTS = 25.0   # ±25 cents  ≈ half a quarter-tone

# F0 confidence boost multiplier: voiced F0 is far more reliable than STFT
# harmonics, so we amplify its PCP contribution by this factor.
_F0_BOOST = 8.0

_SHRUTI_FREQS_ARR = np.array(
    [SHRUTI_FREQUENCIES[n] for n in SHRUTI_NAMES], dtype=np.float64
)


# ─────────────────────────────────────────────────────────────────────────────
# F0 extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_f0(y, sr=SR, hop_length=HOP_LENGTH):
    """
    Extract a monophonic F0 pitch track using the pYIN algorithm.

    pYIN is a probabilistic refinement of YIN that produces per-frame voiced /
    unvoiced decisions alongside the fundamental frequency estimate.  For
    single-voice Vedic chanting it is substantially more reliable than STFT
    peak-picking or chroma-based approaches.

    Parameters
    ----------
    y : ndarray
        Audio time-series (mono, float32/64).
    sr : int
        Sample rate (default SR = 22 050 Hz).
    hop_length : int
        Hop size shared with all other feature extractors so frame counts align.

    Returns
    -------
    f0 : ndarray, shape (n_frames,)
        Fundamental frequency in Hz per frame. Unvoiced frames carry NaN.
    voiced_flag : ndarray of bool, shape (n_frames,)
        True for frames where pYIN is confident a pitch is present.
    voiced_probs : ndarray, shape (n_frames,)
        Per-frame probability [0, 1] of being voiced.
    """
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=librosa.note_to_hz('C2'),   # ~65 Hz  — below lowest Vedic pitch
        fmax=librosa.note_to_hz('C7'),   # ~2093 Hz — above highest expected
        sr=sr,
        hop_length=hop_length,
        fill_na=np.nan,
    )
    return f0, voiced_flag, voiced_probs


# ─────────────────────────────────────────────────────────────────────────────
# PCP computation (harmonic STFT + pYIN F0 fusion)
# ─────────────────────────────────────────────────────────────────────────────

def compute_pcp(y, sr=SR, hop_length=HOP_LENGTH, n_fft=4096,
                f0=None, voiced_flag=None):
    """
    Compute a Pitch-Class Profile (PCP) over the 22 Shruti bins.

    When ``f0`` and ``voiced_flag`` are provided (from :func:`extract_f0`),
    voiced frames receive a high-confidence F0 boost directly onto the nearest
    Shruti bin in addition to the regular harmonic accumulation.  This fusion
    strategy greatly sharpens the PCP for monophonic signals.

    Returns
    -------
    pcp : ndarray, shape (22, n_frames), dtype float32
        Per-frame energy at each Shruti, normalized so each frame sums to 1
        (frames with zero energy are left as zero vectors).
    freqs : ndarray, shape (n_fft // 2 + 1,)
        FFT frequency axis (Hz), useful for debugging.
    """
    # ── STFT ─────────────────────────────────────────────────────────────────
    stft = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, window='hann')
    magnitude = np.abs(stft).astype(np.float32)      # (n_bins, n_frames)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)  # (n_bins,)

    n_shruti = len(_SHRUTI_FREQS_ARR)
    n_bins, n_frames = magnitude.shape
    pcp = np.zeros((n_shruti, n_frames), dtype=np.float32)

    # Only consider bins above a minimum useful frequency
    valid_mask = freqs > 20.0
    mag_valid = magnitude[valid_mask]          # (n_valid_bins, n_frames)
    f_valid = freqs[valid_mask]                # (n_valid_bins,)

    # ── Vectorized harmonic accumulation ─────────────────────────────────────
    # For each harmonic h we check whether f_valid / h is within threshold of
    # any Shruti frequency, and accumulate weighted magnitude.
    for h_idx, h in enumerate(range(1, _N_HARMONICS + 1)):
        f_fundamental = f_valid / h            # (n_valid_bins,)

        with np.errstate(divide='ignore', invalid='ignore'):
            cents_diff = np.abs(
                1200.0 * np.log2(
                    f_fundamental[:, None] / _SHRUTI_FREQS_ARR[None, :]
                )
            )  # (n_valid_bins, n_shruti)

        best_shruti = np.argmin(cents_diff, axis=1)  # (n_valid_bins,)
        within = cents_diff < _THRESHOLD_CENTS
        hit_mask = within[np.arange(len(f_valid)), best_shruti]

        weight = _HARMONIC_WEIGHTS[h_idx]
        np.add.at(
            pcp,
            best_shruti[hit_mask],
            weight * mag_valid[hit_mask, :],
        )

    # ── pYIN F0 fusion (voiced frames only) ──────────────────────────────────
    # For each voiced frame we know the fundamental exactly; bypass harmonic
    # ambiguity by directly adding a large boost to the nearest Shruti bin.
    if f0 is not None and voiced_flag is not None:
        # Align frame counts: pyin may differ by ±1 frame from the STFT
        n_f0 = len(f0)
        align_frames = min(n_f0, n_frames)

        f0_aligned = f0[:align_frames]
        voiced_aligned = voiced_flag[:align_frames]

        voiced_indices = np.where(voiced_aligned)[0]

        if len(voiced_indices) > 0:
            f0_voiced = f0_aligned[voiced_indices]    # (n_voiced,)

            # cents distance from each voiced F0 to each of the 22 Shrutis
            with np.errstate(divide='ignore', invalid='ignore'):
                cents_f0 = np.abs(
                    1200.0 * np.log2(
                        f0_voiced[:, None] / _SHRUTI_FREQS_ARR[None, :]
                    )
                )  # (n_voiced, n_shruti)

            best_shruti_f0 = np.argmin(cents_f0, axis=1)  # (n_voiced,)
            within_f0 = cents_f0[np.arange(len(f0_voiced)), best_shruti_f0] \
                        < _THRESHOLD_CENTS                 # (n_voiced,)

            # Average magnitude at voiced frames as a reference amplitude
            voiced_mag = magnitude[:, voiced_indices].mean(axis=0)  # (n_voiced,)

            # Accumulate boost for each voiced frame individually
            for i, frame_idx in enumerate(voiced_indices):
                if within_f0[i]:
                    pcp[best_shruti_f0[i], frame_idx] += (
                        _F0_BOOST * float(voiced_mag[i])
                    )

    # ── Per-frame normalisation (0-1 range) ──────────────────────────────────
    frame_sums = pcp.sum(axis=0, keepdims=True)       # (1, n_frames)
    nonzero = frame_sums > 0
    pcp = np.where(nonzero, pcp / np.where(nonzero, frame_sums, 1), 0.0)

    return pcp.astype(np.float32), freqs


# ─────────────────────────────────────────────────────────────────────────────
# Top-level feature extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_features(audio_path):
    y, sr = librosa.load(audio_path, sr=SR)
    duration = librosa.get_duration(y=y, sr=sr)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, hop_length=HOP_LENGTH)

    chroma = librosa.feature.chroma_stft(
        y=y, sr=sr, n_fft=2048, hop_length=HOP_LENGTH, n_chroma=N_CHROMA,
    )

    spectral_centroid = librosa.feature.spectral_centroid(
        y=y, sr=sr, hop_length=HOP_LENGTH,
    )[0]

    spectrogram = np.abs(librosa.stft(y, hop_length=HOP_LENGTH))
    spectrogram_db = librosa.amplitude_to_db(spectrogram, ref=np.max)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if hasattr(tempo, '__len__'):
        tempo = float(tempo[0]) if len(tempo) > 0 else 0.0
    else:
        tempo = float(tempo)

    # ── F0 via pYIN ──────────────────────────────────────────────────────────
    f0, voiced_flag, voiced_probs = extract_f0(y, sr=SR, hop_length=HOP_LENGTH)

    voiced_ratio = float(voiced_flag.mean()) if len(voiced_flag) > 0 else 0.0

    # ── PCP with F0 fusion ───────────────────────────────────────────────────
    # Pass f0 and voiced_flag so the PCP is reinforced at voiced frames.
    pcp, _ = compute_pcp(
        y, sr=SR, hop_length=HOP_LENGTH,
        f0=f0, voiced_flag=voiced_flag,
    )
    mean_pcp = pcp.mean(axis=1)    # (22,) — recording-level tonal fingerprint

    # Serialise F0 track: NaN → None for clean JSON
    f0_track = [
        None if np.isnan(v) else round(float(v), 3)
        for v in f0
    ]

    return {
        'mfcc': mfcc,
        'chroma': chroma,
        'spectral_centroid': spectral_centroid,
        'spectrogram': spectrogram_db,
        # ── PCP ──────────────────────────────────────────────────────────────
        'pcp': pcp,                # (22, n_frames)  per-frame Shruti energies
        'mean_pcp': mean_pcp,      # (22,)           recording-level fingerprint
        # ── F0 / pYIN ────────────────────────────────────────────────────────
        'f0': f0,                  # ndarray (n_frames,) — raw, NaN for unvoiced
        'f0_track': f0_track,      # list[float|None]   — JSON-ready
        'voiced_flag': voiced_flag,# ndarray bool (n_frames,)
        'voiced_probs': voiced_probs,
        'voiced_ratio': voiced_ratio,
        # ── Other ─────────────────────────────────────────────────────────────
        'tempo': tempo,
        'duration': duration,
        'sr': sr,
        'y': y,
    }
