"""Oyuncak şablonunun zaman çizelgesi: oyuncak.json → sahneler, kolon yükselişleri, zıplamalar, ses olayları.

Görüntü (`sahne.js`, `cizelge()` çıktısıyla) ve ses (`sentez.py`) yalnız buradan okur; ikisi de aynı anlarda vurur.
Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SIRA = ("adimlar", "buyume", "karsitlik", "kapanis")  # ilk ikisi zorunlu, sıra sabit
ROLLER = ("gok_ust", "gok_alt", "gok_ust_son", "gok_alt_son", "ada", "kahraman", "kolon_bas", "kolon_orta",
          "kolon_son", "yazi_yuz", "yazi_yan", "doruk_yuz", "doruk_yan")
VARSAYILAN_PALET = {"gok_ust": "#FFD9C4", "gok_alt": "#FFB8A0", "gok_ust_son": "#FFF1C9", "gok_alt_son": "#FFCFA0",
                    "ada": "#FFF3E4", "kahraman": "#FF6B5B", "kolon_bas": "#5CC9B5", "kolon_orta": "#7DA7F0",
                    "kolon_son": "#FFC94A", "yazi_yuz": "#FFF8EC", "yazi_yan": "#FF6B5B",
                    "doruk_yuz": "#FFC94A", "doruk_yan": "#E59A1E"}
# Fa majör, sıcak: Fmaj7 – Dm9 – B♭maj7 – Fmaj7 – C – F(add9); [bas, ses1..ses4] MIDI
VARSAYILAN_AKORLAR = [[41, 57, 60, 64, 69], [38, 57, 60, 62, 65], [46, 58, 62, 65, 69],
                      [41, 57, 60, 64, 67], [43, 55, 60, 62, 67], [41, 60, 64, 65, 69]]
ZIPLA_SN = 0.42       # bir zıplamanın havada geçen süresi
YUKSELIS_SN = 0.38    # bir kolonun yerden çıkışı
KUTLAMA_SN = 0.36     # tepede sevinç zıplaması
YAZI_SINIRI = {"adimlar": 8, "buyume": 8, "kapanis": 18}
EN_KISA_SAHNE = 0.8


class SenaryoHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("kimlik", yol.stem)
    s.setdefault("fps", 30)
    s["palet"] = {**VARSAYILAN_PALET, **s.get("palet", {})}
    m = s.setdefault("muzik", {})
    m.setdefault("bpm", 120)
    m.setdefault("ilk_vurus", 0.1)
    m.setdefault("akorlar", VARSAYILAN_AKORLAR)
    s.setdefault("seslendirme", {"satirlar": []})
    k = s.setdefault("kolonlar", {})
    k.setdefault("adet", 52)
    k.setdefault("oran", 37.4)  # son kolon / ilk kolon: 1,01^364
    sahneler = s.get("sahneler", [])
    for i, sh in enumerate(sahneler):
        sh["_son"] = sahneler[i + 1]["bas"] if i + 1 < len(sahneler) else s.get("sure", 0)
        sh.setdefault("kutlama", [])
        if sh.get("tur") == "adimlar":
            sh.setdefault("ziplamalar", [])
            if "yazi" in sh:
                sh["yazi"].setdefault("son_t", sh["_son"] - 0.25)
    return s


def sahne(s: dict, tur: str) -> dict | None:
    return next((x for x in s.get("sahneler", []) if x.get("tur") == tur), None)


def _renk(v) -> bool:
    return isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v) is not None


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    """HATA listesi; boşsa senaryo render'a hazır. `sureler`: seslendirme satırı → saniye (seslendirme.json)."""
    h = []
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or not 6 <= sure <= 20:
        return ["sure: 6–20 sn olmalı"]
    if s["fps"] not in (24, 25, 30, 60):
        h.append("fps: 24, 25, 30 ya da 60 olmalı")
    for r, v in s["palet"].items():
        if r not in ROLLER:
            h.append(f"palet: bilinmeyen rol {r} ({', '.join(ROLLER)})")
        elif not _renk(v):
            h.append(f"palet.{r}: #RRGGBB olmalı")
    m = s["muzik"]
    if not 70 <= m["bpm"] <= 160:
        h.append("muzik.bpm: 70–160 olmalı")
    if not 0 <= m["ilk_vurus"] < 60 / m["bpm"]:
        h.append("muzik.ilk_vurus: 0 ile bir vuruş süresi arasında olmalı")
    if len(m["akorlar"]) != 6 or any(not (isinstance(a, list) and len(a) == 5) for a in m["akorlar"]):
        h.append("muzik.akorlar: 6 akor, her biri [bas, 4 nota] (MIDI) olmalı")
    k = s["kolonlar"]
    if not (isinstance(k["adet"], int) and 8 <= k["adet"] <= 120):
        h.append("kolonlar.adet: 8–120 arası tam sayı olmalı")
    if not 1.5 <= k["oran"] <= 100:
        h.append("kolonlar.oran: 1,5–100 olmalı (son kolonun ilkine oranı)")

    sahneler = s.get("sahneler") or []
    turler = [x.get("tur") for x in sahneler]
    yapi = len(h)
    if turler[:2] != ["adimlar", "buyume"]:
        h.append("sahneler: 'adimlar' ve 'buyume' ile başlamalı")
    if any(t not in SIRA for t in turler):
        h.append(f"sahneler: tür {', '.join(SIRA)} olmalı")
    elif turler != sorted(turler, key=SIRA.index) or len(set(turler)) != len(turler):
        h.append(f"sahneler: her tür en çok bir kez ve {' → '.join(SIRA)} sırasıyla")
    if len(h) > yapi:  # sahne yapısı bozuksa ayrıntılı zaman denetimi anlamsız
        return h
    onceki = -1.0
    for i, sh in enumerate(sahneler):
        ad = f"sahne {i + 1} ({sh['tur']})"
        bas, son = sh.get("bas"), sh["_son"]
        if i == 0 and bas != 0:
            h.append(f"{ad}: ilk sahne 0'da başlamalı")
        if not isinstance(bas, (int, float)) or bas <= onceki or bas >= sure:
            h.append(f"{ad}: başlangıçlar artan sırada ve videonun içinde olmalı")
            return h
        if son - bas < EN_KISA_SAHNE:
            h.append(f"{ad}: en az {EN_KISA_SAHNE} sn sürmeli")
        onceki = bas

        def icinde(alan, t, a=bas, b=son):
            if not isinstance(t, (int, float)) or not a <= t <= b:
                h.append(f"{ad}: {alan}={t} sahnenin içinde olmalı ({a:.2f}–{b:.2f})")
                return False
            return True

        y = sh.get("yazi")
        if y is not None:
            if not isinstance(y.get("metin"), str) or not y["metin"].strip():
                h.append(f"{ad}: yazi.metin boş")
            elif len(y["metin"]) > YAZI_SINIRI.get(sh["tur"], 0):
                h.append(f"{ad}: yazi.metin en çok {YAZI_SINIRI.get(sh['tur'], 0)} karakter" if sh["tur"] in YAZI_SINIRI
                         else f"{ad}: bu sahnede yazı yok")
            if sh["tur"] != "buyume":  # büyümenin yazısı doruktadır
                icinde("yazi.t", y.get("t"))
        if sh["tur"] == "adimlar":
            z = sh["ziplamalar"]
            if not 1 <= len(z) <= 4:
                h.append(f"{ad}: ziplamalar 1–4 an olmalı")
            for j, t in enumerate(z):
                if icinde(f"ziplamalar[{j}]", t, bas + YUKSELIS_SN, son - ZIPLA_SN) and j and t - z[j - 1] < ZIPLA_SN + 0.12:
                    h.append(f"{ad}: zıplamalar arası en az {ZIPLA_SN + 0.12:.2f} sn")
            if y and "son_t" in y and isinstance(y.get("t"), (int, float)) and y["son_t"] <= y["t"]:
                h.append(f"{ad}: yazi.son_t yazi.t'den sonra olmalı")
        if sh["tur"] == "buyume":
            d = sh.get("doruk_t")
            if icinde("doruk_t", d, bas + 0.8, son - 0.3):
                for j, t in enumerate(sh["kutlama"]):
                    icinde(f"kutlama[{j}]", t, d + 0.3, son - KUTLAMA_SN)
        if sh["tur"] == "karsitlik":
            icinde("vinc_t", sh.get("vinc_t"), bas + 0.2, son - 0.9)
            for j, t in enumerate(sh["kutlama"]):
                icinde(f"kutlama[{j}]", t, bas, son - KUTLAMA_SN)
        if sh["tur"] == "kapanis":
            i_t, z_t = sh.get("inis_t"), sh.get("zipla_t")
            if icinde("inis_t", i_t, bas + 0.15, son - 0.6) and icinde("zipla_t", z_t, bas, son - ZIPLA_SN):
                if z_t < i_t + 0.2:
                    h.append(f"{ad}: zipla_t inişten en az 0,2 sn sonra olmalı")
    # seslendirme: süre içinde, üst üste binmeden
    satirlar = s["seslendirme"].get("satirlar", [])
    ids = [x.get("id") for x in satirlar]
    if len(set(ids)) != len(ids):
        h.append("seslendirme: satır id'leri benzersiz olmalı")
    sureler = sureler or {}
    for a, b in zip(satirlar, satirlar[1:] + [None]):
        if not isinstance(a.get("t"), (int, float)) or not 0 <= a["t"] < sure:
            h.append(f"seslendirme {a.get('id')}: t videonun içinde olmalı")
            continue
        d = sureler.get(a["id"])
        if d is None:
            continue
        if a["t"] + d > sure:
            h.append(f"seslendirme {a['id']}: {d:.2f} sn sürüyor, video bitmeden sığmıyor")
        if b and isinstance(b.get("t"), (int, float)) and a["t"] + d > b["t"]:
            h.append(f"seslendirme {a['id']}: {d:.2f} sn sürüyor, {b['id']} ({b['t']}) ile çakışıyor")
    return h


