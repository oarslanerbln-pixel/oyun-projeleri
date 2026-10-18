"""Kolaj şablonunun zaman çizelgesi: senaryo.json → sahneler, geçişler, harf anları, darbeler, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur; ikisi de aynı anlarda vurur.
Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
from pathlib import Path

TURLER = ("fis", "esitlik", "kapanis")
GECISLER = ("kesme", "yirt", "kaydir")
NESNELER = ("bardak", "kupa", "simit", "cekirdek", "kase", "tabak")
ROLLER = ("zemin", "kagit", "gazete", "murekkep", "vurgu", "ikinci", "marka")
VARSAYILAN_PALET = {"zemin": "#C9A67A", "kagit": "#FBF8F1", "gazete": "#E9E3D5", "murekkep": "#221A16",
                    "vurgu": "#D63A2C", "ikinci": "#E0A243", "marka": "#3B2418"}
ADIM_FPS = 15        # stop-motion: hareketler saniyede 15 adımda ilerler (30 fps'te "ikişerli")
YIRT_SN = 0.45       # yırtılan sayfanın iki yarısı ekrandan bu sürede çıkar
KAYDIR_SN = 0.30     # yeni sayfa alttan bu sürede kayarak gelir (sahne başından önce başlar)
HARF_ARALIK = 0.055  # `son` verilmezse harfler bu aralıkla düşer
# sahne türü → anlık (saniye) alanları; hepsi sahnenin içinde olmalı. "a.b" iç içe alan demek.
ZAMAN_ALANLARI = {
    "fis": ["nesne.t", "kalem_t", "kalem_son", "toplam_t", "cember_t", "damga.t", "damga.son"],
    "esitlik": ["nesne.t", "ust.t", "ust.son", "esit_t", "alt.t", "alt.son", "nesne2.t", "cizgi_t"],
    "kapanis": ["logo.t", "marka.t", "marka.son", "alt.t", "nesne.t", "damga_t"],
}


class SenaryoHatasi(ValueError):
    pass


def al(sh: dict, alan: str):
    v = sh
    for k in alan.split("."):
        if not isinstance(v, dict) or k not in v:
            return None
        v = v[k]
    return v


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s["palet"] = {**VARSAYILAN_PALET, **s.get("palet", {})}
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", 100)
    s["muzik"].setdefault("akorlar", [[53, 57, 60, 65], [50, 53, 57, 62], [46, 50, 53, 58], [48, 52, 55, 60]])
    s.setdefault("seslendirme", {"satirlar": []})
    sahneler = s.get("sahneler", [])
    for i, sh in enumerate(sahneler):
        sh.setdefault("gecis", "kesme" if i == 0 else "yirt")
        sh["_son"] = sahneler[i + 1]["bas"] if i + 1 < len(sahneler) else s.get("sure", 0)
    m = s["muzik"]
    if "dusus" not in m:  # tam ritim ikinci sahneyle girer
        m["dusus"] = sahneler[1]["bas"] if len(sahneler) > 1 else 0
    if "zirve" not in m:  # zirve: ikinci nesnenin çarptığı an (varsa)
        z = [al(sh, "nesne2.t") for sh in sahneler if al(sh, "nesne2.t") is not None]
        m["zirve"] = z[0] if z else None
    if "sakin" not in m:  # zirveden kapanışa kadar davul susar
        k = [sh["bas"] for sh in sahneler if sh.get("tur") == "kapanis"]
        m["sakin"] = [m["zirve"] + 0.8, k[0]] if m["zirve"] is not None and k and k[0] > m["zirve"] + 0.8 else None
    return s


def harf_anlari(yazi: dict | None) -> list[float]:
    """Kesik harf yazısında boşluk olmayan her harfin düştüğü an (t → son arasına eşit dağılır)."""
    if not yazi:
        return []
    n = sum(1 for c in yazi["metin"] if not c.isspace())
    if n == 0:
        return []
    t0 = yazi["t"]
    son = yazi.get("son", t0 + HARF_ARALIK * (n - 1))
    return [t0 + (son - t0) * i / max(1, n - 1) for i in range(n)]


def kelime_anlari(yazi: dict | None) -> list[float]:
    """Marka yazısında her kelimenin (ayrı kâğıt şerit) yapıştığı an."""
    if not yazi:
        return []
    n = len(yazi["metin"].split())
    t0 = yazi["t"]
    son = yazi.get("son", t0 + 0.3 * (n - 1))
    return [t0 + (son - t0) * i / max(1, n - 1) for i in range(n)]


def kalem_anlari(sh: dict) -> list[float]:
    k = sh.get("kalemler") or []
    t0, son = sh.get("kalem_t", sh["bas"] + 0.3), sh.get("kalem_son", sh["bas"] + 1.8)
    return [t0 + (son - t0) * i / max(1, len(k) - 1) for i in range(len(k))]


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
        if sh.get("tur") not in TURLER:
            h.append(f"{ad}: tür {', '.join(TURLER)} olmalı")
            continue
        if sh["gecis"] not in GECISLER:
            h.append(f"{ad}: geçiş {', '.join(GECISLER)} olmalı")
        if i == 0 and sh["bas"] != 0:
            h.append(f"{ad}: ilk sahne 0'da başlamalı")
        if sh["bas"] <= onceki:
            h.append(f"{ad}: başlangıçlar artan sırada olmalı")
        onceki = sh["bas"]
        for alan in ZAMAN_ALANLARI[sh["tur"]]:
            v = al(sh, alan)
            if v is None:
                continue
            if not isinstance(v, (int, float)):
                h.append(f"{ad}: {alan} sayı olmalı")
            elif not sh["bas"] <= v < sh["_son"]:
                h.append(f"{ad}: {alan}={v} sahnenin dışında ({sh['bas']}–{sh['_son']})")
        lg = sh.get("logo")
        if lg is not None and not (Path(s["_klasor"]) / lg.get("gorsel", "")).is_file():
            h.append(f"{ad}: logo.gorsel bulunamadı: {lg.get('gorsel')}")
        for k in ("nesne", "nesne2"):
            n = sh.get(k)
            if n is None:
                continue
            if n.get("gorsel"):
                if not (Path(s["_klasor"]) / n["gorsel"]).exists():
                    h.append(f"{ad}: {k}.gorsel bulunamadı: {n['gorsel']}")
            elif n.get("tur") not in NESNELER:
                h.append(f"{ad}: {k}.tur {', '.join(NESNELER)} olmalı (ya da gorsel: dosya.png)")
        for j, kalem in enumerate(sh.get("kalemler") or []):
            if not (isinstance(kalem, str) or (isinstance(kalem, list) and len(kalem) == 2 and all(isinstance(x, str) for x in kalem))):
                h.append(f"{ad}: kalemler[{j}] \"METİN\" ya da [\"METİN\", \"FİYAT\"] olmalı")
        if sh.get("isaret", "=") not in ("=", "+"):
            h.append(f"{ad}: isaret '=' ya da '+' olmalı")
        for k in ("ust", "alt", "damga", "marka"):
            y = sh.get(k)
            if isinstance(y, dict) and "son" in y and y["son"] < y.get("t", 0):
                h.append(f"{ad}: {k}.son, {k}.t'den önce olamaz")
    satirlar = sorted(s["seslendirme"].get("satirlar", []), key=lambda x: x.get("t", 0))
    for j, x in enumerate(satirlar):
        if not {"id", "t", "metin"} <= x.keys():
            h.append(f"seslendirme: her satırda id, t, metin olmalı ({x})")
            continue
        if sureler and x["id"] in sureler:
            bitis = x["t"] + sureler[x["id"]]
            sinir = satirlar[j + 1]["t"] if j + 1 < len(satirlar) else sure
            if bitis > sinir + 1e-6:
                h.append(f"seslendirme {x['id']}: {bitis:.2f} sn'de bitiyor, {sinir:.2f} sn'den önce bitmeli")
    return h


def adim(t: float) -> float:
    """Stop-motion zamanı: hareketler 1/ADIM_FPS'lik basamaklarla ilerler."""
    return int(t * ADIM_FPS + 1e-6) / ADIM_FPS


