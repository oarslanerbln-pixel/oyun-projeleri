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
import zaman  # noqa: E402

DEPO = HERE.parents[2]
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar" / "senaryo.json"
SKIA = all(importlib.util.find_spec(m) for m in ("skia", "numpy", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "senaryo.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_varsayilanlar(self):
        s = zaman.yukle(ORNEK)
        self.assertEqual(s["muzik"]["dusus"], 3.0)  # ilk diyagonal geçiş
        self.assertEqual(s["sahneler"][0]["gecis"], "kesme")
        self.assertEqual(s["sahneler"][-1]["_son"], 10)

    def test_sahne_disi_an(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["sayi_t"] = 5.0
        self.assertTrue(any("sayi_t" in x for x in zaman.denetle(yaz(h))))

    def test_bilinmeyen_tur_ve_sira(self):
        h = copy.deepcopy(self.ham); h["sahneler"][2]["tur"] = "yok"; h["sahneler"][3]["bas"] = 2.0
        hatalar = zaman.denetle(yaz(h))
        self.assertTrue(any("tür" in x for x in hatalar))
        self.assertTrue(any("artan" in x for x in hatalar))

    def test_seslendirme_cakismasi(self):
        hatalar = zaman.denetle(zaman.yukle(ORNEK), {"v0": 3.5})
        self.assertTrue(any("v0" in x and "bitmiyor" in x for x in hatalar))

    def test_palet(self):
        h = copy.deepcopy(self.ham); h["palet"]["vurgu"] = "sari"
        self.assertTrue(any("palet.vurgu" in x for x in zaman.denetle(yaz(h))))


class Zamanlama(unittest.TestCase):
    def setUp(self):
        self.s = zaman.yukle(ORNEK)

    def test_darbeler_kelimelerde(self):
        anlar = [t for t, _ in zaman.darbeler(self.s)]
        for t in (0.34, 0.62, 1.45, 4.70, 6.80, 8.68):
            self.assertIn(t, anlar)

    def test_ses_olaylari_sirali_ve_sahnede(self):
        o = zaman.ses_olaylari(self.s)
        self.assertEqual([x[0] for x in o], sorted(x[0] for x in o))
        self.assertTrue(all(-0.6 < x[0] < self.s["sure"] for x in o))
        self.assertIn((4.70, "boom"), [(x[0], x[1]) for x in o])
        # sayaç tıkları eğri boyunca, zirveden önce
        tik = [x[0] for x in o if x[1] == "tick"]
        self.assertGreater(len(tik), 10)
        self.assertTrue(all(3.15 <= t < 4.70 for t in tik))

    def test_davul_bosluklari(self):
        self.assertEqual(zaman.davul_bosluklari(self.s), [(2.5, 3.0), (5.75, 6.0), (7.75, 8.0)])

    def test_egri(self):
        self.assertAlmostEqual(zaman.egri(0), 0)
        self.assertAlmostEqual(zaman.egri(1), 1)
        self.assertLess(zaman.egri(0.5), 0.2)  # bileşik büyüme: yarı yolda tepenin çok altında


@unittest.skipUnless(SKIA, "skia-python / numpy / soundfile / ffmpeg yok")
class Render(unittest.TestCase):
    def test_kare_ve_ses(self):
        import cizim
        import sentez
        s = zaman.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            k = cizim.kareler(s, 270, 480, [0.5, 4.9, 9.6], Path(tmp))
            self.assertEqual(len(k), 3)
            self.assertTrue(all(p.stat().st_size > 1000 for p in k))
            bilgi = sentez.miksle(s, Path(tmp))
            self.assertEqual(bilgi["seslendirme"], [])
            self.assertTrue((Path(tmp) / "ses.wav").exists())


if __name__ == "__main__":
    unittest.main()
