"""Video formatları: tek tablo, iki yazım (`9x16` dosya adında, `9:16` senaryoda ve panelde)."""

from __future__ import annotations

FORMATLAR = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}
IKISI = ("9x16", "16x9")


def anahtar(f: str) -> str:
    """`9:16` → `9x16`; bilinmeyen format için ValueError."""
    k = str(f).strip().replace(":", "x")
    if k not in FORMATLAR:
        raise ValueError(f"format bilinmiyor: {f} ({', '.join(sorted(FORMATLAR))})")
    return k


def boyut(f: str) -> tuple[int, int]:
    return FORMATLAR[anahtar(f)]


def coz(istek: str | list[str] | None, senaryo: dict | None = None, varsayilan: list[str] | None = None) -> list[str]:
    """Komut satırı isteği → senaryonun `format` alanı → varsayılan (yalnız 9x16). `ikisi` 9x16 + 16x9 demek.

    Hem tek değer (`"9:16"`) hem liste (`["9x16", "1x1"]`) kabul edilir; sonuç `9x16` yazımıyla döner.
    """
    for aday in (istek, (senaryo or {}).get("format"), varsayilan or ["9x16"]):
        if not aday:
            continue
        liste = [aday] if isinstance(aday, str) else list(aday)
        out: list[str] = []
        for f in liste:
            for k in (IKISI if f == "ikisi" else (anahtar(f),)):
                if k not in out:
                    out.append(k)
        return out
    return ["9x16"]


def bilinmeyenler(liste: str | list[str] | None) -> list[str]:
    liste = [liste] if isinstance(liste, str) else (liste or [])
    return [f for f in liste if f != "ikisi" and str(f).replace(":", "x") not in FORMATLAR]
