import unittest

from atolye.brief import parse_brief, validate_brief
from atolye.formats import FORMATS
from atolye.issues import ERROR, WARNING

from .helpers import brief, messages

KNOWN = set(FORMATS)


class BriefTests(unittest.TestCase):
    def test_valid_brief(self):
        self.assertEqual(validate_brief(brief(), KNOWN), [])

    def test_required_fields(self):
        for name in ("objective", "audience", "insight", "proposition", "kpi"):
            with self.subTest(name=name):
                issues = validate_brief(brief(**{name: "  "}), KNOWN)
                self.assertIn(f"brif.{name}: zorunlu alan boş", messages(issues, ERROR))

    def test_long_proposition_warns(self):
        issues = validate_brief(brief(proposition=" ".join(["söz"] * 13)), KNOWN)
        self.assertTrue(messages(issues, WARNING))
        self.assertFalse(messages(issues, ERROR))

    def test_double_proposition_warns(self):
        issues = validate_brief(brief(proposition="Hızlı ve ucuz"), KNOWN)
        self.assertTrue(any("'ve'" in m for m in messages(issues, WARNING)))

    def test_unknown_channel(self):
        issues = validate_brief(brief(channels=["billboard"]), KNOWN)
        self.assertTrue(any("billboard" in m for m in messages(issues, ERROR)))

    def test_missing_proof_warns(self):
        issues = validate_brief(brief(reasons_to_believe=[]), KNOWN)
        self.assertTrue(messages(issues, WARNING))

    def test_parse(self):
        b = parse_brief(brief())
        self.assertEqual(b.channels, ("reels",))
        self.assertEqual(b.cta, "Hemen dene")


if __name__ == "__main__":
    unittest.main()
