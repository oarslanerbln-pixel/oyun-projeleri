"""Neon şablonu testleri: senaryo denetimi, olay anlarının süreyle orantılanması, kare çizimi ve tane."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import neon  # noqa: E402

DEPO = Path(__file__).resolve().parents[4]
MARKA = DEPO / 'ornekler' / 'demli-kahve' / 'marka' / 'marka.json'

try:
    import skia  # noqa: F401
    SKIA = True
except ImportError:
    SKIA = False


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def senaryo(self, **ek):
        s = {'kimlik': 'deneme', 'stil': 'neon', 'marka': str(MARKA), 'neon': {'logo': 'Deneme', 'monogram': 'D'}, **ek}
        p = self.kok / 'neon.json'
        p.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        return str(p)


class Denetim(Tmp):
    def test_ornek_gecer(self):
        hata, _ = neon.denetle(str(DEPO / 'ornekler' / 'demli-kahve' / 'neon.json'))
        self.assertEqual(hata, [])

    def test_hatalar(self):
        hata, _ = neon.denetle(self.senaryo(sure=14, neon={'logo': 'x' * 30, 'monogram': 'ABCD', 'fazla': 1}))
        metin = '\n'.join(hata)
        for parca in ('sure', 'en çok 18', 'en çok 3', 'tanımsız alan'):
            self.assertIn(parca, metin)


@unittest.skipUnless(SKIA, 'skia-python yok')
class Cizim(Tmp):
    def test_anlar_sureyle_orantili(self):
        g = neon.Gorunum(self.senaryo(sure=10))
        self.assertAlmostEqual(g.an['logo'], neon.AN['logo'] * 10 / 8)

    def test_kare_ve_tane(self):
        g = neon.Gorunum(self.senaryo())
        a, _ = neon._kare_dizi(g, 6.0, 216, 384, np.random.default_rng(0))
        self.assertEqual(a.shape[:2], (384, 216))
        b, _ = neon._kare_dizi(g, 6.0, 216, 384, np.random.default_rng(1))
        self.assertTrue((a != b).any())          # tane her karede değişir
        self.assertLess(np.abs(a.astype(int) - b.astype(int)).max(), 8)  # ama görüntüyü değiştirmez

    def test_muzik(self):
        g = neon.Gorunum(self.senaryo())
        x = neon.muzik(g)
        self.assertEqual(len(x), int(neon.SR * 8))
        self.assertGreater(np.abs(x).max(), 0)


if __name__ == '__main__':
    unittest.main()
