import logging
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

SWARA_MAP = {
    'Sa': 0, 'Re1': 1, 'Re2': 2, 'Ga1': 3, 'Ga2': 4, 'Ga3': 5,
    'Ma1': 6, 'Ma2': 7, 'Ma3': 8, 'Tivra Ma': 9, 'Pa': 10,
    'Dha1': 11, 'Dha2': 12, 'Ni1': 13, 'Ni2': 14, 'Ni3': 15,
}

RAGA_DATABASE = [
    {
        'name': 'Yaman',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 9, 10, 12, 14],
        'arohana': [0, 2, 4, 9, 10, 12, 14],
        'avarohana': [14, 12, 10, 9, 4, 2, 0],
        'vadi': 4, 'samvadi': 14,
        'time': 'Evening (9 PM - Midnight)',
        'mood': 'Devotional, serene, romantic',
    },
    {
        'name': 'Bilawal',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 10, 12, 14],
        'arohana': [0, 2, 4, 6, 10, 12, 14],
        'avarohana': [14, 12, 10, 6, 4, 2, 0],
        'vadi': 0, 'samvadi': 6,
        'time': 'Morning',
        'mood': 'Bright, joyful',
    },
    {
        'name': 'Bhupali',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 10, 12],
        'arohana': [0, 2, 4, 10, 12, 0],
        'avarohana': [0, 12, 10, 4, 2, 0],
        'vadi': 4, 'samvadi': 0,
        'time': 'First prahar of night',
        'mood': 'Devotional, contemplative',
    },
    {
        'name': 'Bhairav',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 4, 6, 10, 11, 13],
        'arohana': [0, 1, 4, 6, 10, 11, 13, 0],
        'avarohana': [0, 13, 11, 10, 6, 4, 1, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Early morning',
        'mood': 'Solemn, devotional',
    },
    {
        'name': 'Malkauns',
        'tradition': 'Hindustani',
        'swaras': [0, 3, 6, 8, 11],
        'arohana': [0, 3, 6, 8, 11, 0],
        'avarohana': [0, 11, 8, 6, 3, 0],
        'vadi': 6, 'samvadi': 0,
        'time': 'Midnight',
        'mood': 'Mystical, meditative',
    },
    {
        'name': 'Darbari Kanada',
        'tradition': 'Hindustani',
        'swaras': [0, 3, 5, 6, 10, 11, 13],
        'arohana': [0, 3, 5, 6, 10, 11, 13, 0],
        'avarohana': [0, 13, 11, 10, 6, 5, 3, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Late night',
        'mood': 'Deep, dignified',
    },
    {
        'name': 'Khamaj',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 10, 12, 13],
        'arohana': [0, 2, 4, 6, 10, 12, 13, 0],
        'avarohana': [0, 13, 12, 10, 6, 4, 2, 0],
        'vadi': 6, 'samvadi': 13,
        'time': 'Late evening',
        'mood': 'Light, romantic',
    },
    {
        'name': 'Kafi',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 3, 6, 10, 12, 13],
        'arohana': [0, 2, 3, 6, 10, 12, 13, 0],
        'avarohana': [0, 13, 12, 10, 6, 3, 2, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Evening',
        'mood': 'Light, lyrical',
    },
    {
        'name': 'Asavari',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 3, 6, 10, 11, 13],
        'arohana': [0, 2, 3, 6, 10, 11, 13, 0],
        'avarohana': [0, 13, 11, 10, 6, 3, 2, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Late morning',
        'mood': 'Devotional, plaintive',
    },
    {
        'name': 'Poorvi',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 4, 6, 10, 11, 14],
        'arohana': [0, 1, 4, 6, 10, 11, 14, 0],
        'avarohana': [0, 14, 11, 10, 6, 4, 1, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Late evening',
        'mood': 'Serious, dignified',
    },
    {
        'name': 'Todi',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 3, 6, 8, 11, 13],
        'arohana': [0, 1, 3, 6, 8, 11, 13, 0],
        'avarohana': [0, 13, 11, 8, 6, 3, 1, 0],
        'vadi': 8, 'samvadi': 1,
        'time': 'Morning',
        'mood': 'Deep, meditative',
    },
    {
        'name': 'Puriya',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 4, 6, 10, 11, 14],
        'arohana': [0, 1, 4, 6, 10, 11, 14, 0],
        'avarohana': [14, 11, 10, 6, 4, 1, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Sunset',
        'mood': 'Devotional, yearning',
    },
    {
        'name': 'Marwa',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 4, 6, 10, 11, 14],
        'arohana': [0, 1, 4, 6, 10, 11, 14, 0],
        'avarohana': [0, 14, 11, 10, 6, 4, 1, 0],
        'vadi': 4, 'samvadi': 11,
        'time': 'Sunset',
        'mood': 'Restless, expectant',
    },
    {
        'name': 'Bhairavi',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 3, 6, 10, 11, 13],
        'arohana': [0, 1, 3, 6, 10, 11, 13, 0],
        'avarohana': [0, 13, 11, 10, 6, 3, 1, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Morning',
        'mood': 'Devotional, tender',
    },
    {
        'name': 'Kedar',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 6, 8, 10, 12, 14],
        'arohana': [0, 2, 6, 8, 10, 12, 14, 0],
        'avarohana': [0, 14, 12, 10, 8, 6, 2, 0],
        'vadi': 10, 'samvadi': 6,
        'time': 'Late evening',
        'mood': 'Devotional, yearning',
    },
    {
        'name': 'Megh',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 10, 12],
        'arohana': [0, 2, 4, 6, 10, 12, 0],
        'avarohana': [0, 12, 10, 6, 4, 2, 0],
        'vadi': 6, 'samvadi': 0,
        'time': 'Monsoon season',
        'mood': 'Majestic, rain-bringing',
    },
    {
        'name': 'Jhinjhoti',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 10, 12, 14],
        'arohana': [0, 2, 4, 6, 10, 12, 14, 0],
        'avarohana': [14, 12, 10, 6, 4, 2, 0],
        'vadi': 4, 'samvadi': 12,
        'time': 'Late night',
        'mood': 'Romantic, pleasant',
    },
    {
        'name': 'Rageshree',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 10, 11, 14],
        'arohana': [0, 2, 4, 6, 10, 11, 14, 0],
        'avarohana': [0, 14, 11, 10, 6, 4, 2, 0],
        'vadi': 4, 'samvadi': 11,
        'time': 'Late night',
        'mood': 'Passionate, intense',
    },
    {
        'name': 'Bihag',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 10, 14],
        'arohana': [0, 2, 4, 6, 10, 14, 0],
        'avarohana': [0, 14, 10, 6, 4, 2, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Night',
        'mood': 'Devotional, tender',
    },
    {
        'name': 'Sindhi Bhairavi',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 2, 3, 4, 6, 10, 11, 12, 13, 14, 15],
        'arohana': [0, 1, 2, 3, 4, 6, 10, 11, 12, 13, 14, 15, 0],
        'avarohana': [0, 15, 14, 13, 12, 11, 10, 6, 4, 3, 2, 1, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Any time',
        'mood': 'Devotional, pathos',
    },
    {
        'name': 'Shankarabharanam',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 6, 10, 12, 14],
        'arohana': [0, 2, 4, 6, 10, 12, 14, 0],
        'avarohana': [0, 14, 12, 10, 6, 4, 2, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Morning',
        'mood': 'Grand, auspicious',
    },
    {
        'name': 'Kharaharapriya',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 3, 6, 10, 12, 13],
        'arohana': [0, 2, 3, 6, 10, 12, 13, 0],
        'avarohana': [0, 13, 12, 10, 6, 3, 2, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Any time',
        'mood': 'Expressive, deeply emotional',
    },
    {
        'name': 'Mayamalavagowla',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 4, 6, 10, 11, 13],
        'arohana': [0, 1, 4, 6, 10, 11, 13, 0],
        'avarohana': [0, 13, 11, 10, 6, 4, 1, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Early morning',
        'mood': 'Peaceful, meditative',
    },
    {
        'name': 'Sri Raga',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 4, 6, 8, 11, 13],
        'arohana': [0, 1, 4, 6, 8, 11, 13, 0],
        'avarohana': [0, 13, 11, 8, 6, 4, 1, 0],
        'vadi': 6, 'samvadi': 13,
        'time': 'Evening',
        'mood': 'Devotional, majestic',
    },
    {
        'name': 'Kalyani',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 7, 10, 12, 14],
        'arohana': [0, 2, 4, 7, 10, 12, 14, 0],
        'avarohana': [0, 14, 12, 10, 7, 4, 2, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Any time',
        'mood': 'Joyous, auspicious',
    },
    {
        'name': 'Todi (Carnatic)',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 3, 6, 8, 11, 13],
        'arohana': [0, 1, 3, 6, 8, 11, 13, 0],
        'avarohana': [0, 13, 11, 8, 6, 3, 1, 0],
        'vadi': 8, 'samvadi': 1,
        'time': 'Morning',
        'mood': 'Serene, contemplative',
    },
    {
        'name': 'Bhairavi (Carnatic)',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 3, 6, 10, 11, 13],
        'arohana': [0, 1, 3, 6, 10, 11, 13, 0],
        'avarohana': [0, 13, 11, 10, 6, 3, 1, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Any time',
        'mood': 'Devotion, pathos',
    },
    {
        'name': 'Kambhoji',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 6, 10, 12, 13],
        'arohana': [0, 2, 4, 6, 10, 12, 13, 0],
        'avarohana': [0, 13, 12, 10, 6, 4, 2, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Evening',
        'mood': 'Devotional, romantic',
    },
    {
        'name': 'Abhogi',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 3, 6, 10],
        'arohana': [0, 2, 3, 6, 10, 0],
        'avarohana': [0, 10, 6, 3, 2, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Any time',
        'mood': 'Introspective, tender',
    },
    {
        'name': 'Hamsadhwani',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 10, 14],
        'arohana': [0, 2, 4, 10, 14, 0],
        'avarohana': [0, 14, 10, 4, 2, 0],
        'vadi': 14, 'samvadi': 4,
        'time': 'Any time',
        'mood': 'Bright, auspicious',
    },
    {
        'name': 'Chakravakam',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 4, 6, 10, 12, 13],
        'arohana': [0, 1, 4, 6, 10, 12, 13, 0],
        'avarohana': [0, 13, 12, 10, 6, 4, 1, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Morning',
        'mood': 'Evocative, pathos',
    },
    {
        'name': 'Kapi',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 3, 6, 8, 11, 13],
        'arohana': [0, 2, 3, 6, 8, 11, 13, 0],
        'avarohana': [0, 13, 11, 8, 6, 3, 2, 0],
        'vadi': 6, 'samvadi': 13,
        'time': 'Evening',
        'mood': 'Devotional, pathos',
    },
    {
        'name': 'Latangi',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 4, 7, 10, 11, 14],
        'arohana': [0, 1, 4, 7, 10, 11, 14, 0],
        'avarohana': [0, 14, 11, 10, 7, 4, 1, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Morning',
        'mood': 'Grand, festive',
    },
    {
        'name': 'Mechakalyani',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 7, 10, 12, 14],
        'arohana': [0, 2, 4, 7, 10, 12, 14, 0],
        'avarohana': [0, 14, 12, 10, 7, 4, 2, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Night',
        'mood': 'Ethereal, deeply moving',
    },
    # ── 10 new ragas (ML-6) ───────────────────────────────────────────────────
    {
        'name': 'Durga',
        'tradition': 'Hindustani',
        # Sa Re2 Ma1 Pa Dha2  (pentatonic, no Ga or Ni)
        'swaras': [0, 2, 6, 10, 12],
        'arohana': [0, 2, 6, 10, 12, 0],
        'avarohana': [0, 12, 10, 6, 2, 0],
        'vadi': 10, 'samvadi': 2,
        'time': 'Late evening',
        'mood': 'Bright, devotional, joyous',
    },
    {
        'name': 'Shankara',
        'tradition': 'Hindustani',
        # Sa Ga2 Pa Ni2 (audav — omits Re and Ma)
        'swaras': [0, 4, 10, 14, 15],
        'arohana': [0, 4, 10, 14, 15, 0],
        'avarohana': [0, 15, 14, 10, 4, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Night',
        'mood': 'Heroic, devotional, majestic',
    },
    {
        'name': 'Charukeshi',
        'tradition': 'Hindustani',
        # Sa Re2 Ga2 Ma1 Pa Dha1 Ni1  (Bilawal + komal Dha & komal Ni)
        'swaras': [0, 2, 4, 6, 10, 11, 13],
        'arohana': [0, 2, 4, 6, 10, 11, 13, 0],
        'avarohana': [0, 13, 11, 10, 6, 4, 2, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Afternoon',
        'mood': 'Serious, dignified, melancholic',
    },
    {
        'name': 'Nata Bhairavi',
        'tradition': 'Hindustani',
        # Sa Re2 Ga1 Ma1 Pa Dha1 Ni1 — uses both komal Re (aroh) and shuddha Re (avaroh)
        'swaras': [0, 2, 3, 6, 10, 11, 13],
        'arohana': [0, 2, 3, 6, 10, 11, 13, 0],
        'avarohana': [0, 13, 11, 10, 6, 3, 2, 0],
        'vadi': 10, 'samvadi': 3,
        'time': 'Evening to midnight',
        'mood': 'Plaintive, romantic, yearning',
    },
    {
        'name': 'Mand',
        'tradition': 'Hindustani',
        # Sa Re2 Ga2 Ma1 Pa Dha2 Ni2 — folk-flavoured Rajasthani raga
        'swaras': [0, 2, 4, 6, 10, 12, 14],
        'arohana': [0, 2, 4, 6, 10, 12, 14, 0],
        'avarohana': [0, 14, 12, 10, 6, 4, 2, 0],
        'vadi': 10, 'samvadi': 4,
        'time': 'Night',
        'mood': 'Folk, festive, lyrical',
    },
    {
        'name': 'Madhyamavati',
        'tradition': 'Carnatic',
        # Sa Re2 Ma1 Pa Ni2 — pentatonic, very popular Carnatic raga
        'swaras': [0, 2, 6, 10, 14],
        'arohana': [0, 2, 6, 10, 14, 0],
        'avarohana': [0, 14, 10, 6, 2, 0],
        'vadi': 10, 'samvadi': 2,
        'time': 'Any time',
        'mood': 'Devotional, melodious, meditative',
    },
    {
        'name': 'Vasanta',
        'tradition': 'Carnatic',
        # Sa Re1 Ga3 Ma2 Pa Dha1 Ni3 — vakra prayogas in both directions
        'swaras': [0, 1, 5, 7, 10, 11, 15],
        'arohana': [0, 5, 1, 10, 7, 15, 11, 0],
        'avarohana': [0, 15, 11, 10, 7, 5, 1, 0],
        'vadi': 10, 'samvadi': 5,
        'time': 'Spring season, any time',
        'mood': 'Joyful, festive, celebratory',
    },
    {
        'name': 'Panthuvarali',
        'tradition': 'Carnatic',
        # Sa Re1 Ga3 Ma2 Pa Dha1 Ni3 — 51st melakarta (Kamavardhini)
        'swaras': [0, 1, 5, 7, 10, 11, 15],
        'arohana': [0, 1, 5, 7, 10, 11, 15, 0],
        'avarohana': [0, 15, 11, 10, 7, 5, 1, 0],
        'vadi': 7, 'samvadi': 1,
        'time': 'Any time',
        'mood': 'Serious, profound, intense',
    },
    {
        'name': 'Saveri',
        'tradition': 'Carnatic',
        # Sa Re1 Ma1 Pa Dha1 — pentatonic (Suddha Saveri without Ni)
        'swaras': [0, 1, 6, 10, 11],
        'arohana': [0, 1, 6, 10, 11, 0],
        'avarohana': [0, 11, 10, 6, 1, 0],
        'vadi': 10, 'samvadi': 1,
        'time': 'Morning',
        'mood': 'Serene, devotional, gentle',
    },
    {
        'name': 'Ritigowla',
        'tradition': 'Carnatic',
        # Sa Re1 Ga3 Ma1 Pa Dha1 Ni2 — vakra arohana, deeply emotive
        'swaras': [0, 1, 5, 6, 10, 11, 14],
        'arohana': [0, 1, 5, 6, 10, 11, 14, 0],
        'avarohana': [0, 14, 11, 10, 6, 5, 1, 0],
        'vadi': 10, 'samvadi': 5,
        'time': 'Any time',
        'mood': 'Devotional, tender, deeply moving',
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Pakad (characteristic phrase) database — Stage 4b
# ─────────────────────────────────────────────────────────────────────────────
# Each entry is a list of (n_frames, 22) idealised PCP keyframe sequences that
# represent the raga's pakad (signature melodic phrase).  DTW is used to
# search for the best-matching subsequence in the audio's PCP matrix.
#
# Shruti→PCP index (0-based, same as SWARA_MAP above):
#   0=Sa 1=Re1 2=Re2 3=Ga1 4=Ga2 5=Ga3 6=Ma1 7=Ma2 8=Ma3 9=TivraMa
#   10=Pa 11=Dha1 12=Dha2 13=Ni1 14=Ni2 15=Ni3
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
    # ── Ambiguous group 1: {0,2,4,6,10,12,14} ────────────────────────────────
    # Yaman:    N Re Ga — Ga Ma (tivra) Pa — characteristic ni-re-ga opening
    'Yaman': _pakad_template([
        [14],           # Ni2 (strong opening note)
        [2],            # Re2
        [4],            # Ga2
        [14, 2],        # Ni–Re oscillation
        [4, 9],         # Ga–TivraMa (the diagnostic interval)
        [10],           # Pa
    ]),

    # Bilawal:  Sa Re Ga Ma — Pa Dha — Ni Sa' — emphasis on Sa and Pa
    'Bilawal': _pakad_template([
        [0],            # Sa (strong start)
        [2, 4],         # Re–Ga
        [6],            # Ma1 (shuddha Ma)
        [10],           # Pa
        [12],           # Dha2
        [0],            # Sa (return — vakra)
    ]),

    # Jhinjhoti: Sa Re Ga Ma Pa — Ni Dha Pa — Ga Re Sa — komal Ni in descent
    'Jhinjhoti': _pakad_template([
        [0, 2],         # Sa–Re
        [4],            # Ga2
        [10],           # Pa
        [13],           # Ni1 (komal — diagnostic!)
        [12],           # Dha2
        [10],           # Pa
        [4, 2, 0],      # Ga–Re–Sa
    ]),

    # Shankarabharanam: Pa Ma Ga Re Sa — Ni Dha Pa (Carnatic major scale, starts Pa)
    'Shankarabharanam': _pakad_template([
        [10],           # Pa (characteristic opening from Pa)
        [6],            # Ma1
        [4],            # Ga2
        [2],            # Re2
        [0],            # Sa
        [14],           # Ni2
        [12],           # Dha2
        [10],           # Pa
    ]),

    # Mand:     Sa Ga Pa Dha — Ma Ga Re Sa — Rajasthani folk curve
    'Mand': _pakad_template([
        [0],            # Sa
        [4],            # Ga2
        [10],           # Pa
        [12],           # Dha2
        [6, 4, 2, 0],   # Ma–Ga–Re–Sa (folk descending)
    ]),

    # ── Ambiguous group 2: Bhairav region {0,1,4,6,10,11,13} ─────────────────
    # Bhairav:        Sa Re1 — Ga Pa — Dha1 Ni1 Sa'
    'Bhairav': _pakad_template([
        [0],            # Sa
        [1],            # Re1 (komal)
        [4, 6],         # Ga–Ma
        [10],           # Pa
        [11],           # Dha1 (komal)
        [13],           # Ni1 (komal)
        [0],            # Sa'
    ]),

    # Mayamalavagowla:  Sa Re1 Ga2 — Pa Dha1 Ni1 — distinctive jump Re1→Ga2
    'Mayamalavagowla': _pakad_template([
        [0],            # Sa
        [1],            # Re1
        [4],            # Ga2 (shuddha — jumps over Ga1)
        [10],           # Pa
        [11],           # Dha1 (komal)
        [13, 0],        # Ni1→Sa
    ]),

    # ── Ambiguous group 3: Kafi/Khamaj region ────────────────────────────────
    # Kafi:   Sa Re Ga1 Ma Pa Dha — komal Ga and komal Ni
    'Kafi': _pakad_template([
        [0],            # Sa
        [2],            # Re2
        [3],            # Ga1 (komal — diagnostic)
        [6, 10],        # Ma–Pa
        [12],           # Dha2
        [13],           # Ni1 (komal)
        [0],            # Sa
    ]),

    # Khamaj: Pa Ni Dha Pa — Ga Ma Pa — Ni in descent only
    'Khamaj': _pakad_template([
        [10],           # Pa (characteristic start)
        [13],           # Ni1 (komal in descent)
        [12],           # Dha2
        [10],           # Pa
        [4, 6, 10],     # Ga–Ma–Pa ascending
    ]),

    # ── Ambiguous group 4: Todi variants ─────────────────────────────────────
    # Todi (Hindustani): Re1 Ga1 Ma2 — Pa Dha1 Ni1 — all komal + tivra Ma
    'Todi': _pakad_template([
        [1],            # Re1 (komal)
        [3],            # Ga1 (komal)
        [8],            # Ma3/Tivra region
        [10],           # Pa (avoided in avaroh)
        [11],           # Dha1
        [13, 1, 0],     # Ni1–Re1–Sa
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
    pcp = features.get('pcp')  # (22, n_frames)
    if pcp is None or pcp.shape[1] < 5:
        return matches

    n_frames = pcp.shape[1]
    pcp_T = pcp.T.astype(np.float32)  # (n_frames, 22) — row=frame, col=shruti

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
            window = pcp_T[start: start + T_tpl]   # (T_tpl, 22)
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
    """Legacy path: build swara hits from per-frame string assignments."""
    swara_hits = Counter()
    for assignment in freq_assignments:
        if assignment is None:
            continue
        for shruti_name, swara_idx in SWARA_MAP.items():
            if shruti_name in assignment:
                swara_hits[swara_idx] += 1
                break
    return swara_hits


def _extract_detected_swaras_from_pcp(mean_pcp, energy_threshold=0.02):
    """
    Build a swara energy map from the 22-element mean PCP vector.

    mean_pcp : list or array of 22 floats in [0, 1]
        Recording-level Shruti energy fingerprint from compute_pcp().
    energy_threshold : float
        Shrutis with mean energy below this fraction of the max are ignored.

    Returns a dict {swara_index: energy_float} for the first 15 Shrutis
    (indices 0-14) that map to the classical SWARA_MAP.
    """
    import numpy as np
    pcp = np.asarray(mean_pcp, dtype=np.float64)
    max_energy = pcp.max()
    if max_energy == 0:
        return {}

    # Build a fast lookup: short swara name -> PCP index
    # SHRUTI_NAMES entries look like 'Shruti 1 (Sa)', 'Shruti 2 (Re1)', etc.
    shruti_idx_map = {}
    for idx, full_name in enumerate(SHRUTI_NAMES):
        for short in SWARA_MAP:
            if short in full_name and short not in shruti_idx_map:
                shruti_idx_map[short] = idx

    swara_energy = {}
    for shruti_name, swara_idx in SWARA_MAP.items():
        if shruti_name not in shruti_idx_map:
            continue
        energy = float(pcp[shruti_idx_map[shruti_name]])
        if energy >= energy_threshold * max_energy:
            swara_energy[swara_idx] = swara_energy.get(swara_idx, 0.0) + energy

    return swara_energy


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
    bleed that falsely lights up 15 swaras, and the duration gate removes
    transient vocal glides that never settle on a sustained note.

    Parameters
    ----------
    pcp : ndarray (22, n_frames) — per-frame Shruti energies
    voiced_flag : ndarray (n_frames,) bool — True for voiced frames
    f0 : ndarray (n_frames,) optional — pYIN fundamental frequency (NaN unvoiced)
    presence_threshold : float — min fraction of voiced frames a swara must be
                                 the dominant pitch class for to count as present

    Returns
    -------
    dict {swara_index: salience} for the classical 15 swaras (PCP bins 0-14)
    whose occupancy is >= presence_threshold.  The value is the occupancy
    fraction, used as the swara's salience weight in scoring.
    """
    import numpy as np
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
    # unavailable or out of range.  Counting only voiced frames (never the
    # drone-heavy unvoiced frames) keeps the tanpura bleed out while retaining
    # the ornamented notes that never settle on a single F0.
    shruti_idx = _nearest_shruti_from_f0
    counts = np.zeros(pcp.shape[0], dtype=np.int64)
    for i in range(n_frames):
        if not voiced[i]:
            continue
        assigned = None
        if f0_arr is not None and i < len(f0_arr) and not np.isnan(f0_arr[i]):
            assigned = shruti_idx(f0_arr[i])
        if assigned is None:
            assigned = int(pcp[:, i].argmax())
        if 0 <= assigned < pcp.shape[0]:
            counts[assigned] += 1

    occupancy = counts / total_voiced
    return {
        int(i): float(occupancy[i])
        for i in range(min(16, pcp.shape[0]))
        if occupancy[i] >= presence_threshold
    }


def _extract_directional_swaras(pcp, f0, voiced_flag,
                                energy_threshold=0.02,
                                smoothing_frames=3):
    """
    Split PCP energy into arohana (rising F0) and avarohana (falling F0) dicts.

    Uses the frame-by-frame F0 gradient to classify each voiced frame as
    rising or falling, then accumulates PCP energy into two separate
    {swara_idx: energy} maps.

    Parameters
    ----------
    pcp : ndarray (22, n_frames)
    f0  : ndarray (n_frames,) — NaN for unvoiced
    voiced_flag : ndarray bool (n_frames,)
    energy_threshold : float — min fraction of per-direction max to count
    smoothing_frames : int — frames to smooth gradient over (reduces jitter)

    Returns
    -------
    arohana_swaras   : dict {swara_idx: energy}
    avarohana_swaras : dict {swara_idx: energy}
    """
    n_frames = pcp.shape[1]
    align = min(len(f0), n_frames)
    f0_a = np.array(f0[:align], dtype=np.float64)
    vf_a = np.array(voiced_flag[:align], dtype=bool)

    # Smooth F0 (replace NaN with 0 for gradient, then mask)
    f0_filled = np.where(np.isnan(f0_a), 0.0, f0_a)
    # Gradient via centered diff, smoothed over a short window
    if align > 2 * smoothing_frames:
        kernel = np.ones(smoothing_frames) / smoothing_frames
        f0_smooth = np.convolve(f0_filled, kernel, mode='same')
    else:
        f0_smooth = f0_filled
    gradient = np.gradient(f0_smooth)

    # Build a lookup: shruti_name (short) → shruti PCP index (0-21)
    shruti_idx_map = {}
    for idx, full_name in enumerate(SHRUTI_NAMES):
        for short in SWARA_MAP:
            if short in full_name and short not in shruti_idx_map:
                shruti_idx_map[short] = idx

    aro_energy = {}    # rising (arohana) frames
    ava_energy = {}    # falling (avarohana) frames

    for frame_idx in range(align):
        if not vf_a[frame_idx]:
            continue
        frame_pcp = pcp[:, frame_idx]  # (22,)
        bucket = aro_energy if gradient[frame_idx] >= 0 else ava_energy
        for short, swara_idx in SWARA_MAP.items():
            if short not in shruti_idx_map:
                continue
            e = float(frame_pcp[shruti_idx_map[short]])
            if e > 0:
                bucket[swara_idx] = bucket.get(swara_idx, 0.0) + e

    # Apply energy threshold per direction
    def _threshold(d):
        if not d:
            return {}
        mx = max(d.values())
        return {k: v for k, v in d.items() if v >= energy_threshold * mx}

    return _threshold(aro_energy), _threshold(ava_energy)


def _score_raga(detected_swaras, raga,
               arohana_swaras=None, avarohana_swaras=None,
               total_frames=None):
    """
    Score a raga against detected swara energies with directional weighting.

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
    """
    if not detected_swaras:
        return 0.0, {}

    raga_swaras = set(raga['swaras'])
    detected_set = set(detected_swaras.keys())
    intersection = raga_swaras & detected_set
    union = raga_swaras | detected_set
    if not union:
        return 0.0, {}

    jaccard = len(intersection) / len(union)

    # ── Extraneous swara penalty ──────────────────────────────────────────────
    # Notes present in the audio but *completely forbidden* in the raga (i.e.
    # not part of its scale at all) undermine the match: a real Bhimpalasi
    # alap never sits on an out-of-scale pitch for long.  The more of the
    # detected set lies outside the raga's scale, the more we subtract.
    extraneous = detected_set - raga_swaras
    extraneous_penalty = 0.0
    if detected_set:
        extraneous_penalty = round(
            0.20 * (len(extraneous) / len(detected_set)), 4
        )

    vadi = raga['vadi']
    samvadi = raga['samvadi']
    total_weight = sum(detected_swaras.values()) or 1.0

    vadi_bonus = 0.0
    if vadi in detected_swaras:
        vadi_bonus = 0.10 * min(detected_swaras[vadi] / (total_weight * 0.1), 1.0)

    samvadi_bonus = 0.0
    if samvadi in detected_swaras:
        samvadi_bonus = 0.05 * min(detected_swaras[samvadi] / (total_weight * 0.05), 1.0)

    # ── Directional coverage ──────────────────────────────────────────────────
    # arohana: ordered list of unique swara indices (Sa=0 direction, ascending)
    raga_aro_set = set(raga['arohana'])
    raga_ava_set = set(raga['avarohana'])

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
        'vadi_detected': vadi in detected_swaras,
        'samvadi_detected': samvadi in detected_swaras,
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
    # pYIN marks broadband-noise frames as voiced and their PCP argmax lands on
    # arbitrary Shruti bins, so silent clips can be scored as a confident raga.
    # Reject recording-level RMS at or below room-noise floor first.
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
    # tanpura drone bleed / slides that falsely light up 15 swaras).  Fall back
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
        pcp = features['pcp']             # (22, n_frames)
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
    swara_names = {
        0: 'Sa', 1: 'Re1', 2: 'Re2', 3: 'Ga1', 4: 'Ga2', 5: 'Ga3',
        6: 'Ma1', 7: 'Ma2', 8: 'Ma3', 9: 'Tivra Ma', 10: 'Pa',
        11: 'Dha1', 12: 'Dha2', 13: 'Ni1', 14: 'Ni2', 15: 'Ni3',
    }

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
                'arohana': raga['arohana'],
                'avarohana': raga['avarohana'],
                'vadi': swara_names.get(raga['vadi'], str(raga['vadi'])),
                'samvadi': swara_names.get(raga['samvadi'], str(raga['samvadi'])),
                'time': raga['time'],
                'mood': raga['mood'],
            })

    matches.sort(key=lambda m: m['confidence'], reverse=True)

    # ── Stage 4b: Pakad (phrase-level) tiebreak ───────────────────────────────
    # When the top candidates are within 5% of each other, perform a sliding-
    # window DTW search against the Pakad templates to differentiate ragas that
    # share the same swara set (e.g. Yaman vs Bilawal vs Jhinjhoti vs Mand).
    if features is not None and matches:
        matches = apply_pakad_tiebreak(matches, features)

    # Build directional swara summary for the API response
    def _fmt(d):
        return [
            {'swara': swara_names.get(s, str(s)), 'index': s, 'energy': round(e, 4)}
            for s, e in sorted(d.items())
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
            {'swara': swara_names.get(s, str(s)), 'index': s,
             'weight': round(float(w), 4)}
            for s, w in sorted(detected_swaras.items())
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
