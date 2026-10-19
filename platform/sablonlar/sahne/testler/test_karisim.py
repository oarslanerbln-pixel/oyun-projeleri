"""Stil karışımı: plan (stil sonraki sahnelere taşınır), denetim, geçiş karelerinin iki stili de içermesi."""

import sys
import unittest
from pathlib import Path

import numpy as np

BURADA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BURADA))
import dil  # noqa: E402
import kaplama  # noqa: E402
import karisim  # noqa: E402
import sahne  # noqa: E402

SENARYO = BURADA / "testler" / "regresyon" / "regresyon.json"


def senaryo(**sahne_alanlari):
    s = dil.yukle(SENARYO)
    for i, alan in sahne_alanlari.items():
        s["sahneler"][int(i[1:])].update(alan)
    return s


def kare(kap, t, W=216, H=384):
    import skia
    surf = skia.Surface(W, H)
    with surf as cv:
        cv.clear(0xFF000000)
        kap.kare(cv, t, W, H, "9x16")
    return np.asarray(surf.makeImageSnapshot())[..., :3].astype(np.int16)


class Plan(unittest.TestCase):
    def test_stil_sonraki_sahnelere_tasinir(self):
        s = senaryo(s1={"stil": "piksel"}, s2={"donustur": "origami"})
        self.assertEqual(karisim.plan(s, "kinetik"),
                         [("kinetik", "kinetik"), ("piksel", "piksel"), ("piksel", "origami"), ("origami", "origami")])

    def test_karisim_yoksa_tek_kaplama(self):
        z = dil.zamanla(senaryo(), {})
        self.assertFalse(karisim.var_mi(z))
        self.assertNotIsInstance(sahne.kaplama_yap(z, "hamur"), karisim.Karisim)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.k = sahne.kaplama_adlari()

    def test_gecerli(self):
        s = senaryo(s1={"stil": "piksel"}, s2={"donustur": {"stil": "origami", "an": 0.4}})
        self.assertEqual(dil.denetle(s), [])
        self.assertEqual(karisim.denetle(s, "kinetik", self.k), [])

    def test_hatalar(self):
        s = senaryo(s1={"stil": "vitray"}, s2={"donustur": {"stil": "hamur", "an": 0.95}})
        s["stil_gecisi"] = {"tur": "patlama"}
        h = " ".join(karisim.denetle(s, "cini", self.k))
        for parca in ("stil_gecisi", "sahneler[1].stil", "donustur.an", "cini için uzun video kurgusunda"):
            self.assertIn(parca, h)

    def test_cevirici_stil_karisimi_reddedilir(self):
        s = senaryo(s1={"stil": "piksel"})
        self.assertTrue(karisim.denetle(s, "vitray", self.k))


class Kareler(unittest.TestCase):
    def test_gecis_iki_stili_de_gosterir(self):
        for tur in karisim.TURLER:
            z = dil.zamanla(senaryo(s1={"stil": "piksel"}), {})
            z["stil_gecisi"] = {"tur": tur, "sure": 0.8}
            kap = sahne.kaplama_yap(z, "kinetik")
            sh = z["sahneler"][1]
            orta = kare(kap, sh["bas"] + 0.4)
            eski = kare(sahne.kaplama_yap(dil.zamanla(senaryo(), {}), "kinetik"), sh["bas"] - 1e-3)
            piksel = kaplama.kaplamalar()["piksel"](z)
            yeni = kare(piksel, sh["bas"] + 0.4)
            ayni_eski = (np.abs(orta - eski).max(2) < 8).mean()
            ayni_yeni = (np.abs(orta - yeni).max(2) < 8).mean()
            self.assertGreater(ayni_eski, 0.15, tur)
            self.assertGreater(ayni_yeni, 0.15, tur)
            # geçiş bitince saf yeni stil
            sonra = sh["bas"] + 1.2
            self.assertEqual(np.abs(kare(kap, sonra) - kare(piksel, sonra)).max(), 0)


if __name__ == "__main__":
    unittest.main()
