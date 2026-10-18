"""Kolaj şablonunun yazı tipleri: bulma ve (bir kez) indirme.

Yazı tipleri depoya girmez (ikili dosyalar LFS'e düşer). `kolaj.py fontlar` hepsini Google Fonts
deposundan (SIL OFL) `~/.cache/studyo/fonts` altına indirir; Fraunces değişken yazı tipinden
fontTools ile sabit kesimler çıkarılır. Bulunamayan yazı tipi yerine sistemdeki bir yedek kullanılır
(DejaVu / Liberation), böylece render hiç durmaz, yalnız görünüş sadeleşir.
"""

from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path

ONBELLEK = Path.home() / ".cache" / "studyo" / "fonts"
DIZINLER = [os.environ.get("KOLAJ_FONT_DIZINI", ""), str(ONBELLEK), "/usr/share/fonts/opentype/inter",
            "/usr/share/fonts/truetype/inter", str(Path.home() / "Library/Fonts"), "/Library/Fonts"]
# ad → (dosya adları, fontconfig yedeği)
FONTLAR = {
    "fraunces": (["Fraunces-Black.ttf"], "DejaVu Serif:bold"),
    "fraunces-italik": (["Fraunces-BoldItalic.ttf"], "DejaVu Serif:bold:italic"),
    "archivo": (["ArchivoBlack-Regular.ttf"], "DejaVu Sans:bold"),
    "anton": (["Anton-Regular.ttf"], "DejaVu Sans Condensed:bold"),
    "abril": (["AbrilFatface-Regular.ttf"], "Liberation Serif:bold"),
    "courier": (["CourierPrime-Bold.ttf"], "Liberation Mono:bold"),
    "inter": (["Inter-ExtraBold.otf", "Inter-800.ttf", "Inter-ExtraBold.ttf"], "DejaVu Sans:bold"),
}
KAYNAK = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
INDIRILECEK = {
    "Fraunces[SOFT,WONK,opsz,wght].ttf": "fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf",
    "Fraunces-Italic[SOFT,WONK,opsz,wght].ttf": "fraunces/Fraunces-Italic%5BSOFT,WONK,opsz,wght%5D.ttf",
    "ArchivoBlack-Regular.ttf": "archivoblack/ArchivoBlack-Regular.ttf",
    "Anton-Regular.ttf": "anton/Anton-Regular.ttf",
    "AbrilFatface-Regular.ttf": "abrilfatface/AbrilFatface-Regular.ttf",
    "CourierPrime-Bold.ttf": "courierprime/CourierPrime-Bold.ttf",
    "OFL-Fraunces.txt": "fraunces/OFL.txt",
}
# değişken Fraunces → sabit kesimler (WONK=1: eğik yaprak biçimli harfler, dergi başlığı havası)
KESIMLER = {
    "Fraunces-Black.ttf": ("Fraunces[SOFT,WONK,opsz,wght].ttf", {"wght": 900, "opsz": 144, "SOFT": 0, "WONK": 1}),
    "Fraunces-BoldItalic.ttf": ("Fraunces-Italic[SOFT,WONK,opsz,wght].ttf", {"wght": 700, "opsz": 144, "SOFT": 50, "WONK": 1}),
}


def bul(ad: str) -> str:
    dosyalar, yedek = FONTLAR[ad]
    for d in DIZINLER:
        for f in dosyalar:
            if d and (Path(d) / f).exists():
                return str(Path(d) / f)
    r = subprocess.run(["fc-match", "-f", "%{file}", yedek], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    raise RuntimeError(f"yazı tipi bulunamadı: {ad} (önce `kolaj.py fontlar`)")


def eksikler() -> list[str]:
    return [ad for ad, (dosyalar, _) in FONTLAR.items()
            if not any(d and (Path(d) / f).exists() for d in DIZINLER for f in dosyalar)]


def indir(hedef: Path = ONBELLEK) -> list[Path]:
    hedef.mkdir(parents=True, exist_ok=True)
    out = []
    for ad, yol in INDIRILECEK.items():
        p = hedef / ad
        if not p.exists():
            urllib.request.urlretrieve(KAYNAK + yol, p)
        out.append(p)
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    except ImportError:
        print("UYARI: fontTools yok (`pip install fonttools`); Fraunces yerine yedek yazı tipi kullanılacak.")
        return out
    for ad, (kaynak, eksen) in KESIMLER.items():
        p = hedef / ad
        if not p.exists():
            f = TTFont(hedef / kaynak)
            instancer.instantiateVariableFont(f, eksen, inplace=True)
            f.save(p)
        out.append(p)
    return out
