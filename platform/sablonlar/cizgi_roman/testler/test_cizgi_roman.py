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
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar" / "cizgi-roman.json"
RENDER = all(importlib.util.find_spec(m) for m in ("skia", "numpy", "scipy", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "cizgi-roman.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_vuruslar_ve_muzik(self):
        s = zaman.yukle(ORNEK)
        self.assertEqual(zaman.vuruslar(s), [1.35, 4.5, 6.85])
        self.assertEqual((s["muzik"]["yukselis"], s["muzik"]["sakin"], s["muzik"]["final"]), (3.0, 6.0, 8.0))

    def test_bilinmeyen_oge(self):
        h = copy.deepcopy(self.ham); h["sahneler"][0]["paneller"][0]["ogeler"][0]["tur"] = "ejderha"
        self.assertTrue(any("tur" in x for x in zaman.denetle(yaz(h))))

    def test_palette_olmayan_renk(self):
        h = copy.deepcopy(self.ham); h["sahneler"][0]["paneller"][0]["zemin"] = "mor"
        self.assertTrue(any("mor" in x for x in zaman.denetle(yaz(h))))

    def test_oge_sahne_disi(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["paneller"][0]["ogeler"][1]["sayac"]["bitis_t"] = 6.5
        self.assertTrue(any("bitis_t" in x for x in zaman.denetle(yaz(h))))

    def test_patlama_metin_ve_sayac_birden(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["paneller"][0]["ogeler"][1]["metin"] = "X"
        self.assertTrue(any("tam biri" in x for x in zaman.denetle(yaz(h))))

    def test_uc_panel_olmaz(self):
        h = copy.deepcopy(self.ham); p = h["sahneler"][2]["paneller"]; p.append(copy.deepcopy(p[0]))
        self.assertTrue(any("panel" in x for x in zaman.denetle(yaz(h))))

    def test_bicim_ezme(self):
        s = zaman.bicim_icin(zaman.yukle(ORNEK), "16x9")
        o = s["sahneler"][3]["paneller"][0]["ogeler"][1]
        self.assertEqual((o["x"], o["kuyruk"]), (0.27, [520, 330]))
        self.assertNotIn("16x9", o)

    def test_seslendirme_cakismasi(self):
        h = zaman.yukle(ORNEK)
        self.assertTrue(any("v0" in x for x in zaman.denetle(h, {"v0": 4.0})))

    def test_ses_olaylari_sirali(self):
        o = zaman.ses_olaylari(zaman.yukle(ORNEK))
        self.assertEqual([x[0] for x in o], sorted(x[0] for x in o))
        self.assertEqual(sum(1 for x in o if x[1] == "darbe"), 3)


@unittest.skipUnless(RENDER, "skia-python, numpy, scipy, soundfile ve ffmpeg gerekir")
class Render(unittest.TestCase):
    def test_kare_ve_kisa_video(self):
        sys.path.insert(0, str(HERE))
        import cizim
        import cizgi_roman
        s = zaman.yukle(ORNEK); s["sure"] = 1.0; s["sahneler"] = s["sahneler"][:1]; s["sahneler"][0]["_son"] = 1.0
        s["seslendirme"] = {"satirlar": []}
        for o in s["sahneler"][0]["paneller"][0]["ogeler"]:
            if o["tur"] == "patlama": o["t"] = 0.5
            if o["tur"] == "takvim": o["bitis_t"], o["cikis_t"] = 0.4, 0.45
        with tempfile.TemporaryDirectory() as tmp:
            k = cizim.kareler(s, "16x9", 480, 270, [0.6], Path(tmp))
            self.assertTrue(k[0].exists())
            out = cizgi_roman.render(s, Path(tmp), ["9x16"])
            self.assertTrue(all(p.exists() and p.stat().st_size > 0 for p in out))


if __name__ == "__main__":
    unittest.main()
