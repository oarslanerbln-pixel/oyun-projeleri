"""Hamur (claymation) stop-motion stili.

Her parça elle yoğrulmuş hamur: yumuşak hacim (kenarda gölge, üstte ışık), kalınlık, parmak izi, altında yumuşak
gölge. Saniyede 12 poz; her pozda konturlar hafifçe "kaynar" (boil) ve yazılar milim oynar. Biçimler birbirine
yoğrularak geçer (top → kart, kart → kart). Arka plan düz krem fon; radyal gradyan ve ışık parlaması yok, ince
tanecik dokusu 8 bit bantlaşmayı da dağıtır.

Görsel metafor bir ilerleme kartıdır (damga yuvaları): sadakat kartı, alışkanlık takibi, ilk adım teşvikleri gibi
"ilerleme" mesajlarına uyar. Kart `stiller.hamur` alanından ayarlanır:

    "stiller": {"hamur": {
        "kart": {"bos": 8, "toplam": 10, "hazir": 2},    # 1. vuruşta boş yuva sayısı; 2. vuruşta toplam ve basılı
        "marka": "DEMLİ KAHVE",                          # kartın etiketi ve kapanıştaki imza
        "dipnot": "bahşedilmiş ilerleme etkisi · ...",   # kapanışta küçük kaynak satırı (isteğe bağlı)
        "metin": {...}}}                                 # yazı yuvaları (motor.YUVALAR)

Yazılar motor.METIN'den gelir; kullanım için stil.py'ye bakın.
"""
import functools, math, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motor import *  # noqa: E402,F403
import motor  # noqa: E402
import skia  # noqa: E402

POZ = 12  # stop-motion poz/sn

# ---------- palet ----------
FON_UST, FON_ALT = 0xFFF7EAD7, 0xFFF0DCC2
KART, GRI = 0xFFFBF3E6, 0xFFDCD5CB
KAHVE, AMBER, TURUNCU = 0xFF4A2C1D, 0xFFE3A13F, 0xFFEE8547
NANE, PEMBE, KREM = 0xFF7FC8A9, 0xFFF0A296, 0xFFFFF8EC
KONFETI = (AMBER, TURUNCU, NANE, PEMBE, 0xFF8FB8E8)

Z = dict(
    dus=0.25, yere=0.62, kart=0.95, yuva=1.00, kanca=1.25, kanca_alt=1.70, sarkma=2.15,
    gecis2=2.80, yuva2=3.12, damga=3.25, bas1=3.55, bas2=3.95, sayac=4.10, sayi=4.40, sayi_alt=4.85,
    gecis3=5.80, kucuk=6.30, buyuk=6.75,
    gecis4=7.80, cagri=8.35, marka=8.75, konfeti=8.65,
)


def _ayar(ad, vars_):
    return motor.STIL_AYAR.get(ad, vars_)


def kart_ayar():
    k = {'bos': 8, 'toplam': 10, 'hazir': 2}
    k.update(_ayar('kart', {}))
    return k


# ---------- yardımcılar ----------
def _poz(t): return math.floor(t * POZ + 1e-6)


def _h(*a):  # deterministik 0..1
    x = math.sin(sum((i + 1) * 12.9898 * v for i, v in enumerate(a)) + 78.233) * 43758.5453
    return x - math.floor(x)


def koyu(c, k):
    a, r, g, b = c >> 24 & 255, c >> 16 & 255, c >> 8 & 255, c & 255
    return a << 24 | int(r * k) << 16 | int(g * k) << 8 | int(b * k)


def acik(c, k):
    a, r, g, b = c >> 24 & 255, c >> 16 & 255, c >> 8 & 255, c & 255
    f = lambda v: int(v + (255 - v) * k)
    return a << 24 | f(r) << 16 | f(g) << 8 | f(b)


def karis(c1, c2, p):
    o = [int(lerp(c1 >> s & 255, c2 >> s & 255, p)) for s in (24, 16, 8, 0)]
    return o[0] << 24 | o[1] << 16 | o[2] << 8 | o[3]


def alfa(c, a): return (int(255 * clamp(a)) << 24) | (c & 0xFFFFFF)


def ziplama(p):  # 0→1, hamur gibi: hafif taşma ve yerine oturma
    return out_back(clamp(p), 2.2) if p < 1 else 1.0


def ezilme(t, t0, d=0.35, g=0.22):
    """t0 anında çarpma: (sx, sy) ölçek çifti; kısa sönümlü salınım (squash & stretch)."""
    if t < t0: return 1.0, 1.0
    u = (t - t0) / d
    if u > 1: return 1.0, 1.0
    e = g * math.exp(-4 * u) * math.cos(u * 2.6 * math.pi)
    return 1 + e, 1 - e


# ---------- yazı tipi (Baloo 2, SIL OFL 1.1; Türkçe karakterleri tam) ----------
BALOO_URL = 'https://raw.githubusercontent.com/google/fonts/main/ofl/baloo2/Baloo2%5Bwght%5D.ttf'


