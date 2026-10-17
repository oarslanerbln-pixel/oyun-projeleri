import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import metin  # noqa: E402

DEPO = Path(__file__).resolve().parents[3]
KIRK_ODA_SOZLUK = DEPO / "kirk-oda" / "tools" / "metin-denetimi" / "yasak-sozcukler.tsv"
KIRK_ODA_TABLO = DEPO / "kirk-oda" / "localization" / "oyuncu-metni.csv"


def yaz(tmp, ad, icerik):
    p = Path(tmp) / ad
    p.write_text(icerik, encoding="utf-8")
    return p


class KuralTests(unittest.TestCase):
    def setUp(self):
        self.temel = metin.sozluk_oku(metin.TEMEL)

    def hits(self, text, dil="tr", kurallar=None):
        return [k.kimlik for k, _ in metin.tara(text, dil, kurallar or self.temel)]

    def test_turkish_capitals(self):
        self.assertEqual(self.hits("ŞEHRİN EN İYİ KAHVESİ"), ["TEMEL-EN-IYI"])

    def test_whole_words_only(self):
        self.assertEqual(self.hits("iyi kahve"), [])
        self.assertEqual(self.hits("mucizevi değil"), ["TEMEL-MUCIZE"])  # desen bunu kapsıyor
        self.assertEqual(self.hits("garantici"), [])

    def test_language_scoping(self):
        self.assertEqual(self.hits("The BEST coffee", "en"), ["TEMEL-BEST"])
        self.assertEqual(self.hits("the best", "tr"), [])
        self.assertEqual(self.hits("%100 arabica", "en"), ["TEMEL-YUZDE-YUZ"])

    def test_brand_rules_ignore_dotted_i(self):
        k = metin.marka_kurallari(["kahve molası"])
        self.assertEqual(self.hits("KAHVE MOLASI verelim", "tr", k), ["MARKA-1"])
        self.assertEqual(self.hits("Kahve  molasi", "en", k), ["MARKA-1"])
        self.assertEqual(self.hits("kahveci molası", "tr", k), [])

    def test_bad_lexicon_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = yaz(tmp, "s.tsv", "X\tKIRMIZI\ttr\tx\tgerekçe\n")
            with self.assertRaises(ValueError):
                metin.sozluk_oku(p)


class TabloTests(unittest.TestCase):
    def test_read_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = yaz(tmp, "m.csv", "anahtar,tr,en,kaynak,not,izin,azami\n"
                                   "a,Kısa,Short,,,,10\n"
                                   "b,Bu satır çok uzun bir başlık,Long,,,,10\n"
                                   "c,En iyi kahve,,,,,\n"
                                   "d,En iyi kahve,Coffee,,,TEMEL-EN-IYI,\n"
                                   "a,Tekrar,Again,,,,\n")
            tablo, b = metin.tablo_oku([p], ("tr", "en"))
            self.assertTrue(any("tekrar" in x.mesaj for x in b))
            self.assertEqual(tablo.al("a", "en"), "Short")
            b = metin.denetle(tablo, metin.sozluk_oku(metin.TEMEL))
            s = [str(x) for x in b]
            self.assertTrue(any("b/tr" in x and "en çok 10" in x for x in s))
            self.assertTrue(any("c/tr" in x and "TEMEL-EN-IYI" in x for x in s))
            self.assertTrue(any("c/en" in x and "boş" in x for x in s))
            self.assertFalse(any(x.startswith("HATA d/") for x in s))  # izin

    def test_missing_language_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = yaz(tmp, "m.csv", "anahtar,tr\na,Bir\n")
            _, b = metin.tablo_oku([p], ("tr", "en"))
            self.assertTrue(metin.has_errors(b))


class KirkOdaUyumTests(unittest.TestCase):
    """Mimari faz 1 ölçütü: platform denetleyicisi Kırk Oda verisinde Kırk Oda'nınkiyle aynı sonucu verir."""

    @unittest.skipUnless(KIRK_ODA_SOZLUK.exists() and KIRK_ODA_TABLO.exists(), "Kırk Oda verisi yok")
    def test_same_findings_as_kirk_oda(self):
        sys.path.insert(0, str(KIRK_ODA_SOZLUK.parent))
        sys.dont_write_bytecode = True  # kirk-oda/ içine __pycache__ yazılmasın
        try:
            import denetle as kirk
        finally:
            sys.path.pop(0)
            sys.dont_write_bytecode = False
        eski = sorted((f[2], f[3], f[4], f[5]) for f in kirk.check_csv(str(KIRK_ODA_TABLO), kirk.load_lexicon()))
        tablo, _ = metin.tablo_oku([KIRK_ODA_TABLO], ("tr", "en"))
        kurallar = metin.sozluk_oku(KIRK_ODA_SOZLUK)
        yeni = []
        for key, row in tablo.satirlar.items():
            izin = {a.strip() for a in row.get("izin", "").split(",") if a.strip()}
            for dil in ("tr", "en"):
                yeni += [(key, dil, k.kimlik, k.seviye) for k, _ in metin.tara(row[dil], dil, kurallar, izin)]
        self.assertEqual(sorted(yeni), eski)

    @unittest.skipUnless(KIRK_ODA_SOZLUK.exists(), "Kırk Oda verisi yok")
    def test_kirk_oda_lexicon_catches_its_own_words(self):
        kurallar = metin.sozluk_oku(KIRK_ODA_SOZLUK)
        self.assertTrue(metin.tara("Odadan bir DEM aldın", "tr", kurallar))


if __name__ == "__main__":
    unittest.main()
