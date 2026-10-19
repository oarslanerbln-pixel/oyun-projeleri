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

ORNEK = HERE / "ornek" / "senaryo.json"
SKIA = all(importlib.util.find_spec(m) for m in ("skia", "numpy", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict, tmp: str) -> dict:
    p = Path(tmp) / "senaryo.json"
    p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
    return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_varsayilanlar(self):
        s = zaman.yukle(ORNEK)
        self.assertEqual(s["sahneler"][0]["gecis"], "kesme")
        self.assertEqual(s["sahneler"][-1]["_son"], 10)
        h = copy.deepcopy(self.ham); del h["muzik"]
        s = yaz(h, self.tmp.name)
        self.assertEqual(s["muzik"]["dusus"], 3.0)   # ikinci sahne
        self.assertEqual(s["muzik"]["zirve"], 6.0)   # çarpan simit
        self.assertEqual(s["muzik"]["sakin"], [6.8, 7.5])

    def test_sahne_disi_an(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["nesne2"]["t"] = 8.0
        self.assertTrue(any("nesne2.t" in x for x in zaman.denetle(yaz(h, self.tmp.name))))

    def test_bilinmeyen_nesne_ve_gorsel(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][0]["nesne"]["tur"] = "pasta"
        h["sahneler"][1]["nesne"] = {"gorsel": "yok.png", "t": 3.3}
        hatalar = zaman.denetle(yaz(h, self.tmp.name))
        self.assertTrue(any("nesne.tur" in x for x in hatalar))
        self.assertTrue(any("gorsel bulunamadı" in x for x in hatalar))

    def test_tur_gecis_sira(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][1]["gecis"] = "iris"; h["sahneler"][2]["bas"] = 2.0
        hatalar = zaman.denetle(yaz(h, self.tmp.name))
        self.assertTrue(any("geçiş" in x for x in hatalar))
        self.assertTrue(any("artan" in x for x in hatalar))

    def test_seslendirme_cakismasi(self):
        hatalar = zaman.denetle(zaman.yukle(ORNEK), {"v0": 3.2})
        self.assertTrue(any("v0" in x and "bitmeli" in x for x in hatalar))

    def test_palet(self):
        h = copy.deepcopy(self.ham); h["palet"]["vurgu"] = "kirmizi"
        self.assertTrue(any("palet.vurgu" in x for x in zaman.denetle(yaz(h, self.tmp.name))))


class Zamanlama(unittest.TestCase):
    def setUp(self):
        self.s = zaman.yukle(ORNEK)

    def test_harf_anlari(self):
        a = zaman.harf_anlari({"metin": "ÇALIŞAN BAŞINA", "t": 4.3, "son": 5.05})
        self.assertEqual(len(a), 13)  # boşluk sayılmaz
        self.assertAlmostEqual(a[0], 4.3); self.assertAlmostEqual(a[-1], 5.05)

    def test_adim_15fps(self):
        self.assertEqual(zaman.adim(0.10), 1 / 15)
        self.assertEqual(zaman.adim(1 / 15), 1 / 15)

    def test_ses_olaylari(self):
        o = zaman.ses_olaylari(self.s)
        self.assertEqual([x[0] for x in o], sorted(x[0] for x in o))
        self.assertTrue(all(0 <= x[0] < self.s["sure"] for x in o))
        turler = {x[1] for x in o}
        self.assertTrue({"yirt", "kaydir", "carp", "damga", "harf", "yazici", "bant", "kalem"} <= turler)
        self.assertIn((6.0, "carp"), o)

    def test_darbeler(self):
        anlar = [t for t, _ in zaman.darbeler(self.s)]
        for t in (2.45, 3.0, 6.0, 7.75):
            self.assertIn(t, anlar)


@unittest.skipUnless(SKIA, "skia-python / numpy / soundfile / ffmpeg yok")
class Render(unittest.TestCase):
    def test_kare_ve_ses(self):
        import cizim
        import sentez
        s = zaman.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            k = cizim.kareler(s, 270, 480, [0.5, 3.1, 6.9, 7.4, 9.6], Path(tmp))
            self.assertEqual(len(k), 5)
            self.assertTrue(all(p.stat().st_size > 1000 for p in k))
            bilgi = sentez.miksle(s, Path(tmp), Path(tmp) / "yok")
            self.assertEqual(bilgi["seslendirme"], {})
            self.assertTrue((Path(tmp) / "ses.wav").exists())


if __name__ == "__main__":
    unittest.main()
