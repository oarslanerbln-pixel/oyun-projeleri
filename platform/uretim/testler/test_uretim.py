import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sablonlar" / "animasyon" / "testler"))
import yardim  # noqa: E402
from yardim import BASLIK  # noqa: E402

import saglayici  # noqa: E402
import uretim  # noqa: E402

DEPO = HERE.parents[1]
ORNEK = DEPO / "ornekler" / "demli-kahve" / "proje.json"
BASLIK_K = BASLIK.rstrip("\n") + ",anahtar_kare\n"
SAG = {
    "kuru": {"tur": "kuru", "usd_sn": 0, "ticari": False, "kare_gerekli": False},
    "api": {"tur": "fal", "model": "x/y", "anahtar": "TEST_KEY", "usd_sn": 0.1, "sureler": [5, 10],
            "ticari": True, "kare_gerekli": True},
    "ucretsiz": {"tur": "fal", "model": "x/z", "usd_sn": 0, "ticari": False},
    "taslak": {"tur": "henuz-yok", "usd_sn": 0.05, "sureler": [4, 6, 8], "ticari": True},
}


def satir(cid, sure, sinif="C", durum="uretim", kare=""):
    return f"{cid},{sure},,,ürün,yavaş itme,kesme,0.5,0.5,{sinif},{durum},,,,,{kare}\n"


def mesajlar(b, seviye=None):
    return [str(x) for x in b if seviye is None or x.seviye == seviye]


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)
        self._patch = mock.patch.object(saglayici, "yukle", return_value=SAG)
        self._patch.start()
        (self.kok / "kare.png").write_bytes(b"\x89PNG kare")

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def kur(self, rows, uretim_ayar=None):
        over = {"uretim": {"saglayici": "api", "butce_usd": 5, **(uretim_ayar or {})}}
        return yardim.proje_kur(self.kok, cekimler=BASLIK_K + "".join(rows), proje_over=over)

    def plan(self, rows, secilen=None, **ayar):
        return uretim.plan_kur(self.kur(rows, ayar), secilen, kok=self.kok)


class PlanTests(Tmp):
    def test_only_class_c_and_billed_duration(self):
        p, b = self.plan([satir("C01", 2, sinif="B"), satir("C02", 3, kare="kare.png"),
                          satir("C03", 6, kare="kare.png")])
        self.assertEqual(mesajlar(b, uretim.HATA), [])
        self.assertEqual([(i["cekim"], i["faturali_sn"], i["maliyet_usd"]) for i in p.isler],
                         [("C02", 5.0, 0.5), ("C03", 10.0, 1.0)])
        self.assertEqual(p.tahmini, 1.5)

    def test_not_approved_at_v1_or_locked_costs_nothing(self):
        p, b = self.plan([satir("C01", 2, durum="animatik"), satir("C02", 2, durum="kilit")])
        self.assertEqual([i["durum"] for i in p.isler], [uretim.BEKLIYOR, uretim.KILITLI])
        self.assertEqual(p.tahmini, 0)
        self.assertEqual(mesajlar(b, uretim.HATA), [])  # kare yalnız üretilecek çekimde aranır

    def test_budget_breaker_counts_previous_spend(self):
        p, b = self.plan([satir("C01", 3, kare="kare.png")], butce_usd=0.4)
        self.assertTrue(any("bütçe" in m for m in mesajlar(b, uretim.HATA)))
        kayit = self.kok / "p" / "yz-kaydi.csv"
        uretim.kayit_ekle(kayit, {"model": "api", "maliyet_usd": "4.8", "istek_ozeti": "eski", "dosya": "x"})
        p, b = self.plan([satir("C01", 3, kare="kare.png")])
        self.assertEqual(p.harcanan, 4.8)
        self.assertTrue(any("4.80 $ + bu plan 0.50 $ > bütçe 5.00 $" in m for m in mesajlar(b, uretim.HATA)))

    def test_license_gate(self):
        _, b = self.plan([satir("C01", 3)], secilen="ucretsiz")
        self.assertTrue(any("ticari kullanıma izin vermiyor" in m for m in mesajlar(b, uretim.HATA)))
        _, b = self.plan([satir("C01", 3)], secilen="ucretsiz", ticari=False)
        self.assertEqual(mesajlar(b, uretim.HATA), [])

    def test_keyframe_required_and_must_exist(self):
        _, b = self.plan([satir("C01", 3), satir("C02", 3, kare="yok.png")])
        hatalar = " ".join(mesajlar(b, uretim.HATA))
        self.assertIn("C01: 'api' görüntüden video üretir", hatalar)
        self.assertIn("C02: anahtar kare yok: yok.png", hatalar)

    def test_shot_longer_than_provider_max(self):
        _, b = self.plan([satir("C01", 12, kare="kare.png")])
        self.assertTrue(any("en çok 10 sn üretir; çekimi bölün" in m for m in mesajlar(b, uretim.HATA)))

    def test_unknown_provider_and_no_adapter(self):
        _, b = self.plan([satir("C01", 3)], secilen="yok")
        self.assertTrue(any("bilinmiyor" in m for m in mesajlar(b, uretim.HATA)))
        p, b = self.plan([satir("C01", 3)], secilen="taslak")
        self.assertEqual(p.isler[0]["faturali_sn"], 4.0)
        self.assertTrue(any("bağdaştırıcı yok" in m for m in mesajlar(b, uretim.UYARI)))
        self.assertTrue(any("bağdaştırıcı yok" in str(x) for x in uretim.calistir(p)))

    def test_invalid_project_stops_before_planning(self):
        path = yardim.proje_kur(self.kok, cekimler=BASLIK + "C01,0,,,,,,,,C,uretim,,,,\n")
        p, b = uretim.plan_kur(path, kok=self.kok)
        self.assertIsNone(p)
        self.assertTrue(mesajlar(b, uretim.HATA))

    def test_bad_settings(self):
        _, b = self.plan([satir("C01", 3)], butce_usd="çok", azami_deneme=0)
        self.assertIn("HATA proje.uretim.butce_usd: türü yanlış", mesajlar(b))


