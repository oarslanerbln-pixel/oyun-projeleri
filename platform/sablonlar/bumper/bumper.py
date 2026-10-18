"""Bumper / logo açılışı şablonu: marka.json + kısa senaryo → 6 sn YouTube bumper ya da 3 sn video imzası.

    python3 platform/sablonlar/bumper/bumper.py denetle senaryo.json
    python3 platform/sablonlar/bumper/bumper.py kare    senaryo.json --an 1.2 3.6 5.9 [--format 16:9]
    python3 platform/sablonlar/bumper/bumper.py render  senaryo.json [--format 9:16 | 16:9 | 1:1 | 4:5 | ikisi] [--olcek 0.25]
`stil.py <komut> senaryo.json --stil bumper` aynı komutları buraya iletir (`uret` = `render`; seslendirme yok).

Renk, yazı tipi, logo ve hareket eğrisi yalnız marka.json'dan gelir; marka değişince senaryoda yalnız
"marka" yolu ve birkaç kelime değişir. Görüntü ve müzik kodla üretilir, her kare t'nin saf fonksiyonudur.

Varyantlar:
    bumper (6 sn)  önerme kelime kelime → halka geçişi → logo → çağrı. YouTube atlanamaz bumper.
    imza   (3 sn)  doğrudan halka geçişi → logo. Her videonun başına/sonuna konan marka imzası.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np

BURADA = os.path.dirname(os.path.abspath(__file__))
SABLONLAR = os.path.dirname(BURADA)
PLATFORM = os.path.dirname(SABLONLAR)
DEPO = os.path.dirname(PLATFORM)
sys.path.insert(0, os.path.join(SABLONLAR, 'stil'))
sys.path.insert(0, os.path.join(PLATFORM, 'marka'))
import motor  # noqa: E402  (yazı tipi, kodlama, -14 LUFS, kolaylaştırma eğrileri ortak)
import marka as marka_mod  # noqa: E402

FPS, SR = motor.FPS, motor.SR
BPM = 120
VURUS = 60 / BPM  # 0,5 sn: kelimeler, halka ve logo bu ızgaraya oturur
VARYANTLAR = {'bumper': 6.0, 'imza': 3.0}
AZAMI_SURE = 6.0  # platform/medya/teslim.json → youtube-bumper.sure_siniri
# ekran yazısı: alan -> (azami karakter, azami kelime). Bumper'da az yazı: göz 6 sn'de ancak bu kadarını okur.
SINIRLAR = {'onerme': (32, 5), 'logo': (12, 2), 'alt': (18, 3), 'cagri': (26, 4)}
GUVENLI = {'9x16': (0.14, 0.20, 0.08), '4x5': (0.08, 0.10, 0.08)}  # üst, alt, yan (teslim.json "dikey")
FONT_ONBELLEK = motor.FONT_ONBELLEK
CIZGI_Y = 150  # önerme çizgisinin ortadan uzaklığı (tasarım birimi: kısa kenar 1080)


class SenaryoHatasi(ValueError):
    pass


# ---------- senaryo + marka ----------
def _yol(senaryo_yolu, yol):
    """Önce senaryonun klasörüne, sonra depo köküne göre (platform kuralı) çözer."""
    if os.path.isabs(yol):
        return yol
    for kok in (os.path.dirname(os.path.abspath(senaryo_yolu)), DEPO):
        aday = os.path.join(kok, yol)
        if os.path.exists(aday):
            return aday
    return os.path.join(os.path.dirname(os.path.abspath(senaryo_yolu)), yol)


def yukle(senaryo_yolu):
    """(senaryo, Marka | None, marka bulguları)"""
    with open(senaryo_yolu, encoding='utf-8') as f:
        s = json.load(f)
    if not s.get('marka'):
        return s, None, [marka_mod.Bulgu(marka_mod.HATA, 'marka', 'senaryoda "marka" yolu yok')]
    m, bulgular = marka_mod.yukle(_yol(senaryo_yolu, s['marka']))
    return s, m, bulgular


def alanlar(s, m):
    """Ekran yazıları. logo varsayılanı marka.json logo.metin, o da yoksa marka adı."""
    b = s.get('bumper', {})
    logo = b.get('logo') or (m.logo_metin if m else '') or (m.ad if m else '')
    return {'onerme': b.get('onerme', ''), 'logo': logo, 'alt': b.get('alt', ''), 'cagri': b.get('cagri', '')}


def varyant(s):
    return s.get('bumper', {}).get('varyant', 'bumper')


def denetle(senaryo_yolu):
    """(hatalar, uyarılar). HATA üretimi durdurur."""
    s, m, bulgular = yukle(senaryo_yolu)
    hata = [f'marka: {b.yer}: {b.mesaj}' for b in bulgular if b.seviye == marka_mod.HATA]
    uyari = [f'marka: {b.yer}: {b.mesaj}' for b in bulgular if b.seviye != marka_mod.HATA]
    v = varyant(s)
    if v not in VARYANTLAR:
        hata.append(f'bumper.varyant: "{v}" bilinmiyor (geçerli: {", ".join(VARYANTLAR)})')
        return hata, uyari
    sure = s.get('sure', VARYANTLAR[v])
    if sure != VARYANTLAR[v]:
        hata.append(f'sure: {v} varyantı {VARYANTLAR[v]:g} sn sabit (senaryo: {sure})')
    if sure > AZAMI_SURE:
        hata.append(f'sure: YouTube bumper en çok {AZAMI_SURE:g} sn')
    a = alanlar(s, m)
    if v == 'bumper' and not a['onerme'].strip():
        hata.append('bumper.onerme: bumper varyantında gerekli (yoksa "varyant": "imza")')
    if v == 'imza' and a['onerme']:
        uyari.append('bumper.onerme: imza varyantında gösterilmez')
    if not a['logo'].strip() and not (m and m.logo_dosya):
        hata.append('logo: bumper.logo, marka.json logo.metin ya da logo.dosya gerekli')
    for k, (azami, kelime) in SINIRLAR.items():
        x = a[k]
        if not isinstance(x, str):
            hata.append(f'{k}: metin olmalı'); continue
        if len(x) > azami:
            hata.append(f'{k}: "{x}" {len(x)} karakter, en çok {azami} (yerleşim taşar)')
        elif len(x.split()) > kelime:
            uyari.append(f'{k}: {len(x.split())} kelime; 6 sn içinde {kelime} kelimeden fazlası okunmaz')
    for k in s.get('bumper', {}):
        if k not in ('onerme', 'logo', 'alt', 'cagri', 'varyant'):
            hata.append(f'bumper.{k}: tanımsız alan (geçerli: onerme, logo, alt, cagri, varyant)')
    if m and m.logo_dosya and not m.logo_dosya.lower().endswith(('.png', '.svg')):
        hata.append(f'marka logo.dosya: {m.logo_dosya} desteklenmiyor (PNG ya da SVG)')
    return hata, uyari


# ---------- marka → görünüm ----------
def _argb(hexs):
    return 0xFF000000 | int(hexs.lstrip('#'), 16)


def _renk(m, *adlar):
    for ad in adlar:
        if ad in m.renk:
            return _argb(m.renk[ad])
    raise KeyError(adlar)


def bezier(egri):
    """CSS cubic-bezier(x1, y1, x2, y2) → p ↦ ilerleme (marka.json hareket.egri)."""
    x1, y1, x2, y2 = egri

    def f(p):
        if p <= 0: return 0.0
        if p >= 1: return 1.0
        u = p
        for _ in range(8):  # Newton: x(u) = p
            x = 3 * (1 - u) ** 2 * u * x1 + 3 * (1 - u) * u ** 2 * x2 + u ** 3 - p
            dx = 3 * (1 - u) ** 2 * x1 + 6 * (1 - u) * u * (x2 - x1) + 3 * u ** 2 * (1 - x2)
            if abs(dx) < 1e-6: break
            u = min(1.0, max(0.0, u - x / dx))
        return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u ** 2 * y2 + u ** 3
    return f


def marka_yazi_tipi(aile, agirlik):
    """Google Fonts'tan statik ağırlık (css2 API düz TTF verir) → önbellek; olmazsa Inter (motor.yazi_tipi)."""
    import skia
    ad = f"{aile.replace(' ', '')}-{agirlik}.ttf"
    yol = os.path.join(FONT_ONBELLEK, ad)
    if not os.path.exists(yol):
        try:
            import re, urllib.parse, urllib.request
            os.makedirs(FONT_ONBELLEK, exist_ok=True)
            url = f'https://fonts.googleapis.com/css2?family={urllib.parse.quote(aile)}:wght@{agirlik}'
            css = urllib.request.urlopen(url, timeout=20).read().decode()
            ttf = re.search(r'url\((https://[^)]+\.ttf)\)', css).group(1)
            urllib.request.urlretrieve(ttf, yol + '.indiriliyor')
            os.replace(yol + '.indiriliyor', yol)
        except Exception as e:
            print(f'UYARI {aile} {agirlik} indirilemedi ({e}); Inter kullanılıyor', file=sys.stderr)
            return motor.yazi_tipi(800 if agirlik >= 750 else 700)
    tf = skia.Typeface.MakeFromFile(yol)
    if tf is None or tf.unicharToGlyph(ord('İ')) == 0:  # Türkçe harfi olmayan yazı tipiyle bozuk görünmesin
        print(f'UYARI {aile}: Türkçe harfler yok; Inter kullanılıyor', file=sys.stderr)
        return motor.yazi_tipi(800 if agirlik >= 750 else 700)
    return tf


