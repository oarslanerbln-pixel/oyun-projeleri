"""Kâğıt kesik (paper cut-out) stop-motion stili.

Her parça el kesimi kenarlı bir kâğıt; altında yumuşak gölge, bütün karede kâğıt dokusu.
Nesne hareketi saniyede 12 poza kuantize edilir ve her pozda parçalar hafifçe titrer (stop-motion hissi).
Ekran yazıları motor.METIN'den gelir; kullanım için stil.py'ye bakın.
"""
import functools, math, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motor import *  # noqa: E402,F403

POZ = 12  # stop-motion poz/sn

# ---------- palet ----------
KRAFT, KAGIT = 0xFFF4EBD9, 0xFFFFFBF2
GOK1, GOK2, GOK3 = 0xFFBFE0E8, 0xFFDCD3EF, 0xFFCDE8D6
TEPE1, TEPE2, TEPE3 = 0xFFA6D1A6, 0xFF6FAE7C, 0xFF3F7F5C
GUNES, KIRMIZI, KOYU_KIRMIZI = 0xFFF6A84B, 0xFFE5574B, 0xFFB43B33
LACI, SARI, TEN, SAC, KAHVE = 0xFF263247, 0xFFF7CF4A, 0xFFF2C29B, 0xFF4A3426, 0xFF8B5A3C
PEMBE, MAVI = 0xFFF2A7A0, 0xFF5B8DEF

Z = dict(
    tepe=0.0, gunes=0.25, kahraman=0.45, hergun=0.40, adim1=1.05, etiket=1.45,
    gecis2=2.80, merdiven=3.20, takvim=3.20, x37=4.45,
    gecis3=5.80, filiz=6.15, kucuk=6.20, agac=6.70, buyuk=6.80,
    gecis4=7.80, bayrak=8.30, konfeti=8.70,
)

# ---------- yollar (tasarım birimi: kısa kenar = 1080) ----------
import skia  # noqa: E402


def _poz_t(t): return math.floor(t * POZ) / POZ


def _h(*a):  # deterministik 0..1
    x = math.sin(sum((i + 1) * 12.9898 * v for i, v in enumerate(a)) + 78.233) * 43758.5453
    return x - math.floor(x)


@functools.lru_cache(maxsize=None)
def yirtik(nokta, seed=0, amp=2.2, adim=14.0, kapali=True):
    """Makasla kesilmiş kenar: çokgen sık örneklenir, kenarlar boyunca yumuşak (düşük frekanslı) dalgalanma alır.
    Köşeler keskin kalır, kenar pürüzsüz ama elle kesilmiş gibi hafif kıvrımlı olur."""
    pts = list(nokta)
    seg = pts + [pts[0]] if kapali else pts
    rng = np.random.default_rng(seed)
    a = amp * 0.45  # eski değerler pürüzlüydü; yumuşak dalga için genliği düşür
    # dalga, tüm çevre boyunca sürekli bir fonksiyon: kısa kenarlı şekillerde (daire) tırtık oluşmaz
    ks = rng.uniform(1 / 260, 1 / 120, 3); fz = rng.uniform(0, 6.28, 3); ag = (1.0, 0.5, 0.25)
    dalga = lambda s_: a * sum(g * math.sin(2 * math.pi * k * s_ + f) for g, k, f in zip(ag, ks * (1, 2.1, 4.3), fz))
    out = []; yol = 0.0
    for (x0, y0), (x1, y1) in zip(seg, seg[1:]):
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / 4))
        nx, ny = (-(y1 - y0) / (L or 1), (x1 - x0) / (L or 1))
        for i in range(n):
            p = i / n; d = dalga(yol + p * L)
            out.append((x0 + (x1 - x0) * p + nx * d, y0 + (y1 - y0) * p + ny * d))
        yol += L
    if not kapali: out.append(seg[-1])
    path = skia.Path(); path.moveTo(*out[0])
    for q in out[1:]: path.lineTo(*q)
    if kapali: path.close()
    return path


def daire(cx, cy, r, n=None):
    n = n or max(64, int(r * 1.2))
    return tuple((cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n))


def kutu(x, y, w, h): return ((x, y), (x + w, y), (x + w, y + h), (x, y + h))


def tepe_noktalari(x0, x1, y, h, seed, n=7):
    rng = np.random.default_rng(seed)
    pts = [(x0, y + 900)]
    for i in range(n + 1):
        xx = x0 + (x1 - x0) * i / n
        pts.append((xx, y - h * (0.55 + 0.45 * math.sin(i * 1.7 + seed)) - rng.uniform(0, h * 0.2)))
    pts.append((x1, y + 900))
    # yumuşat: her ara noktaya ortalama ekle
    yum = []
    for a, b in zip(pts, pts[1:]):
        yum += [a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 6)]
    return tuple(yum + [pts[-1]])


# ---------- çizim temel taşları ----------
_GOLGE_BLUR = {}


