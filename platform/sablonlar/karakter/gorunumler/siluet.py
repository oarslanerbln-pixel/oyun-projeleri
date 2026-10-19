"""Gün batımı siluet görünümü: düz renk bantlı gökyüzü (gradyan yok, bantlanma olmaz), batan büyük güneş, koyu tepe
ve tepenin üstünde tek renk siluet karakter; istenirse yanında ikinci bir siluet (eşlikçi) durur.

Yüz çizilmez: ifadeler beden dilinden okunur (poz, baş eğimi, zıplama), ağız senkronu görünmez; bu stil
anlatıcı sesiyle hikâye anlatmak içindir. Yazı tepenin koyu zemininde açık renkle durur.
"""

from __future__ import annotations

import math

import skia

import iskelet
from cizim import out_cubic, prog, renk
from gorunumler import cizgisel

# Yatayda yazı tepenin üstüne iner (sağdaki açık bantlar üstünde okunmaz); diğer formatlarda yazı zaten tepede.
DUZEN = {"16x9": dict(boy=0.56, ayak=0.70, cx=0.34, gez=0.10, yazi=(0.66, 0.845, 0.56, 0.046))}


class Gorunum(cizgisel.Gorunum):
    def __init__(self, s: dict, c):
        super().__init__(s, c)
        pal = s["palet"]
        self.siluet = renk(pal["cizgi"])
        self.sac = self.ten = self.dolgu = self.siluet
        self.bantlar = [renk(x) for x in pal["bantlar"]]
        self.gunes = renk(pal["vurgu"])
        self.kalin = 0.0085 * c.boy
        self._t = 0.0

    # ---------- zemin ----------
    def zemin(self, cv, t, g, ekr):
        self._t = t
        W, H, B, d = self.c.W, self.c.H, self.c.boy, self.c.d
        ufuk = d["ayak"] * H
        bant = ufuk / len(self.bantlar)
        for i, r in enumerate(self.bantlar):   # düz bantlar, ufukta biter
            cv.drawRect(skia.Rect.MakeLTRB(0, round(i * bant), W, round((i + 1) * bant) + 1), self._boya(r))
        # güneş karakterin başlangıç yerinin arkasında; video boyunca yavaşça batar
        gx = d["cx"] * W
        gy = ufuk - 0.60 * B + 0.10 * B * (t / max(1.0, self.s["sure"]))
        cv.drawCircle(gx, gy, 0.27 * B, self._boya(self.gunes))
        self._kuslar(cv, t, W, H, B)
        # tepe: karakterin durduğu yerde ufuk, kenarlara doğru hafifçe iner
        p = skia.Path()
        p.moveTo(0, ufuk + 0.022 * H)
        p.cubicTo(gx - 0.45 * W, ufuk + 0.012 * H, gx - 0.25 * W, ufuk - 0.004 * B, gx, ufuk - 0.004 * B)
        p.cubicTo(gx + 0.25 * W, ufuk - 0.004 * B, gx + 0.45 * W, ufuk + 0.012 * H, W, ufuk + 0.022 * H)
        p.lineTo(W, H); p.lineTo(0, H); p.close()
        cv.drawPath(p, self._boya(self.siluet))
        e = self.k.get("eslik")
        if e:   # eşlikçi karakterin arkasında, tepede
            self._eslik(cv, e, t, g, ekr)

    def _kuslar(self, cv, t, W, H, B):
        k = self._kalem(0.006 * B, self.siluet)
        for i, (y0, hiz, faz) in enumerate(((0.20, 0.035, 0.0), (0.24, 0.028, 0.35), (0.17, 0.030, 0.7))):
            x = ((faz + t * hiz) % 1.3 - 0.15) * W
            y = (y0 + 0.006 * math.sin(t * 1.3 + i)) * H
            kanat = 0.022 * B * (0.6 + 0.4 * math.sin(t * 9 + i * 2))
            p = skia.Path(); p.moveTo(x - 0.03 * B, y - kanat); p.quadTo(x - 0.012 * B, y - kanat * 0.2, x, y)
            p.quadTo(x + 0.012 * B, y - kanat * 0.2, x + 0.03 * B, y - kanat)
            cv.drawPath(p, k)

    def _eslik(self, cv, e, t, g, ekr):
        boy = e.get("boy", 0.92)
        poz = iskelet.poz(e.get("poz", "ayakta"))
        for k_, v in iskelet.nefes(t + 1.7).items():
            poz[k_] += v
        for k_, v in iskelet.salinim(poz.pop("salinim"), t).items():
            poz[k_] += v
        g2 = iskelet.govde_kur(poz)
        dx = e.get("x", 0.35)
        ek = lambda p: ekr((g.kalca[0] + dx + p[0] * boy, p[1] * boy))
        sac = self.k.get("sac")
        self.k["sac"] = e.get("sac", "uzun")
        self._beden(cv, g2, ek, boy)
        self.k["sac"] = sac

    # ---------- karakter: tek renk dolgu beden ----------
    def karakter(self, cv, g, y, ekr):
        self._beden(cv, g, ekr, 1.0)

    def _beden(self, cv, g, ekr, boy):
        B = self.c.boy * boy
        bacak = self._kalem(0.050 * B, self.siluet)
        for taraf, isaret in (("sol", -1), ("sag", 1)):
            k, d, a = ekr(g.kalca_eklem[taraf]), ekr(g.diz[taraf]), ekr(g.ayak[taraf])
            p = skia.Path(); p.moveTo(*k); p.lineTo(*d); p.lineTo(*a); p.lineTo(a[0] + isaret * 0.035 * B, a[1])
            cv.drawPath(p, bacak)
        egim = math.radians(g.govde_aci)
        yuk = (math.sin(egim), math.cos(egim)); sag = (yuk[1], -yuk[0])
        kose = lambda m, yari, asagi=0.0: ekr((m[0] + sag[0] * yari - yuk[0] * asagi, m[1] + sag[1] * yari - yuk[1] * asagi))
        p = skia.Path()
        p.addPoly([kose(g.boyun, -0.088), kose(g.boyun, 0.088), kose(g.kalca, 0.072, 0.02), kose(g.kalca, -0.072, 0.02)], True)
        cv.drawPath(p, self._boya(self.siluet))
        cv.drawPath(p, self._kalem(0.03 * B, self.siluet))   # köşeleri yuvarlar
        kol = self._kalem(0.046 * B, self.siluet)
        for taraf in ("sol", "sag"):
            p = skia.Path(); p.moveTo(*ekr(g.omuz[taraf])); p.lineTo(*ekr(g.dirsek[taraf])); p.lineTo(*ekr(g.el[taraf]))
            cv.drawPath(p, kol)
        boyun = self._kalem(0.05 * B, self.siluet)
        cv.drawLine(*ekr(g.boyun), *ekr(g.bas), boyun)
        r = g.oran.bas_yaricap * B
        cx, cy = ekr(g.bas)
        cv.save(); cv.translate(cx, cy); cv.rotate(g.bas_aci)
        sac = self.k.get("sac", "kisa")
        if sac == "uzun":
            for i in (-1, 1):
                cv.drawRoundRect(skia.Rect.MakeXYWH(i * 0.62 * r - 0.38 * r, -0.1 * r, 0.76 * r, 1.35 * r), 0.35 * r, 0.35 * r,
                                 self._boya(self.siluet))
        if sac == "topuz":
            cv.drawCircle(0, -1.18 * r, 0.42 * r, self._boya(self.siluet))
        cv.drawCircle(0, 0, r, self._boya(self.siluet))
        if sac != "kel":
            self._sac(cv, sac, r)
        cv.restore()

    def _yuz(self, cv, y, bakis, r):   # siluette yüz yok
        return

    # nesneler: ortak çizim, siluet renkleriyle (koyu çizgi, güneş rengi dolgu)
    def nesne(self, cv, n, g, ekr, olcek, gecen):
        self.bos, self.vurgu = self.gunes, self.gunes
        super().nesne(cv, n, g, ekr, olcek, gecen)