@functools.lru_cache(maxsize=None)
def yazi_tipi_baloo(agirlik=800):
    ad = f'Baloo2-{agirlik}.ttf'
    for d in (FONTS, FONT_ONBELLEK):
        if os.path.exists(os.path.join(d, ad)):
            return skia.Typeface.MakeFromFile(os.path.join(d, ad))
    try:
        import urllib.request
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
        os.makedirs(FONT_ONBELLEK, exist_ok=True)
        degisken = os.path.join(FONT_ONBELLEK, 'Baloo2-degisken.ttf')
        if not os.path.exists(degisken):
            urllib.request.urlretrieve(BALOO_URL, degisken + '.indiriliyor')
            os.replace(degisken + '.indiriliyor', degisken)
        instantiateVariableFont(TTFont(degisken), {'wght': agirlik}).save(os.path.join(FONT_ONBELLEK, ad))
        return skia.Typeface.MakeFromFile(os.path.join(FONT_ONBELLEK, ad))
    except Exception as e:
        print(f'UYARI Baloo 2 yüklenemedi ({e}); Inter kullanılıyor', file=sys.stderr)
        return yazi_tipi(800)


@functools.lru_cache(maxsize=256)
def _yazi_yolu(s, boy, agirlik=800):
    """Yazının kontur yolu, (0,0) ortada; (yol, genişlik, yükseklik)."""
    f = skia.Font(yazi_tipi_baloo(agirlik), boy)
    g = f.textToGlyphs(s); xs = f.getXPos(g)
    yol = skia.Path()
    for gi, x in zip(g, xs):
        p = f.getPath(gi)
        if p is not None:
            p.offset(x, 0); yol.addPath(p)
    b = yol.computeTightBounds()
    yol.offset(-b.centerX(), -b.centerY())
    return yol, b.width(), b.height()


def yazi_genislik(s, boy, agirlik=800):
    return _yazi_yolu(s, boy, agirlik)[1]


# ---------- hamur biçimleri ----------
def _kaynama(i, n, seed, harm=4):
    s = 0.0
    for k in range(1, harm + 1):
        s += math.sin(2 * math.pi * k * i / n + 6.283 * _h(seed, k)) / k
    return s / 1.6


def noktalar(cx, cy, a, b, us=2.0, n=72, kaynama=0.0, seed=0):
    """Süperelips noktaları (us=2 elips, us≈5 yuvarlak köşeli dikdörtgen); kaynama: poz başına kontur oynaması."""
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        c, s = math.cos(th), math.sin(th)
        x = a * math.copysign(abs(c) ** (2 / us), c); y = b * math.copysign(abs(s) ** (2 / us), s)
        if kaynama:
            d = math.hypot(x, y) or 1.0
            k = kaynama * _kaynama(i, n, seed)
            x += k * x / d; y += k * y / d
        pts.append((cx + x, cy + y))
    return pts


def yumusak_yol(pts):
    """Kapalı Catmull-Rom eğrisi."""
    n = len(pts); p = skia.Path(); p.moveTo(*pts[0])
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        p.cubicTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                  p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1])
    p.close()
    return p


def blob(cx, cy, a, b, us=2.0, kaynama=1.2, seed=0, n=72):
    return yumusak_yol(noktalar(cx, cy, a, b, us, n, kaynama, seed))


_KOCA = skia.Path.Rect(skia.Rect.MakeLTRB(-1e4, -1e4, 1e4, 1e4))


def _halka(yol, dx, dy):
    """yol içinde kalan, (dx,dy) kaydırılmış kopyanın dışındaki şerit."""
    k = skia.Path(yol); k.offset(dx, dy)
    return skia.Op(yol, k, skia.PathOp.kDifference_PathOp)


def _bulanik(renk, sigma, a=1.0):
    return skia.Paint(AntiAlias=True, Color=alfa(renk, a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sigma))


def golge(cv, yol, guc=1.0, yuks=1.0):
    """Zemine düşen yumuşak gölge (ışık sol üstten)."""
    if guc <= 0: return
    cv.save(); cv.translate(10 * yuks, 18 * yuks); cv.drawPath(yol, _bulanik(0xFF5A3A22, 16 * yuks, 0.20 * guc)); cv.restore()
    cv.save(); cv.translate(3, 5); cv.drawPath(yol, _bulanik(0xFF5A3A22, 4, 0.22 * guc)); cv.restore()


def hamur(cv, yol, renk, kalinlik=0.0, golge_guc=1.0, iz=None, hacim=1.0, yuks=1.0):
    """Hamur parça: gölge, kalınlık (yan yüz), gövde, kenar gölgesi + üst ışık, parmak izi."""
    golge(cv, yol, golge_guc, yuks)
    if kalinlik > 0:
        yan = koyu(renk, 0.80)
        pn = skia.Paint(AntiAlias=True, Color=yan)
        k = kalinlik
        while k > 0:
            cv.save(); cv.translate(0, k); cv.drawPath(yol, pn); cv.restore()
            k -= 2.0
    cv.drawPath(yol, skia.Paint(AntiAlias=True, Color=renk))
    b = yol.computeTightBounds()
    s = max(4.0, min(b.width(), b.height()) * 0.09) * hacim
    cv.save(); cv.clipPath(yol, doAntiAlias=True)
    cv.drawPath(_halka(yol, -0.5 * s, -0.9 * s), _bulanik(koyu(renk, 0.62), s * 0.9, 0.55))   # alt-sağ kenar gölgesi
    cv.drawPath(_halka(yol, 0.45 * s, 0.8 * s), _bulanik(acik(renk, 0.6), s * 0.75, 0.6))     # üst-sol ışık
    if iz is not None:
        parmak_izi(cv, b, iz, renk)
    cv.restore()


