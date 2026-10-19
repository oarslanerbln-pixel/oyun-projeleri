"""Ekran stilleri (kalkış tabelası, VHS, akış alanı) için ortak senaryo: yükleme, varsayılanlar, denetim.

Üç stil aynı senaryo biçimini kullanır; yalnız `stil` alanı değişir, bir video içerik değişmeden stil
değiştirebilir. Sahne = birkaç kelimelik ana metin (+ isteğe bağlı küçük alt satır). `*kelime*` vurgu rengiyle
yazılır, `\\n` satırı zorla böler. Görüntü (`cizim.py`) ve ses (`sentez.py`) anları yalnız buradan okur.
Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

STILLER = ("kalkis-tabelasi", "vhs", "akis-alani")
FORMATLAR = ("9x16", "16x9", "1x1", "4x5")
SURE = (4.0, 30.0)
SAHNE_EN_KISA = 1.5
# stil → (ana metin en çok karakter, alt satır en çok karakter)
SINIR = {"kalkis-tabelasi": (48, 18), "vhs": (40, 48), "akis-alani": (40, 60)}
VARSAYILAN_PALET = {
    "kalkis-tabelasi": {"zemin": "#111214", "kasa": "#1B1C1F", "hucre": "#26272B", "harf": "#F3EEDF",
                        "vurgu": "#FFC233", "ayrac": "#0A0A0B", "etiket": "#FFC233"},
    "vhs": {"zemin": "#15102C", "metin": "#F4F1FF", "vurgu": "#FF3EA5", "ikincil": "#2EE6D6", "osd": "#FFFFFF"},
    "akis-alani": {"zemin": "#0D1B2A", "cizgi": "#5FA8D3", "cizgi2": "#E8D8B0", "vurgu": "#F2B134", "metin": "#F7F3EA"},
}
AKIS_KAGIT = {"zemin": "#F4EEDC", "cizgi": "#1F3A5F", "cizgi2": "#8C6A43", "vurgu": "#C8553D", "metin": "#14213D"}
TEMALAR = ("gece", "kagit")
VARSAYILAN_BPM = {"kalkis-tabelasi": 96, "vhs": 108, "akis-alani": 72}
# kalkış tabelasının hücre ızgarası (sütun, satır) ve alt şeridin sütun sayısı
IZGARA = {"9x16": (10, 6, 18), "16x9": (18, 4, 30), "1x1": (12, 5, 22), "4x5": (11, 6, 20)}
# yazının kaçınması gereken kenar payları (üst, alt, yan) — 9:16'da Reels arayüzü alttan %22'yi kaplar
GUVENLI = {"9x16": (0.10, 0.22, 0.08), "16x9": (0.08, 0.10, 0.07), "1x1": (0.07, 0.09, 0.07), "4x5": (0.08, 0.10, 0.08)}
# kalkış tabelasının harf dizisi: hücre hedefe gelene kadar bu sırayla döner
ALFABE = " ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVWXYZ0123456789%.,:!?-+&/'·"


class SenaryoHatasi(ValueError):
    pass


def tr_buyuk(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


def parcala(metin: str) -> list[list[tuple[str, bool]]]:
    """'Her gün *%1* daha\\niyi' → satırlar; her satır (kelime, vurgu) listesi. Satır sonu yalnız \\n ile zorlanır."""
    out = []
    for satir in metin.split("\n"):
        kelimeler = []
        vurgu = False
        for parca in re.split(r"(\*)", satir):
            if parca == "*":
                vurgu = not vurgu
                continue
            if vurgu and parca.strip():  # vurgulu öbek bölünmez: "*37 kat*" aynı satırda kalır
                kelimeler.append((" ".join(parca.split()), True))
            else:
                kelimeler += [(k, vurgu) for k in parca.split()]
        out.append(kelimeler)
    return out


def duz(metin: str) -> str:
    return metin.replace("*", "").replace("\n", " ")


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s.setdefault("dil", "tr")
    s.setdefault("tema", "gece")
    st = s.get("stil", "kalkis-tabelasi")
    temel = AKIS_KAGIT if st == "akis-alani" and s["tema"] == "kagit" else VARSAYILAN_PALET.get(st, {})
    s["palet"] = {**temel, **s.get("palet", {})}
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", VARSAYILAN_BPM.get(st, 100))
    s.setdefault("seslendirme", {"satirlar": []})
    s["seslendirme"].setdefault("satirlar", [])
    sure = s.get("sure") if isinstance(s.get("sure"), (int, float)) else 0
    shs = s.get("sahneler") or []
    for i, sh in enumerate(shs):
        sh.setdefault("bas", 0.0 if i == 0 else None)
        sh.setdefault("alt", "")
        sh["_son"] = shs[i + 1].get("bas") if i + 1 < len(shs) else sure
    return s


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    """HATA listesi; boşsa senaryo render'a hazır. `sureler`: seslendirme satırı → saniye (seslendirme.json)."""
    h = []
    st = s.get("stil")
    if st not in STILLER:
        return [f"stil: {', '.join(STILLER)} olmalı"]
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or not SURE[0] <= sure <= SURE[1]:
        h.append(f"sure: {SURE[0]:g}–{SURE[1]:g} sn olmalı")
        sure = 0
    if s.get("format", "9x16") not in FORMATLAR:
        h.append(f"format: {', '.join(FORMATLAR)} olmalı")
    if not isinstance(s["fps"], int) or not 24 <= s["fps"] <= 60:
        h.append("fps 24–60 arasında tam sayı olmalı")
    if s["tema"] not in TEMALAR:
        h.append(f"tema: {', '.join(TEMALAR)} olmalı")
    for r, v in s["palet"].items():
        if r not in VARSAYILAN_PALET[st]:
            h.append(f"palet: {st} için bilinmeyen rol {r} ({', '.join(VARSAYILAN_PALET[st])})")
        elif not (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)):
            h.append(f"palet.{r}: #RRGGBB olmalı")
    bpm = s["muzik"].get("bpm")
    if not isinstance(bpm, (int, float)) or not 60 <= bpm <= 160:
        h.append("muzik.bpm 60–160 arasında olmalı")
    shs = s.get("sahneler") or []
    if not shs:
        h.append("sahneler: en az bir sahne gerekli")
    if len(shs) > 8:
        h.append("sahneler: en çok 8 sahne (daha uzun video için kurgu şablonu)")
    ana, alt = SINIR[st]
    onceki = None
    for i, sh in enumerate(shs):
        ad = f"sahne {i + 1}"
        m = sh.get("metin")
        if not isinstance(m, str) or not duz(m).strip():
            h.append(f"{ad}: metin boş")
            continue
        if m.count("*") % 2:
            h.append(f"{ad}: vurgu yıldızları (*) çift olmalı")
        if len(duz(m)) > ana:
            h.append(f"{ad}: metin {len(duz(m))} karakter, {st} için en çok {ana} (az yazı kuralı)")
        if not isinstance(sh.get("alt", ""), str) or len(sh.get("alt", "")) > alt:
            h.append(f"{ad}: alt satır en çok {alt} karakter")
        b = sh.get("bas")
        if not isinstance(b, (int, float)):
            h.append(f"{ad}: bas (saniye) eksik")
            continue
        if i == 0 and b != 0:
            h.append(f"{ad}: ilk sahne 0'da başlamalı")
        if onceki is not None and b - onceki < SAHNE_EN_KISA:
            h.append(f"{ad}: önceki sahneden en az {SAHNE_EN_KISA:g} sn sonra başlamalı")
        if sure and b > sure - SAHNE_EN_KISA:
            h.append(f"{ad}: video bitmeden en az {SAHNE_EN_KISA:g} sn görünmeli")
        onceki = b
        if st == "kalkis-tabelasi":
            h += _tabela_denetle(ad, sh)
    satirlar = s["seslendirme"]["satirlar"]
    for x in satirlar:
        if not {"id", "t", "metin"} <= set(x):
            h.append("seslendirme: her satırda id, t, metin olmalı")
            return h
    for a, b in zip(satirlar, satirlar[1:]):
        if b["t"] <= a["t"]:
            h.append(f"seslendirme: {b['id']} {a['id']}'den sonra başlamalı")
        elif sureler and a["id"] in sureler and a["t"] + sureler[a["id"]] > b["t"] + 0.05:
            h.append(f"seslendirme: {a['id']} ({sureler[a['id']]:.2f} sn) {b['id']} başlamadan bitmiyor")
    if satirlar and sureler and sure:
        z = satirlar[-1]
        if z["id"] in sureler and z["t"] + sureler[z["id"]] > sure:
            h.append(f"seslendirme: {z['id']} video bitince hâlâ konuşuyor")
    return h


