"""Ortak sahne dili testleri: biçim denetimi, zamanlama, çeviriciler, her kaplamanın her sahne tipini çizmesi, uçtan uca render."""

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

BURADA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BURADA))
import bol  # noqa: E402
import cevir  # noqa: E402
import dil  # noqa: E402
import kanca  # noqa: E402
import sahne  # noqa: E402

DEPO = BURADA.parents[2]
ORNEKLER = [DEPO / "ornekler" / "kucuk-aliskanliklar" / "sahne.json", DEPO / "ornekler" / "demli-kahve" / "sahne.json"]


def ornek(i=1):
    return dil.yukle(ORNEKLER[i])


class Dil(unittest.TestCase):
    def test_ornekler_gecerli(self):
        for p in ORNEKLER:
            self.assertEqual(dil.denetle(dil.yukle(p)), [], p.name)

    def test_her_tip_ornekte(self):
        self.assertEqual({sh["tip"] for sh in ornek()["sahneler"]}, set(dil.TIPLER))

    def test_hatalar(self):
        s = ornek()
        s["sahneler"][0]["tip"] = "yok"
        s["sahneler"][1]["maddeler"] = ["tek"]
        s["sahneler"][2]["deger"] = "123456789"
        s["sahneler"][3]["renk"] = "x"
        s["sahneler"][4]["seslendirme"] = "geçiş konuşmaz"
        h = "\n".join(dil.denetle(s))
        for parca in ("sahne 1: tip", "maddeler", "deger", "bilinmeyen alan renk", "geçiş sahnesi seslendirme almaz"):
            self.assertIn(parca, h)

    def test_zamanlama_seslendirmeden(self):
        s = ornek()
        z = dil.zamanla(s, {"s0": 2.0, "s1": 3.0})
        a, b = z["sahneler"][:2]
        self.assertEqual(a["bas"], 0)
        self.assertAlmostEqual(a["son"], dil.ON + 2.0 + dil.ARKA, 3)
        self.assertAlmostEqual(b["son"] - b["bas"], dil.ON + 3.0 + dil.ARKA, 3)
        ids = [x["id"] for x in z["seslendirme"]["satirlar"]]
        self.assertNotIn("s4", ids)  # geçiş
        self.assertEqual(z["sure"], z["sahneler"][-1]["son"])
        for x, sh in zip(z["seslendirme"]["satirlar"], [sh for sh in z["sahneler"] if sh.get("seslendirme")]):
            self.assertAlmostEqual(x["t"], sh["bas"] + dil.ON, 3)

    def test_bu_dil_mi(self):
        self.assertTrue(dil.bu_dil_mi(ornek()))
        self.assertFalse(dil.bu_dil_mi(json.loads((DEPO / "ornekler/kucuk-aliskanliklar/senaryo.json").read_text(encoding="utf-8"))))


class Cevirici(unittest.TestCase):
    def test_kisa_ornek_her_stile_cevrilir(self):
        z = dil.zamanla(dil.yukle(ORNEKLER[0]))
        for stil in cevir.STILLER:
            self.assertEqual(cevir.denetle(z, stil), [], stil)

    def test_sigmayan_yazi_kesilmez_hata_doner(self):
        z = dil.zamanla(ornek())
        self.assertTrue(cevir.denetle(z, "vitray"))  # alıntı 16 karakterlik başlığa sığmaz


class Grafik(unittest.TestCase):
    def test_csv_okunur(self):
        with tempfile.TemporaryDirectory() as g:
            (Path(g) / "v.csv").write_text("Ay;Satış\nOcak;1.200\nŞubat;1.850,5\n", encoding="utf-8")
            self.assertEqual(dil.veri_oku({"veri": "v.csv"}, g), [("Ocak", 1200.0), ("Şubat", 1850.5)])
            (Path(g) / "w.csv").write_text("a,3\nb,4.5\n", encoding="utf-8")
            self.assertEqual(dil.veri_oku({"veri": "w.csv"}, g), [("a", 3.0), ("b", 4.5)])

    def test_grafik_hatalari(self):
        s = ornek()
        g = next(sh for sh in s["sahneler"] if sh["tip"] == "grafik")
        for degis, parca in (({"tur": "halka"}, "tur"), ({"veri": [["a", 1]]}, "2–8"), ({"veri": [["a", "x"], ["b", 2]]}, "sayı değil"),
                             ({"tur": "pasta", "veri": [["a", -1], ["b", 2]]}, "negatif"), ({"veri": "yok.csv"}, "bulunamadı"),
                             ({"kanca": "yok"}, "kanca")):
            s2 = copy.deepcopy(s)
            next(sh for sh in s2["sahneler"] if sh["tip"] == "grafik").update(degis)
            self.assertIn(parca, "\n".join(dil.denetle(s2)), degis)
        self.assertEqual(dil.bicim(1200, "{} ₺"), "1.200 ₺")
        self.assertEqual(dil.bicim(12.5, "%{}"), "%12,5")

    def test_ceviricide_en_buyuk_deger(self):
        z = dil.zamanla(ornek())
        x = cevir.cevir(z, "kalkis-tabelasi")
        self.assertIn("*260 fincan* Cum", [sh["metin"] for sh in x["sahneler"]])


