"""Kolaj malzemeleri (skia): yırtık kâğıt, makasla kesilmiş kenar, yarım ton (halftone) baskı, kesik harf,
bant, keçeli kalem çizgisi ve kâğıt dokusu.

Bütün kenarlar vektördür ve tam çözünürlükte, kenar yumuşatmayla çizilir: yırtık kenar her 2 pikselde
bir örneklenen yumuşak gürültüdür (köşeli çokgen değil), makas kenarı 25–35 piksellik düz kesimlerdir.
Parçalar bir kez `skia.Picture` olarak kaydedilir; her karede yalnız dönüşümle yeniden oynatılır.
Ölçüler 1080 piksellik kısa kenara göre `u` ile çarpılır.
"""

from __future__ import annotations

import math
import random

import numpy as np
import skia

import fontlar


def renk(hex_: str, a: float = 1.0) -> int:
    return (int(round(a * 255)) << 24) | int(hex_.lstrip("#"), 16)


def karistir(h1: str, h2: str, p: float) -> str:
    a = [int(h1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(h2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * p):02X}" for x, y in zip(a, b))


def boya(c: int, stroke: float = 0, blur: float = 0, blend=None, cap=True) -> skia.Paint:
    p = skia.Paint(AntiAlias=True, Color=c)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend is not None:
        p.setBlendMode(blend)
    return p


# ---------- gürültü ----------
class Dalga:
    """Yumuşak 1B gürültü: rastgele fazlı sinüslerin toplamı (tekrar etmez, her yerde türevlenebilir)."""

    def __init__(self, rnd: random.Random, oktavlar: list[tuple[float, float]]):
        # oktav: (dalga boyu px, genlik px); her oktavda 3 sinüs
        self.b = [(2 * math.pi / (dl * rnd.uniform(0.7, 1.3)), rnd.uniform(0, 2 * math.pi), g * rnd.uniform(0.5, 1.0) / 1.7)
                  for dl, g in oktavlar for _ in range(3)]

    def __call__(self, x: float) -> float:
        return sum(g * math.sin(w * x + f) for w, f, g in self.b)


def yirtik_oktavlar(g: float) -> list[tuple[float, float]]:
    """Yırtık kâğıt kenarı: büyük dalgalanma + orta ısırıklar + ince lif titreşimi."""
    return [(160, g), (38, g * 0.45), (11, g * 0.2), (4.5, g * 0.07)]


def kenar_noktalari(p0, p1, dalga: Dalga, ic: float = 0.0, adim: float = 2.0, uc: float = 14.0, s0: float = 0.0):
    """p0→p1 doğrusunu normali boyunca dalga(s) kadar oynatır (sol normal = içe). Uçlarda yumuşak sıfırlanır."""
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    n = max(2, int(L / adim))
    tx, ty = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -ty, tx
    out = []
    for i in range(n + 1):
        s = L * i / n
        k = min(1.0, s / uc, (L - s) / uc) if uc > 0 else 1.0
        k = k * k * (3 - 2 * k)
        d = (dalga(s + s0) + ic) * k
        out.append((x0 + tx * s + nx * d, y0 + ty * s + ny * d))
    return out


def cokgen(noktalar) -> skia.Path:
    p = skia.Path()
    p.moveTo(*noktalar[0])
    for q in noktalar[1:]:
        p.lineTo(*q)
    p.close()
    return p


def parca_yolu(w: float, h: float, rnd: random.Random, yirtik: str = "tb", genlik: float = 8.0, ic: float = 0.0,
               kes: float = 0.0) -> skia.Path:
    """(0,0)–(w,h) dikdörtgeni; `yirtik` içindeki kenarlar (t,r,b,l) yırtık, diğerleri makas kesiği.
    `ic`: yırtık kenarlar bu kadar içeri çekilir (lif şeridinin iç sınırı için). `kes`: köşe oynaması."""
    k = [(rnd.uniform(-kes, kes), rnd.uniform(-kes, kes)) for _ in range(4)]
    kose = [(0 + k[0][0], 0 + k[0][1]), (w + k[1][0], 0 + k[1][1]), (w + k[2][0], h + k[2][1]), (0 + k[3][0], h + k[3][1])]
    pts = []
    for j, ad in enumerate("trbl"):  # ekran koordinatında saat yönü: sol normal içe bakar
        a, b = kose[j], kose[(j + 1) % 4]
        if ad in yirtik:
            d = Dalga(rnd, yirtik_oktavlar(genlik))
            seg = kenar_noktalari(a, b, d, ic=ic, uc=0)
        else:
            seg = [a, b]
        pts += seg[:-1]
    return cokgen(pts)


def makas(yol: skia.Path, pay: float, adim: float, rnd: random.Random) -> skia.Path:
    """Siluetin `pay` kadar dışından makasla kesilmiş, düz kesimlerden oluşan beyaz kenar yolu."""
    st = boya(0xFF000000, stroke=2 * pay)
    genis = skia.Path()
    st.getFillPath(yol, genis)
    genis = skia.Op(genis, yol, skia.PathOp.kUnion_PathOp)
    out = skia.Path()
    pm = skia.PathMeasure(genis, True, 1)
    while True:
        L = pm.getLength()
        if L > 12:
            a = min(adim, L / 18)  # küçük iç konturlar (kupa sapının deliği) daha sık kesilir
            n = max(8, int(L / (a * rnd.uniform(0.85, 1.15))))
            pts = []
            for i in range(n):
                r = pm.getPosTan(L * (i + rnd.uniform(-0.2, 0.2)) / n)
                if r:
                    (pos, _tan) = r
                    pts.append((pos.x() + rnd.uniform(-0.6, 0.6), pos.y() + rnd.uniform(-0.6, 0.6)))
            if len(pts) > 2:
                out.addPath(cokgen(pts))
        if not pm.nextContour():
            break
    out.setFillType(skia.PathFillType.kWinding)
    return out


# ---------- doku ----------
_DOKU = {}


def doku(boyut: int = 384, tohum: int = 3) -> skia.Image:
    """Kenarsız tekrar eden kâğıt dokusu: işaretli gürültü (açık/koyu) + yumuşak lekeler. Bantlaşmayı da kırar."""
    if (boyut, tohum) in _DOKU:
        return _DOKU[(boyut, tohum)]
    g = np.random.default_rng(tohum)
    ince = g.standard_normal((boyut, boyut))
    leke = g.standard_normal((boyut, boyut))
    f = np.fft.fftfreq(boyut)
    r2 = f[:, None] ** 2 + f[None, :] ** 2
    leke = np.real(np.fft.ifft2(np.fft.fft2(leke) * np.exp(-r2 / (2 * 0.012 ** 2))))
    leke /= leke.std() + 1e-9
    lif = np.real(np.fft.ifft2(np.fft.fft2(g.standard_normal((boyut, boyut))) * np.exp(-(f[:, None] ** 2) / (2 * 0.004 ** 2)
                                                                                    - (f[None, :] ** 2) / (2 * 0.12 ** 2))))
    lif /= lif.std() + 1e-9
    v = 0.6 * ince + 0.35 * leke + 0.12 * lif
    a = np.clip(np.abs(v) * 7, 0, 40).astype(np.uint8)
    rgb = np.where(v[..., None] > 0, 255, 0).astype(np.uint8).repeat(3, axis=2)
    arr = np.dstack([rgb, a])
    img = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.ColorType.kRGBA_8888_ColorType)
    _DOKU[(boyut, tohum)] = img
    return img