def parca(cv, path, renk, kalk=1.0, kimlik=None, t=0.0, titre=1.0):
    """Kâğıt parça: gölge + dolgu. kimlik verilirse poz başına hafif titreme."""
    cv.save()
    if kimlik is not None and titre:
        k = math.floor(t * POZ)
        b = path.getBounds(); cx, cy = b.centerX(), b.centerY()
        cv.translate((_h(k, kimlik, 1) - .5) * 2.6 * titre, (_h(k, kimlik, 2) - .5) * 2.6 * titre)
        cv.rotate((_h(k, kimlik, 3) - .5) * 0.7 * titre, cx, cy)
    key = round(kalk, 2)
    if key not in _GOLGE_BLUR:
        _GOLGE_BLUR[key] = skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 3.5 + 5 * kalk)
    g = skia.Paint(AntiAlias=True, Color=0x55000000, MaskFilter=_GOLGE_BLUR[key])
    cv.save(); cv.translate(1.5 * kalk, 4.5 * kalk); cv.drawPath(path, g); cv.restore()
    cv.drawPath(path, skia.Paint(AntiAlias=True, Color=renk))
    # kesik kenarda ince açık çizgi (kâğıdın beyaz özü)
    cv.drawPath(path, skia.Paint(AntiAlias=True, Color=0x26FFFFFF, Style=skia.Paint.kStroke_Style, StrokeWidth=1.2))
    cv.restore()


TF = yazi_tipi(800)


def kesik_yazi(cv, s, x, y, size, renk, t, kimlik, a=1.0, aralik=0.02, kalk=0.8, gelis=None):
    """Harf harf kesilmiş yazı: her harf ayrı kâğıt, ayrı gölge, ayrı küçük açı. gelis: harf başına 0..1."""
    f = skia.Font(TF, size); f.setSubpixel(True)
    gl = f.textToGlyphs(s); ws = f.getWidths(gl)
    top = sum(ws) + aralik * size * (len(s) - 1)
    xx = x - top / 2
    for i, (g, w) in enumerate(zip(gl, ws)):
        p = 1.0 if gelis is None else gelis(i)
        if p > 0 and s[i] != ' ':
            path = f.getPath(g)
            if path is not None:
                path = skia.Simplify(path) or path  # örtüşen konturlar kenar çizgisinde görünmesin
                cv.save()
                k = math.floor(t * POZ)
                cx = xx + w / 2
                sc = out_back(clamp(p))
                cv.translate(cx + (_h(k, kimlik, i, 4) - .5) * 2.2, y + (1 - clamp(p * 1.4)) * -size * 0.4 + (_h(k, kimlik, i, 5) - .5) * 2.2)
                cv.rotate((_h(kimlik, i, 6) - .5) * 7)
                cv.scale(sc, sc)
                cv.translate(-w / 2, size * 0.36)
                parca(cv, path, renk, kalk=kalk)
                cv.restore()
        xx += w + aralik * size
    return top


def serit(cv, s, x, y, size, t, kimlik, p=1.0, zemin=KAGIT, renk=LACI, aci=-2.0):
    """Kâğıt şerit üstünde yazı (etiket). p: 0..1 açılma."""
    if p <= 0: return
    f = skia.Font(TF, size); w = f.measureText(s)
    pw, ph = w + size * 0.9, size * 1.45
    cv.save(); cv.translate(x, y); cv.rotate(aci + (1 - out_back(p)) * -12)
    sc = out_back(p); cv.scale(sc, sc)
    parca(cv, yirtik(kutu(-pw / 2, -ph / 2, pw, ph), seed=kimlik, amp=1.6), zemin, kalk=1.1, kimlik=kimlik, t=t)
    # bant (seloteyp) uçları
    for sx in (-1, 1):
        cv.save(); cv.translate(sx * pw / 2, -ph / 2 + 4); cv.rotate(sx * 28)
        cv.drawRect(skia.Rect.MakeXYWH(-size * 0.35, -size * 0.13, size * 0.7, size * 0.26), skia.Paint(AntiAlias=True, Color=0x66FFF4C2))
        cv.restore()
    blob = skia.TextBlob(s, f)
    cv.drawTextBlob(blob, -w / 2, size * 0.36, skia.Paint(AntiAlias=True, Color=renk))
    cv.restore()


# ---------- kâğıt dokusu + vinyet ----------
@functools.lru_cache(maxsize=1)
def _doku():
    rng = np.random.default_rng(3)
    n = 512
    a = rng.normal(0, 1, (n, n))
    # lif: yatayda yumuşat
    k = np.ones(9) / 9
    lif = np.apply_along_axis(lambda r: np.convolve(np.r_[r[-8:], r, r[:8]], k, 'same')[8:-8], 1, rng.normal(0, 1, (n, n)))
    v = 248 + a * 2 + lif * 4
    v = np.clip(v, 205, 255).astype(np.uint8)
    rgba = np.dstack([v, v, (v * 0.985).astype(np.uint8), np.full_like(v, 255)])
    img = skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)
    return img.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat)


def doku(cv, W, H):
    cv.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=_doku(), BlendMode=skia.BlendMode.kMultiply))
    r = math.hypot(W, H) / 2
    sh = skia.GradientShader.MakeRadial((W / 2, H / 2), r, [0x00000000, 0x00000000, 0x38301A00], [0, 0.6, 1])
    cv.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))


