"""Stil şablonu testleri: senaryo denetimi ve stillerin küçük çözünürlükte uçtan uca üretimi."""

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motor  # noqa: E402
import stil  # noqa: E402

SURELER = {'v0': 2.0, 'v1': 2.0, 'v2': 1.2, 'v3': 0.8}
DEPO = Path(__file__).resolve().parents[4]
ORNEK = DEPO / 'ornekler' / 'kucuk-aliskanliklar' / 'senaryo.json'


def senaryo_kur(kok, sureler=SURELER, **degisiklik):
    """Kinetik biçiminde senaryo + cikti/seslendirme altına sinüs 'seslendirme' yazar; senaryo yolunu döner."""
    import soundfile as sf
    sd = kok / 'cikti' / 'seslendirme'; sd.mkdir(parents=True, exist_ok=True)
    kayit = []
    for i, (vid, d) in enumerate(sureler.items()):
        t = np.arange(int(d * motor.SR)) / motor.SR
        sf.write(sd / f'{vid}.wav', (0.3 * np.sin(2 * np.pi * (180 + 40 * i) * t)).astype(np.float32), motor.SR)
        kayit.append({'id': vid, 'metin': 'bir iki üç', 'sure': d})
    (sd / 'seslendirme.json').write_text(json.dumps({'saglayici': 'test', 'satirlar': kayit}), encoding='utf-8')
    s = {'kimlik': 'test', 'sure': 10,
         'seslendirme': {'satirlar': [{'id': v, 't': b, 'metin': 'bir iki üç'} for v, (b, _) in zip(sureler, motor.VURUSLAR)]},
         'sahneler': [{'tur': 'kelimeler', 'bas': 0, 'kelimeler': [{'metin': 'HER', 't': 0.3}, {'metin': 'HAFTA', 't': 0.6}]},
                      {'tur': 'buyuk-sayi', 'bas': 1.2, 'sayi': '%5'},
                      {'tur': 'egri', 'bas': 3.0, 'oran': 0.05, 'gun': 52, 'alt': 'bir yıl sonra'},
                      {'tur': 'karsitlik', 'bas': 6.0, 'kucuk': 'TEK SAYFA', 'buyuk': 'KOCA KİTAP'},
                      {'tur': 'kapanis', 'bas': 8.0, 'satirlar': [{'metin': 'ŞİMDİ'}, {'metin': 'BAŞLA.'}]}]}
    s.update(degisiklik)
    yol = kok / 'senaryo.json'
    yol.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
    return yol


def oku(yol):
    return json.loads(Path(yol).read_text(encoding='utf-8'))


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class TestDenetim(Tmp):
    def _denetle(self, yol, stil_ad='kagit-kesik', render=True):
        return motor.denetle(oku(yol), stil_ad, str(Path(yol).parent / 'cikti' / 'seslendirme'), render)

    def test_kinetik_sahnelerinden_metin(self):
        m = motor.metin_cikar(oku(senaryo_kur(self.kok)), 'izometrik')
        self.assertEqual((m['kanca'], m['kanca_alt'], m['sayi'], m['sayac']), ('%5', 'her hafta', '12x', 52))
        self.assertEqual((m['kucuk'], m['buyuk'], m['cagri']), ('tek sayfa', 'koca kitap', 'Şimdi başla.'))

    def test_stile_ozel_metin_ustune_yazar(self):
        yol = senaryo_kur(self.kok, stiller={'izometrik': {'metin': {'cagri': 'Hadi!'}}})
        self.assertEqual(motor.metin_cikar(oku(yol), 'izometrik')['cagri'], 'Hadi!')
        self.assertEqual(motor.metin_cikar(oku(yol), 'kagit-kesik')['cagri'], 'Şimdi başla.')

    def test_ornek_senaryo_iki_stilde_temiz(self):
        """Kinetik örneği (seslendirmesiz) bu iki stilde de geçerli: aynı içerik, stil değişir."""
        for ad in motor.STILLER:
            self.assertEqual(motor.denetle(oku(ORNEK), ad, str(self.kok / 'yok'), render=False), ([], []), ad)

    def test_yuvaya_sigmayan_satir_hata(self):
        hata, _ = self._denetle(senaryo_kur(self.kok, sureler=dict(SURELER, v2=3.0)))
        self.assertTrue(any('v2: 3.00 sn' in h for h in hata), hata)

    def test_vurus_ani_kaymasi_ve_sure(self):
        s = oku(senaryo_kur(self.kok)); s['seslendirme']['satirlar'][1]['t'] = 3.6; s['sure'] = 12
        hata, _ = motor.denetle(s, 'izometrik', str(self.kok / 'cikti' / 'seslendirme'))
        self.assertTrue(any('v1: t=3.6' in h for h in hata), hata)
        self.assertTrue(any(h.startswith('sure:') for h in hata), hata)

    def test_metin_siniri_ve_tanimsiz_yuva(self):
        yol = senaryo_kur(self.kok, stiller={'kagit-kesik': {'metin': {'cagri': 'x' * 30, 'baslik': 'a'}}})
        hata, _ = self._denetle(yol)
        for parca in ('cagri:', 'baslik'):
            self.assertTrue(any(parca in h for h in hata), (parca, hata))

    def test_seslendirme_yoksa_yol_gosterir(self):
        yol = senaryo_kur(self.kok)
        hata, _ = motor.denetle(oku(yol), 'izometrik', str(self.kok / 'yok'))
        self.assertTrue(any('seslendir' in h for h in hata), hata)

    def test_cli(self):
        yol = str(senaryo_kur(self.kok))
        self.assertEqual(stil.main(['denetle', yol, '--stil', 'izometrik']), 0)
        self.assertEqual(stil.main(['denetle', yol]), 1)  # stil yok
        self.assertEqual(stil.main(['denetle', str(senaryo_kur(self.kok, stil='kagit-kesik', sure=12))]), 1)

    def test_tr_harfler(self):
        self.assertEqual(motor.tr_buyuk('büyük fikir ılık'), 'BÜYÜK FİKİR ILIK')
        self.assertEqual(motor.cumle('BUGÜN BAŞLA İLK'), 'Bugün başla ilk')


