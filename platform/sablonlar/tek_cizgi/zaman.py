"""Tek çizgi şablonunun zaman çizelgesi: senaryo.json → pozlar (anahtar biçimler), zemin değişimleri, ses olayları.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur; ikisi de aynı anlarda vurur.
Bağımlılık yok (CI'da senaryo denetimi için); şekil adları `sekiller.py` içindeki listeyle aynıdır.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROLLER = ("zemin", "murekkep", "vurgu", "kapanis")
VARSAYILAN_PALET = {"zemin": "#F6EFE3", "murekkep": "#2B211C", "vurgu": "#D9532B", "kapanis": "#F2C14E"}
SEKIL_ADLARI = ("kruvasan", "fincan", "tabak", "basak", "saat", "canta", "kase", "sapka", "daire", "kalp")  # sekiller.SEKILLER ile aynı
DONUSUM_SN = 0.62   # bir biçimden ötekine dönüşüm süresi
CIZIM_SN = 1.35     # ilk sahnede çizginin soldan çizilerek gelmesi
IRIS_SN = 0.45      # zemin rengi değişimi (şeklin merkezinden açılan düz renk daire)
YAZI_SN = 0.35      # yazının belirmesi


class SenaryoHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    s["palet"] = {**VARSAYILAN_PALET, **s.get("palet", {})}
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", 96)
    s["muzik"].setdefault("akorlar", [[53, 57, 60, 64], [50, 53, 57, 60], [46, 50, 53, 57], [48, 52, 55, 60]])
    s.setdefault("seslendirme", {"satirlar": []})
    sh_ = s.get("sahneler", [])
    for i, sh in enumerate(sh_):
        sh["_son"] = sh_[i + 1]["bas"] if i + 1 < len(sh_) else s.get("sure", 0)
        sh.setdefault("renk", "murekkep")
    # müzikte enerji: sayaç sahnesiyle yükselir, sonraki sahnede sakinleşir, son sahnede parlak final
    sayac = [sh["bas"] for sh in sh_ if "sayac" in sh]
    s["muzik"].setdefault("yukselis", sayac[0] if sayac else (sh_[1]["bas"] if len(sh_) > 1 else 0))
    sonra = [sh["bas"] for sh in sh_ if sh["bas"] > s["muzik"]["yukselis"]]
    s["muzik"].setdefault("sakin", sonra[0] if len(sonra) > 1 else s.get("sure", 0))
    s["muzik"].setdefault("final", sh_[-1]["bas"] if sh_ else 0)
    return s


def _bicim_sayisi(sh: dict) -> int:
    return sum(k in sh for k in ("sekil", "sayi", "sayac"))


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
        ad = f"sahne {i + 1}"
        if i == 0 and sh.get("bas") != 0:
            h.append(f"{ad}: ilk sahne 0'da başlamalı")
        if sh.get("bas", -1) <= onceki:
            h.append(f"{ad}: başlangıçlar artan sırada olmalı")
        onceki = sh.get("bas", onceki)
        if sure and sh["bas"] >= sure:
            h.append(f"{ad}: video süresinden sonra başlıyor")
        if _bicim_sayisi(sh) != 1:
            h.append(f"{ad}: sekil, sayi ya da sayac alanlarından tam biri gerekli"); continue
        if "sekil" in sh:
            v = sh["sekil"]
            if not (v in SEKIL_ADLARI or (isinstance(v, str) and v.lstrip()[:1] in ("M", "m"))):
                h.append(f"{ad}: bilinmeyen şekil '{v}' ({', '.join(SEKIL_ADLARI)} ya da SVG yol verisi)")
        if "sayi" in sh and not str(sh["sayi"]).isdigit():
            h.append(f"{ad}: sayi yalnız rakam olmalı")
        if "sayac" in sh:
            c = sh["sayac"]
            d = c.get("degerler", []) if isinstance(c, dict) else []
            if len(d) < 2 or not all(isinstance(x, int) and x >= 0 for x in d):
                h.append(f"{ad}: sayac.degerler en az iki doğal sayı olmalı")
            b = c.get("bitis_t") if isinstance(c, dict) else None
            if not isinstance(b, (int, float)) or not (sh["bas"] + 0.2 * len(d) <= b < sh["_son"]):
                h.append(f"{ad}: sayac.bitis_t sahnenin içinde olmalı ve her adıma en az 0,2 sn bırakmalı")
        if i == 0 and sh["_son"] - sh["bas"] < CIZIM_SN:
            h.append(f"{ad}: ilk sahne çizginin çizilmesi için en az {CIZIM_SN} sn sürmeli")
        if i > 0 and sh["_son"] - sh["bas"] < DONUSUM_SN:
            h.append(f"{ad}: dönüşüm için en az {DONUSUM_SN} sn gerekir")
        for k in ("renk",):
            if sh.get(k) not in ROLLER:
                h.append(f"{ad}: {k} rolü bilinmiyor")
        if "zemin" in sh and sh["zemin"] not in ROLLER:
            h.append(f"{ad}: zemin rolü bilinmiyor")
        if "gorsel" in sh:
            g = sh["gorsel"]
            if sh.get("sekil") != "daire":
                h.append(f"{ad}: gorsel yalnız `daire` şekliyle kullanılır (fotoğraf çizginin çizdiği dairenin içine açılır)")
            elif not (isinstance(g, dict) and g.get("dosya") and isinstance(g.get("t"), (int, float))):
                h.append(f"{ad}: gorsel {{dosya, t}} olmalı")
            elif not (Path(s.get("_klasor", ".")) / g["dosya"]).is_file():
                h.append(f"{ad}: gorsel dosyası bulunamadı: {g['dosya']}")
            elif not (sh["bas"] <= g["t"] < sh["_son"]):
                h.append(f"{ad}: gorsel t={g['t']} sahnenin içinde değil ({sh['bas']}–{sh['_son']})")
        for k in ("yazi", "baslik", "alt"):
            if k in sh:
                y = sh[k]
                if not (isinstance(y, dict) and y.get("metin") and isinstance(y.get("t"), (int, float))):
                    h.append(f"{ad}: {k} {{metin, t}} olmalı")
                elif not (sh["bas"] <= y["t"] < sh["_son"]):
                    h.append(f"{ad}: {k} t={y['t']} sahnenin içinde değil ({sh['bas']}–{sh['_son']})")
                elif y.get("renk", "murekkep") not in ROLLER:
                    h.append(f"{ad}: {k} renk rolü bilinmiyor")
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


def sayac_anlari(sh: dict) -> list[float]:
    """sayaç adımlarının anları: aralıklar giderek kısalır (geri sayım hızlanır, kıtlık hissi)"""
    d = sh["sayac"]["degerler"]; b0, b1 = sh["bas"], sh["sayac"]["bitis_t"]
    n = len(d) - 1
    return [b0 + (b1 - b0) * (k / n) ** 0.8 for k in range(n + 1)]


def pozlar(s: dict) -> list[dict]:
    """anahtar biçimler: {t (dönüşüm başı), sure, tur, deger, renk, olcek, y, sahne, son (sayaç inişi)}.
    Biçim t+sure anında tamamlanır ve bir sonraki pozun t anına kadar kalır."""
    out = []
    for i, sh in enumerate(s["sahneler"]):
        ortak = {"olcek": sh.get("olcek", 1.0), "y": sh.get("y", 0.44), "sahne": i}
        if "sayac" in sh:
            d = sh["sayac"]["degerler"]; an = sayac_anlari(sh)
            for k, (v, t) in enumerate(zip(d, an)):
                son = k == len(d) - 1
                aralik = an[k] - an[k - 1] if k else DONUSUM_SN / 0.85
                sure = min(DONUSUM_SN, 0.85 * aralik) if k else DONUSUM_SN
                if son:  # son değer öne çıkar: biraz daha uzun iner, büyür, sahnenin rengini alır
                    sure = max(sure, 0.38); t = an[k] - sure * 0.55
                out.append({**ortak, "t": t if k else sh["bas"], "sure": sure, "tur": "sayi", "deger": str(v),
                            "renk": sh["renk"] if son else "murekkep", "olcek": ortak["olcek"] * (sh["sayac"].get("son_olcek", 1.45) if son else 1.0),
                            "son": son})
        else:
            tur = "sekil" if "sekil" in sh else "sayi"
            out.append({**ortak, "t": sh["bas"], "sure": CIZIM_SN if i == 0 else DONUSUM_SN, "tur": tur,
                        "deger": str(sh.get("sekil", sh.get("sayi"))), "renk": sh["renk"], "son": False, "ilk": i == 0})
    if out:
        out[0]["ilk"] = True
    return out


def poz_at(pz: list[dict], t: float) -> tuple[int, float]:
    """t anında hangi poza dönüşülüyor ve ilerleme (0..1); 0. poz için ilerleme = çizim oranı"""
    k = 0
    for j, p in enumerate(pz):
        if t >= p["t"]:
            k = j
    p = pz[k]
    return k, max(0.0, min(1.0, (t - p["t"]) / p["sure"]))


def zemin_degisimleri(s: dict) -> list[tuple[float, str]]:
    """(an, rol): sahnenin `zemin` alanı önceki zeminden farklıysa iris ile değişir"""
    out, simdiki = [], "zemin"
    for sh in s["sahneler"]:
        z = sh.get("zemin", simdiki)
        if z != simdiki:
            out.append((sh["bas"], z)); simdiki = z
    return out


def ses_olaylari(s: dict) -> list[tuple[float, str, float, float, dict]]:
    """(an, efekt, kazanç, pan, ek) listesi — sentez.py çalar. Kalem sesi geometriden ayrıca üretilir."""
    o = []
    pz = pozlar(s)
    for j, p in enumerate(pz[1:], 1):
        if p["deger"] == pz[j - 1]["deger"]:
            continue
        if p.get("son"):
            iniş = p["t"] + p["sure"] * 0.55
            o.append((iniş, "vurus", 0.9, 0.0, {}))
            o.append((iniş, "parilti", 0.35, 0.1, {}))
        elif p["tur"] == "sayi" and "sayac" in s["sahneler"][p["sahne"]] and p["t"] > s["sahneler"][p["sahne"]]["bas"]:
            o.append((p["t"] + p["sure"] * 0.6, "tik", 0.5, 0.25 * math.sin(p["t"] * 7), {}))
        else:
            o.append((p["t"], "kayma", 0.35, 0.0, {"sure": p["sure"]}))
    for an, _ in zemin_degisimleri(s):
        o.append((an - 0.05, "kayma", 0.4, -0.2, {"sure": IRIS_SN + 0.1}))
    for sh in s["sahneler"]:
        if "gorsel" in sh:
            o.append((sh["gorsel"]["t"], "parilti", 0.3, 0.0, {}))
        if "yazi" in sh:
            o.append((sh["yazi"]["t"], "pop", 0.3, 0.2, {}))
        if "baslik" in sh:
            o.append((sh["baslik"]["t"], "cinlama", 0.4, 0.0, {}))
        if "alt" in sh:
            o.append((sh["alt"]["t"], "pop", 0.22, -0.2, {}))
    return sorted(o, key=lambda x: x[0])
