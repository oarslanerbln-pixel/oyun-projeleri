import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seslendirme  # noqa: E402
import yonetmen  # noqa: E402

SATIRLAR = [{"id": "s0", "metin": "Otuz bir Ekim'de ne olacak?"},
            {"id": "s1", "metin": "Çağrı %40 daha fazla paylaşıldı"},
            {"id": "s2", "metin": "Altmış beş yıllık gurbet... hasret... bitmedi."},
            {"id": "s3", "metin": "Siz ne düşünüyorsunuz?"}]


class Yonetmen(unittest.TestCase):
    def test_rol_ton_ve_tarz(self):
        p = yonetmen.yonet(SATIRLAR, "ciddi-analiz", "cjVigY5qzO86Huf0OWal", "tr")
        self.assertEqual([x["rol"] for x in p], ["kanca", "bilgi", "govde", "kapanis"])
        self.assertEqual([x["ton"] for x in p], ["vurgulu", "sakin", "duygusal", "vurgulu"])
        self.assertEqual(p[1]["metin"], "Çağrı yüzde 40 daha fazla paylaşıldı.")
        # ciddi tarzda satır içi "..." virgüle döner (uzun bekleme yok), style tavanı aşılmaz
        self.assertNotIn("...", p[2]["metin"])
        self.assertTrue(all(x["voice_settings"]["style"] <= 0.25 for x in p))
        self.assertEqual((p[1]["onceki"], p[1]["sonraki"]), (p[0]["metin"], p[2]["metin"]))
        # aynı tarzda ayarlar satırdan satıra değişir; reklam tarzı ciddi tarzdan daha canlı
        self.assertGreater(len({json.dumps(x["voice_settings"], sort_keys=True) for x in p}), 3)
        r = yonetmen.yonet(SATIRLAR, "sicak-reklam")
        self.assertGreater(r[0]["voice_settings"]["style"], p[0]["voice_settings"]["style"])
        # senaryonun tonu önce gelir; aynı metin hep aynı ayarı alır (önbellek)
        q = yonetmen.yonet([dict(SATIRLAR[1], ton="enerjik")], "anlatim")
        self.assertEqual((q[0]["ton"], q[0]["neden"]), ("enerjik", "senaryo"))
        self.assertEqual(yonetmen.yonet(SATIRLAR, "ciddi-analiz"), yonetmen.yonet(SATIRLAR, "ciddi-analiz"))
        with self.assertRaises(ValueError):
            yonetmen.yonet(SATIRLAR, "yok")

    def test_duzelt(self):
        self.assertEqual(yonetmen.duzelt("Das sind 40 % z. B. mehr", "de"), "Das sind 40 Prozent zum Beispiel mehr.")
        self.assertEqual(yonetmen.duzelt("Jetzt richten sich die Blicke … nach Berlin", "de"), "Jetzt richten sich die Blicke nach Berlin.")
        self.assertEqual(yonetmen.duzelt("Bir... iki... üç", "tr", 1), "Bir... iki, üç.")
        self.assertEqual(yonetmen.duzelt("Ve sonra...", "tr"), "Ve sonra.")
        self.assertEqual(yonetmen.duzelt("Kim kazandı — biz", "tr"), "Kim kazandı, biz.")

    def test_tempo_denetimi(self):
        u = yonetmen.denetle([{"id": "a", "metin": "x" * 60, "sure": 2.0}, {"id": "b", "metin": "x" * 60, "sure": 4.5}],
                             "ciddi-analiz")
        self.assertEqual([(x["id"], x["sorun"]) for x in u], [("a", "hızlı")])

    def test_uzun_durak_kisalir(self):
        import wave
        with tempfile.TemporaryDirectory() as tmp:
            yol, hiz = Path(tmp) / "a.wav", Path(tmp) / "a.hizalama.json"
            ses = b"\xff\x3f" * 4800  # 0.1 sn ses
            with wave.open(str(yol), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
                w.writeframes(ses + b"\x00\x00" * 48000 + ses)  # arada 1 sn sessizlik
            hiz.write_text(json.dumps({"karakterler": ["a", "b"], "bas": [0.0, 1.1], "son": [0.1, 1.2]}))
            k = yonetmen.duraklari_kisalt(yol, 0.5, hiz)
            self.assertAlmostEqual(k[0][1], 0.5, delta=0.02)
            with wave.open(str(yol)) as w:
                self.assertAlmostEqual(w.getnframes() / 48000, 0.7, delta=0.02)
            self.assertAlmostEqual(json.loads(hiz.read_text())["bas"][1], 0.6, delta=0.02)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg yok")
    def test_uret_yonetmenle(self):
        gelen = []

        def sahte(metin, ayar):
            gelen.append(seslendirme.eleven_ayar(ayar))
            return b"\x10\x20" * 4800, 48000

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k", "STUDYO_SES_ONBELLEK": str(Path(tmp) / "ob")}, clear=True), \
                mock.patch.dict(seslendirme.SAGLAYICILAR, {"elevenlabs": sahte}), \
                mock.patch.dict(seslendirme.KREDI, {"elevenlabs": lambda: {"plan": "free", "limit": 1, "harcanan": 0, "kalan": 9999}}):
            k = seslendirme.uret(SATIRLAR[:2], Path(tmp) / "c", "elevenlabs", {"ses": "eric", "tarz": "ciddi-analiz"})
            self.assertEqual(k["yonetmen"]["tarz"], "ciddi-analiz")
            self.assertEqual(gelen[0]["onceki"] if "onceki" in gelen[0] else None, None)
            self.assertEqual(gelen[1]["onceki"], "Otuz bir Ekim'de ne olacak?")
            self.assertNotEqual(gelen[0]["voice_settings"], gelen[1]["voice_settings"])
            self.assertEqual(k["satirlar"][1]["metin"], "Çağrı yüzde 40 daha fazla paylaşıldı.")
            gelen.clear()  # yönetmen kapalı: tek ayar
            seslendirme.uret(SATIRLAR[:2], Path(tmp) / "d", "elevenlabs", {"ses": "eric", "yonetmen": False})
            self.assertEqual(gelen[0]["voice_settings"], gelen[1]["voice_settings"])


if __name__ == "__main__":
    unittest.main()
