"""Çizgi roman şablonunun görüntüsü: dikey bir çizgi roman sayfası, kamera sahneler arasında aşağı kayar.

Kalın siyah mürekkep konturu, düz baskı renkleri, Ben-Day noktaları (ton degradeyle değil nokta boyuyla
verilir), hız çizgileri, patlama balonları. Yumuşak degrade ya da bulanıklık yoktur: her şey keskin vektör.
Her kare `t` anının saf fonksiyonudur. Öğeler panelin içinde oranla yerleşir (x, y: 0–1) ve panelin kısa
kenarına göre ölçeklenir (1000 px'lik kenar = ölçek 1); dikey formatta iki panel üst üste, yatayda yan
yana bölünür.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
import skia

import fontlar
import zaman

M = 40          # oluk (kenar boşluğu)
KONTUR = 12


# ---------- yardımcılar ----------
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, p): return a + (b - a) * p
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def in_cubic(p): return p ** 3
def in_out_cubic(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_back(p, s=1.9): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def renk(hexs: str) -> int:
    return 0xFF000000 | int(hexs[1:], 16)


def boya(r, a=1.0, cizgi=0.0):
    p = skia.Paint(AntiAlias=True, Color=r)
    p.setAlphaf(a)
    if cizgi:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(cizgi)
        p.setStrokeJoin(skia.Paint.kRound_Join); p.setStrokeCap(skia.Paint.kRound_Cap)
    return p


def yol(noktalar, kapali=True):
    p = skia.Path(); p.moveTo(*noktalar[0])
    for n in noktalar[1:]: p.lineTo(*n)
    if kapali: p.close()
    return p


def kaydir(p, dx, dy):
    q = skia.Path(p); q.offset(dx, dy); return q


def sarsinti(t, t0, guc=14, sure=0.35):
    """darbe sonrası sönümlü sarsıntı (dx, dy)"""
    p = (t - t0) / sure
    if p < 0 or p > 1: return 0.0, 0.0
    a = guc * (1 - p) ** 2
    return a * math.sin(t * 95), a * math.cos(t * 77)


def patlama_yolu(r, n=14, seed=3, sivri=0.62):
    rng = np.random.default_rng(seed); pts = []
    for i in range(2 * n):
        th = math.pi * i / n + rng.uniform(-0.05, 0.05)
        rr = r * (1 if i % 2 == 0 else sivri) * rng.uniform(0.9, 1.08)
        pts.append((rr * math.cos(th), rr * math.sin(th)))
    return yol(pts)


class Cizici:
    def __init__(self, s: dict, W: int, H: int, fmt: str = "9x16"):
        self.s = zaman.bicim_icin(s, fmt)
        self.W, self.H = W, H
        self.u = min(W, H) / 1080
        self.VW, self.VH = W / self.u, H / self.u
        self.c = {k: renk(v) for k, v in s["palet"].items()}
        self.yuz = skia.Typeface.MakeFromFile(fontlar.bul())
        self._nokta: dict = {}
        self._gorsel: dict = {}
        self.klasor = Path(s.get("_klasor", "."))

    # ---------- temel çizim ----------
    def font(self, boy):
        f = skia.Font(self.yuz, boy); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True)
        return f

    def murekkep(self, cv, p, dolgu, kalin=KONTUR):
        cv.drawPath(p, boya(dolgu)); cv.drawPath(p, boya(self.c["murekkep"], 1, kalin))

    def yazi(self, cv, metin, x, y, boy, dolgu, derinlik=0, kontur=14, hiza=0.5):
        """çizgi roman harfi: düz renkli kabartma (derinlik), kalın kontur, dolgu"""
        f = self.font(boy); ink = self.c["murekkep"]
        blob = skia.TextBlob.MakeFromString(metin, f)
        x -= f.measureText(metin) * hiza
        for k in range(int(derinlik), 0, -2):
            cv.drawTextBlob(blob, x + k * 0.75, y + k * 0.75, boya(ink))
            cv.drawTextBlob(blob, x + k * 0.75, y + k * 0.75, boya(ink, 1, kontur))
        if kontur: cv.drawTextBlob(blob, x, y, boya(ink, 1, kontur))
        cv.drawTextBlob(blob, x, y, boya(dolgu))

    def noktalar(self, anahtar, alan, aralik, r_fn):
        """45°'lik ızgarada Ben-Day nokta yolu (önbellekli). r_fn(x, y) -> yarıçap"""
        if anahtar in self._nokta: return self._nokta[anahtar]
        x0, y0, x1, y1 = alan
        s = aralik * math.sqrt(2); p = skia.Path()
        j = 0; y = y0 - s
        while y < y1 + s:
            x = x0 - s + (j % 2) * s / 2
            while x < x1 + s:
                r = r_fn(x, y)
                if r > 0.6: p.addCircle(x, y, r)
                x += s
            j += 1; y += s / 2
        self._nokta[anahtar] = p
        return p

    def nokta_ciz(self, cv, klip, anahtar, alan, aralik, r_fn, r_renk):
        cv.save(); cv.clipPath(klip, doAntiAlias=True)
        cv.drawPath(self.noktalar(anahtar, alan, aralik, r_fn), boya(r_renk))
        cv.restore()

    def hiz_cizgileri(self, cv, cx, cy, r0, r_renk, aci=0.0, n=44, seed=1, uzun=2600):
        rng = np.random.default_rng(seed); p = skia.Path()
        for i in range(n):
            th = aci + 2 * math.pi * i / n + rng.uniform(-0.04, 0.04)
            gen = rng.uniform(0.012, 0.03); r = r0 * rng.uniform(0.9, 1.25)
            p.moveTo(cx + r * math.cos(th), cy + r * math.sin(th))
            p.lineTo(cx + uzun * math.cos(th - gen), cy + uzun * math.sin(th - gen))
            p.lineTo(cx + uzun * math.cos(th + gen), cy + uzun * math.sin(th + gen))
            p.close()
        cv.drawPath(p, boya(r_renk))

    # ---------- paneller ----------
    def poligonlar(self, sh):
        VW, VH = self.VW, self.VH
        pn = sh["paneller"]
        if len(pn) == 1:
            ust = M + (80 if pn[0].get("egim") else 0)
            return [[(M, ust), (VW - M, M), (VW - M, VH - M), (M, VH - M)]]
        b = sh.get("bolme", 0.34)
        if VH >= VW:
            yb = b * VH
            return [[(M, M), (VW - M, M), (VW - M, yb - 50), (M, yb + 50)],
                    [(M, yb + 90), (VW - M, yb - 10), (VW - M, VH - M), (M, VH - M)]]
        xb = b * VW
        return [[(M, M), (xb + 50, M), (xb - 50, VH - M), (M, VH - M)],
                [(xb + 90, M), (VW - M, M), (VW - M, VH - M), (xb - 10, VH - M)]]

    def sahne(self, cv, t, i):
        sh = self.s["sahneler"][i]
        for j, (p, pts) in enumerate(zip(sh["paneller"], self.poligonlar(sh))):
            xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
            P = {"x0": min(xs), "y0": min(ys), "pw": max(xs) - min(xs), "ph": max(ys) - min(ys), "pts": pts, "ana": (i, j)}
            P["k"] = min(P["pw"], P["ph"]) / 1000
            cv.save()
            if "vurus" in p:
                dx, dy = sarsinti(t, p["vurus"], 14)
                sc = 1.0 + 0.05 * (1 - out_cubic(prog(t, p["vurus"], 0.3))) * (t >= p["vurus"])
                cx, cy = P["x0"] + P["pw"] / 2, P["y0"] + P["ph"] / 2
                cv.translate(cx + dx, cy + dy); cv.scale(sc, sc); cv.translate(-cx, -cy)
            self.panel(cv, t, p, P)
            cv.restore()

    def panel(self, cv, t, p, P):
        c = self.c; x0, y0, pw, ph = P["x0"], P["y0"], P["pw"], P["ph"]
        klip = yol(P["pts"])
        cv.drawPath(klip, boya(c[p.get("zemin", "beyaz")]))
        cv.save(); cv.clipPath(klip, doAntiAlias=True)
        if "nokta" in p:
            yon, guc = p.get("nokta_yon", "asagi"), p.get("nokta_guc", 9.0)
            bas = p.get("nokta_bas", 0.36 if yon == "asagi" else 0.66)
            def r_fn(x, y, yon=yon, guc=guc, bas=bas):
                yy = (y - y0) / ph
                if yon == "duz": return guc
                q = (yy - bas) / (1 - bas) if yon == "asagi" else (bas - yy) / bas
                return guc * clamp(q) ** 1.15
            self.nokta_ciz(cv, klip, ("panel",) + P["ana"], (x0, y0, x0 + pw, y0 + ph), p.get("nokta_aralik", 20), r_fn, c[p["nokta"]])
        if "hiz_cizgileri" in p:
            hz = p["hiz_cizgileri"]
            ac = out_cubic(prog(t, hz["t"], 0.55)) if "t" in hz else 1.0
            if ac > 0:
                r0 = hz.get("r", 470) * P["k"]
                self.hiz_cizgileri(cv, x0 + hz.get("x", 0.5) * pw, y0 + hz.get("y", 0.5) * ph, lerp(1400 * P["k"], r0, ac),
                                   c[hz.get("renk", "murekkep")], aci=t * hz.get("donus", 0.05), n=hz.get("n", 44), seed=hz.get("seed", 4))
        for o in p["ogeler"]:
            getattr(self, "o_" + o["tur"])(cv, t, o, P, ic=True)
        cv.restore()
        cv.drawPath(klip, boya(c["murekkep"], 1, KONTUR))
        for o in p["ogeler"]:
            getattr(self, "o_" + o["tur"])(cv, t, o, P, ic=False)
        if "anlati" in p:
            a = p["anlati"]; egim = p.get("egim", False)
            self.anlati(cv, a["metin"], x0 + 50, y0 + 70 + (100 if egim else 0), a.get("boy", 88), prog(t, a["t"], 0.4),
                        a.get("aci", -4.5 if egim else -2.0), c[a.get("renk", "sari")])

    def anlati(self, cv, metin, x, y, boy, p, aci, dolgu):
        """sol üstteki anlatıcı kutusu: soldan kayarak girer"""
        if p <= 0: return
        f = self.font(boy); w = f.measureText(metin) + boy * 0.7; h = boy * 1.15
        cv.save(); cv.translate(x - (1 - out_cubic(p)) * (w + 120), y); cv.rotate(aci)
        r = skia.Rect.MakeXYWH(0, 0, w, h)
        cv.drawRect(r.makeOffset(10, 10), boya(self.c["murekkep"]))
        cv.drawRect(r, boya(dolgu)); cv.drawRect(r, boya(self.c["murekkep"], 1, 8))
        self.yazi(cv, metin, boy * 0.35, h * 0.80, boy, self.c["murekkep"], kontur=0, hiza=0)
        cv.restore()

    def yer(self, o, P):
        k = P["k"] * o.get("olcek", 1.0)
        return P["x0"] + o.get("x", 0.5) * P["pw"], P["y0"] + o.get("y", 0.5) * P["ph"], k

    # ---------- öğeler (ic=True: panelin içinde kırpılı; ic=False: çerçevenin üstünde) ----------
    def o_yazi(self, cv, t, o, P, ic):
        if not ic or t < o["t"] - zaman.CARPMA_SN: return
        X, Y, k = self.yer(o, P)
        giris = o.get("giris", "carp")
        if giris == "carp":
            s = lerp(2.6, 1.0, in_cubic(prog(t, o["t"] - zaman.CARPMA_SN, zaman.CARPMA_SN)))
            dx, dy = sarsinti(t, o["t"], 18)
        elif giris == "pop":
            if t < o["t"]: return
            s = out_back(prog(t, o["t"], 0.3), 2.2); dx = dy = 0
        else:
            if t < o["t"]: return
            s = 1.0; dx = dy = 0
        boy = o.get("boy", 200)
        cv.save(); cv.translate(X + dx, Y + dy); cv.scale(s * k, s * k); cv.rotate(o.get("aci", 0))
        self.yazi(cv, o["metin"], 0, 0, boy, self.c[o["renk"]], derinlik=o.get("derinlik", 0),
                  kontur=o.get("kontur", 14 if boy >= 150 else 0), hiza=o.get("hiza", 0.5))
        cv.restore()

    def o_patlama(self, cv, t, o, P, ic):
        if ic: return
        X, Y, k = self.yer(o, P); ink = self.c["murekkep"]
        sayacli = "sayac" in o
        vur = zaman.vurus_ani(o)
        if sayacli:
            if t < o["t"]: return
            ilk, son = o["sayac"]["degerler"]
            sayi = int(round(lerp(ilk, son, out_cubic(prog(t, o["t"], o["sayac"]["bitis_t"] - o["t"])))))
            metin = f"{sayi}{o.get('son_ek', '')}" if t >= vur else str(sayi)
            dolgu = self.c[o["renk"]] if t >= vur else self.c[o.get("ara_renk", "beyaz")]
            s = out_back(prog(t, o["t"], 0.3)) * (1 + 0.22 * (1 - out_cubic(prog(t, vur, 0.25))) * (t >= vur))
            pb, don = 1.0, o.get("aci", -8)
            r, boy, der, kon = o.get("r", 400), o.get("boy", 290), o.get("derinlik", 24), 16
        else:
            if t < vur - zaman.CARPMA_SN: return
            metin, dolgu = o["metin"], self.c[o["renk"]]
            s = lerp(2.6, 1.0, in_cubic(prog(t, vur - zaman.CARPMA_SN, zaman.CARPMA_SN))) * (1 + 0.025 * math.sin(max(0, t - vur) * 5))
            pb, don = out_back(prog(t, vur, 0.3)), o.get("aci", 0) + t * o.get("donus", 6)
            r, boy, der, kon = o.get("r", 470), o.get("boy", 560), o.get("derinlik", 34), 18
        dx, dy = sarsinti(t, vur, 16)
        cv.save(); cv.translate(X + dx, Y + dy); cv.scale(s * k, s * k)
        if sayacli: cv.rotate(don)
        cv.save(); cv.scale(pb, pb)
        if not sayacli: cv.rotate(don)
        b = patlama_yolu(r, n=o.get("uc", 13 if not sayacli else 12), seed=o.get("seed", 5), sivri=0.62 if not sayacli else 0.7)
        cv.drawPath(kaydir(b, 14, 14), boya(ink)); self.murekkep(cv, b, self.c[o["zemin"]], 14)
        cv.restore()
        self.yazi(cv, metin, -14 if not sayacli else 0, boy * 0.36, boy, dolgu, derinlik=der, kontur=kon)
        cv.restore()

    def o_takvim(self, cv, t, o, P, ic):
        if not ic: return
        gir = out_back(prog(t, o["t"], 0.35), 1.6)
        cik_t = o.get("cikis_t", o["bitis_t"] + 0.03)
        cik = in_cubic(prog(t, cik_t, 0.25))
        if gir <= 0 or cik >= 1: return
        X, Y, k = self.yer(o, P); c = self.c; ink = c["murekkep"]
        cv.save(); cv.translate(X + cik * 900 * k, Y - (1 - gir) * 1300 * k - cik * 300 * k); cv.scale(k, k); cv.rotate(-4 + cik * 50)
        w, h = 520, 560
        kutu = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
        cv.drawRect(kutu.makeOffset(16, 16), boya(ink)); cv.drawRect(kutu, boya(c["beyaz"]))
        ust = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, 130)
        cv.drawRect(ust, boya(c[o["renk"]]))
        self.nokta_ciz(cv, skia.Path().addRect(ust), "takvim", (-w / 2, -h / 2, w / 2, -h / 2 + 130), 11, lambda x, y: 3.4, c[o["golge"]])
        cv.drawRect(ust, boya(ink, 1, 10)); cv.drawRect(kutu, boya(ink, 1, KONTUR))
        for hx in (-150, 150):
            rr = skia.Rect.MakeXYWH(hx - 16, -h / 2 - 40, 32, 80)
            cv.drawRoundRect(rr, 16, 16, boya(0xFF9A9A9A)); cv.drawRoundRect(rr, 16, 16, boya(ink, 1, 8))
        ilk, son = o.get("degerler", [1, 7])
        bas = o["t"] + 0.3
        f = prog(t, bas, o["bitis_t"] - bas) * (son - ilk)
        gun = min(son, ilk + int(f))
        self.yazi(cv, str(min(son, gun + 1) if f > 0 else gun), 0, 190, 330, ink, kontur=0)
        if gun < son:
            q = f - int(f)
            cv.save(); cv.translate(q * 380, -q * 260); cv.rotate(q * 35)
            kag = skia.Rect.MakeXYWH(-w / 2, -h / 2 + 130, w, h - 130)
            cv.drawRect(kag, boya(c["beyaz"])); cv.drawRect(kag, boya(ink, 1, 10))
            self.yazi(cv, str(gun), 0, 190, 330, ink, kontur=0)
            cv.restore()
        cv.restore()

    def o_buyume_oku(self, cv, t, o, P, ic):
        x0, y0, pw, ph, k = P["x0"], P["y0"], P["pw"], P["ph"], P["k"] * o.get("olcek", 1.0)
        (ax, ay), (bx, by) = o.get("baslangic", [0.11, 0.9]), o.get("bitis", [0.9, -0.07])
        e = o.get("us", 3.4)
        def nokta(v):
            return x0 + pw * lerp(ax, bx, v), y0 + ph * lerp(ay, by, (math.exp(e * v) - 1) / (math.exp(e) - 1))
        u = in_out_cubic(prog(t, o["t"], o["bitis_t"] - o["t"]))
        c = self.c; ink = c["murekkep"]
        if ic:
            n = o.get("sutun", 12)
            if n:
                taban = y0 + ph + 60; w = min(54 * k, pw * abs(bx - ax) / n * 0.45)
                for i in range(n):
                    ui = (i + 0.5) / n; x, y = nokta(ui)
                    g = out_back(prog(u, ui - 0.02, 0.12)) if u > ui - 0.02 else 0
                    if g <= 0: continue
                    top = lerp(taban - 140 * k, y + 40 * k, g)
                    r = skia.Rect.MakeLTRB(x - w, top, x + w, taban)
                    cv.drawRect(r, boya(c[o["sutun_renk"]]))
                    self.nokta_ciz(cv, yol([(x + w * 0.2, top), (x + w, top), (x + w, taban), (x + w * 0.2, taban)]), ("sutun",) + P["ana"] + (i,),
                                   (x - w, y0 - 200, x + w, taban), 10, lambda px, py: 3.6, c[o["sutun_golge"]])
                    cv.drawRect(r, boya(ink, 1, 9))
            return
        if u <= 0: return
        m = 60; pts = [nokta(u * i / m) for i in range(m + 1)]
        govde = yol(pts, False)
        cv.drawPath(govde, boya(ink, 1, 128 * k)); cv.drawPath(govde, boya(c[o["renk"]], 1, 100 * k))
        isik = yol([(x - 22 * k, y - 10 * k) for x, y in pts[: max(2, m - 4)]], False)
        cv.drawPath(isik, boya(0xFFFFFFFF, 0.4, 14 * k))
        (x1, y1), (xa, ya) = pts[-1], pts[-2]
        a = math.atan2(y1 - ya, x1 - xa)
        uc = [(x1 + 120 * k * math.cos(a), y1 + 120 * k * math.sin(a)),
              (x1 + 110 * k * math.cos(a + 2.2), y1 + 110 * k * math.sin(a + 2.2)),
              (x1 + 110 * k * math.cos(a - 2.2), y1 + 110 * k * math.sin(a - 2.2))]
        self.murekkep(cv, yol(uc), c[o["renk"]], 13 * k)
        if o.get("cerceveyi_kir", True):
            kir = prog(t, o.get("kirik_t", o["bitis_t"] - 0.2), 0.6)
            if kir > 0:
                ex, ey = nokta(1.0); ey = max(ey, y0 + 30)
                rng = np.random.default_rng(9)
                for _ in range(7):
                    ang = rng.uniform(-2.6, -0.5); hz = rng.uniform(260, 520) * k
                    px = ex + math.cos(ang) * hz * out_cubic(kir); py = ey + math.sin(ang) * hz * out_cubic(kir) + 500 * k * kir ** 2
                    sz = rng.uniform(18, 34) * k
                    cv.save(); cv.translate(px, py); cv.rotate(kir * rng.uniform(-300, 300))
                    self.murekkep(cv, yol([(-sz, -sz * 0.4), (sz * 0.8, -sz), (sz * 0.5, sz), (-sz * 0.6, sz * 0.7)]), c["beyaz"], 7)
                    cv.restore()

    def o_filiz(self, cv, t, o, P, ic):
        p = prog(t, o["t"], 0.45)
        if not ic or p <= 0: return
        X, Y, k = self.yer(o, P); c = self.c; ink = c["murekkep"]
        cv.save(); cv.translate(X, Y); cv.scale(k, k)
        self.murekkep(cv, yol([(-80, 0), (80, 0), (60, 120), (-60, 120)]), c[o["saksi"]], 10)
        kenar = skia.Rect.MakeLTRB(-92, -24, 92, 6)
        cv.drawRect(kenar, boya(c[o["saksi"]])); cv.drawRect(kenar, boya(ink, 1, 10))
        h = 150 * out_back(p); sal = 6 * math.sin(t * 4)
        sap = skia.Path(); sap.moveTo(0, -24); sap.quadTo(sal, -24 - h * 0.5, sal * 1.5, -24 - h)
        cv.drawPath(sap, boya(ink, 1, 22)); cv.drawPath(sap, boya(c[o["yaprak"]], 1, 10))
        for sx in (-1, 1):
            yp = skia.Path(); tx, ty = sal * 1.5, -24 - h
            yp.moveTo(tx, ty); yp.quadTo(tx + sx * 70 * p, ty - 60 * p, tx + sx * 110 * p, ty - 10 * p); yp.quadTo(tx + sx * 60 * p, ty + 30 * p, tx, ty)
            self.murekkep(cv, yp, c[o["yaprak"]], 9)
        cv.restore()

    def o_agac(self, cv, t, o, P, ic):
        if not ic or t < o["t"]: return
        X, Y, k = self.yer(o, P); c = self.c; ink = c["murekkep"]
        g = out_back(prog(t, o["t"], 0.45), 1.4)
        cv.save(); cv.translate(X, Y); cv.scale(k * g, k * g)
        govde = yol([(-55, 0), (55, 0), (40, -330), (120, -470), (80, -480), (10, -380), (-30, -500), (-70, -490), (-40, -330)])
        self.murekkep(cv, govde, c[o["govde"]], 12)
        rng = np.random.default_rng(21)
        daireler = [(0, -660, 300)] + [(260 * math.cos(a), -660 + 210 * math.sin(a), rng.uniform(150, 210)) for a in np.linspace(0, 2 * math.pi, 9, endpoint=False)]
        cv.translate(8 * math.sin(t * 2.2), 0)  # taç rüzgârda hafifçe salınır
        tac = skia.Path()
        for cx, cy, r in daireler: tac.addCircle(cx, cy, r)
        cv.drawPath(tac, boya(ink, 1, 26)); cv.drawPath(tac, boya(c[o["tac"]]))
        self.nokta_ciz(cv, tac, "tac", (-560, -1000, 560, -300), 15, lambda px, py: 6.8 * clamp((px + 60) / 380) ** 1.1, c[o["golge"]])
        for cx, cy, r in daireler[1:6]:
            cv.drawArc(skia.Rect.MakeXYWH(cx - r * 0.6, cy - r * 0.6, r * 1.2, r * 1.2), 200, 70, False, boya(c[o["isik"]], 1, 14))
        if o.get("meyveler", True):
            for i, (cx, cy) in enumerate(((-150, -760), (120, -820), (230, -600), (-260, -560), (20, -520))):
                pp = out_back(prog(t, o["t"] + 0.4 + i * 0.07, 0.25))
                if pp > 0:
                    cv.drawCircle(cx, cy, 34 * pp, boya(c[o["meyve"]])); cv.drawCircle(cx, cy, 34 * pp, boya(ink, 1, 8))
                    cv.drawCircle(cx - 10 * pp, cy - 10 * pp, 9 * pp, boya(c["beyaz"]))
        cv.restore()
        if o.get("zemin_bandi", True):  # çimen bandı panelin altına kadar
            bant = skia.Rect.MakeLTRB(P["x0"] - 20, Y - 10 * k, P["x0"] + P["pw"] + 20, P["y0"] + P["ph"] + 60)
            cv.drawRect(bant, boya(c[o["cimen"]])); cv.drawLine(bant.left(), bant.top(), bant.right(), bant.top(), boya(ink, 1, 10))

    def o_kahraman(self, cv, t, o, P, ic):
        if not ic or t < o["t"]: return
        X, Y, k = self.yer(o, P)
        yuk = out_back(prog(t, o["t"], 0.45), 1.3)
        yum = 0.0
        if "yumruk_t" in o:
            yum = clamp(out_back(prog(t, o["yumruk_t"], 0.3), 2.5) - 0.5 * out_cubic(prog(t, o["yumruk_t"] + 0.4, 0.5)), -0.2, 1.3)
        goz = 1 - math.sin(math.pi * prog(t, o["goz_kirp_t"], 0.16)) if "goz_kirp_t" in o else 1.0
        self.kahraman(cv, o, X, Y + (1 - yuk) * 950 * k, k, yum, goz)

    def kahraman(self, cv, o, x, y, s, yumruk, goz):
        c = self.c; ink = c["murekkep"]; ten, tis = c[o["ten"]], c[o["tisort"]]
        cv.save(); cv.translate(x, y); cv.scale(s, s)
        govde = skia.Path(); govde.moveTo(-340, 760); govde.lineTo(-340, 430)
        govde.cubicTo(-340, 300, -250, 250, -120, 232); govde.lineTo(120, 232)
        govde.cubicTo(250, 250, 340, 300, 340, 430); govde.lineTo(340, 760); govde.close()
        omuz, dirsek, el = (250, 330), (450, 150 - 30 * yumruk), (400, -150 - 80 * yumruk)
        kol = skia.Path(); kol.moveTo(*omuz); kol.lineTo(*dirsek); kol.lineTo(*el)
        cv.drawPath(kol, boya(ink, 1, 132)); cv.drawPath(kol, boya(ten, 1, 108))
        cv.drawPath(govde, boya(tis))
        self.nokta_ciz(cv, govde, "govde", (-340, 230, 340, 760), 13, lambda px, py: 5.5 * clamp((px - 110) / 230), c[o["tisort_golge"]])
        cv.drawPath(govde, boya(ink, 1, KONTUR))
        yildiz = [(math.cos(-math.pi / 2 + i * math.pi / 5) * (95 if i % 2 == 0 else 40),
                   520 + math.sin(-math.pi / 2 + i * math.pi / 5) * (95 if i % 2 == 0 else 40)) for i in range(10)]
        self.murekkep(cv, yol(yildiz), c[o["yildiz"]], 9)
        kolluk = skia.Path(); kolluk.moveTo(*omuz); kolluk.lineTo(lerp(omuz[0], dirsek[0], 0.42), lerp(omuz[1], dirsek[1], 0.42))
        cv.drawPath(kolluk, boya(ink, 1, 150)); cv.drawPath(kolluk, boya(tis, 1, 126))
        cv.save(); cv.translate(*el); cv.rotate(-4)
        yr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-78, -82, 156, 150), 46, 46)
        cv.drawRRect(yr, boya(ten)); cv.drawRRect(yr, boya(ink, 1, 11))
        for fx in (-38, 0, 38):
            cv.drawLine(fx, -82, fx, -30, boya(ink, 1, 8))
        cv.drawArc(skia.Rect.MakeXYWH(-90, -10, 90, 70), 200, 120, False, boya(ink, 1, 8))
        cv.restore()
        boyun = skia.Path(); boyun.addRect(skia.Rect.MakeLTRB(-62, 120, 62, 262))
        cv.drawPath(boyun, boya(ten))
        self.nokta_ciz(cv, boyun, "boyun", (-62, 120, 62, 262), 11, lambda px, py: 5.0 * clamp((215 - py) / 80), c[o["ten_golge"]])
        cv.drawLine(-62, 120, -62, 238, boya(ink, 1, 11)); cv.drawLine(62, 120, 62, 238, boya(ink, 1, 11))
        cv.drawPath(yol([(-70, 236), (0, 300), (70, 236)], False), boya(ink, 1, 11))
        for sx in (-1, 1):
            kulak = skia.Path(); kulak.addOval(skia.Rect.MakeXYWH(sx * 168 - 40, -30, 80, 96)); self.murekkep(cv, kulak, ten, 10)
        kafa = skia.Path(); kafa.addOval(skia.Rect.MakeLTRB(-168, -195, 168, 200))
        cv.drawPath(kafa, boya(ten))
        self.nokta_ciz(cv, kafa, "kafa", (-170, -200, 170, 200), 12, lambda px, py: 5.4 * clamp((px - 55) / 110), c[o["ten_golge"]])
        cv.drawPath(kafa, boya(ink, 1, KONTUR))
        sac = [(-178, 20), (-196, -110), (-150, -108), (-170, -228), (-96, -172), (-66, -296), (-2, -206), (58, -306),
               (92, -196), (172, -246), (152, -124), (196, -112), (176, 22), (136, -66), (64, -108), (-18, -88), (-104, -112), (-142, -56)]
        self.murekkep(cv, yol(sac), c[o["sac"]])
        for a0, a1 in (((-120, -150), (-60, -205)), ((30, -170), (80, -215))):
            cv.drawLine(*a0, *a1, boya(c[o["sac_isik"]], 1, 10))
        cv.drawLine(-122, -58, -36, -36, boya(ink, 1, 24)); cv.drawLine(36, -36, 122, -58, boya(ink, 1, 24))
        for sx in (-1, 1):
            cv.save(); cv.translate(sx * 72, 6); cv.scale(1, max(0.08, goz))
            g = skia.Rect.MakeXYWH(-34, -42, 68, 84)
            cv.drawOval(g, boya(c["beyaz"])); cv.drawOval(g, boya(ink, 1, 7))
            cv.drawCircle(-sx * 6, 8, 17, boya(ink)); cv.drawCircle(-sx * 6 + 6, 1, 5.5, boya(c["beyaz"]))
            cv.restore()
        burun = skia.Path(); burun.moveTo(0, 30); burun.quadTo(-26, 72, 6, 78)
        cv.drawPath(burun, boya(ink, 1, 8))
        agiz = skia.Path(); agiz.moveTo(-88, 100); agiz.quadTo(0, 200, 88, 100); agiz.close()
        cv.drawPath(agiz, boya(0xFF6E1020))
        cv.save(); cv.clipPath(agiz, doAntiAlias=True)
        cv.drawRect(skia.Rect.MakeLTRB(-90, 96, 90, 124), boya(c["beyaz"])); cv.drawCircle(0, 178, 42, boya(c["kirmizi"]))
        cv.restore()
        cv.drawPath(agiz, boya(ink, 1, 9))
        cv.restore()

    def o_balon(self, cv, t, o, P, ic):
        if ic or t < o["t"]: return
        X, Y, k = self.yer(o, P); c = self.c; ink = c["murekkep"]
        b = out_back(prog(t, o["t"], 0.3), 2.2)
        rx, ry = o.get("rx", 450), o.get("ry", 265)
        kx, ky = o.get("kuyruk", [30, 430])
        cv.save(); cv.translate(X, Y); cv.scale(b * k, b * k); cv.rotate(o.get("aci", -2))
        balon = skia.Path(); balon.addOval(skia.Rect.MakeXYWH(-rx, -ry, 2 * rx, 2 * ry))
        kuyruk = yol([(kx * 0.3 - 50, ry * 0.79), (kx * 0.3 + 100, ry * 0.83), (kx, ky)])
        for pth in (balon, kuyruk): cv.drawPath(kaydir(pth, 12, 12), boya(ink))
        for pth in (balon, kuyruk): cv.drawPath(pth, boya(ink, 1, 26))
        for pth in (balon, kuyruk): cv.drawPath(pth, boya(c["beyaz"]))
        st = o["satirlar"]; boy = o.get("boy", 205); ara = boy * 0.96
        for i, sat in enumerate(st):
            r = sat.get("renk", "murekkep")
            self.yazi(cv, sat["metin"], 0, (i - (len(st) - 1) / 2) * ara + boy * 0.39, boy, c[r], kontur=0 if r == "murekkep" else 10)
        cv.restore()

    def o_gorsel(self, cv, t, o, P, ic):
        if ic or t < o["t"]: return
        if o["yol"] not in self._gorsel:
            self._gorsel[o["yol"]] = skia.Image.open(str(self.klasor / o["yol"]))
        im = self._gorsel[o["yol"]]
        X, Y, _ = self.yer(o, P)
        w = o.get("genislik", 0.5) * P["pw"]; h = w * im.height() / im.width()
        s = out_back(prog(t, o["t"], 0.3), 2.0)
        cv.save(); cv.translate(X, Y); cv.scale(s, s); cv.rotate(o.get("aci", -3))
        r = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
        if o.get("kart", True):
            kart = r.makeOutset(30, 30)
            cv.drawRect(kart.makeOffset(14, 14), boya(self.c["murekkep"])); cv.drawRect(kart, boya(self.c["beyaz"]))
            cv.drawRect(kart, boya(self.c["murekkep"], 1, 10))
        cv.drawImageRect(im, r, skia.SamplingOptions(skia.CubicResampler.Mitchell()))
        cv.restore()

    # ---------- kare ----------
    def kamera_y(self, t):
        y = 0.0
        for sh in self.s["sahneler"][1:]:
            y += in_out_cubic(prog(t, sh["bas"] - zaman.KAYDIRMA_SN / 2, zaman.KAYDIRMA_SN))
        return y * self.VH

    def kare(self, cv, t):
        cv.save(); cv.scale(self.u, self.u)
        cv.drawRect(skia.Rect.MakeWH(self.VW, self.VH), boya(self.c["kagit"]))
        ky = self.kamera_y(t)
        for i in range(len(self.s["sahneler"])):
            oy = i * self.VH - ky
            if oy >= self.VH or oy <= -self.VH: continue
            cv.save(); cv.translate(0, oy)
            self.sahne(cv, t, i)
            cv.restore()
        cv.restore()


def kareler(s: dict, fmt: str, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    klasor.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H, fmt); out = []
    for t in anlar:
        surf = skia.Surface(W, H)
        with surf as cv:
            c.kare(cv, t)
        p = klasor / f"{s.get('kimlik', 'cizgi-roman')}-{fmt}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(p), skia.kPNG); out.append(p)
    return out


def kapak(s: dict, fmt: str, W: int, H: int, t: float, yol_: Path) -> Path:
    surf = skia.Surface(W, H)
    with surf as cv:
        Cizici(s, W, H, fmt).kare(cv, t)
    surf.makeImageSnapshot().save(str(yol_), skia.kPNG)
    return yol_


def video(s: dict, fmt: str, W: int, H: int, yol_: Path) -> Path:
    yol_.parent.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H, fmt)
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
        raise RuntimeError("ffmpeg görüntü kodlaması başarısız")
    return yol_