def parmak_izi(cv, b, seed, renk):
    """Yüzeyde birkaç ince eş merkezli kıvrım (hamurda kalan parmak izi)."""
    pn = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6, Color=alfa(koyu(renk, 0.7), 0.10))
    for j in range(2):
        cx = b.left() + b.width() * (0.25 + 0.5 * _h(seed, j, 1)); cy = b.top() + b.height() * (0.25 + 0.5 * _h(seed, j, 2))
        r0 = min(b.width(), b.height()) * (0.10 + 0.06 * _h(seed, j, 3)); ac = 360 * _h(seed, j, 4)
        for k in range(5):
            r = r0 + k * 5.5
            cv.save(); cv.translate(cx, cy); cv.rotate(ac); cv.scale(1.0, 0.7)
            cv.drawArc(skia.Rect.MakeLTRB(-r, -r, r, r), 200 + 15 * k, 120 + 10 * _h(seed, j, k), False, pn)
            cv.restore()


def cukur(cv, x, y, r, renk, derin=1.0):
    """Hamura bastırılmış boş yuva: içe göçük (ışık ters)."""
    if r <= 0.5: return
    yol = skia.Path.Circle(x, y, r)
    cv.drawPath(yol, skia.Paint(AntiAlias=True, Color=koyu(renk, 1 - 0.05 * derin)))
    s = r * 0.22
    cv.save(); cv.clipPath(yol, doAntiAlias=True)
    cv.drawPath(_halka(yol, s, s * 1.2), _bulanik(koyu(renk, 0.55), s * 0.8, 0.55 * derin))   # üst-sol iç gölge
    cv.drawPath(_halka(yol, -s * 0.7, -s), _bulanik(acik(renk, 0.7), s * 0.7, 0.6 * derin))   # alt-sağ ışık
    cv.restore()


def hamur_yazi(cv, s, x, y, boy, renk, t, kimlik, olcek=1.0, kalinlik=None, aci=0.0, sx=1.0, sy=1.0, agirlik=800):
    if not s or olcek <= 0.01: return
    yol, w, h = _yazi_yolu(s, boy, agirlik)
    p = _poz(t)
    jx, jy, ja = (_h(kimlik, p, 1) - .5) * 2.4, (_h(kimlik, p, 2) - .5) * 2.4, (_h(kimlik, p, 3) - .5) * 1.0
    cv.save(); cv.translate(x + jx, y + jy); cv.rotate(aci + ja); cv.scale(olcek * sx, olcek * sy)
    hamur(cv, yol, renk, kalinlik if kalinlik is not None else boy * 0.06, golge_guc=0.9, iz=None, hacim=0.5)
    cv.restore()


def serit(cv, s, x, y, boy, renk, yazi_renk, t, kimlik, p=1.0, aci=-3.0):
    """Hamur şerit (yuvarlanmış kalın bant) üstünde yazı."""
    if p <= 0 or not s: return
    w = yazi_genislik(s, boy, 700) + boy * 1.2; h = boy * 1.35
    sk = ziplama(p)
    cv.save(); cv.translate(x, y); cv.rotate(aci); cv.scale(sk, sk)
    hamur(cv, blob(0, 0, w / 2, h / 2, us=5.5, kaynama=1.0, seed=_poz(t) * 7 + kimlik), renk, kalinlik=7, iz=kimlik)
    hamur_yazi(cv, s, 0, -boy * 0.02, boy, yazi_renk, t, kimlik + 1, kalinlik=2.5, agirlik=700)
    cv.restore()


# ---------- kart ----------
def yuva_yerleri(n, w, h):
    """n yuvayı iki satıra dağıtır; kartın merkezine göre (x, y) ve yarıçap."""
    sut = math.ceil(n / 2)
    alan_w, alan_h = w * 0.86, h * 0.50
    ad = alan_w / sut
    r = min(ad * 0.36, alan_h * 0.24)
    out = []
    for i in range(n):
        sat, s = divmod(i, sut)
        out.append((-alan_w / 2 + ad * (s + 0.5), h * 0.08 + (sat - 0.5) * alan_h * 0.52))
    return out, r


def damga_izi(cv, x, y, r, t, t0, seed):
    """Basılmış yuva: kahve çekirdeği biçimli amber hamur; basıldığı an ezilip oturur."""
    if t < t0: return
    sx, sy = ezilme(t, t0, 0.4, 0.3)
    cv.save(); cv.translate(x, y); cv.rotate(-25 + 10 * _h(seed)); cv.scale(sx, sy)
    yol = blob(0, 0, r * 0.82, r * 1.0, us=2.1, kaynama=0.8, seed=_poz(t) * 3 + seed, n=48)
    hamur(cv, yol, AMBER, kalinlik=4, golge_guc=0.6, iz=seed, yuks=0.4)
    oluk = skia.Path(); oluk.moveTo(0, -r * 0.72); oluk.cubicTo(r * 0.28, -r * 0.25, -r * 0.28, r * 0.25, 0, r * 0.72)
    cv.drawPath(oluk, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=r * 0.16,
                                 StrokeCap=skia.Paint.kRound_Cap, Color=koyu(AMBER, 0.62)))
    cv.restore()