# ---------- kahraman ----------
def kahraman(cv, x, y, s, t, kimlik=50, adim=0.0, el=0.0, zipla=0.0):
    """Kâğıt bebek: ayaklar (x, y) noktasında. adim: bacak salınımı, el: sağ kol kaldırma 0..1."""
    cv.save(); cv.translate(x, y - zipla); cv.scale(s, s)
    sal = math.sin(adim * math.pi) * 16
    for i, sgn in enumerate((-1, 1)):  # bacaklar
        cv.save(); cv.translate(sgn * 13, -78); cv.rotate(sgn * sal)
        parca(cv, yirtik(kutu(-9, 0, 18, 80), seed=kimlik + i, amp=1.0), LACI, kalk=0.6, kimlik=kimlik + i, t=t)
        parca(cv, yirtik(kutu(-11 + sgn * 3, 70, 26, 12), seed=kimlik + 10 + i, amp=0.8), SAC, kalk=0.4)
        cv.restore()
    # sol kol
    cv.save(); cv.translate(-34, -176); cv.rotate(12 - sal * 0.6)
    parca(cv, yirtik(kutu(-8, 0, 16, 74), seed=kimlik + 3, amp=1.0), KIRMIZI, kalk=0.7, kimlik=kimlik + 3, t=t)
    parca(cv, yirtik(daire(0, 78, 9), seed=kimlik + 4, amp=0.6), TEN, kalk=0.4)
    cv.restore()
    # gövde (kazak)
    parca(cv, yirtik(((-38, -182), (38, -182), (46, -70), (-46, -70)), seed=kimlik + 5, amp=1.4), KIRMIZI, kalk=1.0, kimlik=kimlik + 5, t=t)
    # sağ kol
    cv.save(); cv.translate(34, -176); cv.rotate(-12 + sal * 0.6 - el * 150)
    parca(cv, yirtik(kutu(-8, 0, 16, 74), seed=kimlik + 6, amp=1.0), KIRMIZI, kalk=0.7, kimlik=kimlik + 6, t=t)
    parca(cv, yirtik(daire(0, 78, 9), seed=kimlik + 7, amp=0.6), TEN, kalk=0.4)
    cv.restore()
    # atkı
    parca(cv, yirtik(kutu(-34, -190, 68, 20), seed=kimlik + 8, amp=1.0), SARI, kalk=0.6, kimlik=kimlik + 8, t=t)
    parca(cv, yirtik(kutu(10, -180, 16, 46), seed=kimlik + 9, amp=0.9), SARI, kalk=0.6, kimlik=kimlik + 9, t=t)
    # kafa
    cv.save(); cv.translate(0, -238); cv.rotate(math.sin(adim * math.pi * 2) * 3)
    parca(cv, yirtik(daire(0, 0, 44), seed=kimlik + 11, amp=1.2), TEN, kalk=1.0, kimlik=kimlik + 11, t=t)
    parca(cv, yirtik(((-46, -2), (-40, -34), (-10, -50), (24, -46), (46, -18), (44, -6), (10, -22), (-26, -14)), seed=kimlik + 12, amp=1.2), SAC, kalk=0.5)
    p = skia.Paint(AntiAlias=True, Color=LACI)
    cv.drawCircle(-14, 4, 4.5, p); cv.drawCircle(16, 4, 4.5, p)
    pp = skia.Paint(AntiAlias=True, Color=0x66E5574B); cv.drawCircle(-24, 18, 7, pp); cv.drawCircle(26, 18, 7, pp)
    gul = skia.Path(); gul.moveTo(-9, 20); gul.quadTo(1, 30, 11, 20)
    cv.drawPath(gul, skia.Paint(AntiAlias=True, Color=LACI, Style=skia.Paint.kStroke_Style, StrokeWidth=3.5, StrokeCap=skia.Paint.kRound_Cap))
    cv.restore()
    cv.restore()


# ---------- sahneler (tasarım birimi; VW x VH) ----------
def gunes(cv, x, y, r, t, kimlik=20):
    k = math.floor(t * POZ)
    for i in range(12):
        cv.save(); cv.translate(x, y); cv.rotate(i * 30 + k * 1.5)
        parca(cv, yirtik(((-14, -r - 8), (14, -r - 8), (0, -r - 50)), seed=kimlik + i, amp=0.8), SARI, kalk=0.5)
        cv.restore()
    parca(cv, yirtik(daire(x, y, r), seed=kimlik, amp=1.8), GUNES, kalk=1.0, kimlik=kimlik, t=t)


def bulut(cv, x, y, s, kimlik, t):
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    parca(cv, yirtik(((-90, 20), (-80, -10), (-50, -30), (-20, -26), (0, -50), (40, -46), (60, -20), (90, -12), (100, 20)), seed=kimlik, amp=1.5), KAGIT, kalk=0.8, kimlik=kimlik, t=t)
    cv.restore()


def zemin_tepeler(cv, VW, yer, t, gir=None, renkler=(TEPE1, TEPE2, TEPE3), seed=0):
    for i, (renk, h, dy) in enumerate(zip(renkler, (260, 190, 120), (-40, 0, 40))):
        p = 1.0 if gir is None else out_back(prog(t, gir + i * 0.12, 0.5), 1.3)
        cv.save(); cv.translate(0, (1 - p) * 700)
        parca(cv, yirtik(tepe_noktalari(-60, VW + 60, yer + dy, h, seed + i * 7), seed=seed + i, amp=2.0), renk, kalk=1.2 + i * 0.3, kimlik=seed + 30 + i, t=t)
        cv.restore()


