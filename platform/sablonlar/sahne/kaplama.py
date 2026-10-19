"""Kaplama: bir stilin ortak sahne dilini nasıl çizdiği. Taban sınıf düz, kalın tipografili (kinetik) görünümü çizer.

Yeni stil yalnız değiştirmek istediğini ezer. Sahne tipleri (`baslik`, `liste`, ...) aynı yerleşimi kullanır ve
şu temel taşlarla çizilir; bir stil çoğu zaman yalnız bunları ezerek bütün tiplere kendi görünümünü verir:

    fon(cv, VW, VH, t, i)                  arka plan (i: sahne sırası)
    panel(cv, r, renk, p, kimlik, t)       yazı/kart zemini (r: skia.Rect, p: 0..1 giriş)
    yazi(cv, s, x, y, boy, renk, ...)      tek satır yazı (y = satırın dikey ortası)
    buyuk_yazi(...)                        büyük başlık/sayı yazısı (varsayılan: yazi)
    isaret(cv, x, y, r, renk, p, kimlik, t, n)   liste imi
    nesne(cv, r, sh, p, t)                 görseli olmayan ürün için stile özgü nesne
    gecis_ciz(cv, VW, VH, p, eski, yeni)   sahne geçişi (eski/yeni: çizen işlevler)
    ust_katman(cv, W, H, t)                piksel düzeyinde son katman (doku, tanecik)

Bütün çizim tasarım biriminde yapılır: kısa kenar 1080. Her öğe güvenli alanın (`alan`) içinde kalır; yazılar
sığmazsa küçülür ya da satıra bölünür, hiçbir zaman kesilmez.
"""

from __future__ import annotations

import math
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

import skia

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA.parent / "stil"))
import motor  # noqa: E402  (Inter yazı tipi, Türkçe büyük/küçük harf)

# (sol, sağ, üst, alt) sınırı, ekran oranı. 9:16: Reels arayüzü üst %10, alt %22, sağ %13 (beğen/yorum sütunu).
GUVENLI = {"9x16": (0.06, 0.13, 0.10, 0.78), "16x9": (0.06, 0.06, 0.08, 0.92), "1x1": (0.06, 0.06, 0.07, 0.93),
           "4x5": (0.06, 0.06, 0.07, 0.92)}


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, p): return a + (b - a) * p
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - clamp(p)) ** 3
def in_out(p): p = clamp(p); return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_back(p, s=1.6): p = clamp(p) - 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def renk(h: str | int, a: float = 1.0) -> int:
    """'#RRGGBB' ya da 0xRRGGBB → ARGB."""
    v = int(h.lstrip("#"), 16) if isinstance(h, str) else h & 0xFFFFFF
    return (int(255 * clamp(a)) << 24) | v


def karis(c1: int, c2: int, p: float) -> int:
    p = clamp(p)
    return (0xFF << 24) | sum(int(lerp((c1 >> s) & 255, (c2 >> s) & 255, p)) << s for s in (16, 8, 0))


def alfa(c: int, a: float) -> int:
    return (int(((c >> 24) & 255) * clamp(a)) << 24) | (c & 0xFFFFFF)


def _h(*a) -> float:
    """Deterministik 0..1."""
    x = math.sin(sum((i + 1) * 12.9898 * (v + 0.37) for i, v in enumerate(a))) * 43758.5453
    return x - math.floor(x)


@lru_cache(maxsize=8)
def _resim(yol: str):
    return skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(yol))


SAYI = re.compile(r"\d[\d.,]*")


def say(deger: str, p: float) -> str:
    """'37x' / '%40' / '1.200 ₺' içindeki ilk sayıyı 0'dan p oranında sayar; biçim (ayraç, ondalık) korunur."""
    m = SAYI.search(deger)
    if not m or p >= 1:
        return deger
    ham = m.group()
    ondalik = 1 if re.search(r",\d{1,2}$", ham) else 0
    v = float(ham.replace(".", "").replace(",", ".")) if ondalik else float(ham.replace(".", "").replace(",", ""))
    x = v * out_cubic(p)
    if ondalik:
        s = f"{x:.1f}".replace(".", ",")
    else:
        s = f"{int(round(x)):,}".replace(",", ".") if ("." in ham or "," in ham) and v >= 1000 else str(int(round(x)))
    return deger[:m.start()] + s + deger[m.end():]


