import importlib.util
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

DEPO = HERE.parents[1]
NUMPY = importlib.util.find_spec("numpy") is not None
SOUNDFILE = importlib.util.find_spec("soundfile") is not None
FFMPEG = shutil.which("ffmpeg") is not None
SR = 48000


def _pad(sure: float):
    import numpy as np
    t = np.arange(int(sure * SR)) / SR
    return sum(np.sin(2 * np.pi * f * t) for f in (220, 277, 330)) * 0.15


@unittest.skipUnless(NUMPY, "numpy yok")
class Ilkeller(unittest.TestCase):
    def test_hepsi_sonlu_ve_normal(self):
        import numpy as np
        import sfx
        r = np.random.default_rng(1)
        for ad, x in [("hat", sfx.hat(r)), ("acik_hat", sfx.hat(r, acik=True)), ("shaker", sfx.shaker(r)),
                      ("zil", sfx.zil(r)), ("clap", sfx.clap(r)), ("tik", sfx.tik(r)), ("kick", sfx.kick(r)),
                      ("boom", sfx.boom(r)), ("whoosh", sfx.whoosh(r, 0.4)), ("whoosh_in", sfx.whoosh(r, 0.4, False)),
                      ("riser", sfx.riser(r, 1.2)), ("hisirti", sfx.hisirti(r, 1.0)), ("parilti", sfx.parilti(r, 1.5)),
                      ("citirti", sfx.citirti(r, 1.0))]:
            with self.subTest(ad):
                self.assertTrue(np.isfinite(x).all())
                self.assertGreater(len(x), 100)
                self.assertLessEqual(float(np.abs(x).max()), 1.3)

    def test_ayni_vurus_iki_kez_ayni_degil(self):
        import numpy as np
        import sfx
        r = np.random.default_rng(2)
        a, b = sfx.hat(r), sfx.hat(r)
        n = min(len(a), len(b))
        self.assertFalse(np.allclose(a[:n], b[:n]))

    def test_renkli_egim(self):
        import numpy as np
        import sfx
        x = sfx.renkli(SR * 4, 3, -3.0)
        P = np.abs(np.fft.rfft(x)) ** 2
        f = np.fft.rfftfreq(len(x), 1 / SR)
        alt = P[(f > 500) & (f < 1000)].mean()
        ust = P[(f > 8000) & (f < 16000)].mean()
        # pembe: 4 oktav yukarıda ~12 dB az güç (beyazda eşit)
        self.assertLess(10 * np.log10(ust / alt), -9)


@unittest.skipUnless(NUMPY, "numpy yok")
class GurultuAnalizi(unittest.TestCase):
    def test_uzun_tiz_gurultu_yakalanir(self):
        """LÉVA'nın ilk sürümü: müziğin altında 3 sn düz bant gürültüsü (eski 'parıltı')."""
        import numpy as np
        import sfx
        x = _pad(6.0)
        g = sfx.bant(np.random.default_rng(0).standard_normal(int(3 * SR)), 3000, 9000, 4)
        x[SR: SR + len(g)] += g / np.abs(g).max() * 0.5
        a = sfx.gurultu_analizi(x)
        self.assertGreater(a["en_uzun_sn"], 2.0)
        self.assertAlmostEqual(a["en_uzun_an"], 1.0, delta=0.3)

    def test_yeni_parilti_ve_hisirti_tekduze_degil(self):
        import numpy as np
        import sfx
        for ad, efekt in (("parilti", sfx.parilti(1, 3.0)), ("hisirti", sfx.hisirti(1, 3.0))):
            with self.subTest(ad):
                x = _pad(6.0)
                x[SR: SR + len(efekt)] += efekt * 0.3
                self.assertLess(sfx.gurultu_analizi(x)["en_uzun_sn"], 1.0)

    def test_hi_hat_kalibi(self):
        import numpy as np
        import sfx
        x = _pad(6.0)
        r = np.random.default_rng(4)
        for i in range(24):
            h = sfx.hat(r) * 0.25
            j = int((0.125 + i * 0.25) * SR)
            x[j: j + len(h)] += h
        a = sfx.gurultu_analizi(x)
        self.assertLess(a["en_uzun_sn"], 0.5)
        self.assertLess(a["oran"], 0.2)


