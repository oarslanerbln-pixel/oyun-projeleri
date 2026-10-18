"""İzometrik mini dünya stili: yüzen pastel izometrik ada dioraması.

Küçük bir karakter blokların oluşturduğu bileşik (Fibonacci) merdiveni tırmanır, ağaç büyür, bayrak açılır;
kelimeler adadaki izometrik tabelada durur. Her kare t'nin saf fonksiyonudur.
Ekran yazıları motor.METIN'den gelir; kullanım için stil.py'ye bakın.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motor import *  # noqa
import numpy as np
import skia

TF8 = yazi_tipi(800)
TF7 = yazi_tipi(700)
C30 = math.cos(math.pi / 6)


# ---------- renk ----------
def rgb(h): return ((h >> 16) & 255, (h >> 8) & 255, h & 255)
def col(r, g, b, a=255): return skia.Color(int(clamp(r, 0, 255)), int(clamp(g, 0, 255)), int(clamp(b, 0, 255)), int(clamp(a, 0, 255)))


def mix(h1, h2, p):
    a, b = rgb(h1), rgb(h2)
    return (int(lerp(a[0], b[0], p)) << 16) | (int(lerp(a[1], b[1], p)) << 8) | int(lerp(a[2], b[2], p))


def ton(h):
    """3 ton: üst açık, sol orta, sağ koyu (morumsu gölge tonu)."""
    return (mix(h, 0xFFFFFF, 0.38), h, mix(mix(h, 0x6A5A9A, 0.22), 0x000000, 0.10))


def C(h, a=1.0): r, g, b = rgb(h); return col(r, g, b, 255 * a)


SKY_TOP, SKY_BOT = 0xDCD9F5, 0xFFE7D6
GRASS = ton(0xA8DDB5)
DIRT = ton(0xF0C29E)
ROCK = ton(0xC7B9E4)
WOOD = ton(0xD9A77F)
INK = 0x3B3760
CREAM = 0xFFF8EC
SHADOW = 0x5A4A8C
BLOK_RENK = [0xFFAE9E, 0xFFD98F, 0x9FE0CF, 0xA5CFF2, 0xC9B5F2, 0xFFB7D0]

# ---------- dünya ----------
ADA = 6.0                       # ada 6x6, üst yüz z=0
SLAB = 0.42                     # blok dilimi yüksekliği
KOLON_N = [1, 2, 3, 5, 8, 13]   # bileşik büyüme: her basamak öncekilerin toplamı gibi
KOLON_XY = [(1.0, 5.5 - k) for k in range(6)]
AYAK = 0.92

# dilim iniş zamanları (s2'de hızlanan kaskad)
INIS = [[0.78]]
_t, _dt = 3.20, 0.074
for k in range(1, 6):
    l = []
    for j in range(KOLON_N[k]):
        l.append(_t); _t += _dt; _dt *= 0.952
    INIS.append(l); _t += 0.02
DUSUS = 0.20
INIS_DUZ = sorted((tt, k, j) for k, l in enumerate(INIS) for j, tt in enumerate(l))

# karakter sıçramaları: (başla, bitiş, kolondan, kolona)
SICRA = [(1.62, 1.98, -1, 0)]
_hs = 0.0
for k in range(1, 6):
    hazir = INIS[k][-1] + 0.02
    t0 = max(hazir - 0.06, SICRA[-1][1] + 0.02)
    d = 0.24
    SICRA.append((t0, t0 + d, k - 1, k))
T_ZIRVE = SICRA[-1][1]
T_37 = 4.45
T_BAYRAK = T_ZIRVE + 0.05
T_KUCUK, T_BUYUK, T_BUGUN = 6.17, 6.80, 8.37
T_YUZDE = 1.40

TABELA = dict(x0=1.75, x1=5.95, y=0.42, z0=0.95, z1=3.75)
AGAC = (4.85, 4.75)


def kolon_h(k, t):
    """kolonun o anki yerleşik yüksekliği (düşen dilim dahil değil)"""
    return sum(1 for tt in INIS[k] if t >= tt) * SLAB


def kolon_tam(k): return KOLON_N[k] * SLAB


# ---------- kamera ----------
# kamera anahtarları: (t, hx: ekran merkezindeki dünya x-y, vy: ekran merkezindeki izometrik derinlik-yükseklik,
#                      s: 1080 tabanında birim başına piksel). Her en-boy oranı için ayrı çerçeveleme.
# içerik ölçüleri (vy cinsinden): bayrak tepesi ~ -6.3, tabela üstü ~ -2.7, ada ön üst köşe 6, toprak altı 7, kaya altı ~8
KAM_D = [  # 9:16
    (0.00, -0.20, 3.85, 100),
    (2.90, -0.25, 3.70, 104),
    (4.45, -0.20, 0.75, 100),
    (6.00, -0.15, 0.80, 98),
    (6.70, 2.00, 1.25, 124),
    (7.60, -0.20, 0.70, 100),
    (8.90, -0.20, 0.75, 97),
    (10.0, -0.20, 0.75, 99),
]
KAM_Y = [  # 16:9
    (0.00, -0.20, 2.40, 90),
    (2.90, -0.25, 2.35, 94),
    (4.45, 0.00, 0.40, 73),
    (6.00, 0.00, 0.45, 74),
    (6.70, 0.40, 0.50, 77),
    (7.60, 0.10, 0.45, 75),
    (8.90, 0.00, 0.45, 73),
    (10.0, 0.00, 0.45, 75),
]
DARBE = [(T_37, 0.035), (6.80, 0.02), (8.37, 0.03)]


def kamera(t, KAM):
    for i in range(len(KAM) - 1):
        a, b = KAM[i], KAM[i + 1]
        if t <= b[0]:
            p = in_out_cubic(clamp((t - a[0]) / (b[0] - a[0])))
            return [lerp(a[j], b[j], p) for j in range(1, 4)]
    return list(KAM[-1][1:])


class Iso:
    def __init__(self, W, H, t):
        self.W, self.H = W, H
        u = min(W, H) / 1080
        self.u = u
        dikey = H > W
        hx, vy, s = kamera(t, KAM_D if dikey else KAM_Y)
        for td, g in DARBE:
            if t >= td: s *= 1 + g * math.exp(-(t - td) * 4.5) * min(1, (t - td) * 18)
        self.s = s * u * (1 + 0.010 * math.sin(t * 0.7))
        vy -= 0.06 * math.sin(t * 1.3)                  # ada süzülme
        hx += 0.08 * math.sin(t * 0.45)
        self.ox = W / 2 - hx * C30 * self.s
        self.oy = H * 0.5 - vy * self.s

    def P(self, x, y, z):
        return (self.ox + (x - y) * C30 * self.s, self.oy + ((x + y) * 0.5 - z) * self.s)


def yol(pts):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    p.close(); return p


def boya(c, a=1.0, aa=True):
    return skia.Paint(AntiAlias=aa, Color=C(c, a) if isinstance(c, int) else c)


def kutu(cv, I, x0, y0, z0, dx, dy, dz, tonlar, a=1.0, kenar=True):
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    P = I.P
    ust = [P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)]
    sol = [P(x0, y1, z1), P(x1, y1, z1), P(x1, y1, z0), P(x0, y1, z0)]
    sag = [P(x1, y0, z1), P(x1, y1, z1), P(x1, y1, z0), P(x1, y0, z0)]
    # siluet önce (kenar boşluklarını kapatır)
    sil = [P(x0, y0, z1), P(x1, y0, z1), P(x1, y0, z0), P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1)]
    cv.drawPath(yol(sil), boya(tonlar[2], a))
    cv.drawPath(yol(sol), boya(tonlar[1], a))
    cv.drawPath(yol(sag), boya(tonlar[2], a))
    cv.drawPath(yol(ust), boya(tonlar[0], a))
    if kenar and dz > 0.02:
        q = boya(0xFFFFFF, 0.45 * a); q.setStyle(skia.Paint.kStroke_Style); q.setStrokeWidth(max(1.0, 1.6 * I.u))
        q.setStrokeJoin(skia.Paint.kRound_Join)
        p = skia.Path(); p.moveTo(*P(x0, y1, z1)); p.lineTo(*P(x1, y1, z1)); p.lineTo(*P(x1, y0, z1))
        cv.drawPath(p, q)


# ---------- gölge ----------
LX, LY = 0.95, 0.42   # uzun gölge yönü (zemin düzleminde, z başına)


def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3: return pts
    def cr(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def golge_kutu(x0, y0, z0, dx, dy, dz, zg=0.0):
    pts = []
    for x in (x0, x0 + dx):
        for y in (y0, y0 + dy):
            for z in (z0, z0 + dz):
                h = z - zg
                pts.append((round(x + h * LX, 4), round(y + h * LY, 4)))
    return hull(pts)


# ---------- metin ----------
def font(sz, tf=None):
    f = skia.Font(tf or TF8, sz); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias); return f


def metin_genislik(s, f): return f.measureText(s)


# ---------- sahne parçaları ----------
def arka_plan(cv, I, t):
    W, H, u = I.W, I.H, I.u
    p = skia.Paint()
    parlak = 0.5 * out_cubic(prog(t, T_BUGUN - 0.1, 0.8))   # finalde daha sıcak/aydınlık
    ust_r = mix(SKY_TOP, 0xFCE3EC, parlak)
    alt_r = mix(SKY_BOT, 0xFFF0D2, parlak)
    p.setShader(skia.GradientShader.MakeLinear([(0, 0), (0, H)], [C(ust_r), C(alt_r)]))
    cv.drawRect(skia.Rect(0, 0, W, H), p)
    # yumuşak güneş
    gx = W * (0.80 if H > W else 0.84) + (I.ox - W / 2) * 0.04
    gy = H * (0.13 if H > W else 0.20) + (I.oy - H / 2) * 0.04
    gr = 70 * u * (1 + 0.15 * parlak)
    g = skia.Paint()
    g.setShader(skia.GradientShader.MakeRadial((gx, gy), gr * 3.2, [col(255, 236, 200, 150), col(255, 236, 200, 0)]))
    cv.drawCircle(gx, gy, gr * 3.2, g)
    cv.drawCircle(gx, gy, gr, boya(0xFFF1D6))
    cv.drawCircle(gx, gy, gr * 0.78, boya(0xFFE7BE))
    # adanın arkasında yumuşak ışık
    cx, cy = I.P(3, 3, -0.5)
    g = skia.Paint()
    R = 9 * I.s
    g.setShader(skia.GradientShader.MakeRadial((cx, cy), R, [col(255, 255, 255, 120), col(255, 255, 255, 0)]))
    cv.drawCircle(cx, cy, R, g)
    # bulutlar (paralaks)
    bul = [(-0.30, 0.16, 1.00, 0.020), (0.78, 0.10, 0.80, -0.016), (1.05, 0.40, 1.15, 0.012),
           (-0.08, 0.62, 0.70, -0.010), (0.62, 0.86, 0.95, 0.014), (0.20, 0.30, 0.55, 0.018)]
    for i, (bx, by, sc, v) in enumerate(bul):
        par = 0.25
        x = ((bx + v * t) % 1.6 - 0.3) * W + (I.ox - W / 2) * par * 0.15
        y = by * H + (I.oy - H / 2) * par * 0.15
        r = 46 * u * sc * (I.s / (78 * u)) ** 0.3
        a = 0.72 if i % 2 == 0 else 0.55
        q = boya(0xFFFFFF, a)
        pth = skia.Path()
        pth.addCircle(x, y, r); pth.addCircle(x + r * 1.05, y - r * 0.35, r * 1.25); pth.addCircle(x + r * 2.2, y, r * 0.9)
        pth.addRRect(skia.RRect.MakeRectXY(skia.Rect(x - r * 0.2, y - r * 0.1, x + r * 2.6, y + r * 0.9), r * 0.5, r * 0.5))
        pth.setFillType(skia.PathFillType.kWinding)
        cv.save(); cv.clipRect(skia.Rect(0, 0, W, y + r * 0.62)); cv.drawPath(pth, q); cv.restore()
    # süzülen minik küpler (uzak)
    rng = np.random.default_rng(3)
    for i in range(9):
        wx, wy = rng.uniform(-6, 12), rng.uniform(-6, 12)
        wz = rng.uniform(-6, 7) + 0.25 * math.sin(t * 0.9 + i)
        sz = rng.uniform(0.18, 0.38)
        if -1.0 < wx < 7 and -1.0 < wy < 7: continue
        renk = BLOK_RENK[i % 6]
        tt = ton(mix(renk, SKY_TOP, 0.35))
        kutu(cv, I, wx, wy, wz, sz, sz, sz, tt, a=0.85, kenar=False)


def ada(cv, I, t):
    s = I.s
    # alttaki yumuşak gölge
    cx, cy = I.P(3.6, 3.6, -8.0)
    q = boya(SHADOW, 0.10); q.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22 * I.u))
    cv.drawOval(skia.Rect(cx - 3.2 * s, cy - 0.7 * s, cx + 3.2 * s, cy + 0.7 * s), q)
    # kaya alt katmanlar (küçükten büyüğe, alttan üste)
    katman = [(2.55, -4.55, 0.70), (1.85, -3.85, 0.70), (1.10, -3.05, 0.80), (0.40, -2.10, 0.95), (0.12, -1.25, 0.30)]
    for i, (ins, z0, dz) in enumerate(katman):
        tl = tuple(mix(c, 0x8E7CB8, 0.10 * (4 - i)) for c in ROCK)
        kutu(cv, I, ins, ins, z0, ADA - 2 * ins, ADA - 2 * ins, dz, tl, kenar=False)
    # altta asılı küçük kayalar (hafif süzülür)
    for i, (x, y, z, r) in enumerate([(3.2, 3.0, -5.6, 0.45), (1.6, 4.3, -3.9, 0.3), (4.6, 1.7, -4.4, 0.32)]):
        zz = z + 0.12 * math.sin(t * 1.6 + i * 2)
        kutu(cv, I, x, y, zz, r, r, r, ROCK, kenar=False)
    kutu(cv, I, 0, 0, -0.95, ADA, ADA, 0.72, DIRT, kenar=False)
    kutu(cv, I, 0, 0, -0.23, ADA, ADA, 0.23, GRASS)
    # dirt üzerine birkaç taş benek
    for (x, z) in [(0.8, -0.6), (2.6, -0.75), (4.1, -0.5), (5.3, -0.7)]:
        a, b = I.P(x, ADA, z)
        cv.drawOval(skia.Rect(a - 0.13 * s, b - 0.06 * s, a + 0.13 * s, b + 0.06 * s), boya(DIRT[0], 0.7))
    for (y, z) in [(1.2, -0.55), (3.3, -0.7), (4.8, -0.48)]:
        a, b = I.P(ADA, y, z)
        cv.drawOval(skia.Rect(a - 0.12 * s, b - 0.06 * s, a + 0.12 * s, b + 0.06 * s), boya(DIRT[1], 0.6))
    # çim karo ızgarası
    q = boya(0xFFFFFF, 0.16); q.setStyle(skia.Paint.kStroke_Style); q.setStrokeWidth(max(1, 1.2 * I.u))
    for i in range(1, 6):
        p = skia.Path(); p.moveTo(*I.P(i, 0, 0)); p.lineTo(*I.P(i, ADA, 0)); cv.drawPath(p, q)
        p = skia.Path(); p.moveTo(*I.P(0, i, 0)); p.lineTo(*I.P(ADA, i, 0)); cv.drawPath(p, q)
    # taş patika (önden merdivene)
    for (x, y) in [(4.55, 5.5), (3.55, 5.5), (2.55, 5.5)]:
        pts = [I.P(x - 0.36, y - 0.36, 0.005), I.P(x + 0.36, y - 0.36, 0.005), I.P(x + 0.36, y + 0.36, 0.005), I.P(x - 0.36, y + 0.36, 0.005)]
        cv.drawPath(yol(pts), boya(0xFFF3E2, 0.95))


def ust_golgeler(cv, I, t, g):
    """ada üstüne düşen uzun yumuşak gölgeler (adanın üst yüzüne kırpılır)"""
    cv.save()
    cv.clipPath(yol([I.P(0, 0, 0), I.P(ADA, 0, 0), I.P(ADA, ADA, 0), I.P(0, ADA, 0)]), doAntiAlias=True)
    q = boya(SHADOW, 0.20); q.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 2.2 * I.u))
    pth = skia.Path(); pth.setFillType(skia.PathFillType.kWinding)
    for poly in g:
        if len(poly) >= 3:
            pth.addPath(yol([I.P(x, y, 0) for x, y in poly]))
    cv.drawPath(pth, q)
    cv.restore()


def kolon_ciz(cv, I, t, k):
    x, y = KOLON_XY[k]
    x0, y0 = x - AYAK / 2, y - AYAK / 2
    tl = ton(BLOK_RENK[k])
    for j, tt in enumerate(INIS[k]):
        if t < tt - DUSUS: break
        z = j * SLAB
        p = prog(t, tt - DUSUS, DUSUS)
        dz = (1 - in_cubic(p)) * 1.6
        a = clamp(p * 2.2)
        # iniş sonrası küçük ezilme
        sq = 1.0
        if t > tt: sq = 1 - 0.18 * math.exp(-(t - tt) * 30) * math.sin(min(math.pi, (t - tt) * 40))
        hh = SLAB * sq
        kutu(cv, I, x0, y0, z + dz, AYAK, AYAK, hh, tl, a=a)
        # dilim arası ince çizgi
        if j > 0 and t >= tt:
            q = boya(tl[2], 0.35); q.setStyle(skia.Paint.kStroke_Style); q.setStrokeWidth(max(1, 1.3 * I.u))
            pp = skia.Path(); pp.moveTo(*I.P(x0, y0 + AYAK, z)); pp.lineTo(*I.P(x0 + AYAK, y0 + AYAK, z)); pp.lineTo(*I.P(x0 + AYAK, y0, z))
            cv.drawPath(pp, q)


def kolon_golge(k, t):
    x, y = KOLON_XY[k]
    h = kolon_h(k, t)
    if h <= 0: return None
    return golge_kutu(x - AYAK / 2, y - AYAK / 2, 0, AYAK, AYAK, h)


def iki_satir(s):
    """Tabela için: ilk harf büyük, sözcükler en dengeli noktadan iki satıra bölünür."""
    s = s.strip()
    s = tr_buyuk(s[0]) + s[1:]
    w = s.split()
    if len(w) < 2: return [s]
    i = min(range(1, len(w)), key=lambda k: abs(len(' '.join(w[:k])) - len(' '.join(w[k:]))))
    return [' '.join(w[:i]), ' '.join(w[i:])]


def tabela_metni(t):
    """(eski, yeni, p) — tabela yazısı geçişi"""
    seq = [(-1, ['']), (T_YUZDE, [METIN['kanca']]), (T_37, [METIN['sayi']]), (T_KUCUK, iki_satir(METIN['kucuk'])),
           (T_BUYUK, iki_satir(METIN['buyuk'])), (T_BUGUN, iki_satir(METIN['cagri']))]
    i = max(j for j, (tt, _) in enumerate(seq) if t >= tt)
    eski = seq[i - 1][1] if i > 0 else ['']
    return eski, seq[i][1], (t - seq[i][0]) if i > 0 else 9, i


def tabela(cv, I, t):
    T = TABELA
    x0, x1, y, z0, z1 = T['x0'], T['x1'], T['y'], T['z0'], T['z1']
    # yükseliş: tabela ilk saniyede yerden çıkar
    r = out_back(prog(t, 0.05, 0.6), 1.4)
    zo = (1 - r) * -2.4
    if r <= 0.001: return
    for px in (x0 + 0.35, x1 - 0.5):
        kutu(cv, I, px, y - 0.06, 0, 0.16, 0.12, max(0.01, z0 + 0.2 + zo), WOOD, kenar=False)
    son = t >= T_BUGUN
    yuz_renk = mix(CREAM, 0xFFD98F, out_cubic(prog(t, T_BUGUN, 0.4))) if son else CREAM
    cerceve = ton(0xF6B49A if not son else 0xFF9E8A)
    kutu(cv, I, x0, y - 0.10, z0 + zo, x1 - x0, 0.14, z1 - z0, cerceve)
    # ön yüz (y + 0.04 düzlemi) krem panel, kenarlarda pay
    yf = y + 0.04
    m = 0.14
    pts = [I.P(x0 + m, yf, z1 - m + zo), I.P(x1 - m, yf, z1 - m + zo), I.P(x1 - m, yf, z0 + m + zo), I.P(x0 + m, yf, z0 + m + zo)]
    cv.drawPath(yol(pts), boya(yuz_renk))
    # metin: düzlem y=yf, u: +x, v: -z
    X0, Y0 = I.P((x0 + x1) / 2, yf, (z0 + z1) / 2 + zo)
    s = I.s
    cv.save()
    cv.clipPath(yol(pts), doAntiAlias=True)
    cv.concat(skia.Matrix.MakeAll(C30, 0, X0, 0.5, 1, Y0, 0, 0, 1))
    eski, yeni, dt, idx = tabela_metni(t)
    gen = (x1 - x0 - 2 * m - 0.30) * s
    yuk = (z1 - z0 - 2 * m - 0.20) * s

    def blok(satir, sc, a, dy):
        if not satir or satir == [''] or a <= 0: return
        tek = len(satir) == 1
        bas = yuk * (0.74 if tek else 0.50)
        f = font(bas)
        w = max(metin_genislik(sx, f) for sx in satir)
        k = min(1.0, gen / w)
        f = font(bas * k)
        cv.save(); cv.translate(0, dy); cv.scale(sc, sc)
        lh = bas * k * 1.0
        top = -lh * len(satir) / 2
        for i, sx in enumerate(satir):
            ww = metin_genislik(sx, f) if tek else w * k
            renk = INK
            if not tek and i == 1: renk = 0xE0705E
            if tek and sx == METIN['sayi']: renk = 0xE0705E
            cv.drawString(sx, -ww / 2, top + lh * (i + 0.80), f, boya(renk, a))
        cv.restore()

    pe = clamp(dt / 0.16)
    blok(eski, 1.0, 1 - pe, -pe * yuk * 0.5)
    pn = prog(dt, 0.08, 0.42)
    blok(yeni, 0.6 + 0.4 * out_back(pn, 2.2), clamp(pn * 3), (1 - out_cubic(pn)) * yuk * 0.5)
    cv.restore()


def tabela_golge(t):
    T = TABELA
    if t < 0.1: return []
    g = [golge_kutu(T['x0'], T['y'] - 0.1, T['z0'], T['x1'] - T['x0'], 0.14, T['z1'] - T['z0'])]
    for px in (T['x0'] + 0.35, T['x1'] - 0.5):
        g.append(golge_kutu(px, T['y'] - 0.06, 0, 0.16, 0.12, T['z0'] + 0.2))
    return g


def agac_buyume(t):
    g0 = 0.30 + 0.06 * out_cubic(prog(t, 0.2, 1.0))
    g = out_elastic(prog(t, T_BUYUK - 0.02, 1.1))
    return lerp(g0, 1.0, g)


def agac(cv, I, t):
    x, y = AGAC
    g = agac_buyume(t)
    s = I.s
    gov_h = 1.5 * g
    w = 0.22 * max(0.5, g)
    kutu(cv, I, x - w / 2, y - w / 2, 0, w, w, gov_h, WOOD, kenar=False)
    # taç: düz gölgeli küreler (3 ton)
    taclar = [(0.0, 0.0, 0.0, 1.00), (-0.42, 0.25, -0.45, 0.68), (0.40, -0.20, -0.30, 0.62)]
    yaprak = (0xC9F0C6, 0x8FD39C, 0x6BB68A)
    for dx, dy, dz, rr in sorted(taclar, key=lambda q: q[0] + q[1]):
        if g < 0.55 and rr < 1.0: continue
        cx, cy = I.P(x + dx * g, y + dy * g, gov_h + 0.55 * g + dz * g)
        R = 0.88 * rr * g * s
        cv.drawCircle(cx, cy, R, boya(yaprak[1]))
        cv.save()
        pth = skia.Path(); pth.addCircle(cx, cy, R)
        cv.clipPath(pth, doAntiAlias=True)
        cv.drawCircle(cx + R * 0.55, cy + R * 0.42, R * 1.02, boya(yaprak[2]))
        cv.drawCircle(cx - R * 0.42, cy - R * 0.48, R * 0.62, boya(yaprak[0]))
        cv.restore()
    # meyveler / çiçekler büyükken
    if g > 0.8:
        a = clamp((g - 0.8) / 0.2)
        for (dx, dy, dz) in [(-0.3, 0.4, 0.1), (0.35, 0.3, 0.45), (0.1, 0.6, -0.25), (-0.55, 0.1, 0.55)]:
            cx, cy = I.P(x + dx, y + dy, gov_h + 0.55 + dz)
            cv.drawCircle(cx, cy, 0.075 * s * a, boya(0xFF9E8A))


def agac_golge(t):
    x, y = AGAC
    g = agac_buyume(t)
    pts = []
    h = 1.5 * g + 0.55 * g
    R = 0.85 * g
    for i in range(16):
        a = i / 16 * math.tau
        for z in (h - R * 0.6, h + R * 0.6):
            px, py = x + math.cos(a) * R * 0.8, y + math.sin(a) * R * 0.8
            pts.append((round(px + z * LX, 4), round(py + z * LY, 4)))
    w = 0.11 * g
    return [hull(pts), golge_kutu(x - w, y - w, 0, 2 * w, 2 * w, 1.5 * g)]


def bayrak(cv, I, t):
    if t < T_BAYRAK - 0.3: return
    x, y = KOLON_XY[5]
    z = kolon_tam(5)
    px, py = x + 0.33, y - 0.33
    up = out_back(prog(t, T_BAYRAK - 0.3, 0.45), 1.6)
    ph = 1.6 * up
    kutu(cv, I, px - 0.035, py - 0.035, z, 0.07, 0.07, max(0.01, ph), (0xFFFFFF, 0xEDE8F7, 0xC9C0E0), kenar=False)
    a0 = I.P(px, py, z + ph)
    s = I.s
    cv.drawCircle(a0[0], a0[1], 0.06 * s, boya(0xFFD98F))
    acil = out_cubic(prog(t, T_BAYRAK, 0.5))
    if acil <= 0: return
    L = 1.15 * acil
    N = 14
    ust, alt = [], []
    for i in range(N + 1):
        f = i / N
        dalga = 0.10 * math.sin(t * 7 - f * 5) * f
        xx = px + f * L * 0.9
        yy = py + f * L * 0.45
        ust.append(I.P(xx, yy, z + ph - 0.05 + dalga))
        alt.append(I.P(xx, yy, z + ph - 0.05 - 0.62 * (1 - f * 0.55) + dalga))
    cv.drawPath(yol(ust + alt[::-1]), boya(0xFF8F7E))
    # bayrak üst kenar açık ton
    hp = yol(ust + [alt[i] for i in range(N, -1, -1)][:0] or ust)
    q = boya(0xFFC4B8); q.setStyle(skia.Paint.kStroke_Style); q.setStrokeWidth(2.0 * I.u)
    pth = skia.Path(); pth.moveTo(*ust[0])
    for pnt in ust[1:]: pth.lineTo(*pnt)
    cv.drawPath(pth, q)


# ---------- karakter ----------
YURU = [(0.00, 4.35, 5.50), (1.55, 1.86, 5.50)]


def karakter_durum(t):
    """(x, y, z, yon(+1 sağa), yuruyor, sort_key)"""
    if t < SICRA[0][0]:
        p = clamp(t / YURU[1][0])
        p = in_out_cubic(p) * 0.25 + p * 0.75
        x = lerp(YURU[0][1], YURU[1][1], p)
        y = YURU[0][2]
        return x, y, 0.0, -1, (t < YURU[1][0]), x + y, 0
    for i, (t0, t1, a, b) in enumerate(SICRA):
        if t < t0:
            # bir önceki kolonda bekliyor
            k = SICRA[i - 1][3]
            x, y = KOLON_XY[k]
            return x, y, kolon_tam(k), -1, False, x + y + 0.05, 0
        if t <= t1:
            p = (t - t0) / (t1 - t0)
            if a < 0:
                xa, ya, za = YURU[1][1], YURU[1][2], 0.0
            else:
                xa, ya = KOLON_XY[a]; za = kolon_tam(a)
            xb, yb = KOLON_XY[b]; zb = kolon_tam(b)
            pe = in_out_cubic(p)
            x, y = lerp(xa, xb, pe), lerp(ya, yb, pe)
            z = lerp(za, zb, pe) + (0.35 + 0.3 * (zb - za)) * 4 * p * (1 - p)
            kk = (xa + ya + 0.05) if a >= 0 else (xb + yb + 0.05)
            return x, y, z, (1 if xb - yb > xa - ya else -1), False, max(kk, xb + yb + 0.05), p
    k = 5
    x, y = KOLON_XY[k]
    return x, y, kolon_tam(k), 1, False, x + y + 0.05, 0


def karakter(cv, I, t):
    x, y, z, yon, yuru, _, hp = karakter_durum(t)
    s = I.s
    # temas gölgesi
    zt = z
    if 0 < hp < 1:
        zt = None
    cx, cy = I.P(x, y, z)
    if zt is not None:
        q = boya(SHADOW, 0.25)
        cv.drawOval(skia.Rect(cx - 0.22 * s, cy - 0.11 * s, cx + 0.22 * s, cy + 0.11 * s), q)
    faz = t * 13
    bob = abs(math.sin(faz)) * 0.04 * s if yuru else 0
    # zirvede sevinç zıplaması
    if t > T_BUGUN:
        bob += abs(math.sin((t - T_BUGUN) * 7)) * 0.10 * s * math.exp(-(t - T_BUGUN) * 0.6)
    elif t > T_BUYUK + 0.1 and t < T_BUYUK + 1.0:
        bob += abs(math.sin((t - T_BUYUK) * 8)) * 0.06 * s
    cv.save()
    cv.translate(cx, cy - bob)
    cv.scale(yon * 1.3, 1.3)
    # bacaklar
    leg = boya(0x4A4472); leg.setStyle(skia.Paint.kStroke_Style); leg.setStrokeWidth(0.085 * s); leg.setStrokeCap(skia.Paint.kRound_Cap)
    sw = math.sin(faz) * 0.10 * s if yuru else 0
    if 0 < hp < 1: sw = 0.06 * s
    cv.drawLine(-0.06 * s, -0.24 * s, -0.06 * s - sw, -0.03 * s, leg)
    cv.drawLine(0.06 * s, -0.24 * s, 0.06 * s + sw, -0.03 * s, leg)
    # gövde (3 ton: sol orta, sağ koyu)
    gov = skia.RRect.MakeRectXY(skia.Rect(-0.16 * s, -0.60 * s, 0.16 * s, -0.20 * s), 0.10 * s, 0.10 * s)
    cv.drawRRect(gov, boya(0xFF8F7E))
    cv.save(); cv.clipRRect(gov, doAntiAlias=True)
    cv.drawRect(skia.Rect(0.04 * s, -0.7 * s, 0.3 * s, 0), boya(0xE86F62))
    cv.restore()
    # kollar
    arm = boya(0xFF8F7E); arm.setStyle(skia.Paint.kStroke_Style); arm.setStrokeWidth(0.07 * s); arm.setStrokeCap(skia.Paint.kRound_Cap)
    if t > T_BUGUN or (T_ZIRVE < t < T_ZIRVE + 0.9):
        el = math.sin(t * 12) * 0.05 * s
        cv.drawLine(0.13 * s, -0.52 * s, 0.30 * s + el, -0.80 * s, arm)
        cv.drawLine(-0.13 * s, -0.52 * s, -0.24 * s, -0.30 * s, arm)
    else:
        sw2 = math.sin(faz) * 0.08 * s if yuru else 0
        cv.drawLine(0.12 * s, -0.52 * s, 0.18 * s + sw2, -0.30 * s, arm)
        cv.drawLine(-0.12 * s, -0.52 * s, -0.18 * s - sw2, -0.30 * s, arm)
    # baş
    hx, hy, hr = 0.0, -0.76 * s, 0.17 * s
    cv.drawCircle(hx, hy, hr, boya(0xFFD9C2))
    cv.save(); pth = skia.Path(); pth.addCircle(hx, hy, hr); cv.clipPath(pth, doAntiAlias=True)
    cv.drawCircle(hx + hr * 0.9, hy + hr * 0.3, hr * 0.75, boya(0xF4C1A6))
    # saç / bere
    cv.drawRect(skia.Rect(-hr * 1.2, hy - hr * 1.2, hr * 1.2, hy - hr * 0.25), boya(0x4A4472))
    cv.restore()
    cv.drawCircle(-hr * 0.35, hy + hr * 0.05, 0.025 * s, boya(0x3B3760))
    cv.restore()


# ---------- süs ----------
CICEK = [(3.1, 2.6), (5.3, 2.2), (2.6, 4.3), (5.5, 3.6), (3.9, 3.2), (4.2, 1.6), (2.2, 2.0), (5.6, 5.6), (0.4, 0.4)]
CALI = [(3.3, 4.2, 0.42), (5.4, 1.2, 0.36), (0.5, 3.2, 0.30)]


def cicekler(cv, I, t, key_max, key_min):
    s = I.s
    for i, (x, y) in enumerate(CICEK):
        k = x + y
        if not (key_min <= k < key_max): continue
        cx, cy = I.P(x, y, 0)
        sal = math.sin(t * 2 + i) * 0.02 * s
        q = boya(0x7FC296); q.setStrokeWidth(0.035 * s); q.setStyle(skia.Paint.kStroke_Style)
        cv.drawLine(cx, cy, cx + sal, cy - 0.18 * s, q)
        cv.drawCircle(cx + sal, cy - 0.2 * s, 0.07 * s, boya([0xFFB7D0, 0xFFFFFF, 0xFFD98F][i % 3]))
        cv.drawCircle(cx + sal, cy - 0.2 * s, 0.03 * s, boya(0xFF9E8A if i % 3 != 2 else 0xFFFFFF))


# ---------- kıvılcımlar ----------
def kivilcim(cv, I, t, t0, wx, wy, wz, n=10, R=1.2, renk=0xFFFFFF, seed=1):
    d = t - t0
    if d < 0 or d > 1.0: return
    rng = np.random.default_rng(seed)
    cx, cy = I.P(wx, wy, wz)
    s = I.s
    for i in range(n):
        a = rng.uniform(0, math.tau); v = rng.uniform(0.5, 1.0)
        rr = R * v * out_cubic(clamp(d / 0.7)) * s
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.8 - d * 0.3 * s
        al = 1 - clamp((d - 0.3) / 0.7)
        sz = 0.07 * s * (1 - d * 0.6)
        c = [renk, 0xFFD98F, 0xFFAE9E, 0xA5CFF2][i % 4]
        pth = skia.Path()
        pth.moveTo(x, y - sz); pth.lineTo(x + sz * 0.35, y); pth.lineTo(x, y + sz); pth.lineTo(x - sz * 0.35, y); pth.close()
        cv.drawPath(pth, boya(c, al))


def konfeti(cv, I, t):
    d = t - T_BUGUN
    if d < 0: return
    rng = np.random.default_rng(11)
    W, H, u = I.W, I.H, I.u
    cx, cy = I.P(3.9, 0.4, 3.6)
    for i in range(46):
        a = rng.uniform(-math.pi * 0.95, -math.pi * 0.05)
        v = rng.uniform(500, 1250) * u
        g = 900 * u
        x = cx + math.cos(a) * v * d * 0.9 + math.sin(d * 3 + i) * 12 * u
        y = cy + math.sin(a) * v * d + 0.5 * g * d * d
        sz = rng.uniform(7, 13) * u
        rot = d * rng.uniform(-6, 6) + i
        al = clamp(1.6 - d * 0.9)
        if al <= 0: continue
        c = BLOK_RENK[i % 6]
        cv.save(); cv.translate(x, y); cv.rotate(math.degrees(rot))
        sk = abs(math.cos(d * 5 + i))
        cv.drawRect(skia.Rect(-sz / 2, -sz * 0.3 * (0.3 + sk), sz / 2, sz * 0.3 * (0.3 + sk)), boya(mix(c, 0x000000, 0.06), al))
        cv.restore()


# ---------- kare ----------
def kare(cv, t, W, H):
    I = Iso(W, H, t)
    arka_plan(cv, I, t)
    ada(cv, I, t)
    # gölgeler
    g = []
    for k in range(6):
        gg = kolon_golge(k, t)
        if gg: g.append(gg)
    g += tabela_golge(t)
    g += agac_golge(t)
    for x, y, h in CALI:
        g.append(golge_kutu(x - h / 2, y - h / 2, 0, h, h, h * 0.8))
    cx_, cy_, cz_, *_ = karakter_durum(t)
    if cz_ < 0.05:
        g.append(golge_kutu(cx_ - 0.14, cy_ - 0.1, 0, 0.28, 0.2, 0.95))
    ust_golgeler(cv, I, t, g)

    # boyama sırası (x+y derinliği)
    nesne = []
    for k in range(6):
        x, y = KOLON_XY[k]
        nesne.append((x + y, lambda k=k: kolon_ciz(cv, I, t, k)))
    nesne.append((TABELA['x0'] + 0.6 + TABELA['y'], lambda: tabela(cv, I, t)))
    nesne.append((AGAC[0] + AGAC[1], lambda: agac(cv, I, t)))
    nesne.append((KOLON_XY[5][0] + KOLON_XY[5][1] + 0.02, lambda: bayrak(cv, I, t)))
    for x, y, h in CALI:
        tl = ton(0x9FD9A8)
        nesne.append((x + y, lambda x=x, y=y, h=h, tl=tl: kutu(cv, I, x - h / 2, y - h / 2, 0, h, h, h * 0.8, tl)))
    sk = karakter_durum(t)[5]
    nesne.append((sk, lambda: karakter(cv, I, t)))
    # çiçekler aralıklarla
    sinirlar = sorted(set([0] + [n[0] for n in nesne] + [99]))
    for a, b in zip(sinirlar[:-1], sinirlar[1:]):
        nesne.append((a + 1e-4, lambda a=a, b=b: cicekler(cv, I, t, b, a)))
    nesne.sort(key=lambda n: n[0])
    for _, f in nesne: f()

    # efektler
    xk, yk = KOLON_XY[5]
    kivilcim(cv, I, t, T_37, xk, yk, kolon_tam(5) + 1.0, n=12, R=1.6, seed=4)
    kivilcim(cv, I, t, T_BUYUK + 0.1, AGAC[0], AGAC[1], 2.6, n=12, R=1.7, seed=7)
    T = TABELA
    kivilcim(cv, I, t, T_BUGUN, (T['x0'] + T['x1']) / 2, T['y'], T['z1'] + 0.2, n=14, R=2.0, seed=9)
    konfeti(cv, I, t)
    kivilcim(cv, I, t, T_YUZDE, (T['x0'] + T['x1']) / 2, T['y'], T['z1'] + 0.1, n=8, R=1.3, seed=2)


# =====================================================================================
#  SES
# =====================================================================================
BPM = 100
VUR = 60 / BPM


def fft_filtre(x, lo=None, hi=None):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if hi: m *= 1 / np.sqrt(1 + (f / hi) ** 4)
    if lo: m *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X * m, len(x))


def bell(f, d, idx=1.6, oran=3.5, dec=0.45):
    e, tt = zarf(d, a=0.004, dec=dec)
    I = idx * np.exp(-tt / (dec * 0.35))
    return np.sin(2 * np.pi * f * tt + I * np.sin(2 * np.pi * f * oran * tt)) * e


def pluck(f, d, dec=0.32):
    e, tt = zarf(d, a=0.003, dec=dec)
    x = np.zeros_like(tt)
    for h in range(1, 6):
        x += np.sin(2 * np.pi * f * h * tt) * (0.6 ** (h - 1)) * np.exp(-tt * h * 3.0)
    return x * e


B0 = 0.25  # vuruş ızgarası başlangıcı: 4.45 (37x) ve 6.85 vuruşa denk gelir
AKOR = [  # (başla, bitir, midi notalar) — kök + 4 ses
    (0.00, 3.25, [53, 57, 60, 64, 67]),   # Fmaj9   sakin
    (3.25, 4.45, [50, 53, 57, 60, 64]),   # Dm9     yükseliş
    (4.45, 6.10, [46, 53, 57, 60, 65]),   # Bbmaj7  zirve (37x)
    (6.10, 6.85, [43, 50, 53, 58, 62]),   # Gm9     içten/sakin
    (6.85, 8.35, [48, 55, 58, 60, 65]),   # C7sus4  kalkış, gerilim
    (8.35, 10.0, [41, 53, 57, 60, 67]),   # Fadd9   çözülme, parlak
]


def akor_at(t):
    for a in AKOR:
        if a[0] <= t < a[1]: return a[2]
    return AKOR[-1][2]


def dinamik(t):
    """0..1 enerji eğrisi: s1 sakin, s2 yükselir -> 37x tepe, s3 düşer, 6.85 kalkış, s4 parlak final"""
    if t < 3.0: return 0.25
    if t < 4.45: return lerp(0.35, 0.85, (t - 3.0) / 1.45)
    if t < 6.0: return lerp(1.0, 0.7, (t - 4.45) / 1.55)
    if t < 6.85: return 0.18
    if t < 8.35: return lerp(0.5, 0.75, (t - 6.85) / 1.5)
    return 1.0


def muzik(n):
    buf = np.zeros((n, 2))
    # pad: her akor kendi kesimiyle (dinamiğe göre parlaklık)
    for t0, t1, notalar in AKOR:
        kuyruk = 0.2 if t1 == 6.10 else 0.5
        d = t1 - t0 + kuyruk
        tt = np.arange(int(d * SR)) / SR
        atk = 0.6 if t0 < 1 else (0.08 if t0 in (4.45, 8.35) else 0.3)
        e = np.minimum(tt / atk, 1) * np.clip((d - tt) / kuyruk, 0, 1)
        if t1 >= 10: e = np.minimum(tt / atk, 1) * np.exp(-np.maximum(tt - 0.8, 0) * 0.5)
        x = np.zeros((len(tt), 2))
        for m in notalar[1:]:
            for det, ch in ((-0.08, 0), (0.08, 1)):
                f = mtof(m + det)
                x[:, ch] += sum(np.sin(2 * np.pi * f * h * tt + h * ch) / h ** 1.2 for h in range(1, 6))
        en = dinamik(t0 + 0.2)
        cut = 600 + 2600 * en
        for ch in (0, 1): x[:, ch] = fft_filtre(x[:, ch] * e, hi=cut)
        g = 0.035 * (0.35 + 0.95 * en)
        i0 = int(t0 * SR); m_ = min(len(tt), n - i0)
        buf[i0:i0 + m_] += x[:m_] * g
        # bas: kök, yumuşak sinüs
        f = mtof(notalar[0] - 12 if notalar[0] > 45 else notalar[0])
        bx = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) * e
        ekle(buf, t0, bx * 0.16 * (0.25 + 0.9 * en))
    # arpej olayları (yoğunluk dinamiği izler)
    olay = []
    t = B0
    while t < 3.25: olay.append((t, 0.45)); t += VUR            # s1: dörtlük, yumuşak
    t = 3.25
    while t < 3.85 - 1e-6: olay.append((t, 0.6)); t += VUR / 2   # s2: sekizlik
    while t < 4.45 - 1e-6: olay.append((t, 0.75)); t += VUR / 4  # tepeye 16'lık
    t = 4.45
    while t < 6.0: olay.append((t, 0.85)); t += VUR / 2
    for t in (6.25, 6.55): olay.append((t, 0.4))                 # s3: seyrek
    t = 6.85
    while t < 8.35 - 1e-6: olay.append((t, 0.6 + 0.2 * (t - 6.85) / 1.5)); t += VUR / 2
    t = 8.35
    while t < 9.6: olay.append((t, 0.9)); t += VUR / 4 if t < 8.95 else VUR / 2
    desen = [1, 2, 3, 4, 3, 2, 4, 3]
    for i, (t, v) in enumerate(olay):
        ak = akor_at(t + 1e-3)
        m = ak[desen[i % 8]] + 12
        pan = 0.4 * math.sin(i * 0.9)
        ekle(buf, t, bell(mtof(m), 1.4, idx=1.0, oran=2.0, dec=0.42) * 0.15 * v, pan=pan)
        ekle(buf, t, pluck(mtof(m - 12), 0.6, dec=0.18) * 0.06 * v, pan=-pan)
        if t >= 8.35 or 4.45 <= t < 5.5:  # parlak oktav
            ekle(buf, t + 0.01, bell(mtof(m + 12), 0.9, idx=0.6, oran=2.0, dec=0.25) * 0.05 * v, pan=-pan)
    # davul: yumuşak tekme + shaker + hafif el çırpma, yalnız enerjik bölümlerde
    def tekme(t0, g):
        e, tt = zarf(0.3, a=0.002, dec=0.09)
        f = 48 + 80 * np.exp(-tt * 32)
        ekle(buf, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * e * g)
    def ciz(t0, g, seed):
        e, _ = zarf(0.07, a=0.002, dec=0.02)
        ekle(buf, t0, fft_filtre(gurultu(0.07, seed) * e, lo=6000) * g, pan=0.3)
    def alkis(t0, g, seed):
        e, _ = zarf(0.18, a=0.001, dec=0.05)
        ekle(buf, t0, fft_filtre(gurultu(0.18, seed) * e, lo=900, hi=4000) * g, pan=-0.1)
    for k in range(-1, 17):
        bt = B0 + k * VUR
        if 3.25 - 1e-6 <= bt < 6.0:
            tekme(bt, 0.12 + 0.14 * dinamik(bt))
            ciz(bt + VUR / 2, 0.03 + 0.03 * dinamik(bt), k)
            if bt >= 4.45 and k % 2 == 0: alkis(bt, 0.05, 40 + k)
        elif 6.85 - 1e-6 <= bt < 8.3:
            if (k % 2) == 0 or bt > 7.9: tekme(bt, 0.13)
            ciz(bt + VUR / 2, 0.035, k)
        elif bt >= 8.9 and bt < 9.7:
            tekme(bt, 0.22); ciz(bt + VUR / 2, 0.05, k)
            if k % 2 == 1: alkis(bt, 0.06, 60 + k)
    tekme(4.45, 0.34); tekme(8.35, 0.34); tekme(6.85, 0.16)
    # yükselen gürültü (riser) 37x ve finale
    for t0, t1, g in ((3.55, 4.45, 0.10), (7.75, 8.35, 0.09)):
        d = t1 - t0
        x = gurultu(d, int(t0 * 10)); tt = np.arange(len(x)) / SR
        a = fft_filtre(x, lo=400, hi=1500); b = fft_filtre(x, lo=2500, hi=9000)
        p = tt / d
        ekle(buf, t0, (a * (1 - p) + b * p) * p ** 2 * g)
    # yumuşak zil/crash (tepe ve final)
    for t0, g in ((4.45, 0.07), (8.35, 0.08)):
        e, tt = zarf(2.0, a=0.003, dec=0.6)
        ekle(buf, t0, fft_filtre(gurultu(2.0, int(t0)) * e, lo=5000, hi=12000) * g)
    # 6.85 kalkış: ters pad şişmesi
    d = 0.6; tt = np.arange(int(d * SR)) / SR
    sw = sum(np.sin(2 * np.pi * mtof(m + 12) * tt) for m in AKOR[4][2][1:]) * (tt / d) ** 3
    ekle(buf, 6.85 - d, sw * 0.025)
    # final çözülme akoru: parlak arpejli strum + uzun sönüm
    for i, m in enumerate([53, 57, 60, 64, 67, 72, 76]):
        ekle(buf, 8.35 + i * 0.025, bell(mtof(m + 12), 1.6, idx=0.9, oran=2.0, dec=0.7) * 0.10, pan=(i - 3) * 0.12)
        ekle(buf, 8.35 + i * 0.025, pluck(mtof(m), 1.6, dec=0.6) * 0.06, pan=(i - 3) * 0.12)
    return buf


def tok(f, seed=0):
    """yumuşak tahta 'tok'"""
    e, tt = zarf(0.12, a=0.0008, dec=0.022)
    ff = f * (1 + 0.25 * np.exp(-tt * 80))
    ph = 2 * np.pi * np.cumsum(ff) / SR
    x = np.sin(ph) * e + 0.4 * np.sin(2.7 * ph) * e * np.exp(-tt * 60)
    nz = gurultu(0.12, seed) * np.exp(-tt / 0.004)
    x += fft_filtre(nz, lo=1200, hi=5000) * 0.5
    return x


def whoosh(d, seed=0, yuk=True):
    nz = gurultu(d, seed)
    tt = np.arange(len(nz)) / SR
    e = np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 2
    # süpürülen bant: iki filtreyi karıştır
    a = fft_filtre(nz, lo=300, hi=1200); b = fft_filtre(nz, lo=1500, hi=5000)
    p = tt / d if yuk else 1 - tt / d
    return (a * (1 - p) + b * p) * e


def zil(f, d=1.6):
    e, tt = zarf(d, a=0.002, dec=0.5)
    x = np.zeros_like(tt)
    for r, g, dd in ((1, 1.0, 0.6), (2.76, 0.5, 0.3), (5.40, 0.25, 0.15), (2.0, 0.3, 0.5)):
        x += np.sin(2 * np.pi * f * r * tt) * g * np.exp(-tt / dd)
    return x * np.minimum(tt / 0.002, 1)


def blip(f0, f1, d=0.12):
    e, tt = zarf(d, a=0.003, dec=d / 3)
    ff = f0 * (f1 / f0) ** (tt / d)
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * e


def sfx(n):
    buf = np.zeros((n, 2))
    # blok inişleri
    for i, (tt, k, j) in enumerate(INIS_DUZ):
        f = 520 * 2 ** ((k * 2 + j * 0.25) / 12)
        x, y = KOLON_XY[k]
        ekle(buf, tt, tok(f, seed=i), gain=0.9 if k == 0 else 0.55, pan=clamp((x - y) / 8, -0.6, 0.6))
    # tabela çıkışı
    ekle(buf, 0.10, whoosh(0.5, 1, True), 0.25)
    ekle(buf, 0.45, tok(380, 99), 0.6)
    # kamera hareketleri
    for t0, d, s, g in ((3.10, 0.7, 2, 0.35), (6.10, 0.6, 3, 0.15), (7.75, 0.6, 4, 0.25)):
        ekle(buf, t0, whoosh(d, s, True), g)
    # karakter adım/sıçrama
    for t0 in np.arange(0.1, 1.55, 0.24):
        ekle(buf, t0, tok(1500, int(t0 * 100)) * 0.3, 0.25, pan=-0.2)
    for (t0, t1, a, b) in SICRA:
        ekle(buf, t0, blip(500, 900, 0.10), 0.18)
        ekle(buf, t1, tok(900, int(t1 * 50)), 0.30)
    # tabela yazı değişimleri
    for t0 in (T_YUZDE, T_KUCUK, T_BUYUK):
        ekle(buf, t0 + 0.06, blip(700, 1100, 0.09), 0.30)
    # 37x zil
    ekle(buf, T_37, zil(mtof(84)), 0.45, pan=-0.2)
    ekle(buf, T_37 + 0.12, zil(mtof(91)), 0.30, pan=0.25)
    ekle(buf, T_BAYRAK, whoosh(0.35, 8, True), 0.2)
    # ağaç büyümesi: yükselen yumuşak 'bloop' + parıltı
    ekle(buf, T_BUYUK, blip(220, 660, 0.35), 0.35)
    for i, m in enumerate([88, 91, 95]):
        ekle(buf, T_BUYUK + 0.12 + i * 0.07, zil(mtof(m), 0.9), 0.12, pan=(i - 1) * 0.4)
    # final
    ekle(buf, T_BUGUN, zil(mtof(81), 2.0), 0.35)
    ekle(buf, T_BUGUN + 0.09, zil(mtof(88), 1.8), 0.25, pan=0.3)
    ekle(buf, T_BUGUN + 0.18, zil(mtof(93), 1.6), 0.18, pan=-0.3)
    return buf


AYAR = {'kapak_t': 6.9, 'sfx_db': -4.0}