def kart(cv, t, x, y, w, h, n, dolu=(), renk=KART, aci=0.0, olcek=1.0, kimlik=0, form=1.0, yuva_p=1.0, etiket=True,
         sayac=None, soluk=0.0):
    """Hamur sadakat kartı. form: 0 top → 1 kart (yoğrulma). dolu: [(yuva indeksi, basılma anı)]."""
    if olcek <= 0.01: return
    p = _poz(t)
    renk = karis(renk, GRI, soluk)
    a, b = lerp(h * 0.42, w / 2, form), h / 2 * lerp(0.84, 1.0, form)
    cv.save(); cv.translate(x, y); cv.rotate(aci); cv.scale(olcek, olcek)
    hamur(cv, blob(0, 0, a, b, us=lerp(2.0, 5.2, form), kaynama=1.4, seed=p * 13 + kimlik, n=96), renk,
          kalinlik=lerp(6, 16, form), iz=kimlik + 3)
    if form > 0.98:
        yerler, r = yuva_yerleri(n, w, h)
        for i, (yx, yy) in enumerate(yerler):
            pi = clamp(yuva_p * n - i)  # yuvalar soldan sağa sırayla bastırılır
            cukur(cv, yx, yy, r * out_back(pi, 1.5), renk, derin=pi)
        for i, t0 in dolu:
            if i < n: damga_izi(cv, yerler[i][0], yerler[i][1], r, t, t0, kimlik * 10 + i)
        if etiket:
            m = _ayar('marka', 'DEMLİ KAHVE')
            boy = 40
            ew = yazi_genislik(m, boy, 700) + 50
            ex, ey = -w / 2 + 40 + ew / 2, -h / 2 + 52
            hamur(cv, blob(ex, ey, ew / 2, 30, us=6, kaynama=0.6, seed=p * 5 + kimlik + 1), karis(KAHVE, GRI, soluk * 0.8),
                  kalinlik=5, golge_guc=0.5, yuks=0.3)
            hamur_yazi(cv, m, ex, ey, boy, KREM, t, kimlik + 77, kalinlik=1.5, agirlik=700)
        if sayac:
            hamur_yazi(cv, sayac, w / 2 - 95, -h / 2 + 52, 46, karis(TURUNCU, GRI, soluk), t, kimlik + 88, kalinlik=3)
    cv.restore()


def damga_aleti(cv, x, y, s, t, kimlik, ez=(1.0, 1.0)):
    """Hamur damga: kahve rengi sap + amber taban."""
    cv.save(); cv.translate(x, y); cv.scale(s * ez[0], s * ez[1])
    p = _poz(t)
    hamur(cv, blob(0, -150, 46, 70, us=2.2, kaynama=1.0, seed=p * 3 + kimlik), KAHVE, kalinlik=6, golge_guc=0.7, yuks=2.0, iz=kimlik)
    hamur(cv, blob(0, -62, 36, 30, us=3.0, kaynama=0.8, seed=p * 3 + kimlik + 1), koyu(KAHVE, 0.9), kalinlik=4, golge_guc=0.4, yuks=2.0)
    hamur(cv, blob(0, -22, 92, 34, us=4.5, kaynama=1.0, seed=p * 3 + kimlik + 2), AMBER, kalinlik=10, golge_guc=0.8, yuks=2.0, iz=kimlik + 1)
    cv.restore()


def konfeti(cv, t, VW, VH, t0):
    if t < t0: return
    for i in range(16):
        ts = t0 + 0.04 * i
        if t < ts: continue
        u = t - ts
        ang = math.pi * (1.1 + 0.8 * _h(i, 1)); hiz = 900 + 500 * _h(i, 2)
        x = VW / 2 + math.cos(ang) * hiz * u * 0.9 + (_h(i, 3) - .5) * VW * 0.3
        y = VH * 0.45 + math.sin(ang) * hiz * u + 1400 * u * u
        yer = VH * (0.80 + 0.12 * _h(i, 4))
        if y > yer:  # yere düşünce yassılaşıp kalır
            y = yer
        r = 14 + 10 * _h(i, 5)
        sq = 0.55 if y >= yer else 1.0
        cv.save(); cv.translate(x, y); cv.scale(1 / sq ** 0.5, sq)
        hamur(cv, blob(0, 0, r, r, kaynama=0.8, seed=_poz(t) + i, n=36), KONFETI[i % len(KONFETI)], kalinlik=3, golge_guc=0.5, yuks=0.3)
        cv.restore()


# ---------- sahneler (tasarım birimi: kısa kenar = 1080) ----------
def _cikis(t, t0, d=0.22):
    """t0'dan sonra küçülerek yok olma ölçeği."""
    return 1.0 - in_cubic(prog(t, t0, d))


