"""Carousel şablonu testleri: senaryo denetimi, slayt boyutları, büyütme uyarısı, kalite raporu."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import karusel  # noqa: E402

DEPO = Path(__file__).resolve().parents[4]
MARKA = DEPO / 'ornekler' / 'demli-kahve' / 'marka' / 'marka.json'

try:
    import skia
    SKIA = True
except ImportError:
    SKIA = False


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def foto(self, ad, w, h):
        p = self.kok / ad
        surf = skia.Surface(w, h)
        with surf as cv:
            cv.clear(0xFF553322)
            for i in range(0, w, 16):  # dokulu: düz degrade banding sayılmasın
                cv.drawLine(i, 0, i, h, skia.Paint(Color=0xFFDDAA66, StrokeWidth=3))
        surf.makeImageSnapshot().save(str(p), skia.kPNG)
        return ad

    def senaryo(self, slaytlar, **ek):
        s = {'kimlik': 'deneme', 'stil': 'karusel', 'marka': str(MARKA), 'slaytlar': slaytlar, **ek}
        p = self.kok / 'karusel.json'
        p.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        return str(p)


class Denetim(Tmp):
    def test_ornek_gecer(self):
        hata, _ = karusel.denetle(str(DEPO / 'ornekler' / 'demli-kahve' / 'karusel.json'))
        self.assertEqual(hata, [])

    def test_hatalar(self):
        yol = self.senaryo([
            {'tur': 'yok', 'baslik': 'x'},
            {'tur': 'foto', 'baslik': 'a' * 50, 'fazla': 1},
            {'tur': 'liste', 'baslik': 'x'},
        ], format='9:16')
        hata, uyari = karusel.denetle(yol)
        metin = '\n'.join(hata)
        for parca in ('bilinmiyor', 'tanımsız alan', 'foto slaytında gerekli', 'en çok 44', 'maddeler', 'format'):
            self.assertIn(parca, metin)
        self.assertTrue(any('kapanış' in u for u in uyari))

    def test_slayt_sayisi(self):
        hata, _ = karusel.denetle(self.senaryo([{'tur': 'kapanis', 'baslik': 'x'}]))
        self.assertTrue(any('2–10' in h for h in hata))


@unittest.skipUnless(SKIA, 'skia-python yok')
class Uretim(Tmp):
    def test_slaytlar_ve_rapor(self):
        yatay = self.foto('yatay.png', 1600, 1060)
        kucuk = self.foto('kucuk.png', 500, 400)
        yol = self.senaryo([
            {'tur': 'kapak', 'foto': yatay, 'ust': 'Etiket', 'baslik': 'Başlık burada', 'alt': 'Alt satır'},
            {'tur': 'foto', 'foto': kucuk, 'ust': 'Salon', 'baslik': 'Uzun bir başlık iki satıra bölünür',
             'metin': 'Kısa bir açıklama metni.'},
            {'tur': 'liste', 'baslik': 'Liste', 'maddeler': ['Bir', 'İki', 'Üç']},
            {'tur': 'kapanis', 'baslik': 'Son', 'satirlar': ['Adres'], 'cagri': 'Ara'},
        ])
        cikti = self.kok / 'cikti'
        r = karusel.calistir(yol, str(cikti))
        pngler = sorted(cikti.glob('deneme-4x5-*.png'))
        self.assertEqual(len(pngler), 4)
        self.assertEqual(skia.Image.open(str(pngler[0])).dimensions(), skia.ISize(1080, 1350))
        self.assertTrue((cikti / 'deneme.kalite.json').exists() and (cikti / 'deneme.kontakt.png').exists())
        self.assertTrue(any(b['kontrol'] == 'cozunurluk' and 'slayt 2' in b['mesaj'] for b in r['bulgular']))
        self.assertNotEqual(r['sonuc'], 'kaldi')

    def test_kare_kare(self):
        yol = self.senaryo([{'tur': 'kapak', 'baslik': 'A'}, {'tur': 'kapanis', 'baslik': 'B'}], format='1:1')
        self.assertEqual(karusel.main(['kare', yol, '--an', '2', '-o', str(self.kok / 'k')]), 0)
        p = list((self.kok / 'k' / 'kareler').glob('*.png'))
        self.assertEqual(len(p), 1)
        self.assertEqual(skia.Image.open(str(p[0])).dimensions(), skia.ISize(1080, 1080))


if __name__ == '__main__':
    unittest.main()
