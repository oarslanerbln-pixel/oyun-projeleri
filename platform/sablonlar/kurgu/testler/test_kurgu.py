import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import kurgu  # noqa: E402

DEPO = HERE.parents[2]
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar-uzun" / "kurgu.json"
NUMPY = all(importlib.util.find_spec(m) for m in ("numpy", "soundfile"))


def sahne(sure, satirlar=(), ic=()):
    return {"sure": sure, "seslendirme": {"satirlar": [{"id": i, "t": t, "metin": "x"} for i, t in satirlar]},
            "sahneler": [{"bas": b} for b in ic]}


class Kurgu(unittest.TestCase):
    def kur(self, k: dict, sahneler: dict) -> dict:
        self.tmp = tempfile.TemporaryDirectory()
        kok = Path(self.tmp.name)
        for ad, s in sahneler.items():
            (kok / ad).write_text(json.dumps(s), encoding="utf-8")
        (kok / "kurgu.json").write_text(json.dumps(k), encoding="utf-8")
        return kurgu.yukle(kok / "kurgu.json")

    def tearDown(self):
        if hasattr(self, "tmp"):
            self.tmp.cleanup()

    def test_ornek_denetim(self):
        k = kurgu.yukle(ORNEK)
        self.assertEqual(kurgu.denetle(k), [])
        self.assertGreater(k["sure"], 50)

    def test_zaman_cizelgesi_gecis_ortusmesi(self):
        k = self.kur({"gecis": {"tur": "erime", "sure": 0.5}, "sahneler": [
            {"id": "a", "stil": "kinetik", "senaryo": "a.json"},
            {"id": "b", "stil": "analiz", "senaryo": "b.json"},
            {"id": "c", "stil": "kinetik", "senaryo": "c.json", "gecis": "kesme"}]},
            {"a.json": sahne(10), "b.json": sahne(20, [("v0", 1.0)]), "c.json": sahne(5)})
        self.assertEqual([sh["_bas"] for sh in k["sahneler"]], [0.0, 9.5, 29.5])
        self.assertEqual(k["sure"], 34.5)
        sat = kurgu.satirlar(k)
        self.assertEqual(sat[0]["id"], "b-v0")
        self.assertAlmostEqual(sat[0]["t"], 10.5)

    def test_denetim_hatalari(self):
        k = self.kur({"sahneler": [
            {"id": "a", "stil": "yok", "senaryo": "a.json"},
            {"id": "b", "stil": "kinetik", "senaryo": "eksik.json"},
            {"id": "c", "stil": "kinetik", "senaryo": "a.json", "gecis": {"tur": "erime", "sure": 4}}]},
            {"a.json": sahne(6)})
        h = kurgu.denetle(k, sahneler=False)
        self.assertTrue(any("sahne a: stil" in x for x in h))
        self.assertTrue(any("sahne b: senaryo okunamadı" in x for x in h))
        self.assertTrue(any("sahne c: geçiş süresi" in x for x in h))

    def test_seslendirme_sahne_disina_tasmaz(self):
        k = self.kur({"gecis": {"tur": "kesme"}, "sahneler": [
            {"id": "a", "stil": "kinetik", "senaryo": "a.json"},
            {"id": "b", "stil": "kinetik", "senaryo": "b.json"}]},
            {"a.json": sahne(5, [("v0", 3.0)]), "b.json": sahne(5, [("v0", 0.2)])})
        self.assertEqual(kurgu.denetle(k, {"a-v0": 1.5}, sahneler=False), [])
        h = kurgu.denetle(k, {"a-v0": 2.5}, sahneler=False)
        self.assertTrue(any("a-v0" in x and "b-v0" in x for x in h))
        self.assertTrue(any("kendi sahnesi bitince" in x for x in h))

    def test_bolum_listesi_ve_onizleme_anlari(self):
        k = self.kur({"gecis": {"tur": "kesme"}, "sahneler": [
            {"id": "a", "baslik": "Giriş", "stil": "kinetik", "senaryo": "a.json"},
            {"id": "b", "baslik": "Veri", "stil": "analiz", "senaryo": "b.json"}]},
            {"a.json": sahne(65), "b.json": sahne(40, ic=(0, 5, 15, 25, 35))})
        self.assertEqual(kurgu.bolum_listesi(k), "00:00 Giriş\n01:05 Veri\n")
        self.assertEqual(kurgu.onizleme_anlari(k["sahneler"][1]), [14.6, 34.6, 39.6])

    @unittest.skipUnless(NUMPY, "numpy/soundfile yok")
    def test_muzik_bolumleri(self):
        import numpy as np
        import muzik
        bol = [{"bas": 0, "enerji": 0}, {"bas": 4, "enerji": 2}]
        m = muzik.muzik_yatagi(8.0, bol, 100, kurgu.VARSAYILAN_AKORLAR)
        self.assertEqual(m.shape, (8 * muzik.SR, 2))
        rms = lambda a, b: float(np.sqrt((m[int(a * muzik.SR):int(b * muzik.SR)] ** 2).mean()))
        self.assertGreater(rms(4.2, 6.0), rms(0.5, 3.0))  # enerjik bölüm sakin bölümden dolu
        self.assertTrue(np.isfinite(m).all())


if __name__ == "__main__":
    unittest.main()
