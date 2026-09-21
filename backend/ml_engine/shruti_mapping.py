REFERENCE_FREQ = 261.626

SHRUTI_FREQUENCIES = {}

# The 22 Vedic Shruti frequencies (plus the octave Sa') arranged in strictly
# ascending pitch order.  Bins 1..22 are the 22-shruti division of the octave
# as given by the Jyotirvidābharaṇam ratio list; 0 is Sa and 22 is the octave
# Sa'.  Kept ascending so that bin index == ascending pitch, and so that each
# swara grade (Re/Ga/Ma/Dha/Ni, komal or shuddha/tivra) owns a contiguous zone
# of natural-just or Pythagorean bins.
#
# Cents are computed from 1200 * log2(ratio).
SHRUTI_RATIOS = [
    1.0,          # S1  Sa           — 261.63 Hz  (1/1)        0.0 ¢
    256 / 243,    # S2  Re1  komal   — 275.65 Hz  (256/243)    90.2 ¢
    16 / 15,      # S3  Re2  komal   — 279.07 Hz  (16/15)      111.7 ¢
    10 / 9,       # S4  Re3  shuddha — 290.70 Hz  (10/9)       182.4 ¢
    9 / 8,        # S5  Re4  shuddha — 294.33 Hz  (9/8)        203.9 ¢
    32 / 27,      # S6  Ga1  komal   — 310.07 Hz  (32/27)      294.1 ¢
    6 / 5,        # S7  Ga2  komal   — 313.95 Hz  (6/5)        315.6 ¢
    5 / 4,        # S8  Ga3  shuddha — 327.03 Hz  (5/4)        386.3 ¢
    81 / 64,      # S9  Ga4  shuddha — 331.14 Hz  (81/64)      407.8 ¢
    4 / 3,        # S10 Ma1  shuddha — 348.84 Hz  (4/3)        498.0 ¢
    27 / 20,      # S11 Ma2  tivra   — 353.20 Hz  (27/20 1.35) 519.6 ¢   — thick (large) tivra Ma
    45 / 32,      # S12 Ma3  tivra   — 367.91 Hz  (45/32)      590.2 ¢   — tritone, ~12-TET Ma♯
    729 / 512,    # S13 Ma4  tivra   — 372.51 Hz  (729/512)    611.7 ¢   — Pythagorean tritone
    3 / 2,        # S14 Pa           — 392.44 Hz  (3/2)        702.0 ¢
    128 / 81,     # S15 Dha1 komal   — 413.43 Hz  (128/81)     792.2 ¢
    8 / 5,        # S16 Dha2 komal   — 418.60 Hz  (8/5)        813.7 ¢
    5 / 3,        # S17 Dha3 shuddha — 436.04 Hz  (5/3)        884.4 ¢
    27 / 16,      # S18 Dha4 shuddha — 441.49 Hz  (27/16)      905.9 ¢
    16 / 9,       # S19 Ni1 komal    — 465.11 Hz  (16/9)       996.1 ¢
    9 / 5,        # S20 Ni2 komal    — 470.93 Hz  (9/5)        1017.6 ¢
    15 / 8,       # S21 Ni3 shuddha  — 490.55 Hz  (15/8)       1088.3 ¢
    243 / 128,    # S22 Ni4 shuddha  — 496.68 Hz  (243/128)    1109.8 ¢   — ~12-TET major 7th
    2 / 1,        # S23 Sa’ octave   — 523.25 Hz  (2/1)        1200.0 ¢
]

SHRUTI_NAMES = [
    'Shruti 1 (Sa)',
    'Shruti 2 (Re1, komal)',
    'Shruti 3 (Re2, komal)',
    'Shruti 4 (Re3, shuddha)',
    'Shruti 5 (Re4, shuddha)',
    'Shruti 6 (Ga1, komal)',
    'Shruti 7 (Ga2, komal)',
    'Shruti 8 (Ga3, shuddha)',
    'Shruti 9 (Ga4, shuddha)',
    'Shruti 10 (Ma1, shuddha)',
    'Shruti 11 (Ma2, tivra)',
    'Shruti 12 (Ma3, tivra)',
    'Shruti 13 (Ma4, tivra)',
    'Shruti 14 (Pa)',
    'Shruti 15 (Dha1, komal)',
    'Shruti 16 (Dha2, komal)',
    'Shruti 17 (Dha3, shuddha)',
    'Shruti 18 (Dha4, shuddha)',
    'Shruti 19 (Ni1, komal)',
    'Shruti 20 (Ni2, komal)',
    'Shruti 21 (Ni3, shuddha)',
    'Shruti 22 (Ni4, shuddha)',
    'Shruti 23 (Sa’)',
]

for name, ratio in zip(SHRUTI_NAMES, SHRUTI_RATIOS):
    SHRUTI_FREQUENCIES[name] = round(REFERENCE_FREQ * ratio, 2)


def assign_shruti(centroid, features, cluster_frames=None):
    """
    Return the Shruti name whose bin has the highest energy in the chroma
    portion of the K-Means cluster centroid.

    The centroid vector is laid out as [13 MFCC coefficients | 22 chroma bins]
    so ``centroid[13:]`` is the 22-element sub-vector carrying the pitch info.
    The argmax of that sub-vector is the dominant Shruti bin — a direct,
    musically meaningful assignment that replaces the previous invalid formula
    which treated MFCC-1 as a semitone offset from C4.
    """
    import numpy as np
    from .audio_processing import _SHRUTI_FREQS_ARR, _THRESHOLD_CENTS

    # Prefer the cluster's voiced F0s (musical truth); fall back to the
    # dominant chroma bin only when the cluster has no F0 energy.
    f0 = features.get('f0')
    voiced = features.get('voiced_flag')
    if f0 is not None and voiced is not None and cluster_frames is not None:
        f0_voiced = np.asarray(f0, dtype=np.float64)[np.asarray(voiced, dtype=bool)]
        if f0_voiced.size:
            median = float(np.nanmedian(f0_voiced))
            if np.isfinite(median):
                cents = np.abs(1200.0 * np.log2(median / _SHRUTI_FREQS_ARR))
                best = int(np.argmin(cents))
                if cents[best] < _THRESHOLD_CENTS:
                    return SHRUTI_NAMES[best]

    chroma_part = centroid[13:] if len(centroid) > 13 else centroid
    if len(chroma_part) == 0:
        return SHRUTI_NAMES[0]
    return SHRUTI_NAMES[int(np.argmax(chroma_part)) % len(SHRUTI_NAMES)]