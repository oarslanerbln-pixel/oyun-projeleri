"""Neon logo açılışı: marka.json + birkaç kelime → mekân duvarındaki neon tabelanın yanışı gibi kısa logo animasyonu.

    python3 platform/sablonlar/neon/neon.py denetle senaryo.json
    python3 platform/sablonlar/neon/neon.py kare    senaryo.json --an 1.5 3.2 7.5 [--format 9:16]
    python3 platform/sablonlar/neon/neon.py uret    senaryo.json [--format 9:16 | 1:1 | 4:5 | 16:9] [--olcek 0.5]

Akış (8 sn'ye göre; süre 6–10 sn arasında orantılı uzar): karanlık duvarda iki spot yanar → altın halka kıvılcımla
kendini çizer → halkanın içinde monogram belirir → logo yazısı harf harf titreyerek neon gibi yanar → altındaki
çizgi kalpten iki yana açılır, kalp bir kez atar → alt satır ve çağrı. Son kare logonun tam yandığı hâlde durur.

Işıma 8 bitte dairesel basamak yapmasın diye her kareye ince, her karede değişen tane eklenir (kalite kapısının
banding ölçüsü bunu denetler). Müzik sentezlenir: sıcak ped, halkada yükselen ses, harflerde tık, kalpte çan, yanışta
gümbürtü; seslendirme yok. Renk ve yazı tipi marka.json'dan.
"""
import argparse, json, os, subprocess, sys
import numpy as np

BURADA = os.path.dirname(os.path.abspath(__file__))
SABLONLAR = os.path.dirname(BURADA)
PLATFORM = os.path.dirname(SABLONLAR)
sys.path.insert(0, os.path.join(SABLONLAR, 'stil'))
sys.path.insert(0, os.path.join(SABLONLAR, 'bumper'))
sys.path.insert(0, os.path.join(PLATFORM, 'ortak'))
import motor  # noqa: E402
import bumper  # noqa: E402  (marka yükleme, marka yazı tipi, ped/çan sentezi)
import marka as marka_mod  # noqa: E402
import sfx as fx  # noqa: E402

FPS, SR = motor.FPS, motor.SR
clamp, lerp, prog, out_cubic = motor.clamp, motor.lerp, motor.prog, motor.out_cubic
SURE = (6.0, 10.0)
SINIR = {'logo': 18, 'monogram': 3, 'ust': 34, 'cagri': 34}
ALANLAR = {'logo', 'monogram', 'ust', 'cagri', 'kalp'}
GUVENLI = {'9x16': (0.13, 0.22), '4x5': (0.08, 0.10), '1x1': (0.06, 0.08), '16x9': (0.08, 0.10)}
# olay anları (8 sn'lik akışta); başka sürede orantılanır
AN = {'spot': 0.3, 'halka': 0.8, 'monogram': 2.0, 'logo': 2.6, 'kalp': 3.9, 'ust': 4.6, 'cagri': 5.4}


def _yol(senaryo_yolu, yol):
    return bumper._yol(senaryo_yolu, yol)


def yukle(yol):
    s, m, bulgular = bumper.yukle(yol)
    return s, m, bulgular


def denetle(yol):
    s, m, bulgular = yukle(yol)
    hata = [f'marka: {b.yer}: {b.mesaj}' for b in bulgular if b.seviye == marka_mod.HATA]
    uyari = [f'marka: {b.yer}: {b.mesaj}' for b in bulgular if b.seviye != marka_mod.HATA]
    n = s.get('neon', {})
    for k in n:
        if k not in ALANLAR: hata.append(f'neon.{k}: tanımsız alan')
    logo = n.get('logo') or m.logo_metin or m.ad
    if not logo: hata.append('neon.logo: logo yazısı yok (marka.json logo.metin ya da ad)')
    for k, v in (('logo', logo), *((k, n.get(k, '')) for k in ('monogram', 'ust', 'cagri'))):
        if not isinstance(v, str): hata.append(f'neon.{k}: metin olmalı')
        elif len(v) > SINIR[k]: hata.append(f'neon.{k}: "{v}" {len(v)} karakter, en çok {SINIR[k]}')
    sure = s.get('sure', 8)
    if not isinstance(sure, (int, float)) or not SURE[0] <= sure <= SURE[1]:
        hata.append(f'sure: {sure}; {SURE[0]:g}–{SURE[1]:g} sn olmalı')
    return hata, uyari


