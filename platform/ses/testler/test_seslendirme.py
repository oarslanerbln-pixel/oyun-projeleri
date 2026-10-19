import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import seslendirme  # noqa: E402

FFMPEG = shutil.which("ffmpeg") is not None


def ton(metin, ayar):
    """sahte sağlayıcı: metin uzunluğuyla orantılı, başı ve sonu sessiz 220 Hz ton"""
    import math
    sr = 22050
    n = int(sr * (0.2 + 0.05 * len(metin)))
    ornek = [0] * int(sr * 0.2) + [int(8000 * math.sin(2 * math.pi * 220 * i / sr)) for i in range(n)] + [0] * int(sr * 0.2)
    return b"".join(int(x).to_bytes(2, "little", signed=True) for x in ornek), sr


class ElevenLabs(unittest.TestCase):
    def test_anahtar_yoksa_acik_hata(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(seslendirme.SeslendirmeHatasi, "ELEVENLABS_API_KEY"):
                seslendirme.elevenlabs("merhaba", {"ses": "x"})

    def test_ses_verilmezse_dilin_varsayilani(self):
        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k"}, clear=True):
            self.assertEqual(seslendirme.eleven_ayar({})["ses"], seslendirme.ELEVEN_SESLERI["erkek"]["id"])
            # senaryolardaki Piper adı: dili ve cinsiyeti alınır
            e = seslendirme.eleven_ayar({"ses": "kerstin"})
            self.assertEqual((e["ses"], e["dil"]), (seslendirme.ELEVEN_SESLERI["kadin"]["id"], "de"))
            self.assertEqual(seslendirme.eleven_ayar({"ses": "abc123"})["ses"], "abc123")
        with mock.patch.dict(os.environ, {"ELEVENLABS_VOICE_ID_DE": "almanca"}, clear=True):
            self.assertEqual(seslendirme.eleven_ayar({"dil": "de"})["ses"], "almanca")

    def test_otomatik_saglayici(self):
        # varsayılan ElevenLabs (Atilla, 2026-10-19); senaryo bilerek Piper isteyebilir, komut satırı ikisini de ezer
        self.assertEqual(seslendirme.saglayici_coz("otomatik"), "elevenlabs")
        self.assertEqual(seslendirme.saglayici_coz(None), "elevenlabs")
        self.assertEqual(seslendirme.saglayici_coz(None, {"saglayici": "piper"}), "piper")
        self.assertEqual(seslendirme.saglayici_coz("piper", {"saglayici": "elevenlabs"}), "piper")

    def test_kredi_sorgusu(self):
        def ag(istek):
            self.assertTrue(istek.full_url.endswith("/v1/user/subscription"))
            return json.dumps({"tier": "free", "character_limit": 10000, "character_count": 1022}).encode()

        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k"}, clear=True):
            k = seslendirme.eleven_kredi(ag=ag)
        self.assertEqual((k["plan"], k["kalan"]), ("free", 8978))
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(seslendirme.SeslendirmeHatasi, "ELEVENLABS_API_KEY"):
                seslendirme.eleven_kredi(ag=ag)

    def test_istek_bicimi(self):
        yakalanan = {}

        def ag(istek):
            yakalanan["url"] = istek.full_url
            yakalanan["basliklar"] = dict(istek.header_items())
            yakalanan["govde"] = json.loads(istek.data)
            return b"mp3"

        cozulen = []
        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "gizli"}, clear=True), \
                mock.patch.object(seslendirme, "mp3_coz", lambda b: cozulen.append(b) or b"\x00\x00" * 10):
            pcm, sr = seslendirme.elevenlabs("Bugün başla.", {"ses": "abc"}, ag=ag)
            self.assertEqual(sr, 44100)
            self.assertEqual((len(pcm), cozulen), (20, [b"mp3"]))
            # ücretsiz ve Starter planda pcm_44100 yok (403); mp3 istenir
            self.assertIn("/text-to-speech/abc?output_format=mp3_44100_128", yakalanan["url"])
        self.assertEqual(yakalanan["basliklar"]["Xi-api-key"], "gizli")
        self.assertEqual(yakalanan["govde"]["text"], "Bugün başla.")
        self.assertNotIn("language_code", yakalanan["govde"])  # multilingual_v2 dil alanını reddeder
        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "gizli"}, clear=True), \
                mock.patch.object(seslendirme, "mp3_coz", lambda b: b"\x00\x00"):
            seslendirme.elevenlabs("Heute.", {"ses": "abc", "model": "eleven_flash_v2_5", "dil": "de"}, ag=ag)
        self.assertEqual(yakalanan["govde"]["language_code"], "de")