METIN = """# Küçük alışkanlıklar büyük fark yaratır

Her gün yüzde 1 daha iyi olursan, bir yılın sonunda 37 kat daha iyi olursun. Bu bir sihir değil, matematik.

Başlamak için üç adım:
- Küçük başla
- Her gün aynı saatte yap
- İlerlemeni yaz

Bir yılda tekrar sayısı:
tur: cizgi
Ocak: 20
Nisan: 45
Ağustos: 80

"Başarı, küçük çabaların toplamıdır." — Robert Collier

---

Bu videoyu kaydet ve yarın ilk adımı at.
"""


class Bolme(unittest.TestCase):
    def test_metinden_sahneler(self):
        shs = bol.bol(METIN)
        self.assertEqual([sh["tip"] for sh in shs],
                         ["baslik", "sayi", "karsilastirma", "liste", "grafik", "alinti", "gecis", "cta"])
        self.assertEqual(shs[1]["deger"], "37x")
        self.assertEqual(shs[4]["tur"], "cizgi")
        self.assertEqual(shs[5]["kaynak"], "Robert Collier")
        self.assertEqual(shs[0]["seslendirme"], "Küçük alışkanlıklar büyük fark yaratır")
        s = bol.senaryo(shs, "deneme", "9:16", None)
        self.assertEqual(dil.denetle(s), [])

    def test_almanca_ve_uzun_metin(self):
        shs = bol.bol("Unser Umsatz stieg um 40 %.\n\nJetzt folgen und nichts verpassen!")
        self.assertEqual(shs[0]["tip"], "baslik")
        self.assertEqual(bol._sayi("Unser Umsatz stieg um 40 %.")["deger"], "40%")
        self.assertEqual(shs[-1]["tip"], "cta")
        uzun = "\n\n".join(f"Cümle numarası {k} burada duruyor." for k in range(30))
        with tempfile.TemporaryDirectory() as g:
            (Path(g) / "u.txt").write_text(uzun, encoding="utf-8")
            bol.main([str(Path(g) / "u.txt")])
            self.assertEqual(sorted(p.name for p in Path(g).glob("*.json")), ["u.sahne-1.json", "u.sahne-2.json"])

    def test_kisaltma_kesmez(self):
        self.assertLessEqual(len(bol.kisalt("Bu cümle ekran için fazlasıyla uzun ve kalabalık bir cümle", 28)), 28)
        self.assertEqual(bol.ikiye("Küçük alışkanlıklar büyük fark yaratır", 28, 40), ("Küçük alışkanlıklar", "büyük fark yaratır"))


class Kanca(unittest.TestCase):
    def test_uc_varyant(self):
        s = ornek()
        soru, rakam, sok = (kanca.varyant(s, t) for t in kanca.TURLER)
        self.assertEqual(soru["sahneler"][0]["kanca"], "soru")
        self.assertEqual(len(soru["sahneler"]), len(s["sahneler"]) + 1)
        self.assertEqual(rakam["sahneler"][0]["tip"], "sayi")
        self.assertEqual(len(rakam["sahneler"]), len(s["sahneler"]))  # sayı başa taşındı
        self.assertEqual(sok["sahneler"][0]["kanca"], "sok")
        for v in (soru, rakam, sok):
            self.assertEqual(dil.denetle(v), [], v["kimlik"])

    def test_grafikten_rakam_ve_ozel_metin(self):
        s = ornek()
        s["sahneler"] = [sh for sh in s["sahneler"] if sh["tip"] != "sayi"]
        self.assertEqual(kanca.varyant(s, "rakam")["sahneler"][0]["deger"], "260")
        s["kancalar"] = {"soru": "Hâlâ hazır kahve mi?"}
        v = kanca.varyant(s, "soru")
        self.assertEqual(v["sahneler"][0]["metin"], "Hâlâ hazır kahve mi?")
        self.assertNotIn("kancalar", v)
        s["sahneler"] = [sh for sh in s["sahneler"] if sh["tip"] != "grafik"]
        self.assertIsNone(kanca.varyant(s, "rakam"))
        self.assertEqual(kanca.dil_kodu({"sahneler": [{"seslendirme": "Das ist nicht mit dir und der Welt"}]}), "de")


