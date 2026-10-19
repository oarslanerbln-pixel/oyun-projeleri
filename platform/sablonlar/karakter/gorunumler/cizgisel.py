"""Çizgisel insan (doodle) görünümü: ince siyah çizgi, beyaz dolgulu yamuk gövde, çubuk kol ve bacaklar,
nokta gözler, tek vurgu rengi. İskelet ve yüz değerleri `iskelet.py`'den gelir; burası yalnız çizer.

Yeni bir görünüm (konuşan maskot, siluet...) aynı arayüzle yazılır: `Gorunum(s, cizici)`,
`karakter(cv, govde, yuz, ekran)` ve `nesne(cv, nesne, govde, ekran, olcek, gecen)`.
"""

from __future__ import annotations

import math

import skia

from cizim import renk


class Gorunum:
    def __init__(self, s: dict, c):
        self.s, self.c = s, c
        self.k = s["karakter"]
        pal = s["palet"]
        self.cizgi = renk(pal["cizgi"])
        self.dolgu = renk(self.k.get("ust", pal["dolgu"]))
        self.ten = renk(self.k.get("ten", pal["dolgu"]))
        self.sac = renk(self.k.get("sac_rengi", pal["cizgi"]))
        self.vurgu = renk(pal["vurgu"])
        self.bos = renk(pal["dolgu"])
        self.kalin = 0.0105 * c.boy

    # ---------- yardımcılar ----------
    def _kalem(self, kalin=None, renk_=None):
        return skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=kalin or self.kalin,
                          Color=self.cizgi if renk_ is None else renk_, StrokeCap=skia.Paint.kRound_Cap,
                          StrokeJoin=skia.Paint.kRound_Join)

    def _boya(self, renk_):
        return skia.Paint(AntiAlias=True, Color=renk_)

    def _cizgi(self, cv, *noktalar, kalin=None):
        p = skia.Path()
        p.moveTo(*noktalar[0])
        for q in noktalar[1:]:
            p.lineTo(*q)
        cv.drawPath(p, self._kalem(kalin))

    # ---------- karakter ----------
    def karakter(self, cv, g, y, ekr):
        B = self.c.boy
        # bacaklar ve ayaklar (gövdenin arkasında)
        for taraf, isaret in (("sol", -1), ("sag", 1)):
            k, d, a = ekr(g.kalca_eklem[taraf]), ekr(g.diz[taraf]), ekr(g.ayak[taraf])
            self._cizgi(cv, k, d, a)
            self._cizgi(cv, a, (a[0] + isaret * 0.048 * B, a[1] + 0.004 * B))
        # gövde: omuzlarda dar, kalçada geniş yamuk (gövde eğimiyle döner)
        egim = math.radians(g.govde_aci)
        yuk = (math.sin(egim), math.cos(egim)); sag = (yuk[1], -yuk[0])
        def kose(merkez, yari, asagi=0.0):
            return ekr((merkez[0] + sag[0] * yari - yuk[0] * asagi, merkez[1] + sag[1] * yari - yuk[1] * asagi))
        govde = [kose(g.boyun, -0.10), kose(g.boyun, 0.10), kose(g.kalca, 0.135, 0.0), kose(g.kalca, -0.135, 0.0)]
        p = skia.Path(); p.addPoly(govde, True)
        cv.drawPath(p, self._boya(self.dolgu)); cv.drawPath(p, self._kalem())
        # kollar: omuz → dirsek → el (gövdenin önünde)
        for taraf in ("sol", "sag"):
            self._cizgi(cv, ekr(g.omuz[taraf]), ekr(g.dirsek[taraf]), ekr(g.el[taraf]))
        self._bas(cv, g, y, ekr)

    def _bas(self, cv, g, y, ekr):
        r = g.oran.bas_yaricap * self.c.boy
        cx, cy = ekr(g.bas)
        cv.save()
        cv.translate(cx, cy); cv.rotate(g.bas_aci)   # yerel: (0,0) baş merkezi, y aşağı, r birim
        sac = self.k.get("sac", "kase")
        if sac == "uzun":   # yanlardan omza inen saç başın arkasında
            for i in (-1, 1):
                cv.drawRoundRect(skia.Rect.MakeXYWH(i * 0.78 * r - 0.32 * r, -0.55 * r, 0.64 * r, 1.65 * r), 0.3 * r, 0.3 * r,
                                 self._boya(self.sac))
        if sac == "topuz":
            cv.drawCircle(0, -1.18 * r, 0.42 * r, self._boya(self.sac))
        cv.drawCircle(0, 0, r, self._boya(self.ten)); cv.drawCircle(0, 0, r, self._kalem())
        self._sac(cv, sac, r)
        self._yuz(cv, y, g.bakis, r)
        cv.restore()

    def _sac(self, cv, sac, r):
        b = self._boya(self.sac)
        if sac == "kase":   # başı aşan, altı düz kâse kesim (aday karedeki gibi)
            p = skia.Path()
            p.moveTo(-1.38 * r, -0.36 * r)
            p.cubicTo(-1.32 * r, -1.55 * r, 1.32 * r, -1.55 * r, 1.38 * r, -0.36 * r)
            p.cubicTo(0.6 * r, -0.48 * r, -0.6 * r, -0.48 * r, -1.38 * r, -0.36 * r)
            cv.drawPath(p, b)
        elif sac in ("kisa", "uzun", "topuz"):   # tepeyi kaplayan, alnında hafif kâkül
            p = skia.Path()
            p.moveTo(-r * 1.04, -0.05 * r)
            p.cubicTo(-1.1 * r, -1.42 * r, 1.1 * r, -1.42 * r, 1.04 * r, -0.05 * r)
            p.cubicTo(0.75 * r, -0.42 * r, 0.25 * r, -0.62 * r, -0.15 * r, -0.48 * r)
            p.cubicTo(-0.55 * r, -0.36 * r, -0.85 * r, -0.30 * r, -1.04 * r, -0.05 * r)
            cv.drawPath(p, b)
        elif sac == "kel":
            k = self._kalem(self.kalin * 0.8)
            p = skia.Path(); p.moveTo(-0.1 * r, -0.98 * r); p.quadTo(0.05 * r, -1.3 * r, 0.22 * r, -1.08 * r)
            cv.drawPath(p, k)

    def _yuz(self, cv, y, bakis, r):
        bx, by = bakis[0] * 0.08 * r, -bakis[1] * 0.06 * r
        mor = self._boya(self.cizgi)
        for i in (-1, 1):
            ex, ey = i * 0.34 * r + bx, -0.02 * r + by
            if y.mutlu_goz > 0.5:   # gülen göz: hilal
                p = skia.Path(); p.moveTo(ex - 0.11 * r, ey + 0.03 * r); p.quadTo(ex, ey - 0.12 * r * y.goz, ex + 0.11 * r, ey + 0.03 * r)
                cv.drawPath(p, self._kalem(self.kalin * 0.85))
            else:
                ry = 0.085 * r * max(0.08, y.goz)
                cv.drawOval(skia.Rect.MakeXYWH(ex - 0.075 * r, ey - ry, 0.15 * r, 2 * ry), mor)
            # kaş: nötrde görünmez, ifade belirginleştikçe çıkar
            belir = min(1.0, max(0.0, (abs(y.kas) + abs(y.kas_aci) - 0.3) / 0.15))
            if belir > 0.02:
                kh = ey - (0.22 + 0.08 * y.kas) * r
                ic = -0.07 * r * y.kas_aci   # iç uç: + üzgün (yukarı), - kararlı (aşağı)
                p = skia.Path()
                p.moveTo(i * 0.20 * r + bx, kh + ic); p.lineTo(i * 0.48 * r + bx, kh - ic * 0.3)
                pn = self._kalem(self.kalin * 0.8); pn.setAlphaf(belir)
                cv.drawPath(p, pn)
        if self.k.get("gozluk"):
            k = self._kalem(self.kalin * 0.75)
            for i in (-1, 1):
                cv.drawCircle(i * 0.36 * r + bx * 0.3, -0.02 * r, 0.21 * r, k)
            cv.drawLine(-0.15 * r, -0.04 * r, 0.15 * r, -0.04 * r, k)
        self._agiz(cv, y, r)

    def _agiz(self, cv, y, r):
        my = 0.43 * r
        gen = 0.24 * r * y.agiz_gen
        ac = y.agiz_ac
        if ac < 0.06 or y.agiz_bicim == "M" and y.konusuyor and ac < 0.25:
            p = skia.Path(); p.moveTo(-gen, my); p.quadTo(0, my + y.egri * 0.34 * r, gen, my)
            cv.drawPath(p, self._kalem(self.kalin * 0.85))
            return
        olcu = {"A": (0.34, 0.46), "E": (0.38, 0.26), "O": (0.21, 0.38), "F": (0.30, 0.11), "M": (0.24, 0.09)}
        w, h = olcu.get(y.agiz_bicim, (0.22, 0.25))
        w = w * r * (0.75 + 0.25 * y.agiz_gen); h = max(0.05, h * ac) * r * 1.0
        ust = my - h * 0.25 - max(0.0, y.egri) * 0.04 * r
        p = skia.Path()
        if y.agiz_bicim == "O":
            p.addOval(skia.Rect.MakeXYWH(-w / 2, ust, w, h))
        else:   # düz üst, yuvarlak alt (gülümseyen açık ağız)
            p.moveTo(-w / 2, ust)
            p.lineTo(w / 2, ust)
            p.cubicTo(w / 2, ust + h * 1.25, -w / 2, ust + h * 1.25, -w / 2, ust)
            p.close()
        cv.drawPath(p, self._boya(self.cizgi))

    # ---------- nesneler ----------
    def nesne(self, cv, n, g, ekr, olcek, gecen):
        B = self.c.boy
        tur = n["tur"]
        bx, by = ekr(g.bas)
        r = g.oran.bas_yaricap * B
        if tur == "tabela":   # kaldırılan eldeki tabela (aday kare)
            el = ekr(g.el["sag"] if g.el["sag"][1] >= g.el["sol"][1] else g.el["sol"])
            cv.save(); cv.translate(*el); cv.scale(olcek, olcek)
            self._cizgi(cv, (0, 0), (0.012 * B, -0.07 * B))
            dik = skia.Rect.MakeXYWH(-0.06 * B, -0.155 * B, 0.17 * B, 0.09 * B)
            cv.drawRoundRect(dik, 0.016 * B, 0.016 * B, self._boya(self.bos))
            cv.drawRoundRect(dik, 0.016 * B, 0.016 * B, self._kalem())
            self._metin(cv, n.get("metin", "!"), dik.centerX(), dik.centerY(), 0.058 * B, dik.width() * 0.84)
            cv.restore()
        elif tur == "ampul":
            cx, cy = bx + 0.02 * B, by - r - 0.135 * B
            cv.save(); cv.translate(cx, cy); cv.scale(olcek, olcek)
            R = 0.052 * B
            for i in range(7):   # ışınlar
                a = math.radians(-160 + i * 23.3)
                gir = min(1.0, max(0.0, (gecen - 0.15 - i * 0.03) / 0.2))
                if gir > 0:
                    self._cizgi(cv, (math.cos(a) * R * 1.45, math.sin(a) * R * 1.45),
                                (math.cos(a) * R * (1.45 + 0.5 * gir), math.sin(a) * R * (1.45 + 0.5 * gir)))
            cv.drawCircle(0, 0, R, self._boya(self.vurgu)); cv.drawCircle(0, 0, R, self._kalem())
            taban = skia.Rect.MakeXYWH(-0.45 * R, R * 0.92, 0.9 * R, 0.55 * R)
            cv.drawRect(taban, self._boya(self.bos)); cv.drawRect(taban, self._kalem())
            self._cizgi(cv, (-0.45 * R, R * 1.2), (0.45 * R, R * 1.2), kalin=self.kalin * 0.7)
            cv.restore()
        elif tur == "soru":
            cx, cy = bx + 0.13 * B, by - r - 0.07 * B
            cv.save(); cv.translate(cx, cy); cv.rotate(8 * math.sin(gecen * 3)); cv.scale(olcek, olcek)
            self._metin(cv, n.get("metin", "?"), 0, 0, 0.15 * B, B, renk_=self.cizgi)
            cv.restore()
        elif tur == "kalp":
            cx, cy = bx + 0.12 * B, by - r - 0.06 * B
            nab = 1 + 0.06 * math.sin(gecen * 7) * min(1.0, gecen * 2)
            cv.save(); cv.translate(cx, cy); cv.scale(olcek * nab, olcek * nab)
            R = 0.05 * B
            p = skia.Path()
            p.moveTo(0, R * 0.9)
            p.cubicTo(-R * 1.6, -R * 0.1, -R * 0.9, -R * 1.25, 0, -R * 0.45)
            p.cubicTo(R * 0.9, -R * 1.25, R * 1.6, -R * 0.1, 0, R * 0.9)
            cv.drawPath(p, self._boya(self.vurgu)); cv.drawPath(p, self._kalem())
            cv.restore()
        elif tur == "balon":
            cx, cy = bx + 0.20 * B, by - r - 0.05 * B
            cv.save(); cv.translate(cx, cy); cv.scale(olcek, olcek)
            dik = skia.Rect.MakeXYWH(-0.11 * B, -0.07 * B, 0.22 * B, 0.11 * B)
            p = skia.Path(); p.addRoundRect(dik, 0.04 * B, 0.04 * B)
            kuyruk = skia.Path(); kuyruk.addPoly([(-0.06 * B, 0.03 * B), (-0.03 * B, 0.03 * B), (-0.11 * B, 0.08 * B)], True)
            p = skia.Op(p, kuyruk, skia.PathOp.kUnion_PathOp) or p
            cv.drawPath(p, self._boya(self.bos)); cv.drawPath(p, self._kalem())
            self._metin(cv, n.get("metin", "…"), 0, dik.centerY(), 0.05 * B, dik.width() * 0.84)
            cv.restore()
        elif tur == "grafik":   # karakterin yanında yere oturan, sırayla yükselen çubuklar
            zx, zy = ekr((0.22, 0.0))
            for i, yuk in enumerate((0.10, 0.18, 0.30)):
                bu = min(1.0, max(0.0, (gecen - i * 0.18) / 0.3))
                if bu <= 0:
                    continue
                h = yuk * B * (1 - (1 - bu) ** 3) * olcek
                dik = skia.Rect.MakeXYWH(zx + i * 0.065 * B, zy - h, 0.048 * B, h)
                cv.drawRect(dik, self._boya(self.vurgu)); cv.drawRect(dik, self._kalem())
            self._cizgi(cv, (zx - 0.02 * B, zy), (zx + 0.20 * B, zy))

    def _metin(self, cv, metin, x, y, punto, maks_gen, renk_=None):
        f = skia.Font(self.c.yazi_tipi, punto)
        gen = f.measureText(metin)
        if gen > maks_gen:
            f = skia.Font(self.c.yazi_tipi, punto * maks_gen / gen); gen = maks_gen
        cv.drawString(metin, x - gen / 2, y + f.getSize() * 0.36, f, self._boya(self.cizgi if renk_ is None else renk_))
