from collections import Counter
from .shruti_mapping import SHRUTI_NAMES

SWARA_MAP = {
    'Sa': 0, 'Re1': 1, 'Re2': 2, 'Ga1': 3, 'Ga2': 4, 'Ga3': 5,
    'Ma1': 6, 'Ma2': 7, 'Ma3': 8, 'Pa': 9, 'Dha1': 10, 'Dha2': 11,
    'Ni1': 12, 'Ni2': 13, 'Ni3': 14,
}

RAGA_DATABASE = [
    {
        'name': 'Yaman',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 9, 11, 13],
        'arohana': [0, 2, 4, 6, 9, 11, 13],
        'avarohana': [13, 11, 9, 6, 4, 2, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Evening (9 PM - Midnight)',
        'mood': 'Devotional, serene, romantic',
    },
    {
        'name': 'Bilawal',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 9, 11, 13],
        'arohana': [0, 2, 4, 6, 9, 11, 13],
        'avarohana': [13, 11, 9, 6, 4, 2, 0],
        'vadi': 0, 'samvadi': 6,
        'time': 'Morning',
        'mood': 'Bright, joyful',
    },
    {
        'name': 'Bhupali',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 9, 11],
        'arohana': [0, 2, 4, 9, 11, 0],
        'avarohana': [0, 11, 9, 4, 2, 0],
        'vadi': 4, 'samvadi': 0,
        'time': 'First prahar of night',
        'mood': 'Devotional, contemplative',
    },
    {
        'name': 'Bhairav',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 4, 6, 9, 10, 12],
        'arohana': [0, 1, 4, 6, 9, 10, 12, 0],
        'avarohana': [0, 12, 10, 9, 6, 4, 1, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Early morning',
        'mood': 'Solemn, devotional',
    },
    {
        'name': 'Malkauns',
        'tradition': 'Hindustani',
        'swaras': [0, 3, 6, 8, 10],
        'arohana': [0, 3, 6, 8, 10, 0],
        'avarohana': [0, 10, 8, 6, 3, 0],
        'vadi': 6, 'samvadi': 0,
        'time': 'Midnight',
        'mood': 'Mystical, meditative',
    },
    {
        'name': 'Darbari Kanada',
        'tradition': 'Hindustani',
        'swaras': [0, 3, 5, 6, 9, 10, 12],
        'arohana': [0, 3, 5, 6, 9, 10, 12, 0],
        'avarohana': [0, 12, 10, 9, 6, 5, 3, 0],
        'vadi': 9, 'samvadi': 3,
        'time': 'Late night',
        'mood': 'Deep, dignified',
    },
    {
        'name': 'Khamaj',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 9, 11, 12],
        'arohana': [0, 2, 4, 6, 9, 11, 12, 0],
        'avarohana': [0, 12, 11, 9, 6, 4, 2, 0],
        'vadi': 6, 'samvadi': 12,
        'time': 'Late evening',
        'mood': 'Light, romantic',
    },
    {
        'name': 'Kafi',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 3, 6, 9, 11, 12],
        'arohana': [0, 2, 3, 6, 9, 11, 12, 0],
        'avarohana': [0, 12, 11, 9, 6, 3, 2, 0],
        'vadi': 9, 'samvadi': 3,
        'time': 'Evening',
        'mood': 'Light, lyrical',
    },
    {
        'name': 'Asavari',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 3, 6, 9, 10, 12],
        'arohana': [0, 2, 3, 6, 9, 10, 12, 0],
        'avarohana': [0, 12, 10, 9, 6, 3, 2, 0],
        'vadi': 9, 'samvadi': 3,
        'time': 'Late morning',
        'mood': 'Devotional, plaintive',
    },
    {
        'name': 'Poorvi',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 4, 6, 9, 10, 13],
        'arohana': [0, 1, 4, 6, 9, 10, 13, 0],
        'avarohana': [0, 13, 10, 9, 6, 4, 1, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Late evening',
        'mood': 'Serious, dignified',
    },
    {
        'name': 'Todi',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 3, 6, 8, 10, 12],
        'arohana': [0, 1, 3, 6, 8, 10, 12, 0],
        'avarohana': [0, 12, 10, 8, 6, 3, 1, 0],
        'vadi': 8, 'samvadi': 1,
        'time': 'Morning',
        'mood': 'Deep, meditative',
    },
    {
        'name': 'Puriya',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 4, 6, 9, 10, 13],
        'arohana': [0, 1, 4, 6, 9, 10, 13, 0],
        'avarohana': [13, 10, 9, 6, 4, 1, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Sunset',
        'mood': 'Devotional, yearning',
    },
    {
        'name': 'Marwa',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 4, 6, 9, 10, 13],
        'arohana': [0, 1, 4, 6, 9, 10, 13, 0],
        'avarohana': [0, 13, 10, 9, 6, 4, 1, 0],
        'vadi': 4, 'samvadi': 10,
        'time': 'Sunset',
        'mood': 'Restless, expectant',
    },
    {
        'name': 'Bhairavi',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 3, 6, 9, 10, 12],
        'arohana': [0, 1, 3, 6, 9, 10, 12, 0],
        'avarohana': [0, 12, 10, 9, 6, 3, 1, 0],
        'vadi': 9, 'samvadi': 3,
        'time': 'Morning',
        'mood': 'Devotional, tender',
    },
    {
        'name': 'Kedar',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 6, 8, 9, 11, 13],
        'arohana': [0, 2, 6, 8, 9, 11, 13, 0],
        'avarohana': [0, 13, 11, 9, 8, 6, 2, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Late evening',
        'mood': 'Devotional, yearning',
    },
    {
        'name': 'Megh',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 9, 11],
        'arohana': [0, 2, 4, 6, 9, 11, 0],
        'avarohana': [0, 11, 9, 6, 4, 2, 0],
        'vadi': 6, 'samvadi': 0,
        'time': 'Monsoon season',
        'mood': 'Majestic, rain-bringing',
    },
    {
        'name': 'Jhinjhoti',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 9, 11, 13],
        'arohana': [0, 2, 4, 6, 9, 11, 13, 0],
        'avarohana': [13, 11, 9, 6, 4, 2, 0],
        'vadi': 4, 'samvadi': 11,
        'time': 'Late night',
        'mood': 'Romantic, pleasant',
    },
    {
        'name': 'Rageshree',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 9, 10, 13],
        'arohana': [0, 2, 4, 6, 9, 10, 13, 0],
        'avarohana': [0, 13, 10, 9, 6, 4, 2, 0],
        'vadi': 4, 'samvadi': 10,
        'time': 'Late night',
        'mood': 'Passionate, intense',
    },
    {
        'name': 'Bihag',
        'tradition': 'Hindustani',
        'swaras': [0, 2, 4, 6, 9, 13],
        'arohana': [0, 2, 4, 6, 9, 13, 0],
        'avarohana': [0, 13, 9, 6, 4, 2, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Night',
        'mood': 'Devotional, tender',
    },
    {
        'name': 'Sindhi Bhairavi',
        'tradition': 'Hindustani',
        'swaras': [0, 1, 2, 3, 4, 6, 9, 10, 11, 12, 13, 14],
        'arohana': [0, 1, 2, 3, 4, 6, 9, 10, 11, 12, 13, 14, 0],
        'avarohana': [0, 14, 13, 12, 11, 10, 9, 6, 4, 3, 2, 1, 0],
        'vadi': 9, 'samvadi': 3,
        'time': 'Any time',
        'mood': 'Devotional, pathos',
    },
    {
        'name': 'Shankarabharanam',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 6, 9, 11, 13],
        'arohana': [0, 2, 4, 6, 9, 11, 13, 0],
        'avarohana': [0, 13, 11, 9, 6, 4, 2, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Morning',
        'mood': 'Grand, auspicious',
    },
    {
        'name': 'Kharaharapriya',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 3, 6, 9, 11, 12],
        'arohana': [0, 2, 3, 6, 9, 11, 12, 0],
        'avarohana': [0, 12, 11, 9, 6, 3, 2, 0],
        'vadi': 9, 'samvadi': 3,
        'time': 'Any time',
        'mood': 'Expressive, deeply emotional',
    },
    {
        'name': 'Mayamalavagowla',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 4, 6, 9, 10, 12],
        'arohana': [0, 1, 4, 6, 9, 10, 12, 0],
        'avarohana': [0, 12, 10, 9, 6, 4, 1, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Early morning',
        'mood': 'Peaceful, meditative',
    },
    {
        'name': 'Sri Raga',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 4, 6, 8, 10, 12],
        'arohana': [0, 1, 4, 6, 8, 10, 12, 0],
        'avarohana': [0, 12, 10, 8, 6, 4, 1, 0],
        'vadi': 6, 'samvadi': 12,
        'time': 'Evening',
        'mood': 'Devotional, majestic',
    },
    {
        'name': 'Kalyani',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 7, 9, 11, 13],
        'arohana': [0, 2, 4, 7, 9, 11, 13, 0],
        'avarohana': [0, 13, 11, 9, 7, 4, 2, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Any time',
        'mood': 'Joyous, auspicious',
    },
    {
        'name': 'Todi (Carnatic)',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 3, 6, 8, 10, 12],
        'arohana': [0, 1, 3, 6, 8, 10, 12, 0],
        'avarohana': [0, 12, 10, 8, 6, 3, 1, 0],
        'vadi': 8, 'samvadi': 1,
        'time': 'Morning',
        'mood': 'Serene, contemplative',
    },
    {
        'name': 'Bhairavi (Carnatic)',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 3, 6, 9, 10, 12],
        'arohana': [0, 1, 3, 6, 9, 10, 12, 0],
        'avarohana': [0, 12, 10, 9, 6, 3, 1, 0],
        'vadi': 9, 'samvadi': 3,
        'time': 'Any time',
        'mood': 'Devotion, pathos',
    },
    {
        'name': 'Kambhoji',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 6, 9, 11, 12],
        'arohana': [0, 2, 4, 6, 9, 11, 12, 0],
        'avarohana': [0, 12, 11, 9, 6, 4, 2, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Evening',
        'mood': 'Devotional, romantic',
    },
    {
        'name': 'Abhogi',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 3, 6, 9],
        'arohana': [0, 2, 3, 6, 9, 0],
        'avarohana': [0, 9, 6, 3, 2, 0],
        'vadi': 9, 'samvadi': 3,
        'time': 'Any time',
        'mood': 'Introspective, tender',
    },
    {
        'name': 'Hamsadhwani',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 9, 13],
        'arohana': [0, 2, 4, 9, 13, 0],
        'avarohana': [0, 13, 9, 4, 2, 0],
        'vadi': 13, 'samvadi': 4,
        'time': 'Any time',
        'mood': 'Bright, auspicious',
    },
    {
        'name': 'Chakravakam',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 4, 6, 9, 11, 12],
        'arohana': [0, 1, 4, 6, 9, 11, 12, 0],
        'avarohana': [0, 12, 11, 9, 6, 4, 1, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Morning',
        'mood': 'Evocative, pathos',
    },
    {
        'name': 'Kapi',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 3, 6, 8, 10, 12],
        'arohana': [0, 2, 3, 6, 8, 10, 12, 0],
        'avarohana': [0, 12, 10, 8, 6, 3, 2, 0],
        'vadi': 6, 'samvadi': 12,
        'time': 'Evening',
        'mood': 'Devotional, pathos',
    },
    {
        'name': 'Latangi',
        'tradition': 'Carnatic',
        'swaras': [0, 1, 4, 7, 9, 10, 13],
        'arohana': [0, 1, 4, 7, 9, 10, 13, 0],
        'avarohana': [0, 13, 10, 9, 7, 4, 1, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Morning',
        'mood': 'Grand, festive',
    },
    {
        'name': 'Mechakalyani',
        'tradition': 'Carnatic',
        'swaras': [0, 2, 4, 7, 9, 11, 13],
        'arohana': [0, 2, 4, 7, 9, 11, 13, 0],
        'avarohana': [0, 13, 11, 9, 7, 4, 2, 0],
        'vadi': 9, 'samvadi': 4,
        'time': 'Night',
        'mood': 'Ethereal, deeply moving',
    },
]


