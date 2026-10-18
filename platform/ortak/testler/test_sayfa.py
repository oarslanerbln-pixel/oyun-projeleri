import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import sayfa  # noqa: E402

PLAYWRIGHT = importlib.util.find_spec("playwright") is not None

IYI = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0;background:#f7f3e8;font:16px system-ui;color:#111}main{max-width:900px;margin:auto;padding:24px}
.kart{background:#fff;padding:20px}button{background:#111;color:#fff;border:0;padding:14px 22px;font-size:16px}
.liste{overflow-x:auto}.liste div{width:900px}</style></head>
<body><main><h1>Stüdyo paneli</h1><div class="kart"><p>Bu ay 5 uzun, 15 kısa video.</p>
<button>Yeni sipariş</button></div><div class="liste"><div>Yana kayan geniş tablo kabın içinde kalır</div></div>
</main></body></html>"""

KOTU = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0;background:#fff;font:16px system-ui}.genis{width:900px}.soluk{color:#bbb}.okunmaz{color:#f4f4f4}
.kutu{width:120px;height:40px;overflow:hidden;white-space:nowrap}.minik{font-size:9px}button{padding:2px 4px}</style></head>
<body><div class="genis">Çok geniş şerit</div><p class="soluk">Soluk yazı</p><p class="okunmaz">Görünmez yazı</p>
<div class="kutu">Bu cümle kutuya kesinlikle sığmayacak kadar uzun</div><p class="minik">Dipnot</p><button>OK</button>
<img src="yok.png" alt="kırık"><script>console.error("deneme")</script></body></html>"""


@unittest.skipUnless(PLAYWRIGHT, "playwright yok")
class Sayfa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        (t / "iyi.html").write_text(IYI, encoding="utf-8")
        (t / "kotu.html").write_text(KOTU, encoding="utf-8")
        cls.iyi = sayfa.denetle(str(t / "iyi.html"), t / "iyi.png", bekle_ms=100)
        cls.kotu = sayfa.denetle(str(t / "kotu.html"), t / "kotu.png", bekle_ms=100)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def bulgu(self, kontrol, ekran="telefon"):
        return [b for b in self.kotu["bulgular"] if b["kontrol"] == kontrol and b["ekran"] == ekran]

    def test_temiz_sayfa_gecer(self):
        self.assertEqual(self.iyi["sonuc"], "gecti", self.iyi["bulgular"])
        self.assertTrue(Path(self.iyi["kontakt"]).exists())

    def test_telefonda_tasma_hata(self):
        self.assertEqual(self.kotu["sonuc"], "kaldi")
        self.assertEqual(self.bulgu("yatay_kaydirma")[0]["seviye"], "hata")
        self.assertIn("div.genis", self.bulgu("ekrandan_tasan")[0]["ornekler"][0])
        self.assertFalse(self.bulgu("yatay_kaydirma", "masaustu"))

    def test_kontrast(self):
        b = self.bulgu("kontrast")[0]
        self.assertEqual(b["seviye"], "hata")      # #f4f4f4 beyazda okunmaz
        self.assertEqual(len(b["ornekler"]), 2)    # #bbb ise uyarı düzeyinde

    def test_kesilen_kucuk_kirik(self):
        self.assertTrue(self.bulgu("kesilen_yazi"))
        self.assertTrue(self.bulgu("kucuk_yazi"))
        self.assertTrue(self.bulgu("dokunma_hedefi"))
        self.assertFalse(self.bulgu("kucuk_yazi", "masaustu"))
        self.assertEqual(self.bulgu("kirik_gorsel")[0]["seviye"], "hata")
        self.assertIn("deneme", self.bulgu("konsol")[0]["ornekler"])


if __name__ == "__main__":
    unittest.main()
