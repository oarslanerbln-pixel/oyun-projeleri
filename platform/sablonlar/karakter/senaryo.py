"""Karakter şablonunun senaryosu ve zaman çizelgesi: <stil>.json → her an için poz, ifade, konum, yazı, nesne.

Görüntü (`cizim.py`) ve ses (`sentez.py`) yalnız buradan okur. Yalnız standart kütüphane (CI'da denetim için).
"""

from __future__ import annotations

import json
from pathlib import Path

import iskelet

GORUNUMLER = ("cizgisel", "maskot", "siluet")   # gorunumler/<ad>.py; yeni görünüm buraya eklenir
NESNELER = ("tabela", "ampul", "soru", "grafik", "balon", "kalp")
EK_NESNELER = {"maskot": ("logo",)}   # yalnız o görünümde anlamlı nesneler
MASKOT_NESNELERI = ("kupa", "sise", "kutu", "gorsel")   # maskotun gövdesi; gorsel = müşterinin ürün fotoğrafı (PNG)
SACLAR = ("kase", "kisa", "uzun", "topuz", "kel")
FORMATLAR = ("9x16", "16x9", "1x1", "4x5")
VARSAYILAN_PALET = {"zemin": "#F7F5EF", "cizgi": "#161616", "vurgu": "#FFD25A", "dolgu": "#FFFFFF", "yazi": "#161616"}
# Görünüme göre varsayılan palet (senaryonun "palet"i bunların üstüne yazılır).
STIL_PALETLERI = {
    "maskot": {"zemin": "#FDE3DA", "cizgi": "#2A1E1A", "vurgu": "#F49A8E", "dolgu": "#FFFFFF", "yazi": "#2A1E1A",
               "golge": "#F2CBBE", "govde": "#FFFFFF", "icerik": "#7A4A2C"},
    "siluet": {"cizgi": "#1E1424", "vurgu": "#FFF1C9", "dolgu": "#FFF1C9", "yazi": "#FFE7B0",
               "bantlar": ["#FBE3A8", "#F9CB7E", "#F4A764", "#E2805F", "#B85A69", "#6E3C5E"]},
}
YAZI_SN = 0.32
YAZI_SINIR = 42   # karakter: ekranda az yazı (Atilla'nın içerik brifi)


class SenaryoHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("stil", "cizgisel")
    s.setdefault("fps", 30)
    s["palet"] = {**VARSAYILAN_PALET, **STIL_PALETLERI.get(s["stil"], {}), **s.get("palet", {})}
    s["karakter"] = {"sac": "kase", "gozluk": False, **s.get("karakter", {})}
    s.setdefault("muzik", {}).setdefault("bpm", 100)
    s.setdefault("seslendirme", {"satirlar": []}).setdefault("satirlar", [])
    sh_ = s.get("sahneler", [])
    for i, sh in enumerate(sh_):
        sh["_son"] = sh_[i + 1]["bas"] if i + 1 < len(sh_) else s.get("sure", 0)
        if isinstance(sh.get("yazi"), str):
            sh["yazi"] = {"metin": sh["yazi"]}
        if sh.get("yazi"):
            sh["yazi"].setdefault("t", sh["bas"] + 0.25)
        if isinstance(sh.get("nesne"), str):
            sh["nesne"] = {"tur": sh["nesne"]}
        if sh.get("nesne"):
            sh["nesne"].setdefault("t", sh["bas"] + 0.35)
    return s


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    h = []
    if not s.get("kimlik"):
        h.append("kimlik eksik")
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or not 3 <= sure <= 90:
        h.append("sure 3–90 sn arasında olmalı")
        sure = 0
    if s.get("stil") not in GORUNUMLER:
        h.append(f"stil '{s.get('stil')}' bilinmiyor ({', '.join(GORUNUMLER)})")
    h += [f"format {f} bilinmiyor ({', '.join(FORMATLAR)})" for f in s.get("format", []) if f not in FORMATLAR]
    if s["karakter"].get("sac") not in SACLAR:
        h.append(f"karakter.sac '{s['karakter'].get('sac')}' bilinmiyor ({', '.join(SACLAR)})")
    h += _gorunum_denetle(s)
    nesneler = NESNELER + EK_NESNELER.get(s.get("stil"), ())
    sh_ = s.get("sahneler") or []
    if not sh_:
        h.append("en az bir sahne gerekli")
    elif sh_[0].get("bas") != 0:
        h.append("ilk sahne bas=0 olmalı")
    onceki = -1.0
    for i, sh in enumerate(sh_, 1):
        b = sh.get("bas")
        if not isinstance(b, (int, float)) or b <= onceki and i > 1 or (sure and b >= sure):
            h.append(f"sahne {i}: bas sırayla artmalı ve süreden küçük olmalı")
            continue
        onceki = b
        for k in [sh] + sh.get("anahtarlar", []):
            if "poz" in k and k["poz"] not in iskelet.POZ_ADLARI:
                h.append(f"sahne {i}: poz '{k['poz']}' bilinmiyor ({', '.join(iskelet.POZ_ADLARI)})")
            if "ifade" in k and k["ifade"] not in iskelet.IFADE_ADLARI:
                h.append(f"sahne {i}: ifade '{k['ifade']}' bilinmiyor ({', '.join(iskelet.IFADE_ADLARI)})")
            if "x" in k and not -1 <= k["x"] <= 1:
                h.append(f"sahne {i}: x -1..1 arasında olmalı")
        for k in sh.get("anahtarlar", []):
            if not b <= k.get("t", -1) < sh["_son"]:
                h.append(f"sahne {i}: anahtar t={k.get('t')} sahnenin içinde olmalı ({b}–{sh['_son']})")
        if sh.get("yazi") and len(sh["yazi"].get("metin", "")) > YAZI_SINIR:
            h.append(f"sahne {i}: yazı {YAZI_SINIR} karakterden uzun (ekranda az yazı)")
        n = sh.get("nesne")
        if n and n.get("tur") not in nesneler:
            h.append(f"sahne {i}: nesne '{n.get('tur')}' bilinmiyor ({', '.join(nesneler)})")
        if n and n.get("tur") in ("tabela", "balon") and len(n.get("metin", "")) > 14:
            h.append(f"sahne {i}: {n['tur']} metni 14 karakterden uzun")
    son = -1.0
    for x in sorted(s["seslendirme"]["satirlar"], key=lambda x: x.get("t", 0)):
        t = x.get("t", -1)
        if not 0 <= t < (sure or 1e9):
            h.append(f"seslendirme {x.get('id')}: t süre içinde olmalı")
        if t < son:
            h.append(f"seslendirme {x.get('id')}: önceki satırla çakışıyor")
        d = (sureler or {}).get(x.get("id"))
        if d is not None:
            son = t + d
            if sure and son > sure - 0.3:
                h.append(f"seslendirme {x['id']}: {d:.2f} sn sürüyor, videonun sonuna sığmıyor (t+süre ≤ sure-0.3)")
    return h


def _gorunum_denetle(s: dict) -> list[str]:
    """Görünüme özgü karakter alanları: maskotun gövdesi ve logosu, siluetin bantları ve eşlikçisi."""
    k, h = s["karakter"], []
    klasor = Path(s.get("_klasor", "."))
    if s.get("stil") == "maskot":
        if k.get("nesne", "kupa") not in MASKOT_NESNELERI:
            h.append(f"karakter.nesne '{k.get('nesne')}' bilinmiyor ({', '.join(MASKOT_NESNELERI)})")
        if k.get("nesne") == "gorsel" and not k.get("gorsel"):
            h.append("karakter.nesne 'gorsel' için karakter.gorsel (şeffaf PNG yolu) gerekli")
        for alan in ("gorsel", "logo"):
            if k.get(alan) and not (klasor / k[alan]).exists():
                h.append(f"karakter.{alan} bulunamadı: {k[alan]}")
        if len(k.get("logo_metin", "")) > 14:
            h.append("karakter.logo_metin 14 karakterden uzun")
    if s.get("stil") == "siluet":
        b = s["palet"].get("bantlar")
        if not isinstance(b, list) or not 2 <= len(b) <= 9:
            h.append("palet.bantlar 2–9 renklik liste olmalı (düz bantlar, gradyan yok)")
        e = k.get("eslik")
        if e is not None and not (isinstance(e, dict) and -1 <= e.get("x", 0.35) <= 1.5):
            h.append("karakter.eslik bir nesne olmalı, x -1..1.5")
    return h


# ---------- zaman çizelgesi ----------

def anahtarlar(s: dict) -> list[dict]:
    out = []
    for sh in s["sahneler"]:
        out.append({"t": sh["bas"], **{k: sh[k] for k in ("poz", "ifade", "x") if k in sh}})
        out += [dict(k) for k in sh.get("anahtarlar", [])]
    out.sort(key=lambda k: k["t"])
    return out


def _son_iki(keys: list[dict], alan: str, t: float, varsayilan):
    """t anındaki son değer, ondan önceki değer ve değişim anı."""
    once, simdi, an = varsayilan, varsayilan, 0.0
    for k in keys:
        if alan in k and k["t"] <= t:
            once, simdi, an = simdi, k[alan], k["t"]
    return once, simdi, an


