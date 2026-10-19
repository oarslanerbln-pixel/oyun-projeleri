"""Konuşan nesne maskot görünümü: ürün (kupa, şişe, kutu ya da müşterinin şeffaf PNG ürün fotoğrafı) gövde olur;
yüzü gövdenin üstünde, ince çubuk kol ve kısa bacaklarla konuşur. Logo gövdede ve istenirse büyük rozet olarak
(`nesne: logo`) öne çıkar. İskelet, pozlar, ifadeler ve ağız senkronu ortak; burada yalnız çizim ve beden oranı var.

Gövde yerel düzlemde çizilir: (0,0) kalça, y aşağı, birim karakter boyu; gövde eğimiyle döner.
"""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import skia

import iskelet
from cizim import renk
from gorunumler import cizgisel

# Kısa bacak, büyük gövde: omuzlar gövdenin yan kenarına, boyun dibi gövdenin ortasının biraz üstüne düşer.
ORAN = iskelet.Oranlar(ust_bacak=0.12, alt_bacak=0.11, kalca_genislik=0.075, govde=0.30, omuz_genislik=0.20,
                       ust_kol=0.13, alt_kol=0.12, boyun=0.0, bas_yaricap=0.07)

# Gövde biçimleri (yerel, karakter boyu): üst/alt kenar, yarı genişlik, yüz merkezi, yüz ölçüsü, logo merkezi.
BICIM = {
    "kupa": dict(ust=-0.50, alt=0.03, yari=0.19, yuz=-0.31, r=0.15, logo=-0.08),
    "sise": dict(ust=-0.64, alt=0.03, yari=0.16, yuz=-0.27, r=0.13, logo=-0.07),
    "kutu": dict(ust=-0.50, alt=0.03, yari=0.20, yuz=-0.31, r=0.15, logo=-0.08),
    "gorsel": dict(ust=-0.58, alt=0.03, yari=0.22, yuz=-0.33, r=0.14, logo=None),
}


# Maskot insandan kısa (boyunun ~%73'ü): kadrajda büyütülür; tepesinde logo rozetine güvenli alan kalır.
DUZEN = {"9x16": dict(boy=0.52), "16x9": dict(boy=0.78), "1x1": dict(boy=0.64), "4x5": dict(boy=0.62)}


