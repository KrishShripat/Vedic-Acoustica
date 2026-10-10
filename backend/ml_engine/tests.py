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
        # Descent nishada is kaisiki (N2 / Ni-k); N3 (Ni-s) is only an anya
        # swara in the phrase S N3 P D2 S, so it must not drive the scale.
        self.assertIn('Ni-k', kb['avarohana'])
        self.assertNotIn('Ni-s', kb['avarohana'])
        # Ni bins (18..21) must be absent from arohana_bins
        ni_bins = {18, 19, 20, 21}
        self.assertTrue(set(kb['arohana_bins']).isdisjoint(ni_bins))
        # But Ni bins must be present in avarohana_bins
        self.assertFalse(set(kb['avarohana_bins']).isdisjoint(ni_bins))

    def test_yaman_performance_time(self):
        """Yaman performance time is first prahar of night: 6 PM - 9 PM."""
        yaman = next(r for r in RAGA_DATABASE if r['name'] == 'Yaman')
        self.assertEqual(yaman['time'], 'Evening (6 PM - 9 PM)')

    def test_carnatic_bhairavi_bhashanga_scale(self):
        """Bhairavi (Carnatic) is a bhashanga raga with Chatushruti Dhaivata (Dha-s / D2)
        in arohana and Shuddha Dhaivata (Dha-k / D1) in avarohana."""
        cb = next(r for r in RAGA_DATABASE if r['name'] == 'Bhairavi (Carnatic)')
        nb = next(r for r in RAGA_DATABASE if r['name'] == 'Nata Bhairavi')

        # Carnatic Bhairavi must have Dha-s in arohana and Dha-k in avarohana
        self.assertIn('Dha-s', cb['arohana'])
        self.assertNotIn('Dha-k', cb['arohana'])
        self.assertIn('Dha-k', cb['avarohana'])
        self.assertNotIn('Dha-s', cb['avarohana'])
        self.assertIn('Dha-s', cb['swaras'])
        self.assertIn('Dha-k', cb['swaras'])

        # Parent Nata Bhairavi uses Dha-k in both directions (linear sampurna)
        self.assertIn('Dha-k', nb['arohana'])
        self.assertIn('Dha-k', nb['avarohana'])
        self.assertNotIn('Dha-s', nb['swaras'])

        # Dha-s bins (16, 17) must be in cb arohana_bins, Dha-k bins (14, 15) in avarohana_bins
        dha_s_bins = {16, 17}
        dha_k_bins = {14, 15}
        self.assertTrue(dha_s_bins.issubset(set(cb['arohana_bins'])))
        self.assertTrue(dha_k_bins.issubset(set(cb['avarohana_bins'])))

    def test_carnatic_janya_scale_grades_canonical(self):
        """Regression guard for janya-raga grade encoding.

        Six ragas previously encoded the wrong rishabha/gandhara/dhaivata/
        nishada grade, silently shifting their Shruti bins and corrupting
        scoring. Each expected scale is the canonical janya scale of the
        stated parent melakarta (verified against Wikipedia / Darbar /
        karnatik / raagawheel).
        """
        expected = {
            # 22 Kharaharapriya: R2 G2 M1 D2 N2
            'Abhogi': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Dha-s'],
            'Madhyamavati': ['Sa', 'Re-s', 'Ma-s', 'Pa', 'Ni-k'],
            'Sri Raga': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
            'Ritigowla': ['Sa', 'Re-s', 'Ga-k', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
            # 16 Chakravakam: R1 G3 M1 D2 N2
            'Chakravakam': ['Sa', 'Re-k', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
            # 28 Harikambhoji: R2 G3 M1 D2 N2
            'Kambhoji': ['Sa', 'Re-s', 'Ga-s', 'Ma-s', 'Pa', 'Dha-s', 'Ni-k'],
        }
        for name, scale in expected.items():
            raga = next(r for r in RAGA_DATABASE if r['name'] == name)
            self.assertEqual(raga['swaras'], scale, f"{name}: wrong swara grades")
            for grade in raga['arohana'] + raga['avarohana']:
                self.assertIn(
                    grade, scale,
                    f"{name}: direction uses {grade}, not in scale {scale}"
                )


class TonicEstimationTestCase(TestCase):
    def test_recovers_reference_tonic(self):
        """A sustained middle-C pitch track must resolve to the C4 reference."""
        import numpy as np
        from ml_engine.tonic import estimate_tonic_cents

        f0 = np.full(200, 261.626)
        cents, conf = estimate_tonic_cents(f0, np.ones(200, dtype=bool))
        self.assertAlmostEqual(cents, 0.0, delta=15.0)
        self.assertGreater(conf, 0.5)

    def test_recovers_shifted_tonic(self):
        """A sustained pitch a fourth below C4 (G3) must resolve to ~-500 cents."""
        import numpy as np
        from ml_engine.tonic import estimate_tonic_cents

        sa = 261.626 * 2 ** (-5 / 12)   # G3
        f0 = np.full(200, sa)
        cents, conf = estimate_tonic_cents(f0, np.ones(200, dtype=bool))
        self.assertAlmostEqual(cents, -500.0, delta=15.0)
        self.assertGreater(conf, 0.5)

    def test_flat_scale_is_ambiguous(self):
        """An equal-weight scalar passage has no dominant pitch class: keep C4."""
        import numpy as np
        from ml_engine.tonic import estimate_tonic_cents

        ratios = [1.0, 16 / 15, 9 / 8, 6 / 5, 3 / 2, 8 / 5, 15 / 8]
        f0 = np.concatenate([np.full(30, 261.626 * r) for r in ratios])
        cents, conf = estimate_tonic_cents(f0, np.ones(len(f0), dtype=bool))
        self.assertEqual(cents, 0.0)
        self.assertLess(conf, 0.5)

    def test_too_few_frames_returns_reference(self):
        """Estimation is not attempted below the voiced-frame floor."""
        import numpy as np
        from ml_engine.tonic import estimate_tonic_cents

        f0 = np.full(5, 300.0)
        cents, conf = estimate_tonic_cents(f0, np.ones(5, dtype=bool))
        self.assertEqual(cents, 0.0)
        self.assertEqual(conf, 0.0)


class TonicTranspositionTestCase(TestCase):
    def test_nearest_shruti_respects_tonic(self):
        """The Shruti grid must rotate so the tonic maps to bin 0 (Sa)."""
        from ml_engine.ml_engine import _nearest_shruti_from_f0

        tonic = 293.664   # D4
        self.assertEqual(_nearest_shruti_from_f0(tonic, tonic), 0)
        self.assertEqual(_nearest_shruti_from_f0(tonic * (3 / 2), tonic), 13)
        self.assertNotEqual(_nearest_shruti_from_f0(tonic, 261.626), 0)

    def test_compute_pcp_transposes_bins(self):
        """A tone at a non-C tonic must land on bin 0 when transposed."""
        import numpy as np
        from ml_engine.audio_processing import compute_pcp, SR

        tonic = 293.664   # D4
        t = np.linspace(0, 0.4, int(SR * 0.4), endpoint=False)
        y = np.sin(2 * np.pi * tonic * t).astype(np.float32)

        pcp_tonic, _ = compute_pcp(y, sr=SR, tonic_hz=tonic)
        self.assertEqual(int(np.argmax(pcp_tonic.mean(axis=1))), 0)

        pcp_c4, _ = compute_pcp(y, sr=SR)
        self.assertNotEqual(int(np.argmax(pcp_c4.mean(axis=1))), 0)


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




