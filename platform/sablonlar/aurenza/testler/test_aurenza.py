import copy
import sys
import unittest
from pathlib import Path

KLASOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KLASOR))
import aurenza  # noqa: E402

ORNEK = aurenza.oku(KLASOR / "ornek" / "veri.de.json")


class AurenzaTest(unittest.TestCase):
    def test_ornek_gecer(self):
        self.assertEqual(aurenza.denetle(ORNEK), [])

    def test_takip_karti_zorunlu(self):
        v = copy.deepcopy(ORNEK)
        del v["son"]
        self.assertTrue(any("takip" in h for h in aurenza.denetle(v)))

    def test_guvenli_alan(self):
        v = copy.deepcopy(ORNEK)
        v["ogeler"][1]["y"] = 2100
        self.assertTrue(any("güvenli alan" in h for h in aurenza.denetle(v)))

    def test_kanca_kisa_kalir(self):
        v = copy.deepcopy(ORNEK)
        v["kancalar"]["A"]["t1"] = 5
        self.assertTrue(any("3,5" in h for h in aurenza.denetle(v)))

    def test_srt(self):
        s = aurenza.srt(ORNEK)
        self.assertTrue(s.startswith("1\n00:00:00,100 --> 00:00:02,200\n"))
        self.assertEqual(s.count(" --> "), len(ORNEK["altyazi"]))


if __name__ == "__main__":
    unittest.main()
