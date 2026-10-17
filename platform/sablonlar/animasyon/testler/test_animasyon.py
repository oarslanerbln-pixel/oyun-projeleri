import contextlib
import io
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yardim  # noqa: E402
from yardim import BASLIK, proje_kur  # noqa: E402

import animasyon  # noqa: E402
import cekimler  # noqa: E402
import cizim  # noqa: E402
import proje  # noqa: E402

DEPO = Path(__file__).resolve().parents[4]
ORNEK = DEPO / "ornekler" / "demli-kahve" / "proje.json"


def bulgular(b, seviye=None):
    return [str(x) for x in b if seviye is None or x.seviye == seviye]


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def yukle(self, **kw):
        return proje.yukle(proje_kur(self.kok, **kw))


class CekimOkuTests(Tmp):
    def oku(self, rows, header=BASLIK):
        p = self.kok / "c.csv"
        p.write_text(header + rows, encoding="utf-8")
        return cekimler.oku(p)

    def test_valid(self):
        liste, b = self.oku("C01,2,,,,,,,,,,,,,\n")
        self.assertEqual(b, [])
        c = liste[0]
        self.assertEqual((c.gecis, c.durum, c.odak_x, c.zemin, c.on, c.logo), ("kesme", "animatik", 0.5, "zemin", "metin", False))

    def test_row_errors(self):
        _, b = self.oku("C01,2,,,,,,,,,,,,,\n"
                        "C01,2,,,,,,,,,,,,,\n"
                        "C02,0,,,,,,,,,,,,,\n"
                        "C03,1,,,,,silme,1.5,,Z,bitti,,,belki,\n")
        h = bulgular(b, "HATA")
        for parca in ("tekrar", "sure_sn", "gecis", "odak_x", "durum", "sinif", "logo"):
            self.assertTrue(any(parca in x for x in h), parca)

    def test_missing_required_and_unknown_columns(self):
        _, b = self.oku("2\n", header="sure_sn\n")
        self.assertTrue(any("'cekim'" in x for x in bulgular(b, "HATA")))
        _, b = self.oku("C01,2,x\n", header="cekim,sure_sn,renk\n")
        self.assertTrue(any("bilinmeyen sütun" in x for x in bulgular(b, "UYARI")))

    def test_empty(self):
        _, b = self.oku("")
        self.assertTrue(any("en az bir" in x for x in bulgular(b, "HATA")))


class ZamanTests(unittest.TestCase):
    def test_contiguous_without_drift(self):
        liste = [cekimler.Cekim(str(i), 1 / 3) for i in range(9)]
        tl = cekimler.zaman_cizelgesi(liste, 30)
        for a, b in zip(tl, tl[1:]):
            self.assertEqual(a.son_kare, b.bas_kare)
            self.assertEqual(a.son, b.bas)
        self.assertEqual(tl[-1].son_kare, 90)
        self.assertEqual(sum(z.kareler for z in tl), 90)

    def test_timecode(self):
        self.assertEqual(cizim.timecode(3725.5), "01:02:05,500")
        self.assertEqual(cizim.timecode(2, "."), "00:00:02.000")