def darbeler(s: dict) -> list[tuple[float, float]]:
    """Kamera sarsıntısı (an, şiddet): damga, yırtılma, çarpan nesne, marka."""
    d = []
    for sh in s["sahneler"]:
        if sh["tur"] == "fis" and al(sh, "damga.t") is not None:
            d.append((harf_anlari(sh["damga"])[-1], 0.6))
        if sh["gecis"] == "yirt" and sh["bas"] > 0:
            d.append((sh["bas"], 0.5))
        if al(sh, "nesne2.t") is not None:
            d.append((sh["nesne2"]["t"], 1.0))
        if sh["tur"] == "kapanis":
            d += [(a, 0.45) for a in kelime_anlari(sh.get("marka"))]
    return d


def ses_olaylari(s: dict) -> list[tuple[float, str]]:
    """Efekt sesleri (an, tür). Türler: harf, yazici, bant, kaydir, damga, yirt, carp, kalem, esit."""
    o = []
    for sh in s["sahneler"]:
        if sh["gecis"] == "yirt" and sh["bas"] > 0:
            o.append((sh["bas"] - 0.04, "yirt"))
        if sh["gecis"] == "kaydir" and sh["bas"] > 0:
            o.append((sh["bas"] - KAYDIR_SN, "kaydir"))
        if al(sh, "nesne.t") is not None:
            o += [(sh["nesne"]["t"], "kaydir"), (sh["nesne"]["t"] + 0.2, "bant")]
        for k in ("ust", "alt", "damga"):
            y = sh.get(k)
            if isinstance(y, dict) and "t" in y and sh["tur"] != "kapanis":
                o += [(a, "harf") for a in harf_anlari(y)]
        if sh["tur"] == "fis":
            o += [(a, "yazici") for a in kalem_anlari(sh)]
            if al(sh, "damga.t") is not None:
                o.append((harf_anlari(sh["damga"])[-1] + 0.02, "damga"))
            if "cember_t" in sh:
                o.append((sh["cember_t"], "kalem"))
        if sh["tur"] == "esitlik":
            if "esit_t" in sh:
                o.append((sh["esit_t"], "esit"))
            if al(sh, "nesne2.t") is not None:
                o.append((sh["nesne2"]["t"], "carp"))
            if "cizgi_t" in sh:
                o.append((sh["cizgi_t"], "kalem"))
        if sh["tur"] == "kapanis":
            o += [(a, "damga") for a in kelime_anlari(sh.get("marka"))]
            if al(sh, "alt.t") is not None:
                o.append((sh["alt"]["t"], "bant"))
            if al(sh, "logo.t") is not None:
                o.append((sh["logo"]["t"], "damga"))
            if "damga_t" in sh:
                o.append((sh["damga_t"], "damga"))
    return sorted(o)