def sahne1(cv, t, VW, VH, dik):
    cv.drawRect(skia.Rect.MakeWH(VW, VH), skia.Paint(Color=GOK1))
    yer = VH * (0.80 if dik else 0.84)
    # güneş tepelerin arkasından doğar
    gp = out_cubic(prog(t, Z['gunes'], 1.0))
    gx = VW * (0.80 if dik else 0.76)
    gunes(cv, gx, lerp(yer - 80, VH * (0.17 if dik else 0.30), gp), 92, t)
    bulut(cv, VW * 0.22 + t * 8, VH * (0.17 if dik else 0.18), 1.0, 70, t)
    bulut(cv, VW * 0.55 - t * 5, VH * (0.26 if dik else 0.34), 0.7, 71, t)
    zemin_tepeler(cv, VW, yer, t, gir=Z['tepe'])
    # ilk basamak (küçük kâğıt blok)
    bx = VW * (0.58 if dik else 0.56)
    bp = out_back(prog(t, Z['adim1'] - 0.25, 0.35))
    if bp > 0:
        cv.save(); cv.translate(bx, yer + 20); cv.scale(1, bp)
        parca(cv, yirtik(kutu(-80, -46, 160, 46), seed=81, amp=1.5), SARI, kalk=1.0, kimlik=81, t=t)
        cv.restore()
    # kahraman: soldan girer, bloğa çıkar
    gx0, gx1 = VW * (0.18 if dik else 0.32), bx
    yuru = prog(t, Z['kahraman'], 0.6)
    zp = prog(t, Z['adim1'], 0.3)
    x = lerp(-120, gx0 + (bx - gx0) * 0.55, out_cubic(yuru))
    x = lerp(x, gx1, in_out_cubic(zp))
    y = yer + 20 - 46 * out_cubic(zp)
    zip_ = math.sin(zp * math.pi) * 70
    kahraman(cv, x, y, 1.25 if dik else 0.9, t, adim=yuru * 4 + zp, zipla=zip_, el=out_back(prog(t, Z['etiket'] + 0.3, 0.4)) * 0.6)
    # "%1" etiketi ipte sallanarak iner
    ep = prog(t, Z['etiket'], 0.5)
    if ep > 0:
        ex, ey = (VW * 0.5, VH * 0.30) if dik else (VW * 0.27, VH * 0.40)
        iniş = out_back(ep, 1.4)
        sal = math.sin((t - Z['etiket']) * 7) * 14 * math.exp(-(t - Z['etiket']) * 1.6)
        cv.save(); cv.translate(ex, -40); cv.rotate(sal)
        ip = lerp(0, ey + 40, iniş)
        cv.drawLine(0, 0, 0, ip - 120, skia.Paint(AntiAlias=True, Color=0xFF7A6A58, StrokeWidth=3))
        cv.translate(0, ip)
        parca(cv, yirtik(((-150, -120), (150, -120), (170, 110), (-170, 110)), seed=90, amp=2.0), KIRMIZI, kalk=1.4, kimlik=90, t=t)
        cv.drawCircle(0, -96, 9, skia.Paint(AntiAlias=True, Color=GOK1))
        kesik_yazi(cv, METIN['kanca'], 0, 0, 170 if len(METIN['kanca']) <= 2 else 130, KAGIT, t, 91, kalk=0.5)
        cv.restore()
    serit(cv, METIN['kanca_alt'], VW * (0.5 if dik else 0.27), VH * (0.40 if dik else 0.64), 64, t, 95, p=prog(t, Z['hergun'], 0.35), aci=-3)


def takvim(cv, x, y, t):
    """Yırtılan takvim yaprakları: gün 1 → 365."""
    p = prog(t, Z['takvim'], 1.15)
    tq = _poz_t(t)
    gun = 1 + int((METIN['sayac'] - 1) * in_cubic(prog(tq, Z['takvim'], 1.15)))
    f = skia.Font(TF, 92); f2 = skia.Font(TF, 30)
    cv.save(); cv.translate(x, y); cv.rotate(4)
    parca(cv, yirtik(kutu(-110, -100, 220, 230), seed=60, amp=1.4), KAGIT, kalk=1.2, kimlik=60, t=t)
    parca(cv, yirtik(kutu(-110, -100, 220, 60), seed=61, amp=1.2), KIRMIZI, kalk=0.6)
    for rx in (-60, 0, 60):
        cv.drawCircle(rx, -100, 8, skia.Paint(AntiAlias=True, Color=LACI))
    s = METIN['sayac_ust']; cv.drawString(s, -f2.measureText(s) / 2, -58, f2, skia.Paint(AntiAlias=True, Color=KAGIT))
    s = str(gun); cv.drawString(s, -f.measureText(s) / 2, 80, f, skia.Paint(AntiAlias=True, Color=LACI))
    # düşen yaprak
    if 0 < p < 1:
        k = math.floor(t * POZ); dp = (t * POZ) % 1
        cv.save(); cv.translate(40 + dp * 120, -40 + dp * 260); cv.rotate(dp * 70 + _h(k) * 20)
        parca(cv, yirtik(kutu(-110, -40, 220, 170), seed=62 + k % 3, amp=1.5), KAGIT, kalk=1.6)
        cv.restore()
    cv.restore()


def merdiven_yer(VW, VH, dik):
    yer = VH * (0.86 if dik else 0.88)
    n, gw = 7, (124 if dik else 118)
    x0 = VW / 2 - n * gw / 2 + (0 if dik else 200)
    hs = [34 * 1.36 ** i for i in range(n)]
    return yer, n, gw, x0, hs


