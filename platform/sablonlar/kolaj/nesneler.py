"""Kolaj nesneleri: dergiden kesilmiş "fotoğraf" gibi görünen, kodla çizilmiş kahve ürünleri.

Her nesne bir siluet, gri tonlu bir ışık/gölge çizimi ve düz spot renk alanları verir; `kagit.kesik_resim`
bunları yarım ton baskıya çevirip makasla keser. Telifli görsel yok. Gerçek ürün fotoğrafı için senaryoda
`"gorsel": "dosya.png"` verilir (bkz. `kagit.gorsel_resim`).
"""

from __future__ import annotations

import math
import random

import skia

from kagit import karistir


def _gri(v: float) -> int:
    g = max(0, min(255, int(v * 255)))
    return 0xFF000000 | (g << 16) | (g << 8) | g


def _yatay(x0, x1, degerler, konumlar=None) -> skia.Paint:
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([(x0, 0), (x1, 0)], [_gri(v) for v in degerler], konumlar))
    return p


def _dikey(y0, y1, degerler) -> skia.Paint:
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([(0, y0), (0, y1)], [_gri(v) for v in degerler]))
    return p


def _yol(*noktalar) -> skia.Path:
    p = skia.Path(); p.moveTo(*noktalar[0])
    for q in noktalar[1:]:
        p.lineTo(*q)
    p.close(); return p


def _oval(x0, y0, x1, y1) -> skia.Path:
    p = skia.Path(); p.addOval(skia.Rect(x0, y0, x1, y1)); return p


SILINDIR = [0.5, 0.82, 0.97, 0.86, 0.6, 0.4]


def bardak(u: float, P: dict):
    """Karton kahve bardağı: kapak, konik gövde, zarf."""
    w, h = 330 * u, 480 * u
    kapak = skia.Path(); kapak.addRRect(skia.RRect.MakeRectXY(skia.Rect(4 * u, 0, w - 4 * u, 38 * u), 12 * u, 12 * u))
    kubbe = _yol((20 * u, 34 * u), (w - 20 * u, 34 * u), (w - 30 * u, 72 * u), (30 * u, 72 * u))
    govde = _yol((32 * u, 70 * u), (w - 32 * u, 70 * u), (w - 66 * u, h), (66 * u, h))
    zarf = _yol((32 * u + 34 * u * 110 / 410, 180 * u), (w - 32 * u - 34 * u * 110 / 410, 180 * u),
                (w - 32 * u - 34 * u * 250 / 410, 320 * u), (32 * u + 34 * u * 250 / 410, 320 * u))
    sil = skia.Op(skia.Op(kapak, kubbe, skia.PathOp.kUnion_PathOp), govde, skia.PathOp.kUnion_PathOp)

    def gri(cv):
        cv.drawPath(govde, _yatay(32 * u, w - 32 * u, [v * 0.98 + 0.02 for v in SILINDIR]))
        cv.drawPath(zarf, _yatay(40 * u, w - 40 * u, [v * 0.62 for v in SILINDIR]))
        cv.drawPath(kubbe, _yatay(20 * u, w - 20 * u, [v * 0.55 for v in SILINDIR]))
        cv.drawPath(kapak, _yatay(4 * u, w - 4 * u, [v * 0.42 for v in SILINDIR]))
        cv.drawRect(skia.Rect(w * 0.6, 10 * u, w * 0.6 + 34 * u, 22 * u), skia.Paint(AntiAlias=True, Color=_gri(0.08)))
        # kesik çizgi dikiş + gövdede ince parlama
        cv.drawPath(_yol((w * 0.38, 76 * u), (w * 0.4, 76 * u), (w * 0.42, h - 6 * u), (w * 0.4, h - 6 * u)),
                    skia.Paint(AntiAlias=True, Color=_gri(1.0)))
    spot = [(zarf, P["ikinci"]), (skia.Op(kapak, kubbe, skia.PathOp.kUnion_PathOp), karistir(P["marka"], "#FFFFFF", 0.25))]
    return w, h, sil, gri, spot


