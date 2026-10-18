"""Çizgi roman şablonunun zaman çizelgesi: cizgi-roman.json → sahneler, paneller, vuruşlar, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur; ikisi de aynı anlarda vurur.
Bağımlılık yok (CI'da senaryo denetimi için).
"""

from __future__ import annotations

import json
from pathlib import Path

VARSAYILAN_PALET = {
    "kagit": "#FFFBF0", "murekkep": "#141414", "beyaz": "#FFFFFF",
    "sari": "#FFD23F", "turuncu": "#F08A24", "kirmizi": "#E63946", "koyu_kirmizi": "#A4161A", "acik_kirmizi": "#FF6B6B",
    "mavi": "#35C5F0", "lacivert": "#1D4E89", "yesil": "#4CB944", "koyu_yesil": "#1E7A3A", "acik_yesil": "#B8E986",
    "cimen": "#3E9A3A", "krem": "#FFF4D6", "krem_nokta": "#F3D27A",
    "ten": "#F7C59F", "ten_golge": "#E0956A", "sac": "#23233A", "kahve": "#8A5A33",
}
OGE_TURLERI = ("yazi", "patlama", "takvim", "buyume_oku", "filiz", "agac", "kahraman", "balon", "gorsel")
FORMATLAR = ("9x16", "16x9", "1x1", "4x5")
KAYDIRMA_SN = 0.5   # sahneler arası sayfa kayması (sahne başının ortasında)
CARPMA_SN = 0.12    # "çarp" girişinde yazının ekrana düşmesi

# her öğe türünün renk alanları ve varsayılan rolleri
RENK_ALANLARI = {
    "yazi": {"renk": "kirmizi"},
    "patlama": {"renk": "kirmizi", "zemin": "beyaz"},
    "takvim": {"renk": "kirmizi", "golge": "koyu_kirmizi"},
    "buyume_oku": {"renk": "kirmizi", "sutun_renk": "beyaz", "sutun_golge": "lacivert"},
    "filiz": {"saksi": "kirmizi", "yaprak": "yesil"},
    "agac": {"govde": "kahve", "tac": "yesil", "golge": "koyu_yesil", "isik": "acik_yesil", "meyve": "kirmizi", "cimen": "cimen"},
    "kahraman": {"tisort": "sari", "tisort_golge": "turuncu", "yildiz": "kirmizi", "ten": "ten", "ten_golge": "ten_golge", "sac": "sac", "sac_isik": "mavi"},
    "balon": {},
    "gorsel": {},
}


class SenaryoHatasi(ValueError):
    pass


def _bicimle(d: dict, fmt: str) -> dict:
    """öğe/panel üstündeki format anahtarları ("16x9": {...}) o formatta alanları ezer"""
    return {**{k: v for k, v in d.items() if k not in FORMATLAR}, **d.get(fmt, {})}


def bicim_icin(s: dict, fmt: str) -> dict:
    """senaryonun verilen formata göre ezilmiş kopyası (cizim.py bunu kullanır)"""
    out = dict(s)
    out["sahneler"] = []
    for sh in s["sahneler"]:
        sh2 = _bicimle(sh, fmt)
        sh2["paneller"] = [{**_bicimle(p, fmt), "ogeler": [_bicimle(o, fmt) for o in p.get("ogeler", [])]}
                           for p in sh.get("paneller", [])]
        out["sahneler"].append(sh2)
    return out


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s["palet"] = {**VARSAYILAN_PALET, **s.get("palet", {})}
    s.setdefault("seslendirme", {"satirlar": []})
    sh_ = s.get("sahneler", [])
    for i, sh in enumerate(sh_):
        sh["_son"] = sh_[i + 1]["bas"] if i + 1 < len(sh_) else s.get("sure", 0)
        for p in sh.get("paneller", []):
            p.setdefault("ogeler", [])
            for o in p["ogeler"]:
                for alan, rol in RENK_ALANLARI.get(o.get("tur"), {}).items():
                    o.setdefault(alan, rol)
    s.setdefault("muzik", {})
    m = s["muzik"]
    m.setdefault("bpm", 120)
    m.setdefault("akorlar", [[60, 64, 67, 71], [57, 60, 64, 67], [65, 69, 72, 76], [67, 71, 74, 77]])
    # enerji: ikinci sahnede yükselir, üçüncüde sakinleşir, sonda parlak final
    m.setdefault("yukselis", sh_[1]["bas"] if len(sh_) > 1 else 0)
    m.setdefault("sakin", sh_[2]["bas"] if len(sh_) > 3 else s.get("sure", 0))
    m.setdefault("final", sh_[-1]["bas"] if sh_ else 0)
    return s


