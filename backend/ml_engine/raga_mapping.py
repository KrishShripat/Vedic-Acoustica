import logging
import re
import numpy as np
from collections import Counter
from .shruti_mapping import SHRUTI_NAMES

logger = logging.getLogger(__name__)

# ── Pakad (characteristic phrase) import — local to avoid circular deps ───────
# DTW is already a project dependency (used in ghana_patha.py).
try:
    from .ghana_patha import dtw_distance as _dtw_distance
    _PAKAD_DTW_AVAILABLE = True
except Exception:  # pragma: no cover
    _PAKAD_DTW_AVAILABLE = False

# Minimum best-match confidence required to declare a conclusive raga match.
# Anything below this is reported as "Inconclusive" to the client.
CONFIDENCE_THRESHOLD = 0.40


# ─────────────────────────────────────────────────────────────────────────────
# Swara ↔ Shruti-bin vocabulary
# ─────────────────────────────────────────────────────────────────────────────
# Every raga scale is described by *grades* (e.g. 'Re-s' for shuddha Re).  Each
# grade owns a contiguous zone of 22-shruti bins (see shruti_mapping.py for the
# ascending bin order).  Scoring works on bins so both the natural-just and
# Pythagorean variants of a grade match the same raga, and 12-TET renderings
# land inside the correct zone.
#
# Zone scheme (bin ranges):
#   0 = Sa           [0]
#   Re komal  [1,2]      Re shuddha [3,4]
#   Ga komal  [5,6]      Ga shuddha [7,8]
#   Ma shuddha [9]       Ma tivra [10,11,12]
#   13 = Pa
#   Dha komal  [14,15]   Dha shuddha [16,17]
#   Ni komal  [18,19]    Ni shuddha [20,21]
#   22 = Sa' (octave, always rendered alongside Sa=0)
SWARA_ZONES = {
    'Sa':    [0],
    'Re-k':  [1, 2],
    'Re-s':  [3, 4],
    'Ga-k':  [5, 6],
    'Ga-s':  [7, 8],
    'Ma-s':  [9],
    'Ma-t':  [10, 11, 12],
    'Pa':    [13],
    'Dha-k': [14, 15],
    'Dha-s': [16, 17],
    'Ni-k':  [18, 19],
    'Ni-s':  [20, 21],
}

# Short display names for every Shruti bin, aligned 1:1 with SHRUTI_NAMES
# (parsed from the parenthesised token so the two can never drift apart).
_PILL_RE = re.compile(r'\(([^,\)]*)')


def _short_swara(full_name):
    m = _PILL_RE.search(full_name)
    return m.group(1).strip() if m else full_name


SWARA_SHORT_NAMES = [_short_swara(n) for n in SHRUTI_NAMES]
# 0:'Sa' 1:'Re1' 2:'Re2' 3:'Re3' 4:'Re4' 5:'Ga1' … 8:'Ga4' 9:'Ma1'
# 10:'Ma2' 11:'Ma3' 12:'Ma4' 13:'Pa' 14:'Dha1' … 17:'Dha4'
# 18:'Ni1' … 21:'Ni4' 22:"Sa'"

_SHRUTI_INDEX = {name: i for i, name in enumerate(SHRUTI_NAMES)}


def _expand_grades(grades):
    """Flatten a list of swara grades into their zone of Shruti bins."""
    bins = []
    for grade in grades:
        zone = SWARA_ZONES.get(grade)
        if zone is None:
            logger.warning('Unknown swara grade %r — skipping', grade)
            continue
        bins.extend(zone)
    return bins


