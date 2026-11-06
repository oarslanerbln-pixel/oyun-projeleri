import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "sinema"))
sys.path.insert(0, str(KOK.parents[1] / "ortak"))


class SinemaSahne(unittest.TestCase):
    def test_ornekler_cozulur(self):
        import json
        import sinema
        for yol in sorted((KOK.parents[2] / "ornekler" / "dunya-sinema").glob("*.json")):
            s = json.loads(yol.read_text(encoding="utf-8"))
            for fmt in ("16x9", "9x16"):
                c = sinema.sahne_coz(s, fmt)
                self.assertGreaterEqual(len(c["kamera"]), 2, yol.name)
                self.assertEqual(len(c["odak"]), 4)
                for k in c["kamera"]:
                    self.assertEqual(len(k["hedef"]), 2)
                    self.assertIsInstance(k["irtifa"], float)
                if fmt == "9x16":
                    self.assertTrue(all(k["kayX"] == 0 for k in c["kamera"]))

    def test_konum(self):
        import sinema
        lo, la, et = sinema._konum("Türkiye")
        self.assertTrue(25 < lo < 45 and 35 < la < 43)
        self.assertEqual(sinema._konum([10, 20])[:2], (10.0, 20.0))


if __name__ == "__main__":
    unittest.main()


class GrafikStilleri(unittest.TestCase):
    def test_her_stil_markada_ve_grafik_js_te(self):
        import json
        import sinema
        mj = json.loads((KOK / "sinema" / "marka.json").read_text())
        js = (KOK / "sinema" / "grafik.js").read_text()
        for ad in sinema.GRAFIKLER:
            self.assertIn(ad, mj["grafikler"], ad)
            if ad != "belgesel":
                self.assertIn(f"\n    {ad}: {{", js, ad)
            m = sinema._birlestir(mj["varsayilan"], mj["grafikler"][ad])
            for rol in ("ana", "karsi", "dost", "notr"):
                self.assertTrue(m["roller"][rol]["dolgu"].startswith("#"))
            for k, y in m["yazi"].items():  # her yazı ailesi gömülü olmalı
                self.assertIn(y["aile"], sinema.AILE.values(), f"{ad}.{k}")

    def test_birlestir_derin(self):
        import sinema
        m = sinema._birlestir({"a": {"x": 1, "y": 2}, "b": 1}, {"a": {"y": 3}})
        self.assertEqual(m, {"a": {"x": 1, "y": 3}, "b": 1})


class SesIzi(unittest.TestCase):
    """ses.py: olaylar karedeki zamanlamayla aynı, iz tıslamaz, 50 Hz altı uğultu yok."""

    def _sahne(self):
        import json
        s = json.loads((KOK.parents[2] / "ornekler" / "dunya-sinema" / "barbarossa-1941.json").read_text(encoding="utf-8"))
        s["grafik"] = "firca"
        return s

    def test_olaylar_grafikle_esli(self):
        import ses
        s = self._sahne()
        o = ses.olaylar(s)
        turler = {e["tur"] for e in o}
        for t in ("darbe", "sicrama", "damga", "damla", "baslik", "tahta", "vurgu"):
            self.assertIn(t, turler)
        ok = next(k for k in s["katmanlar"] if k["tip"] == "ok")
        d = ok["cizim"] * ses.STIL["firca"][0]
        self.assertTrue(any(e["tur"] == "sicrama" and abs(e["t"] - (ok["t"][0] + 0.29 * d)) < 1e-6 for e in o))
        self.assertEqual(ses.ruh(s), "gergin")
        self.assertEqual(o, sorted(o, key=lambda e: e["t"]))

    def test_iz_tislamaz(self):
        import numpy as np
        import ses
        import sfx
        s = self._sahne()
        s["sure"] = 10
        o = [e for e in ses.olaylar(s) if e["t"] < 9]
        x = ses.muzik(s, 10, "gergin", o) * 0.5 + ses.efektler(s, 10, "gergin", o) * 0.9
        self.assertLess(sfx.gurultu_analizi(x)["en_uzun_sn"], 1.0)
        m = x.mean(axis=1)
        P = np.abs(np.fft.rfft(m)) ** 2
        f = np.fft.rfftfreq(len(m), 1 / ses.SR)
        self.assertLess(10 * np.log10(P[f < 50].sum() / P.sum()), -20)  # taiko ve bas kökü 73 Hz'e inmez
