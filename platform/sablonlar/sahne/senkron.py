"""Kelimeye senkron giriş: sahnedeki öğeler (liste maddesi, sayı, karşılaştırma kartları, alt satır, fiyat) anlatıcı
o kelimeyi söylediği an girer. Kelime zamanları ElevenLabs hizalamasından (platform/ortak/altyazi.py).

`bagla(z, ses_dizini)` zamanlanmış senaryonun her sahnesine şunları ekler:
    _an        öğe → sahne başından saniye (bulunamayan öğe yazılmaz; çizim kendi varsayılanını kullanır)
    _kelimeler sahnenin satırındaki kelimeler, sahne başından saniye (alıntı satırları söylendikçe gelir)
ve senaryoya `_altyazi` (altyazı grupları, mutlak saniye). Senaryoda `"senkron": false` girişleri eski sabit
zamanlarına döndürür; altyazı verisi yine üretilir (.srt her zaman yazılır).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import altyazi  # noqa: E402

ONCE = 0.08  # öğe kelimeden biraz önce başlar (giriş animasyonu kelimeyle buluşsun)
EN_GEC = 0.6  # öğe sahne bitmeden en az bu kadar önce girmiş olur


def _anahtarlar(sh: dict) -> list[tuple[str, str]]:
    """(öğe, aranacak metin), ekranda geliş sırasıyla"""
    t = sh["tip"]
    if t == "baslik":
        return [("alt", sh.get("alt", ""))]
    if t == "liste":
        return [(f"madde{j}", x) for j, x in enumerate(sh.get("maddeler") or [])]
    if t == "sayi":
        return [("deger", sh.get("deger", "")), ("etiket", sh.get("etiket", ""))]
    if t == "karsilastirma":
        return [("sol", f"{sh.get('sol', '')} {sh.get('sol_deger', '')}"), ("sag", f"{sh.get('sag', '')} {sh.get('sag_deger', '')}")]
    if t == "urun":
        return [("ozellik", sh.get("ozellik", "")), ("fiyat", sh.get("fiyat", ""))]
    if t == "cta":
        return [("alt", sh.get("alt", ""))]
    return []


def bagla(z: dict, ses_dizini: Path) -> dict:
    z = dict(z)
    satirlar = altyazi.kelimeler(z["seslendirme"].get("satirlar", []), ses_dizini)
    z["_altyazi"] = altyazi.gruplar(satirlar)
    z["_altyazi_kaynak"] = sorted({x["kaynak"] for x in satirlar})
    if z.get("senkron") is False:
        return z
    satir = {x["id"]: x for x in satirlar}
    shs = []
    for i, sh in enumerate(z["sahneler"]):
        sh = dict(sh)
        x = satir.get(f"s{i}")
        if x:
            b, d = sh["bas"], sh["son"] - sh["bas"]
            sh["_kelimeler"] = [{**w, "bas": round(w["bas"] - b, 3), "son": round(w["son"] - b, 3)} for w in x["kelimeler"]]
            an, sonra = {}, -1.0
            for anahtar, metin in _anahtarlar(sh):
                v = altyazi.an(sh["_kelimeler"], metin, sonra)
                if v is None:
                    continue
                an[anahtar] = round(min(max(0.05, v - ONCE), d - EN_GEC), 3)
                sonra = v + 0.01
            sh["_an"] = an
        shs.append(sh)
    z["sahneler"] = shs
    return z


def acik(z: dict) -> bool:
    """yakılı altyazı istendi mi (`"altyazi": true` ya da {"acik": true})"""
    a = z.get("altyazi")
    return a is True or (isinstance(a, dict) and a.get("acik", True))
