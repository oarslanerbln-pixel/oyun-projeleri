"""Kinetik şablonun zaman çizelgesi: senaryo.json → sahneler, geçişler, darbeler, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur; ikisi de aynı anlarda vurur.
Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

TURLER = ("kelimeler", "buyuk-sayi", "egri", "karsitlik", "kapanis")
GECISLER = ("kesme", "iris", "diyagonal")
ROLLER = ("zemin", "vurgu", "ikinci", "ucuncu", "acik")
VARSAYILAN_PALET = {"zemin": "#15122E", "vurgu": "#FFD23F", "ikinci": "#FF5A5F", "ucuncu": "#3DDC97", "acik": "#FFF8E7"}
# her sahne türünün zemini ve üstündeki ana yazı rengi (palet rolleri)
ZEMIN = {"kelimeler": "zemin", "buyuk-sayi": "vurgu", "egri": "zemin", "karsitlik": "ucuncu", "kapanis": "vurgu"}
IRIS_SN = 0.28          # iris geçişi sahne başından önce bu kadar sürer
DIYAGONAL_GIRIS = 0.20  # mercan perde sahne başına kadar ekranı kaplar ...
DIYAGONAL_CIKIS = 0.30  # ... sonra yeni sahnede çekilir
RISER_SN = 0.55         # diyagonal geçişten önce yükselen ses + yakınlaşma
ZAMAN_ALANLARI = {  # sahne türü → anlık (saniye) alanları; hepsi sahnenin içinde olmalı
    "kelimeler": [],
    "buyuk-sayi": ["ust_t", "sayi_t", "etiket_t"],
    "egri": ["zirve_t"],
    "karsitlik": ["kucuk_t", "panel_t", "buyuk_t"],
    "kapanis": ["cizgi_t", "alt_t"],
}


class SenaryoHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s.setdefault("palet", {})
    s["palet"] = {**VARSAYILAN_PALET, **s["palet"]}
    s.setdefault("ondalik", ",")
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", 120)
    s["muzik"].setdefault("akorlar", [[60, 64, 67, 72], [57, 60, 64, 69], [53, 57, 60, 65], [55, 59, 62, 67]])
    s.setdefault("seslendirme", {"satirlar": []})
    for i, sh in enumerate(s.get("sahneler", [])):
        sh.setdefault("gecis", "kesme" if i == 0 else "iris")
        sh["_son"] = s["sahneler"][i + 1]["bas"] if i + 1 < len(s["sahneler"]) else s.get("sure", 0)
    if "dusus" not in s["muzik"]:  # tam ritmin girdiği an: ilk diyagonal geçiş, yoksa ikinci sahne
        d = [sh["bas"] for sh in s.get("sahneler", [])[1:] if sh["gecis"] == "diyagonal"]
        s["muzik"]["dusus"] = d[0] if d else (s["sahneler"][1]["bas"] if len(s.get("sahneler", [])) > 1 else 0)
    return s


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    """HATA listesi; boşsa senaryo render'a hazır. `sureler`: seslendirme satırı → saniye (seslendirme.json)."""
    h = []
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or sure <= 0:
        h.append("sure (saniye) eksik ya da geçersiz")
        sure = 0
    for r, v in s["palet"].items():
        if r not in ROLLER:
            h.append(f"palet: bilinmeyen rol {r}")
        elif not (isinstance(v, str) and v.startswith("#") and len(v) == 7):
            h.append(f"palet.{r}: #RRGGBB olmalı")
    sahneler = s.get("sahneler") or []
    if not sahneler:
        h.append("sahneler boş")
    onceki = -1.0
    for i, sh in enumerate(sahneler):
        ad = f"sahne {i + 1} ({sh.get('tur')})"
        if sh["gecis"] not in GECISLER:
            h.append(f"{ad}: geçiş {', '.join(GECISLER)} olmalı")
        if i == 0 and sh["bas"] != 0:
            h.append(f"{ad}: ilk sahne 0'da başlamalı")
        if sh["bas"] <= onceki:
            h.append(f"{ad}: başlangıçlar artan sırada olmalı")
        onceki = sh["bas"]
        if sure and sh["bas"] >= sure:
            h.append(f"{ad}: video süresinden sonra başlıyor")
        if sh.get("tur") not in TURLER:
            h.append(f"{ad}: tür {', '.join(TURLER)} olmalı"); continue
        for k in ZAMAN_ALANLARI[sh["tur"]]:
            if k in sh and not (sh["bas"] <= sh[k] < sh["_son"]):
                h.append(f"{ad}: {k}={sh[k]} sahnenin içinde değil ({sh['bas']}–{sh['_son']})")
        if sh.get("gorsel"):
            g = sh["gorsel"]
            if sh["tur"] != "kelimeler":
                h.append(f"{ad}: gorsel yalnız `kelimeler` sahnesinde kullanılır")
            elif not (Path(s["_klasor"]) / g.get("dosya", "")).is_file():
                h.append(f"{ad}: gorsel.dosya bulunamadı: {g.get('dosya')}")
            elif not (isinstance(g.get("t"), (int, float)) and sh["bas"] <= g["t"] < sh["_son"]):
                h.append(f"{ad}: gorsel.t sahnenin içinde olmalı")
        if sh.get("logo") and not (Path(s["_klasor"]) / sh["logo"].get("dosya", "")).is_file():
            h.append(f"{ad}: logo.dosya bulunamadı: {sh['logo'].get('dosya')}")
        for k in ("kelimeler", "satirlar"):
            for w in sh.get(k, []):
                if not (sh["bas"] <= w["t"] < sh["_son"]):
                    h.append(f"{ad}: '{w['metin']}' t={w['t']} sahnenin içinde değil")
                if w.get("renk", "acik") not in ROLLER:
                    h.append(f"{ad}: '{w['metin']}' renk rolü bilinmiyor")
        gerekli = {"kelimeler": ["kelimeler"], "buyuk-sayi": ["sayi", "sayi_t"], "egri": ["zirve_t"],
                   "karsitlik": ["kucuk", "buyuk", "kucuk_t", "buyuk_t"], "kapanis": ["satirlar"]}[sh["tur"]]
        for k in gerekli:
            if not sh.get(k):
                h.append(f"{ad}: {k} gerekli")
        if sh["tur"] == "egri" and sh.get("zirve_t", 0) - sh["bas"] < 0.8:
            h.append(f"{ad}: eğrinin çizilmesi için en az 0,8 sn gerekir")
    satirlar = s["seslendirme"].get("satirlar", [])
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


