"""Risograf şablonunun zaman çizelgesi: risograf.json → sayfalar, öğeler, damgalar, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur; ikisi de aynı anlarda vurur.
Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
from pathlib import Path

VARSAYILAN_MUREKKEPLER = {
    "sari": {"renk": "#FFE14D", "kayma": [0, 0]},
    "pembe": {"renk": "#FF48B0", "kayma": [5, -3]},
    "mavi": {"renk": "#0078BF", "kayma": [-4, 4]},
}
OGE_TURLERI = ("yazi", "sayac", "daire", "zemin", "egri", "halkalar", "ok", "figur", "cizgi", "logo")
GIRISLER = ("sil", "kay", "belir", "pop")
FORMATLAR = ("9x16", "16x9", "1x1", "4x5")
BESLE_SN = 0.5     # sayfa besleme (yeni sayfa alttan gelir), sayfa başının ortasında
GIRIS_SN = {"sil": 0.5, "kay": 0.45, "belir": 0.0, "pop": 0.35}


class SenaryoHatasi(ValueError):
    pass


def _bicimle(d: dict, fmt: str) -> dict:
    """öğe/sayfa üstündeki format anahtarları ("16x9": {...}) o formatta alanları ezer"""
    return {**{k: v for k, v in d.items() if k not in FORMATLAR}, **d.get(fmt, {})}


def bicim_icin(s: dict, fmt: str) -> dict:
    out = dict(s)
    out["sayfalar"] = [{**_bicimle(sy, fmt), "ogeler": [_bicimle(o, fmt) for o in sy.get("ogeler", [])]} for sy in s["sayfalar"]]
    return out


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s.setdefault("kagit", "#F4EFE4")
    s["murekkepler"] = s.get("murekkepler") or json.loads(json.dumps(VARSAYILAN_MUREKKEPLER))
    for m in s["murekkepler"].values():
        m.setdefault("kayma", [0, 0])
    s.setdefault("baski_sirasi", list(s["murekkepler"]))
    s.setdefault("tanecik", {})
    s["tanecik"].setdefault("guc", 1.0)
    s["tanecik"].setdefault("kaynama", 4)
    s.setdefault("isaretler", {"murekkep": s["baski_sirasi"][-1]})
    s.setdefault("seslendirme", {"satirlar": []})
    sy_ = s.get("sayfalar", [])
    for i, sy in enumerate(sy_):
        sy["_son"] = sy_[i + 1]["bas"] if i + 1 < len(sy_) else s.get("sure", 0)
        sy.setdefault("ogeler", [])
    s.setdefault("muzik", {})
    m = s["muzik"]
    m.setdefault("bpm", 80)
    # bölüm başına akorlar (giriş, yükseliş, sakin, final); her bölümde iki vuruşta bir sıradaki akor
    m.setdefault("akorlar", [[[53, 57, 64, 67, 69], [57, 60, 64, 67, 72]], [[57, 60, 64, 67, 71], [55, 59, 64, 67, 69]],
                             [[50, 57, 60, 64, 65]], [[48, 55, 59, 62, 64], [60, 64, 67, 71, 74]]])
    m.setdefault("yukselis", sy_[1]["bas"] if len(sy_) > 1 else 0)
    m.setdefault("sakin", sy_[2]["bas"] if len(sy_) > 3 else s.get("sure", 0))
    m.setdefault("final", sy_[-1]["bas"] if sy_ else 0)
    return s


def damga_ani(o: dict) -> float | None:
    """öğenin baskı "damgası" anı (tok vuruş + çan) ya da None"""
    if o["tur"] == "yazi" and o.get("damga", o.get("boy", 100) >= 200):
        return o["t"] + GIRIS_SN.get(o.get("giris", "kay"), 0) * 0.3
    if o["tur"] == "sayac":
        return o["bitis_t"]
    if o["tur"] == "daire" and "buyume" in o:
        return o["buyume"]["t"]
    return None


def damgalar(s: dict) -> list[float]:
    return sorted({round(v, 3) for sy in s["sayfalar"] for o in sy["ogeler"] if (v := damga_ani(o)) is not None})


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    """HATA listesi; boşsa senaryo render'a hazır. `sureler`: seslendirme satırı → saniye (seslendirme.json)."""
    h = []
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or sure <= 0:
        h.append("sure (saniye) eksik ya da geçersiz")
        sure = 0
    renk_mi = lambda v: isinstance(v, str) and v.startswith("#") and len(v) == 7
    if not renk_mi(s["kagit"]):
        h.append("kagit: #RRGGBB olmalı")
    mk = s["murekkepler"]
    if not 1 <= len(mk) <= 4:
        h.append("murekkepler 1–4 mürekkep olmalı (riso makinesi tambur sayısı)")
    for ad, m in mk.items():
        if not renk_mi(m.get("renk")):
            h.append(f"murekkepler.{ad}.renk: #RRGGBB olmalı")
        if not (isinstance(m["kayma"], list) and len(m["kayma"]) == 2):
            h.append(f"murekkepler.{ad}.kayma: [dx, dy] olmalı")
    if sorted(s["baski_sirasi"]) != sorted(mk):
        h.append("baski_sirasi her mürekkebi bir kez içermeli")
    if s["isaretler"] and s["isaretler"].get("murekkep") not in mk:
        h.append("isaretler.murekkep tanımlı bir mürekkep olmalı")

    def ink(ad, v, alan="murekkep"):
        if v not in mk:
            h.append(f"{ad}: {alan} '{v}' tanımlı değil ({', '.join(mk)})")

    def an(ad, alan, v, bas, son):
        if not isinstance(v, (int, float)):
            h.append(f"{ad}: {alan} (saniye) gerekli"); return False
        if not (bas <= v <= son):
            h.append(f"{ad}: {alan}={v} sayfanın içinde değil ({bas}–{son})"); return False
        return True

    sayfalar = s.get("sayfalar") or []
    if not sayfalar:
        h.append("sayfalar boş")
    onceki = -1.0
    for i, sy in enumerate(sayfalar):
        ad = f"sayfa {i + 1}"
        if i == 0 and sy.get("bas") != 0:
            h.append(f"{ad}: ilk sayfa 0'da başlamalı")
        if not isinstance(sy.get("bas"), (int, float)) or sy["bas"] <= onceki:
            h.append(f"{ad}: başlangıçlar artan sırada olmalı"); continue
        onceki = sy["bas"]
        bas, son = sy["bas"], sy["_son"]
        if sure and bas >= sure:
            h.append(f"{ad}: video süresinden sonra başlıyor")
        if i > 0 and son - bas < BESLE_SN:
            h.append(f"{ad}: sayfa beslemesi için en az {BESLE_SN} sn gerekir")
        for k, o in enumerate(sy["ogeler"]):
            oad = f"{ad} öğe {k + 1} ({o.get('tur', '?')})"
            tur = o.get("tur")
            if tur not in OGE_TURLERI:
                h.append(f"{oad}: tur {', '.join(OGE_TURLERI)} olmalı"); continue
            if tur == "figur":
                r = o.get("renkler", {})
                for parca in ("govde", "bacak", "sapka"):
                    if parca in r:
                        ink(oad, r[parca], f"renkler.{parca}")
            else:
                ink(oad, o.get("murekkep"))
            t = o.get("t", bas)
            if not an(oad, "t", t, bas, son):
                continue
            if tur in ("yazi", "sayac"):
                if o.get("giris", "kay") not in GIRISLER:
                    h.append(f"{oad}: giris {', '.join(GIRISLER)} olmalı")
            if tur == "yazi" and not o.get("metin"):
                h.append(f"{oad}: metin gerekli")
            if tur == "sayac":
                d = o.get("degerler", [])
                if len(d) != 2 or not all(isinstance(x, int) for x in d):
                    h.append(f"{oad}: degerler [ilk, son] iki tam sayı olmalı")
            if tur in ("sayac", "egri") or (tur in ("yazi", "figur") and "bitis_t" in o):
                if an(oad, "bitis_t", o.get("bitis_t"), bas, son) and o["bitis_t"] <= t:
                    h.append(f"{oad}: bitis_t t'den sonra olmalı")
            if tur == "egri":
                for alan in ("golge", "noktalar"):
                    if alan in o:
                        ink(oad, o[alan], alan)
            if tur == "daire" and "buyume" in o:
                b = o["buyume"]
                if an(oad, "buyume.t", b.get("t") if isinstance(b, dict) else None, bas, son) and not isinstance(b.get("r"), (int, float)):
                    h.append(f"{oad}: buyume.r gerekli")
            if tur == "logo":
                if not o.get("yol"):
                    h.append(f"{oad}: yol gerekli")
                elif not (Path(s.get("_klasor", ".")) / o["yol"]).exists():
                    h.append(f"{oad}: logo bulunamadı: {o['yol']}")
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
    for f in s.get("format", []):
        if f not in FORMATLAR:
            h.append(f"format {f} bilinmiyor ({', '.join(FORMATLAR)})")
    return h


def ses_olaylari(s: dict) -> list[tuple[float, str, float, float, dict]]:
    """(an, efekt, kazanç, pan, ek) listesi — sentez.py çalar."""
    o = []
    for sy in s["sayfalar"][1:]:
        o.append((sy["bas"] - BESLE_SN / 2 - 0.05, "makine", 0.8, 0.0, {}))
    for d in damgalar(s):
        o.append((d, "damga", 0.6, 0.0, {}))
    for sy in s["sayfalar"]:
        for e in sy["ogeler"]:
            if e["tur"] == "daire" and e.get("giris") == "buyu":
                o.append((e.get("t", sy["bas"]), "pop", 0.4, 0.0, {"f": 800}))
            if e["tur"] == "egri" and "noktalar" in e:
                n = e.get("nokta_sayisi", 11)
                for k in range(n):
                    o.append((e["t"] + (e["bitis_t"] - e["t"]) * (k + 1) / (n + 1) + 0.05, "pop", 0.12, -0.4 + 0.8 * k / max(1, n - 1),
                              {"f": 1200 + 60 * k}))
    return sorted(o, key=lambda x: x[0])
