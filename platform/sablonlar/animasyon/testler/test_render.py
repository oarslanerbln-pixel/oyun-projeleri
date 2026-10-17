import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yardim import BASLIK, proje_kur  # noqa: E402

import animasyon  # noqa: E402
import proje  # noqa: E402
import render  # noqa: E402

CEKIMLER = (BASLIK +
            "C01,2,,baslik,açılış,sabit,erime,0.5,0.5,,animatik,ana,ana-ustu,evet,\n"
            "C02,2,vo,,ürün,yavaş itme,kayma,0.3,0.6,C,uretim,,,,\n"
            "C03,1,,,kapanış,yavaş çekme,kesme,0.5,0.5,,animatik,,,evet,evet\n")
KAYIT = "dosya,sinif,model,tarih,prompt,kullanildigi_yer,kaynak_ozeti,arac,duzenleme,istek_ozeti,maliyet_usd,lisans,tohum\n"


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)
        self.proje_json = proje_kur(self.kok, cekimler=CEKIMLER)
        self.p, b = proje.yukle(self.proje_json)
        self.assertIsNotNone(self.p, b)
        self.k = self.p.kurgular[0]

    def tearDown(self):
        self._tmp.cleanup()

    def kayit_yaz(self, *satirlar):
        (self.p.klasor / "yz-kaydi.csv").write_text(KAYIT + "".join(s + "\n" for s in satirlar), encoding="utf-8")
        return render.kayitlar(render.kayit_yolu(self.p, self.kok))


class SureTests(unittest.TestCase):
    def test_dtcg_sure(self):
        self.assertEqual(render.sure_sn("400ms"), 0.4)
        self.assertEqual(render.sure_sn("0.25s"), 0.25)
        self.assertEqual(render.sure_sn(300), 0.3)
        self.assertEqual(render.sure_sn(None), render.VARSAYILAN_GIRIS)


class KaynakTests(Tmp):
    def tl(self):
        return render.zaman_cizelgesi(list(self.k.cekimler), self.k.fps)

    def test_kayit_yoksa_yer_tutucu(self):
        z = self.tl()[1]
        self.assertEqual(render.kaynak_bul("k", z, [], self.kok).tur, render.YER_TUTUCU)

    def test_en_son_klip_kazanir_dosyasi_olmayan_atlanir(self):
        (self.kok / "eski.mp4").write_bytes(b"x")
        (self.kok / "yeni.mp4").write_bytes(b"x")
        kayit = self.kayit_yaz("eski.mp4,C,fal-kling,,,k/C02,,,,a,0.5,ticari,1",
                               "yeni.mp4,C,fal-kling,,,k/C02,,,,b,0.5,ticari,2",
                               "yok.mp4,C,fal-kling,,,k/C02,,,,c,0.5,ticari,3",
                               "istek.kuru.json,C,kuru,,,k/C02,,,,d,0,kuru,4")
        kaynak = render.kaynak_bul("k", self.tl()[1], kayit, self.kok)
        self.assertEqual((kaynak.tur, kaynak.yol.name, kaynak.lisans), (render.KLIP, "yeni.mp4", "ticari"))

    def test_baska_kurgunun_klibi_kullanilmaz(self):
        (self.kok / "a.mp4").write_bytes(b"x")
        kayit = self.kayit_yaz("a.mp4,C,fal-kling,,,baska/C02,,,,a,0.5,ticari,1")
        self.assertEqual(render.kaynak_bul("k", self.tl()[1], kayit, self.kok).tur, render.YER_TUTUCU)

    def test_anahtar_kare(self):
        csv_ = (BASLIK.rstrip("\n") + ",anahtar_kare\n"
                "C01,2,,baslik,a,sabit,kesme,0.5,0.5,B,animatik,ana,ana-ustu,evet,,kare.png\n")
        p, b = proje.yukle(proje_kur(self.kok, cekimler=csv_))
        (self.kok / "kare.png").write_bytes(b"x")
        z = render.zaman_cizelgesi(list(p.kurgular[0].cekimler), 30)[0]
        self.assertEqual(render.kaynak_bul("k", z, [], self.kok).tur, render.KARE)


