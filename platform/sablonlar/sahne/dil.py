"""Ortak sahne dili: tek senaryo biçimi, her stil aynı sahne tiplerini kendi görünümüyle çizer.

Senaryo (`"dil": "sahne"`) sahnelerden oluşur; her sahnenin bir `tip`i, ekran yazıları ve isteğe bağlı bir
seslendirme satırı vardır. Zaman çizelgesi seslendirmeden çıkar: sahne, satırı kadar (önünde ve arkasında kısa
nefesle) sürer; satır yoksa tipin en kısa süresi kullanılır. Böylece senaryoda saniye yazmak gerekmez.

Bağımlılık yok (CI'da senaryo denetimi için); çizim `kaplama.py`, ses `ses.py`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SURUM = "sahne"
FORMATLAR = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}
SURE = (4.0, 120.0)
ON, ARKA = 0.35, 0.45  # seslendirme sahne başından ON sn sonra başlar, bittikten ARKA sn sonra sahne değişir
TAHMINI_HIZ = 2.6  # seslendirme dosyası yokken süre tahmini (sözcük/sn)

# tip -> alan -> (zorunlu, en çok karakter). Sınırlar yerleşimin taşmaması için; çizim yine de sığdırır.
TIPLER: dict[str, dict] = {
    "baslik": {"alan": {"metin": (True, 28), "alt": (False, 40), "ust": (False, 20)}, "en_kisa": 1.8},
    "liste": {"alan": {"baslik": (False, 28)}, "en_kisa": 2.4},  # maddeler: 2–5 satır, her biri ≤ 28
    "sayi": {"alan": {"deger": (True, 8), "etiket": (False, 28), "ust": (False, 20)}, "en_kisa": 2.0},
    "alinti": {"alan": {"metin": (True, 90), "kaynak": (False, 30)}, "en_kisa": 2.6},
    "karsilastirma": {"alan": {"sol": (True, 16), "sag": (True, 16), "sol_deger": (False, 6), "sag_deger": (False, 6),
                               "baslik": (False, 28)}, "en_kisa": 2.4},
    "urun": {"alan": {"ad": (True, 24), "fiyat": (False, 12), "ozellik": (False, 32), "gorsel": (False, None)}, "en_kisa": 2.4},
    "cta": {"alan": {"metin": (True, 22), "alt": (False, 32)}, "en_kisa": 2.2},
    "gecis": {"alan": {"metin": (False, 20)}, "en_kisa": 0.8},  # sahneler arası kısa ara kart, seslendirme almaz
}
MADDE = (2, 5, 28)  # liste: en az, en çok madde, madde başına karakter
ORTAK_ALANLAR = {"tip", "seslendirme", "okunus", "sure", "not", "stiller"}
ENERJI = {"baslik": 1, "liste": 1, "sayi": 2, "alinti": 0, "karsilastirma": 2, "urun": 1, "cta": 2, "gecis": 0}


class SenaryoHatasi(ValueError):
    pass


def bu_dil_mi(s: dict) -> bool:
    """Senaryo ortak sahne dilinde mi (stil.py yönlendirmesi için)."""
    return s.get("dil") == SURUM or any(isinstance(x, dict) and "tip" in x for x in s.get("sahneler") or [])


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    return s


def sozcuk(metin: str) -> int:
    return len(re.findall(r"\w+", metin or ""))


def tahmini_sure(metin: str) -> float:
    return sozcuk(metin) / TAHMINI_HIZ + 0.2 if metin else 0.0


def denetle(s: dict) -> list[str]:
    """Biçim denetimi (seslendirme dosyası gerekmez). Boş liste = geçerli."""
    h: list[str] = []
    shs = s.get("sahneler")
    if not isinstance(shs, list) or not shs:
        return ["sahneler: en az bir sahne gerekli"]
    if len(shs) > 24:
        h.append(f"sahneler: en çok 24 sahne ({len(shs)}); daha uzun video için kurgu şablonu")
    for f in ([s["format"]] if isinstance(s.get("format"), str) else s.get("format") or []):
        if str(f).replace(":", "x") not in FORMATLAR and f != "ikisi":
            h.append(f"format: {f} bilinmiyor (9:16, 16:9, 1:1, 4:5 ya da ikisi)")
    for k, v in (s.get("palet") or {}).items():
        if not (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)):
            h.append(f"palet.{k}: #RRGGBB olmalı")
    logo = (s.get("marka") or {}).get("logo")
    if logo and not (Path(s.get("_klasor", ".")) / logo).exists():
        h.append(f"marka.logo: {logo} bulunamadı (senaryoya göre)")
    for i, sh in enumerate(shs):
        ad = f"sahne {i + 1}"
        if not isinstance(sh, dict) or sh.get("tip") not in TIPLER:
            h.append(f"{ad}: tip {', '.join(TIPLER)} olmalı ({sh.get('tip') if isinstance(sh, dict) else sh})")
            continue
        tip = sh["tip"]
        ad = f"{ad} ({tip})"
        alan = TIPLER[tip]["alan"]
        for k in sh:
            if k not in alan and k not in ORTAK_ALANLAR and not (tip == "liste" and k == "maddeler"):
                h.append(f"{ad}: bilinmeyen alan {k} ({', '.join(list(alan) + (['maddeler'] if tip == 'liste' else []))})")
        for k, (zorunlu, azami) in alan.items():
            v = sh.get(k)
            if v is None:
                if zorunlu:
                    h.append(f"{ad}: {k} gerekli")
                continue
            if not isinstance(v, str) or not v.strip():
                h.append(f"{ad}: {k} boş olmayan metin olmalı")
            elif azami and len(v) > azami:
                h.append(f"{ad}: {k} \"{v}\" {len(v)} karakter, en çok {azami} (az yazı kuralı)")
        if tip == "liste":
            m = sh.get("maddeler")
            if not isinstance(m, list) or not MADDE[0] <= len(m) <= MADDE[1]:
                h.append(f"{ad}: maddeler {MADDE[0]}–{MADDE[1]} satırlık liste olmalı")
            else:
                for j, x in enumerate(m):
                    if not isinstance(x, str) or not x.strip() or len(x) > MADDE[2]:
                        h.append(f"{ad}: madde {j + 1} boş olmamalı ve en çok {MADDE[2]} karakter olmalı")
        if tip == "urun" and sh.get("gorsel") and not (Path(s.get("_klasor", ".")) / sh["gorsel"]).exists():
            h.append(f"{ad}: gorsel {sh['gorsel']} bulunamadı (senaryoya göre)")
        if tip == "gecis" and sh.get("seslendirme"):
            h.append(f"{ad}: geçiş sahnesi seslendirme almaz")
        if "seslendirme" in sh and not (isinstance(sh["seslendirme"], str) and sh["seslendirme"].strip()):
            h.append(f"{ad}: seslendirme boş olmayan metin olmalı")
        if "sure" in sh and not (isinstance(sh["sure"], (int, float)) and 0.6 <= sh["sure"] <= 20):
            h.append(f"{ad}: sure 0,6–20 sn olmalı")
    if not h:
        sure = zamanla(s)["sure"]
        if not SURE[0] <= sure <= SURE[1]:
            h.append(f"toplam süre {sure:.1f} sn; {SURE[0]:g}–{SURE[1]:g} sn olmalı")
    return h


def zamanla(s: dict, sureler: dict[str, float] | None = None) -> dict:
    """Sahnelere `bas`/`son` verir ve seslendirme satırlarını kurar. Satır süresi seslendirme dosyasından
    (`sureler`, id → sn), yoksa sözcük sayısından tahmin edilir. Senaryonun kopyasını döner."""
    sureler = sureler or {}
    out = dict(s)
    sb = dict(s.get("seslendirme") or {}) if isinstance(s.get("seslendirme"), dict) else {}
    satirlar, zs, t = [], [], 0.0
    for i, sh in enumerate(s["sahneler"]):
        sh = dict(sh)
        en_kisa = TIPLER[sh["tip"]]["en_kisa"] + (0.45 * len(sh.get("maddeler") or []) if sh["tip"] == "liste" else 0.0)
        d = en_kisa
        metin = sh.get("seslendirme")
        if metin:
            sid = f"s{i}"
            ses = sureler.get(sid, tahmini_sure(sh.get("okunus") or metin))
            satir = {"id": sid, "t": round(t + ON, 3), "metin": metin}
            if sh.get("okunus"):
                satir["okunus"] = sh["okunus"]
            satirlar.append(satir)
            sh["_ses"] = (t + ON, t + ON + ses)
            d = max(d, ON + ses + ARKA)
        if isinstance(sh.get("sure"), (int, float)):
            d = max(sh["sure"], d if metin else 0.0)
        sh["bas"], sh["son"] = round(t, 3), round(t + d, 3)
        zs.append(sh)
        t += d
    sb["satirlar"] = satirlar
    out["sahneler"], out["seslendirme"], out["sure"] = zs, sb, round(t, 3)
    return out


def sureler_oku(klasor: Path) -> dict[str, float]:
    k = Path(klasor) / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}
