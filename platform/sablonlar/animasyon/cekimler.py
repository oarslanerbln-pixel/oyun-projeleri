"""Çekim listesi (`cekimler.csv`, mimari §5.1): zamanlamanın depodaki tek kaynağı.

Belgedeki sütunlar: `cekim, sure_sn, metin_anahtari, gorsel, kamera, gecis,
odak_x, odak_y, sinif, durum`. Animatik için eklenen isteğe bağlı sütunlar:
`ekran` (ekrandaki yazının metin anahtarı), `zemin` ve `on` (marka renk adları),
`logo` ve `cagri` (`evet` ise o çekimde logo / CTA görünür).

`metin_anahtari` seslendirme ve altyazıdır; `ekran` ekrana basılan yazıdır.
İkisi de metin tablosuna bağlanır, metnin kendisi bu dosyada yazılmaz.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import _yollar  # noqa: F401
from marka import CONTRAST_LARGE, Marka, contrast_ratio
from metin import HATA, UYARI, Bulgu, Tablo

COLUMNS = ("cekim", "sure_sn", "metin_anahtari", "gorsel", "kamera", "gecis",
           "odak_x", "odak_y", "sinif", "durum", "ekran", "zemin", "on", "logo", "cagri")
REQUIRED = ("cekim", "sure_sn")
GECISLER = ("kesme", "erime", "kayma")
DURUMLAR = ("animatik", "uretim", "onay", "kilit")
SINIFLAR = ("A", "B", "C", "elle")
EVET = ("evet", "")

VO_WPS = 2.5          # rahat seslendirme hızı (sözcük/sn)
SCREEN_WPS = 3.0      # ekrandaki yazı için rahat okuma hızı
LOGO_ICINDE_SN = 3.0  # kısa biçimde markanın görünmesi gereken süre
KISA_BICIM_SN = 90


@dataclass(frozen=True)
class Cekim:
    cekim: str
    sure_sn: float
    metin_anahtari: str = ""
    gorsel: str = ""
    kamera: str = ""
    gecis: str = "kesme"
    odak_x: float = 0.5
    odak_y: float = 0.5
    sinif: str = ""
    durum: str = "animatik"
    ekran: str = ""
    zemin: str = "zemin"
    on: str = "metin"
    logo: bool = False
    cagri: bool = False


@dataclass(frozen=True)
class Zamanli:
    cekim: Cekim
    bas: float
    son: float
    bas_kare: int
    son_kare: int  # dahil değil

    @property
    def kareler(self) -> int:
        return self.son_kare - self.bas_kare


def zaman_cizelgesi(cekimler: list[Cekim], fps: int) -> list[Zamanli]:
    """Çekimleri art arda dizer. Kare sınırları birikimli süreden yuvarlanır;
    yuvarlama hatası birikmez, çekimler arasında boşluk kalmaz."""
    out, t = [], 0.0
    for c in cekimler:
        bas, son = t, t + c.sure_sn
        out.append(Zamanli(c, round(bas, 6), round(son, 6), round(bas * fps), round(son * fps)))
        t = son
    return out


def oku(path: str | Path) -> tuple[list[Cekim], list[Bulgu]]:
    path = Path(path)
    cekimler: list[Cekim] = []
    b: list[Bulgu] = []
    try:
        f = path.open(encoding="utf-8", newline="")
    except FileNotFoundError:
        return [], [Bulgu(HATA, str(path), "dosya yok")]
    with f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for col in REQUIRED:
            if col not in cols:
                b.append(Bulgu(HATA, path.name, f"'{col}' sütunu yok"))
        unknown = [c for c in cols if c not in COLUMNS]
        if unknown:
            b.append(Bulgu(UYARI, path.name, f"bilinmeyen sütun: {', '.join(unknown)}"))
        if b and any(x.seviye == HATA for x in b):
            return [], b
        seen: set[str] = set()
        for n, row in enumerate(reader, start=2):
            row = {k: (v or "").strip() for k, v in row.items() if k}
            yer = f"{path.name}:{n}"
            cid = row.get("cekim", "")
            if not cid:
                b.append(Bulgu(HATA, yer, "cekim kimliği boş"))
                continue
            if cid in seen:
                b.append(Bulgu(HATA, yer, f"cekim {cid!r} tekrar ediyor"))
                continue
            seen.add(cid)
            yer = f"{path.name}:{cid}"
            try:
                sure = float(row.get("sure_sn", ""))
            except ValueError:
                sure = 0.0
            if sure <= 0:
                b.append(Bulgu(HATA, yer, "sure_sn pozitif sayı olmalı"))
                continue
            odak = []
            for key in ("odak_x", "odak_y"):
                raw = row.get(key) or "0.5"
                try:
                    v = float(raw)
                except ValueError:
                    v = -1
                if not 0 <= v <= 1:
                    b.append(Bulgu(HATA, yer, f"{key} 0 ile 1 arasında olmalı, {raw!r} geldi"))
                    v = 0.5
                odak.append(v)
            gecis = row.get("gecis") or "kesme"
            if gecis not in GECISLER:
                b.append(Bulgu(HATA, yer, f"gecis {gecis!r} bilinmiyor; {', '.join(GECISLER)}"))
            durum = row.get("durum") or "animatik"
            if durum not in DURUMLAR:
                b.append(Bulgu(HATA, yer, f"durum {durum!r} bilinmiyor; {', '.join(DURUMLAR)}"))
            sinif = row.get("sinif", "")
            if sinif and sinif not in SINIFLAR:
                b.append(Bulgu(HATA, yer, f"sinif {sinif!r} bilinmiyor; {', '.join(SINIFLAR)}"))
            for key in ("logo", "cagri"):
                if row.get(key, "") not in EVET:
                    b.append(Bulgu(HATA, yer, f"{key} yalnız 'evet' ya da boş olabilir"))
            cekimler.append(Cekim(
                cekim=cid, sure_sn=sure, metin_anahtari=row.get("metin_anahtari", ""),
                gorsel=row.get("gorsel", ""), kamera=row.get("kamera", ""), gecis=gecis,
                odak_x=odak[0], odak_y=odak[1], sinif=sinif, durum=durum,
                ekran=row.get("ekran", ""), zemin=row.get("zemin") or "zemin", on=row.get("on") or "metin",
                logo=row.get("logo") == "evet", cagri=row.get("cagri") == "evet",
            ))
    if not cekimler and not b:
        b.append(Bulgu(HATA, path.name, "en az bir çekim gerekli"))
    return cekimler, b


def denetle(kurgu: str, cekimler: list[Cekim], marka: Marka, tablo: Tablo, dil: str,
            on_ayarlar: list, cagri: str) -> list[Bulgu]:
    """Kurgu düzeyindeki rasyonel kreatif denetimleri. `on_ayarlar`: kurgunun teslim ön ayarları."""
    b: list[Bulgu] = []
    toplam, logo_at, has_cagri = 0.0, None, False
    for c in cekimler:
        yer = f"{kurgu}:{c.cekim}"
        for role in (c.zemin, c.on):
            if role not in marka.renk:
                b.append(Bulgu(HATA, yer, f"marka kitinde {role!r} rengi yok"))
        for key in (c.metin_anahtari, c.ekran):
            if key and key not in tablo.satirlar:
                b.append(Bulgu(HATA, yer, f"metin tablosunda {key!r} anahtarı yok"))
        if c.ekran in tablo.satirlar:
            text = tablo.al(c.ekran, dil)
            words = len(text.split())
            if words / c.sure_sn > SCREEN_WPS:
                b.append(Bulgu(UYARI, yer, f"ekran yazısı {words} sözcük, {c.sure_sn:g} sn'de okunmaz "
                                           f"(en çok {SCREEN_WPS:g} sözcük/sn)"))
            if c.zemin in marka.renk and c.on in marka.renk:
                ratio = contrast_ratio(marka.renk_al(c.on), marka.renk_al(c.zemin))
                if ratio < CONTRAST_LARGE:
                    b.append(Bulgu(HATA, yer, f"{c.zemin} üstünde {c.on} kontrastı {ratio:.2f}, "
                                              f"ekran yazısı için en az {CONTRAST_LARGE}"))
        if c.metin_anahtari in tablo.satirlar:
            words = len(tablo.al(c.metin_anahtari, dil).split())
            if words / c.sure_sn > VO_WPS:
                b.append(Bulgu(UYARI, yer, f"seslendirme {words} sözcük, {c.sure_sn:g} sn'ye sığmaz "
                                           f"(en çok {VO_WPS:g} sözcük/sn)"))
        if c.logo and logo_at is None:
            logo_at = toplam
        has_cagri |= c.cagri
        toplam += c.sure_sn

    for a in on_ayarlar:
        if a.sure_siniri and toplam > a.sure_siniri:
            b.append(Bulgu(HATA, kurgu, f"toplam {toplam:g} sn, '{a.ad}' en çok {a.sure_siniri:g} sn "
                                        f"(sınır kontrolü {a.sinir_kontrol})"))
    if any(a.sure_siniri and a.sure_siniri <= KISA_BICIM_SN for a in on_ayarlar) and (
            logo_at is None or logo_at > LOGO_ICINDE_SN):
        b.append(Bulgu(UYARI, kurgu, f"kısa biçimde marka ilk {LOGO_ICINDE_SN:g} sn içinde görünmeli "
                                     "(bir çekimde logo=evet)"))
    if cagri and not has_cagri:
        b.append(Bulgu(UYARI, kurgu, f"brifte çağrı var ({cagri!r}) ama hiçbir çekimde cagri=evet yok"))
    return b