def _argb(h, a=1.0):
    return (int(clamp(a) * 255) << 24) | int(h.lstrip('#'), 16)


def _karistir(a, b, p):
    ca = [int(a.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(int(lerp(x, y, p)) for x, y in zip(ca, cb))


class Gorunum:
    def __init__(self, yol):
        s, m, _ = yukle(yol)
        self.s, self.m = s, m
        n = s.get('neon', {})
        r = m.renk
        bul = lambda *adlar: next(r[a] for a in adlar if a in r)
        self.duvar = bul('ana', 'zemin')
        self.neon = bul('isik.sicak', 'vurgu') if 'isik.sicak' in r else bul('vurgu', 'logo')
        self.cekirdek = _karistir(self.neon, '#FFFFFF', 0.72)   # tüpün beyaza yakın içi
        self.metal = _karistir(bul('vurgu', 'logo'), self.duvar, 0.25)  # monogram: ışımayan pirinç
        self.yazi = bul('ana-ustu', 'metin')
        self.logo = n.get('logo') or m.logo_metin or m.ad
        self.monogram = n.get('monogram', '')
        self.ust = n.get('ust', '')
        self.cagri = n.get('cagri', '')
        self.kalp = n.get('kalp', True)
        self.sure = float(s.get('sure', 8))
        k = self.sure / 8.0
        self.an = {a: t * k for a, t in AN.items()}
        self.buyuk = motor.tr_buyuk if s.get('dil', 'tr') == 'tr' else str.upper
        b, g = m.yazi.get('baslik'), m.yazi.get('govde')
        self.tf_baslik = bumper.marka_yazi_tipi(b.aile, b.agirlik) if b else motor.yazi_tipi(800)
        self.tf_govde = bumper.marka_yazi_tipi(g.aile, 600) if g else motor.yazi_tipi(600)
        # harflerin yanma sırası ve titreşimi: her harf için sabit (tohumlu) bir yanma anı
        rng = np.random.default_rng(11)
        harfler = [i for i, c in enumerate(self.logo) if c != ' ']
        sira = rng.permutation(len(harfler))
        self.harf_an = {h: 0.06 * j + rng.uniform(0, 0.05) for h, j in zip(harfler, sira)}
        self._zemin = {}


def _font(tf, boy):
    import skia
    f = skia.Font(tf, boy); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def _yerlesim(W, H):
    u = min(W, H) / 1080
    ad = next((k for k, (w, h) in motor.BOYUTLAR.items() if abs(w / h - W / H) < 0.01), '9x16')
    ust, alt = GUVENLI.get(ad, (0.08, 0.10))
    y0, y1 = ust * H, (1 - alt) * H
    # blok: logo (~150u) + çizgi + halka (çap 460u) + alt satır + çağrı ≈ 1000u; güvenli alanda ortalanır
    olcek = min(1.0, (y1 - y0) / (1060 * u))
    u2 = u * olcek
    cy = (y0 + y1) / 2
    return u2, cy


def _isik(cv, g, ciz, guc, u):
    """Neon tüpü: geniş ve dar iki ışıma, üstte beyaza yakın ince çekirdek. ciz(paint) yolu/çizgiyi çizer."""
    import skia
    if guc <= 0:
        return
    for gen, sig, a in ((18, 34, 0.42), (8, 9, 0.85)):
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=gen * u, Color=_argb(g.neon, a * guc),
                       StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join,
                       MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, sig * u))
        ciz(p)
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.6 * u,
                   Color=_argb(_karistir(g.duvar, g.cekirdek, clamp(0.35 + 0.65 * guc)), clamp(guc * 1.4)),
                   StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    ciz(p)


