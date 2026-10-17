"""Animasyon projesini `proje.json`'dan okur ve bütün katmanları birlikte doğrular.

`proje.json` (mimari §2) projenin kökündedir; içindeki yollar depo köküne
görelidir (deponun kökü: içinde `platform/` klasörü olan en yakın üst klasör).
Animasyon türü için alanlar:

  kimlik, tur ("animasyon"), marka, diller, metin {tablolar, sozlukler},
  brif (01-oz), kurgular [{ad, cekimler (04-yapi), fps, teslim [ön ayar…]}]

Tek brif, birden çok kurgu: aynı önerme 15 sn dikey ve 6 sn bumper olarak
ayrı kurgulanır. Bir kurgu birden çok ön ayara teslim edilir (aynı çekim
listesi, farklı oran; kırpma merkezi `odak_x/odak_y`'den).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import _yollar  # noqa: F401
import cekimler as cekim_mod
import marka as marka_mod
import metin as metin_mod
import teslim as teslim_mod
from metin import HATA, UYARI, Bulgu, has_errors

FPS_IZINLI = (24, 25, 30, 60)
BRIF_ZORUNLU = ("hedef", "kitle", "icgoru", "onerme", "olcut")
ONERME_EN_COK_SOZCUK = 12


@dataclass(frozen=True)
class Brif:
    hedef: str
    kitle: str
    icgoru: str
    onerme: str
    olcut: str
    cagri: str = ""
    kanitlar: tuple[str, ...] = ()


@dataclass(frozen=True)
class Kurgu:
    ad: str
    fps: int
    cekimler: tuple[cekim_mod.Cekim, ...]
    teslim: tuple[teslim_mod.OnAyar, ...]

    @property
    def sure(self) -> float:
        return sum(c.sure_sn for c in self.cekimler)


@dataclass(frozen=True)
class Proje:
    kimlik: str
    klasor: Path
    marka: marka_mod.Marka
    diller: tuple[str, ...]
    tablo: metin_mod.Tablo
    brif: Brif
    kurgular: tuple[Kurgu, ...]


def depo_koku(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "platform").is_dir():
            return p
    return start


def _platform_yolu(kok: Path, rel: str) -> Path:
    """`platform/...` yolu depoda yoksa bu kodun bulunduğu platforma düşer
    (platformu alt modül ya da kopya olarak alan müşteri deposu, testler)."""
    path = kok / rel
    if not path.exists() and Path(rel).parts[:1] == ("platform",):
        return _yollar.PLATFORM.joinpath(*Path(rel).parts[1:])
    return path


def brif_denetle(data: object) -> list[Bulgu]:
    if not isinstance(data, dict):
        return [Bulgu(HATA, "brif", "nesne olmalı")]
    b = []
    for name in BRIF_ZORUNLU:
        if not isinstance(data.get(name), str) or not data[name].strip():
            b.append(Bulgu(HATA, f"brif.{name}", "zorunlu alan boş"))
    onerme = data.get("onerme")
    if isinstance(onerme, str):
        n = len(onerme.split())
        if n > ONERME_EN_COK_SOZCUK:
            b.append(Bulgu(UYARI, "brif.onerme", f"{n} sözcük; tek önerme {ONERME_EN_COK_SOZCUK} sözcüğü geçmemeli"))
        if " ve " in f" {metin_mod.lower(onerme, 'tr')} ":
            b.append(Bulgu(UYARI, "brif.onerme", "'ve' içeriyor; iki önerme olabilir"))
    kanitlar = data.get("kanitlar", [])
    if not isinstance(kanitlar, list) or not all(isinstance(k, str) for k in kanitlar):
        b.append(Bulgu(HATA, "brif.kanitlar", "metin listesi olmalı"))
    elif not kanitlar:
        b.append(Bulgu(UYARI, "brif.kanitlar", "önermeyi destekleyen kanıt yok"))
    return b


def _json(path: Path, b: list[Bulgu]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        b.append(Bulgu(HATA, str(path), "dosya yok"))
    except json.JSONDecodeError as e:
        b.append(Bulgu(HATA, str(path), f"geçersiz JSON (satır {e.lineno}): {e.msg}"))
    return None


def yukle(proje_json: str | Path, kok: Path | None = None) -> tuple[Proje | None, list[Bulgu]]:
    proje_json = Path(proje_json).resolve()
    kok = (kok or depo_koku(proje_json.parent)).resolve()
    b: list[Bulgu] = []
    data = _json(proje_json, b)
    if data is None:
        return None, b
    if not isinstance(data, dict):
        return None, [Bulgu(HATA, "proje", "nesne olmalı")]
    if data.get("tur") != "animasyon":
        b.append(Bulgu(HATA, "proje.tur", f"bu şablon 'animasyon' türünü okur, {data.get('tur')!r} geldi"))
    for key in ("kimlik", "marka", "brif"):
        if not isinstance(data.get(key), str) or not data[key]:
            b.append(Bulgu(HATA, f"proje.{key}", "zorunlu"))
    diller = data.get("diller") or ["tr"]
    metin_cfg = data.get("metin") or {}
    kurgular_raw = data.get("kurgular")
    if not isinstance(kurgular_raw, list) or not kurgular_raw:
        b.append(Bulgu(HATA, "proje.kurgular", "en az bir kurgu gerekli"))
        kurgular_raw = []
    if has_errors(b):
        return None, b

    # 0 · marka
    marka, mb = marka_mod.yukle(kok / data["marka"])
    b += [Bulgu(x.seviye, x.yer, x.mesaj) for x in mb]

    # metin: tablo + katmanlı sözlük (temel + proje sözlükleri + marka)
    tablo, tb = metin_mod.tablo_oku([kok / p for p in metin_cfg.get("tablolar", [])], tuple(diller))
    b += tb
    kurallar = []
    # Sözlük verilmezse stüdyonun temel sözlüğü kullanılır (mutlak yol; kok / mutlak = mutlak).
    for s in metin_cfg.get("sozlukler", [str(metin_mod.TEMEL)]):
        try:
            kurallar += metin_mod.sozluk_oku(_platform_yolu(kok, s))
        except (FileNotFoundError, ValueError) as e:
            b.append(Bulgu(HATA, "proje.metin.sozlukler", str(e)))
    if marka is not None:
        kurallar += metin_mod.marka_kurallari(marka.yasak)
    b += metin_mod.denetle(tablo, kurallar)

    # 1 · öz (brif)
    brif_raw = _json(kok / data["brif"], b)
    brif = None
    if brif_raw is not None:
        bb = brif_denetle(brif_raw)
        b += bb
        if not has_errors(bb):
            brif = Brif(**{k: brif_raw.get(k, "") for k in ("hedef", "kitle", "icgoru", "onerme", "olcut", "cagri")},
                        kanitlar=tuple(brif_raw.get("kanitlar", [])))

    # 4 · yapı (kurgular)
    on_ayarlar = teslim_mod.yukle()
    kurgular: list[Kurgu] = []
    seen: set[str] = set()
    for i, k in enumerate(kurgular_raw):
        yer = f"proje.kurgular[{i}]"
        if not isinstance(k, dict) or not isinstance(k.get("ad"), str) or not isinstance(k.get("cekimler"), str):
            b.append(Bulgu(HATA, yer, "ad ve cekimler zorunlu"))
            continue
        ad = k["ad"]
        if ad in seen:
            b.append(Bulgu(HATA, yer, f"kurgu adı {ad!r} tekrar ediyor"))
            continue
        seen.add(ad)
        fps = k.get("fps", 30)
        if fps not in FPS_IZINLI:
            b.append(Bulgu(HATA, f"{ad}.fps", f"{fps!r} desteklenmiyor; {FPS_IZINLI}"))
        teslim = []
        for t in k.get("teslim") or []:
            if t in on_ayarlar:
                teslim.append(on_ayarlar[t])
            else:
                b.append(Bulgu(HATA, f"{ad}.teslim", f"bilinmeyen ön ayar {t!r}; {', '.join(on_ayarlar)}"))
        if not k.get("teslim"):
            b.append(Bulgu(HATA, f"{ad}.teslim", "en az bir teslim ön ayarı gerekli"))
        liste, cb = cekim_mod.oku(kok / k["cekimler"])
        b += cb
        if liste and marka is not None and not has_errors(cb):
            b += cekim_mod.denetle(ad, liste, marka, tablo, diller[0], teslim, brif.cagri if brif else "")
        kurgular.append(Kurgu(ad, fps, tuple(liste), tuple(teslim)))

    if has_errors(b) or marka is None or brif is None:
        return None, b
    return Proje(data["kimlik"], proje_json.parent, marka, tuple(diller), tablo, brif, tuple(kurgular)), b
