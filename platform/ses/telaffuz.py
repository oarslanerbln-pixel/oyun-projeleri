"""Telaffuz sözlüğü: marka ve yer adları seslendirmeye gitmeden önce okunuşuyla değiştirilir.

ElevenLabs ve Piper yabancı adları (Residenzstraße, Mezquita, LÉVA) yanlış okuyabiliyor. Ekrandaki yazı
değişmez; yalnız sese giden metin değişir. Sözlükler, sonraki öncekini ezer:

1. Ortak: `platform/ses/telaffuz/<dil>.tsv` (sesin diline göre; `yazılış<TAB>okunuş`, `#` açıklama).
2. Proje: senaryonun klasöründeki `telaffuz.tsv` (her dil için) ve `telaffuz.<dil>.tsv`.
3. Senaryo: `"seslendirme": {"telaffuz": {"LÉVA": "Leva"}}`.

Eşleşme bütün kelimedir (Unicode), büyük/küçük harf yazıldığı gibi; uzun adlar önce değişir. Satırın kendi
`okunus` alanı varsa sözlük onun üstünde de çalışır. Seslendirme önbelleği okunan metne göre tutulduğu
için sözlüğe eklenen ad yalnız o adın geçtiği satırları yeniden seslendirir.

    python3 platform/ses/telaffuz.py dene "Residenzstraße 109'da The Leaf" --dil tr [--klasor proje/]
    python3 platform/ses/telaffuz.py liste --dil de
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ORTAK = Path(__file__).resolve().parent / "telaffuz"


def tsv_oku(yol: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not yol.exists():
        return out
    for satir in yol.read_text(encoding="utf-8").splitlines():
        if not satir.strip() or satir.lstrip().startswith("#") or "\t" not in satir:
            continue
        yazilis, okunus = (x.strip() for x in satir.split("\t", 1))
        if yazilis and okunus:
            out[yazilis] = okunus
    return out


def sozluk(dil: str = "tr", klasor: str | Path | None = None, ek: dict | None = None) -> dict[str, str]:
    """Ortak + proje klasörü + senaryo sözlüğünü birleştirir (sonraki öncekini ezer)."""
    s = tsv_oku(ORTAK / f"{dil}.tsv")
    if klasor:
        s.update(tsv_oku(Path(klasor) / "telaffuz.tsv"))
        s.update(tsv_oku(Path(klasor) / f"telaffuz.{dil}.tsv"))
    s.update({k: v for k, v in (ek or {}).items() if k and v})
    return s


def degistir(metin: str, s: dict[str, str]) -> str:
    if not s:
        return metin
    adlar = sorted(s, key=len, reverse=True)
    desen = re.compile(r"(?<!\w)(" + "|".join(re.escape(a) for a in adlar) + r")(?!\w)")
    return desen.sub(lambda m: s[m.group(1)], metin)


def uygula(satirlar: list[dict], dil: str = "tr", klasor: str | Path | None = None, ek: dict | None = None) -> list[dict]:
    """Seslendirmenin tek bağlantı noktası: satırların `metin`ini okunuşla değiştirilmiş kopyasını döner."""
    s = sozluk(dil, klasor, ek)
    if not s:
        return satirlar
    out = []
    for x in satirlar:
        y = dict(x)
        y["metin"] = degistir(x["metin"], s)
        out.append(y)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    d = alt.add_parser("dene", help="bir cümlenin sese giden halini göster")
    d.add_argument("metin")
    lst = alt.add_parser("liste", help="bir dilin birleşik sözlüğünü göster")
    for p in (d, lst):
        p.add_argument("--dil", default="tr")
        p.add_argument("--klasor", help="proje klasörü (telaffuz.tsv)")
    a = ap.parse_args(argv)
    s = sozluk(a.dil, a.klasor)
    if a.komut == "dene":
        print(degistir(a.metin, s))
    else:
        for k, v in sorted(s.items()):
            print(f"{k}\t{v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
