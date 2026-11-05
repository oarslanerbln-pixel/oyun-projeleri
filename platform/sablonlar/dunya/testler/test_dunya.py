import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BURADA = Path(__file__).resolve().parents[1]
DEPO = BURADA.parents[2]
sys.path.insert(0, str(BURADA))
import dunya  # noqa: E402

ORNEK = json.loads((DEPO / "ornekler/dunya-1961/dunya.json").read_text(encoding="utf-8"))
HAZIR = importlib.util.find_spec("playwright") is not None and (BURADA / "node_modules/d3-geo").exists()


class SahneTest(unittest.TestCase):
    def test_sahne_coz(self):
        s = dunya.sahne_coz(ORNEK, "9x16", 1)
        self.assertEqual((s["W"], s["H"]), (1080, 1920))
        self.assertEqual([r["etiket"] for r in s["rota"]], ["İstanbul", "Münih"])
        self.assertTrue(1500 < s["km"] < 1650)
        self.assertEqual(s["vurgu"][0]["ad"], "Turkey")
        self.assertTrue(all(n["nufus"] for n in s["noktalar"]))

    def test_motor_kaplamalari(self):
        motor = (BURADA / "motor.js").read_text(encoding="utf-8")
        for k in dunya.KAPLAMALAR:
            self.assertIn(f"STILLER.{k} = {{", motor)


@unittest.skipUnless(HAZIR, "playwright ya da npm bağımlılıkları yok (dunya.py kur)")
class CizimTest(unittest.TestCase):
    def test_her_kaplama_bir_kare(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as t:
            for k in dunya.KAPLAMALAR:
                p = dunya.kareler({**ORNEK, "kaplama": k}, [9.0], "16x9", Path(t), ss=0.5)[0]
                a = np.asarray(__import__("PIL.Image", fromlist=["Image"]).open(p).convert("RGB"))
                self.assertEqual(a.shape, (1080, 1920, 3))
                self.assertGreater(a.std(), 10, k)  # boş kare değil


if __name__ == "__main__":
    unittest.main()