class Piper(unittest.TestCase):
    def test_lisans_kapisi(self):
        with self.assertRaisesRegex(seslendirme.SeslendirmeHatasi, "ticari işte kullanılamaz"):
            seslendirme.piper("x", {"ses": "dfki", "ticari": True})

    def test_bilinmeyen_ses(self):
        with self.assertRaisesRegex(seslendirme.SeslendirmeHatasi, "bilinmeyen"):
            seslendirme.piper("x", {"ses": "yok"})


def kredi(kalan):
    return {"elevenlabs": lambda: {"plan": "free", "limit": 10000, "harcanan": 10000 - kalan, "kalan": kalan}}


@unittest.skipUnless(FFMPEG, "ffmpeg yok")
class Uret(unittest.TestCase):
    def test_cila_seviye_ve_kayit(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(seslendirme.SAGLAYICILAR, {"sahte": ton}):
            k = seslendirme.uret([{"id": "a", "metin": "kısa"}, {"id": "b", "metin": "biraz daha uzun bir satır"}],
                                 Path(tmp), "sahte")
            self.assertEqual([s["id"] for s in k["satirlar"]], ["a", "b"])
            for s in k["satirlar"]:
                yol = Path(tmp) / f"{s['id']}.wav"
                with seslendirme.wave.open(str(yol)) as w:
                    self.assertEqual(w.getframerate(), seslendirme.ORNEKLEME)
                self.assertAlmostEqual(seslendirme.olc_lufs(yol), seslendirme.HEDEF_LUFS, delta=1.5)
            # baş ve sondaki sessizlik kırpılır: süre ham sesten (0.4 sn sessizlik dahil) kısa
            self.assertLess(k["satirlar"][0]["sure"], 0.2 + 0.05 * 4 + 0.2)
            kayit = json.loads((Path(tmp) / "seslendirme.json").read_text(encoding="utf-8"))
            self.assertEqual(kayit["saglayici"], "sahte")

    def test_onbellek_ve_kullanim_kaydi(self):
        cagri = []

        def sahte_eleven(metin, ayar):
            cagri.append(metin)
            return ton(metin, ayar)

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k", "STUDYO_SES_ONBELLEK": str(Path(tmp) / "ob")}, clear=True), \
                mock.patch.dict(seslendirme.SAGLAYICILAR, {"elevenlabs": sahte_eleven}), \
                mock.patch.dict(seslendirme.KREDI, kredi(5000)):
            satirlar = [{"id": "a", "metin": "Bugün başla."}, {"id": "b", "metin": "Her gün yüzde bir."}]
            k1 = seslendirme.uret(satirlar, Path(tmp) / "c1", "elevenlabs")
            self.assertEqual(k1["saglayici"], "elevenlabs")
            self.assertEqual(k1["kullanim"]["karakter"], len("Bugün başla.") + len("Her gün yüzde bir."))
            k2 = seslendirme.uret(satirlar, Path(tmp) / "c2", "elevenlabs")  # aynı metin: kredi harcanmaz
            self.assertEqual(len(cagri), 2)
            self.assertEqual((k2["kullanim"]["karakter"], k2["kullanim"]["onbellek"]), (0, 2))
            self.assertEqual([s["sure"] for s in k1["satirlar"]], [s["sure"] for s in k2["satirlar"]])
            self.assertEqual(seslendirme.kullanim_ozeti()["karakter"], k1["kullanim"]["karakter"])

    def test_otomatikte_eleven_hatasi_pipera_doner(self):
        def bozuk(metin, ayar):
            raise seslendirme.SeslendirmeHatasi("ElevenLabs'e ulaşılamadı")

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k", "STUDYO_SES_ONBELLEK": tmp}, clear=True), \
                mock.patch.dict(seslendirme.SAGLAYICILAR, {"elevenlabs": bozuk, "piper": ton}), \
                mock.patch.dict(seslendirme.KREDI, kredi(5000)):
            k = seslendirme.uret([{"id": "a", "metin": "kısa"}], Path(tmp) / "c")
            self.assertEqual(k["saglayici"], "piper")
            # yedek seslendirme.json'a yazılır; kalite raporu buradan uyarır
            kayit = json.loads((Path(tmp) / "c" / "seslendirme.json").read_text(encoding="utf-8"))
            self.assertEqual(kayit["yedek"]["istenen"], "elevenlabs")
            self.assertIn("ulaşılamadı", kayit["yedek"]["neden"])
            with self.assertRaises(seslendirme.SeslendirmeHatasi):  # açıkça istenince düşmez
                seslendirme.uret([{"id": "a", "metin": "kısa"}], Path(tmp) / "c", "elevenlabs")

    def test_anahtar_yoksa_otomatik_piper(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"STUDYO_SES_ONBELLEK": tmp}, clear=True), \
                mock.patch.dict(seslendirme.SAGLAYICILAR, {"piper": ton}):
            k = seslendirme.uret([{"id": "a", "metin": "kısa"}], Path(tmp) / "c")
            self.assertEqual((k["saglayici"], k["ses"]), ("piper", "fahrettin"))
            self.assertIn("ELEVENLABS_API_KEY", k["yedek"]["neden"])

    def test_kredi_yetmezse_is_baslamaz(self):
        cagri = []

        def sahte_eleven(metin, ayar):
            cagri.append(metin)
            return ton(metin, ayar)

        satirlar = [{"id": "a", "metin": "Bugün başla."}, {"id": "b", "metin": "Her gün yüzde bir daha iyi ol."}]
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k", "STUDYO_SES_ONBELLEK": str(Path(tmp) / "ob")}, clear=True), \
                mock.patch.dict(seslendirme.SAGLAYICILAR, {"elevenlabs": sahte_eleven, "piper": ton}):
            with mock.patch.dict(seslendirme.KREDI, kredi(20)):
                with self.assertRaisesRegex(seslendirme.KrediYetersiz, "42 kredi istiyor, hesapta 20"):
                    seslendirme.uret(satirlar, Path(tmp) / "c1", "elevenlabs")
                self.assertEqual(cagri, [])  # yarım iş yok: tek satır bile istenmedi
                k = seslendirme.uret(satirlar, Path(tmp) / "c2")  # otomatik: bütün iş Piper'a
                self.assertEqual(k["saglayici"], "piper")
                self.assertIn("kredisi yetmiyor", k["yedek"]["neden"])
            with mock.patch.dict(seslendirme.KREDI, kredi(100)):
                seslendirme.uret(satirlar[:1], Path(tmp) / "c3", "elevenlabs")
            # önbellekteki satır kredi istemez: kalan 30, gereken yalnız ikinci satır (30)
            with mock.patch.dict(seslendirme.KREDI, kredi(30)):
                k = seslendirme.uret(satirlar, Path(tmp) / "c4", "elevenlabs")
                self.assertEqual((k["kullanim"]["onbellek"], k["kullanim"]["karakter"]), (1, 30))
            # hepsi önbellekteyse hesap hiç sorulmaz
            with mock.patch.dict(seslendirme.KREDI, {"elevenlabs": lambda: self.fail("hesap soruldu")}):
                seslendirme.uret(satirlar, Path(tmp) / "c5", "elevenlabs")

    def test_senaryodan(self):
        yakalanan = {}

        def sahte(metin, ayar):
            yakalanan.setdefault("metin", []).append(metin)
            yakalanan["ayar"] = ayar
            return ton(metin, ayar)

        s = {"dil": "de", "seslendirme": {"ses": "kerstin", "saglayici": "sahte",
                                          "satirlar": [{"id": "a", "metin": "16,90 €", "okunus": "sechzehn neunzig"}]}}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(seslendirme.SAGLAYICILAR, {"sahte": sahte}):
            k = seslendirme.senaryodan(s, Path(tmp))
        self.assertEqual(yakalanan["metin"], ["sechzehn neunzig"])
        self.assertEqual((yakalanan["ayar"]["ses"], yakalanan["ayar"]["dil"]), ("kerstin", "de"))
        self.assertEqual(k["saglayici"], "sahte")

    def test_bilinmeyen_saglayici(self):
        with self.assertRaises(seslendirme.SeslendirmeHatasi):
            seslendirme.uret([], Path(tempfile.gettempdir()), "yok")


if __name__ == "__main__":
    unittest.main()
