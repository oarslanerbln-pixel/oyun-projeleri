"""Çizgi roman şablonunun yazı tipi: Bangers (SIL OFL). Bulma ve (bir kez) indirme.

Yazı tipleri depoya girmez (ikili dosyalar LFS'e düşer). `cizgi_roman.py fontlar` Google Fonts
deposundan `~/.cache/studyo/fonts` altına indirir. Bulunamazsa sistemdeki kalın bir yedek kullanılır.
"""

from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path

ONBELLEK = Path.home() / ".cache" / "studyo" / "fonts"
DIZINLER = [os.environ.get("CIZGI_ROMAN_FONT_DIZINI", ""), str(ONBELLEK)]
DOSYA = "Bangers-Regular.ttf"
KAYNAK = "https://raw.githubusercontent.com/google/fonts/main/ofl/bangers/"


def bul() -> str:
    for d in DIZINLER:
        if d and (Path(d) / DOSYA).exists():
            return str(Path(d) / DOSYA)
    r = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans:bold"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    raise RuntimeError("yazı tipi bulunamadı (önce `cizgi_roman.py fontlar`)")


def var_mi() -> bool:
    return any(d and (Path(d) / DOSYA).exists() for d in DIZINLER)


def indir(hedef: Path = ONBELLEK) -> list[Path]:
    hedef.mkdir(parents=True, exist_ok=True)
    out = []
    for ad, kaynak in ((DOSYA, DOSYA), ("OFL-Bangers.txt", "OFL.txt")):
        p = hedef / ad
        if not p.exists():
            urllib.request.urlretrieve(KAYNAK + kaynak, p)
        out.append(p)
    return out
