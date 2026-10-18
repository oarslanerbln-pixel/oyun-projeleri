"""Origami şablonunun zaman çizelgesi: origami.json → sahneler, katlanma anları, darbeler, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur; ikisi de aynı anlarda vurur.
Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
from pathlib import Path

TURLER = ("vitrin", "kapanis")
NESNELER = ("kupa", "kutu")
GECISLER = ("kesme", "katla")
ISARETLER = ("turna", "yok")
ROLLER = ("zemin", "koyu", "vurgu", "ikinci", "ucuncu", "acik")
VARSAYILAN_PALET = {"zemin": "#F3ECDF", "koyu": "#22304A", "vurgu": "#E2603F", "ikinci": "#2E8A84",
                    "ucuncu": "#EDB548", "acik": "#FFFBF3"}
KATLANMA_SN = 0.75  # bir nesnenin bütün yüzleri bu sürede açılır
KAYMA_SN = 0.5      # yeni nesne gelince diğerleri yer açar (gelişten 0,25 sn önce başlar)
KATLA_SN = 0.6      # sayfa geçişi: iki kanat sırayla ekranı kaplar, sahne başında biter
ZAMAN_ALANLARI = {  # sahne türü → anlık (saniye) alanları; hepsi sahnenin içinde olmalı
    "vitrin": [],
    "kapanis": ["isaret_t", "alt_t"],
}
NESNE_ZAMANLARI = ("t", "etiket_t", "zipla_t", "one_t", "sonuk_t")


class SenaryoHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s.setdefault("palet", {})
    s["palet"] = {**VARSAYILAN_PALET, **s["palet"]}
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", 96)
    s["muzik"].setdefault("akorlar", [[62, 66, 69, 73], [59, 62, 66, 69], [55, 59, 62, 66], [57, 61, 64, 69]])
    s.setdefault("seslendirme", {"satirlar": []})
    for i, sh in enumerate(s.get("sahneler", [])):
        sh.setdefault("gecis", "kesme" if i == 0 else "katla")
        sh["_son"] = s["sahneler"][i + 1]["bas"] if i + 1 < len(s["sahneler"]) else s.get("sure", 0)
        for n in sh.get("nesneler", []):
            n.setdefault("tur", "kupa"); n.setdefault("boy", 1.0); n.setdefault("renk", "vurgu")
    if "dusus" not in s["muzik"]:  # tam ritmin girdiği an: ilk öne çıkış, yoksa ikinci sahne
        d = [n["one_t"] for sh in s.get("sahneler", []) for n in sh.get("nesneler", []) if "one_t" in n]
        s["muzik"]["dusus"] = min(d) if d else (s["sahneler"][1]["bas"] if len(s.get("sahneler", [])) > 1 else 0)
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
        if i > 0 and sh["gecis"] == "katla" and sh["bas"] - KATLA_SN < onceki:
            h.append(f"{ad}: katla geçişi önceki sahnenin başından önce başlıyor")
        onceki = sh["bas"]
        if sure and sh["bas"] >= sure:
            h.append(f"{ad}: video süresinden sonra başlıyor")
        if sh.get("tur") not in TURLER:
            h.append(f"{ad}: tür {', '.join(TURLER)} olmalı"); continue
        for k in ZAMAN_ALANLARI[sh["tur"]]:
            if k in sh and not (sh["bas"] <= sh[k] < sh["_son"]):
                h.append(f"{ad}: {k}={sh[k]} sahnenin içinde değil ({sh['bas']}–{sh['_son']})")
        if sh["tur"] == "vitrin":
            nes = sh.get("nesneler") or []
            if not 1 <= len(nes) <= 4:
                h.append(f"{ad}: 1–4 nesne gerekli")
            if len({n.get("id") for n in nes}) != len(nes):
                h.append(f"{ad}: nesne kimlikleri (id) benzersiz olmalı")
            for n in nes:
                na = f"{ad} nesne {n.get('id')}"
                if n["tur"] not in NESNELER:
                    h.append(f"{na}: tür {', '.join(NESNELER)} olmalı")
                if n["renk"] not in ROLLER:
                    h.append(f"{na}: renk rolü bilinmiyor")
                if "t" not in n:
                    h.append(f"{na}: t gerekli")
                for k in NESNE_ZAMANLARI:
                    if k in n and not (sh["bas"] <= n[k] < sh["_son"]):
                        h.append(f"{na}: {k}={n[k]} sahnenin içinde değil")
                for k in NESNE_ZAMANLARI[1:]:
                    if k in n and "t" in n and n[k] < n["t"]:
                        h.append(f"{na}: {k} nesne gelmeden önce")
                if not 0.3 <= n["boy"] <= 1.0:
                    h.append(f"{na}: boy 0,3–1,0 arasında olmalı")
            for k in ("baslik", "rozet"):
                if sh.get(k) and not sh[k].get("metin"):
                    h.append(f"{ad}: {k}.metin gerekli")
            if sh.get("baslik") and not (sh["bas"] <= sh["baslik"].get("t", sh["bas"]) < sh["_son"]):
                h.append(f"{ad}: baslik t sahnenin içinde değil")
            rz = sh.get("rozet")
            if rz:
                if not (sh["bas"] <= rz.get("t", -1) < sh["_son"]):
                    h.append(f"{ad}: rozet t sahnenin içinde değil")
        if sh["tur"] == "kapanis":
            if not sh.get("satirlar"):
                h.append(f"{ad}: satirlar gerekli")
            if sh.get("isaret", "turna") not in ISARETLER:
                h.append(f"{ad}: işaret {', '.join(ISARETLER)} olmalı")
            for w in sh.get("satirlar", []):
                if not (sh["bas"] <= w["t"] < sh["_son"]):
                    h.append(f"{ad}: '{w['metin']}' t={w['t']} sahnenin içinde değil")
                if w.get("renk", "acik") not in ROLLER:
                    h.append(f"{ad}: '{w['metin']}' renk rolü bilinmiyor")
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


def ilk_nesneler(sh: dict) -> set[str]:
    """sahne açılırken gelen nesneler (kayma efekti çalmaz)"""
    if not sh.get("nesneler"):
        return set()
    ilk = min(n["t"] for n in sh["nesneler"])
    return {n["id"] for n in sh["nesneler"] if n["t"] - ilk < KAYMA_SN}


def darbeler(s: dict) -> list[tuple[float, float]]:
    """kamera sarsıntısı: (an, şiddet). Ses efektleri de aynı anlarda vurur."""
    d = []
    for i, sh in enumerate(s["sahneler"]):
        if sh["tur"] == "vitrin":
            d += [(n["one_t"], 9) for n in sh["nesneler"] if "one_t" in n]
        if i > 0 and sh["gecis"] == "katla":
            d.append((sh["bas"], 6))
    return d


def ses_olaylari(s: dict) -> list[tuple[float, str, float, float, dict]]:
    """(an, efekt, kazanç, pan, ek) listesi — sentez.py çalar"""
    o = []
    for i, sh in enumerate(s["sahneler"]):
        b = sh["bas"]
        if i > 0 and sh["gecis"] == "katla":
            o.append((b - KATLA_SN, "hisirti", 0.45, 0.4, {"sure": KATLA_SN / 2}))
            o.append((b - KATLA_SN / 2, "hisirti", 0.4, -0.3, {"sure": KATLA_SN / 2}))
            o.append((b, "pat", 0.55, 0.0, {}))
        if sh["tur"] == "vitrin":
            n_ = sh["nesneler"]
            ilk = ilk_nesneler(sh)
            for k, n in enumerate(n_):
                pan = (k - (len(n_) - 1) / 2) * 0.35
                if n["id"] not in ilk:
                    o.append((n["t"] - 0.25, "kayma", 0.3, 0.0, {"sure": KAYMA_SN}))
                o.append((n["t"], "kat", 0.45, pan, {}))
                o.append((n["t"] + 0.3, "kat", 0.32, pan, {}))
                o.append((n["t"] + KATLANMA_SN - 0.05, "tik", 0.3, pan, {"frekans": 1700}))
                if "etiket_t" in n:
                    o.append((n["etiket_t"], "fiske", 0.4, pan, {}))
                if "zipla_t" in n:
                    o.append((n["zipla_t"], "tik", 0.3, pan, {"frekans": 1300}))
                    o.append((n["zipla_t"] + 0.2, "tik", 0.22, pan, {"frekans": 1000}))
                if "one_t" in n:
                    o.append((n["one_t"], "pat", 0.75, pan, {}))
                    o.append((n["one_t"], "parilti", 0.32, 0.0, {}))
                    o.append((n["one_t"] + 0.05, "hisirti", 0.25, 0.0, {"sure": 0.9}))
                    o.append((n["one_t"] + 0.18, "fiske", 0.35, pan, {}))  # etiket döner
                if "sonuk_t" in n:
                    o.append((n["sonuk_t"], "kayma", 0.18, pan, {"sure": 0.4}))
            rz = sh.get("rozet")
            if rz:
                o.append((rz["t"], "kat", 0.4, 0.0, {}))
                o.append((rz["t"] + 0.2, "fiske", 0.35, 0.0, {}))
        elif sh["tur"] == "kapanis":
            if sh.get("isaret", "turna") != "yok":
                t0 = sh.get("isaret_t", b + 0.1)
                for k in range(3):
                    o.append((t0 + k * 0.17, "kat", 0.4, (-0.3, 0.3, 0.0)[k], {}))
            for k, w in enumerate(sh["satirlar"]):
                o.append((w["t"], "fiske", 0.45, -0.2 if k % 2 == 0 else 0.2, {}))
            o.append((sh["satirlar"][-1]["t"] + 0.1, "parilti", 0.3, 0.0, {}))
            if "alt_t" in sh:
                o.append((sh["alt_t"], "tik", 0.25, 0.0, {"frekans": 2200}))
    return sorted(o, key=lambda x: x[0])
