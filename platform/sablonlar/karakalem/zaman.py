"""Karakalem şablonunun zaman çizelgesi ve sayfa geometrisi: karakalem.json → çizgiler, kamera, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur: kalem bir köşeyi döndüğü an ses de tıklar,
karakter bir basamağa indiği an marimba çalar. Bağımlılık yok (CI'da senaryo denetimi için).

Sayfa 1000 x 1100 birimlik bir defter yaprağıdır; kamera bunun üstünde gezer. Hikâye üç sahnedir:
  hedef    kalem dağı çizer (kamera ucun peşinde), sonra geri çekilip karakteri gösterir
  adimlar  her vuruşta bir basamak çizilir, karakter üstüne zıplar (kamera onu izler)
  sonuc    kamera geri çekilir: basamakların tepeleri zirveye çıkan bir eğridir; damga ve başlık
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROLLER = ("kagit", "grafit", "vurgu")
VARSAYILAN_PALET = {"kagit": "#F7F4EC", "grafit": "#34343A", "vurgu": "#E0703E"}
VARSAYILAN_KARAKTER = {"ad": "Mert", "sac": "daginik", "sac_rengi": "#4A4A52", "gozluk": True, "ten": "#F3EEE4",
                       "kazak": "#D8D5CE", "pantolon": "#4A4A52"}
SAC_STILLERI = ("daginik", "kisa", "kel")
SAHNE_SIRASI = ("hedef", "adimlar", "sonuc")
# lo-fi döngü (MIDI): Fmaj7 – Em7 – Dm7 – Cmaj7, her biri bir ölçü
VARSAYILAN_AKORLAR = [{"notalar": [57, 60, 64], "bas": 41}, {"notalar": [55, 59, 62], "bas": 40},
                      {"notalar": [53, 57, 60], "bas": 38}, {"notalar": [55, 59, 64], "bas": 36}]
SESLI = set("aeıioöuüAEIİOÖUÜ")

# sayfa
ZEMIN = 1000.0
ZIRVE = (800.0, 447.0)
SX0 = 250.0               # ilk basamağın sol kenarı
GENIS_POZ = (560.0, 690.0, 1.0)  # bütün sayfayı gösteren kamera (x, y, yakınlık)
DAG_YOLU = [(520, ZEMIN), (590, 800), (650, 700), (700, 640), ZIRVE, (850, 560), (905, 650), (950, 760), (1010, ZEMIN)]
KAR_YOLU = [(700, 640), (735, 600), (760, 585), (780, 540), ZIRVE, (820, 520), (850, 560), (828, 575), (800, 560),
            (770, 590), (745, 575), (700, 640)]

# süreler (sn)
DAG_BAS, DAG_SN, KAR_SN, TARAMA_SN = 0.35, 1.35, 0.26, 0.45
KAMERA_SN = 0.6           # geri çekilme / yakınlaşma
YAKIN_SN = 0.45
BASAMAK_SN = 0.3          # bir basamağın çizilmesi; karakter vuruştan 0,28 sn önce zıplar
EGRI_SN = 0.9
BASLIK_SN = 0.7
NEFES_SN = 0.3            # damgadan önce müziğin sustuğu an
HEDEF_EN_AZ = DAG_BAS + DAG_SN + KAR_SN + KAMERA_SN + 0.1


class SenaryoHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s["palet"] = {**VARSAYILAN_PALET, **s.get("palet", {})}
    s["karakter"] = {**VARSAYILAN_KARAKTER, **s.get("karakter", {})}
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", 90)
    s["muzik"].setdefault("akorlar", VARSAYILAN_AKORLAR)
    s.setdefault("seslendirme", {"satirlar": []})
    for sh in s.get("sahneler", []):
        if sh.get("tur") == "adimlar":
            sh.setdefault("adet", 5)
            sh.setdefault("buyume", 1.62)
            sh.setdefault("etiket", "+%1")
    return s


def sahne(s: dict, tur: str) -> dict:
    return next(sh for sh in s["sahneler"] if sh.get("tur") == tur)


def vurus(s: dict) -> float:
    return 60.0 / s["muzik"]["bpm"]


def _renk_mi(v) -> bool:
    return isinstance(v, str) and v.startswith("#") and len(v) == 7


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    """HATA listesi; boşsa senaryo render'a hazır. `sureler`: seslendirme satırı → saniye (seslendirme.json)."""
    h = []
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or sure <= 0:
        h.append("sure (saniye) eksik ya da geçersiz"); sure = 0
    for r, v in s["palet"].items():
        if r not in ROLLER:
            h.append(f"palet: bilinmeyen rol {r} ({', '.join(ROLLER)})")
        elif not _renk_mi(v):
            h.append(f"palet.{r}: #RRGGBB olmalı")
    k = s["karakter"]
    for alan in ("ten", "sac_rengi", "kazak", "pantolon"):
        if not _renk_mi(k.get(alan)):
            h.append(f"karakter.{alan}: #RRGGBB olmalı")
    if k.get("sac") not in SAC_STILLERI:
        h.append(f"karakter.sac: {', '.join(SAC_STILLERI)} olmalı")
    bpm = s["muzik"].get("bpm")
    if not isinstance(bpm, (int, float)) or not 60 <= bpm <= 140:
        h.append("muzik.bpm 60–140 arasında olmalı")
        return h
    ak = s["muzik"]["akorlar"]
    if not (isinstance(ak, list) and ak and all(isinstance(a, dict) and a.get("notalar") and isinstance(a.get("bas"), int) for a in ak)):
        h.append("muzik.akorlar [{notalar: [MIDI...], bas: MIDI}, ...] olmalı")
    turler = [sh.get("tur") for sh in s.get("sahneler", [])]
    if tuple(turler) != SAHNE_SIRASI:
        h.append(f"sahneler sırayla {', '.join(SAHNE_SIRASI)} olmalı (şu an: {', '.join(map(str, turler)) or 'boş'})")
        return h
    hd, ad, sn = (sahne(s, t) for t in SAHNE_SIRASI)
    if hd.get("bas") != 0:
        h.append("hedef: 0'da başlamalı")
    if not isinstance(ad.get("bas"), (int, float)) or ad["bas"] < HEDEF_EN_AZ:
        h.append(f"adimlar: en erken {HEDEF_EN_AZ:.2f} sn'de başlayabilir (dağın çizilmesi ve geri çekilme)")
        return h
    if not isinstance(ad["adet"], int) or not 3 <= ad["adet"] <= 8:
        h.append("adimlar.adet 3–8 arasında bir tam sayı olmalı")
        return h
    if not isinstance(ad["buyume"], (int, float)) or not 1.1 <= ad["buyume"] <= 2.2:
        h.append("adimlar.buyume 1,1–2,2 arasında olmalı")
    son_adim = ad["bas"] + ad["adet"] * vurus(s)
    if not isinstance(sn.get("bas"), (int, float)) or sn["bas"] < son_adim + 0.2:
        h.append(f"sonuc: en erken {son_adim + 0.2:.2f} sn'de başlayabilir ({ad['adet']} basamak, vuruş başına bir)")
        return h
    if sure and sn["bas"] + KAMERA_SN + EGRI_SN > sure:
        h.append("sonuc: eğrinin çizilmesine yetecek süre yok")
    d = sn.get("damga")
    if d is not None:
        if not (isinstance(d, dict) and d.get("metin") and isinstance(d.get("t"), (int, float))):
            h.append("sonuc.damga {metin, t} olmalı")
        elif not (sn["bas"] + EGRI_SN <= d["t"] < (sure or 1e9) - 0.3):
            h.append(f"sonuc.damga.t eğri bittikten sonra ({sn['bas'] + EGRI_SN:.2f}) ve videonun bitiminden 0,3 sn önce olmalı")
    b = sn.get("baslik")
    if b is not None:
        if not (isinstance(b, dict) and b.get("metin") and isinstance(b.get("t"), (int, float))):
            h.append("sonuc.baslik {metin, t} olmalı")
        elif not (sn["bas"] <= b["t"] and b["t"] + BASLIK_SN <= (sure or 1e9) - 0.2):
            h.append("sonuc.baslik.t sonuç sahnesinde olmalı ve yazı video bitmeden tamamlanmalı")
    sl = s["seslendirme"]
    if not isinstance(sl.get("saglayici", "piper"), str) or ("ses" in sl and not isinstance(sl["ses"], str)):
        h.append("seslendirme.saglayici ve seslendirme.ses yazı olmalı (ör. \"elevenlabs\" ve ses kimliği)")
    satirlar = sl.get("satirlar", [])
    for a, b2 in zip(satirlar, satirlar[1:]):
        if b2["t"] <= a["t"]:
            h.append(f"seslendirme: {b2['id']} {a['id']}'den sonra başlamalı")
        elif sureler and a["id"] in sureler and a["t"] + sureler[a["id"]] > b2["t"] + 0.05:
            h.append(f"seslendirme: {a['id']} ({sureler[a['id']]:.2f} sn) {b2['id']} başlamadan bitmiyor")
    if satirlar and sureler and sure:
        z = satirlar[-1]
        if z["id"] in sureler and z["t"] + sureler[z["id"]] > sure:
            h.append(f"seslendirme: {z['id']} video bitince hâlâ konuşuyor")
    return h