class Gorunum:
    """Marka kitinden çözülen roller. Renk rolleri eksikse yakın role düşer (yalnız zemin + metin zorunlu)."""

    def __init__(self, m, a, vary, senaryo_yolu=None):
        self.m, self.a, self.varyant = m, a, vary
        self.ana = _renk(m, 'ana', 'metin')
        self.ana_ustu = _renk(m, 'ana-ustu', 'zemin')
        self.vurgu = _renk(m, 'vurgu', 'ana', 'metin')
        self.zemin = _renk(m, 'zemin')
        self.metin = _renk(m, 'metin')
        self.isik = _renk(m, 'isik.sicak', 'vurgu', 'ana-ustu', 'zemin')
        self.egri = bezier(m.hareket.get('egri', [0.2, 0, 0, 1]))
        b, g = m.yazi.get('baslik'), m.yazi.get('govde')
        self.tf_baslik = marka_yazi_tipi(b.aile, b.agirlik) if b else motor.yazi_tipi(800)
        self.tf_govde = marka_yazi_tipi(g.aile, max(g.agirlik, 500)) if g else motor.yazi_tipi(700)
        self.logo_resim = _logo_resim(m, senaryo_yolu) if m.logo_dosya else None
        self.sure = VARYANTLAR[vary]
        self.buyuk = motor.tr_buyuk  # senaryo "dil" Türkçe değilse gorunum() str.upper'a çevirir (BERLIN, BERLİN değil)
        # olay anları (sn). imza, bumper'ın halka geçişinden başlar.
        k = 0.0 if vary == 'bumper' else -2.2
        self.z = dict(nokta=0.15, kelime=0.5, cizgi=0.45, halka=2.55 + k, logo=3.0 + k, alt=3.55 + k,
                      cagri=4.4 + k, son=self.sure)


