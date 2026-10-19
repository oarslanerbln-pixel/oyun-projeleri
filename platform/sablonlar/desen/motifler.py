"""Desen şablonunun motif kitaplığı: her motif [-1, 1] karesinde, sırayla boyanan çokgenlerdir.

Bir motif `[(nokta_listesi, dolu), ...]` döndürür; `dolu=False` olan parça öncekilerden oyulur (fincan kulpu,
yaprak damarı). Dört stil aynı geometriyi kendi diliyle yorumlar: vitrayda kurşun çizgili cam, linolde oyulmuş
mürekkep, çinide sırlı madalyon, teknik çizimde cetvelle çizilen kontur. Bağımlılık yok (CI denetimi için).
"""

from __future__ import annotations

import math

Nokta = tuple[float, float]


def _daire(cx: float, cy: float, r: float, n: int = 72, ry: float | None = None) -> list[Nokta]:
    ry = r if ry is None else ry
    return [(cx + r * math.cos(i / n * math.tau), cy + ry * math.sin(i / n * math.tau)) for i in range(n)]


def _yay(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def gunes():
    out = [(_daire(0, 0, 0.46), True)]
    for i in range(12):
        a = i / 12 * math.tau - math.pi / 2
        r1, r2, g = 0.58, (0.96 if i % 2 == 0 else 0.80), 0.13
        out.append(([(r1 * math.cos(a - g), r1 * math.sin(a - g)), (r2 * math.cos(a), r2 * math.sin(a)),
                     (r1 * math.cos(a + g), r1 * math.sin(a + g))], True))
    return out


def kalp():
    p = []
    for i in range(96):
        a = i / 96 * math.tau
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        p.append((x / 17.0, -y / 17.0 - 0.15))
    return [(p, True)]


def yildiz():
    p = []
    for i in range(10):
        r = 0.95 if i % 2 == 0 else 0.40
        a = i / 10 * math.tau - math.pi / 2
        p.append((r * math.cos(a), r * math.sin(a) + 0.06))
    return [(p, True)]


def fincan():
    govde = [(-0.62, -0.30), (0.42, -0.30), (0.40, 0.08)] + _yay(-0.10, 0.08, 0.50, 0, math.pi)[1:] + [(-0.62, 0.08)]
    return [
        (_daire(0.44, -0.06, 0.26), True),
        (_daire(0.44, -0.06, 0.14), False),
        (govde, True),
        (_daire(-0.10, 0.70, 0.86, ry=0.11), True),
        ([(-0.32, -0.85), (-0.24, -0.85), (-0.30, -0.40), (-0.38, -0.40)], True),  # buhar
        ([(-0.06, -0.95), (0.02, -0.95), (-0.04, -0.42), (-0.12, -0.42)], True),
        ([(0.20, -0.85), (0.28, -0.85), (0.22, -0.40), (0.14, -0.40)], True),
    ]


def ampul():
    cam = _yay(0, -0.28, 0.58, math.radians(140), math.radians(400), 48)
    cam += [(0.22, 0.42), (-0.22, 0.42)]
    return [
        (cam, True),
        ([(-0.24, 0.48), (0.24, 0.48), (0.24, 0.58), (-0.24, 0.58)], True),
        ([(-0.22, 0.64), (0.22, 0.64), (0.22, 0.74), (-0.22, 0.74)], True),
        ([(-0.14, 0.80), (0.14, 0.80), (0.08, 0.92), (-0.08, 0.92)], True),
        ([(-0.05, 0.40), (0.05, 0.40), (0.05, -0.18), (-0.05, -0.18)], False),  # tel
    ]


def yaprak():
    sol = [(0.0, 0.95)] + [(-0.62 * math.sin(math.pi * i / 30), 0.95 - 1.85 * i / 30) for i in range(1, 30)] + [(0.0, -0.90)]
    sag = [(0.62 * math.sin(math.pi * i / 30), 0.95 - 1.85 * i / 30) for i in range(29, 0, -1)]
    return [
        (sol + sag, True),
        ([(-0.025, 0.95), (0.025, 0.95), (0.025, -0.70), (-0.025, -0.70)], False),
        ([(0.0, 0.20), (0.36, -0.18), (0.36, -0.10), (0.0, 0.29)], False),
        ([(0.0, 0.55), (-0.38, 0.17), (-0.38, 0.25), (0.0, 0.64)], False),
    ]


def dag():
    return [
        ([(-0.98, 0.70), (-0.30, -0.55), (0.10, 0.12), (0.34, -0.22), (0.98, 0.70)], True),
        ([(-0.30, -0.55), (-0.13, -0.24), (-0.24, -0.30), (-0.32, -0.20), (-0.43, -0.31)], False),  # kar
        (_daire(0.56, -0.62, 0.20), True),
    ]


def ok():
    return [([(0.0, -0.95), (0.62, -0.25), (0.22, -0.25), (0.22, 0.90), (-0.22, 0.90), (-0.22, -0.25), (-0.62, -0.25)], True)]


def ev():
    return [
        ([(0.0, -0.92), (0.90, -0.10), (0.66, -0.10), (0.66, 0.82), (-0.66, 0.82), (-0.66, -0.10), (-0.90, -0.10)], True),
        ([(-0.18, 0.82), (0.18, 0.82), (0.18, 0.30), (-0.18, 0.30)], False),
        (_daire(0.0, -0.30, 0.13, 32), False),
    ]


MOTIFLER = {"gunes": gunes, "kalp": kalp, "yildiz": yildiz, "fincan": fincan, "ampul": ampul,
            "yaprak": yaprak, "dag": dag, "ok": ok, "ev": ev}


def parcalar(ad: str) -> list[tuple[list[Nokta], bool]]:
    return MOTIFLER[ad]()


def konturlar(ad: str) -> list[list[Nokta]]:
    """Teknik çizim için kapalı yollar (ilk nokta sona eklenmiş), boyanma sırasıyla."""
    return [p + [p[0]] for p, _ in parcalar(ad)]