@unittest.skipUnless(NUMPY and FFMPEG and SOUNDFILE, "numpy, soundfile ya da ffmpeg yok")
class KaliteKapisi(unittest.TestCase):
    def test_hisirti_hata_verir(self):
        import numpy as np
        import soundfile as sf
        import kalite
        import mastering
        import sfx
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            x = _pad(5.0)
            g = sfx.bant(np.random.default_rng(0).standard_normal(int(2.6 * SR)), 3000, 9000, 4)
            x[SR: SR + len(g)] += g / np.abs(g).max() * 0.5
            sf.write(str(t / "ham.wav"), x.astype(np.float32), SR)
            mastering.master(t / "ham.wav", t / "ses.wav")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                            "testsrc2=s=1080x1920:d=5:r=30", "-i", str(t / "ses.wav"), "-c:v", "libx264", "-pix_fmt",
                            "yuv420p", "-c:a", "aac", "-shortest", str(t / "v.mp4")], check=True)
            r = kalite.denetle(t / "v.mp4")
            self.assertIn("hisirti", {b["kontrol"] for b in r["bulgular"] if b["seviye"] == "hata"})
            self.assertIn("hisirti", r["olcum"]["ses"])


# Şablonların müzik + efekt izi (seslendirmesiz): tiz cızırtı payı sınırın altında kalmalı.
# Eski beyaz gürültülü sürümler: kinetik 0.26, origami 0.30, çizgi roman 0.38, gölge oyunu 0.28.
SABLON_IZLERI = [
    ("kinetik", "ornekler/kucuk-aliskanliklar/senaryo.json", 0.15),
    ("origami", "ornekler/tuzak-fiyat-origami/origami.json", 0.22),
    ("tek_cizgi", "ornekler/hamurkar-firin/tek-cizgi.json", 0.15),
    ("cizgi_roman", "ornekler/kucuk-aliskanliklar/cizgi-roman.json", 0.2),
    ("risograf", "ornekler/kucuk-aliskanliklar/risograf.json", 0.2),
    ("golge_oyunu", "ornekler/kucuk-aliskanliklar/golge-oyunu.json", 0.15),
    ("analiz", "ornekler/fransa-ekim-2026/analiz.json", 0.1),
]
IZ_BETIGI = textwrap.dedent("""
    import importlib, sys
    from pathlib import Path
    import soundfile as sf
    depo, modul, ornek, cik = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    md = depo / 'platform' / 'sablonlar' / modul
    sys.path[:0] = [str(md), str(depo / 'platform' / 'ortak')]
    z = importlib.import_module('zaman') if (md / 'zaman.py').exists() else importlib.import_module(modul)
    snt = importlib.import_module('muzik' if (md / 'muzik.py').exists() else 'sentez')
    snt.miksle(z.yukle(str(depo / ornek)), cik, None)
    import sfx
    x, sr = sf.read(str(cik / 'ses.wav'))
    a = sfx.gurultu_analizi(x, sr)
    print(a['oran'], a['en_uzun_sn'])
""")


@unittest.skipUnless(NUMPY and SOUNDFILE and importlib.util.find_spec("skia"), "numpy, soundfile ya da skia yok")
class SablonIzleri(unittest.TestCase):
    def test_tiz_cizirti_payi(self):
        for modul, ornek, sinir in SABLON_IZLERI:
            with self.subTest(modul), tempfile.TemporaryDirectory() as tmp:
                r = subprocess.run([sys.executable, "-c", IZ_BETIGI, str(DEPO), modul, ornek, tmp],
                                   capture_output=True, text=True, timeout=300)
                self.assertEqual(r.returncode, 0, r.stderr[-800:])
                oran, en_uzun = map(float, r.stdout.split()[-2:])
                self.assertLess(oran, sinir, f"{modul}: tiz cızırtı payı {oran:.2f}")
                self.assertLess(en_uzun, 1.0, f"{modul}: {en_uzun:.1f} sn kesintisiz cızırtı")


if __name__ == "__main__":
    unittest.main()