def _zemin(g, W, H):
    """Duvar + iki spot konisi (bir kez çizilir, titreşimli)."""
    import skia
    k = (W, H)
    if k not in g._zemin:
        surf = skia.Surface(W, H)
        with surf as cv:
            cv.clear(_argb(g.duvar))
            for x in (0.24 * W, 0.76 * W):
                # tavandaki spotun duvara düşen yumuşak ışığı: dikey uzatılmış radyal degrade
                cv.save(); cv.translate(x, 0); cv.scale(1.0, 2.6)
                sh = skia.GradientShader.MakeRadial((0, 0), 0.26 * W, [_argb(g.neon, 0.20), _argb(g.neon, 0.0)])
                cv.drawCircle(0, 0, 0.26 * W, skia.Paint(Shader=sh, Dither=True))
                cv.restore()
                cv.drawCircle(x, 14, 9 * min(W, H) / 1080, skia.Paint(AntiAlias=True, Color=_argb(g.cekirdek)))
        g._zemin[k] = surf.makeImageSnapshot()
    return g._zemin[k]


def _kalp_yolu(cx, cy, r):
    import skia
    h = skia.Path()
    h.moveTo(cx, cy + r * 0.95)
    h.cubicTo(cx - r * 1.5, cy - r * 0.05, cx - r * 0.95, cy - r * 1.25, cx, cy - r * 0.45)
    h.cubicTo(cx + r * 0.95, cy - r * 1.25, cx + r * 1.5, cy - r * 0.05, cx, cy + r * 0.95)
    return h


