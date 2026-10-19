import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import render_suresi  # noqa: E402
import uret  # noqa: E402

DEPO = HERE.parents[1]
SKIA = importlib.util.find_spec("skia") is not None and importlib.util.find_spec("numpy") is not None


def calistir(*arg: str, ortam: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HERE / "uret.py"), *arg], capture_output=True, text=True,
                          env={**os.environ, **(ortam or {})})


class RenderSuresi(unittest.TestCase):
    def test_olcum(self):
        r = {"dosya": "/x/a.mp4", "akis": {"sure": 10.0, "video": {"fps": 24}}}
        os.environ["STUDYO_RENDER_BASLANGIC"] = "100"
        os.environ["STUDYO_STIL"] = "risograf"
        try:
            o = render_suresi.olc(r, simdi=148)
        finally:
            del os.environ["STUDYO_RENDER_BASLANGIC"], os.environ["STUDYO_STIL"]
        self.assertEqual(o, {"stil": "risograf", "render_sn": 48.0, "kare": 240, "sn_kare": 0.2})
        self.assertNotIn("render", render_suresi.ekle(dict(r)))  # ortamda başlangıç yoksa eklenmez

    def test_tablo(self):
        r = {"dosya": "/x/a.mp4", "akis": {"sure": 10.0}, "render": {"stil": "kinetik", "render_sn": 30.0, "kare": 240,
                                                                     "sn_kare": 0.125}}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "g" / "render-sureleri.csv"
            render_suresi.kaydet(p, "deneme", "9x16", r)
            render_suresi.kaydet(p, "deneme", "16x9", r)
            satirlar = p.read_text(encoding="utf-8").splitlines()
        self.assertEqual(satirlar[0].split(","), render_suresi.ALANLAR)
        self.assertEqual(len(satirlar), 3)
        self.assertIn("kinetik,9x16,10.0,240,30.0,0.125,a.mp4", satirlar[1])


class Siparis(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        shutil.copy(DEPO / "ornekler/kucuk-aliskanliklar/senaryo.json", self.tmp / "kinetik.json")
        shutil.copy(DEPO / "ornekler/kucuk-aliskanliklar/risograf.json", self.tmp / "risograf.json")

    def siparis(self, **ek) -> Path:
        s = {"is": "deneme", "baslik": "Deneme", "senaryolar": [{"senaryo": "kinetik.json", "stil": "kinetik"},
                                                               {"senaryo": "risograf.json"}], **ek}
        p = self.tmp / "siparis.json"
        p.write_text(json.dumps(s), encoding="utf-8")
        return p

    def test_stil_dosya_adindan(self):
        s = uret.oku(self.siparis())
        self.assertEqual([g["stil"] for g in s["senaryolar"]], ["kinetik", "risograf"])
        self.assertEqual(uret.cikti_klasoru(s, s["senaryolar"][1]).name, "cikti-risograf")

    def test_eksik_alan(self):
        p = self.tmp / "bos.json"
        p.write_text(json.dumps({"senaryo": "yok.json"}), encoding="utf-8")
        r = calistir(str(p))
        self.assertEqual(r.returncode, 2)
        self.assertIn('"is"', r.stderr)
        self.assertIn("bulunamadı", r.stderr)

    def test_onizlemesiz_onay_yok(self):
        r = calistir(str(self.siparis()), "--onay")
        self.assertEqual(r.returncode, 1)
        self.assertIn("önce önizleme", r.stderr)

    def test_kapanis_teslimden_sonra(self):
        p = self.siparis()
        csv = self.tmp / "maliyet.csv"
        r = calistir(str(p), "--kapat", "--usd", "1.2", "--maliyet-csv", str(csv))
        self.assertEqual(r.returncode, 1)
        (self.tmp / uret.DURUM).write_text(json.dumps({"asama": "teslim", "elevenlabs_karakter": 412, "videolar": [
            {"stil": "risograf", "dosya": "a.mp4"}]}), encoding="utf-8")
        r = calistir(str(p), "--kapat", "--usd", "1.2", "--cevap", "3", "--maliyet-csv", str(csv),
                     ortam={"STUDYO_PAYLASIM": str(self.tmp)})
        self.assertEqual(r.returncode, 0, r.stderr)
        satir = csv.read_text(encoding="utf-8").splitlines()
        self.assertEqual(satir[0].split(","), uret.MALIYET_ALANLARI)
        self.assertTrue(satir[1].endswith(",Deneme,uretim,1,1,0,3,0,0,1.20,412"), satir[1])
        self.assertEqual(json.loads((self.tmp / uret.DURUM).read_text(encoding="utf-8"))["asama"], "kapandi")
        k = [json.loads(x) for x in (self.tmp / "gelistirme" / "katalog.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual((k[0]["stil"], k[0]["maliyet_usd"], k[0]["kaynak"]), ("risograf", 1.2, "siparis"))

    @unittest.skipUnless(SKIA, "skia yok")
    def test_onizlemede_durur(self):
        p = self.siparis(senaryolar=[{"senaryo": "kinetik.json", "stil": "kinetik"}])
        r = calistir(str(p))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("onayı bekleniyor", r.stdout)
        self.assertTrue((self.tmp / "onizleme.png").exists())
        d = json.loads((self.tmp / uret.DURUM).read_text(encoding="utf-8"))
        self.assertEqual(d["asama"], "onizleme")
        self.assertEqual([p for p in self.tmp.rglob("*.mp4") if p.name != "animatik.mp4"], [])  # onaydan önce render yok
        self.assertEqual(d["animatik"][0]["dosya"], str(self.tmp / "animatik.mp4"))  # yalnız küçük, sessiz taslak


if __name__ == "__main__":
    unittest.main()
