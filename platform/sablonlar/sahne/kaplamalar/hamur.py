"""hamur: claymation. Saniyede 12 poz, kaynayan konturlu hamur kartlar ve hamur harfler (Baloo 2), parmak izi,
krem fon + tanecik; sahneler yoğrularak değişir. Parçalar stil/hamur.py'den."""

import skia

import hamur as hm
from kaplama import Kaplama, clamp, out_back


class Hamur(Kaplama):
    ad = "hamur"
    aciklama = "Claymation: kaynayan konturlu hamur kartlar ve harfler"
    POZ = 12
    GECIS = 0.42
    BUYUK_HARF = False
    PALET = {"zemin": "#F7EAD7", "yuzey": "#FBF3E6", "murekkep": "#4A2C1D", "soluk": "#8A6A55", "vurgu": "#EE8547",
             "ikinci": "#E3A13F", "ucuncu": "#7FC8A9", "vurgu_yazi": "#FFF8EC"}
    MUZIK = {**Kaplama.MUZIK, "bpm": 104, "kok": 60, "enstruman": "marimba"}
    SFX = "pop"

    def yazi_tipi(self, agirlik):
        return hm.yazi_tipi_baloo(max(600, min(800, agirlik)))

    def fon(self, cv, VW, VH, t, i):
        hm.fon(cv, VW, VH)
        k = hm._poz(t)
        for j, (x, y, a, c) in enumerate(((0.08, 0.05, 60, hm.NANE), (0.93, 0.08, 44, hm.PEMBE), (0.9, 0.93, 70, hm.AMBER),
                                          (0.06, 0.95, 50, 0xFF8FB8E8))):
            hm.hamur(cv, hm.blob(VW * x, VH * y, a, a * 0.9, us=2.2, kaynama=1.2, seed=k * 3 + j), c, kalinlik=6, iz=j)

    def panel(self, cv, r, renk_, p=1.0, kimlik=0, t=0.0):
        if p <= 0:
            return
        s = hm.ziplama(p)
        cv.save(); cv.translate(r.centerX(), r.centerY()); cv.scale(s, s)
        hm.hamur(cv, hm.blob(0, 0, r.width() / 2, r.height() / 2, us=6.0, kaynama=1.4, seed=hm._poz(t) * 7 + kimlik),
                 renk_, kalinlik=8, iz=kimlik)
        cv.restore()

    def buyuk_yazi(self, cv, s, x, y, boy, renk_, hiza="orta", p=1.0, kimlik=0, t=0.0):
        if p <= 0 or not s:
            return
        w = hm.yazi_genislik(s, round(boy, 1))
        x = x + w / 2 if hiza == "sol" else x - w / 2 if hiza == "sag" else x
        hm.hamur_yazi(cv, s, x, y, round(boy, 1), renk_, t, kimlik, olcek=hm.ziplama(p))

    def isaret(self, cv, x, y, r, renk_, p=1.0, kimlik=0, t=0.0, n=1):
        if p <= 0:
            return
        cv.save(); cv.translate(x, y); s = hm.ziplama(p); cv.scale(s, s)
        hm.hamur(cv, hm.blob(0, 0, r, r * 0.94, us=2.0, kaynama=0.8, seed=hm._poz(t) * 5 + kimlik), renk_, kalinlik=5)
        cv.restore()
        self.yazi(cv, str(n), x, y, r * 1.1, self.p["vurgu_yazi"], p=min(1, p * 2))

    def nesne(self, cv, r, sh, p, t):
        a = min(r.width(), r.height()) * 0.3
        cv.save(); cv.translate(r.centerX(), r.centerY()); s = hm.ziplama(p); cv.scale(s, s)
        hm.hamur(cv, hm.blob(0, a * 0.1, a, a * 0.95, us=3.2, kaynama=1.2, seed=hm._poz(t) * 3), self.p["vurgu"], kalinlik=10, iz=3)
        hm.hamur(cv, hm.blob(0, -a * 0.85, a * 0.55, a * 0.18, us=4, kaynama=1.0, seed=hm._poz(t) * 3 + 1), self.p["ikinci"], kalinlik=6)
        cv.restore()

    def gecis_ciz(self, cv, VW, VH, p, eski, yeni):
        """Yoğurma: eski sahne ezilip küçülür, yeni hamur gibi zıplayarak açılır."""
        if p < 0.45:
            e = clamp(p / 0.45)
            cv.save(); cv.translate(VW / 2, VH / 2); cv.scale(1 + 0.1 * e, 1 - 0.6 * e ** 1.5)
            cv.translate(-VW / 2, -VH / 2); cv.saveLayerAlpha(None, int(255 * (1 - e))); eski(); cv.restore(); cv.restore()
        else:
            s = out_back(clamp((p - 0.45) / 0.55), 2.0)
            cv.save(); cv.translate(VW / 2, VH / 2); cv.scale(s, s); cv.translate(-VW / 2, -VH / 2); yeni(); cv.restore()

    def ust_katman(self, cv, W, H, t):
        if getattr(self, "_tane_boy", None) != (W, H):
            self._tane = [hm._tanecik(W, H, i) for i in range(4)]
            self._tane_boy = (W, H)
        cv.drawImage(self._tane[hm._poz(t) % 4], 0, 0, skia.SamplingOptions(), skia.Paint(BlendMode=skia.BlendMode.kOverlay))


KAPLAMA = Hamur