def sahne_at(s: dict, t: float) -> int:
    i = 0
    for k, sh in enumerate(s["sahneler"]):
        if t >= sh["bas"]:
            i = k
    return i


def egri(x: float, oran: float = 0.01, gun: int = 365) -> float:
    """bileşik büyüme 0..1 → 0..1"""
    tavan = (1 + oran) ** gun - 1
    return ((1 + oran) ** (gun * x) - 1) / tavan if tavan else x


def egri_baslangic(sh: dict) -> float:
    return sh.get("baslangic_t", sh["bas"] + 0.15)


def darbeler(s: dict) -> list[tuple[float, float]]:
    """kamera sarsıntısı: (an, şiddet). Ses efektleri de aynı anlarda vurur."""
    d = []
    for i, sh in enumerate(s["sahneler"]):
        tur = sh["tur"]
        if i == 0 and sh.get("acilis", True):
            d.append((0.02, 6))
        if tur == "kelimeler":
            d += [(w["t"], 10) for w in sh["kelimeler"]]
        elif tur == "buyuk-sayi":
            d.append((sh["sayi_t"], 26))
        elif tur == "egri":
            d += [(sh["bas"], 14), (sh["zirve_t"], 30)]
        elif tur == "karsitlik":
            d.append((sh["buyuk_t"], 30))
        elif tur == "kapanis":
            d += [(w["t"], 12 if k < len(sh["satirlar"]) - 1 else 22) for k, w in enumerate(sh["satirlar"])]
    return d