class ProjeTests(Tmp):
    def test_example_project_is_clean(self):
        p, b = proje.yukle(ORNEK)
        self.assertEqual(bulgular(b), [])
        self.assertEqual([k.ad for k in p.kurgular], ["sabah-14", "bumper-6"])
        self.assertEqual(p.kurgular[0].sure, 14)

    def test_small_project_is_clean(self):
        p, b = self.yukle()
        self.assertEqual(bulgular(b), [])
        self.assertEqual(p.marka.kimlik, "test-marka")

    def test_wrong_type_and_missing_fields(self):
        p, b = self.yukle(proje_over={"tur": "oyun", "brif": ""})
        self.assertIsNone(p)
        h = bulgular(b, "HATA")
        self.assertTrue(any("proje.tur" in x for x in h))
        self.assertTrue(any("proje.brif" in x for x in h))

    def test_unknown_preset_and_fps(self):
        k = [{"ad": "k", "cekimler": "p/docs/04-yapi/cekimler.csv", "fps": 29, "teslim": ["sinema"]}]
        _, b = self.yukle(kurgular=k)
        h = bulgular(b, "HATA")
        self.assertTrue(any("sinema" in x for x in h))
        self.assertTrue(any("k.fps" in x for x in h))

    def test_missing_files(self):
        k = [{"ad": "k", "cekimler": "p/yok.csv", "teslim": ["dikey"]}]
        p, b = self.yukle(kurgular=k)
        self.assertIsNone(p)
        self.assertTrue(any("dosya yok" in x for x in bulgular(b, "HATA")))

    def test_brand_forbidden_word_in_text_table(self):
        # Çekimde kullanılmayan anahtar da denetlenir.
        _, b = self.yukle(metin=yardim.METIN.replace("Yavaş", "ACELE ET"))
        self.assertTrue(any("kotu/tr" in x and "MARKA-1" in x for x in bulgular(b, "HATA")))

    def test_brief(self):
        b = proje.brif_denetle({"hedef": " ", "onerme": " ".join(["söz"] * 13) + " ve", "kanitlar": []})
        h, u = bulgular(b, "HATA"), bulgular(b, "UYARI")
        self.assertTrue(any("brif.hedef" in x for x in h))
        self.assertTrue(any("sözcük" in x for x in u))
        self.assertTrue(any("'ve'" in x for x in u))
        self.assertTrue(any("kanıt" in x for x in u))


class KurguDenetimTests(Tmp):
    def test_unknown_key_and_color(self):
        _, b = self.yukle(cekimler=BASLIK + "C01,2,yok,,,,,,,,,mor,,evet,evet\n")
        h = bulgular(b, "HATA")
        self.assertTrue(any("'yok' anahtarı" in x for x in h))
        self.assertTrue(any("'mor' rengi" in x for x in h))

    def test_screen_text_contrast(self):
        _, b = self.yukle(cekimler=BASLIK + "C01,2,,baslik,,,,,,,,zemin,gri,evet,evet\n")
        self.assertTrue(any("kontrast" in x for x in bulgular(b, "HATA")))

    def test_reading_speed(self):
        _, b = self.yukle(cekimler=BASLIK + "C01,2,uzun,uzun,,,,,,,,,,evet,evet\n")
        u = bulgular(b, "UYARI")
        self.assertTrue(any("seslendirme" in x for x in u))
        self.assertTrue(any("ekran yazısı" in x for x in u))

    def test_too_long_for_preset(self):
        k = [{"ad": "k", "cekimler": "p/docs/04-yapi/cekimler.csv", "teslim": ["youtube-bumper"]}]
        p, b = self.yukle(kurgular=k, cekimler=BASLIK + "C01,4,,,,,,,,,,,,evet,\nC02,3,,,,,,,,,,,,,evet\n")
        self.assertIsNone(p)
        self.assertTrue(any("en çok 6" in x for x in bulgular(b, "HATA")))

    def test_late_logo_and_missing_cta(self):
        _, b = self.yukle(cekimler=BASLIK + "C01,4,,,,,,,,,,,,,\nC02,2,,,,,,,,,,,,evet,\n")
        u = bulgular(b, "UYARI")
        self.assertTrue(any("ilk 3 sn" in x for x in u))
        self.assertTrue(any("cagri=evet" in x for x in u))

    def test_no_logo_rule_without_short_preset(self):
        k = [{"ad": "k", "cekimler": "p/docs/04-yapi/cekimler.csv", "teslim": ["yatay-web"]}]
        _, b = self.yukle(kurgular=k, cekimler=BASLIK + "C01,4,,,,,,,,,,,,,evet\n")
        self.assertFalse(any("ilk 3 sn" in x for x in bulgular(b)))