def vurus_ani(o: dict) -> float | None:
    """öğenin "darbe" anı (sarsıntı + vuruş sesi + bakır vuruşu) ya da None"""
    if o["tur"] == "yazi" and o.get("giris", "carp") == "carp":
        return o["t"]
    if o["tur"] == "patlama":
        return o.get("vurus_t", o["sayac"]["bitis_t"] if "sayac" in o else o["t"])
    if o["tur"] == "agac":
        return o["t"]
    return None


def vuruslar(s: dict) -> list[float]:
    out = set()
    for sh in s["sahneler"]:
        for p in sh.get("paneller", []):
            if "vurus" in p:
                out.add(p["vurus"])
            for o in p["ogeler"]:
                v = vurus_ani(o)
                if v is not None:
                    out.add(v)
    return sorted(out)


def _renk_mi(v) -> bool:
    return isinstance(v, str) and v.startswith("#") and len(v) == 7


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    """HATA listesi; boşsa senaryo render'a hazır. `sureler`: seslendirme satırı → saniye (seslendirme.json)."""
    h = []
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or sure <= 0:
        h.append("sure (saniye) eksik ya da geçersiz")
        sure = 0
    for r, v in s["palet"].items():
        if not _renk_mi(v):
            h.append(f"palet.{r}: #RRGGBB olmalı")
    pal = s["palet"]

    def rol(ad, alan, v):
        if v not in pal:
            h.append(f"{ad}: {alan} rengi '{v}' palette yok")

    def an(ad, alan, v, bas, son):
        if not isinstance(v, (int, float)):
            h.append(f"{ad}: {alan} (saniye) gerekli"); return False
        if not (bas <= v < son):
            h.append(f"{ad}: {alan}={v} sahnenin içinde değil ({bas}–{son})"); return False
        return True

    sahneler = s.get("sahneler") or []
    if not sahneler:
        h.append("sahneler boş")
    onceki = -1.0
    for i, sh in enumerate(sahneler):
        ad = f"sahne {i + 1}"
        if i == 0 and sh.get("bas") != 0:
            h.append(f"{ad}: ilk sahne 0'da başlamalı")
        if not isinstance(sh.get("bas"), (int, float)) or sh["bas"] <= onceki:
            h.append(f"{ad}: başlangıçlar artan sırada olmalı"); continue
        onceki = sh["bas"]
        bas, son = sh["bas"], sh["_son"]
        if sure and bas >= sure:
            h.append(f"{ad}: video süresinden sonra başlıyor")
        if i > 0 and son - bas < KAYDIRMA_SN:
            h.append(f"{ad}: sayfa kayması için en az {KAYDIRMA_SN} sn gerekir")
        pn = sh.get("paneller") or []
        if len(pn) not in (1, 2):
            h.append(f"{ad}: 1 ya da 2 panel olmalı"); continue
        if "bolme" in sh and not (0.15 <= sh["bolme"] <= 0.85):
            h.append(f"{ad}: bolme 0,15–0,85 arasında olmalı")
        for j, p in enumerate(pn):
            pad = f"{ad} panel {j + 1}"
            rol(pad, "zemin", p.get("zemin", "beyaz"))
            if "nokta" in p:
                rol(pad, "nokta", p["nokta"])
            if p.get("nokta_yon", "asagi") not in ("asagi", "yukari", "duz"):
                h.append(f"{pad}: nokta_yon asagi, yukari ya da duz olmalı")
            if "vurus" in p:
                an(pad, "vurus", p["vurus"], bas, son)
            if "hiz_cizgileri" in p:
                hz = p["hiz_cizgileri"]
                rol(pad, "hiz_cizgileri.renk", hz.get("renk", "murekkep"))
                if "t" in hz:
                    an(pad, "hiz_cizgileri.t", hz["t"], bas, son)
            if "anlati" in p:
                a = p["anlati"]
                if not (isinstance(a, dict) and a.get("metin")):
                    h.append(f"{pad}: anlati {{metin, t}} olmalı")
                else:
                    an(pad, "anlati.t", a.get("t"), bas, son)
            for k, o in enumerate(p.get("ogeler", [])):
                oad = f"{pad} öğe {k + 1} ({o.get('tur', '?')})"
                if o.get("tur") not in OGE_TURLERI:
                    h.append(f"{oad}: tur {', '.join(OGE_TURLERI)} olmalı"); continue
                if not an(oad, "t", o.get("t"), bas, son):
                    continue
                for alan in RENK_ALANLARI[o["tur"]]:
                    rol(oad, alan, o[alan])
                tur = o["tur"]
                if tur == "yazi":
                    if not o.get("metin"):
                        h.append(f"{oad}: metin gerekli")
                    if o.get("giris", "carp") not in ("carp", "pop", "yok"):
                        h.append(f"{oad}: giris carp, pop ya da yok olmalı")
                if tur == "patlama":
                    if ("metin" in o) == ("sayac" in o):
                        h.append(f"{oad}: metin ya da sayac alanlarından tam biri gerekli")
                    if "sayac" in o:
                        c = o["sayac"]
                        d = c.get("degerler", []) if isinstance(c, dict) else []
                        if len(d) != 2 or not all(isinstance(x, int) for x in d):
                            h.append(f"{oad}: sayac.degerler [ilk, son] iki tam sayı olmalı")
                        if an(oad, "sayac.bitis_t", c.get("bitis_t") if isinstance(c, dict) else None, bas, son) and c["bitis_t"] <= o["t"]:
                            h.append(f"{oad}: sayac.bitis_t t'den sonra olmalı")
                if tur in ("takvim", "buyume_oku"):
                    if an(oad, "bitis_t", o.get("bitis_t"), bas, son) and o["bitis_t"] <= o["t"]:
                        h.append(f"{oad}: bitis_t t'den sonra olmalı")
                if tur == "takvim":
                    d = o.get("degerler", [1, 7])
                    if len(d) != 2 or not all(isinstance(x, int) for x in d) or d[1] <= d[0]:
                        h.append(f"{oad}: degerler [ilk, son] artan iki tam sayı olmalı")
                if tur == "kahraman":
                    for alan in ("yumruk_t", "goz_kirp_t"):
                        if alan in o:
                            an(oad, alan, o[alan], bas, son)
                if tur == "balon":
                    st = o.get("satirlar")
                    if not (isinstance(st, list) and 1 <= len(st) <= 3 and all(isinstance(x, dict) and x.get("metin") for x in st)):
                        h.append(f"{oad}: satirlar 1–3 {{metin, renk}} olmalı")
                    else:
                        for x in st:
                            rol(oad, "satır rengi", x.get("renk", "murekkep"))
                if tur == "gorsel":
                    if not o.get("yol"):
                        h.append(f"{oad}: yol gerekli")
                    elif not (Path(s.get("_klasor", ".")) / o["yol"]).exists():
                        h.append(f"{oad}: görsel bulunamadı: {o['yol']}")
                for alan in ("x", "y"):
                    if alan in o and not isinstance(o[alan], (int, float)):
                        h.append(f"{oad}: {alan} sayı olmalı (panelin oranı)")
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
    for sh in s["sahneler"][1:]:
        o.append((sh["bas"] - KAYDIRMA_SN / 2 - 0.05, "kayma", 0.5, 0.0, {}))
    for v in vuruslar(s):
        o.append((v, "darbe", 1.0, 0.0, {}))
    for sh in s["sahneler"]:
        for p in sh.get("paneller", []):
            if "anlati" in p:
                o.append((p["anlati"]["t"], "vuus", 0.25, -0.4, {}))
            for e in p["ogeler"]:
                tur = e["tur"]
                if tur == "patlama" and "sayac" in e:
                    for k in range(14):
                        o.append((e["t"] + (e["sayac"]["bitis_t"] - e["t"]) * (k / 13) * 0.98, "tik", 0.35, -0.2, {"k": k}))
                if tur == "takvim":
                    n = e.get("degerler", [1, 7])[1] - e.get("degerler", [1, 7])[0]
                    bas = e["t"] + 0.3
                    for k in range(n):
                        o.append((bas + (e["bitis_t"] - bas) * k / n + 0.06, "yaprak", 0.35, 0.3, {"k": k}))
                if tur == "yazi" and e.get("giris") == "pop":
                    o.append((e["t"], "pop", 0.3, 0.2, {"f": 900}))
                if tur in ("filiz", "balon"):
                    o.append((e["t"], "pop", 0.4 if tur == "filiz" else 0.5, 0.0, {"f": 700 if tur == "filiz" else 500}))
                if tur == "kahraman" and "yumruk_t" in e:
                    o.append((e["yumruk_t"], "vuus", 0.3, 0.3, {"yukari": True}))
                if tur == "buyume_oku":
                    o.append((e["t"], "vuus", 0.3, 0.0, {"yukari": True, "sure": e["bitis_t"] - e["t"]}))
    return sorted(o, key=lambda x: x[0])