def _extract_detected_swaras(freq_assignments):
    swara_hits = Counter()
    for assignment in freq_assignments:
        if assignment is None:
            continue
        for shruti_name, swara_idx in SWARA_MAP.items():
            if shruti_name in assignment:
                swara_hits[swara_idx] += 1
                break
    return swara_hits


def _score_raga(detected_swaras, raga, total_frames):
    if not detected_swaras:
        return 0.0, {}

    raga_swaras = set(raga['swaras'])
    detected_set = set(detected_swaras.keys())

    intersection = raga_swaras & detected_set
    union = raga_swaras | detected_set

    if not union:
        return 0.0, {}

    jaccard = len(intersection) / len(union)

    vadi = raga['vadi']
    samvadi = raga['samvadi']

    vadi_weight = 0.0
    if vadi in detected_swaras:
        vadi_hits = detected_swaras[vadi]
        total_hits = sum(detected_swaras.values())
        vadi_weight = 0.3 * min(vadi_hits / max(total_hits * 0.1, 1), 1.0)

    samvadi_weight = 0.0
    if samvadi in detected_swaras:
        samvadi_hits = detected_swaras[samvadi]
        total_hits = sum(detected_swaras.values())
        samvadi_weight = 0.15 * min(samvadi_hits / max(total_hits * 0.05, 1), 1.0)

    coverage = len(intersection) / len(raga_swaras) if raga_swaras else 0.0

    score = min(0.45 * jaccard + 0.25 * coverage + vadi_weight + samvadi_weight, 1.0)

    return round(score, 4), {
        'matched_swaras': sorted(intersection),
        'jaccard_similarity': round(jaccard, 4),
        'coverage': round(coverage, 4),
        'vadi_detected': vadi in detected_swaras,
        'samvadi_detected': samvadi in detected_swaras,
    }


def detect_raga(clustering_results, min_confidence=0.25):
    freq_assignments = clustering_results.get('freq_assignments', [])
    detected_swaras = _extract_detected_swaras(freq_assignments)

    if not detected_swaras:
        return {
            'detected_swaras': [],
            'matches': [],
            'best_match': None,
            'total_frames_analyzed': len(freq_assignments),
        }

    total_frames = len(freq_assignments)
    swara_names = {
        0: 'Sa', 1: 'Re1', 2: 'Re2', 3: 'Ga1', 4: 'Ga2', 5: 'Ga3',
        6: 'Ma1', 7: 'Ma2', 8: 'Ma3', 9: 'Pa', 10: 'Dha1', 11: 'Dha2',
        12: 'Ni1', 13: 'Ni2', 14: 'Ni3',
    }

    matches = []
    for raga in RAGA_DATABASE:
        score, details = _score_raga(detected_swaras, raga, total_frames)
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

    return {
        'detected_swaras': [
            {'swara': swara_names.get(s, str(s)), 'index': s, 'hits': h}
            for s, h in sorted(detected_swaras.items())
        ],
        'matches': matches[:5],
        'best_match': matches[0] if matches else None,
        'total_frames_analyzed': total_frames,
    }
