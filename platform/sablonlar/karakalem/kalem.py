"""Karakalem çizim araçları (skia): titrek kurşun kalem çizgisi, çift kontur, tarama, kalın uzuv, ışın.

Her çizgi, noktalarına tohumdan (seed) gelen küçük bir sapma eklenerek çizilir; sapma saniyede 12 kez
değişir (`Kalem.kaynat`), böylece çizgiler elle çizilmiş animasyondaki gibi hafifçe "kaynar".
Birimler dünyanındır; ölçek kameradan gelir.
"""

from __future__ import annotations

import math

M32 = 0xFFFFFFFF
KAYNAMA_FPS = 12


def karma(*xs) -> float:
    """durumsuz karma → [0, 1)"""
    h = 2166136261
    for x in xs:
        h ^= int(math.floor(x * 1000003)) & M32
        h = (h * 16777619) & M32
        h ^= h >> 13
        h = (h * 0x5BD1E995) & M32
        h ^= h >> 15
    return h / 4294967296


def gurultu(x: float, seed: float = 0) -> float:
    i = math.floor(x); f = x - i
    a, b = karma(i, seed) * 2 - 1, karma(i + 1, seed) * 2 - 1
    return a + (b - a) * f * f * (3 - 2 * f)


def renk(hex_: str, alfa: float = 1.0) -> int:
    return (int(round(max(0.0, min(1.0, alfa)) * 255)) << 24) | int(hex_.lstrip("#"), 16)


def karistir(a: str, b: str, p: float) -> str:
    x, y = int(a.lstrip("#"), 16), int(b.lstrip("#"), 16)
    c = [round(((x >> s) & 255) * (1 - p) + ((y >> s) & 255) * p) for s in (16, 8, 0)]
    return "#%02X%02X%02X" % tuple(c)


def elips_noktalari(cx, cy, rx, ry, n=0):
    n = n or max(10, round(math.pi * (rx + ry) / 20))
    return [(cx + math.cos(i / n * 2 * math.pi) * rx, cy + math.sin(i / n * 2 * math.pi) * ry) for i in range(n)]


def bol(koseler, adim=22.0, kapali=True):
    """köşe noktaları → aralıklı noktalar (titreme her yere düşsün diye)"""
    out = []
    m = len(koseler) if kapali else len(koseler) - 1
    for i in range(m):
        a, b = koseler[i], koseler[(i + 1) % len(koseler)]
        n = max(1, round(math.dist(a, b) / adim))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    if not kapali:
        out.append(tuple(koseler[-1]))
    return out


def kutu(p):
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return min(xs), min(ys), max(xs), max(ys)


