"""Instagram carousel şablonu: gerçek fotoğraflar + marka.json → kaydırmalı gönderi (4:5 ya da 1:1 PNG slaytlar).

    python3 platform/sablonlar/karusel/karusel.py denetle senaryo.json
    python3 platform/sablonlar/karusel/karusel.py uret    senaryo.json [-o klasör] [--format 4:5 | 1:1]
    python3 platform/sablonlar/karusel/karusel.py kare    senaryo.json --an 1 3 [-o klasör]   # yalnız seçilen slaytlar

Slaytlar durağan olduğu için önizleme ile ürün aynıdır: `uret` her slaytı tam çözünürlükte yazar, ardından tek
kontakt sayfası ve kalite raporu (`<kimlik>.kontakt.png`, `<kimlik>.kalite.json`). Renk, yazı tipi ve logo
marka.json'dan; metin ve fotoğraflar senaryodan gelir. Bütün slaytlarda aynı alt şerit: sayfa sayacı ve sağ
kenara uzanan ince vurgu çizgisi (son slayt hariç), kaydırmaya çağırır ve slaytları birbirine bağlar.
"""
import argparse, json, os, sys

BURADA = os.path.dirname(os.path.abspath(__file__))
SABLONLAR = os.path.dirname(BURADA)
PLATFORM = os.path.dirname(SABLONLAR)
sys.path.insert(0, os.path.join(SABLONLAR, 'stil'))
sys.path.insert(0, os.path.join(SABLONLAR, 'bumper'))
sys.path.insert(0, os.path.join(SABLONLAR, 'mekan'))
sys.path.insert(0, os.path.join(PLATFORM, 'ortak'))
import motor  # noqa: E402  (büyük harf kuralı, yazı tipi yedeği)
import bumper  # noqa: E402  (marka yükleme, yol çözme, marka yazı tipi)
import marka as marka_mod  # noqa: E402
from mekan import _argb, _font, _genislik, _yaz, _satirla  # noqa: E402

BOYUTLAR = {'4x5': (1080, 1350), '1x1': (1080, 1080)}
TURLER = {  # slayt türü -> izinli alanlar
    'kapak': {'tur', 'foto', 'odak', 'ust', 'baslik', 'alt'},
    'foto': {'tur', 'foto', 'odak', 'ust', 'baslik', 'metin'},
    'liste': {'tur', 'foto', 'ust', 'baslik', 'maddeler'},
    'kapanis': {'tur', 'ust', 'baslik', 'satirlar', 'cagri'},
}
SINIR = {'ust': 32, 'baslik': 44, 'alt': 60, 'metin': 160, 'madde': 38, 'satir': 40, 'cagri': 28}
EN_AZ, EN_COK = 2, 10          # Instagram: bir gönderide 2–10 slayt
BUYUTME_UYARI = 1.25           # fotoğraf kendi çözünürlüğünün bu katından fazla büyütülürse yumuşar
KENAR = 84                     # yan pay (tasarım birimi: genişlik 1080)


class SenaryoHatasi(ValueError):
    pass


# ---------- senaryo ----------
def boyut_adi(s, istek=None):
    f = (istek or s.get('format') or '4:5').replace(':', 'x')
    if f not in BOYUTLAR:
        raise SenaryoHatasi(f'format: "{f}" desteklenmiyor (4:5 ya da 1:1)')
    return f


def _buyutme(img_wh, rect_wh):
    (iw, ih), (rw, rh) = img_wh, rect_wh
    return max(rw / iw, rh / ih)


