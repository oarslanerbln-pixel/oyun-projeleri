"""origami: katlanmış kâğıt. Kartlar çapraz katlı (iki tonlu yarım, kat izi) ve yukarıdan açılarak gelir;
liste imleri katlı kareler, fonda yavaş dönen kâğıt üçgenler; sahneler katlanarak değişir."""

import math

import skia

from kaplama import Kaplama, alfa, clamp, in_out, karis, out_cubic


def _cokgen(pts):
    return skia.Path.Polygon([skia.Point(*q) for q in pts], True)


class Origami(Kaplama):
    ad = "origami"
    aciklama = "Katlanmış kâğıt: çapraz katlı kartlar, açılarak gelen yüzeyler"
    GECIS = 0.5
    PALET = {"zemin": "#F3ECDF", "yuzey": "#FFFBF3", "murekkep": "#22304A", "soluk": "#5E6880", "vurgu": "#E2603F",
             "ikinci": "#2E8A84", "ucuncu": "#EDB548", "vurgu_yazi": "#FFFBF3"}
    MUZIK = {**Kaplama.MUZIK, "bpm": 88, "kok": 62, "dizi": [0, 2, 4, 7, 9, 12], "enstruman": "mizrap"}
    SFX = "katla"

    def kagit(self, cv, r, c, kimlik=0, kat=1.0):
        """Çapraz katlı kâğıt: gölge, alt yarı, üst-sağ yarı açık ton, kat izi."""
        cv.drawRect(r.makeOffset(6, 10), skia.Paint(AntiAlias=True, Color=0x2622304A,
                    MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 9)))
        cv.drawRect(r, skia.Paint(AntiAlias=True, Color=karis(c, 0xFF22304A, 0.07)))
        ters = kimlik % 2
        ust = [(r.left(), r.top()), (r.right(), r.top()), (r.right(), r.bottom())] if not ters else \
              [(r.left(), r.top()), (r.right(), r.top()), (r.left(), r.bottom())]
        cv.drawPath(_cokgen(ust), skia.Paint(AntiAlias=True, Color=karis(c, 0xFFFFFFFF, 0.12)))
        a, b = (ust[0], ust[2])
        cv.drawLine(*a, *b, skia.Paint(AntiAlias=True, Color=alfa(0xFF22304A, 0.12 * kat), StrokeWidth=2))

    def fon(self, cv, VW, VH, t, i):
        cv.drawColor(self.p["zemin"])
        for k, (x, y, s, c) in enumerate(((0.1, 0.06, 70, 0xFFE9DCC6), (0.88, 0.05, 54, 0xFFEBD3C4), (0.92, 0.9, 90, 0xFFDCE6E0),
                                          (0.07, 0.93, 60, 0xFFEDE0B9))):
            cv.save(); cv.translate(VW * x, VH * y); cv.rotate(t * 6 * (1 if k % 2 else -1) + k * 40)
            cv.drawPath(_cokgen([(-s, s * 0.6), (s, s * 0.6), (0, -s)]), skia.Paint(AntiAlias=True, Color=c))
            cv.drawPath(_cokgen([(0, s * 0.6), (s, s * 0.6), (0, -s)]), skia.Paint(AntiAlias=True, Color=karis(c, 0xFF22304A, 0.06)))
            cv.restore()

    def panel(self, cv, r, renk_, p=1.0, kimlik=0, t=0.0):
        if p <= 0:
            return
        e = out_cubic(p)
        cv.save(); cv.translate(r.centerX(), r.top()); cv.scale(1, max(0.02, e)); cv.translate(-r.centerX(), -r.top())
        self.kagit(cv, r, renk_, kimlik, kat=1.0)
        if e < 1:
            cv.drawRect(r, skia.Paint(Color=alfa(0xFF22304A, 0.25 * (1 - e))))
        cv.restore()

    def isaret(self, cv, x, y, r, renk_, p=1.0, kimlik=0, t=0.0, n=1):
        if p <= 0:
            return
        s = r * out_cubic(p)
        cv.save(); cv.translate(x, y); cv.rotate(45 + (1 - p) * 90)
        cv.drawRect(skia.Rect.MakeLTRB(-s * 0.8, -s * 0.8, s * 0.8, s * 0.8), skia.Paint(AntiAlias=True, Color=renk_))
        cv.drawPath(_cokgen([(-s * 0.8, -s * 0.8), (s * 0.8, -s * 0.8), (s * 0.8, s * 0.8)]),
                    skia.Paint(AntiAlias=True, Color=karis(renk_, 0xFFFFFFFF, 0.15)))
        cv.restore()
        self.yazi(cv, str(n), x, y, r * 1.05, self.p["vurgu_yazi"], p=min(1, p * 2))

    def nesne(self, cv, r, sh, p, t):
        """Görselsiz ürün: katlanmış kâğıt kutu (üç yüz)."""
        s = min(r.width(), r.height()) * 0.3 * out_cubic(p)
        cx, cy = r.centerX(), r.centerY() + s * 0.3
        c = self.p["vurgu"]
        cv.drawPath(_cokgen([(cx - s, cy - s * 0.5), (cx, cy), (cx, cy + s * 1.1), (cx - s, cy + s * 0.6)]),
                    skia.Paint(AntiAlias=True, Color=karis(c, 0xFF22304A, 0.15)))
        cv.drawPath(_cokgen([(cx, cy), (cx + s, cy - s * 0.5), (cx + s, cy + s * 0.6), (cx, cy + s * 1.1)]),
                    skia.Paint(AntiAlias=True, Color=c))
        cv.drawPath(_cokgen([(cx - s, cy - s * 0.5), (cx, cy - s), (cx + s, cy - s * 0.5), (cx, cy)]),
                    skia.Paint(AntiAlias=True, Color=karis(c, 0xFFFFFFFF, 0.2)))

    def gecis_ciz(self, cv, VW, VH, p, eski, yeni):
        """Kat: eski sahne ortadan katlanıp kapanır, yeni sahne açılır."""
        if p < 0.5:
            e = in_out(p / 0.5)
            cv.save(); cv.translate(VW / 2, 0); cv.scale(max(0.02, 1 - e), 1); cv.translate(-VW / 2, 0); eski()
            cv.drawRect(skia.Rect.MakeWH(VW, VH), skia.Paint(Color=alfa(0xFF22304A, 0.18 * e))); cv.restore()
        else:
            e = in_out((p - 0.5) / 0.5)
            cv.save(); cv.translate(VW / 2, 0); cv.scale(max(0.02, e), 1); cv.translate(-VW / 2, 0); yeni()
            cv.drawRect(skia.Rect.MakeWH(VW, VH), skia.Paint(Color=alfa(0xFF22304A, 0.18 * (1 - e)))); cv.restore()
        cv.drawLine(VW / 2, 0, VW / 2, VH, skia.Paint(Color=alfa(0xFF22304A, 0.1 * math.sin(math.pi * p)), StrokeWidth=2))


KAPLAMA = Origami
