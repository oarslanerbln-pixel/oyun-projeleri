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
import analiz  # noqa: E402
import cizim  # noqa: E402

DEPO = HERE.parents[2]
ORNEK = DEPO / "ornekler" / "fransa-ekim-2026" / "analiz.json"
SKIA = all(importlib.util.find_spec(m) for m in ("skia", "numpy", "soundfile")) and shutil.which("ffmpeg")


def yukle(ham: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "analiz.json"
        p.write_text(json.dumps(ham, ensure_ascii=False), encoding="utf-8")
        return analiz.yukle(str(p))


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(analiz.denetle(analiz.yukle(str(ORNEK))), [])

    def test_kaynak_zorunlu(self):
        h = copy.deepcopy(self.ham)
        del h["sahneler"][1]["kaynak"]
        self.assertTrue(any("kaynak" in x for x in analiz.denetle(yukle(h))))

    def test_deger_sayi_olmali(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][1]["cubuklar"][0]["deger"] = "5,8"
        self.assertTrue(any("deger sayı" in x for x in analiz.denetle(yukle(h))))

    def test_bilinmeyen_tur_ve_sira(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][2]["tur"] = "pasta"
        h["sahneler"][4]["bas"] = 1.0
        hatalar = analiz.denetle(yukle(h))
        self.assertTrue(any("bilinmeyen tür" in x for x in hatalar))
        self.assertTrue(any("artan" in x for x in hatalar))

    def test_harita_koordinat(self):
        h = copy.deepcopy(self.ham)
        del h["sahneler"][4]["noktalar"][0]["lat"]
        self.assertTrue(any("lon/lat" in x for x in analiz.denetle(yukle(h))))

    def test_seslendirme_cakismasi(self):
        s = analiz.yukle(str(ORNEK))
        self.assertTrue(any("çakışıyor" in x for x in analiz.denetle(s, {"v0": 9.0})))

    def test_format(self):
        s = analiz.yukle(str(ORNEK))
        self.assertEqual(analiz.formatlar_coz(s, None), ["16:9"])
        self.assertEqual(analiz.formatlar_coz(s, "ikisi"), ["16:9", "9:16"])
        s.pop("format")
        self.assertEqual(analiz.formatlar_coz(s, None), ["16:9"])


class Yardimcilar(unittest.TestCase):
    def test_sayi_yaz(self):
        self.assertEqual(cizim.sayi_yaz(550000), "550.000")
        self.assertEqual(cizim.sayi_yaz(5.4, 1), "5,4")
        self.assertEqual(cizim.sayi_yaz(1234567.891, 2), "1.234.567,89")
        self.assertEqual(cizim.sayi_yaz(-3.25, 1), "-3,2")

    def test_buyuk_harf(self):
        self.assertEqual(cizim.buyuk("Ekim zirvesi · analiz"), "EKİM ZİRVESİ · ANALİZ")
        self.assertEqual(cizim.buyuk("kapalı"), "KAPALI")

    def test_harita_verisi(self):
        h = cizim.harita_verisi()
        self.assertIn("FR", h)
        self.assertGreater(sum(len(r) for r in h["FR"]), 500)

    def test_oge_anlari(self):
        sahne = {"bas": 10, "cubuklar": [{"t": 12}, {}, {}]}
        self.assertEqual(cizim.oge_anlari(sahne, sahne["cubuklar"], 0.9, 0.5), [12, 11.4, 11.9])


@unittest.skipUnless(SKIA, "skia-python / numpy / soundfile / ffmpeg yok")
class Uretim(unittest.TestCase):
    def test_kareler_ve_ses(self):
        s = analiz.yukle(str(ORNEK))
        with tempfile.TemporaryDirectory() as tmp:
            for f in ("16:9", "9:16"):
                anlar = [x["bas"] + 2.5 for x in s["sahneler"]]
                yollar = cizim.kareler(s, *analiz.FORMATLAR[f], anlar, Path(tmp))
                self.assertEqual(len(yollar), len(s["sahneler"]))
            import muzik
            bilgi = muzik.miksle(s, Path(tmp), None)
            self.assertEqual(bilgi["seslendirme"], [])
            self.assertTrue((Path(tmp) / "ses.wav").exists())


if __name__ == "__main__":
    unittest.main()