def sahne2(cv, t, VW, VH, dik):
    cv.drawRect(skia.Rect.MakeWH(VW, VH), skia.Paint(Color=GOK2))
    yer, n, gw, x0, hs = merdiven_yer(VW, VH, dik)
    # kamera: basamaklar yükseldikçe uzaklaş
    zp = in_out_cubic(prog(t, Z['merdiven'], 1.6))
    sc = lerp(1.35, 1.0, zp)
    pivot = (x0 + n * gw * 0.3, yer)
    cv.save(); cv.translate(*pivot); cv.scale(sc, sc); cv.translate(-pivot[0], -pivot[1])
    # zemin şeridi
    parca(cv, yirtik(kutu(-200, yer, VW + 400, 400), seed=100, amp=2.0), TEPE2, kalk=1.3, kimlik=100, t=t)
    renkler = [SARI, GUNES, PEMBE, MAVI, TEPE1, KIRMIZI, SARI]
    ust = yer
    tepeler = []
    for i in range(n):
        ti = Z['merdiven'] + i * 0.17
        p = out_back(prog(t, ti, 0.3), 1.6)
        top = sum(hs[: i + 1])
        tepeler.append((x0 + i * gw + gw / 2, yer - top, ti))
        if p <= 0: continue
        cv.save(); cv.translate(x0 + i * gw, yer); cv.scale(1, p)
        parca(cv, yirtik(kutu(0, -top, gw + 2, top), seed=110 + i, amp=1.6), renkler[i], kalk=1.0 + i * 0.12, kimlik=110 + i, t=t)
        cv.restore()
    # kahraman basamak basamak zıplar
    tq = _poz_t(t)
    i_akt = max([i for i, (_, _, ti) in enumerate(tepeler) if tq >= ti + 0.08] or [-1])
    if i_akt < 0:
        hx, hy, zz = x0 - 60, yer, 0
    else:
        xa, ya, ta = tepeler[i_akt]
        xp, yp = (tepeler[i_akt - 1][:2] if i_akt > 0 else (x0 - 60, yer))
        q = prog(tq, ta + 0.08, 0.16)
        hx, hy = lerp(xp, xa, q), lerp(yp, ya, q)
        zz = math.sin(q * math.pi) * 60
    kahraman(cv, hx, hy, 0.62, t, adim=tq * 3, zipla=zz, el=out_back(prog(t, Z['x37'] + 0.1, 0.4)))
    cv.restore()
    # takvim + 37x (kameradan bağımsız)
    if dik:
        takvim(cv, VW * 0.78, VH * 0.13, t)
        tx, ty = VW * 0.40, VH * 0.28
    else:
        takvim(cv, VW * 0.10, VH * 0.20, t)
        tx, ty = VW * 0.28, VH * 0.46
    xp = prog(t, Z['x37'], 0.45)
    if xp > 0:
        kesik_yazi(cv, METIN['sayi'], tx, ty, (300 if dik else 280) * (1 if len(METIN['sayi']) <= 3 else 0.8), KIRMIZI, t, 120, kalk=1.6,
                   gelis=lambda i: prog(t, Z['x37'] + i * 0.08, 0.3))
        serit(cv, METIN['sayi_alt'], tx, ty + (230 if dik else 210), 52, t, 125, p=prog(t, Z['x37'] + 0.35, 0.3), aci=2)


def agac(cv, x, y, s, t):
    cv.save(); cv.translate(x, y); cv.scale(s, s)
    parca(cv, yirtik(((-34, 0), (-20, -260), (-60, -340), (-40, -350), (0, -290), (40, -360), (58, -346), (20, -260), (34, 0)), seed=200, amp=1.8), KAHVE, kalk=1.2, kimlik=200, t=t)
    yap = [(-150, -380, 120, TEPE2), (140, -390, 120, TEPE2), (0, -470, 150, TEPE3), (-90, -540, 110, TEPE1), (100, -540, 115, TEPE1),
           (0, -620, 110, TEPE2), (-40, -380, 90, TEPE1), (60, -440, 80, TEPE3)]
    for i, (lx, ly, r, renk) in enumerate(yap):
        p = out_back(prog(t, Z['agac'] + 0.05 + i * 0.06, 0.32), 2.2)
        if p <= 0: continue
        cv.save(); cv.translate(lx, ly); cv.scale(p, p)
        parca(cv, yirtik(daire(0, 0, r), seed=210 + i, amp=2.2), renk, kalk=1.0 + i * 0.1, kimlik=210 + i, t=t)
        cv.restore()
    for i, (mx, my) in enumerate([(-120, -420), (90, -500), (20, -600), (130, -400), (-60, -560)]):  # meyveler
        p = out_back(prog(t, Z['agac'] + 0.6 + i * 0.05, 0.25), 2.5)
        if p > 0:
            parca(cv, yirtik(daire(mx, my, 20 * p), seed=230 + i, amp=0.8), KIRMIZI, kalk=0.6, kimlik=230 + i, t=t)
    cv.restore()