def kelimeler(s: dict, sureler: dict[str, float]) -> list[dict]:
    """altyazı: her satırın kelimeleri ve söylendikleri an. Satırın süresi hecelere bölünür (Türkçede her ünlü bir hece)."""
    out = []
    for x in s["seslendirme"].get("satirlar", []):
        if x["id"] not in sureler:
            continue
        d = sureler[x["id"]]
        ks = x["metin"].split()
        hece = [max(1, sum(c in SESLI for c in k)) for k in ks]
        top, acc, ws = sum(hece), 0, []
        for k, h_ in zip(ks, hece):
            ws.append({"k": k, "t": x["t"] + acc / top * d, "son": x["t"] + (acc + h_) / top * d}); acc += h_
        out.append({"id": x["id"], "t": x["t"], "son": x["t"] + d, "kelimeler": ws})
    return out


# ---------- geometri ----------
def basamaklar(s: dict) -> dict:
    """basamak genişliği, yükseklikleri ve büyüme eğrisi: eğri her basamağın sağ üst köşesinden geçip zirveye varır"""
    ad = sahne(s, "adimlar")
    n, g = ad["adet"], ad["buyume"]
    w = 460.0 / n
    tepe = ZEMIN - ZIRVE[1]
    h0 = tepe / g ** ((ZIRVE[0] - (SX0 + w)) / w)
    yuk = [h0 * g ** i for i in range(n)]
    return {"w": w, "h0": h0, "g": g, "yuk": yuk}


