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
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar" / "oyuncak.json"
SES = all(importlib.util.find_spec(m) for m in ("numpy", "soundfile"))
RENDER = SES and shutil.which("node") and shutil.which("ffmpeg") and (HERE / "node_modules" / "three").exists() \
    and (HERE / "node_modules" / "playwright").exists()


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "oyuncak.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_varsayilanlar(self):
        h = copy.deepcopy(self.ham)
        for k in ("palet", "muzik", "kolonlar"):
            h.pop(k)
        s = yaz(h)
        self.assertEqual(zaman.denetle(s), [])
        self.assertEqual(s["kolonlar"]["adet"], 52)
        self.assertEqual(s["palet"]["kahraman"], zaman.VARSAYILAN_PALET["kahraman"])
        self.assertEqual(s["sahneler"][-1]["_son"], 10)

    def test_sahne_sirasi(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][2], h["sahneler"][3] = h["sahneler"][3], h["sahneler"][2]
        self.assertTrue(any("sırasıyla" in x for x in zaman.denetle(yaz(h))))
        h = copy.deepcopy(self.ham); h["sahneler"] = h["sahneler"][1:]
        self.assertTrue(any("başlamalı" in x for x in zaman.denetle(yaz(h))))

    def test_istege_bagli_sahneler(self):
        h = copy.deepcopy(self.ham); h["sahneler"] = h["sahneler"][:2]
        s = yaz(h)
        self.assertEqual(zaman.denetle(s), [])
        c = zaman.cizelge(s)
        self.assertIsNone(c["karsitlik"]); self.assertIsNone(c["kapanis"])
        self.assertEqual(c["yazilar"]["doruk"]["son_t"], 10)
        self.assertEqual(len(zaman.akor_bolumleri(s)), 3)

    def test_zaman_hatalari(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][0]["ziplamalar"] = [1.1, 1.3]          # çok sık
        h["sahneler"][1]["doruk_t"] = 6.0                     # sahne dışı
        h["sahneler"][3]["zipla_t"] = 8.4                     # inişe çok yakın
        hatalar = zaman.denetle(yaz(h))
        self.assertTrue(any("arası" in x for x in hatalar))
        self.assertTrue(any("doruk_t" in x for x in hatalar))
        self.assertTrue(any("zipla_t" in x for x in hatalar))

    def test_yazi_ve_palet(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][3]["yazi"]["metin"] = "x" * 30
        h["palet"]["kahraman"] = "kırmızı"
        h["palet"]["mor"] = "#AA00AA"
        hatalar = zaman.denetle(yaz(h))
        self.assertTrue(any("karakter" in x for x in hatalar))
        self.assertTrue(any("palet.kahraman" in x for x in hatalar))
        self.assertTrue(any("bilinmeyen rol mor" in x for x in hatalar))

    def test_seslendirme_cakismasi(self):
        hatalar = zaman.denetle(zaman.yukle(ORNEK), {"v0": 3.0})
        self.assertTrue(any("v1" in x and "çakışıyor" in x for x in hatalar))

    def test_cizelge(self):
        s = zaman.yukle(ORNEK)
        c = zaman.cizelge(s)
        kb = c["kolon_bas"]
        self.assertEqual(len(kb), 52)
        self.assertEqual(c["adim_sayisi"], 3)
        self.assertEqual(kb[:3], [-1.0, 0.75, 1.95])          # zıplamadan 0,35 sn önce yükselir
        self.assertEqual(kb[3], 3.1)                           # dalga büyümeyle başlar
        self.assertAlmostEqual(kb[-1], 4.15)                   # dorukdan 0,45 sn önce biter
        self.assertTrue(all(a <= b for a, b in zip(kb[3:], kb[4:])))
        self.assertEqual(c["kutlama"], [4.95, 5.45, 7.0])
        self.assertEqual(c["yazilar"]["doruk"], {"metin": "37×", "t": 4.6, "son_t": 8.1})

    def test_enerji(self):
        s = zaman.yukle(ORNEK)
        self.assertEqual(zaman.enerji(s, 1.0), 0.3)
        self.assertEqual(zaman.enerji(s, 5.0), 1.0)
        self.assertLess(zaman.enerji(s, 6.5), 0.5)
        self.assertEqual(zaman.enerji(s, 9.0), 0.85)


@unittest.skipUnless(SES, "numpy ve soundfile gerekli")
class Ses(unittest.TestCase):
    def test_miks(self):
        import numpy as np
        import soundfile as sf
        import sentez
        s = zaman.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            bilgi = sentez.miksle(s, Path(tmp))           # seslendirme olmadan da müzik + efekt çıkar
            x, sr = sf.read(str(Path(tmp) / "ses.wav"))
        self.assertEqual(bilgi["seslendirme"], {})
        self.assertEqual(sr, 48000)
        self.assertEqual(len(x), 480000)
        self.assertTrue(np.isfinite(x).all())
        self.assertGreater(np.abs(x).max(), 0.5)


@unittest.skipUnless(RENDER, "node, ffmpeg ve `npm install` (three, playwright) gerekli")
class Render(unittest.TestCase):
    def test_kare(self):
        import oyuncak
        s = zaman.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            yollar = oyuncak.kareler(s, Path(tmp), "1x1", [4.8])
            self.assertTrue(yollar[0].exists())
            self.assertGreater(yollar[0].stat().st_size, 50_000)


if __name__ == "__main__":
    unittest.main()