def sahne3(cv, t, VW, VH, dik):
    cv.drawRect(skia.Rect.MakeWH(VW, VH), skia.Paint(Color=GOK3))
    yer = VH * (0.84 if dik else 0.86)
    bulut(cv, VW * 0.2, VH * 0.12, 0.8, 300, t)
    parca(cv, yirtik(tepe_noktalari(-60, VW + 60, yer, 60, 9, n=5), seed=301, amp=2.0), TEPE2, kalk=1.4, kimlik=301, t=t)
    # küçük filiz
    fx = VW * (0.22 if dik else 0.25)
    fp = out_back(prog(t, Z['filiz'], 0.4), 2.0)
    if fp > 0:
        cv.save(); cv.translate(fx, yer - 30); cv.scale(fp * 1.6, fp * 1.6)
        parca(cv, yirtik(kutu(-4, -70, 8, 70), seed=310, amp=0.6), TEPE3, kalk=0.5)
        cv.save(); cv.translate(0, -66); cv.rotate(-30)
        parca(cv, yirtik(((0, 0), (-26, -14), (-46, 0), (-26, 12)), seed=311, amp=0.6), TEPE1, kalk=0.6, kimlik=311, t=t)
        cv.restore(); cv.save(); cv.translate(0, -56); cv.rotate(20)
        parca(cv, yirtik(((0, 0), (26, -14), (46, 0), (26, 12)), seed=312, amp=0.6), TEPE1, kalk=0.6, kimlik=312, t=t)
        cv.restore(); cv.restore()
    serit(cv, METIN['kucuk'], fx + (40 if dik else 0), yer - (230 if dik else 210), 50, t, 320, p=prog(t, Z['kucuk'], 0.3), aci=-4)
    # büyük ağaç büyür
    ax = VW * (0.66 if dik else 0.66)
    ap = out_back(prog(t, Z['agac'], 0.5), 1.4)
    if ap > 0:
        agac(cv, ax, yer - 20, (1.15 if dik else 1.05) * (0.25 + 0.75 * ap), t)
    kahraman(cv, fx + 110, yer - 6, 0.55, t, adim=0, el=0.0)
    if dik:
        serit(cv, tr_buyuk(METIN['buyuk']), VW * 0.5, VH * 0.12, 110, t, 330, p=prog(t, Z['buyuk'], 0.35), zemin=KIRMIZI, renk=KAGIT, aci=-3)
    else:
        serit(cv, tr_buyuk(METIN['buyuk']), VW * 0.3, VH * 0.26, 104, t, 330, p=prog(t, Z['buyuk'], 0.35), zemin=KIRMIZI, renk=KAGIT, aci=-3)


@functools.lru_cache(maxsize=4)
def _resim(yol):
    r = skia.Image.open(yol)
    if r is None:
        raise SenaryoHatasi(f'gorsel açılamadı: {yol}')
    return r


def gorsel_kart(cv, t, x, y, gen):
    """stiller.kagit-kesik.gorsel: gerçek görsel (ör. kitap kapağı) yırtık kenarlı beyaz kâğıt kartta, çizilmeden olduğu gibi."""
    g = STIL_AYAR['gorsel']
    r = _resim(g['dosya'])
    w = gen; h = w * r.height() / r.width()
    p = out_back(prog(t, g.get('t', Z['bayrak'] - 0.35), 0.4), 1.5)
    if p <= 0: return
    cv.save(); cv.translate(x, y); cv.rotate(-3 + 3 * (1 - p)); cv.scale(p, p)
    k = 18
    parca(cv, yirtik(kutu(-w / 2 - k, -h / 2 - k, w + 2 * k, h + 2 * k), seed=440, amp=1.8), KAGIT, kalk=2.0, kimlik=440, t=t)
    cv.drawImageRect(r, skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h),
                     skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), skia.Paint(AntiAlias=True))
    cv.restore()