# ─────────────────────────────────────────────────────────────────────────────
# Raga database
# ─────────────────────────────────────────────────────────────────────────────
# Each raga is described once, by grade tokens.  ``vadi``/``samvadi`` hold the
# dominant (vadi) and sub-dominant (samvadi) notes: ``grade`` selects the bin
# zone used for scoring, ``name`` is the human-readable swara letter shown in
# the UI.  ``arohana``/``avarohana`` are the traditional ascent/descent (order
# matters — some ragas are vakra, some omit notes in one direction).
RAGA_DATABASE = [
    {
        'name': 'Yaman',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Pa', 'Ma-t', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-s', 'name': 'Ni'},
        'time': 'Evening (9 PM - Midnight)',
        'mood': 'Devotional, serene, romantic',
    },
    {
        'name': 'Bilawal',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Pa', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Dha-s', 'name': 'Dha'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Morning (9 AM - Noon)',
        'mood': 'Bright, joyful',
    },
    {
        'name': 'Bhupali',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Pa', 'Dha-s'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Pa', 'Dha-s'],
        'avarohana': ['Sa', 'Dha-s', 'Pa', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Dha-s', 'name': 'Dha'},
        'time': 'First prahar of night',
        'mood': 'Devotional, contemplative',
    },
    {
        'name': 'Bhairav',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-s'],
        'arohana': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-k', 'Pa', 'Ma-s', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Dha-k', 'name': 'Dha'},
        'samvadi': {'grade': 'Re-k', 'name': 'Re'},
        'time': 'Early morning',
        'mood': 'Solemn, devotional',
    },
    {
        'name': 'Malkauns',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Ga-k', 'Ma-s', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Ga-k', 'Ma-s', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Ma-s', 'Ga-k', 'Sa'],
        'vadi': {'grade': 'Ma-s', 'name': 'Ma'},
        'samvadi': {'grade': 'Sa', 'name': 'Sa'},
        'time': 'Midnight',
        'mood': 'Mystical, meditative',
    },
    {
        'name': 'Darbari Kanada',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-k', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Re-s', 'name': 'Re'},
        'samvadi': {'grade': 'Pa', 'name': 'Pa'},
        'time': 'Late night',
        'mood': 'Deep, dignified',
    },
    {
        'name': 'Khamaj',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-s', 'Pa', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-k', 'name': 'Ni'},
        'time': 'Late evening',
        'mood': 'Light, romantic',
    },
    {
        'name': 'Kafi',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-s', 'Pa', 'Ma-s', 'Ga-k', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Sa', 'name': 'Sa'},
        'time': 'Evening',
        'mood': 'Light, lyrical',
    },
    {
        'name': 'Asavari',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Dha-k'],      # Ga, Ni omitted in ascent
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-k', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Dha-k', 'name': 'Dha'},
        'samvadi': {'grade': 'Ga-k', 'name': 'Ga'},
        'time': 'Late morning',
        'mood': 'Devotional, plaintive',
    },
    {
        'name': 'Poorvi',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'arohana': ['Sa', 'Re-k', 'Ga-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-k', 'Pa', 'Ma-t', 'Ma-s', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-s', 'name': 'Ni'},
        'time': 'Late evening',
        'mood': 'Serious, dignified',
    },
    {
        'name': 'Todi',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-k', 'Ga-k', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'arohana': ['Sa', 'Re-k', 'Ga-k', 'Ma-t', 'Dha-k', 'Ni-s'],  # Pa omitted in ascent
        'avarohana': ['Sa', 'Ni-s', 'Dha-k', 'Pa', 'Ma-t', 'Ga-k', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Dha-k', 'name': 'Dha'},
        'samvadi': {'grade': 'Ga-k', 'name': 'Ga'},
        'time': 'Morning',
        'mood': 'Deep, meditative',
    },
    {
        'name': 'Puriya',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-t', 'Dha-s', 'Ni-s'],   # no Pa
        'arohana': ['Sa', 'Re-k', 'Ga-s', 'Ma-t', 'Dha-s', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Ma-t', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-s', 'name': 'Ni'},
        'time': 'Sunset',
        'mood': 'Devotional, yearning',
    },
    {
        'name': 'Marwa',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-t', 'Dha-s', 'Ni-s'],   # no Pa
        'arohana': ['Sa', 'Re-k', 'Ga-s', 'Ma-t', 'Dha-s', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Ma-t', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Re-k', 'name': 'Re'},
        'samvadi': {'grade': 'Dha-s', 'name': 'Dha'},
        'time': 'Sunset',
        'mood': 'Restless, expectant',
    },
    {
        'name': 'Bhairavi',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-k', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-k', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-k', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Ma-s', 'name': 'Ma'},
        'samvadi': {'grade': 'Sa', 'name': 'Sa'},
        'time': 'Morning',
        'mood': 'Devotional, tender',
    },
    {
        'name': 'Kedar',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Sa', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],          # Re, Ga omitted in ascent
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Pa', 'Ma-t', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ma-s', 'name': 'Ma'},
        'samvadi': {'grade': 'Sa', 'name': 'Sa'},
        'time': 'Late evening',
        'mood': 'Devotional, yearning',
    },
    {
        'name': 'Megh',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Ni-k'],            # no Ga, no Dha
        'arohana': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Pa', 'Ma-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Sa', 'name': 'Sa'},
        'samvadi': {'grade': 'Pa', 'name': 'Pa'},
        'time': 'Monsoon season',
        'mood': 'Majestic, rain-bringing',
    },
    {
        'name': 'Jhinjhoti',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Dha-s'],          # Ga, Ni omitted in ascent
        'avarohana': ['Sa', 'Ni-k', 'Dha-s', 'Pa', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-k', 'name': 'Ni'},
        'time': 'Late night',
        'mood': 'Romantic, pleasant',
    },
    {
        'name': 'Rageshree',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Dha-s', 'Ni-k'],  # no Pa
        'arohana': ['Sa', 'Ga-s', 'Ma-s', 'Dha-s', 'Ni-k'],         # Re omitted in ascent
        'avarohana': ['Sa', 'Ni-k', 'Dha-s', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-k', 'name': 'Ni'},
        'time': 'Late night',
        'mood': 'Passionate, intense',
    },
    {
        'name': 'Bihag',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Pa', 'Ma-t', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-s', 'name': 'Ni'},
        'time': 'Night',
        'mood': 'Devotional, tender',
    },
    {
        'name': 'Sindhi Bhairavi',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-k', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Dha-s', 'Ni-k'],
        'arohana': ['Sa', 'Re-k', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Dha-s', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-s', 'Dha-k', 'Pa', 'Ma-s', 'Ga-k', 'Re-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Ma-s', 'name': 'Ma'},
        'samvadi': {'grade': 'Sa', 'name': 'Sa'},
        'time': 'Any time',
        'mood': 'Devotional, pathos',
    },
    {
        'name': 'Shankarabharanam',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Pa', 'Ma-s', 'Ga-s', 'Re-s', 'Sa', 'Ni-s', 'Dha-s', 'Pa'],
        'avarohana': ['Pa', 'Dha-s', 'Ni-s', 'Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Morning',
        'mood': 'Grand, auspicious',
    },
    {
        'name': 'Kharaharapriya',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-s', 'Pa', 'Ma-s', 'Ga-k', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-k', 'name': 'Ga'},
        'time': 'Afternoon',
        'mood': 'Expressive, deeply emotional',
    },
    {
        'name': 'Mayamalavagowla',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-s'],
        'arohana': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-k', 'Pa', 'Ma-s', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Dha-k', 'name': 'Dha'},
        'samvadi': {'grade': 'Re-k', 'name': 'Re'},
        'time': 'Early morning',
        'mood': 'Peaceful, meditative',
    },
    {
        'name': 'Sri Raga',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Ni-k'],          # Ga, Dha omitted in ascent
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ma-s', 'name': 'Ma'},
        'samvadi': {'grade': 'Ni-k', 'name': 'Ni'},
        'time': 'Evening',
        'mood': 'Devotional, majestic',
    },
    {
        'name': 'Kalyani',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Pa', 'Ma-t', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Any time',
        'mood': 'Joyous, auspicious',
    },
    {
        'name': 'Todi (Carnatic)',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-k', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-k', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-k', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Dha-k', 'name': 'Dha'},
        'samvadi': {'grade': 'Ga-k', 'name': 'Ga'},
        'time': 'Morning',
        'mood': 'Serene, contemplative',
    },
    {
        'name': 'Bhairavi (Carnatic)',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-k', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ma-s', 'name': 'Ma'},
        'samvadi': {'grade': 'Sa', 'name': 'Sa'},
        'time': 'Any time',
        'mood': 'Devotion, pathos',
    },
    {
        'name': 'Kambhoji',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Pa', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Evening',
        'mood': 'Devotional, romantic',
    },
    {
        'name': 'Abhogi',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Dha-k'],        # no Pa, no Ni
        'arohana': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Dha-k'],
        'avarohana': ['Sa', 'Dha-k', 'Ma-s', 'Ga-k', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-k', 'name': 'Ga'},
        'time': 'Any time',
        'mood': 'Introspective, tender',
    },
    {
        'name': 'Hamsadhwani',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Pa', 'Ni-s'],           # no Ma, no Dha
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Pa', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Pa', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ni-s', 'name': 'Ni'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Any time',
        'mood': 'Bright, auspicious',
    },
    {
        'name': 'Chakravakam',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Morning',
        'mood': 'Evocative, pathos',
    },
    {
        'name': 'Kapi',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-t', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ma-s', 'name': 'Ma'},
        'samvadi': {'grade': 'Ni-k', 'name': 'Ni'},
        'time': 'Evening',
        'mood': 'Devotional, pathos',
    },
    {
        'name': 'Latangi',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-k', 'Pa', 'Ma-t', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Morning',
        'mood': 'Grand, festive',
    },
    {
        'name': 'Mechakalyani',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-t', 'Pa', 'Dha-s', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-s', 'Pa', 'Ma-t', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Night',
        'mood': 'Ethereal, deeply moving',
    },
    # ── 10 ragas (ML-6) ─────────────────────────────────────────────────────
    {
        'name': 'Durga',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Dha-s'],          # pentatonic — no Ga, no Ni
        'arohana': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Dha-s'],
        'avarohana': ['Sa', 'Dha-s', 'Pa', 'Ma-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Dha-s', 'name': 'Dha'},
        'samvadi': {'grade': 'Re-s', 'name': 'Re'},
        'time': 'Late evening',
        'mood': 'Bright, devotional, joyous',
    },
    {
        'name': 'Shankara',
        'tradition': 'Hindustani',
        'swaras': ['Sa', 'Ga-s', 'Pa', 'Ni-s'],                   # audav — no Re, no Ma
        'arohana': ['Sa', 'Ga-s', 'Pa', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Pa', 'Ga-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Night',
        'mood': 'Heroic, devotional, majestic',
    },
    {
        'name': 'Charukeshi',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Afternoon',
        'mood': 'Serious, dignified, melancholic',
    },
    {
        'name': 'Nata Bhairavi',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-k', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Ma-s', 'name': 'Ma'},
        'samvadi': {'grade': 'Sa', 'name': 'Sa'},
        'time': 'Evening to midnight',
        'mood': 'Plaintive, romantic, yearning',
    },
    {
        'name': 'Mand',
        'tradition': 'Rajasthani folk',
        'swaras': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-s'],
        'arohana': ['Sa', 'Ga-s', 'Pa', 'Dha-s', 'Ma-s', 'Re-s'],
        'avarohana': ['Sa', 'Dha-s', 'Pa', 'Ga-s', 'Ma-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Re-s', 'name': 'Re'},
        'time': 'Night',
        'mood': 'Folk, festive, lyrical',
    },
    {
        'name': 'Madhyamavati',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Ni-s'],           # pentatonic, no Ga, no Dha
        'arohana': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Pa', 'Ma-s', 'Re-s', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Re-s', 'name': 'Re'},
        'time': 'Any time',
        'mood': 'Devotional, melodious, meditative',
    },
    {
        'name': 'Vasanta',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'arohana': ['Sa', 'Ga-s', 'Re-k', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-k', 'Pa', 'Ma-t', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-s', 'name': 'Ni'},
        'time': 'Spring season, any time',
        'mood': 'Joyful, festive, celebratory',
    },
    {
        'name': 'Panthuvarali',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'arohana': ['Sa', 'Re-k', 'Ga-s', 'Ma-t', 'Pa', 'Dha-k', 'Ni-s'],
        'avarohana': ['Sa', 'Ni-s', 'Dha-k', 'Pa', 'Ma-t', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'samvadi': {'grade': 'Ni-s', 'name': 'Ni'},
        'time': 'Any time',
        'mood': 'Serious, profound, intense',
    },
    {
        'name': 'Saveri',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-k', 'Ma-s', 'Pa', 'Dha-k'],          # pentatonic — no Ga, no Ni
        'arohana': ['Sa', 'Re-k', 'Ma-s', 'Pa', 'Dha-k'],
        'avarohana': ['Sa', 'Dha-k', 'Pa', 'Ma-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Re-k', 'name': 'Re'},
        'time': 'Morning',
        'mood': 'Serene, devotional, gentle',
    },
    {
        'name': 'Ritigowla',
        'tradition': 'Carnatic',
        'swaras': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'arohana': ['Sa', 'Ga-s', 'Re-k', 'Ma-s', 'Pa', 'Dha-k', 'Ni-k'],
        'avarohana': ['Sa', 'Ni-k', 'Dha-k', 'Pa', 'Ma-s', 'Ga-s', 'Re-k', 'Sa'],
        'vadi': {'grade': 'Pa', 'name': 'Pa'},
        'samvadi': {'grade': 'Ga-s', 'name': 'Ga'},
        'time': 'Any time',
        'mood': 'Devotional, tender, deeply moving',
    },
]

