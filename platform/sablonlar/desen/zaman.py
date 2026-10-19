"""Desen şablonunun senaryosu ve zaman çizelgesi: <stil>.json → sahneler, yerleşim, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur; ikisi de sahne başlarında vurur.
Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
from pathlib import Path

from motifler import MOTIFLER

STILLER = ("vitray", "linol", "cini", "teknik-cizim")
FORMATLAR = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}
SURE = (6.0, 20.0)
SAHNE_EN_KISA = 1.6
BASLIK_AZAMI, ALT_AZAMI, IMZA_AZAMI = 16, 32, 24
GECIS = 0.45  # sahne geçişi (sn): önceki sahne bu kadar önce söner / kayar

# Yerleşim (ekran oranı): motif merkezi ve yarı boyu, başlık / alt satır merkezi, yazı genişliği.
# 9:16'da üst %10 ve alt %22 Reels arayüzüne kalır; her öğe bu bandın içinde.
YERLESIM = {
    "9x16": {"mx": 0.50, "my": 0.385, "mr": 0.285, "r_eksen": "w", "bx": 0.50, "by": 0.655, "ay": 0.725, "gen": 0.84, "boy": 0.135},
    "16x9": {"mx": 0.26, "my": 0.50, "mr": 0.30, "r_eksen": "h", "bx": 0.73, "by": 0.45, "ay": 0.585, "gen": 0.42, "boy": 0.15},
    "1x1": {"mx": 0.50, "my": 0.355, "mr": 0.225, "r_eksen": "w", "bx": 0.50, "by": 0.745, "ay": 0.845, "gen": 0.84, "boy": 0.12},
    "4x5": {"mx": 0.50, "my": 0.37, "mr": 0.255, "r_eksen": "w", "bx": 0.50, "by": 0.70, "ay": 0.79, "gen": 0.84, "boy": 0.125},
}
GUVENLI = {"9x16": (0.10, 0.78), "16x9": (0.06, 0.94), "1x1": (0.05, 0.95), "4x5": (0.06, 0.92)}  # (üst, alt) sınırı


class SenaryoHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s.setdefault("seslendirme", {"satirlar": []})
    s.setdefault("muzik", {})
    s.setdefault("renkler", {})
    sh = s.get("sahneler") or []
    for i, x in enumerate(sh):
        x["_son"] = sh[i + 1]["t"] if i + 1 < len(sh) else s.get("sure", 0)
    return s


def bicim(s: dict, fmt: str) -> dict:
    """Senaryonun `yerlesim.<format>` alanı varsayılan yerleşimi ezer (ince ayar için)."""
    return {**YERLESIM[fmt], **(s.get("yerlesim", {}).get(fmt, {}))}


def sahne(s: dict, t: float) -> tuple[int, float, float]:
    """t anındaki sahne: (sıra, sahne içi an, sahne süresi)."""
    sh = s["sahneler"]
    i = max([k for k, x in enumerate(sh) if x["t"] <= t] or [0])
    return i, t - sh[i]["t"], sh[i]["_son"] - sh[i]["t"]


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    """HATA listesi; boşsa senaryo render'a hazır. `sureler`: seslendirme satırı → saniye (seslendirme.json)."""
    h: list[str] = []
    stil = s.get("stil")
    if stil not in STILLER:
        h.append(f"stil: \"{stil}\" bilinmiyor ({', '.join(STILLER)})")
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or not SURE[0] <= sure <= SURE[1]:
        h.append(f"sure: {SURE[0]:g}–{SURE[1]:g} sn arası olmalı ({sure})")
        return h
    fmt = s.get("format")
    for f in ([fmt] if isinstance(fmt, str) else (fmt or [])):
        k = str(f).replace(":", "x")
        if k != "ikisi" and k not in FORMATLAR:
            h.append(f"format: {f} bilinmiyor (9:16, 16:9, 1:1, 4:5 ya da ikisi)")
    sh = s.get("sahneler") or []
    if not 1 <= len(sh) <= 6:
        h.append(f"sahneler: 1–6 sahne olmalı ({len(sh)})")
        return h
    if sh[0].get("t") != 0:
        h.append("sahneler[0].t: ilk sahne 0'da başlamalı")
    for i, x in enumerate(sh):
        ad = f"sahneler[{i}]"
        if not isinstance(x.get("t"), (int, float)):
            h.append(f"{ad}.t: sayı olmalı"); continue
        son = sh[i + 1].get("t") if i + 1 < len(sh) else sure
        if isinstance(son, (int, float)) and son - x["t"] < SAHNE_EN_KISA:
            h.append(f"{ad}: {son - x['t']:.2f} sn, en az {SAHNE_EN_KISA:g} sn olmalı (sahneler sırayla)")
        if x.get("motif") is not None and x["motif"] not in MOTIFLER:
            h.append(f"{ad}.motif: \"{x['motif']}\" yok ({', '.join(MOTIFLER)})")
        b = x.get("baslik")
        if not isinstance(b, str) or not b.strip():
            h.append(f"{ad}.baslik: boş")
        elif len(b) > BASLIK_AZAMI:
            h.append(f"{ad}.baslik: \"{b}\" {len(b)} karakter, en çok {BASLIK_AZAMI}")
        a = x.get("alt")
        if a is not None and (not isinstance(a, str) or len(a) > ALT_AZAMI):
            h.append(f"{ad}.alt: en çok {ALT_AZAMI} karakterlik metin olmalı")
        if x.get("olcu") is not None and not isinstance(x["olcu"], (list, tuple)):
            h.append(f"{ad}.olcu: [genişlik, yükseklik] olmalı")
    imza = s.get("imza")
    if imza is not None and (not isinstance(imza, str) or len(imza) > IMZA_AZAMI):
        h.append(f"imza: en çok {IMZA_AZAMI} karakter")
    g = s.get("gorsel")
    if g is not None:
        if not isinstance(g, dict) or not g.get("dosya"):
            h.append('gorsel: {"dosya": "logo.png"} biçiminde olmalı')
        elif not (Path(s.get("_klasor", ".")) / g["dosya"]).exists():
            h.append(f"gorsel.dosya: {g['dosya']} bulunamadı (senaryoya göre)")
    satirlar = s["seslendirme"].get("satirlar", [])
    for a, b in zip(satirlar, satirlar[1:]):
        if b.get("t", 0) <= a.get("t", 0):
            h.append(f"seslendirme: {b['id']} {a['id']}'den sonra başlamalı")
        elif sureler and a["id"] in sureler and a["t"] + sureler[a["id"]] > b["t"]:
            h.append(f"seslendirme: {a['id']} ({sureler[a['id']]:.2f} sn) {b['id']} başlamadan bitmiyor")
    for x in satirlar:
        if not isinstance(x.get("t"), (int, float)) or not 0 <= x["t"] < sure:
            h.append(f"seslendirme: {x.get('id')} anı videonun içinde olmalı")
    if satirlar and sureler and satirlar[-1]["id"] in sureler:
        z = satirlar[-1]
        if z["t"] + sureler[z["id"]] > sure - 0.15:
            h.append(f"seslendirme: {z['id']} video bitince hâlâ konuşuyor")
    return h
