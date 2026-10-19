"""Desen şablonunun görüntüsü: dört stil (vitray, linol, çini, teknik çizim), PIL + numpy.

Her kare `t` anının saf fonksiyonudur. Ağır katmanlar (cam hücreleri, çini deseni, motif maskeleri, yazılar) format
ve sahne başına bir kez hazırlanır; kareler paralel süreçlerde bu katmanlardan birleştirilir. Kenarlar 3 kat süper
örneklenir (temiz kenar), her kareye ±1 kod değeri tane eklenir (ışık geçişlerinde basamaklanma olmaz).
"""

from __future__ import annotations

import math
import multiprocessing as mp
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import fontlar
import motifler
import zaman

SS = 3


# ---------- yardımcılar ----------
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def in_cubic(p): return p ** 3
def in_out(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_back(p, s=1.7): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def renk(h) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def _font(agirlik: int, boy: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(fontlar.yol(agirlik), max(8, int(boy)))


class Katman:
    """Ekranın bir dikdörtgeninde alfa maskesi (0–1)."""

    def __init__(self, a: np.ndarray, x0: int, y0: int):
        self.a, self.x0, self.y0 = a, x0, y0

    @property
    def kutu(self):
        return self.x0, self.y0, self.x0 + self.a.shape[1], self.y0 + self.a.shape[0]

    def olcekli(self, k: float, cx: float, cy: float) -> "Katman":
        if abs(k - 1) < 1e-3:
            return self
        h, w = self.a.shape
        nw, nh = max(1, int(w * k)), max(1, int(h * k))
        a = np.asarray(Image.fromarray(self.a).resize((nw, nh), Image.BILINEAR), np.float32)
        return Katman(a, int(round(cx - (cx - self.x0) * k)), int(round(cy - (cy - self.y0) * k)))

    def kaydir(self, dx: int, dy: int) -> "Katman":
        return Katman(self.a, self.x0 + dx, self.y0 + dy)


def katman(kutu, ciz, ss: int = SS) -> Katman:
    """kutu içinde ss kat çizip küçültür; ciz(d, T) — T(x, y) ekran koordinatını tuvale çevirir."""
    x0, y0, x1, y1 = (int(math.floor(kutu[0])), int(math.floor(kutu[1])), int(math.ceil(kutu[2])), int(math.ceil(kutu[3])))
    im = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    ciz(ImageDraw.Draw(im), lambda x, y: ((x - x0) * ss, (y - y0) * ss), ss)
    return Katman(np.asarray(im.reduce(ss), np.float32) / 255.0, x0, y0)


def boya(img: np.ndarray, k: Katman | None, rnk, alfa: float = 1.0) -> None:
    if k is None or alfa <= 0:
        return
    H, W = img.shape[:2]
    x0, y0, x1, y1 = k.kutu
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if cx0 >= cx1 or cy0 >= cy1:
        return
    a = k.a[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0, None] * alfa
    bolge = img[cy0:cy1, cx0:cx1]
    bolge *= 1 - a
    bolge += np.asarray(rnk, np.float32) * a


def puruz(W, H, olcek, seed) -> np.ndarray:
    """0–1 arası yumuşak gürültü (olcek px'lik taneler)."""
    rng = np.random.default_rng(seed)
    a = (rng.random((max(2, int(H / olcek)), max(2, int(W / olcek)))) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(a).resize((W, H), Image.BICUBIC), np.float32) / 255.0


def motif_noktalar(ad, cx, cy, R):
    return [([(cx + x * R, cy + y * R) for x, y in p], dolu) for p, dolu in motifler.parcalar(ad)]


def motif_katmani(ad, cx, cy, R, pay=0.0) -> Katman:
    def ciz(d, T, ss):
        for p, dolu in motif_noktalar(ad, cx, cy, R):
            d.polygon([T(x, y) for x, y in p], fill=255 if dolu else 0)
    m = R * (1.05 + pay)
    return katman((cx - m, cy - m, cx + m, cy + m), ciz)


def yazi_katmani(metin, agirlik, boy, cx, cy, max_w, harf=0.0) -> tuple[Katman, float]:
    """Ortalanmış yazı; genişliğe sığmazsa küçülür. (katman, kullanılan punto)"""
    while True:
        f = _font(agirlik, boy)
        x0, y0, x1, y1 = f.getbbox(metin)
        gen = x1 - x0 + harf * boy * max(0, len(metin) - 1)
        if gen <= max_w or boy < 14:
            break
        boy *= 0.95
    pay = boy * 0.25
    kutu = (cx - gen / 2 - pay, cy - boy * 0.75 - pay, cx + gen / 2 + pay, cy + boy * 0.75 + pay)

    def ciz(d, T, ss):
        fs = _font(agirlik, boy * ss)
        if not harf:
            d.text(T(cx, cy), metin, font=fs, anchor="mm", fill=255)
            return
        x = cx - gen / 2
        for c in metin:
            d.text(T(x, cy), c, font=fs, anchor="lm", fill=255)
            x += f.getlength(c) + harf * boy
    return katman(kutu, ciz, ss=2), boy


def gorsel_oku(s, max_w, max_h) -> Image.Image | None:
    g = s.get("gorsel")
    if not g:
        return None
    im = Image.open(Path(s["_klasor"]) / g["dosya"]).convert("RGBA")
    k = min(max_w / im.width, max_h / im.height)
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)


def gorsel_bas(img, gor: Image.Image, cx, cy, alfa=1.0, k=1.0):
    if gor is None or alfa <= 0:
        return
    if abs(k - 1) > 1e-3:
        gor = gor.resize((max(1, int(gor.width * k)), max(1, int(gor.height * k))), Image.LANCZOS)
    a = np.asarray(gor, np.float32)
    boya_rgba(img, a, int(cx - gor.width / 2), int(cy - gor.height / 2), alfa)


def boya_rgba(img, a, x0, y0, alfa=1.0):
    H, W = img.shape[:2]
    h, w = a.shape[:2]
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if cx0 >= cx1 or cy0 >= cy1:
        return
    p = a[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    al = p[..., 3:4] / 255.0 * alfa
    bolge = img[cy0:cy1, cx0:cx1]
    bolge *= 1 - al
    bolge += p[..., :3] * al


# ---------- ortak sahne düzeni ----------
class Duzen:
    def __init__(self, s, fmt, W, H, olcek_r=1.0):
        y = zaman.bicim(s, fmt)
        self.W, self.H, self.fmt = W, H, fmt
        self.cx, self.cy = y["mx"] * W, y["my"] * H
        self.R = y["mr"] * (W if y["r_eksen"] == "w" else H) * olcek_r
        self.bx, self.by, self.ay = y["bx"] * W, y["by"] * H, y["ay"] * H
        self.gen = y["gen"] * W
        self.boy = y["boy"] * min(W, H)


def _gorsel_sahnesi(s, i):
    return bool(s.get("gorsel")) and i == len(s["sahneler"]) - 1


# ---------- 1 · vitray ----------
class Vitray:
    """Kurşun çizgili cam: hücreler sırayla yanar, motif sıcak camdan, arka cam soğuk; ışık arkadan kayar."""
    TANE = 2.2  # ışık geçişleri ve cam dokusunda basamaklanmayı kırar
    SICAK = ["#E8B032", "#D9762B", "#C23A3A", "#F0CC62", "#B5482A"]
    SOGUK = ["#1F4E9C", "#2A8A7A", "#5B3A8F", "#2E6FB0", "#1D6B54", "#3C2F7A"]
    KURSUN = renk("#161412")
    KREM = renk("#FAECC8")
    ALTIN = renk("#E2B85A")

    def __init__(self, s):
        self.s = s
        r = s.get("renkler", {})
        self.sicak = np.stack([renk(x) for x in r.get("sicak", self.SICAK)])
        self.soguk = np.stack([renk(x) for x in r.get("soguk", self.SOGUK)])
        self.on = {}

    def hazirla(self, fmt, W, H):
        if fmt in self.on:
            return
        s, D = self.s, Duzen(self.s, fmt, W, H)
        hucre = 0.105 * min(W, H)
        rng = np.random.default_rng(11)
        gx, gy = int(W / hucre) + 2, int(H / hucre) + 2
        pts = np.array([((i - 0.5 + rng.uniform(.15, .85)) * hucre, (j - 0.5 + rng.uniform(.15, .85)) * hucre)
                        for j in range(gy) for i in range(gx)], np.float32)
        xs = np.arange(W, dtype=np.float32)[None, :]
        ys = np.arange(H, dtype=np.float32)[:, None]
        d1 = np.full((H, W), np.inf, np.float32); d2 = d1.copy()
        l1 = np.zeros((H, W), np.int32); l2 = l1.copy()
        for k, (px, py) in enumerate(pts):
            d = (xs - px) ** 2 + (ys - py) ** 2
            yeni1 = d < d1
            yeni2 = ~yeni1 & (d < d2)
            d2 = np.where(yeni1, d1, np.where(yeni2, d, d2)); l2 = np.where(yeni1, l1, np.where(yeni2, k, l2))
            d1 = np.where(yeni1, d, d1); l1 = np.where(yeni1, k, l1)
        aralik = np.linalg.norm(pts[l1] - pts[l2], axis=-1) + 1e-6
        kenar = (d2 - d1) / (2 * aralik)  # komşu hücre sınırına dik uzaklık (px)
        yk = 0.0042 * min(W, H)
        kursun = np.clip((yk + 0.75 - kenar) / 1.5, 0, 1).astype(np.float32)
        doku = (0.86 + 0.20 * puruz(W, H, 0.05 * min(W, H), 3) + 0.08 * puruz(W, H, 0.012 * min(W, H), 4)).astype(np.float32)
        q = (xs / W * 0.55 + ys / H * 0.45).astype(np.float32)
        sahneler = []
        for i, sh in enumerate(s["sahneler"]):
            gorsel = _gorsel_sahnesi(s, i)
            if sh.get("motif") and not gorsel:
                M = np.zeros((H, W), np.float32); boya_m = motif_katmani(sh["motif"], D.cx, D.cy, D.R)
                x0, y0, x1, y1 = boya_m.kutu
                M[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = boya_m.a[max(0, -y0):max(0, -y0) + min(H, y1) - max(0, y0),
                                                                              max(0, -x0):max(0, -x0) + min(W, x1) - max(0, x0)]
                ic = M > 0.5

                def kontur(d, T, ss, ad=sh["motif"]):
                    for p, _ in motif_noktalar(ad, D.cx, D.cy, D.R):
                        d.line([T(x, y) for x, y in p + [p[0]]], fill=255, width=int(yk * 2.6 * ss), joint="curve")
                m = D.R * 1.1
                kk = katman((D.cx - m, D.cy - m, D.cx + m, D.cy + m), kontur)
            else:
                ic = np.zeros((H, W), bool); kk = None
            bolge = l1 * 2 + ic
            n = len(pts) * 2
            rr = np.random.default_rng(100 + i)
            renkler = np.where((np.arange(n) % 2 == 1)[:, None], self.sicak[rr.integers(0, len(self.sicak), n)],
                               self.soguk[rr.integers(0, len(self.soguk), n)]) * rr.uniform(0.88, 1.08, (n, 1))
            merkez = np.hypot(pts[np.arange(n) // 2, 0] - D.cx, pts[np.arange(n) // 2, 1] - D.cy) / max(W, H)
            gecikme = np.where(np.arange(n) % 2 == 1, 0.05 + 0.5 * merkez, 0.30 + 0.9 * merkez + rr.uniform(0, 0.35, n))
            sonme = rr.uniform(0, zaman.GECIS - 0.18, n)
            k_all = kursun.copy()
            if kk is not None:
                x0, y0, x1, y1 = kk.kutu
                sl = (slice(max(0, y0), min(H, y1)), slice(max(0, x0), min(W, x1)))
                k_all[sl] = np.maximum(k_all[sl], kk.a[sl[0].start - y0:sl[0].stop - y0, sl[1].start - x0:sl[1].stop - x0])
            taban = (renkler[bolge] * doku[..., None]).astype(np.float32)
            sahneler.append({"bolge": bolge, "taban": taban, "kursun": k_all, "gecikme": gecikme, "sonme": sonme,
                             "yazi": self._yazilar(sh, D)})
        gor = gorsel_oku(s, D.R * 1.7, D.R * 1.7)
        self.on[fmt] = {"D": D, "q": q, "sahneler": sahneler, "gorsel": gor}

    def _yazilar(self, sh, D):
        b, boy = yazi_katmani(sh["baslik"], 900, D.boy, D.bx, D.by, D.gen * 0.86)
        a = yazi_katmani(sh["alt"], 700, boy * 0.36, D.bx, D.ay, D.gen * 0.86, harf=0.04)[0] if sh.get("alt") else None
        x0 = min(b.kutu[0], a.kutu[0] if a else 1e9) - boy * 0.25
        x1 = max(b.kutu[2], a.kutu[2] if a else -1e9) + boy * 0.25
        y0, y1 = b.kutu[1] + boy * 0.05, (a.kutu[3] if a else b.kutu[3]) + boy * 0.05
        lev = katman((x0, y0, x1, y1), lambda d, T, ss: d.rounded_rectangle([*T(x0, y0), *T(x1, y1)], radius=int(boy * 0.18 * ss), fill=255))
        cer = katman((x0, y0, x1, y1), lambda d, T, ss: d.rounded_rectangle([*T(x0 + 5, y0 + 5), *T(x1 - 5, y1 - 5)],
                                                                            radius=int(boy * 0.14 * ss), outline=255, width=int(2.2 * ss)))
        return {"baslik": b, "alt": a, "levha": lev, "cerceve": cer}

    def kare(self, t, fmt, W, H):
        self.hazirla(fmt, W, H)
        on = self.on[fmt]
        i, u, d = zaman.sahne(self.s, t)
        sh = on["sahneler"][i]
        son = i == len(on["sahneler"]) - 1
        alt_deger = 0.0 if i == 0 else 0.14
        yan = np.clip((u - sh["gecikme"]) / 0.28, 0, 1)
        b = alt_deger + (1 - alt_deger) * (yan * yan * (3 - 2 * yan))
        if not son:
            kalan = d - u
            b = np.where(kalan < zaman.GECIS, 0.14 + (b - 0.14) * np.clip((kalan - sh["sonme"]) / 0.18, 0, 1), b)
        isik = 1 + 0.20 * np.exp(-((on["q"] - (-0.25 + 1.5 * (u / max(d, 1e-6)))) / 0.11) ** 2)
        img = sh["taban"] * (b[sh["bolge"]] * isik)[..., None]
        k = sh["kursun"][..., None]
        img = img * (1 - k) + self.KURSUN * k
        D = on["D"]
        cik = 1.0 if son else clamp((d - u) / zaman.GECIS * 1.6)
        if _gorsel_sahnesi(self.s, i) and on["gorsel"] is not None:
            p = out_cubic(prog(u, 0.35, 0.5))
            yr = max(on["gorsel"].size) * 0.62
            daire = katman((D.cx - yr * 1.2, D.cy - yr * 1.2, D.cx + yr * 1.2, D.cy + yr * 1.2),
                           lambda dd, T, ss: dd.ellipse([*T(D.cx - yr, D.cy - yr), *T(D.cx + yr, D.cy + yr)], fill=255))
            boya(img, daire.olcekli(0.8 + 0.2 * p, D.cx, D.cy), self.KREM, p)
            gorsel_bas(img, on["gorsel"], D.cx, D.cy, p, 0.8 + 0.2 * p)
        y = sh["yazi"]
        boya(img, y["levha"], self.KURSUN, out_cubic(prog(u, 0.25, 0.3)) * cik)
        boya(img, y["cerceve"], self.ALTIN, out_cubic(prog(u, 0.35, 0.35)) * cik * 0.9)
        boya(img, y["baslik"], self.KREM, out_cubic(prog(u, 0.40, 0.35)) * cik)
        boya(img, y["alt"], self.ALTIN, out_cubic(prog(u, 0.60, 0.35)) * cik)
        return img


# ---------- 2 · linol baskı ----------
class Linol:
    """Linol baskı: merdane mürekkebi yukarıdan aşağı yayar, oyma çizgiler kazınır, yazı damga gibi basılır.
    Saniyede 12 poz (stop-motion), her pozda mürekkep dokusu ve konum hafifçe oynar."""
    POZ = 12

    def __init__(self, s):
        self.s = s
        r = s.get("renkler", {})
        self.kagit = renk(r.get("kagit", "#EEE4D0"))
        self.murekkep = renk(r.get("murekkep", "#181614"))
        self.vurgu = renk(r.get("vurgu", "#C2382B"))
        self.on = {}

    def hazirla(self, fmt, W, H):
        if fmt in self.on:
            return
        s, D = self.s, Duzen(self.s, fmt, W, H, olcek_r=0.80)
        kagit = (self.kagit + (puruz(W, H, 0.004 * W, 21)[..., None] - 0.5) * 7
                 + (puruz(W, H, 0.08 * W, 22)[..., None] - 0.5) * 6).astype(np.float32)
        pozlar = []
        for p in range(6):
            kenar = puruz(W, H, 0.006 * W, 30 + p)
            rr = np.random.default_rng(40 + p)
            bosluk = (rr.random((H // 3, W // 3)) > 0.9985).astype(np.uint8) * 255
            bosluk = np.asarray(Image.fromarray(bosluk).resize((W, H), Image.BILINEAR), np.float32) / 255.0
            pozlar.append((kenar, bosluk))
        sahneler = []
        for i, sh in enumerate(s["sahneler"]):
            gorsel = _gorsel_sahnesi(s, i)
            cx, cy, R = D.cx, D.cy, D.R
            m = R * 1.62
            ad = None if gorsel else sh.get("motif")

            def taban(d, T, ss, ad=ad):
                d.ellipse([*T(cx - R * 1.15, cy - R * 1.15), *T(cx + R * 1.15, cy + R * 1.15)], fill=255)
                if ad:
                    for p_, dolu in motif_noktalar(ad, cx, cy, R * 0.86):
                        d.polygon([T(x, y) for x, y in p_], fill=0 if dolu else 255)
                d.ellipse([*T(cx - R * 1.27, cy - R * 1.27), *T(cx + R * 1.27, cy + R * 1.27)], outline=255, width=int(R * 0.05 * ss))
                for k in range(28):
                    a = k / 28 * math.tau
                    r1, r2, g = R * 1.36, R * (1.60 if k % 2 == 0 else 1.48), 0.045
                    d.polygon([T(cx + r1 * math.cos(a - g), cy + r1 * math.sin(a - g)), T(cx + r2 * math.cos(a), cy + r2 * math.sin(a)),
                               T(cx + r1 * math.cos(a + g), cy + r1 * math.sin(a + g))], fill=255)

            def tarama(d, T, ss, ad=ad):
                if not ad:
                    return
                ara = R * 0.085
                y = cy - R
                while y < cy + R:
                    pts = [T(x, y + math.sin((x - cx) / R * 3.2 + y * 0.01) * ara * 0.18) for x in np.linspace(cx - R, cx + R, 40)]
                    d.line(pts, fill=255, width=int(ara * 0.32 * ss))
                    y += ara

            kutu = (cx - m, cy - m, cx + m, cy + m)
            tb = katman(kutu, taban)
            mk = motif_katmani(ad, cx, cy, R * 0.86) if ad else None
            tr = katman(kutu, tarama)
            if mk is not None:  # tarama yalnız motifin içinde
                x0, y0 = mk.x0 - tr.x0, mk.y0 - tr.y0
                maske = np.zeros_like(tr.a)
                h, w = mk.a.shape
                maske[max(0, y0):y0 + h, max(0, x0):x0 + w] = mk.a[max(0, -y0):, max(0, -x0):][:maske.shape[0] - max(0, y0), :maske.shape[1] - max(0, x0)]
                tr = Katman(tr.a * maske, tr.x0, tr.y0)
            b, boy = yazi_katmani(sh["baslik"], 900, D.boy, D.bx, D.by, D.gen)
            a = yazi_katmani(sh["alt"], 700, boy * 0.36, D.bx, D.ay, D.gen, harf=0.06)[0] if sh.get("alt") else None
            sahneler.append({"taban": tb, "tarama": tr, "baslik": b, "alt": a})
        gor = gorsel_oku(s, D.R * 1.5, D.R * 1.5)
        self.on[fmt] = {"D": D, "kagit": kagit, "pozlar": pozlar, "sahneler": sahneler, "gorsel": gor}

    def _murekkep(self, k: Katman, poz, dx, dy, ust_y=None) -> Katman:
        kenar, bosluk = poz
        x0, y0, x1, y1 = k.kutu
        H, W = kenar.shape
        sl = (slice(max(0, y0), min(H, y1)), slice(max(0, x0), min(W, x1)))
        a = k.a[sl[0].start - y0:sl[0].stop - y0, sl[1].start - x0:sl[1].stop - x0]
        v = a + (kenar[sl] - 0.5) * 0.55
        a = np.clip((v - 0.5) * 3.2 + 0.5, 0, 1) * (1 - 0.85 * bosluk[sl])
        if ust_y is not None:
            ys = np.arange(sl[0].start, sl[0].stop, dtype=np.float32)[:, None]
            a = a * np.clip((ust_y - ys) / 6.0, 0, 1)
        return Katman(a.astype(np.float32), sl[1].start + dx, sl[0].start + dy)

    def kare(self, t, fmt, W, H):
        self.hazirla(fmt, W, H)
        on = self.on[fmt]
        n = int(t * self.POZ)
        tq = n / self.POZ  # stop-motion: zaman poza yuvarlanır
        i, u, d = zaman.sahne(self.s, tq)
        sh, D = on["sahneler"][i], on["D"]
        poz = on["pozlar"][n % len(on["pozlar"])]
        rr = np.random.default_rng(n)
        dx, dy = (int(v) for v in rr.integers(-1, 2, 2))
        img = on["kagit"].copy()
        merdane = in_out(prog(u, 0.0, 0.75))
        ust_y = -0.08 * H + merdane * 1.16 * H
        boya(img, self._murekkep(sh["taban"], poz, dx, dy, ust_y), self.murekkep)
        kazi = prog(u, 0.55, 0.6)
        if kazi > 0:
            tr = sh["tarama"]
            kes = tr.a * (np.arange(tr.a.shape[1])[None, :] < kazi * tr.a.shape[1])
            boya(img, self._murekkep(Katman(kes, tr.x0, tr.y0), poz, dx, dy), self.murekkep)
        if _gorsel_sahnesi(self.s, i) and on["gorsel"] is not None:
            p = prog(u, 0.6, 0.25)
            gorsel_bas(img, on["gorsel"], D.cx, D.cy, p, 1.0 + 0.08 * (1 - p))
        for k, t0, rnk in ((sh["baslik"], 0.85, self.murekkep), (sh["alt"], 1.05, self.vurgu)):
            if k is None or u < t0:
                continue
            bas = 1.0 + 0.10 * max(0.0, 1 - (u - t0) * self.POZ / 2.5)
            kk = k.olcekli(bas, (k.kutu[0] + k.kutu[2]) / 2, (k.kutu[1] + k.kutu[3]) / 2)
            boya(img, self._murekkep(kk, poz, dx, dy), rnk)
        if u < 0.80:  # merdane
            yr = ust_y
            h = 0.035 * H
            ys = np.arange(H, dtype=np.float32)[:, None]
            band = np.clip(1 - np.abs(ys - yr) / h, 0, 1)
            golge = np.clip(1 - np.abs(ys - yr - h * 1.2) / (h * 0.8), 0, 1) * 0.25
            img *= (1 - golge)[..., None]
            gov = np.clip(band * 3, 0, 1)
            parlak = 1 + 0.6 * np.clip(1 - np.abs(ys - (yr - h * 0.35)) / (h * 0.18), 0, 1)
            img[:] = img * (1 - gov[..., None]) + (self.murekkep * 1.6 * parlak[..., None]) * gov[..., None]
        if i < len(on["sahneler"]) - 1 and d - u < zaman.GECIS:  # yaprak yukarı çekilir, altında temiz kâğıt
            p = in_cubic(prog(u, d - zaman.GECIS, zaman.GECIS))
            k = int(p * H)
            if k > 0:
                yeni = on["kagit"].copy()
                yeni[:H - k] = img[k:]
                golge = np.clip(1 - (np.arange(H) - (H - k)) / (0.03 * H), 0, 1)[:, None] * (np.arange(H)[:, None] >= H - k) * 0.35
                yeni *= (1 - golge)[..., None]
                img = yeni
        return img


# ---------- 3 · çini / girih ----------
class Cini:
    """Çini: sekiz köşeli yıldız karoları ortadan dışa simetrik dizilir, sırlanır; madalyonda motif, panoda yazı."""
    def __init__(self, s):
        self.s = s
        r = s.get("renkler", {})
        self.krem = renk(r.get("zemin", "#F6F3EC"))
        self.kobalt = renk(r.get("kobalt", "#183A8C"))
        self.turkuaz = renk(r.get("turkuaz", "#2896A0"))
        self.mercan = renk(r.get("mercan", "#BE2828"))
        self.on = {}

    @staticmethod
    def _yildiz(cx, cy, r, T):
        p = []
        for k in range(16):
            rr = r if k % 2 == 0 else r * .62
            a = k / 16 * math.tau + math.pi / 8
            p.append(T(cx + rr * math.cos(a), cy + rr * math.sin(a)))
        return p

    def _karo(self, d, T, cx, cy, s_, k, sir, renkler):
        kob, kre, tur, mer = renkler
        if k <= 0:
            return
        d.polygon(self._yildiz(cx, cy, s_ * .48 * k, T), fill=kob)
        d.polygon(self._yildiz(cx, cy, s_ * .31 * k, T), fill=kre)
        if sir > 0:
            d.polygon(self._yildiz(cx, cy, s_ * .17 * k * sir, T), fill=tur)
            r = s_ * .045 * sir
            for ox, oy in ((.5, .5), (-.5, .5), (.5, -.5), (-.5, -.5)):
                d.ellipse([*T(cx + ox * s_ - r, cy + oy * s_ - r), *T(cx + ox * s_ + r, cy + oy * s_ + r)], fill=mer)
            r = s_ * .05 * sir
            for ox, oy in ((.5, 0), (-.5, 0), (0, .5), (0, -.5)):
                x, y = cx + ox * s_, cy + oy * s_
                d.polygon([T(x - r, y), T(x, y - r), T(x + r, y), T(x, y + r)], fill=tur)

    def _desen(self, W, H, s_, ox, oy, zamanla=None):
        """2 kat çözünürlükte desen; zamanla(i, j) -> (ölçek, sır) giriş animasyonu için."""
        ss = 2
        im = Image.new("RGB", (W * ss, H * ss), tuple(int(v) for v in self.krem))
        d = ImageDraw.Draw(im)
        T = lambda x, y: (x * ss, y * ss)  # noqa: E731
        renkler = tuple(tuple(int(v) for v in c) for c in (self.kobalt, self.krem, self.turkuaz, self.mercan))
        nx, ny = int(W / s_) + 3, int(H / s_) + 3
        for j in range(-1, ny):
            for i in range(-1, nx):
                cx, cy = i * s_ + s_ / 2 - ox, j * s_ + s_ / 2 - oy
                k, sir = zamanla(cx, cy) if zamanla else (1.0, 1.0)
                self._karo(d, T, cx, cy, s_, k, sir, renkler)
        return np.asarray(im.reduce(ss), np.float32)

    def hazirla(self, fmt, W, H):
        if fmt in self.on:
            return
        s, D = self.s, Duzen(self.s, fmt, W, H, olcek_r=0.92)
        s_ = 0.25 * min(W, H)
        sahneler = []
        for i, sh in enumerate(s["sahneler"]):
            cx, cy, R = D.cx, D.cy, D.R
            m = R * 1.2
            kutu = (cx - m, cy - m, cx + m, cy + m)
            madalyon = katman(kutu, lambda d, T, ss: d.ellipse([*T(cx - R * 1.14, cy - R * 1.14), *T(cx + R * 1.14, cy + R * 1.14)], fill=255))
            halka = katman(kutu, lambda d, T, ss: (d.ellipse([*T(cx - R * 1.10, cy - R * 1.10), *T(cx + R * 1.10, cy + R * 1.10)], outline=255, width=int(R * .045 * ss)),
                                                  d.ellipse([*T(cx - R * 1.0, cy - R * 1.0), *T(cx + R * 1.0, cy + R * 1.0)], outline=255, width=int(R * .012 * ss))))
            ad = None if _gorsel_sahnesi(s, i) else sh.get("motif")
            dolgu = motif_katmani(ad, cx, cy, R * 0.70) if ad else None

            def kontur(d, T, ss, ad=ad):
                for p, _ in motif_noktalar(ad, cx, cy, R * 0.70):
                    d.line([T(x, y) for x, y in p + [p[0]]], fill=255, width=int(R * .035 * ss), joint="curve")
            kon = katman(kutu, kontur) if ad else None
            b, boy = yazi_katmani(sh["baslik"], 900, D.boy, D.bx, D.by, D.gen * 0.82)
            a = yazi_katmani(sh["alt"], 700, boy * 0.36, D.bx, D.ay, D.gen * 0.82, harf=0.04)[0] if sh.get("alt") else None
            x0 = min(b.kutu[0], a.kutu[0] if a else 1e9) - boy * 0.35
            x1 = max(b.kutu[2], a.kutu[2] if a else -1e9) + boy * 0.35
            y0, y1 = b.kutu[1] - boy * 0.05, (a.kutu[3] if a else b.kutu[3]) + boy * 0.12
            pano = katman((x0, y0, x1, y1), lambda d, T, ss: d.rectangle([*T(x0, y0), *T(x1, y1)], fill=255))
            cer = katman((x0, y0, x1, y1), lambda d, T, ss: d.rectangle([*T(x0 + 4, y0 + 4), *T(x1 - 4, y1 - 4)], outline=255, width=int(7 * ss)))
            ince = katman((x0, y0, x1, y1), lambda d, T, ss: d.rectangle([*T(x0 + 17, y0 + 17), *T(x1 - 17, y1 - 17)], outline=255, width=int(2 * ss)))
            sahneler.append({"madalyon": madalyon, "halka": halka, "dolgu": dolgu, "kontur": kon,
                             "baslik": b, "alt": a, "pano": pano, "cerceve": cer, "ince": ince})
        gor = gorsel_oku(s, D.R * 1.45, D.R * 1.45)
        self.on[fmt] = {"D": D, "s": s_, "sahneler": sahneler, "gorsel": gor, "durgun": {}}

    def _kayma(self, t):
        return 14.0 * t, 8.0 * t

    def kare(self, t, fmt, W, H):
        self.hazirla(fmt, W, H)
        on = self.on[fmt]
        D, s_ = on["D"], on["s"]
        i, u, d = zaman.sahne(self.s, t)
        ox, oy = self._kayma(t)
        giris = 1.5
        if t < giris:
            rmax = math.hypot(W, H) / 2

            def zamanla(cx, cy):
                t0 = math.hypot(cx - D.cx, cy - D.cy) / rmax * 0.95
                return out_back(prog(t, t0, 0.32)), out_cubic(prog(t, t0 + 0.18, 0.25))
            img = self._desen(W, H, s_, ox, oy, zamanla)
        else:
            img = self._desen(W, H, s_, ox, oy)
        sh = on["sahneler"][i]
        ilk = 1.05 if i == 0 else 0.0
        son = i == len(on["sahneler"]) - 1
        cik = 1.0 if son else 1 - in_cubic(prog(u, d - zaman.GECIS, zaman.GECIS))
        p = out_back(prog(u, ilk, 0.45)) * cik
        if p > 0.01:
            for k, rnk in ((sh["madalyon"], self.krem), (sh["halka"], self.kobalt)):
                boya(img, k.olcekli(p, D.cx, D.cy), rnk)
            sir = out_cubic(prog(u, ilk + 0.25, 0.5))
            if sh["dolgu"] is not None:
                dg = sh["dolgu"].olcekli(p, D.cx, D.cy)
                ys = np.arange(dg.a.shape[0], dtype=np.float32)[:, None]
                on_ = (1 - sir) * dg.a.shape[0]
                boya(img, Katman(dg.a * np.clip((ys - on_) / 8.0, 0, 1), dg.x0, dg.y0), self.turkuaz)
                boya(img, sh["kontur"].olcekli(p, D.cx, D.cy), self.kobalt)
            if _gorsel_sahnesi(self.s, i) and on["gorsel"] is not None:
                gorsel_bas(img, on["gorsel"], D.cx, D.cy, sir * cik, p)
        y0 = ilk + 0.2
        boya(img, sh["pano"], self.krem, out_cubic(prog(u, y0, 0.3)) * cik)
        boya(img, sh["cerceve"], self.kobalt, out_cubic(prog(u, y0, 0.3)) * cik)
        boya(img, sh["ince"], self.mercan, out_cubic(prog(u, y0 + 0.1, 0.3)) * cik)
        boya(img, sh["baslik"], self.kobalt, out_cubic(prog(u, y0 + 0.15, 0.35)) * cik)
        boya(img, sh["alt"], self.mercan, out_cubic(prog(u, y0 + 0.35, 0.35)) * cik)
        return img


# ---------- 4 · teknik çizim ----------
class TeknikCizim:
    """Mavi çizim kâğıdı: kurulum çizgileri, motif konturu cetvelle çizilir, ölçüler açılır, yazı daktiloyla gelir;
    sahne değişince kâğıt sola kayar."""
    def __init__(self, s):
        self.s = s
        r = s.get("renkler", {})
        self.zemin = renk(r.get("zemin", "#16407F"))
        self.ince = renk(r.get("izgara", "#24528F"))
        self.kalin = renk(r.get("izgara_kalin", "#3463A6"))
        self.cizgi = renk(r.get("cizgi", "#E1ECFF"))
        self.on = {}

    def hazirla(self, fmt, W, H):
        if fmt in self.on:
            return
        s, D = self.s, Duzen(self.s, fmt, W, H, olcek_r=0.86)
        adim = round(0.025 * min(W, H))
        zem = np.empty((H, 2 * W, 3), np.float32)
        zem[:] = self.zemin
        zem += (puruz(2 * W, H, 0.01 * W, 51)[..., None] - 0.5) * 6
        for x in range(0, 2 * W, adim):
            zem[:, x] = self.kalin if (x // adim) % 5 == 0 else self.ince
        for y in range(0, H, adim):
            zem[y, :] = self.kalin if (y // adim) % 5 == 0 else self.ince
        lw = 0.0055 * min(W, H)
        sahneler = []
        for i, sh in enumerate(s["sahneler"]):
            cx, cy, R = D.cx, D.cy, D.R
            ad = None if _gorsel_sahnesi(s, i) else sh.get("motif")
            yollar = [[(cx + x * R, cy + y * R) for x, y in p] for p in motifler.konturlar(ad)] if ad else []
            uz = [sum(math.dist(a, b) for a, b in zip(p, p[1:])) for p in yollar]
            olcu = sh.get("olcu") or [120, 120]
            yazilar = []
            for metin, agirlik, boy, yy, harf in ((sh["baslik"], 900, D.boy, D.by, 0.02), (sh.get("alt"), 500, D.boy * 0.36, D.ay, 0.08)):
                if not metin:
                    yazilar.append(None); continue
                tam, boy_ = yazi_katmani(metin, agirlik, boy, D.bx, yy, D.gen, harf=harf)
                f = _font(agirlik, boy_)
                gen = f.getlength(metin) + harf * boy_ * (len(metin) - 1)
                sinirlar, x = [], D.bx - gen / 2
                for c in metin:
                    x += f.getlength(c) + harf * boy_
                    sinirlar.append(x)
                yazilar.append({"k": tam, "sinir": sinirlar, "boy": boy_, "y": yy})
            sahneler.append({"yollar": yollar, "uz": uz, "olcu": olcu, "yazi": yazilar})
        no_boy = 0.022 * min(W, H)
        self.on[fmt] = {"D": D, "zemin": zem, "adim": adim, "lw": lw, "sahneler": sahneler, "no_boy": no_boy,
                        "gorsel": gorsel_oku(s, D.R * 1.6, D.R * 1.6)}

    def _cizim(self, on, sh, u, i, W, H) -> Katman:
        D, lw = on["D"], on["lw"]
        cx, cy, R = D.cx, D.cy, D.R
        m = R * 1.5
        y_ol = cy + R * 1.22
        x_ol = cx + R * 1.22
        kur = out_cubic(prog(u, 0.0, 0.45))
        cizgi = in_out(prog(u, 0.30, 1.0))
        ol = out_cubic(prog(u, 1.0, 0.45))
        olcu_birim = self.s.get("birim", "mm")

        def ciz(d, T, ss):
            w = max(1, int(lw * ss))
            ince = max(1, int(lw * 0.45 * ss))
            # kurulum: kesikli eksenler ve çember
            for k in range(0, int(26 * kur)):
                a0 = k / 26 * 360
                d.arc([*T(cx - R * 1.08, cy - R * 1.08), *T(cx + R * 1.08, cy + R * 1.08)], a0, a0 + 8, fill=150, width=ince)
            L = R * 1.28 * kur
            for k in np.arange(-L, L, R * 0.09):
                d.line([T(cx + k, cy), T(cx + min(k + R * 0.05, L), cy)], fill=150, width=ince)
                d.line([T(cx, cy + k), T(cx, cy + min(k + R * 0.05, L))], fill=150, width=ince)
            # motif konturu cetvelle
            kalan = cizgi * sum(sh["uz"])
            for p, uz in zip(sh["yollar"], sh["uz"]):
                if kalan <= 0:
                    break
                pts, gidilen = [p[0]], 0.0
                for a, b in zip(p, p[1:]):
                    seg = math.dist(a, b)
                    if gidilen + seg >= kalan:
                        r = (kalan - gidilen) / max(seg, 1e-6)
                        pts.append((a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r)); break
                    pts.append(b); gidilen += seg
                d.line([T(*q) for q in pts], fill=255, width=w, joint="curve")
                kalan -= uz
            # ölçü çizgileri
            if ol > 0:
                yar = R * ol
                for (x1, y1, x2, y2) in ((cx - yar, y_ol, cx + yar, y_ol), (x_ol, cy - yar, x_ol, cy + yar)):
                    d.line([T(x1, y1), T(x2, y2)], fill=230, width=ince)
                    for (x, y) in ((x1, y1), (x2, y2)):
                        if y1 == y2:
                            d.line([T(x, y - R * 0.06), T(x, y + R * 0.06)], fill=230, width=ince)
                        else:
                            d.line([T(x - R * 0.06, y), T(x + R * 0.06, y)], fill=230, width=ince)
                for x in (cx - R, cx + R):
                    d.line([T(x, cy + R * 1.04), T(x, cy + R * 1.04 + (y_ol - cy - R * 0.98) * ol)], fill=150, width=ince)
                f = _font(500, R * 0.12 * ss)
                v1, v2 = (int(round(v * ol)) for v in sh["olcu"][:2])
                d.text(T(cx, y_ol - R * 0.10), f"{v1} {olcu_birim}", font=f, anchor="mb", fill=230)
                d.text(T(x_ol + R * 0.08, cy), f"{v2}", font=f, anchor="lm", fill=230)
        return katman((cx - m, cy - m, cx + m * 1.15, cy + m), ciz, ss=2)

    def kare(self, t, fmt, W, H):
        self.hazirla(fmt, W, H)
        on = self.on[fmt]
        D = on["D"]
        i, u, d = zaman.sahne(self.s, t)
        sh = on["sahneler"][i]
        kay = 0
        if i < len(on["sahneler"]) - 1 and d - u < zaman.GECIS:
            kay = int(in_out(prog(u, d - zaman.GECIS, zaman.GECIS)) * W)
        x0 = (kay + i * W) % (on["adim"] * 5 * max(1, W // (on["adim"] * 5)))
        x0 = min(x0, W)
        img = on["zemin"][:, x0:x0 + W].copy()
        if img.shape[1] < W:
            img = np.concatenate([img, on["zemin"][:, :W - img.shape[1]]], axis=1)
        boya(img, self._cizim(on, sh, u, i, W, H).kaydir(-kay, 0), self.cizgi)
        if _gorsel_sahnesi(self.s, i) and on["gorsel"] is not None:
            p = out_cubic(prog(u, 1.1, 0.5))
            gorsel_bas(img, on["gorsel"], D.cx - kay, D.cy, p)
        for k, (yz, t0) in enumerate(zip(sh["yazi"], (0.5, 0.5 + len(sh["yazi"][0]["sinir"]) / 22 + 0.1))):
            if yz is None or u < t0:
                continue
            n = min(len(yz["sinir"]), int((u - t0) * 22) + 1)
            kk = yz["k"]
            sag = yz["sinir"][n - 1] - kk.x0 + 2
            kes = kk.a.copy()
            kes[:, int(max(0, sag)):] = 0
            boya(img, Katman(kes, kk.x0 - kay, kk.y0), self.cizgi)
            if n < len(yz["sinir"]) and int(u * 8) % 2 == 0:  # yazarken alt çizgi imleç
                bx = yz["sinir"][n - 1] + yz["boy"] * 0.06 - kay
                y1 = yz["y"] + yz["boy"] * 0.36
                imlec = katman((bx, y1, bx + yz["boy"] * 0.5, y1 + yz["boy"] * 0.08),
                               lambda dd, T, ss, bx=bx, y1=y1, b=yz["boy"]: dd.rectangle([*T(bx, y1), *T(bx + b * 0.5, y1 + b * 0.08)], fill=255))
                boya(img, imlec, self.cizgi, 0.9)
        self._antet(img, on, i, W, H, kay)
        return img

    def _antet(self, img, on, i, W, H, kay):
        b = on["no_boy"]
        ust, _ = zaman.GUVENLI[on["D"].fmt]
        x0, y0 = 0.07 * W - kay, max(ust * H + b * 0.6, 0.04 * H)
        metin = f"ÇİZİM NO. {i + 1:02d}"
        imza = self.s.get("imza")
        f = _font(600, b)
        gen = max(f.getlength(metin), f.getlength(imza) if imza else 0) + b * 1.4
        yuk = b * (3.3 if imza else 1.9)

        def ciz(d, T, ss):
            d.rectangle([*T(x0, y0), *T(x0 + gen, y0 + yuk)], outline=255, width=max(1, int(1.6 * ss)))
            fs = _font(600, b * ss)
            d.text(T(x0 + b * 0.7, y0 + b * 0.45), metin, font=fs, anchor="lt", fill=255)
            if imza:
                d.line([T(x0, y0 + b * 1.85), T(x0 + gen, y0 + b * 1.85)], fill=255, width=max(1, int(1.2 * ss)))
                d.text(T(x0 + b * 0.7, y0 + b * 2.15), imza, font=_font(500, b * 0.9 * ss), anchor="lt", fill=255)
        boya(img, katman((x0 - 4, y0 - 4, x0 + gen + 4, y0 + yuk + 4), ciz, ss=2), self.cizgi, 0.95)


STILLER = {"vitray": Vitray, "linol": Linol, "cini": Cini, "teknik-cizim": TeknikCizim}

# ---------- kare akışı ----------
_IS: dict = {}


def _kare_bayt(i: int) -> bytes:
    stil, fmt, W, H, fps = _IS["stil"], _IS["fmt"], _IS["W"], _IS["H"], _IS["fps"]
    img = stil.kare(i / fps, fmt, W, H)
    rng = np.random.default_rng(i)
    tane = (rng.random((H, W, 1), np.float32) - rng.random((H, W, 1), np.float32)) * getattr(stil, "TANE", 1.2)
    return np.clip(img + tane + 0.5, 0, 255).astype(np.uint8).tobytes()


def stil_nesnesi(s):
    return STILLER[s["stil"]](s)


def en_yakin_format(W, H) -> str:
    return min(zaman.FORMATLAR, key=lambda f: abs(math.log(zaman.FORMATLAR[f][0] / zaman.FORMATLAR[f][1] / (W / H))))


def video(s, W, H, yol: Path, fmt: str | None = None, isci: int | None = None) -> Path:
    """Sessiz video. `fmt` yerleşimi seçer; verilmezse en yakın en-boy oranı (kurgu.py sahneleri böyle çağırır)."""
    fmt = fmt or en_yakin_format(W, H)
    stil = stil_nesnesi(s)
    stil.hazirla(fmt, W, H)  # ağır katmanlar bir kez; çatallanan süreçler devralır
    _IS.update(stil=stil, fmt=fmt, W=W, H=H, fps=s["fps"])
    n = int(round(s["sure"] * s["fps"]))
    yol.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(s["fps"]), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-tune", "grain",
                           "-pix_fmt", "yuv420p", str(yol)], stdin=subprocess.PIPE)
    isci = isci or max(1, min(4, os.cpu_count() or 1))
    if isci > 1:
        with mp.get_context("fork").Pool(isci) as havuz:
            for b in havuz.imap(_kare_bayt, range(n), chunksize=2):
                ff.stdin.write(b)
    else:
        for k in range(n):
            ff.stdin.write(_kare_bayt(k))
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError(f"ffmpeg kodlaması başarısız: {yol}")
    return yol


def tek_kare(s, fmt, W, H, t) -> Image.Image:
    stil = stil_nesnesi(s)
    img = stil.kare(t, fmt, W, H)
    return Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8))


def kareler(s, fmt, W, H, anlar, klasor: Path) -> list[Path]:
    klasor.mkdir(parents=True, exist_ok=True)
    stil = stil_nesnesi(s)
    out = []
    for t in anlar:
        p = klasor / f"{s.get('kimlik', 'desen')}-{fmt}-{t:05.2f}.png"
        Image.fromarray(np.clip(stil.kare(t, fmt, W, H) + 0.5, 0, 255).astype(np.uint8)).save(p)
        out.append(p)
    return out
