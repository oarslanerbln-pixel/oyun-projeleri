"""Risograf şablonunun yazı tipi: Archivo Black (SIL OFL). Bulma ve (bir kez) indirme.

Yazı tipleri depoya girmez (ikili dosyalar LFS'e düşer). `risograf.py fontlar` Google Fonts
deposundan `~/.cache/studyo/fonts` altına indirir. Bulunamazsa sistemdeki kalın bir yedek kullanılır.
"""

from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path

ONBELLEK = Path.home() / ".cache" / "studyo" / "fonts"
DIZINLER = [os.environ.get("RISOGRAF_FONT_DIZINI", ""), str(ONBELLEK)]
DOSYA = "ArchivoBlack-Regular.ttf"
KAYNAK = "https://raw.githubusercontent.com/google/fonts/main/ofl/archivoblack/"


def bul() -> str:
    for d in DIZINLER:
        if d and (Path(d) / DOSYA).exists():
            return str(Path(d) / DOSYA)
    r = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans:bold"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    raise RuntimeError("yazı tipi bulunamadı (önce `risograf.py fontlar`)")


def var_mi() -> bool:
    return any(d and (Path(d) / DOSYA).exists() for d in DIZINLER)


def indir(hedef: Path = ONBELLEK) -> list[Path]:
    hedef.mkdir(parents=True, exist_ok=True)
    out = []
    for ad, kaynak in ((DOSYA, DOSYA), ("OFL-ArchivoBlack.txt", "OFL.txt")):
        p = hedef / ad
        if not p.exists():
            urllib.request.urlretrieve(KAYNAK + kaynak, p)
        out.append(p)
    return out
