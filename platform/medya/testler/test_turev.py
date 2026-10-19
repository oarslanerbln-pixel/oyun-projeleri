import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import teslim  # noqa: E402
import turev  # noqa: E402


class KirpmaTests(unittest.TestCase):
    def test_wide_to_vertical_centered(self):
        self.assertEqual(turev.kirpma(1920, 1080, 1080, 1920), (608, 1080, 656, 0))

    def test_focus_moves_window_and_stops_at_edge(self):
        w, h, x, y = turev.kirpma(1920, 1080, 1080, 1080, 0.25, 0.5)
        self.assertEqual((w, h, x), (1080, 1080, 0))  # 0.25·1920 − 540 < 0 → kenarda
        self.assertEqual(turev.kirpma(1920, 1080, 1080, 1080, 1.0, 0.5)[2], 840)

    def test_tall_to_wide_crops_height(self):
        self.assertEqual(turev.kirpma(1080, 1920, 1920, 1080, 0.5, 0.0), (1080, 608, 0, 0))

    def test_dimensions_are_even(self):
        w, h, _, _ = turev.kirpma(1279, 719, 1080, 1350)
        self.assertEqual((w % 2, h % 2), (0, 0))


class KomutTests(unittest.TestCase):
    def setUp(self):
        self.a = teslim.yukle()

    def test_loudness_from_preset(self):
        cmd = turev.komut("a.mp4", "b.mp4", self.a["dikey"], 1920, 1080, True, 0.6, 0.4)
        self.assertIn("crop=608:1080:848:0,scale=1080:1920:flags=lanczos,setsar=1", cmd)
        self.assertIn("loudnorm=I=-14:TP=-1:LRA=11", cmd)

    def test_silent_input_or_preset_drops_audio(self):
        self.assertIn("-an", turev.komut("a.mp4", "b.mp4", self.a["dikey"], 1920, 1080, False))
        self.assertIn("-an", turev.komut("a.mp4", "b.mp4", self.a["sessiz-gif"], 1920, 1080, True))


if __name__ == "__main__":
    unittest.main()
