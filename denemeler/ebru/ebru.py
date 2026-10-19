"""Ebru (su üstü kâğıt boyama) stil testi: matematiksel ebru ile 10 sn 9:16 reklam.

Yöntem: Jaffer & Lu, "Mathematical Marbling" (IEEE CG&A 2012). Her işlem (damla, iğne çekişi)
kapalı formda bir dönüşüm; her piksel için işlemler sondan başa TERS uygulanır ve pikselin
hangi damladan geldiği bulunur. Sonuç: vektör kadar keskin kenarlar, kare kare deterministik.
Kenar yumuşatma 2x2 süper örnekleme ile.

Uydurma marka: Desenhane (tek parça el yapımı ipek eşarp). İlke: kıtlık/tekillik, "Her desen bir kez olur."

Kullanım:
  python3 ebru.py kare ÇIKTI_KLASÖRÜ t1 t2 ... [--olcek 0.5]
  python3 ebru.py video ÇIKTI.mp4 [--olcek 1]
  python3 ebru.py kareler KLASÖR BAŞLANGIÇ ADIM   (4 süreç: 0..3 ve adım 4; sonra ffmpeg -framerate 30 -i %04d.png)
"""
import math, os, subprocess, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BURADA = os.path.dirname(os.path.abspath(__file__))
FPS, SURE = 30, 10.0
W, H = 1080, 1920
SS = 2  # süper örnekleme

# geleneksel ebru paleti
ZEMIN = (233, 223, 201)
RENK = {
    'lacivert': (31, 47, 92), 'kirmizi': (168, 50, 45), 'hardal': (214, 160, 62),
    'turkuaz': (52, 136, 134), 'kahve': (52, 40, 34), 'beyaz': (246, 241, 230), 'gul': (205, 120, 110),
}
ADLAR = list(RENK)
PALET = np.array([RENK[a] for a in ADLAR] + [ZEMIN], dtype=np.float32) / 255.0  # son indeks = zemin


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def out_cubic(p): p = clamp(p); return 1 - (1 - p) ** 3
def in_out(p): p = clamp(p); return p * p * (3 - 2 * p)


# ---------------------------------------------------------------- işlem listesi (zaman çizelgesi)
# koordinatlar yüksekliğe göre: x ∈ [0, 0.5625], y ∈ [0, 1]
AX = W / H


def islemler():
    rng = np.random.default_rng(11)
    ops = []
    # 1) battal: serpilen damlalar (büyükten küçüğe), 0.25 – 3.0 sn
    renkler = ['lacivert', 'hardal', 'kirmizi', 'turkuaz', 'beyaz', 'lacivert', 'kahve', 'hardal']
    n = 120
    for i in range(n):
        t0 = 0.25 + 2.6 * (i / n) ** 0.85
        r = 0.085 * (1 - 0.55 * i / n) * rng.uniform(0.8, 1.15)
        ops.append(dict(tur='damla', t0=t0, d=0.55, cx=rng.uniform(-0.04, AX + 0.04), cy=rng.uniform(-0.03, 1.03),
                        r=r, renk=ADLAR.index(renkler[i % len(renkler)])))
    # 2) halka damlalar: aynı merkeze üst üste damla -> iç içe halkalar (lale gövdeleri), 3.0 – 4.3 sn
    merkezler = [(0.17, 0.30), (0.40, 0.55), (0.16, 0.78)]
    sira = ['kirmizi', 'beyaz', 'lacivert', 'beyaz', 'kirmizi', 'hardal']
    for k, (cx, cy) in enumerate(merkezler):
        for j, rk in enumerate(sira):
            ops.append(dict(tur='damla', t0=3.0 + 0.09 * k + 0.2 * j, d=0.4, cx=cx, cy=cy,
                            r=0.040 - 0.004 * j, renk=ADLAR.index(rk)))
    # 3) gelgit: dikey iğne çekişleri, yön sırayla aşağı/yukarı, soldan sağa, 4.4 – 5.6 sn
    xs = np.arange(0.02, AX, 0.062)
    for i, x in enumerate(xs):
        ops.append(dict(tur='cizgi', t0=4.4 + 0.095 * i, d=0.5, bx=x, by=0.5, mx=0.0, my=1.0 if i % 2 else -1.0,
                        a=0.11, lam=0.018))
    # 4) tarak: yatay ince tarak, tüm dişler birlikte sağa, 5.8 – 6.7 sn
    for y in np.arange(0.015, 1.0, 0.045):
        ops.append(dict(tur='cizgi', t0=5.8, d=0.9, bx=0.0, by=y, mx=1.0, my=0.0, a=0.045, lam=0.010))
    # 5) bülbül yuvası: iki yumuşak girdap, 6.6 – 7.4 sn
    for cx, cy, yon in [(0.16, 0.36, 1), (0.40, 0.66, -1)]:
        ops.append(dict(tur='girdap', t0=6.6, d=0.8, cx=cx, cy=cy, aci=yon * 2.4, R=0.13))
    return ops


