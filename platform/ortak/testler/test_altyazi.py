"""altyazi.py: harf zamanlarından kelimeler, gruplar, eşleşme, srt/vtt/ass ve yakma."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import altyazi as a  # noqa: E402


def hizalama(metin, hiz=0.07, bas=0.0):
    """her harf `hiz` sn; boşluklarda 0,05 sn durak"""
    k, b, s, t = [], [], [], bas
    for c in metin:
        d = 0.05 if c == " " else hiz
        k.append(c); b.append(round(t, 3)); s.append(round(t + d, 3)); t += d
    return {"karakterler": k, "bas": b, "son": s}


class Altyazi(unittest.TestCase):
    def test_hizalamadan_kelimeler(self):
        ws = a.hizalamadan(hizalama("Küçük başla. Her gün yap."))
        self.assertEqual([w["k"] for w in ws], ["Küçük", "başla.", "Her", "gün", "yap."])
        self.assertTrue(all(w["son"] > w["bas"] for w in ws))
        self.assertTrue(all(ws[i]["bas"] >= ws[i - 1]["son"] for i in range(1, len(ws))))

    def test_okunus_farkliysa_yayilir_hizalama_yoksa_tahmin(self):
        ws, kaynak = a.satir_kelimeleri("LÉVA serum", 1.0, hizalama("Leva diye okunan serum"))
        self.assertEqual(kaynak, "hizalama")
        self.assertEqual([w["k"] for w in ws], ["LÉVA", "serum"])
        ws, kaynak = a.satir_kelimeleri("bir iki üç", 1.5, None)
        self.assertEqual(kaynak, "tahmin")
        self.assertAlmostEqual(ws[-1]["son"], 1.5)

    def test_gruplar_kisa_ve_ortusmez(self):
        x = [{"kelimeler": a.yay("Her gün sadece yüzde bir daha iyi ol ve bunu her sabah tekrarla.".split(), 0.0, 4.0)}]
        gs = a.gruplar(x)
        self.assertGreater(len(gs), 2)
        for g in gs:
            self.assertLessEqual(len(" ".join(w["k"] for w in g["kelimeler"])), a.AZAMI_KARAKTER)
        for p, q in zip(gs, gs[1:]):
            self.assertLessEqual(p["son"], q["bas"])
        g, i, _ = a.etkin(gs, gs[0]["kelimeler"][1]["bas"] + 0.01)
        self.assertIs(g, gs[0]); self.assertEqual(i, 1)
        self.assertEqual(a.etkin(gs, 99)[0], None)

    def test_an_sayi_ve_ek(self):
        ws = a.yay("Bir yıl sonra otuz yedi kat güçlüsün".split(), 0, 3)
        self.assertEqual(a.an(ws, "37x"), ws[3]["bas"])  # 'Bir' tanımlık, sayı değil
        self.assertEqual(a.an(ws, "güçlü"), ws[6]["bas"])
        ws = a.yay("Her gün yüzde bir".split(), 0, 2)
        self.assertEqual(a.an(ws, "%1"), ws[2]["bas"])
        self.assertIsNone(a.an(ws, "kahve"))
        self.assertIsNone(a.an(ws, "gün", sonra=ws[2]["bas"]))

    def test_dosyalar(self):
        gs = a.gruplar([{"kelimeler": a.yay("Bugün başla. Hemen şimdi.".split(), 1.0, 2.5)}])
        self.assertTrue(a.srt(gs).startswith("1\n00:00:00,940 --> "))
        self.assertTrue(a.vtt(gs).startswith("WEBVTT"))
        ass = a.ass(gs, 1080, 1920, "9x16")
        self.assertIn("\\k", ass); self.assertIn("PlayResY: 1920", ass)
        with tempfile.TemporaryDirectory() as d:
            out = a.yaz(gs, Path(d) / "x")
            self.assertEqual([p.name for p in out], ["x.altyazi.json", "x.srt", "x.vtt"])
            self.assertEqual(json.loads(out[0].read_text(encoding="utf-8")), gs)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg yok")
    def test_yak(self):
        with tempfile.TemporaryDirectory() as d:
            v = Path(d) / "v.mp4"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=270x480:d=2", "-f", "lavfi",
                            "-i", "sine=d=2", "-shortest", "-pix_fmt", "yuv420p", str(v)], check=True)
            gs = a.gruplar([{"kelimeler": a.yay("Bugün başla".split(), 0.2, 1.5)}])
            a.yak(v, gs, v)
            r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "0.8", "-i", str(v), "-frames:v", "1", "-f", "rawvideo",
                                "-pix_fmt", "gray", "-"], capture_output=True, check=True)
            self.assertGreater(max(r.stdout), 100)  # siyah videoda yazı çıktı
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(v)],
                               capture_output=True, text=True)
            self.assertIn("audio", r.stdout)


if __name__ == "__main__":
    unittest.main()
