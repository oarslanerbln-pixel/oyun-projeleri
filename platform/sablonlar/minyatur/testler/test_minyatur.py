import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import cizim  # noqa: E402
import minyatur  # noqa: E402

DEPO = HERE.parents[2]
ORNEK = DEPO / "ornekler" / "lale-sofrasi" / "minyatur.json"
SES = all(importlib.util.find_spec(m) for m in ("numpy", "soundfile"))
SKIA = SES and importlib.util.find_spec("skia") and shutil.which("ffmpeg")


def yukle(ham: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "minyatur.json"
        p.write_text(json.dumps(ham, ensure_ascii=False), encoding="utf-8")
        return minyatur.yukle(str(p))


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(minyatur.denetle(minyatur.yukle(str(ORNEK))), [])

    def test_doluluk_araligi(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][1]["doluluk"] = 1.4
        self.assertTrue(any("doluluk" in x for x in minyatur.denetle(yukle(h))))

    def test_bilinmeyen_tur_ve_sira(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][1]["tur"] = "pasta"
        h["sahneler"][3]["bas"] = 1.0
        hatalar = minyatur.denetle(yukle(h))
        self.assertTrue(any("bilinmeyen tür" in x for x in hatalar))
        self.assertTrue(any("artan" in x for x in hatalar))

    def test_kartus_kisa_olmali(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][2]["kartus"] = "Her akşam burası tıklım tıklım dolu"
        self.assertTrue(any("kartuş" in x for x in minyatur.denetle(yukle(h))))

    def test_kapanis_marka_ister(self):
        h = copy.deepcopy(self.ham)
        h["marka"] = {}
        self.assertTrue(any("marka.ad" in x for x in minyatur.denetle(yukle(h))))

    def test_seslendirme_cakismasi_ve_sonu(self):
        s = minyatur.yukle(str(ORNEK))
        self.assertTrue(any("çakışıyor" in x for x in minyatur.denetle(s, {"v0": 9.0})))
        self.assertTrue(any("sonuna" in x for x in minyatur.denetle(s, {"v3": 3.0})))


class Zaman(unittest.TestCase):
    def setUp(self):
        self.s = minyatur.yukle(str(ORNEK))

    def test_doluluk_artar_ve_dolar(self):
        d = [cizim.doluluk(self.s, i / 10) for i in range(101)]
        self.assertTrue(all(b >= a - 1e-9 for a, b in zip(d, d[1:])))
        self.assertAlmostEqual(d[0], 0.09)
        self.assertAlmostEqual(d[-1], 1.0)

    def test_gece_tepe_sahnesinde_coker(self):
        self.assertEqual(cizim.gece(self.s, 4.0), 0.0)
        self.assertAlmostEqual(cizim.gece(self.s, 7.0), 1.0)

    def test_usul_ritimle_baslar_kapanista_biter(self):
        u = cizim.usul(self.s)
        self.assertEqual(u[0], (2.3, "dum"))
        self.assertTrue(all(2.3 <= t < 7.8 for t, _ in u))
        tepe = [t for t, tur in u if tur == "ke" and t >= 5.2]
        self.assertGreater(len(tepe), 2)


@unittest.skipUnless(SKIA, "skia-python, numpy, soundfile ve ffmpeg gerekli")
class Cizim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = minyatur.yukle(str(ORNEK))
        try:
            cls.c = cizim.Cizici(cls.s, 540, 960)
        except RuntimeError as e:  # yazı tipi indirilemedi (ağ yok)
            raise unittest.SkipTest(str(e))

    def test_herkes_oturur_yol_mindere_varir(self):
        for k in self.c.koltuk:
            self.assertLess(k["oturma"], 7.8, "kapanıştan önce bütün minderler dolmalı")
            self.assertEqual(k["yol"][-1], (k["x"], k["y"]))

    def test_masa_arkadaslari_birlikte_gelir(self):
        # yalnız sahne sınırına denk gelen masalar (her rampa başına en çok bir) bölünebilir
        bolunen = 0
        for mi in range(len(self.c.L.masalar)):
            anlar = sorted(k["oturma"] for k in self.c.koltuk if k["masa"] == mi)
            bolunen += anlar[-1] - anlar[0] > 0.8
        self.assertLessEqual(bolunen, len(cizim.doluluk_anahtarlari(self.s)))

    def test_kareler_cizilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            for W, H in ((540, 960), (960, 540)):
                yollar = cizim.kareler(self.s, W, H, [0.0, 3.0, 6.5, 9.5], Path(tmp))
                self.assertEqual(len(yollar), 4)
                self.assertTrue(all(p.stat().st_size > 1000 for p in yollar))


@unittest.skipUnless(SES, "numpy ve soundfile gerekli")
class Ses(unittest.TestCase):
    def test_muzik_ve_miks(self):
        import numpy as np
        import muzik
        s = minyatur.yukle(str(ORNEK))
        n = int(s["sure"] * muzik.SR)
        m = muzik.muzik_uret(s, n)
        self.assertEqual(m.shape, (n, 2))
        self.assertLess(abs(float(m.mean())), 1e-3)
        self.assertTrue(np.isfinite(m).all())
        with tempfile.TemporaryDirectory() as tmp:
            bilgi = muzik.miksle(s, Path(tmp), None)
            self.assertEqual(bilgi["seslendirme"], [])
            self.assertTrue((Path(tmp) / "ses.wav").exists())


if __name__ == "__main__":
    unittest.main()
