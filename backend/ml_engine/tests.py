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



