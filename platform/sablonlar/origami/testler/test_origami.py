import copy
import importlib.util
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import zaman  # noqa: E402

DEPO = HERE.parents[2]
ORNEK = DEPO / "ornekler" / "tuzak-fiyat-origami" / "origami.json"
SKIA = all(importlib.util.find_spec(m) for m in ("skia", "numpy", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "origami.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_varsayilanlar(self):
        s = zaman.yukle(ORNEK)
        self.assertEqual(s["muzik"]["dusus"], 4.9)  # ilk öne çıkış
        self.assertEqual(s["sahneler"][0]["gecis"], "kesme")
        self.assertEqual(s["sahneler"][1]["gecis"], "katla")
        self.assertEqual(s["sahneler"][-1]["_son"], 10)

    def test_nesne_zamani_sahne_disi(self):
        h = copy.deepcopy(self.ham); h["sahneler"][0]["nesneler"][2]["one_t"] = 8.0
        self.assertTrue(any("one_t" in x for x in zaman.denetle(yaz(h))))

    def test_nesne_gelmeden_etiket(self):
        h = copy.deepcopy(self.ham); h["sahneler"][0]["nesneler"][1]["etiket_t"] = 2.0
        self.assertTrue(any("gelmeden" in x for x in zaman.denetle(yaz(h))))

    def test_bilinmeyenler(self):
        h = copy.deepcopy(self.ham)
        h["sahneler"][0]["nesneler"][0]["tur"] = "sise"
        h["sahneler"][0]["nesneler"][1]["id"] = "kucuk"
        h["sahneler"][1]["gecis"] = "iris"
        hatalar = zaman.denetle(yaz(h))
        self.assertTrue(any("tür" in x for x in hatalar))
        self.assertTrue(any("benzersiz" in x for x in hatalar))
        self.assertTrue(any("geçiş" in x for x in hatalar))

    def test_seslendirme_cakismasi(self):
        hatalar = zaman.denetle(zaman.yukle(ORNEK), {"v0": 3.0})
        self.assertTrue(any("v0" in x and "bitmiyor" in x for x in hatalar))

    def test_palet(self):
        h = copy.deepcopy(self.ham); h["palet"]["vurgu"] = "turuncu"
        self.assertTrue(any("palet.vurgu" in x for x in zaman.denetle(yaz(h))))


class Zamanlama(unittest.TestCase):
    def setUp(self):
        self.s = zaman.yukle(ORNEK)

    def test_ses_olaylari(self):
        o = zaman.ses_olaylari(self.s)
        self.assertEqual([x[0] for x in o], sorted(x[0] for x in o))
        self.assertTrue(all(0 <= x[0] < self.s["sure"] for x in o))
        anlar = [(x[0], x[1]) for x in o]
        self.assertIn((4.9, "pat"), anlar)          # öne çıkış darbesi
        self.assertIn((7.2, "pat"), anlar)          # sayfa kapanır
        self.assertIn((3.15 - 0.25, "kayma"), anlar)  # orta gelince diğerleri yer açar
        self.assertNotIn((0.25 - 0.25, "kayma"), anlar)  # açılış nesneleri kaymaz

    def test_darbeler(self):
        self.assertEqual(zaman.darbeler(self.s), [(4.9, 9), (7.2, 6)])


@unittest.skipUnless(SKIA, "skia-python / numpy / soundfile / ffmpeg yok")
class Render(unittest.TestCase):
    def test_katlanma_matrisi(self):
        import cizim
        A, B = (0.0, 0.0), (0.0, 1.0)  # dikey menteşe
        M = cizim.Cizici.kat(A, B, math.pi)  # tam katlanınca yansır
        p = M.mapXY(2, 3)
        self.assertAlmostEqual(p.x(), -2, places=5); self.assertAlmostEqual(p.y(), 3, places=5)
        self.assertLess(cizim.Cizici.det(M), 0)  # arka yüz
        p = cizim.Cizici.kat(A, B, 0).mapXY(2, 3)
        self.assertAlmostEqual(p.x(), 2, places=5)

    def test_kare_ve_ses(self):
        import cizim
        import sentez
        s = zaman.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            k = cizim.kareler(s, 270, 480, [0.5, 5.6, 6.9, 9.6], Path(tmp))
            self.assertEqual(len(k), 4)
            self.assertTrue(all(p.stat().st_size > 1000 for p in k))
            k = cizim.kareler(s, 480, 270, [5.6], Path(tmp))
            self.assertEqual(len(k), 1)
            bilgi = sentez.miksle(s, Path(tmp))
            self.assertEqual(bilgi["seslendirme"], [])
            self.assertTrue((Path(tmp) / "ses.wav").exists())


if __name__ == "__main__":
    unittest.main()