def kare(cv, t, W, H, g):
    import skia
    a = g.an
    u, cy = _yerlesim(W, H)
    cx = W / 2
    # karanlıktan açılış; spotlar yanar
    spot = out_cubic(prog(t, a['spot'], 1.1))
    cv.clear(_argb(g.duvar))
    p = skia.Paint(); p.setAlphaf(spot)
    cv.drawImage(_zemin(g, W, H), 0, 0, skia.SamplingOptions(), p)
    # kamera: çok yavaş yaklaşma
    z = lerp(1.0, 1.035, out_cubic(clamp(t / g.sure)))
    cv.save(); cv.translate(cx, cy); cv.scale(z, z); cv.translate(-cx, -cy)
    nefes = 0.94 + 0.06 * np.sin(t * 2.1)
    # yerleşim (blok merkezi cy): logo üstte, halka ortada, yazılar altta
    R = 250 * u
    hy = cy + 60 * u                     # halka merkezi
    ly = hy - R - 160 * u                # logo taban çizgisi
    cizgi_y = ly + 70 * u
    # halkanın duvara vurduğu sıcak ışık (halka yandıkça)
    halka_p = clamp((t - a['halka']) / 1.8)
    tam = clamp((t - a['logo']) / 1.4)
    if halka_p > 0:
        sh = skia.GradientShader.MakeRadial((cx, hy), R * 2.1, [_argb(g.neon, 0.16 * halka_p * nefes), _argb(g.neon, 0.0)])
        cv.drawCircle(cx, hy, R * 2.1, skia.Paint(Shader=sh, Dither=True))
    # monogram: ışımayan pirinç harfler, aşağıdan süzülür
    mp = out_cubic(prog(t, a['monogram'], 1.0))
    if g.monogram and mp > 0:
        golge = skia.Paint(AntiAlias=True, Color=_argb('#000000', 0.5 * mp),
                           MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6 * u))
        boya = skia.Paint(AntiAlias=True, Color=_argb(g.metal, mp))
        ilk, kalan = g.monogram[0], g.monogram[1:]
        f1, f2 = _font(g.tf_baslik, 290 * u), _font(g.tf_baslik, 200 * u)
        w1, w2 = f1.measureText(ilk), f2.measureText(kalan)
        bindir = w1 * 0.42 if kalan else 0           # ikinci harf ilkinin ayağına biner
        x1 = cx - (w1 + w2 - bindir) / 2
        kay = (1 - mp) * 26 * u
        for f_, harf, x_, y_ in ((f1, ilk, x1, hy + 70 * u), (f2, kalan, x1 + w1 - bindir, hy + 95 * u)):
            if harf:
                cv.drawString(harf, x_, y_ + kay + 4 * u, f_, golge)
                cv.drawString(harf, x_, y_ + kay, f_, boya)
    # halka: tepeden saat yönünde kendini çizer, ucunda kıvılcım
    if halka_p > 0:
        ep = motor.in_out_cubic(halka_p)
        oval = skia.Rect(cx - R, hy - R, cx + R, hy + R)
        _isik(cv, g, lambda pp: cv.drawArc(oval, -90, 360 * ep, False, pp), nefes * (0.75 + 0.25 * tam), u)
        if ep < 1:
            aci = np.radians(-90 + 360 * ep)
            sx, sy = cx + R * np.cos(aci), hy + R * np.sin(aci)
            for r_, al in ((22, 0.35), (9, 0.8)):
                cv.drawCircle(sx, sy, r_ * u, skia.Paint(AntiAlias=True, Color=_argb(g.cekirdek, al),
                              MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, r_ * 0.6 * u)))
            cv.drawCircle(sx, sy, 4 * u, skia.Paint(AntiAlias=True, Color=_argb('#FFFFFF')))
    # logo: harf harf titreyerek yanar (neon tüp: harf dış çizgisi)
    f = _font(g.tf_baslik, 172 * u)
    gl = f.textToGlyphs(g.logo)
    xs = f.getXPos(gl)
    w = sum(f.getWidths(gl))
    if w > W - 140 * u:
        f = _font(g.tf_baslik, 172 * u * (W - 140 * u) / w)
        xs = f.getXPos(gl); w = sum(f.getWidths(gl))
    x0 = cx - w / 2
    lt = t - a['logo']
    for i, (gid, x) in enumerate(zip(gl, xs)):
        if i not in g.harf_an:
            continue
        h0 = g.harf_an[i]
        q = lt - h0
        if q < 0:
            guc = 0.0
        elif q < 0.28:  # titreşim: kısa yanıp sönmeler, sonra tam
            guc = (0.0, 0.9, 0.15, 1.0, 0.4, 1.0)[min(5, int(q / 0.05))]
        else:
            guc = 1.0
        yol = f.getPath(gid)
        yol.offset(x0 + x, ly)
        _isik(cv, g, lambda pp, yol=yol: cv.drawPath(yol, pp), guc * nefes, u * 0.75)
    # çizgi + kalp: kalpten iki yana açılır, kalp bir kez atar
    kp = prog(t, a['kalp'], 0.9)
    if g.kalp and kp > 0:
        e = out_cubic(kp)
        yarim = w / 2
        kr = 15 * u
        atis = 1 + 0.25 * np.sin(np.pi * clamp((t - a['kalp']) / 0.35)) if t > a['kalp'] else 1
        bos = kr * 1.9
        uz = (yarim - bos) * e

        def cizgiler(pp):
            cv.drawLine(cx - bos - uz, cizgi_y, cx - bos, cizgi_y, pp)
            cv.drawLine(cx + bos, cizgi_y, cx + bos + uz, cizgi_y, pp)
        _isik(cv, g, cizgiler, nefes * 0.8, u * 0.7)
        yol = _kalp_yolu(cx, cizgi_y, kr * atis)
        _isik(cv, g, lambda pp: cv.drawPath(yol, pp), nefes * min(1.0, kp * 3), u * 0.7)
    # alt satır ve çağrı
    yy = hy + R + 120 * u
    for anahtar, metin, boy, renk, ara in (('ust', g.ust, 30, g.neon, 0.26), ('cagri', g.cagri, 34, g.yazi, 0.04)):
        if not metin:
            continue
        q = out_cubic(prog(t, a[anahtar], 0.8))
        if q > 0:
            s = g.buyuk(metin) if anahtar == 'ust' else metin
            ff = _font(g.tf_govde, boy * u)
            ws = ff.measureText(s) + ara * boy * u * (len(s) - 1)
            if ws > W - 160 * u:
                ff = _font(g.tf_govde, boy * u * (W - 160 * u) / ws); ws = W - 160 * u
            xx = cx - ws / 2
            pp = skia.Paint(AntiAlias=True, Color=_argb(renk, q))
            yb = yy + (1 - q) * 18 * u
            if ara:
                for ch in s:
                    cv.drawString(ch, xx, yb, ff, pp); xx += ff.measureText(ch) + ara * boy * u
            else:
                cv.drawString(s, xx, yb, ff, pp)
        yy += 90 * u
    cv.restore()
    # son anda hafif kararma yok: son kare logonun yandığı hâlde kalır (Reel kapağı olur)
    if t < 0.35:
        cv.drawPaint(skia.Paint(Color=_argb('#000000', 1 - t / 0.35)))


