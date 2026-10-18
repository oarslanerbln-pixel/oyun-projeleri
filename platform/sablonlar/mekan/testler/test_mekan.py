"""Mekân şablonu testleri: senaryo denetimi, satır bölme, TV döngüsünün kesintisizliği, küçük çözünürlükte üretim."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mekan  # noqa: E402

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
        self.foto = self.kok / 'foto.png'
        if SKIA:  # gradyanlı deneme fotoğrafı (dikey, Instagram oranı)
            surf = skia.Surface(108, 137)
            with surf as cv:
                cv.drawPaint(skia.Paint(Shader=skia.GradientShader.MakeLinear([(0, 0), (108, 137)], [0xFF884422, 0xFF224488])))
                cv.drawCircle(54, 70, 30, skia.Paint(AntiAlias=True, Color=0xFFEEDDAA))
            surf.makeImageSnapshot().save(str(self.foto), skia.kPNG)
        else:
            self.foto.write_bytes(b'')

    def tearDown(self):
        self._tmp.cleanup()

    def senaryo(self, varyant='tv', sahneler=None, **ek):
        s = {'kimlik': 'test', 'stil': 'mekan', 'varyant': varyant, 'marka': str(MARKA),
             'sahneler': sahneler or [
                 {'tur': 'urun', 'sure': 6, 'foto': 'foto.png', 'ust': 'Hausgemacht', 'baslik': 'Lotus Cake', 'alt': 'Karamell & Creme'},
                 {'tur': 'bilgi', 'sure': 6, 'baslik': 'Öffnungszeiten', 'satirlar': [['So–Do', '15–01 Uhr']], 'alt': 'Berlin'},
             ], **ek}
        yol = self.kok / 'mekan.json'
        yol.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        return yol


class TestDenetim(Tmp):
    def test_gecerli(self):
        hata, _ = mekan.denetle(self.senaryo())
        self.assertEqual(hata, [])

    def test_bilinmeyen_tur_ve_alan(self):
        hata, _ = mekan.denetle(self.senaryo(sahneler=[{'tur': 'video', 'sure': 5}, {'tur': 'urun', 'sure': 5, 'foto': 'foto.png', 'fiyat': '9 €'}]))
        self.assertTrue(any('video' in h for h in hata))
        self.assertTrue(any('fiyat' in h for h in hata))

    def test_eksik_foto(self):
        hata, _ = mekan.denetle(self.senaryo(sahneler=[{'tur': 'urun', 'sure': 6, 'foto': 'yok.png'}]))
        self.assertTrue(any('yok.png' in h for h in hata))

    def test_uzun_baslik(self):
        hata, _ = mekan.denetle(self.senaryo(sahneler=[{'tur': 'urun', 'sure': 6, 'foto': 'foto.png', 'baslik': 'x' * 40}]))
        self.assertTrue(any('baslik' in h for h in hata))

    def test_bilinmeyen_tema(self):
        hata, _ = mekan.denetle(self.senaryo(tema='neon'))
        self.assertTrue(any('tema' in h for h in hata))

    def test_tv_seslendirme_yok(self):
        hata, _ = mekan.denetle(self.senaryo(seslendirme={'satirlar': [{'id': 'v0', 't': 0, 'metin': 'Hallo'}]}))
        self.assertTrue(any('seslendirme' in h for h in hata))

    def test_reel_seslendirme_dosyasi_render_icin_gerekli(self):
        yol = self.senaryo('reel', seslendirme={'satirlar': [{'id': 'v0', 't': 0.3, 'metin': 'Hallo'}]})
        self.assertEqual(mekan.denetle(yol)[0], [])
        self.assertTrue(any('v0' in h for h in mekan.denetle(yol, render=True)[0]))


@unittest.skipUnless(SKIA, 'skia-python yok')
class TestCizim(Tmp):
    def test_satirla_ayracta_boler(self):
        tf = mekan.motor.yazi_tipi(700)
        satirlar = mekan._satirla(tf, 'Lounge · Fancy Drinks · Chef Kitchen', 40, 600)
        self.assertEqual(satirlar[0], 'Lounge · Fancy Drinks')
        self.assertEqual(satirlar[-1], 'Chef Kitchen')

    def test_tv_dongu_kesintisiz(self):
        """Son karenin bir kare sonrası ilk kareyle birebir aynı: mekânda tekrar oynarken atlama görünmez."""
        import numpy as np
        g = mekan.Gorunum(self.senaryo())
        def ciz(t):
            surf = skia.Surface(192, 108)
            with surf as cv:
                mekan.kare(cv, t, 192, 108, g)
            return np.asarray(surf.makeImageSnapshot().toarray(), dtype=int)
        self.assertEqual(int(np.abs(ciz(0.0) - ciz(g.sure)).max()), 0)
        g.acik_tema = True
        g.tz, g.ty, g.tvv = g.acik, g.koyu_yazi, g.logo_renk
        self.assertEqual(int(np.abs(ciz(0.0) - ciz(g.sure)).max()), 0)
        self.assertLess(np.abs(ciz(g.sure - 1 / 30) - ciz(0.0)).mean(), 2.0)

    def test_tv_muzigi_dongu_uzunlugunda(self):
        g = mekan.Gorunum(self.senaryo())
        self.assertEqual(len(mekan.muzik_tv(g)), int(mekan.SR * g.sure))

    def test_uretim_tv(self):
        cikti = self.kok / 'cikti'
        r = subprocess.run([sys.executable, str(Path(mekan.__file__)), 'render', str(self.senaryo()), '-o', str(cikti),
                            '--olcek', '0.1'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for ad in ('test-16x9.mp4', 'test-16x9-sessiz.mp4', 'test-kapak.png'):
            self.assertTrue((cikti / ad).exists(), ad)
        akis = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0',
                               str(cikti / 'test-16x9-sessiz.mp4')], capture_output=True, text=True).stdout.split()
        self.assertEqual(akis, ['video'])


if __name__ == '__main__':
    unittest.main()