def doku_boyasi(guc: float = 1.0, tohum: int = 3) -> skia.Paint:
    p = skia.Paint(AntiAlias=True)
    p.setShader(doku(tohum=tohum).makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat))
    p.setAlphaf(min(1.0, guc))
    return p


def golge(cv, yol: skia.Path, u: float, guc: float = 1.0, dx: float = 5, dy: float = 9, blur: float = 7):
    cv.save()
    cv.translate(dx * u, dy * u)
    cv.drawPath(yol, boya(renk("#000000", 0.26 * guc), blur=blur * u))
    cv.restore()


# ---------- yırtık kâğıt parçası ----------
def kagit(w: float, h: float, zemin: str, u: float, tohum: int, yirtik: str = "tb", genlik: float = 9.0,
          lif: str = "#FFFFFF", golgeli: bool = True, doku_gucu: float = 0.65, kes: float = 2.0):
    """Yırtık kenarlarında beyaz lif şeridi olan renkli kâğıt. Dönüş: (Picture, dış yol)."""
    rnd = random.Random(tohum)
    dis = parca_yolu(w, h, rnd, yirtik, genlik * u, kes=kes * u)
    ic = parca_yolu(w, h, random.Random(tohum * 7 + 1), yirtik, genlik * u * 0.8, ic=4.5 * u, kes=0)
    ic = skia.Op(ic, dis, skia.PathOp.kIntersect_PathOp)
    m = 40 * u
    rec = skia.PictureRecorder()
    cv = rec.beginRecording(skia.Rect(-m, -m, w + m, h + m))
    if golgeli:
        golge(cv, dis, u)
    cv.drawPath(dis, boya(renk(lif)))
    cv.drawPath(ic, boya(renk(zemin)))
    if doku_gucu:
        cv.save(); cv.clipPath(dis, skia.ClipOp.kIntersect, True)
        cv.drawPaint(doku_boyasi(doku_gucu, tohum % 5))
        cv.restore()
    return rec.finishRecordingAsPicture(), dis


