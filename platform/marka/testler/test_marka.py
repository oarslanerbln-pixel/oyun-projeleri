import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import marka  # noqa: E402

TEMEL = {
    "kimlik": "test-marka",
    "ad": "Test Marka",
    "renk": {
        "ana": {"$type": "color", "$value": "#000000"},
        "ana-ustu": {"$type": "color", "$value": "#ffffff"},
        "zemin": {"$type": "color", "$value": "#ffffff"},
        "metin": {"$type": "color", "$value": "#111111"},
        "isik": {"sicak": {"$type": "color", "$value": "#FFB36B"}},
    },
    "ciftler": [{"on": "metin", "zemin": "zemin"}, {"on": "ana-ustu", "zemin": "ana"}],
    "yazi": {
        "baslik": {"aile": {"$type": "fontFamily", "$value": "Inter"},
                   "agirlik": {"$type": "fontWeight", "$value": 700}},
        "govde": {"aile": {"$type": "fontFamily", "$value": "Inter"}},
    },
    "logo": {"metin": "TEST"},
    "hareket": {"giris": {"$type": "duration", "$value": "400ms"},
                "egri": {"$type": "cubicBezier", "$value": [0.2, 0, 0, 1]}},
    "ses": {"ton": ["net"], "yasak": ["mucize"]},
    "prompt": {"uslup": "Sabah ışığı.", "negatif": ["neon"]},
}


def veri(**over):
    d = copy.deepcopy(TEMEL)
    d.update(over)
    return d


def hatalar(d, kok=None):
    return [str(b) for b in marka.denetle(d, kok) if b.seviye == marka.HATA]


class RenkTests(unittest.TestCase):
    def test_contrast_extremes(self):
        self.assertAlmostEqual(marka.contrast_ratio("#000000", "#ffffff"), 21.0, places=2)
        self.assertAlmostEqual(marka.contrast_ratio("#777777", "#777777"), 1.0)

    def test_known_wcag_value(self):
        self.assertAlmostEqual(marka.contrast_ratio("#777777", "#ffffff"), 4.48, places=2)

    def test_is_hex(self):
        self.assertTrue(marka.is_hex("#A1b2C3"))
        for bad in ("#fff", "a1b2c3", "#12345g", 123, None):
            self.assertFalse(marka.is_hex(bad), bad)


class DenetleTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(marka.denetle(veri()), [])

    def test_required_colors(self):
        d = veri()
        del d["renk"]["metin"]
        self.assertTrue(any("renk.metin" in h for h in hatalar(d)))

    def test_bad_hex_and_type(self):
        d = veri()
        d["renk"]["ana"]["$value"] = "kahverengi"
        d["renk"]["vurgu"] = "#ffcc00"  # $type/$value nesnesi değil
        h = hatalar(d)
        self.assertTrue(any("renk.ana" in x for x in h))
        self.assertTrue(any("renk.vurgu" in x for x in h))

    def test_pair_contrast(self):
        d = veri()
        d["renk"]["ana-ustu"]["$value"] = "#222222"
        self.assertTrue(any("ciftler[1]" in h and "kontrast" in h for h in hatalar(d)))

    def test_pair_with_lower_threshold(self):
        d = veri(ciftler=[{"on": "metin", "zemin": "zemin"}, {"on": "isik.sicak", "zemin": "ana", "en_az": 3}])
        self.assertEqual(hatalar(d), [])

    def test_pair_threshold_cannot_go_below_large_text(self):
        d = veri(ciftler=[{"on": "metin", "zemin": "zemin", "en_az": 2}])
        self.assertTrue(any("en_az" in h for h in hatalar(d)))

    def test_text_on_background_checked_even_without_pair(self):
        d = veri(ciftler=[])
        d["renk"]["metin"]["$value"] = "#cccccc"
        self.assertTrue(any("zemin üstünde metin" in h for h in hatalar(d)))

    def test_pair_with_unknown_color(self):
        d = veri(ciftler=[{"on": "yok", "zemin": "zemin"}])
        self.assertTrue(any("tanımsız" in h for h in hatalar(d)))

    def test_type(self):
        d = veri()
        d["yazi"]["govde"]["agirlik"] = {"$type": "fontWeight", "$value": 450}
        del d["yazi"]["baslik"]
        h = hatalar(d)
        self.assertTrue(any("yazi.baslik" in x for x in h))
        self.assertTrue(any("agirlik" in x for x in h))

    def test_motion(self):
        d = veri(hareket={"giris": {"$type": "duration", "$value": "yavaş"},
                          "egri": {"$type": "cubicBezier", "$value": [2, 0, 0, 1]}})
        self.assertEqual(len(hatalar(d)), 2)

    def test_missing_logo_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = veri(logo={"dosya": "logo.svg"})
            self.assertTrue(any("logo.dosya" in h for h in hatalar(d, Path(tmp))))
            (Path(tmp) / "logo.svg").write_text("<svg/>")
            self.assertEqual(hatalar(d, Path(tmp)), [])

    def test_missing_tone_is_warning(self):
        b = marka.denetle(veri(ses={"yasak": []}))
        self.assertFalse(marka.has_errors(b))
        self.assertTrue(b)

    def test_not_an_object(self):
        self.assertTrue(marka.has_errors(marka.denetle([])))


class AktarTests(unittest.TestCase):
    def setUp(self):
        self.m = marka.ayristir(veri())

    def test_parse_flattens_nested_and_lowercases(self):
        self.assertEqual(self.m.renk_al("isik.sicak"), "#ffb36b")
        self.assertEqual(self.m.yazi["govde"].agirlik, 400)

    def test_css(self):
        css = marka.to_css(self.m)
        self.assertIn("--renk-isik-sicak: #ffb36b;", css)
        self.assertIn('--yazi-baslik-aile: "Inter";', css)
        self.assertIn("--hareket-egri: cubic-bezier(0.2, 0, 0, 1);", css)

    def test_unity_uss_has_no_motion(self):
        uss = marka.to_unity_uss(self.m)
        self.assertIn("--renk-ana: #000000;", uss)
        self.assertNotIn("hareket", uss)

    def test_unity_json(self):
        doc = json.loads(marka.to_unity_json(self.m))
        self.assertEqual(doc["renk"]["ana-ustu"], [1.0, 1.0, 1.0, 1.0])

    def test_figma_is_nested_dtcg(self):
        doc = json.loads(marka.to_figma(self.m))
        self.assertEqual(doc["renk"]["isik"]["sicak"], {"$type": "color", "$value": "#ffb36b"})
        self.assertEqual(doc["hareket"]["egri"]["$type"], "cubicBezier")
        self.assertEqual(doc["yazi"]["baslik"]["agirlik"]["$value"], 700)

    def test_prompt(self):
        text = marka.to_prompt(self.m)
        self.assertTrue(text.startswith("Sabah ışığı."))
        self.assertIn("isik.sicak #ffb36b", text)
        self.assertIn("Kaçın: neon.", text)


class CliTests(unittest.TestCase):
    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "marka.json"
            path.write_text(json.dumps(veri()), encoding="utf-8")
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(marka.main(["denetle", str(path)]), 0)
                self.assertEqual(marka.main(["aktar", "css", str(path)]), 0)
            self.assertIn("--renk-ana", buf.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(marka.main(["aktar", "pdf", str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
