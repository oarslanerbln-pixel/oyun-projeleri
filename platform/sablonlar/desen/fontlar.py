"""Desen şablonunun yazı tipi: Inter (SIL OFL), ağırlık başına statik dosya.

Sıra: DESEN_FONT_DIZINI → ~/.cache/studyo/fonts/Inter-<ağırlık>.ttf (stil motorunun önbelleği; yoksa değişken Inter
indirilip fontTools ile örneklenir) → sistemdeki Inter (fc-match) → DejaVu Sans Bold (uyarıyla).
"""

from __future__ import annotations

import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ONBELLEK = Path(os.environ.get("STIL_FONT_DIZINI", Path.home() / ".cache" / "studyo" / "fonts"))
INTER_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"
_SISTEM = {900: "Inter:black", 800: "Inter:extrabold", 700: "Inter:bold", 600: "Inter:semibold", 500: "Inter:medium"}
_bulunan: dict[int, str] = {}


def _fc(desen: str) -> str | None:
    try:
        r = subprocess.run(["fc-match", "-f", "%{file}", desen], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def yol(agirlik: int = 800) -> str:
    if agirlik in _bulunan:
        return _bulunan[agirlik]
    ad = f"Inter-{agirlik}.ttf"
    for d in (os.environ.get("DESEN_FONT_DIZINI", ""), str(ONBELLEK)):
        if d and (Path(d) / ad).exists():
            _bulunan[agirlik] = str(Path(d) / ad)
            return _bulunan[agirlik]
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
        ONBELLEK.mkdir(parents=True, exist_ok=True)
        degisken = ONBELLEK / "Inter-degisken.ttf"
        if not degisken.exists():
            urllib.request.urlretrieve(INTER_URL, str(degisken) + ".indiriliyor")
            os.replace(str(degisken) + ".indiriliyor", degisken)
        instantiateVariableFont(TTFont(degisken), {"wght": agirlik, "opsz": 32}).save(ONBELLEK / ad)
        _bulunan[agirlik] = str(ONBELLEK / ad)
        return _bulunan[agirlik]
    except Exception as e:  # ağ ya da fontTools yoksa sistemdeki Inter
        sistem = _fc(_SISTEM.get(agirlik, "Inter:bold"))
        if sistem and "inter" in Path(sistem).name.lower():
            _bulunan[agirlik] = sistem
            return sistem
        print(f"UYARI Inter {agirlik} bulunamadı ({e}); DejaVu Sans kullanılıyor", file=sys.stderr)
        _bulunan[agirlik] = _fc("DejaVu Sans:bold") or "DejaVuSans-Bold.ttf"
        return _bulunan[agirlik]