# ---------- yarım ton ----------
def yari_ton_yolu(gri: np.ndarray, hucre: float, aci: float = 45.0, kaydir=(0.0, 0.0)) -> skia.Path:
    """gri (h,w; 0 = siyah, 1 = beyaz, maske dışı 1) → döndürülmüş ızgarada alanı koyulukla orantılı noktalar."""
    h, w = gri.shape
    a = math.radians(aci)
    ca, sa = math.cos(a), math.sin(a)
    R = math.hypot(w, h)
    k = np.arange(-R / hucre, R / hucre + 1)
    I, J = np.meshgrid(k, k)
    X = (I * ca - J * sa) * hucre + w / 2 + kaydir[0]
    Y = (I * sa + J * ca) * hucre + h / 2 + kaydir[1]
    ok = (X >= 0) & (X < w - 1) & (Y >= 0) & (Y < h - 1)
    X, Y = X[ok], Y[ok]
    koyu = 1.0 - gri[Y.astype(int), X.astype(int)]
    r = hucre * np.sqrt(np.clip(koyu, 0, 1) / math.pi) * 1.08
    yol = skia.Path()
    for x, y, rr in zip(X, Y, r):
        if rr > 0.45:
            yol.addCircle(float(x), float(y), float(rr))
    return yol


def raster(w: int, h: int, ciz) -> np.ndarray:
    """ciz(canvas) → beyaz zeminde gri tonlu görüntü, (h,w) float 0..1"""
    s = skia.Surface(int(w), int(h))
    with s as cv:
        cv.clear(0xFFFFFFFF)
        ciz(cv)
    return s.makeImageSnapshot().toarray()[..., 1].astype(np.float32) / 255.0


