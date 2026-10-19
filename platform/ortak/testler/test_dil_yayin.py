import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import dil_varyanti as dv  # noqa: E402
import uret  # noqa: E402
import yayin  # noqa: E402

DEPO = HERE.parents[1]
FFMPEG = shutil.which("ffmpeg") is not None

DE_SAHNE = {
    "marka/ad": "Demli Kahve", "sahneler/0/ust": "Demli Kahve", "sahneler/0/metin": "Der erste Schluck",
    "sahneler/0/alt": "jeden Tag frisch geröstet", "sahneler/0/seslendirme": "Der erste Schluck, jeden Tag frisch geröstet.",
    "sahneler/5/sol_deger": "3 Mon.", "sahneler/5/sag_deger": "3 Tage",
    "sahneler/7/birim": " Tassen",  # grafik sahnesi (#54): birim ≤ 8 karakter
}


def doldur(tablo: Path, ceviri: dict[str, str] | None = None) -> None:
    t = json.loads(tablo.read_text(encoding="utf-8"))
    for a in t["alanlar"]:
        a["ceviri"] = (ceviri or {}).get(a["yol"], a["kaynak"] + " DE")
    tablo.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")


class DilVaryanti(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.sahne = self.tmp / "sahne.json"
        shutil.copy(DEPO / "ornekler/demli-kahve/sahne.json", self.sahne)
        self.cizgi = self.tmp / "tek-cizgi.json"
        shutil.copy(DEPO / "ornekler/hamurkar-firin/tek-cizgi.json", self.cizgi)

    def test_alanlar(self):
        a = {x["yol"]: x for x in dv.alanlar(json.loads(self.sahne.read_text(encoding="utf-8")))}
        self.assertIn("sahneler/1/maddeler/2", a)
        self.assertEqual(a["sahneler/0/metin"]["azami"], 28)
        self.assertTrue(a["marka/ad"]["sabit"])
        self.assertFalse(any(y.endswith(("/tip", "kimlik", "/not")) for y in a))
        b = {x["yol"] for x in dv.alanlar(json.loads(self.cizgi.read_text(encoding="utf-8")))}
        self.assertIn("seslendirme/satirlar/0/metin", b)
        self.assertNotIn("sahneler/4/zemin", b)  # palet anahtarı ("kapanis") çevrilmez
        self.assertFalse(any("palet" in y or y.endswith("/id") for y in b))

    def test_tablo_ve_uygula(self):
        tp = dv.tablo(self.sahne, "de")
        self.assertEqual(tp.name, "sahne.ceviri-de.json")
        with self.assertRaises(ValueError):  # boş tabloyla varyant yok
            dv.uygula(self.sahne, "de")
        doldur(tp, DE_SAHNE)
        r = dv.uygula(self.sahne, "de", ses="liam")
        self.assertEqual(r["hatalar"], [])
        v = json.loads(Path(r["dosya"]).read_text(encoding="utf-8"))
        self.assertEqual(v["sahneler"][0]["metin"], "Der erste Schluck")
        self.assertEqual(v["dil"], "sahne")  # biçim alanı korunur, dil seslendirmede
        self.assertEqual((v["seslendirme"]["dil"], v["seslendirme"]["ses"]), ("de", "liam"))
        self.assertEqual(v["kimlik"], "demli-kahve-sahne-de")
        self.assertEqual(v["dil_varyanti"]["kaynak_dil"], "tr")
        # yeniden tablo eski çevirileri korur
        dv.tablo(self.sahne, "de")
        self.assertEqual(dv.eksikler(json.loads(tp.read_text(encoding="utf-8"))), [])

    def test_ekran_siniri_ve_degisen_kaynak(self):
        tp = dv.tablo(self.sahne, "de")
        cta = next(i for i, sh in enumerate(json.loads(self.sahne.read_text(encoding="utf-8"))["sahneler"]) if sh["tip"] == "cta")
        doldur(tp, {**DE_SAHNE, f"sahneler/{cta}/metin": "Komm vorbei und trink einen Kaffee mit uns"})  # 22 karakter sınırı
        r = dv.uygula(self.sahne, "de")
        self.assertIsNone(r["dosya"])
        self.assertTrue(any(f"sahneler/{cta}/metin" in h and "kısaltın" in h for h in r["hatalar"]))
        s = json.loads(self.sahne.read_text(encoding="utf-8"))
        s["sahneler"][0]["metin"] = "Yeni başlık"
        self.sahne.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        doldur(tp)
        r = dv.uygula(self.sahne, "de")
        self.assertTrue(any("değişmiş" in h for h in r["hatalar"]))

    def test_saniyeli_sablon_esner(self):
        tp = dv.tablo(self.cizgi, "de")
        uzun = "Jeden Morgen gibt es bei uns nur genau fünfzig frisch gebackene Butter Croissants."
        doldur(tp, {"seslendirme/satirlar/0/metin": uzun})
        r = dv.uygula(self.cizgi, "de")
        self.assertEqual(r["hatalar"], [])
        self.assertGreater(r["esneme"], 1.0)
        v = json.loads(Path(r["dosya"]).read_text(encoding="utf-8"))
        s = json.loads(self.cizgi.read_text(encoding="utf-8"))
        o = r["esneme"]
        self.assertAlmostEqual(v["sure"], round(s["sure"] * o, 3))
        self.assertAlmostEqual(v["sahneler"][2]["sayac"]["bitis_t"], round(s["sahneler"][2]["sayac"]["bitis_t"] * o, 3))
        self.assertEqual(v["sahneler"][4]["olcek"], s["sahneler"][4]["olcek"])  # zaman olmayan sayı değişmez
        self.assertNotIn("okunus", json.dumps(v))

    def test_siparis_diller(self):
        sp = self.tmp / "siparis.json"
        sp.write_text(json.dumps({"is": "d", "dil": "tr", "diller": ["tr", "de"], "dil_sesleri": {"de": "liam"},
                                  "senaryolar": [{"senaryo": "tek-cizgi.json", "stil": "tek-cizgi"}]}), encoding="utf-8")
        with self.assertRaises(ValueError) as e:
            uret.oku(sp)
        self.assertIn("tek-cizgi.ceviri-de.json", str(e.exception))
        doldur(self.tmp / "tek-cizgi.ceviri-de.json")
        s = uret.oku(sp)
        self.assertEqual([(g["etiket"], g["dil"]) for g in s["senaryolar"]], [("tr", "tr"), ("de", "de")])
        de = s["senaryolar"][1]
        self.assertTrue(de["senaryo"].endswith("tek-cizgi.de.json"))
        self.assertEqual(uret.cikti_klasoru(s, de).name, "cikti-de")
        self.assertEqual(uret.ses_bayraklari(s, de), ["--ses", "liam"])
        self.assertEqual(uret.ses_bayraklari(s, s["senaryolar"][0]), [])

    def test_tek_dil_eskisi_gibi(self):
        sp = self.tmp / "siparis.json"
        sp.write_text(json.dumps({"is": "d", "senaryo": "tek-cizgi.json", "stil": "tek-cizgi"}), encoding="utf-8")
        s = uret.oku(sp)
        self.assertEqual(uret.cikti_klasoru(s, s["senaryolar"][0]).name, "cikti")
        self.assertFalse((self.tmp / "tek-cizgi.ceviri-de.json").exists())


class YayinMetni(unittest.TestCase):
    def test_oneriler_ve_sinir(self):
        s = json.loads((DEPO / "ornekler/demli-kahve/sahne.json").read_text(encoding="utf-8"))
        m = yayin.oneriler(s, {"dil": "tr"}, "tr", None, kisa=True)
        self.assertEqual(m["youtube"]["baslik"], "Sabahın ilk yudumu #shorts")
        self.assertIn("Gel, bir fincan iç.", m["youtube"]["aciklama"])
        self.assertEqual(m["youtube"]["etiketler"][0], "demlikahve")
        self.assertLessEqual(m["instagram"]["aciklama"].count("#"), 5)
        self.assertEqual(yayin.denetle(m), [])
        s["yayin"] = {"baslik": "Kentin en iyi kahvesi", "etiketler": ["#kahve", "moda kahve"]}
        m = yayin.oneriler(s, None, "tr", None, kisa=False)
        self.assertEqual(m["youtube"]["etiketler"], ["kahve", "modakahve"])
        self.assertTrue(any("TEMEL-EN-IYI" in b["mesaj"] for b in yayin.denetle(m)))
        m["youtube"]["baslik"] = "x" * 101
        self.assertTrue(any(b["yer"] == "youtube.baslik" for b in yayin.denetle(m)))

    def test_almanca_anahtar(self):
        k = yayin.anahtar_kelimeler(["Eine Marke ist kein Logo.", "Vertrauen schafft Wert, nicht wegen des Preises.",
                                     "Marke und Vertrauen."], "de")
        self.assertEqual(k[:2], ["marke", "vertrauen"])
        self.assertNotIn("kein", k)
        self.assertNotIn("wegen", k)


@unittest.skipUnless(FFMPEG, "ffmpeg yok")
class YayinPaketi(unittest.TestCase):
    def test_paket(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        cikti = tmp / "cikti"
        cikti.mkdir()
        video = cikti / "deneme-16x9.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc=size=640x360:rate=10:duration=3", "-pix_fmt", "yuv420p", str(video)], check=True)
        (cikti / "deneme-16x9.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nMerhaba\n", encoding="utf-8")
        sen = tmp / "a.json"
        sen.write_text(json.dumps({"kimlik": "a", "seslendirme": {"dil": "de", "satirlar": [
            {"id": "v0", "t": 0.2, "metin": "Was ist eine Marke?"}]}, "yayin": {"kapak": 1.5}}), encoding="utf-8")
        p = yayin.paketle(video, sen, {"_klasor": str(tmp), "dil": "tr", "baslik": "Markalaşma nedir?"})
        k = Path(p["klasor"])
        self.assertEqual(k, tmp / "yayin" / "deneme-16x9")
        for ad in ("deneme-16x9.mp4", "kapak.jpg", "kapak-youtube.jpg", "altyazi.srt", "metin.json", "YUKLE.md"):
            self.assertTrue((k / ad).exists(), ad)
        self.assertEqual(p["dil"], "de")
        self.assertEqual(p["metin"]["youtube"]["baslik"], "Was ist eine Marke?")  # Türkçe sipariş başlığı alınmaz
        self.assertEqual(yayin.boyut(k / "kapak-youtube.jpg"), (1280, 720))
        self.assertIsNone(yayin.bolum_listesi(video, None, 3.0))


if __name__ == "__main__":
    unittest.main()
