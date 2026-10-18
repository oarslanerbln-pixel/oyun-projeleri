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

    def test_ses_kimligi_yoksa_hata(self):
        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k"}, clear=True):
            with self.assertRaisesRegex(seslendirme.SeslendirmeHatasi, "ses kimliği"):
                seslendirme.elevenlabs("merhaba", {})

    def test_istek_bicimi(self):
        yakalanan = {}

        def ag(istek):
            yakalanan["url"] = istek.full_url
            yakalanan["basliklar"] = dict(istek.header_items())
            yakalanan["govde"] = json.loads(istek.data)
            return b"\x00\x00" * 10

        with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "gizli"}, clear=True):
            pcm, sr = seslendirme.elevenlabs("Bugün başla.", {"ses": "abc"}, ag=ag)
        self.assertEqual(sr, 44100)
        self.assertEqual(len(pcm), 20)
        self.assertIn("/text-to-speech/abc?output_format=pcm_44100", yakalanan["url"])
        self.assertEqual(yakalanan["basliklar"]["Xi-api-key"], "gizli")
        self.assertEqual(yakalanan["govde"]["text"], "Bugün başla.")
        self.assertEqual(yakalanan["govde"]["language_code"], "tr")


class Piper(unittest.TestCase):
    def test_lisans_kapisi(self):
        with self.assertRaisesRegex(seslendirme.SeslendirmeHatasi, "ticari işte kullanılamaz"):
            seslendirme.piper("x", {"ses": "dfki", "ticari": True})

    def test_bilinmeyen_ses(self):
        with self.assertRaisesRegex(seslendirme.SeslendirmeHatasi, "bilinmeyen"):
            seslendirme.piper("x", {"ses": "yok"})


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

    def test_bilinmeyen_saglayici(self):
        with self.assertRaises(seslendirme.SeslendirmeHatasi):
            seslendirme.uret([], Path(tempfile.gettempdir()), "yok")


if __name__ == "__main__":
    unittest.main()
