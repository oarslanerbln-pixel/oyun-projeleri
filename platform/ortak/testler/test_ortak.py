import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import formatlar  # noqa: E402

DEPO = HERE.parents[1]
FFMPEG = shutil.which("ffmpeg") is not None
NUMPY = importlib.util.find_spec("numpy") is not None


def ffmpeg(*arg: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *arg], check=True)


class Formatlar(unittest.TestCase):
    def test_iki_yazim(self):
        self.assertEqual(formatlar.anahtar("9:16"), "9x16")
        self.assertEqual(formatlar.boyut("4:5"), (1080, 1350))
        with self.assertRaises(ValueError):
            formatlar.anahtar("21:9")

    def test_coz_sirasi(self):
        self.assertEqual(formatlar.coz(None), ["9x16"])
        self.assertEqual(formatlar.coz(None, {"format": "16:9"}), ["16x9"])
        self.assertEqual(formatlar.coz(["1x1"], {"format": "16:9"}), ["1x1"])
        self.assertEqual(formatlar.coz("ikisi"), ["9x16", "16x9"])
        self.assertEqual(formatlar.coz(None, {"format": ["9:16", "ikisi"]}), ["9x16", "16x9"])
        self.assertEqual(formatlar.bilinmeyenler(["9:16", "21:9", "ikisi"]), ["21:9"])


@unittest.skipUnless(FFMPEG, "ffmpeg yok")
class Mastering(unittest.TestCase):
    def test_hedef_ve_gercek_tepe(self):
        import mastering
        with tempfile.TemporaryDirectory() as tmp:
            gir, cik = Path(tmp) / "gir.wav", Path(tmp) / "cik.wav"
            # yüksek ve keskin geçişli kare dalga: örnekler arası tepe taşmasını kışkırtır
            ffmpeg("-f", "lavfi", "-i", "aevalsrc=0.9*sgn(sin(2*PI*997*t)):s=48000:d=4", str(gir))
            mastering.master(gir, cik)
            o = mastering.olc(cik, on_filtre=None)
            self.assertAlmostEqual(o["lufs"], mastering.HEDEF_LUFS, delta=1.0)
            self.assertLessEqual(o["tepe_dbtp"], mastering.TEPE_HEDEF + 0.05)