def kesik_resim(w: float, h: float, sil: skia.Path, gri_ciz, spotlar, P: dict, u: float, tohum: int,
                hucre: float = 9.0, pay: float = 11.0, ustler=()):
    """Dergiden kesilmiş fotoğraf parçası: makas kenarlı beyaz pay + kayık baskılı spot renk + yarım ton mürekkep.
    gri_ciz(cv): siluetin içini gri tonlarla boyar (ışık/gölge). spotlar: [(yol, hex)] düz renk alanları.
    ustler: noktaların üstüne basılan açık renkli alanlar (simitin susamı gibi)."""
    rnd = random.Random(tohum)
    gri = raster(w, h, lambda cv: (cv.clipPath(sil, skia.ClipOp.kIntersect, True), gri_ciz(cv)))
    noktalar = yari_ton_yolu(gri, hucre * u)
    kenar = makas(sil, pay * u, 28 * u, rnd)
    m = 50 * u
    rec = skia.PictureRecorder()
    cv = rec.beginRecording(skia.Rect(-m, -m, w + m, h + m))
    golge(cv, kenar, u)
    cv.drawPath(kenar, boya(renk(P["kagit"])))
    cv.save(); cv.clipPath(sil, skia.ClipOp.kIntersect, True)
    cv.drawPath(sil, boya(renk(karistir(P["kagit"], "#FFFFFF", 0.4))))
    cv.save(); cv.translate(3.0 * u, 2.0 * u)  # baskı kayması: spot renk mürekkebe tam oturmaz
    for yol, hx in spotlar:
        cv.drawPath(yol, boya(renk(hx, 0.92), blend=skia.BlendMode.kMultiply))
    cv.restore()
    cv.drawPath(noktalar, boya(renk(P["murekkep"], 0.88), blend=skia.BlendMode.kMultiply))
    for yol, hx in ustler:
        cv.drawPath(yol, boya(renk(hx)))
    cv.restore()
    cv.save(); cv.clipPath(kenar, skia.ClipOp.kIntersect, True)
    cv.drawPaint(doku_boyasi(0.8, tohum % 5))
    cv.restore()
    return rec.finishRecordingAsPicture()


def gorsel_resim(yol: str, hedef_w: float, P: dict, u: float, tohum: int, renkli: bool = False):
    """Herhangi bir PNG/JPG → kesik yarım ton parça. Saydamlık varsa siluet odur, yoksa makas kesikli dikdörtgen.
    renkli=True: yarım tona çevirmeden kendi renkleriyle kesilir (kitap kapağı, yemek ve ürün fotoğrafı gibi okunması/rengiyle satması gerekenler)."""
    img = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(yol))
    k = hedef_w / img.width()
    w, h = img.width() * k, img.height() * k
    arr = img.toarray()
    alfa = arr[..., 3] if arr.shape[2] == 4 else np.full(arr.shape[:2], 255, np.uint8)
    if alfa.min() > 250:
        sil = skia.Path(); sil.addRect(skia.Rect(0, 0, w, h))
    else:  # saydam alanın sınırını makas yolu için kaba ızgarada izle: alfa > 128 olan hücrelerin birleşimi
        sil = skia.Path()
        adim = max(2, int(6 / k))
        for y in range(0, alfa.shape[0], adim):
            satir = alfa[y, ::adim] > 128
            x = 0
            while x < len(satir):
                if satir[x]:
                    x0 = x
                    while x < len(satir) and satir[x]:
                        x += 1
                    sil.addRect(skia.Rect(x0 * adim * k, y * k, x * adim * k, (y + adim) * k))
                x += 1
        sil = skia.Op(sil, sil, skia.PathOp.kUnion_PathOp)

    ornekleme = skia.SamplingOptions(skia.CubicResampler.Mitchell()) if renkli else skia.SamplingOptions(skia.FilterMode.kLinear)
    if renkli:
        rnd = random.Random(tohum)
        kenar = makas(sil, 11 * u, 28 * u, rnd)
        m = 50 * u
        rec = skia.PictureRecorder()
        cv = rec.beginRecording(skia.Rect(-m, -m, w + m, h + m))
        golge(cv, kenar, u)
        cv.drawPath(kenar, boya(renk(P["kagit"])))
        cv.drawImageRect(img, skia.Rect(0, 0, w, h), ornekleme, skia.Paint(AntiAlias=True))  # kenarı kendi saydamlığı (basamaksız)
        cv.save(); cv.clipPath(kenar, skia.ClipOp.kIntersect, True)
        cv.drawPaint(doku_boyasi(0.5, tohum % 5))
        cv.restore()
        return rec.finishRecordingAsPicture(), w, h

    def gri_ciz(cv):
        p = skia.Paint(AntiAlias=True)
        p.setColorFilter(skia.ColorFilters.Matrix([0.3, 0.59, 0.11, 0, 0] * 3 + [0, 0, 0, 1, 0]))
        cv.drawImageRect(img, skia.Rect(0, 0, w, h), ornekleme, p)
    return kesik_resim(w, h, sil, gri_ciz, [], P, u, tohum), w, h


