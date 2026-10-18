"""Gölge oyunu şablonunun görüntüsü: aydınlatılmış perde önünde renkli, yarı saydam deri kuklalar.

Her kukla parçası düz renkli yarı saydam dolgu, zımba delikleri (delikten perde ışığı görünür) ve koyu
konturdan oluşur; eklemlerde pim, altta kuklacının çubuğu vardır. Levhalar perdeye "yaklaşarak" bulanık iri
gölgeden keskin kuklaya döner. Perde düz renktir (degrade ya da parlama yok). Kare `t` anının saf fonksiyonudur.
"""

from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

import skia

FONT_ADLARI = ["InterDisplay-Black.otf", "Inter-Black.otf", "Inter-ExtraBold.otf", "Inter-800.ttf", "Inter-ExtraBold.ttf"]
FONT_DIZINLERI = [os.environ.get("KINETIK_FONT_DIZINI", ""), "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
                  str(Path.home() / ".fonts"), "/Library/Fonts", str(Path.home() / "Library/Fonts")]


def font_bul() -> str:
    for d in FONT_DIZINLERI:
        for ad in FONT_ADLARI:
            if d and os.path.exists(os.path.join(d, ad)):
                return os.path.join(d, ad)
    raise RuntimeError("Inter yazı tipi bulunamadı: `apt-get install fonts-inter` ya da KINETIK_FONT_DIZINI")


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, p): return a + (b - a) * p
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def in_out_cubic(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_back(p, s=1.9): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def argb(hex_: str) -> int:
    return 0xFF000000 | int(hex_.lstrip("#"), 16)


def yol(noktalar, kapali=True):
    p = skia.Path(); p.moveTo(*noktalar[0])
    for n in noktalar[1:]:
        p.lineTo(*n)
    if kapali:
        p.close()
    return p


def egri(noktalar):
    """noktalardan geçen yumuşak kapalı yol (Catmull-Rom → kübik Bezier)"""
    p = skia.Path(); n = len(noktalar); p.moveTo(*noktalar[0])
    for i in range(n):
        p0, p1, p2, p3 = noktalar[i - 1], noktalar[i], noktalar[(i + 1) % n], noktalar[(i + 2) % n]
        p.cubicTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                  p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1])
    p.close()
    return p