def sahne4(cv, t, VW, VH, dik):
    cv.drawRect(skia.Rect.MakeWH(VW, VH), skia.Paint(Color=0xFFFBE3A0))
    cx, cy = VW / 2, VH * (0.44 if dik else 0.42)
    gorsel = isinstance(STIL_AYAR.get('gorsel'), dict)
    k = math.floor(t * POZ)
    R = math.hypot(VW, VH)
    for i in range(16):  # güneş ışınları (kâğıt üçgenler)
        if i % 2: continue
        a0 = (i / 16) * 360 + k * 0.8
        pts = ((0, 0), (R * math.cos(math.radians(a0)), R * math.sin(math.radians(a0))),
               (R * math.cos(math.radians(a0 + 22.5)), R * math.sin(math.radians(a0 + 22.5))))
        cv.save(); cv.translate(cx, cy)
        parca(cv, yirtik(pts, seed=400 + i, amp=2.0, adim=40), 0xFFF9D277, kalk=0.4)
        cv.restore()
    yer = VH * (0.88 if dik else 0.92)
    zemin_tepeler(cv, VW, yer, t, renkler=(TEPE1, TEPE2, TEPE3), seed=410)
    if gorsel:  # görsel üstte, kurdele altına iner (yatayda görsel solda, kurdele sağda)
        gen = VW * STIL_AYAR['gorsel'].get('genislik', 0.44 if dik else 0.2)
        if dik:
            gorsel_kart(cv, t, cx, VH * 0.36, gen); cy = VH * 0.66
        else:
            gorsel_kart(cv, t, VW * 0.24, VH * 0.45, gen); cx = VW * 0.62
    # kurdele açılır
    bp = in_out_cubic(prog(t, Z['bayrak'], 0.45))
    boy = 112 if dik else 132
    yw = skia.Font(TF, boy).measureText(METIN['cagri'])
    sig = (VW - 330) if not (gorsel and not dik) else (VW * 0.7 - 330)
    if yw > sig:  # kuyruklar dahil kadraja sığsın
        boy *= sig / yw; yw = sig
    bw, bh = yw + boy * 0.9, 190
    if bp > 0:
        cv.save(); cv.translate(cx, cy); cv.rotate(-3)
        for sgn in (-1, 1):  # kuyruklar
            x = sgn * bw * bp / 2
            parca(cv, yirtik(((x, -bh / 2 + 40), (x + sgn * 120, -bh / 2 + 40), (x + sgn * 80, bh / 2 + 10 - 0), (x + sgn * 120, bh / 2 + 40), (x, bh / 2 + 40)), seed=420 + sgn, amp=1.4), KOYU_KIRMIZI, kalk=1.0)
        w = max(bw * bp, 1)
        parca(cv, yirtik(kutu(-w / 2, -bh / 2, w, bh), seed=425, amp=1.6), KIRMIZI, kalk=1.6, kimlik=425, t=t)
        cv.save(); cv.clipRect(skia.Rect.MakeXYWH(-w / 2, -bh, w, bh * 2))
        kesik_yazi(cv, METIN['cagri'], 0, -6, boy, KAGIT, t, 430, kalk=0.5, aralik=0.0)
        cv.restore()
        cv.restore()
    # kahraman el sallar
    hx = VW * (0.5 if dik else (0.62 if gorsel else 0.5))
    el = 0.75 + 0.25 * math.sin(_poz_t(t) * 14)
    kahraman(cv, hx, yer - 40, 0.95 if dik else 0.8, t, adim=0, el=el * prog(t, Z['bayrak'] + 0.2, 0.2))
    # konfeti
    if t > Z['konfeti']:
        tq = _poz_t(t) - Z['konfeti']
        for i in range(40):
            x = _h(i, 1) * VW; v = 380 + _h(i, 2) * 320
            y = -40 + tq * v - _h(i, 3) * 300
            if y < -40 or y > VH: continue
            cv.save(); cv.translate(x + math.sin(tq * 3 + i) * 30, y); cv.rotate(tq * 200 * (_h(i, 4) - .5) + i * 40)
            renk = [KIRMIZI, MAVI, SARI, TEPE2, PEMBE][i % 5]
            parca(cv, yirtik(kutu(-12, -7, 24, 14), seed=500 + i % 7, amp=0.6, adim=8), renk, kalk=0.5)
            cv.restore()


SAHNELER = [(0.0, sahne1), (3.0, sahne2), (6.0, sahne3), (8.0, sahne4)]
GECIS = 0.36  # yeni kâğıt sayfanın kayarak girme süresi (sahne sınırından önce başlar)


def kare(cv, t, W, H):
    u = min(W, H) / 1080; VW, VH = W / u, H / u; dik = H > W
    cv.save(); cv.scale(u, u)
    tq = _poz_t(t)
    idx = max(i for i, (ts, _) in enumerate(SAHNELER) if tq >= ts - GECIS * 0.7) if tq > 0 else 0
    yeni_ts, yeni = SAHNELER[idx]
    gp = prog(tq, yeni_ts - GECIS * 0.7, GECIS)
    if idx > 0 and gp < 1:
        SAHNELER[idx - 1][1](cv, tq, VW, VH, dik)
        kenar = lerp(VW + 40, 0, out_cubic(gp))
        # sayfa kenarı gölgesi
        sh = skia.GradientShader.MakeLinear([(kenar - 60, 0), (kenar, 0)], [0x00000000, 0x55000000])
        cv.drawRect(skia.Rect.MakeLTRB(kenar - 60, 0, kenar, VH), skia.Paint(Shader=sh))
        cv.save(); cv.clipRect(skia.Rect.MakeLTRB(kenar, 0, VW + 100, VH))
        cv.translate(kenar * 0.15, 0)  # sayfa kayarken içerik de hafif kayar
        yeni(cv, tq, VW, VH, dik)
        cv.restore()
    else:
        yeni(cv, tq, VW, VH, dik)
    cv.restore()
    doku(cv, W, H)


# =====================================================================================
#  SES: kalimba + yumuşak davul + kâğıt efektleri
# =====================================================================================
BPM = 96
VURUS = 60 / BPM


def kalimba(m, d=0.9, br=1.0):
    e, tt = zarf(d, a=0.002, dec=0.28)
    f = mtof(m)
    x = np.sin(2 * np.pi * f * tt) + 0.35 * br * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt / 0.04) + 0.12 * np.sin(2 * np.pi * f * 2 * tt)
    return x * e


