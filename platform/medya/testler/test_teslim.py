import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import teslim  # noqa: E402


class TeslimTests(unittest.TestCase):
    def setUp(self):
        self.a = teslim.yukle()

    def test_presets_from_architecture(self):
        for ad in ("yatay-master", "yatay-web", "dikey", "kare", "dikey-akis", "sessiz-gif", "steam-fragman"):
            self.assertIn(ad, self.a)

    def test_ratios(self):
        self.assertEqual(self.a["dikey"].oran, "9:16")
        self.assertEqual(self.a["dikey-akis"].oran, "4:5")
        self.assertEqual(self.a["yatay-master"].oran, "16:9")

    def test_every_limit_is_dated(self):
        for a in self.a.values():
            if a.sure_siniri:
                datetime.date.fromisoformat(a.sinir_kontrol)

    def test_safe_area_is_sane(self):
        for a in self.a.values():
            self.assertLess(a.guvenli_ust + a.guvenli_alt, 0.5, a.ad)
            self.assertLess(a.guvenli_yan * 2, 0.5, a.ad)


if __name__ == "__main__":
    unittest.main()