def egri_y(b: dict, x: float) -> float:
    return ZEMIN - b["h0"] * b["g"] ** ((x - (SX0 + b["w"])) / b["w"])


def yol_uzunlugu(p) -> float:
    return sum(math.dist(p[i - 1], p[i]) for i in range(1, len(p)))


def kismi(p, f: float) -> list[tuple[float, float]]:
    """yolun f (0..1) kadarı (yay uzunluğuna göre); son nokta kalemin ucu"""
    hedef = yol_uzunlugu(p) * f
    out, acc = [tuple(p[0])], 0.0
    for i in range(1, len(p)):
        s = math.dist(p[i - 1], p[i])
        if acc + s >= hedef:
            k = (hedef - acc) / s if s else 0.0
            out.append((p[i - 1][0] + (p[i][0] - p[i - 1][0]) * k, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * k))
            return out
        out.append(tuple(p[i])); acc += s
    return out


def yumusak(p: float) -> float:  # kalemin hızlanıp yavaşlaması (in-out quad)
    p = min(1.0, max(0.0, p))
    return 2 * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 2 / 2


def cizgiler(s: dict) -> dict:
    """ad → {t, d, yol, noktali}: kalemin çizdiği her çizgi"""
    b = basamaklar(s)
    ad, sn = sahne(s, "adimlar"), sahne(s, "sonuc")
    out = {"dag": {"t": DAG_BAS, "d": DAG_SN, "yol": DAG_YOLU},
           "kar": {"t": DAG_BAS + DAG_SN + 0.02, "d": KAR_SN, "yol": KAR_YOLU}}
    for i, an in enumerate(inisler(s)):
        x0, y = SX0 + i * b["w"], ZEMIN - b["yuk"][i]
        out[f"basamak{i}"] = {"t": an - 0.36, "d": BASAMAK_SN, "yol": [(x0, ZEMIN), (x0, y), (x0 + b["w"], y), (x0 + b["w"], ZEMIN)]}
    x, egri = SX0, []
    while x <= ZIRVE[0] + 0.1:
        egri.append((x, egri_y(b, x))); x += 10
    out["egri"] = {"t": sn["bas"] + 0.1, "d": EGRI_SN, "yol": egri, "noktali": True}
    return out


