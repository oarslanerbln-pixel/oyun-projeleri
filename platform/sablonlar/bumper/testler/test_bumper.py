"""Bumper şablonu testleri: senaryo/marka denetimi, hareket eğrisi ve küçük çözünürlükte uçtan uca üretim."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bumper  # noqa: E402

DEPO = Path(__file__).resolve().parents[4]
MARKA = DEPO / 'ornekler' / 'demli-kahve' / 'marka' / 'marka.json'
ORNEKLER = [DEPO / 'ornekler' / 'demli-kahve' / 'bumper.json', DEPO / 'ornekler' / 'demli-kahve' / 'imza.json']

try:
    import skia  # noqa: F401
    SKIA = True
except ImportError:
    SKIA = False


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def senaryo(self, **bumper_alan):
        ust = {k: bumper_alan.pop(k) for k in list(bumper_alan) if k in ('sure', 'marka')}
        s = {'kimlik': 'test', 'stil': 'bumper', 'sure': 6, 'marka': str(MARKA),
             'bumper': {'onerme': 'Sabahın on dakikası senin', 'cagri': 'ornek.com', **bumper_alan}}
        s.update(ust)
        yol = self.kok / 'bumper.json'
        yol.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        return yol


class TestDenetim(Tmp):
    def test_ornekler_temiz(self):
        for yol in ORNEKLER:
            hata, _ = bumper.denetle(yol)
            self.assertEqual(hata, [], yol)

    def test_logo_varsayilani_marka_json(self):
        s, m, _ = bumper.yukle(self.senaryo())
        self.assertEqual(bumper.alanlar(s, m)['logo'], 'DEMLİ')

    def test_uzun_onerme_hata(self):
        hata, _ = bumper.denetle(self.senaryo(onerme='Bu cümle bir bumper için fazlasıyla uzun kaldı'))
        self.assertTrue(any('onerme' in h for h in hata))

    def test_bumper_onermesiz_hata(self):
        hata, _ = bumper.denetle(self.senaryo(onerme=''))
        self.assertTrue(any('onerme' in h for h in hata))

    def test_imza_uc_saniye(self):
        hata, _ = bumper.denetle(self.senaryo(varyant='imza', onerme=''))
        self.assertTrue(any('sure' in h for h in hata))
        hata, _ = bumper.denetle(self.senaryo(varyant='imza', onerme='', sure=3))
        self.assertEqual(hata, [])

    def test_alti_saniyeyi_asamaz(self):
        hata, _ = bumper.denetle(self.senaryo(sure=7))
        self.assertTrue(any('sure' in h for h in hata))

    def test_bilinmeyen_varyant_ve_alan(self):
        self.assertTrue(bumper.denetle(self.senaryo(varyant='uzun'))[0])
        self.assertTrue(any('baslik' in h for h in bumper.denetle(self.senaryo(baslik='x'))[0]))

    def test_marka_yok(self):
        hata, _ = bumper.denetle(self.senaryo(marka=str(self.kok / 'yok.json')))
        self.assertTrue(any(h.startswith('marka') for h in hata))


class TestEgri(unittest.TestCase):
    def test_bezier_uclar_ve_monoton(self):
        f = bumper.bezier([0.2, 0, 0, 1])
        self.assertEqual(f(0), 0.0); self.assertEqual(f(1), 1.0)
        d = [f(i / 50) for i in range(51)]
        self.assertTrue(all(b >= a - 1e-9 for a, b in zip(d, d[1:])))
        self.assertAlmostEqual(bumper.bezier([0, 0, 1, 1])(0.3), 0.3, places=3)


@unittest.skipUnless(SKIA, 'skia-python yok')
class TestUretim(Tmp):
    def test_render_kucuk(self):
        cikti = self.kok / 'cikti'
        r = bumper.main(['render', str(self.senaryo(alt='Kahve')), '-o', str(cikti), '--olcek', '0.2'])
        self.assertEqual(r, 0)
        mp4 = cikti / 'test-bumper-9x16.mp4'
        self.assertTrue(mp4.exists())
        self.assertTrue((cikti / 'test-bumper-kapak.png').exists())
        sure = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(mp4)],
                                    capture_output=True, text=True).stdout)
        self.assertLessEqual(sure, bumper.AZAMI_SURE + 0.01)
        self.assertGreater(sure, 5.9)

    def test_stil_py_iletir(self):
        sys.path.insert(0, str(DEPO / 'platform' / 'sablonlar' / 'stil'))
        import stil
        cikti = self.kok / 'k'
        self.assertEqual(stil.main(['kare', str(self.senaryo()), '--stil', 'bumper', '--an', '3.5', '-o', str(cikti),
                                    '--format', '1:1']), 0)
        self.assertEqual(len(list((cikti / 'kareler').glob('*-1x1-*.png'))), 1)


if __name__ == '__main__':
    unittest.main()
