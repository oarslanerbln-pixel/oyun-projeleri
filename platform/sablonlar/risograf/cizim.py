"""Risograf şablonunun görüntüsü: spot mürekkepler ayrı tambur katmanlarında basılır ve çarpma ile üst üste biner.

Her mürekkep kendi katmanına (saveLayer, multiply) hafif kayık basılır (baskı kayması); katmanın içinde aynı
mürekkebin şekilleri birbirini koyulaştırmaz, tıpkı tek tamburdaki gibi. Mürekkep yoğunluğu ince tanecik ve
seyrek boşluk lekeleriyle verilir (tanecik `tanecik.kaynama` kare/sn hızında "kaynar"). Kâğıt sıcak kırık beyaz,
hafif lifli. Degrade yoktur: tonlar düz mürekkep ya da yarım ton noktayla verilir, tanecik bantlaşmayı da önler.
Her sayfa baskı makinesinden çıkan yeni bir kâğıt gibi alttan gelir. Her kare `t` anının saf fonksiyonudur.
Öğeler sayfaya oranla yerleşir (x, y: 0–1) ve 1080x1350'lik kutuya göre ölçeklenir (9:16'da ölçek 1).
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
import skia

import fontlar
import zaman


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, p): return a + (b - a) * p
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def in_out_cubic(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_back(p, s=1.9): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def renk(hexs: str) -> int:
    return 0xFF000000 | int(hexs[1:], 16)


def boya(r, cizgi=0.0):
    p = skia.Paint(AntiAlias=True, Color=r)
    if cizgi:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(cizgi)
        p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def _bulanik(a, s):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, s, mode="wrap")


class Cizici:
    def __init__(self, s: dict, W: int, H: int, fmt: str = "9x16"):
        self.s = zaman.bicim_icin(s, fmt)
        self.u = min(W, H) / 1080
        self.VW, self.VH = W / self.u, H / self.u
        self.k = min(self.VW / 1080, self.VH / 1350)
        self.kagit = renk(s["kagit"])
        self.ink = {ad: renk(m["renk"]) for ad, m in s["murekkepler"].items()}
        self.yuz = skia.Typeface.MakeFromFile(fontlar.bul())
        self.klasor = Path(s.get("_klasor", "."))
        self._doku: dict = {}
        self._nokta: dict = {}
        self._logo: dict = {}

    # ---------- dokular ----------
    def tanecik(self, i):
        """mürekkep yoğunluğu maskesi (alfa): ince tanecik + seyrek boşluk lekeleri + geniş yoğunluk dalgası"""
        if ("t", i) in self._doku: return self._doku[("t", i)]
        w, h = int(math.ceil(self.VW)), int(math.ceil(self.VH)); g = self.s["tanecik"]["guc"]
        rng = np.random.default_rng(100 + i)
        ince = _bulanik(rng.standard_normal((h, w)), 0.7); ince /= ince.std()
        leke = _bulanik(rng.standard_normal((h, w)), 2.2); leke /= leke.std()
        genis = _bulanik(rng.standard_normal((h // 8 + 1, w // 8 + 1)), 10); genis /= genis.std()
        genis = np.kron(genis, np.ones((8, 8)))[:h, :w]
        a = np.clip(1 - g * (0.08 - 0.07 * ince - 0.03 * genis + 0.55 * np.clip(leke - 2.3, 0, 1)), 0, 1)
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[..., 3] = (a * 255 + rng.uniform(0, 1, a.shape)).clip(0, 255).astype(np.uint8)
        img = skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)
        self._doku[("t", i)] = img
        return img

    def kagit_dokusu(self):
        if "k" in self._doku: return self._doku["k"]
        w, h = int(math.ceil(self.VW)), int(math.ceil(self.VH))
        rng = np.random.default_rng(7)
        n = _bulanik(rng.standard_normal((h, w)), 0.9); n /= n.std()
        lif = _bulanik(rng.standard_normal((h, w)), (0.6, 6)); lif /= lif.std()
        v = 1 - 0.018 * np.abs(n) - 0.012 * np.clip(lif, 0, None)
        gg = (v * 255 + rng.uniform(0, 1, v.shape)).clip(0, 255).astype(np.uint8)
        self._doku["k"] = skia.Image.fromarray(np.dstack([gg, gg, gg, np.full_like(gg, 255)]), colorType=skia.kRGBA_8888_ColorType)
        return self._doku["k"]

    def yarim_ton(self, anahtar, alan, aralik, r, aci=15):
        """yarım ton nokta yolu (açılı ızgara, önbellekli); r sayı ya da r(x, y)"""
        if anahtar in self._nokta: return self._nokta[anahtar]
        x0, y0, x1, y1 = alan; p = skia.Path()
        c, s_ = math.cos(math.radians(aci)), math.sin(math.radians(aci))
        R = math.hypot(x1 - x0, y1 - y0); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        n = int(R / aralik) + 2
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x = cx + (i * c - j * s_) * aralik; y = cy + (i * s_ + j * c) * aralik
                if x0 - aralik <= x <= x1 + aralik and y0 - aralik <= y <= y1 + aralik:
                    rr = r(x, y) if callable(r) else r
                    if rr > 0.5: p.addCircle(x, y, rr)
        self._nokta[anahtar] = p
        return p

    # ---------- yazı ----------
    def font(self, boy):
        f = skia.Font(self.yuz, boy); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True)
        return f

    def _yazi(self, cv, t, o, metin, renk_):
        k = self.k * o.get("olcek", 1.0)
        X, Y = o.get("x", 0.5) * self.VW, o.get("y", 0.5) * self.VH
        boy = o.get("boy", 120) * k
        f = self.font(boy)
        if "genislik" in o:
            f = self.font(boy * o["genislik"] * self.VW / max(1, f.measureText(metin)))
            boy = f.getSize()
        w = f.measureText(metin); x = X - w * o.get("hiza", 0.0)
        t0 = o.get("t", 0); giris = o.get("giris", "kay")
        p = prog(t, t0, zaman.GIRIS_SN[giris])
        cv.save()
        if giris == "sil":
            cv.clipRect(skia.Rect.MakeLTRB(x - 4, Y - boy * 1.1, x - 4 + (w + 8) * out_cubic(p), Y + boy * 0.3), doAntiAlias=True)
        elif giris == "kay":
            cv.clipRect(skia.Rect.MakeLTRB(-10, Y - boy * 1.1, self.VW + 10, Y + boy * 0.28), doAntiAlias=True)
            cv.translate(0, boy * 1.3 * (1 - out_cubic(p)))
        elif giris == "pop":
            s = out_back(p, 2.2); cv.translate(X, Y - boy * 0.35); cv.scale(s, s); cv.translate(-X, -(Y - boy * 0.35))
        if o["tur"] == "sayac" and t >= o["bitis_t"]:
            s = 1 + 0.12 * (1 - out_cubic(prog(t, o["bitis_t"], 0.3)))
            cv.translate(x, Y); cv.scale(s, s); cv.translate(-x, -Y)
        cv.drawString(metin, x, Y, f, boya(renk_))
        cv.restore()

    # ---------- öğeler: her biri yalnız kendi mürekkebinin katmanında çizilir ----------
    def o_yazi(self, cv, t, o, ink):
        if o["murekkep"] != ink or t < o.get("t", 0) or ("bitis_t" in o and t >= o["bitis_t"]): return
        self._yazi(cv, t, o, o["metin"], self.ink[ink])

    def o_sayac(self, cv, t, o, ink):
        if o["murekkep"] != ink or t < o.get("t", 0): return
        ilk, son = o["degerler"]
        sayi = int(round(lerp(ilk, son, out_cubic(prog(t, o["t"], o["bitis_t"] - o["t"])))))
        metin = f"{sayi}{o.get('son_ek', '')}" if t >= o["bitis_t"] else str(sayi)
        self._yazi(cv, t, {"giris": "belir", **o}, metin, self.ink[ink])

    def o_daire(self, cv, t, o, ink):
        if o["murekkep"] != ink: return
        t0 = o.get("t", 0)
        if t < t0: return
        k = self.k * o.get("olcek", 1.0)
        X, Y, r = o.get("x", 0.5) * self.VW, o.get("y", 0.5) * self.VH, o.get("r", 200) * k
        giris = o.get("giris", "belir")
        if giris == "yuksel":
            Y = lerp(o.get("baslangic_y", 1.0) * self.VH, Y, out_cubic(prog(t, t0, o.get("sure", 1.1))))
        elif giris == "buyu":
            r *= out_back(prog(t, t0, o.get("sure", 0.35)), o.get("yay", 2.5))
        if "buyume" in o:
            b = o["buyume"]
            r = lerp(r, b["r"] * k, out_cubic(prog(t, b["t"], b.get("sure", 0.6))))
        if r > 0:
            cv.drawCircle(X, Y, r, boya(self.ink[ink]))

    def o_zemin(self, cv, t, o, ink):
        if o["murekkep"] != ink or t < o.get("t", 0): return
        Y = o.get("y", 0.78) * self.VH; k = self.k
        cv.drawRect(skia.Rect.MakeLTRB(-20, Y, self.VW + 20, self.VH + 20), boya(self.ink[ink]))
        if o.get("yarim_ton", True):
            h = 160 * k
            cv.drawPath(self.yarim_ton(("zemin", Y), (0, Y - h, self.VW, Y), 13 * k,
                                       lambda x, y: 5.5 * k * clamp((y - (Y - h)) / h)), boya(self.ink[ink]))

    def _egri_nokta(self, o, u):
        (ax, ay), (bx, by) = o.get("baslangic", [0.056, 0.885]), o.get("bitis", [1.04, 0.3125])
        e = o.get("us", 3.3)
        return self.VW * lerp(ax, bx, u), self.VH * lerp(ay, by, (math.exp(e * u) - 1) / (math.exp(e) - 1))

    def o_egri(self, cv, t, o, ink):
        u = in_out_cubic(prog(t, o["t"], o["bitis_t"] - o["t"]))
        if u <= 0: return
        sinir = self._egri_nokta(o, u)[0]
        if o["murekkep"] == ink:
            n = 80; pts = [self._egri_nokta(o, i / n) for i in range(n + 1)]
            p = skia.Path(); p.moveTo(pts[0][0], self.VH + 10)
            for q in pts: p.lineTo(*q)
            p.lineTo(pts[-1][0], self.VH + 10); p.close()
            cv.save(); cv.clipRect(skia.Rect.MakeLTRB(-10, -10, sinir, self.VH + 10))
            cv.drawPath(p, boya(self.ink[ink])); cv.restore()
        if o.get("golge") == ink:  # yarım ton gölge (üst üste binince ikinci renk doku)
            y0 = o.get("golge_y", 0.677) * self.VH; k = self.k
            cv.save(); cv.clipRect(skia.Rect.MakeLTRB(-10, -10, sinir, self.VH + 10))
            cv.drawPath(self.yarim_ton(("egri", y0), (0, y0, self.VW, self.VH), 16 * k,
                                       lambda x, y: 6.8 * k * clamp((y - y0) / (self.VH - y0)) ** 0.8, aci=75), boya(self.ink[ink]))
            cv.restore()
        if o.get("noktalar") == ink:
            n = o.get("nokta_sayisi", 11)
            for i in range(1, n + 1):
                ui = i / (n + 1)
                if u >= ui:
                    x, y = self._egri_nokta(o, ui)
                    cv.drawCircle(x, y - 34 * self.k, 16 * self.k * out_back(clamp((u - ui) * 8)), boya(self.ink[ink]))

    def o_halkalar(self, cv, t, o, ink):
        if o["murekkep"] != ink: return
        X, Y, k = o.get("x", 0.5) * self.VW, o.get("y", 0.5) * self.VH, self.k
        for j in range(o.get("adet", 3)):
            r = prog(t, o["t"] + j * o.get("aralik", 0.18), o.get("sure", 1.1))
            if 0 < r < 1:
                cv.drawCircle(X, Y, lerp(o.get("r0", 560), o.get("r1", 1400), out_cubic(r)) * k, boya(self.ink[ink], lerp(12, 4, r) * k))

    def o_ok(self, cv, t, o, ink):
        if o["murekkep"] != ink: return
        p = out_cubic(prog(t, o["t"], o.get("sure", 0.5)))
        if p <= 0: return
        k = self.k; Y = o.get("y", 0.6) * self.VH
        x0 = o.get("x0", 0.093) * self.VW; x1 = lerp(x0 + 20 * k, o.get("x1", 0.89) * self.VW, p)
        g, u_, b = o.get("kalinlik", 120) * k / 2, 130 * k, 120 * k
        ok = skia.Path(); ok.moveTo(x0, Y - g); ok.lineTo(x1 - b, Y - g); ok.lineTo(x1 - b, Y - u_); ok.lineTo(x1, Y)
        ok.lineTo(x1 - b, Y + u_); ok.lineTo(x1 - b, Y + g); ok.lineTo(x0, Y + g); ok.close()
        cv.drawPath(ok, boya(self.ink[ink]))

    def o_cizgi(self, cv, t, o, ink):
        if o["murekkep"] != ink or t < o.get("t", 0): return
        Y = o.get("y", 0.86) * self.VH
        cv.drawRect(skia.Rect.MakeLTRB(-10, Y, self.VW + 10, Y + o.get("kalinlik", 14) * self.k), boya(self.ink[ink]))

    def o_figur(self, cv, t, o, ink):
        """geometrik yürüyen kişi: bacak/kollar, gövde ve şapka ayrı mürekkeplerde (üst üste binince yeni renk)"""
        r = {"govde": "pembe", "bacak": "mavi", "sapka": "sari", **o.get("renkler", {})}
        if ink not in r.values(): return
        t0, t1 = o.get("t", 0), o.get("bitis_t", self.s["sure"])
        p = prog(t, t0, t1 - t0)
        p = out_cubic(p) if o.get("hareket", "yavasla") == "yavasla" else p
        X = lerp(o.get("x0", o.get("x", 0.5)), o.get("x", 0.5), p) * self.VW
        yuru = 0.0
        if t0 <= t:
            yuru = 1 - prog(t, t1 - 0.3, 0.4) if o.get("hareket", "yavasla") == "yavasla" else float(t < t1)
        faz = (t - t0) * o.get("adim_hizi", 9)
        cv.save(); cv.translate(X, o.get("y", 0.78) * self.VH); s = self.k * o.get("olcek", 0.95); cv.scale(s, s)
        sal = math.sin(faz) * 0.45 * yuru
        kalca, omuz = (0, -175), (0, -300)
        if ink == r["bacak"]:
            for yon in (1, -1):
                a = sal * yon
                diz = (95 * math.sin(a), kalca[1] + 95 * math.cos(a))
                ayak = (diz[0] + 85 * math.sin(a - 0.25 * yuru * max(0, -yon * math.cos(faz))), diz[1] + 85 * math.cos(a))
                pth = skia.Path(); pth.moveTo(*kalca); pth.lineTo(*diz); pth.lineTo(*ayak)
                cv.drawPath(pth, boya(self.ink[ink], 40))
                cv.drawLine(ayak[0] - 4, ayak[1], ayak[0] + 30, ayak[1], boya(self.ink[ink], 40))
            cv.drawCircle(0, -395, 58, boya(self.ink[ink]))
        if ink == r["govde"]:
            cv.drawRoundRect(skia.Rect.MakeLTRB(-62, -330, 62, -150), 58, 58, boya(self.ink[ink]))
            for yon in (1, -1):
                a = -sal * yon * 0.9
                cv.drawLine(*omuz, omuz[0] + 150 * math.sin(a), omuz[1] + 150 * math.cos(a), boya(self.ink[ink], 34))
        if ink == r["sapka"]:
            cv.drawRect(skia.Rect.MakeLTRB(-70, -420, 70, -395), boya(self.ink[ink]))
            cv.drawCircle(-8, -440, 50, boya(self.ink[ink]))
        cv.restore()

    def o_logo(self, cv, t, o, ink):
        """logo tek mürekkeple basılır: görselin alfa kanalı kalıp olur"""
        if o["murekkep"] != ink or t < o.get("t", 0): return
        if o["yol"] not in self._logo:
            self._logo[o["yol"]] = skia.Image.open(str(self.klasor / o["yol"]))
        im = self._logo[o["yol"]]
        w = o.get("genislik", 0.4) * self.VW; h = w * im.height() / im.width()
        X, Y = o.get("x", 0.5) * self.VW, o.get("y", 0.5) * self.VH
        s = out_back(prog(t, o.get("t", 0), 0.35), 2.0) if o.get("giris") == "pop" else 1.0
        p = skia.Paint(AntiAlias=True)
        p.setColorFilter(skia.ColorFilters.Blend(self.ink[ink], skia.BlendMode.kSrcIn))
        cv.save(); cv.translate(X, Y); cv.scale(s, s)
        cv.drawImageRect(im, skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), skia.SamplingOptions(skia.CubicResampler.Mitchell()), p)
        cv.restore()

    def isaretler(self, cv, ink, no, toplam):
        """köşe kayıt işaretleri + sayfa no (baskı detayı)"""
        isr = self.s["isaretler"]
        if not isr or isr["murekkep"] != ink: return
        b = boya(self.ink[ink], 3)
        for x, y in ((60, 60), (self.VW - 60, 60), (60, self.VH - 60), (self.VW - 60, self.VH - 60)):
            cv.drawCircle(x, y, 14, b); cv.drawLine(x - 24, y, x + 24, y, b); cv.drawLine(x, y - 24, x, y + 24, b)
        f = self.font(30); m = f"{no}/{toplam}"
        cv.drawString(m, self.VW - 100 - f.measureText(m), self.VH - 52, f, boya(self.ink[ink]))

    # ---------- sayfa ve kare ----------
    def sayfa(self, cv, t, i, oy):
        sy = self.s["sayfalar"][i]
        cv.save(); cv.translate(0, oy)
        r = skia.Rect.MakeWH(self.VW, self.VH)
        cv.drawRect(r, boya(self.kagit))
        carp = skia.Paint(); carp.setBlendMode(skia.BlendMode.kMultiply)
        cv.drawImage(self.kagit_dokusu(), 0, 0, skia.SamplingOptions(), carp)
        kaynat = int(t * self.s["tanecik"]["kaynama"])
        for j, ink in enumerate(self.s["baski_sirasi"]):
            cv.saveLayer(r, carp)
            dx, dy = self.s["murekkepler"][ink]["kayma"]
            jx, jy = ((kaynat * 7 + j * 3) % 3) - 1, ((kaynat * 5 + j) % 3) - 1
            cv.save(); cv.translate(dx + jx * 0.6, dy + jy * 0.6)
            for o in sy["ogeler"]:
                getattr(self, "o_" + o["tur"])(cv, t, o, ink)
            self.isaretler(cv, ink, i + 1, len(self.s["sayfalar"]))
            cv.restore()
            dst = skia.Paint(); dst.setBlendMode(skia.BlendMode.kDstIn)
            cv.drawImage(self.tanecik((i * 3 + j + kaynat) % 6), 0, 0, skia.SamplingOptions(), dst)
            cv.restore()
        cv.restore()

    def kare(self, cv, t):
        cv.save(); cv.scale(self.u, self.u)
        y = 0.0
        for sy in self.s["sayfalar"][1:]:
            y += in_out_cubic(prog(t, sy["bas"] - zaman.BESLE_SN / 2, zaman.BESLE_SN))
        i0 = int(y); f = y - i0
        self.sayfa(cv, t, i0, -f * self.VH)
        if f > 0 and i0 + 1 < len(self.s["sayfalar"]):
            self.sayfa(cv, t, i0 + 1, (1 - f) * self.VH)
            cv.drawLine(0, (1 - f) * self.VH, self.VW, (1 - f) * self.VH, boya(0xFFD9D2C3, 3))
        cv.restore()


def kareler(s: dict, fmt: str, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    klasor.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H, fmt); out = []
    for t in anlar:
        surf = skia.Surface(W, H)
        with surf as cv:
            c.kare(cv, t)
        p = klasor / f"{s.get('kimlik', 'risograf')}-{fmt}-{t:05.2f}.png"
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