def denetle(yol):
    """(hatalar, uyarılar). HATA üretimi durdurur."""
    s, m, bulgular = bumper.yukle(yol)
    hata = [f'marka: {b.yer}: {b.mesaj}' for b in bulgular if b.seviye == marka_mod.HATA]
    uyari = [f'marka: {b.yer}: {b.mesaj}' for b in bulgular if b.seviye != marka_mod.HATA]
    try:
        boyut_adi(s)
    except SenaryoHatasi as e:
        hata.append(str(e))
    sl = s.get('slaytlar', [])
    if not EN_AZ <= len(sl) <= EN_COK:
        hata.append(f'slaytlar: {len(sl)} slayt; Instagram carousel {EN_AZ}–{EN_COK} slayt alır')
    for i, x in enumerate(sl):
        yer = f'slaytlar[{i}]'
        tur = x.get('tur')
        if tur not in TURLER:
            hata.append(f'{yer}.tur: "{tur}" bilinmiyor (geçerli: {", ".join(TURLER)})'); continue
        for k in x:
            if k not in TURLER[tur]: hata.append(f'{yer}.{k}: {tur} slaytında tanımsız alan')
        if tur == 'foto' and not x.get('foto'):
            hata.append(f'{yer}.foto: foto slaytında gerekli')
        if not x.get('baslik'):
            hata.append(f'{yer}.baslik: gerekli')
        if x.get('foto'):
            p = bumper._yol(yol, x['foto'])
            if not os.path.exists(p): hata.append(f'{yer}: fotoğraf yok: {x["foto"]}')
            elif not p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')): hata.append(f'{yer}: {x["foto"]} desteklenmiyor')
        for k in ('ust', 'baslik', 'alt', 'metin', 'cagri'):
            v = x.get(k, '')
            if not isinstance(v, str): hata.append(f'{yer}.{k}: metin olmalı')
            elif len(v) > SINIR[k]: hata.append(f'{yer}.{k}: "{v}" {len(v)} karakter, en çok {SINIR[k]}')
        for k, sinir in (('maddeler', SINIR['madde']), ('satirlar', SINIR['satir'])):
            v = x.get(k, [])
            if not isinstance(v, list) or not all(isinstance(a, str) for a in v):
                hata.append(f'{yer}.{k}: metin listesi olmalı'); continue
            if len(v) > 6: hata.append(f'{yer}.{k}: en çok 6 satır')
            for a in v:
                if len(a) > sinir: hata.append(f'{yer}.{k}: "{a}" {len(a)} karakter, en çok {sinir}')
        if tur == 'liste' and not x.get('maddeler'):
            hata.append(f'{yer}.maddeler: liste slaytında gerekli')
    if sl and sl[-1].get('tur') != 'kapanis':
        uyari.append('son slayt kapanış değil: logo ve çağrı sonda görünmez')
    return hata, uyari


# ---------- görünüm ----------
class Gorunum:
    def __init__(self, yol):
        import skia
        s, m, _ = bumper.yukle(yol)
        self.s, self.m = s, m
        r = m.renk
        bul = lambda *adlar: next(r[a] for a in adlar if a in r)
        self.zemin = bul('ana', 'zemin')
        self.yazi = bul('ana-ustu', 'metin')
        self.vurgu = bul('vurgu', 'ana-ustu')
        self.vurgu_ustu = bul('vurgu-ustu', 'ana')
        self.logo_renk = bul('logo', 'vurgu', 'ana-ustu')
        self.buyuk = motor.tr_buyuk if s.get('dil', 'tr') == 'tr' else str.upper
        b, g = m.yazi.get('baslik'), m.yazi.get('govde')
        self.tf_baslik = bumper.marka_yazi_tipi(b.aile, b.agirlik) if b else motor.yazi_tipi(800)
        self.tf_govde = bumper.marka_yazi_tipi(g.aile, g.agirlik) if g else motor.yazi_tipi(500)
        self.tf_govde_kalin = bumper.marka_yazi_tipi(g.aile, 600) if g else motor.yazi_tipi(700)
        self.logo = None
        if m.logo_dosya:
            kok = os.path.dirname(bumper._yol(yol, s['marka']))
            self.logo = skia.Image.open(m.logo_dosya if os.path.isabs(m.logo_dosya) else os.path.join(kok, m.logo_dosya))
        self.slaytlar = s['slaytlar']
        self.resimler = {}
        for x in self.slaytlar:
            if x.get('foto') and x['foto'] not in self.resimler:
                self.resimler[x['foto']] = skia.Image.open(bumper._yol(yol, x['foto']))
        self.ornek = skia.SamplingOptions(skia.CubicResampler.Mitchell())
        self.buyutmeler = {}  # slayt no -> fotoğrafın büyütme katsayısı (kalite raporu)


