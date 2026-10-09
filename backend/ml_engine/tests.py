from django.test import TestCase
from ml_engine.raga_mapping import RAGA_DATABASE


class RagaDatabaseIntegrityTestCase(TestCase):
    def test_all_ragas_vadi_samvadi_in_scale(self):
        """Every raga's vadi and samvadi must be notes in its swaras scale."""
        for raga in RAGA_DATABASE:
            name = raga['name']
            swaras = raga['swaras']
            swaras_bins = set(raga['swaras_bins'])
            vadi = raga['vadi']['grade']
            samvadi = raga['samvadi']['grade']
            vadi_bins = set(raga['vadi_bins'])
            samvadi_bins = set(raga['samvadi_bins'])

            self.assertIn(
                vadi, swaras,
                f"Raga {name}: vadi {vadi} is not in swaras {swaras}"
            )
            self.assertIn(
                samvadi, swaras,
                f"Raga {name}: samvadi {samvadi} is not in swaras {swaras}"
            )
            self.assertTrue(
                vadi_bins.issubset(swaras_bins),
                f"Raga {name}: vadi bins {vadi_bins} not subset of swaras_bins {swaras_bins}"
            )
            self.assertTrue(
                samvadi_bins.issubset(swaras_bins),
                f"Raga {name}: samvadi bins {samvadi_bins} not subset of swaras_bins {swaras_bins}"
            )

    def test_abhogi_vadi_samvadi_specification(self):
        """Abhogi canonical scale is audav (Sa Re2 Ga2 Ma1 Dha1). Vadi=Ma, Samvadi=Sa."""
        abhogi = next(r for r in RAGA_DATABASE if r['name'] == 'Abhogi')
        self.assertEqual(abhogi['vadi']['grade'], 'Ma-s')
        self.assertEqual(abhogi['vadi']['name'], 'Ma')
        self.assertEqual(abhogi['samvadi']['grade'], 'Sa')
        self.assertEqual(abhogi['samvadi']['name'], 'Sa')
        self.assertIn(9, abhogi['vadi_bins'])
        self.assertIn(0, abhogi['samvadi_bins'])

    def test_shankarabharanam_arohana_avarohana_order(self):
        """Shankarabharanam (29th Melakarta) must ascend in arohana and descend in avarohana."""
        sb = next(r for r in RAGA_DATABASE if r['name'] == 'Shankarabharanam')
        expected_arohana = ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-s']
        expected_avarohana = ['Sa', 'Ni-s', 'Dha-s', 'Pa', 'Ma-s', 'Ga-s', 'Re-s', 'Sa']
        self.assertEqual(sb['arohana'], expected_arohana)
        self.assertEqual(sb['avarohana'], expected_avarohana)
        self.assertEqual(sb['arohana_bins'][0], 0)
        self.assertIn(sb['arohana_bins'][-1], [20, 21])
        self.assertEqual(sb['avarohana_bins'][0], 0)
        self.assertEqual(sb['avarohana_bins'][-1], 0)

    def test_kambhoji_shadava_ascent(self):
        """Kambhoji is shadava-sampurna: arohana omits Ni, avarohana includes Ni."""
        kb = next(r for r in RAGA_DATABASE if r['name'] == 'Kambhoji')
        self.assertEqual(
            kb['arohana'],
            ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s']
        )
        self.assertNotIn('Ni-s', kb['arohana'])
        self.assertNotIn('Ni-k', kb['arohana'])
        self.assertIn('Ni-s', kb['avarohana'])
        # Ni bins (18..21) must be absent from arohana_bins
        ni_bins = {18, 19, 20, 21}
        self.assertTrue(set(kb['arohana_bins']).isdisjoint(ni_bins))
        # But Ni bins must be present in avarohana_bins
        self.assertFalse(set(kb['avarohana_bins']).isdisjoint(ni_bins))

    def test_yaman_performance_time(self):
        """Yaman performance time is first prahar of night: 6 PM - 9 PM."""
        yaman = next(r for r in RAGA_DATABASE if r['name'] == 'Yaman')
        self.assertEqual(yaman['time'], 'Evening (6 PM - 9 PM)')


class ClusterFeatureScalingTestCase(TestCase):
    def test_run_clustering_output_structure(self):
        """run_clustering must return valid clusters, labels, and 35-D unscaled centroids."""
        import numpy as np
        from ml_engine.ml_engine import run_clustering

        n_frames = 100
        # Synthetic MFCC: range ~[-400, 100]
        mfcc = np.random.RandomState(42).randn(13, n_frames) * 50.0 - 200.0
        # Synthetic Chroma: range ~[0, 1]
        chroma = np.random.RandomState(42).rand(22, n_frames)
        pcp = np.random.RandomState(42).rand(23, n_frames)

        features = {
            'mfcc': mfcc,
            'chroma': chroma,
            'pcp': pcp,
            'mean_pcp': pcp.mean(axis=1),
        }

        result = run_clustering(features)
        self.assertIn('shruti_clusters', result)
        self.assertIn('labels', result)
        self.assertEqual(len(result['labels']), n_frames)
        self.assertEqual(len(result['shruti_clusters']), 22)

        # Centroid must have 35 dimensions (13 MFCC + 22 Chroma)
        c1 = result['shruti_clusters']['shruti_1']['centroid']
        self.assertEqual(len(c1), 35)
        # Check that centroids are in unscaled feature range, not pure z-scores
        mfcc_part = np.array([c1[:13] for c1 in [cl['centroid'] for cl in result['shruti_clusters'].values()]])
        self.assertTrue(np.any(mfcc_part < -50.0), "Centroids should be in original unscaled MFCC range")




