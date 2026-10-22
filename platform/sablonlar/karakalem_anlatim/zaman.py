"""Karakalem anlatım şablonunun senaryosu: serbest uzunlukta sahne tipleri, zaman çizelgesi ve denetim.

Senaryo art arda gelen sahnelerdir; her sahnenin bir `tip`'i ve `sure`'si vardır, video sahnelerin
toplamı kadar sürer. Seslendirme satırlarının `t` anları videonun başından saniyedir (karakalem gibi).
Yalnız standart kütüphane: `denetle` CI'da skia olmadan çalışır.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

BURADA = Path(__file__).resolve().parent
ROLLER = ("kagit", "grafit", "vurgu")
VARSAYILAN_PALET = {"kagit": "#F7F4EC", "grafit": "#34343A", "vurgu": "#D9541E"}
# anlatıcı: genç, kısa saçlı, kapüşonlu; karakalem karakterinin görünüş alanları
VARSAYILAN_KARAKTER = {"ad": "Deniz", "sac": "kisa", "sac_rengi": "#3A3A42", "gozluk": False, "ten": "#F3EEE4",
                       "kazak": "#D6D9DC", "pantolon": "#4A4A52"}
SESLI = set("aeıioöuüAEIİOÖUÜ")
CIZIM_SN = 2.4      # sahnenin çizilip yazıldığı süre (kısa sahnede sürenin %55'i)
EN_AZ_SN, EN_COK_SN = 2.5, 90.0

# tip → alan: (zorunlu mu, karakter sınırı). Liste alanları için sınır her öğeye uygulanır.
TIPLER = {
    "baslik": {"metin": (True, 40), "ust": (False, 24), "alt": (False, 60)},
    "harita": {"baslik": (False, 40), "odak": (False, 0), "sehirler": (False, 16), "oklar": (False, 0),
               "vurgulu": (False, 0), "etiketler": (False, 0)},
    "karakter": {"metin": (False, 90), "poz": (False, 0), "ifade": (False, 0), "yon": (False, 0), "notlar": (False, 30)},
    "belge": {"baslik": (True, 34), "satirlar": (True, 44), "vurgu": (False, 0), "damga": (False, 16), "kaynak": (False, 40),
              "ust": (False, 40)},
    "kalabalik": {"metin": (False, 50), "pankartlar": (False, 14), "yogunluk": (False, 0)},
    "sayac": {"deger": (True, 8), "etiket": (False, 36), "ust": (False, 28), "kaynak": (False, 50)},
    "terazi": {"sol": (True, 18), "sag": (True, 18), "egim": (False, 0), "soru": (False, 40), "sol_deger": (False, 8),
               "sag_deger": (False, 8)},
    "takvim": {"olaylar": (True, 0), "vurgu": (False, 0), "baslik": (False, 40)},
}
POZLAR = ("anlat", "dusun", "sasir", "isaret", "omuz", "sevin")
IFADELER = ("normal", "endise", "sasir", "gulumse", "ciddi")
ODAKLAR = {  # harita kadrajı: (boylam0, boylam1, enlem0, enlem1)
    "avrupa": (-10.5, 30.0, 36.0, 58.5),
    "bati-avrupa": (-6.0, 19.0, 42.0, 56.0),
    "almanya": (3.5, 17.5, 46.8, 55.4),
    "fransa": (-5.5, 10.0, 41.5, 51.5),
}
SEHIRLER = {
    "Berlin": (13.40, 52.52), "Hamburg": (9.99, 53.55), "München": (11.58, 48.14), "Köln": (6.96, 50.94),
    "Frankfurt": (8.68, 50.11), "Stuttgart": (9.18, 48.78), "Düsseldorf": (6.77, 51.23), "Leipzig": (12.37, 51.34),
    "Dresden": (13.74, 51.05), "Hannover": (9.73, 52.37), "Bremen": (8.80, 53.08), "Nürnberg": (11.08, 49.45),
    "Paris": (2.35, 48.86), "Lyon": (4.84, 45.76), "Marsilya": (5.37, 43.30), "Lille": (3.06, 50.63),
    "Strazburg": (7.75, 48.58), "Toulouse": (1.44, 43.60), "Nantes": (-1.55, 47.22), "Bordeaux": (-0.58, 44.84),
    "Brüksel": (4.35, 50.85), "Amsterdam": (4.90, 52.37), "Viyana": (16.37, 48.21), "Prag": (14.42, 50.08),
    "Varşova": (21.01, 52.23), "Roma": (12.50, 41.90), "Madrid": (-3.70, 40.42), "Londra": (-0.13, 51.51),
    "Zürih": (8.54, 47.37), "Kopenhag": (12.57, 55.68), "Milano": (9.19, 45.46), "İstanbul": (28.98, 41.01),
}


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s["palet"] = {**VARSAYILAN_PALET, **s.get("palet", {})}
    s["karakter"] = {**VARSAYILAN_KARAKTER, **s.get("karakter", {})}
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", 84)
    s.setdefault("seslendirme", {"satirlar": []})
    s.setdefault("altyazi", True)
    bas = 0.0
    for i, sh in enumerate(s.get("sahneler", [])):
        sh.setdefault("id", f"{sh.get('tip', 's')}{i + 1}")
        sh["_bas"] = round(bas, 6)
        bas += sh.get("sure", 0) if isinstance(sh.get("sure"), (int, float)) else 0
    s["sure"] = round(bas, 6)
    return s


def cizim_suresi(sh: dict) -> float:
    return min(CIZIM_SN, sh["sure"] * 0.55)


def sahne_an(s: dict, t: float) -> tuple[dict | None, float]:
    """t anındaki sahne ve sahnenin başından geçen süre"""
    for sh in s["sahneler"]:
        if t < sh["_bas"] + sh["sure"] - 1e-9:
            return sh, t - sh["_bas"]
    son = s["sahneler"][-1] if s["sahneler"] else None
    return son, (t - son["_bas"]) if son else 0.0


def _renk_mi(v) -> bool:
    return isinstance(v, str) and len(v) == 7 and v[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in v[1:])


def _uzunluk(h: list, ad: str, alan: str, v, sinir: int) -> None:
    if not sinir:
        return
    for x in v if isinstance(v, list) else [v]:
        if isinstance(x, str) and len(x) > sinir:
            h.append(f"{ad}: `{alan}` en çok {sinir} karakter ({len(x)}: \"{x[:24]}…\")")


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    h = []
    for r in ROLLER:
        if not _renk_mi(s["palet"].get(r)):
            h.append(f"palet.{r} #RRGGBB olmalı")
    if not isinstance(s["fps"], int) or not 24 <= s["fps"] <= 60:
        h.append("fps 24–60 arasında tam sayı olmalı")
    sh_ler = s.get("sahneler") or []
    if not sh_ler:
        h.append("en az bir sahne gerekli")
    gorulen = set()
    for sh in sh_ler:
        ad = f"sahne {sh.get('id')}"
        if sh["id"] in gorulen:
            h.append(f"{ad}: kimlik tekrar ediyor")
        gorulen.add(sh["id"])
        tip = sh.get("tip")
        if tip not in TIPLER:
            h.append(f"{ad}: tip {', '.join(TIPLER)} olmalı")
            continue
        sure = sh.get("sure")
        if not isinstance(sure, (int, float)) or not EN_AZ_SN <= sure <= EN_COK_SN:
            h.append(f"{ad}: sure {EN_AZ_SN}–{EN_COK_SN} sn olmalı")
        for alan, (zorunlu, sinir) in TIPLER[tip].items():
            if zorunlu and not sh.get(alan):
                h.append(f"{ad}: `{alan}` zorunlu")
            if alan in sh:
                _uzunluk(h, ad, alan, sh[alan], sinir)
        bilinmeyen = {a for a in sh if not a.startswith("_")} - set(TIPLER[tip]) - {"id", "tip", "sure"}
        if bilinmeyen:
            h.append(f"{ad}: bilinmeyen alan {', '.join(sorted(bilinmeyen))}")
        h += [f"{ad}: {x}" for x in _tip_denetle(sh)]
    satir = s["seslendirme"].get("satirlar", [])
    ids = [x.get("id") for x in satir]
    if len(set(ids)) != len(ids):
        h.append("seslendirme satır kimlikleri tekrar ediyor")
    for x in satir:
        if not isinstance(x.get("t"), (int, float)) or not 0 <= x["t"] < s["sure"]:
            h.append(f"seslendirme {x.get('id')}: t videonun içinde olmalı (0–{s['sure']})")
    if sureler:  # seslendirme üretildiyse: satırlar taşmasın
        sira = sorted((x for x in satir if x["id"] in sureler), key=lambda x: x["t"])
        for a, b in zip(sira, sira[1:]):
            if a["t"] + sureler[a["id"]] > b["t"] + 0.05:
                h.append(f"seslendirme {a['id']} ({sureler[a['id']]:.2f} sn) {b['id']} başlamadan bitmiyor")
        if sira and sira[-1]["t"] + sureler[sira[-1]["id"]] > s["sure"] + 0.05:
            h.append(f"seslendirme {sira[-1]['id']} video bitince hâlâ sürüyor")
    return h


def _tip_denetle(sh: dict) -> list[str]:
    h, tip = [], sh["tip"]
    if tip == "harita":
        if sh.get("odak", "bati-avrupa") not in ODAKLAR:
            h.append(f"odak {', '.join(ODAKLAR)} olmalı")
        for c in sh.get("sehirler", []):
            if isinstance(c, str) and c not in SEHIRLER:
                h.append(f"şehir {c} bilinmiyor; {{\"ad\", \"boylam\", \"enlem\"}} ile verin")
        adlar = {c if isinstance(c, str) else c.get("ad") for c in sh.get("sehirler", [])}
        for o in sh.get("oklar", []):
            for u in ("den", "ye"):
                if o.get(u) not in adlar:
                    h.append(f"ok {o.get('den')}→{o.get('ye')}: {o.get(u)} `sehirler` içinde yok")
            if len(o.get("etiket", "")) > 16:
                h.append("ok etiketi en çok 16 karakter")
        if len(sh.get("sehirler", [])) > 10:
            h.append("en çok 10 şehir")
    elif tip == "karakter":
        if sh.get("poz", "anlat") not in POZLAR:
            h.append(f"poz {', '.join(POZLAR)} olmalı")
        if sh.get("ifade", "normal") not in IFADELER:
            h.append(f"ifade {', '.join(IFADELER)} olmalı")
        if sh.get("yon", "sol") not in ("sol", "sag"):
            h.append("yon sol ya da sag olmalı")
        if len(sh.get("notlar", [])) > 3:
            h.append("en çok 3 not")
    elif tip == "belge":
        if not 1 <= len(sh.get("satirlar", [])) <= 6:
            h.append("satirlar 1–6 satır olmalı")
        v = sh.get("vurgu")
        if v is not None and not (isinstance(v, int) and 0 <= v < len(sh.get("satirlar", []))):
            h.append("vurgu bir satır sırası (0'dan) olmalı")
    elif tip == "kalabalik":
        if len(sh.get("pankartlar", [])) > 5:
            h.append("en çok 5 pankart")
        if sh.get("yogunluk", "orta") not in ("az", "orta", "cok"):
            h.append("yogunluk az, orta ya da cok olmalı")
    elif tip == "terazi":
        e = sh.get("egim", 0.4)
        if not isinstance(e, (int, float)) or not -1 <= e <= 1:
            h.append("egim -1 (sol ağır) ile 1 (sağ ağır) arasında olmalı")
    elif tip == "takvim":
        ol = sh.get("olaylar", [])
        if not 2 <= len(ol) <= 6:
            h.append("olaylar 2–6 olay olmalı")
        for o in ol:
            if len(o.get("tarih", "")) > 12 or len(o.get("metin", "")) > 22 or not o.get("tarih"):
                h.append("her olayın `tarih`i (≤12) ve `metin`i (≤22) olmalı")
                break
        v = sh.get("vurgu")
        if v is not None and not (isinstance(v, int) and 0 <= v < len(ol)):
            h.append("vurgu bir olay sırası (0'dan) olmalı")
    return h


def kelimeler(s: dict, sureler: dict[str, float]) -> list[dict]:
    """altyazı ve dudak: her satırın kelimeleri, söylendikleri an ve hece sayısı (Türkçede her ünlü bir hece)"""
    out = []
    for x in s["seslendirme"].get("satirlar", []):
        if x["id"] not in sureler:
            continue
        d = sureler[x["id"]]
        ks = x["metin"].split()
        hece = [max(1, sum(c in SESLI for c in k)) for k in ks]
        top, acc, ws = sum(hece), 0, []
        for k, h_ in zip(ks, hece):
            ws.append({"k": k, "t": x["t"] + acc / top * d, "son": x["t"] + (acc + h_) / top * d, "hece": h_}); acc += h_
        out.append({"id": x["id"], "t": x["t"], "son": x["t"] + d, "kelimeler": ws})
    return out


def yumusak(p: float) -> float:
    p = max(0.0, min(1.0, p))
    return 2 * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 2 / 2


def asama(u: float, bas: float, sure: float) -> float:
    """[bas, bas+sure] aralığında 0→1 yumuşak ilerleme"""
    return yumusak((u - bas) / sure) if sure > 0 else float(u >= bas)


def cizim_olaylari(s: dict) -> list[tuple[float, float]]:
    """kalem sesinin düştüğü anlar: her sahnenin çizim evresi birkaç vuruşa bölünür (t, süre)"""
    out = []
    for sh in s["sahneler"]:
        d = cizim_suresi(sh)
        n = max(2, round(d / 0.55))
        for i in range(n):
            out.append((sh["_bas"] + 0.15 + i * d / n, d / n * 0.85))
    return out


def sayi_parcala(deger: str) -> tuple[str, float, str, int]:
    """'%37' → ('%', 37, '', 0); '1.200' → ('', 1200, '', 0) ; biçimi korunarak saydırılır"""
    i = next((j for j, c in enumerate(deger) if c.isdigit()), None)
    if i is None:
        return deger, 0.0, "", -1
    j = i
    while j < len(deger) and (deger[j].isdigit() or deger[j] in ".,"):
        j += 1
    govde = deger[i:j]
    ondalik = 0
    if "," in govde:
        ondalik = len(govde.split(",")[1])
        sayi = float(govde.replace(".", "").replace(",", "."))
    else:
        sayi = float(govde.replace(".", ""))
    return deger[:i], sayi, deger[j:], ondalik


def sayi_yaz(on: str, x: float, son: str, ondalik: int, ornek: str) -> str:
    if ondalik < 0:
        return ornek
    if ondalik:
        g = f"{x:.{ondalik}f}".replace(".", ",")
    else:
        g = f"{int(round(x)):,}".replace(",", ".") if "." in ornek else str(int(round(x)))
    return f"{on}{g}{son}"


def yay(a, b, egrilik: float = 0.25, n: int = 40):
    """iki nokta arası kavisli yol (ok)"""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    cx, cy = mx - dy * egrilik, my + dx * egrilik
    return [((1 - u) ** 2 * a[0] + 2 * (1 - u) * u * cx + u * u * b[0], (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * cy + u * u * b[1])
            for u in (i / (n - 1) for i in range(n))]


def kismi(p, f: float):
    """yolun baştan f oranı (yay uzunluğuna göre)"""
    if f >= 1 or len(p) < 2:
        return list(p)
    L = [0.0]
    for a, b in zip(p, p[1:]):
        L.append(L[-1] + math.dist(a, b))
    hedef = L[-1] * max(0.0, f)
    out = [p[0]]
    for i in range(1, len(p)):
        if L[i] >= hedef:
            k = (hedef - L[i - 1]) / max(1e-9, L[i] - L[i - 1])
            out.append((p[i - 1][0] + (p[i][0] - p[i - 1][0]) * k, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * k))
            break
        out.append(p[i])
    return out
