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
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar" / "golge-oyunu.json"
SKIA = all(importlib.util.find_spec(m) for m in ("skia", "numpy", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "golge-oyunu.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_varsayilanlar(self):
        s = zaman.yukle(ORNEK)
        self.assertEqual([sh["gecis"] for sh in s["sahneler"]], ["kesme", "lale", "lale", "lale"])
        self.assertEqual([sh["muzik"] for sh in s["sahneler"]], ["taksim", "ritim", "sakin", "ritim"])
        self.assertEqual(s["sahneler"][-1]["_son"], 10)
        self.assertFalse(s["sahneler"][0]["levha"]["zil"])
        self.assertEqual(s["palet"]["ten"], zaman.VARSAYILAN_PALET["ten"])
        self.assertEqual(zaman.gecis_anlari(s), [3.0, 6.0, 8.0])

    def test_zaman_sahne_disi(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["zafer_t"] = 6.5
        self.assertTrue(any("zafer_t" in x for x in zaman.denetle(yaz(h))))

    def test_tirmanis_sigmali(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["tirman_sure"] = 3.0
        self.assertTrue(any("tırmanış" in x for x in zaman.denetle(yaz(h))))

    def test_bilinmeyenler(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][2]["tur"] = "deniz"
        h["sahneler"][1]["gecis"] = "iris"
        h["kukla"]["sapka"] = "vurgu"
        h["muzik"]["makam"] = "saba"
        h["format"] = "21x9"
        hatalar = zaman.denetle(yaz(h))
        for parca in ("tür", "geçiş", "sapka", "makam", "format"):
            self.assertTrue(any(parca in x for x in hatalar), parca)

    def test_levha_ve_lale_gecisi(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][0]["levha"]["metin"] = " "
        h["sahneler"][2]["bas"] = 3.3
        h["sahneler"][2]["filiz_t"] = 3.4; h["sahneler"][2]["t"] = 3.5
        hatalar = zaman.denetle(yaz(h))
        self.assertTrue(any("levha.metin" in x for x in hatalar))
        self.assertTrue(any("lale" in x for x in hatalar))

    def test_seslendirme_cakismasi(self):
        self.assertTrue(any("bitmiyor" in x for x in zaman.denetle(zaman.yukle(ORNEK), {"v0": 3.0})))

    def test_ses_olaylari(self):
        o = zaman.ses_olaylari(zaman.yukle(ORNEK))
        self.assertEqual(o[0][1], "nareke")
        self.assertEqual(sum(1 for x in o if x[1] == "zil"), 2)
        self.assertEqual([x[0] for x in o], sorted(x[0] for x in o))


@unittest.skipUnless(SKIA, "skia-python / numpy / soundfile / ffmpeg yok")
class Uretim(unittest.TestCase):
    def test_kareler_ve_ses(self):
        import cizim
        import sentez
        s = zaman.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            for W, H in ((1080, 1920), (1920, 1080), (1080, 1080)):
                yollar = cizim.kareler(s, W, H, [1.0, 3.0, 4.6, 7.5, 9.5], Path(tmp))
                self.assertEqual(len(yollar), 5)
            bilgi = sentez.miksle(s, Path(tmp), None)
            self.assertEqual(bilgi["seslendirme"], [])
            self.assertTrue((Path(tmp) / "ses.wav").exists())

    def test_baska_makam_ve_sira(self):
        import sentez
        s = zaman.yukle(ORNEK)
        h = {k: v for k, v in s.items() if not k.startswith("_")}
        h["muzik"]["makam"] = "nihavent"
        h["sahneler"] = [copy.deepcopy(s["sahneler"][2]), copy.deepcopy(s["sahneler"][3])]
        h["sahneler"][0].update(bas=0, filiz_t=0.2, t=0.6); h["sahneler"][1].update(bas=4.0, bayrak_t=4.3, kol_t=4.1)
        h["sahneler"][1]["levha"]["t"] = 4.4
        for sh in h["sahneler"]:
            for k in [k for k in sh if k.startswith("_")] + ["gecis", "muzik"]:
                sh.pop(k, None)
        y = yaz(h)
        self.assertEqual(zaman.denetle(y), [])
        with tempfile.TemporaryDirectory() as tmp:
            sentez.miksle(y, Path(tmp), None)


if __name__ == "__main__":
    unittest.main()