class TestUretim(Tmp):
    def _sure(self, yol):
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height', '-show_entries',
                            'format=duration', '-of', 'json', str(yol)], capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def test_iki_stil_uctan_uca(self):
        yol = senaryo_kur(self.kok)
        for ad in motor.STILLER:
            with self.subTest(stil=ad):
                cikti = self.kok / 'cikti'
                self.assertEqual(stil.main(['render', str(yol), '-o', str(cikti), '--stil', ad, '--format', 'ikisi',
                                            '--olcek', '0.1']), 0)
                for b, (W, H) in (('9x16', (108, 192)), ('16x9', (192, 108))):
                    bilgi = self._sure(cikti / f'test-{ad}-{b}.mp4')
                    self.assertAlmostEqual(float(bilgi['format']['duration']), motor.SURE, delta=0.1)
                    v = [s for s in bilgi['streams'] if s['codec_type'] == 'video'][0]
                    self.assertEqual((v['width'], v['height']), (W, H))
                    self.assertTrue(any(s['codec_type'] == 'audio' for s in bilgi['streams']))
                self.assertTrue((cikti / f'test-{ad}-kapak.png').exists())
                self.assertFalse((cikti / 'is' / 'ses.wav').exists())

    def test_uret_tek_adim_mevcut_seslendirmeyle(self):
        yol = senaryo_kur(self.kok)
        self.assertEqual(stil.main(['uret', str(yol), '--stil', 'izometrik', '--format', '1x1', '--olcek', '0.1']), 0)
        self.assertTrue((self.kok / 'cikti' / 'test-izometrik-1x1.mp4').exists())

    def test_format_secimi(self):
        """Varsayılan yalnız 9:16; senaryodaki "format" alanı ya da --format ikisini birden ister."""
        yol = senaryo_kur(self.kok, format='16:9')
        self.assertEqual(stil.main(['uret', str(yol), '--stil', 'kagit-kesik', '--olcek', '0.1']), 0)
        mp4 = sorted(p.name for p in (self.kok / 'cikti').glob('*.mp4'))
        self.assertEqual(mp4, ['test-kagit-kesik-16x9.mp4'])
        self.assertEqual(stil.formatlar(None), ['9x16'])
        self.assertEqual(stil.formatlar(['9:16', 'ikisi']), ['9x16', '16x9'])
        self.assertEqual(stil.main(['render', str(yol), '--stil', 'izometrik', '--format', '3:2']), 1)

    def test_kinetige_cozulen_format_iletilir(self):
        yol = str(senaryo_kur(self.kok, format='ikisi'))
        gelen = []
        eski, stil._kinetik = stil._kinetik, lambda argv: gelen.append(argv) or 0
        try:
            stil.main(['render', yol, '--stil', 'kinetik', '--olcek', '0.5'])
            stil.main(['render', yol, '--stil', 'kinetik', '--format', '16:9', '-o', 'x'])
            stil.main(['kare', yol, '--stil', 'kinetik', '--an', '1', '--format', '16:9'])
        finally:
            stil._kinetik = eski
        self.assertEqual(gelen, [['render', yol, '--format', '9x16', '16x9'],
                                 ['render', yol, '-o', 'x', '--format', '16x9'],
                                 ['kare', yol, '--an', '1', '--format', '16x9']])

    def test_hamur_kart_ayari(self):
        """stiller.hamur altındaki metin dışı alanlar STIL_AYAR'a gelir; verilmeyen kart alanları varsayılan kalır."""
        yol = senaryo_kur(self.kok, stiller={'hamur': {'kart': {'bos': 6}, 'marka': 'KÖŞE FIRIN', 'metin': {'sayi': '2x'}}})
        motor.kur(oku(yol), 'hamur', str(self.kok / 'cikti' / 'seslendirme'))
        hamur = importlib.import_module('hamur')
        self.assertEqual(hamur.kart_ayar(), {'bos': 6, 'toplam': 10, 'hazir': 2})
        self.assertEqual(motor.STIL_AYAR['marka'], 'KÖŞE FIRIN')
        self.assertNotIn('metin', motor.STIL_AYAR)
        self.assertEqual(motor.METIN['sayi'], '2x')
        motor.kur(oku(senaryo_kur(self.kok)), 'izometrik', str(self.kok / 'cikti' / 'seslendirme'))
        self.assertEqual(motor.STIL_AYAR, {})

    def test_kare_saf_fonksiyon(self):
        """Aynı t iki kez aynı kareyi verir (stop-motion titremesi de t'ye bağlı)."""
        import skia
        yol = senaryo_kur(self.kok)
        for ad in motor.STILLER:
            motor.kur(oku(yol), ad, str(self.kok / 'cikti' / 'seslendirme'))
            m = importlib.import_module(motor.STILLER[ad])
            kareler = []
            for _ in range(2):
                surf = skia.Surface(108, 192)
                with surf as cv:
                    m.kare(cv, 4.7, 108, 192)
                kareler.append(surf.makeImageSnapshot().tobytes())
            self.assertEqual(kareler[0], kareler[1], ad)


if __name__ == '__main__':
    unittest.main()