def ses_olaylari(s: dict) -> list[tuple[float, str, float, float, dict]]:
    """(an, efekt, kazanç, pan, ek) listesi — sentez.py çalar"""
    o = []
    sh_ = s["sahneler"]
    for i, sh in enumerate(sh_):
        tur, b = sh["tur"], sh["bas"]
        if i > 0 and sh["gecis"] == "iris":
            o.append((b - IRIS_SN - 0.05, "whoosh", 0.38, 0.0, {}))
        if i > 0 and sh["gecis"] == "diyagonal":
            o.append((b - RISER_SN, "riser", 0.45, 0.0, {"sure": RISER_SN}))
            o.append((b - DIYAGONAL_GIRIS, "whoosh", 0.45, 0.5, {}))
        if i == 0 and sh.get("acilis", True):
            o.append((0.02, "pop", 0.5, 0.0, {}))
        if tur == "kelimeler":
            for k, w in enumerate(sh["kelimeler"]):
                o.append((w["t"], "slam", 0.35, -0.2 if k % 2 == 0 else 0.2, {}))
        elif tur == "buyuk-sayi":
            if sh.get("ust"):
                o.append((sh.get("ust_t", b + 0.05), "pop", 0.25, 0.3, {}))
            o.append((sh["sayi_t"], "boom", 0.85, 0.0, {}))
            if sh.get("etiket"):
                o.append((sh.get("etiket_t", sh["sayi_t"] + 0.5), "whoosh-in", 0.3, -0.4, {"sure": 0.25}))
        elif tur == "egri":
            t0, t1 = egri_baslangic(sh), sh["zirve_t"]
            o.append((b, "boom", 0.6, 0.0, {"sure": 0.7}))
            o.append((t0, "whoosh", 0.15, 0.0, {"sure": t1 - t0}))
            oran, gun = sh.get("oran", 0.01), sh.get("gun", 365)
            tepe = (1 + oran) ** gun
            adim = max(1, int(tepe / 40))
            son = -1
            for k in range(400):  # sayaç tıkları: eğri büyüdükçe hızlanır ve tizleşir
                tt = t0 + (t1 - t0) * k / 400
                v = int(((1 + oran) ** (gun * _in_out_cubic(k / 400))) / adim)
                if v != son and tt < t1:
                    o.append((tt, "tick", 0.22, 0.2 * math.sin(k), {"frekans": 900 + min(v, 40) * 45}))
                    son = v
            o.append((t1, "boom", 0.9, 0.0, {"sure": 1.0}))
            o.append((t1, "sparkle", 0.3, 0.0, {}))
        elif tur == "karsitlik":
            o.append((sh["kucuk_t"], "pop", 0.4, 0.0, {}))
            o.append((sh.get("panel_t", sh["buyuk_t"] - 0.18) - 0.1, "whoosh", 0.4, -0.3, {}))
            o.append((sh["buyuk_t"], "slam", 0.6, 0.0, {}))
            o.append((sh["buyuk_t"], "boom", 0.6, 0.0, {"sure": 1.0}))
        elif tur == "kapanis":
            for k, w in enumerate(sh["satirlar"]):
                o.append((w["t"], "slam", 0.4 if k < len(sh["satirlar"]) - 1 else 0.5, -0.2 if k % 2 == 0 else 0.2, {}))
            o.append((sh["satirlar"][-1]["t"], "sparkle", 0.3, 0.0, {}))
            if "cizgi_t" in sh:
                o.append((sh["cizgi_t"], "whoosh", 0.25, 0.4, {"sure": 0.25}))
    return sorted(o, key=lambda x: x[0])


def davul_bosluklari(s: dict) -> list[tuple[float, float]]:
    """geçişlerden hemen önce kick ve bas susar; geçiş daha sert vurur"""
    b = []
    for i, sh in enumerate(s["sahneler"][1:], 1):
        if sh["gecis"] == "diyagonal":
            b.append((sh["bas"] - 0.5, sh["bas"]))
        elif sh["gecis"] == "iris" and sh["bas"] > s["muzik"]["dusus"]:
            b.append((sh["bas"] - 0.25, sh["bas"]))
    return b


def _in_out_cubic(p: float) -> float:
    return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
