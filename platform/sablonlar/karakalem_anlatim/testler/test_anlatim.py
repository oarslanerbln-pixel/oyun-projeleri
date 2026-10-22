import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import zaman  # noqa: E402

DEPO = HERE.parents[2]
ORNEK = DEPO / "ornekler" / "karakalem-anlatim" / "anlatim.json"
SKIA = all(importlib.util.find_spec(m) for m in ("numpy", "skia", "soundfile")) and shutil.which("ffmpeg")


def yukle(ham: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "anlatim.json"
        p.write_text(json.dumps(ham, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_gecer_ve_her_tip_var(self):
        s = yukle(self.ham)
        self.assertEqual(zaman.denetle(s), [])
        self.assertEqual({x["tip"] for x in s["sahneler"]}, set(zaman.TIPLER))
        self.assertAlmostEqual(s["sure"], sum(x["sure"] for x in self.ham["sahneler"]))

    def test_hatalar_yakalanir(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][0]["metin"] = "x" * 60
        h["sahneler"][1]["sehirler"].append("Atlantis")
        h["sahneler"][2]["poz"] = "dans"
        h["sahneler"][7]["vurgu"] = 9
        h["sahneler"][5]["sure"] = 1
        hatalar = " | ".join(zaman.denetle(yukle(h)))
        for parca in ("en çok 40", "Atlantis", "poz", "vurgu", "sure"):
            self.assertIn(parca, hatalar)

    def test_seslendirme_tasmasi(self):
        s = yukle(self.ham)
        self.assertTrue(any("bitmiyor" in x for x in zaman.denetle(s, {"v1": 9.0, "v2": 1.0, "v3": 1.0})))

    def test_sayi_bicimi_korunur(self):
        for d in ("%37", "1.200", "3,5 kat", "37x"):
            on, x, son, o = zaman.sayi_parcala(d)
            self.assertEqual(zaman.sayi_yaz(on, x, son, o, d), d)

    def test_sahne_an(self):
        s = yukle(self.ham)
        sh, u = zaman.sahne_an(s, 6.0)
        self.assertEqual(sh["tip"], "harita"); self.assertAlmostEqual(u, 0.5)


@unittest.skipUnless(SKIA, "skia, numpy, soundfile ve ffmpeg gerekli")
class Cizim(unittest.TestCase):
    def test_kontakt_ve_kisa_render(self):
        import anlatim
        ham = json.loads(ORNEK.read_text(encoding="utf-8"))
        ham["sahneler"] = [dict(ham["sahneler"][0], sure=2.5), dict(ham["sahneler"][5], sure=2.5)]
        ham["seslendirme"]["satirlar"] = []
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "anlatim.json"
            p.write_text(json.dumps(ham, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(anlatim.main(["kontakt", str(p)]), 0)
            self.assertEqual(anlatim.main(["render", str(p), "--format", "1x1"]), 0)
            self.assertTrue((Path(tmp) / "cikti" / "dalga-almanya-karakalem-1x1.mp4").stat().st_size > 10000)


if __name__ == "__main__":
    unittest.main()