OPS = islemler()
DESEN_BITIS = max(o['t0'] + o['d'] for o in OPS)


def ilerleme(o, t):
    p = (t - o['t0']) / o['d']
    if p <= 0: return 0.0
    return out_cubic(p) if o['tur'] == 'damla' else in_out(p)


def desen(t, w, h, x0=0.0, y0=0.0, s=1.0):
    """Ebru desenini (w x h piksel, süper örneklemeli) üretir. Görüş: x = x0 + u*s, y = y0 + v*s (yüksekliğe göre)."""
    ww, hh = w * SS, h * SS
    v, u = np.mgrid[0:hh, 0:ww].astype(np.float32)
    X = (x0 + (u + 0.5) / hh * s).ravel(); Y = (y0 + (v + 0.5) / hh * s).ravel()
    renk = np.full(X.shape, len(ADLAR), dtype=np.int8)
    kenar = np.zeros(X.shape, dtype=np.float32)
    aktif = np.ones(X.shape, dtype=bool)
    # hafif su dalgalanması (sabit, düşük frekans): tüm işlemlerden "sonra" gelen küçük kayma
    dal = 0.0025 * min(1.0, t / 2.0)
    X = X + dal * np.sin(Y * 23.0 + 1.3) * np.cos(X * 17.0)
    Y = Y + dal * np.sin(X * 19.0 + 0.7)
    for o in reversed(OPS):
        p = ilerleme(o, t)
        if p <= 0: continue
        if o['tur'] == 'damla':
            r2 = (o['r'] * math.sqrt(p)) ** 2 if p < 1 else o['r'] ** 2
            dx = X - o['cx']; dy = Y - o['cy']; d2 = dx * dx + dy * dy
            ic = aktif & (d2 < r2)
            if ic.any():
                renk[ic] = o['renk']; kenar[ic] = np.sqrt(d2[ic] / r2); aktif &= ~ic
            f = np.sqrt(np.clip(1.0 - r2 / np.maximum(d2, 1e-12), 0.0, 1.0))
            X = o['cx'] + dx * f; Y = o['cy'] + dy * f
        elif o['tur'] == 'cizgi':
            nx, ny = -o['my'], o['mx']
            d = np.abs((X - o['bx']) * nx + (Y - o['by']) * ny)
            z = (o['a'] * p) * o['lam'] / (d + o['lam'])
            X = X - z * o['mx']; Y = Y - z * o['my']
        else:  # girdap: merkeze yakın daha çok döner (ters: eksi açı)
            dx = X - o['cx']; dy = Y - o['cy']; rr = np.sqrt(dx * dx + dy * dy)
            th = -o['aci'] * p * np.exp(-(rr / o['R']) ** 2)
            c, sn = np.cos(th), np.sin(th)
            X = o['cx'] + dx * c - dy * sn; Y = o['cy'] + dx * sn + dy * c
    rgb = PALET[renk]
    # damla kenarında boyanın topladığı ince koyu çizgi (gerçek ebrudaki kenar yığılması)
    halka = np.clip((kenar - 0.90) / 0.10, 0, 1) * (renk < len(ADLAR))
    rgb *= (1.0 - 0.10 * halka)[:, None]
    img = rgb.reshape(hh, ww, 3).reshape(h, SS, w, SS, 3).mean(axis=(1, 3))
    return img