class Kalem:
    def __init__(self, murekkep: str):
        import skia
        self.skia = skia
        self.murekkep = murekkep
        self.kaynama = 0
        self.fps, self.carpan = KAYNAMA_FPS, 1.0  # titreme hızı ve genliği (anlatım senaryosu `titreme` ile azaltır)

    def kaynat(self, t: float) -> None:
        self.kaynama = math.floor(t * self.fps)

    # ---------- noktalar ----------
    def titret(self, pts, seed, amp=1.8):
        b, amp = self.kaynama, amp * self.carpan
        return [(p[0] + (karma(seed, i, b) - 0.5) * 2 * amp, p[1] + (karma(seed, i + 7919, b) - 0.5) * 2 * amp) for i, p in enumerate(pts)]

    def yol(self, p, kapali=True):
        """noktalardan geçen yumuşak yol (orta noktalar arası ikinci derece eğriler)"""
        skia = self.skia
        y = skia.Path(); n = len(p)
        if n < 2:
            return y
        if not kapali:
            y.moveTo(*p[0])
            for i in range(1, n - 1):
                y.quadTo(p[i][0], p[i][1], (p[i][0] + p[i + 1][0]) / 2, (p[i][1] + p[i + 1][1]) / 2)
            y.lineTo(*p[-1])
            return y
        y.moveTo((p[-1][0] + p[0][0]) / 2, (p[-1][1] + p[0][1]) / 2)
        for i in range(n):
            a, b = p[i], p[(i + 1) % n]
            y.quadTo(a[0], a[1], (a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        y.close()
        return y

    def _boya(self, rgb: int, lw: float = 0, cizgi=True, alfa=1.0, kesik=None):
        skia = self.skia
        p = skia.Paint(AntiAlias=True, Color=rgb)
        if cizgi:
            p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(lw)
            p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
        if alfa < 1:
            p.setAlphaf(p.getAlphaf() * alfa)
        if kesik:
            p.setPathEffect(skia.DashPathEffect.Make(kesik, 0))
        return p

    # ---------- çizimler ----------
    def tara(self, cv, kutu_, renk_=0x5A28282E, aralik=8.0, aci=-0.95, lw=1.6, seed=3, oynama=1.5):
        """kutunun içini paralel kalem çizgileriyle tarar (çağıran kırpar)"""
        x0, y0, x1, y1 = kutu_
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        R = math.hypot(x1 - x0, y1 - y0) / 2 + 4
        ca, sa = math.cos(aci), math.sin(aci)
        y = self.skia.Path(); d, k = -R, 0
        oynama *= self.carpan
        while d <= R:
            j1 = (karma(seed, k, self.kaynama) - 0.5) * oynama * 2
            j2 = (karma(seed + 1, k, self.kaynama) - 0.5) * oynama * 2
            y.moveTo(cx - ca * R - sa * (d + j1), cy - sa * R + ca * (d + j1))
            y.lineTo(cx + ca * R - sa * (d + j2), cy + sa * R + ca * (d + j2))
            d += aralik; k += 1
        cv.drawPath(y, self._boya(renk_, lw))

    def sekil(self, cv, pts, dolgu=None, kontur="ink", lw=4.0, seed=1, amp=1.6, tarama=None, ikinci=True, alfa=1.0, kapali=True):
        """dolgu + tarama + çift kalem konturu; `pts` önceden bölünmüş noktalar"""
        p = self.titret(pts, seed, amp) if amp > 0 else list(pts)
        y = self.yol(p, kapali)
        if dolgu and kapali:
            cv.drawPath(y, self._boya(dolgu if isinstance(dolgu, int) else renk(dolgu), cizgi=False, alfa=alfa))
        if tarama and kapali:
            cv.save(); cv.clipPath(y, self.skia.ClipOp.kIntersect, True)
            self.tara(cv, kutu(p), seed=seed + 11, **tarama)
            cv.restore()
        if kontur and lw > 0:
            k = renk(self.murekkep if kontur == "ink" else kontur)
            cv.drawPath(y, self._boya(k, lw, alfa=alfa))
            if ikinci:
                y2 = self.yol(self.titret(pts, seed + 5, amp * 1.4 + 0.6), kapali)
                cv.drawPath(y2, self._boya(k, max(1.0, lw * 0.55), alfa=alfa * 0.3))
        return p

    def elips(self, cv, cx, cy, rx, ry, **o):
        return self.sekil(cv, elips_noktalari(cx, cy, rx, ry), **o)

    def cokgen(self, cv, koseler, adim=22.0, **o):
        return self.sekil(cv, bol(koseler, adim), **o)

    def cizgi(self, cv, pts, renk_=None, lw=4.0, seed=9, amp=1.4, adim=20.0, alfa=1.0, kesik=None):
        """açık, titrek kalem çizgisi"""
        alt = bol(pts, adim, kapali=False) if len(pts) > 1 else list(pts)
        p = self.titret(alt, seed, amp) if amp > 0 else alt
        c = renk_ if isinstance(renk_, int) else renk(renk_ or self.murekkep)
        cv.drawPath(self.yol(p, False), self._boya(c, lw, alfa=alfa, kesik=kesik))

    def uzuv(self, cv, pts, dolgu: str, lw=26.0, kontur=4.0, seed=1):
        """konturlu kalın kol / bacak"""
        y = self.yol(self.titret(pts, seed, 1.2), False)
        cv.drawPath(y, self._boya(renk(self.murekkep), lw + kontur * 2))
        cv.drawPath(y, self._boya(renk(dolgu), lw))

    def isinlar(self, cv, cx, cy, n=36, r0=120.0, r1=1400.0, renk_=None, lw=5.0, seed=1, alfa=1.0):
        c = renk(renk_ or self.murekkep, alfa)
        for i in range(n):
            a = i / n * 2 * math.pi + karma(seed, i, self.kaynama) * 0.12
            a0, a1 = r0 * (0.8 + karma(seed, i, 3) * 0.6), r1 * (0.6 + karma(seed, i, 4) * 0.5)
            y = self.skia.Path(); y.moveTo(cx + math.cos(a) * a0, cy + math.sin(a) * a0); y.lineTo(cx + math.cos(a) * a1, cy + math.sin(a) * a1)
            cv.drawPath(y, self._boya(c, lw * (0.5 + karma(seed, i, 5))))

    def daire(self, cv, x, y, r, rgb: int):
        cv.drawCircle(x, y, r, self._boya(rgb, cizgi=False))