def _logo_resim(m, senaryo_yolu):
    import skia
    kok = os.path.dirname(os.path.abspath(senaryo_yolu)) if senaryo_yolu else DEPO
    yol = m.logo_dosya if os.path.isabs(m.logo_dosya) else _yol(os.path.join(kok, '_'), m.logo_dosya)
    if yol.lower().endswith('.svg'):
        return ('svg', skia.SVGDOM.MakeFromStream(skia.Stream.MakeFromFile(yol)))
    return ('png', skia.Image.open(yol))


# ---------- çizim ----------
clamp, lerp, prog = motor.clamp, motor.lerp, motor.prog
out_cubic, out_back = motor.out_cubic, motor.out_back


def _alfa(renk, a):
    return (int(clamp(a) * 255) << 24) | (renk & 0xFFFFFF)


def _font(tf, boy):
    import skia
    f = skia.Font(tf, boy); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
    return f


def _sigdir(tf, s, boy, genislik, harf_araligi=0.0):
    """Metni genişliğe sığdıran yazı boyu (harf aralığı boya oranlı)."""
    f = _font(tf, boy)
    w = f.measureText(s) + harf_araligi * boy * max(0, len(s) - 1)
    return boy if w <= genislik else boy * genislik / w


def _harfler(cv, tf, s, boy, cx, y, renk, harf_araligi=0.0, harf_t=None):
    """Ortalanmış metin, harf harf. harf_t(i) -> (alfa, dy, olcek)."""
    import skia
    f = _font(tf, boy)
    ara = harf_araligi * boy
    xs = [f.measureText(s[:i]) + ara * i for i in range(len(s) + 1)]
    w = xs[-1] - ara if s else 0
    x0 = cx - w / 2
    p = skia.Paint(AntiAlias=True)
    for i, ch in enumerate(s):
        if ch == ' ': continue
        a, dy, olc = harf_t(i) if harf_t else (1.0, 0.0, 1.0)
        if a <= 0: continue
        p.setColor(_alfa(renk, a))
        gw = f.measureText(ch)
        cv.save()
        cv.translate(x0 + xs[i] + gw / 2, y + dy)
        cv.scale(olc, olc)
        cv.drawString(ch, -gw / 2, 0, f, p)
        cv.restore()
    return w


