import importlib.util
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NUMPY = all(importlib.util.find_spec(m) for m in ("numpy", "soundfile"))


@unittest.skipUnless(NUMPY, "numpy/soundfile yok")
class Kisma(unittest.TestCase):
    def test_onden_iner_kelime_arasinda_tutar_cumle_arasinda_acilir(self):
        import numpy as np
        import miks
        SR = miks.SR
        t = np.arange(6 * SR) / SR
        vo = np.zeros_like(t)
        for a, b in ((1, 2), (2.15, 3), (4.5, 5)):  # 0.15 sn kelime arası, 1.5 sn cümle arası
            m = (t >= a) & (t < b)
            vo[m] = 0.3 * np.sin(2 * np.pi * 200 * t[m])
        z = miks.konusma_zarfi(vo)
        an = lambda s: z[int(s * SR)]  # noqa: E731
        self.assertLess(an(0.5), 0.05)
        self.assertGreater(an(1.0), 0.6)      # ilk hecede müzik çoktan inmiş (önden bakma)
        self.assertGreater(an(2.07), 0.95)    # kelime arasında zıplamaz
        self.assertLess(an(4.2), 0.2)         # cümle arasında açılır
        g = miks.kisma(vo, derinlik_db=6)
        self.assertAlmostEqual(float(g.max()), 1.0, places=3)
        self.assertAlmostEqual(float(g.min()), 10 ** (-6 / 20), places=2)

    def test_sessiz_konusma(self):
        import numpy as np
        import miks
        self.assertFalse(miks.konusma_zarfi(np.zeros(1000)).any())


@unittest.skipUnless(NUMPY, "numpy/soundfile yok")
class Vurus(unittest.TestCase):
    def tik_izi(self, bpm, ofset, sure=20.0):
        import numpy as np
        import miks
        SR = miks.SR
        x = np.zeros(int(sure * SR))
        i, tb = 0, ofset
        while tb < sure - 0.5:
            j, n = int(tb * SR), int(0.08 * SR)
            e = np.exp(-np.arange(n) / SR / 0.02)
            x[j:j + n] += np.sin(2 * np.pi * 60 * np.arange(n) / SR) * e * (1 if i % 2 == 0 else 0.5)
            x[j:j + n] += 0.3 * np.random.default_rng(i).standard_normal(n) * e
            i, tb = i + 1, tb + 60 / bpm
        return x

    def test_tempo_ve_ilk_vurus(self):
        import miks
        for bpm, ofset in ((100, 0.2), (128, 0.05), (84, 0.4)):
            r = miks.vurus_bul(self.tik_izi(bpm, ofset))
            self.assertAlmostEqual(r["bpm"], bpm, delta=1.0)
            fark = (r["ofset"] - ofset) % (60 / bpm)
            self.assertLess(min(fark, 60 / bpm - fark), 0.03)
            self.assertGreater(r["guven"], 0.5)

    def test_sonraki_vurus(self):
        import miks
        self.assertAlmostEqual(miks.sonraki_vurus(12.31, 100), 12.6)
        self.assertAlmostEqual(miks.sonraki_vurus(12.0, 100), 12.0)
        self.assertAlmostEqual(miks.sonraki_vurus(12.31, 100, her=4), 14.4)


@unittest.skipUnless(NUMPY, "numpy/soundfile yok")
class Kutuphane(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.yama = unittest.mock.patch.dict(os.environ, {"EFEKT_KUTUPHANESI": self.tmp.name})
        self.yama.start()
        import kutuphane
        kutuphane.dizin(yenile=True)
        kutuphane.KULLANIM.clear()
        self.k = kutuphane

    def tearDown(self):
        self.yama.stop()
        self.tmp.cleanup()
        self.k.dizin(yenile=True)

    def wav(self, ad, x):
        import soundfile as sf
        yol = Path(self.tmp.name) / ad
        sf.write(str(yol), x, 48000)
        return yol

    def test_kayit_yoksa_yedek(self):
        import numpy as np
        x = self.k.kayit("kalem", 1, yedek=lambda: np.ones(10))
        self.assertEqual(len(x), 10)
        self.assertEqual(self.k.KULLANIM["kalem"], {"kayit": 0, "sentez": 1})

    def test_ekle_sec_ve_lisans(self):
        import numpy as np
        if not __import__("shutil").which("ffmpeg"):
            self.skipTest("ffmpeg yok")
        t = np.arange(int(0.3 * 48000)) / 48000
        tik = np.concatenate([np.zeros(4800), np.sin(2 * np.pi * 900 * t) * np.exp(-t / 0.05), np.zeros(4800)])
        yol = self.wav("tik.wav", tik * 0.5)
        with self.assertRaises(self.k.KutuphaneHatasi):
            self.k.ekle(yol, "tik", "https://ornek", "biri", lisans="CC-BY-4.0")
        k = self.k.ekle(yol, "tik", "https://ornek", "biri")
        self.assertEqual(k["lisans"], "CC0-1.0")
        d = json.loads((Path(self.tmp.name) / "kutuphane.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d["kayitlar"]), 1)
        self.assertTrue((Path(self.tmp.name) / "LISANSLAR.md").exists())
        self.assertTrue(self.k.var_mi("tik"))
        a = self.k.kayit("tik", 3, yedek=lambda: None)
        self.assertLess(len(a), len(tik))                   # baştaki/sondaki sessizlik kırpıldı
        self.assertEqual(self.k.KULLANIM["tik"]["kayit"], 1)
        b = self.k.sec("tik", 4)
        self.assertFalse(len(a) == len(b) and np.allclose(a, b))  # her çağrı biraz farklı
        uzun = self.k.sec("tik", 5, sure=1.0)
        self.assertEqual(len(uzun), 48000)

    def test_tekduze_cizirti_alinmaz(self):
        import numpy as np
        rng = np.random.default_rng(0)
        x, neden = self.k.isle(rng.standard_normal(int(1.8 * 48000)) * 0.3, "gecis_whoosh")
        self.assertIsNone(x)
        self.assertIn("cızırtı", neden)

    def test_palet(self):
        self.assertEqual(self.k.rol("karakalem", "cizgi"), "kalem")
        self.assertEqual(self.k.rol("bilinmeyen", "gecis"), self.k.PALETLER["varsayilan"]["gecis"])
        for stil, p in self.k.PALETLER.items():
            for kat in p.values():
                self.assertIn(kat, self.k.KATALOG, stil)


if __name__ == "__main__":
    unittest.main()
