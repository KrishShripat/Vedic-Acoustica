import numpy as np

REFERENCE_FREQ = 261.626

SHRUTI_FREQUENCIES = {}

SHRUTI_RATIOS = [
    1.0,
    256 / 243,
    16 / 15,
    10 / 9,
    9 / 8,
    32 / 27,
    5 / 4,
    81 / 64,
    4 / 3,
    729 / 512,
    3 / 2,
    128 / 81,
    8 / 5,
    5 / 3,
    27 / 16,
    16 / 9,
    9 / 5,
    15 / 8,
    243 / 128,
    2 / 1,
    25 / 8,
    3,
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


def assign_shruti(mfcc_centroid, features):
    centroid_mfcc = mfcc_centroid[0] if len(mfcc_centroid) > 0 else 0
    estimated_freq = 261.626 * (2 ** (centroid_mfcc / 12))

    min_diff = float('inf')
    closest = None
    for name, freq in SHRUTI_FREQUENCIES.items():
        diff = abs(estimated_freq - freq)
        if diff < min_diff:
            min_diff = diff
            closest = name
    return closest