_DOKU = {}
def kagit(w, h):
    """Sabit kâğıt/su dokusu: çok düşük genlikli gürültü (aynı zamanda dither görevi görür)."""
    if (w, h) not in _DOKU:
        rng = np.random.default_rng(3)
        kaba = Image.fromarray((rng.random((h // 6 + 1, w // 6 + 1)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        k = (np.asarray(kaba, dtype=np.float32) / 255 - 0.5) * 0.018
        ince = (rng.random((h, w)).astype(np.float32) - 0.5) * 0.02
        _DOKU[(w, h)] = (1.0 + k + ince)[:, :, None]
    return _DOKU[(w, h)]


def font(ad, px, agirlik):
    f = ImageFont.truetype(os.path.join(BURADA, 'fonts', ad), px)
    try: f.set_variation_by_axes([agirlik] if 'Cormorant' in ad else [14, agirlik])
    except Exception: pass
    return f


def ortali(d, metin, f, cx, y, renk, aralik=0):
    gen = sum(f.getlength(c) for c in metin) + aralik * (len(metin) - 1); x = cx - gen / 2
    for c in metin: d.text((x, y), c, font=f, fill=renk); x += f.getlength(c) + aralik


_SON = {}
def kare(t, olcek=1.0):
    w, h = int(W * olcek), int(H * olcek)
    # 7.4 sn'den sonra desen donar; "kâğıda alınmış baskı" geri çekilerek kartpostal gibi görünür
    T_GERI, D_GERI = 7.5, 1.1
    if t < T_GERI:
        img = desen(min(t, DESEN_BITIS), w, h)
        img = img * kagit(w, h)
        im = Image.fromarray(np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8))
    else:
        if w not in _SON:
            _SON[w] = np.clip(desen(DESEN_BITIS, w, h) * kagit(w, h) * 255 + 0.5, 0, 255).astype(np.uint8)
        p = in_out((t - T_GERI) / D_GERI)
        sc = 1.0 - 0.38 * p                      # baskı küçülür
        cy = h * (0.5 - 0.13 * p)                # ve yukarı kayar
        bw, bh = int(round(w * sc)), int(round(h * sc))
        zemin = np.array([241, 235, 222], np.float32) / 255
        tuval = (zemin[None, None, :] * kagit(w, h)) * 255
        im = Image.fromarray(np.clip(tuval + 0.5, 0, 255).astype(np.uint8))
        baski = Image.fromarray(_SON[w]).resize((bw, bh), Image.LANCZOS)
        x0, y0 = (w - bw) // 2, int(cy - bh / 2)
        # yumuşak gölge (düz renk üstünde, bulanık; bant yapmaz çünkü doku ile dither'lanır)
        if p > 0:
            g = Image.new('L', (w, h), 0); ImageDraw.Draw(g).rectangle((x0 + 6, y0 + 14, x0 + bw + 6, y0 + bh + 14), fill=int(70 * p))
            g = g.filter(ImageFilter.GaussianBlur(18 * olcek + 2))
            koyu = Image.new('RGB', (w, h), (90, 70, 50)); im = Image.composite(koyu, im, g)
        im.paste(baski, (x0, y0))
        # yazılar
        d = ImageDraw.Draw(im)
        a1 = clamp((t - 8.05) / 0.5); a2 = clamp((t - 8.55) / 0.5); a3 = clamp((t - 9.0) / 0.45)
        alt = y0 + bh
        def renk(a, r=(40, 32, 28)): return tuple(int(zemin[i] * 255 * (1 - a) + r[i] * a) for i in range(3))
        if a1 > 0:
            ortali(d, 'DESENHANE', font('CormorantGaramond.ttf', int(92 * olcek), 600), w / 2, alt + (40 + 12 * (1 - a1)) * olcek, renk(a1), aralik=int(14 * olcek))
        if a2 > 0:
            ortali(d, 'Her desen bir kez olur.', font('CormorantGaramond.ttf', int(56 * olcek), 500), w / 2, alt + (150 + 8 * (1 - a2)) * olcek, renk(a2, (120, 52, 42)))
        if a3 > 0:
            ortali(d, 'TEK PARÇA EL YAPIMI İPEK EŞARP', font('Inter.ttf', int(28 * olcek), 500), w / 2, alt + 232 * olcek, renk(a3, (70, 60, 52)), aralik=int(5 * olcek))
    # açılış: ilk 0.25 sn sudan beliren zemin
    if t < 0.4:
        a = t / 0.4; arr = np.asarray(im, np.float32) * (0.6 + 0.4 * a) + 255 * 0.0
        im = Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8))
    return im


def main():
    arg = sys.argv[1:]; kip, cikti = arg[0], arg[1]
    olcek = float(arg[arg.index('--olcek') + 1]) if '--olcek' in arg else 1.0
    if kip == 'kare':
        os.makedirs(cikti, exist_ok=True)
        ts, k = [], 2
        while k < len(arg):
            if arg[k].startswith('--'): k += 2; continue
            ts.append(float(arg[k])); k += 1
        for t in ts:
            b = time.time(); kare(t, olcek).save(os.path.join(cikti, f'ebru-{t:05.2f}.png')); print(f't={t} {time.time() - b:.1f} sn', flush=True)
        return
    if kip == 'kareler':  # paralel üretim: python3 ebru.py kareler KLASÖR BAŞLANGIÇ ADIM  (kare i = başlangıç, +adım, ...)
        os.makedirs(cikti, exist_ok=True); bas, adim = int(arg[2]), int(arg[3])
        for i in range(bas, int(FPS * SURE), adim):
            yol = os.path.join(cikti, f'{i:04d}.png')
            if not os.path.exists(yol): kare(i / FPS, olcek).convert('RGB').save(yol, compress_level=1)
        return
    w, h = int(W * olcek), int(H * olcek)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', cikti], stdin=subprocess.PIPE)
    n = int(FPS * SURE); bas = time.time()
    for i in range(n):
        ff.stdin.write(kare(i / FPS, olcek).convert('RGB').tobytes())
        if i % 30 == 0: print(f'kare {i}/{n} {time.time() - bas:.0f} sn', flush=True)
    ff.stdin.close(); ff.wait()


if __name__ == '__main__':
    main()
