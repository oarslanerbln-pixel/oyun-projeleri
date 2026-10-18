"""Karakalem şablonunun görüntüsü: tek bir defter sayfası ve kalemin ucunda gezen bir kamera (skia).

Dağ çizilirken kalemin ucuna aşırı yakın, sonra geri çekilip karakteri gösterir, basamaklarda onu izler,
sonuçta yeniden geri çekilip basamakların aslında bir eğri olduğunu gösterir, damgada içeri vurur.
Her kare t'nin saf fonksiyonudur. Kâğıt düz renktir; doku ve grenin ikisi de gri üstü bindirme, radyal
gradyan ve parlama yok (bantlaşma olmaz). Gerekenler: skia-python (Linux'ta libegl1, libgl1), numpy.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np

import fontlar
import karakter
import zaman
from kalem import Kalem, bol, gurultu, karistir, renk

GR = {"koyu": "#4A4A52", "kursun": "#B9B6B0", "silgi": "#E9A7A0", "ahsap": "#EAD7B5", "beyaz": "#FFFFFF"}


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, k): return a + (b - a) * k
def in_out_cubic(p): p = clamp(p); return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2
def in_out_quad(p): return zaman.yumusak(p)
def out_back(p, s=3.0): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


class Duzen:
    """formata göre yazı bandı (CAP) ve sahne (STG) yerleşimi"""

    def __init__(self, W: int, H: int):
        self.W, self.H = W, H
        self.genis = W / H > 1.2
        if self.genis:
            o = H / 1080
            m = round(min(W, H) * 0.05)
            safe = (m, m, W - 2 * m, H - 2 * m)
            self.cap = {"x": safe[0] + 20 * o, "y": safe[1] + safe[3] * 0.25, "w": W * 0.34, "h": safe[3] * 0.5, "punto": 74 * o}
            self.stg = {"x": W * 0.38, "y": 0, "w": W * 0.62, "h": H}
        else:
            o = W / 1080
            if H > W * 1.5:  # 9:16: üstte başlık, altta açıklama ve düğmeler için güvenli alan
                safe = (60 * o, round(H * 0.115), W - 200 * o, round(H * (1 - 0.115 - 0.22)))
            else:
                m = round(min(W, H) * 0.05); safe = (m, m, W - 2 * m, H - 2 * m)
            punto = 76 * o
            ch = max(0.135 * H, 2.4 * punto)
            self.cap = {"x": safe[0], "y": safe[1], "w": safe[2], "h": ch, "punto": punto}
            ust = safe[1] + ch - 30 * o
            self.stg = {"x": 0, "y": ust, "w": W, "h": H - ust - H * (0.12 if H > W * 1.5 else 0.04)}
        self.K = min(self.stg["w"] / 1000, self.stg["h"] / 700)


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        import skia
        self.skia, self.s, self.W, self.H = skia, s, W, H
        self.pal = s["palet"]
        self.k = Kalem(self.pal["grafit"])
        self.d = Duzen(W, H)
        self.cz = zaman.cizgiler(s)
        self.b = zaman.basamaklar(s)
        self.inis = zaman.inisler(s)
        self.kam = zaman.kamera(s)
        self.tarama = zaman.tarama(s)
        self.ad = zaman.sahne(s, "adimlar")
        self.sn = zaman.sahne(s, "sonuc")
        self.damga_t = self.sn["damga"]["t"] if self.sn.get("damga") else self.sn["bas"] + zaman.KAMERA_SN + zaman.EGRI_SN
        self.yazi = {a: skia.Typeface.MakeFromFile(fontlar.bul(a)) for a in ("el", "damga")}
        vur = [w.lower() for w in s["seslendirme"].get("vurgulu", [])]
        self.vurgulu = lambda w: any(c.isdigit() for c in w) or "%" in w or w.lower().strip(".,!?;:…\"'") in vur
        self.vo = zaman.kelimeler(s, s.get("_sureler", {}))  # seslendirme.json süreleri (karakalem.py koyar)
        self._doku = self._doku_uret()

    # ---------- kâğıt dokusu: kalıcı lif + kaynayan gren, gri (128) çevresinde bindirme ----------
    def _doku_uret(self):
        skia = self.skia
        rng = np.random.default_rng(5)
        H, W = self.H, self.W
        kaba = rng.standard_normal((H // 6 + 2, W // 6 + 2)).astype(np.float32)
        kaba = np.kron(kaba, np.ones((6, 6), np.float32))[:H, :W]
        kaba = (kaba + np.roll(kaba, 3, 0) + np.roll(kaba, 3, 1) + np.roll(kaba, (3, 3), (0, 1))) / 4  # yumuşak lif
        out = []
        for i in range(3):
            g = rng.standard_normal((H, W)).astype(np.float32)
            v = np.clip(128 + kaba * 5.5 + g * 7.0, 0, 255).astype(np.uint8)
            a = np.empty((H, W, 4), np.uint8); a[..., 0] = a[..., 1] = a[..., 2] = v; a[..., 3] = 255
            out.append(skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType))
        return out

    # ---------- yazı ----------
    def _font(self, ad, punto):
        f = self.skia.Font(self.yazi[ad], punto)
        f.setSubpixel(True); f.setEdging(self.skia.Font.Edging.kAntiAlias)
        return f

    def olc(self, metin, punto, ad="el"):
        return self._font(ad, punto).measureText(metin)

    def metin(self, cv, metin, x, y, punto, rgb, ad="el", ortala=False, alfa=1.0):
        f = self._font(ad, punto)
        j = len(metin) * 13 + punto  # yazı da hafifçe kaynar
        dx, dy = math.sin(j + self.k.kaynama * 1.7) * 0.8, math.cos(j * 1.3 + self.k.kaynama * 2.1) * 0.8
        if ortala:
            x -= f.measureText(metin) / 2
        p = self.skia.Paint(AntiAlias=True, Color=rgb)
        if alfa < 1:
            p.setAlphaf(p.getAlphaf() * alfa)
        cv.drawString(metin, x + dx, y + dy, f, p)

    # ---------- karakterin yolu: her basamağa bir zıplama, vuruşta iniş ----------
    def basamak_ustu(self, i):
        return (zaman.SX0 + i * self.b["w"] + self.b["w"] / 2, zaman.ZEMIN - self.b["yuk"][i])

    def karakter_konumu(self, t):
        i = next((j for j, a in enumerate(self.inis) if t < a), len(self.inis)) - 1
        x, y = (150.0, zaman.ZEMIN) if i < 0 else self.basamak_ustu(i)
        sx = sy = 1.0; havada = False
        if i + 1 < len(self.inis) and t > self.inis[i + 1] - 0.28:
            u = clamp((t - (self.inis[i + 1] - 0.28)) / 0.28)
            nx, ny = self.basamak_ustu(i + 1)
            kalk = 50 + max(0.0, y - ny) * 0.6
            x, y = lerp(x, nx, u), lerp(y, ny, u) - math.sin(math.pi * u) * kalk
            sy, sx, havada = 1.07, 0.94, True
        elif i >= 0:
            e = math.exp(-(t - self.inis[i]) * 14); sy, sx = 1 - 0.18 * e, 1 + 0.13 * e
        return x, y, sx, sy, havada, i

    # ---------- kamera ----------
    def _uc(self, t):
        c = self.cz["dag"] if t < self.cz["kar"]["t"] else self.cz["kar"]
        return zaman.kalem_ucu(c, t)

    @staticmethod
    def _ort(f, t, aralik=0.25, n=6):
        x = y = 0.0
        for j in range(n):
            p = f(t - aralik * j / (n - 1)); x += p[0]; y += p[1]
        return x / n, y / n

    def kamera(self, t):
        gx, gy, _ = zaman.GENIS_POZ
        kalem = lambda u: (*self._ort(self._uc, u, 0.12), 2.7)  # kısa ortalama: uç kadrajdan kaçmasın
        kisi = lambda u: (*self._ort(lambda v: (self.karakter_konumu(v)[0] + 60, self.karakter_konumu(v)[1] - 150), u, 0.35), 1.85)
        genis = lambda u, t0: (gx, gy, 1 + 0.025 * clamp((u - t0) / 1.5))
        karis = lambda a, b, k: (lerp(a[0], b[0], k), lerp(a[1], b[1], k), math.exp(lerp(math.log(a[2]), math.log(b[2]), k)))
        (g1, d1), (y1, dy), (g2, d2) = self.kam["geri1"], self.kam["yakin"], self.kam["geri2"]
        if t < g1: return kalem(t)
        if t < g1 + d1: return karis(kalem(t), genis(t, g1), in_out_cubic((t - g1) / d1))
        if t < y1: return genis(t, g1)
        if t < y1 + dy: return karis(genis(t, g1), kisi(t), in_out_cubic((t - y1) / dy))
        if t < g2: return kisi(t)
        if t < g2 + d2: return karis(kisi(t), (gx, gy, 1.0), in_out_cubic((t - g2) / d2))
        z = 1 + 0.04 * clamp((t - g2 - d2) / 2.5)
        if t >= self.damga_t and self.sn.get("damga"):
            z += 0.07 * math.exp(-(t - self.damga_t) * 7)  # damgada içeri vuruş
        return gx, gy, z

    # ---------- kalem ----------
    def kalem(self, cv, x, y, olcek=1.0):
        k, sk = self.k, self.skia
        cv.save(); cv.translate(x, y); cv.scale(olcek, olcek); cv.rotate(math.degrees(-0.75))
        cv.drawRect(sk.Rect.MakeXYWH(6, -10, 240, 22), sk.Paint(AntiAlias=True, Color=renk("#28282E", 0.12)))
        k.cokgen(cv, [(0, 0), (44, -14), (44, 14)], dolgu=GR["ahsap"], lw=3, seed=7, ikinci=False)
        k.cokgen(cv, [(0, 0), (14, -4.5), (14, 4.5)], dolgu=self.pal["grafit"], lw=2, seed=8, ikinci=False)
        k.cokgen(cv, [(44, -14), (210, -14), (210, 14), (44, 14)], dolgu=self.pal["vurgu"], lw=3, seed=9, ikinci=False)
        k.cizgi(cv, [(48, 0), (206, 0)], renk(karistir(self.pal["vurgu"], "#000000", 0.45), 0.45), lw=2, seed=10)
        k.cokgen(cv, [(210, -14), (232, -14), (232, 14), (210, 14)], dolgu=GR["kursun"], lw=3, seed=11, ikinci=False)
        k.cokgen(cv, [(232, -13), (252, -13), (252, 13), (232, 13)], dolgu=GR["silgi"], lw=3, seed=12, ikinci=False)
        cv.restore()

    def cizgi(self, cv, c, t, rgb=None, lw=5.0, seed=1, uc=0.5, kesik=None):
        """yay uzunluğuna göre çizilen çizgi; kalem ucunda"""
        f = zaman.oran(c, t)
        if t < c["t"] or f <= 0:
            return
        pts = zaman.kismi(c["yol"], f)
        if len(pts) > 1:
            self.k.cizgi(cv, pts, rgb, lw=lw, seed=seed, adim=12, kesik=kesik)
        if f < 1:
            self.kalem(cv, pts[-1][0], pts[-1][1], uc)

    # ---------- sayfa ----------
    def dag(self, cv, t):
        sk, k = self.skia, self.k
        yol = zaman.DAG_YOLU
        ta, td = self.tarama
        if t >= ta:  # gölge, ilerleyen bir kalemin arkasında taranır
            p = clamp((t - ta) / td); ex = lerp(520, 1010, in_out_quad(p))
            cv.save()
            cv.clipPath(k.yol(yol + [(1010, zaman.ZEMIN)], True), sk.ClipOp.kIntersect, True)
            cv.clipRect(sk.Rect.MakeLTRB(500, 400, ex, 1020), True)
            k.tara(cv, (500, 440, 1020, 1010), renk("#28282E", 0.26), aralik=11, aci=-1.1, lw=1.6, seed=31)
            zr = zaman.ZIRVE
            cv.clipPath(k.yol([zr, *yol[5:], (zr[0], zaman.ZEMIN)], True), sk.ClipOp.kIntersect, True)
            k.tara(cv, (zr[0], zr[1], 1010, zaman.ZEMIN), renk("#28282E", 0.3), aralik=7, aci=0.9, lw=1.5, seed=32)
            cv.restore()
            if p < 1:
                self.kalem(cv, ex, lerp(620, 960, 0.5 + 0.5 * math.sin(t * 38)), 0.5)
        self.cizgi(cv, self.cz["dag"], t, lw=6, seed=30, uc=0.55)
        self.cizgi(cv, self.cz["kar"], t, lw=4, seed=33, uc=0.5)

    def merdiven(self, cv, t):
        k, w = self.k, self.b["w"]
        vurgu = self.pal["vurgu"]
        acik = karistir(vurgu, "#FFFFFF", 0.6)
        for i, an in enumerate(self.inis):
            c = self.cz[f"basamak{i}"]
            if t < c["t"]:
                continue
            x0, y0 = zaman.SX0 + i * w, zaman.ZEMIN - self.b["yuk"][i]
            dolu = clamp((t - (c["t"] + c["d"])) / 0.12)
            vur = math.exp(-(t - an) * 5) if t >= an else 0
            if dolu > 0:
                k.cokgen(cv, [(x0, y0), (x0 + w, y0), (x0 + w, zaman.ZEMIN), (x0, zaman.ZEMIN)], dolgu=acik if vur > 0.05 else GR["beyaz"],
                         kontur=None, seed=70 + i, alfa=dolu, tarama={"renk_": renk("#28282E", 0.2 * dolu), "aralik": 9, "aci": -0.9, "lw": 1.4})
            self.cizgi(cv, c, t, lw=5, seed=80 + i, uc=0.42)
            a = t - an  # etiket her inişten havalanır
            if 0 <= a < 0.9 and self.ad.get("etiket"):
                cv.save()
                kk = 0.6 + 0.4 * out_back(clamp(a / 0.18))
                cv.translate(x0 + w / 2 - 125, y0 - 170 - a * 70)  # kafanın solunda havalanır; cv.scale(kk, kk)
                self.metin(cv, self.ad["etiket"], 0, 0, 48, renk(vurgu), ortala=True, alfa=1 - clamp((a - 0.5) / 0.4))
                cv.restore()

    def karakter_ciz(self, cv, t):
        x, y, sx, sy, havada, i = self.karakter_konumu(t)
        korku, sevinc = t < self.kam["yakin"][0], t >= self.damga_t
        tepe = t >= self.kam["geri2"][0]
        if sevinc:
            sy = 1 - 0.12 * math.exp(-(t - self.damga_t) * 9)
        karakter.ciz(cv, self.k, self.s["karakter"], self.pal["vurgu"], x, y, s=0.5, sx=sx, sy=sy, t=t, seed=400,
                     gozler="happy" if sevinc else "wide" if korku or havada else "normal", bakis=0.9,
                     bakis_y=-0.9 if korku or tepe else -0.3,
                     agiz="grin" if sevinc else "worry" if korku else "o" if havada else "smile",
                     kaslar="worry" if korku else "up", ter=1.0 if korku else 0.0,
                     kol_sol=2.6 if sevinc else 1.3 if havada else 0.3, kol_sag=2.7 if sevinc else 1.4 if havada else 0.3,
                     kizarma=1.0 if sevinc else 0.5 if i >= 2 else 0.0,
                     kirp=not sevinc and not havada and ((t + 0.3) % 2.7) < 0.1)

    def damga(self, cv, t):
        d = self.sn.get("damga")
        if not d or t < d["t"]:
            return
        a = t - d["t"]; kk = 1 + 1.5 * math.exp(-a * 18)
        vurgu = renk(self.pal["vurgu"])
        x, y = 430.0, 600.0
        rx = max(165.0, self.olc(d["metin"], 78, "damga") / 2 + 45)
        cv.save(); cv.translate(x, y); cv.rotate(math.degrees(-0.12)); cv.scale(kk, kk)
        self.k.elips(cv, 0, 0, rx, 88, kontur=self.pal["vurgu"], lw=8, seed=130)
        self.metin(cv, d["metin"], 0, 6 + (0 if d.get("alt") else 20), 78, vurgu, ad="damga", ortala=True)
        if d.get("alt"):
            self.metin(cv, d["alt"], 0, 56, 42, vurgu, ortala=True)
        cv.restore()
        if a < 0.25:
            self.k.isinlar(cv, x, y, n=14, r0=rx + 25, r1=rx + 115, lw=4, seed=131, alfa=1 - a / 0.25)

    def baslik(self, cv, t, cx, y, punto, sinir):
        b = self.sn.get("baslik")
        if not b or t < b["t"]:
            return
        metin = b["metin"]
        w = self.olc(metin, punto)
        if w > sinir:
            punto *= sinir / w; w = sinir
        x0 = cx - w / 2
        p = in_out_quad((t - b["t"]) / zaman.BASLIK_SN); ex = x0 + w * p
        cv.save(); cv.clipRect(self.skia.Rect.MakeLTRB(x0 - 20, y - punto, ex + 30 * p * punto / 72, y + punto * 0.5), True)
        self.metin(cv, metin, x0, y, punto, renk(self.pal["grafit"]))
        self.k.cizgi(cv, [(x0 + w * 0.62, y + 18 * punto / 72), (x0 + w + 10, y + 22 * punto / 72)], self.pal["vurgu"], lw=7 * punto / 72, seed=5)
        cv.restore()
        if p < 1:
            self.kalem(cv, ex, y - 20 * punto / 72 + 14 * math.sin(t * 30) * punto / 72, 0.45 * punto / 72)

    # ---------- söylenen sözler, söylendikçe yazılır ----------
    def _sar(self, ws, punto, sinir):
        satirlar, cur = [[]], ""
        for w in ws:
            dene = f"{cur} {w['k']}" if cur else w["k"]
            if self.olc(dene, punto) > sinir and cur:
                satirlar.append([w]); cur = w["k"]
            else:
                satirlar[-1].append(w); cur = dene
        return satirlar

    def altyazi(self, cv, t):
        sk = self.skia
        l = next((x for x in self.vo if x["t"] - 0.1 <= t < x["son"] + 0.5), None)
        if not l:
            return
        cap = self.d.cap
        punto, lh = cap["punto"], cap["punto"] * 1.12
        satirlar = self._sar(l["kelimeler"], punto, cap["w"] - 30)
        if len(satirlar) > 3:  # bant taşmasın
            punto *= 0.82; lh = punto * 1.12; satirlar = self._sar(l["kelimeler"], punto, cap["w"] - 30)
        sol = clamp((t - (l["t"] - 0.1)) / 0.15) * (1 - clamp((t - l["son"] - 0.2) / 0.3))
        y0 = cap["y"] + cap["h"] / 2 - (len(satirlar) - 1) * lh / 2 + punto * 0.3
        kg = self.pal["kagit"]
        # kâğıt bandı: çizim yazıyla hiç çakışmasın
        bant = sk.Paint(AntiAlias=True)
        bant.setShader(sk.GradientShader.MakeLinear(
            [(0, cap["y"] - 40), (0, cap["y"] + cap["h"] + 40)],
            [renk(kg, 0), renk(kg, 0.92), renk(kg, 0.92), renk(kg, 0)], [0, 0.2, 0.8, 1]))
        bant.setAlphaf(sol)
        cv.drawRect(sk.Rect.MakeXYWH(0, cap["y"] - 40, cap["x"] + cap["w"] + 30 if self.d.genis else self.W, cap["h"] + 80), bant)
        gr, vur = self.pal["grafit"], self.pal["vurgu"]
        for i, ws in enumerate(satirlar):
            x = cap["x"] + cap["w"] / 2 - self.olc(" ".join(w["k"] for w in ws), punto) / 2
            for w in ws:
                soylendi = t >= w["t"]
                kk = 1 + 0.08 * math.exp(-(t - w["t"]) * 12) if soylendi else 1.0
                rgb = renk(vur if self.vurgulu(w["k"]) else gr) if soylendi else renk(gr, 0.25)
                cv.save(); cv.translate(x, y0 + i * lh); cv.scale(kk, kk)
                self.metin(cv, w["k"], 0, 0, punto, rgb, alfa=sol)
                cv.restore()
                x += self.olc(w["k"] + " ", punto)

    # ---------- kare ----------
    def kare(self, cv, t: float) -> None:
        sk, k, d = self.skia, self.k, self.d
        k.kaynat(t)
        cv.drawColor(renk(self.pal["kagit"]))
        cx, cy, z = self.kamera(t)
        sars = 10 * math.exp(-(t - self.damga_t) * 9) if t >= self.damga_t and self.sn.get("damga") else 0
        cv.save()
        cv.translate(d.stg["x"] + d.stg["w"] / 2 + gurultu(t * 40, 1) * sars * d.K,
                     d.stg["y"] + d.stg["h"] / 2 + gurultu(t * 40, 2) * sars * d.K)
        cv.scale(d.K * z, d.K * z)
        cv.translate(-cx, -cy)
        k.cizgi(cv, [(-400, zaman.ZEMIN), (1400, zaman.ZEMIN)], lw=4, seed=2)
        self.dag(cv, t)
        self.merdiven(cv, t)
        self.cizgi(cv, self.cz["egri"], t, renk(self.pal["vurgu"]), lw=7, seed=121, uc=0.5, kesik=[2, 16])
        if t >= self.kam["geri1"][0] - 0.1:
            self.karakter_ciz(cv, t)
        self.damga(cv, t)
        if not d.genis:
            self.baslik(cv, t, zaman.GENIS_POZ[0], 270, 72, 900)
        cv.restore()
        self.altyazi(cv, t)
        if d.genis:
            self.baslik(cv, t, d.cap["x"] + d.cap["w"] / 2, d.cap["y"] + d.cap["h"] + 40 * d.H / 1080, d.cap["punto"] * 0.87, d.cap["w"])
        # kâğıt dokusu + gren (bindirme, saniyede 12 kez değişir)
        p = sk.Paint(); p.setBlendMode(sk.BlendMode.kOverlay); p.setAlphaf(0.55)
        cv.drawImage(self._doku[k.kaynama % 3], 0, 0, sk.SamplingOptions(), p)
        son = self.s["sure"] - 0.25
        if t > son:  # kâğıda sönüş
            cv.drawColor(renk(self.pal["kagit"], clamp((t - son) / 0.25)))


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    import skia
    klasor.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H); out = []
    for t in anlar:
        surf = skia.Surface(W, H)
        with surf as cv:
            c.kare(cv, t)
        p = klasor / f"{s.get('kimlik', 'karakalem')}-{W}x{H}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(p), skia.kPNG); out.append(p)
    return out


def kapak(s: dict, W: int, H: int, t: float, yol: Path) -> Path:
    return kareler(s, W, H, [t], yol.parent)[0].replace(yol)


def video(s: dict, W: int, H: int, yol: Path) -> Path:
    import skia
    yol.parent.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H)
    surf = skia.Surface(W, H)
    # skia'nın yerel düzeni çoğu makinede BGRA; ffmpeg'e doğru bildir (yoksa kırmızı/mavi yer değiştirir)
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