def sahne(cv, t, VW, VH, dik):
    k = kart_ayar()
    cx = VW / 2
    w, h = (820, 520) if dik else (760, 480)
    ky = VH * (0.53 if dik else 0.56)
    tx = cx if dik else VW * 0.36  # 16:9'da yazılar kartın sağına

    # --- 1. vuruş: top düşer, yoğrulup boş karta dönüşür ---
    if t < Z['gecis2'] + 0.36:
        u = prog(t, Z['dus'], Z['yere'] - Z['dus'])
        if t < Z['yere']:
            yy = lerp(-300, ky, in_cubic(u)); form = 0.0; sx, sy = 0.92, 1.08
        else:
            yy = ky; form = out_cubic(prog(t, Z['yere'] + 0.05, Z['kart'] - Z['yere']))
            sx, sy = ezilme(t, Z['yere'], 0.5, 0.25)
        sark = in_out_cubic(prog(t, Z['sarkma'], 0.7))
        cik = in_cubic(prog(t, Z['gecis2'], 0.3))
        if t >= Z['dus']:
            cv.save(); cv.translate(tx if not dik else cx, yy); cv.scale(sx, sy); cv.translate(-(tx if not dik else cx), -yy)
            kart(cv, t, (tx if not dik else cx) + 30 * sark, yy + 20 * sark, w, h, k['bos'], aci=-4 * sark,
                 olcek=lerp(1, 0.86, cik), form=form * (1 - cik), kimlik=1, yuva_p=prog(t, Z['yuva'], 0.5),
                 sayac=f"0/{k['bos']}" if t >= Z['yuva'] + 0.4 else None, soluk=0.45 * sark)
            cv.restore()
        sc = ziplama(prog(t, Z['kanca'], 0.3)) * _cikis(t, Z['gecis2'])
        yx = cx if dik else VW * 0.76
        hamur_yazi(cv, METIN['kanca'], yx, ky - (500 if dik else 140), 230 if len(METIN['kanca']) <= 3 else 190, TURUNCU, t, 11,
                   olcek=sc, aci=-4 + 3 * sark)
        serit(cv, METIN['kanca_alt'], yx, ky + (420 if dik else 120), 62, KAHVE, KREM, t, 12,
              p=prog(t, Z['kanca_alt'], 0.3) * _cikis(t, Z['gecis2']), aci=3)
        return

    # --- 2. vuruş: kart yeniden yoğrulur, iki yuva önceden basılır ---
    dolu = [(i, Z['bas1'] if i % 2 == 0 else Z['bas2']) for i in range(min(k['hazir'], 2))]
    dolu += [(i, Z['bas2'] + 0.12 * (i - 1)) for i in range(2, k['hazir'])]
    if t < Z['gecis3'] + 0.36:
        form = out_cubic(prog(t, Z['gecis2'] + 0.30, 0.25))
        kx = cx if dik else VW * 0.36
        cik = in_cubic(prog(t, Z['gecis3'], 0.3))
        kart(cv, t, kx, ky, w, h, k['toplam'], dolu=dolu, olcek=lerp(1, 0.9, cik), form=max(form, 0.0) if form > 0 else 0.0,
             kimlik=2, yuva_p=prog(t, Z['yuva2'], 0.35), sayac=f"{k['hazir']}/{k['toplam']}" if t >= Z['sayac'] else None)
        # damga aleti iner, iki kez basar, çıkar
        if Z['damga'] <= t < Z['bas2'] + 0.5:
            yerler, r = yuva_yerleri(k['toplam'], w, h)
            hedef = [kx + yerler[0][0], kx + yerler[1][0]]
            if t < Z['bas1']:
                dx = hedef[0]; dy = lerp(ky - 900, ky + yerler[0][1], in_cubic(prog(t, Z['damga'], Z['bas1'] - Z['damga'])))
            elif t < Z['bas2']:
                u = prog(t, Z['bas1'] + 0.06, Z['bas2'] - Z['bas1'] - 0.06)
                dx = lerp(hedef[0], hedef[1], in_out_cubic(u)); dy = ky + yerler[0][1] - 120 * math.sin(math.pi * u)
            else:
                dx = hedef[1]; dy = lerp(ky + yerler[1][1], ky - 1000, in_cubic(prog(t, Z['bas2'] + 0.1, 0.35)))
            ez = ezilme(t, Z['bas2'], 0.3, 0.2) if t >= Z['bas2'] else ezilme(t, Z['bas1'], 0.3, 0.2)
            damga_aleti(cv, dx, dy - r * 0.4, 1.35, t, 30, ez=(ez[0], ez[1]))
        sc = ziplama(prog(t, Z['sayi'], 0.35)) * _cikis(t, Z['gecis3'])
        sx, sy = ezilme(t, Z['sayi'] + 0.22, 0.45, 0.18)
        yx = cx if dik else VW * 0.77
        hamur_yazi(cv, METIN['sayi'], yx, ky - (540 if dik else 110), 300 if len(METIN['sayi']) <= 3 else 250, TURUNCU, t, 21,
                   olcek=sc, aci=-3, sx=sx, sy=sy)
        serit(cv, METIN['sayi_alt'], yx, ky + (430 if dik else 130), 60, NANE, KAHVE, t, 22,
              p=prog(t, Z['sayi_alt'], 0.3) * _cikis(t, Z['gecis3']), aci=-2)
        return

    # --- 3. vuruş: iki kart yan yana (boş / başlamış), sakin ---
    if t < Z['gecis4'] + 0.36:
        cik = in_cubic(prog(t, Z['gecis4'], 0.28))
        g1 = out_back(prog(t, Z['gecis3'] + 0.3, 0.4), 1.4)
        g2 = out_cubic(prog(t, Z['gecis3'] + 0.25, 0.4))
        if dik:
            k1 = (cx, VH * 0.33); k2 = (cx, VH * 0.69); oc = 0.80
        else:
            k1 = (VW * 0.29, VH * 0.52); k2 = (VW * 0.71, VH * 0.52); oc = 0.72
        bob = math.sin(2 * math.pi * (_poz(t) / POZ) * 0.9) * 6
        kart(cv, t, lerp(-500, k1[0], g1), k1[1], w, h, k['bos'], olcek=oc * (1 - cik), kimlik=3, aci=-3,
             sayac=f"0/{k['bos']}", soluk=0.55)
        kart(cv, t, lerp(cx, k2[0], g2), lerp(ky, k2[1], g2) + bob, w, h, k['toplam'], dolu=[(i, -1) for i, _ in dolu],
             olcek=lerp(0.9, oc, g2), kimlik=2, aci=2, sayac=f"{k['hazir']}/{k['toplam']}")
        o1 = (k1[0], k1[1] + h * oc * 0.5 + 70) if dik else (k1[0], k1[1] + h * oc * 0.5 + 80)
        o2 = (k2[0], k2[1] + h * oc * 0.5 + 70) if dik else (k2[0], k2[1] + h * oc * 0.5 + 80)
        serit(cv, METIN['kucuk'], o1[0], o1[1], 54, GRI, koyu(GRI, 0.45), t, 31, p=prog(t, Z['kucuk'], 0.3) * _cikis(t, Z['gecis4']), aci=-3)
        serit(cv, METIN['buyuk'], o2[0], o2[1], 60, TURUNCU, KREM, t, 32, p=prog(t, Z['buyuk'], 0.3) * _cikis(t, Z['gecis4']), aci=3)
        return

    # --- 4. vuruş: çağrı + marka, hamur konfeti ---
    g = out_cubic(prog(t, Z['gecis4'] + 0.2, 0.4))
    if dik:
        k2 = (cx, VH * 0.69); hk = (cx, VH * 0.36); oc0, oc1 = 0.80, 0.78
    else:
        k2 = (VW * 0.71, VH * 0.52); hk = (VW * 0.30, VH * 0.50); oc0, oc1 = 0.72, 0.72
    konfeti(cv, t, VW, VH, Z['konfeti'])  # kartın arkasında kalır
    kart(cv, t, lerp(k2[0], hk[0], g), lerp(k2[1], hk[1], g), w, h, k['toplam'], dolu=[(i, -1) for i, _ in dolu],
         olcek=lerp(oc0, oc1, g), kimlik=2, aci=lerp(2, -3, g), sayac=f"{k['hazir']}/{k['toplam']}")
    bx, by = (cx, VH * 0.62) if dik else (VW * 0.72, VH * 0.42)
    p = prog(t, Z['cagri'], 0.35)
    if p > 0:
        boy = 92 if dik else 84
        bw = yazi_genislik(METIN['cagri'], boy, 800) + 130; bh = boy * 1.55
        sk = ziplama(p); sx, sy = ezilme(t, Z['cagri'] + 0.25, 0.45, 0.15)
        cv.save(); cv.translate(bx, by); cv.rotate(-2); cv.scale(sk * sx, sk * sy)
        hamur(cv, blob(0, 0, bw / 2, bh / 2, us=5.0, kaynama=1.2, seed=_poz(t) * 11 + 41), KAHVE, kalinlik=14, iz=41)
        hamur_yazi(cv, METIN['cagri'], 0, -boy * 0.04, boy, KREM, t, 42, kalinlik=3)
        cv.restore()
    m = _ayar('marka', 'DEMLİ KAHVE')
    hamur_yazi(cv, m, bx, by + (190 if dik else 170), 70, AMBER, t, 43, olcek=ziplama(prog(t, Z['marka'], 0.3)), aci=1.5, agirlik=800)
    dip = _ayar('dipnot', '')
    if dip and t >= Z['marka'] + 0.25:
        f = skia.Font(yazi_tipi_baloo(600), 30 if dik else 26)
        a = clamp((t - Z['marka'] - 0.25) / 0.25)
        dw = f.measureText(dip)
        cv.drawString(dip, (VW - dw) / 2, VH - (110 if dik else 60), f, skia.Paint(AntiAlias=True, Color=alfa(koyu(KAHVE, 1.0), 0.55 * a)))