def tabela_satirlari(metin: str, sutun: int) -> list[list[tuple[str, bool]]] | None:
    """Kelimeleri tabela satırlarına yerleştirir (kelime bölünmez). Sığmazsa None."""
    out = []
    for satir in parcala(tr_buyuk(metin)):
        cur, n = [], 0
        for k, v in satir:
            if len(k) > sutun:
                return None
            ek = len(k) + (1 if cur else 0)
            if n + ek > sutun:
                out.append(cur); cur, n = [], 0; ek = len(k)
            cur.append((k, v)); n += ek
        out.append(cur)
    return out


def _tabela_denetle(ad: str, sh: dict) -> list[str]:
    h = []
    for k in duz(tr_buyuk(sh["metin"] + " " + sh.get("alt", ""))):
        if k not in ALFABE:
            return [f"{ad}: '{k}' tabelada yok ({ALFABE.strip()})"]
    for f in FORMATLAR:  # her formatta sığmalı: aynı senaryo başka formatta da render edilebilir
        su, sa, al = IZGARA[f]
        sat = tabela_satirlari(sh["metin"], su)
        if sat is None:
            h.append(f"{ad}: bir kelime {f} tabelasının {su} hücresine sığmıyor")
        elif len(sat) > sa:
            h.append(f"{ad}: metin {f} tabelasında {len(sat)} satır tutuyor, en çok {sa}")
        elif len(sh.get("alt", "")) > al:
            h.append(f"{ad}: alt satır {f} şeridine ({al} hücre) sığmıyor")
        if h:
            break
    return h
