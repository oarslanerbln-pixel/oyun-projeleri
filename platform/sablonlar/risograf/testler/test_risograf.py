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
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar" / "risograf.json"
RENDER = all(importlib.util.find_spec(m) for m in ("skia", "numpy", "scipy", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "risograf.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_varsayilanlar(self):
        h = copy.deepcopy(self.ham)
        for k in ("murekkepler", "tanecik", "kagit"):
            h.pop(k)
        s = yaz(h)
        self.assertEqual(s["baski_sirasi"], ["sari", "pembe", "mavi"])
        self.assertEqual(s["isaretler"]["murekkep"], "mavi")
        self.assertEqual(zaman.denetle(s), [])

    def test_tanimsiz_murekkep(self):
        h = copy.deepcopy(self.ham); h["sayfalar"][0]["ogeler"][0]["murekkep"] = "yesil"
        self.assertTrue(any("yesil" in x for x in zaman.denetle(yaz(h))))

    def test_bes_murekkep_olmaz(self):
        h = copy.deepcopy(self.ham)
        for ad in ("a", "b"):
            h["murekkepler"][ad] = {"renk": "#000000"}
        self.assertTrue(any("1–4" in x for x in zaman.denetle(yaz(h))))

    def test_bilinmeyen_giris(self):
        h = copy.deepcopy(self.ham); h["sayfalar"][0]["ogeler"][2]["giris"] = "uc"
        self.assertTrue(any("giris" in x for x in zaman.denetle(yaz(h))))

    def test_sayac_sayfa_disi(self):
        h = copy.deepcopy(self.ham); h["sayfalar"][1]["ogeler"][2]["bitis_t"] = 6.5
        self.assertTrue(any("bitis_t" in x for x in zaman.denetle(yaz(h))))

    def test_damgalar(self):
        self.assertEqual(zaman.damgalar(zaman.yukle(ORNEK)), [1.435, 4.5, 6.85, 6.985, 8.285, 8.535])

    def test_bicim_ezme(self):
        s = zaman.bicim_icin(zaman.yukle(ORNEK), "16x9")
        o = s["sayfalar"][3]["ogeler"][2]
        self.assertEqual((o["x0"], o["y"]), (0.62, 0.45))
        self.assertNotIn("16x9", o)

    def test_ses_olaylari(self):
        o = zaman.ses_olaylari(zaman.yukle(ORNEK))
        self.assertEqual([x[0] for x in o], sorted(x[0] for x in o))
        self.assertEqual(sum(1 for x in o if x[1] == "makine"), 3)


@unittest.skipUnless(RENDER, "skia-python, numpy, scipy, soundfile ve ffmpeg gerekir")
class Render(unittest.TestCase):
    def test_kare_ve_kisa_video(self):
        import cizim
        import risograf
        s = zaman.yukle(ORNEK); s["sure"] = 1.0; s["sayfalar"] = s["sayfalar"][:1]; s["sayfalar"][0]["_son"] = 1.0
        s["seslendirme"] = {"satirlar": []}
        for o in s["sayfalar"][0]["ogeler"]:
            o["t"] = min(o.get("t", 0), 0.5); o.pop("bitis_t", None)
        with tempfile.TemporaryDirectory() as tmp:
            k = cizim.kareler(s, "16x9", 480, 270, [0.8], Path(tmp))
            self.assertTrue(k[0].exists())
            out = risograf.render(s, Path(tmp), ["1x1"])
            self.assertTrue(all(p.exists() and p.stat().st_size > 0 for p in out))


if __name__ == "__main__":
    unittest.main()