@unittest.skipUnless(FFMPEG and NUMPY, "ffmpeg ya da numpy yok")
class Kalite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        cls.ses = t / "ses.wav"
        ffmpeg("-f", "lavfi", "-i", "sine=f=330:d=2:sample_rate=48000", "-af", "volume=-6dB", str(cls.ses))
        cls.ses_m = t / "ses-m.wav"
        import mastering
        mastering.master(cls.ses, cls.ses_m)
        # koyu, sığ degrade: 8 bitte geniş basamaklar (banding)
        cls.bantli = t / "bantli.mp4"
        ffmpeg("-f", "lavfi", "-i", "gradients=s=1080x1920:c0=0x182430:c1=0x24384a:d=2:speed=0.0001:r=30:seed=1",
               "-i", str(cls.ses_m), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
               str(cls.bantli))
        # aynı degrade, üstüne titreşim (dither) gürültüsü
        cls.titresimli = t / "titresimli.mp4"
        ffmpeg("-f", "lavfi", "-i", "gradients=s=1080x1920:c0=0x182430:c1=0x24384a:d=2:speed=0.0001:r=30:seed=1",
               "-i", str(cls.ses_m), "-vf", "noise=alls=6:allf=t", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-shortest", str(cls.titresimli))
        # düşük çözünürlük, sessiz
        cls.kucuk = t / "kucuk.mp4"
        ffmpeg("-f", "lavfi", "-i", "testsrc2=s=540x960:d=3:r=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.kucuk))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def kontroller(self, r: dict, seviye: str) -> set[str]:
        return {b["kontrol"] for b in r["bulgular"] if b["seviye"] == seviye}

    def test_banding_yakalanir(self):
        import kalite
        r = kalite.denetle(self.bantli)
        self.assertIn("banding", self.kontroller(r, "hata"))
        self.assertEqual(r["sonuc"], "kaldi")

    def test_titresimli_degrade_gecer(self):
        import kalite
        r = kalite.denetle(self.titresimli)
        self.assertNotIn("banding", self.kontroller(r, "hata") | self.kontroller(r, "uyari"))
        self.assertNotIn("lufs", self.kontroller(r, "hata"))

    def test_dusuk_cozunurluk_ve_ses_yok(self):
        import kalite
        r = kalite.denetle(self.kucuk)
        self.assertEqual({"cozunurluk", "ses"} - self.kontroller(r, "hata"), set())
        r = kalite.denetle(self.kucuk, sessiz_olabilir=True)
        self.assertNotIn("ses", self.kontroller(r, "hata"))

    def test_kontakt_ve_rapor(self):
        import akis
        with tempfile.TemporaryDirectory() as tmp:
            sessiz = Path(tmp) / "sessiz.mp4"
            ffmpeg("-i", str(self.titresimli), "-an", "-c:v", "copy", str(sessiz))
            hedef = akis.birlestir(sessiz, self.ses_m, Path(tmp) / "video.mp4")
            rapor = json.loads(hedef.with_suffix(".kalite.json").read_text(encoding="utf-8"))
            self.assertIn(rapor["sonuc"], ("gecti", "uyarili"))
            self.assertTrue(hedef.with_suffix(".kontakt.png").exists())

    def test_komut_satiri_cikis_kodu(self):
        r = subprocess.run([sys.executable, str(HERE / "kalite.py"), str(self.bantli)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("KALDI", r.stdout)


@unittest.skipUnless(NUMPY, "numpy yok")
class BandingBirim(unittest.TestCase):
    def test_duz_dolgu_ve_doku(self):
        import numpy as np
        import kalite
        duz = np.full((256, 256, 3), 40, dtype=np.uint8)
        self.assertEqual(kalite.banding_orani(duz), 0.0)
        rng = np.random.default_rng(1)
        doku = (40 + rng.integers(0, 6, (256, 256, 1))).repeat(3, axis=2).astype(np.uint8)
        self.assertEqual(kalite.banding_orani(doku), 0.0)

    def test_genis_basamaklar(self):
        import numpy as np
        import kalite
        x = np.arange(256)[None, :, None]
        kare = np.broadcast_to(30 + x // 20, (256, 256, 3)).astype(np.uint8)
        self.assertGreater(kalite.banding_orani(kare), 0.5)

    def test_acik_zemin_sayilmaz(self):
        import numpy as np
        import kalite
        x = np.arange(256)[None, :, None]
        kare = np.broadcast_to(230 + x // 20, (256, 256, 3)).astype(np.uint8)
        self.assertEqual(kalite.banding_orani(kare), 0.0)


@unittest.skipUnless(NUMPY and importlib.util.find_spec("skia") and importlib.util.find_spec("PIL"), "skia, numpy ya da PIL yok")
class Onizleme(unittest.TestCase):
    def test_iki_stil_tek_sayfa(self):
        import onizleme
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            hedef = Path(tmp) / "onizleme.png"
            r = onizleme.onizle([str(DEPO / "ornekler/tuzak-fiyat-origami/origami.json"),
                                 "tek-cizgi=" + str(DEPO / "ornekler/hamurkar-firin/tek-cizgi.json")], hedef, [2.0, 6.0])
            self.assertEqual([x["stil"] for x in r["stiller"]], ["origami", "tek-cizgi"])
            self.assertTrue(all(len(x["kareler"]) == 2 and "hata" not in x for x in r["stiller"]))
            w, h = Image.open(hedef).size
            self.assertGreater(h, w)  # 2 satır x 2 sütun dikey kare

    def test_sablon_bulma(self):
        import onizleme
        self.assertEqual(onizleme.sablon_bul({}, DEPO / "platform/sablonlar/kolaj/ornek/senaryo.json", None), "kolaj")
        self.assertEqual(onizleme.sablon_bul({"stil": "hamur"}, Path("x.json"), None), "hamur")
        self.assertEqual(onizleme.sablon_bul({}, Path("x.json"), "izometrik"), "izometrik")
        self.assertEqual(onizleme.anlar_bul({"sure": 10}, None), [1.5, 5.0, 8.5])


class CiCalistirici(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(DEPO / "platform" / "ci"))
        import calistir
        self.c = calistir

    def test_kesif(self):
        adlar = {d.parent.name for d in self.c.test_klasorleri()}
        self.assertTrue({"ortak", "kinetik", "marka"} <= adlar)
        for klasor, c in self.c.ci_dosyalari():
            for adim in c.get("denetle", []):
                self.assertTrue(adim["dosyalar"] and adim["komut"], klasor)

    def test_dizin_her_sablonu_listeler(self):
        metin = self.c.dizin_metni()
        for d in (DEPO / "platform" / "sablonlar").iterdir():
            if (d / "README.md").exists():
                self.assertIn(f"[`{d.name}`]", metin)


if __name__ == "__main__":
    unittest.main()
