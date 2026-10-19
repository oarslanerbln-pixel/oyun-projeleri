"""kagit-kesik: stop-motion kâğıt kesik. Yırtık kenarlı kâğıt kartlar, harf harf kesilmiş başlıklar, kâğıt dokusu,
alttan tepeler; sahneler sayfa gibi kayar. Parçalar ve yazılar stil/kagit_kesik.py'den."""

import skia

import kagit_kesik as kk
from kaplama import Kaplama, clamp, in_out, out_back


class KagitKesik(Kaplama):
    ad = "kagit-kesik"
    aciklama = "Stop-motion kâğıt kesik: yırtık kenarlı kartlar, harf harf kesik başlıklar"
    POZ = 12
    GECIS = 0.38
    PALET = {"zemin": "#F4EBD9", "yuzey": "#FFFBF2", "murekkep": "#263247", "soluk": "#5D6577", "vurgu": "#E5574B",
             "ikinci": "#F7CF4A", "ucuncu": "#6FAE7C", "vurgu_yazi": "#FFFBF2"}
    MUZIK = {**Kaplama.MUZIK, "bpm": 96, "kok": 60, "enstruman": "kalimba"}
    SFX = "kagit"

    def fon(self, cv, VW, VH, t, i):
        cv.drawColor(self.p["zemin"])
        dik = VH > VW
        kk.gunes(cv, VW * 0.86, VH * (0.07 if dik else 0.12), 52, t, kimlik=20)
        for k, (x, y, s) in enumerate(((0.18, 0.06, 0.8), (0.62, 0.1, 0.6))):
            kk.bulut(cv, (VW * x + t * 9 * (k + 1)) % (VW + 200) - 100, VH * y, s, 30 + k, t)
        cv.save(); cv.translate(0, VH); cv.scale(1, 1.0 if dik else 0.42)
        kk.zemin_tepeler(cv, VW, 0, t)
        cv.restore()

    def panel(self, cv, r, renk_, p=1.0, kimlik=0, t=0.0):
        if p <= 0:
            return
        s = out_back(clamp(p), 1.3)
        cv.save(); cv.translate(r.centerX(), r.centerY()); cv.rotate((1 - s) * -8 + ((kimlik % 3) - 1) * 0.8); cv.scale(s, s)
        kk.parca(cv, kk.yirtik(kk.kutu(-r.width() / 2, -r.height() / 2, r.width(), r.height()), seed=kimlik, amp=2.0),
                 renk_, kalk=1.0, kimlik=kimlik, t=t)
        cv.restore()

    def buyuk_yazi(self, cv, s, x, y, boy, renk_, hiza="orta", p=1.0, kimlik=0, t=0.0):
        if p <= 0 or not s:
            return
        w = self.olc(s, boy)
        x = x + w / 2 if hiza == "sol" else x - w / 2 if hiza == "sag" else x
        kk.kesik_yazi(cv, s, x, y, boy, renk_, t, kimlik, gelis=lambda i: clamp(p * 1.8 - i * 0.07))

    def isaret(self, cv, x, y, r, renk_, p=1.0, kimlik=0, t=0.0, n=1):
        if p <= 0:
            return
        cv.save(); cv.translate(x, y); s = out_back(p); cv.scale(s, s)
        kk.parca(cv, kk.yirtik(kk.daire(0, 0, r), seed=kimlik, amp=1.2), renk_, kalk=0.7, kimlik=kimlik, t=t)
        cv.restore()
        self.yazi(cv, str(n), x, y, r * 1.1, self.p["vurgu_yazi"], p=min(1, p * 2))

    def nesne(self, cv, r, sh, p, t):
        w = min(r.width(), r.height()) * 0.6
        k = skia.Rect.MakeXYWH(r.centerX() - w / 2, r.centerY() - w / 2, w, w)
        self.panel(cv, k, self.p["vurgu"], p, kimlik=71, t=t)
        self.panel(cv, skia.Rect.MakeXYWH(k.left() - 6, k.centerY() - w * 0.09, w + 12, w * 0.18), self.p["ikinci"], p, kimlik=72, t=t)
        self.buyuk_yazi(cv, self.harf(sh["ad"][:1], True), k.centerX(), k.top() + w * 0.27, w * 0.32, self.p["vurgu_yazi"], p=p,
                        kimlik=73, t=t)

    def gecis_ciz(self, cv, VW, VH, p, eski, yeni):
        """Yeni kâğıt sayfa sağdan kayarak gelir (kenarında gölge)."""
        eski()
        kenar = VW + 40 - (VW + 40) * in_out(p)
        sh = skia.GradientShader.MakeLinear([(kenar - 50, 0), (kenar, 0)], [0x00000000, 0x40000000])
        cv.drawRect(skia.Rect.MakeLTRB(kenar - 50, 0, kenar, VH), skia.Paint(Shader=sh, Dither=True))
        cv.save(); cv.clipRect(skia.Rect.MakeLTRB(kenar, 0, VW + 100, VH)); cv.translate(kenar * 0.15, 0)
        self.fon(cv, VW, VH, self._t, self._i)
        yeni()
        cv.restore()

    def ust_katman(self, cv, W, H, t):
        if not hasattr(self, "_doku"):
            self._doku = kk._doku()
        cv.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=self._doku, BlendMode=skia.BlendMode.kMultiply))


KAPLAMA = KagitKesik