def kupa(u: float, P: dict):
    """Seramik kupa, içinde kahve; buhar ayrı (kalemle) çizilir."""
    w, h = 440 * u, 380 * u
    govde = skia.Path()
    govde.addRRect(skia.RRect.MakeRectXY(skia.Rect(30 * u, 40 * u, 330 * u, 370 * u), 46 * u, 46 * u))
    ust = skia.Path(); ust.addRect(skia.Rect(30 * u, 40 * u, 330 * u, 120 * u))
    govde = skia.Op(govde, ust, skia.PathOp.kUnion_PathOp)
    agiz = _oval(30 * u, 16 * u, 330 * u, 66 * u)
    kahve = _oval(46 * u, 25 * u, 314 * u, 58 * u)
    sap = skia.Op(_oval(282 * u, 110 * u, 432 * u, 310 * u), _oval(318 * u, 150 * u, 398 * u, 270 * u), skia.PathOp.kDifference_PathOp)
    sap = skia.Op(sap, govde, skia.PathOp.kDifference_PathOp)
    sil = skia.Op(skia.Op(govde, agiz, skia.PathOp.kUnion_PathOp), sap, skia.PathOp.kUnion_PathOp)

    def gri(cv):
        cv.drawPath(govde, _yatay(30 * u, 330 * u, SILINDIR))
        cv.drawPath(sap, _yatay(290 * u, 432 * u, [0.75, 0.55, 0.32]))
        cv.drawPath(agiz, skia.Paint(AntiAlias=True, Color=_gri(0.9)))
        cv.drawPath(kahve, _yatay(46 * u, 314 * u, [0.12, 0.22, 0.3, 0.18]))
        cv.drawPath(_oval(110 * u, 32 * u, 230 * u, 50 * u), skia.Paint(AntiAlias=True, Color=_gri(0.42)))  # köpük
    spot = [(skia.Op(govde, sap, skia.PathOp.kUnion_PathOp), P["vurgu"]), (kahve, P["marka"])]
    return w, h, sil, gri, spot


def simit(u: float, P: dict):
    """Susamlı simit: kalın, burgulu halka, hafif yukarıdan."""
    w, h = 560 * u, 400 * u
    ust = _oval(0, 20 * u, w, 360 * u)
    alt = _oval(4 * u, 52 * u, w - 4 * u, 392 * u)
    delik = _oval(150 * u, 128 * u, 410 * u, 254 * u)
    sil = skia.Op(skia.Op(ust, alt, skia.PathOp.kUnion_PathOp), delik, skia.PathOp.kDifference_PathOp)
    rnd = random.Random(11)
    cx, cy = w / 2, 190 * u

    def gri(cv):
        cv.drawPath(alt, skia.Paint(AntiAlias=True, Color=_gri(0.6)))
        cv.drawPath(ust, _dikey(20 * u, 360 * u, [0.97, 0.86, 0.7]))
        # burgu: halka boyunca eğik koyu şeritler
        for i in range(30):
            a = 2 * math.pi * i / 30
            ox, oy = cx + 272 * u * math.cos(a), cy + 165 * u * math.sin(a)
            ix, iy = cx + 138 * u * math.cos(a + 0.22), cy + 70 * u * math.sin(a + 0.22)
            p = skia.Path(); p.moveTo(ox, oy); p.quadTo((ox + ix) / 2 + 22 * u * math.cos(a + 1.6), (oy + iy) / 2 + 14 * u * math.sin(a + 1.6), ix, iy)
            cv.drawPath(p, skia.Paint(AntiAlias=True, Color=_gri(0.45), Style=skia.Paint.kStroke_Style, StrokeWidth=16 * u,
                                      StrokeCap=skia.Paint.kRound_Cap, Alphaf=0.6))
        # delik çevresi gölgesi
        cv.drawPath(_oval(140 * u, 118 * u, 420 * u, 264 * u), skia.Paint(AntiAlias=True, Color=_gri(0.42), Style=skia.Paint.kStroke_Style,
                                                                     StrokeWidth=20 * u))
    susam = skia.Path()
    for _ in range(150):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.6, 0.96)
        x, y = cx + 276 * u * r * math.cos(a), cy + 168 * u * r * math.sin(a)
        if ((x - cx) / (150 * u)) ** 2 + ((y - cy - 3 * u) / (78 * u)) ** 2 < 1.25:
            continue
        m = skia.Matrix.RotateDeg(rnd.uniform(0, 180)); m.postTranslate(x, y)
        o = skia.Path(); o.addOval(skia.Rect(-7 * u, -3.6 * u, 7 * u, 3.6 * u)); o.transform(m)
        susam.addPath(o)
    spot = [(sil, karistir(P["ikinci"], P["marka"], 0.25))]
    return w, h, sil, gri, spot, [(susam, "#F6ECD6")]


def cekirdek(u: float, P: dict):
    """Kahve çekirdeği."""
    w, h = 170 * u, 230 * u
    sil = _oval(0, 0, w, h)
    yarik = skia.Path(); yarik.moveTo(w / 2 + 4 * u, 14 * u); yarik.cubicTo(w * 0.28, h * 0.36, w * 0.72, h * 0.62, w / 2 - 4 * u, h - 14 * u)

    def gri(cv):
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeLinear([(0, 0), (w, h)], [_gri(0.9), _gri(0.6), _gri(0.38)]))
        cv.drawPath(sil, p)
        cv.drawPath(yarik, skia.Paint(AntiAlias=True, Color=_gri(0.0), Style=skia.Paint.kStroke_Style, StrokeWidth=15 * u,
                                      StrokeCap=skia.Paint.kRound_Cap))
    spot = [(sil, karistir(P["marka"], P["ikinci"], 0.35))]
    return w, h, sil, gri, spot


NESNELER = {"bardak": bardak, "kupa": kupa, "simit": simit, "cekirdek": cekirdek}
HUCRE = {"bardak": 9.0, "kupa": 9.0, "simit": 9.5, "cekirdek": 6.5}