def _alan(W, H):
    u = min(W, H) / 1080
    ad = next((k for k, (w, h) in motor.BOYUTLAR.items() if abs(w / h - W / H) < 0.01), '16x9')
    ust, alt, yan = GUVENLI.get(ad, (0.06, 0.08, 0.08))
    return u, ust * H, H - alt * H, yan * W, W - yan * W


def kare(cv, t, W, H, g):
    """t anındaki kare (t'nin saf fonksiyonu)."""
    import skia
    z, a = g.z, g.a
    u, ust, alt, sol, sag = _alan(W, H)
    cx, cy = W / 2, (ust + alt) / 2
    genis = sag - sol
    hy = cy + (CIZGI_Y * u if g.varyant == 'bumper' else 0)  # halka merkezi: önermenin altındaki çizgi
    R = math.hypot(W / 2, max(hy, H - hy)) + 4

    # --- 1. bölüm: koyu marka zemini, sıcak ışık, önerme ---
    if t < z['logo'] + 0.2:
        cv.clear(g.ana)
        nefes = 0.5 + 0.5 * math.sin(t * 2.2)
        isik = skia.GradientShader.MakeRadial(
            (cx, cy - 0.05 * H), max(W, H) * (0.55 + 0.04 * nefes),
            [_alfa(g.isik, 0.20 + 0.06 * nefes), _alfa(g.isik, 0.0)])
        cv.drawPaint(skia.Paint(Shader=isik))
        if g.varyant == 'bumper':
            _onerme(cv, t, W, H, g, cx, cy, genis, u)
        _nokta_ve_halka(cv, t, g, cx, hy, u, R)

    # --- 2. bölüm: açık zemin, logo, çağrı ---
    if t >= z['halka'] + 0.25:
        p2 = out_cubic(prog(t, z['halka'] + 0.25, 0.42))
        if p2 >= 1:
            cv.clear(g.zemin)
        else:
            cv.drawCircle(cx, hy, R * p2, skia.Paint(AntiAlias=True, Color=g.zemin))
        if t >= z['logo'] - 0.05:
            cv.save()
            cv.clipPath(skia.Path().addCircle(cx, hy, R * p2))
            _logo(cv, t, W, H, g, cx, cy, genis, u, alt)
            cv.restore()
    # hafif vinyet: düz renk zemin "basılı" değil sıcak görünsün
    vin = skia.GradientShader.MakeRadial((cx, H / 2), max(W, H) * 0.75,
                                         [0x00000000, 0x00000000, 0x22000000 if t < z['halka'] + 0.4 else 0x0C000000], [0.0, 0.6, 1.0])
    cv.drawPaint(skia.Paint(Shader=vin))


