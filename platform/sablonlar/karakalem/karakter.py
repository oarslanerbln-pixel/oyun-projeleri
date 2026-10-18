"""Karakalem karikatür karakteri: kocaman kafa, küçük gövde, iri burun, yuvarlak gözlük, dağınık saç.

Orijin ayaklardır; gövde yukarı doğru yerel birimlerle kurulur (s = 1'de yaklaşık 560 birim boy).
Görünüş senaryonun `karakter` alanından gelir: ten, sac (daginik | kisa | kel), sac_rengi, gozluk,
kazak, pantolon. Cebindeki kalem vurgu rengindedir. Yüz ifadesi her karede çağıran tarafından verilir.
"""

from __future__ import annotations

import math

from kalem import Kalem, elips_noktalari, renk

BEYAZ = "#FFFFFF"


def _tarama(aralik=9.0, aci=-0.9, rgb="#28282E", alfa=0.35):
    return {"renk_": renk(rgb, alfa), "aralik": aralik, "aci": aci, "lw": 1.5}


def ciz(cv, k: Kalem, gorunus: dict, vurgu: str, x: float, y: float, s: float = 1.0, sx: float = 1.0, sy: float = 1.0,
        yon: int = 1, seed: int = 400, t: float = 0.0, gozler="normal", agiz="smile", kaslar="normal", bakis=0.0, bakis_y=0.0,
        kol_sol=0.25, kol_sag=0.25, kizarma=0.0, ter=0.0, kirp=False) -> None:
    ink = k.murekkep
    ten, kazak, pantolon, sac = gorunus["ten"], gorunus["kazak"], gorunus["pantolon"], gorunus["sac_rengi"]
    cv.save()
    cv.translate(x, y)
    # ayak altındaki kalem gölgesi
    k.cizgi(cv, [(-80 * s, 2), (-20 * s, 5), (40 * s, 3), (85 * s, 1)], renk(ink, 0.45), lw=3, seed=seed)
    cv.scale(s * sx * yon, s * sy)

    # bacaklar
    for j in (-1, 1):
        k.uzuv(cv, [(j * 22, -125), (j * 26, -60), (j * 30, -10)], pantolon, lw=26, kontur=4, seed=seed + 3 + j)
        k.elips(cv, j * 38, -8, 30, 14, dolgu=ink, lw=3.5, seed=seed + 6 + j)
    # gövde: armut biçimli küçük bir kazak
    k.cokgen(cv, [(-40, -128), (-62, -175), (-58, -250), (-30, -268), (30, -268), (58, -250), (62, -175), (40, -128)],
             dolgu=kazak, lw=4.5, seed=seed + 10, tarama=_tarama(10))
    # vurgu: cepten çıkan kalem
    k.cokgen(cv, [(22, -232), (30, -232), (30, -196), (22, -196)], dolgu=vurgu, lw=3, seed=seed + 11)
    k.cizgi(cv, [(14, -200), (44, -200)], lw=3.5, seed=seed + 12)

    # kollar: omuzdan, açı dik sarkmadan ölçülür
    def kol(j, aci):
        om = (j * 54, -246)
        dirsek = (om[0] + j * math.sin(aci) * 62, om[1] + math.cos(aci) * 62)
        b2 = aci * 1.15
        el = (dirsek[0] + j * math.sin(b2) * 58, dirsek[1] + math.cos(b2) * 58)
        k.uzuv(cv, [om, dirsek, el], kazak, lw=22, kontur=4, seed=seed + 20 + j)
        k.elips(cv, el[0], el[1], 15, 15, dolgu=ten, lw=3.5, seed=seed + 24 + j)
    kol(-1, kol_sol); kol(1, kol_sag)

    # boyun + kafa (karikatür: kafa bütün gövde kadar)
    k.cokgen(cv, [(-16, -290), (16, -290), (16, -260), (-16, -260)], adim=10, dolgu=ten, lw=3.5, seed=seed + 40)
    hy, hr = -405.0, 128.0
    for j in (-1, 1):  # kulaklar
        k.elips(cv, j * 124, hy + 10, 22, 30, dolgu=ten, lw=4, seed=seed + 42 + j)
    kafa = [(px * (1.04 if py > hy else 0.97), py) for px, py in elips_noktalari(0, hy, hr, hr * 1.02)]  # çeneye doğru genişleyen yumurta
    k.sekil(cv, kafa, dolgu=ten, lw=5, seed=seed + 45)
    stil = gorunus["sac"]
    if stil != "kel":
        sac_ = []
        n = 18
        for i in range(n + 1):
            a = math.pi + i / n * math.pi
            if stil == "daginik":
                r = hr * (1.02 + ((0.2 + 0.08 * math.sin(i * 2.3)) if i % 2 else 0) + (0.25 if i == 9 else 0))
            else:  # kısa: düzgün, kafaya yakın
                r = hr * (1.04 + (0.05 if i % 2 else 0))
            sac_.append((math.cos(a) * r * 1.02, hy - 10 + math.sin(a) * r))
        sac_ += [(hr * 0.95, hy - 30), (hr * 0.4, hy - 70), (-hr * 0.2, hy - 60), (-hr * 0.95, hy - 25)]
        k.sekil(cv, sac_, dolgu=sac, lw=4.5, seed=seed + 50, tarama=_tarama(6, -0.7, "#0A0A0C", 0.5))

    # kaşlar: [dış uç, iç uç] kaydırma; endişe iç uçları kaldırır, kararlılık indirir
    by = hy - 52
    bk = {"worry": (4, -16), "up": (-16, -16), "angry": (-6, 10)}.get(kaslar, (0, -2))
    for j in (-1, 1):
        k.cizgi(cv, [(j * 72, by + bk[0]), (j * 24, by + bk[1])], lw=9, seed=seed + 55 + j)
    # gözler (gözlük arkasında)
    ey = hy - 12
    for j in (-1, 1):
        ex = j * 48
        if gozler == "closed" or kirp:
            k.cizgi(cv, [(ex - 18, ey), (ex, ey + 6), (ex + 18, ey)], lw=5, seed=seed + 60 + j)
        elif gozler == "happy":
            k.cizgi(cv, [(ex - 18, ey + 6), (ex, ey - 8), (ex + 18, ey + 6)], lw=5, seed=seed + 60 + j)
        else:
            b = 1.25 if gozler == "wide" else 1.0
            k.elips(cv, ex, ey, 22 * b, 26 * b, dolgu=BEYAZ, lw=3.5, seed=seed + 60 + j)
            k.daire(cv, ex + bakis * 9, ey + bakis_y * 9 + 2, 9 * b, renk(ink))
            k.daire(cv, ex + bakis * 9 + 3, ey + bakis_y * 9 - 2, 2.6, renk(BEYAZ))
        if gorunus.get("gozluk", True):
            k.elips(cv, ex, ey, 40, 38, lw=5, seed=seed + 64 + j)
    if gorunus.get("gozluk", True):
        k.cizgi(cv, [(-10, ey - 4), (0, ey - 8), (10, ey - 4)], lw=5, seed=seed + 68)
    # burun: iri ve yuvarlak, biraz taralı
    k.elips(cv, 6, hy + 42, 30, 26, dolgu=ten, lw=4.5, seed=seed + 70, tarama=_tarama(6, -0.5, alfa=0.25))
    if kizarma > 0:  # yanaklar
        for j in (-1, 1):
            cv.save()
            r = k.skia.Rect.MakeLTRB(j * 80 - 22, hy + 40, j * 80 + 22, hy + 60)
            cv.clipRect(r, True)
            k.tara(cv, (r.left(), r.top(), r.right(), r.bottom()), renk(vurgu, 0.5 * kizarma), aralik=5, aci=-0.6, lw=2, seed=seed + 72 + j)
            cv.restore()
    # ağız
    my = hy + 88
    if agiz == "smile":
        k.cizgi(cv, [(-40, my - 6), (-15, my + 10), (15, my + 10), (40, my - 6)], lw=5, seed=seed + 80)
    elif agiz == "flat":
        k.cizgi(cv, [(-28, my + 2), (28, my + 2)], lw=5, seed=seed + 80)
    elif agiz == "worry":
        k.cizgi(cv, [(-34, my + 8), (-14, my), (4, my + 6), (20, my - 1), (34, my + 6)], lw=5, seed=seed + 80)
    elif agiz == "o":
        k.elips(cv, 0, my + 4, 14, 18, dolgu=pantolon, lw=4, seed=seed + 80)
    else:  # grin / open
        k.sekil(cv, [(-46, my - 8), (46, my - 8), (30, my + 22), (0, my + 34), (-30, my + 22)], dolgu="#4A4A52", lw=4.5, seed=seed + 80)
        k.cokgen(cv, [(-40, my - 7), (40, my - 7), (34, my + 3), (-34, my + 3)], dolgu=BEYAZ, lw=2.5, seed=seed + 81)
    if ter > 0:  # endişe damlaları
        for i in range(2):
            u = (t * 1.1 + i * 0.5) % 1
            dx, dy = 130 + i * 18, hy - 60 + u * 90
            k.sekil(cv, [(dx, dy - 22), (dx + 11, dy), (dx, dy + 10), (dx - 11, dy)], dolgu=BEYAZ, lw=3.5, seed=seed + 90 + i, alfa=(1 - u) * ter)
    cv.restore()
