"""Gölge oyunu şablonunun zaman çizelgesi: golge-oyunu.json → sahneler, varsayılanlar, denetim, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) anları yalnız buradan okur. Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
from pathlib import Path

FORMATLAR = ("9x16", "16x9", "1x1", "4x5")
TURLER = ("yuruyus", "merdiven", "agac", "kapanis")
GECISLER = ("lale", "kesme")
MUZIK_KIPLERI = ("taksim", "ritim", "sakin")
ROLLER = ("perde", "isik", "cerceve", "cerceve_cizgi", "kontur", "govde", "vurgu", "altin", "lacivert", "ten",
          "turuncu", "yaprak", "toprak", "gece")
VARSAYILAN_PALET = {
    "perde": "#F2DDB0", "isik": "#FFF4DA", "cerceve": "#2B1A10", "cerceve_cizgi": "#A8742F", "kontur": "#3B2416",
    "govde": "#2E7D4F", "vurgu": "#B83A2E", "altin": "#C98B2B", "lacivert": "#34477A", "ten": "#E0A15E",
    "turuncu": "#E08A2E", "yaprak": "#3F8F4F", "toprak": "#7A8F3A", "gece": "#1A0F08",
}
KUKLA_PARCALARI = ("entari", "kusak", "kulah", "kol", "bacak", "pabuc", "ten")
VARSAYILAN_KUKLA = {"entari": "govde", "kusak": "altin", "kulah": "vurgu", "kol": "altin", "bacak": "lacivert",
                    "pabuc": "vurgu", "ten": "ten"}
MAKAMLAR = {  # Re üzerinde sekiz ses (MIDI); mikro aralıklar yerine en yakın yarım ses
    "hicaz": [62, 63, 66, 67, 69, 70, 72, 74],
    "kurdi": [62, 63, 65, 67, 69, 70, 72, 74],
    "nihavent": [62, 64, 65, 67, 69, 70, 73, 74],
    "rast": [62, 64, 66, 67, 69, 71, 72, 74],
}
YURUME_SN = 1.5      # kahramanın sahneye yürüyüşü
GECIS_SN = 0.4       # lale geçişi sahne başından bu kadar önce başlar, bu kadar sonra biter
BASAMAK_ARALIK = 0.13
VARSAYILAN_KIP = {"yuruyus": "taksim", "merdiven": "ritim", "agac": "sakin", "kapanis": "ritim"}
ZAMAN_ALANLARI = {  # sahne türü → anlık (saniye) alanları; hepsi sahnenin içinde olmalı
    "yuruyus": ["giris_t", "kol_t"],
    "merdiven": ["t", "tirman_t", "zafer_t"],
    "agac": ["filiz_t", "t"],
    "kapanis": ["bayrak_t", "kol_t"],
}
ZORUNLU = {"yuruyus": ["giris_t"], "merdiven": ["t", "tirman_t"], "agac": ["t"], "kapanis": []}


class SenaryoHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s["palet"] = {**VARSAYILAN_PALET, **s.get("palet", {})}
    s["kukla"] = {**VARSAYILAN_KUKLA, **s.get("kukla", {})}
    s.setdefault("gul", True)
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", 100)
    s["muzik"].setdefault("makam", "hicaz")
    s["muzik"].setdefault("nareke", True)
    s.setdefault("seslendirme", {"satirlar": []})
    sahneler = s.get("sahneler", [])
    for i, sh in enumerate(sahneler):
        sh.setdefault("gecis", "kesme" if i == 0 else "lale")
        sh.setdefault("muzik", VARSAYILAN_KIP.get(sh.get("tur"), "ritim"))
        sh["_son"] = sahneler[i + 1]["bas"] if i + 1 < len(sahneler) else s.get("sure", 0)
        sh["_sira"] = i
        if sh.get("tur") == "merdiven":
            sh.setdefault("basamak", 7)
            sh.setdefault("tirman_sure", 1.0)
        if sh.get("levha"):
            sh["levha"].setdefault("renk", "vurgu" if i == len(sahneler) - 1 else "altin")
            sh["levha"].setdefault("zil", i > 0)
    return s


def gecis_anlari(s: dict) -> list[float]:
    return [sh["bas"] for sh in s["sahneler"][1:] if sh["gecis"] == "lale"]


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
    for p, r in s["kukla"].items():
        if p not in KUKLA_PARCALARI:
            h.append(f"kukla: bilinmeyen parça {p} ({', '.join(KUKLA_PARCALARI)})")
        elif r not in ROLLER:
            h.append(f"kukla.{p}: renk rolü bilinmiyor ({r})")
    if s.get("format", "9x16") not in FORMATLAR:
        h.append(f"format: {', '.join(FORMATLAR)} olmalı")
    if s["muzik"]["makam"] not in MAKAMLAR:
        h.append(f"muzik.makam: {', '.join(MAKAMLAR)} olmalı")
    sahneler = s.get("sahneler") or []
    if not sahneler:
        h.append("sahneler boş")
    onceki = -1.0
    for i, sh in enumerate(sahneler):
        ad = f"sahne {i + 1} ({sh.get('tur')})"
        if not isinstance(sh.get("bas"), (int, float)):
            h.append(f"{ad}: bas (saniye) gerekli"); continue
        if i == 0 and sh["bas"] != 0:
            h.append(f"{ad}: ilk sahne 0'da başlamalı")
        if sh["bas"] <= onceki:
            h.append(f"{ad}: başlangıçlar artan sırada olmalı")
        if sh["gecis"] not in GECISLER:
            h.append(f"{ad}: geçiş {', '.join(GECISLER)} olmalı")
        elif i > 0 and sh["gecis"] == "lale" and sh["bas"] - GECIS_SN <= onceki:
            h.append(f"{ad}: lale geçişi önceki sahnenin başından önce başlıyor")
        onceki = sh["bas"]
        if sure and sh["bas"] >= sure:
            h.append(f"{ad}: video süresinden sonra başlıyor")
        if sh["muzik"] not in MUZIK_KIPLERI:
            h.append(f"{ad}: muzik {', '.join(MUZIK_KIPLERI)} olmalı")
        if sh.get("tur") not in TURLER:
            h.append(f"{ad}: tür {', '.join(TURLER)} olmalı"); continue
        for k in ZORUNLU[sh["tur"]]:
            if k not in sh:
                h.append(f"{ad}: {k} gerekli")
        for k in ZAMAN_ALANLARI[sh["tur"]]:
            if k in sh and not (sh["bas"] <= sh[k] < sh["_son"]):
                h.append(f"{ad}: {k}={sh[k]} sahnenin içinde değil ({sh['bas']}–{sh['_son']})")
        lv = sh.get("levha")
        if lv:
            if not str(lv.get("metin", "")).strip():
                h.append(f"{ad}: levha.metin gerekli")
            if not (sh["bas"] <= lv.get("t", -1) < sh["_son"]):
                h.append(f"{ad}: levha.t sahnenin içinde değil")
            if lv["renk"] not in ROLLER:
                h.append(f"{ad}: levha.renk rolü bilinmiyor")
        if sh["tur"] == "merdiven":
            if not (isinstance(sh["basamak"], int) and 3 <= sh["basamak"] <= 10):
                h.append(f"{ad}: basamak 3–10 arasında tam sayı olmalı")
            elif "t" in sh and "tirman_t" in sh:
                if sh["tirman_t"] < sh["t"]:
                    h.append(f"{ad}: tirman_t merdiven kurulmadan önce")
                if sh["tirman_t"] + sh["tirman_sure"] > sh["_son"]:
                    h.append(f"{ad}: tırmanış sahne bitmeden tamamlanmıyor")
        if sh["tur"] == "agac" and "filiz_t" in sh and "t" in sh and sh["filiz_t"] > sh["t"]:
            h.append(f"{ad}: filiz_t ağacın büyümesinden (t) önce olmalı")
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


def ses_olaylari(s: dict) -> list[tuple[float, str, dict]]:
    """(an, olay, ayrıntı) listesi, zamana göre sıralı. Efektler buradan üretilir."""
    o = []
    if s["muzik"]["nareke"]:
        o.append((0.05, "nareke", {}))
    for ts in gecis_anlari(s):
        o.append((ts - GECIS_SN, "hisirti", {"sure": 2 * GECIS_SN, "kazanc": 0.6}))
    for sh in s["sahneler"]:
        lv = sh.get("levha")
        if lv:
            if lv["zil"]:
                o.append((lv["t"] + 0.45, "zil", {}))
            o.append((lv["t"] + 0.4, "tahta", {"f": 1000, "kazanc": 0.75}))
        tur = sh["tur"]
        if tur == "merdiven":
            n = sh["basamak"]
            for i in range(n):
                o.append((sh["t"] + i * BASAMAK_ARALIK + 0.2, "tahta", {"f": 500 + i * 70, "kazanc": 0.55, "pan": -0.4 + 0.8 * i / max(1, n - 1)}))
            for i in range(n - 1):
                o.append((sh["tirman_t"] + (i + 1) * sh["tirman_sure"] / (n - 1) - 0.02, "tahta", {"f": 700, "kazanc": 0.35}))
        elif tur == "agac":
            if "filiz_t" in sh:
                o.append((sh["filiz_t"] + 0.1, "hisirti", {"sure": 0.3, "kazanc": 0.4}))
            for i in range(6):
                o.append((sh["t"] + 0.1 + i * 0.12, "hisirti", {"sure": 0.12, "kazanc": 0.35}))
        elif tur == "kapanis" and "bayrak_t" in sh:
            o.append((sh["bayrak_t"] + 0.4, "tahta", {"f": 800, "kazanc": 0.6}))
    return sorted(o, key=lambda x: x[0])
