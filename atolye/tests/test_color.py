import unittest

from atolye import color


class ColorTests(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(color.contrast_ratio("#000000", "#ffffff"), 21.0, places=2)

    def test_same_color_is_1(self):
        self.assertAlmostEqual(color.contrast_ratio("#777777", "#777777"), 1.0)

    def test_ratio_is_symmetric(self):
        self.assertAlmostEqual(color.contrast_ratio("#3b2418", "#f7efe4"),
                               color.contrast_ratio("#f7efe4", "#3b2418"))

    def test_known_wcag_value(self):
        # #777777 beyaz üstünde 4.48: AA gövde metnini kıl payı geçemez.
        self.assertAlmostEqual(color.contrast_ratio("#777777", "#ffffff"), 4.48, places=2)

    def test_is_hex(self):
        self.assertTrue(color.is_hex("#A1b2C3"))
        for bad in ("#fff", "a1b2c3", "#12345g", 123, None):
            self.assertFalse(color.is_hex(bad), bad)

    def test_to_rgb_rejects_short_hex(self):
        with self.assertRaises(ValueError):
            color.to_rgb("#fff")


if __name__ == "__main__":
    unittest.main()