def oran(c: dict, t: float) -> float:
    return yumusak((t - c["t"]) / c["d"])


def kalem_ucu(c: dict, t: float):
    return kismi(c["yol"], oran(c, t))[-1]


def koseler(c: dict) -> list[float]:
    """kalemin keskin köşeleri döndüğü anlar (sesteki küçük tıklar)"""
    p, L, out, acc = c["yol"], yol_uzunlugu(c["yol"]), [], 0.0
    for i in range(1, len(p) - 1):
        acc += math.dist(p[i - 1], p[i])
        a = math.atan2(p[i][1] - p[i - 1][1], p[i][0] - p[i - 1][0])
        b = math.atan2(p[i + 1][1] - p[i][1], p[i + 1][0] - p[i][0])
        don = abs(b - a)
        if don > math.pi:
            don = 2 * math.pi - don
        if don < 0.5:
            continue
        f, lo, hi = acc / L, 0.0, 1.0
        for _ in range(30):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if yumusak(m) < f else (lo, m)
        out.append(c["t"] + lo * c["d"])
    return out


def inisler(s: dict) -> list[float]:
    """karakterin basamaklara indiği anlar: adımlar sahnesinden sonraki her vuruş"""
    ad = sahne(s, "adimlar")
    return [ad["bas"] + (i + 1) * vurus(s) for i in range(ad["adet"])]


def kamera(s: dict) -> dict:
    hd_son = sahne(s, "adimlar")["bas"]
    return {"geri1": (DAG_BAS + DAG_SN + 0.25, KAMERA_SN), "yakin": (hd_son, YAKIN_SN), "geri2": (sahne(s, "sonuc")["bas"], KAMERA_SN)}


def tarama(s: dict) -> tuple[float, float]:
    return (DAG_BAS + DAG_SN + 0.28, TARAMA_SN)


def ses_olaylari(s: dict) -> list[tuple[float, str, float, float, dict]]:
    """(an, efekt, kazanç, pan, ek) — sentez.py çalar. Kalem sesi çizgilerden ayrıca üretilir."""
    o = []
    for ad_, (t, d) in kamera(s).items():
        o.append((t - 0.05, "yakinlas" if ad_ == "yakin" else "uzaklas", 0.55, 0.0, {"sure": d + 0.15}))
    for i, an in enumerate(inisler(s)):
        o.append((an, "inis", 0.55, -0.3 + 0.6 * i / max(1, len(inisler(s)) - 1), {"adim": i}))
    sn = sahne(s, "sonuc")
    o.append((cizgiler(s)["egri"]["t"], "tirmanis", 0.3, 0.0, {"sure": EGRI_SN}))
    if sn.get("damga"):
        o.append((sn["damga"]["t"], "damga", 1.0, 0.0, {}))
    if sn.get("baslik"):
        o.append((sn["baslik"]["t"], "yazi", 0.5, 0.0, {"sure": BASLIK_SN}))
    return sorted(o, key=lambda x: x[0])
