import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path

from atolye import cli, project, render, tokens
from atolye.brand import parse_brand

from .helpers import board, brand, brief

EXAMPLE = Path(__file__).resolve().parents[1] / "ornekler" / "demo-kahve"


def write_project(root: Path, b=None, br=None, boards=None):
    (root / "marka.json").write_text(json.dumps(b or brand()), encoding="utf-8")
    (root / "brif.json").write_text(json.dumps(br or brief()), encoding="utf-8")
    for name, data in (boards or {"storyboard": board()}).items():
        (root / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


class ProjectLoadTests(unittest.TestCase):
    def test_example_project_is_clean(self):
        proj, issues = project.load(EXAMPLE)
        self.assertEqual([str(i) for i in issues], [])
        self.assertEqual(set(proj.storyboards), {"storyboard-reels", "storyboard-bumper"})

    def test_missing_files_and_bad_json(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "marka.json").write_text("{ bozuk", encoding="utf-8")
            proj, issues = project.load(d)
            self.assertIsNone(proj)
            text = "\n".join(map(str, issues))
            self.assertIn("geçersiz JSON", text)
            self.assertIn("brif.json", text)
            self.assertIn("storyboard", text)

    def test_storyboard_issues_are_prefixed_with_file(self):
        with tempfile.TemporaryDirectory() as d:
            write_project(Path(d), boards={"storyboard-kisa": board(fps=29)})
            proj, issues = project.load(d)
            self.assertIsNone(proj)
            self.assertTrue(any(i.where.startswith("storyboard-kisa:") for i in issues))


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.brand = parse_brand(brand(id="demli-kahve"))

    def test_css(self):
        css = tokens.to_css(self.brand)
        self.assertIn("--color-on-primary: #ffffff;", css)
        self.assertIn('--font-heading-family: "Inter";', css)

    def test_dtcg(self):
        doc = json.loads(tokens.to_dtcg(self.brand))
        self.assertEqual(doc["color"]["accent"], {"$type": "color", "$value": "#ffcc00"})
        self.assertEqual(doc["font"]["heading"]["weight"]["$value"], 700)

    def test_unity(self):
        cs = tokens.to_unity(self.brand)
        self.assertIn("public static class DemliKahveTokens", cs)
        self.assertIn("OnPrimary = new Color32(255, 255, 255, 255);", cs)
        self.assertEqual(cs.count("{"), cs.count("}"))


class RenderTests(unittest.TestCase):
    def test_wrap_respects_width(self):
        lines = render.wrap("bir iki üç dört beş altı yedi sekiz", size=10, max_width=60)
        self.assertTrue(all(len(l) <= int(60 / (10 * render.CHAR_WIDTH)) for l in lines))
        self.assertEqual(" ".join(lines), "bir iki üç dört beş altı yedi sekiz")

    def test_wrap_keeps_overlong_word(self):
        self.assertEqual(render.wrap("çokuzunbirsözcük", size=10, max_width=20), ["çokuzunbirsözcük"])

    def test_build_writes_everything(self):
        proj, _ = project.load(EXAMPLE)
        with tempfile.TemporaryDirectory() as d:
            written = render.build(proj, d)
            rel = {str(p.relative_to(d)) for p in written}
            for expected in ("belirtecler/tokens.css", "belirtecler/tokens.json",
                             "belirtecler/DemliKahveTokens.cs", "brif.md",
                             "storyboard-reels/manifest.json", "storyboard-reels/animatik.html",
                             "storyboard-reels/kareler/01-acilis.svg",
                             "storyboard-bumper/kareler/02-cagri.svg"):
                self.assertIn(expected, rel)

            for svg in Path(d).rglob("*.svg"):
                ET.fromstring(svg.read_text(encoding="utf-8"))  # iyi biçimli XML

            m = json.loads((Path(d) / "storyboard-reels" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(m["format"]["aspect"], "9:16")
            self.assertEqual(m["frames"], 14 * 30)
            self.assertEqual(m["scenes"][0]["start_frame"], 0)
            for s in m["scenes"]:
                self.assertTrue((Path(d) / "storyboard-reels" / s["frame_file"]).exists())

            html = (Path(d) / "storyboard-reels" / "animatik.html").read_text(encoding="utf-8")
            self.assertEqual(html.count('class="scene '), len(m["scenes"]))
            self.assertIn("--color-primary", html)

    def test_text_is_escaped(self):
        data = board(scenes=[{"id": "a", "duration": 2, "headline": "<b>A & B</b>", "show_logo": True,
                              "cta": True}])
        with tempfile.TemporaryDirectory() as d:
            write_project(Path(d), boards={"storyboard": data})
            proj, issues = project.load(d)
            self.assertIsNotNone(proj, [str(i) for i in issues])
            render.build(proj, Path(d) / "out")
            svg = (Path(d) / "out" / "storyboard" / "kareler" / "01-a.svg").read_text(encoding="utf-8")
            self.assertIn("&lt;b&gt;A &amp; B&lt;/b&gt;", svg)
            ET.fromstring(svg)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(list(argv))
        return code, buf.getvalue()

    def test_check_example(self):
        code, out = self.run_cli("denetle", str(EXAMPLE))
        self.assertEqual(code, 0, out)
        self.assertIn("Tamam: Demli Kahve", out)

    def test_check_fails_on_errors(self):
        with tempfile.TemporaryDirectory() as d:
            code, out = self.run_cli("denetle", d)
            self.assertEqual(code, 1)
            self.assertIn("HATA", out)

    def test_new_then_build(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "yeni-marka"
            code, _ = self.run_cli("yeni", str(root), "--ad", "Yeni Marka")
            self.assertEqual(code, 0)
            code, out = self.run_cli("denetle", str(root))
            self.assertEqual(code, 0, out)
            code, out = self.run_cli("uret", str(root), "-o", str(Path(d) / "cikti"))
            self.assertEqual(code, 0, out)
            self.assertTrue((Path(d) / "cikti" / "storyboard" / "animatik.html").exists())

    def test_new_refuses_non_empty_folder(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x").write_text("x")
            import contextlib
            with contextlib.redirect_stderr(io.StringIO()):
                code, _ = self.run_cli("yeni", d)
            self.assertEqual(code, 2)

    def test_formats(self):
        code, out = self.run_cli("bicimler")
        self.assertEqual(code, 0)
        self.assertIn("reels", out)


if __name__ == "__main__":
    unittest.main()
