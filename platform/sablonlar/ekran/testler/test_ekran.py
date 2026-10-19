"""Ekran stilleri testleri: senaryo denetimi, tabela takvimi, üç stilin karesi ve sesi."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import zaman  # noqa: E402

DEPO = Path(__file__).resolve().parents[4]
ORNEK = DEPO / "ornekler" / "kucuk-aliskanliklar"

try:
    import cizim  # noqa: F401
    cizim.font_yolu("bold")
    CIZIM = True
except Exception:  # Pillow ya da Inter yoksa çizim testleri atlanır
    CIZIM = False


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def senaryo(self, stil="kalkis-tabelasi", **ek):
        s = {"kimlik": "deneme", "stil": stil, "sure": 4, "fps": 24,
             "sahneler": [{"bas": 0, "metin": "Her gün *%1*", "alt": "deneme"}, {"bas": 2, "metin": "Bugün başla"}], **ek}
        p = self.kok / f"{stil}.json"
        p.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(Tmp):
    def test_ornekler_gecer(self):
        for ad in ("kalkis-tabelasi", "vhs", "akis-alani"):
            self.assertEqual(zaman.denetle(zaman.yukle(ORNEK / f"{ad}.json")), [], ad)

    def test_hatalar(self):
        s = self.senaryo(sure=40, palet={"yok": "#000000", "harf": "kirmizi"})
        s["sahneler"][1]["bas"] = 0.5
        s["sahneler"][0]["metin"] = "Çokçokçokuzunkelime ✈"
        metin = "\n".join(zaman.denetle(s))
        for parca in ("sure", "bilinmeyen rol", "#RRGGBB", "en az 1.5", "tabelada yok"):
            self.assertIn(parca, metin)

    def test_kelime_tabelaya_sigmali(self):
        s = self.senaryo()
        s["sahneler"][0]["metin"] = "Sürdürülebilirlik"
        self.assertTrue(any("hücresine sığmıyor" in h for h in zaman.denetle(s)))

    def test_vurgu_obegi_bolunmez(self):
        self.assertEqual(zaman.parcala("Bir yıl *37 kat*")[0], [("Bir", False), ("yıl", False), ("37 kat", True)])


@unittest.skipUnless(CIZIM, "Pillow ya da Inter yok")
class Cizim(Tmp):
    def test_tabela_takvimi_hedefe_varir(self):
        import tabela
        s = self.senaryo()
        tk = tabela.takvim(s, "9x16")
        son = {h: o[-1][1][-1] for h, o in tk.items()}
        ana = "".join(son.get(("ana", r, c), " ") for r in range(6) for c in range(10))
        self.assertIn("BUGÜN", ana)
        self.assertTrue(all(len(x[1]) - 1 <= tabela.EN_COK_DONUS for o in tk.values() for x in o))

    def test_uc_stil_kare(self):
        import cizim
        for st in zaman.STILLER:
            s = self.senaryo(st)
            c = cizim.cizici(s, 216, 384)
            a = c.kare(0.0); b = c.kare(2.5)
            self.assertEqual(a.shape, (384, 216, 3), st)
            self.assertGreater(np.abs(a.astype(int) - b.astype(int)).mean(), 1, st)  # sahne değişince görüntü değişir

    def test_ses(self):
        import sentez
        for st in zaman.STILLER:
            s = self.senaryo(st)
            n = int(sentez.SR * s["sure"])
            for x in (sentez.muzik(s, n), sentez.sfx(s, n)):
                self.assertEqual(x.shape, (n, 2), st)
                self.assertTrue(np.isfinite(x).all() and np.abs(x).max() > 0, st)


if __name__ == "__main__":
    unittest.main()
