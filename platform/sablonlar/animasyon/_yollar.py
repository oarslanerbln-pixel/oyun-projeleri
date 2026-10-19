"""Kardeş platform modüllerini (`marka`, `metin`, `medya`) içe aktarılabilir kılar.

Klasörün adı `platform` olduğu için Python paketi yapılamaz (standart
kitaplıktaki `platform` modülünü gölgeler); modüller tek dosyalık betiklerdir.
"""

import sys
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[2]

for _name in ("marka", "metin", "medya"):
    _path = str(PLATFORM / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)