class Kaplamalar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import skia  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("skia yok")

    def _gorselli(self, kok):
        import skia
        surf = skia.Surface(320, 240)
        with surf as cv:
            cv.clear(0xFFE2603F)
            cv.drawCircle(160, 120, 80, skia.Paint(Color=0xFFFFFFFF))
        surf.makeImageSnapshot().save(str(kok / "urun.png"), skia.kPNG)
        surf.makeImageSnapshot().save(str(kok / "logo.png"), skia.kPNG)
        s = ornek()
        s["_klasor"] = str(kok)
        s["marka"]["logo"] = "logo.png"
        next(sh for sh in s["sahneler"] if sh["tip"] == "urun")["gorsel"] = "urun.png"
        return s

    def test_her_kaplama_her_tipi_cizer(self):
        import skia
        adlar = sahne.kaplama_adlari()
        self.assertGreaterEqual(len(adlar), 6)
        with tempfile.TemporaryDirectory() as g:
            s = self._gorselli(Path(g))
            self.assertEqual(dil.denetle(s), [])
            z = dil.zamanla(s)
            for ad in adlar:
                kap = sahne.kaplama_yap(z, ad)
                for fmt, (W, H) in (("9x16", (216, 384)), ("16x9", (384, 216))):
                    for sh in z["sahneler"]:
                        for t in (sh["bas"] + 0.1, sh["son"] - 0.05):
                            surf = skia.Surface(W, H)
                            with surf as cv:
                                kap.kare(cv, t, W, H, fmt)
                            a = surf.makeImageSnapshot().toarray()
                            self.assertGreater(a[..., :3].std(), 2.0, f"{ad} {fmt} {sh['tip']} {t:.2f}")

    def test_grafik_turleri_ve_sok(self):
        import skia
        s = ornek()
        s["sahneler"] = [{"tip": "grafik", "tur": tur, "veri": [["A", 3], ["B", 5], ["C", 2], ["D", 4]], "baslik": "Deneme",
                          "kaynak": "kaynak", "seslendirme": "bir iki üç dört"} for tur in ("cizgi", "pasta", "cubuk")]
        s["sahneler"][1]["kanca"] = "sok"
        self.assertEqual(dil.denetle(s), [])
        z = dil.zamanla(s)
        for ad in sahne.kaplama_adlari():
            kap = sahne.kaplama_yap(z, ad)
            for fmt, (W, H) in (("9x16", (216, 384)), ("16x9", (384, 216))):
                for sh in z["sahneler"]:
                    surf = skia.Surface(W, H)
                    with surf as cv:
                        kap.kare(cv, sh["son"] - 0.05, W, H, fmt)
                    self.assertGreater(surf.makeImageSnapshot().toarray()[..., :3].std(), 2.0, f"{ad} {fmt} {sh.get('tur')}")

    def test_kelimeye_senkron_ve_altyazi(self):
        import skia
        import senkron
        sys.path.insert(0, str(DEPO / "platform" / "ortak" / "testler"))
        from test_altyazi import hizalama
        with tempfile.TemporaryDirectory() as g:
            sd = Path(g)
            z = dil.zamanla(ornek(0))  # küçük alışkanlıklar
            kayit = []
            for x in z["seslendirme"]["satirlar"]:
                (sd / f"{x['id']}.hizalama.json").write_text(json.dumps(hizalama(x["metin"])), encoding="utf-8")
                kayit.append({"id": x["id"], "metin": x["metin"], "sure": 0.07 * len(x["metin"]), "hizalama": f"{x['id']}.hizalama.json"})
            (sd / "seslendirme.json").write_text(json.dumps({"satirlar": kayit}), encoding="utf-8")
            z = dil.zamanla(ornek(0), {x["id"]: x["sure"] for x in kayit})
            b = senkron.bagla(z, sd)
            liste = next(sh for sh in b["sahneler"] if sh["tip"] == "liste")
            an = [liste["_an"][f"madde{j}"] for j in range(3)]
            self.assertEqual(an, sorted(an)); self.assertGreater(an[2] - an[0], 0.5)  # maddeler söylendikçe
            sayi = next(sh for sh in b["sahneler"] if sh["tip"] == "sayi")
            self.assertGreater(sayi["_an"]["deger"], 0.6)  # "otuz yedi", "Bir yıl" değil
            self.assertTrue(b["_altyazi"])
            self.assertTrue(senkron.acik({"altyazi": True})); self.assertFalse(senkron.acik({}))
            self.assertNotIn("_an", senkron.bagla({**z, "senkron": False}, sd)["sahneler"][0])
            b["altyazi"] = True
            g0 = b["_altyazi"][1]
            t = (g0["kelimeler"][0]["bas"] + g0["kelimeler"][0]["son"]) / 2
            for ad in sahne.kaplama_adlari():
                kaplar = [sahne.kaplama_yap(dict(b, altyazi=False), ad), sahne.kaplama_yap(b, ad)]
                A = [k.alan(1080, 1920, "9x16") for k in kaplar]
                self.assertLess(A[1].bottom(), A[0].bottom() - 150, ad)  # bant ayrıldı
                fark = []
                for k in kaplar:
                    surf = skia.Surface(216, 384)
                    with surf as cv:
                        k.kare(cv, t, 216, 384, "9x16")
                    fark.append(surf.makeImageSnapshot().toarray()[260:300, :, :3].astype(int))
                self.assertGreater(np.abs(fark[0] - fark[1]).mean(), 3.0, ad)  # altyazı bandı çizildi

    def test_sayac(self):
        from kaplama import say
        self.assertEqual(say("37x", 0), "0x")
        self.assertEqual(say("1.200", 1), "1.200")
        self.assertEqual(say("%40", 0.5)[0], "%")
        self.assertEqual(say("yok", 0.3), "yok")

    def test_yeni_stil_kiti_derlenir(self):
        kod = sahne.KIT.format(ad="sulu-boya", sinif="SuluBoya")
        compile(kod, "sulu_boya.py", "exec")
        self.assertIn('ad = "sulu-boya"', kod)

    def test_uctan_uca_render(self):
        import soundfile as sf
        with tempfile.TemporaryDirectory() as g:
            kok = Path(g)
            s = copy.deepcopy(json.loads(ORNEKLER[0].read_text(encoding="utf-8")))
            s["sahneler"] = s["sahneler"][:2] + s["sahneler"][-1:]
            (kok / "s.json").write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
            sd = kok / "cikti" / "seslendirme"; sd.mkdir(parents=True)
            kayit = []
            for i in range(3):
                vid = f"s{i}"
                t = np.arange(int(1.0 * 48000)) / 48000
                sf.write(sd / f"{vid}.wav", (0.3 * np.sin(2 * np.pi * 200 * t)).astype(np.float32), 48000)
                kayit.append({"id": vid, "metin": "bir iki", "sure": 1.0})
            (sd / "seslendirme.json").write_text(json.dumps({"satirlar": kayit}), encoding="utf-8")
            os.environ["STUDYO_KALITE"] = "0"
            self.assertEqual(sahne.main(["uret", str(kok / "s.json"), "--stil", "piksel", "--olcek", "0.2"]), 0)
            mp4 = kok / "cikti" / "kucuk-aliskanliklar-sahne-piksel-9x16.mp4"
            self.assertTrue(mp4.exists() and mp4.stat().st_size > 10000)
            self.assertTrue((kok / "cikti" / "kucuk-aliskanliklar-sahne-piksel.srt").exists())