def _nokta_ve_halka(cv, t, g, cx, hy, u, R):
    """Marka noktası: belirir, önermenin altında çizgiye açılır, sonra halka olup ekranı kaplar."""
    import skia
    z = g.z
    p = skia.Paint(AntiAlias=True, Color=g.vurgu)
    r0 = 14 * u
    if t < z['nokta']:
        return
    if g.varyant == 'bumper' and t < z['halka']:
        pop = out_back(prog(t, z['nokta'], 0.35), 2.4)
        ac = g.egri(prog(t, z['cizgi'] + 0.1, 1.6))       # nokta → çizgi
        kapan = g.egri(prog(t, z['halka'] - 0.45, 0.4))   # çizgi → nokta
        yari = lerp(0, 230 * u, ac * (1 - kapan))
        y = hy - CIZGI_Y * u * (1 - ac)  # nokta ortadan çizginin yerine iner, kapanırken orada kalır
        cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(cx - yari - r0 * pop, y - r0 * pop * (1 - 0.6 * ac * (1 - kapan)),
                                                     cx + yari + r0 * pop, y + r0 * pop * (1 - 0.6 * ac * (1 - kapan))),
                                           r0, r0), p)
        return
    if g.varyant == 'imza' and t < z['halka']:
        cv.drawCircle(cx, hy, r0 * out_back(prog(t, z['nokta'], 0.3), 2.4), p)
        return
    # halka: vurgu rengi daire ekranı kaplar, arkasından zemin rengi gelir (fincandaki halka gibi)
    q = g.egri(prog(t, z['halka'], 0.55))
    cv.drawCircle(cx, hy, lerp(r0, R, q), p)


def _onerme(cv, t, W, H, g, cx, cy, genis, u):
    z = g.z
    kelimeler = g.a['onerme'].split()
    if not kelimeler or t >= z['halka'] + 0.3:
        return
    boy = _sigdir(g.tf_baslik, max(kelimeler, key=len), 128 * u, genis * 0.92)
    # kelimeler satırlara: geniş ekranda tek satır sığarsa tek, yoksa iki satır
    tek = _sigdir(g.tf_baslik, ' '.join(kelimeler), 104 * u, genis * 0.92)
    if W > H and tek >= 80 * u:
        satirlar, boy = [kelimeler], tek
    else:
        yarim = math.ceil(len(kelimeler) / 2)
        satirlar = [kelimeler[:yarim], kelimeler[yarim:]] if len(kelimeler) > 2 else [[k] for k in kelimeler]
        boy = min(_sigdir(g.tf_baslik, ' '.join(s), 150 * u, genis * 0.92) for s in satirlar)
    satir_ara = boy * 1.12
    y0 = cy - satir_ara * (len(satirlar) - 1) / 2 + boy * 0.33 - 40 * u
    # her kelime bir vuruşta; hepsi 4 vuruşa sığar (kelime fazlaysa sıklaşır)
    adim = min(VURUS, 1.9 / max(1, len(kelimeler) - 1)) if len(kelimeler) > 1 else VURUS
    cikis = g.egri(prog(t, z['halka'] - 0.05, 0.3))
    f = _font(g.tf_baslik, boy)
    bosluk = f.measureText(' ')
    i = 0
    for si, satir in enumerate(satirlar):
        genislikler = [f.measureText(k) for k in satir]
        x = cx - (sum(genislikler) + bosluk * (len(satir) - 1)) / 2
        y = y0 + si * satir_ara
        for k, kw in zip(satir, genislikler):
            p = g.egri(prog(t, z['kelime'] + i * adim, 0.45))
            son = i == len(kelimeler) - 1
            renk = g.vurgu if son else g.ana_ustu
            _harfler(cv, g.tf_baslik, k, boy, x + kw / 2, y + (1 - p) * 46 * u - cikis * 30 * u, renk,
                     harf_t=lambda j, p=p: (p * (1 - cikis), 0.0, 1.0))
            x += kw + bosluk
            i += 1


