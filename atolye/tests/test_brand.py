import unittest

from atolye.brand import parse_brand, validate_brand
from atolye.issues import ERROR, WARNING

from .helpers import brand, messages


class BrandValidationTests(unittest.TestCase):
    def test_valid_brand_has_no_issues(self):
        self.assertEqual(validate_brand(brand()), [])

    def test_missing_required_color_role(self):
        b = brand(); del b["colors"]["text"]
        self.assertTrue(any("colors.text" in m for m in messages(validate_brand(b), ERROR)))

    def test_bad_hex(self):
        b = brand(); b["colors"]["accent"] = "sarı"
        self.assertTrue(any("colors.accent" in m for m in messages(validate_brand(b), ERROR)))

    def test_low_text_contrast_is_error(self):
        b = brand(); b["colors"]["text"] = "#cccccc"
        self.assertTrue(any("kontrast" in m for m in messages(validate_brand(b), ERROR)))

    def test_bad_id(self):
        self.assertTrue(messages(validate_brand(brand(id="Test Marka")), ERROR))

    def test_bad_font_weight(self):
        b = brand(); b["typography"]["body"]["weight"] = 450
        self.assertTrue(any("weight" in m for m in messages(validate_brand(b), ERROR)))

    def test_missing_tone_is_only_warning(self):
        b = brand(voice={"forbidden": []})
        issues = validate_brand(b)
        self.assertEqual(messages(issues, ERROR), [])
        self.assertTrue(messages(issues, WARNING))

    def test_not_an_object(self):
        self.assertTrue(messages(validate_brand([]), ERROR))


class BrandModelTests(unittest.TestCase):
    def test_parse_lowercases_colors_and_defaults_weight(self):
        b = brand(); b["colors"]["accent"] = "#FFCC00"
        parsed = parse_brand(b)
        self.assertEqual(parsed.color("accent"), "#ffcc00")
        self.assertEqual(parsed.typography["body"].weight, 400)
        self.assertEqual(parsed.logo_text, "TEST")

    def test_forbidden_hits_whole_words_case_insensitive(self):
        parsed = parse_brand(brand())
        self.assertEqual(parsed.forbidden_hits("Şehrin EN İYİ kahvesi"), ["en iyi"])
        self.assertEqual(parsed.forbidden_hits("Şehrin en iyi kahvesi"), ["en iyi"])
        self.assertEqual(parsed.forbidden_hits("Mucize gibi"), ["mucize"])
        self.assertEqual(parsed.forbidden_hits("mucizevi değil"), [])

    def test_fold_handles_turkish_dotted_and_dotless_i(self):
        from atolye.brand import fold
        self.assertEqual(fold("İYİ"), "iyi")
        self.assertEqual(fold("KIRMIZI"), fold("kırmızı"))


if __name__ == "__main__":
    unittest.main()