class ZamanTests(Tmp):
    def test_gecis_ve_kuyruk_toplam_sureyi_korur(self):
        pl = render.parcalar(self.p, self.k, self.kok, [])
        fps = self.k.fps
        self.assertEqual([round(pa.gecis * fps) for pa in pl], [12, 12, 0])  # 400 ms, kesme 0
        self.assertEqual([pa.kuyruk for pa in pl], [12, 0, 0])
        # xfade her geçişte örtüşen kareleri bir kez sayar: toplam = çekim listesi.
        toplam = sum(pa.z.kareler + pa.kuyruk for pa in pl) - sum(round(pa.gecis * fps) for pa in pl[1:])
        self.assertEqual(toplam, pl[-1].z.son_kare)

    def test_kisa_cekimde_gecis_ucte_bir(self):
        csv_ = BASLIK + "C01,0.6,,,a,sabit,erime,0.5,0.5,,animatik,,,evet,\n"
        p, _ = proje.yukle(proje_kur(self.kok, cekimler=csv_))
        self.assertAlmostEqual(render.parcalar(p, p.kurgular[0], self.kok, [])[0].gecis, 0.2)

    def test_birlestir_grafi(self):
        graf = render.birlestir_grafi(render.parcalar(self.p, self.k, self.kok, []), 30)
        self.assertIn("[p0]fade=in:st=0:d=0.4[a0]", graf)
        self.assertIn("[a0][p1]xfade=transition=slideleft:duration=0.4:offset=2.000000[x1]", graf)
        self.assertIn("[x1][p2]concat=n=2:v=1:a=0[x2]", graf)


class KatmanTests(Tmp):
    def test_katman_saydam_kilavuzsuz_yer_tutucu_etiketli(self):
        pl = render.parcalar(self.p, self.k, self.kok, [])
        a = self.k.teslim[0]
        svg = render.katman_svg(pl[1], a, self.p, "tr")
        self.assertNotIn("<rect width=", svg)
        self.assertNotIn("kilavuz", svg)
        self.assertIn("YZ C02 · yer tutucu", svg)
        self.assertNotIn("yer tutucu", render.katman_svg(pl[0], a, self.p, "tr"))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg yok")
class RenderTests(Tmp):
    def test_mp4_suresi_kareleri_sesi_altyazisi(self):
        klip = self.kok / "c02.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=24:d=1",
                        "-pix_fmt", "yuv420p", str(klip)], check=True)
        self.kayit_yaz("c02.mp4,C,fal-kling,,,k/C02,,,,a,0.5,ticari,1")
        out = self.kok / "cikti"
        with unittest.mock.patch("sys.stdout"):
            kod = animasyon.main(["render", str(self.proje_json), "--teslim", "kare", "-o", str(out)])
        self.assertEqual(kod, 0)
        mp4 = out / "k" / "kare" / "test-k-kare-tr.mp4"
        bilgi = render.olcum(mp4)
        akis = {s["codec_type"]: s for s in bilgi["streams"]}
        self.assertEqual((akis["video"]["width"], akis["video"]["height"]), (1080, 1080))
        self.assertEqual(int(akis["video"]["nb_frames"]), 150)
        self.assertAlmostEqual(float(bilgi["format"]["duration"]), 5.0, delta=0.05)
        self.assertIn("audio", akis)
        self.assertEqual(sum(s["codec_type"] == "subtitle" for s in bilgi["streams"]), 2)

    def test_bilinmeyen_on_ayar_hata(self):
        yazilan, b = render.render(self.p, self.kok, self.kok / "o", teslim="youtube-bumper")
        self.assertEqual(yazilan, [])
        self.assertTrue(any(x.seviye == render.HATA for x in b))

    def test_eksik_muzik_hata(self):
        _, b = render.render(self.p, self.kok, self.kok / "o", muzik=self.kok / "yok.wav")
        self.assertTrue(any(x.seviye == render.HATA for x in b))


if __name__ == "__main__":
    unittest.main()
