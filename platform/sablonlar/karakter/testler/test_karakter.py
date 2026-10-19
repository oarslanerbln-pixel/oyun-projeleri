import copy
import importlib.util
import json
import math
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import agiz  # noqa: E402
import iskelet  # noqa: E402
import senaryo  # noqa: E402

DEPO = HERE.parents[2]
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar" / "cizgisel.json"
SKIA = all(importlib.util.find_spec(m) for m in ("skia", "numpy", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "cizgisel.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return senaryo.yukle(p)


class Iskelet(unittest.TestCase):
    def test_ayakta_simetrik_ve_yere_basar(self):
        g = iskelet.govde_kur(iskelet.poz("ayakta"))
        self.assertAlmostEqual(min(g.ayak["sol"][1], g.ayak["sag"][1]), 0.0)
        self.assertAlmostEqual(g.el["sol"][0], -g.el["sag"][0])
        self.assertLess(g.omuz["sol"][0], 0)   # sol ekranın solunda
        self.assertGreater(g.bas[1], g.boyun[1])

    def test_el_kaldir_el_basin_ustunde(self):
        g = iskelet.govde_kur(iskelet.poz("el_kaldir"))
        self.assertGreater(g.el["sag"][1], g.bas[1])
        self.assertGreater(g.el["sag"][0], g.bas[0] + g.oran.bas_yaricap)  # el başın arkasında kalmaz

    def test_kol_uzunlugu_korunur(self):
        for ad in iskelet.POZ_ADLARI:
            g = iskelet.govde_kur(iskelet.poz(ad))
            for t in ("sol", "sag"):
                self.assertAlmostEqual(math.dist(g.omuz[t], g.dirsek[t]), g.oran.ust_kol)
                self.assertAlmostEqual(math.dist(g.dirsek[t], g.el[t]), g.oran.alt_kol)

    def test_gecis_yumusak(self):
        self.assertEqual((iskelet.yumusak(0), iskelet.yumusak(1)), (0, 1))
        self.assertAlmostEqual(iskelet.yumusak(0.5), 0.5)

    def test_goz_kirpar(self):
        anlar = [i / 30 for i in range(30 * 10)]
        self.assertTrue(any(iskelet.goz_kirp(t) < 0.3 for t in anlar))
        self.assertGreater(sum(iskelet.goz_kirp(t) == 1 for t in anlar) / len(anlar), 0.9)


class Agiz(unittest.TestCase):
    def test_harflerden(self):
        h = {"karakterler": list("mama"), "bas": [0.0, 0.1, 0.2, 0.3], "son": [0.1, 0.2, 0.3, 0.4]}
        acik, bicim = agiz.harflerden(h, 0.7)
        self.assertEqual(bicim[5], "M")
        self.assertEqual(bicim[15], "A")
        self.assertGreater(acik[18], 0.5)
        self.assertLess(acik[65], 0.1)   # sonda kapanır

    def test_genlikten_ve_an(self):
        with tempfile.TemporaryDirectory() as tmp:
            yol = Path(tmp) / "v.wav"
            with wave.open(str(yol), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
                ornek = [int(12000 * math.sin(i * 0.05)) if 4000 < i < 12000 else 0 for i in range(16000)]
                w.writeframes(b"".join(x.to_bytes(2, "little", signed=True) for x in ornek))
            a = agiz.Agiz()
            self.assertEqual(a.ekle(2.0, yol, Path(tmp) / "yok.json"), "genlik")
            self.assertLess(a.an(2.1)[0], 0.1)
            self.assertGreater(a.an(2.5)[0], 0.5)
            self.assertFalse(a.an(5.0)[2])


class Senaryo(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(senaryo.denetle(senaryo.yukle(ORNEK)), [])

    def test_bilinmeyen_poz_ve_nesne(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["poz"] = "uc"; h["sahneler"][2]["nesne"]["tur"] = "roket"
        hatalar = senaryo.denetle(yaz(h))
        self.assertTrue(any("poz 'uc'" in x for x in hatalar))
        self.assertTrue(any("roket" in x for x in hatalar))

    def test_sesin_sigmasi(self):
        hatalar = senaryo.denetle(senaryo.yukle(ORNEK), {"v5": 9.0})
        self.assertTrue(any("sığmıyor" in x for x in hatalar))

    def test_poz_gecisi_ve_durum(self):
        s = senaryo.yukle(ORNEK)
        _, ad = senaryo.poz_at(s, 7.0)
        self.assertEqual(ad, "el_kaldir")
        g, y, x = senaryo.durum(s, 13.0)
        self.assertGreater(y.mutlu_goz, 0.5)
        self.assertEqual(x, 0.0)


@unittest.skipUnless(SKIA, "skia/numpy/soundfile/ffmpeg yok")
class Cizim(unittest.TestCase):
    def test_kare_bos_degil(self):
        import cizim
        s = senaryo.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            for f, (W, H) in {"9x16": (270, 480), "16x9": (480, 270)}.items():
                p = cizim.kareler(s, W, H, [7.5], Path(tmp))[0]
                self.assertGreater(p.stat().st_size, 2000)


if __name__ == "__main__":
    unittest.main()
