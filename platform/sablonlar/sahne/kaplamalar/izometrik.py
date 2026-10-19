"""izometrik: yüzen pastel ada, üç tonlu bloklar ve uzun gölgeler. Kartlar kalınlığı olan blok tabelalardır; liste
imleri küp, adadaki sütunlar her sahnede bir basamak yükselir (video ilerledikçe büyüme)."""

import math

import skia

from kaplama import Kaplama, alfa, clamp, in_out, karis, out_back, prog

INK = 0xFF3B3760


class Izometrik(Kaplama):
    ad = "izometrik"
    aciklama = "Yüzen pastel ada, üç tonlu bloklar, uzun gölgeler"
    GECIS = 0.5
    PALET = {"zemin": "#DDEBF3", "yuzey": "#FFF8EC", "murekkep": "#3B3760", "soluk": "#6A6496", "vurgu": "#F27A66",
             "ikinci": "#FFD98F", "ucuncu": "#9FE0CF", "vurgu_yazi": "#3B3760"}
    MUZIK = {**Kaplama.MUZIK, "bpm": 100, "kok": 62, "enstruman": "can"}
    SFX = "tok"
    RENKLER = [0xFFFFAE9E, 0xFFFFD98F, 0xFF9FE0CF, 0xFFA5CFF2, 0xFFC9B5F2, 0xFFFFB7D0]

    def tonlar(self, c):
        return karis(c, 0xFFFFFFFF, 0.35), c, karis(c, INK, 0.28)

    def kup(self, cv, cx, cy, s, h, c):
        """Taban merkezi (cx, cy), yarı genişlik s, yükseklik h; üst, sol, sağ yüz."""
        ust, sol, sag = self.tonlar(c)
        dy = s * 0.5
        yuz = lambda pts, renk_: cv.drawPath(skia.Path.Polygon([skia.Point(*q) for q in pts], True),  # noqa: E731
                                             skia.Paint(AntiAlias=True, Color=renk_))
        yuz([(cx - s, cy - h), (cx, cy - h + dy), (cx, cy + dy), (cx - s, cy)], sol)
        yuz([(cx, cy - h + dy), (cx + s, cy - h), (cx + s, cy), (cx, cy + dy)], sag)
        yuz([(cx - s, cy - h), (cx, cy - h - dy), (cx + s, cy - h), (cx, cy - h + dy)], ust)

    def fon(self, cv, VW, VH, t, i):
        cv.drawColor(self.p["zemin"])
        for k, (x, y, w) in enumerate(((0.15, 0.06, 150), (0.7, 0.04, 110), (0.45, 0.95, 130))):
            xx = (VW * x + t * 14 * (1 + k % 2)) % (VW + 300) - 150
            cv.drawRoundRect(skia.Rect.MakeXYWH(xx, VH * y, w, w * 0.32), w * 0.16, w * 0.16,
                             skia.Paint(AntiAlias=True, Color=0xCCFFFFFF))
        # ada: alt köşede, sütunları sahne sırasıyla büyür (yalnız süs; yazı alanına girmez)
        dik = VH > VW
        s = 64 if dik else 44
        ox, oy = (VW * 0.5, VH * 0.905) if dik else (VW * 0.9, VH * 0.86)
        bob = math.sin(t * 1.3) * 5
        cv.drawOval(skia.Rect.MakeXYWH(ox - s * 4.4, oy + s * 1.2 + bob, s * 8.8, s * 1.6),
                    skia.Paint(AntiAlias=True, Color=0x223B3760, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14)))
        self.kup(cv, ox, oy + bob, s * 3.2, s * 0.9, 0xFFF0C29E)
        self.kup(cv, ox, oy - s * 0.9 + bob, s * 3.2, s * 0.22, 0xFFA8DDB5)
        n = len(self.s["sahneler"])
        for k in range(6):
            hedef = [1, 2, 3, 5, 8, 13][k] * s * 0.16 * clamp((i + 1) * 6 / n - k, 0, 1)
            bas = self.s["sahneler"][i]["bas"]
            h = hedef * (0.4 + 0.6 * in_out(prog(t, bas, 0.6))) if hedef else 0
            if h > 1:
                x = ox + (k - 2.5) * s * 0.95
                y = oy - s * 1.12 + bob + (k - 2.5) * s * 0.48 * 0 + abs(k - 2.5) * s * 0.08
                self.kup(cv, x, y, s * 0.38, h, self.RENKLER[k])

    def blok(self, cv, r, c, derin):
        ust, on, sag = self.tonlar(c)
        dx, dy = derin * 0.9, derin * 0.5
        golge = skia.Path.Polygon([skia.Point(*q) for q in ((r.left(), r.bottom()), (r.right(), r.bottom()),
                                  (r.right() + derin * 2.2, r.bottom() + derin * 1.6), (r.left() + derin * 2.2, r.bottom() + derin * 1.6))], True)
        cv.drawPath(golge, skia.Paint(AntiAlias=True, Color=0x263B3760, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10)))
        cv.drawPath(skia.Path.Polygon([skia.Point(*q) for q in ((r.left(), r.top()), (r.right(), r.top()), (r.right() + dx, r.top() - dy),
                    (r.left() + dx, r.top() - dy))], True), skia.Paint(AntiAlias=True, Color=ust))
        cv.drawPath(skia.Path.Polygon([skia.Point(*q) for q in ((r.right(), r.top()), (r.right() + dx, r.top() - dy),
                    (r.right() + dx, r.bottom() - dy), (r.right(), r.bottom()))], True), skia.Paint(AntiAlias=True, Color=sag))
        cv.drawRect(r, skia.Paint(AntiAlias=True, Color=on))

    def panel(self, cv, r, renk_, p=1.0, kimlik=0, t=0.0):
        if p <= 0:
            return
        derin = min(34.0, r.height() * 0.22)
        dus = (1 - out_back(p, 1.2)) * -80 + math.sin(t * 1.6 + kimlik) * 4
        cv.save(); cv.translate(0, dus)
        cv.saveLayerAlpha(None, int(255 * clamp(p * 2)))
        self.blok(cv, r, renk_, derin)
        cv.restore(); cv.restore()

    def isaret(self, cv, x, y, r, renk_, p=1.0, kimlik=0, t=0.0, n=1):
        if p <= 0:
            return
        s = r * 0.85 * out_back(p)
        self.kup(cv, x, y + s * 0.6, s, s * 1.1, renk_)
        self.yazi(cv, str(n), x, y - s * 0.05, r * 0.85, INK, p=min(1, p * 2))

    def nesne(self, cv, r, sh, p, t):
        s = min(r.width(), r.height()) * 0.3 * out_back(p)
        self.kup(cv, r.centerX(), r.centerY() + s * 0.8, s, s * 1.2, self.p["vurgu"])
        self.kup(cv, r.centerX(), r.centerY() - s * 0.4, s * 0.5, s * 0.12, self.p["ikinci"])

    def gecis_ciz(self, cv, VW, VH, p, eski, yeni):
        """Kamera kayar: eski sahne sola, yeni sağdan."""
        e = in_out(p)
        cv.save(); cv.translate(-VW * 0.35 * e, VH * 0.08 * e); cv.saveLayerAlpha(None, int(255 * (1 - e))); eski(); cv.restore(); cv.restore()
        cv.save(); cv.translate(VW * 0.35 * (1 - e), -VH * 0.08 * (1 - e)); cv.saveLayerAlpha(None, int(255 * e)); yeni()
        cv.restore(); cv.restore()


KAPLAMA = Izometrik