# ---------- kesik harfler ----------
YAZI_TIPLERI = ["fraunces", "archivo", "anton", "abril", "fraunces-italik", "courier", "inter"]
RENK_CIFTLERI = [("kagit", "murekkep"), ("murekkep", "kagit"), ("vurgu", "kagit"), ("ikinci", "murekkep"),
                 ("kagit", "vurgu"), ("marka", "kagit"), ("murekkep", "ikinci")]
_TF = {}


def tf(ad: str) -> skia.Typeface:
    if ad not in _TF:
        _TF[ad] = skia.Typeface.MakeFromFile(fontlar.bul(ad))
    return _TF[ad]


def font_boyu(ad: str, buyuk_harf: float) -> skia.Font:
    """Büyük harf yüksekliği `buyuk_harf` piksel olacak boyda font (yazı tipleri arasında eşit görünür)."""
    f = skia.Font(tf(ad), 100)
    cap = f.getMetrics().fCapHeight or 70
    f = skia.Font(tf(ad), 100 * buyuk_harf / cap)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


def harf_cipi(ch: str, boy: float, P: dict, u: float, rnd: random.Random, cift, yazi_tipi: str):
    """Dergiden kesilmiş tek harf: düz kesimli (bazen bir kenarı yırtık) renkli kâğıt + harf."""
    zem, on = cift
    cap = boy * rnd.uniform(0.5, 0.62)
    f = font_boyu(yazi_tipi, cap)
    if f.unicharToGlyph(ord(ch)) == 0:
        yazi_tipi = "inter"; f = font_boyu("inter", cap)
    adv = f.measureText(ch)
    h = boy * rnd.uniform(0.92, 1.08)
    w = adv + boy * rnd.uniform(0.16, 0.26)
    yirtik = rnd.choice(["", "", "", "b", "t"])
    pic, dis = kagit(w, h, P[zem], u, rnd.randrange(1 << 30), yirtik=yirtik, genlik=3.5, golgeli=False, doku_gucu=0.7,
                     lif=karistir(P[zem], "#FFFFFF", 0.75), kes=3.0)
    m = 30 * u
    rec = skia.PictureRecorder()
    cv = rec.beginRecording(skia.Rect(-m, -m, w + m, h + m))
    golge(cv, dis, u, 0.9, 3, 5, 4)
    cv.drawPicture(pic)
    taban = h / 2 + cap / 2 + rnd.uniform(-0.04, 0.04) * h
    cv.drawString(ch, (w - adv) / 2, taban, f, boya(renk(P[on])))
    return rec.finishRecordingAsPicture(), w, h


def kesik_yazi(metin: str, boy: float, max_w: float, P: dict, u: float, tohum: int, satir_araligi: float = 1.08,
               ciftler=None, yazi_tipleri=None):
    """Fidye notu tarzı yazı. Dönüş: harf listesi [(pic, x, y, w, h, aci)] — (x,y) çipin merkezi, yazının
    merkezine göre. Sığmazsa kelime aralarından satır kırılır; yine sığmazsa küçülür."""
    rnd = random.Random(tohum)
    ciftler = ciftler or RENK_CIFTLERI
    yazi_tipleri = yazi_tipleri or YAZI_TIPLERI

    def kur(boy):
        cipler, onceki = [], None
        for kel in metin.split():
            kc = []
            for ch in kel:
                c = rnd.choice([x for x in ciftler if x != onceki]); onceki = c
                pic, w, h = harf_cipi(ch, boy, P, u, rnd, c, rnd.choice(yazi_tipleri))
                kc.append((pic, w, h, rnd.uniform(-7, 7), rnd.uniform(-0.07, 0.07) * boy))
            cipler.append(kc)
        return cipler

    for _ in range(4):
        kelimeler = kur(boy)
        ust = -6 * u  # çipler biraz üst üste biner
        gen = [sum(c[1] for c in k) + ust * (len(k) - 1) for k in kelimeler]
        bosluk = boy * 0.4
        satirlar, cur = [], []
        for i, g in enumerate(gen):
            if cur and sum(gen[j] for j in cur) + bosluk * len(cur) + g > max_w:
                satirlar.append(cur); cur = []
            cur.append(i)
        satirlar.append(cur)
        en_genis = max(sum(gen[j] for j in s) + bosluk * (len(s) - 1) for s in satirlar)
        if en_genis <= max_w:
            break
        boy *= max_w / en_genis * 0.97
    out = []
    toplam_h = boy * satir_araligi * len(satirlar)
    for si, s in enumerate(satirlar):
        sw = sum(gen[j] for j in s) + bosluk * (len(s) - 1)
        x = -sw / 2
        y = -toplam_h / 2 + boy * satir_araligi * (si + 0.5)
        for j in s:
            for pic, w, h, aci, dy in kelimeler[j]:
                out.append((pic, x + w / 2, y + dy, w, h, aci))
                x += w + ust
            x += bosluk - ust
    return out


