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
