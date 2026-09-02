REFERENCE_FREQ = 261.626

SHRUTI_FREQUENCIES = {}

SHRUTI_RATIOS = [
    1.0,          # S1  Sa      — 261.63 Hz
    256 / 243,    # S2  Re1     — 275.65 Hz
    16 / 15,      # S3  Re2     — 278.44 Hz
    10 / 9,       # S4  Ga1     — 290.69 Hz
    9 / 8,        # S5  Ga2     — 294.33 Hz
    32 / 27,      # S6  Ga3     — 310.07 Hz
    5 / 4,        # S7  Ma1     — 327.03 Hz
    81 / 64,      # S8  Ma2     — 331.12 Hz
    4 / 3,        # S9  Ma3     — 348.83 Hz
    729 / 512,    # S10 Pa      — 372.51 Hz
    3 / 2,        # S11 Dha1    — 392.44 Hz
    128 / 81,     # S12 Dha2    — 413.43 Hz
    8 / 5,        # S13 Ni1     — 418.60 Hz
    5 / 3,        # S14 Ni2     — 436.05 Hz
    27 / 16,      # S15 Ni3     — 441.49 Hz
    16 / 9,       # S16 Sa'     — 465.11 Hz
    9 / 5,        # S17 Re'     — 470.93 Hz
    15 / 8,       # S18 Ga'     — 490.55 Hz
    243 / 128,    # S19 Ma'     — 496.68 Hz
    2 / 1,        # S20 Pa'     — 523.25 Hz
    8 / 3,        # S21 Dha'    — 697.66 Hz  ← was 25/8 (3.125) which is WRONG
    3,            # S22 Ni'     — 784.88 Hz
]

SHRUTI_NAMES = [
    'Shruti 1 (Sa)',
    'Shruti 2 (Re1)',
    'Shruti 3 (Re2)',
    'Shruti 4 (Ga1)',
    'Shruti 5 (Ga2)',
    'Shruti 6 (Ga3)',
    'Shruti 7 (Ma1)',
    'Shruti 8 (Ma2)',
    'Shruti 9 (Ma3)',
    'Shruti 10 (Pa)',
    'Shruti 11 (Dha1)',
    'Shruti 12 (Dha2)',
    'Shruti 13 (Ni1)',
    'Shruti 14 (Ni2)',
    'Shruti 15 (Ni3)',
    'Shruti 16 (Sa_)',
    'Shruti 17 (Re_)',
    'Shruti 18 (Ga_)',
    'Shruti 19 (Ma_)',
    'Shruti 20 (Pa_)',
    'Shruti 21 (Dha_)',
    'Shruti 22 (Ni_)',
]

for name, ratio in zip(SHRUTI_NAMES, SHRUTI_RATIOS):
    SHRUTI_FREQUENCIES[name] = round(REFERENCE_FREQ * ratio, 2)


def assign_shruti(centroid, features):
    """
    Return the Shruti name whose bin has the highest energy in the chroma
    portion of the K-Means cluster centroid.

    The centroid vector is laid out as [13 MFCC coefficients | 22 chroma bins]
    so ``centroid[13:]`` is the 22-element PCP sub-vector.  The argmax of that
    sub-vector is the dominant Shruti bin — a direct, musically meaningful
    assignment that replaces the previous invalid formula which treated MFCC-1
    as a semitone offset from C4.
    """
    import numpy as np
    chroma_part = centroid[13:] if len(centroid) > 13 else centroid
    if len(chroma_part) == 0:
        return SHRUTI_NAMES[0]
    return SHRUTI_NAMES[int(np.argmax(chroma_part)) % len(SHRUTI_NAMES)]
