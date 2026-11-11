"""Zarif çizgi: çizgisel karakterin klas sürümü (2026-11-11, Atilla: "animasyon, görsel ve ses daha klas").

Çizgiselden farkları:
- Kâğıt zemin (sıcak krem + çok ince sabit gren; gradyan yok, bantlanmaz), sıcak mürekkep rengi (saf siyah değil).
- Fırça çizgisi: kollar ve bacaklar eklemden geçen eğri, uçlara doğru incelen mürekkep (dirsek ve diz kırılmaz).
- Yuvarlak kazak gövde, düz iki ton gölge, yanak allığı, rüzgârda gecikmeli dalgalanan atkı (ikincil hareket).
- Sahne dekoru (`dekor`): pencere ve doğan güneş, yatak, kapı (açılır, yere ışık düşer), dağ, taş, yol, bitki,
  masa, telefon, kitap, büyük güneş. Çizgiler elle çiziliyormuş gibi belirir, dolgular sonra gelir.
- Yavaş kamera: sahnenin `kamera`sı (`yakin`, `genis`, `normal`) yumuşak geçişle; sahne içinde hafif yaklaşma.
- Başlık yazısı serif (DM Serif Display, SIL OFL; ilk kullanımda indirilir, yoksa Inter).
Ses tarafı `sentez.py`'de: piyano + yaylı pad, gürültü tabanlı efekt yok (hışırtı, shaker, whoosh kullanılmaz).
"""

from __future__ import annotations

import math
import urllib.request
from pathlib import Path

import numpy as np
import skia

import senaryo
from cizim import clamp, out_cubic, prog, renk
from gorunumler import cizgisel

FONT_ONBELLEK = Path.home() / ".cache" / "studyo" / "fonts"
FONT_DOSYA = "DMSerifDisplay-Regular.ttf"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/dmserifdisplay/DMSerifDisplay-Regular.ttf"

DEKORLAR = ("pencere", "yatak", "kapi", "dag", "tas", "yol", "bitki", "masa", "telefon", "kitap", "gunes")
KAMERALAR = {"normal": 1.0, "yakin": 1.10, "genis": 0.94}


def serif_font() -> str | None:
    yol = FONT_ONBELLEK / FONT_DOSYA
    if not yol.exists():
        try:
            FONT_ONBELLEK.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(FONT_URL, yol)
        except OSError:
            return None
    return str(yol)


