"""Karakalem şablonunun yazı tipleri: el yazısı (Caveat) ve damga (Permanent Marker).

Yazı tipleri depoya girmez (ikili dosyalar LFS'e düşer). `karakalem.py fontlar` ikisini Google Fonts
deposundan `~/.cache/studyo/fonts` altına indirir; Caveat değişken yazı tipinden fontTools ile kalın
(wght 700) kesim çıkarılır. Bulunamayan yazı tipi yerine sistemdeki bir yedek kullanılır, render durmaz.
"""

from __future__ import annotations

import os
import subprocess
import urllib.request
from pathlib import Path

ONBELLEK = Path.home() / ".cache" / "studyo" / "fonts"
DIZINLER = [os.environ.get("KARAKALEM_FONT_DIZINI", ""), str(ONBELLEK), str(Path.home() / "Library/Fonts"), "/Library/Fonts"]
# ad → (dosya adları, fontconfig yedeği)
FONTLAR = {
    "el": (["Caveat-Bold.ttf"], "DejaVu Sans:bold"),
    "damga": (["PermanentMarker-Regular.ttf"], "DejaVu Sans:bold"),
}
KAYNAK = "https://raw.githubusercontent.com/google/fonts/main/"
INDIRILECEK = {
    "Caveat[wght].ttf": "ofl/caveat/Caveat%5Bwght%5D.ttf",
    "OFL-Caveat.txt": "ofl/caveat/OFL.txt",
    "PermanentMarker-Regular.ttf": "apache/permanentmarker/PermanentMarker-Regular.ttf",
    "LICENSE-PermanentMarker.txt": "apache/permanentmarker/LICENSE.txt",
}
KESIMLER = {"Caveat-Bold.ttf": ("Caveat[wght].ttf", {"wght": 700})}


def bul(ad: str) -> str:
    dosyalar, yedek = FONTLAR[ad]
    for d in DIZINLER:
        for f in dosyalar:
            if d and (Path(d) / f).exists():
                return str(Path(d) / f)
    r = subprocess.run(["fc-match", "-f", "%{file}", yedek], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    raise RuntimeError(f"yazı tipi bulunamadı: {ad} (önce `karakalem.py fontlar`)")


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
        print("UYARI: fontTools yok (`pip install fonttools`); Caveat yerine yedek yazı tipi kullanılacak.")
        return out
    for ad, (kaynak, eksen) in KESIMLER.items():
        p = hedef / ad
        if not p.exists():
            f = TTFont(hedef / kaynak)
            instancer.instantiateVariableFont(f, eksen, inplace=True)
            f.save(p)
        out.append(p)
    return out
