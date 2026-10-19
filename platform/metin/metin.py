#!/usr/bin/env python3
"""Görünen metin: tek tablo, katmanlı yasak sözlük, uzunluk sınırı (mimari §4.2).

Tablo (CSV): `anahtar, <dil>…, kaynak, not, izin, azami`. `izin` o satırda bilerek
izin verilen sözlük kimliklerini (virgülle) taşır; `azami` her dil için ayrı
ölçülen en çok karakter sayısıdır.

Sözlük (TSV, Kırk Oda biçimi): `kimlik  seviye  dil  desen  gerekçe`. `desen`
küçük harfe çevrilmiş metinde tam sözcük olarak aranan düzenli ifadedir.
Sözlükler sırayla birleşir: `platform/metin/temel.tsv` + marka (`marka.json → ses.yasak`)
+ projenin sözlükleri.

Kullanım:
  metin.py denetle <tablo.csv> [--sozluk a.tsv ...] [--dil tr en ...]

Yalnız Python standart kitaplığı.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HATA = "HATA"
UYARI = "UYARI"
LETTERS = "A-Za-z0-9ÇĞİÖŞÜçğıöşüÂâÎîÛû"
META_COLUMNS = ("anahtar", "kaynak", "not", "izin", "azami")
TEMEL = Path(__file__).resolve().parent / "temel.tsv"


@dataclass(frozen=True)
class Bulgu:
    seviye: str
    yer: str
    mesaj: str

    def __str__(self) -> str:
        return f"{self.seviye} {self.yer}: {self.mesaj}"


def has_errors(bulgular) -> bool:
    return any(b.seviye == HATA for b in bulgular)


def lower(text: str, dil: str) -> str:
    """Türkçede I→ı, İ→i; diğer dillerde olağan küçük harf."""
    if dil == "tr":
        return text.replace("I", "ı").replace("İ", "i").lower()
    return text.replace("İ", "i").lower()


@dataclass(frozen=True)
class Kural:
    kimlik: str
    seviye: str
    dil: str          # "tr", "en" ya da "*" (her dil)
    desen: re.Pattern
    gerekce: str


def kural(kimlik: str, seviye: str, dil: str, desen: str, gerekce: str) -> Kural:
    rx = re.compile(r"(?<![%s])(?:%s)(?![%s])" % (LETTERS, desen, LETTERS))
    return Kural(kimlik, seviye, dil, rx, gerekce)


def sozluk_oku(path: str | Path) -> list[Kural]:
    out = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 5 or parts[1] not in (HATA, UYARI):
            raise ValueError(f"{path}:{n}: 'kimlik<TAB>HATA|UYARI<TAB>dil<TAB>desen<TAB>gerekçe' bekleniyordu")
        out.append(kural(*parts))
    return out


def marka_kurallari(yasak: tuple[str, ...] | list[str]) -> list[Kural]:
    """Markanın yasak ifadeleri: her dilde HATA, büyük/küçük harf ve Türkçe i/ı farkı gözetilmeden."""
    out = []
    for i, ifade in enumerate(yasak, start=1):
        words = ["".join("[iı]" if ch in "iı" else re.escape(ch) for ch in lower(w, "tr")) for w in ifade.split()]
        out.append(kural(f"MARKA-{i}", HATA, "*", r"\s+".join(words), f"marka sesine aykırı: {ifade!r}"))
    return out


def tara(metin: str, dil: str, kurallar: list[Kural], izin: set[str] = frozenset()) -> list[tuple[Kural, str]]:
    low = lower(metin, dil)
    hits = []
    for k in kurallar:
        if (k.dil != dil and k.dil != "*") or k.kimlik in izin:
            continue
        hits += [(k, m.group(0)) for m in k.desen.finditer(low)]
    return hits


@dataclass
class Tablo:
    diller: tuple[str, ...]
    satirlar: dict[str, dict[str, str]] = field(default_factory=dict)  # anahtar → satır

    def al(self, anahtar: str, dil: str) -> str:
        return self.satirlar[anahtar][dil]


def tablo_oku(paths, diller: tuple[str, ...]) -> tuple[Tablo, list[Bulgu]]:
    """Birden çok tabloyu tek sözlükte birleştirir; tekrar eden anahtar HATA'dır."""
    tablo, b = Tablo(tuple(diller)), []
    for path in paths:
        path = Path(path)
        try:
            with path.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                cols = reader.fieldnames or []
                for col in ("anahtar",) + tuple(diller):
                    if col not in cols:
                        b.append(Bulgu(HATA, path.name, f"'{col}' sütunu yok"))
                if has_errors(b):
                    continue
                for n, row in enumerate(reader, start=2):
                    key = (row.get("anahtar") or "").strip()
                    yer = f"{path.name}:{n}"
                    if not key:
                        b.append(Bulgu(HATA, yer, "anahtar boş"))
                    elif key in tablo.satirlar:
                        b.append(Bulgu(HATA, yer, f"anahtar {key!r} tekrar ediyor"))
                    else:
                        tablo.satirlar[key] = {k: (v or "") for k, v in row.items() if k}
        except FileNotFoundError:
            b.append(Bulgu(HATA, str(path), "dosya yok"))
    return tablo, b


def denetle(tablo: Tablo, kurallar: list[Kural]) -> list[Bulgu]:
    b = []
    for key, row in tablo.satirlar.items():
        izin = {a.strip() for a in row.get("izin", "").split(",") if a.strip()}
        azami_raw = row.get("azami", "").strip()
        azami = None
        if azami_raw:
            if azami_raw.isdigit():
                azami = int(azami_raw)
            else:
                b.append(Bulgu(HATA, key, f"azami sayı olmalı, {azami_raw!r} geldi"))
        for dil in tablo.diller:
            text = row.get(dil, "")
            yer = f"{key}/{dil}"
            if not text.strip():
                b.append(Bulgu(UYARI, yer, "çeviri boş"))
                continue
            if azami is not None and len(text) > azami:
                b.append(Bulgu(HATA, yer, f"{len(text)} karakter, en çok {azami}"))
            for k, word in tara(text, dil, kurallar, izin):
                b.append(Bulgu(k.seviye, yer, f"'{word}' ({k.kimlik}) — {k.gerekce}"))
    return b


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="metin.py")
    sub = p.add_subparsers(dest="komut", required=True)
    d = sub.add_parser("denetle")
    d.add_argument("tablo", nargs="+")
    d.add_argument("--sozluk", nargs="*", default=[str(TEMEL)])
    d.add_argument("--dil", nargs="*", default=["tr"])
    args = p.parse_args(argv)
    kurallar = [k for s in args.sozluk for k in sozluk_oku(s)]
    tablo, b = tablo_oku(args.tablo, tuple(args.dil))
    b += denetle(tablo, kurallar)
    for x in b:
        print(x)
    print(f"Satır: {len(tablo.satirlar)} · HATA: {sum(x.seviye == HATA for x in b)} · "
          f"UYARI: {sum(x.seviye == UYARI for x in b)}")
    return 1 if has_errors(b) else 0


if __name__ == "__main__":
    sys.exit(main())