def nokta_dizisi(x0, y0, x1, y1, n, r):
    return [(lerp(x0, x1, i / max(1, n - 1)), lerp(y0, y1, i / max(1, n - 1)), r) for i in range(n)]


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        self.s, self.W, self.H = s, W, H
        self.P = {k: argb(v) for k, v in s["palet"].items()}
        self.K = {k: self.P[v] for k, v in s["kukla"].items()}
        self.TF = skia.Typeface.MakeFromFile(font_bul())
        self.u = min(W, H) / 1080
        self.VW, self.VH = W / self.u, H / self.u
        self.dik = self.VH / self.VW > 1.5          # yalnız 9:16 dikey yerleşim kullanır
        self.yer = self.VH - (300 if self.dik else 170) + 40
        self.gecisler = [sh["bas"] for sh in s["sahneler"][1:] if sh["gecis"] == "lale"]

    # ---------- temel ----------
    def boya(self, renk, a=1.0, cizgi=0.0):
        p = skia.Paint(AntiAlias=True, Color=renk)
        p.setAlphaf(a)
        if cizgi:
            p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(cizgi)
            p.setStrokeJoin(skia.Paint.kRound_Join); p.setStrokeCap(skia.Paint.kRound_Cap)
        return p

    def font(self, boy):
        f = skia.Font(self.TF, boy); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True)
        return f

    def deri(self, cv, p, renk, delikler=(), a=0.9, kalin=3.5):
        """yarı saydam boyalı deri parça: dolgu, zımba delikleri, kontur"""
        cv.drawPath(p, self.boya(renk, a))
        isik = self.boya(self.P["isik"], 0.95)
        for x, y, r in delikler:
            cv.drawCircle(x, y, r, isik)
        cv.drawPath(p, self.boya(self.P["kontur"], 1, kalin))

    def pim(self, cv, x, y):
        cv.drawCircle(x, y, 4.5, self.boya(self.P["kontur"])); cv.drawCircle(x, y, 1.8, self.boya(self.P["altin"]))

    def cubuk(self, cv, x, y, dx=40):
        """kuklacının çubuğu: perdenin altına iner"""
        cv.drawLine(x, y, x + dx, y + 2600, self.boya(self.P["kontur"], 0.85, 3.2))

    # ---------- kuklalar ----------
    def kahraman(self, cv, x, y, s=1.0, faz=0.0, yuru=0.0, kol=0.0, egim=0.0):
        """kalça (x, y)'de, profilden kukla. faz: yürüme evresi, yuru: 0..1 adım genliği, kol: ön kolu kaldırma (0..1)"""
        K = self.K
        cv.save(); cv.translate(x, y); cv.scale(s, s); cv.rotate(egim)
        sw = math.sin(faz) * yuru
        self.cubuk(cv, 0, -70, 30)

        def bacak(aci, diz, a, dx=0):
            cv.save(); cv.translate(dx, 28); cv.rotate(aci)
            self.deri(cv, yol([(-17, -6), (17, -6), (14, 74), (-14, 74)]), K["bacak"], nokta_dizisi(0, 8, 0, 60, 4, 3.2), a)
            cv.translate(0, 72); cv.rotate(diz)
            self.deri(cv, yol([(-13, -4), (13, -4), (11, 66), (-11, 66)]), K["bacak"], nokta_dizisi(0, 10, 0, 52, 3, 3.0), a)
            self.deri(cv, egri([(-12, 60), (10, 58), (34, 66), (46, 58), (40, 74), (-12, 78)]), K["pabuc"], [(14, 69, 3)], a)
            self.pim(cv, 0, 0); cv.restore()
            self.pim(cv, dx, 28)

        def kol_ciz(omuz, dirsek, a):
            cv.save(); cv.translate(8, -138); cv.rotate(omuz)
            self.deri(cv, yol([(-15, -6), (15, -6), (12, 66), (-12, 66)]), K["kol"], nokta_dizisi(0, 10, 0, 54, 4, 3), a)
            cv.translate(0, 64); cv.rotate(dirsek)
            self.deri(cv, yol([(-11, -4), (11, -4), (9, 56), (-9, 56)]), K["kol"], [], a)
            self.deri(cv, egri([(-10, 52), (10, 52), (13, 66), (0, 76), (-12, 66)]), K["ten"], [], a)
            self.pim(cv, 0, 0); cv.restore()
            self.pim(cv, 8, -138)

        # arka uzuvlar biraz daha koyu görünür (üst üste binen deri)
        bacak(-22 * sw + 7, 28 * max(0, -sw), 0.75, -12)
        kol_ciz(22 * sw - 10, -15, 0.75)
        self.deri(cv, yol([(-42, -152), (46, -152), (60, 6), (70, 50), (-68, 50), (-56, 6)]), K["entari"],
                  [(-14, -120, 4), (14, -120, 4), (0, -100, 5), (-20, -78, 3.5), (0, -78, 3.5), (20, -78, 3.5), (-10, -56, 4),
                   (10, -56, 4), (-34, 32, 3), (-16, 32, 3), (2, 32, 3), (20, 32, 3), (38, 32, 3)])
        self.deri(cv, yol([(-52, -16), (56, -16), (57, 2), (-53, 2)]), K["kusak"], [(-30, -7, 3), (-10, -7, 3), (10, -7, 3), (30, -7, 3)])
        bas = egri([(-26, -170), (-30, -200), (-12, -226), (16, -226), (34, -206), (48, -192), (34, -184), (32, -170), (14, -160), (-12, -160)])
        self.deri(cv, bas, K["ten"], [(20, -200, 4.5)])
        self.deri(cv, egri([(-34, -212), (-4, -236), (34, -222), (8, -286), (-8, -290), (-20, -250)]), K["kulah"],
                  [(4, -240, 4), (2, -262, 3.2), (-10, -226, 3)])
        self.pim(cv, 0, -160)
        bacak(22 * sw - 5, 28 * max(0, sw), 0.92, 12)
        kalk = in_out_cubic(clamp(kol))
        kol_ciz(lerp(-22 * sw + 8, -150, kalk), lerp(-20, 25, kalk), 0.92)
        cv.restore()

    def levha(self, cv, lv, cx, cy, t, genislik=None):
        """yazılı levha kuklası. Perdeye yaklaşırken bulanık iri gölgeden keskin kuklaya döner; yazı deliktir."""
        p = prog(t, lv["t"], 0.55)
        if p <= 0:
            return
        metin = lv["metin"]
        f1 = self.font(100)
        sigir = (genislik or (0.72 if self.dik else 0.5)) * self.VW / (f1.measureText(metin) / 100 + 1.6)
        boy = min(lv.get("boy", 170 if self.dik else 150), sigir)
        f = self.font(boy)
        w = f.measureText(metin) + boy * 1.6; h = boy * 1.55
        yak = out_cubic(p)
        cv.save()
        if yak < 1:
            lp_ = skia.Paint(); lp_.setImageFilter(skia.ImageFilters.Blur(26 * (1 - yak), 26 * (1 - yak)))
            lp_.setAlphaf(clamp(p * 2.2))
            cv.saveLayer(None, lp_)
        cv.translate(cx, cy); k = lerp(1.22, 1.0, yak); cv.scale(k, k); cv.rotate(lerp(-4, 0, yak))
        self.cubuk(cv, 0, h / 2 - 4, 20)
        sekil = yol([(-w / 2, 0), (-w / 2 + h / 2, -h / 2), (w / 2 - h / 2, -h / 2), (w / 2, 0), (w / 2 - h / 2, h / 2), (-w / 2 + h / 2, h / 2)])
        self.deri(cv, sekil, self.P[lv["renk"]], [(-w / 2 + h * 0.32, 0, 5), (w / 2 - h * 0.32, 0, 5)], 0.94, 4)
        ic = yol([(-w / 2 + 14, 0), (-w / 2 + h / 2 + 6, -h / 2 + 10), (w / 2 - h / 2 - 6, -h / 2 + 10), (w / 2 - 14, 0),
                  (w / 2 - h / 2 - 6, h / 2 - 10), (-w / 2 + h / 2 + 6, h / 2 - 10)])
        cv.drawPath(ic, self.boya(self.P["kontur"], 0.9, 2))
        cv.drawString(metin, -f.measureText(metin) / 2, boy * 0.36, f, self.boya(self.P["isik"]))
        cv.restore()
        if yak < 1:
            cv.restore()

    def gul(self, cv, x, y, r, t, a=1.0):
        """12 yapraklı rozet, yavaşça döner"""
        if not self.s["gul"] or a <= 0:
            return
        cv.save(); cv.translate(x, y); cv.rotate(t * 14)
        for i in range(12):
            cv.save(); cv.rotate(i * 30)
            self.deri(cv, egri([(0, -r * 0.42), (r * 0.17, -r * 0.7), (0, -r), (-r * 0.17, -r * 0.7)]), self.P["turuncu"],
                      [(0, -r * 0.72, 3.5)], 0.9 * a, 3)
            cv.restore()
        self.deri(cv, egri([(r * 0.46 * math.cos(k * math.pi / 4), r * 0.46 * math.sin(k * math.pi / 4)) for k in range(8)]),
                  self.P["altin"], [], 0.95 * a)
        yildiz = []
        for k in range(16):
            rr = r * (0.26 if k % 2 == 0 else 0.12); aa = k * math.pi / 8
            yildiz.append((rr * math.cos(aa), rr * math.sin(aa)))
        cv.drawPath(yol(yildiz), self.boya(self.P["isik"], 0.95 * a))
        cv.restore()

    def zemin(self, cv, t):
        """alt bant: tepeler ve zımbalı çiçekler (perdenin dibi)"""
        VW, yer = self.VW, self.yer
        noktalar = [(-20, yer + 400)]
        for i in range(0, int(VW) + 60, 30):
            noktalar.append((i, yer + 10 * math.sin(i / 90) + 6 * math.sin(i / 37 + 1)))
        noktalar.append((VW + 20, yer + 400))
        self.deri(cv, yol(noktalar), self.P["toprak"], [(x, yer + 46 + 14 * math.sin(x), 4) for x in range(40, int(VW), 70)], 0.85)
        for i, x in enumerate(range(90, int(VW), 260)):
            cv.save(); cv.translate(x, yer + 8); cv.rotate(4 * math.sin(t * 2 + i))
            cv.drawLine(0, 0, 0, -38, self.boya(self.P["kontur"], 1, 3))
            self.deri(cv, egri([(0, -36), (12, -52), (8, -70), (0, -60), (-8, -70), (-12, -52)]), self.P["vurgu"], [(0, -52, 2.6)], 0.9, 2.5)
            cv.restore()

    def merdiven(self, cv, x0, w, n, t, t0):
        """n basamak; her biri alttan yükselen bir deri blok. Basamak üstlerinin listesini döndürür"""
        yer = self.yer
        ustler = []
        adim = min(44, 300 / max(1, n - 1))
        for i in range(n):
            h = 46 + i * adim
            p = out_back(prog(t, t0 + i * 0.13, 0.32), 1.4)
            yy = yer - h * p
            x = x0 + i * w
            if p > 0:
                self.deri(cv, yol([(x, yer + 30), (x, yy), (x + w - 6, yy), (x + w - 6, yer + 30)]), self.P["lacivert"],
                          [(x + w / 2 - 3, yy + 22 + k * 30, 4) for k in range(int(h * p / 30))] + [(x + 14, yy + 12, 3), (x + w - 20, yy + 12, 3)], 0.86)
                self.cubuk(cv, x + w / 2, yer + 20, 0)
            ustler.append((x + w / 2 - 3, yer - h))
        return ustler

    def agac(self, cv, x, g, t, olcek=1.0):
        """hayat ağacı: g büyüme (0..1); dallar gövdeden çıkar, yapraklar ve laleler sırayla açılır"""
        if g <= 0:
            return
        cv.save(); cv.translate(x, self.yer); s = lerp(0.18, 1.0, g) * olcek; cv.scale(s, s); cv.rotate(2 * math.sin(t * 1.7))
        self.cubuk(cv, 0, 0, -10)
        govde = yol([(-30, 10), (-15, -160), (-9, -335), (9, -335), (15, -160), (30, 10)])
        self.deri(cv, govde, 0xFF8A5A33, nokta_dizisi(0, -20, 0, -200, 6, 4))
        ogeler = [(-150, -190, -230, 'y'), (-150, 190, -230, 'y'), (-205, -160, -340, 'l'), (-205, 160, -340, 'l'),
                  (-255, -210, -400, 'y'), (-255, 210, -400, 'y'), (-300, -95, -480, 'y'), (-300, 95, -480, 'y'), (-330, 0, -580, 'l')]
        for i, (sy, dx, dy, tur) in enumerate(ogeler):
            p = clamp((g - 0.12 - i * 0.07) / 0.3)
            if p <= 0:
                continue
            pe = out_cubic(p)
            ex, ey = lerp(0, dx, pe), lerp(sy, dy, pe)
            cv.drawLine(0, sy, ex, ey, self.boya(self.P["kontur"], 1, 8 if tur == 'y' else 6))
            cv.save(); cv.translate(ex, ey)
            cv.rotate(math.degrees(math.atan2(dx, -(dy - sy))) + 5 * math.sin(t * 2.3 + i)); k = out_back(p, 1.8); cv.scale(k, k)
            if tur == 'y':
                self.deri(cv, egri([(0, 6), (36, -30), (0, -96), (-36, -30)]), self.P["yaprak"], [(0, -30, 4.5), (0, -56, 3.5)], 0.9)
            else:
                self.deri(cv, egri([(0, 6), (30, -18), (34, -62), (14, -40), (0, -72), (-14, -40), (-34, -62), (-30, -18)]),
                          self.P["vurgu"], [(0, -26, 4)], 0.92)
            cv.restore()
        cv.restore()

    def bayrak(self, cv, x, p, t):
        if p <= 0:
            return
        yer = self.yer
        h = 470 * out_back(p, 1.2)
        cv.drawLine(x, yer + 20, x, yer - h, self.boya(self.P["kontur"], 1, 9))
        cv.drawCircle(x, yer - h - 10, 12, self.boya(self.P["altin"])); cv.drawCircle(x, yer - h - 10, 12, self.boya(self.P["kontur"], 1, 3))
        nok = []
        for k in range(13):
            u = k / 12
            nok.append((x + 6 + 220 * u * p, yer - h + 6 + 16 * math.sin(u * 5 - t * 9) * u))
        for k in range(12, -1, -1):
            u = k / 12
            nok.append((x + 6 + 220 * u * p, yer - h + 6 + lerp(130, 70, u) + 16 * math.sin(u * 5 - t * 9) * u))
        self.deri(cv, yol(nok), self.P["vurgu"], [(x + 60 * p, yer - h + 70, 6), (x + 120 * p, yer - h + 66, 5)], 0.9)

    def lale_gosterlik(self, cv, x):
        """geçişte perdenin önünden geçen büyük lale göstermelik (koyu, dantel delikli)"""
        VH = self.VH
        cv.save(); cv.translate(x, VH * 0.55); s = VH / 900; cv.scale(s, s)
        cv.drawLine(0, 120, 0, 900, self.boya(self.P["kontur"], 0.96, 26))
        sekil = egri([(0, 150), (-150, 70), (-200, -110), (-120, -300), (-55, -170), (0, -330), (55, -170), (120, -300), (200, -110), (150, 70)])
        delikler = [(0, -200 + k * 60, 10) for k in range(5)] + [(-110 + j * 55, -40 + 30 * (j % 2), 8) for j in range(5)]
        self.deri(cv, sekil, self.P["kontur"], delikler, 0.96, 5)
        cv.restore()

    # ---------- sahneler ----------
    def gul_yeri(self, r_yatay, r_dikey):
        return (self.VW - (190 if self.dik else 170), 240 if self.dik else 170, r_dikey if self.dik else r_yatay)

    def yuruyus(self, cv, t, sh):
        VW, dik, yer = self.VW, self.dik, self.yer
        cx = VW / 2
        gx, gy, gr = self.gul_yeri(95, 95)
        self.gul(cv, gx, gy, gr, t, out_cubic(prog(t, sh["bas"] + 0.2, 0.6)))
        g = sh["giris_t"]
        p = out_cubic(prog(t, g, 1.5))
        hx = lerp(-160, cx - (60 if dik else 150), p)
        yuru = 1.0 if p < 1 else max(0, 1 - (t - g - 1.5) * 4)
        s = 1.35 if dik else 1.15
        kol = prog(t, sh["kol_t"], 0.4) if "kol_t" in sh else 0
        self.kahraman(cv, hx, yer - 150 * s - abs(math.sin(t * 7.5)) * 8 * yuru, s, t * 7.5, yuru, kol=kol)
        if sh.get("levha"):
            self.levha(cv, sh["levha"], cx + (150 if dik else 190), yer - (860 if dik else 520), t)

    def merdiven_sahne(self, cv, t, sh):
        VW, dik, yer = self.VW, self.dik, self.yer
        n = sh["basamak"]
        w = min(120, (VW - 240) / n)
        x0 = VW / 2 - n / 2 * w
        gx, gy, gr = self.gul_yeri(80, 80)
        self.gul(cv, gx, gy - (20 if not dik else 0), gr, t)
        ustler = self.merdiven(cv, x0, w, n, t, sh["t"])
        q = clamp((t - sh["tirman_t"]) / sh["tirman_sure"]) * (n - 1)
        k = int(q); f = q - k
        if t < sh["tirman_t"]:
            hx, hy, faz = x0 - 60, yer - 150, 0
        else:
            a = ustler[min(k, n - 1)]; b = ustler[min(k + 1, n - 1)]
            hx = lerp(a[0], b[0], f); hy = lerp(a[1], b[1], f) - 150 - math.sin(math.pi * f) * 50 * (k < n - 1)
            faz = q * math.pi
        zafer = prog(t, sh["zafer_t"], 0.4) if "zafer_t" in sh else 0
        self.kahraman(cv, hx, hy, 0.95 if dik else 0.82, faz, 0.6 * (1 - zafer), kol=zafer)
        if sh.get("levha"):
            self.levha(cv, sh["levha"], VW / 2 - (0 if dik else 220), yer - (1080 if dik else 640), t)

    def agac_sahne(self, cv, t, sh):
        dik = self.dik
        g = 0.25 * out_back(prog(t, sh.get("filiz_t", sh["t"]), 0.4), 1.5) + 0.75 * in_out_cubic(prog(t, sh["t"], 0.9))
        lv = sh.get("levha")
        yan = bool(lv) and not dik and self.VW >= 1500   # geniş formatta levha ağacın yanında, diğerlerinde üstünde
        self.agac(cv, self.VW * (0.28 if yan else 0.5), g, t, (1.35 if dik else 1.2) * ((0.75 if self.VH < 1200 else 0.85) if lv and not yan else 1))
        gx, gy, gr = self.gul_yeri(70, 70)
        self.gul(cv, gx, gy - (20 if not dik else 0), gr, t)
        if lv:
            if yan:
                self.levha(cv, lv, self.VW * 0.7, self.yer - 560, t, genislik=0.4)
            else:
                self.levha(cv, lv, self.VW / 2, self.yer - (1150 if dik else 760), t)

    def kapanis(self, cv, t, sh):
        VW, dik, yer = self.VW, self.dik, self.yer
        cx = VW / 2
        kare_ = not dik and VW < 1500  # 1:1 ve 4:5'te rozet levhanın üstünde kalmasın
        self.gul(cv, VW - (190 if dik or kare_ else 240), 300 if dik else (140 if kare_ else 200), 85 if kare_ else 110, t * 1.5)
        bp = prog(t, sh["bayrak_t"], 0.45) if "bayrak_t" in sh else 0
        self.bayrak(cv, cx + (40 if dik else 80), bp, t)
        s = 1.35 if dik else 1.15
        kol = prog(t, sh["kol_t"], 0.35) if "kol_t" in sh else 0
        self.kahraman(cv, cx - (170 if dik else 130), yer - 150 * s - abs(math.sin(t * 6)) * 6, s, 0, 0, kol=kol, egim=-4 * bp)
        if sh.get("levha"):
            self.levha(cv, sh["levha"], cx, yer - (1000 if dik else 660), t)

    def kare(self, cv, t):
        VW, VH = self.VW, self.VH
        cv.save(); cv.scale(self.u, self.u)
        cv.drawRect(skia.Rect.MakeWH(VW, VH), self.boya(self.P["perde"]))
        self.zemin(cv, t)
        sh = [x for x in self.s["sahneler"] if t >= x["bas"]][-1]
        {"yuruyus": self.yuruyus, "merdiven": self.merdiven_sahne, "agac": self.agac_sahne, "kapanis": self.kapanis}[sh["tur"]](cv, t, sh)
        # geçiş: kandil kısılır (düz renk), lale göstermelik sağdan sola geçer; sahne en karanlık anda değişir
        for ts in self.gecisler:
            p = prog(t, ts - 0.4, 0.8)
            if 0 < p < 1:
                cv.drawRect(skia.Rect.MakeWH(VW, VH), self.boya(self.P["gece"], 0.82 * math.sin(math.pi * p) ** 2))
                self.lale_gosterlik(cv, lerp(VW + VH * 0.35, -VH * 0.35, in_out_cubic(p)))
        k = 34
        c = self.boya(self.P["cerceve"])
        for r in (skia.Rect.MakeLTRB(0, 0, VW, k), skia.Rect.MakeLTRB(0, VH - k, VW, VH), skia.Rect.MakeLTRB(0, 0, k, VH),
                  skia.Rect.MakeLTRB(VW - k, 0, VW, VH)):
            cv.drawRect(r, c)
        cv.drawRect(skia.Rect.MakeLTRB(k + 6, k + 6, VW - k - 6, VH - k - 6), self.boya(self.P["cerceve_cizgi"], 1, 4))
        cv.restore()


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    klasor.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H)
    surf = skia.Surface(W, H)
    out = []
    for t in anlar:
        with surf as cv:
            cv.clear(0xFF000000)
            c.kare(cv, t)
        p = klasor / f"{s.get('kimlik', 'golge')}-{W}x{H}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(p), skia.kPNG)
        out.append(p)
    return out


def video(s: dict, W: int, H: int, yol_: Path) -> Path:
    yol_.parent.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H)
    surf = skia.Surface(W, H)
    # skia'nın yerel düzeni çoğu makinede BGRA; ffmpeg'e doğru bildir (yoksa kırmızı/mavi yer değiştirir)
    pf = "bgra" if surf.imageInfo().colorType() == skia.kBGRA_8888_ColorType else "rgba"
    fps = s["fps"]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pf, "-s", f"{W}x{H}", "-r", str(fps),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(yol_)],
                          stdin=subprocess.PIPE)
    for i in range(int(round(fps * s["sure"]))):
        with surf as cv:
            cv.clear(0xFF000000)
            c.kare(cv, i / fps)
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise RuntimeError(f"ffmpeg başarısız: {yol_}")
    return yol_