def _foto(cv, g, no, f, rect, odak=(0.5, 0.5)):
    """Fotoğrafı rect'i dolduracak şekilde odak noktasına göre kırpar (cover); büyütmeyi kaydeder."""
    import skia
    img = g.resimler[f]
    x0, y0, x1, y1 = rect
    rw, rh = x1 - x0, y1 - y0
    sc = _buyutme((img.width(), img.height()), (rw, rh))
    g.buyutmeler[no] = max(g.buyutmeler.get(no, 0), sc)
    iw, ih = img.width() * sc, img.height() * sc
    ox = min(0, max(rw - iw, rw / 2 - odak[0] * iw))
    oy = min(0, max(rh - ih, rh / 2 - odak[1] * ih))
    cv.save()
    cv.clipRect(skia.Rect(x0, y0, x1, y1), doAntiAlias=True)
    cv.drawImageRect(img, skia.Rect(x0 + ox, y0 + oy, x0 + ox + iw, y0 + oy + ih), g.ornek, skia.Paint(AntiAlias=True))
    cv.restore()


def _bulanik_zemin(cv, g, f, W, H, alfa):
    import skia
    img = g.resimler[f]
    cv.save()
    sc = max(W / img.width(), H / img.height()) * 1.15
    cv.translate(W / 2, H / 2); cv.scale(sc, sc); cv.translate(-img.width() / 2, -img.height() / 2)
    p = skia.Paint(ImageFilter=skia.ImageFilters.Blur(30 / sc, 30 / sc), Dither=True)
    p.setAlphaf(alfa)
    cv.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), p)
    cv.restore()


def _boy_sigdir(tf, metin, boy, genislik, satir_sayisi, en_kucuk):
    """Metni en çok `satir_sayisi` satıra sığdıran en büyük boy; sığmazsa None."""
    while boy >= en_kucuk:
        satirlar = _satirla(tf, metin, boy, genislik)
        if len(satirlar) <= satir_sayisi and all(_genislik(_font(tf, boy), x) <= genislik for x in satirlar):
            return boy, satirlar
        boy *= 0.95
    return None


def _metin_blogu(cv, tf, metin, boy, genislik, satir_sayisi, x, y, renk, satir_arasi=1.18, hiza='sol', en_kucuk=None):
    """Satırlara bölünmüş metni y taban çizgisinden başlayarak yazar; son satırın taban çizgisini döndürür."""
    sonuc = _boy_sigdir(tf, metin, boy, genislik, satir_sayisi, en_kucuk or boy * 0.6)
    if sonuc is None:
        raise SenaryoHatasi(f'"{metin}" {satir_sayisi} satıra sığmıyor')
    boy, satirlar = sonuc
    for k, s in enumerate(satirlar):
        _yaz(cv, tf, s, boy, x, y + k * boy * satir_arasi, renk, 1.0, hiza)
    return y + (len(satirlar) - 1) * boy * satir_arasi


def _etiket(cv, g, metin, x, y, u, hiza='sol', renk=None):
    """Küçük, harf aralıklı büyük harf etiket (vurgu renginde)."""
    _yaz(cv, g.tf_govde_kalin, g.buyuk(metin), 26 * u, x, y, renk or g.vurgu, 1.0, hiza, 0.22)