class Gorunum(cizgisel.Gorunum):
    ORAN = ORAN

    def __init__(self, s: dict, c):
        super().__init__(s, c)
        pal = s["palet"]
        self.tur = self.k.get("nesne", "kupa")
        self.b = BICIM[self.tur]
        self.govde_renk = renk(self.k.get("govde_rengi", pal.get("govde", "#FFFFFF")))
        self.icerik = renk(self.k.get("icerik_rengi", pal.get("icerik", "#7A4A2C")))
        self.yanak = renk(pal["vurgu"], 0.85)
        self.golge = renk(pal.get("golge", pal["zemin"]))
        self.kalin = 0.0095 * c.boy
        klasor = Path(s.get("_klasor", "."))
        self.gorsel = skia.Image.open(str(klasor / self.k["gorsel"])) if self.k.get("gorsel") else None
        self.logo = skia.Image.open(str(klasor / self.k["logo"])) if self.k.get("logo") else None
        self.logo_metin = self.k.get("logo_metin", "").replace(" ", "\u2002")   # büyük harfte boşluk kaybolmasın
        self.ornekleme = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)

    # ---------- zemin: düz renk + yerde yumuşak olmayan (düz) gölge elipsi ----------
    def zemin(self, cv, t, g, ekr):
        self._t = t
        cv.clear(renk(self.s["palet"]["zemin"]))
        B = self.c.boy
        x, y = ekr((g.kalca[0], 0.0))
        z = max(0.0, 1 - (g.kalca[1] - self._kalca_yer()) * 6)   # zıplarken gölge küçülür
        cv.drawOval(skia.Rect.MakeXYWH(x - 0.24 * B * z, y - 0.022 * B, 0.48 * B * z, 0.044 * B), self._boya(self.golge))

    def _kalca_yer(self):
        return ORAN.ust_bacak + ORAN.alt_bacak

    # ---------- karakter ----------
    def karakter(self, cv, g, y, ekr):
        B = self.c.boy
        # bacaklar ve ayakkabılar (gövdenin arkasında)
        for taraf, isaret in (("sol", -1), ("sag", 1)):
            k, d, a = ekr(g.kalca_eklem[taraf]), ekr(g.diz[taraf]), ekr(g.ayak[taraf])
            self._cizgi(cv, k, d, a)
            cv.drawOval(skia.Rect.MakeXYWH(a[0] - 0.035 * B + isaret * 0.014 * B, a[1] - 0.022 * B, 0.07 * B, 0.034 * B),
                        self._boya(self.cizgi))
        kx, ky = ekr(g.kalca)
        cv.save()
        cv.translate(kx, ky); cv.rotate(g.govde_aci); cv.scale(B, B)   # yerel: karakter boyu birimi
        self._govde(cv)
        cv.restore()
        # yüz: gövdenin üstünde, baş eğimi kadar döner, bakışla hafif kayar
        fx, fy = self._yerel_ekran(g, ekr, 0.0, self.b["yuz"])
        if self.tur != "gorsel" or self.k.get("yuz", True):
            r = self.b["r"] * B
            cv.save(); cv.translate(fx, fy); cv.rotate(g.bas_aci)
            for i in (-1, 1):
                cv.drawOval(skia.Rect.MakeXYWH(i * 0.50 * r - 0.11 * r, 0.20 * r, 0.22 * r, 0.12 * r), self._boya(self.yanak))
            self._yuz(cv, y, g.bakis, r)
            cv.restore()
        # kollar ve eller (gövdenin önünde)
        for taraf in ("sol", "sag"):
            self._cizgi(cv, ekr(g.omuz[taraf]), ekr(g.dirsek[taraf]), ekr(g.el[taraf]))
            cv.drawCircle(*ekr(g.el[taraf]), 0.019 * B, self._boya(self.cizgi))

    def _yerel_ekran(self, g, ekr, lx, ly):
        """Gövde yerel noktası (kalça kökenli, y aşağı) → ekran."""
        e = math.radians(g.govde_aci)
        yuk = (math.sin(e), math.cos(e)); sag = (yuk[1], -yuk[0])
        return ekr((g.kalca[0] + sag[0] * lx - yuk[0] * ly, g.kalca[1] + sag[1] * lx - yuk[1] * ly))

    def _govde(self, cv):
        b, kal = self.b, self.kalin / self.c.boy
        kalem = self._kalem(kal)
        u, a, w = b["ust"], b["alt"], b["yari"]
        if self.tur == "gorsel":
            self._resim(cv, self.gorsel, -w, u, 2 * w, a - u, alta=True)
            return
        if self.tur == "kupa":
            kulp = skia.Path()
            kulp.moveTo(w - 0.01, u + 0.12); kulp.cubicTo(w + 0.13, u + 0.11, w + 0.13, u + 0.34, w - 0.01, u + 0.33)
            cv.drawPath(kulp, self._kalem(0.028))
            govde = self._kap(-w, u, w, a, 0.02, 0.10)
            self._dolgu_cerceve(cv, govde, kalem, bant=(u, u + 0.055))
            if self.k.get("buhar", True):
                self._buhar(cv, u)
        elif self.tur == "sise":
            p = skia.Path()
            boyun_w, omuz_y = 0.05, u + 0.20
            p.moveTo(-boyun_w, u + 0.04); p.lineTo(boyun_w, u + 0.04)
            p.lineTo(boyun_w, u + 0.10); p.cubicTo(w, u + 0.13, w, omuz_y - 0.02, w, omuz_y + 0.04)
            p.lineTo(w, a - 0.05); p.quadTo(w, a, w - 0.05, a); p.lineTo(-w + 0.05, a); p.quadTo(-w, a, -w, a - 0.05)
            p.lineTo(-w, omuz_y + 0.04); p.cubicTo(-w, omuz_y - 0.02, -w, u + 0.13, -boyun_w, u + 0.10); p.close()
            self._dolgu_cerceve(cv, p, kalem, bant=(a - 0.25, a - 0.04))
            kapak = skia.Rect.MakeLTRB(-boyun_w - 0.008, u, boyun_w + 0.008, u + 0.055)
            cv.drawRoundRect(kapak, 0.01, 0.01, self._boya(self.icerik)); cv.drawRoundRect(kapak, 0.01, 0.01, kalem)
        else:   # kutu: kapaklı karton
            govde = self._kap(-w, u + 0.05, w, a, 0.015, 0.015)
            self._dolgu_cerceve(cv, govde, kalem)
            kapak = skia.Rect.MakeLTRB(-w - 0.012, u, w + 0.012, u + 0.065)
            cv.drawRoundRect(kapak, 0.012, 0.012, self._boya(self.icerik)); cv.drawRoundRect(kapak, 0.012, 0.012, kalem)
        if b["logo"] is not None:
            self._logo(cv, 0.0, b["logo"], 1.75 * w, 0.12)

    def _kap(self, x0, y0, x1, y1, r_ust, r_alt):
        p = skia.Path()
        p.moveTo(x0 + r_ust, y0); p.lineTo(x1 - r_ust, y0); p.quadTo(x1, y0, x1, y0 + r_ust)
        p.lineTo(x1, y1 - r_alt); p.quadTo(x1, y1, x1 - r_alt, y1)
        p.lineTo(x0 + r_alt, y1); p.quadTo(x0, y1, x0, y1 - r_alt)
        p.lineTo(x0, y0 + r_ust); p.quadTo(x0, y0, x0 + r_ust, y0); p.close()
        return p

    def _dolgu_cerceve(self, cv, p, kalem, bant=None):
        cv.drawPath(p, self._boya(self.govde_renk))
        if bant:   # kupada kahve, şişede etiket: gövdeye kırpılmış düz bant
            cv.save(); cv.clipPath(p, doAntiAlias=True)
            cv.drawRect(skia.Rect.MakeLTRB(-1, bant[0], 1, bant[1]), self._boya(self.icerik if self.tur == "kupa" else self.vurgu))
            cv.restore()
        cv.drawPath(p, kalem)

    def _buhar(self, cv, u):
        t = getattr(self, "_t", 0.0)
        k = self._kalem(0.008, renk(self.s["palet"]["cizgi"], 0.55))
        for i, x in enumerate((-0.07, 0.0, 0.07)):
            p = skia.Path()
            y0 = u - 0.03
            p.moveTo(x, y0)
            for j in range(1, 7):
                yy = y0 - j * 0.022
                p.lineTo(x + 0.014 * math.sin(t * 3.2 + i * 1.7 + j * 1.1), yy)
            cv.drawPath(p, k)

    def _resim(self, cv, img, x, y, w, h, alta=False):
        if img is None:
            return
        o = min(w / img.width(), h / img.height())
        iw, ih = img.width() * o, img.height() * o
        dx = x + (w - iw) / 2
        dy = y + (h - ih) if alta else y + (h - ih) / 2
        cv.drawImageRect(img, skia.Rect.MakeXYWH(dx, dy, iw, ih), self.ornekleme)

    def _logo(self, cv, cx, cy, gen, yuk):
        """Logo PNG'si (sığdırılır) ya da yoksa logo_metin: koyu hap içinde açık yazı."""
        if self.logo is not None:
            self._resim(cv, self.logo, cx - gen / 2, cy - yuk / 2, gen, yuk)
            return
        if not self.logo_metin:
            return
        f = skia.Font(self.c.yazi_tipi, 1.0)
        olcu = f.measureText(self.logo_metin)
        punto = min(yuk * 0.48, gen * 0.80 / olcu)
        f = skia.Font(self.c.yazi_tipi, punto)
        tw = f.measureText(self.logo_metin)
        dik = skia.Rect.MakeXYWH(cx - tw / 2 - punto * 0.55, cy - punto * 0.85, tw + punto * 1.1, punto * 1.7)
        cv.drawRoundRect(dik, punto * 0.85, punto * 0.85, self._boya(self.cizgi))
        cv.drawString(self.logo_metin, cx - tw / 2, cy + punto * 0.36, f, self._boya(self.govde_renk))

    # ---------- nesneler: ortak nesneler gövdenin tepesine göre, logo rozeti ----------
    def nesne(self, cv, n, g, ekr, olcek, gecen):
        B = self.c.boy
        r = ORAN.bas_yaricap
        tepe = g.kalca[1] - self.b["ust"] - r   # ortak nesneler başın üstüne konur: "baş" gövdenin tepesi
        e = math.radians(g.govde_aci)
        bas = (g.kalca[0] + math.sin(e) * (tepe - g.kalca[1]), tepe)
        if n["tur"] != "logo":
            super().nesne(cv, n, dataclasses.replace(g, bas=bas), ekr, olcek, gecen)
            return
        bx, by = ekr(bas)
        cv.save(); cv.translate(bx, by - r * B - 0.11 * B); cv.scale(olcek * B, olcek * B)
        if self.logo is None:   # metin logosu rozet gibi büyük
            self._logo(cv, 0.0, 0.0, 0.70, 0.20)
        else:
            self._resim(cv, self.logo, -0.35, -0.11, 0.70, 0.22)
        cv.restore()