def _logo(cv, t, W, H, g, cx, cy, genis, u, alt):
    import skia
    z, a = g.z, g.a
    itme = 1.0 + 0.035 * motor.in_out_cubic(prog(t, z['logo'], g.sure - z['logo']))  # yavaş kamera itmesi
    cv.save()
    cv.translate(cx, cy); cv.scale(itme, itme); cv.translate(-cx, -cy)
    # halka dalgaları: logo vuruşunda bir kez dışa yayılır
    for k in range(3):
        q = prog(t, z['logo'] + k * 0.12, 1.1)
        if 0 < q < 1:
            cv.drawCircle(cx, cy - 20 * u, lerp(120, 620, out_cubic(q)) * u,
                          skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=(6 - 1.5 * k) * u,
                                     Color=_alfa(g.vurgu, 0.55 * (1 - q))))
    logo_y = cy + (10 if a['alt'] else 40) * u
    if g.logo_resim:
        _logo_resim_ciz(cv, t, g, cx, logo_y - 80 * u, genis, u)
    else:
        s = g.buyuk(a['logo']) if a['logo'] == a['logo'].upper() else a['logo']
        boy = _sigdir(g.tf_baslik, s, 230 * u, genis * 0.86, 0.04)
        n = len(s)

        def harf(i):
            p = prog(t, z['logo'] + i * 0.055, 0.5)
            return (clamp(p * 3), (1 - out_back(p, 1.7)) * -90 * u, lerp(0.6, 1.0, out_back(p, 1.7)) if p < 1 else 1.0)
        aralik = lerp(0.18, 0.04, g.egri(prog(t, z['logo'], 0.9)))  # harfler yakınlaşarak oturur
        w = _harfler(cv, g.tf_baslik, s, boy, cx, logo_y, g.metin, aralik, harf)
        # vurgu çizgisi ortadan iki yana çizilir
        q = g.egri(prog(t, z['logo'] + 0.06 * n + 0.1, 0.5))
        if q > 0:
            yari = w * 0.5 * q
            cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect(cx - yari, logo_y + boy * 0.2, cx + yari, logo_y + boy * 0.2 + 12 * u),
                                               6 * u, 6 * u), skia.Paint(AntiAlias=True, Color=g.vurgu))
    if a['alt']:
        q = g.egri(prog(t, z['alt'], 0.6))
        boy = _sigdir(g.tf_govde, g.buyuk(a['alt']), 44 * u, genis * 0.7, 0.32)
        alt_y = logo_y + (200 if g.logo_resim else 130) * u  # görsel logo daha uzun: alt yazı altına iner
        _harfler(cv, g.tf_govde, g.buyuk(a['alt']), boy, cx, alt_y + (1 - q) * 16 * u,
                 g.metin, lerp(0.6, 0.32, q), lambda i: (q * 0.85, 0.0, 1.0))
    cv.restore()
    if a['cagri'] and g.varyant == 'bumper':
        q = g.egri(prog(t, z['cagri'], 0.5))
        boy = _sigdir(g.tf_govde, a['cagri'], 54 * u, genis * 0.8, 0.02)
        f = _font(g.tf_govde, boy)
        w = f.measureText(a['cagri']) + 0.02 * boy * (len(a['cagri']) - 1)
        y = alt - 70 * u
        # çağrı hap şeklinde: ana renk zemin, ana-üstü yazı (marka çifti)
        pad_x, pad_y = 34 * u, 24 * u
        r = skia.Rect(cx - w / 2 - pad_x, y - boy * 0.75 - pad_y + (1 - q) * 30 * u,
                      cx + w / 2 + pad_x, y + boy * 0.25 + pad_y + (1 - q) * 30 * u)
        cv.drawRRect(skia.RRect.MakeRectXY(r, r.height() / 2, r.height() / 2), skia.Paint(AntiAlias=True, Color=_alfa(g.ana, q)))
        _harfler(cv, g.tf_govde, a['cagri'], boy, cx, y + (1 - q) * 30 * u, g.ana_ustu, 0.02, lambda i: (q, 0.0, 1.0))