# ── Derived bin representations (computed once at import) ────────────────────
# Scoring and the API operate on concrete Shruti bins (0..22); the grade tokens
# above are the single source of truth.  ``arohana_bins``/``avarohana_bins``
# preserve phrase order (used for the vakra direction checks and the UI strip).
for _raga in RAGA_DATABASE:
    _raga['swaras_bins'] = list(dict.fromkeys(_expand_grades(_raga['swaras'])))
    _raga['arohana_bins'] = _expand_grades(_raga['arohana'])
    _raga['avarohana_bins'] = _expand_grades(_raga['avarohana'])
    _raga['vadi_bins'] = _expand_grades([_raga['vadi']['grade']])
    _raga['samvadi_bins'] = _expand_grades([_raga['samvadi']['grade']])


# ─────────────────────────────────────────────────────────────────────────────
# Pakad (characteristic phrase) database — Stage 4b
# ─────────────────────────────────────────────────────────────────────────────
# Each entry is a list of (n_frames, 23) idealised PCP keyframe sequences that
# represent the raga's pakad (signature melodic phrase).  DTW is used to search
# for the best-matching subsequence in the audio's PCP matrix.
#
# Shruti→PCP index (0-based, matches shruti_mapping.py ascending order):
#   0=Sa 1=Re1 2=Re2 3=Re3 4=Re4 5=Ga1 6=Ga2 7=Ga3 8=Ga4
#   9=Ma1 10=Ma2 11=Ma3 12=Ma4 13=Pa 14=Dha1 15=Dha2 16=Dha3 17=Dha4
#   18=Ni1 19=Ni2 20=Ni3 21=Ni4 22=Sa'
#
# These templates encode *order* and *emphasis*, not just presence — allowing
# the system to distinguish ragas that share the same swara set.
# ─────────────────────────────────────────────────────────────────────────────

