"""Piksel stili: RETRO PİKSEL SANAT (16-bit oyun görünümü).

Her kare düşük iç çözünürlükte (kısa kenar 180 px) 16 renkli Sweetie-16 paletiyle numpy dizisine çizilir,
en yakın komşu ile 1080p'ye büyütülür. Kendi bitmap fontu (Türkçe Ü Ç Ş Ğ İ Ö ı dahil), paralaks arka plan,
yürüme döngülü kahraman, "+%1" pop'ları, XP çubuğu, LEVEL UP, başlık ekranı. Müzik/efekt: chiptune sentezi.
Ekran yazıları motor.METIN'den gelir (bitmap fonta sığsın diye büyük harfe çevrilir ve gerekirse küçültülür);
"GÜN", "GÜÇ", "XP", "LEVEL UP!", "> START" oyun arayüzünün sabit parçalarıdır. Kullanım için stil.py'ye bakın.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motor import *  # noqa
import numpy as np

# =====================================================================================
#  PALET (Sweetie-16)
# =====================================================================================
_HEX = ['1a1c2c', '5d275d', 'b13e53', 'ef7d57', 'ffcd75', 'a7f070', '38b764', '257179',
        '29366f', '3b5dc9', '41a6f6', '73eff7', 'f4f4f4', '94b0c2', '566c86', '333c57']
PAL = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] + [255] for h in _HEX], np.uint8)
SIYAH, MOR, KIRMIZI, TURUNCU, SARI, ACIKYESIL, YESIL, CAMGOBEGI, LACI, MAVI, ACIKMAVI, CYAN, BEYAZ, ACIKGRI, GRI, KOYUGRI = range(16)

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16

# =====================================================================================
#  BITMAP FONT 5x7 (+ 3 satır üst işaret, 2 satır alt çengel)
# =====================================================================================
_G = {
    'A': ".###.|#...#|#...#|#####|#...#|#...#|#...#", 'B': "####.|#...#|#...#|####.|#...#|#...#|####.",
    'C': ".###.|#...#|#....|#....|#....|#...#|.###.", 'D': "####.|#...#|#...#|#...#|#...#|#...#|####.",
    'E': "#####|#....|#....|####.|#....|#....|#####", 'F': "#####|#....|#....|####.|#....|#....|#....",
    'G': ".###.|#...#|#....|#.###|#...#|#...#|.####", 'H': "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    'I': "###|.#.|.#.|.#.|.#.|.#.|###", 'J': "..###|...#.|...#.|...#.|#..#.|#..#.|.##..",
    'K': "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", 'L': "#....|#....|#....|#....|#....|#....|#####",
    'M': "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", 'N': "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    'O': ".###.|#...#|#...#|#...#|#...#|#...#|.###.", 'P': "####.|#...#|#...#|####.|#....|#....|#....",
    'R': "####.|#...#|#...#|####.|#.#..|#..#.|#...#", 'S': ".####|#....|#....|.###.|....#|....#|####.",
    'T': "#####|..#..|..#..|..#..|..#..|..#..|..#..", 'U': "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    'V': "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..", 'W': "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#",
    'X': "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#", 'Y': "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    'Z': "#####|....#|...#.|..#..|.#...|#....|#####", 'Q': ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    'x': ".....|.....|#...#|.#.#.|..#..|.#.#.|#...#", 'ı': ".|.|#|#|#|#|#",
    '0': ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", '1': ".#.|##.|.#.|.#.|.#.|.#.|###",
    '2': ".###.|#...#|....#|...#.|..#..|.#...|#####", '3': "####.|....#|....#|.###.|....#|....#|####.",
    '4': "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.", '5': "#####|#....|####.|....#|....#|#...#|.###.",
    '6': ".###.|#....|#....|####.|#...#|#...#|.###.", '7': "#####|....#|...#.|..#..|.#...|.#...|.#...",
    '8': ".###.|#...#|#...#|.###.|#...#|#...#|.###.", '9': ".###.|#...#|#...#|.####|....#|....#|.###.",
    '%': "##..#|##..#|...#.|..#..|.#...|#..##|#..##", '+': ".....|..#..|..#..|#####|..#..|..#..|.....",
    '.': "..|..|..|..|..|##|##", ',': "..|..|..|..|##|##|.#", '!': "##|##|##|##|##|..|##",
    ':': "..|##|##|..|##|##|..", '-': "....|....|....|####|....|....|....", '/': "....#|...#.|...#.|..#..|.#...|.#...|#....",
    '>': "#...|##..|###.|####|###.|##..|#...", '*': "..#..|#.#.#|.###.|#####|.###.|#.#.#|..#..",
    '?': ".###.|#...#|....#|...#.|..#..|.....|..#..", "'": "#|#|.|.|.|.|.", '©': ".###.|#...#|#.#.#|#.#..|#.#.#|#...#|.###.",
}
_UST = {'Ü': ('U', ".#.#."), 'Ö': ('O', ".#.#."), 'İ': ('I', ".#."), 'Ğ': ('G', "#...#|.###.")}
_ALT = {'Ç': ('C', "..#..|.##.."), 'Ş': ('S', "..#..|.##..")}
UST, GOV, ALT = 3, 7, 2
SATIR = UST + GOV + ALT


def _glif_yap():
    out = {}
    def sat(s): return [[c == '#' for c in r] for r in s.split('|')]
    for k, s in _G.items():
        g = np.zeros((SATIR, len(s.split('|')[0])), bool)
        g[UST:UST + GOV] = sat(s); out[k] = g
    for k, (b, isaret) in _UST.items():
        g = out[b].copy(); m = sat(isaret)
        for i, r in enumerate(m):
            g[UST - 1 - len(m) + i, :len(r)] |= np.array(r)
        out[k] = g
    for k, (b, isaret) in _ALT.items():
        g = out[b].copy(); m = sat(isaret); g[UST + GOV - 1, :] = False if b == 'X' else g[UST + GOV - 1, :]
        for i, r in enumerate(m):
            g[UST + GOV + i, :len(r)] |= np.array(r)
        out[k] = g
    out[' '] = np.zeros((SATIR, 3), bool)
    return out


GLIF = _glif_yap()


def metin_maske(s):
    cols = []
    for ch in s:
        g = GLIF.get(ch, GLIF.get(ch.upper(), GLIF['?']))
        cols.append(g); cols.append(np.zeros((SATIR, 1), bool))
    return np.concatenate(cols[:-1], 1) if cols else np.zeros((SATIR, 1), bool)


def metin_gen(s, k=1): return (metin_maske(s).shape[1]) * k


def ekran(s):
    """METIN değeri → bitmap fontun yazabildiği biçim: büyük harf (Türkçe kurallı); sayıdaki 'x' küçük kalır."""
    s = tr_buyuk(s.strip())
    return s[:-1] + 'x' if len(s) > 1 and s[-1] == 'X' and s[:-1].replace('.', '').replace(',', '').isdigit() else s


def sigdir(satirlar, k, gen):
    """En geniş satır `gen` piksele sığana kadar ölçeği küçültür (en az 1)."""
    while k > 1 and max(metin_gen(x, k) for x in satirlar) > gen:
        k -= 1
    return k


def bol(s):
    """İki satıra en dengeli noktadan böler; tek sözcükse tek satır."""
    w = s.split()
    if len(w) < 2: return [s]
    i = min(range(1, len(w)), key=lambda j: abs(len(' '.join(w[:j])) - len(' '.join(w[j:]))))
    return [' '.join(w[:i]), ' '.join(w[i:])]


def satir_araligi(alt_satir, k, sik):
    """İkinci satırda üst işaret (Ü Ö İ Ğ) varsa üstteki satırın altına değmesin diye aralık açılır."""
    return SATIR * k + k if any(c in _UST for c in alt_satir) else SATIR * k - sik


def sayi_carpani():
    """'37x' → 37.0 (HUD'daki GÜÇ sayacı bu değere varır); okunamazsa 37."""
    try:
        return max(1.0, float(METIN['sayi'].lower().rstrip('x').replace(',', '.')))
    except ValueError:
        return 37.0


# =====================================================================================
#  ÇİZİM YARDIMCILARI (palet indeksli numpy tamponu)
# =====================================================================================
def boya(buf, mask, x, y, renk):
    """mask: bool (h,w); renk: int veya (h,w) int dizi. Kırpmalı."""
    x, y = int(round(x)), int(round(y))
    H, W = buf.shape; mh, mw = mask.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + mw), min(H, y + mh)
    if x0 >= x1 or y0 >= y1: return
    m = mask[y0 - y:y1 - y, x0 - x:x1 - x]
    hedef = buf[y0:y1, x0:x1]
    if np.isscalar(renk) or np.ndim(renk) == 0:
        hedef[m] = renk
    else:
        hedef[m] = np.asarray(renk)[y0 - y:y1 - y, x0 - x:x1 - x][m]