def _egri(a, b, c, n=16):
    """a'dan c'ye, b'den GEÇEN ikinci derece eğri üzerinde n nokta."""
    kx, ky = 2 * b[0] - (a[0] + c[0]) / 2, 2 * b[1] - (a[1] + c[1]) / 2
    out = []
    for i in range(n + 1):
        u = i / n
        out.append(((1 - u) ** 2 * a[0] + 2 * (1 - u) * u * kx + u * u * c[0],
                    (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * ky + u * u * c[1]))
    return out


def firca(noktalar, w, uc=0.55) -> skia.Path:
    """Uçlara doğru incelen dolu fırça izi (orta kalın, uçlar `uc` oranında), yuvarlak uçlu."""
    n = len(noktalar)
    sol, sag = [], []
    for i, (x, y) in enumerate(noktalar):
        a = noktalar[max(0, i - 1)]; b = noktalar[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        u = i / (n - 1)
        r = w / 2 * (uc + (1 - uc) * math.sin(math.pi * u) ** 0.6)
        sol.append((x + nx * r, y + ny * r)); sag.append((x - nx * r, y - ny * r))
    p = skia.Path()
    p.moveTo(*sol[0])
    for q in sol[1:]:
        p.lineTo(*q)
    for q in reversed(sag):
        p.lineTo(*q)
    p.close()
    r0 = w / 2 * uc
    p.addCircle(noktalar[0][0], noktalar[0][1], r0)
    p.addCircle(noktalar[-1][0], noktalar[-1][1], r0)
    return p


class Gorunum(cizgisel.Gorunum):
    def __init__(self, s: dict, c):
        super().__init__(s, c)
        pal = s["palet"]
        self.kagit = renk(pal["zemin"])
        self.golge = renk(pal["golge"])
        self.ikincil = renk(pal["ikincil"])
        self.allik = renk(pal["vurgu"], 0.28)
        self.atki = renk(self.k.get("atki", pal["vurgu"]))
        self.ten = renk(self.k.get("ten", pal.get("ten", "#F7E2CF")))
        self.kalin = 0.0095 * c.boy
        f = serif_font()
        if f:
            c.yazi_tipi = skia.Typeface.MakeFromFile(f)
        self._zemin_resmi = None

    # ---------- kamera (cizim.Cizici.kare çağırır) ----------
    def kamera(self, t: float) -> tuple[float, float, float]:
        """(ölçek, odak x, odak y) — odak kadraj oranı. Sahne değişince 0,9 sn'de yumuşak geçiş, içinde hafif yaklaşma."""
        sh_ = self.s["sahneler"]
        hedef = [KAMERALAR.get(sh.get("kamera", "normal"), 1.0) for sh in sh_]
        z = hedef[0]
        for i, sh in enumerate(sh_[1:], 1):
            p = out_cubic(prog(t, sh["bas"], 0.9)) if t >= sh["bas"] else 0.0
            z = z + (hedef[i] - z) * (p * p * (3 - 2 * p) if p < 1 else 1.0)
        sh = senaryo.sahne_at(self.s, t)
        ic = prog(t, sh["bas"], max(0.5, sh["_son"] - sh["bas"]))
        z *= 1.0 + 0.025 * ic
        d = self.c.d
        return z, d["cx"], d["ayak"]   # ayak çizgisi sabit kalır, yazıyla çakışmaz

    # ---------- zemin ----------
    def zemin(self, cv, t, g, ekr):
        W, H = self.c.W, self.c.H
        if self._zemin_resmi is None:
            rng = np.random.default_rng(5)
            gren = rng.normal(0, 1, (H // 2, W // 2))
            gren = np.repeat(np.repeat(gren, 2, 0), 2, 1)[:H, :W]
            taban = np.array([skia.ColorGetR(self.kagit), skia.ColorGetG(self.kagit), skia.ColorGetB(self.kagit)], float)
            rgb = np.clip(taban[None, None, :] + gren[..., None] * 2.2, 0, 255).astype(np.uint8)
            rgba = np.dstack([rgb, np.full((H, W), 255, np.uint8)])
            self._zemin_resmi = skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)
        # kamera dışına taşan kenar boşluğu için önce düz renk
        cv.clear(self.kagit)
        cv.drawImage(self._zemin_resmi, 0, 0)
        ay = self.c.d["ayak"] * H
        # ufuk/zemin çizgisi: kadrajı aşan, çok hafif dalgalı tek mürekkep çizgisi
        p = skia.Path(); p.moveTo(-0.2 * W, ay)
        for i in range(1, 25):
            x = -0.2 * W + i * 1.4 * W / 24
            p.lineTo(x, ay + math.sin(i * 1.7) * 0.0012 * H)
        k = self._kalem(self.kalin * 0.7); k.setAlphaf(0.85)
        cv.drawPath(p, k)
        for d in self._aktif_dekor(t, arka=True):
            self._dekor(cv, d, t)
        # ayak gölgesi
        sx, sy = ekr(((g.ayak["sol"][0] + g.ayak["sag"][0]) / 2, 0.0))
        z = max(0.0, min(g.ayak["sol"][1], g.ayak["sag"][1]))
        gol = skia.Paint(AntiAlias=True, Color=self.golge); gol.setAlphaf(0.75 * (1 - min(1.0, z * 8)))
        cv.drawOval(skia.Rect.MakeXYWH(sx - 0.17 * self.c.boy, ay - 0.012 * self.c.boy, 0.34 * self.c.boy, 0.024 * self.c.boy), gol)

    def on_plan(self, cv, t):
        """Karakterin önünde kalan dekor (masa, telefon, kitap, taş)."""
        for d in self._aktif_dekor(t, arka=False):
            self._dekor(cv, d, t)

    def _aktif_dekor(self, t, arka: bool):
        on = {"masa", "telefon", "kitap", "tas"}
        hepsi = []
        for d in self.s.get("dekor", []):
            hepsi.append((d, 0.0, self.s["sure"]))
        for sh in self.s["sahneler"]:
            for d in sh.get("dekor", []):
                hepsi.append((d, sh["bas"], sh["_son"]))
        out = []
        for d, bas, son in hepsi:
            if (d["tur"] in on) == arka:
                continue
            t0 = d.get("t", bas)
            son = d.get("son", son)
            if t < t0 or t >= son + 0.01:
                continue
            cik = 1 - prog(t, son - 0.3, 0.3) if son < self.s["sure"] else 1.0
            out.append({**d, "_t0": t0, "_bas": bas, "_son": son, "_alfa": cik})
        return out

    # ---------- dekor ----------
    def _dekor(self, cv, d, t):
        W, H, B = self.c.W, self.c.H, self.c.boy
        ay = self.c.d["ayak"] * H
        x = d.get("x", 0.5) * W
        y = d["y"] * H if "y" in d else ay
        o = d.get("olcek", 1.0) * B
        ciz = out_cubic(prog(t, d["_t0"], d.get("cizim_sn", 0.9)))       # çizgi belirme
        dol = prog(t, d["_t0"] + d.get("cizim_sn", 0.9) * 0.6, 0.4)      # dolgu sonra
        ilerle = prog(t, d["_t0"], max(0.5, d["_son"] - d["_t0"]))        # sahne boyunca (güneş doğar, kapı açılır)
        a = d["_alfa"]
        cizgiler, dolgular = getattr(self, "_d_" + d["tur"])(x, y, o, ilerle, d)
        for yol, renk_, alfa in dolgular:
            b = skia.Paint(AntiAlias=True, Color=renk_); b.setAlphaf(alfa * dol * a)
            if b.getAlphaf() > 0.003:
                cv.drawPath(yol, b)
        self._ciz_belir(cv, cizgiler, ciz, a)

    def _ciz_belir(self, cv, yollar, p, alfa):
        """Yolları toplam uzunluğun p oranı kadar çizer (elle çizilme etkisi)."""
        if p <= 0 or alfa <= 0:
            return
        olc = [skia.PathMeasure(y, False).getLength() for y in yollar]
        kalan = sum(olc) * p
        k = self._kalem(self.kalin * 0.72); k.setAlphaf(alfa)
        for y, L in zip(yollar, olc):
            if kalan <= 0:
                break
            if kalan >= L:
                cv.drawPath(y, k)
            else:
                parca = skia.Path()
                skia.PathMeasure(y, False).getSegment(0, kalan, parca, True)
                cv.drawPath(parca, k)
            kalan -= L

    @staticmethod
    def _dik(x, y, w, h, r=0.0):
        p = skia.Path()
        if r:
            p.addRoundRect(skia.Rect.MakeXYWH(x, y, w, h), r, r)
        else:
            p.addRect(skia.Rect.MakeXYWH(x, y, w, h))
        return p

    @staticmethod
    def _cizgi_yol(*n):
        p = skia.Path(); p.moveTo(*n[0])
        for q in n[1:]:
            p.lineTo(*q)
        return p

    def _d_pencere(self, x, y0, o, ilerle, d):
        w, h = 0.46 * o, 0.56 * o
        y = y0 - 0.80 * o if "y" not in d else y0 - h
        cer = self._dik(x - w / 2, y, w, h, 0.02 * o)
        icx, icy = x, y + h * (0.95 - 0.55 * out_cubic(ilerle))          # güneş pencerede yükselir
        gunes = skia.Path(); gunes.addCircle(icx, icy, 0.085 * o)
        gunes = skia.Op(gunes, cer, skia.PathOp.kIntersect_PathOp) or gunes
        hale = skia.Path(); hale.addCircle(icx, icy, 0.15 * o)
        hale = skia.Op(hale, cer, skia.PathOp.kIntersect_PathOp) or hale
        dolgu = [(cer, self.vurgu, 0.16 + 0.12 * ilerle), (hale, self.vurgu, 0.30), (gunes, self.vurgu, 1.0)]
        cizgi = [cer, self._cizgi_yol((x, y), (x, y + h)), self._cizgi_yol((x - w / 2, y + h * 0.48), (x + w / 2, y + h * 0.48)),
                 self._cizgi_yol((x - w / 2 - 0.04 * o, y + h + 0.02 * o), (x + w / 2 + 0.04 * o, y + h + 0.02 * o))]
        # perde: iki yanda yumuşak dalgalı kenar
        for i in (-1, 1):
            px = x + i * (w / 2 + 0.01 * o)
            p = skia.Path(); p.moveTo(px, y - 0.03 * o)
            p.cubicTo(px - i * 0.06 * o, y + h * 0.35, px + i * 0.03 * o, y + h * 0.7, px - i * 0.05 * o, y + h + 0.06 * o)
            p.lineTo(px + i * 0.05 * o, y + h + 0.06 * o); p.lineTo(px + i * 0.05 * o, y - 0.03 * o); p.close()
            dolgu.append((p, self.ikincil, 0.55)); cizgi.append(p)
        return cizgi, dolgu

    def _d_yatak(self, x, y, o, ilerle, d):
        w = 0.95 * o
        bas = self._dik(x - w / 2, y - 0.42 * o, 0.07 * o, 0.42 * o, 0.03 * o)
        sil = self._dik(x - w / 2 + 0.05 * o, y - 0.22 * o, w - 0.05 * o, 0.12 * o, 0.03 * o)
        yas = self._dik(x - w / 2 + 0.09 * o, y - 0.29 * o, 0.2 * o, 0.075 * o, 0.035 * o)
        ort = skia.Path(); ort.moveTo(x - w / 2 + 0.33 * o, y - 0.23 * o)
        ort.cubicTo(x - 0.05 * o, y - 0.30 * o, x + 0.2 * o, y - 0.22 * o, x + w / 2, y - 0.24 * o)
        ort.lineTo(x + w / 2 + 0.01 * o, y - 0.06 * o); ort.lineTo(x - w / 2 + 0.30 * o, y - 0.08 * o); ort.close()
        bac = [self._cizgi_yol((x - w / 2 + 0.08 * o, y - 0.1 * o), (x - w / 2 + 0.08 * o, y)),
               self._cizgi_yol((x + w / 2 - 0.04 * o, y - 0.1 * o), (x + w / 2 - 0.04 * o, y))]
        return [bas, sil, yas, ort] + bac, [(bas, self.golge, 1.0), (sil, self.bos, 1.0), (yas, self.bos, 1.0), (ort, self.ikincil, 0.85)]

    def _d_kapi(self, x, y, o, ilerle, d):
        w, h = 0.40 * o, 0.86 * o
        ac = out_cubic(clamp(ilerle * 1.6)) if d.get("acil", True) else 0.0
        cer = self._dik(x - w / 2, y - h, w, h)
        isik = skia.Path()   # açılan kapıdan yere düşen ışık (düz, gradyansız)
        yay = 0.55 * o * ac
        isik.moveTo(x - w / 2, y); isik.lineTo(x + w / 2, y)
        isik.lineTo(x + w / 2 + yay * 0.5, y + 0.10 * o * ac); isik.lineTo(x - w / 2 - yay * 0.7, y + 0.10 * o * ac); isik.close()
        kanat_w = w * (1 - 0.82 * ac)
        kanat = skia.Path()
        kanat.moveTo(x - w / 2, y - h); kanat.lineTo(x - w / 2 + kanat_w, y - h - 0.04 * o * ac)
        kanat.lineTo(x - w / 2 + kanat_w, y + 0.02 * o * ac); kanat.lineTo(x - w / 2, y); kanat.close()
        tok = skia.Path(); tok.addCircle(x - w / 2 + kanat_w * 0.85, y - h * 0.48, 0.012 * o)
        dolgu = [(cer, self.vurgu, 0.20 + 0.75 * ac), (isik, self.vurgu, 0.45 * ac), (kanat, self.golge, 1.0)]
        return [cer, kanat, tok], dolgu

    def _d_dag(self, x, y, o, ilerle, d):
        w, h = 1.3 * o, 0.95 * o
        p = skia.Path(); p.moveTo(x - w / 2, y)
        p.cubicTo(x - w * 0.25, y - h * 0.55, x - w * 0.08, y - h, x, y - h)
        p.cubicTo(x + w * 0.08, y - h, x + w * 0.25, y - h * 0.55, x + w / 2, y)
        kar = skia.Path(); kar.moveTo(x - w * 0.12, y - h * 0.78)
        kar.cubicTo(x - w * 0.07, y - h * 0.97, x + w * 0.07, y - h * 0.97, x + w * 0.12, y - h * 0.78)
        kar.lineTo(x + w * 0.05, y - h * 0.72); kar.lineTo(x, y - h * 0.8); kar.lineTo(x - w * 0.05, y - h * 0.72); kar.close()
        dol = skia.Path(p); dol.close()
        return [p, kar], [(dol, self.ikincil, 0.45), (kar, self.bos, 1.0)]

    def _d_tas(self, x, y, o, ilerle, d):
        p = skia.Path(); p.addOval(skia.Rect.MakeXYWH(x - 0.05 * o, y - 0.055 * o, 0.1 * o, 0.06 * o))
        return [p], [(p, self.golge, 1.0)]

    def _d_yol(self, x, y, o, ilerle, d):
        H = self.c.H
        ufuk = y - 0.02 * o
        sol = self._cizgi_yol((x - 0.55 * o, H * 1.05), (x - 0.02 * o, ufuk))
        sag = self._cizgi_yol((x + 0.55 * o, H * 1.05), (x + 0.02 * o, ufuk))
        dol = skia.Path(); dol.moveTo(x - 0.55 * o, H * 1.05); dol.lineTo(x - 0.02 * o, ufuk); dol.lineTo(x + 0.02 * o, ufuk)
        dol.lineTo(x + 0.55 * o, H * 1.05); dol.close()
        return [sol, sag], [(dol, self.vurgu, 0.22 * (0.4 + 0.6 * ilerle))]

    def _d_bitki(self, x, y, o, ilerle, d):
        sak = self._dik(x - 0.06 * o, y - 0.11 * o, 0.12 * o, 0.11 * o, 0.015 * o)
        cizgi, dolgu = [sak], [(sak, self.vurgu, 0.55)]
        for i, (aci, boy) in enumerate(((-28, 0.22), (-6, 0.30), (18, 0.25), (36, 0.17))):
            r = math.radians(aci); uz = boy * o * (0.85 + 0.15 * math.sin(self.c.t * 1.1 + i))
            ux, uy = x + math.sin(r) * uz, y - 0.11 * o - math.cos(r) * uz
            yp = skia.Path(); yp.moveTo(x, y - 0.11 * o)
            yp.quadTo((x + ux) / 2 - 0.05 * o * math.cos(r), (y - 0.11 * o + uy) / 2, ux, uy)
            yp.quadTo((x + ux) / 2 + 0.05 * o * math.cos(r), (y - 0.11 * o + uy) / 2, x, y - 0.11 * o)
            cizgi.append(yp); dolgu.append((yp, self.ikincil, 1.0))
        return cizgi, dolgu

    def _d_masa(self, x, y, o, ilerle, d):
        ust = self._dik(x - 0.2 * o, y - 0.30 * o, 0.4 * o, 0.03 * o, 0.01 * o)
        return [ust, self._cizgi_yol((x - 0.16 * o, y - 0.27 * o), (x - 0.17 * o, y)),
                self._cizgi_yol((x + 0.16 * o, y - 0.27 * o), (x + 0.17 * o, y))], [(ust, self.golge, 1.0)]

    def _d_telefon(self, x, y, o, ilerle, d):
        yuk = y - (0.30 * o if d.get("masada", True) else 0.0)
        g = self._dik(x - 0.045 * o, yuk - 0.022 * o, 0.09 * o, 0.022 * o, 0.006 * o)   # masada yüzüstü
        if d.get("ekran"):
            g = self._dik(x - 0.03 * o, yuk - 0.11 * o, 0.06 * o, 0.11 * o, 0.01 * o)
            return [g], [(g, self.cizgi, 1.0), (self._dik(x - 0.022 * o, yuk - 0.1 * o, 0.044 * o, 0.088 * o, 0.006 * o), self.vurgu, 0.9)]
        return [g], [(g, self.cizgi, 0.9)]

    def _d_kitap(self, x, y, o, ilerle, d):
        yuk = y - (0.30 * o if d.get("masada", True) else 0.0)
        p = skia.Path(); p.moveTo(x - 0.09 * o, yuk); p.quadTo(x - 0.045 * o, yuk - 0.035 * o, x, yuk - 0.01 * o)
        p.quadTo(x + 0.045 * o, yuk - 0.035 * o, x + 0.09 * o, yuk); p.lineTo(x, yuk + 0.008 * o); p.close()
        return [p, self._cizgi_yol((x, yuk - 0.01 * o), (x, yuk + 0.008 * o))], [(p, self.bos, 1.0)]

    def _d_gunes(self, x, y0, o, ilerle, d):
        y = (d["y"] * self.c.H if "y" in d else self.c.d["ayak"] * self.c.H - 0.55 * o) + (1 - out_cubic(ilerle)) * 0.12 * o
        R = d.get("yaricap", 0.36) * o
        dolgu = []
        for k, a in ((1.55, 0.10), (1.27, 0.18)):   # iki düz hale halkası (gradyan değil, bantlanmaz)
            p = skia.Path(); p.addCircle(x, y, R * k); dolgu.append((p, self.vurgu, a))
        p = skia.Path(); p.addCircle(x, y, R); dolgu.append((p, self.vurgu, 0.95))
        return [], dolgu

    # ---------- karakter ----------
    def karakter(self, cv, g, y, ekr):
        B = self.c.boy
        w = self.kalin * 1.25
        t = self.c.t
        g_once = senaryo.durum(self.s, max(0.0, t - 0.12))[0]   # ikincil hareket için 0,12 sn önceki beden
        kalem = skia.Paint(AntiAlias=True, Color=self.cizgi)
        # bacaklar: kalça → diz → ayak tek eğri, uçta küçük ayakkabı
        for taraf, isaret in (("sol", -1), ("sag", 1)):
            k, d, a = ekr(g.kalca_eklem[taraf]), ekr(g.diz[taraf]), ekr(g.ayak[taraf])
            cv.drawPath(firca(_egri(k, d, a), w, 0.8), kalem)
            ay = skia.Path(); ay.moveTo(a[0] - isaret * 0.01 * B, a[1] - 0.012 * B)
            ay.quadTo(a[0] + isaret * 0.05 * B, a[1] - 0.02 * B, a[0] + isaret * 0.055 * B, a[1] + 0.003 * B)
            ay.lineTo(a[0] - isaret * 0.012 * B, a[1] + 0.003 * B); ay.close()
            cv.drawPath(ay, kalem)
        # atkının sarkan ucu (gövdenin arkasında): boyundan gecikmeyle sallanır
        bx, by = ekr(g.boyun)
        ox, oy = ekr(g_once.boyun)
        ruz = (bx - ox) * 2.2
        uc = skia.Path()
        x0 = bx - 0.045 * B
        uc.moveTo(x0, by + 0.005 * B)
        dal = math.sin(t * 2.3) * 0.012 * B
        uc.cubicTo(x0 + 0.02 * B - ruz * 0.3, by + 0.06 * B, x0 + 0.03 * B - ruz * 0.7 + dal, by + 0.10 * B,
                   x0 + 0.045 * B - ruz + dal, by + 0.14 * B)
        uc.lineTo(x0 + 0.085 * B - ruz + dal, by + 0.13 * B)
        uc.cubicTo(x0 + 0.06 * B - ruz * 0.7 + dal, by + 0.09 * B, x0 + 0.05 * B - ruz * 0.3, by + 0.05 * B, x0 + 0.05 * B, by)
        uc.close()
        # gövde: yuvarlak kazak (omuzlar yuvarlak, kalçada hafif genişler)
        egim = math.radians(g.govde_aci)
        yuk = (math.sin(egim), math.cos(egim)); sag = (yuk[1], -yuk[0])
        def n(merkez, yari, asagi=0.0):
            return ekr((merkez[0] + sag[0] * yari - yuk[0] * asagi, merkez[1] + sag[1] * yari - yuk[1] * asagi))
        p = skia.Path()
        p.moveTo(*n(g.boyun, -0.03))
        p.cubicTo(*n(g.boyun, -0.08, -0.004), *n(g.boyun, -0.106, 0.0), *n(g.boyun, -0.104, 0.045))
        p.cubicTo(*n(g.kalca, -0.10, -0.12), *n(g.kalca, -0.118, -0.03), *n(g.kalca, -0.112, 0.005))
        p.cubicTo(*n(g.kalca, -0.04, 0.02), *n(g.kalca, 0.04, 0.02), *n(g.kalca, 0.112, 0.005))
        p.cubicTo(*n(g.kalca, 0.118, -0.03), *n(g.kalca, 0.10, -0.12), *n(g.boyun, 0.104, 0.045))
        p.cubicTo(*n(g.boyun, 0.106, 0.0), *n(g.boyun, 0.08, -0.004), *n(g.boyun, 0.03))
        p.close()
        cv.drawPath(p, self._boya(self.dolgu))
        cv.save(); cv.clipPath(p, doAntiAlias=True)        # düz gölge: gövdenin sağ yarısı, tek ton
        gp = skia.Path(p); gp.offset(-0.055 * B, 0.0)
        golge = skia.Paint(AntiAlias=True, Color=self.cizgi); golge.setAlphaf(0.07)
        tum = skia.Path(); tum.addRect(skia.Rect.MakeXYWH(-10, -10, self.c.W + 20, self.c.H + 20))
        cv.drawPath(skia.Op(tum, gp, skia.PathOp.kDifference_PathOp) or gp, golge)
        cv.restore()
        cv.drawPath(p, self._kalem(self.kalin * 0.95))
        # atkı boğaz sargısı
        sar = skia.Path()
        sar.moveTo(*n(g.boyun, -0.062, 0.0)); sar.quadTo(*n(g.boyun, 0.0, -0.03), *n(g.boyun, 0.062, 0.0))
        sar.quadTo(*n(g.boyun, 0.07, 0.018), *n(g.boyun, 0.058, 0.028))
        sar.quadTo(*n(g.boyun, 0.0, 0.0), *n(g.boyun, -0.058, 0.028))
        sar.quadTo(*n(g.boyun, -0.07, 0.018), *n(g.boyun, -0.062, 0.0)); sar.close()
        # kollar: omuz → dirsek → el, gecikmeli eğilme (bükülme yumuşak)
        for taraf in ("sol", "sag"):
            o_, dr, el = ekr(g.omuz[taraf]), ekr(g.dirsek[taraf]), ekr(g.el[taraf])
            eo = ekr(g_once.el[taraf])
            dr = (dr[0] + (eo[0] - el[0]) * 0.12, dr[1] + (eo[1] - el[1]) * 0.12)
            cv.drawPath(firca(_egri(o_, dr, el), w, 0.75), kalem)
            cv.drawCircle(el[0], el[1], w * 1.05, self._boya(self.ten)); cv.drawCircle(el[0], el[1], w * 1.05, self._kalem(self.kalin * 0.6))
        cv.drawPath(uc, self._boya(self.atki)); cv.drawPath(uc, self._kalem(self.kalin * 0.7))
        self._bas(cv, g, y, ekr)
        cv.drawPath(sar, self._boya(self.atki)); cv.drawPath(sar, self._kalem(self.kalin * 0.7))

    def _yuz(self, cv, y, bakis, r):
        # yanak allığı (gülümserken belirginleşir), sonra çizgiselin yüzü
        a = 0.45 + 0.55 * clamp(y.egri)
        b = skia.Paint(AntiAlias=True, Color=self.allik); b.setAlphaf(b.getAlphaf() * a)
        for i in (-1, 1):
            cv.drawOval(skia.Rect.MakeXYWH(i * 0.52 * r - 0.13 * r, 0.16 * r, 0.26 * r, 0.14 * r), b)
        super()._yuz(cv, y, bakis, r)
