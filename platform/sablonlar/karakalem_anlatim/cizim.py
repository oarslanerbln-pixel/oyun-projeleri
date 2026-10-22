"""Karakalem anlatımının görüntüsü: defter sayfasında kurşun kalemle çizilen serbest sahneler (skia).

Sahneler 1600×900'lük sanal bir sayfada kurulur ve çıktıya sığdırılır (16:9 tam dolar; başka formatta
sayfa ortalanır, kenarlar kâğıt rengindedir). Her sahne önce kalemle çizilir ve yazılır (`zaman.cizim_suresi`),
sonra çizgiler saniyede 12 kez kaynar, kamera yavaşça yaklaşır, oklar ve sayaçlar yaşamaya devam eder.
Her kare t'nin saf fonksiyonudur. Kâğıt düz renktir; doku ve gren gri üstü bindirme, radyal gradyan
ve parlama yok. Kalem, karakter ve yazı tipleri karakalem şablonundan gelir.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

BURADA = Path(__file__).resolve().parent
sys.path.append(str(BURADA.parent / "karakalem"))  # kalem, karakter, fontlar (zaman ve cizim buradaki)
import fontlar  # noqa: E402
import karakter  # noqa: E402
import zaman  # noqa: E402
from kalem import Kalem, bol, elips_noktalari, gurultu, karistir, karma, renk  # noqa: E402

SW, SH = 1600.0, 900.0      # sanal sayfa
ALT_Y = 812.0               # altyazı satırının taban çizgisi (sahne içeriği bunun üstünde kalır)
GOLGE = "#28282E"
BEYAZ = "#FFFFFF"
_HARITA = None


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, k): return a + (b - a) * k
def out_back(p, s=2.2): p = clamp(p) - 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def harita_verisi() -> dict:
    global _HARITA
    if _HARITA is None:
        _HARITA = json.loads((BURADA / "veri" / "avrupa.json").read_text(encoding="utf-8"))["ulkeler"]
    return _HARITA


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        import skia
        self.skia, self.s, self.W, self.H = skia, s, W, H
        self.pal = s["palet"]
        self.ink, self.vur = self.pal["grafit"], self.pal["vurgu"]
        self.acik = karistir(self.vur, self.pal["kagit"], 0.78)
        self.k = Kalem(self.ink)
        self.olcek = min(W / SW, H / SH)
        self.ox, self.oy = (W - SW * self.olcek) / 2, (H - SH * self.olcek) / 2
        self.yazi = {a: skia.Typeface.MakeFromFile(fontlar.bul(a)) for a in ("el", "damga")}
        self.vo = zaman.kelimeler(s, s.get("_sureler", {}))
        self._doku = self._doku_uret()

    # ---------- kâğıt dokusu: kalıcı lif + kaynayan gren, gri (128) çevresinde bindirme ----------
    def _doku_uret(self):
        skia = self.skia
        rng = np.random.default_rng(5)
        H, W = self.H, self.W
        kaba = rng.standard_normal((H // 6 + 2, W // 6 + 2)).astype(np.float32)
        kaba = np.kron(kaba, np.ones((6, 6), np.float32))[:H, :W]
        kaba = (kaba + np.roll(kaba, 3, 0) + np.roll(kaba, 3, 1) + np.roll(kaba, (3, 3), (0, 1))) / 4
        out = []
        for _ in range(3):
            g = rng.standard_normal((H, W)).astype(np.float32)
            v = np.clip(128 + kaba * 5.5 + g * 7.0, 0, 255).astype(np.uint8)
            a = np.empty((H, W, 4), np.uint8); a[..., 0] = a[..., 1] = a[..., 2] = v; a[..., 3] = 255
            out.append(skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType))
        return out

    # ---------- yazı ----------
    def _ad(self, metin, ad):
        """damga yazı tipinde (Permanent Marker) Türkçe ğ, ş, İ yok: o metin el yazısıyla yazılır"""
        if ad == "damga" and 0 in self.yazi[ad].unicharsToGlyphs([ord(c) for c in metin]):
            return "el"
        return ad

    def _font(self, ad, punto):
        f = self.skia.Font(self.yazi[ad], punto)
        f.setSubpixel(True); f.setEdging(self.skia.Font.Edging.kAntiAlias)
        return f

    def olc(self, metin, punto, ad="el"):
        ad = self._ad(metin, ad)
        return self._font(ad, punto).measureText(metin)

    def sigdir(self, metin, punto, sinir, ad="el"):
        w = self.olc(metin, punto, ad)
        return punto * sinir / w if w > sinir else punto

    def sar(self, metin, punto, sinir, ad="el"):
        satirlar, cur = [], ""
        for w in metin.split():
            dene = f"{cur} {w}" if cur else w
            if cur and self.olc(dene, punto, ad) > sinir:
                satirlar.append(cur); cur = w
            else:
                cur = dene
        return satirlar + ([cur] if cur else [])

    def metin(self, cv, metin, x, y, punto, rgb, ad="el", ortala=False, alfa=1.0):
        f = self._font(self._ad(metin, ad), punto)
        j = len(metin) * 13 + punto  # yazı da hafifçe kaynar
        dx, dy = math.sin(j + self.k.kaynama * 1.7) * 0.7, math.cos(j * 1.3 + self.k.kaynama * 2.1) * 0.7
        if ortala:
            x -= f.measureText(metin) / 2
        p = self.skia.Paint(AntiAlias=True, Color=rgb)
        if alfa < 1:
            p.setAlphaf(p.getAlphaf() * alfa)
        cv.drawString(metin, x + dx, y + dy, f, p)

    def halo(self, cv, metin, x, y, punto, alfa=1.0, ad="el"):
        """yazının arkasına kâğıt renginde kalın kontur: çizgilerin üstünde okunur"""
        sk = self.skia
        p = sk.Paint(AntiAlias=True, Color=renk(self.pal["kagit"], 0.92 * alfa))
        p.setStyle(sk.Paint.kStroke_Style); p.setStrokeWidth(punto * 0.22); p.setStrokeJoin(sk.Paint.kRound_Join)
        cv.drawString(metin, x, y, self._font(self._ad(metin, ad), punto), p)

    def yaz(self, cv, metin, x, y, punto, rgb, p, ad="el", ortala=False, kalem=True):
        """el yazısı: soldan sağa açılır, kalem ucu yazının ucunda"""
        if p <= 0:
            return
        w = self.olc(metin, punto, ad)
        x0 = x - w / 2 if ortala else x
        ex = x0 + (w + punto * 0.3) * clamp(p)
        cv.save(); cv.clipRect(self.skia.Rect.MakeLTRB(x0 - punto, y - punto * 1.2, ex, y + punto * 0.6), True)
        self.metin(cv, metin, x0, y, punto, rgb, ad)
        cv.restore()
        if kalem and p < 1:
            self.kalem(cv, ex, y - punto * 0.3 + math.sin(p * 60) * punto * 0.15, 0.32 * punto / 60)

    # ---------- kalem ----------
    def kalem(self, cv, x, y, olcek=0.5):
        k, sk = self.k, self.skia
        cv.save(); cv.translate(x, y); cv.scale(olcek, olcek); cv.rotate(math.degrees(-0.75))
        cv.drawRect(sk.Rect.MakeXYWH(6, -10, 240, 22), sk.Paint(AntiAlias=True, Color=renk(GOLGE, 0.12)))
        k.cokgen(cv, [(0, 0), (44, -14), (44, 14)], dolgu="#EAD7B5", lw=3, seed=7, ikinci=False)
        k.cokgen(cv, [(0, 0), (14, -4.5), (14, 4.5)], dolgu=self.ink, lw=2, seed=8, ikinci=False)
        k.cokgen(cv, [(44, -14), (210, -14), (210, 14), (44, 14)], dolgu=self.vur, lw=3, seed=9, ikinci=False)
        k.cokgen(cv, [(210, -14), (232, -14), (232, 14), (210, 14)], dolgu="#B9B6B0", lw=3, seed=11, ikinci=False)
        k.cokgen(cv, [(232, -13), (252, -13), (252, 13), (232, 13)], dolgu="#E9A7A0", lw=3, seed=12, ikinci=False)
        cv.restore()

    def yol_ciz(self, cv, pts, p, rgb=None, lw=4.0, seed=1, kalem=True, kesik=None, amp=1.4):
        """yay uzunluğuna göre kısmen çizilen kalem çizgisi"""
        if p <= 0 or len(pts) < 2:
            return None
        q = zaman.kismi(pts, p)
        if len(q) > 1:
            self.k.cizgi(cv, q, rgb, lw=lw, seed=seed, adim=12, kesik=kesik, amp=amp)
        if kalem and p < 1:
            self.kalem(cv, q[-1][0], q[-1][1], 0.42)
        return q[-1]

    def ok_ucu(self, cv, a, b, rgb, boy=34.0, lw=6.0, seed=3):
        aci = math.atan2(b[1] - a[1], b[0] - a[0])
        for s_ in (-1, 1):
            u = aci + math.pi + s_ * 0.45
            self.k.cizgi(cv, [b, (b[0] + math.cos(u) * boy, b[1] + math.sin(u) * boy)], rgb, lw=lw, seed=seed + s_)

    def cerceve(self, cv, x0, y0, x1, y1, p, seed=5, lw=4.0):
        """elle çizilmiş çerçeve: köşelerden taşan iki çizgi"""
        kenar = [[(x0 - 14, y0), (x1 + 10, y0 + 2)], [(x1, y0 - 12), (x1 - 2, y1 + 12)],
                 [(x1 + 12, y1), (x0 - 10, y1 - 2)], [(x0, y1 + 10), (x0 + 2, y0 - 14)]]
        for i, c in enumerate(kenar):
            self.yol_ciz(cv, c, clamp(p * 4 - i), lw=lw, seed=seed + i, kalem=False)

    def tarali_kutu(self, cv, kutu, rgb, aralik=9.0, aci=-0.9, lw=1.6, seed=3):
        sk = self.skia
        cv.save(); cv.clipRect(sk.Rect.MakeLTRB(*kutu), True)
        self.k.tara(cv, kutu, rgb, aralik=aralik, aci=aci, lw=lw, seed=seed)
        cv.restore()

    # ---------- 1. bölüm kartı ----------
    def baslik(self, cv, sh, u, D):
        cx = SW / 2
        ust, metin, alt = sh.get("ust"), sh["metin"], sh.get("alt")
        punto = self.sigdir(metin, 150, 1240)
        y = 470 if alt else 500
        if ust:
            pu = self.sigdir(ust.upper(), 46, 900, "damga")
            w = self.olc(ust.upper(), pu, "damga")
            a = zaman.asama(u, 0.1, 0.35)
            cv.save(); cv.translate(cx, y - punto * 0.95); cv.rotate(-2); cv.scale(0.8 + 0.2 * out_back(a), 0.8 + 0.2 * out_back(a))
            if a > 0:
                self.k.cokgen(cv, [(-w / 2 - 26, -pu * 0.95), (w / 2 + 26, -pu * 0.95), (w / 2 + 26, pu * 0.35), (-w / 2 - 26, pu * 0.35)],
                              dolgu=self.acik, kontur=self.vur, lw=4, seed=11, alfa=a, ikinci=False)
                self.metin(cv, ust.upper(), 0, 0, pu, renk(self.vur), "damga", ortala=True, alfa=a)
            cv.restore()
        p = zaman.asama(u, 0.35, D * 0.55)
        self.yaz(cv, metin, cx, y, punto, renk(self.ink), p, ortala=True)
        w = self.olc(metin, punto)
        alt_cizgi = [(cx - w * 0.42 + i * w * 0.86 / 30, y + punto * 0.28 + math.sin(i / 30 * math.pi) * 10 - i * 0.6) for i in range(31)]
        self.yol_ciz(cv, alt_cizgi, zaman.asama(u, 0.35 + D * 0.55, D * 0.25), self.vur, lw=9, seed=21)
        if alt:
            pa = self.sigdir(alt, 58, 1100)
            self.yaz(cv, alt, cx, y + punto * 0.28 + 100, pa, renk(karistir(self.ink, self.pal["kagit"], 0.25)),
                     zaman.asama(u, D * 0.8, D * 0.35), ortala=True)
        # köşe süsleri: kalemle atılmış iki köşe parantezi
        pc = zaman.asama(u, 0.0, D * 0.4)
        for sx, sy in ((-1, -1), (1, 1)):
            x0, y0 = cx + sx * 700, 450 + sy * 330
            self.yol_ciz(cv, [(x0, y0 - sy * 120), (x0, y0), (x0 - sx * 160, y0)], pc, lw=5, seed=30 + sx, kalem=False)

    # ---------- 2. harita ----------
    def harita(self, cv, sh, u, D):
        sk, k = self.skia, self.k
        lo0, lo1, la0, la1 = zaman.ODAKLAR[sh.get("odak", "bati-avrupa")]
        cosl = math.cos(math.radians((la0 + la1) / 2))
        bx0, by0, bx1, by1 = 150.0, 130.0 if sh.get("baslik") else 70.0, 1450.0, 770.0
        sx = min((bx1 - bx0) / ((lo1 - lo0) * cosl), (by1 - by0) / (la1 - la0))
        mx = (bx0 + bx1) / 2 - ((lo0 + lo1) / 2) * cosl * sx
        my = (by0 + by1) / 2 + ((la0 + la1) / 2) * sx
        P = lambda lon, lat: (mx + lon * cosl * sx, my - lat * sx)
        vurgulu = set(sh.get("vurgulu", []))
        cerceve = sk.Rect.MakeLTRB(bx0, by0, bx1, by1)
        p_kiyi = zaman.asama(u, 0.1, D * 0.6)
        cv.save(); cv.clipRect(cerceve, True)
        # deniz: kıyıdan bağımsız birkaç dalga işareti
        for i, (lo, la) in enumerate([(-8, 46), (-7, 50.5), (3.4, 55.2), (5.2, 41.3), (17.5, 55.6), (-3.5, 44.6), (15, 39), (-9, 42)]):
            x, y = P(lo, la)
            if bx0 < x < bx1 and by0 < y < by1:
                for j in range(2):
                    dl = [(x - 30 + v * 4, y + j * 14 + math.sin(v * 0.9) * 4) for v in range(16)]
                    k.cizgi(cv, dl, renk(self.ink, 0.35 * clamp(p_kiyi * 2)), lw=2.4, seed=200 + i * 3 + j, amp=0.8)
        ulkeler = harita_verisi()
        etiket = {}
        for iso, ul in ulkeler.items():
            for j, ring in enumerate(ul["p"]):
                pts = [P(a, b) for a, b in ring]
                xs, ys = [q[0] for q in pts], [q[1] for q in pts]
                if max(xs) < bx0 - 40 or min(xs) > bx1 + 40 or max(ys) < by0 - 40 or min(ys) > by1 + 40:
                    continue
                seed = int(karma(len(iso), j, ord(iso[0])) * 900) + 50
                if iso in vurgulu:
                    a = zaman.asama(u, D * 0.45, D * 0.4)
                    if a > 0:
                        yol = k.yol(pts, True)
                        cv.drawPath(yol, k._boya(renk(self.acik), cizgi=False, alfa=a))
                        cv.save(); cv.clipPath(yol, sk.ClipOp.kIntersect, True)
                        lx0, ly0, lx1, ly1 = min(xs), min(ys), max(xs), max(ys)
                        k.tara(cv, (lx0, ly0, lx0 + (lx1 - lx0) * a + 2, ly1), renk(self.vur, 0.55), aralik=8, aci=-0.95, lw=1.8, seed=seed)
                        cv.restore()
                q = zaman.kismi(pts + [pts[0]], p_kiyi)
                if len(q) > 1:
                    k.cizgi(cv, q, renk(self.ink, 0.9 if iso in vurgulu else 0.7), lw=3.6 if iso in vurgulu else 2.6, seed=seed, adim=10, amp=1.0)
                alan = 0.5 * abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts))))
                if alan > etiket.get(iso, (0,))[0]:  # ad en büyük parçanın ortasına
                    etiket[iso] = (alan, sum(xs) / len(xs), sum(ys) / len(ys))
        # ülke adları: vurgulular ve istenenler
        istenen = set(sh.get("etiketler", [])) | vurgulu
        for iso, (alan, x, y) in etiket.items():
            if iso in istenen and bx0 + 60 < x < bx1 - 60:
                ad = ulkeler[iso]["ad"].upper()
                if iso in sh.get("adlar", {}):
                    ad = sh["adlar"][iso]
                self.metin(cv, ad, x, y + 50, 34, renk(self.vur if iso in vurgulu else self.ink, 0.85 * zaman.asama(u, D * 0.6, 0.4)),
                           "damga", ortala=True)
        cv.restore()
        self.cerceve(cv, bx0, by0, bx1, by1, zaman.asama(u, 0, D * 0.35), seed=61)
        # pusula
        cx_, cy_ = bx1 - 70, by0 + 80
        pp = zaman.asama(u, D * 0.3, 0.5)
        self.yol_ciz(cv, [(cx_, cy_ + 34), (cx_, cy_ - 34)], pp, lw=3.5, seed=70, kalem=False)
        if pp >= 1:
            self.ok_ucu(cv, (cx_, cy_ + 34), (cx_, cy_ - 34), self.ink, boy=14, lw=3.5)
            self.metin(cv, "K", cx_, cy_ - 46, 34, renk(self.ink), ortala=True)
        if sh.get("baslik"):
            self.yaz(cv, sh["baslik"], bx0, by0 - 28, self.sigdir(sh["baslik"], 64, 1000), renk(self.ink), zaman.asama(u, 0.1, D * 0.5))
        # şehirler
        sehir, kutular, adlar = {}, [], []
        for c in sh.get("sehirler", []):  # önce bütün noktalar: adlar noktaların üstüne binmesin
            ad, (lon, lat) = (c, zaman.SEHIRLER[c]) if isinstance(c, str) else (c["ad"], (c["boylam"], c["enlem"]))
            x, y = P(lon, lat); kutular.append((x - 12, y - 12, x + 12, y + 12))
        for i, c in enumerate(sh.get("sehirler", [])):
            ad, (lon, lat) = (c, zaman.SEHIRLER[c]) if isinstance(c, str) else (c["ad"], (c["boylam"], c["enlem"]))
            x, y = P(lon, lat); sehir[ad] = (x, y)
            a = zaman.asama(u, D * 0.55 + i * 0.12, 0.25)
            if a <= 0:
                continue
            r = 9 * out_back(a)
            k.daire(cv, x, y, r, renk(self.ink))
            k.elips(cv, x, y, r + 7, r + 7, lw=2.5, seed=90 + i, ikinci=False)
            w = self.olc(ad, 40)
            aday = [(x + 20, y - 14), (x - 20 - w, y - 14), (x - w / 2, y + 50), (x - w / 2, y - 32)]
            if x > bx1 - 220:
                aday = aday[1:] + aday[:1]
            dolu = lambda q: any(q[0] < b[2] and q[0] + w > b[0] and q[1] - 34 < b[3] and q[1] + 6 > b[1] for b in kutular)
            lx, ly = next((q for q in aday if not dolu(q)), aday[0])
            kutular.append((lx, ly - 34, lx + w, ly + 6))
            adlar.append((ad, lx, ly, a))
        # oklar: kavisli, vurgu renginde; çizildikten sonra üstünden bir dalga geçer
        for i, o in enumerate(sh.get("oklar", [])):
            a, b = sehir[o["den"]], sehir[o["ye"]]
            d = math.dist(a, b)
            pa = (a[0] + (b[0] - a[0]) * 22 / d, a[1] + (b[1] - a[1]) * 22 / d)
            pb = (b[0] - (b[0] - a[0]) * 26 / d, b[1] - (b[1] - a[1]) * 26 / d)
            yol = zaman.yay(pa, pb, o.get("egrilik", -0.22))
            p = zaman.asama(u, D * 0.75 + i * 0.3, D * 0.45)
            uc = self.yol_ciz(cv, yol, p, self.vur, lw=8, seed=110 + i)
            if p >= 1:
                self.ok_ucu(cv, yol[-4], yol[-1], self.vur, boy=38, lw=8, seed=120 + i)
                f = ((u - D * 1.2) / 1.6) % 1  # yolda ilerleyen dalga
                q = yol[int(f * (len(yol) - 1))]
                k.elips(cv, q[0], q[1], 13, 13, dolgu=self.acik, kontur=self.vur, lw=4, seed=130 + i, ikinci=False)
            if o.get("etiket") and p > 0.5:
                m = yol[len(yol) // 2]
                pu = 44
                cv.save(); cv.translate(m[0], m[1] - 34); cv.rotate(-4)
                w = self.olc(o["etiket"], pu, "damga")
                aa = clamp((p - 0.5) * 3)
                k.cokgen(cv, [(-w / 2 - 18, -pu * 0.9), (w / 2 + 18, -pu * 0.9), (w / 2 + 18, pu * 0.3), (-w / 2 - 18, pu * 0.3)],
                         dolgu=BEYAZ, kontur=self.vur, lw=3.5, seed=140 + i, alfa=aa, ikinci=False)
                self.metin(cv, o["etiket"], 0, 0, pu, renk(self.vur), "damga", ortala=True, alfa=aa)
                cv.restore()
        for ad, lx, ly, a in adlar:  # şehir adları okların üstünde
            self.halo(cv, ad, lx, ly, 40, a)
            self.metin(cv, ad, lx, ly, 40, renk(self.ink, a))

    # ---------- 3. karakter (anlatıcı) ----------
    def _agiz(self, t, varsayilan):
        """dudak: o an söylenen hecenin ünlüsünde ağız açılır"""
        for l in self.vo:
            if l["t"] <= t < l["son"]:
                for w in l["kelimeler"]:
                    if w["t"] <= t < w["son"]:
                        f = (t - w["t"]) / max(1e-3, w["son"] - w["t"]) * w["hece"]
                        ph = f % 1
                        return "grin" if ph < 0.35 else "o" if ph < 0.7 else "flat"
                return "flat"
        return varsayilan

    def karakter(self, cv, sh, u, D, t):
        sol = sh.get("yon", "sol") == "sol"
        x = 400.0 if sol else 1200.0
        poz, ifade = sh.get("poz", "anlat"), sh.get("ifade", "normal")
        g = zaman.asama(u, 0.0, 0.45)  # sahneye zıplayarak girer
        y = 790 - math.sin(math.pi * g) * 40 * (1 - g)
        nefes = math.sin(t * 2.4) * 0.012
        kol = {"anlat": (0.45, 1.25 + 0.25 * math.sin(t * 2.7)), "dusun": (0.35, 2.75), "sasir": (2.0, 2.05),
               "isaret": (0.35, 1.75), "omuz": (1.15, 1.15), "sevin": (2.6, 2.7)}[poz]
        if not sol:
            kol = kol[::-1]
        yuz = {"normal": ("normal", "smile", "normal"), "endise": ("normal", "worry", "worry"), "sasir": ("wide", "o", "up"),
               "gulumse": ("happy", "smile", "up"), "ciddi": ("normal", "flat", "angry")}[ifade]
        if poz == "sasir":
            yuz = ("wide", "o", "up")
        elif poz == "sevin":
            yuz = ("happy", "grin", "up")
        bakis = 0.8 if sol else -0.8
        karakter.ciz(cv, self.k, self.s["karakter"], self.vur, x, y, s=1.12, sx=1 - nefes, sy=1 + nefes, yon=1, t=t, seed=400,
                     gozler=yuz[0], bakis=bakis, bakis_y=-0.9 if poz == "dusun" else -0.2,
                     agiz=self._agiz(t, yuz[1]), kaslar=yuz[2], kol_sol=kol[0], kol_sag=kol[1],
                     ter=0.7 if ifade == "endise" else 0.0, kizarma=0.6 if ifade == "gulumse" or poz == "sevin" else 0.0,
                     kirp=((t + 0.7) % 3.1) < 0.1)
        if poz == "dusun":  # düşünce noktaları
            for i in range(3):
                a = clamp((u * 1.6 - i * 0.3) % 2.2)
                hx = x + (150 if sol else -150) + (i * 30 if sol else -i * 30)
                self.k.elips(cv, hx, 250 - i * 34, 7 + i * 5, 7 + i * 5, dolgu=BEYAZ, lw=3, seed=150 + i, alfa=clamp(a * 3), ikinci=False)
        # konuşma balonu
        metin = sh.get("metin")
        bx0, bx1 = (720.0, 1460.0) if sol else (140.0, 880.0)
        if metin:
            pu = 62
            sat = self.sar(metin, pu, bx1 - bx0 - 90)
            while len(sat) > 4:
                pu *= 0.9; sat = self.sar(metin, pu, bx1 - bx0 - 90)
            lh = pu * 1.12
            by0 = 150.0; by1 = by0 + len(sat) * lh + 70
            a = zaman.asama(u, 0.3, 0.35)
            if a > 0:
                cv.save()
                ox = bx0 if sol else bx1
                cv.translate(ox, (by0 + by1) / 2); cv.scale(0.6 + 0.4 * out_back(a), 0.6 + 0.4 * out_back(a)); cv.translate(-ox, -(by0 + by1) / 2)
                r = 40
                kose = [(bx0 + r, by0), (bx1 - r, by0), (bx1, by0 + r), (bx1, by1 - r), (bx1 - r, by1)]
                kuyruk_x = bx0 + 60 if sol else bx1 - 60
                uc = (x + (175 if sol else -175), 330 if poz != "dusun" else 250)
                if sol:
                    kose += [(bx0 + 150, by1), uc, (bx0 + 70, by1), (bx0 + r, by1), (bx0, by1 - r), (bx0, by0 + r)]
                else:
                    kose += [(bx1 - 70, by1), uc, (bx1 - 150, by1), (bx0 + r, by1), (bx0, by1 - r), (bx0, by0 + r)]
                self.k.cokgen(cv, kose, adim=18, dolgu=BEYAZ, lw=5, seed=160, alfa=a)
                cv.restore()
                _ = kuyruk_x
            n = sum(len(x_) for x_ in sat)
            p = zaman.asama(u, 0.6, max(0.8, D * 0.75))
            sayac = 0
            for i, sx in enumerate(sat):
                pp = clamp((p * n - sayac) / max(1, len(sx)))
                self.yaz(cv, sx, (bx0 + bx1) / 2, by0 + 45 + pu * 0.75 + i * lh, pu, renk(self.ink), pp, ortala=True)
                sayac += len(sx)
        # notlar: işaretli kısa maddeler
        for i, nt in enumerate(sh.get("notlar", [])):
            yy = 560 + i * 78
            p = zaman.asama(u, D * 0.9 + i * 0.35, 0.5)
            if p <= 0:
                continue
            nx = bx0 + 40
            self.k.cokgen(cv, [(nx, yy - 34), (nx + 36, yy - 34), (nx + 36, yy + 2), (nx, yy + 2)], adim=10, lw=3.5, seed=170 + i, ikinci=False)
            if p > 0.6:
                self.k.cizgi(cv, [(nx + 4, yy - 18), (nx + 16, yy - 4), (nx + 46, yy - 48)], self.vur, lw=6, seed=180 + i)
            self.yaz(cv, nt, nx + 64, yy, self.sigdir(nt, 52, bx1 - nx - 70), renk(self.ink), p)

    # ---------- 4. belge yakın planı ----------
    def belge(self, cv, sh, u, D):
        sk, k = self.skia, self.k
        x0, y0, x1, y1 = 440.0, 80.0, 1160.0, 770.0
        g = zaman.asama(u, 0.0, 0.5)  # kâğıt aşağıdan kayarak gelir
        cv.save()
        cv.translate(800, 425 + (1 - g) * 500); cv.rotate(-2.5 + (1 - g) * 6); cv.translate(-800, -425)
        k.cokgen(cv, [(x0 + 18, y0 + 20), (x1 + 18, y0 + 20), (x1 + 18, y1 + 20), (x0 + 18, y1 + 20)], dolgu=None, kontur=None, seed=200,
                 tarama={"renk_": renk(GOLGE, 0.22), "aralik": 7, "aci": -0.8, "lw": 1.4})
        k.cokgen(cv, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], adim=30, dolgu=BEYAZ, lw=4.5, seed=201)
        k.cizgi(cv, [(x0 + 70, y0 + 10), (x0 + 70, y1 - 10)], renk(self.vur, 0.45), lw=2.5, seed=202)  # kenar boşluğu çizgisi
        # ataş
        k.cizgi(cv, [(x1 - 120, y0 + 60), (x1 - 120, y0 - 40), (x1 - 96, y0 - 58), (x1 - 72, y0 - 40), (x1 - 72, y0 + 80),
                     (x1 - 90, y0 + 96), (x1 - 108, y0 + 80), (x1 - 108, y0 - 20)], "#7A7A82", lw=5, seed=203)
        yy = y0 + 70
        if sh.get("ust"):
            self.metin(cv, sh["ust"], x0 + 100, yy, 34, renk(self.ink, 0.6 * g)); yy += 30
        pb = self.sigdir(sh["baslik"], 66, x1 - x0 - 200, "damga")
        self.yaz(cv, sh["baslik"], x0 + 100, yy + pb, pb, renk(self.ink), zaman.asama(u, 0.4, 0.7), "damga")
        k.cizgi(cv, [(x0 + 100, yy + pb + 26), (x1 - 60, yy + pb + 24)], renk(self.ink, 0.8 * zaman.asama(u, 1.0, 0.2)), lw=3, seed=204)
        yy += pb + 105
        satir = sh["satirlar"]
        lh = min(84.0, (y1 - 120 - yy) / max(1, len(satir)))
        for i, m in enumerate(satir):
            pu = self.sigdir(m, 50, x1 - x0 - 170)
            ty = yy + i * lh
            a0 = 1.0 + i * (D * 0.5 / len(satir))
            if sh.get("vurgu") == i:  # fosforlu kalem: yazıdan sonra üstünden geçer
                pv = zaman.asama(u, D * 0.95, 0.45)
                if pv > 0:
                    w = self.olc(m, pu) + 30
                    hx1 = x0 + 85 + w * pv
                    cv.save(); cv.clipRect(sk.Rect.MakeLTRB(x0 + 80, ty - pu, hx1, ty + pu * 0.5), True)
                    k.cokgen(cv, [(x0 + 85, ty - pu * 0.72), (x0 + 85 + w, ty - pu * 0.8), (x0 + 85 + w, ty + pu * 0.26), (x0 + 85, ty + pu * 0.3)],
                             adim=30, dolgu=karistir(self.vur, BEYAZ, 0.55), kontur=None, seed=210 + i)
                    cv.restore()
            self.yaz(cv, m, x0 + 100, ty, pu, renk(self.ink), zaman.asama(u, a0, D * 0.4))
        if sh.get("kaynak"):
            self.metin(cv, sh["kaynak"], x0 + 100, y1 - 40, 30, renk(self.ink, 0.55 * zaman.asama(u, D * 0.9, 0.3)))
        cv.restore()
        d = sh.get("damga")
        if d:
            a = u - (D + 0.25)
            if a >= 0:
                kk = 1 + 1.4 * math.exp(-a * 16)
                pu = self.sigdir(d.upper(), 70, 520, "damga")
                w = self.olc(d.upper(), pu, "damga")
                cv.save(); cv.translate(1010, 640); cv.rotate(-14); cv.scale(kk, kk)
                k.cokgen(cv, [(-w / 2 - 34, -pu * 0.95), (w / 2 + 34, -pu * 0.95), (w / 2 + 34, pu * 0.45), (-w / 2 - 34, pu * 0.45)],
                         adim=20, kontur=self.vur, lw=7, seed=220, alfa=0.92)
                self.metin(cv, d.upper(), 0, 0, pu, renk(self.vur, 0.92), "damga", ortala=True)
                cv.restore()
                if a < 0.25:
                    k.isinlar(cv, 1010, 620, n=14, r0=w / 2 + 50, r1=w / 2 + 140, lw=4, seed=221, alfa=1 - a / 0.25)

    # ---------- 5. kalabalık / sokak ----------
    def _insan(self, cv, x, y, s, seed, t, kol=0.0, alfa=1.0, pankart=None, vurgu=False):
        k = self.k
        sall = math.sin(t * 3 + seed) * 4
        cv.save(); cv.translate(x, y + sall * 0.3); cv.scale(s, s)
        govde = karistir(self.ink, self.pal["kagit"], 0.55 + karma(seed, 1) * 0.3) if not vurgu else self.acik
        k.cokgen(cv, [(-34, 0), (-40, -110), (-24, -138), (24, -138), (40, -110), (34, 0)], adim=16, dolgu=govde, lw=3.5, seed=seed,
                 alfa=alfa, tarama={"renk_": renk(GOLGE, 0.18 * alfa), "aralik": 8, "aci": -0.9, "lw": 1.3})
        k.elips(cv, 0, -168, 30, 33, dolgu=karistir(self.pal["kagit"], BEYAZ, 0.4), lw=3.5, seed=seed + 1, alfa=alfa)
        if karma(seed, 2) > 0.45:  # saç ya da bere
            k.sekil(cv, [(math.cos(a) * 32, -172 + math.sin(a) * 34) for a in (math.pi + i * math.pi / 8 for i in range(9))],
                    dolgu=self.ink if karma(seed, 3) > 0.5 else "#5A5A62", lw=3, seed=seed + 2, alfa=alfa, kapali=True)
        if pankart:
            el_y = -150 - 60 * kol
            k.cizgi(cv, [(26, -112), (44, el_y)], renk(self.ink, alfa), lw=7, seed=seed + 4)
            k.cizgi(cv, [(44, el_y + 20), (44, -330)], "#8A6A44", lw=7, seed=seed + 5)
            pu = 40
            w = max(150.0, self.olc(pankart, pu, "damga") + 40)
            cv.save(); cv.translate(44, -330); cv.rotate(math.sin(t * 2.2 + seed) * 3)
            k.cokgen(cv, [(-w / 2, -96), (w / 2, -96), (w / 2, 0), (-w / 2, 0)], adim=20, dolgu=BEYAZ, lw=4, seed=seed + 6, alfa=alfa)
            self.metin(cv, pankart, 0, -34, self.sigdir(pankart, pu, w - 26, "damga"), renk(self.vur if vurgu else self.ink, alfa),
                       "damga", ortala=True)
            cv.restore()
        cv.restore()

    def kalabalik(self, cv, sh, u, D, t):
        k = self.k
        p = zaman.asama(u, 0.0, D * 0.55)
        # şehir silueti: binalar, kule, pencereler
        bina = [(60, 360, 220), (230, 300, 180), (420, 250, 120), (550, 330, 230), (790, 230, 150), (950, 340, 200),
                (1160, 280, 140), (1310, 360, 230)]
        zemin = 560.0
        for i, (bx, by, bw) in enumerate(bina):
            f = clamp(p * len(bina) * 0.7 - i * 0.5)
            if f <= 0:
                continue
            pts = [(bx, zemin), (bx, by), (bx + bw, by), (bx + bw, zemin)]
            self.yol_ciz(cv, pts, f, renk(self.ink, 0.6), lw=3, seed=300 + i, kalem=False)
            if f >= 1:
                for r in range(int((zemin - by - 40) // 56)):
                    for c in range(int((bw - 30) // 46)):
                        wx, wy = bx + 22 + c * 46, by + 30 + r * 56
                        if karma(i, r, c) > 0.25:
                            self.tarali_kutu(cv, (wx, wy, wx + 22, wy + 30), renk(GOLGE, 0.3), aralik=6, seed=310 + r * 9 + c)
        # kule (kubbe + direk)
        if p > 0.5:
            f = clamp((p - 0.5) * 2)
            self.yol_ciz(cv, [(700, 230), (700, 140)], f, renk(self.ink, 0.6), lw=3, seed=330, kalem=False)
            k.elips(cv, 700, 190, 26 * f, 26 * f, lw=3, seed=331, alfa=0.6, ikinci=False)
            self.yol_ciz(cv, [(680, 230), (680, zemin)], f, renk(self.ink, 0.6), lw=3, seed=333, kalem=False)
            self.yol_ciz(cv, [(720, 230), (720, zemin)], f, renk(self.ink, 0.6), lw=3, seed=334, kalem=False)
        k.cizgi(cv, [(-20, zemin), (1620, zemin)], renk(self.ink, 0.6), lw=3, seed=332)
        # kalabalık: üç sıra, arkadakiler küçük ve soluk
        n = {"az": 6, "orta": 10, "cok": 14}[sh.get("yogunluk", "orta")]
        pank = list(sh.get("pankartlar", []))
        sira = [(0.62, 620.0, 0.45), (0.8, 700.0, 0.7), (1.0, 800.0, 1.0)]
        no = 0
        for si, (sc, yy, al) in enumerate(sira):
            m = n + (2 - si) * 3
            for j in range(m):
                x = 60 + (j + 0.5 + (0.5 if si % 2 else 0)) * (1480 / m) + (karma(si, j) - 0.5) * 50
                a = zaman.asama(u, D * 0.35 + (j / m) * D * 0.4 + si * 0.15, 0.3)
                if a <= 0:
                    continue
                pk = None
                if si == 2 and pank and j % max(1, m // len(sh.get("pankartlar", [1]))) == 1:
                    pk = pank.pop(0)
                self._insan(cv, x, yy + (1 - a) * 60, sc * (0.92 + karma(si, j, 7) * 0.16), 500 + si * 40 + j, t,
                            kol=0.3 + 0.2 * math.sin(t * 2 + j), alfa=al * a, pankart=pk, vurgu=pk is not None and no == 0)
                no += pk is not None
        if sh.get("metin"):
            pu = self.sigdir(sh["metin"], 70, 1300)
            yy = 110
            w = self.olc(sh["metin"], pu)
            a = zaman.asama(u, D * 0.2, 0.3)
            if a > 0:
                k.cokgen(cv, [(800 - w / 2 - 40, yy - pu * 0.95), (800 + w / 2 + 40, yy - pu * 0.95), (800 + w / 2 + 40, yy + pu * 0.4),
                              (800 - w / 2 - 40, yy + pu * 0.4)], adim=24, dolgu=BEYAZ, lw=4, seed=340, alfa=a)
            self.yaz(cv, sh["metin"], 800, yy, pu, renk(self.ink), zaman.asama(u, D * 0.3, D * 0.5), ortala=True)

    # ---------- 6. sayaç ----------
    def sayac(self, cv, sh, u, D):
        k = self.k
        on, hedef, son, ondalik = zaman.sayi_parcala(sh["deger"])
        p = zaman.asama(u, 0.3, D * 0.7)
        metin = zaman.sayi_yaz(on, hedef * (1 - (1 - p) ** 3), son, ondalik, sh["deger"]) if ondalik >= 0 else sh["deger"]
        pu = self.sigdir(sh["deger"], 300, 900, "damga")
        cy = 470
        oturt = math.exp(-(u - (0.3 + D * 0.7)) * 9) if u > 0.3 + D * 0.7 else 0  # sayı yerine oturunca küçük vuruş
        cv.save(); cv.translate(800, cy); cv.scale(1 + 0.06 * oturt, 1 + 0.06 * oturt)
        if u > 0.25:
            w_son = self.olc(sh["deger"], pu, "damga")
            w = self.olc(metin, pu, "damga")
            self.metin(cv, metin, -w_son / 2 + (w_son - w), pu * 0.35, pu, renk(self.ink), "damga")
        cv.restore()
        # kalemle iki tur atılan halka
        w = self.olc(sh["deger"], pu, "damga")
        rx, ry = w / 2 + 110, pu * 0.62
        halka = [(800 + math.cos(-2.2 + a * 2 * math.pi * 1.12) * rx * (1 + 0.04 * a), cy + math.sin(-2.2 + a * 2 * math.pi * 1.12) * ry * (1 - 0.05 * a))
                 for a in (i / 90 for i in range(91))]
        self.yol_ciz(cv, halka, zaman.asama(u, D * 0.75, D * 0.4), self.vur, lw=9, seed=401)
        if u > D * 1.15:  # vurgu çizgileri
            a = clamp((u - D * 1.15) / 0.2)
            for i, aci in enumerate((-0.75, -0.35, 0.05)):
                r0, r1 = rx + 30, rx + 30 + 60 * a
                k.cizgi(cv, [(800 + math.cos(aci) * r0, cy + math.sin(aci) * r0 * ry / rx),
                             (800 + math.cos(aci) * r1, cy + math.sin(aci) * r1 * ry / rx)], self.vur, lw=7, seed=410 + i)
        if sh.get("ust"):
            self.yaz(cv, sh["ust"].upper(), 800, cy - ry - 90, self.sigdir(sh["ust"].upper(), 54, 1100, "damga"), renk(self.ink, 0.75),
                     zaman.asama(u, 0.0, 0.6), "damga", ortala=True)
        if sh.get("etiket"):
            self.yaz(cv, sh["etiket"], 800, cy + ry + 110, self.sigdir(sh["etiket"], 76, 1300), renk(self.ink),
                     zaman.asama(u, D * 0.6, D * 0.45), ortala=True)
        if sh.get("kaynak"):
            self.metin(cv, "Kaynak: " + sh["kaynak"], 1480 - self.olc("Kaynak: " + sh["kaynak"], 30), 770, 30,
                       renk(self.ink, 0.6 * zaman.asama(u, D, 0.3)))

    # ---------- 7. terazi / olasılık ----------
    def terazi(self, cv, sh, u, D, t):
        k = self.k
        cx, ay = 800.0, 300.0
        p = zaman.asama(u, 0.0, D * 0.5)
        self.yol_ciz(cv, [(cx, 760), (cx, ay)], p, lw=7, seed=600, kalem=False)
        k.cokgen(cv, [(cx - 150, 770), (cx + 150, 770), (cx + 90, 735), (cx - 90, 735)], adim=16, dolgu=karistir(self.ink, BEYAZ, 0.75), lw=5, seed=601,
                 alfa=clamp(p * 3), tarama={"renk_": renk(GOLGE, 0.3), "aralik": 8, "aci": -0.9, "lw": 1.4})
        egim = sh.get("egim", 0.4)
        a0 = D * 0.65
        if u < a0:
            aci = 0.0
        else:  # sönümlü salınımla yerine oturur
            v = u - a0
            aci = egim * 0.32 * (1 - math.exp(-v * 3.2) * math.cos(v * 7.5))
        aci += math.sin(t * 1.3) * 0.006
        L = 430.0
        sol = (cx - math.cos(aci) * L, ay - math.sin(aci) * L)
        sag = (cx + math.cos(aci) * L, ay + math.sin(aci) * L)
        if p > 0.4:
            self.yol_ciz(cv, [sol, sag], clamp((p - 0.4) / 0.6), lw=8, seed=602, kalem=False)
            k.elips(cv, cx, ay, 20, 20, dolgu=self.vur, lw=4, seed=603)
        pa = zaman.asama(u, D * 0.45, 0.5)
        for j, (uc, ad, deger) in enumerate(((sol, sh["sol"], sh.get("sol_deger")), (sag, sh["sag"], sh.get("sag_deger")))):
            if pa <= 0:
                continue
            ky = uc[1] + 210
            for dx in (-120, 120):
                k.cizgi(cv, [uc, (uc[0] + dx, ky)], renk(self.ink, pa), lw=3, seed=610 + j * 3 + (dx > 0))
            kefe = [(uc[0] - 160, ky), (uc[0] + 160, ky), (uc[0] + 110, ky + 50), (uc[0] - 110, ky + 50)]
            k.cokgen(cv, kefe, adim=16, dolgu=BEYAZ, lw=5, seed=620 + j, alfa=pa, tarama={"renk_": renk(GOLGE, 0.2 * pa), "aralik": 9, "aci": 0.9, "lw": 1.3})
            # kefedeki ağırlık kutusu: etiket
            pu = self.sigdir(ad, 54, 300)
            w = self.olc(ad, pu) + 46
            vurgulu = (egim > 0) == (j == 1) and egim != 0
            k.cokgen(cv, [(uc[0] - w / 2, ky - 4), (uc[0] + w / 2, ky - 4), (uc[0] + w / 2, ky - pu * 1.5), (uc[0] - w / 2, ky - pu * 1.5)],
                     adim=16, dolgu=self.acik if vurgulu else BEYAZ, kontur=self.vur if vurgulu else "ink", lw=4.5, seed=630 + j, alfa=pa)
            self.yaz(cv, ad, uc[0], ky - pu * 0.48, pu, renk(self.ink), zaman.asama(u, D * 0.55 + j * 0.3, 0.5), ortala=True)
            if deger:
                self.yaz(cv, deger, uc[0], ky + 125, 72, renk(self.vur if vurgulu else self.ink), zaman.asama(u, D * 0.9 + j * 0.2, 0.4),
                         "damga", ortala=True)
        soru = sh.get("soru")
        if soru:
            self.yaz(cv, soru, cx, 140, self.sigdir(soru, 76, 1200), renk(self.ink), zaman.asama(u, 0.2, D * 0.5), ortala=True)
        else:  # büyük soru işareti
            self.yaz(cv, "?", cx, 210, 170, renk(self.vur), zaman.asama(u, 0.2, 0.6), "damga", ortala=True)

    # ---------- 8. takvim / zaman çizelgesi ----------
    def takvim(self, cv, sh, u, D):
        k = self.k
        ol = sh["olaylar"]
        n = len(ol)
        y = 520.0
        x0, x1 = 140.0, 1460.0
        p = zaman.asama(u, 0.1, D * 0.55)
        uc = self.yol_ciz(cv, [(x0 - 20, y), (x1 + 20, y + 4)], p, lw=7, seed=700)
        if p >= 1:
            self.ok_ucu(cv, (x1, y + 4), (x1 + 20, y + 4), self.ink, boy=34, lw=7)
        _ = uc
        vi = sh.get("vurgu")
        for i, o in enumerate(ol):
            x = x0 + 80 + i * (x1 - x0 - 160) / max(1, n - 1)
            a = clamp(p * (n + 1) - i - 0.5)
            if a <= 0:
                continue
            vur = i == vi
            k.cizgi(cv, [(x, y - 26), (x, y + 26)], self.vur if vur else self.ink, lw=6, seed=710 + i)
            k.daire(cv, x, y, 11 if vur else 8, renk(self.vur if vur else self.ink))
            ust = i % 2 == 0
            ty = y - 150 if ust else y + 100
            w_max = (x1 - x0) / max(1, n - 1) * 1.6
            pt = self.sigdir(o["tarih"], 54, w_max, "damga")
            self.yaz(cv, o["tarih"], x, ty, pt, renk(self.vur if vur else self.ink), zaman.asama(u, D * 0.3 + i * 0.25, 0.4), "damga", ortala=True)
            sat = self.sar(o["metin"], 46, w_max * 0.95)
            for j, sx in enumerate(sat[:2]):
                self.yaz(cv, sx, x, ty + (52 + j * 48 if ust else 52 + j * 48), 46, renk(self.ink, 0.85),
                         zaman.asama(u, D * 0.45 + i * 0.25, 0.45), ortala=True)
            if vur:  # vurgulanan gün: kalemle çevrilir, üstünde koparılmış takvim yaprağı
                w = max(self.olc(o["tarih"], pt, "damga"), 120) / 2 + 40
                halka = [(x + math.cos(-2 + v * 2 * math.pi * 1.1) * w, ty - pt * 0.3 + math.sin(-2 + v * 2 * math.pi * 1.1) * pt * 0.85)
                         for v in (q / 70 for q in range(71))]
                self.yol_ciz(cv, halka, zaman.asama(u, D * 0.95, 0.6), self.vur, lw=7, seed=730)
                pa = zaman.asama(u, D * 1.05, 0.4)
                if pa > 0:
                    gx, gy = x, 170 if ust else 230
                    if ust:
                        gy = ty - pt - 150
                    gun = "".join(c for c in o["tarih"] if c.isdigit())[:2] or "!"
                    ay = o["tarih"].replace(gun, "").strip()[:8].upper()
                    cv.save(); cv.translate(gx, gy); cv.rotate(4 * (1 - pa)); cv.scale(0.7 + 0.3 * out_back(pa), 0.7 + 0.3 * out_back(pa))
                    k.cokgen(cv, [(-90, -90), (90, -90), (90, 100), (-90, 100)], adim=20, dolgu=BEYAZ, lw=5, seed=740)
                    k.cokgen(cv, [(-90, -90), (90, -90), (90, -40), (-90, -40)], adim=20, dolgu=self.vur, lw=5, seed=741, ikinci=False)
                    for hx in (-45, 45):
                        k.elips(cv, hx, -92, 9, 9, dolgu=self.ink, lw=3, seed=742 + hx, ikinci=False)
                    self.metin(cv, ay, 0, -54, 30, renk(BEYAZ), "damga", ortala=True)
                    self.metin(cv, gun, 0, 72, 104, renk(self.ink), "damga", ortala=True)
                    cv.restore()
        if sh.get("baslik"):
            self.yaz(cv, sh["baslik"], x0, 110, self.sigdir(sh["baslik"], 72, 700), renk(self.ink), zaman.asama(u, 0.0, D * 0.45))

    # ---------- altyazı: söylenen satır, kelime kelime koyulaşır ----------
    def altyazi(self, cv, t):
        if not self.s.get("altyazi", True):
            return
        l = next((x for x in self.vo if x["t"] - 0.1 <= t < x["son"] + 0.4), None)
        if not l:
            return
        punto = 50.0
        sinir = 1300.0
        satirlar, cur = [[]], ""
        for w in l["kelimeler"]:
            dene = f"{cur} {w['k']}" if cur else w["k"]
            if self.olc(dene, punto) > sinir and cur:
                satirlar.append([w]); cur = w["k"]
            else:
                satirlar[-1].append(w); cur = dene
        # uzun satır: yalnız söylenen kısmın bulunduğu iki satır gösterilir
        i_aktif = next((i for i, ws in enumerate(satirlar) if ws and t < ws[-1]["son"]), len(satirlar) - 1)
        bas = max(0, min(i_aktif, len(satirlar) - 2) if len(satirlar) > 2 else 0)
        gor = satirlar[bas:bas + 2]
        sol = clamp((t - (l["t"] - 0.1)) / 0.15) * (1 - clamp((t - l["son"] - 0.1) / 0.3))
        lh = punto * 1.1
        y0 = ALT_Y + 30 - (len(gor) - 1) * lh
        sk = self.skia
        bant = sk.Paint(AntiAlias=True, Color=renk(self.pal["kagit"], 0.9 * sol))
        cv.drawRect(sk.Rect.MakeLTRB(130, y0 - punto - 6, 1470, y0 + (len(gor) - 1) * lh + punto * 0.4), bant)
        for i, ws in enumerate(gor):
            x = 800 - self.olc(" ".join(w["k"] for w in ws), punto) / 2
            for w in ws:
                rgb = renk(self.ink) if t >= w["t"] else renk(self.ink, 0.3)
                if t >= w["t"] and (any(c.isdigit() for c in w["k"]) or "%" in w["k"]):
                    rgb = renk(self.vur)
                self.metin(cv, w["k"], x, y0 + i * lh, punto, rgb, alfa=sol)
                x += self.olc(w["k"] + " ", punto)

    # ---------- kare ----------
    def kare(self, cv, t: float) -> None:
        sk, k = self.skia, self.k
        k.kaynat(t)
        cv.drawColor(renk(self.pal["kagit"]))
        sh, u = zaman.sahne_an(self.s, t)
        cv.save()
        cv.translate(self.ox, self.oy); cv.scale(self.olcek, self.olcek)
        if sh:
            D = zaman.cizim_suresi(sh)
            z = 1 + 0.035 * clamp(u / max(1.0, sh["sure"]))  # yavaş yaklaşma
            cv.save(); cv.translate(800, 430); cv.scale(z, z); cv.translate(-800, -430)
            tip = sh["tip"]
            if tip in ("karakter", "kalabalik", "terazi"):
                getattr(self, tip)(cv, sh, u, D, t)
            else:
                getattr(self, tip)(cv, sh, u, D)
            cv.restore()
            son = sh["sure"] - u
            if son < 0.2 and sh is not self.s["sahneler"][-1]:  # dosya içinde sahneden sahneye kâğıt silinir
                cv.drawColor(renk(self.pal["kagit"], clamp(1 - son / 0.2)))
            if u < 0.15 and sh is not self.s["sahneler"][0]:
                cv.drawColor(renk(self.pal["kagit"], clamp(1 - u / 0.15)))
        self.altyazi(cv, t)
        cv.restore()
        p = sk.Paint(); p.setBlendMode(sk.BlendMode.kOverlay); p.setAlphaf(0.55)
        cv.drawImage(self._doku[k.kaynama % 3], 0, 0, sk.SamplingOptions(), p)


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    import skia
    klasor.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H); out = []
    for t in anlar:
        surf = skia.Surface(W, H)
        with surf as cv:
            c.kare(cv, t)
        p = klasor / f"{s.get('kimlik', 'anlatim')}-{W}x{H}-{t:06.2f}.png"
        surf.makeImageSnapshot().save(str(p), skia.kPNG); out.append(p)
    return out


def kontakt(s: dict, W: int, H: int, yol: Path, sutun: int = 2) -> Path:
    """her sahnenin çizimi bitmiş hâli, tek sayfada; sahnenin tipi ve kimliği üstünde"""
    import skia
    c = Cizici(s, W, H)
    tw = 960; th = round(tw * H / W); bas = 64; ara = 24
    n = len(s["sahneler"]); satir = math.ceil(n / sutun)
    TW, TH = sutun * tw + (sutun + 1) * ara, satir * (th + bas) + (satir + 1) * ara
    sayfa = skia.Surface(TW, TH)
    tek = skia.Surface(W, H)
    font = skia.Font(c.yazi["damga"], 34)
    with sayfa as sc:
        sc.drawColor(renk("#E9E6DE"))
        for i, sh in enumerate(s["sahneler"]):
            an = sh["_bas"] + min(sh["sure"] - 0.25, zaman.cizim_suresi(sh) + 1.6)
            with tek as cv:
                c.kare(cv, an)
            img = tek.makeImageSnapshot()
            x = ara + (i % sutun) * (tw + ara); y = ara + (i // sutun) * (th + bas + ara)
            sc.drawString(f"{i + 1}. {sh['tip']}  ·  {sh['id']}", x + 6, y + 44, font, skia.Paint(AntiAlias=True, Color=renk("#34343A")))
            sc.drawImageRect(img, skia.Rect.MakeXYWH(x, y + bas, tw, th), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
    yol.parent.mkdir(parents=True, exist_ok=True)
    sayfa.makeImageSnapshot().save(str(yol), skia.kPNG)
    return yol


def kapak(s: dict, W: int, H: int, t: float, yol: Path) -> Path:
    return kareler(s, W, H, [t], yol.parent)[0].replace(yol)


def video(s: dict, W: int, H: int, yol: Path) -> Path:
    import skia
    yol.parent.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H)
    surf = skia.Surface(W, H)
    pf = "bgra" if surf.imageInfo().colorType() == skia.kBGRA_8888_ColorType else "rgba"
    fps = s["fps"]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pf, "-s", f"{W}x{H}", "-r", str(fps),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(yol)],
                          stdin=subprocess.PIPE)
    for i in range(int(round(fps * s["sure"]))):
        with surf as cv:
            c.kare(cv, i / fps)
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise RuntimeError("ffmpeg görüntü kodlaması başarısız")
    return yol