def cizelge(s: dict) -> dict:
    """sahne.js ve sentez.py'nin ortak okuduğu türetilmiş anlar."""
    a, b = sahne(s, "adimlar"), sahne(s, "buyume")
    n = s["kolonlar"]["adet"]
    z = sorted(a["ziplamalar"])
    n_adim = len(z) + 1
    bas = [-1.0] + [t - 0.35 for t in z]
    d = b["doruk_t"]
    dalga_son = d - 0.45
    for i in range(n_adim, n):
        bas.append(b["bas"] + (dalga_son - b["bas"]) * (i - n_adim) / max(1, n - n_adim - 1))
    k, p = sahne(s, "karsitlik"), sahne(s, "kapanis")
    return {
        "kolon_bas": [round(x, 4) for x in bas],
        "adim_sayisi": n_adim,
        "ziplamalar": z,
        "kosu": [b["bas"] + 0.15, d],
        "doruk": d,
        "kutlama": sorted(b["kutlama"] + (k["kutlama"] if k else [])),
        "karsitlik": k and {"bas": k["bas"], "vinc_t": k["vinc_t"]},
        "kapanis": p and {"bas": p["bas"], "inis_t": p["inis_t"], "zipla_t": p["zipla_t"]},
        "yazilar": {
            "adim": a.get("yazi"),
            "doruk": b.get("yazi") and {**b["yazi"], "t": d, "son_t": p["bas"] if p else s["sure"]},
            "kapanis": p and p.get("yazi"),
        },
        "sahne_sinirlari": [x["bas"] for x in s["sahneler"]] + [s["sure"]],
    }