def poz_at(s: dict, t: float) -> tuple[dict, str | None]:
    keys = s.setdefault("_anahtarlar", anahtarlar(s))
    once, simdi, an = _son_iki(keys, "poz", t, "ayakta")
    p = iskelet.yumusak((t - an) / iskelet.GECIS_SN) if an > 0 else 1.0
    a, b = iskelet.poz(once), iskelet.poz(simdi)
    deger = iskelet.karistir(a, b, p, iskelet.POZ_ALANLARI)
    for ad, guc in ((a["salinim"], 1 - p), (b["salinim"], p)):
        for k, v in iskelet.salinim(ad, t, guc).items():
            deger[k] += v
    for k, v in iskelet.nefes(t).items():
        deger[k] += v
    return deger, simdi


def ifade_at(s: dict, t: float) -> dict:
    keys = s.setdefault("_anahtarlar", anahtarlar(s))
    once, simdi, an = _son_iki(keys, "ifade", t, "notr")
    p = iskelet.yumusak((t - an) / iskelet.GECIS_SN) if an > 0 else 1.0
    return iskelet.karistir(iskelet.ifade(once), iskelet.ifade(simdi), p, iskelet.IFADE_ALANLARI)


def x_at(s: dict, t: float) -> float:
    """Yatay konum (-1..1, kadrajın karaktere ayrılan bölümünde). Yürürken bir sonraki anahtara kadar doğrusal."""
    keys = s.setdefault("_anahtarlar", anahtarlar(s))
    xs = [k for k in keys if "x" in k]
    x0 = 0.0
    for k in xs:
        if k["t"] > t:
            break
        yuru = (k.get("poz") or _son_iki(keys, "poz", k["t"], "ayakta")[1]) == "yuru"
        sonraki = next((j["t"] for j in keys if j["t"] > k["t"]), s["sure"])
        d = max(0.2, sonraki - k["t"]) if yuru else iskelet.GECIS_SN * 1.6
        p = min(1.0, (t - k["t"]) / d)
        p = p if yuru else iskelet.yumusak(p)
        x0 = x0 + (k["x"] - x0) * p
    return x0


def sahne_at(s: dict, t: float) -> dict:
    sh = s["sahneler"][0]
    for x in s["sahneler"]:
        if x["bas"] <= t:
            sh = x
    return sh


def durum(s: dict, t: float, agiz=None, oran: iskelet.Oranlar | None = None) -> tuple:
    """t anı → (Govde, Yuz, x). `agiz`: agiz.Agiz (konuşma satırları), yoksa ağız ifadeden.
    `oran`: görünümün beden oranları (maskot kısa bacaklı, büyük gövdeli); yoksa insan oranı."""
    p, _ = poz_at(s, t)
    g = iskelet.govde_kur(p, oran or iskelet.Oranlar())
    e = ifade_at(s, t)
    acik, bicim, konusuyor = agiz.an(t) if agiz else (0.0, "M", False)
    y = iskelet.Yuz(kas=e["kas"], kas_aci=e["kas_aci"], goz=e["goz"] * iskelet.goz_kirp(t), mutlu_goz=e["mutlu_goz"],
                    egri=e["egri"], agiz_gen=e["agiz_gen"], agiz_bicim=bicim, konusuyor=konusuyor,
                    agiz_ac=max(e["agiz_ac"] * (0.5 if konusuyor else 1.0), acik))
    return g, y, x_at(s, t)


def ses_olaylari(s: dict) -> list[tuple[float, str]]:
    """Efekt anları: nesne belirişi (pop), yazı (tık), poz değişimi (hafif hışırtı), sevinç (parıltı)."""
    out = []
    for sh in s["sahneler"]:
        if sh.get("nesne"):
            out.append((sh["nesne"]["t"], "pop"))
        if sh.get("yazi"):
            out.append((sh["yazi"]["t"], "tik"))
    onceki = "ayakta"
    for k in anahtarlar(s):
        if "poz" in k and k["poz"] != onceki:
            out.append((k["t"], "parilti" if k["poz"] == "sevin" else "hisirti"))
            onceki = k["poz"]
    return sorted(out)


def enerji(s: dict, t: float) -> str:
    return sahne_at(s, t).get("enerji", "orta")


def konusan_satirlar(s: dict) -> list[dict]:
    return [x for x in s["seslendirme"]["satirlar"] if x.get("konusan", "karakter") == "karakter"]

