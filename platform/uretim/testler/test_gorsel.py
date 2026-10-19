import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import gorsel  # noqa: E402

DEPO = HERE.parents[1]
MARKA = DEPO / "ornekler" / "demli-kahve" / "marka" / "marka.json"
PIL = importlib.util.find_spec("PIL") is not None


def png(w, h) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (w, h), (200, 120, 40)).save(b, "PNG")
    return b.getvalue()


class SahteFal:
    """fal.ai kuyruğunu taklit eder: her POST bir iş, iş hemen biter, görsel indirilir."""

    def __init__(self, w=1536, h=2752, tip="image/png"):
        self.w, self.h, self.tip = w, h, tip
        self.istekler: list[tuple[str, dict]] = []

    def __call__(self, method, url, body=None, headers=None):
        if method == "POST":
            self.istekler.append((url, body))
            return json.dumps({"status_url": "s", "response_url": "r"}).encode()
        if url == "s":
            return b'{"status": "COMPLETED"}'
        if url == "r":
            return json.dumps({"images": [{"url": "dosya", "content_type": self.tip}]}).encode()
        return b"<svg/>" if "svg" in self.tip else png(self.w, self.h)


class Yardimcilar(unittest.TestCase):
    def test_oran_ve_boyut(self):
        m = gorsel.yukle()
        self.assertEqual(gorsel.hedef_boyut("9:16"), (1080, 1920))
        self.assertEqual(gorsel.hedef_boyut("1200x628"), (1200, 628))
        self.assertEqual(gorsel.en_yakin_oran(1080, 1350, m["flux-ultra"]["oranlar"]), "3:4")
        self.assertEqual(gorsel.istek_boyutu(1080, 1920, m["flux-schnell"]), (576, 1024))
        self.assertEqual(gorsel.maliyet(m["flux-schnell"], 1080, 1920), 0.003)
        self.assertEqual(gorsel.maliyet(m["recraft-svg"], 1080, 1920), 0.08)
        with self.assertRaises(gorsel.Hata):
            gorsel.hedef_boyut("21:9")

    def test_marka_uslup_ve_renk(self):
        uslup, renkler = gorsel.marka_bilgisi(str(MARKA))
        self.assertTrue(uslup)
        self.assertTrue(renkler and all(r.startswith("#") for r in renkler))
        b = gorsel.govde("fincan", gorsel.yukle()["recraft"], 1080, 1080, 1, None, renkler)
        self.assertEqual(len(b["colors"]), len(renkler))
        self.assertNotIn("seed", b)


@unittest.skipUnless(PIL, "Pillow yok")
class Uret(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"FAL_KEY": "test"})
        self.env.start()
        self.uyku = mock.patch.object(gorsel.saglayici.time, "sleep")
        self.uyku.start()

    def tearDown(self):
        self.env.stop()
        self.uyku.stop()
        self.tmp.cleanup()

    def calistir(self, *arg, ag=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            kod = gorsel.main(list(arg), ag=ag or SahteFal())
        return kod, out.getvalue() + err.getvalue()

    def test_final_kucultulur_ve_onbellek_odemez(self):
        from PIL import Image
        ag = SahteFal()
        hedef = self.t / "hero.png"
        kod, _ = self.calistir("uret", "ürün", "--model", "flux-ultra", "--boyut", "9:16", "-o", str(hedef), ag=ag)
        self.assertEqual(kod, 0)
        self.assertEqual(Image.open(hedef).size, (1080, 1920))
        self.assertEqual(ag.istekler[0][0], "https://queue.fal.run/fal-ai/flux-pro/v1.1-ultra")
        self.assertEqual(ag.istekler[0][1]["aspect_ratio"], "9:16")
        satirlar = gorsel.kayit_oku(self.t / "gorsel-kaydi.csv")
        self.assertEqual((satirlar[0]["lisans"], satirlar[0]["maliyet_usd"]), ("ticari", "0.0600"))
        # aynı istek, başka kırpma: ödeme yok, ham dosyadan yeniden kesilir
        kod, cikti = self.calistir("uret", "ürün", "--model", "flux-ultra", "--boyut", "9:16",
                                   "-o", str(self.t / "hero2.png"), "--kayit", str(self.t / "gorsel-kaydi.csv"), ag=ag)
        self.assertEqual(kod, 0)
        self.assertIn("önbellek", cikti)
        self.assertEqual(len(ag.istekler), 1)

    def test_final_buyutulmez(self):
        kod, cikti = self.calistir("uret", "ürün", "--model", "flux-ultra", "--boyut", "9:16",
                                   "-o", str(self.t / "k.png"), ag=SahteFal(540, 960))
        self.assertEqual(kod, 1)
        self.assertIn("büyütmek gerekir", cikti)

    def test_taslak_varyantlar_buyutulebilir(self):
        ag = SahteFal(576, 1024)
        kod, cikti = self.calistir("uret", "ürün", "--model", "flux-schnell", "--adet", "3", "-o",
                                   str(self.t / "t.png"), ag=ag)
        self.assertEqual(kod, 0, cikti)
        self.assertEqual([b["seed"] for _, b in ag.istekler], [1, 2, 3])
        self.assertTrue(all((self.t / f"t-{i}.png").exists() for i in (1, 2, 3)))
        self.assertIn("taslak", cikti)

    def test_butce_kesici(self):
        ag = SahteFal()
        kod, cikti = self.calistir("uret", "ürün", "--model", "flux-ultra", "--adet", "4", "--butce", "0.2",
                                   "-o", str(self.t / "b.png"), ag=ag)
        self.assertEqual(kod, 1)
        self.assertIn("bütçe", cikti)
        self.assertEqual(ag.istekler, [])

    def test_svg_ve_anahtar_yok(self):
        kod, _ = self.calistir("uret", "ikon", "--model", "recraft-svg", "--boyut", "1:1", "-o",
                               str(self.t / "ikon.png"), ag=SahteFal(tip="image/svg+xml"))
        self.assertEqual(kod, 0)
        self.assertEqual((self.t / "ikon.svg").read_bytes(), b"<svg/>")
        with mock.patch.dict(os.environ, {"FAL_KEY": ""}):
            kod, cikti = self.calistir("uret", "x", "--model", "recraft", "-o", str(self.t / "y.png"))
        self.assertEqual(kod, 1)
        self.assertIn("FAL_KEY", cikti)

    def test_kuru_ve_plan(self):
        kod, cikti = self.calistir("plan", "ürün", "--model", "flux-ultra", "--boyut", "4:5", "--adet", "2")
        self.assertEqual(kod, 0)
        self.assertIn("0.120 $", cikti)
        self.assertIn("3:4", cikti)
        kod, _ = self.calistir("uret", "ürün", "--model", "kuru", "-o", str(self.t / "k.png"))
        self.assertEqual(kod, 0)
        self.assertTrue((self.t / "k.kuru.json").exists())


if __name__ == "__main__":
    unittest.main()