class CalistirTests(Tmp):
    def test_dry_run_records_and_caches(self):
        rows = [satir("C01", 3)]
        p, _ = self.plan(rows, secilen="kuru")
        self.assertEqual(mesajlar(uretim.calistir(p), uretim.HATA), [])
        kayit = uretim.kayit_oku(self.kok / "p" / "yz-kaydi.csv")
        self.assertEqual([(r["model"], r["lisans"], r["kullanildigi_yer"]) for r in kayit], [("kuru", "kuru", "k/C01")])
        self.assertTrue((self.kok / kayit[0]["dosya"]).is_file())
        self.assertEqual(len(kayit[0]["kaynak_ozeti"]), 64)
        p, _ = self.plan(rows, secilen="kuru")
        self.assertEqual(p.isler[0]["durum"], uretim.ONBELLEK)
        p, _ = self.plan([satir("C01", 4)], secilen="kuru")  # süre değişti: yeni istek
        self.assertEqual(p.isler[0]["durum"], uretim.URETILECEK)

    def test_record_without_local_file_is_not_paid_again(self):
        rows = [satir("C01", 3, kare="kare.png")]
        p, _ = self.plan(rows)
        uretim.kayit_ekle(self.kok / "p" / "yz-kaydi.csv",
                          {"model": "api", "istek_ozeti": p.isler[0]["istek_ozeti"], "dosya": "baska/makine.mp4"})
        p, b = self.plan(rows)
        self.assertEqual((p.isler[0]["durum"], p.tahmini), (uretim.KAYITTA, 0))
        p, _ = uretim.plan_kur(self.kok / "p" / "proje.json", kok=self.kok, yeniden=True)
        self.assertEqual(p.isler[0]["durum"], uretim.URETILECEK)

    def fal(self, durumlar=("IN_QUEUE", "COMPLETED"), fail=False):
        calls = []
        seq = iter(durumlar)

        def ag(method, url, body, headers):
            calls.append((method, url, body, headers))
            if fail:
                raise OSError("bağlantı yok")
            if method == "POST":
                return json.dumps({"status_url": "S", "response_url": "R"}).encode()
            if url == "S":
                return json.dumps({"status": next(seq)}).encode()
            if url == "R":
                return json.dumps({"video": {"url": "V"}}).encode()
            return b"MP4"
        return ag, calls

    def test_fal_adapter(self):
        p, _ = self.plan([satir("C01", 3, kare="kare.png")])
        ag, calls = self.fal()
        with mock.patch.dict(os.environ, {"TEST_KEY": "k"}), mock.patch.object(saglayici, "BEKLEME_SN", 0):
            b = uretim.calistir(p, ag)
        self.assertEqual(mesajlar(b), [])
        method, url, body, headers = calls[0]
        self.assertEqual((method, url, body["duration"], headers["Authorization"]),
                         ("POST", saglayici.FAL_KUYRUK + "x/y", "5", "Key k"))
        self.assertTrue(body["image_url"].startswith("data:image/png;base64,"))
        self.assertNotIn("seed", body)
        kayit = uretim.kayit_oku(self.kok / "p" / "yz-kaydi.csv")
        self.assertEqual((kayit[0]["lisans"], kayit[0]["maliyet_usd"]), ("ticari", "0.5"))
        self.assertEqual((self.kok / kayit[0]["dosya"]).read_bytes(), b"MP4")

    def test_failed_attempts_are_retried_and_not_recorded(self):
        p, _ = self.plan([satir("C01", 3, kare="kare.png")], azami_deneme=3)
        ag, calls = self.fal(fail=True)
        with mock.patch.dict(os.environ, {"TEST_KEY": "k"}):
            b = uretim.calistir(p, ag)
        self.assertEqual(len(calls), 3)
        self.assertTrue(any("3 denemede üretilemedi" in m for m in mesajlar(b, uretim.HATA)))
        self.assertFalse((self.kok / "p" / "yz-kaydi.csv").exists())

    def test_missing_key(self):
        p, _ = self.plan([satir("C01", 3, kare="kare.png")], azami_deneme=1)
        with mock.patch.dict(os.environ, {}, clear=True):
            b = uretim.calistir(p, self.fal()[0])
        self.assertTrue(any("TEST_KEY ortam değişkeni yok" in m for m in mesajlar(b)))

    def test_budget_stops_mid_run(self):
        rows = [satir("C01", 3, kare="kare.png"), satir("C02", 3, kare="kare.png")]
        p, _ = self.plan(rows, butce_usd=1)
        p.ayar["butce_usd"] = 0.6  # plan sonrası bütçe düştü
        with mock.patch.dict(os.environ, {"TEST_KEY": "k"}), mock.patch.object(saglayici, "BEKLEME_SN", 0):
            b = uretim.calistir(p, self.fal(("COMPLETED",))[0])
        self.assertTrue(any("C02: bütçe doldu" in m for m in mesajlar(b, uretim.HATA)))
        self.assertEqual(len(uretim.kayit_oku(self.kok / "p" / "yz-kaydi.csv")), 1)


