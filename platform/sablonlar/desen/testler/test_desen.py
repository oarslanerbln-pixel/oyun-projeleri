import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import motifler  # noqa: E402
import zaman  # noqa: E402

DEPO = HERE.parents[2]
ORNEKLER = [DEPO / "ornekler" / "kucuk-aliskanliklar" / f"{s}.json" for s in zaman.STILLER]
CIZIM = all(importlib.util.find_spec(m) for m in ("numpy", "PIL"))


def yaz(h: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "desen.json"
        p.write_text(json.dumps({k: v for k, v in h.items() if not k.startswith("_")}, ensure_ascii=False), encoding="utf-8")
        return zaman.yukle(p)


class Denetim(unittest.TestCase):
    def setUp(self):
        self.ham = json.loads(ORNEKLER[0].read_text(encoding="utf-8"))

    def test_ornekler_temiz(self):
        for p in ORNEKLER:
            with self.subTest(p.name):
                self.assertEqual(zaman.denetle(zaman.yukle(p)), [])

    def test_her_stilin_ornegi_var(self):
        self.assertEqual(sorted(json.loads(p.read_text(encoding="utf-8"))["stil"] for p in ORNEKLER), sorted(zaman.STILLER))

    def test_bilinmeyen_motif_ve_stil(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["motif"] = "ejderha"; h["stil"] = "yagli-boya"
        hata = zaman.denetle(yaz(h))
        self.assertTrue(any("ejderha" in x for x in hata))
        self.assertTrue(any("yagli-boya" in x for x in hata))

    def test_uzun_baslik(self):
        h = copy.deepcopy(self.ham); h["sahneler"][0]["baslik"] = "çok uzun bir başlık metni"
        self.assertTrue(any("en çok" in x for x in zaman.denetle(yaz(h))))

    def test_kisa_sahne_ve_sure(self):
        h = copy.deepcopy(self.ham); h["sahneler"][1]["t"] = 0.5
        self.assertTrue(any("en az" in x for x in zaman.denetle(yaz(h))))
        h = copy.deepcopy(self.ham); h["sure"] = 30
        self.assertTrue(any("sure" in x for x in zaman.denetle(yaz(h))))

    def test_seslendirme_sigmali(self):
        s = zaman.yukle(ORNEKLER[0])
        self.assertEqual(zaman.denetle(s, {"v0": 2.3, "v1": 2.3, "v2": 1.3, "v3": 0.8}), [])
        self.assertTrue(any("başlamadan" in x for x in zaman.denetle(s, {"v0": 3.5})))
        self.assertTrue(any("hâlâ" in x for x in zaman.denetle(s, {"v3": 2.0})))

    def test_sahne_bulma(self):
        s = zaman.yukle(ORNEKLER[0])
        self.assertEqual(zaman.sahne(s, 0.0)[0], 0)
        self.assertEqual(zaman.sahne(s, 6.5)[:2], (2, 0.5))
        self.assertEqual(zaman.sahne(s, 9.99)[0], 3)

    def test_stil_py_iletir(self):
        """stil.py --stil linol desen şablonuna iletilir (aynı içerik başka stilde)."""
        sys.path.insert(0, str(HERE.parent / "stil"))
        import stil
        self.assertEqual(stil.main(["denetle", str(ORNEKLER[2]), "--stil", "linol"]), 0)
        self.assertEqual(stil.main(["denetle", str(ORNEKLER[3])]), 0)

    def test_motifler_karede(self):
        for ad in motifler.MOTIFLER:
            for p, _ in motifler.parcalar(ad):
                with self.subTest(ad):
                    self.assertGreaterEqual(len(p), 3)
                    self.assertTrue(all(-1.0 <= x <= 1.0 and -1.0 <= y <= 1.0 for x, y in p))


@unittest.skipUnless(CIZIM, "numpy/Pillow yok")
class Cizim(unittest.TestCase):
    def test_her_stil_kare_uretir(self):
        import cizim
        for p in ORNEKLER:
            s = zaman.yukle(p)
            st = cizim.stil_nesnesi(s)
            for t in (0.4, 3.6, 9.8):
                with self.subTest(s["stil"], t=t):
                    a = st.kare(t, "1x1", 216, 216)
                    self.assertEqual(a.shape, (216, 216, 3))
                    self.assertGreater(float(a.std()), 3.0)  # boş kare değil

    def test_yazilar_guvenli_alanda(self):
        """Her formatta başlık ve alt satır ekrana tam sığar; 9:16'da üst %10 / alt %22 boş kalır."""
        import cizim
        s = zaman.yukle(ORNEKLER[1])  # linol: yerleşim bütün stillerde ortak, hazırlığı ucuz
        s["sahneler"][3]["alt"] = "en uzun alt satır otuz iki harf"
        for fmt, (W, H) in zaman.FORMATLAR.items():
            st = cizim.Linol(s)
            st.hazirla(fmt, W, H)
            ust, alt = zaman.GUVENLI[fmt]
            for sh in st.on[fmt]["sahneler"]:
                for k in (sh["baslik"], sh["alt"]):
                    if k is None:
                        continue
                    ys, xs = (k.a > 0.1).nonzero()
                    with self.subTest(fmt):
                        self.assertGreaterEqual(k.x0 + xs.min(), 0.03 * W)
                        self.assertLessEqual(k.x0 + xs.max(), 0.97 * W)
                        self.assertGreaterEqual(k.y0 + ys.min(), ust * H)
                        self.assertLessEqual(k.y0 + ys.max(), alt * H)


if __name__ == "__main__":
    unittest.main()
