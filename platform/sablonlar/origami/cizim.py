"""Origami şablonunun görüntüsü: katlanarak açılan düz renkli kâğıt yüzeyler (skia).

Her nesne, menteşesi bir üst yüzün kenarında duran üçgen ve dörtgen yüzlerden oluşur. Bir yüz
menteşesi etrafında dönerek açılır: dik izdüşümde bu, menteşeye dik eksende `cos(açı)` ölçeğidir.
Açı 90°'yi geçince kâğıdın arka yüzü (açık renk) görünür. Gölgeler ve yüz tonları düz renktir,
bant yapacak gradyan yoktur; en üstte sabit, çok hafif bir kâğıt dokusu titreşimi kırar.

Her kare t'nin saf fonksiyonudur. Ölçüler 1080 piksellik kısa kenara göre (`u`) verilir; dikey ve
yatay yerleşim aynı sahne tanımından çıkar. Gerekenler: skia-python (Linux'ta libegl1, libgl1), numpy.
"""

from __future__ import annotations

import math
import os
import random
import subprocess
from pathlib import Path

import zaman

FONT_ADLARI = {800: ["Inter-ExtraBold.otf", "Inter-800.ttf", "Inter-ExtraBold.ttf"], 700: ["Inter-Bold.otf", "Inter-700.ttf", "Inter-Bold.ttf"]}
FONT_DIZINLERI = [os.environ.get("KINETIK_FONT_DIZINI", ""), "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
                  str(Path.home() / "Library/Fonts"), "/Library/Fonts"]
