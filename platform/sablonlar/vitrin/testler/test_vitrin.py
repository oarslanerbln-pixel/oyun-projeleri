"""Ürün vitrini testleri: zamanlama, senaryo denetimi, müzik/efekt sentezi, sahne ayarı ve stil.py yönlendirmesi.
Görüntü render'ı (Chromium + three.js) burada koşmaz; `vitrin.py kare` ile elle denenir."""

import copy
import io
import json
import math
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import numpy as np

BURADA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BURADA))
sys.path.insert(0, str(BURADA.parent / 'stil'))
import vitrin  # noqa: E402

DEPO = BURADA.parents[2]
ORNEK = DEPO / 'ornekler' / 'demli-kahve' / 'vitrin.json'


def ornek():
    return json.loads(ORNEK.read_text(encoding='utf-8'))


def denetle(s, render=False):
    with tempfile.TemporaryDirectory() as d:
        hata, uyari, _ = vitrin.denetle(s, ORNEK, Path(d), render=render)
    return hata


class Zamanlama(unittest.TestCase):
    def test_anlar_vurusa_oturur_ve_sirali(self):
        z = vitrin.zamanla(ornek())
        anlar = [z['giris_son']] + [o['bas'] for o in z['ozellikler']] + [z['final']]
        for t in anlar:
            self.assertAlmostEqual(t / z['vurus'], round(t / z['vurus']), places=6)
        self.assertEqual(anlar[1:], sorted(anlar[1:]))
        self.assertEqual(z['ozellikler'][-1]['son'], z['final'])
        self.assertLess(z['final'], z['sure'] - 2.5)  # logo ve çağrıya yer kalır

    def test_ozelliksiz_bumper(self):
        s = ornek(); s['ozellikler'] = []; s['sure'] = 6
        self.assertEqual(denetle(s), [])
        self.assertEqual(vitrin.zamanla(s)['ozellikler'], [])

    def test_format_cozumu(self):
        self.assertEqual(vitrin.formatlar(None), ['9x16'])
        self.assertEqual(vitrin.formatlar('ikisi'), ['9x16', '16x9'])
        self.assertEqual(vitrin.formatlar(['4:5', '1:1']), ['4x5', '1x1'])
        with self.assertRaises(ValueError):
            vitrin.formatlar('21:9')


class Denetim(unittest.TestCase):
    def test_ornek_gecer(self):
        self.assertEqual(denetle(ornek()), [])

    def test_hatalar(self):
        durumlar = [
            (lambda s: s.update(sure=30), 'sure'),
            (lambda s: s['ozellikler'].extend(copy.deepcopy(s['ozellikler'][:2])), 'en çok 4'),
            (lambda s: s['ozellikler'][0].update(metin='Çok uzun bir özellik yazısı'), 'karakter'),
            (lambda s: s['ozellikler'][0].update(odak='ic'), 'odak'),
            (lambda s: s['urun'].update(tur='sise'), 'urun.tur'),
            (lambda s: s['urun'].update(model='yok/urun.glb'), 'urun.model'),
            (lambda s: s.update(sure=7), 'süre kısa'),
            (lambda s: s['final'].update(cagri='Bir kahve molası ver'), 'marka yasağı'),
            (lambda s: s.pop('marka'), 'marka'),
        ]
        for degistir, beklenen in durumlar:
            s = ornek(); degistir(s)
            with self.subTest(beklenen=beklenen):
                self.assertTrue(any(beklenen in h for h in denetle(s)), denetle(s))

    def test_render_seslendirme_ister(self):
        self.assertTrue(any('seslendirme yok' in h for h in denetle(ornek(), render=True)))
        s = ornek(); s.pop('seslendirme')
        self.assertEqual(denetle(s, render=True), [])


class Ses(unittest.TestCase):
    def test_muzik_ve_efekt_sonlu_ve_sesli(self):
        s = ornek(); z = vitrin.zamanla(s); n = int(vitrin.SR * z['sure'])
        for x in (vitrin.muzik(n, z), vitrin.sfx(n, z)):
            self.assertEqual(x.shape, (n, 2))
            self.assertTrue(np.isfinite(x).all())
            self.assertGreater(float(np.abs(x).max()), 0.01)
        m = vitrin.muzik(n, z)
        rms = lambda a, b: math.sqrt(float(np.mean(m[int(a * vitrin.SR):int(b * vitrin.SR)] ** 2)))
        self.assertGreater(rms(z['giris_son'] + 0.5, z['final']), rms(0.3, z['giris_son']))  # giriş sakin, sonra dolar

    def test_miks_seslendirmesiz(self):
        import soundfile as sf
        s = ornek(); s.pop('seslendirme'); z = vitrin.zamanla(s); n = int(vitrin.SR * z['sure'])
        with tempfile.TemporaryDirectory() as d:
            vitrin.miks(Path(d), vitrin.muzik(n, z), vitrin.sfx(n, z), [], Path(d), z['sure'])
            x, sr = sf.read(Path(d) / 'ses.wav')
        self.assertEqual((sr, len(x)), (vitrin.SR, n))


class SahneAyari(unittest.TestCase):
    def test_marka_renkleri_ve_zamanlar(self):
        s = ornek()
        with tempfile.TemporaryDirectory() as d:
            _, _, m = vitrin.denetle(s, ORNEK, Path(d), render=False)
        with mock.patch.object(vitrin, 'font_yolu', lambda ag: Path(f'/yok/Inter-{ag}.ttf')):  # ağ gerekmesin
            a = vitrin.ayar(s, ORNEK, m, 540, 960)
        self.assertEqual(a['renk']['ana'], m.renk['ana'])
        self.assertEqual(a['urun']['etiket'], 'DEMLİ')
        self.assertEqual([o['odak'] for o in a['ozellikler']], ['on', 'ust', 'yan'])
        self.assertEqual(a['final']['logo'], m.logo_metin)
        self.assertIn('/font/Inter-800.ttf', a['dosyalar'])

    def test_model_dosyasi_sunulur(self):
        s = ornek()
        with tempfile.TemporaryDirectory() as d:
            glb = Path(d) / 'urun.glb'; glb.write_bytes(b'glTF')
            s['urun']['model'] = str(glb)
            hata, _, m = vitrin.denetle(s, ORNEK, Path(d), render=False)
            self.assertEqual(hata, [])
            with mock.patch.object(vitrin, 'font_yolu', lambda ag: Path(f'/yok/Inter-{ag}.ttf')):
                a = vitrin.ayar(s, ORNEK, m, 540, 960)
        self.assertEqual(a['urun']['model'], '/model/urun.glb')
        self.assertEqual(a['dosyalar']['/model/urun.glb'], str(glb))


class StilYonlendirme(unittest.TestCase):
    def test_stil_py_vitrine_iletir(self):
        import stil
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()) as out:
            r = stil.main(['denetle', str(ORNEK), '--stil', 'urun-vitrini', '-o', d])
        self.assertEqual(r, 0)
        self.assertIn('urun-vitrini', out.getvalue())


if __name__ == '__main__':
    unittest.main()