def kutu(buf, x, y, w, h, renk):
    x, y, w, h = int(round(x)), int(round(y)), int(round(w)), int(round(h))
    H, W = buf.shape
    buf[max(0, y):max(0, min(H, y + h)), max(0, x):max(0, min(W, x + w))] = renk


def genislet(m, r=1, kare_=True):
    h, w = m.shape; o = np.zeros((h + 2 * r, w + 2 * r), bool)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if not kare_ and abs(dx) + abs(dy) > r: continue
            o[r + dy:r + dy + h, r + dx:r + dx + w] |= m
    return o


def yaz(buf, s, x, y, renk, k=1, kontur=SIYAH, golge=None, hiza='sol', renk_satir=None):
    """Bitmap metin. y = metin kutusunun üstü (üst işaret alanı dahil). renk_satir: k ölçekli satır başına renk listesi."""
    m = metin_maske(s)
    if k > 1: m = np.kron(m, np.ones((k, k), bool)).astype(bool)
    w = m.shape[1]
    if hiza == 'orta': x -= w // 2
    elif hiza == 'sag': x -= w
    x, y = int(round(x)), int(round(y))
    if golge is not None:
        gm = genislet(m, 1) if kontur is not None else m
        o = 1 if kontur is not None else 0
        boya(buf, gm, x - o + max(1, k // 2), y - o + max(1, k // 2), golge)
    if kontur is not None:
        boya(buf, genislet(m, 1), x - 1, y - 1, kontur)
    if renk_satir is not None:
        rs = np.asarray(renk_satir)
        rr = np.repeat(rs[:, None], w, 1) if rs.ndim == 1 else rs
        boya(buf, m, x, y, rr[:m.shape[0], :m.shape[1]])
    else:
        boya(buf, m, x, y, renk)
    return w


# ---------- spritelar ----------
_HARF = {'t': CAMGOBEGI, 'k': SIYAH, 'r': KIRMIZI, 'R': TURUNCU, 's': SARI, 'S': TURUNCU, 'b': MAVI, 'B': ACIKMAVI, 'd': LACI,
         'w': BEYAZ, 'y': SARI, 'o': TURUNCU, 'g': ACIKGRI, 'h': MOR, 'c': CYAN}


def sprite(satirlar):
    h, w = len(satirlar), max(len(r) for r in satirlar)
    idx = np.zeros((h, w), np.int16); m = np.zeros((h, w), bool)
    for i, r in enumerate(satirlar):
        for j, c in enumerate(r):
            if c in _HARF: idx[i, j] = _HARF[c]; m[i, j] = True
    return m, idx


_KAFA = [
    ".....kk.....",
    "....kcck....",
    "..kkkttkkk..",
    ".kttttttttk.",
    ".kcccccccck.",
    ".khhhhhhhk..",
    ".khhSSSSSk..",
    ".khSSSSkSk..",
    "..kSSSSSSk..",
    "...kkSSkk...",
]
_GOVDE = {
    'a': [".ttkyyyyyk..",
          "tttkyyoyySk.",
          "tttkyyyyySk.",
          ".ttkyyyyyk..",
          "..kddddddk..",
          ".kddk..kddk.",
          ".kwwk...kwwk"],
    'b': [".ttkyyyyyk..",
          "tttkyyoyyk..",
          "tttkyyyySk..",
          ".ttkyyyyyk..",
          "..kddddddk..",
          "...kddkdk...",
          "...kwwkwwk.."],
    'c': [".ttkyyyyyk..",
          "tttkyyoyyk..",
          "tttkSyyyyyk.",
          ".ttkyyyyySk.",
          "..kddddddk..",
          "..kdk.kddk..",
          "..kwwkkwwk.."],
    'z': [".ttkyyyyykSk",
          "tttkyyoyyk..",
          "tttkyyyyyk..",
          ".ttkyyyyyk..",
          "..kddddddk..",
          ".kddk..kddk.",
          "kwwk....kwwk"],
    'd': [".ttkyyyyyk..",
          "tttkyyoyyk..",
          "tttkyyyySk..",
          ".ttkyyyyyk..",
          "..kddddddk..",
          "..kddkkddk..",
          "..kwwk.kwwk."],
}


def _kontur_ekle(spr):
    m, idx = spr
    h, w = m.shape; o = np.zeros_like(m)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        sh = np.zeros_like(m)
        sh[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = m[max(0, -dy):h + min(0, -dy), max(0, -dx):w + min(0, -dx)]
        o |= sh
    yeni = o & ~m
    idx = idx.copy(); idx[yeni] = SIYAH
    return m | yeni, idx


KAHRAMAN = {k: _kontur_ekle(sprite(_KAFA + v)) for k, v in _GOVDE.items()}
YURU = ['a', 'b', 'c', 'b']

_PARA = [
    [".kkkk.", "kyyyyk", "kywyok", "kywyok", "kywyok", "kywyok", "kyyyok", ".kkkk."],
    ["..kk..", ".kyyk.", ".kwok.", ".kwok.", ".kwok.", ".kwok.", ".kyok.", "..kk.."],
    ["..kk..", "..ko..", "..ko..", "..ko..", "..ko..", "..ko..", "..ko..", "..kk.."],
    ["..kk..", ".kyyk.", ".kyok.", ".kyok.", ".kyok.", ".kyok.", ".kyok.", "..kk.."],
]
PARA = [sprite(p) for p in _PARA]

_YILDIZ = sprite(["..w..", ".wyw.", "wyyyw", ".wyw.", "..w.."])


def ciz_sprite(buf, spr, x, y, k=1, ayna=False, tek_renk=None):
    m, idx = spr
    if ayna: m, idx = m[:, ::-1], idx[:, ::-1]
    if k > 1:
        m = np.kron(m, np.ones((k, k), bool)).astype(bool); idx = np.kron(idx, np.ones((k, k), np.int16))
    boya(buf, m, x, y, tek_renk if tek_renk is not None else idx)


# =====================================================================================
#  ZAMAN ÇİZELGESİ (görüntü ve ses aynı tablodan)
# =====================================================================================
Z = dict(yuru=0.35, hiz0=3.15, gun365=4.0, x37=4.05, lvup=4.45, wipe1=5.75, s3=6.0, kucuk=6.15, adim=6.3,
         buyuk=6.71, dev=6.92, wipe2=7.75, s4=8.0, bugun=8.35, basla=8.72, start=9.05, bas=9.3)

_TT = np.arange(0, SURE + 0.002, 0.001)


def _hiz(t):
    r = np.where(t < Z['yuru'], 0.0, 1.9)
    p = np.clip((t - Z['hiz0']) / 1.1, 0, 1); p = p * p * (3 - 2 * p)
    r = r + (6.2 - 1.9) * p
    p2 = np.clip((t - Z['lvup']) / 0.25, 0, 1)
    return r + 1.0 * p2


_SS = np.concatenate([[0], np.cumsum((_hiz(_TT[:-1]) + _hiz(_TT[1:])) / 2 * 0.001)])


def adim_s(t): return float(np.interp(t, _TT, _SS))
def adim_t(s): return float(np.interp(s, _SS, _TT))


SW, SH = 16, 5          # basamak genişliği / yüksekliği (iç piksel)
HOP0 = 0.55             # adım içinde zıplamanın başladığı oran
TOPLA = 0.80            # paranın toplandığı oran


def zipla_y(t):
    return 10 if t < Z['hiz0'] else lerp(10, 6, prog(t, Z['hiz0'], 0.8))


def kahraman_dunya(t):
    """(x, y_ayak, kare, havada) dünya koordinatında; y yukarı."""
    s = adim_s(t); k = math.floor(s); f = s - k
    x = s * SW
    if f < HOP0:
        y = k * SH; havada = False
    else:
        q = (f - HOP0) / (1 - HOP0)
        y = k * SH + q * SH + math.sin(math.pi * q) * zipla_y(t); havada = True
    if s <= 0.001:
        kare_ = 'd'
    elif havada:
        kare_ = 'z'
    else:
        kare_ = YURU[int(s * 6.5) % 4]
    return x, y, kare_, havada


def gun(t):
    s1 = adim_s(Z['hiz0']); d0 = 1 + math.floor(s1)
    if t < Z['hiz0']: return 1 + math.floor(adim_s(t))
    p = prog(t, Z['hiz0'] + 0.05, Z['gun365'] - Z['hiz0'] - 0.05)
    return int(round(lerp(d0, METIN['sayac'], p ** 1.6)))


def toplama_zamanlari():
    out = []; k = 0
    while True:
        tk = adim_t(k + TOPLA)
        if tk > Z['wipe1'] + 0.1 or k > 200: break
        out.append((k, tk)); k += 1
    return out


TOPLAMA = toplama_zamanlari()
ZIPLAMA = [adim_t(k + HOP0) for k, _ in TOPLAMA]


# =====================================================================================
#  ARKA PLAN KATMANLARI
# =====================================================================================
def gok(buf, renkler, ust, alt, kay=0):
    """Bayer titreşimli dikey gradyan (renkler: üstten alta)."""
    H, W = buf.shape
    ys = np.arange(H)[:, None]; xs = np.arange(W)[None, :]
    v = np.clip((ys - ust) / max(1, alt - ust), 0, 0.9999) * (len(renkler) - 1)
    b = BAYER[ys % 4, (xs + kay) % 4]
    i = np.clip(np.floor(v + b - 0.5 + 0.5).astype(int), 0, len(renkler) - 1)
    i = np.clip(np.floor(v + (b - 0.5)).astype(int) + 0, 0, len(renkler) - 1)
    buf[:] = np.asarray(renkler)[np.clip(np.where(v - np.floor(v) > b, np.floor(v) + 1, np.floor(v)).astype(int), 0, len(renkler) - 1)]


def _dag_yuk(xw, tohum, genlik, dalga):
    y = np.zeros_like(xw, dtype=float)
    for i, (a, l) in enumerate(zip(genlik, dalga)):
        ph = (tohum * 1.7 + i * 2.3)
        u = xw / l + ph
        y += a * (2 * np.abs(u - np.floor(u + 0.5)))  # üçgen dalga -> sivri tepeler
    return y


def daglar(buf, kamx, taban, renk_a, renk_b, kar=None, tohum=0, genlik=(26, 9, 4), dalga=(97, 41, 17), f=0.15):
    H, W = buf.shape
    xw = np.arange(W) + kamx * f
    yuk = _dag_yuk(xw, tohum, genlik, dalga)
    ust = (taban - yuk).astype(int)
    egim = np.gradient(yuk)
    ys = np.arange(H)[:, None]
    m = ys >= ust[None, :]
    renk = np.where(egim[None, :] > 0, renk_a, renk_b)
    buf[m] = np.broadcast_to(renk, m.shape)[m]
    if kar is not None:
        tepe = yuk > (sum(genlik) * 0.62)
        km = m & (ys < (ust + 4 + (np.arange(W) % 3 == 0))[None, :]) & tepe[None, :]
        buf[km] = kar


def tepeler(buf, kamx, taban, renk, renk2, f=0.35, tohum=1, agac=True):
    H, W = buf.shape
    xw = np.arange(W) + kamx * f
    yuk = 10 + 7 * np.sin(xw / 23 + tohum) + 4 * np.sin(xw / 9.3 + tohum * 2)
    ust = (taban - yuk).astype(int)
    ys = np.arange(H)[:, None]
    m = ys >= ust[None, :]
    buf[m] = renk
    # titreşimli alt gölge
    xs = np.arange(W)[None, :]
    alt = m & (ys > ust[None, :] + 8) & (((xs + ys) % 2 == 0) | (ys > ust[None, :] + 14))
    buf[alt] = renk2
    if agac:
        for xa in range(-40, W + 40):
            xg = xa + kamx * f
            if int(math.floor(xg)) % 37 != 0: continue
            xi = int(xa); yb = int(taban - (10 + 7 * math.sin(xg / 23 + tohum) + 4 * math.sin(xg / 9.3 + tohum * 2)))
            for r in range(9):
                yw = r - 9
                wdt = (r + 2) // 2
                kutu(buf, xi - wdt, yb + yw - 3, 2 * wdt + 1, 1, YESIL if r < 6 else CAMGOBEGI)
            kutu(buf, xi, yb - 3, 1, 4, MOR)


def bulutlar(buf, kamx, y0, t, f=0.06):
    H, W = buf.shape
    span = W + 80
    for i, (bx, by, bs) in enumerate([(10, 0, 1.0), (85, 12, 0.7), (150, 4, 1.2), (230, 18, 0.8), (290, 2, 0.9)]):
        x = ((bx * (W / 180) - kamx * f - t * 3 * (1 + i % 2)) % span) - 40
        y = y0 + by
        bulut(buf, x, y, bs)


def bulut(buf, x, y, s):
    w, h = int(34 * s), int(14 * s)
    ys, xs = np.mgrid[0:h, 0:w]
    m = np.zeros((h, w), bool)
    for cx, cy, r in [(0.25, 0.65, 0.22), (0.5, 0.45, 0.32), (0.75, 0.62, 0.24), (0.4, 0.7, 0.25), (0.62, 0.72, 0.25)]:
        m |= ((xs - cx * w) / (r * w)) ** 2 + ((ys - cy * h) / (r * w)) ** 2 < 1
    m &= ys < h * 0.92
    renk = np.where(ys > h * 0.62, ACIKGRI, BEYAZ)
    boya(buf, genislet(m, 1)[1:-1, 1:-1] if False else m, x, y, renk)


def basamaklar(buf, kamx, kamy, tabany, k0, k1, t):
    """Basamak k: x ∈ [(k-0.2)SW, (k+0.8)SW), üst = k*SH. Çim + tuğla toprak."""
    H, W = buf.shape
    for k in range(k0, k1):
        xa = int(round((k - 0.2) * SW - kamx)); xb = int(round((k + 0.8) * SW - kamx))
        yu = int(round(tabany - (k * SH - kamy)))
        if xb < 0 or xa > W or yu > H: continue
        kutu(buf, xa, yu, xb - xa, H - yu, TURUNCU)
        # tuğla dokusu
        for yy in range(yu + 5, H, 5):
            kutu(buf, xa, yy, xb - xa, 1, KIRMIZI)
            off = 4 if ((yy - yu) // 5 + k) % 2 else 12
            kutu(buf, xa + off, yy - 4, 1, 4, KIRMIZI)
        kutu(buf, xa, yu, xb - xa, 3, ACIKYESIL)
        kutu(buf, xa, yu + 3, xb - xa, 1, YESIL)
        for j in range(xa, xb, 3):
            kutu(buf, j + (k % 2), yu + 4, 1, 1, YESIL)
        kutu(buf, xa, yu, 1, H - yu, SIYAH)
        kutu(buf, xa, yu - 1, xb - xa + 1, 1, SIYAH)


def elmas_perde(buf, p, renk=SIYAH, n=14):
    """Klasik elmas geçiş; p 0..1 kaplama."""
    if p <= 0: return
    H, W = buf.shape
    ys, xs = np.mgrid[0:H, 0:W]
    d = np.abs((xs % n) - n / 2 + 0.5) + np.abs((ys % n) - n / 2 + 0.5)
    buf[d < p * (n + 1)] = renk


# =====================================================================================
#  SAHNELER
# =====================================================================================
def duzen(w, h):
    dikey = h > w
    return dict(dikey=dikey, anx=int(w * 0.34) if dikey else int(w * 0.30), taban=int(h * 0.62) if dikey else int(h * 0.74))


def hud(buf, t, w, h, L):
    d = gun(t); guc = sayi_carpani() ** (d / max(1, METIN['sayac']))
    yaz(buf, 'GÜN', 6, 3, BEYAZ, golge=LACI)
    yaz(buf, f'{d:03d}', 6 + metin_gen('GÜN') + 4, 3, SARI, golge=LACI)
    yaz(buf, f'x{guc:.2f}' if guc < 10 else f'x{guc:.1f}', w - 6, 3, SARI, golge=LACI, hiza='sag')
    yaz(buf, 'GÜÇ', w - 6 - metin_gen('x00.00') - 6, 3, BEYAZ, golge=LACI, hiza='sag')
    # XP çubuğu
    bx, by, bw = 6, 18, w - 12
    yaz(buf, 'XP', bx, by - 3, ACIKMAVI, golge=LACI)
    x0 = bx + 14; ww = bw - 14
    kutu(buf, x0 - 1, by - 1, ww + 2, 8, SIYAH)
    kutu(buf, x0, by, ww, 6, KOYUGRI)
    dolu = d / max(1, METIN['sayac'])
    fw = int(round(ww * dolu))
    if fw > 0:
        dolu_renk = SARI if t > Z['lvup'] and int(t * 12) % 2 else ACIKYESIL
        kutu(buf, x0, by, fw, 6, dolu_renk)
        kutu(buf, x0, by, fw, 2, BEYAZ if dolu_renk == SARI else ACIKYESIL)
        kutu(buf, x0, by + 4, fw, 2, YESIL if dolu_renk != SARI else TURUNCU)
    for j in range(x0 + 8, x0 + ww, 8):
        kutu(buf, j, by, 1, 6, SIYAH if j < x0 + fw else GRI)


def sahne_oyun(buf, t, w, h, L):
    """Sahne 1+2: paralaks dünya, basamak tırmanan kahraman."""
    hx, hy, kare_, havada = kahraman_dunya(t)
    s = adim_s(t)
    kamx = hx - L['anx']; kamy = s * SH
    taban = L['taban']
    # sarsıntı (level up)
    if Z['lvup'] <= t < Z['lvup'] + 0.3:
        a = int(3 * (1 - prog(t, Z['lvup'], 0.3)) + 0.5)
        kamx += a * (1 if int(t * 60) % 2 else -1); kamy += a * (1 if int(t * 45) % 2 else -1)
    # gökyüzü: yıl ilerledikçe gün batımına kayar
    gp = prog(t, Z['hiz0'], Z['gun365'] - Z['hiz0'])
    if gp < 0.4:
        gok(buf, [LACI, MAVI, ACIKMAVI, CYAN], 0, taban - 10)
    else:
        gok(buf, [MOR, KIRMIZI, TURUNCU, SARI], 0, taban - 10) if gp < 0.999 or t < Z['lvup'] else gok(buf, [LACI, MAVI, ACIKMAVI, CYAN], 0, taban - 10)
    if t < Z['lvup'] and 0.5 <= gp < 0.999:
        pass
    # güneş
    gx = int((w * 0.78 if L['dikey'] else w * 0.12) - kamx * 0.02); gy = int(taban * (0.30 if L['dikey'] else 0.42) + kamy * 0.03)
    yy, xx = np.mgrid[-10:11, -10:11]
    boya(buf, xx ** 2 + yy ** 2 <= 90, gx - 10, gy - 10, SARI)
    boya(buf, xx ** 2 + yy ** 2 <= 30, gx - 10 - 2, gy - 10 - 2, BEYAZ)
    bulutlar(buf, kamx, int(taban * 0.12) + 20, t)
    daglar(buf, kamx, taban - 18 + kamy * 0.08, ACIKGRI, GRI, kar=BEYAZ, tohum=0, f=0.12)
    daglar(buf, kamx, taban + 2 + kamy * 0.16, GRI, KOYUGRI, tohum=3, genlik=(16, 6, 3), dalga=(61, 29, 11), f=0.22)
    tepeler(buf, kamx, taban + 18 + kamy * 0.35, CAMGOBEGI, LACI, f=0.4)
    # hız çizgileri (sahne 2)
    hzp = prog(t, Z['hiz0'] + 0.3, 0.6) * (1 - prog(t, Z['wipe1'] - 0.2, 0.2))
    if hzp > 0:
        for i in range(14):
            yv = int((i * 37 + 11) % (taban + 10)) + 26
            ln = int(18 + (i * 13) % 30) * hzp
            xv = int(w - ((t * 600 + i * 97) % (w + 80)))
            kutu(buf, xv, yv, ln, 1, BEYAZ if i % 3 else CYAN)
    k0 = int((kamx) // SW) - 1
    basamaklar(buf, kamx, kamy, taban, max(-30, k0), k0 + w // SW + 3, t)
    # sol düz zemin (başlangıç öncesi)
    # paralar
    for k, tk in TOPLAMA:
        if t >= tk: continue
        px = (k + TOPLA) * SW - kamx - 3
        q = (TOPLA - HOP0) / (1 - HOP0)
        py = taban - (k * SH + q * SH + zipla_y(tk) * math.sin(math.pi * q) - kamy) - 20
        if px < -10 or px > w + 10: continue
        bob = int(round(math.sin(t * 5 + k) * 1.5))
        ciz_sprite(buf, PARA[int(t * 10 + k) % 4], px, py + bob)
    # kahraman
    sx = int(round(hx - kamx)) - 6; sy = int(round(taban - (hy - kamy))) - 17
    parla = t > Z['lvup'] and t < Z['wipe1'] and int(t * 15) % 2 == 0
    if parla:
        m, idx = KAHRAMAN[kare_]
        boya(buf, genislet(m, 1), sx - 1, sy - 1, SARI)
    ciz_sprite(buf, KAHRAMAN[kare_], sx, sy)
    # toz (yere inişte)
    for k, tk in TOPLAMA:
        ti = adim_t(k + 1.0)
        if 0 <= t - ti < 0.2:
            q = (t - ti) / 0.2
            xg = (k + 1) * SW - kamx; yg = taban - ((k + 1) * SH - kamy)
            for sgn in (-1, 1):
                kutu(buf, xg + sgn * (4 + q * 8), yg - 2 - q * 3, 2, 2, BEYAZ if q < 0.5 else ACIKGRI)
    # +%1 pop'ları
    for k, tk in TOPLAMA:
        dt = t - tk
        omur = 0.65 if tk < Z['hiz0'] else 0.32
        if not (0 <= dt < omur): continue
        if dt > omur - 0.15 and int(dt * 30) % 2: continue
        px = (k + TOPLA) * SW - kamx; py = taban - ((k + TOPLA) * SH - kamy) - 30 - out_cubic(prog(dt, 0, 0.5)) * 14
        if dt < 0.12:  # parıltı
            ciz_sprite(buf, _YILDIZ, px - 2, py + 10)
        renk = SARI if (dt * 10) % 2 < 1 else BEYAZ
        yaz(buf, '+' + ekran(METIN['kanca']), px, py, renk, hiza='orta', golge=None)
    hud(buf, t, w, h, L)
    # 37x ve LEVEL UP
    if t >= Z['x37']:
        p = prog(t, Z['x37'], 0.35)
        k = max(1, int(round(out_back(p) * sigdir([ekran(METIN['sayi'])], 6 if L['dikey'] else 4, w - 8))))
        cy = int(h * 0.24) if L['dikey'] else 34
        cx = w // 2 if L['dikey'] else int(w * 0.64)
        renk_s = [SARI] * (SATIR * k)
        rs = [BEYAZ if r < k * (UST + 2) else SARI if r < k * (UST + 5) else TURUNCU for r in range(SATIR * k)]
        yaz(buf, ekran(METIN['sayi']), cx, cy - (UST * k), SARI, k=k, golge=KIRMIZI, hiza='orta', renk_satir=rs)
    if t >= Z['lvup']:
        dt = t - Z['lvup']
        dongu = [SARI, BEYAZ, CYAN, ACIKYESIL, TURUNCU]
        k2 = 2
        cy2 = int(h * 0.24) + 50 if L['dikey'] else 70
        cx2 = w // 2 if L['dikey'] else int(w * 0.64)
        if dt < 1.2 or int(dt * 8) % 4 != 0:
            sw_ = metin_gen('LEVEL UP!', k2); x0 = cx2 - sw_ // 2
            for i, ch in enumerate('LEVEL UP!'):
                yo = int(round(-3 * abs(math.sin(dt * 9 - i * 0.6)))) if dt < 1.5 else 0
                gx = x0 + (metin_gen('LEVEL UP!'[:i], k2) + k2 if i else 0)
                yaz(buf, ch, gx, cy2 + yo, dongu[(int(dt * 14) + i) % 5], k=k2, golge=LACI)
        # yıldız patlaması
        if dt < 0.9:
            for i in range(16):
                a = i / 16 * 2 * math.pi
                r = 8 + out_cubic(dt / 0.9) * (60 if L['dikey'] else 70)
                px = (w // 2 if L['dikey'] else int(w * 0.64)) + math.cos(a) * r; py = (int(h * 0.24) + 18 if L['dikey'] else 48) + math.sin(a) * r * 0.8
                if dt < 0.6 or int(dt * 30) % 2:
                    ciz_sprite(buf, _YILDIZ, px - 2, py - 2) if i % 2 == 0 else kutu(buf, px, py, 2, 2, BEYAZ)
        if dt < 0.07: buf[:] = np.where(buf == SIYAH, LACI, BEYAZ)
    # geçiş
    elmas_perde(buf, prog(t, Z['wipe1'], Z['s3'] - Z['wipe1']))


def sahne_kucuk_buyuk(buf, t, w, h, L):
    taban = int(h * 0.74) if L['dikey'] else int(h * 0.78)
    sars = 0
    if Z['dev'] <= t < Z['dev'] + 0.35:
        sars = int(round(3 * (1 - prog(t, Z['dev'], 0.35)))) * (1 if int(t * 60) % 2 else -1)
    taban += sars
    # sakin gece-öncesi gökyüzü -> "büyük fark"ta aydınlanır
    if t < Z['buyuk']:
        gok(buf, [LACI, LACI, MAVI, ACIKMAVI], 0, taban)
    else:
        gok(buf, [MAVI, ACIKMAVI, CYAN, BEYAZ], 0, taban)
    bulutlar(buf, 0, int(h * 0.1), t + 20)
    daglar(buf, (t - 6) * 20, taban - 10, ACIKGRI, GRI, kar=BEYAZ, tohum=2, f=1)
    tepeler(buf, (t - 6) * 40, taban + 4, CAMGOBEGI, LACI, f=1, tohum=4)
    kutu(buf, 0, taban, w, h - taban, TURUNCU)
    for yy in range(taban + 5, h, 5):
        kutu(buf, 0, yy, w, 1, KIRMIZI)
        for xx in range((yy // 5 % 2) * 8, w, 16): kutu(buf, xx, yy - 4, 1, 4, KIRMIZI)
    kutu(buf, 0, taban, w, 3, ACIKYESIL); kutu(buf, 0, taban + 3, w, 1, YESIL); kutu(buf, 0, taban - 1, w, 1, SIYAH)
    # minik basamak
    bx = int(w * 0.42) if L['dikey'] else int(w * 0.40)
    kutu(buf, bx - 1, taban - 5, 14, 5, SIYAH); kutu(buf, bx, taban - 4, 12, 4, TURUNCU); kutu(buf, bx, taban - 4, 12, 2, ACIKYESIL)
    # kahraman: küçük adım (zıplama) -> büyüme titremesi -> dev
    x0 = bx - 22
    p = prog(t, Z['adim'], 0.35)
    hx = lerp(x0, bx + 6, in_out_cubic(p)); hy = taban - 4 * clamp(p * 2 - 0.6) - math.sin(math.pi * p) * 7
    kare_ = 'd' if p in (0.0, 1.0) else ('z' if 0.15 < p < 0.85 else 'b')
    if t < Z['adim']: kare_ = YURU[int(t * 6) % 4] if t > Z['s3'] + 0.05 else 'd'; hx = x0 - 10 * (1 - prog(t, Z['s3'], Z['adim'] - Z['s3']))
    olc = 1
    if t >= Z['buyuk']:
        q = prog(t, Z['buyuk'], Z['dev'] - Z['buyuk'])
        sira = [1, 2, 1, 2, 3, 2, 3, 4, 3, 4]
        olc = sira[min(len(sira) - 1, int(q * len(sira)))] if q < 1 else 4
        if not L['dikey']: olc = min(olc, 3) if olc < 4 else 3
    m, _ = KAHRAMAN[kare_]
    sx = int(round(hx)) - 6 * olc; sy = int(round(hy)) - 16 * olc - 1
    if olc > 1:
        sx = bx + 6 - 6 * olc; sy = taban - 4 - 16 * olc
    if t >= Z['dev']:
        dt = t - Z['dev']
        if int(dt * 10) % 2 == 0 and dt < 0.6:
            boya(buf, genislet(np.kron(m, np.ones((olc, olc), bool)).astype(bool), 2), sx - 2, sy - 2, SARI)
    ciz_sprite(buf, KAHRAMAN[kare_], sx, sy, k=olc)
    # metinler
    if Z['kucuk'] <= t:
        dt = t - Z['kucuk']
        if t < Z['buyuk'] + 0.05 or int(t * 20) % 2:
            if t < Z['dev'] - 0.05:
                lx = bx + 6; ly = taban - 40 - (0 if dt > 0.12 else 4)
                yazi = ekran(METIN['kucuk'])
                lx = min(max(lx, metin_gen(yazi) // 2 + 2), w - metin_gen(yazi) // 2 - 2)
                yaz(buf, yazi, lx, ly, BEYAZ, hiza='orta', golge=LACI)
                kutu(buf, lx, ly + SATIR + 2, 1, 14, BEYAZ)  # ok
                kutu(buf, lx - 1, ly + SATIR + 14, 3, 1, BEYAZ); kutu(buf, lx, ly + SATIR + 15, 1, 1, BEYAZ)
    if t >= Z['buyuk'] + 0.08:
        p = prog(t, Z['buyuk'] + 0.08, 0.3)
        rs_f = lambda k: [BEYAZ if r < k * (UST + 2) else SARI if r < k * (UST + 5) else TURUNCU for r in range(SATIR * k)]
        buyuk = ekran(METIN['buyuk'])
        satirlar = bol(buyuk) if L['dikey'] else [buyuk]
        k = max(1, int(round(out_back(p) * sigdir(satirlar, 4 if L['dikey'] else 3, w - 8))))
        for i, sat in enumerate(satirlar):
            yaz(buf, sat, w // 2, (10 if L['dikey'] else 8) + i * satir_araligi(sat, k, 2 * k), SARI, k=k, golge=KIRMIZI,
                hiza='orta', renk_satir=rs_f(k))
        # toz bulutu
        dt = t - Z['dev']
        if 0 <= dt < 0.5:
            for i in range(8):
                xs_ = bx + 6 + (i - 3.5) * (8 + dt * 40); ys_ = taban - 3 - dt * 10 * (1 + i % 2)
                kutu(buf, xs_, ys_, 3, 3, BEYAZ if dt < 0.25 else ACIKGRI)
    if Z['buyuk'] <= t < Z['buyuk'] + 0.05:
        buf[:] = np.where(buf == SIYAH, SIYAH, BEYAZ)
    elmas_perde(buf, 1 - prog(t, Z['s3'], 0.25))
    elmas_perde(buf, prog(t, Z['wipe2'], Z['s4'] - Z['wipe2']))


def sahne_baslik(buf, t, w, h, L):
    taban = int(h * 0.86) if L['dikey'] else int(h * 0.82)
    gok(buf, [SIYAH, LACI, MOR, KIRMIZI], 0, taban - 4)
    # yıldızlar
    for i in range(46):
        sx = (i * 73 + 17) % w; sy = (i * 41 + 7) % max(1, int(taban * 0.7))
        tw = (math.sin(t * 6 + i * 1.3) > 0.3)
        if tw: kutu(buf, sx, sy, 1, 1, BEYAZ if i % 3 else CYAN)
        if i % 9 == 0 and tw:
            kutu(buf, sx - 1, sy, 3, 1, ACIKGRI); kutu(buf, sx, sy - 1, 1, 3, ACIKGRI); kutu(buf, sx, sy, 1, 1, BEYAZ)
    # ay
    yy, xx = np.mgrid[-9:10, -9:10]
    mx, my = (int(w * 0.82), int(h * 0.30)) if L['dikey'] else (int(w * 0.92), int(h * 0.36))
    boya(buf, xx ** 2 + yy ** 2 <= 70, mx - 9, my - 9, SARI)
    boya(buf, (xx - 3) ** 2 + (yy + 2) ** 2 <= 50, mx - 9, my - 9, SIYAH if False else LACI)
    daglar(buf, (t - 8) * 6, taban - 6, MOR, LACI, tohum=5, f=1)
    tepeler(buf, (t - 8) * 12, taban + 6, KOYUGRI, SIYAH, f=1, tohum=7, agac=False)
    kutu(buf, 0, taban, w, h - taban, TURUNCU)
    for yy_ in range(taban + 5, h, 5):
        kutu(buf, 0, yy_, w, 1, KIRMIZI)
        for xx_ in range((yy_ // 5 % 2) * 8, w, 16): kutu(buf, xx_, yy_ - 4, 1, 4, KIRMIZI)
    kutu(buf, 0, taban, w, 3, ACIKYESIL); kutu(buf, 0, taban + 3, w, 1, YESIL); kutu(buf, 0, taban - 1, w, 1, SIYAH)
    # kahraman (bekleme sallanması, START'ta zıplar)
    kare_ = 'd'; zy = 0
    if t >= Z['bas']:
        q = prog(t, Z['bas'], 0.45); zy = math.sin(math.pi * q) * 14; kare_ = 'z' if 0 < q < 1 else 'd'
    elif int(t * 2.5) % 2:
        zy = 1
    olc = 2
    ciz_sprite(buf, KAHRAMAN[kare_], int(w * (0.5 if L['dikey'] else 0.16)) - 6 * olc, taban - 16 * olc - int(zy), k=olc)
    # logo
    rs_f = lambda k: [BEYAZ if r < k * (UST + 2) else SARI if r < k * (UST + 5) else TURUNCU for r in range(SATIR * k)]
    cagri = ekran(METIN['cagri']).rstrip('.!')
    logo_s = bol(cagri)
    k = sigdir(logo_s if L['dikey'] else [cagri], 4 if L['dikey'] else 3, w - 8)
    ly = int(h * 0.17) if L['dikey'] else int(h * 0.17)

    def logo(s, x, y, t0, hiza='orta'):
        if t < t0: return
        p = prog(t, t0, 0.35)
        yd = int(round((1 - out_back(p, 2.4)) * -60))
        yaz(buf, s, x, y + yd, SARI, k=k, golge=KIRMIZI, hiza=hiza, renk_satir=rs_f(k))
        # parıltı süpürmesi
        sw_ = metin_gen(s, k); x0 = x - sw_ // 2 if hiza == 'orta' else x
        ps = ((t - t0 - 0.5) % 1.6) / 0.6
        if ps < 1:
            m = np.kron(metin_maske(s), np.ones((k, k), bool)).astype(bool)
            ys, xs = np.mgrid[0:m.shape[0], 0:m.shape[1]]
            band = np.abs((xs + ys * 0.6) - ps * (sw_ + 40) + 20) < 4
            boya(buf, m & band, x0, y + yd, BEYAZ)

    ilk, son = logo_s[0], (logo_s[1] if len(logo_s) > 1 else '')
    if L['dikey']:
        logo(ilk, w // 2, ly, Z['bugun'])
        if son: logo(son, w // 2, ly + satir_araligi(son, k, 6), Z['basla'])
    else:
        tw = metin_gen(cagri, k); x0 = w // 2 - tw // 2
        logo(ilk, x0, ly, Z['bugun'], 'sol')
        if son: logo(son, x0 + metin_gen(ilk + ' ', k) + k, ly, Z['basla'], 'sol')
    # ▶ START
    sy = int(h * 0.56) if L['dikey'] else int(h * 0.56)
    if t >= Z['start']:
        dt = t - Z['start']
        if t >= Z['bas']:
            goster = int((t - Z['bas']) * 16) % 2 == 0
            renk = BEYAZ if int((t - Z['bas']) * 16) % 4 < 2 else SARI
        else:
            goster = (dt % 0.6) < 0.4; renk = BEYAZ
        if goster:
            yaz(buf, '> START', w // 2, sy, renk, k=2 if L['dikey'] else 1 if False else 2, golge=LACI, hiza='orta')
    yaz(buf, 'EN İYİ ' + ekran(METIN['sayi']), w // 2, 4 if L['dikey'] else 3, ACIKGRI, golge=None, hiza='orta')
    elmas_perde(buf, 1 - prog(t, Z['s4'], 0.25))


def kare_ic(t, w, h):
    buf = np.zeros((h, w), np.int16)
    L = duzen(w, h)
    if t < Z['s3']:
        sahne_oyun(buf, t, w, h, L)
    elif t < Z['s4']:
        sahne_kucuk_buyuk(buf, t, w, h, L)
    else:
        sahne_baslik(buf, t, w, h, L)
    return buf


def kare(cv, t, W, H):
    import skia
    S = max(1, min(W, H) // 135)
    w, h = W // S, H // S
    buf = kare_ic(t, w, h)
    rgba = PAL[np.clip(buf, 0, 15)]
    big = np.repeat(np.repeat(rgba, S, 0), S, 1)
    tam = np.zeros((H, W, 4), np.uint8); tam[..., 3] = 255
    tam[:big.shape[0], :big.shape[1]] = big[:H, :W]
    img = skia.Image.fromarray(np.ascontiguousarray(tam), colorType=skia.kRGBA_8888_ColorType)
    cv.drawImage(img, 0, 0)


# =====================================================================================
#  SES: chiptune (120 BPM -> 2 sn'lik ölçüler sahne sınırlarına oturur)
# =====================================================================================
BPM = 120; VUR = 60 / BPM; ON6 = VUR / 4

# akorlar (başlangıç sn, kök midi, tip)
AKOR = [(0, 48, 'M'), (2, 45, 'm'), (4, 41, 'M'), (5, 43, 'M'), (6, 45, 'm'), (7, 41, 'M'), (7.5, 43, 'M'), (8, 48, 'M'),
        (9, 41, 'M'), (9.25, 43, 'M'), (9.6, 48, 'M')]


def akor(t):
    a = AKOR[0]
    for x in AKOR:
        if t >= x[0]: a = x
    kok, tip = a[1], a[2]
    return kok, [0, 4, 7] if tip == 'M' else [0, 3, 7]


def kare_dalga(f, d, duty=0.5, vib=0.0):
    tt = np.arange(int(d * SR)) / SR
    ph = np.cumsum(f * (1 + vib * np.sin(2 * math.pi * 5.5 * tt) * np.minimum(tt / 0.15, 1)) / SR)
    return np.where((ph % 1) < duty, 1.0, -1.0)


def ucgen(f, d):
    tt = np.arange(int(d * SR)) / SR
    ph = (f * tt) % 1
    return 4 * np.abs(ph - 0.5) - 1


def nota(f, d, dalga='kare', duty=0.5, a=0.004, rel=0.04, dec=None, vib=0.0):
    x = kare_dalga(f, d, duty, vib) if dalga == 'kare' else ucgen(f, d)
    e, tt = zarf(d, a, dec)
    r = np.clip((d - tt) / rel, 0, 1)
    return x * e * r


def yogunluk(t):
    """0..1 müzik enerjisi eğrisi (sakin -> yükseliş -> zirve -> sakin -> kalkış -> parlak final)."""
    pts = [(0, 0.25), (2.9, 0.35), (3.1, 0.5), (4.4, 0.75), (4.45, 1.0), (5.7, 1.0), (5.95, 0.15), (6.65, 0.2),
           (6.72, 0.85), (7.9, 0.8), (8.0, 0.65), (9.25, 0.7), (9.3, 1.0), (10, 1.0)]
    xs, ys = zip(*pts)
    return float(np.interp(t, xs, ys))


def muzik(n):
    sq = np.zeros((n, 2)); tri = np.zeros((n, 2)); dr = np.zeros((n, 2))
    nb = int(SURE / ON6)
    for i in range(nb):
        t0 = i * ON6
        kok, ar = akor(t0); E = yogunluk(t0)
        beat16 = i % 16; ceyrek = i % 4 == 0
        sessiz_bolge = (5.92 <= t0 < 6.0) or (7.92 <= t0 < 8.0)
        # --- üçgen bas ---
        if 6.0 <= t0 < 6.7 or t0 < 3.0:
            if beat16 % 8 == 0:
                tri_n = nota(mtof(kok), VUR * 1.9, 'ucgen', a=0.01, rel=0.2)
                ekle(tri, t0, tri_n, 0.55)
        elif not sessiz_bolge:
            if i % 2 == 0:
                m = kok + (12 if (i // 2) % 2 else 0)
                ekle(tri, t0, nota(mtof(m), ON6 * 1.8, 'ucgen', rel=0.03), 0.6)
        # --- arpej (yumuşak darbe dalgası) ---
        if not sessiz_bolge and t0 < 9.3:
            hiz = 2 if (t0 < 3.0 or 6.0 <= t0 < 6.7) else 1
            if i % hiz == 0:
                nn = kok + 24 + ar[(i // hiz) % 3] + (12 if (i // hiz) % 6 >= 3 and E > 0.6 else 0)
                g = 0.10 + 0.10 * E
                ekle(sq, t0, nota(mtof(nn), ON6 * 0.9, duty=0.25, rel=0.05, dec=0.12), g, pan=0.35 * (1 if (i // hiz) % 2 else -1))
        # --- davul ---
        if sessiz_bolge: continue
        davul = (3.0 <= t0 < 5.92) or (6.7 <= t0 < 7.92) or (8.0 <= t0 < 10)
        if davul:
            if ceyrek and (t0 >= 4.45 or t0 >= 6.7 or beat16 % 8 == 0 or t0 >= 3.5):
                d_ = 0.16; tt = np.arange(int(d_ * SR)) / SR
                f = 50 + 120 * np.exp(-tt / 0.03)
                ekle(dr, t0, np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.07), 0.9)
            if (4.45 <= t0 < 5.92 or 6.7 <= t0 < 7.92 or t0 >= 8.0) and beat16 % 8 == 4:
                x = gurultu(0.14, i) * np.exp(-np.arange(int(0.14 * SR)) / SR / 0.05)
                x = x - lp_hizli(x, 900)
                ekle(dr, t0, x * 0.5, 0.45); ekle(dr, t0, nota(180, 0.1, 'ucgen', dec=0.04) * 0.4, 0.45)
            hat = (i % 2 == 0) or t0 >= 4.45
            if hat and t0 >= 3.3:
                x = gurultu(0.03, 1000 + i); x = x - lp_hizli(x, 5000)
                ekle(dr, t0, x * np.exp(-np.arange(len(x)) / SR / 0.012), 0.10 + 0.08 * E, pan=0.3)
        elif t0 >= 1.5 and t0 < 3.0 and i % 4 == 2:  # sahne 1: hafif çıt
            x = gurultu(0.02, 2000 + i); x = x - lp_hizli(x, 6000)
            ekle(dr, t0, x * np.exp(-np.arange(len(x)) / SR / 0.008), 0.06)
    # trampet rulosu 4.0 -> 4.45
    for j in range(12):
        tr = 4.0 + j * (0.45 / 12)
        x = gurultu(0.06, 3000 + j) * np.exp(-np.arange(int(0.06 * SR)) / SR / 0.02); x = x - lp_hizli(x, 1200)
        ekle(dr, tr, x, 0.12 + 0.3 * j / 12)
    # zirve kreşendosu (crash) 4.45 ve 6.72
    for tc, g in [(4.45, 0.35), (6.72, 0.28), (9.6, 0.25)]:
        x = gurultu(1.0, int(tc * 10)); x = x - lp_hizli(x, 3000)
        ekle(dr, tc, x * np.exp(-np.arange(len(x)) / SR / 0.3), g)
    # --- solo melodi (zirve ve final) ---
    MEL = [  # (sn, süre, midi)
        (4.45, 0.25, 77), (4.75, 0.25, 81), (5.0, 0.25, 84), (5.25, 0.5, 86), (5.5, 0.25, 84),
        (6.75, 0.25, 76), (7.0, 0.25, 79), (7.25, 0.5, 81), (7.5, 0.25, 79), (7.75, 0.2, 83),
        (8.0, 0.5, 79), (8.5, 0.25, 84), (8.75, 0.25, 83), (9.0, 0.25, 81),
    ]
    for t0, d, m in MEL:
        ekle(sq, t0, nota(mtof(m), d * 0.95, duty=0.5, rel=0.06, vib=0.006, dec=0.6), 0.22)
        ekle(sq, t0 + 0.12, nota(mtof(m), d * 0.8, duty=0.5, rel=0.06, dec=0.3), 0.06, pan=0.5)  # yankı
    # final akoru (çözülme)
    for j, m in enumerate([60, 64, 67, 72]):
        ekle(sq, 9.6, nota(mtof(m + 12), 0.35, duty=0.25, dec=0.5, rel=0.3), 0.12, pan=(j - 1.5) * 0.3)
    ekle(tri, 9.6, nota(mtof(36), 0.35, 'ucgen', rel=0.3), 0.7)
    for c in range(2):
        sq[:, c] = lp_hizli(lp_hizli(sq[:, c], 3200), 6000)
        dr[:, c] = lp_hizli(dr[:, c], 9000)
        tri[:, c] = lp_hizli(tri[:, c], 5000)
    out = sq * 0.9 + tri * 1.0 + dr * 0.8
    # genel enerji zarfı
    tt = np.arange(n) / SR
    env = np.interp(tt, *zip(*[(0, 0.5), (2.9, 0.6), (4.4, 0.85), (4.45, 1.0), (5.8, 1.0), (6.0, 0.5), (6.65, 0.5), (6.72, 0.95), (10, 1.0)]))
    return out * env[:, None]


def sfx(n):
    b = np.zeros((n, 2))
    tt_ = lambda d: np.arange(int(d * SR)) / SR
    # zıplama blipleri (adımla birlikte tizleşir)
    for j, tz in enumerate(ZIPLAMA):
        if tz > Z['wipe1']: break
        d = 0.07; tt = tt_(d)
        f0 = 330 * 2 ** (min(j, 24) / 24)
        f = f0 * (1 + 1.2 * tt / d)
        x = np.where((np.cumsum(f) / SR) % 1 < 0.5, 1.0, -1.0) * np.exp(-tt / 0.04)
        ekle(b, tz, lp_hizli(x, 3500), 0.25 if tz < Z['hiz0'] else 0.15)
    # para sesi (B5 -> E6)
    for j, (k, tc) in enumerate(TOPLAMA):
        if tc > Z['wipe1']: break
        g = 0.32 if tc < Z['hiz0'] else 0.18
        ekle(b, tc, lp_hizli(nota(988, 0.06, duty=0.5), 4000), g, pan=0.2)
        ekle(b, tc + 0.06, lp_hizli(nota(1319, 0.18, duty=0.5, dec=0.08), 4000), g, pan=0.2)
    # 37x vuruş + LEVEL UP arpeji
    ekle(b, Z['x37'], nota(110, 0.3, 'ucgen', dec=0.12), 0.5)
    for j, m in enumerate([72, 76, 79, 84, 88, 91, 96]):
        ekle(b, Z['lvup'] + j * 0.055, lp_hizli(nota(mtof(m), 0.12, duty=0.25, dec=0.1), 4500), 0.3)
    ekle(b, Z['lvup'] + 7 * 0.055, lp_hizli(nota(mtof(96), 0.4, duty=0.5, dec=0.18, vib=0.01), 4500), 0.25)
    # elmas geçiş süpürmesi
    for tw in (Z['wipe1'], Z['wipe2']):
        d = 0.4; tt = tt_(d)
        x = gurultu(d, int(tw * 100)); x = lp_hizli(x, 2500) * np.sin(np.pi * tt / d)
        ekle(b, tw - 0.1, x, 0.25)
    # küçük adım: minik blip
    ekle(b, Z['adim'], lp_hizli(nota(1400, 0.05, duty=0.125, dec=0.03), 5000), 0.18)
    # büyüme: kademeli yükselen titreşim (power-up)
    for j in range(10):
        tj = Z['buyuk'] + j * (Z['dev'] - Z['buyuk']) / 10
        m = [67, 74, 67, 74, 79, 74, 79, 86, 79, 86][j]
        ekle(b, tj, lp_hizli(nota(mtof(m), 0.022, duty=0.5), 4000), 0.2)
    d = 0.6; tt = tt_(d)
    boom = np.sin(2 * math.pi * np.cumsum(45 + 90 * np.exp(-tt / 0.05)) / SR) * np.exp(-tt / 0.22)
    ekle(b, Z['dev'], boom, 0.7)
    ekle(b, Z['dev'], lp_hizli(gurultu(0.4, 77), 600) * np.exp(-tt_(0.4) / 0.12), 0.5)
    # logo düşüşleri
    for tl in (Z['bugun'] + 0.2, Z['basla'] + 0.2):
        ekle(b, tl, nota(90, 0.18, 'ucgen', dec=0.07), 0.45)
    # START jingle -> çözülme
    for j, m in enumerate([67, 72, 76, 79]):
        ekle(b, Z['bas'] + j * 0.07, lp_hizli(nota(mtof(m + 12), 0.1, duty=0.25, dec=0.08), 4500), 0.28)
    return b


AYAR = {'kapak_t': 4.75, 'sfx_db': -4.0}