class UretTests(Tmp):
    def test_wrap(self):
        lines = cizim.wrap("bir iki üç dört beş altı yedi sekiz", 10, 60)
        self.assertTrue(all(len(x) <= int(60 / (10 * cizim.CHAR_WIDTH)) for x in lines))
        self.assertEqual(" ".join(lines), "bir iki üç dört beş altı yedi sekiz")
        self.assertEqual(cizim.wrap("çokuzunbirsözcük", 10, 20), ["çokuzunbirsözcük"])

    def test_hareket(self):
        self.assertEqual(cizim.hareket("Yavaş itme"), "yaklas")
        self.assertEqual(cizim.hareket("yavaş çekme"), "uzaklas")
        self.assertEqual(cizim.hareket("sabit"), "sabit")

    def test_example_build(self):
        p, _ = proje.yukle(ORNEK)
        out = self.kok / "cikti"
        rel = {str(x.relative_to(out)) for x in cizim.uret(p, out)}
        for f in ("brif.md", "marka/tokens.css", "marka/figma.json", "marka/unity.uss", "marka/unity.json",
                  "marka/prompt.txt", "sabah-14/manifest.json", "sabah-14/altyazi.tr.srt",
                  "sabah-14/altyazi.en.vtt", "sabah-14/dikey/animatik.html", "sabah-14/kare/kareler/05-C05.svg",
                  "bumper-6/youtube-bumper/animatik.html"):
            self.assertIn(f, rel)
        self.assertFalse(any(x.startswith("bumper-6/altyazi") for x in rel))  # seslendirme yok
        for svg in out.rglob("*.svg"):
            ET.fromstring(svg.read_text(encoding="utf-8"))
        m = json.loads((out / "sabah-14/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((m["fps"], m["kareler"]), (30, 420))
        self.assertEqual([t["oran"] for t in m["teslim"]], ["9:16", "1:1", "4:5"])
        self.assertEqual(m["cekimler"][1]["hareket"], "yaklas")
        srt = (out / "sabah-14/altyazi.en.srt").read_text(encoding="utf-8")
        self.assertTrue(srt.startswith("1\n00:00:02,000 --> 00:00:05,000\nMornings"))
        vtt = (out / "sabah-14/altyazi.tr.vtt").read_text(encoding="utf-8")
        self.assertTrue(vtt.startswith("WEBVTT\n\n00:00:02.000 --> 00:00:05.000\n"))
        html = (out / "sabah-14/dikey/animatik.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('<section class="cekim '), 5)
        self.assertIn("--renk-zemin", html)

    def test_text_is_escaped(self):
        p, b = self.yukle(cekimler=BASLIK + "C01,2,,kotu,<görsel> & not,,,,,,,,,evet,evet\n")
        self.assertIsNotNone(p, bulgular(b))
        out = self.kok / "cikti"
        cizim.uret(p, out)
        svg = (out / "k/dikey/kareler/01-C01.svg").read_text(encoding="utf-8")
        self.assertIn("&lt;b&gt;&amp;&lt;/b&gt;", svg)
        self.assertIn("&lt;görsel&gt; &amp; not", svg)
        ET.fromstring(svg)


class CliTests(Tmp):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = animasyon.main(list(argv))
        return code, buf.getvalue()

    def test_example(self):
        code, out = self.run_cli("denetle", str(ORNEK))
        self.assertEqual(code, 0, out)
        self.assertIn("Tamam: Demli Kahve", out)

    def test_errors_exit_1(self):
        code, out = self.run_cli("uret", str(self.kok / "yok.json"))
        self.assertEqual(code, 1)
        self.assertIn("Üretim yapılmadı", out)

    def test_new_check_build(self):
        (self.kok / "platform").mkdir()
        hedef = self.kok / "musteriler" / "yeni"
        code, out = self.run_cli("yeni", str(hedef), "--ad", "Yeni Işık")
        self.assertEqual(code, 0, out)
        data = json.loads((hedef / "proje.json").read_text(encoding="utf-8"))
        self.assertEqual(data["kimlik"], "yeni-isik")
        self.assertEqual(data["marka"], "musteriler/yeni/marka/marka.json")
        code, out = self.run_cli("denetle", str(hedef / "proje.json"))
        self.assertEqual(code, 0, out)
        code, out = self.run_cli("uret", str(hedef / "proje.json"))
        self.assertEqual(code, 0, out)
        self.assertTrue((hedef / "cikti/tanitim/dikey/animatik.html").exists())
        code, _ = self.run_cli("yeni", str(hedef))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