def _serit(cv, g, no, n, W, H, u):
    """Alt şerit: sayfa sayacı + sağ kenara uzanan çizgi ve ok (son slaytta çizgi kalp ile biter)."""
    import skia
    y = H - 72 * u
    sol = KENAR * u
    sayac = f'{no:02d} / {n:02d}'
    w = _yaz(cv, g.tf_govde_kalin, sayac, 24 * u, sol, y + 8 * u, g.yazi, 0.85, 'sol', 0.12)
    p = skia.Paint(AntiAlias=True, Color=_argb(g.vurgu, 0.9), StrokeWidth=2 * u, Style=skia.Paint.kStroke_Style,
                   StrokeCap=skia.Paint.kRound_Cap)
    x0 = sol + w + 28 * u
    if no < n:  # kenardan taşar: bir sonraki slaytta devam ediyor hissi
        cv.drawLine(x0, y, W, y, p)
        ax = W - KENAR * u
        cv.drawLine(ax - 16 * u, y - 12 * u, ax, y, p); cv.drawLine(ax - 16 * u, y + 12 * u, ax, y, p)
    else:
        cx = W - KENAR * u - 14 * u
        cv.drawLine(x0, y, cx - 26 * u, y, p)
        _kalp(cv, cx, y, 14 * u, p)


def _kalp(cv, cx, cy, r, p):
    import skia
    h = skia.Path()
    h.moveTo(cx, cy + r * 0.95)
    h.cubicTo(cx - r * 1.5, cy - r * 0.05, cx - r * 0.95, cy - r * 1.25, cx, cy - r * 0.45)
    h.cubicTo(cx + r * 0.95, cy - r * 1.25, cx + r * 1.5, cy - r * 0.05, cx, cy + r * 0.95)
    cv.drawPath(h, p)


def _logo(cv, g, cx, cy, genislik, yukseklik, alfa=1.0):
    import skia
    if g.logo is None:
        ad = g.m.logo_metin or g.m.ad
        boy = min(yukseklik * 0.7, yukseklik * 0.7 * genislik / max(1, _genislik(_font(g.tf_baslik, yukseklik * 0.7), ad)))
        _yaz(cv, g.tf_baslik, ad, boy, cx, cy + boy * 0.33, g.logo_renk, alfa, 'orta')
        return
    k = min(genislik / g.logo.width(), yukseklik / g.logo.height())
    w, h = g.logo.width() * k, g.logo.height() * k
    p = skia.Paint(AntiAlias=True, ColorFilter=skia.ColorFilters.Blend(_argb(g.logo_renk), skia.BlendMode.kSrcIn))
    p.setAlphaf(alfa)
    cv.drawImageRect(g.logo, skia.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), g.ornek, p)


# ---------- slayt türleri ----------
def _kapak(cv, g, no, x, W, H, u):
    """Tam kadraj fotoğraf; alt bölümde koyu geçiş üstünde etiket, büyük başlık, alt satır. Üstte küçük logo."""
    import skia
    sol, sag = KENAR * u, W - KENAR * u
    if x.get('foto'):
        _foto(cv, g, no, x['foto'], (0, 0, W, H), x.get('odak', (0.5, 0.5)))
        # okunurluk için alttan koyu geçiş (titreşimli: 8 bitte basamak olmasın)
        y0 = H * 0.42
        cv.drawRect(skia.Rect(0, y0, W, H), skia.Paint(Dither=True, Shader=skia.GradientShader.MakeLinear(
            [(0, y0), (0, H * 0.78)], [_argb(g.zemin, 0.0), _argb(g.zemin, 0.94)])))
    else:
        _logo(cv, g, W / 2, H * 0.36, sag - sol, 260 * u)
    if x.get('foto') and g.logo is not None:
        cv.drawRect(skia.Rect(0, 0, W, 190 * u), skia.Paint(Dither=True, Shader=skia.GradientShader.MakeLinear(
            [(0, 0), (0, 190 * u)], [_argb(g.zemin, 0.55), _argb(g.zemin, 0.0)])))
    alt_y = H - 150 * u
    y = alt_y
    if x.get('alt'):
        _yaz(cv, g.tf_govde, x['alt'], 32 * u, sol, y, g.yazi, 0.9)
        y -= 70 * u
    # önce tek satır (biraz küçülerek); olmazsa iki satır: tek kelimelik ikinci satır kalmasın
    sonuc = (_boy_sigdir(g.tf_baslik, x['baslik'], 112 * u, sag - sol, 1, 84 * u)
             or _boy_sigdir(g.tf_baslik, x['baslik'], 112 * u, sag - sol, 2, 70 * u))
    if sonuc is None:
        raise SenaryoHatasi(f'slayt {no}: başlık iki satıra sığmıyor')
    boy, satirlar = sonuc
    y0 = y - (len(satirlar) - 1) * boy * 1.05
    for k, s in enumerate(satirlar):
        _yaz(cv, g.tf_baslik, s, boy, sol, y0 + k * boy * 1.05, g.yazi)
    if x.get('ust'):
        _etiket(cv, g, x['ust'], sol, y0 - boy - 6 * u, u)