# ---------- bant, kalem ----------
def bant(w: float, h: float, u: float, tohum: int, hx: str = "#EFE6CF"):
    """Yarı saydam kâğıt bant: iki ucu tırtıklı (dişli) koparılmış."""
    rnd = random.Random(tohum)
    pts = [(0, 0)]
    n = max(4, int(h / (6 * u)))
    pts = [(rnd.uniform(-2, 2) * u + (3 * u if i % 2 else 0), h * i / n) for i in range(n + 1)]
    sag = [(w + rnd.uniform(-2, 2) * u - (3 * u if i % 2 else 0), h * (n - i) / n) for i in range(n + 1)]
    yol = cokgen(pts + sag)
    rec = skia.PictureRecorder()
    m = 20 * u
    cv = rec.beginRecording(skia.Rect(-m, -m, w + m, h + m))
    cv.save(); cv.translate(1.5 * u, 2.5 * u)
    cv.drawPath(yol, boya(renk("#000000", 0.10), blur=2 * u))
    cv.restore()
    cv.drawPath(yol, boya(renk(hx, 0.78)))
    cv.save(); cv.clipPath(yol, skia.ClipOp.kIntersect, True)
    cv.drawPaint(doku_boyasi(0.6, tohum % 5))
    cv.restore()
    return rec.finishRecordingAsPicture()


def kalem_yolu(noktalar) -> skia.Path:
    """Noktalardan geçen yumuşak (Catmull-Rom → kübik) keçeli kalem yolu."""
    p = skia.Path()
    p.moveTo(*noktalar[0])
    for i in range(len(noktalar) - 1):
        p0 = noktalar[max(0, i - 1)]; p1 = noktalar[i]; p2 = noktalar[i + 1]; p3 = noktalar[min(len(noktalar) - 1, i + 2)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        p.cubicTo(*c1, *c2, *p2)
    return p


def kalem_ciz(cv, yol: skia.Path, ilerleme: float, hx: str, kalinlik: float, a: float = 0.9):
    """Yolun ilk `ilerleme` kısmını keçeli kalemle çizer (çarpma karışımı: alttaki baskı görünür)."""
    if ilerleme <= 0:
        return
    pm = skia.PathMeasure(yol, False, 1)
    L = pm.getLength()
    p = boya(renk(hx, a), stroke=kalinlik, blend=skia.BlendMode.kMultiply)
    if ilerleme < 1:
        p.setPathEffect(skia.DashPathEffect.Make([L * ilerleme, L + 1], 0))
    cv.drawPath(yol, p)


def el_cemberi(cx: float, cy: float, rx: float, ry: float, rnd: random.Random, tur: float = 1.18) -> skia.Path:
    """Elle çizilmiş, ucu taşan oval (keçeli kalem halkası)."""
    n = 48
    a0 = rnd.uniform(-2.6, -2.0)
    d = Dalga(rnd, [(3.0, 0.06), (1.2, 0.025)])
    pts = []
    for i in range(int(n * tur) + 1):
        a = a0 + 2 * math.pi * i / n
        k = 1 + d(a) + 0.05 * i / n
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return kalem_yolu(pts)