def _pakad_template(frames_shruti_lists):
    """Build a (T, len(SHRUTI_NAMES)) float32 PCP template from a list of active shruti indices."""
    T = len(frames_shruti_lists)
    tpl = np.zeros((T, len(SHRUTI_NAMES)), dtype=np.float32)
    for t, indices in enumerate(frames_shruti_lists):
        for idx in indices:
            tpl[t, idx] = 1.0
        norm = np.linalg.norm(tpl[t])
        if norm > 0:
            tpl[t] /= norm
    return tpl


PAKAD_DATABASE = {
    # ── Yaman: Ni Re Ga — Ga TivraMa Pa — ni-re-ga opening ──────────────────
    # Ni-s(21) Re-s(4) Ga-s(8) → Ga-s + TivraMa(11) → Pa(13)
    'Yaman': _pakad_template([
        [21],            # Ni-s (strong opening note)
        [4],             # Re-s
        [8],             # Ga-s
        [21, 4],         # Ni–Re oscillation
        [8, 11],         # Ga–TivraMa (the diagnostic interval)
        [13],            # Pa
    ]),

    # Bilawal: Sa Re Ga Ma — Pa Dha — Ni Sa' — emphasis on Sa and Pa
    'Bilawal': _pakad_template([
        [0],             # Sa (strong start)
        [3, 4, 7, 8],    # Re–Ga region
        [9],             # Ma (shuddha)
        [13],            # Pa
        [16, 17],        # Dha region
        [22],            # Sa' (return — vakra)
    ]),

    # Jhinjhoti: Sa Re Ga Ma Pa — Ni Dha Pa — Ga Re Sa — komal Ni in descent
    'Jhinjhoti': _pakad_template([
        [0, 3, 4],       # Sa–Re
        [8],             # Ga-s
        [13],            # Pa
        [18],            # Ni1 (komal — diagnostic!)
        [16, 17],        # Dha region
        [13],            # Pa
        [8, 4, 0],       # Ga–Re–Sa
    ]),

    # Shankarabharanam: Pa Ma Ga Re Sa — Ni Dha Pa (Carnatic major, starts Pa)
    'Shankarabharanam': _pakad_template([
        [13],            # Pa (characteristic opening from Pa)
        [9],             # Ma
        [8],             # Ga-s
        [4],             # Re-s
        [0],             # Sa
        [21],            # Ni-s
        [17],            # Dha-s
        [13],            # Pa
    ]),

    # Mand: Sa Ga Pa Dha — Ma Ga Re Sa — Rajasthani folk curve
    'Mand': _pakad_template([
        [0],             # Sa
        [8],             # Ga-s
        [13],            # Pa
        [17],            # Dha-s
        [9, 8, 4, 0],    # Ma–Ga–Re–Sa (folk descending)
    ]),

    # ── Bhairav region ──────────────────────────────────────────────────────
    # Bhairav: Sa Re1 — Ga Ma — Pa Dha1 Ni1 Sa'
    'Bhairav': _pakad_template([
        [0],             # Sa
        [1],             # Re1 (komal)
        [8, 9],          # Ga–Ma
        [13],            # Pa
        [14],            # Dha1 (komal)
        [18],            # Ni1 (komal)
        [22],            # Sa'
    ]),

    # Mayamalavagowla: Sa Re1 Ga2 — Pa Dha1 Ni1 — distinctive jump Re1→Ga2
    'Mayamalavagowla': _pakad_template([
        [0],             # Sa
        [1],             # Re1 (komal)
        [8],             # Ga2 (shuddha — jumps over Ga1)
        [13],            # Pa
        [14],            # Dha1 (komal)
        [18, 22],        # Ni1→Sa'
    ]),

    # ── Kafi/Khamaj region ──────────────────────────────────────────────────
    # Kafi: Sa Re Ga1 Ma Pa Dha — komal Ga and komal Ni
    'Kafi': _pakad_template([
        [0],             # Sa
        [4],             # Re-s
        [5],             # Ga1 (komal — diagnostic)
        [9, 13],         # Ma–Pa
        [17],            # Dha-s
        [18],            # Ni1 (komal)
        [0],             # Sa
    ]),

    # Khamaj: Pa Ni Dha Pa — Ga Ma Pa — Ni in descent only
    'Khamaj': _pakad_template([
        [13],            # Pa (characteristic start)
        [18],            # Ni1 (komal in descent)
        [17],            # Dha-s
        [13],            # Pa
        [8, 9, 13],      # Ga–Ma–Pa ascending
    ]),

    # ── Todi variants ───────────────────────────────────────────────────────
    # Todi (Hindustani): Re1 Ga1 Ma2 — Pa Dha1 Ni1 — komal + tivra Ma
    'Todi': _pakad_template([
        [1],             # Re1 (komal)
        [5],             # Ga1 (komal)
        [11],            # Ma3/tivra region
        [13],            # Pa (avoided in avaroh)
        [14],            # Dha1 (komal)
        [18, 1, 0],      # Ni1–Re1–Sa
    ]),
}


