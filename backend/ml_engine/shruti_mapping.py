REFERENCE_FREQ = 261.626

SHRUTI_FREQUENCIES = {}

SHRUTI_RATIOS = [
    1.0,          # S1  Sa          — 261.63 Hz  (1/1)
    256 / 243,    # S2  Re1         — 275.65 Hz  (256/243)
    16 / 15,      # S3  Re2         — 278.44 Hz  (16/15)
    10 / 9,       # S4  Ga1         — 290.69 Hz  (10/9)
    9 / 8,        # S5  Ga2         — 294.33 Hz  (9/8)
    32 / 27,      # S6  Ga3         — 310.07 Hz  (32/27)
    5 / 4,        # S7  Ma1         — 327.03 Hz  (5/4)
    81 / 64,      # S8  Ma2         — 331.12 Hz  (81/64)
    4 / 3,        # S9  Ma3         — 348.83 Hz  (4/3)
    729 / 512,    # S10 Tivra Ma    — 372.51 Hz  (729/512)
    3 / 2,        # S11 Pa          — 392.44 Hz  (3/2)
    128 / 81,     # S12 Dha1        — 413.43 Hz  (128/81)
    8 / 5,        # S13 Dha2        — 418.60 Hz  (8/5)
    5 / 3,        # S14 Ni1         — 436.05 Hz  (5/3)
    27 / 16,      # S15 Ni2         — 441.49 Hz  (27/16)
    16 / 9,       # S16 Ni3         — 465.11 Hz  (16/9)
    9 / 5,        # S17 Ni4         — 470.93 Hz  (9/5)    — Daniélou canonical
    15 / 8,       # S18 Ni5         — 490.55 Hz  (15/8)   — Daniélou canonical
    243 / 128,    # S19 Ni6         — 496.68 Hz  (243/128)— Daniélou canonical
    6 / 5,        # S20 Ga-Komal    — 313.95 Hz  (6/5)    — replaces 2/1 (octave Sa’)
    27 / 20,      # S21 Ma-Komal    — 353.20 Hz  (27/20)  — replaces 8/3 (above octave)
    45 / 32,      # S22 Tivra Ma2   — 367.79 Hz  (45/32)  — replaces 3   (above octave)
    2 / 1,        # S23 Sa’         — 523.25 Hz  (2/1)    — octave Sa’ (NEW)
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
    'Shruti 10 (Tivra Ma)',
    'Shruti 11 (Pa)',
    'Shruti 12 (Dha1)',
    'Shruti 13 (Dha2)',
    'Shruti 14 (Ni1)',
    'Shruti 15 (Ni2)',
    'Shruti 16 (Ni3)',
    'Shruti 17 (Ni4)',
    'Shruti 18 (Ni5)',
    'Shruti 19 (Ni6)',
    'Shruti 20 (Ga-Komal)',
    'Shruti 21 (Ma-Komal)',
    'Shruti 22 (Tivra Ma2)',
    'Shruti 23 (Sa’)',
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
