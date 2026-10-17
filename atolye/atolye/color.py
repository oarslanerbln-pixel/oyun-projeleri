"""Renk yardımcıları: hex ayrıştırma ve WCAG 2.1 kontrast oranı."""

from __future__ import annotations

import re

_HEX = re.compile(r"^#([0-9a-fA-F]{6})$")

# WCAG 2.1 AA eşikleri
CONTRAST_TEXT = 4.5   # gövde metni
CONTRAST_LARGE = 3.0  # başlık (büyük metin)


def is_hex(value: object) -> bool:
    return isinstance(value, str) and _HEX.match(value) is not None


def to_rgb(value: str) -> tuple[int, int, int]:
    m = _HEX.match(value)
    if not m:
        raise ValueError(f"#RRGGBB biçiminde değil: {value!r}")
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def relative_luminance(value: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)