def muzik(n):
    m = np.zeros((n, 2))
    akorlar = [(60, 64, 67, 72), (57, 60, 64, 69), (53, 57, 60, 65), (55, 59, 62, 67)]  # C Am F G
    desen = [0, 2, 1, 3, 2, 1, 3, 2]
    adim = VURUS / 2
    i = 0
    tb = 0.0
    while tb < SURE - 0.6:
        bar = int(tb / (VURUS * 4)) % 4
        ak = akorlar[bar]
        if tb >= 8.3: ak = (60, 64, 67, 72)
        nota = ak[desen[i % 8]] + (12 if i % 8 in (3, 6) else 0)
        sakin = tb < 3.0 or 6.0 <= tb < 6.75  # sakin bölümler: yalnız vuruşlarda, yumuşak
        if not (sakin and i % 2):
            ekle(m, tb, kalimba(nota, br=0.5 if sakin else 0.9), 0.17 if sakin else 0.24, pan=0.35 * math.sin(i))
        if i % 2 == 0:
            ekle(m, tb, kalimba(ak[0] - 12, d=1.2, br=0.2), 0.20, pan=-0.1)
        i += 1; tb += adim
    # yumuşak tekme + çalkalayıcı
    rng = np.random.default_rng(4)
    for k in range(int(SURE / VURUS)):
        tb = k * VURUS
        if tb > SURE - 0.5: break
        if tb < 3.0 or 6.0 <= tb < 6.75: continue  # davul yalnız enerjik bölümlerde
        e, tt = zarf(0.25, a=0.002, dec=0.07)
        f = 110 * np.exp(-tt / 0.03) + 48
        ekle(m, tb, np.sin(2 * np.pi * np.cumsum(f) / SR) * e, 0.35)
        sh = rng.standard_normal(int(0.05 * SR)); sh = sh - lp_hizli(sh, 5000)
        ekle(m, tb + VURUS / 2, sh * zarf(0.05, a=0.004, dec=0.015)[0], 0.05, pan=0.4)
    # 37x öncesi yükselen hışırtı + vurgu
    d = Z['x37'] - 3.6; e = np.linspace(0, 1, int(d * SR)) ** 2.5
    ekle(m, 3.6, (lp_hizli(gurultu(d, 5), 3000) - lp_hizli(gurultu(d, 5), 400)) * e, 0.08)
    for j, nn in enumerate((72, 76, 79, 84)):
        ekle(m, Z['x37'] + j * 0.05, kalimba(nn, d=1.0, br=1.2), 0.14, pan=(j - 1.5) * 0.3)
    # final akoru
    for j, nn in enumerate((60, 64, 67, 72, 76)):
        ekle(m, 8.35 + j * 0.04, kalimba(nn, d=1.6, br=1.0), 0.16, pan=(j - 2) * 0.2)
    return m


def hisirti(d, seed, parlak=1.0):  # kâğıt hışırtısı (kullanıcı geri bildirimi: arka planda baskın olmasın)
    x = gurultu(d, seed) * 0.35
    x = lp_hizli(x, 6000 * parlak) - lp_hizli(x, 900)
    rng = np.random.default_rng(seed + 1)
    tane = (rng.random(len(x)) < 0.004).astype(float) * rng.normal(0, 3, len(x))  # çıtırtılar
    e = np.sin(np.pi * np.arange(len(x)) / len(x)) ** 0.7
    return (x + lp_hizli(tane, 4000)) * e


def makas(seed):
    x = np.zeros(int(0.18 * SR))
    for k, t0 in enumerate((0.0, 0.09)):
        e, tt = zarf(0.03, a=0.0005, dec=0.006)
        c = gurultu(0.03, seed + k); c = c - lp_hizli(c, 2500)
        i = int(t0 * SR); x[i:i + len(c)] += c * e
    return x


def tok(f=180, d=0.12):  # kartona konan parça
    e, tt = zarf(d, a=0.001, dec=0.03)
    return (np.sin(2 * np.pi * f * tt) * 0.8 + lp_hizli(gurultu(d, 9), 1500) * 0.6) * e


def sfx(n):
    s = np.zeros((n, 2))
    for i in range(3): ekle(s, Z['tepe'] + i * 0.12, hisirti(0.25, 10 + i), 0.5, pan=(i - 1) * 0.4)
    ekle(s, Z['adim1'], tok(160), 0.8)
    ekle(s, Z['etiket'] - 0.05, makas(20), 0.6, pan=-0.2)
    ekle(s, Z['etiket'] + 0.2, hisirti(0.2, 21), 0.4)
    ekle(s, Z['hergun'], hisirti(0.18, 22, 1.3), 0.4, pan=0.3)
    for ts in (3.0, 6.0, 8.0):  # sayfa kayması
        ekle(s, ts - GECIS * 0.7, hisirti(GECIS + 0.1, int(ts * 10), 0.8), 0.7)
    for i in range(7):
        ekle(s, Z['merdiven'] + i * 0.17, tok(150 + i * 25, 0.1), 0.6, pan=-0.4 + i * 0.12)
    for k in range(14):  # takvim yaprakları
        ekle(s, Z['takvim'] + k / POZ, hisirti(0.06, 40 + k, 1.4), 0.25, pan=0.5)
    for i in range(3):
        ekle(s, Z['x37'] + i * 0.08, tok(110, 0.18), 0.9)
    ekle(s, Z['x37'] + 0.35, makas(50), 0.5, pan=-0.3)
    ekle(s, Z['filiz'], hisirti(0.15, 60, 1.2), 0.3, pan=-0.4)
    for i in range(8):
        ekle(s, Z['agac'] + 0.05 + i * 0.06, hisirti(0.08, 61 + i, 1.2), 0.3, pan=0.3)
    ekle(s, Z['buyuk'], tok(120, 0.16), 0.7)
    ekle(s, Z['bayrak'], hisirti(0.5, 70, 0.9), 0.6)
    for i in range(10):
        ekle(s, Z['konfeti'] + i * 0.09, hisirti(0.05, 80 + i, 1.6), 0.18, pan=math.sin(i))
    return s


AYAR = {'kapak_t': 6.9, 'sfx_db': -11.0}  # hışırtı arka planda kalsın (kullanıcı geri bildirimi)