class Kaplama:
    ad = "kinetik"
    aciklama = "Düz, kalın tipografi; koyu zemin, sarı vurgu"
    POZ: int | None = None  # stop-motion poz/sn (None: akıcı)
    GECIS = 0.42
    PALET = {"zemin": "#15122E", "yuzey": "#241F4A", "murekkep": "#FFF8E7", "soluk": "#B8B2D9",
             "vurgu": "#FFD23F", "ikinci": "#FF5A5F", "ucuncu": "#3DDC97", "vurgu_yazi": "#15122E"}
    AGIRLIK = 800
    BUYUK_HARF = True  # büyük yazılar (başlık, çağrı) Türkçe kurallı büyük harfe çevrilir
    MUZIK = {"bpm": 116, "kok": 60, "dizi": [0, 2, 4, 7, 9, 12, 14], "ped": [48, 55, 60, 64], "enstruman": "sinus",
             "akor": [0, 9, 5, 7]}
    SFX = "whoosh"

    def __init__(self, s: dict):
        self.s = s
        self.p = {k: renk(v) for k, v in {**self.PALET, **(s.get("palet") or {})}.items()}
        self.klasor = Path(s.get("_klasor", "."))
        self.marka = s.get("marka") or {}

    # ---------- yazı ----------
    def yazi_tipi(self, agirlik: int):
        return motor.yazi_tipi(agirlik)

    @lru_cache(maxsize=4096)
    def _font(self, boy: float, agirlik: int):
        f = skia.Font(self.yazi_tipi(agirlik), boy)
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        return f

    def olc(self, s: str, boy: float, agirlik: int | None = None) -> float:
        return self._font(round(boy, 1), agirlik or self.AGIRLIK).measureText(s)

    def harf(self, s: str, buyuk: bool | None = None) -> str:
        return motor.tr_buyuk(s) if (self.BUYUK_HARF if buyuk is None else buyuk) else s

    def sar(self, s: str, boy: float, gen: float, azami: int = 3, agirlik: int | None = None, en_kucuk: float = 0.45):
        """Metni `gen`e sığan en çok `azami` satıra böler; sığmazsa boyu küçültür. (satırlar, boy)"""
        b = boy
        while True:
            satir, sat = [], ""
            for w in s.split():
                aday = (sat + " " + w).strip()
                if sat and self.olc(aday, b, agirlik) > gen:
                    satir.append(sat); sat = w
                else:
                    sat = aday
            satir.append(sat)
            if (len(satir) <= azami and max(self.olc(x, b, agirlik) for x in satir) <= gen) or b <= boy * en_kucuk:
                return satir, b
            b *= 0.94

    def sigdir(self, s: str, boy: float, gen: float, agirlik: int | None = None) -> float:
        w = self.olc(s, boy, agirlik)
        return boy if w <= gen else boy * gen / w

    def yazi(self, cv, s, x, y, boy, renk_, hiza="orta", agirlik=None, p=1.0, kimlik=0, t=0.0):
        """Tek satır; y satırın dikey ortası. p: giriş (saydamlık + aşağıdan kayma)."""
        if p <= 0 or not s:
            return
        f = self._font(round(boy, 1), agirlik or self.AGIRLIK)
        w = f.measureText(s)
        x0 = x - w / 2 if hiza == "orta" else x - w if hiza == "sag" else x
        dy = (1 - out_cubic(p)) * boy * 0.45
        cv.drawString(s, x0, y + boy * 0.36 + dy, f, skia.Paint(AntiAlias=True, Color=alfa(renk_, clamp(p * 1.6))))

    def buyuk_yazi(self, cv, s, x, y, boy, renk_, hiza="orta", p=1.0, kimlik=0, t=0.0):
        self.yazi(cv, s, x, y, boy, renk_, hiza, p=p, kimlik=kimlik, t=t)

    def satirlar(self, cv, satir, x, y, boy, renk_, hiza="orta", p0=0.0, u=0.0, aralik=1.12, buyuk=False, kimlik=0, t=0.0):
        """Ortası y olan çok satırlı blok; satırlar 0,12 sn arayla girer. Toplam yüksekliği döner."""
        n = len(satir)
        for j, s in enumerate(satir):
            yy = y + (j - (n - 1) / 2) * boy * aralik
            pp = prog(u, p0 + 0.12 * j, 0.45)
            (self.buyuk_yazi if buyuk else self.yazi)(cv, s, x, yy, boy, renk_, hiza, p=pp, kimlik=kimlik + j, t=t)
        return n * boy * aralik

    # ---------- temel taşlar ----------
    def fon(self, cv, VW, VH, t, i):
        cv.drawColor(self.p["zemin"])
        # yavaş kayan iki düz daire (gradyan yok: bantlanmaz)
        for k, (cx, cy, r) in enumerate(((0.85, 0.18, 0.42), (0.1, 0.92, 0.36))):
            dx = math.sin(t * 0.25 + k * 2) * 18
            cv.drawCircle(VW * cx + dx, VH * cy, min(VW, VH) * r, skia.Paint(AntiAlias=True, Color=alfa(self.p["yuzey"], 0.7)))

    def panel(self, cv, r, renk_, p=1.0, kimlik=0, t=0.0):
        if p <= 0:
            return
        s = 0.86 + 0.14 * out_back(p)
        cv.save(); cv.translate(r.centerX(), r.centerY()); cv.scale(s, s); cv.translate(-r.centerX(), -r.centerY())
        cv.drawRoundRect(r, 22, 22, skia.Paint(AntiAlias=True, Color=alfa(renk_, clamp(p * 1.5))))
        cv.restore()

    def isaret(self, cv, x, y, r, renk_, p=1.0, kimlik=0, t=0.0, n=1):
        if p <= 0:
            return
        rr = r * out_back(p)
        cv.drawCircle(x, y, rr, skia.Paint(AntiAlias=True, Color=renk_))
        self.yazi(cv, str(n), x, y, r * 1.1, self.p["vurgu_yazi"], p=min(1, p * 2))

    def nesne(self, cv, r, sh, p, t):
        """Görselsiz ürün: yuvarlak köşeli kutu + adın baş harfi."""
        s = out_back(p)
        w = min(r.width(), r.height()) * 0.62 * s
        k = skia.Rect.MakeXYWH(r.centerX() - w / 2, r.centerY() - w / 2, w, w)
        cv.drawRoundRect(k, w * 0.12, w * 0.12, skia.Paint(AntiAlias=True, Color=self.p["vurgu"]))
        self.yazi(cv, self.harf(sh["ad"][:1], True), k.centerX(), k.centerY(), w * 0.5, self.p["vurgu_yazi"], p=p)

    def gorsel(self, cv, yol, r, p=1.0, kimlik=0, t=0.0, cerceve=True):
        """Gerçek görsel (müşteri ürünü/logo): yeniden çizilmez, oranı korunur, kutuya sığar; beyaz kart + gölge."""
        img = _resim(str(yol))
        if img is None or p <= 0:
            return
        o = min(r.width() / img.width(), r.height() / img.height())
        w, h = img.width() * o, img.height() * o
        s = 0.9 + 0.1 * out_back(p)
        cv.save(); cv.translate(r.centerX(), r.centerY()); cv.scale(s, s)
        k = skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h)
        if cerceve:
            pay = min(w, h) * 0.04
            kk = k.makeOutset(pay, pay)
            cv.drawRoundRect(kk.makeOffset(0, 10), 18, 18, skia.Paint(AntiAlias=True, Color=0x33000000,
                             MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14)))
            cv.drawRoundRect(kk, 18, 18, skia.Paint(AntiAlias=True, Color=alfa(0xFFFFFFFF, p)))
        cv.drawImageRect(img, k, skia.SamplingOptions(skia.CubicResampler.Mitchell()), skia.Paint(Alphaf=clamp(p * 1.5)))
        cv.restore()

    def gecis_ciz(self, cv, VW, VH, p, eski, yeni):
        """Eski sahne yukarı kayıp söner, yeni aşağıdan gelir."""
        e = in_out(p)
        cv.save(); cv.translate(0, -VH * 0.06 * e); cv.saveLayerAlpha(None, int(255 * (1 - e))); eski(); cv.restore(); cv.restore()
        cv.save(); cv.translate(0, VH * 0.05 * (1 - e)); cv.saveLayerAlpha(None, int(255 * e)); yeni(); cv.restore(); cv.restore()

    def ust_katman(self, cv, W, H, t):
        pass

    # ---------- yerleşim ----------
    def alan(self, VW, VH, fmt):
        sol, sag, ust, alt = GUVENLI.get(fmt, GUVENLI["1x1"])
        return skia.Rect.MakeLTRB(VW * sol, VH * ust, VW * (1 - sag), VH * alt)

    # ---------- sahne tipleri ----------
    def ciz_baslik(self, cv, sh, u, d, A, t):
        dik = A.height() > A.width()
        gen = A.width() * 0.92
        sat, boy = self.sar(self.harf(sh["metin"]), 190 if dik else 150, gen, 3)
        cy = A.centerY() - (40 if sh.get("alt") else 0)
        h = self.satirlar(cv, sat, A.centerX(), cy, boy, self.p["murekkep"], u=u, p0=0.12, aralik=1.08, buyuk=True, t=t)
        if sh.get("ust"):
            b = self.sigdir(self.harf(sh["ust"], True), 52, gen, 700)
            self.yazi(cv, self.harf(sh["ust"], True), A.centerX(), cy - h / 2 - b * 1.4, b, self.p["vurgu"], p=prog(u, 0.02, 0.4), agirlik=700)
        if sh.get("alt"):
            alt, b = self.sar(sh["alt"], 66, gen, 2, 700)
            self.satirlar(cv, alt, A.centerX(), cy + h / 2 + b * 0.9 * len(alt), b, self.p["soluk"], u=u, p0=0.45)

    def ciz_liste(self, cv, sh, u, d, A, t):
        m = sh["maddeler"]
        n = len(m)
        bas = self.sar(self.harf(sh["baslik"]), 110, A.width() * 0.92, 2) if sh.get("baslik") else ([], 0)
        bas_h = len(bas[0]) * bas[1] * 1.12 + (50 if bas[0] else 0)
        satir_h = min(200, (A.height() - bas_h) / n)
        ust = A.centerY() - (bas_h + satir_h * n) / 2
        if bas[0]:
            self.satirlar(cv, bas[0], A.centerX(), ust + (bas_h - 50) / 2, bas[1], self.p["vurgu"], u=u, buyuk=True, t=t)
            ust += bas_h
        boy = min(86, satir_h * 0.4)
        aralik = min(0.55, max(0.25, (d - 1.0) / (n + 1)))
        r = boy * 0.62
        x0 = A.left() + r * 1.4
        gen = A.right() - (x0 + r * 2.2) - 10
        boy = min(boy, *(self.sigdir(x, boy, gen, 700) for x in m))
        for j, x in enumerate(m):
            yy = ust + satir_h * (j + 0.5)
            pp = prog(u, 0.35 + j * aralik, 0.4)
            if pp <= 0:
                continue
            kr = skia.Rect.MakeLTRB(A.left(), yy - satir_h * 0.42, A.right(), yy + satir_h * 0.42)
            self.panel(cv, kr, self.p["yuzey"], pp, kimlik=10 + j, t=t)
            self.isaret(cv, x0, yy, r, self.p["vurgu"], pp, kimlik=20 + j, t=t, n=j + 1)
            self.yazi(cv, x, x0 + r * 2.0, yy, boy, self.p["murekkep"], "sol", 700, pp, kimlik=30 + j, t=t)

    def ciz_sayi(self, cv, sh, u, d, A, t):
        gen = A.width() * 0.9
        cp = prog(u, 0.2, min(1.2, d * 0.45))
        deger = self.harf(sh["deger"], False)
        boy = self.sigdir(sh["deger"], 330, gen)
        cy = A.centerY() - (50 if sh.get("etiket") else 0)
        if sh.get("ust"):
            b = self.sigdir(self.harf(sh["ust"], True), 48, gen, 700)
            self.yazi(cv, self.harf(sh["ust"], True), A.centerX(), cy - boy * 0.72, b, self.p["soluk"], p=prog(u, 0.0, 0.4), agirlik=700)
        pb = prog(u, 0.12, 0.35)
        cv.save(); s = 0.7 + 0.3 * out_back(pb); cv.translate(A.centerX(), cy); cv.scale(s, s)
        self.buyuk_yazi(cv, say(deger, cp), 0, 0, boy, self.p["vurgu"], p=pb, kimlik=3, t=t)
        cv.restore()
        if sh.get("etiket"):
            sat, b = self.sar(sh["etiket"], 74, gen, 2, 700)
            self.satirlar(cv, sat, A.centerX(), cy + boy * 0.62 + b * 0.6 * len(sat), b, self.p["murekkep"], u=u, p0=0.55)

    def ciz_alinti(self, cv, sh, u, d, A, t):
        gen = A.width() * 0.86
        dik = A.height() > A.width()
        sat, boy = self.sar(sh["metin"], 100, gen, 5, 700)
        h = len(sat) * boy * 1.22
        cy = A.centerY() - (30 if sh.get("kaynak") else 0)
        q = prog(u, 0.0, 0.4)
        self.buyuk_yazi(cv, "“", A.centerX(), cy - h / 2 - 110, 260, self.p["vurgu"], p=q, kimlik=1, t=t)
        for j, s in enumerate(sat):
            self.yazi(cv, s, A.centerX(), cy - h / 2 + boy * 1.22 * (j + 0.5), boy, self.p["murekkep"],
                      agirlik=700, p=prog(u, 0.2 + 0.18 * j, 0.5), kimlik=10 + j, t=t)
        if sh.get("kaynak"):
            b = self.sigdir("— " + sh["kaynak"], 56, gen, 700)
            self.yazi(cv, "— " + sh["kaynak"], A.centerX(), cy + h / 2 + 70, b, self.p["soluk"], agirlik=700,
                      p=prog(u, 0.4 + 0.18 * len(sat), 0.5))

    def ciz_karsilastirma(self, cv, sh, u, d, A, t):
        dik = A.height() > A.width() * 1.15
        ust = A.top()
        if sh.get("baslik"):
            sat, b = self.sar(self.harf(sh["baslik"]), 78, A.width() * 0.92, 2)
            h = self.satirlar(cv, sat, A.centerX(), ust + b * len(sat) * 0.6, b, self.p["murekkep"], u=u, buyuk=True, t=t)
            ust += h + 30
        bosluk = 70
        if dik:
            ph = (A.bottom() - ust - bosluk) / 2
            r1 = skia.Rect.MakeLTRB(A.left(), ust, A.right(), ust + ph)
            r2 = skia.Rect.MakeLTRB(A.left(), ust + ph + bosluk, A.right(), A.bottom())
        else:
            pw = (A.width() - bosluk) / 2
            r1 = skia.Rect.MakeLTRB(A.left(), ust, A.left() + pw, A.bottom())
            r2 = skia.Rect.MakeLTRB(A.right() - pw, ust, A.right(), A.bottom())
        for k, (r, ad, deger, zemin, yazi_r, t0) in enumerate((
                (r1, sh["sol"], sh.get("sol_deger"), self.p["yuzey"], self.p["soluk"], 0.1),
                (r2, sh["sag"], sh.get("sag_deger"), self.p["vurgu"], self.p["vurgu_yazi"], 0.55))):
            pp = prog(u, t0, 0.45)
            self.panel(cv, r, zemin, pp, kimlik=40 + k, t=t)
            gen = r.width() * 0.84
            if deger:
                b = self.sigdir(deger, min(220, r.height() * 0.46), gen)
                self.buyuk_yazi(cv, say(deger, prog(u, t0 + 0.1, 0.8)), r.centerX(), r.centerY() - r.height() * 0.12, b, yazi_r,
                                p=pp, kimlik=50 + k, t=t)
                b2 = self.sigdir(self.harf(ad), min(80, r.height() * 0.2), gen)
                self.yazi(cv, self.harf(ad), r.centerX(), r.centerY() + r.height() * 0.24, b2, yazi_r, p=pp)
            else:
                sat, b = self.sar(self.harf(ad), min(120, r.height() * 0.3), gen, 2)
                self.satirlar(cv, sat, r.centerX(), r.centerY(), b, yazi_r, u=u, p0=t0 + 0.05, buyuk=True, kimlik=60 + k, t=t)
        pa = prog(u, 0.45, 0.3)
        if pa > 0:
            x, y = (A.centerX(), (r1.bottom() + r2.top()) / 2) if dik else ((r1.right() + r2.left()) / 2, (r1.centerY()))
            self.ok(cv, x, y, 30 * out_back(pa), dik)

    def ok(self, cv, x, y, s, dik):
        yol = skia.Path()
        if dik:
            yol.moveTo(x - s, y - s * 0.5); yol.lineTo(x + s, y - s * 0.5); yol.lineTo(x, y + s * 0.7)
        else:
            yol.moveTo(x - s * 0.5, y - s); yol.lineTo(x - s * 0.5, y + s); yol.lineTo(x + s * 0.7, y)
        yol.close()
        cv.drawPath(yol, skia.Paint(AntiAlias=True, Color=self.p["murekkep"]))

    def ciz_urun(self, cv, sh, u, d, A, t):
        dik = A.height() > A.width() * 1.15
        if dik:
            gr = skia.Rect.MakeLTRB(A.left(), A.top(), A.right(), A.top() + A.height() * 0.58)
            yr = skia.Rect.MakeLTRB(A.left(), gr.bottom() + 20, A.right(), A.bottom())
        else:
            gr = skia.Rect.MakeLTRB(A.left(), A.top(), A.centerX() - 20, A.bottom())
            yr = skia.Rect.MakeLTRB(A.centerX() + 20, A.top(), A.right(), A.bottom())
        pg = prog(u, 0.0, 0.55)
        if sh.get("gorsel"):
            self.gorsel(cv, self.klasor / sh["gorsel"], gr.makeInset(10, 10), pg, kimlik=70, t=t)
        else:
            self.nesne(cv, gr, sh, pg, t)
        gen = yr.width() * 0.94
        sat, b = self.sar(self.harf(sh["ad"]), 104, gen, 2)
        parca = [("ad", sat, b)]
        if sh.get("ozellik"):
            s2, b2 = self.sar(sh["ozellik"], 50, gen, 2, 700)
            parca.append(("oz", s2, b2))
        if sh.get("fiyat"):
            parca.append(("fiyat", [sh["fiyat"]], self.sigdir(sh["fiyat"], 72, gen * 0.6)))
        top = sum(len(s) * b * 1.15 + 34 for _, s, b in parca)
        y = yr.centerY() - top / 2
        for k, (tur, s, b) in enumerate(parca):
            h = len(s) * b * 1.15
            p0 = 0.3 + 0.2 * k
            if tur == "fiyat":
                w = self.olc(s[0], b) + b * 1.1
                pr = skia.Rect.MakeXYWH(yr.centerX() - w / 2, y, w, b * 1.5)
                self.panel(cv, pr, self.p["vurgu"], prog(u, p0, 0.4), kimlik=80, t=t)
                self.buyuk_yazi(cv, s[0], pr.centerX(), pr.centerY(), b, self.p["vurgu_yazi"], p=prog(u, p0 + 0.05, 0.4), t=t)
                h = b * 1.5
            else:
                self.satirlar(cv, s, yr.centerX(), y + h / 2, b, self.p["murekkep"] if tur == "ad" else self.p["soluk"],
                              u=u, p0=p0, buyuk=tur == "ad", t=t, kimlik=90 + k)
            y += h + 34

    def ciz_cta(self, cv, sh, u, d, A, t):
        gen = A.width() * 0.84
        logo = self.marka.get("logo")
        cy = A.centerY()
        if logo:
            lr = skia.Rect.MakeXYWH(A.centerX() - A.width() * 0.22, A.top() + A.height() * 0.04, A.width() * 0.44, A.height() * 0.24)
            self.gorsel(cv, self.klasor / logo, lr, prog(u, 0.0, 0.5), kimlik=95, t=t, cerceve=False)
            cy = A.centerY() + A.height() * 0.08
        sat, b = self.sar(self.harf(sh["metin"]), 120, gen * 0.86, 2)
        w = max(self.olc(x, b) for x in sat) + b * 1.2
        h = len(sat) * b * 1.1 + b * 0.9
        r = skia.Rect.MakeXYWH(A.centerX() - w / 2, cy - h / 2, w, h)
        pp = prog(u, 0.1, 0.45)
        nefes = 1 + 0.025 * math.sin(max(0, u - 0.8) * 4.5) * prog(u, 0.8, 0.3)
        cv.save(); cv.translate(r.centerX(), r.centerY()); cv.scale(nefes, nefes); cv.translate(-r.centerX(), -r.centerY())
        self.panel(cv, r, self.p["vurgu"], pp, kimlik=96, t=t)
        self.satirlar(cv, sat, r.centerX(), r.centerY(), b, self.p["vurgu_yazi"], u=u, p0=0.2, aralik=1.1, buyuk=True, t=t, kimlik=97)
        cv.restore()
        alt = sh.get("alt") or self.marka.get("ad")
        if alt:
            b2 = self.sigdir(alt, 58, gen, 700)
            self.yazi(cv, alt, A.centerX(), r.bottom() + b2 * 1.6, b2, self.p["soluk"], agirlik=700, p=prog(u, 0.55, 0.45))

    def ciz_gecis(self, cv, sh, u, d, A, t):
        if sh.get("metin"):
            b = self.sigdir(self.harf(sh["metin"]), 110, A.width() * 0.86)
            self.buyuk_yazi(cv, self.harf(sh["metin"]), A.centerX(), A.centerY(), b, self.p["vurgu"], p=prog(u, 0.05, 0.35), t=t)

    # ---------- kare ----------
    def sahne_ciz(self, cv, i, t, VW, VH, fmt):
        sh = self.s["sahneler"][i]
        A = self.alan(VW, VH, fmt)
        getattr(self, "ciz_" + sh["tip"])(cv, sh, t - sh["bas"], sh["son"] - sh["bas"], A, t)

    def sahne_sirasi(self, t):
        shs = self.s["sahneler"]
        for i in range(len(shs) - 1, -1, -1):
            if t >= shs[i]["bas"]:
                return i
        return 0

    def poz(self, t):
        return math.floor(t * self.POZ + 1e-6) / self.POZ if self.POZ else t

    def kare(self, cv, t, W, H, fmt):
        t = self.poz(min(t, self.s["sure"] - 1e-3))
        u = min(W, H) / 1080
        VW, VH = W / u, H / u
        i = self.sahne_sirasi(t)
        self._t, self._i, self._fmt = t, i, fmt  # geçişlerin fonu yeniden çizebilmesi için
        cv.save(); cv.scale(u, u)
        self.fon(cv, VW, VH, t, i)
        bas = self.s["sahneler"][i]["bas"]
        if i > 0 and t - bas < self.GECIS:
            self.gecis_ciz(cv, VW, VH, (t - bas) / self.GECIS,
                           lambda: self.sahne_ciz(cv, i - 1, t, VW, VH, fmt), lambda: self.sahne_ciz(cv, i, t, VW, VH, fmt))
        else:
            self.sahne_ciz(cv, i, t, VW, VH, fmt)
        cv.restore()
        self.ust_katman(cv, W, H, t)


def kaplamalar() -> dict[str, type]:
    """kaplamalar/ klasöründeki her modülün KAPLAMA sınıfı + taban (kinetik). Yeni stil dosyası eklemek yeter."""
    import importlib
    out = {Kaplama.ad: Kaplama}
    for p in sorted((BURADA / "kaplamalar").glob("*.py")):
        if p.stem.startswith("_"):
            continue
        m = importlib.import_module(f"kaplamalar.{p.stem}")
        out[m.KAPLAMA.ad] = m.KAPLAMA
    return out

