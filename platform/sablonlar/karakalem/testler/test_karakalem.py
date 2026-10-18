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
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar" / "karakalem.json"
NUMPY = importlib.util.find_spec("numpy") is not None
SKIA = NUMPY and all(importlib.util.find_spec(m) for m in ("skia", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "karakalem.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_sahne_sirasi(self):
        h = copy.deepcopy(self.ham); h["sahneler"].reverse()
        self.assertTrue(any("sırayla" in x for x in zaman.denetle(yaz(h))))

    def test_adimlar_cok_erken(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["bas"] = 1.0
        self.assertTrue(any("adimlar" in x for x in zaman.denetle(yaz(h))))

    def test_basamaklara_yer_yok(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["adet"] = 8  # 8 vuruş sonuçtan önce bitmez
        self.assertTrue(any("sonuc" in x for x in zaman.denetle(yaz(h))))

    def test_renk_ve_sac(self):
        h = copy.deepcopy(self.ham); h["palet"]["vurgu"] = "turuncu"; h["karakter"]["sac"] = "mohikan"
        hatalar = zaman.denetle(yaz(h))
        self.assertTrue(any("palet.vurgu" in x for x in hatalar))
        self.assertTrue(any("karakter.sac" in x for x in hatalar))

    def test_damga_egriden_once(self):
        h = copy.deepcopy(self.ham); h["sahneler"][2]["damga"]["t"] = 7.2
        self.assertTrue(any("damga" in x for x in zaman.denetle(yaz(h))))

    def test_seslendirme_cakismasi(self):
        hatalar = zaman.denetle(zaman.yukle(ORNEK), {"v0": 3.0})
        self.assertTrue(any("v0" in x and "bitmiyor" in x for x in hatalar))


class Zamanlama(unittest.TestCase):
    def setUp(self):
        self.s = zaman.yukle(ORNEK)

    def test_inisler_vurusta(self):
        an = zaman.inisler(self.s)
        self.assertEqual(len(an), 5)
        self.assertAlmostEqual(an[0], 2.967 + 60 / 90)
        for a, b in zip(an, an[1:]):
            self.assertAlmostEqual(b - a, 60 / 90)

    def test_egri_basamak_koselerinden_zirveye(self):
        b = zaman.basamaklar(self.s)
        for i, h in enumerate(b["yuk"]):  # eğri her basamağın sağ üst köşesinden geçer
            x = zaman.SX0 + (i + 1) * b["w"]
            self.assertAlmostEqual(zaman.ZEMIN - zaman.egri_y(b, x), h, places=6)
        self.assertAlmostEqual(zaman.egri_y(b, zaman.ZIRVE[0]), zaman.ZIRVE[1], places=6)
        self.assertTrue(all(y >= zaman.ZIRVE[1] for _, y in zaman.cizgiler(self.s)["egri"]["yol"]))

    def test_basamak_inisten_once_biter(self):
        c = zaman.cizgiler(self.s)
        for i, an in enumerate(zaman.inisler(self.s)):
            self.assertLess(c[f"basamak{i}"]["t"] + c[f"basamak{i}"]["d"], an)

    def test_kose_tiklari(self):
        c = zaman.cizgiler(self.s)["basamak0"]  # dikdörtgenin iki üst köşesi
        k = zaman.koseler(c)
        self.assertEqual(len(k), 2)
        self.assertTrue(all(c["t"] < x < c["t"] + c["d"] for x in k))

    def test_kelime_zamanlari(self):
        satirlar = zaman.kelimeler(self.s, {"v3": 0.9})
        self.assertEqual([w["k"] for w in satirlar[0]["kelimeler"]], ["Otuz", "yedi", "kat!"])
        ws = satirlar[0]["kelimeler"]
        self.assertAlmostEqual(ws[0]["t"], 8.5); self.assertAlmostEqual(ws[-1]["son"], 9.4)
        self.assertAlmostEqual(ws[1]["t"], 8.5 + 0.9 * 2 / 5)  # o-tuz | ye-di | kat

    def test_ses_olaylari(self):
        o = zaman.ses_olaylari(self.s)
        self.assertEqual(sum(1 for x in o if x[1] == "inis"), 5)
        self.assertIn((8.3, "damga"), [(x[0], x[1]) for x in o])
        self.assertEqual([x[0] for x in o], sorted(x[0] for x in o))


@unittest.skipUnless(SKIA, "skia-python / numpy / soundfile / ffmpeg yok")
class Uretim(unittest.TestCase):
    def test_kare_ve_ses(self):
        import cizim
        import sentez
        s = zaman.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            for W, H in ((540, 960), (960, 540)):
                p = cizim.kareler(s, W, H, [1.2, 4.0, 9.0], Path(tmp))
                self.assertEqual(len(p), 3)
                self.assertTrue(all(x.stat().st_size > 10_000 for x in p))
            k = copy.deepcopy(s); k["sure"] = 10.2
            bilgi = sentez.miksle(k, Path(tmp))
            self.assertEqual(bilgi["seslendirme"], [])
            self.assertTrue((Path(tmp) / "ses.wav").stat().st_size > 100_000)


if __name__ == "__main__":
    unittest.main()
