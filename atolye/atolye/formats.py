"""Kanal biçimleri: çözünürlük, en uzun süre ve güvenli alan.

Güvenli alan, platform arayüzünün (beğeni düğmeleri, altyazı çubuğu) kapattığı
kenarların dışında kalan bölgedir; metin bunun içinde kalmalıdır.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Format:
    id: str
    label: str
    width: int
    height: int
    max_seconds: float
    # Güvenli alan kenar boşlukları, kare yüksekliğinin/genişliğinin oranı
    safe_top: float = 0.05
    safe_bottom: float = 0.05
    safe_side: float = 0.05

    @property
    def aspect(self) -> str:
        from math import gcd
        g = gcd(self.width, self.height)
        return f"{self.width // g}:{self.height // g}"


FORMATS: dict[str, Format] = {f.id: f for f in (
    Format("youtube", "YouTube / web 16:9", 1920, 1080, 600),
    Format("bumper", "YouTube bumper 16:9", 1920, 1080, 6),
    Format("reels", "Instagram Reels / TikTok / Shorts 9:16", 1080, 1920, 90,
           safe_top=0.14, safe_bottom=0.20, safe_side=0.06),
    Format("story", "Instagram / Facebook hikâye 9:16", 1080, 1920, 15,
           safe_top=0.14, safe_bottom=0.20, safe_side=0.06),
    Format("feed-square", "Akış 1:1", 1080, 1080, 60),
    Format("feed-portrait", "Akış 4:5", 1080, 1350, 60),
    Format("game-trailer", "Oyun fragmanı 16:9 (Steam)", 1920, 1080, 120),
)}


def get(format_id: str) -> Format:
    return FORMATS[format_id]