# ---------- fon + tanecik ----------
@functools.lru_cache(maxsize=8)
def _tanecik(W, H, i):
    rng = np.random.default_rng(1000 + i)
    g = np.clip(128 + rng.normal(0, 7, (H, W)), 0, 255).astype(np.uint8)
    a = np.empty((H, W, 4), np.uint8); a[..., 0] = a[..., 1] = a[..., 2] = g; a[..., 3] = 255
    return skia.Image.fromarray(a)


def fon(cv, VW, VH):
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, VH)], [FON_UST, FON_ALT])
    cv.drawRect(skia.Rect.MakeWH(VW, VH), skia.Paint(Shader=sh, Dither=True))


_ONBELLEK = {'anahtar': None, 'img': None}


def kare(cv, t, W, H):
    """t'nin saf fonksiyonu; aynı pozdaki kareler önbellekten gelir (12 poz/sn)."""
    p = _poz(min(t, SURE - 1e-3))
    anahtar = (W, H, p, tuple(sorted(METIN.items(), key=str)), repr(sorted(motor.STIL_AYAR.items(), key=str)))
    if _ONBELLEK['anahtar'] != anahtar:
        surf = skia.Surface(W, H)
        with surf as c:
            u = min(W, H) / 1080; VW, VH = W / u, H / u
            c.save(); c.scale(u, u)
            fon(c, VW, VH)
            sahne(c, p / POZ, VW, VH, H > W)
            c.restore()
            c.drawImage(_tanecik(W, H, p % 4), 0, 0, skia.SamplingOptions(), skia.Paint(BlendMode=skia.BlendMode.kOverlay))
        _ONBELLEK.update(anahtar=anahtar, img=surf.makeImageSnapshot())
    cv.drawImage(_ONBELLEK['img'], 0, 0)


