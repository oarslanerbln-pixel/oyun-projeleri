"""Kolaj şablonunun görüntüsü: kraft pano üstünde yırtık dergi kâğıtları, yarım ton kesik fotoğraflar,
fidye notu harfleri, bant ve keçeli kalem (skia).

Her kare t'nin saf fonksiyonudur. Parçalar stop-motion gibi saniyede 15 adımda hareket eder ve her adımda
çok hafif kıpırdar (elle yapıştırılmış his). Ölçüler 1080 piksellik kısa kenara göre (`u`); dikey ve yatay
yerleşim aynı sahne tanımından çıkar. Gerekenler: skia-python (Linux'ta libegl1, libgl1), numpy.
"""

from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

import skia

import kagit
import nesneler
import zaman
from kagit import boya, karistir, renk
from zaman import adim, al


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def out_back(p, s=1.7): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def _h(*a) -> random.Random:
    return random.Random(hash(a) & 0xFFFFFFFF)


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        self.s, self.W, self.H = s, W, H
        self.GENIS = W > H
        self.u = min(W, H) / 1080
        self.P = s["palet"]
        self.darbeler = zaman.darbeler(s)
        self._onbellek = {}
        self.tf = {ad: kagit.tf(ad) for ad in ("courier", "inter", "fraunces", "anton")}

    # ---------- yardımcılar ----------
    def bellek(self, anahtar, yap):
        if anahtar not in self._onbellek:
            self._onbellek[anahtar] = yap()
        return self._onbellek[anahtar]

    def yer(self, dikey, yatay):
        """(x, y) oranları → piksel; dikey ve yatay format için ayrı yerleşim."""
        fx, fy = yatay if self.GENIS else dikey
        return fx * self.W, fy * self.H

    def kipir(self, kimlik, t, guc=1.0):
        """Stop-motion kıpırtısı: her adımda yeni, küçük ofset ve açı."""
        r = _h(kimlik, int(t * zaman.ADIM_FPS))
        return r.uniform(-1, 1) * 0.9 * self.u * guc, r.uniform(-1, 1) * 0.9 * self.u * guc, r.uniform(-1, 1) * 0.3 * guc

    def parca(self, cv, pic, x, y, w, h, aci=0.0, olcek=1.0, kimlik=None, t=0.0, kipir=1.0):
        dx = dy = da = 0.0
        if kimlik is not None and kipir:
            dx, dy, da = self.kipir(kimlik, t, kipir)
        cv.save()
        cv.translate(x + dx, y + dy)
        cv.rotate(aci + da)
        if olcek != 1.0:
            cv.scale(olcek, olcek)
        cv.translate(-w / 2, -h / 2)
        cv.drawPicture(pic)
        cv.restore()

    def giris(self, t, t0, tur="pat", yon=(-1, 0)):
        """Girişe göre (görünür mü, dx, dy, ölçek, ek açı). Hareket 15 fps basamaklı."""
        if t < t0:
            return False, 0, 0, 1, 0
        ta = adim(t)
        if tur == "pat":  # büyükten yerine oturur
            p = prog(ta, t0, 0.2)
            return True, 0, 0, 1 + 0.38 * (1 - out_cubic(p)), 6 * (1 - out_cubic(p))
        if tur == "carp":  # çok büyükten sert iner
            p = prog(ta, t0, 0.2)
            return True, 0, 0, 1 + 0.7 * (1 - p) ** 2, -8 * (1 - p)
        p = out_back(prog(ta, t0, 0.34), 1.2)  # kaydır: ekran dışından kayarak gelir
        d = (1 - p) * 1.1 * max(self.W, self.H)
        return True, yon[0] * d, yon[1] * d, 1, 0

    def nesne_resmi(self, n: dict, tohum: int):
        def yap():
            if n.get("gorsel"):
                yol = str(Path(self.s["_klasor"]) / n["gorsel"])
                pic, w, h = kagit.gorsel_resim(yol, n.get("genislik", 420) * self.u, self.P, self.u, tohum, n.get("renkli", False))
                return pic, w, h
            r = nesneler.NESNELER[n["tur"]](self.u, self.P)
            w, h, sil, gri, spot = r[:5]
            ust = r[5] if len(r) > 5 else ()
            return kagit.kesik_resim(w, h, sil, gri, spot, self.P, self.u, tohum, nesneler.HUCRE[n["tur"]], ustler=ust), w, h
        return self.bellek(("nesne", n.get("tur"), n.get("gorsel"), tohum), yap)

    def nesne(self, cv, n, x, y, aci, olcek, t, t0, tur="kaydir", yon=(-1, 0), tohum=1, bant_aci=None):
        gor, dx, dy, k, da = self.giris(t, t0, tur, yon)
        if not gor:
            return
        pic, w, h = self.nesne_resmi(n, tohum)
        self.parca(cv, pic, x + dx, y + dy, w, h, aci + da, olcek * k, ("n", tohum), t)
        if bant_aci is not None and t >= t0 + 0.2:  # bant, parça yerine oturunca yapışır
            b = self.bellek(("bant", tohum), lambda: kagit.bant(150 * self.u, 46 * self.u, self.u, tohum))
            r = math.radians(aci)
            bx, by = -w * 0.32 * olcek, -h * 0.47 * olcek
            self.parca(cv, b, x + bx * math.cos(r) - by * math.sin(r), y + bx * math.sin(r) + by * math.cos(r),
                       150 * self.u, 46 * self.u, aci + bant_aci, 1.0, ("b", tohum), t)

    def yazi(self, cv, y_tanim, x, y, boy, max_w, t, aci=0.0, tohum=1):
        """Fidye notu yazısı: harfler harf_anlari'nda tek tek 'pat' diye yapışır."""
        harfler = self.bellek(("yazi", y_tanim["metin"], boy, max_w, tohum),
                              lambda: kagit.kesik_yazi(y_tanim["metin"], boy * self.u, max_w, self.P, self.u, tohum))
        anlar = zaman.harf_anlari(y_tanim)
        r = math.radians(aci)
        for i, (pic, hx, hy, w, h, ha) in enumerate(harfler):
            gor, _, _, k, da = self.giris(t, anlar[i], "pat")
            if not gor:
                continue
            px, py = x + hx * math.cos(r) - hy * math.sin(r), y + hx * math.sin(r) + hy * math.cos(r)
            self.parca(cv, pic, px, py, w, h, ha + aci + da, k, ("h", tohum, i), t, 1.4)

    def zemin(self, cv):
        cv.drawColor(renk(self.P["zemin"]))
        cv.drawPaint(kagit.doku_boyasi(0.5, 1))

    def gazete_sayfasi(self, w, h, tohum, yirtik="trbl"):
        """Soluk sütun yazısı basılmış gazete kâğıdı (okunmaz; doku olarak)."""
        def yap():
            u = self.u
            pic, dis = kagit.kagit(w, h, self.P["gazete"], u, tohum, yirtik=yirtik, genlik=10)
            rec = skia.PictureRecorder()
            m = 60 * u
            cv = rec.beginRecording(skia.Rect(-m, -m, w + m, h + m))
            cv.drawPicture(pic)
            cv.save(); cv.clipPath(dis, skia.ClipOp.kIntersect, True)
            rnd = random.Random(tohum)
            sutun = 4 if w > 900 * u else 3
            sw = (w - 120 * u) / sutun
            ink = boya(renk(self.P["murekkep"], 0.07))
            y = 70 * u
            cv.drawRect(skia.Rect(60 * u, y, w - 60 * u, y + 56 * u), boya(renk(self.P["murekkep"], 0.09)))
            y += 100 * u
            while y < h - 60 * u:
                for c in range(sutun):
                    x0 = 60 * u + c * sw
                    L = sw - 30 * u if rnd.random() > 0.12 else sw * rnd.uniform(0.3, 0.7)
                    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x0, y, x0 + L, y + 9 * u), 4 * u, 4 * u), ink)
                y += 24 * u
                if rnd.random() < 0.06:
                    y += 30 * u
            cv.restore()
            return rec.finishRecordingAsPicture(), dis
        return self.bellek(("gazete", w, h, tohum), yap)

    # ---------- sahneler ----------
    def ciz_fis(self, cv, sh, t):
        u, P, W, H = self.u, self.P, self.W, self.H
        self.zemin(cv)
        # arka plan kırpıntıları: gazete parçası + kırmızı şerit
        gp, _ = self.gazete_sayfasi(560 * u, 700 * u, 21)
        gx, gy = self.yer((0.24, 0.13), (0.16, 0.30))
        self.parca(cv, gp, gx, gy, 560 * u, 700 * u, -7)
        sp = self.bellek("serit", lambda: kagit.kagit(1400 * u, 130 * u, P["vurgu"], u, 31, yirtik="tblr", genlik=7)[0])
        sx, sy = self.yer((0.5, 0.66), (0.5, 0.86))
        self.parca(cv, sp, sx, sy, 1400 * u, 130 * u, -9)
        # fiş: yazıcıdan çıkar gibi satır satır uzar
        fw = 700 * u if not self.GENIS else 560 * u
        fx, _ = self.yer((0.57, 0), (0.62, 0))
        satir = 92 * u if not self.GENIS else 64 * u
        bas_h = 210 * u if not self.GENIS else 170 * u
        kalemler = sh.get("kalemler", [])
        anlar = zaman.kalem_anlari(sh)
        k = 0.0
        for a in anlar:
            k += out_cubic(prog(adim(t), a, 0.12))
        top_t = sh.get("toplam_t")
        top_p = out_cubic(prog(adim(t), top_t, 0.14)) if top_t is not None else 0
        uzun = 80 * u + bas_h + k * satir + top_p * satir * 1.6 + 30 * u  # 80u: fişin üstü ekran dışında
        ust = -80 * u
        cv.save()
        dx, dy, da = self.kipir("fis", t, 0.6)
        cv.translate(fx - fw / 2 + dx, ust + dy)
        cv.rotate(-2.5 + da)
        yol = self.fis_yolu(fw, uzun)
        kagit.golge(cv, yol, u, 1.1)
        cv.drawPath(yol, boya(renk(karistir(P["kagit"], "#FFFFFF", 0.5))))
        cv.save(); cv.clipPath(yol, skia.ClipOp.kIntersect, True)
        cv.drawPaint(kagit.doku_boyasi(0.5, 2))
        ink = boya(renk(P["murekkep"], 0.86))
        soluk = boya(renk(P["murekkep"], 0.55))
        kb = 1.0 if self.GENIS else 1.15
        fb = skia.Font(self.tf["courier"], 60 * u * kb); fk = skia.Font(self.tf["courier"], 40 * u * kb); fl = skia.Font(self.tf["inter"], 38 * u * kb)
        baslik = sh.get("baslik", "KAFE")
        y = 80 * u + 80 * u
        cv.drawString(baslik, (fw - fb.measureText(baslik)) / 2, y, fb, ink)
        y += 46 * u
        alt = sh.get("fis_alt", "*** FİŞ ***")
        para = sh.get("para", "₺")
        cv.drawString(alt, (fw - fk.measureText(alt)) / 2, y, fk, soluk)
        for i, metin in enumerate(kalemler):
            if t < anlar[i]:
                break
            yy = 80 * u + bas_h + satir * (i + 0.72)
            cv.drawString(metin, 40 * u, yy, fk, ink)
            fiyat = para * (2 + (i * 7) % 3)
            cv.drawString(fiyat, fw - 40 * u - fl.measureText(fiyat), yy, fl, ink)
            nokta_x0 = 48 * u + fk.measureText(metin); nokta_x1 = fw - 52 * u - fl.measureText(fiyat)
            x = nokta_x0
            while x < nokta_x1:
                cv.drawCircle(x, yy - 6 * u, 2.4 * u, soluk); x += 13 * u
        if top_t is not None and t >= top_t:
            yy = 80 * u + bas_h + satir * len(kalemler) + 14 * u
            p = boya(renk(P["murekkep"], 0.7), stroke=3 * u, cap=False)
            p.setPathEffect(skia.DashPathEffect.Make([14 * u, 9 * u], 0))
            cv.drawLine(36 * u, yy, fw - 36 * u, yy, p)
            yy += satir * 1.15
            ft = skia.Font(self.tf["courier"], 56 * u * kb); fl2 = skia.Font(self.tf["inter"], 54 * u * kb)
            cv.drawString(sh.get("toplam", "TOPLAM"), 40 * u, yy, ft, ink)
            tutar = sh.get("toplam_tutar", para * 5)
            cv.drawString(tutar, fw - 40 * u - fl2.measureText(tutar), yy, fl2, ink)
            self._toplam = (fw / 2, yy - 18 * u)
            ct = sh.get("cember_t")
            if ct is not None:
                c = self.bellek("cember", lambda: kagit.el_cemberi(fw / 2, yy - 18 * u, fw * 0.5, 62 * u, random.Random(5)))
                cv.restore()
                kagit.kalem_ciz(cv, c, out_cubic(prog(t, ct, 0.32)), P["vurgu"], 11 * u)
                cv.save()
        cv.restore()
        cv.restore()
        # bardaklar: her kahve bir bardak daha
        n = sh.get("nesne")
        if n:
            yerler = [((0.24, 0.60, 8, 0.92, (-1, 0)), (0.15, 0.60, 8, 0.9, (-1, 0))),
                      ((0.78, 0.69, -11, 0.8, (1, 0)), (0.33, 0.68, -11, 0.78, (0, 1))),
                      ((0.52, 0.74, -3, 0.84, (0, 1)), (0.86, 0.72, 5, 0.76, (1, 0)))]
            for i, (d, y_) in enumerate(yerler[: n.get("adet", 3)]):
                (x, yy, a, k, yon) = y_ if self.GENIS else d
                px, py = x * W, yy * H
                self.nesne(cv, n, px, py, a, k, t, n["t"] + 0.42 * i, "kaydir", yon, tohum=40 + i,
                           bant_aci=[-28, 22, -14][i])
        d = sh.get("damga")
        if d:
            x, y = self.yer((0.5, 0.875), (0.3, 0.2))
            self.yazi(cv, d, x, y, 190, W * 0.92, t, -5, tohum=7)

    def fis_yolu(self, w, h):
        """Fiş: üstü ekran dışında, altı yırtılmış testere dişi."""
        p = skia.Path()
        p.moveTo(0, 0); p.lineTo(w, 0); p.lineTo(w, h)
        n = int(w / (24 * self.u))
        for i in range(n):
            x0 = w - w * i / n; x1 = w - w * (i + 0.5) / n; x2 = w - w * (i + 1) / n
            p.lineTo(x1, h + 12 * self.u); p.lineTo(x2, h)
        p.lineTo(0, 0); p.close()
        return p

    def ciz_esitlik(self, cv, sh, t):
        u, P, W, H = self.u, self.P, self.W, self.H
        self.zemin(cv)
        gw, gh = W * 0.95, H * 0.93
        gp, _ = self.gazete_sayfasi(gw, gh, 22)
        self.parca(cv, gp, W / 2, H / 2, gw, gh, 1.2)
        if sh.get("ust"):
            x, y = self.yer((0.5, 0.15), (0.5, 0.14))
            self.yazi(cv, sh["ust"], x, y, 128 if not self.GENIS else 110, W * (0.88 if not self.GENIS else 0.8), t, -2, tohum=11)
        n = sh.get("nesne")
        if n:
            x, y = self.yer((0.5, 0.405), (0.25, 0.53))
            self.nesne(cv, n, x, y, -4, 1.0, t, n["t"], "kaydir", (-1, 0), tohum=61, bant_aci=-24)
            # buhar: kupanın üstünde üç kıvrımlı kalem çizgisi (bardak/kupa dışında istenirse buhar: true)
            for i in range(3 if n.get("buhar", n.get("tur") in ("kupa", "bardak")) else 0):
                bx = x + (-70 + 60 * i) * u - 20 * u
                rnd = _h("buhar", i, int(t * 6))
                pts = [(bx + 16 * u * math.sin(j * 1.3 + i) + rnd.uniform(-2, 2) * u, y - 205 * u - j * 24 * u) for j in range(5)]
                kagit.kalem_ciz(cv, kagit.kalem_yolu(pts), out_cubic(prog(t, n["t"] + 0.45 + 0.1 * i, 0.4)),
                                karistir(P["murekkep"], P["gazete"], 0.35), 8 * u, 0.75)
        et = sh.get("esit_t")
        if et is not None:
            ex, ey = self.yer((0.5, 0.548), (0.5, 0.53))
            for i, dy in enumerate((-30, 30)):
                pic = self.bellek(("esit", i), lambda i=i: kagit.kagit(250 * u, 40 * u, P["vurgu"], u, 70 + i, yirtik="lr", genlik=5)[0])
                gor, _, _, k, da = self.giris(t, et + 0.07 * i, "pat")
                if gor:
                    self.parca(cv, pic, ex, ey + dy * u, 250 * u, 40 * u, -3 + 4 * i + da, k, ("esit", i), t)
        n2 = sh.get("nesne2")
        if sh.get("alt"):
            x, y = self.yer((0.5, 0.885), (0.5, 0.86))
            self.yazi(cv, sh["alt"], x, y, 120 if not self.GENIS else 104, W * 0.9, t, 2, tohum=12)
            ct = sh.get("cizgi_t")
            if ct is not None:
                harfler = self.bellek(("yazi", sh["alt"]["metin"], 120 if not self.GENIS else 104, W * 0.9, 12), lambda: None)
                alt_y = y + max(hy + h / 2 for _, _, hy, _, h, _ in harfler) + 26 * u
                yari = max(abs(hx) + w / 2 for _, hx, _, w, _, _ in harfler)
                c = self.bellek("alt_cizgi", lambda: kagit.kalem_yolu(
                    [(x - yari + i * yari / 5, alt_y + 9 * u * math.sin(i * 1.7)) for i in range(11)]))
                kagit.kalem_ciz(cv, c, out_cubic(prog(t, ct, 0.3)), P["vurgu"], 12 * u)
        if n2:
            x, y = self.yer((0.5, 0.705), (0.75, 0.53))
            self.nesne(cv, n2, x, y, 3, 1.0, t, n2["t"], "carp", tohum=62, bant_aci=18)

    def ciz_kapanis(self, cv, sh, t):
        u, P, W, H = self.u, self.P, self.W, self.H
        sayfa, _ = self.bellek("kapanis_sayfa", lambda: kagit.kagit(W + 120 * u, H + 260 * u, P["marka"], u, 81, yirtik="t", genlik=14,
                                                                     lif=karistir(P["marka"], "#FFFFFF", 0.8)))
        cv.save(); cv.translate(-60 * u, -50 * u); cv.drawPicture(sayfa); cv.restore()
        pw, ph = (W * 0.88, H * 0.6) if not self.GENIS else (W * 0.62, H * 0.8)
        pano, _ = self.gazete_sayfasi(pw, ph, 82, "tblr")
        px, py = self.yer((0.5, 0.46), (0.4, 0.5))
        self.parca(cv, pano, px, py, pw, ph, -2)
        n = sh.get("nesne")
        if n:
            for i, (d, y_) in enumerate([((0.83, 0.12, 24, 0.85, (1, 0)), (0.86, 0.14, 24, 0.75, (1, 0))),
                                         ((0.17, 0.83, -18, 0.8, (-1, 0)), (0.08, 0.8, -18, 0.7, (-1, 0))),
                                         ((0.36, 0.9, 40, 0.6, (0, 1)), (0.92, 0.86, 40, 0.6, (1, 0)))]):
                x, y, a, k, yon = y_ if self.GENIS else d
                self.nesne(cv, n, x * W, y * H, a, k, t, n["t"] + 0.15 * i, "kaydir", yon, tohum=90 + i)
        m = sh.get("marka")
        if m:
            kel = m["metin"].split()
            anlar = zaman.kelime_anlari(m)
            for i, k_ in enumerate(kel):
                pic, w, h = self.bellek(("marka", i), lambda i=i, k_=k_: self.marka_seridi(k_, i))
                yerler = [((0.46, 0.29), (0.33, 0.3)), ((0.56, 0.415), (0.44, 0.52))]
                x, y = self.yer(*yerler[min(i, 1)]) if i < 2 else self.yer((0.5, 0.33 + 0.13 * i), (0.38, 0.36 + 0.2 * i))
                x = min(max(x, w / 2 + 30 * u), self.W - w / 2 - 30 * u)
                gor, _, _, k, da = self.giris(t, anlar[i], "pat")
                if gor:
                    self.parca(cv, pic, x, y, w, h, (-4 if i % 2 == 0 else 3) + da, k, ("m", i), t)
        a = sh.get("alt")
        if a and t >= a["t"]:
            pic, w, h = self.bellek("etiket", lambda: self.etiket(a["metin"]))
            x, y = self.yer((0.47, 0.535), (0.38, 0.74))
            gor, dx, dy, k, da = self.giris(t, a["t"], "kaydir", (0, 1))
            self.parca(cv, pic, x + dx, y + dy, w, h, 1.5, 1, "etiket", t)
            if t >= a["t"] + 0.2:
                for j, s_ in enumerate((-1, 1)):
                    b = self.bellek(("ebant", j), lambda j=j: kagit.bant(110 * u, 44 * u, u, 100 + j))
                    self.parca(cv, b, x + s_ * (w / 2 - 10 * u), y - 4 * u, 110 * u, 44 * u, 80 + 12 * s_, 1, ("eb", j), t)
        dt = sh.get("damga_t")
        if dt is not None and t >= dt:
            pic, w = self.bellek("muhur", lambda: self.muhur(al(sh, "damga.metin") or ""))
            x, y = self.yer((0.68, 0.675), (0.78, 0.6))
            gor, _, _, k, da = self.giris(t, dt, "pat")
            self.parca(cv, pic, x, y, w, w, -12 + da, k, "muhur", t, 0.5)

    def marka_seridi(self, kelime, i):
        u, P = self.u, self.P
        f = kagit.font_boyu("fraunces", 150 * u)
        w = f.measureText(kelime) + 110 * u
        if w > self.W * 0.9:  # uzun kelime: şerit ekrandan taşmasın, yazı küçülür
            f = kagit.font_boyu("fraunces", 150 * u * (self.W * 0.9 - 110 * u) / (w - 110 * u))
            w = f.measureText(kelime) + 110 * u
        h = 250 * u
        zem = [P["kagit"], P["ikinci"], P["vurgu"]][i % 3]
        pic, dis = kagit.kagit(w, h, zem, u, 120 + i, yirtik="lr" if i % 2 == 0 else "tb", genlik=8)
        rec = skia.PictureRecorder()
        m = 50 * u
        cv = rec.beginRecording(skia.Rect(-m, -m, w + m, h + m))
        cv.drawPicture(pic)
        cv.drawString(kelime, 55 * u, h / 2 + 75 * u, f, boya(renk(P["marka"])))
        return rec.finishRecordingAsPicture(), w, h

    def etiket(self, metin):
        u, P = self.u, self.P
        f = skia.Font(self.tf["courier"], 46 * u)
        w = f.measureText(metin) + 70 * u
        h = 84 * u
        pic, _ = kagit.kagit(w, h, karistir(P["kagit"], "#FFFFFF", 0.5), u, 130, yirtik="", kes=1.5)
        rec = skia.PictureRecorder()
        m = 40 * u
        cv = rec.beginRecording(skia.Rect(-m, -m, w + m, h + m))
        cv.drawPicture(pic)
        cv.drawString(metin, 35 * u, h / 2 + 15 * u, f, boya(renk(P["murekkep"], 0.9)))
        return rec.finishRecordingAsPicture(), w, h

    def muhur(self, metin):
        """Yuvarlak lastik mühür: çevrede yazı, ortada simit halkası; mürekkep yer yer tutmamış."""
        u, P = self.u, self.P
        R = 170 * u
        w = 2 * R + 20 * u
        c = w / 2
        rec = skia.PictureRecorder()
        cv = rec.beginRecording(skia.Rect(0, 0, w, w))
        cv.saveLayer()
        ink = boya(renk(P["vurgu"]), stroke=9 * u)
        cv.drawCircle(c, c, R, ink)
        cv.drawCircle(c, c, R - 70 * u, boya(renk(P["vurgu"]), stroke=5 * u))
        f = skia.Font(self.tf["anton"], 40 * u)
        yazi = (metin + " • ") if metin else ""
        if yazi:
            toplam = sum(f.measureText(ch) for ch in yazi) + 3 * u * len(yazi)
            rr = R - 38 * u
            olcek = min(1.0, 2 * math.pi * rr * 0.97 / toplam)
            aci = -math.pi / 2 - (toplam * olcek / rr) / 2
            for ch in yazi:
                gw = (f.measureText(ch) + 3 * u) * olcek
                a = aci + gw / rr / 2
                cv.save(); cv.translate(c + rr * math.cos(a), c + rr * math.sin(a)); cv.rotate(math.degrees(a) + 90)
                cv.scale(olcek, 1)
                cv.drawString(ch, -f.measureText(ch) / 2, 14 * u, f, boya(renk(P["vurgu"])))
                cv.restore()
                aci += gw / rr
        cv.drawOval(skia.Rect(c - 62 * u, c - 40 * u, c + 62 * u, c + 40 * u), boya(renk(P["vurgu"]), stroke=24 * u))
        sil = skia.Paint(AntiAlias=True)
        sil.setShader(kagit.doku(256, 9).makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat))
        sil.setBlendMode(skia.BlendMode.kDstOut)
        cv.drawPaint(sil)
        cv.drawPaint(sil)
        cv.restore()
        pic = rec.finishRecordingAsPicture()
        rec2 = skia.PictureRecorder()
        cv2 = rec2.beginRecording(skia.Rect(0, 0, w, w))
        p = skia.Paint(); p.setAlphaf(0.93)
        cv2.drawPicture(pic, None, p)
        return rec2.finishRecordingAsPicture(), w

    # ---------- kare ----------
    SAHNE = {"fis": "ciz_fis", "esitlik": "ciz_esitlik", "kapanis": "ciz_kapanis"}

    def sahne(self, cv, i, t):
        sh = self.s["sahneler"][i]
        getattr(self, self.SAHNE[sh["tur"]])(cv, sh, t)

    def yirtik_yarilar(self, tohum):
        def yap():
            W, H, u = self.W, self.H, self.u
            rnd = random.Random(tohum)
            d = kagit.Dalga(rnd, kagit.yirtik_oktavlar(16 * u) + [(420 * u, 40 * u)])
            d2 = kagit.Dalga(random.Random(tohum + 1), kagit.yirtik_oktavlar(6 * u))
            ust, alt = (W * 0.55, -80 * u), (W * 0.45, H + 80 * u)
            cizgi = kagit.kenar_noktalari(ust, alt, d, uc=0)
            # lif şeridi: her yarının kendi yırtık kenarı biraz içeride, farklı tırtıkla
            sol_ic = [(x - 5 * u - abs(d2(y)), y) for x, y in cizgi]
            sag_ic = [(x + 5 * u + abs(d2(y + 300)), y) for x, y in cizgi]
            m = 200 * u
            kose_sol = [(-m, H + m), (-m, -m)]
            kose_sag = [(W + m, H + m), (W + m, -m)]
            sol = kagit.cokgen([(-m, -m)] + cizgi + [(-m, H + m)])
            sol_i = kagit.cokgen([(-m, -m)] + sol_ic + [(-m, H + m)])
            sag = kagit.cokgen([(W + m, -m)] + cizgi + [(W + m, H + m)])
            sag_i = kagit.cokgen([(W + m, -m)] + sag_ic + [(W + m, H + m)])
            del kose_sol, kose_sag
            return (sol, sol_i), (sag, sag_i)
        return self.bellek(("yirt", tohum), yap)

    def kare(self, cv, t):
        s = self.s
        W, H, u = self.W, self.H, self.u
        sahneler = s["sahneler"]
        i = max(j for j, sh in enumerate(sahneler) if sh["bas"] <= t or j == 0)
        sh = sahneler[i]
        cv.save()
        # kamera sarsıntısı: darbelerde basamaklı, hızla sönen
        ta = adim(t)
        for d_t, guc in self.darbeler:
            if 0 <= ta - d_t < 0.3:
                k = (1 - (ta - d_t) / 0.3) ** 2 * guc
                r = _h("sars", d_t, int(t * zaman.ADIM_FPS))
                cv.translate(r.uniform(-1, 1) * 12 * u * k, r.uniform(-1, 1) * 12 * u * k)
                cv.rotate(r.uniform(-1, 1) * 0.5 * k)
        sonraki = sahneler[i + 1] if i + 1 < len(sahneler) else None
        if sonraki and sonraki["gecis"] == "kaydir" and t >= sonraki["bas"] - zaman.KAYDIR_SN:
            self.sahne(cv, i, t)
            p = out_cubic(prog(adim(t), sonraki["bas"] - zaman.KAYDIR_SN, zaman.KAYDIR_SN))
            cv.save(); cv.translate(0, (1 - p) * (H + 300 * u))
            self.sahne(cv, i + 1, t)
            cv.restore()
        elif i > 0 and sh["gecis"] == "yirt" and t < sh["bas"] + zaman.YIRT_SN:
            self.sahne(cv, i, t)
            p = out_cubic(prog(adim(t), sh["bas"], zaman.YIRT_SN))
            onceki_t = sh["bas"] - 1 / s["fps"]
            for j, (dis, ic) in enumerate(self.yirtik_yarilar(i)):
                isaret = -1 if j == 0 else 1
                cv.save()
                px, py = (0, H) if j == 0 else (W, 0)
                cv.translate(isaret * W * 0.95 * p, (0.07 if j == 0 else -0.04) * H * p)
                cv.translate(px, py); cv.rotate(isaret * 13 * p); cv.translate(-px, -py)
                kagit.golge(cv, dis, u, 1.2, -6 * isaret, 8, 9)
                cv.save(); cv.clipPath(dis, skia.ClipOp.kIntersect, True)
                cv.drawColor(renk(karistir(self.P["zemin"], "#FFFFFF", 0.82)))
                cv.drawPaint(kagit.doku_boyasi(0.6, 4))
                cv.clipPath(ic, skia.ClipOp.kIntersect, True)
                self.sahne(cv, i - 1, onceki_t)
                cv.restore()
                cv.restore()
        else:
            self.sahne(cv, i, t)
        cv.restore()
        cv.drawPaint(kagit.doku_boyasi(0.16, 6))  # ince ortak gren: gölgelerde bantlaşmayı kırar
        # son 0,2 sn: hafif kararma yok, kapanış parlak kalır


def yuzey(W, H):
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))


def video(s: dict, W: int, H: int, hedef: Path) -> Path:
    c = Cizici(s, W, H)
    surf = yuzey(W, H)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                           "-r", str(s["fps"]), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                           "-pix_fmt", "yuv420p", str(hedef)], stdin=subprocess.PIPE)
    for i in range(int(round(s["sure"] * s["fps"]))):
        cv = surf.getCanvas()
        cv.clear(0xFF000000)
        c.kare(cv, i / s["fps"])
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg görüntüyü kodlayamadı")
    return hedef


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    c = Cizici(s, W, H)
    surf = yuzey(W, H)
    klasor.mkdir(parents=True, exist_ok=True)
    out = []
    for t in anlar:
        cv = surf.getCanvas()
        cv.clear(0xFF000000)
        c.kare(cv, t)
        yol = klasor / f"kare-{W}x{H}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(yol), skia.kPNG)
        out.append(yol)
    return out