class Revizyon(unittest.TestCase):
    """`"muzik": false` ve `"yerlesim": "simetrik"`: varsayılan kapalı, açılınca müzik yok / alan ortada"""

    def test_simetrik_alan_ortada(self):
        try:
            import skia  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("skia yok")
        import kaplama
        z = dil.zamanla(ornek(), {})
        kap = kaplama.kaplamalar()["origami"]
        eski = kap(z).alan(1080, 1920, "9x16")
        self.assertLess(eski.centerX(), 540)
        yeni = kap({**z, "yerlesim": "simetrik"}).alan(1080, 1920, "9x16")
        self.assertAlmostEqual(yeni.centerX(), 540, places=3)

    def test_muzik_kapali(self):
        import ses
        z = dil.zamanla(ornek(), {})
        z["seslendirme"] = {"satirlar": []}
        with tempfile.TemporaryDirectory() as d:
            import soundfile as sf
            import kaplama
            ses.miksle({**z, "muzik": False}, kaplama.Kaplama.MUZIK, "katla", Path(d), Path(d))
            x, _ = sf.read(str(Path(d) / "ses.wav"))
            sessiz = np.abs(x).max(axis=1) < 1e-4
            self.assertGreater(sessiz.mean(), 0.5)  # yalnız sahne efektleri: çoğu an sessiz


if __name__ == "__main__":
    unittest.main()