class DenetleTests(Tmp):
    def denetle(self, rows, kayit=()):
        path = self.kur(rows)
        for r in kayit:
            uretim.kayit_ekle(self.kok / "p" / "yz-kaydi.csv", r)
        return mesajlar(uretim.denetle(path, kok=self.kok), uretim.HATA)

    def test_approved_shot_needs_commercial_record(self):
        self.assertEqual(self.denetle([satir("C01", 3, durum="onay")]),
                         ["HATA k:C01: durum onay ama yz-kaydi'de satırı yok"])
        kuru = {"model": "kuru", "lisans": "kuru", "kullanildigi_yer": "k/C01"}
        self.assertIn("ticari teslime giremez", self.denetle([satir("C01", 3, durum="kilit")], [kuru])[0])
        api = {"model": "api", "lisans": "ticari", "kullanildigi_yer": "k/C01"}
        self.assertEqual(self.denetle([satir("C01", 3, durum="kilit")], [kuru, api]), [])

    def test_tampered_or_unknown_rows(self):
        hatalar = self.denetle([satir("C01", 3)], [{"model": "ucretsiz", "lisans": "ticari"}, {"model": "?"}])
        self.assertEqual(len(hatalar), 2)
        self.assertIn("'ticari-degil'", hatalar[0])


class OrnekTests(unittest.TestCase):
    def test_example_plan_and_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(uretim.main(["plan", str(ORNEK)]), 0)
            self.assertEqual(uretim.main(["denetle", str(ORNEK)]), 0)
        self.assertIn("sabah-14:C03", out.getvalue())


if __name__ == "__main__":
    unittest.main()
