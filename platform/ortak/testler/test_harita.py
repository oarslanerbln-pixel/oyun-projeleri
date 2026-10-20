"""Harita modülü: yer adı arama (Türkçe/Almanca adlar, aynı adlı şehirler), mesafe, kamera, rota yolu."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harita  # noqa: E402


class Harita(unittest.TestCase):
    def test_turkce_almanca_adlar(self):
        self.assertAlmostEqual(harita.sehir("İstanbul")[0], 29.0, delta=0.3)
        self.assertEqual(harita.sehir("München"), harita.sehir("Münih"))
        self.assertEqual(harita.ulke("İspanya")["iso"], "ESP")
        self.assertEqual(harita.ulke("Deutschland")["iso"], "DEU")

    def test_ayni_adli_sehir_rotaya_gore_secilir(self):
        dd = harita.duraklar(["Málaga", "Sevilla", "Kurtuba", "Granada"])
        for d in dd:
            self.assertTrue(-7 < d["konum"][0] < -3 and 36 < d["konum"][1] < 39, d)
        self.assertAlmostEqual(harita.mesafe([d["konum"] for d in dd]), 408, delta=15)

    def test_konum_ve_hata(self):
        d = harita.durak({"ad": "Válor", "konum": [-3.085, 36.995]})
        self.assertEqual(d["konum"], (-3.085, 36.995))
        with self.assertRaises(harita.HaritaHatasi) as e:
            harita.sehir("Yokboyleyerxyz")
        self.assertIn("konum", str(e.exception))

    def test_kamera_duraklari_sigdirir(self):
        dd = harita.duraklar(["Berlin", "Wien", "İstanbul"])
        kam = harita.Kamera.sigdir([d["konum"] for d in dd], 0, 0, 1000, 1600)
        for d in dd:
            x, y = kam.xy(*d["konum"])
            self.assertTrue(0 < x < 1000 and 0 < y < 1600)
        yol, oran = harita.rota(kam, [d["konum"] for d in dd])
        self.assertEqual((oran[0], oran[-1]), (0.0, 1.0))
        self.assertGreater(len(harita.kara(kam, kam.kutu(0, 0, 1000, 1600))), 10)


if __name__ == "__main__":
    unittest.main()
