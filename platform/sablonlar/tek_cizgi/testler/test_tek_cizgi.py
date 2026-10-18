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
ORNEK = DEPO / "ornekler" / "hamurkar-firin" / "tek-cizgi.json"
NUMPY = importlib.util.find_spec("numpy") is not None
SKIA = NUMPY and all(importlib.util.find_spec(m) for m in ("skia", "soundfile")) and shutil.which("ffmpeg")


def yaz(s: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "tek-cizgi.json"
        p.write_text(json.dumps({k: v for k, v in s.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEK.read_text(encoding="utf-8"))

    def test_ornek_temiz(self):
        self.assertEqual(zaman.denetle(zaman.yukle(ORNEK)), [])

    def test_muzik_bolumleri(self):
        m = zaman.yukle(ORNEK)["muzik"]
        self.assertEqual((m["yukselis"], m["sakin"], m["final"]), (3.0, 6.0, 8.0))

    def test_bilinmeyen_sekil(self):
        h = copy.deepcopy(self.ham); h["sahneler"][0]["sekil"] = "ejderha"
        self.assertTrue(any("ejderha" in x for x in zaman.denetle(yaz(h))))

    def test_svg_yolu_kabul(self):
        h = copy.deepcopy(self.ham); h["sahneler"][3]["sekil"] = "M 0 100 L 50 0 L 100 100"
        self.assertEqual(zaman.denetle(yaz(h)), [])

    def test_iki_bicim_birden(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["sekil"] = "kalp"
        self.assertTrue(any("tam biri" in x for x in zaman.denetle(yaz(h))))

    def test_sayac_sahne_disi(self):
        h = copy.deepcopy(self.ham); h["sahneler"][2]["sayac"]["bitis_t"] = 6.5
        self.assertTrue(any("bitis_t" in x for x in zaman.denetle(yaz(h))))

    def test_yazi_sahne_disi_ve_sira(self):
        h = copy.deepcopy(self.ham); h["sahneler"][2]["yazi"]["t"] = 7.0; h["sahneler"][3]["bas"] = 2.0
        hatalar = zaman.denetle(yaz(h))
        self.assertTrue(any("yazi" in x for x in hatalar))
        self.assertTrue(any("artan" in x for x in hatalar))

    def test_seslendirme_cakismasi(self):
        hatalar = zaman.denetle(zaman.yukle(ORNEK), {"v0": 3.2})
        self.assertTrue(any("v0" in x and "bitmiyor" in x for x in hatalar))


class Zamanlama(unittest.TestCase):
    def setUp(self):
        self.s = zaman.yukle(ORNEK)
        self.pz = zaman.pozlar(self.s)

    def test_sayac_hizlanir_ve_vurguda_iner(self):
        sayac = [p for p in self.pz if p["sahne"] == 2]
        self.assertEqual([p["deger"] for p in sayac], ["50", "38", "24", "12", "3"])
        an = zaman.sayac_anlari(self.s["sahneler"][2])
        araliklar = [b - a for a, b in zip(an, an[1:])]
        self.assertEqual(araliklar, sorted(araliklar, reverse=True))  # geri sayım hızlanır
        self.assertAlmostEqual(an[-1], 4.25)
        son = sayac[-1]
        self.assertTrue(son["son"]); self.assertEqual(son["renk"], "vurgu")
        self.assertAlmostEqual(son["t"] + son["sure"] * 0.55, 4.25)

    def test_ses_olaylari(self):
        o = zaman.ses_olaylari(self.s)
        self.assertEqual([x[0] for x in o], sorted(x[0] for x in o))
        adlar = [x[1] for x in o]
        self.assertEqual(adlar.count("vurus"), 1)
        self.assertEqual(adlar.count("tik"), 3)
        self.assertIn("cinlama", adlar)
        self.assertNotIn(3.0, [x[0] for x in o if x[1] == "kayma"])  # 50 → 50 dönüşümü sessiz

    def test_zemin_degisimi(self):
        self.assertEqual(zaman.zemin_degisimleri(self.s), [(8.0, "kapanis")])

    def test_poz_at(self):
        self.assertEqual(zaman.poz_at(self.pz, 0.0), (0, 0.0))
        k, q = zaman.poz_at(self.pz, 9.9)
        self.assertEqual(self.pz[k]["deger"], "basak"); self.assertEqual(q, 1.0)


@unittest.skipUnless(NUMPY, "numpy yok")
class Geometri(unittest.TestCase):
    def test_yol_ayristirici(self):
        import sekiller
        p = sekiller.yol_ayristir("M 0 0 L 10 0 l 0 10 H 0 Z m 20 20 c 0 10, 10 10, 10 0 Q 40 0 40 10")
        self.assertEqual(len(p), 2)
        self.assertEqual(p[0][-1].tolist(), [0.0, 0.0])          # Z başlangıca döner
        self.assertEqual(p[1][0].tolist(), [20.0, 20.0])          # göreli m
        self.assertAlmostEqual(p[1][-1][0], 40.0)
        with self.assertRaises(sekiller.SekilHatasi):
            sekiller.yol_ayristir("M 0 0 A 5 5 0 0 1 10 10")

    def test_kutuphane_zamanla_ayni(self):
        import sekiller
        self.assertEqual(tuple(sekiller.SEKILLER), zaman.SEKIL_ADLARI)

    def test_her_bicim_ekrani_kesen_tek_cizgi(self):
        import numpy as np
        import sekiller
        W, H = 1080, 1920
        bicimler = [{"tur": "sekil", "deger": a} for a in sekiller.SEKILLER] + [{"tur": "sayi", "deger": d} for d in ("0123456789", "50", "3")]
        for b in bicimler:
            x = sekiller.poz_cizgisi(b, W, H)
            self.assertEqual(x.shape, (sekiller.N_NOKTA, 2), b)
            self.assertTrue(np.isfinite(x).all(), b)
            self.assertLess(x[0, 0], 0); self.assertGreater(x[-1, 0], W)  # soldan girer, sağdan çıkar
            adim = np.hypot(*np.diff(x, axis=0).T)
            self.assertLess(adim.max(), 3 * adim.mean() + 1, b)  # yay uzunluğuna eşit örneklenmiş, kopukluk yok
            ic = x[(x[:, 0] > 0) & (x[:, 0] < W)]
            self.assertTrue(0 < ic[:, 1].min() and ic[:, 1].max() < H, b)

    def test_rakam_baglantilari_govdeyi_kesmez(self):
        import sekiller
        for metin in ("3", "30", "50", "38", "12"):
            x = sekiller.sayi_noktalari(metin)
            self.assertGreater(len(x), 100)
        with self.assertRaises(sekiller.SekilHatasi):
            sekiller.sayi_noktalari("3a")

    def test_cizgi_hic_sicramaz(self):
        import numpy as np
        import sekiller
        s = zaman.yukle(ORNEK)
        c = sekiller.Cizgi(zaman.pozlar(s), 540, 960, n=400)
        onceki = None
        for i in range(int(s["sure"] * 30)):
            x, oran, _, _ = c.an(i / 30)
            if onceki is not None and oran == 1.0 and onceki[1] == 1.0:
                self.assertLess(np.hypot(*(x - onceki[0]).T).max(), 0.2 * 540, f"kare {i}")
            onceki = (x, oran)


@unittest.skipUnless(SKIA, "skia-python / numpy / soundfile / ffmpeg yok")
class Render(unittest.TestCase):
    def test_kare_ve_ses(self):
        import cizim
        import sentez
        s = zaman.yukle(ORNEK)
        with tempfile.TemporaryDirectory() as tmp:
            k = cizim.kareler(s, 270, 480, [0.6, 4.5, 9.6], Path(tmp))
            self.assertEqual(len(k), 3)
            self.assertTrue(all(p.stat().st_size > 1000 for p in k))
            bilgi = sentez.miksle(s, Path(tmp))
            self.assertEqual(bilgi["seslendirme"], [])
            self.assertTrue((Path(tmp) / "ses.wav").exists())


if __name__ == "__main__":
    unittest.main()
