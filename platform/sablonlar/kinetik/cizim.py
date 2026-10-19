"""Kinetik şablonun görüntüsü: düz renkli hareketli grafik + kinetik tipografi (skia).

Her kare t'nin saf fonksiyonudur. Ölçüler 1080 piksellik kısa kenara göre (`u`) verilir; dikey ve
yatay yerleşim aynı sahne tanımından çıkar. Gerekenler: skia-python (Linux'ta libegl1, libgl1).
"""

from __future__ import annotations

import math
import os
import random
import subprocess
from pathlib import Path

import zaman

# Inter (OFL). Depoya girmez (yazı tipleri LFS'e düşer): önce KINETIK_FONT_DIZINI, sonra sistem
# (`apt-get install fonts-inter`, macOS'ta Inter yüklü olmalı), sonra fontconfig.
FONT_ADLARI = {800: ["Inter-ExtraBold.otf", "Inter-800.ttf", "Inter-ExtraBold.ttf"], 700: ["Inter-Bold.otf", "Inter-700.ttf", "Inter-Bold.ttf"]}
FONT_DIZINLERI = [os.environ.get("KINETIK_FONT_DIZINI", ""), "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
                  str(Path.home() / "Library/Fonts"), "/Library/Fonts"]


def font_bul(agirlik: int) -> str:
    for d in FONT_DIZINLERI:
        for ad in FONT_ADLARI[agirlik]:
            if d and (Path(d) / ad).exists():
                return str(Path(d) / ad)
    r = subprocess.run(["fc-match", "-f", "%{file}", f"Inter:weight={205 if agirlik == 800 else 200}"], capture_output=True, text=True)
    if r.returncode == 0 and "inter" in r.stdout.lower():
        return r.stdout.strip()
    raise RuntimeError("Inter yazı tipi bulunamadı: `apt-get install fonts-inter` ya da KINETIK_FONT_DIZINI")


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, p): return a + (b - a) * p
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def in_cubic(p): return p ** 3
def in_out_cubic(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_expo(p): return 1 if p >= 1 else 1 - 2 ** (-10 * p)
def out_back(p, s=1.9): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def out_elastic(p):
    if p <= 0: return 0
    if p >= 1: return 1
    return 2 ** (-10 * p) * math.sin((p * 10 - .75) * (2 * math.pi) / 3) + 1


def renk(hex_: str) -> int:
    return 0xFF000000 | int(hex_.lstrip("#"), 16)


def sayi_yaz(v: float, ondalik: str) -> str:
    return f"{v:.2f}".replace(".", ondalik)


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        import skia
        self.sk = skia
        self.s, self.W, self.H = s, W, H
        self.GENIS = W > H
        self.cx, self.cy = W / 2, H / 2
        self.u = min(W, H) / 1080
        self.DIAG = math.hypot(W, H)
        self.P = {k: renk(v) for k, v in s["palet"].items()}
        self.TF = skia.Typeface.MakeFromFile(font_bul(800))
        self.TF7 = skia.Typeface.MakeFromFile(font_bul(700))
        self.darbeler = zaman.darbeler(s)
        rnd = random.Random(42)
        self.yuzen = [(rnd.random(), rnd.random(), rnd.choice("otx+"), rnd.uniform(14, 34), rnd.uniform(-1, 1), rnd.uniform(0.6, 1.4))
                      for _ in range(22)]
        renkler = [self.P[r] for r in ("vurgu", "ikinci", "ucuncu", "acik")]
        self.parcalar = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(300, 900), rnd.choice(renkler), rnd.uniform(8, 20)) for _ in range(40)]
        self.odak = (self.cx, self.cy)
        self.kayit = None  # okunabilirlik.MetinKaydi: video() render boyunca çizilen yazıları toplar

    # ---------- araçlar ----------
    def paint(self, c, a=1.0, stroke=0, cap=True):
        sk = self.sk
        p = sk.Paint(AntiAlias=True, Color=c)
        if a < 1: p.setAlphaf(a * p.getAlphaf())
        if stroke:
            p.setStyle(sk.Paint.kStroke_Style); p.setStrokeWidth(stroke)
            if cap: p.setStrokeCap(sk.Paint.kRound_Cap); p.setStrokeJoin(sk.Paint.kRound_Join)
        return p

    def genislik(self, s, size, tf=None, track=0.0):
        f = self.sk.Font(tf or self.TF, size)
        return f.measureText(s) + track * size * (len(s) - 1)

    def sigdir(self, s, size, azami, tf=None, track=0.0):
        """yazı azami genişliği aşarsa puntoyu küçült"""
        w = self.genislik(s, size, tf, track)
        return size * min(1.0, azami / w) if w else size

    def yazi(self, cv, s, x, y, size, color, sc=1.0, a=1.0, rot=0.0, tf=None, anchor="c", track=0.0):
        if a <= 0 or sc <= 0: return
        f = self.sk.Font(tf or self.TF, size); f.setSubpixel(True)
        w = f.measureText(s) + track * size * (len(s) - 1)
        hh = -f.getMetrics().fAscent * 0.72
        ox = {"c": -w / 2, "l": 0, "r": -w}[anchor]
        cv.save(); cv.translate(x, y); cv.rotate(rot); cv.scale(sc, sc)
        if self.kayit is not None:
            r = cv.getTotalMatrix().mapRect(self.sk.Rect.MakeLTRB(ox, -hh / 2, ox + w, hh / 2))
            self.kayit.ciz(s, (r.left(), r.top(), r.width(), r.height()),
                           ((color >> 16) & 255, (color >> 8) & 255, color & 255), a)
        p = self.paint(color, a)
        if track:
            xx = ox
            for ch in s:
                cv.drawString(ch, xx, hh / 2, f, p); xx += f.measureText(ch) + track * size
        else:
            cv.drawString(s, ox, hh / 2, f, p)
        cv.restore()

    def slam(self, cv, s, x, y, size, color, t, t0, rot=0.0, azami=None, **kw):
        """kelime ekrana çarpar: büyükten küçüğe, hafif geri tepme + hayalet izler"""
        if t < t0: return
        size = self.sigdir(s, size, azami or (self.W - 140 * self.u), kw.get("tf"), kw.get("track", 0.0))
        p = prog(t, t0, 0.22)
        a = clamp((t - t0) / 0.06)
        for g in (0.12, 0.06):
            pg = prog(t - g, t0, 0.22)
            if 0 < pg < 1: self.yazi(cv, s, x, y, size, color, lerp(2.4, 1.0, out_back(pg, 2.2)), a * 0.18, rot, **kw)
        self.yazi(cv, s, x, y, size, color, lerp(2.4, 1.0, out_back(p, 2.2)), a, rot, **kw)

    def sarsinti(self, t):
        dx = dy = 0.0
        for t0, amp in self.darbeler:
            if t >= t0:
                k = math.exp(-(t - t0) * 14) * amp * self.u
                dx += k * math.sin((t - t0) * 90 + t0 * 7); dy += k * math.cos((t - t0) * 77 + t0 * 3)
        return dx, dy

    def zemin(self, cv, t, zemin_rol, a=0.10):
        sk, u, W, H = self.sk, self.u, self.W, self.H
        cv.clear(self.P[zemin_rol])
        sekil = self.P["acik"] if zemin_rol == "zemin" else self.P["zemin"]
        g = 54 * u; off = (t * 30 * u) % g
        p = self.paint(sekil, 0.07)
        y = -g + off
        while y < H + g:
            x = -g + off
            while x < W + g:
                cv.drawCircle(x, y, 2.6 * u, p); x += g
            y += g
        q = self.paint(sekil, a if zemin_rol != "zemin" else 0.16, stroke=5 * u)
        for fx, fy, k, s, sp, sc in self.yuzen:
            x = (fx * W + t * 40 * sp * u) % W
            yy = (fy * H - t * 60 * sc * u) % H
            r = s * u
            cv.save(); cv.translate(x, yy); cv.rotate(t * 60 * sp)
            if k == "o": cv.drawCircle(0, 0, r, q)
            elif k == "t":
                pth = sk.Path(); pth.moveTo(0, -r); pth.lineTo(r * .87, r * .5); pth.lineTo(-r * .87, r * .5); pth.close(); cv.drawPath(pth, q)
            elif k == "x": cv.drawLine(-r, -r, r, r, q); cv.drawLine(-r, r, r, -r, q)
            else: cv.drawLine(-r, 0, r, 0, q); cv.drawLine(0, -r, 0, r, q)
            cv.restore()

    def halka(self, cv, t, t0, x, y, r0, r1, c, w=10):
        p = prog(t, t0, 0.5)
        if 0 < p < 1:
            cv.drawCircle(x, y, lerp(r0, r1, out_expo(p)), self.paint(c, 1 - p, stroke=w * self.u * (1 - p) + 1))

    def patlama(self, cv, t, t0, x, y, kuvvet=1.0):
        p = prog(t, t0, 0.9)
        if not 0 < p < 1: return
        u = self.u
        for ang, sp, col, s in self.parcalar:
            dd = sp * u * kuvvet * out_expo(p) * 0.9
            cv.save(); cv.translate(x + math.cos(ang) * dd, y + math.sin(ang) * dd + 400 * u * p * p); cv.rotate(p * 500 + ang * 50)
            r = s * u * (1 - p)
            cv.drawRect(self.sk.Rect(-r, -r * .5, r, r * .5), self.paint(col)); cv.restore()

    def diyagonal(self, cv, p, sol):
        """x + 0.6*y = k çizgisinin solunu (sol) ya da sağını ikinci renkle boyar; p çizgiyi soldan sağa taşır"""
        if (sol and p <= 0) or (not sol and p >= 1): return
        W, H = self.W, self.H
        k = lerp(-0.6 * H, W, p)
        a, b = (k, 0), (k - 0.6 * H, H)
        pth = self.sk.Path()
        if sol: pth.moveTo(-W, 0); pth.lineTo(*a); pth.lineTo(*b); pth.lineTo(-W, H)
        else: pth.moveTo(*a); pth.lineTo(W * 3, 0); pth.lineTo(W * 3, H); pth.lineTo(*b)
        pth.close(); cv.drawPath(pth, self.paint(self.P["ikinci"]))
        cv.drawLine(a[0], a[1], b[0], b[1], self.paint(self.P["vurgu"], 1, stroke=22 * self.u, cap=False))

    # ---------- sahneler: her biri çizer ve çıkış geçişinin odak noktasını bırakır ----------
    def kelimeler(self, cv, t, sh, ilk):
        P, u, cx, cy = self.P, self.u, self.cx, self.cy
        self.zemin(cv, t, "zemin")
        ws = sh["kelimeler"]
        if ilk and sh.get("acilis", True):  # açılış topu, ilk kelimede patlar
            r = 150 * u * out_elastic(prog(t, 0.02, 0.5)) * (1 - in_cubic(prog(t, ws[0]["t"] - 0.08, 0.15)))
            if r > 0: cv.drawCircle(cx, cy, r, self.paint(P["vurgu"]))
            self.halka(cv, t, ws[0]["t"] - 0.04, cx, cy, 120 * u, 520 * u, P["vurgu"], 14)
        sz = sh.get("punto", 230) * u
        n = len(ws)
        g = sh.get("gorsel")
        if g:  # gerçek ürün fotoğrafı (saydam PNG): kelimeler üstte (yatayda solda), fotoğraf büyük ve net
            img = self.logo_resmi(g["dosya"])
            gx, gy = (cx + self.W * 0.21, cy) if self.GENIS else (cx, cy + 250 * u)
            gw = min(img.width(), (self.W * 0.5 if self.GENIS else self.W - 120 * u), g.get("genislik", 1e9) * u)
            gh = gw * img.height() / img.width()
            if not self.GENIS and gh > 900 * u:
                gw, gh = gw * 900 * u / gh, 900 * u
            pg = prog(t, g["t"], 0.5)
            if pg > 0:
                k = out_back(pg, 1.4) * (1 + 0.035 * clamp((t - g["t"] - 0.5) / 4))
                self.halka(cv, t, g["t"], gx, gy, 0.3 * gw, 0.75 * gw, P["vurgu"], 12)
                cv.save(); cv.translate(gx, gy); cv.rotate(lerp(-10, 0, out_cubic(pg))); cv.scale(k, k)
                cv.drawImageRect(img, self.sk.Rect(-gw / 2, -gh / 2, gw / 2, gh / 2),
                                 self.sk.SamplingOptions(self.sk.CubicResampler.Mitchell()), self.paint(P["acik"], clamp(pg * 3)))
                cv.restore()
            if self.GENIS:
                tx, azami, aralik = cx - self.W * 0.24, self.W * 0.44, 210 * u
                yb = cy
            else:
                tx, azami, aralik = cx, self.W - 140 * u, 200 * u
                yb = cy - 560 * u
            sz = min(min(self.sigdir(w["metin"], min(sz, 190 * u), azami) for w in ws), sz)
            for i, w in enumerate(ws):
                self.slam(cv, w["metin"], tx, yb + (i - (n - 1) / 2) * aralik, sz, P[w.get("renk", "acik")], t, w["t"])
            self.odak = (gx, gy)
            return
        if self.GENIS:
            gen = [self.genislik(w["metin"], sz) for w in ws]
            bosluk = 90 * u
            toplam = sum(gen) + bosluk * (n - 1)
            k = min(1.0, (self.W - 160 * u) / toplam)
            x = cx - toplam * k / 2
            for w, g in zip(ws, gen):
                self.slam(cv, w["metin"], x + g * k / 2, cy, sz * k, P[w.get("renk", "acik")], t, w["t"])
                x += (g + bosluk) * k
        else:
            aralik = 300 * u
            for i, w in enumerate(ws):
                self.slam(cv, w["metin"], cx, cy + (i - (n - 1) / 2) * aralik, sz, P[w.get("renk", "acik")], t, w["t"])
        self.odak = (cx, cy)

    def buyuk_sayi(self, cv, t, sh):
        P, u, cx, cy = self.P, self.u, self.cx, self.cy
        self.zemin(cv, t, "vurgu")
        # uzun sayı (fiyat gibi "16,90 €") halkaya sığmak için küçülmesin: halka büyür, üst ve etiket açılır
        dogal = self.genislik(sh["sayi"], 400 * u)
        azami = 520 * u if dogal <= 520 * u else min(dogal, (760 if not self.GENIS else 640) * u)
        ek = (azami - 520 * u) / 2
        yb = cy - (400 if not self.GENIS else 345) * u - ek
        if sh.get("ust"):
            self.slam(cv, sh["ust"], cx, yb, 80 * u, P["zemin"], t, sh.get("ust_t", sh["bas"] + 0.05), track=0.12)
        t0 = sh["sayi_t"]
        pr = out_back(prog(t, t0, 0.4), 1.5)
        if pr > 0:  # dönen kesikli halka
            q = self.paint(P["ikinci"], 1, stroke=16 * u)
            q.setPathEffect(self.sk.DashPathEffect.Make([38 * u, 26 * u], (t * 220 * u) % (64 * u)))
            cv.drawCircle(cx, cy + 10 * u, (300 * u + ek) * pr, q)
        self.slam(cv, sh["sayi"], cx - 14 * u, cy + 10 * u, 400 * u, P["zemin"], t, t0, azami=azami)
        self.halka(cv, t, t0, cx, cy, 200 * u, 700 * u, P["zemin"], 18)
        if sh.get("etiket"):
            pd = out_expo(prog(t, sh.get("etiket_t", t0 + 0.5), 0.35))
            if pd > 0:
                yd = cy + (360 if not self.GENIS else 330) * u + ek
                fs = self.sigdir(sh["etiket"], 104 * u, 560 * u)
                bw, bh = self.genislik(sh["etiket"], fs) + 100 * u, 150 * u
                x0 = lerp(-bw, cx - bw / 2, pd)
                cv.save(); cv.rotate(-3, x0 + bw / 2, yd)
                cv.drawRoundRect(self.sk.Rect(x0, yd - bh / 2, x0 + bw, yd + bh / 2), 26 * u, 26 * u, self.paint(P["zemin"]))
                self.yazi(cv, sh["etiket"], x0 + bw / 2, yd, fs, P["vurgu"])
                cv.restore()
        self.odak = (cx, cy)

    def egri_sahnesi(self, cv, t, sh):
        sk, P, u, cx, W, H = self.sk, self.P, self.u, self.cx, self.W, self.H
        self.zemin(cv, t, "zemin", a=0.10)
        if self.GENIS:
            gx0, gx1, gy0, gy1 = 150 * u, 1120 * u, 880 * u, 210 * u
            sx, sy = 1520 * u, self.cy - 40 * u
        else:
            gx0, gx1, gy0, gy1 = 120 * u, W - 120 * u, H * 0.72, H * 0.40  # eksen yazısı alttaki %22 arayüz bandının üstünde
            sx, sy = cx, H * 0.20
        oran, gun = sh.get("oran", 0.01), sh.get("gun", 365)
        tepe = (1 + oran) ** gun
        b, t0, t1 = sh["bas"], zaman.egri_baslangic(sh), sh["zirve_t"]
        ax = self.paint(P["acik"], 0.35, stroke=4 * u)
        pa = out_expo(prog(t, b, 0.4))
        cv.drawLine(gx0, gy0, lerp(gx0, gx1, pa), gy0, ax)
        cv.drawLine(gx0, gy0, gx0, lerp(gy0, gy1, pa), ax)
        self.yazi(cv, "0", gx0, gy0 + 46 * u, 34 * u, P["acik"], a=0.6 * pa, tf=self.TF7)
        self.yazi(cv, sh.get("eksen", f"{gun} GÜN"), gx1, gy0 + 46 * u, 34 * u, P["acik"], a=0.6 * pa, tf=self.TF7, anchor="r", track=0.06)
        q = self.paint(P["acik"], 0.25 * pa, stroke=3 * u); q.setPathEffect(sk.DashPathEffect.Make([14 * u, 12 * u], 0))
        cv.drawLine(gx0, gy0 - 6 * u, gx1, gy0 - 6 * u, q)
        pc = in_out_cubic(prog(t, t0, t1 - t0))
        pth = sk.Path(); ex, ey = gx0, gy0 - 6 * u
        for i in range(161):
            xx = pc * i / 160
            px, py = lerp(gx0, gx1, xx), lerp(gy0 - 6 * u, gy1, zaman.egri(xx, oran, gun))
            (pth.moveTo if i == 0 else pth.lineTo)(px, py)
            ex, ey = px, py
        if pc > 0:
            alan = sk.Path(pth); alan.lineTo(ex, gy0); alan.lineTo(gx0, gy0); alan.close()
            fp = sk.Paint(AntiAlias=True)
            fp.setShader(sk.GradientShader.MakeLinear([(0, gy1), (0, gy0)], [sk.ColorSetA(P["vurgu"], 90), sk.ColorSetA(P["ucuncu"], 0)]))
            cv.drawPath(alan, fp)
            glow = self.paint(P["vurgu"], 0.5, stroke=26 * u); glow.setMaskFilter(sk.MaskFilter.MakeBlur(sk.kNormal_BlurStyle, 14 * u))
            cv.drawPath(pth, glow)
            st = self.paint(P["vurgu"], 1, stroke=12 * u)
            st.setShader(sk.GradientShader.MakeLinear([(gx0, 0), (gx1, 0)], [P["ucuncu"], P["vurgu"]]))
            cv.drawPath(pth, st)
            nab = 1 + 0.25 * math.sin(t * 20)
            cv.drawCircle(ex, ey, 18 * u * nab, self.paint(P["acik"]))
            cv.drawCircle(ex, ey, 30 * u * nab, self.paint(P["acik"], 0.3, stroke=4 * u))
        zirve = t >= t1
        v = tepe if zirve else (1 + oran) ** (gun * pc)
        pul = 1 + 0.25 * math.exp(-(t - t1) * 7) if zirve else 1 + 0.02 * math.sin(t * 30) * pc
        s_in = out_back(prog(t, b + 0.05, 0.3))
        self.yazi(cv, sayi_yaz(v, self.s["ondalik"]) + "×", sx, sy, (170 if self.GENIS else 190) * u,
                  P["vurgu"] if zirve else P["acik"], sc=pul * s_in)
        self.yazi(cv, f"{sh.get('sayac', 'GÜN')} {gun if zirve else int(gun * pc)}", sx, sy - (150 if self.GENIS else 165) * u,
                  46 * u, P["acik"], a=0.75 * s_in, tf=self.TF7, track=0.12)
        if zirve:
            self.halka(cv, t, t1, ex, ey, 30 * u, 520 * u, P["vurgu"], 16)
            self.halka(cv, t, t1 + 0.08, ex, ey, 30 * u, 380 * u, P["ikinci"], 12)
            self.patlama(cv, t, t1, ex, ey)
            rozet = sh.get("rozet")
            pk = out_back(prog(t, t1 + 0.06, 0.3), 2.5)
            if rozet and pk > 0:
                cv.save(); cv.translate(sx, sy + (190 if self.GENIS else 215) * u); cv.rotate(-4); cv.scale(pk, pk)
                fs = self.sigdir(rozet, 84 * u, 520 * u)
                bw, bh = self.genislik(rozet, fs) + 110 * u, 120 * u
                cv.drawRoundRect(sk.Rect(-bw / 2, -bh / 2, bw / 2, bh / 2), 22 * u, 22 * u, self.paint(P["ikinci"]))
                self.yazi(cv, rozet, 0, 0, fs, P["acik"])
                cv.restore()
        self.odak = (ex, ey)

    def karsitlik(self, cv, t, sh):
        sk, P, u, cx, cy, W, H = self.sk, self.P, self.u, self.cx, self.cy, self.W, self.H
        self.zemin(cv, t, "ucuncu")
        panel_t = sh.get("panel_t", sh["buyuk_t"] - 0.18)
        pp = in_out_cubic(prog(t, panel_t, 0.3))
        ax_, ay_ = (lerp(cx, W * 0.25, pp), cy) if self.GENIS else (cx, lerp(cy, H * 0.25, pp))
        yarim = (W / 2 if self.GENIS else W) - 100 * u
        ps = out_back(prog(t, sh["kucuk_t"], 0.3), 3)
        kare = 64 * u * ps
        cv.save(); cv.translate(ax_, ay_ - 40 * u); cv.rotate(math.sin(t * 3) * 6)
        cv.drawRoundRect(sk.Rect(-kare / 2, -kare / 2, kare / 2, kare / 2), 10 * u, 10 * u, self.paint(P["zemin"])); cv.restore()
        self.halka(cv, t, sh["kucuk_t"], ax_, ay_ - 40 * u, 20 * u, 160 * u, P["zemin"], 8)
        self.slam(cv, sh["kucuk"], ax_, ay_ + 100 * u, 84 * u, P["zemin"], t, sh["kucuk_t"] + 0.05, track=0.04, azami=yarim)
        bx, by = self.cx, self.cy
        if pp > 0:
            if self.GENIS:
                r = sk.Rect(lerp(W, cx, pp), 0, W, H); bx, by = lerp(W * 1.25, W * 0.75, pp), cy
            else:
                r = sk.Rect(0, lerp(H, cy, pp), W, H); bx, by = cx, lerp(H * 1.25, H * 0.65, pp)  # yazı arayüz bandının üstünde
            cv.drawRect(r, self.paint(P["ikinci"]))
            cv.save(); cv.clipRect(r)
            b_t = sh["buyuk_t"]
            pb = out_back(prog(t, b_t, 0.4), 1.6)
            big = 360 * u * pb + 14 * u * math.sin((t - b_t) * 9) * (t > b_t + 0.4)
            if pb > 0:
                cv.save(); cv.translate(bx, by - 60 * u); cv.rotate(lerp(-25, -6, clamp(pb)))
                cv.drawRoundRect(sk.Rect(-big / 2, -big / 2, big / 2, big / 2), 40 * u, 40 * u, self.paint(P["vurgu"])); cv.restore()
            self.halka(cv, t, b_t, bx, by - 60 * u, 120 * u, 700 * u, P["vurgu"], 20)
            self.slam(cv, sh["buyuk"], bx, by + 190 * u, 120 * u, P["acik"], t, b_t + 0.04, azami=yarim)
            cv.restore()
        self.odak = (bx, by - 60 * u)

    def kapanis(self, cv, t, sh):
        P, u, cx, cy, H = self.P, self.u, self.cx, self.cy, self.H
        self.zemin(cv, t, "vurgu")
        satir = sh["satirlar"]
        n = len(satir)
        tx, ty = cx, cy - 20 * u  # yazı bloğunun merkezi; logo varsa yana (yatay) ya da aşağı (dikey) kayar
        logo = sh.get("logo")
        if logo:
            boy = logo.get("boy", 560) * u
            lx, ly_ = (cx - self.W * 0.24, cy) if self.GENIS else (cx, cy - 330 * u)
            tx, ty = (cx + self.W * 0.2, cy - 20 * u) if self.GENIS else (cx, cy + 300 * u)
            pl = prog(t, logo.get("t", sh["bas"] + 0.1), 0.45)
            if pl > 0:
                img = self.logo_resmi(logo["dosya"])
                k = out_back(pl, 1.6) * boy
                cv.save(); cv.translate(lx, ly_); cv.rotate(lerp(-18, 0, out_cubic(pl)))
                cv.drawImageRect(img, self.sk.Rect(-k / 2, -k * img.height() / img.width() / 2, k / 2, k * img.height() / img.width() / 2),
                                 self.sk.SamplingOptions(self.sk.CubicResampler.Mitchell()), self.paint(P["acik"], clamp(pl * 3)))
                cv.restore()
        azami = (self.W * 0.46 if logo and self.GENIS else self.W - 140 * u)
        # bütün satırlar aynı boyda: en uzun satır sığacak kadar küçülür, satır aralığı da onunla daralır
        taban = (230 if self.GENIS else 215) * u
        sz = min(self.sigdir(w["metin"], taban, azami) for w in satir)
        aralik = 260 * u * max(sz / taban, 0.55)
        for i, w in enumerate(satir):
            y = ty + (i - (n - 1) / 2) * aralik
            self.slam(cv, w["metin"], tx, y, sz, P[w.get("renk", "zemin" if i < n - 1 else "ikinci")], t, w["t"])
        self.patlama(cv, t, satir[-1]["t"], tx, ty + 20 * u, kuvvet=1.4)
        ly = ty + (n - 1) / 2 * aralik + 160 * u * max(sz / taban, 0.7)
        if "cizgi_t" in sh:
            pl = out_expo(prog(t, sh["cizgi_t"], 0.35))
            if pl > 0:
                L = 640 * u
                cv.drawRoundRect(self.sk.Rect(tx - L / 2, ly - 12 * u, tx - L / 2 + L * pl, ly + 12 * u), 12 * u, 12 * u, self.paint(P["zemin"]))
        if sh.get("alt"):
            pa = out_cubic(prog(t, sh.get("alt_t", satir[-1]["t"] + 0.4), 0.4))
            if pa > 0:
                yy = H * (1 - 0.22) - 50 * u if not self.GENIS else H - 110 * u  # dikeyde Reels arayüzünün üstü
                self.yazi(cv, sh["alt"], cx, yy + 30 * u * (1 - pa), self.sigdir(sh["alt"], 46 * u, self.W - 160 * u, self.TF7),
                          P["zemin"], a=pa * 0.85, tf=self.TF7, track=0.02)
        self.odak = (cx, cy)

    def logo_resmi(self, dosya):
        if not hasattr(self, "_logolar"):
            self._logolar = {}
        if dosya not in self._logolar:
            self._logolar[dosya] = self.sk.Image.open(str(Path(self.s["_klasor"]) / dosya))
        return self._logolar[dosya]

    # ---------- kare ----------
    def kare(self, cv, t):
        s = self.s
        sahneler = s["sahneler"]
        i = zaman.sahne_at(s, t)
        sh = sahneler[i]
        dx, dy = self.sarsinti(t)
        cv.save(); cv.translate(dx, dy)
        sonraki = sahneler[i + 1] if i + 1 < len(sahneler) else None
        zm = 1.0
        if sonraki and sonraki["gecis"] == "diyagonal":  # riser boyunca yakınlaş
            zm = 1 + 0.12 * in_cubic(prog(t, sonraki["bas"] - zaman.RISER_SN, zaman.RISER_SN))
        if zm != 1:
            cv.save(); cv.translate(self.cx, self.cy); cv.scale(zm, zm); cv.translate(-self.cx, -self.cy)
        tur = sh["tur"]
        if tur == "kelimeler": self.kelimeler(cv, t, sh, i == 0)
        elif tur == "buyuk-sayi": self.buyuk_sayi(cv, t, sh)
        elif tur == "egri": self.egri_sahnesi(cv, t, sh)
        elif tur == "karsitlik": self.karsitlik(cv, t, sh)
        else: self.kapanis(cv, t, sh)
        if zm != 1: cv.restore()
        if sh["gecis"] == "diyagonal" and i > 0:
            self.diyagonal(cv, out_cubic(prog(t, sh["bas"], zaman.DIYAGONAL_CIKIS)), sol=False)
        if sonraki:
            if sonraki["gecis"] == "iris":
                p = prog(t, sonraki["bas"] - zaman.IRIS_SN, zaman.IRIS_SN)
                if p > 0:
                    cv.drawCircle(*self.odak, self.DIAG * in_out_cubic(p), self.paint(self.P[zaman.ZEMIN[sonraki["tur"]]]))
            elif sonraki["gecis"] == "diyagonal":
                self.diyagonal(cv, in_out_cubic(prog(t, sonraki["bas"] - zaman.DIYAGONAL_GIRIS, zaman.DIYAGONAL_GIRIS)), sol=True)
        cv.restore()


def yuzey(W, H):
    import skia
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))


def video(s: dict, W: int, H: int, hedef: Path) -> Path:
    import okunabilirlik
    c = Cizici(s, W, H)
    c.kayit = okunabilirlik.MetinKaydi(W, H)
    surf = yuzey(W, H)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                           "-r", str(s["fps"]), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                           "-pix_fmt", "yuv420p", str(hedef)], stdin=subprocess.PIPE)
    for i in range(int(round(s["sure"] * s["fps"]))):
        c.kayit.kare(i / s["fps"])
        c.kare(surf.getCanvas(), i / s["fps"])
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg görüntüyü kodlayamadı")
    c.kayit.yaz(hedef)
    return hedef


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    import skia
    c = Cizici(s, W, H)
    surf = yuzey(W, H)
    klasor.mkdir(parents=True, exist_ok=True)
    out = []
    for t in anlar:
        c.kare(surf.getCanvas(), t)
        yol = klasor / f"kare-{W}x{H}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(yol), skia.kPNG)
        out.append(yol)
    return out
