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
import animatik  # noqa: E402
import katalog  # noqa: E402
import panel  # noqa: E402

DEPO = HERE.parents[1]
SKIA = importlib.util.find_spec("skia") is not None and importlib.util.find_spec("numpy") is not None


class Katalog(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.kj = self.tmp / "gelistirme" / "katalog.jsonl"

    def test_ekle_gunceller_ve_arar(self):
        katalog.ekle([{"dosya": "/x/kahve-de-9x16.mp4", "baslik": "Demli kahve", "stil": "kolaj", "dil": "de",
                       "tarih": "2026-10-01"}], self.kj)
        katalog.ekle([{"dosya": "/x/kahve-de-9x16.mp4", "maliyet_usd": 1.5, "stil": None}], self.kj)
        k = katalog.oku(self.kj)
        self.assertEqual(len(k), 1)
        self.assertEqual((k[0]["stil"], k[0]["maliyet_usd"]), ("kolaj", 1.5))  # None eski değeri silmez
        self.assertEqual(len(katalog.ara(k, ["KAHVE"], dil="de")), 1)
        self.assertEqual(len(katalog.ara(k, ["markalaşma"])), 0)
        self.assertIn("Demli kahve", self.kj.with_suffix(".md").read_text(encoding="utf-8"))

    def test_turkce_harfler_katlanir(self):
        k = [{"dosya": "/a.mp4", "baslik": "Markalaşma nedir?"}]
        self.assertEqual(len(katalog.ara(k, ["markalasma"])), 1)
        self.assertEqual(len(katalog.ara(k, ["MARKALAŞMA"])), 1)

    def test_tara_ara_dosyalari_atlar(self):
        for yol in ["the-leaf/2-reel/the-leaf-reel-9x16.mp4", "markalasma-nedir/tek-cizgi-20sn-de/cikti/m-9x16.mp4",
                    "markalasma-nedir/x/cikti/is/sessiz-9x16.mp4", "a/cikti/is/sahneler/s1.mp4", ".onbellek/v.mp4"]:
            p = self.tmp / yol
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"")
        k = {Path(x["dosya"]).name: x for x in katalog.tara(self.tmp)}
        self.assertEqual(sorted(k), ["m-9x16.mp4", "the-leaf-reel-9x16.mp4"])
        self.assertEqual((k["m-9x16.mp4"]["stil"], k["m-9x16.mp4"]["dil"], k["m-9x16.mp4"]["tur"]), ("tek-cizgi", "de", "kendi"))
        self.assertEqual((k["the-leaf-reel-9x16.mp4"]["dil"], k["the-leaf-reel-9x16.mp4"]["tur"]), ("de", "musteri"))

    def test_siparisten(self):
        s = {"is": "kahve", "baslik": "Kahve", "dil": "de", "ses": {"ses": "liam"}, "_klasor": "/k",
             "senaryolar": [{"stil": "kolaj", "senaryo": "/k/kolaj.json"}], "panel": {"id": "abc"}}
        d = {"elevenlabs_karakter": 300, "videolar": [{"dosya": "/k/a.mp4", "stil": "kolaj", "format": "9x16", "sonuc": "gecti"},
                                                     {"dosya": "/k/b.mp4", "stil": "kolaj", "format": "16x9", "sonuc": "kaldi"}]}
        k = katalog.siparisten(s, d, 2.0)
        self.assertEqual(len(k), 1)  # kalan video kataloğa girmez
        self.assertEqual((k[0]["maliyet_usd"], k[0]["dil"], k[0]["ses"], k[0]["panel_id"], k[0]["senaryo"]),
                         (2.0, "de", "liam", "abc", "/k/kolaj.json"))


class Panel(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_kayittan_siparis(self):
        kayit = {"id": "doc1", "data": {"baslik": "Sabah rutini: 5 adım", "detay": "Kısa ve enerjik", "tur": "kisa",
                                        "format": "9:16", "tarz": "risograf", "dil": "Almanca", "ses": "george",
                                        "muzik": "enerjik", "kime": "Kanal 1"}}
        kp = self.tmp / "kayit.json"
        kp.write_text(json.dumps(kayit), encoding="utf-8")
        r = subprocess.run([sys.executable, str(HERE / "panel.py"), "siparis", str(kp), "--kok", str(self.tmp)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        k = self.tmp / "sabah-rutini-5-adim"
        s = json.loads((k / "siparis.json").read_text(encoding="utf-8"))
        self.assertEqual((s["dil"], s["ses"], s["panel"]["id"]), ("de", {"ses": "george"}, "doc1"))
        self.assertEqual(s["senaryolar"], [{"stil": "risograf", "senaryo": "risograf.json"}])
        self.assertTrue((k / "risograf.json").exists())
        self.assertNotIn("musteri", s)  # kanal müşteri değildir
        self.assertIn("Kısa ve enerjik", (k / "brif.md").read_text(encoding="utf-8"))

    def test_durum_eslemesi(self):
        self.assertEqual(panel.durum({"asama": "onizleme", "onizleme": "/k/o.png"})["durum"], "onay")
        d = panel.durum({"asama": "teslim", "videolar": [{"dosya": "/k/a.mp4", "sonuc": "gecti"}]})
        self.assertEqual((d["durum"], d["teslim_dosyalari"]), ("hazir", ["/k/a.mp4"]))
        s = {"_klasor": str(self.tmp), "panel": {"id": "doc1"}}
        panel.durum_yaz(s, {"asama": "onaylandi"})
        self.assertEqual(json.loads((self.tmp / panel.DOSYA).read_text(encoding="utf-8"))["durum"], "uretimde")
        self.assertIsNone(panel.durum_yaz({"_klasor": str(self.tmp)}, {"asama": "teslim"}))  # panelsiz sipariş


class Animatik(unittest.TestCase):
    def test_anlar_ve_sure(self):
        self.assertEqual(len(animatik.anlar(10, 4, 48)), 40)
        self.assertEqual(len(animatik.anlar(300, 4, 48)), 48)
        self.assertEqual(len(animatik.anlar(1, 4, 48)), 8)
        self.assertIsNone(animatik.sure_bul({"slaytlar": []}))
        self.assertEqual(animatik.sure_bul({"sahneler": [{"sure": 2}, {"sure": 3.5}]}), 5.5)

    @unittest.skipUnless(SKIA and shutil.which("ffmpeg"), "skia ya da ffmpeg yok")
    def test_kucuk_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = Path(tmp) / "animatik.mp4"
            r = animatik.animatik(f"kinetik={DEPO / 'ornekler/kucuk-aliskanliklar/senaryo.json'}", hedef, en_fazla=8,
                                  kare_hizi=0.1)
            self.assertNotIn("hata", r)
            o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,nb_frames", "-of", "csv=p=0",
                                str(hedef)], capture_output=True, text=True).stdout.strip()
            self.assertEqual(o, "360,8")


if __name__ == "__main__":
    unittest.main()
