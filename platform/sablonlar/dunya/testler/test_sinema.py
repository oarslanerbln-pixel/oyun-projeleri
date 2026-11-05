import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "sinema"))


class SinemaSahne(unittest.TestCase):
    def test_ornekler_cozulur(self):
        import json
        import sinema
        for yol in sorted((KOK.parents[2] / "ornekler" / "dunya-sinema").glob("*.json")):
            s = json.loads(yol.read_text(encoding="utf-8"))
            for fmt in ("16x9", "9x16"):
                c = sinema.sahne_coz(s, fmt)
                self.assertGreaterEqual(len(c["kamera"]), 2, yol.name)
                self.assertEqual(len(c["odak"]), 4)
                for k in c["kamera"]:
                    self.assertEqual(len(k["hedef"]), 2)
                    self.assertIsInstance(k["irtifa"], float)
                if fmt == "9x16":
                    self.assertTrue(all(k["kayX"] == 0 for k in c["kamera"]))

    def test_konum(self):
        import sinema
        lo, la, et = sinema._konum("Türkiye")
        self.assertTrue(25 < lo < 45 and 35 < la < 43)
        self.assertEqual(sinema._konum([10, 20])[:2], (10.0, 20.0))


if __name__ == "__main__":
    unittest.main()


class GrafikStilleri(unittest.TestCase):
    def test_her_stil_markada_ve_grafik_js_te(self):
        import json
        import sinema
        mj = json.loads((KOK / "sinema" / "marka.json").read_text())
        js = (KOK / "sinema" / "grafik.js").read_text()
        for ad in sinema.GRAFIKLER:
            self.assertIn(ad, mj["grafikler"], ad)
            if ad != "belgesel":
                self.assertIn(f"\n    {ad}: {{", js, ad)
            m = sinema._birlestir(mj["varsayilan"], mj["grafikler"][ad])
            for rol in ("ana", "karsi", "dost", "notr"):
                self.assertTrue(m["roller"][rol]["dolgu"].startswith("#"))
            for k, y in m["yazi"].items():  # her yazı ailesi gömülü olmalı
                self.assertIn(y["aile"], sinema.AILE.values(), f"{ad}.{k}")

    def test_birlestir_derin(self):
        import sinema
        m = sinema._birlestir({"a": {"x": 1, "y": 2}, "b": 1}, {"a": {"y": 3}})
        self.assertEqual(m, {"a": {"x": 1, "y": 3}, "b": 1})