def _logo_resim_ciz(cv, t, g, cx, cy, genis, u):
    import skia
    p = prog(t, g.z['logo'], 0.6)
    olc = out_back(p, 1.6)
    tur, r = g.logo_resim
    if tur == 'svg':
        boyut = r.containerSize()
        w, h = (boyut.width() or 512), (boyut.height() or 512)
    else:
        w, h = r.width(), r.height()
    k = min(genis * 0.6 / w, 380 * u / h) * olc
    cv.save()
    cv.translate(cx, cy); cv.scale(k, k); cv.translate(-w / 2, -h / 2)
    cv.saveLayerAlpha(None, int(255 * clamp(p * 3)))
    if tur == 'svg':
        r.setContainerSize(skia.Size(w, h)); r.render(cv)
    else:
        cv.drawImage(r, 0, 0)
    cv.restore(); cv.restore()


# ---------- müzik (120 BPM, sentez) ----------
def _cal(buf, t0, x, kazanc=1.0, pan=0.0):
    motor.ekle(buf, t0, x, kazanc, pan)


def _tini(frek, d, dec, parcalar=((1, 1.0), (2, 0.35), (3.01, 0.12))):
    e, tt = motor.zarf(d, 0.002, dec)
    return e * sum(g * np.sin(2 * np.pi * frek * k * tt) for k, g in parcalar)


def _ped(frekler, d, a=0.4):
    tt = np.arange(int(d * SR)) / SR
    e = np.minimum(tt / a, 1.0) * np.minimum((d - tt) / 0.35, 1.0).clip(0, 1)
    x = sum(np.sin(2 * np.pi * f * tt + i) + 0.3 * np.sin(2 * np.pi * f * 1.003 * tt) for i, f in enumerate(frekler))
    return motor.lp_hizli(x * e / len(frekler), 1800)


def _davul(d=0.35):
    tt = np.arange(int(d * SR)) / SR
    f = 46 + 90 * np.exp(-tt / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.12)


def _hisirti(d, dec, seed, cut=6000):
    e, _ = motor.zarf(d, 0.001, dec)
    x = motor.gurultu(d, seed)
    return (x - motor.lp_hizli(x, cut)) * e