def apply_pakad_tiebreak(matches, features, top_n=3):
    """
    Use DTW-based Pakad (phrase) matching to disambiguate ragas that scored
    within ``PAKAD_TIEBREAK_MARGIN`` of each other in the primary scoring step.

    For each candidate raga in ``matches[:top_n]`` that has a Pakad template,
    the function searches for the best-matching subsequence in the audio's PCP
    by sliding a window equal to the template length across the PCP matrix and
    computing the minimum DTW distance.  The candidate with the best Pakad
    match gets a confidence bonus, potentially re-ordering the top candidates.

    Parameters
    ----------
    matches   : list of raga match dicts (already sorted by confidence desc)
    features  : dict — extract_features() output; must contain 'pcp'
    top_n     : int — how many top candidates to check (default 3)

    Returns
    -------
    matches : list, potentially re-ordered if a Pakad match changes ranking
    """
    if not _PAKAD_DTW_AVAILABLE:
        return matches
    pcp = features.get('pcp')  # (23, n_frames)
    if pcp is None or pcp.shape[1] < 5:
        return matches

    n_frames = pcp.shape[1]
    pcp_T = pcp.T.astype(np.float32)  # (n_frames, 23) — row=frame, col=shruti

    PAKAD_TIEBREAK_MARGIN = 0.05   # only fire when top-2 are within 5%
    if len(matches) < 2:
        return matches   # nothing to disambiguate — a tiebreak needs ≥2 candidates
    if matches[0]['confidence'] - matches[1]['confidence'] > PAKAD_TIEBREAK_MARGIN:
        return matches   # clear winner — no need for Pakad check

    PAKAD_BONUS = 0.08   # maximum confidence boost awarded for a Pakad match

    for i, m in enumerate(matches[:top_n]):
        raga_name = m['raga_name']
        template = PAKAD_DATABASE.get(raga_name)
        if template is None:
            continue   # no Pakad defined for this raga yet

        T_tpl = len(template)   # number of keyframes in the Pakad template
        if n_frames < T_tpl:
            continue

        # Sliding-window search: find the minimum DTW distance over all windows
        best_sim = 0.0
        for start in range(0, n_frames - T_tpl + 1, max(T_tpl // 2, 1)):
            window = pcp_T[start: start + T_tpl]   # (T_tpl, 23)
            dist, _ = _dtw_distance(window, template)
            sim = 1.0 - dist
            if sim > best_sim:
                best_sim = sim

        # Award a scaled bonus (up to PAKAD_BONUS) proportional to match quality
        bonus = round(PAKAD_BONUS * best_sim, 4)
        new_conf = round(min(m['confidence'] + bonus, 1.0), 4)

        logger.info(
            'Pakad tiebreak: %s best_sim=%.4f bonus=%.4f old_conf=%.4f new_conf=%.4f',
            raga_name, best_sim, bonus, m['confidence'], new_conf,
        )

        matches[i] = dict(m, confidence=new_conf,
                          pakad_similarity=round(best_sim, 4),
                          pakad_bonus=bonus)

    matches.sort(key=lambda x: x['confidence'], reverse=True)
    return matches


def _extract_detected_swaras(freq_assignments):
    """Legacy path: build swara (bin) hits from per-frame string assignments."""
    swara_hits = Counter()
    for assignment in freq_assignments:
        if assignment is None:
            continue
        idx = _SHRUTI_INDEX.get(assignment)
        if idx is not None:
            swara_hits[idx] += 1
    return swara_hits


def _extract_detected_swaras_from_pcp(mean_pcp, energy_threshold=0.02):
    """
    Build a swara (bin) energy map from the 23-element mean PCP vector.

    mean_pcp : list or array of 23 floats in [0, 1]
        Recording-level Shruti energy fingerprint from compute_pcp().
    energy_threshold : float
        Shrutis with mean energy below this fraction of the max are ignored.

    Returns a dict {bin_index: energy_float} over all 23 Shruti bins.
    """
    pcp = np.asarray(mean_pcp, dtype=np.float64)
    max_energy = pcp.max()
    if max_energy == 0:
        return {}
    return {
        int(i): float(pcp[i])
        for i in range(len(pcp))
        if pcp[i] >= energy_threshold * max_energy
    }


# A swara is only counted as "present" when it is the dominant pitch class for
# at least this fraction of the total voiced frames.  This duration/salience
# gate filters out tanpura drone bleed and transient vocal glides that briefly
# touch many bins but are never actually sustained (the root cause of the
# "15 swaras detected" false-dominance problem on real recordings).
#
# Tuned to 1.2%: at 3.0% continuous vocal ornamentation (meends/gamakas) was
# discarded as transient noise, leaving too few swaras; at 1.2% we filter
# continuous drone noise while keeping legitimate ornamented notes.
SWARA_PRESENCE_THRESHOLD = 0.012


def _extract_detected_swaras_by_salience(pcp, voiced_flag, f0=None,
                                         presence_threshold=SWARA_PRESENCE_THRESHOLD):
    """
    Duration/salience-gated swara detection from the melodic pitch track.

    A swara counts as "present" only when it is the nearest Shruti to the pYIN
    F0 for at least ``presence_threshold`` of the total voiced frames.  Using
    the F0 track (rather than raw PCP argmax) avoids the tanpura-drone/harmonic
    bleed that falsely lights up many swaras, and the duration gate removes
    transient vocal glides that never settle on a sustained note.

    Parameters
    ----------
    pcp : ndarray (23, n_frames) — per-frame Shruti energies
    voiced_flag : ndarray (n_frames,) bool — True for voiced frames
    f0 : ndarray (n_frames,) optional — pYIN fundamental frequency (NaN unvoiced)
    presence_threshold : float — min fraction of voiced frames a swara must be
                                 the dominant pitch class for to count as present

    Returns
    -------
    dict {bin_index: salience} over all 23 Shruti bins whose occupancy is
    >= presence_threshold.  The value is the occupancy fraction, used as the
    swara's salience weight in scoring.
    """
    from .ml_engine import _nearest_shruti_from_f0

    pcp = np.asarray(pcp, dtype=np.float64)
    if pcp.ndim != 2 or pcp.shape[0] < 1 or pcp.shape[1] == 0:
        return {}

    voiced = np.asarray(voiced_flag, dtype=bool)
    n_frames = pcp.shape[1]
    if voiced.ndim == 0 or len(voiced) == 0:
        voiced = np.ones(n_frames, dtype=bool)

    f0_arr = np.asarray(f0, dtype=np.float64) if f0 is not None else None

    total_voiced = int(np.count_nonzero(voiced[:n_frames]))
    if total_voiced == 0:
        return {}

    # Dominant shruti bin per voiced frame, preferring pYIN F0 (clean melodic
    # pitch) and falling back to PCP argmax for voiced frames where F0 is
    # unavailable or out of range.
    counts = np.zeros(pcp.shape[0], dtype=np.int64)
    for i in range(n_frames):
        if not voiced[i]:
            continue
        assigned = None
        if f0_arr is not None and i < len(f0_arr) and not np.isnan(f0_arr[i]):
            assigned = _nearest_shruti_from_f0(f0_arr[i])
        if assigned is None:
            assigned = int(pcp[:, i].argmax())
        if 0 <= assigned < pcp.shape[0]:
            counts[assigned] += 1

    occupancy = counts / total_voiced
    return {
        int(i): float(occupancy[i])
        for i in range(pcp.shape[0])
        if occupancy[i] >= presence_threshold
    }


def _extract_directional_swaras(pcp, f0, voiced_flag,
                                presence_threshold=SWARA_PRESENCE_THRESHOLD):
    """
    Split F0-dominant Shruti occupancy into arohana (rising F0) and avarohana
    (falling F0) maps, using the same salience gating as the overall detector.

    Each voiced frame is assigned its dominant Shruti bin (pYIN F0 nearest
    shruti, falling back to PCP argmax) and classified as rising or falling
    from the smoothed F0 gradient.  A bin only enters a direction's map when it
    held the dominant pitch for at least ``presence_threshold`` of the voiced
    frames *in that direction*, so harmonic bleed and drone energy never
    saturate the arohana/avarohana coverage terms used in scoring.

    Parameters
    ----------
    pcp : ndarray (23, n_frames)
    f0  : ndarray (n_frames,) — NaN for unvoiced
    voiced_flag : ndarray bool (n_frames,)
    presence_threshold : float — min fraction of voiced frames for a bin to
                                 count as present in a direction

    Returns
    -------
    arohana_swaras   : dict {bin_index: occupancy}
    avarohana_swaras : dict {bin_index: occupancy}
    """
    from .ml_engine import _nearest_shruti_from_f0

    n_frames = pcp.shape[1]
    align = min(len(f0), n_frames, len(voiced_flag))
    f0_a = np.asarray(f0[:align], dtype=np.float64)
    vf_a = np.asarray(voiced_flag[:align], dtype=bool)

    # Smoothed F0 gradient for rising/falling classification
    f0_filled = np.where(np.isnan(f0_a), 0.0, f0_a)
    smoothing_frames = 3
    if align > 2 * smoothing_frames:
        kernel = np.ones(smoothing_frames) / smoothing_frames
        f0_smooth = np.convolve(f0_filled, kernel, mode='same')
    else:
        f0_smooth = f0_filled
    gradient = np.gradient(f0_smooth)

    aro_counts = np.zeros(pcp.shape[0], dtype=np.int64)
    ava_counts = np.zeros(pcp.shape[0], dtype=np.int64)
    for i in range(align):
        if not vf_a[i]:
            continue
        assigned = None
        if not np.isnan(f0_a[i]):
            assigned = _nearest_shruti_from_f0(f0_a[i])
        if assigned is None:
            assigned = int(pcp[:, i].argmax())
        if not (0 <= assigned < len(aro_counts)):
            continue
        if gradient[i] >= 0:
            aro_counts[assigned] += 1
        else:
            ava_counts[assigned] += 1

    def _gate(counts):
        if counts.sum() == 0:
            return {}
        occ = counts / counts.sum()
        return {int(i): float(occ[i]) for i in range(pcp.shape[0])
                if occ[i] >= presence_threshold}

    return _gate(aro_counts), _gate(ava_counts)


def _score_raga(detected_swaras, raga,
                arohana_swaras=None, avarohana_swaras=None,
                total_frames=None):
    """
    Score a raga against detected swara (bin) energies with directional weighting.

    When ``arohana_swaras`` / ``avarohana_swaras`` are supplied (split by F0
    gradient direction), the scorer checks ascending and descending swara
    usage separately — allowing ragas with asymmetric or vakra scales to
    score higher than ragas whose flat swara-set looks identical.

    Score components
    ----------------
    jaccard_total (0.25)      — overall swara-set overlap (backward compat)
    arohana_coverage (0.25)   — fraction of raga arohana swaras detected
                                in rising phrases
    avarohana_coverage (0.25) — fraction of raga avarohana swaras detected
                                in falling phrases
    direction_penalty (0.10)  — penalise swaras used in the wrong direction
    vadi/samvadi bonus (0.15) — dominant note prominence

    Note: ``detected_swaras`` keys are Shruti bin indices (0..22).  Raga
    ``swaras_bins``/``arohana_bins``/``avarohana_bins`` are zone-expanded bin
    lists, so the same zone of just/pythagorean microtones (and 12-TET notes
    rendered into it) all count as the grade present.
    """
    if not detected_swaras:
        return 0.0, {}

    raga_swaras = set(raga['swaras_bins'])
    detected_set = set(detected_swaras.keys())
    intersection = raga_swaras & detected_set
    union = raga_swaras | detected_set
    if not union:
        return 0.0, {}

    jaccard = len(intersection) / len(union)

    # ── Extraneous swara penalty ──────────────────────────────────────────────
    # Notes present in the audio but *completely forbidden* in the raga (i.e.
    # not part of its scale at all) undermine the match.  The more of the
    # detected set lies outside the raga's scale, the more we subtract.
    extraneous = detected_set - raga_swaras
    extraneous_penalty = 0.0
    if detected_set:
        extraneous_penalty = round(
            0.20 * (len(extraneous) / len(detected_set)), 4
        )

    vadi_set = set(raga['vadi_bins'])
    samvadi_set = set(raga['samvadi_bins'])
    total_weight = sum(detected_swaras.values()) or 1.0

    vadi_bonus = 0.0
    if vadi_set & detected_set:
        vadi_energy = sum(detected_swaras.get(b, 0.0) for b in vadi_set)
        vadi_bonus = 0.10 * min(vadi_energy / (total_weight * 0.1), 1.0)

    samvadi_bonus = 0.0
    if samvadi_set & detected_set:
        samvadi_energy = sum(detected_swaras.get(b, 0.0) for b in samvadi_set)
        samvadi_bonus = 0.05 * min(samvadi_energy / (total_weight * 0.05), 1.0)

    # ── Directional coverage ──────────────────────────────────────────────────
    raga_aro_set = set(raga['arohana_bins'])
    raga_ava_set = set(raga['avarohana_bins'])

    if arohana_swaras and avarohana_swaras:
        aro_detected = set(arohana_swaras.keys())
        ava_detected = set(avarohana_swaras.keys())

        aro_coverage = (len(raga_aro_set & aro_detected) / len(raga_aro_set)
                        if raga_aro_set else 0.0)
        ava_coverage = (len(raga_ava_set & ava_detected) / len(raga_ava_set)
                        if raga_ava_set else 0.0)

        # Direction penalty: swaras found going UP that the raga only allows
        # going DOWN (and vice versa).  Only penalise when the sets differ
        # (symmetric ragas have identical arohana/avarohana so penalty = 0).
        aro_only = raga_aro_set - raga_ava_set   # swaras exclusive to arohana
        ava_only = raga_ava_set - raga_aro_set   # swaras exclusive to avarohana
        wrong_aro = len(aro_only & ava_detected)  # exclusive-aro found in ava
        wrong_ava = len(ava_only & aro_detected)  # exclusive-ava found in aro
        max_wrong = max(len(aro_only) + len(ava_only), 1)
        direction_penalty = 0.10 * (1.0 - (wrong_aro + wrong_ava) / max_wrong)

        score = min(
            0.25 * jaccard
            + 0.25 * aro_coverage
            + 0.25 * ava_coverage
            + direction_penalty
            + vadi_bonus + samvadi_bonus
            - extraneous_penalty,
            1.0
        )
        directional = True
    else:
        # Flat (non-directional) fallback — original formula
        coverage = len(intersection) / len(raga_swaras) if raga_swaras else 0.0
        aro_coverage = ava_coverage = coverage
        direction_penalty = 0.0
        score = min(
            0.45 * jaccard + 0.25 * coverage + vadi_bonus * 3 + samvadi_bonus * 3
            - extraneous_penalty,
            1.0
        )
        directional = False

    return round(score, 4), {
        'matched_swaras': sorted(intersection),
        'jaccard_similarity': round(jaccard, 4),
        'arohana_coverage': round(aro_coverage, 4),
        'avarohana_coverage': round(ava_coverage, 4),
        'direction_penalty': round(direction_penalty, 4) if directional else None,
        'extraneous_penalty': extraneous_penalty,
        'extraneous_swaras': sorted(extraneous),
        'vadi_detected': bool(vadi_set & detected_set),
        'samvadi_detected': bool(samvadi_set & detected_set),
        'directional_scoring': directional,
    }


def detect_raga(clustering_results, features=None, min_confidence=0.25):
    """
    Detect the most likely raga with arohana/avarohana directional scoring.

    When ``features`` (output of extract_features) is provided and contains
    pYIN F0 data, frames are split into rising/falling by F0 gradient and
    scored against each raga's arohana and avarohana separately.  Falls back
    to flat Jaccard scoring when F0 is unavailable.
    """
    mean_pcp = clustering_results.get('mean_pcp')
    freq_assignments = clustering_results.get('freq_assignments', [])

    # ── Near-silence / noise guard ─────────────────────────────────────────────
    if features is not None and features.get('rms', 1.0) < 0.01:
        reason = 'Audio is essentially silent or pure noise'
        logger.warning(
            'Raga detection (%s): %s (rms=%.4f)',
            'energy-gate', reason, features.get('rms'),
        )
        return {
            'detected_swaras': [],
            'arohana_swaras': [],
            'avarohana_swaras': [],
            'directional_scoring': False,
            'matches': [],
            'best_match': None,
            'is_inconclusive': True,
            'inconclusive_reason': reason,
            'confidence_threshold': CONFIDENCE_THRESHOLD,
            'total_frames_analyzed': 0,
            'detection_source': 'energy-gate',
            'reason': reason,
        }

    # Prefer duration/salience-gated detection from frame-level PCP (it rejects
    # tanpura drone bleed / slides that falsely light up many swaras).  Fall back
    # to the recording-level mean PCP when frame data is unavailable.
    if (features is not None
            and features.get('pcp') is not None
            and features.get('voiced_flag') is not None):
        detected_swaras = _extract_detected_swaras_by_salience(
            features['pcp'], features['voiced_flag'],
            f0=features.get('f0'))
        source = 'salience'
    elif mean_pcp is not None:
        detected_swaras = _extract_detected_swaras_from_pcp(mean_pcp)
        source = 'pcp'
    else:
        detected_swaras = _extract_detected_swaras(freq_assignments)
        source = 'heuristic'

    if not detected_swaras:
        reason = (
            'No frequency data received'
            if (not freq_assignments and mean_pcp is None)
            else 'No valid swaras detected from frequency data'
        )
        logger.warning(
            'Raga detection (%s): %s (%d frames)', source, reason, len(freq_assignments)
        )
        return {
            'detected_swaras': [],
            'arohana_swaras': [],
            'avarohana_swaras': [],
            'directional_scoring': False,
            'matches': [],
            'best_match': None,
            'is_inconclusive': True,
            'inconclusive_reason': reason,
            'confidence_threshold': CONFIDENCE_THRESHOLD,
            'total_frames_analyzed': len(freq_assignments),
            'detection_source': source,
            'reason': reason,
        }

    # ── Directional swara extraction (ML-3) ───────────────────────────────────
    arohana_swaras = None
    avarohana_swaras = None
    directional_available = False

    if (features is not None
            and features.get('pcp') is not None
            and features.get('f0') is not None
            and features.get('voiced_flag') is not None):
        pcp = features['pcp']             # (23, n_frames)
        f0 = features['f0']               # ndarray
        voiced_flag = features['voiced_flag']  # ndarray bool
        n_voiced = int(voiced_flag.sum())
        if n_voiced >= 10:                # need enough voiced frames to be meaningful
            arohana_swaras, avarohana_swaras = _extract_directional_swaras(
                pcp, f0, voiced_flag
            )
            directional_available = bool(arohana_swaras or avarohana_swaras)
            logger.info(
                'Directional scoring: %d aro swaras, %d ava swaras, %d voiced frames',
                len(arohana_swaras or {}), len(avarohana_swaras or {}), n_voiced,
            )

    total_frames = len(freq_assignments)
    swara_names = SWARA_SHORT_NAMES

    matches = []
    for raga in RAGA_DATABASE:
        score, details = _score_raga(
            detected_swaras, raga,
            arohana_swaras=arohana_swaras,
            avarohana_swaras=avarohana_swaras,
        )
        if score >= min_confidence:
            matches.append({
                'raga_name': raga['name'],
                'tradition': raga['tradition'],
                'confidence': score,
                'details': details,
                'arohana': raga['arohana_bins'],
                'avarohana': raga['avarohana_bins'],
                'vadi': raga['vadi']['name'],
                'samvadi': raga['samvadi']['name'],
                'time': raga['time'],
                'mood': raga['mood'],
            })

    matches.sort(key=lambda m: m['confidence'], reverse=True)

    # ── Stage 4b: Pakad (phrase-level) tiebreak ───────────────────────────────
    if features is not None and matches:
        matches = apply_pakad_tiebreak(matches, features)

    # Build directional swara summary for the API response
    def _fmt(d):
        return [
            {'swara': swara_names[s], 'index': s, 'energy': round(e, 4)}
            for s, e in sorted(d.items()) if 0 <= s < len(swara_names)
        ] if d else []

    best_match = matches[0] if matches else None
    is_inconclusive = (
        best_match is None
        or best_match['confidence'] < CONFIDENCE_THRESHOLD
    )
    inconclusive_reason: str | None = None
    if best_match is None:
        inconclusive_reason = 'No raga met the minimum swara-overlap threshold.'
    elif best_match['confidence'] < CONFIDENCE_THRESHOLD:
        inconclusive_reason = (
            f"Best match '{best_match['raga_name']}' scored "
            f"{best_match['confidence'] * 100:.1f}% "
            f"(minimum required: {CONFIDENCE_THRESHOLD * 100:.0f}%). "
            "The recording may be ambiguous, too short, or use microtonal "
            "inflections that span multiple raga scales."
        )
        logger.info(
            'Raga detection inconclusive: best=%s confidence=%.4f threshold=%.2f',
            best_match['raga_name'], best_match['confidence'], CONFIDENCE_THRESHOLD,
        )

    return {
        'detected_swaras': [
            {'swara': swara_names[s] if s < len(swara_names) else str(s),
             'index': s, 'weight': round(float(w), 4)}
            for s, w in sorted(detected_swaras.items())
            if s < len(swara_names)
        ],
        'arohana_swaras': _fmt(arohana_swaras),
        'avarohana_swaras': _fmt(avarohana_swaras),
        'directional_scoring': directional_available,
        'matches': matches[:5],
        'best_match': best_match,
        'is_inconclusive': is_inconclusive,
        'inconclusive_reason': inconclusive_reason,
        'confidence_threshold': CONFIDENCE_THRESHOLD,
        'total_frames_analyzed': total_frames,
        'detection_source': source,
    }