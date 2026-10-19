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
import cevir  # noqa: E402
import dil  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