PI = math.pi
YARIM = PI / 2


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
def in_out_cubic(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_back(p, s=1.7): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def rgb(hex_: str) -> tuple[int, int, int]:
    v = int(hex_.lstrip("#"), 16)
    return v >> 16 & 255, v >> 8 & 255, v & 255


def ton(c: tuple, f: float, karis: tuple | None = None, k: float = 0.0) -> int:
    """f<1 koyulaştırır, f>1 beyaza açar; `karis` rengine k kadar yaklaştırır (sönme)"""
    r, g, b = c
    if f < 1:
        r, g, b = r * f, g * f, b * f
    else:
        r, g, b = (x + (255 - x) * (f - 1) for x in (r, g, b))
    if karis and k:
        r, g, b = (lerp(x, y, k) for x, y in zip((r, g, b), karis))
    return 0xFF000000 | int(clamp(r, 0, 255)) << 16 | int(clamp(g, 0, 255)) << 8 | int(clamp(b, 0, 255))


def yuz(poly, rol, ton_, ust, mente, aci0, t0, d=0.32, arka="acik"):
    """katlanan bir yüz: `mente` (A, B) üst yüzün yerel koordinatında; aci0 başlangıç açısı (PI: üst yüzün
    üstüne katlı, YARIM: yere yatık/kenardan görünmez)"""
    return {"poly": poly, "rol": rol, "ton": ton_, "ust": ust, "mente": mente, "aci0": aci0, "t0": t0, "d": d, "arka": arka}


# ---------- modeller (yerel birim: nesne yüksekliği 1, taban ortası 0,0, y aşağı) ----------
def model_kupa(renk: str) -> list[dict]:
    def w(y): return 0.23 + 0.08 * (-y / 0.80)  # gövdenin y'deki yarı genişliği (alt dar, üst geniş)
    ys, ya = -0.56, -0.30  # manşon
    Y = ((-1, 0), (1, 0))
    return [
        yuz([(-0.23, 0), (0, 0), (0, -0.80), (-0.31, -0.80)], renk, 1.0, -1, Y, YARIM, 0.0, 0.34),
        yuz([(0, 0), (0.23, 0), (0.31, -0.80), (0, -0.80)], renk, 0.84, 0, ((0, 0), (0, -1)), PI, 0.16),
        yuz([(-w(ya), ya), (0, ya), (0, ys), (-w(ys), ys)], "acik", 0.98, 0, ((-w(ya), ya), (-w(ys), ys)), PI, 0.30, 0.28),
        yuz([(0, ya), (w(ya), ya), (w(ys), ys), (0, ys)], "acik", 0.86, 2, ((0, 0), (0, -1)), PI, 0.40, 0.26),
        yuz([(-0.35, -0.80), (0, -0.80), (0, -0.88), (-0.35, -0.88)], "koyu", 1.0, 0, ((-1, -0.80), (1, -0.80)), PI, 0.30),
        yuz([(0, -0.80), (0.35, -0.80), (0.35, -0.88), (0, -0.88)], "koyu", 0.80, 4, ((0, 0), (0, -1)), PI, 0.42, 0.26),
        yuz([(-0.33, -0.88), (0, -0.88), (0, -0.98), (-0.24, -0.98)], "koyu", 1.28, 4, ((-1, -0.88), (1, -0.88)), PI, 0.44, 0.26),
        yuz([(0, -0.88), (0.33, -0.88), (0.24, -0.98), (0, -0.98)], "koyu", 1.10, 6, ((0, 0), (0, -1)), PI, 0.52, 0.22),
    ]


def model_kutu(renk: str) -> list[dict]:
    return [
        yuz([(-0.42, 0), (0.18, 0), (0.18, -0.70), (-0.42, -0.70)], renk, 1.0, -1, ((-1, 0), (1, 0)), YARIM, 0.0, 0.34),
        yuz([(0.18, 0), (0.42, -0.12), (0.42, -0.82), (0.18, -0.70)], renk, 0.78, 0, ((0.18, 0), (0.18, -1)), PI, 0.18),
        yuz([(-0.42, -0.70), (0.18, -0.70), (0.42, -0.82), (-0.18, -0.82)], renk, 1.14, 0, ((-1, -0.70), (1, -0.70)), PI, 0.30),
        yuz([(-0.17, 0), (-0.07, 0), (-0.07, -0.70), (-0.17, -0.70)], "acik", 0.97, 0, ((-0.17, 0), (-0.17, -1)), PI, 0.44, 0.24),
    ]


GENISLIK = {"kupa": 0.70, "kutu": 0.84}  # yükseklik başına
MODEL = {"kupa": model_kupa, "kutu": model_kutu}


def model_turna() -> list[dict]:
    """yandan uçan kâğıt turna (sola bakar), merkez 0,0"""
    G = 0.04
    bas_ucu = (-0.62 + 0.42 * 0.155, -0.40 + 0.44 * 0.155)
    return [
        yuz([(-0.36, G), (0.36, G), (0.02, 0.30)], "acik", 0.80, -1, ((-1, G), (1, G)), YARIM, 0.0, 0.30, "ucuncu"),
        yuz([(0.22, G), (0.36, G), (0.68, -0.34)], "acik", 0.90, 0, ((-1, G), (1, G)), PI, 0.16, 0.30, "ucuncu"),
        yuz([(-0.36, G), (-0.20, G), (-0.62, -0.40)], "acik", 0.94, 0, ((-1, G), (1, G)), PI, 0.16, 0.30, "ucuncu"),
        yuz([(-0.62, -0.40), bas_ucu, (-0.76, -0.28)], "acik", 0.74, 2, ((-0.62, -0.40), bas_ucu), PI, 0.40, 0.22, "ucuncu"),
        yuz([(-0.20, G), (0.22, G), (0.02, -0.62)], "acik", 1.0, 0, ((-1, G), (1, G)), PI, 0.30, 0.34, "ucuncu"),
        yuz([(0.22, G), (0.02, -0.62), (0.40, -0.40)], "acik", 0.80, 4, ((0.22, G), (0.02, -0.62)), PI, 0.52, 0.26, "ucuncu"),
    ]


def model_yildiz(n: int = 8, R: float = 1.0, r: float = 0.52) -> list[dict]:
    """katlanmış kâğıt yıldız: her kol açık ve koyu iki üçgen; merkez 0,0"""
    out = []
    for k in range(n):
        a = -YARIM + 2 * PI * k / n
        uc = (R * math.cos(a), R * math.sin(a))
        sol = (r * math.cos(a - PI / n), r * math.sin(a - PI / n))
        sag = (r * math.cos(a + PI / n), r * math.sin(a + PI / n))
        i = len(out)
        out.append(yuz([(0, 0), sol, uc], "ucuncu", 1.06, -1, ((0, 0), sol), PI, k * 0.025, 0.28))
        out.append(yuz([(0, 0), uc, sag], "ucuncu", 0.84, i, ((0, 0), uc), PI, k * 0.025 + 0.12, 0.24))
    return out


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        import skia
        self.sk = skia
        self.s, self.W, self.H = s, W, H
        self.GENIS = W > H
        self.cx, self.cy = W / 2, H / 2
        self.u = min(W, H) / 1080
        self.C = {k: rgb(v) for k, v in s["palet"].items()}
        self.P = {k: ton(v, 1.0) for k, v in self.C.items()}
        self.TF = skia.Typeface.MakeFromFile(font_bul(800))
        self.TF7 = skia.Typeface.MakeFromFile(font_bul(700))
        self.darbeler = zaman.darbeler(s)
        self.doku = self._doku()
        rnd = random.Random(11)
        renkler = ["vurgu", "ikinci", "ucuncu", "acik", "koyu"]
        self.konfeti = [(rnd.uniform(-PI * 0.88, -PI * 0.12), rnd.uniform(900, 1700), rnd.uniform(16, 30), rnd.uniform(-7, 7),
                         rnd.uniform(5, 12), rnd.choice(renkler), rnd.uniform(0, 2 * PI)) for _ in range(30)]
        # zemindeki büyük kâğıt kıvrımları: köşelerden geçen birkaç düz tonlu üçgen
        self.kivrim = [((0, 0), (0.62, 0), (0, 0.38), 1.012), ((1, 0.18), (1, 0.66), (0.55, 0.42), 0.988),
                       ((0, 1), (0, 0.70), (0.48, 1), 0.985), ((1, 1), (0.66, 1), (1, 0.80), 1.014)]

    # ---------- araçlar ----------
    def _doku(self):
        """sabit kâğıt dokusu: ±2–3 seviyelik siyah/beyaz noktalar (bantlaşmayı da kırar)"""
        import numpy as np
        rng = np.random.default_rng(5)
        n = rng.standard_normal((self.H, self.W)).astype(np.float32)
        a = np.clip(np.abs(n) * 6.5, 0, 40).astype(np.uint8)
        arr = np.zeros((self.H, self.W, 4), np.uint8)
        beyaz = n > 0
        for k in range(3):
            arr[..., k] = np.where(beyaz, a, 0)  # öncül çarpılmış (premul) beyaz ya da siyah
        arr[..., 3] = a
        return self.sk.Image.fromarray(arr, colorType=self.sk.kRGBA_8888_ColorType, alphaType=self.sk.kPremul_AlphaType)

    def paint(self, c, a=1.0):
        p = self.sk.Paint(AntiAlias=True, Color=c)
        if a < 1: p.setAlphaf(a * p.getAlphaf())
        return p

    def yol(self, pts):
        p = self.sk.Path()
        p.moveTo(*pts[0])
        for q in pts[1:]: p.lineTo(*q)
        p.close()
        return p

    def font(self, size, tf=None):
        f = self.sk.Font(tf or self.TF, size); f.setSubpixel(True)
        return f

    def genislik(self, s, size, tf=None, track=0.0):
        return self.font(size, tf).measureText(s) + track * size * (len(s) - 1)

    def yazi(self, cv, s, x, y, size, color, a=1.0, tf=None, track=0.0, anchor="c"):
        """y: yazının görsel ortası"""
        if a <= 0: return
        f = self.font(size, tf)
        w = self.genislik(s, size, tf, track)
        hh = -f.getMetrics().fAscent * 0.72
        xx = x + {"c": -w / 2, "l": 0, "r": -w}[anchor]
        p = self.paint(color, a)
        if track:
            for ch in s:
                cv.drawString(ch, xx, y + hh / 2, f, p); xx += f.measureText(ch) + track * size
        else:
            cv.drawString(s, xx, y + hh / 2, f, p)

    @staticmethod
    def kat(A, B, aci):
        """A–B menteşesi etrafında `aci` kadar katlanmanın dik izdüşümü (afin)"""
        import skia
        dx, dy = B[0] - A[0], B[1] - A[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        k = 1 - math.cos(aci)
        an = A[0] * nx + A[1] * ny
        return skia.Matrix.MakeAll(1 - k * nx * nx, -k * nx * ny, k * an * nx, -k * nx * ny, 1 - k * ny * ny, k * an * ny, 0, 0, 1)

    @staticmethod
    def det(M):
        return M.getScaleX() * M.getScaleY() - M.getSkewX() * M.getSkewY()

    def yuzler(self, cv, model, t_rel, M0, sonuk=0.0, golge=(0.0, 0.0, 0.0), ek_aci=None, opak=1.0):
        """modeli çizer; `golge` (dx, dy, alfa) ekranda kaydırılmış düz gölge, `ek_aci` {indeks: açı}"""
        sk = self.sk
        Ms, ciz = [], []
        olcek = math.sqrt(abs(self.det(M0))) or 1.0
        for i, f in enumerate(model):
            p = prog(t_rel, f["t0"], f["d"])
            aci = f["aci0"] * (1 - (in_out_cubic(p) if f.get("egri") == "io" else out_cubic(p))) + (ek_aci or {}).get(i, 0.0)
            M = sk.Matrix.Concat(Ms[f["ust"]] if f["ust"] >= 0 else M0, self.kat(*f["mente"], aci))
            Ms.append(M)
            d = self.det(M) / (olcek * olcek)
            if abs(d) < 0.004:
                continue
            pts = [M.mapXY(*q) for q in f["poly"]]
            pts = [(q.x(), q.y()) for q in pts]
            on = d > 0
            taban = self.C[f["rol"] if on else f["arka"]]
            isik = (f["ton"] if on else 0.92) * (0.80 + 0.20 * min(1.0, abs(d)))
            ciz.append((pts, ton(taban, isik, self.C["zemin"], sonuk)))
        if not ciz:
            return
        gx, gy, ga = golge
        if ga > 0:  # örtüşen gölgeler koyulaşmasın: tek katmanda opak, katman alfayla
            cv.saveLayerAlpha(None, int(255 * ga * opak * (1 - 0.6 * sonuk)))
            p = self.paint(self.P["koyu"])
            for pts, _ in ciz:
                cv.drawPath(self.yol([(x + gx, y + gy) for x, y in pts]), p)
            cv.restore()
        if opak < 1:
            cv.saveLayerAlpha(None, int(255 * opak))
        for pts, c in ciz:
            p = self.paint(c)
            cv.drawPath(self.yol(pts), p)
            # bitişik yüzler arasında saç teli boşluk kalmasın
            p.setStyle(sk.Paint.kStroke_Style); p.setStrokeWidth(1.2 * self.u); p.setStrokeJoin(sk.Paint.kRound_Join)
            cv.drawPath(self.yol(pts), p)
        if opak < 1:
            cv.restore()

    def sarsinti(self, t):
        dx = dy = 0.0
        for t0, amp in self.darbeler:
            if t >= t0:
                k = math.exp(-(t - t0) * 12) * amp * self.u
                dx += k * math.sin((t - t0) * 80 + t0 * 7); dy += k * math.cos((t - t0) * 67 + t0 * 3)
        return dx, dy

    def zemin(self, cv, rol, kivrim=True):
        cv.clear(self.P[rol])
        if not kivrim:
            return
        W, H = self.W, self.H
        for a, b, c, f in self.kivrim:
            cv.drawPath(self.yol([(a[0] * W, a[1] * H), (b[0] * W, b[1] * H), (c[0] * W, c[1] * H)]), self.paint(ton(self.C[rol], f)))

    # ---------- vitrin ----------
    def olcu(self):
        """(taban y, azami nesne yüksekliği, boşluk)"""
        u = self.u
        if self.GENIS:
            return self.H * 0.68, 360 * u, 60 * u
        return self.H * 0.66, 520 * u, 46 * u

    def yerlesim(self, sh, t):
        taban, hmax, bosluk = self.olcu()
        nes = sh["nesneler"]
        tam = sum(GENISLIK[n["tur"]] * n["boy"] * hmax * (1.18 if "one_t" in n else 1.0) for n in nes) + bosluk * (len(nes) - 1)
        k = min(1.0, (self.W * (0.62 if self.GENIS else 0.9)) / tam)
        ilk = zaman.ilk_nesneler(sh)
        ag = [1.0 if n["id"] in ilk else in_out_cubic(prog(t, n["t"] - 0.25, zaman.KAYMA_SN)) for n in nes]
        gen = [GENISLIK[n["tur"]] * n["boy"] * hmax * k for n in nes]
        bos = [0.0] + [bosluk * k * a for a in ag[1:]]  # boşluk, önündeki nesne geldikçe açılır
        x = self.cx - (sum(g * a for g, a in zip(gen, ag)) + sum(bos)) / 2
        out = {}
        for n, g, a, b in zip(nes, gen, ag, bos):
            x += b
            out[n["id"]] = (x + g * a / 2, taban, n["boy"] * hmax * k, g)
            x += g * a
        return out

    def vitrin(self, cv, t, sh):
        sk, u = self.sk, self.u
        yer = self.yerlesim(sh, t)
        rz = sh.get("rozet")
        self.baslik(cv, t, sh)
        one = [n for n in sh["nesneler"] if "one_t" in n]
        for n in one:  # öne çıkan nesnenin arkasında katlanan yıldız
            if t < n["one_t"]: continue
            x, taban, h, _ = yer[n["id"]]
            M = sk.Matrix.Translate(x, taban - 0.55 * h)
            M.preRotate(-12 + (t - n["one_t"]) * 14)
            M.preScale(0.82 * h, 0.82 * h)
            self.yuzler(cv, model_yildiz(), t - n["one_t"] - 0.05, M, golge=(9 * u, 8 * u, 0.10))
        for n in sh["nesneler"]:
            if t < n["t"]: continue
            x, taban, h, g = yer[n["id"]]
            tr = t - n["t"]
            s = 1.0
            if "one_t" in n:
                s += 0.15 * out_back(prog(t, n["one_t"], 0.45), 2.2)
            sonuk = 0.55 * in_out_cubic(prog(t, n["sonuk_t"], 0.5)) if "sonuk_t" in n else 0.0
            s *= 1 - 0.04 * sonuk / 0.55
            hop = 0.0
            if "zipla_t" in n:
                p = prog(t, n["zipla_t"], 0.42)
                hop = -math.sin(PI * p) * 0.12 * h * (1 - p * 0.3)
            # yer gölgesi: düz elips, zıplayınca küçülür
            ga = clamp(tr / 0.3) * 0.08 * (1 - 0.5 * sonuk) * (1 + hop / h)
            cv.drawOval(sk.Rect.MakeXYWH(x - g * s * 0.55, taban - 10 * u, g * s * 1.1, 20 * u), self.paint(self.P["koyu"], ga))
            M = sk.Matrix.Translate(x, taban + hop)
            M.preScale(h * s, h * s)
            self.yuzler(cv, MODEL[n["tur"]](n["renk"]), tr, M, sonuk, golge=(10 * u, 7 * u, 0.13))
            if "etiket_t" in n and t >= n["etiket_t"]:
                self.etiket(cv, t, n, x, taban + 44 * u, g, sonuk)
        for n in one:
            if t >= n["one_t"]:
                x, taban, h, _ = yer[n["id"]]
                self.konfeti_ciz(cv, t - n["one_t"], x, taban - h * 1.05)

    def baslik_y(self):
        return self.H * (0.12 if self.GENIS else 0.2)

    def baslik(self, cv, t, sh):
        """akordeon gibi katlı kâğıt şerit soldan sağa panel panel açılır; rozet anında yatay ekseninde
        döner ve arka yüzünde rozet kurdelesi çıkar (rozet tek başına da açılabilir)"""
        sk, u = self.sk, self.u
        y = self.baslik_y()
        bs, rz = sh.get("baslik"), sh.get("rozet")
        don = PI * in_out_cubic(prog(t, rz["t"], 0.45)) if rz and bs else (PI if rz and t >= rz["t"] else 0.0)
        c = math.cos(don)
        if abs(c) < 0.01:
            return
        cv.save(); cv.translate(0, y); cv.scale(1, abs(c)); cv.translate(0, -y)
        if c > 0 and bs and t >= bs.get("t", 0):
            tr = t - bs.get("t", 0)
            fs = (48 if self.GENIS else 58) * u
            w = self.genislik(bs["metin"], fs, track=0.3) + 140 * u
            h = 104 * u
            k = 4
            pw = w / k
            x0 = self.cx - w / 2
            model = []
            for i in range(k):
                a, b = x0 + i * pw, x0 + (i + 1) * pw
                model.append(yuz([(a, y - h / 2), (b, y - h / 2), (b, y + h / 2), (a, y + h / 2)], "koyu", 1.0, i - 1,
                                 ((a, 0), (a, 1)), YARIM if i == 0 else PI, i * 0.11, 0.3))
            self.yuzler(cv, model, tr, sk.Matrix(), golge=(9 * u, 7 * u, 0.13))
            a = clamp((tr - 0.42) / 0.25)
            if a > 0:
                self.yazi(cv, bs["metin"], self.cx, y, fs, ton(self.C["acik"], 0.8 + 0.2 * c), a, track=0.3)
        elif c < 0:
            self.rozet(cv, t - rz["t"] - 0.3, rz["metin"], self.cx, y, acilis=not bs, isik=abs(c))
        cv.restore()

    def etiket(self, cv, t, n, x, y, g, sonuk):
        """kupanın altında asılı kâğıt fiyat etiketi; üst kenarından aşağı sallanarak açılır,
        öne çıkınca dikey ekseninde dönüp arka yüzünü (vurgu) gösterir"""
        sk, u = self.sk, self.u
        ad, fiyat = n.get("ad", ""), n.get("fiyat", "")
        fw = self.genislik(fiyat, 62 * u)
        w = max(g * 0.92, fw + 64 * u, self.genislik(ad, 28 * u, self.TF7, 0.14) + 64 * u)
        h = 150 * u
        p = prog(t, n["etiket_t"], 0.42)
        aci = YARIM * (1 - out_back(p, 1.6))
        cy_ = math.cos(aci)
        don = 0.0
        if "one_t" in n:
            don = PI * in_out_cubic(prog(t, n["one_t"] + 0.18, 0.4))
        cx_ = math.cos(don)
        if abs(cy_) < 0.01 or abs(cx_) < 0.01:
            return
        arka = cx_ < 0
        k = 16 * u
        sekil = [(-w / 2 + k, 0), (w / 2 - k, 0), (w / 2, k), (w / 2, h), (-w / 2, h), (-w / 2, k)]
        isik = 0.84 + 0.16 * abs(cy_ * cx_)
        kart = ton(self.C["vurgu" if arka else "acik"], isik, self.C["zemin"], sonuk)
        yazi_r = ton(self.C["acik" if arka else "koyu"], 1.0, self.C["zemin"], sonuk)
        ga = 0.12 * (1 - 0.6 * sonuk)
        cv.save(); cv.translate(x, y); cv.scale(abs(cx_), cy_)
        cv.drawPath(self.yol([(a + 9 * u / abs(cx_), b + 7 * u) for a, b in sekil]), self.paint(self.P["koyu"], ga))
        cv.drawPath(self.yol(sekil), self.paint(kart))
        cv.drawCircle(0, 20 * u, 7 * u, self.paint(ton(self.C["zemin"], 0.93)))
        self.yazi(cv, ad, 0, 54 * u, 28 * u, yazi_r, 0.75, self.TF7, 0.14)
        self.yazi(cv, fiyat, 0, 106 * u, 62 * u, yazi_r)
        cv.restore()

    def rozet(self, cv, tr, metin, x, y, acilis=True, isik=1.0):
        """vurgu renginde kurdele: orta şerit üstten aşağı açılır (acilis), `tr` 0 anından sonra uçlar arkasından
        dışa katlanarak çıkar"""
        sk, u = self.sk, self.u
        fs = (48 if self.GENIS else 54) * u
        rw = self.genislik(metin, fs, track=0.06) + 90 * u
        rh = 104 * u
        uc = 0.75 * rh
        x = clamp(x, rw / 2 + uc + 30 * u, self.W - rw / 2 - uc - 30 * u)
        a = rw / 2
        g = 0.25 * rh
        model = [
            yuz([(-a + g, -0.30 * rh), (-a - uc, -0.30 * rh), (-a - uc + 0.28 * rh, 0.22 * rh), (-a - uc, 0.74 * rh),
                 (-a + g, 0.74 * rh)], "vurgu", 0.80, -1, ((-a + g, -1), (-a + g, 1)), PI, 0.0, 0.3),
            yuz([(a - g, -0.30 * rh), (a + uc, -0.30 * rh), (a + uc - 0.28 * rh, 0.22 * rh), (a + uc, 0.74 * rh),
                 (a - g, 0.74 * rh)], "vurgu", 0.80, -1, ((a - g, -1), (a - g, 1)), PI, 0.0, 0.3),
            yuz([(-a, rh / 2), (-a + g, rh / 2), (-a + g, 0.74 * rh)], "vurgu", 0.55, -1, ((-a, rh / 2), (-a + g, rh / 2)), PI, 0.14, 0.16),
            yuz([(a, rh / 2), (a - g, rh / 2), (a - g, 0.74 * rh)], "vurgu", 0.55, -1, ((a, rh / 2), (a - g, rh / 2)), PI, 0.14, 0.16),
        ]
        if tr > 0:
            self.yuzler(cv, model, tr, sk.Matrix.Translate(x, y), golge=(9 * u, 7 * u, 0.13))
        c = math.cos(YARIM * (1 - out_back(prog(tr + 0.3, 0, 0.34), 1.5))) if acilis else 1.0
        if abs(c) < 0.01:
            return
        orta = [(-a, -rh / 2), (a, -rh / 2), (a, rh / 2), (-a, rh / 2)]
        cv.save(); cv.translate(x, y - rh / 2); cv.scale(1, c); cv.translate(0, rh / 2)
        cv.drawPath(self.yol([(q + 9 * u, r + 7 * u) for q, r in orta]), self.paint(self.P["koyu"], 0.13))
        cv.drawPath(self.yol(orta), self.paint(ton(self.C["vurgu"], (0.82 + 0.18 * isik) * (0.85 + 0.15 * abs(c)))))
        self.yazi(cv, metin, 0, 0, fs, self.P["acik"], track=0.06)
        cv.restore()

    def konfeti_ciz(self, cv, tr, x0, y0):
        """kâğıt üçgenler: havada döner ve ters yüz olur (arka yüz açık renk)"""
        sk, u = self.sk, self.u
        if tr > 2.2: return
        k = 2.4
        for aci, hiz, boy, don, cev, rol, faz in self.konfeti:
            vx, vy = math.cos(aci) * hiz * u, math.sin(aci) * hiz * u
            e = (1 - math.exp(-k * tr)) / k
            x = x0 + vx * e
            y = y0 + vy * e + 0.5 * 900 * u * tr * tr * 0.55
            a = clamp((2.2 - tr) / 0.5) * clamp(tr / 0.05)
            c = math.cos(faz + cev * tr)
            if abs(c) < 0.05: continue
            renk = self.C[rol if c > 0 else "acik"]
            cv.save(); cv.translate(x, y); cv.rotate(math.degrees(faz + don * tr)); cv.scale(1, abs(c))
            b = boy * u
            cv.drawPath(self.yol([(-b, b * 0.6), (b, b * 0.6), (0, -b * 0.9)]), self.paint(ton(renk, 0.85 + 0.15 * abs(c)), a))
            cv.restore()

    # ---------- kapanış ----------
    def kapanis(self, cv, t, sh):
        sk, u, W, H = self.sk, self.u, self.W, self.H
        self.zemin(cv, "vurgu", kivrim=False)
        if sh["gecis"] == "katla":  # geçişin ortadaki kat izi yavaşça kaybolur
            a = 0.16 * (1 - prog(t, sh["bas"], 0.8))
            if a > 0:
                cv.drawRect(sk.Rect.MakeXYWH(W / 2, 0, W / 2, H), self.paint(ton(self.C["vurgu"], 0.9), a))
        tr = t - sh.get("isaret_t", sh["bas"] + 0.1)
        if sh.get("isaret", "turna") == "turna" and tr >= 0:
            S = (330 if self.GENIS else 560) * u
            cy_ = H * (0.30 if self.GENIS else 0.33) + math.sin(t * 2.4) * 10 * u * clamp(tr - 0.6)
            M = sk.Matrix.Translate(self.cx + 0.03 * S, cy_)
            M.preScale(S, S)
            kanat = 0.55 * (0.5 - 0.5 * math.cos((tr - 0.7) * 4.8)) * clamp((tr - 0.7) / 0.3)
            self.yuzler(cv, model_turna(), tr, M, golge=(12 * u, 10 * u, 0.18), ek_aci={4: kanat})
        satirlar = sh["satirlar"]
        boy = (84 if self.GENIS else 104) * u
        y0 = H * (0.60 if self.GENIS else 0.585)
        aralik = boy * 1.22
        for k, w in enumerate(satirlar):
            if t < w["t"]: continue
            p = prog(t, w["t"], 0.38)
            c = math.cos(YARIM * (1 - out_back(p, 1.6)))
            fs = min(boy, boy * (W - 140 * u) / max(1.0, self.genislik(w["metin"], boy)))
            y = y0 + k * aralik
            if abs(c) < 0.01: continue
            cv.save(); cv.translate(0, y - fs * 0.5); cv.scale(1, c); cv.translate(0, fs * 0.5)
            self.yazi(cv, w["metin"], self.cx + 6 * u, 6 * u, fs, self.P["koyu"], 0.16)
            self.yazi(cv, w["metin"], self.cx, 0, fs, self.P[w.get("renk", "acik")])
            cv.restore()
        if sh.get("alt") and t >= sh.get("alt_t", 0):
            p = out_cubic(prog(t, sh["alt_t"], 0.5))
            fs = 30 * u
            fs = min(fs, fs * (W - 120 * u) / max(1.0, self.genislik(sh["alt"], fs, self.TF7, 0.16)))
            y = y0 + len(satirlar) * aralik + 40 * u + (1 - p) * 20 * u
            self.yazi(cv, sh["alt"], self.cx, y, fs, self.P["acik"], 0.88 * p, self.TF7, 0.16)

    def katla(self, cv, t, sh):
        """sonraki sahnenin rengindeki kâğıt iki kanatla ekranı kaplar: sağ kanat kenardan gelir,
        üstüne katlı sol kanat (arka yüzü açık) açılıp sola yatar"""
        sk, W, H = self.sk, self.W, self.H
        b = sh["bas"]
        p1 = prog(t, b - zaman.KATLA_SN, zaman.KATLA_SN / 2)
        p2 = prog(t, b - zaman.KATLA_SN / 2, zaman.KATLA_SN / 2)
        if p1 <= 0: return
        m = 4
        rol = "vurgu" if sh["tur"] == "kapanis" else "zemin"
        model = [
            yuz([(W / 2, -m), (W + m, -m), (W + m, H + m), (W / 2, H + m)], rol, 1.0, -1, ((W, 0), (W, H)), YARIM, 0.0, 1.0),
            yuz([(-m, -m), (W / 2, -m), (W / 2, H + m), (-m, H + m)], rol, 1.0, 0, ((W / 2, 0), (W / 2, H)), PI, 1.0, 1.0),
        ]
        for f in model:
            f["egri"] = "io"
        tr = p1 + p2  # kanat 1: 0–1, kanat 2: 1–2
        self.yuzler(cv, model, tr, sk.Matrix(), golge=(-14 * self.u, 0, 0.12 * (1 - p2)))

    # ---------- kare ----------
    def kare(self, cv, t):
        s = self.s
        sahneler = s["sahneler"]
        i = zaman.sahne_at(s, t)
        sh = sahneler[i]
        sonraki = sahneler[i + 1] if i + 1 < len(sahneler) else None
        dx, dy = self.sarsinti(t)
        cv.save(); cv.translate(dx, dy)
        zm = 1.0 + 0.012 * math.sin(t * 0.9)
        if sh["tur"] == "vitrin":
            for n in sh["nesneler"]:
                if "one_t" in n:
                    zm += 0.035 * out_cubic(prog(t, n["one_t"], 0.6))
        cv.save(); cv.translate(self.cx, self.cy); cv.scale(zm, zm); cv.translate(-self.cx, -self.cy)
        if sh["tur"] == "vitrin":
            self.zemin(cv, "zemin")
            self.vitrin(cv, t, sh)
        else:
            self.kapanis(cv, t, sh)
        cv.restore()
        if sonraki and sonraki["gecis"] == "katla" and t >= sonraki["bas"] - zaman.KATLA_SN:
            self.katla(cv, t, sonraki)
        cv.restore()
        cv.drawImage(self.doku, 0, 0)


def yuzey(W, H):
    import skia
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))


def video(s: dict, W: int, H: int, hedef: Path) -> Path:
    c = Cizici(s, W, H)
    surf = yuzey(W, H)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                           "-r", str(s["fps"]), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                           "-pix_fmt", "yuv420p", str(hedef)], stdin=subprocess.PIPE)
    for i in range(int(round(s["sure"] * s["fps"]))):
        c.kare(surf.getCanvas(), i / s["fps"])
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg görüntüyü kodlayamadı")
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