# =====================================================================================
#  SES: marimba + pizz bas + yumuşak davul; hamur efektleri (vıcık, pıt, tok)
# =====================================================================================
BPM = 100
VURUS = 60 / BPM


def marimba(m, d=0.8, parlak=1.0):
    e, tt = zarf(d, a=0.002, dec=0.22)
    f = mtof(m)
    x = np.sin(2 * np.pi * f * tt) + 0.30 * parlak * np.sin(2 * np.pi * f * 4.0 * tt) * np.exp(-tt / 0.03) \
        + 0.10 * np.sin(2 * np.pi * f * 10.0 * tt) * np.exp(-tt / 0.008)
    return x * e


def bas(m, d=0.5):
    e, tt = zarf(d, a=0.004, dec=0.18)
    f = mtof(m)
    return (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) * np.exp(-tt / 0.06)) * e


def ped(notalar, d):
    n = int(d * SR); tt = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * mtof(m) * (1 + dt) * tt) for m in notalar for dt in (-0.002, 0.002))
    e = np.minimum(tt / 0.6, 1) * np.minimum((d - tt) / 0.6, 1)
    return lp_hizli(x * e, 1800) / (2 * len(notalar))


AKORLAR = [(53, 57, 60, 65), (50, 53, 57, 62), (46, 50, 53, 58), (48, 52, 55, 60)]  # F Dm Bb C


def _sakin(tb): return tb < 3.0 or 6.0 <= tb < 7.9


def muzik(n):
    m = np.zeros((n, 2))
    olcu = VURUS * 4
    for j in range(int(SURE / olcu) + 1):
        ak = AKORLAR[j % 4] if j * olcu < 8.0 else AKORLAR[0]
        d = min(olcu + 0.6, SURE - j * olcu)
        if d > 0.3: ekle(m, j * olcu, ped([x + 12 for x in ak[1:]], d), 0.10)
    desen = [0, 2, 3, 1, 2, 3, 1, 3]
    adim = VURUS / 2
    i = 0; tb = 0.0
    while tb < SURE - 0.7:
        ak = AKORLAR[int(tb / olcu) % 4] if tb < 8.0 else AKORLAR[0]
        nota = ak[desen[i % 8]] + 12 + (12 if i % 8 in (2, 5) else 0)
        sakin = _sakin(tb)
        if not (sakin and i % 2):
            ekle(m, tb, marimba(nota, parlak=0.5 if sakin else 1.0), 0.15 if sakin else 0.22, pan=0.3 * math.sin(i * 1.3))
        if i % 2 == 0:
            ekle(m, tb, bas(ak[0] - 12 + (7 if i % 4 == 2 and not sakin else 0)), 0.30 if not sakin else 0.20)
        i += 1; tb += adim
    rng = np.random.default_rng(7)
    for k in range(int(SURE / VURUS)):
        tb = k * VURUS
        if tb > SURE - 0.6 or _sakin(tb): continue
        e, tt = zarf(0.25, a=0.002, dec=0.07)
        f = 120 * np.exp(-tt / 0.03) + 50
        ekle(m, tb, np.sin(2 * np.pi * np.cumsum(f) / SR) * e, 0.36)
        if k % 2 == 1:  # el çırpma
            ekle(m, tb, fx.clap(rng, 0.12) * 0.9, 0.16, pan=-0.15)
        ekle(m, tb + VURUS / 2, fx.shaker(rng, 0.05) * 0.5, 0.05, pan=0.4)
    # sayı öncesi yükselen marimba tremolosu + vurgu
    for j in range(8):
        ekle(m, Z['sayi'] - 0.4 + j * 0.05, marimba(72 + j, d=0.3), 0.05 + j * 0.012, pan=0.2)
    for j, nn in enumerate((77, 81, 84, 89)):
        ekle(m, Z['sayi'] + j * 0.05, marimba(nn, d=1.0, parlak=1.2), 0.13, pan=(j - 1.5) * 0.3)
    # final akoru
    for j, nn in enumerate((65, 69, 72, 77, 81)):
        ekle(m, Z['cagri'] + j * 0.04, marimba(nn, d=1.5, parlak=1.0), 0.15, pan=(j - 2) * 0.2)
    ekle(m, Z['cagri'], bas(41, d=1.5), 0.32)
    return m


