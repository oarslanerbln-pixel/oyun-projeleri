"""Animasyon testleri için geçici depo kökünde küçük bir proje kurar."""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import _yollar  # noqa: E402,F401

MARKA = {
    "kimlik": "test-marka", "ad": "Test Marka",
    "renk": {
        "ana": {"$type": "color", "$value": "#000000"},
        "ana-ustu": {"$type": "color", "$value": "#ffffff"},
        "vurgu": {"$type": "color", "$value": "#ffcc00"},
        "zemin": {"$type": "color", "$value": "#ffffff"},
        "metin": {"$type": "color", "$value": "#111111"},
        "gri": {"$type": "color", "$value": "#bbbbbb"},
    },
    "yazi": {"baslik": {"aile": {"$type": "fontFamily", "$value": "Inter"}},
             "govde": {"aile": {"$type": "fontFamily", "$value": "Inter"}}},
    "logo": {"metin": "TEST"},
    "ses": {"ton": ["net"], "yasak": ["acele"]},
}
BRIF = {"hedef": "Kaydı artırmak", "kitle": "Öğrenciler", "icgoru": "Vakitleri yok",
        "onerme": "Beş dakikada hazır", "olcut": "Haftalık kayıt", "cagri": "Hemen dene",
        "kanitlar": ["Kurulum 4 dk"]}
METIN = ("anahtar,tr,en,kaynak,not,izin,azami\n"
         "baslik,Beş dakikada hazır,Ready in five,,,,\n"
         "vo,Kısa bir cümle,A short line,,,,\n"
         "uzun,bir iki üç dört beş altı yedi sekiz dokuz on,one two three four five six seven eight nine ten,,,,\n"
         "kotu,Yavaş <b>&</b>,Slow,,,,\n")
BASLIK = "cekim,sure_sn,metin_anahtari,ekran,gorsel,kamera,gecis,odak_x,odak_y,sinif,durum,zemin,on,logo,cagri\n"
CEKIMLER = (BASLIK +
            "C01,2,,baslik,açılış,sabit,erime,0.5,0.5,,animatik,ana,ana-ustu,evet,\n"
            "C02,3,vo,,ürün,yavaş itme,kesme,0.3,0.6,B,animatik,,,,evet\n")


def proje_kur(kok: Path, marka=None, brif=None, metin=METIN, cekimler=CEKIMLER, proje_over=None,
              kurgular=None) -> Path:
    (kok / "platform").mkdir(exist_ok=True)  # depo kökü işareti
    p = kok / "p"
    for sub in ("marka", "metin", "docs/01-oz", "docs/04-yapi"):
        (p / sub).mkdir(parents=True, exist_ok=True)
    (p / "marka/marka.json").write_text(json.dumps(marka or MARKA), encoding="utf-8")
    (p / "docs/01-oz/brif.json").write_text(json.dumps(brif or BRIF), encoding="utf-8")
    (p / "metin/metin.csv").write_text(metin, encoding="utf-8")
    (p / "docs/04-yapi/cekimler.csv").write_text(cekimler, encoding="utf-8")
    data = {
        "kimlik": "test", "tur": "animasyon", "marka": "p/marka/marka.json", "diller": ["tr", "en"],
        "metin": {"tablolar": ["p/metin/metin.csv"]}, "brif": "p/docs/01-oz/brif.json",
        "kurgular": kurgular or [{"ad": "k", "cekimler": "p/docs/04-yapi/cekimler.csv", "fps": 30,
                                  "teslim": ["dikey", "kare"]}],
    }
    data.update(proje_over or {})
    (p / "proje.json").write_text(json.dumps(data), encoding="utf-8")
    return p / "proje.json"


def marka_ile(**renk):
    m = copy.deepcopy(MARKA)
    for k, v in renk.items():
        m["renk"][k] = {"$type": "color", "$value": v}
    return m
