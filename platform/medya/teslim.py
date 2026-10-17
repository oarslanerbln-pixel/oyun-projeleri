#!/usr/bin/env python3
"""Teslim ön ayarlarını okur (`teslim.json`, mimari §4.3).

Ön ayar bir master'dan kanal başına türevin tanımıdır: oran, çözünürlük,
loudness, varsa süre sınırı ve güvenli alan. Değerler veri dosyasındadır;
kod yalnız okur.

Kullanım:
  teslim.py listele
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from math import gcd
from pathlib import Path

DOSYA = Path(__file__).resolve().parent / "teslim.json"
VARSAYILAN_GUVENLI = 0.05


@dataclass(frozen=True)
class OnAyar:
    ad: str
    genislik: int
    yukseklik: int
    lufs: float | None = None
    sure_siniri: float | None = None
    sinir_kontrol: str = ""
    guvenli_ust: float = VARSAYILAN_GUVENLI
    guvenli_alt: float = VARSAYILAN_GUVENLI
    guvenli_yan: float = VARSAYILAN_GUVENLI
    not_: str = ""

    @property
    def oran(self) -> str:
        g = gcd(self.genislik, self.yukseklik)
        return f"{self.genislik // g}:{self.yukseklik // g}"


def yukle(path: str | Path = DOSYA) -> dict[str, OnAyar]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for ad, d in data["on_ayarlar"].items():
        sinir = d.get("sure_siniri") or {}
        alan = d.get("guvenli_alan") or {}
        out[ad] = OnAyar(
            ad=ad, genislik=d["genislik"], yukseklik=d["yukseklik"], lufs=d.get("lufs"),
            sure_siniri=sinir.get("sn"), sinir_kontrol=sinir.get("kontrol", ""),
            guvenli_ust=alan.get("ust", VARSAYILAN_GUVENLI), guvenli_alt=alan.get("alt", VARSAYILAN_GUVENLI),
            guvenli_yan=alan.get("yan", VARSAYILAN_GUVENLI), not_=d.get("not", ""),
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["listele"]:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    for a in yukle().values():
        sinir = f"en çok {a.sure_siniri:g} sn (kontrol {a.sinir_kontrol})" if a.sure_siniri else "süre sınırı yok"
        print(f"{a.ad:<15} {a.genislik}×{a.yukseklik} ({a.oran}) · {sinir} · {a.not_}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