def _tane(dizi, rng, guc=3.5):
    """Her karede değişen ince tane (üçgen dağılım, ±guc kod değeri): ışımadaki 8 bit basamaklarını kırar.
    Daha zayıfı (±2) H.264 kodlamasında koyu tonlarda düzleşir ve basamaklar geri gelir."""
    n = np.rint((rng.random(dizi.shape[:2]) + rng.random(dizi.shape[:2]) - 1.0) * guc).astype(np.int16)
    out = dizi.astype(np.int16)
    out[:, :, :3] += n[:, :, None]
    return np.clip(out, 0, 255).astype(np.uint8)


def _kare_dizi(g, t, W, H, rng):
    import skia
    surf = skia.Surface(W, H)
    with surf as cv:
        kare(cv, t, W, H, g)
    img = surf.makeImageSnapshot()
    return _tane(img.toarray(), rng), img.colorType() == skia.kBGRA_8888_ColorType


def kare_kaydet(g, t, W, H, yol):
    from PIL import Image
    a, bgra = _kare_dizi(g, t, W, H, np.random.default_rng(int(t * 1000)))
    if bgra:
        a = a[:, :, [2, 1, 0, 3]]
    Image.fromarray(a[:, :, :3]).save(yol)


# ---------- ses ----------
def muzik(g):
    n = int(SR * g.sure)
    buf = np.zeros((n, 2))
    m = motor.mtof
    a = g.an
    cal = bumper._cal
    rng = np.random.default_rng(5)
    # sıcak ped (Dmaj9), yanışta bir oktav açılır
    cal(buf, 0.0, bumper._ped([m(50), m(57), m(64), m(66), m(69)], a['logo'] + 0.3, 1.2), 0.30)
    # halka: logo yanışına doğru kabaran yumuşak akor + ince parıltı. Testere dalgalı riser burada vızıltı gibi
    # duyuluyordu (Atilla, 2026-10-19), yalnız sinüs kullanılır
    d = a['logo'] - a['halka']
    tt = np.arange(int(d * SR)) / SR
    kabar = sum(np.sin(2 * np.pi * m(n) * tt + i) for i, n in enumerate((62, 69, 74, 78))) / 4 * (tt / d) ** 2
    cal(buf, a['halka'], kabar, 0.14)
    cal(buf, a['halka'] + d * 0.4, fx.parilti(rng, d * 0.6, yogunluk=10) * np.linspace(0, 1, int(d * 0.6 * SR)), 0.04)
    cal(buf, a['monogram'], bumper._tini(m(74), 1.6, 0.45), 0.16)
    # harfler: her yanışta yumuşak tık
    for i, h0 in sorted(g.harf_an.items(), key=lambda x: x[1]):
        cal(buf, a['logo'] + h0, fx.tik(rng, 2600 + 90 * (i % 7), 0.014), 0.06, -0.5 + i / max(1, len(g.logo)))
    # tam yanış: alçak gümbürtü + açılan akor + parıltı
    L = a['logo'] + max(g.harf_an.values()) + 0.28
    cal(buf, L, fx.boom(rng, 1.1), 0.55)
    cal(buf, L, bumper._ped([m(50), m(57), m(62), m(66), m(69), m(76)], g.sure - L, 0.05), 0.36)
    cal(buf, L, fx.parilti(rng, 1.6), 0.06)
    # kalp: çan arpeji
    for i, nota in enumerate([78, 81, 86]):
        cal(buf, a['kalp'] + 0.1 + i * 0.12, bumper._tini(m(nota), 1.8, 0.5), 0.14, -0.3 + 0.3 * i)
    cal(buf, a['ust'], bumper._tini(m(81), 1.4, 0.4), 0.10)
    cal(buf, a['cagri'], bumper._tini(m(86), 1.4, 0.4), 0.08)
    f = int(0.5 * SR)
    buf[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
    return buf


# ---------- üretim ----------
def calistir(yol, cikti, boyutlar=('9x16',), olcek=1.0):
    import soundfile as sf
    g = Gorunum(yol)
    ad = g.s.get('kimlik', 'neon')
    is_ = os.path.join(cikti, 'is'); os.makedirs(is_, exist_ok=True)
    x = muzik(g)
    sf.write(os.path.join(is_, 'ses.wav'), (x / max(1e-9, np.abs(x).max()) * 0.9).astype(np.float32), SR)
    ses = motor.ses_bitir(is_)
    ciktilar = []
    for b in boyutlar:
        W, H = motor.boyut(b, olcek)
        kare_kaydet(g, g.sure - 0.05, W, H, os.path.join(cikti, f'{ad}-kapak.png'))
        hedef = os.path.join(cikti, f'{ad}-{b}.mp4')
        rng = np.random.default_rng(3)
        ilk, bgra = _kare_dizi(g, 0.0, W, H, rng)
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra' if bgra else 'rgba',
                               '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', ses, '-c:v', 'libx264', '-preset', 'medium',
                               '-crf', '17', '-tune', 'grain', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                               '-t', f'{g.sure:.3f}', '-movflags', '+faststart', hedef], stdin=subprocess.PIPE)
        for i in range(int(round(FPS * g.sure))):
            dizi, _ = _kare_dizi(g, i / FPS, W, H, rng)
            ff.stdin.write(dizi.tobytes())
        ff.stdin.close()
        if ff.wait():
            raise RuntimeError(f'ffmpeg kodlaması başarısız: {hedef}')
        motor.kalite_kapisi(hedef)
        ciktilar.append(hedef)
    for f in ('ses.wav', 'ses_14.wav'):
        os.remove(os.path.join(is_, f))
    return ciktilar