def akor_bolumleri(s: dict) -> list[tuple[float, float, list[int]]]:
    """(başlangıç, bitiş, akor): adımlar, yükseliş, doruk, karşıtlık (vinçten önce/sonra), kapanış"""
    ak = s["muzik"]["akorlar"]
    c = cizelge(s)
    b = sahne(s, "buyume")
    anlar = [(0.0, ak[0]), (b["bas"], ak[1]), (c["doruk"], ak[2])]
    if c["karsitlik"]:
        anlar += [(c["karsitlik"]["bas"], ak[3]), (c["karsitlik"]["vinc_t"], ak[4])]
    if c["kapanis"]:
        anlar.append((c["kapanis"]["bas"], ak[5]))
    sinir = [t for t, _ in anlar[1:]] + [s["sure"]]
    return [(t, sinir[i], a) for i, (t, a) in enumerate(anlar)]


def enerji(s: dict, t: float) -> float:
    """0..1 müzik dinamiği: sakin giriş → yükseliş → doruk → sakin → parlak kapanış"""
    c = cizelge(s)
    b = sahne(s, "buyume")["bas"]
    d = c["doruk"]
    k = c["karsitlik"]["bas"] if c["karsitlik"] else None
    p = c["kapanis"]["bas"] if c["kapanis"] else None
    if t < b:
        return 0.3
    if t < d:
        return 0.3 + 0.6 * ((t - b) / (d - b)) ** 1.5
    if p is not None and t >= p:
        return 0.85
    if k is not None and t >= k:
        if p is not None and t > p - 0.5:
            return 0.32 + 0.4 * (t - (p - 0.5)) / 0.5
        return 0.32
    return 1.0