def muzik(g):
    n = int(SR * g.sure)
    buf = np.zeros((n, 2))
    m = motor.mtof
    z = g.z
    bumper = g.varyant == 'bumper'
    if bumper:
        # sakin giriş: Bm9 ped, her kelimede yükselen çan
        _cal(buf, 0.0, _ped([m(47), m(54), m(57), m(62), m(61)], z['logo'] + 0.1, 0.5), 0.30)
        _cal(buf, z['nokta'], _tini(m(78), 0.6, 0.18), 0.22)  # nokta "tık"
        for i, nota in enumerate([66, 69, 71, 74, 76][: max(1, len(g.a['onerme'].split()))]):
            t0 = z['kelime'] + i * VURUS
            _cal(buf, t0, _tini(m(nota), 1.2, 0.35), 0.30, -0.3 + 0.15 * i)
            _cal(buf, t0, _hisirti(0.08, 0.02, 10 + i), 0.10)
        for i in range(4):  # hafif nabız, enerji toplar
            _cal(buf, z['kelime'] + i * VURUS, _davul(0.3), 0.25 + 0.08 * i)
    # yükselen hışırtı → logo vuruşu
    d = z['logo'] - z['halka'] + 0.25
    tt = np.arange(int(d * SR)) / SR
    riser = motor.gurultu(d, 3) * (tt / d) ** 2
    riser = riser - motor.lp_hizli(riser, 900)
    _cal(buf, z['halka'] - 0.25, motor.lp_hizli(riser, 7000), 0.22)
    # logo vuruşu: alçak gümbürtü + D majör akor (aydınlık çözülüş) + zil kuyruğu
    L = z['logo']
    _cal(buf, L, _davul(0.8), 0.9)
    _cal(buf, L, _hisirti(1.6, 0.5, 7, 4000), 0.18)
    kalan = g.sure - L
    _cal(buf, L, _ped([m(50), m(57), m(62), m(66), m(69), m(76)], kalan, 0.02), 0.42)
    for i, nota in enumerate([74, 78, 81, 86]):  # parlak arpej
        _cal(buf, L + 0.04 + i * 0.09, _tini(m(nota), 1.6, 0.5), 0.20, -0.4 + 0.27 * i)
    if bumper and g.a['cagri']:
        _cal(buf, z['cagri'], _tini(m(81), 1.0, 0.3), 0.18)
        for i in range(int((g.sure - L) / VURUS) - 1):  # logo altında yumuşak yürüyüş
            _cal(buf, L + (i + 1) * VURUS, _davul(0.25), 0.18)
    f = int(0.30 * SR)
    buf[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
    return buf


# ---------- üretim ----------
def gorunum(senaryo_yolu):
    s, m, _ = yukle(senaryo_yolu)
    g = Gorunum(m, alanlar(s, m), varyant(s), senaryo_yolu)
    if s.get('dil', 'tr') != 'tr':
        g.buyuk = str.upper
    return g, s


def kapak(g, yol, W, H, t=None):
    motor.kapak(lambda cv, t_, W_, H_: kare(cv, t_, W_, H_, g), yol, W, H, g.sure - 0.4 if t is None else t)


def calistir(senaryo_yolu, cikti, boyutlar=('9x16',), olcek=1.0):
    g, s = gorunum(senaryo_yolu)
    ad = f"{s.get('kimlik', 'bumper')}-{g.varyant}"
    is_ = os.path.join(cikti, 'is'); os.makedirs(is_, exist_ok=True)
    import soundfile as sf
    x = muzik(g)
    sf.write(os.path.join(is_, 'ses.wav'), (x / max(1e-9, np.abs(x).max()) * 0.9).astype(np.float32), SR)
    ses = motor.ses_bitir(is_)
    W, H = motor.boyut(boyutlar[0], olcek)
    kapak(g, os.path.join(cikti, f'{ad}-kapak.png'), W, H)
    ciktilar = []
    for b in boyutlar:
        W, H = motor.boyut(b, olcek)
        sessiz = os.path.join(is_, f'sessiz-{b}.mp4')
        motor.video(lambda cv, t, W_, H_: kare(cv, t, W_, H_, g), sessiz, W, H, int(round(FPS * g.sure)))
        hedef = os.path.join(cikti, f'{ad}-{b}.mp4')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', sessiz, '-i', ses, '-c:v', 'copy',
                        '-c:a', 'aac', '-b:a', '192k', '-t', f'{g.sure:.3f}', '-movflags', '+faststart', hedef], check=True)
        os.remove(sessiz)
        ciktilar.append(hedef)
    for f in ('ses.wav', 'ses_14.wav'):
        os.remove(os.path.join(is_, f))
    return ciktilar


def main(argv=None):
    sys.path.insert(0, os.path.join(SABLONLAR, 'stil'))
    from stil import formatlar
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    alt = ap.add_subparsers(dest='komut', required=True)
    for ad in ('denetle', 'kare', 'render', 'uret'):
        p = alt.add_parser(ad)
        p.add_argument('senaryo'); p.add_argument('-o', '--cikti')
        if ad == 'kare':
            p.add_argument('--an', type=float, nargs='+', required=True)
            p.add_argument('--format', default='9x16', type=lambda x: formatlar(x)[0])
        if ad in ('render', 'uret'):
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
        print(f"tamam: {s.get('kimlik', '?')} · bumper/{varyant(s)} · {VARYANTLAR[varyant(s)]:g} sn"); return 0
    cikti = a.cikti or os.path.join(os.path.dirname(os.path.abspath(a.senaryo)), 'cikti')
    if a.komut == 'kare':
        g, s = gorunum(a.senaryo)
        klasor = os.path.join(cikti, 'kareler'); os.makedirs(klasor, exist_ok=True)
        W, H = motor.boyut(a.format)
        for t in a.an:
            yol = os.path.join(klasor, f"{s.get('kimlik', 'bumper')}-{g.varyant}-{a.format}-{t:05.2f}.png")
            kapak(g, yol, W, H, t); print(yol)
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