def main(argv=None):
    sys.path.insert(0, os.path.join(SABLONLAR, 'stil'))
    from stil import formatlar
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    alt = ap.add_subparsers(dest='komut', required=True)
    for ad in ('denetle', 'kare', 'uret'):
        p = alt.add_parser(ad)
        p.add_argument('senaryo'); p.add_argument('-o', '--cikti')
        if ad == 'kare':
            p.add_argument('--an', type=float, nargs='+', required=True)
            p.add_argument('--format', default='9x16', type=lambda x: formatlar(x)[0])
        if ad == 'uret':
            p.add_argument('--format', nargs='+', help='9:16, 16:9, 1:1, 4:5 ya da ikisi (varsayılan: senaryodaki "format", yoksa 9:16)')
            p.add_argument('--olcek', type=float, default=1.0)
    a = ap.parse_args(argv)
    hata, uyari = denetle(a.senaryo)
    for h in uyari: print(f'UYARI: {h}', file=sys.stderr)
    for h in hata: print(f'HATA: {h}', file=sys.stderr)
    if hata: return 1
    with open(a.senaryo, encoding='utf-8') as f:
        s = json.load(f)
    if a.komut == 'denetle':
        print(f"tamam: {s.get('kimlik', '?')} · neon · {float(s.get('sure', 8)):g} sn"); return 0
    cikti = a.cikti or os.path.join(os.path.dirname(os.path.abspath(a.senaryo)), 'cikti')
    if a.komut == 'kare':
        g = Gorunum(a.senaryo)
        klasor = os.path.join(cikti, 'kareler'); os.makedirs(klasor, exist_ok=True)
        W, H = motor.boyut(a.format)
        for t in a.an:
            yol = os.path.join(klasor, f"{s.get('kimlik', 'neon')}-{a.format}-{t:05.2f}.png")
            kare_kaydet(g, t, W, H, yol); print(yol)
        return 0
    try:
        boyutlar = formatlar(a.format or s.get('format'))
    except ValueError as e:
        print(f'HATA: {e}', file=sys.stderr); return 1
    for yol in calistir(a.senaryo, cikti, boyutlar, a.olcek):
        print(yol)
    return 0


if __name__ == '__main__':
    sys.exit(main())
