"""Görsel regresyon: her stilin 3 karesi kayıtlı referansla aynı görünmeli (regresyon.py).

Bu test kırmızıysa bir değişiklik bir stilin görünümünü değiştirdi. Fark sayfası: `GORSEL_REGRESYON_FARK`
(CI'da iş akışının ekleri). Değişiklik bilerekse: python3 platform/sablonlar/sahne/regresyon.py guncelle --stiller <stil>
"""

import sys
import unittest
from pathlib import Path

import numpy as np

BURADA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BURADA))
import regresyon  # noqa: E402


class GorselRegresyon(unittest.TestCase):
    def test_her_stilin_referansi_var(self):
        eksik = [s for s in regresyon.stiller() if regresyon.referans(s) is None]
        self.assertEqual(eksik, [], "referansı olmayan stil: regresyon.py guncelle --stiller ...")

    def test_esik_kaymayi_yakalar_kenar_farkini_gecirir(self):
        ref = regresyon.referans("kinetik")[0]
        self.assertFalse(regresyon.olc(ref, np.roll(ref, 10, axis=1))["gecti"])
        renk = ref.copy()
        renk[..., 0] = 255 - renk[..., 0]
        self.assertFalse(regresyon.olc(ref, renk)["gecti"])
        gurultu = np.clip(ref.astype(np.int16) + np.random.default_rng(1).integers(-1, 2, ref.shape), 0, 255).astype(np.uint8)
        self.assertTrue(regresyon.olc(ref, gurultu)["gecti"])

    def test_butun_stiller_referansla_ayni(self):
        self.assertEqual(regresyon.karsilastir(), [])


if __name__ == "__main__":
    unittest.main()