def vicik(d=0.22, seed=0, f0=900, f1=260):
    """Islak hamur sesi: bant geçiren gürültü, düşen merkez frekans, hızlı titreşim."""
    n = int(d * SR); tt = np.arange(n) / SR
    x = gurultu(d, seed)
    parca = 8; cikti = np.zeros(n); k = n // parca
    for j in range(parca):  # zamanla değişen bant (parça parça)
        fc = f0 * (f1 / f0) ** (j / parca)
        y = lp_hizli(x, fc * 1.6) - lp_hizli(x, fc * 0.6)
        cikti[j * k:(j + 1) * k] = y[j * k:(j + 1) * k]
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * (38 + 20 * _h(seed)) * tt)
    e = np.minimum(tt / 0.01, 1) * np.exp(-tt / (d * 0.4))
    return cikti * trem * e * 2.2


def pit(f0=420, f1=900, d=0.09):  # "bloop": yükselen tatlı pıt
    tt = np.arange(int(d * SR)) / SR
    f = f0 * (f1 / f0) ** (tt / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(tt / 0.004, 1) * np.exp(-tt / (d * 0.45))


def tok(f0=200, f1=80, d=0.16, seed=0):  # yere düşen/basılan hamur
    tt = np.arange(int(d * SR)) / SR
    f = f0 * (f1 / f0) ** (tt / d)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.05)
    return x + lp_hizli(gurultu(d, seed), 700) * np.exp(-tt / 0.03) * 0.8


def sfx(n):
    s = np.zeros((n, 2))
    k = kart_ayar()
    ekle(s, Z['dus'], pit(700, 380, 0.25) * 0.4, 0.3)
    ekle(s, Z['yere'], tok(220, 70, 0.2, 1), 1.0)
    ekle(s, Z['yere'] + 0.04, vicik(0.3, 2), 0.8)
    for i in range(k['bos']):
        ekle(s, Z['yuva'] + i * 0.5 / k['bos'], pit(500 + 30 * i, 300, 0.05), 0.25, pan=-0.5 + i / k['bos'])
    ekle(s, Z['kanca'] + 0.05, pit(380, 820, 0.12), 0.5)
    ekle(s, Z['kanca_alt'] + 0.05, pit(520, 900, 0.08), 0.35, pan=0.2)
    ekle(s, Z['sarkma'] + 0.1, pit(500, 260, 0.5) * 0.6, 0.25)  # sönen "üf"
    for ts in (Z['gecis2'], Z['gecis3'], Z['gecis4']):
        ekle(s, ts + 0.05, vicik(0.28, int(ts * 10), 700, 220), 0.6)
    for i in range(k['toplam']):
        ekle(s, Z['yuva2'] + i * 0.35 / k['toplam'], pit(520 + 25 * i, 320, 0.05), 0.2, pan=-0.5 + i / k['toplam'])
    for ts in (Z['bas1'], Z['bas2']):
        ekle(s, ts, tok(160, 60, 0.18, int(ts * 10)), 1.0)
        ekle(s, ts + 0.02, vicik(0.2, int(ts * 7), 1100, 400), 0.7)
    ekle(s, Z['sayac'], pit(600, 1000, 0.07), 0.3)
    ekle(s, Z['sayi'] + 0.05, pit(300, 900, 0.16), 0.6)
    ekle(s, Z['sayi'] + 0.22, tok(180, 90, 0.15, 5), 0.5)
    ekle(s, Z['sayi_alt'] + 0.05, pit(520, 900, 0.08), 0.35, pan=-0.2)
    ekle(s, Z['kucuk'] + 0.05, pit(420, 300, 0.10), 0.25, pan=-0.3)
    ekle(s, Z['buyuk'] + 0.05, pit(520, 980, 0.10), 0.4, pan=0.3)
    ekle(s, Z['cagri'] + 0.05, pit(300, 900, 0.16), 0.6)
    ekle(s, Z['cagri'] + 0.25, tok(180, 90, 0.15, 6), 0.5)
    ekle(s, Z['marka'] + 0.05, pit(600, 1000, 0.08), 0.35)
    for i in range(16):
        ekle(s, Z['konfeti'] + 0.04 * i + 0.25 + 0.1 * _h(i, 9), pit(700 + 300 * _h(i, 8), 1200, 0.04), 0.12, pan=math.sin(i))
    return s


AYAR = {'kapak_t': 5.0, 'sfx_db': -10.0}