def _foto_slayt(cv, g, no, x, W, H, u):
    """Fotoğraf üstte tam genişlikte (kendi oranında, en çok yüksekliğin %58'i), altında numara, etiket, başlık, metin."""
    import skia
    sol, sag = KENAR * u, W - KENAR * u
    img = g.resimler[x['foto']]
    fh = min(H * 0.58, W * img.height() / img.width())
    _foto(cv, g, no, x['foto'], (0, 0, W, fh), x.get('odak', (0.5, 0.5)))
    cv.drawLine(0, fh, W, fh, skia.Paint(AntiAlias=True, Color=_argb(g.vurgu), StrokeWidth=3 * u))
    y = fh + 92 * u
    etiket = f'{no - 1:02d}' + (f'  ·  {x["ust"]}' if x.get('ust') else '')
    _etiket(cv, g, etiket, sol, y, u)
    y += 30 * u
    sonuc = _boy_sigdir(g.tf_baslik, x['baslik'], 92 * u, sag - sol, 2, 64 * u)
    if sonuc is None:
        raise SenaryoHatasi(f'slayt {no}: başlık iki satıra sığmıyor')
    boy, satirlar = sonuc
    for k, s in enumerate(satirlar):
        y += boy * (1.0 if k == 0 else 1.05)
        _yaz(cv, g.tf_baslik, s, boy, sol, y, g.yazi)
    if x.get('metin'):
        kalan = H - 130 * u - (y + 76 * u)
        satir = max(1, min(4, int(kalan // (34 * u * 1.5)) + 1))
        _metin_blogu(cv, g.tf_govde, x['metin'], 34 * u, sag - sol, satir, sol, y + 76 * u, g.yazi, 1.5, en_kucuk=28 * u)


def _liste(cv, g, no, x, W, H, u):
    """Başlık ve kalp işaretli maddeler; fotoğraf verilirse çok koyu, bulanık zemin olur."""
    import skia
    sol, sag = KENAR * u, W - KENAR * u
    if x.get('foto'):
        _bulanik_zemin(cv, g, x['foto'], W, H, 0.28)
    # ince çerçeve
    cv.drawRect(skia.Rect(40 * u, 40 * u, W - 40 * u, H - 130 * u), skia.Paint(
        AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.5 * u, Color=_argb(g.vurgu, 0.55)))
    y = 190 * u
    if x.get('ust'):
        _etiket(cv, g, x['ust'], sol + 30 * u, y, u); y += 40 * u
    sonuc = _boy_sigdir(g.tf_baslik, x['baslik'], 96 * u, sag - sol - 60 * u, 2, 64 * u)
    if sonuc is None:
        raise SenaryoHatasi(f'slayt {no}: başlık iki satıra sığmıyor')
    boy, satirlar = sonuc
    for k, s in enumerate(satirlar):
        y += boy * (1.0 if k == 0 else 1.05)
        _yaz(cv, g.tf_baslik, s, boy, sol + 30 * u, y, g.yazi)
    maddeler = x['maddeler']
    alan_ust, alan_alt = y + 70 * u, H - 200 * u
    adim = min(120 * u, (alan_alt - alan_ust) / max(1, len(maddeler)))
    p = skia.Paint(AntiAlias=True, Color=_argb(g.vurgu))
    for k, md in enumerate(maddeler):
        yy = alan_ust + adim * (k + 0.5)
        _kalp(cv, sol + 46 * u, yy - 12 * u, 13 * u, p)
        boy_m = min(46 * u, 46 * u * (sag - sol - 140 * u) / max(1, _genislik(_font(g.tf_govde, 46 * u), md)))
        _yaz(cv, g.tf_govde, md, boy_m, sol + 92 * u, yy, g.yazi)
        if k < len(maddeler) - 1:
            cv.drawLine(sol + 92 * u, yy + adim / 2 - 6 * u, sag - 30 * u, yy + adim / 2 - 6 * u,
                        skia.Paint(AntiAlias=True, Color=_argb(g.yazi, 0.14), StrokeWidth=1.2 * u))


def _kapanis(cv, g, no, x, W, H, u):
    """Logo, başlık, iletişim satırları ve vurgu renginde çağrı düğmesi; hepsi ortalı."""
    import skia
    sol, sag = KENAR * u, W - KENAR * u
    cx = W / 2
    _logo(cv, g, cx, H * 0.27, (sag - sol) * 0.86, 240 * u)
    y = H * 0.27 + 210 * u
    if x.get('ust'):
        _etiket(cv, g, x['ust'], cx, y, u, 'orta'); y += 40 * u
    sonuc = _boy_sigdir(g.tf_baslik, x['baslik'], 84 * u, sag - sol, 2, 56 * u)
    if sonuc is None:
        raise SenaryoHatasi(f'slayt {no}: başlık iki satıra sığmıyor')
    boy, satirlar = sonuc
    for k, s in enumerate(satirlar):
        y += boy * (1.0 if k == 0 else 1.05)
        _yaz(cv, g.tf_baslik, s, boy, cx, y, g.yazi, 1.0, 'orta')
    y += 30 * u
    for s in x.get('satirlar', []):
        y += 52 * u
        _yaz(cv, g.tf_govde, s, min(34 * u, 34 * u * (sag - sol) / max(1, _genislik(_font(g.tf_govde, 34 * u), s))),
             cx, y, g.yazi, 0.92, 'orta')
    if x.get('cagri'):
        s = g.buyuk(x['cagri'])
        f = _font(g.tf_govde_kalin, 28 * u)
        w = _genislik(f, s, 0.2)
        yy = max(y + 110 * u, H - 250 * u)
        rect = skia.Rect(cx - w / 2 - 44 * u, yy - 46 * u, cx + w / 2 + 44 * u, yy + 30 * u)
        cv.drawRect(rect, skia.Paint(AntiAlias=True, Color=_argb(g.vurgu)))
        _yaz(cv, g.tf_govde_kalin, s, 28 * u, cx, yy + 2 * u, g.vurgu_ustu, 1.0, 'orta', 0.2)


CIZICILER = {'kapak': _kapak, 'foto': _foto_slayt, 'liste': _liste, 'kapanis': _kapanis}


def slayt(g, no, W, H):
    """no: 1'den başlar. RGBA skia.Image döndürür."""
    import skia
    n = len(g.slaytlar)
    x = g.slaytlar[no - 1]
    u = W / 1080
    surf = skia.Surface(W, H)
    with surf as cv:
        cv.clear(_argb(g.zemin))
        CIZICILER[x['tur']](cv, g, no, x, W, H, u)
        _serit(cv, g, no, n, W, H, u)
    return surf.makeImageSnapshot()


# ---------- kalite ----------
def kalite_raporu(g, kareler, hedef_klasor, kimlik):
    """Banding, netlik ve fotoğraf büyütmesi; kalite.json + kontakt sayfası."""
    import kalite
    bulgular = []
    for no, k in kareler:
        b = kalite.banding_orani(k)
        if b >= kalite.ESIK['banding_hata']:
            bulgular.append({'seviye': 'HATA', 'kontrol': 'banding', 'mesaj': f'slayt {no}: banding %{b * 100:.0f}'})
        elif b >= kalite.ESIK['banding_uyari']:
            bulgular.append({'seviye': 'UYARI', 'kontrol': 'banding', 'mesaj': f'slayt {no}: banding %{b * 100:.0f}'})
        sc = g.buyutmeler.get(no)
        if sc and sc > BUYUTME_UYARI:
            bulgular.append({'seviye': 'UYARI', 'kontrol': 'cozunurluk',
                             'mesaj': f'slayt {no}: fotoğraf {sc:.2f} kat büyütüldü, daha büyük dosya gerekli'})
    sonuc = 'kaldi' if any(b['seviye'] == 'HATA' for b in bulgular) else 'uyarili' if bulgular else 'gecti'
    rapor = {'sonuc': sonuc, 'slayt_sayisi': len(kareler), 'bulgular': bulgular,
             'buyutme': {str(k): round(v, 3) for k, v in sorted(g.buyutmeler.items())}}
    with open(os.path.join(hedef_klasor, f'{kimlik}.kalite.json'), 'w', encoding='utf-8') as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    kalite.kontakt_yaz([(f'{no:02d}', k) for no, k in kareler], os.path.join(hedef_klasor, f'{kimlik}.kontakt.png'),
                       dikey=False, sutun=min(5, len(kareler)))
    return rapor


def calistir(yol, cikti, fmt=None, secim=None):
    import numpy as np
    hata, uyari = denetle(yol)
    for u_ in uyari:
        print('UYARI:', u_)
    if hata:
        raise SenaryoHatasi('\n'.join(hata))
    g = Gorunum(yol)
    ad = boyut_adi(g.s, fmt)
    W, H = BOYUTLAR[ad]
    kimlik = g.s.get('kimlik', 'karusel')
    os.makedirs(cikti, exist_ok=True)
    nolar = secim or list(range(1, len(g.slaytlar) + 1))
    kareler = []
    for no in nolar:
        img = slayt(g, no, W, H)
        p = os.path.join(cikti, f'{kimlik}-{ad}-{no:02d}.png')
        img.save(p, __import__('skia').kPNG)
        kareler.append((no, np.ascontiguousarray(img.toarray()[:, :, [2, 1, 0]] if img.colorType() == __import__('skia').kBGRA_8888_ColorType else img.toarray()[:, :, :3])))
        print(p)
    if secim:
        return None
    rapor = kalite_raporu(g, kareler, cikti, kimlik)
    print(f'kalite: {rapor["sonuc"]}' + ''.join(f'\n  {b["seviye"]}: {b["mesaj"]}' for b in rapor['bulgular']))
    return rapor


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('komut', choices=('denetle', 'uret', 'kare'))
    ap.add_argument('senaryo')
    ap.add_argument('-o', '--cikti', default=None)
    ap.add_argument('--format', default=None, help='4:5 (varsayılan) ya da 1:1')
    ap.add_argument('--an', nargs='+', type=float, default=None, help='kare: slayt numaraları (1, 2, …)')
    a = ap.parse_args(argv)
    if a.komut == 'denetle':
        hata, uyari = denetle(a.senaryo)
        for x in uyari: print('UYARI:', x)
        for x in hata: print('HATA:', x)
        if not hata:
            s = json.load(open(a.senaryo, encoding='utf-8'))
            print(f'tamam: {s.get("kimlik")} · karusel · {len(s.get("slaytlar", []))} slayt')
        return 1 if hata else 0
    cikti = a.cikti or os.path.join(os.path.dirname(os.path.abspath(a.senaryo)), 'cikti')
    try:
        if a.komut == 'kare':
            n = len(json.load(open(a.senaryo, encoding='utf-8')).get('slaytlar', []))
            secim = sorted({min(n, max(1, int(x))) for x in (a.an or [1])})
            calistir(a.senaryo, os.path.join(cikti, 'kareler'), a.format, secim)
            return 0
        rapor = calistir(a.senaryo, cikti, a.format)
        return 1 if rapor['sonuc'] == 'kaldi' else 0
    except SenaryoHatasi as e:
        print('HATA:', e)
        return 1


if __name__ == '__main__':
    sys.exit(main())
