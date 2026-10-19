"""Mekân şablonu: gerçek ürün fotoğrafları + marka.json → mekân TV döngüsü ya da kısa sosyal reklam (Reel).

    python3 platform/sablonlar/mekan/mekan.py denetle   senaryo.json
    python3 platform/sablonlar/mekan/mekan.py seslendir senaryo.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/mekan/mekan.py kare      senaryo.json --an 2 11.5 [--format 16:9]
    python3 platform/sablonlar/mekan/mekan.py render    senaryo.json [--format 16:9 | 9:16 | ...] [--olcek 0.25]
`stil.py <komut> senaryo.json --stil mekan` aynı komutları buraya iletir (`uret` = seslendirme yoksa üret + render).

Varyantlar:
    tv    Mekândaki ekran için kesintisiz döngü. Yavaş yakınlaşma, uzun yumuşak geçişler, büyük yazı, koyu zemin;
          son kare ilk kareye birebir bağlanır, müzik de döngü noktasında kesilmez. Müzikli + sessiz iki dosya.
    reel  9:16 kısa reklam. Ritme oturan geçişler, kelime kelime yazı, isteğe bağlı seslendirme, sonda marka kartı.

Renk, yazı tipi ve logo marka.json'dan gelir; metinler ve fotoğraflar senaryodan. Her kare t'nin saf fonksiyonudur.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np

BURADA = os.path.dirname(os.path.abspath(__file__))
SABLONLAR = os.path.dirname(BURADA)
PLATFORM = os.path.dirname(SABLONLAR)
sys.path.insert(0, os.path.join(SABLONLAR, 'stil'))
sys.path.insert(0, os.path.join(SABLONLAR, 'bumper'))
import motor  # noqa: E402  (kodlama, LUFS, kolaylaştırma, ses yardımcıları)
import bumper  # noqa: E402  (marka yükleme, yol çözme, marka yazı tipi, bezier)
import marka as marka_mod  # noqa: E402

FPS, SR = motor.FPS, motor.SR
clamp, lerp, prog = motor.clamp, motor.lerp, motor.prog
out_cubic, in_out = motor.out_cubic, motor.in_out_cubic

VARYANTLAR = ('tv', 'reel')
TURLER = {  # sahne türü -> izinli alanlar
    'marka': {'tur', 'sure', 'foto', 'odak', 'logo', 'ust', 'baslik', 'alt'},
    'urun': {'tur', 'sure', 'foto', 'odak', 'duzen', 'ust', 'baslik', 'alt'},
    'uclu': {'tur', 'sure', 'fotolar', 'baslik'},
    'bilgi': {'tur', 'sure', 'foto', 'odak', 'ust', 'baslik', 'satirlar', 'alt'},
}
# yazı sınırları (karakter): yerleşim taşmasın, TV'de uzaktan okunsun
SINIR = {'ust': 28, 'baslik': 28, 'alt': 48, 'satir': 40}
VARSAYILAN = {
    'tv': {'gecis': 1.6, 'bpm': 64, 'lufs': -16.0},   # sakin: uzun geçiş, 4/4'te bir ölçü 3,75 sn
    'reel': {'gecis': 0.45, 'bpm': 96, 'lufs': -14.0},
}
# üst, alt, yan. 9:16'da kalite kapısının Reels arayüzüyle aynı: alt %22 ve sağdaki düğmeler (%13); ortalı yazı
# iki yanda da bu payı bırakır
GUVENLI = {'9x16': (0.13, 0.22, 0.13), '4x5': (0.08, 0.10, 0.07)}
DUZENLER = ('ust', 'cerceve')  # Reel ürün sahnesi: fotoğraf üstte tam genişlik | çerçeveli kart, arkada bulanık kopyası


class SenaryoHatasi(ValueError):
    pass


# ---------- senaryo ----------
def yukle(yol):
    s, m, bulgular = bumper.yukle(yol)
    return s, m, bulgular


def varyant(s):
    return s.get('varyant', 'tv')


def ayar(s, ad):
    return s.get(ad, VARSAYILAN[varyant(s)][ad]) if ad != 'bpm' else s.get('muzik', {}).get('bpm', VARSAYILAN[varyant(s)]['bpm'])


def zaman_cizelgesi(s):
    """[(baş, süre)] ve toplam süre. TV'de toplam = döngü uzunluğu."""
    t, z = 0.0, []
    for sh in s.get('sahneler', []):
        z.append((t, float(sh.get('sure', 0))))
        t += float(sh.get('sure', 0))
    return z, t


def denetle(yol, render=False, cikti=None):
    """(hatalar, uyarılar). HATA üretimi durdurur."""
    s, m, bulgular = yukle(yol)
    hata = [f'marka: {b.yer}: {b.mesaj}' for b in bulgular if b.seviye == marka_mod.HATA]
    uyari = [f'marka: {b.yer}: {b.mesaj}' for b in bulgular if b.seviye != marka_mod.HATA]
    v = varyant(s)
    if v not in VARYANTLAR:
        return hata + [f'varyant: "{v}" bilinmiyor (geçerli: {", ".join(VARYANTLAR)})'], uyari
    if s.get('tema', 'koyu') not in ('koyu', 'acik'):
        hata.append(f'tema: "{s.get("tema")}" bilinmiyor (koyu ya da acik)')
    sahneler = s.get('sahneler', [])
    if not sahneler:
        hata.append('sahneler: en az bir sahne gerekli')
    gecis = ayar(s, 'gecis')
    for i, sh in enumerate(sahneler):
        yer = f'sahneler[{i}]'
        tur = sh.get('tur')
        if tur not in TURLER:
            hata.append(f'{yer}.tur: "{tur}" bilinmiyor (geçerli: {", ".join(TURLER)})'); continue
        for k in sh:
            if k not in TURLER[tur]: hata.append(f'{yer}.{k}: {tur} sahnesinde tanımsız alan')
        d = sh.get('sure')
        if not isinstance(d, (int, float)) or d <= 0:
            hata.append(f'{yer}.sure: pozitif sayı olmalı')
        elif d < gecis * 2 + (3.0 if v == 'tv' else 1.0):
            uyari.append(f'{yer}.sure: {d} sn, yazının okunması için kısa')
        fotolar = sh.get('fotolar', []) + ([sh['foto']] if sh.get('foto') else [])
        if tur == 'urun' and not sh.get('foto'):
            hata.append(f'{yer}.foto: ürün sahnesinde gerekli')
        if sh.get('duzen', 'ust') not in DUZENLER:
            hata.append(f'{yer}.duzen: "{sh.get("duzen")}" bilinmiyor (geçerli: {", ".join(DUZENLER)})')
        if tur == 'uclu' and len(sh.get('fotolar', [])) != 3:
            hata.append(f'{yer}.fotolar: üç fotoğraf gerekli')
        for f in fotolar:
            p = bumper._yol(yol, f)
            if not os.path.exists(p): hata.append(f'{yer}: fotoğraf yok: {f}')
            elif not p.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')): hata.append(f'{yer}: {f} desteklenmiyor')
        for k in ('ust', 'baslik', 'alt'):
            x = sh.get(k, '')
            if not isinstance(x, str): hata.append(f'{yer}.{k}: metin olmalı')
            elif len(x) > SINIR[k]: hata.append(f'{yer}.{k}: "{x}" {len(x)} karakter, en çok {SINIR[k]}')
        for x in sh.get('satirlar', []):
            if not isinstance(x, list) or len(x) != 2: hata.append(f'{yer}.satirlar: her satır [sol, sağ] olmalı'); continue
            if len(x[0]) + len(x[1]) > SINIR['satir']: hata.append(f'{yer}.satirlar: "{x[0]} {x[1]}" uzun')
    if v == 'tv' and s.get('seslendirme'):
        hata.append('seslendirme: TV döngüsünde kullanılmaz (mekânda ses çoğu zaman kapalı; konuşma döngüde tekrar eder)')
    z, toplam = zaman_cizelgesi(s)
    if v == 'tv' and not 20 <= toplam <= 120:
        uyari.append(f'süre {toplam:g} sn; TV döngüsü için 30–60 sn önerilir')
    if v == 'reel' and toplam > 60:
        hata.append(f'süre {toplam:g} sn; Reel en çok 60 sn')
    # seslendirme satırları kendi sahnesine sığmalı
    sure = _sureler(_ses_dizini(yol, s, cikti))
    for x in s.get('seslendirme', {}).get('satirlar', []):
        d = sure.get(x['id'])
        if d is None:
            if render: hata.append(f'{x["id"]}: seslendirme yok; önce `seslendir` çalıştırın')
            continue
        bitis = x['t'] + d
        sahne = next(((b, dd) for b, dd in z if b <= x['t'] < b + dd), None)
        if bitis > toplam - 0.2:
            hata.append(f'{x["id"]}: {bitis:.2f} sn\'de bitiyor, video {toplam:g} sn')
        elif sahne and bitis > sahne[0] + sahne[1] + 0.35:
            uyari.append(f'{x["id"]}: sahnesinden {bitis - sahne[0] - sahne[1]:.2f} sn taşıyor')
    return hata, uyari


def _ses_dizini(yol, s, cikti=None):
    return os.path.join(cikti or os.path.join(os.path.dirname(os.path.abspath(yol)), 'cikti'), 'seslendirme')


def _sureler(klasor):
    k = os.path.join(klasor, 'seslendirme.json')
    if not os.path.exists(k):
        return {}
    with open(k, encoding='utf-8') as f:
        return {x['id']: x['sure'] for x in json.load(f)['satirlar']}


# ---------- görünüm ----------
def _argb(h, a=1.0):
    return (int(clamp(a) * 255) << 24) | int(h.lstrip('#'), 16)


class Gorunum:
    def __init__(self, yol):
        import skia
        s, m, _ = yukle(yol)
        self.s, self.m, self.v = s, m, varyant(s)
        r = m.renk
        bul = lambda *adlar: next(r[a] for a in adlar if a in r)
        self.zemin = bul('ana', 'metin')          # koyu sahne zemini
        self.yazi = bul('ana-ustu', 'zemin')      # koyu zemindeki yazı
        self.vurgu = bul('vurgu', 'ana-ustu', 'zemin')
        self.acik = bul('zemin')                  # marka kartı zemini
        self.koyu_yazi = bul('metin')
        self.logo_renk = bul('logo', 'ana', 'metin')
        # TV teması: koyu (varsayılan, loş mekân) ya da açık (krem zemin, koyu yazı, logo yeşili vurgu)
        self.acik_tema = s.get('tema', 'koyu') == 'acik'
        self.tz, self.ty, self.tvv = ((self.acik, self.koyu_yazi, self.logo_renk) if self.acik_tema
                                      else (self.zemin, self.yazi, self.vurgu))
        # büyük harf dile göre: Türkçede i → İ, Almancada ß → SS (senaryo "dil", varsayılan tr)
        self.buyuk = motor.tr_buyuk if s.get('dil', 'tr') == 'tr' else str.upper
        self.egri = bumper.bezier(m.hareket.get('egri', [0.2, 0, 0, 1]))
        b, g = m.yazi.get('baslik'), m.yazi.get('govde')
        self.tf_baslik = bumper.marka_yazi_tipi(b.aile, b.agirlik) if b else motor.yazi_tipi(800)
        self.tf_govde = bumper.marka_yazi_tipi(g.aile, g.agirlik) if g else motor.yazi_tipi(700)
        self.tf_govde_kalin = bumper.marka_yazi_tipi(g.aile, 600) if g else motor.yazi_tipi(700)
        self.logo = None
        if m.logo_dosya:  # marka.py gibi marka.json'un klasörüne göre
            kok = os.path.dirname(bumper._yol(yol, s['marka']))
            p = m.logo_dosya if os.path.isabs(m.logo_dosya) else os.path.join(kok, m.logo_dosya)
            self.logo = skia.Image.open(p)
        # logo.isaret (isteğe bağlı): yazısız işaret; küçük imzada yazı okunmadığı için onu kullanırız
        with open(bumper._yol(yol, s['marka']), encoding='utf-8') as f:
            isaret = json.load(f).get('logo', {}).get('isaret')
        self.isaret = None
        if isaret:
            kok = os.path.dirname(bumper._yol(yol, s['marka']))
            self.isaret = skia.Image.open(isaret if os.path.isabs(isaret) else os.path.join(kok, isaret))
        self.sahneler = s['sahneler']
        self.z, self.sure = zaman_cizelgesi(s)
        self.gecis = ayar(s, 'gecis')
        self.bpm = ayar(s, 'bpm')
        self.resimler = {}
        for sh in self.sahneler:
            for f in sh.get('fotolar', []) + ([sh['foto']] if sh.get('foto') else []):
                if f not in self.resimler:
                    self.resimler[f] = skia.Image.open(bumper._yol(yol, f))
        self._bulanik = {}
        self.ornek = skia.SamplingOptions(skia.CubicResampler.Mitchell())

    def bulanik(self, f, W, H):
        """Fotoğrafın kadrajı dolduran, bulanık ve koyulaştırılmış kopyası (boyut başına bir kez)."""
        import skia
        k = (f, W, H)
        if k not in self._bulanik:
            img = self.resimler[f]
            surf = skia.Surface(W, H)
            with surf as cv:
                sc = max(W / img.width(), H / img.height()) * 1.15
                cv.translate(W / 2, H / 2); cv.scale(sc, sc); cv.translate(-img.width() / 2, -img.height() / 2)
                p = skia.Paint(ImageFilter=skia.ImageFilters.Blur(28 / sc, 28 / sc))
                cv.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), p)
            self._bulanik[k] = surf.makeImageSnapshot()
        return self._bulanik[k]


def _font(tf, boy):
    import skia
    f = skia.Font(tf, boy); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def _genislik(f, s, aralik=0.0):
    return f.measureText(s) + aralik * f.getSize() * max(0, len(s) - 1)


def _sigdir(tf, s, boy, genislik, aralik=0.0):
    w = _genislik(_font(tf, boy), s, aralik)
    return boy if w <= genislik else boy * genislik / w


def _yaz(cv, tf, s, boy, x, y, renk, alfa=1.0, hiza='sol', aralik=0.0, golge=0.0):
    """Tek satır. hiza: sol | orta | sag. aralik: harf aralığı (boya oranlı)."""
    import skia
    if alfa <= 0 or not s:
        return 0
    f = _font(tf, boy)
    w = _genislik(f, s, aralik)
    x0 = x - (w / 2 if hiza == 'orta' else w if hiza == 'sag' else 0)
    p = skia.Paint(AntiAlias=True, Color=_argb(renk, alfa))
    if golge:
        p.setImageFilter(skia.ImageFilters.DropShadow(0, boy * 0.04, boy * 0.12, boy * 0.12, _argb('#000000', golge * alfa)))
    if aralik:
        ara = aralik * boy
        for ch in s:
            cv.drawString(ch, x0, y, f, p); x0 += f.measureText(ch) + ara
    else:
        cv.drawString(s, x0, y, f, p)
    return w


def _kelimeler(cv, tf, s, boy, x, y, renk, t0, t, u, hiza='sol', adim=0.09, golge=0.0, egri=out_cubic):
    """Kelime kelime yükselerek beliren satır (Reel)."""
    f = _font(tf, boy)
    kel = s.split()
    bosluk = f.measureText(' ')
    ws = [f.measureText(k) for k in kel]
    w = sum(ws) + bosluk * (len(kel) - 1)
    xx = x - (w / 2 if hiza == 'orta' else 0)
    for i, (k, kw) in enumerate(zip(kel, ws)):
        p = egri(prog(t, t0 + i * adim, 0.5))
        _yaz(cv, tf, k, boy, xx, y + (1 - p) * 40 * u, renk, p, golge=golge)
        xx += kw + bosluk


def _satirla(tf, s, boy, genislik):
    """Metni genişliğe göre satırlara böler. " · " ile ayrılmış listeler yalnız ayraçlarda bölünür."""
    f = _font(tf, boy)
    satirlar, cur = [], ''
    ayrac = ' · ' if ' · ' in s else ' '
    for k in s.split(ayrac):
        aday = (cur + ayrac + k).strip(' ·') if cur else k
        if cur and f.measureText(aday) > genislik:
            satirlar.append(cur); cur = k
        else:
            cur = aday
    return satirlar + ([cur] if cur else [])


def foto_ciz(cv, g, f, rect, odak=(0.5, 0.5), zoom=1.0, kay=(0.0, 0.0), alfa=1.0, logo=None):
    """Fotoğrafı rect'i dolduracak şekilde (cover) odak noktasına göre kırpıp çizer; zoom/kay Ken Burns için.
    logo=[x, y, h] (fotoğrafa oranla): logo fotoğrafla birlikte hareket eder. Düşük çözünürlüklü bir marka
    görselindeki logo silinip yerine keskin logo çizilir; fotoğraf büyüse de logo net kalır."""
    import skia
    img = g.resimler[f]
    x0, y0, x1, y1 = rect
    rw, rh = x1 - x0, y1 - y0
    sc = max(rw / img.width(), rh / img.height()) * zoom
    iw, ih = img.width() * sc, img.height() * sc
    # odak noktası rect merkezine yaklaşır; taşma sınırlanır
    ox = clamp(rw / 2 - odak[0] * iw + kay[0] * rw, rw - iw, 0)
    oy = clamp(rh / 2 - odak[1] * ih + kay[1] * rh, rh - ih, 0)
    cv.save()
    cv.clipRect(skia.Rect(x0, y0, x1, y1), doAntiAlias=True)
    p = skia.Paint(AntiAlias=True); p.setAlphaf(alfa)
    cv.drawImageRect(img, skia.Rect(x0 + ox, y0 + oy, x0 + ox + iw, y0 + oy + ih), g.ornek, p)
    if logo:
        logo_ciz(cv, g, x0 + ox + logo[0] * iw, y0 + oy + logo[1] * ih, logo[2] * ih, g.logo_renk, alfa)
    cv.restore()


def logo_ciz(cv, g, cx, cy, yukseklik, renk, alfa=1.0, isaret=False):
    """Logo PNG'si tek renge boyanır (koyu zeminde açık, açık zeminde marka yeşili). isaret: yazısız işaret."""
    import skia
    img = g.isaret if isaret and g.isaret is not None else g.logo
    if img is None:
        _yaz(cv, g.tf_baslik, g.m.logo_metin or g.m.ad, yukseklik * 0.5, cx, cy + yukseklik * 0.18, renk, alfa, 'orta', 0.12)
        return
    k = yukseklik / img.height()
    w = img.width() * k
    p = skia.Paint(AntiAlias=True, ColorFilter=skia.ColorFilters.Blend(_argb(renk), skia.BlendMode.kSrcIn))
    p.setAlphaf(clamp(alfa))
    cv.drawImageRect(img, skia.Rect(cx - w / 2, cy - yukseklik / 2, cx + w / 2, cy + yukseklik / 2), g.ornek, p)


def _alan(W, H):
    u = min(W, H) / 1080
    ad = next((k for k, (w, h) in motor.BOYUTLAR.items() if abs(w / h - W / H) < 0.01), '16x9')
    ust, alt, yan = GUVENLI.get(ad, (0.06, 0.08, 0.06))
    return u, ust * H, H - alt * H, yan * W, W - yan * W


# ---------- TV ----------
def _tv_zemin(cv, t, W, H, g):
    """Düz marka zemini. Yumuşak radyal ışık 8 bit videoda dairesel basamaklar (banding) yapar; yazının arkası temiz kalır."""
    cv.clear(_argb(g.tz))


def _tv_metin_gir(lt, d, gecis, sira):
    """TV yazısı: sahne yerleşince sırayla belirir, sonraki geçişten önce söner. (alfa, dy oranı)"""
    p = out_cubic(prog(lt, 0.35 + 0.35 * sira, 1.4))
    c = in_out(prog(lt, d - gecis - 1.0, 0.9))
    return p * (1 - c), (1 - p) + 0.3 * c


def _tv_sahne(cv, t, lt, W, H, g, i):
    """Sahne i, yerel zaman lt (−gecis … sure). Yatayda fotoğraf paneli + yazı paneli; dikeyde üst üste."""
    import skia
    sh = g.sahneler[i]
    _, d = g.z[i]
    u = min(W, H) / 1080
    yatay = W >= H
    gecis = g.gecis
    kb = in_out(clamp((lt + gecis) / (d + gecis)))  # Ken Burns ilerlemesi
    tur = sh['tur']
    sag = i % 2 == 0  # fotoğraf paneli sırayla sağda/solda
    foto = sh.get('foto')
    if tur == 'uclu':
        foto = sh['fotolar'][0]
    yazi_alani = None
    if foto and tur != 'bilgi':
        if yatay:
            pw = W * 0.54
            px0 = W - pw if sag else 0
            rect = (px0, 0, px0 + pw, H)
            yazi_alani = (W * 0.065, W - pw - W * 0.05) if sag else (pw + W * 0.05, W - W * 0.065)
        else:
            rect = (0, 0, W, H * 0.56)
            yazi_alani = (W * 0.08, W * 0.92)
        zoom = lerp(1.04, 1.13, kb) if i % 2 else lerp(1.13, 1.04, kb)
        if g.acik_tema:  # açık tema: fotoğraf yumuşak gölgeli, köşeleri yuvarlak bir kartta
            m = 70 * u
            r = skia.Rect(rect[0] + m * (0.5 if sag else 1.0), rect[1] + m, rect[2] - m * (1.0 if sag else 0.5), rect[3] - m)
            rr = skia.RRect.MakeRectXY(r, 28 * u, 28 * u)
            cv.drawRRect(rr, skia.Paint(AntiAlias=True, Color=_argb(g.tz),
                                        ImageFilter=skia.ImageFilters.DropShadow(0, 18 * u, 40 * u, 40 * u, _argb('#3a2a10', 0.22))))
            cv.save(); cv.clipRRect(rr, doAntiAlias=True)
            foto_ciz(cv, g, foto, (r.left(), r.top(), r.right(), r.bottom()), sh.get('odak', (0.5, 0.5)), zoom, (0, lerp(0.015, -0.015, kb)),
                     logo=sh.get('logo'))
            cv.restore()
        else:
            # paneli zemine yumuşak kenarla karıştır
            cv.saveLayer(None)
            foto_ciz(cv, g, foto, rect, sh.get('odak', (0.5, 0.5)), zoom, (0, lerp(0.015, -0.015, kb)), logo=sh.get('logo'))
            if tur == 'marka':  # açık marka görseli loş mekânda parlamasın
                cv.drawRect(skia.Rect(*rect), skia.Paint(Color=_argb(g.tz, 0.22)))
            tuy = 220 * u
            if yatay:
                ic = rect[0] if sag else rect[2]
                dis = ic + (tuy if sag else -tuy)
                mask = skia.GradientShader.MakeLinear([(ic, 0), (dis, 0)], [0x00000000, 0xFF000000])
            else:
                mask = skia.GradientShader.MakeLinear([(0, rect[3]), (0, rect[3] - tuy)], [0x00000000, 0xFF000000])
            cv.drawRect(skia.Rect(*rect), skia.Paint(Shader=mask, BlendMode=skia.BlendMode.kDstIn))
            cv.restore()
    elif foto:  # bilgi sahnesi: fotoğraf tüm ekranda, çok koyu ve bulanık
        img = g.bulanik(foto, W, H)
        p = skia.Paint(); p.setAlphaf(0.0 if g.acik_tema else 0.24)
        cv.drawImage(img, 0, 0, skia.SamplingOptions(), p)

    if tur == 'bilgi':
        _tv_bilgi(cv, lt, W, H, g, sh, d, u)
        return
    # yazı paneli
    if yatay:
        x0, x1 = yazi_alani
        cx = None
        y = H * 0.30
    else:
        x0, x1 = yazi_alani
        y = H * 0.62
    genis = x1 - x0
    sira = 0
    if tur == 'marka' and not foto:  # fotoğraf varsa logo zaten görselde
        a, dy = _tv_metin_gir(lt, d, gecis, 0)
        logo_ciz(cv, g, (x0 + x1) / 2 if not yatay else x0 + 120 * u, y + 20 * u + dy * 30 * u, 210 * u, g.ty, a)
        y += 230 * u; sira = 1
    if sh.get('ust'):
        a, dy = _tv_metin_gir(lt, d, gecis, sira)
        boy = _sigdir(g.tf_govde_kalin, g.buyuk(sh['ust']), 30 * u, genis, 0.22)
        _yaz(cv, g.tf_govde_kalin, g.buyuk(sh['ust']), boy, x0, y + dy * 30 * u, g.tvv, a, aralik=0.22)
        y += 92 * u; sira += 1
    if sh.get('baslik'):
        a, dy = _tv_metin_gir(lt, d, gecis, sira)
        boy = 104 * u
        satirlar = _satirla(g.tf_baslik, sh['baslik'], boy, genis)
        if len(satirlar) > 2:
            boy = _sigdir(g.tf_baslik, sh['baslik'], boy, genis * 2); satirlar = _satirla(g.tf_baslik, sh['baslik'], boy, genis)
        for k, sat in enumerate(satirlar):
            _yaz(cv, g.tf_baslik, sat, boy, x0, y + k * boy * 1.02 + dy * 34 * u, g.ty, a)
        y += boy * 1.02 * (len(satirlar) - 1) + 46 * u
        # ince vurgu çizgisi soldan çizilir
        q = g.egri(prog(lt, 0.9 + 0.35 * sira, 1.2)) * (1 - in_out(prog(lt, d - gecis - 1.0, 0.9)))
        if q > 0:
            cv.drawRect(skia.Rect(x0, y, x0 + 120 * u * q, y + 3 * u), skia.Paint(AntiAlias=True, Color=_argb(g.tvv, q)))
        y += 72 * u; sira += 1
    if sh.get('alt'):
        a, dy = _tv_metin_gir(lt, d, gecis, sira)
        for k, sat in enumerate(_satirla(g.tf_govde, sh['alt'], 40 * u, genis)):
            _yaz(cv, g.tf_govde, sat, 40 * u, x0, y + k * 54 * u + dy * 26 * u, g.ty, a * 0.82)
    if tur != 'marka':  # küçük marka imzası
        a, _ = _tv_metin_gir(lt, d, gecis, 3)
        logo_ciz(cv, g, x0 + 30 * u, H - 112 * u, 44 * u, g.tvv, a * 0.9, isaret=True)
        _yaz(cv, g.tf_govde_kalin, g.buyuk(g.m.ad or ''), 22 * u, x0 + 76 * u, H - 104 * u, g.tvv, a * 0.9, aralik=0.28)


def _tv_bilgi(cv, lt, W, H, g, sh, d, u):
    """Ortalanmış bilgi kartı: logo, başlık, iki sütunlu satırlar (gün … saat), alt satır."""
    import skia
    gecis = g.gecis
    cx = W / 2
    satirlar = sh.get('satirlar', [])
    yatay = W >= H
    genis = min(W * 0.72, 1180 * u)
    y = H * (0.20 if yatay else 0.28)
    a, dy = _tv_metin_gir(lt, d, gecis, 0)
    logo_ciz(cv, g, cx, y + dy * 30 * u, 150 * u, g.tvv, a)
    y += 150 * u
    if sh.get('ust'):
        a, dy = _tv_metin_gir(lt, d, gecis, 0)
        _yaz(cv, g.tf_govde_kalin, g.buyuk(sh['ust']), 28 * u, cx, y + dy * 30 * u, g.tvv, a, 'orta', 0.24)
        y += 84 * u
    if sh.get('baslik'):
        a, dy = _tv_metin_gir(lt, d, gecis, 1)
        boy = _sigdir(g.tf_baslik, sh['baslik'], 92 * u, genis)
        _yaz(cv, g.tf_baslik, sh['baslik'], boy, cx, y + dy * 30 * u, g.ty, a, 'orta')
        y += 70 * u
    for k, (sol, sag) in enumerate(satirlar):
        a, dy = _tv_metin_gir(lt, d, gecis, 2 + 0.6 * k)
        y += 82 * u
        yy = y + dy * 26 * u
        boy = 46 * u
        _yaz(cv, g.tf_govde, sol, boy, cx - genis / 2 + 40 * u, yy, g.ty, a * 0.85)
        _yaz(cv, g.tf_govde_kalin, sag, boy, cx + genis / 2 - 40 * u, yy, g.ty, a, 'sag')
        if k < len(satirlar) - 1:
            cv.drawRect(skia.Rect(cx - genis / 2 + 40 * u, yy + 30 * u, cx + genis / 2 - 40 * u, yy + 31.5 * u),
                        skia.Paint(Color=_argb(g.ty, a * 0.18)))
    if sh.get('alt'):
        a, dy = _tv_metin_gir(lt, d, gecis, 2 + 0.6 * len(satirlar))
        y += 110 * u
        _yaz(cv, g.tf_govde_kalin, sh['alt'], 36 * u, cx, y + dy * 26 * u, g.tvv, a, 'orta', 0.04)


def kare_tv(cv, t, W, H, g):
    """t'nin saf fonksiyonu ve L periyotlu: kare(t) == kare(t + L)."""
    L = g.sure
    t = t % L
    _tv_zemin(cv, t, W, H, g)
    n = len(g.sahneler)
    for i, (b, d) in enumerate(g.z):
        for kayma in (0.0, L, -L):
            lt = t - b + kayma
            if -g.gecis <= lt < d:
                if lt < 0:  # bir önceki sahnenin üstüne yumuşakça biner
                    cv.saveLayerAlpha(None, int(255 * in_out(prog(lt, -g.gecis, g.gecis))))
                    _tv_sahne(cv, t, lt, W, H, g, i)
                    cv.restore()
                else:
                    _tv_sahne(cv, t, lt, W, H, g, i)


# ---------- Reel ----------
def _reel_sahne(cv, t, lt, W, H, g, i):
    import skia
    sh = g.sahneler[i]
    _, d = g.z[i]
    u, ust, alt, sol, sag = _alan(W, H)
    tur = sh['tur']
    vurus = 60 / g.bpm
    if tur == 'uclu':
        # üç fotoğraf uzun kenar boyunca bantlar halinde vuruşlarla kayarak gelir (dikeyde yatay bant:
        # fotoğraf kendi çözünürlüğüne yakın kalır, büyütülüp yumuşamaz)
        cv.clear(_argb(g.zemin))
        n = 3
        for k, f in enumerate(sh['fotolar']):
            p = g.egri(prog(lt, 0.05 + k * vurus * 0.5, 0.55))
            yon = -1 if k % 2 else 1
            if H >= W:
                rect = (0, H * k / n + 3 * u, W, H * (k + 1) / n - 3 * u); kayma = ((1 - p) * W * yon, 0)
            else:
                rect = (W * k / n + 3 * u, 0, W * (k + 1) / n - 3 * u, H); kayma = (0, (1 - p) * H * yon)
            cv.save(); cv.translate(*kayma)
            foto_ciz(cv, g, f, rect, (0.5, 0.55), lerp(1.06, 1.0, out_cubic(prog(lt, 0, d))))
            cv.restore()
        # koyu örtü + soru
        q = out_cubic(prog(lt, 0.6, 0.6))
        cv.drawPaint(skia.Paint(Color=_argb('#000000', 0.38 * q)))
        satirlar = _satirla(g.tf_baslik, sh.get('baslik', ''), 118 * u, sag - sol)
        y = H * 0.47 - (len(satirlar) - 1) * 62 * u
        for k, sat in enumerate(satirlar):
            _kelimeler(cv, g.tf_baslik, sat, 118 * u, W / 2, y + k * 124 * u, g.yazi, 0.75 + k * 0.25, lt, u, 'orta', golge=0.6)
        return
    if tur == 'marka':
        _reel_marka(cv, t, lt, W, H, g, sh, d, u, ust, alt, sol, sag)
        return
    # ürün: fotoğraf genişliğe oturur (kendi çözünürlüğünde, büyütme yok denecek kadar az), altında düz marka
    # zemini; yazılar o temiz zeminde. Fotoğrafın alt kenarı zemine yumuşakça karışır.
    f = sh['foto']
    kb = clamp(lt / d)
    img = g.resimler[f]
    if duzen(sh, img, W, H) == 'cerceve':
        _reel_cerceve(cv, lt, W, H, g, sh, kb, u, ust, alt, sol, sag)
        return
    fh = min(H * 0.78, W * img.height() / img.width())
    cv.clear(_argb(g.zemin))
    cv.saveLayer(None)
    foto_ciz(cv, g, f, (0, 0, W, fh), sh.get('odak', (0.5, 0.5)), lerp(1.0, 1.05, kb), (0, lerp(0.01, -0.01, kb)))
    tuy = 260 * u
    cv.drawRect(skia.Rect(0, fh - tuy, W, fh), skia.Paint(
        Shader=skia.GradientShader.MakeLinear([(0, fh), (0, fh - tuy)], [0x00000000, 0xFF000000]), BlendMode=skia.BlendMode.kDstIn))
    cv.restore()
    # yazılar: alt güvenli alanın üstünde, fotoğrafın altındaki düz zeminde
    y = alt - 40 * u
    if sh.get('alt'):
        q = out_cubic(prog(lt, 0.55, 0.5))
        _yaz(cv, g.tf_govde, sh['alt'], _sigdir(g.tf_govde, sh['alt'], 40 * u, sag - sol), W / 2, y + (1 - q) * 20 * u,
             g.yazi, q * 0.9, 'orta', golge=0.5)
    baslik = sh.get('baslik', '')
    boy = _sigdir(g.tf_baslik, baslik, 112 * u, sag - sol)
    _kelimeler(cv, g.tf_baslik, baslik, boy, W / 2, y - 76 * u, g.yazi, 0.18, lt, u, 'orta', golge=0.6)
    if sh.get('ust'):
        _hap(cv, lt, W, g, sh['ust'], y - 76 * u - boy - 30 * u, u)


def _hap(cv, lt, W, g, metin, yy, u):
    """Ortalı vurgu renginde hap etiket; yy yazının taban çizgisi."""
    import skia
    q = g.egri(prog(lt, 0.05, 0.45))
    s = g.buyuk(metin)
    w = _genislik(_font(g.tf_govde_kalin, 28 * u), s, 0.2)
    rect = skia.Rect(W / 2 - w / 2 - 26 * u, yy - 30 * u, W / 2 + w / 2 + 26 * u, yy + 18 * u)
    cv.save(); cv.translate(0, (1 - q) * 24 * u)
    cv.drawRRect(skia.RRect.MakeRectXY(rect, 24 * u, 24 * u), skia.Paint(AntiAlias=True, Color=_argb(g.vurgu, q)))
    _yaz(cv, g.tf_govde_kalin, s, 28 * u, W / 2, yy, g.zemin, q, 'orta', 0.2)
    cv.restore()


def duzen(sh, img, W, H):
    """Reel ürün sahnesinin düzeni. Verilmezse: dikey videoda yatay fotoğraf çerçeveye girer, çünkü genişliğe
    oturunca ekranın yarısı boş kalır; tam ekrana büyütmek ise fotoğrafı yumuşatır."""
    if sh.get('duzen'):
        return sh['duzen']
    return 'cerceve' if H > W and img.width() > img.height() * 1.15 else 'ust'


def _reel_cerceve(cv, lt, W, H, g, sh, kb, u, ust, alt, sol, sag):
    """Yatay fotoğraf dikey videoda: arkada fotoğrafın bulanık, koyulaştırılmış kopyası ekranı doldurur; fotoğrafın
    kendisi ince vurgu çerçeveli kartta kendi çözünürlüğüne yakın durur, yazılar kartın altında ortalanır."""
    import skia
    f = sh['foto']
    img = g.resimler[f]
    cv.clear(_argb(g.zemin))
    p = skia.Paint(Dither=True); p.setAlphaf(0.4)
    cv.drawImage(g.bulanik(f, W, H), 0, 0, skia.SamplingOptions(), p)
    # kart: yanlarda 56 birim pay; yazı bloğuyla birlikte güvenli alanın ortasına oturur
    kw = W - 112 * u
    kh = min(kw * img.height() / img.width(), (alt - ust) * 0.58)
    baslik = sh.get('baslik', '')
    boy = _sigdir(g.tf_baslik, baslik, 104 * u, sag - sol)
    blok = kh + (92 * u if sh.get('ust') else 0) + 40 * u + boy + (70 * u if sh.get('alt') else 0)
    ky = ust + max(0.0, (alt - ust - blok) / 2)
    q = g.egri(prog(lt, 0.0, 0.5))
    x0, y0 = (W - kw) / 2, ky + (1 - q) * 30 * u
    rect = skia.Rect(x0, y0, x0 + kw, y0 + kh)
    cv.drawRect(rect, skia.Paint(Color=_argb('#000000', 0.0), ImageFilter=skia.ImageFilters.DropShadow(
        0, 18 * u, 36 * u, 36 * u, _argb('#000000', 0.55))))
    foto_ciz(cv, g, f, (rect.left(), rect.top(), rect.right(), rect.bottom()), sh.get('odak', (0.5, 0.5)),
             lerp(1.0, 1.05, kb), (lerp(0.01, -0.01, kb), 0))
    cv.drawRect(rect.makeOutset(9 * u, 9 * u), skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                                          StrokeWidth=2 * u, Color=_argb(g.vurgu, 0.9 * q)))
    y = y0 + kh + 9 * u
    if sh.get('ust'):
        y += 92 * u
        _hap(cv, lt, W, g, sh['ust'], y, u)
    y += 40 * u + boy * 0.8
    _kelimeler(cv, g.tf_baslik, baslik, boy, W / 2, y, g.yazi, 0.18, lt, u, 'orta', golge=0.6)
    if sh.get('alt'):
        qa = out_cubic(prog(lt, 0.55, 0.5))
        y += 70 * u
        _yaz(cv, g.tf_govde, sh['alt'], _sigdir(g.tf_govde, sh['alt'], 40 * u, sag - sol), W / 2, y + (1 - qa) * 20 * u,
             g.yazi, qa * 0.9, 'orta', golge=0.5)


def _reel_marka(cv, t, lt, W, H, g, sh, d, u, ust, alt, sol, sag):
    """Kapanış kartı: marka görseli (varsa) yavaşça uzaklaşır, logo ve bilgi satırları açık kartta belirir."""
    import skia
    f = sh.get('foto')
    if f:
        # görsel yukarı kayar: logo üstte kalır, bilgi kartı altta boş alana oturur
        foto_ciz(cv, g, f, (0, 0, W, H), sh.get('odak', (0.5, 0.5)), lerp(1.06, 1.0, out_cubic(clamp(lt / d))),
                 logo=sh.get('logo'))
    else:
        cv.clear(_argb(g.acik))
        lh = 420 * u
        if g.logo is not None:  # geniş yazı logosu yanlara taşmasın
            lh = min(lh, (sag - sol) * g.logo.height() / g.logo.width())
        logo_ciz(cv, g, W / 2, H * 0.40, lh, g.logo_renk, out_cubic(prog(lt, 0.1, 0.8)))
    # bilgi kartı
    satirlar = [x for x in (sh.get('ust'), sh.get('baslik'), sh.get('alt')) if x]
    if not satirlar:
        return
    q = g.egri(prog(lt, 0.5, 0.6))
    kh = 64 * u * len(satirlar) + 64 * u
    ky = alt - kh - 10 * u
    rect = skia.Rect(sol + 10 * u, ky + (1 - q) * 40 * u, sag - 10 * u, ky + kh + (1 - q) * 40 * u)
    cv.drawRRect(skia.RRect.MakeRectXY(rect, 28 * u, 28 * u), skia.Paint(AntiAlias=True, Color=_argb(g.acik, 0.92 * q),
                                                                        ImageFilter=skia.ImageFilters.DropShadow(0, 8 * u, 24 * u, 24 * u, _argb('#000000', 0.18 * q))))
    for k, s in enumerate(satirlar):
        p = out_cubic(prog(lt, 0.75 + 0.22 * k, 0.5))
        tf = g.tf_baslik if k == 1 else g.tf_govde_kalin
        boy = _sigdir(tf, s, (60 if k == 1 else 38) * u, rect.width() - 60 * u)
        renk = g.logo_renk if k == 1 else g.koyu_yazi
        _yaz(cv, tf, s, boy, W / 2, rect.top() + 78 * u + k * 64 * u + (1 - p) * 16 * u, renk, p, 'orta')


def kare_reel(cv, t, W, H, g):
    import skia
    n = len(g.sahneler)
    i = max(k for k, (b, _) in enumerate(g.z) if b <= t or k == 0)
    b, d = g.z[i]
    lt = t - b
    gecis = g.gecis
    if i > 0 and lt < gecis:
        # itme geçişi: önceki sahne yukarı kayıp kararır, yenisi alttan gelir (vuruşa oturur)
        p = g.egri(lt / gecis)
        pb, pd = g.z[i - 1]
        cv.save(); cv.translate(0, -p * H * 0.28)
        _reel_sahne(cv, t, t - pb, W, H, g, i - 1)
        cv.drawPaint(skia.Paint(Color=_argb('#000000', 0.6 * p)))
        cv.restore()
        cv.save(); cv.translate(0, (1 - p) * H)
        _reel_sahne(cv, t, lt, W, H, g, i)
        cv.restore()
    else:
        _reel_sahne(cv, t, lt, W, H, g, i)
    # açılış ve kapanış
    if t < 0.25:
        cv.drawPaint(skia.Paint(Color=_argb('#000000', 1 - t / 0.25)))
    son = g.sure - t
    if son < 0.35:
        cv.drawPaint(skia.Paint(Color=_argb('#000000', 1 - son / 0.35)))


def kare(cv, t, W, H, g):
    (kare_tv if g.v == 'tv' else kare_reel)(cv, t, W, H, g)


# ---------- müzik ----------
def _ep(frek, d, hiz=1.0):
    """Elektrik piyano (FM): yumuşak çan tınısı, sönümlü."""
    tt = np.arange(int(d * SR)) / SR
    mod = np.sin(2 * np.pi * frek * tt) * 1.2 * np.exp(-tt * 3 * hiz)
    x = np.sin(2 * np.pi * frek * tt + mod) * np.exp(-tt * 1.1 * hiz)
    x += 0.25 * np.sin(2 * np.pi * frek * 2 * tt) * np.exp(-tt * 4 * hiz)
    a = int(0.004 * SR); x[:a] *= np.linspace(0, 1, a)
    return x


def _ped(frekler, d, a=1.2):
    tt = np.arange(int(d * SR)) / SR
    e = np.minimum(tt / a, 1.0) * np.clip((d - tt) / a, 0, 1)
    x = sum(np.sin(2 * np.pi * f * tt + i) + 0.4 * np.sin(2 * np.pi * f * 1.004 * tt + 2 * i) for i, f in enumerate(frekler))
    return motor.lp_hizli(x * e / len(frekler), 1400)


def _bas(frek, d):
    tt = np.arange(int(d * SR)) / SR
    x = np.sin(2 * np.pi * frek * tt) + 0.2 * np.sin(2 * np.pi * frek * 2 * tt)
    e = np.minimum(tt / 0.01, 1) * np.exp(-tt / (d * 0.6))
    return x * e


def _kick(d=0.4):
    tt = np.arange(int(d * SR)) / SR
    f = 45 + 80 * np.exp(-tt / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.13)


def _hat(seed, d=0.08, dec=0.025):
    e, _ = motor.zarf(d, 0.001, dec)
    x = motor.gurultu(d, seed)
    return (x - motor.lp_hizli(x, 7000)) * e


def _clap(seed):
    e, tt = motor.zarf(0.25, 0.002, 0.06)
    x = motor.gurultu(0.25, seed)
    x = motor.lp_hizli(x - motor.lp_hizli(x, 900), 5000)
    return x * e


# Am9 – Fmaj7 – Cmaj7 – G6: sıcak, çözülmeyen lounge döngüsü
AKORLAR = [(45, [57, 60, 64, 67, 71]), (41, [57, 60, 64, 65, 69]), (48, [55, 59, 64, 67, 71]), (43, [55, 59, 62, 64, 67])]
MELODI = [76, 79, 81, 84, 88, 86, 83, 81]  # A minör pentatonik çevresi


def muzik_tv(g):
    """Döngü uzunluğunda, sarmalanmış (son kuyruğu başa eklenir) → döngü noktasında kesinti yok."""
    m = motor.mtof
    L = g.sure
    olcu = 4 * 60 / g.bpm
    kuyruk = 6.0
    n = int(SR * L)
    buf = np.zeros((int(SR * (L + kuyruk)), 2))
    rng = np.random.default_rng(3)
    k = 0
    t = 0.0
    while t < L - 1e-6:
        kok, akor = AKORLAR[k % len(AKORLAR)]
        motor.ekle(buf, t, _ped([m(x) for x in akor], olcu + 1.0, 1.0), 0.16)
        for j, x in enumerate(akor[:4]):  # yumuşak arpejlenmiş akor
            motor.ekle(buf, t + j * 0.03, _ep(m(x), 3.2, 0.8), 0.07, -0.3 + 0.2 * j)
        motor.ekle(buf, t + olcu * 0.625, _ep(m(akor[2] + 12), 1.8, 1.2), 0.035, 0.4)
        motor.ekle(buf, t, _bas(m(kok), olcu * 0.48), 0.20)
        motor.ekle(buf, t + olcu * 0.5, _bas(m(kok + 7 if k % 2 else kok), olcu * 0.45), 0.13)
        for v in range(8):  # çok kısık sekizlik shaker
            motor.ekle(buf, t + v * olcu / 8, _hat(100 + k * 8 + v, 0.07, 0.02), 0.018 if v % 2 else 0.01, 0.3)
        if k % 2 == 1:  # iki ölçüde bir birkaç nota melodi
            for v in range(3):
                nota = MELODI[int(rng.integers(len(MELODI)))]
                motor.ekle(buf, t + olcu * (0.25 + 0.25 * v), _ep(m(nota), 2.2, 1.4), 0.05, -0.5 + 0.5 * v)
        t += olcu; k += 1
    out = buf[:n].copy()
    out[:int(SR * kuyruk)] += buf[n:n + int(SR * kuyruk)]
    return out


def muzik_reel(g):
    """Sakin giriş (ilk sahne), ilk geçişte ritim girer, kapanış kartında yarı tempoda çözülür."""
    m = motor.mtof
    L = g.sure
    vurus = 60 / g.bpm
    olcu = 4 * vurus
    n = int(SR * L)
    buf = np.zeros((n + SR * 4, 2))
    dusus = g.z[1][0] if len(g.z) > 1 else 0.0
    kapanis = g.z[-1][0] if g.sahneler[-1]['tur'] == 'marka' else L
    t, k = 0.0, 0
    while t < L:
        kok, akor = AKORLAR[k % len(AKORLAR)]
        if t >= kapanis - 1e-6:  # son akor: Am9 uzun
            kok, akor = AKORLAR[0]
            motor.ekle(buf, t, _ped([m(x) for x in akor], L - t + 1.0, 0.3), 0.20)
            for j, x in enumerate(akor):
                motor.ekle(buf, t + j * 0.06, _ep(m(x + 12), 3.5, 0.7), 0.06, -0.4 + 0.2 * j)
            motor.ekle(buf, t, _kick(0.8), 0.6)
            motor.ekle(buf, t, _bas(m(kok), 2.5), 0.25)
            break
        motor.ekle(buf, t, _ped([m(x) for x in akor], olcu + 0.6, 0.4), 0.12)
        for v in range(4):
            tv = t + v * vurus
            if tv >= kapanis: break
            ritim = tv >= dusus - 1e-6
            for j, x in enumerate(akor[:4]):  # akor stab'ı: her vuruşun arkasında
                motor.ekle(buf, tv + vurus * 0.5, _ep(m(x), 0.9, 2.5), 0.05 if ritim else 0.035, -0.3 + 0.2 * j)
            if ritim:
                motor.ekle(buf, tv, _kick(), 0.55)
                if v % 2: motor.ekle(buf, tv, _clap(30 + v), 0.12)
                motor.ekle(buf, tv + vurus * 0.5, _hat(50 + v), 0.05)
                motor.ekle(buf, tv + vurus * 0.75, _hat(60 + v), 0.025)
                motor.ekle(buf, tv + vurus * 0.5, _bas(m(kok), vurus * 0.45), 0.22)
            else:
                motor.ekle(buf, tv, _hat(70 + v), 0.02)
        if not (t < dusus <= t + olcu):
            pass
        t += olcu; k += 1
    # ilk geçişe yükselen hışırtı
    if dusus > 0.6:
        d = 0.9
        tt = np.arange(int(d * SR)) / SR
        r = motor.gurultu(d, 5) * (tt / d) ** 2
        motor.ekle(buf, dusus - d, motor.lp_hizli(r - motor.lp_hizli(r, 800), 6000), 0.10)
    out = buf[:n]
    f = int(0.5 * SR); out[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
    return out


def ses_uret(g, yol, is_, ses_dizini):
    """Müzik (+ varsa seslendirme, müzik konuşmanın ~8 dB altında) → hedef LUFS → wav yolu."""
    import soundfile as sf
    x = muzik_tv(g) if g.v == 'tv' else muzik_reel(g)
    n = len(x)
    satirlar = g.s.get('seslendirme', {}).get('satirlar', [])
    if satirlar:
        vo = np.zeros((n, 2)); maske = np.zeros(n)
        for s in satirlar:
            v, sr = sf.read(os.path.join(ses_dizini, s['id'] + '.wav'), always_2d=True)
            v = v if v.shape[1] == 2 else np.repeat(v, 2, axis=1)
            i = int(s['t'] * SR); v = v[: n - i]
            vo[i:i + len(v)] += v; maske[i:i + len(v)] = 1
        rms = lambda a: math.sqrt(float(np.mean(a ** 2)) + 1e-12)
        x = x * (rms(vo[maske > 0]) * 10 ** (-8 / 20) / rms(x))
        k = int(0.15 * SR)
        duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske, np.ones(k) / k, 'same'), 0, 1)
        x = x * duk[:, None] + vo
    sf.write(os.path.join(is_, 'ses.wav'), (x / max(1e-9, np.abs(x).max()) * 0.9).astype(np.float32), SR)
    hedef = ayar(g.s, 'lufs')
    if g.v == 'tv':  # döngü: başa/sona yumuşatma yok; limiter döngü sınırında da sürekli olsun diye iki tur işlenip ortası alınır
        ham, _ = sf.read(os.path.join(is_, 'ses.wav'), always_2d=True)
        sf.write(os.path.join(is_, 'ses.wav'), np.concatenate([ham, ham, ham]).astype(np.float32), SR)
        ara = motor.ses_bitir(is_, hedef)
        y, _ = sf.read(ara, always_2d=True)
        sf.write(ara, y[n:2 * n].astype(np.float32), SR)
        return ara
    return motor.ses_bitir(is_, hedef)


# ---------- üretim ----------
def seslendir(yol, cikti=None, saglayici='otomatik', ses=None):
    sys.path.insert(0, os.path.join(PLATFORM, 'ses'))
    import seslendirme
    with open(yol, encoding='utf-8') as f:
        s = json.load(f)
    if not s.get('seslendirme', {}).get('satirlar'):
        return None
    from pathlib import Path
    return seslendirme.senaryodan(s, Path(_ses_dizini(yol, s, cikti)), saglayici, ses)


def calistir(yol, cikti, boyutlar, olcek=1.0):
    g = Gorunum(yol)
    ad = g.s.get('kimlik', 'mekan')
    is_ = os.path.join(cikti, 'is'); os.makedirs(is_, exist_ok=True)
    ses = ses_uret(g, yol, is_, _ses_dizini(yol, g.s, cikti))
    ciz = lambda cv, t, W_, H_: kare(cv, t, W_, H_, g)
    W, H = motor.boyut(boyutlar[0], olcek)
    motor.kapak(ciz, os.path.join(cikti, f'{ad}-kapak.png'), W, H, g.s.get('kapak_t', g.z[min(1, len(g.z) - 1)][0] + 3.0))
    ciktilar = []
    n_kare = int(round(FPS * g.sure))
    for b in boyutlar:
        W, H = motor.boyut(b, olcek)
        sessiz = os.path.join(is_, f'sessiz-{b}.mp4')
        motor.video(ciz, sessiz, W, H, n_kare)
        hedef = os.path.join(cikti, f'{ad}-{b}.mp4')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', sessiz, '-i', ses, '-c:v', 'copy',
                        '-c:a', 'aac', '-b:a', '192k', '-t', f'{g.sure:.3f}', '-movflags', '+faststart', hedef], check=True)
        motor.kalite_kapisi(hedef)
        ciktilar.append(hedef)
        if g.v == 'tv':  # mekânda ses çoğu zaman kapalı: aynı görüntü, ses izi yok
            sessiz_hedef = os.path.join(cikti, f'{ad}-{b}-sessiz.mp4')
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', sessiz, '-c:v', 'copy', '-an',
                            '-movflags', '+faststart', sessiz_hedef], check=True)
            ciktilar.append(sessiz_hedef)
        os.remove(sessiz)
    for f in os.listdir(is_):
        if f.startswith('ses'): os.remove(os.path.join(is_, f))
    return ciktilar


def main(argv=None):
    sys.path.insert(0, os.path.join(SABLONLAR, 'stil'))
    from stil import formatlar
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    alt = ap.add_subparsers(dest='komut', required=True)
    for ad in ('denetle', 'seslendir', 'kare', 'render', 'uret'):
        p = alt.add_parser(ad)
        p.add_argument('senaryo'); p.add_argument('-o', '--cikti')
        if ad in ('seslendir', 'uret'):
            p.add_argument('--saglayici', default='otomatik'); p.add_argument('--ses')
        if ad == 'kare':
            p.add_argument('--an', type=float, nargs='+', required=True)
            p.add_argument('--format', type=lambda x: formatlar(x)[0])
        if ad in ('render', 'uret'):
            p.add_argument('--format', nargs='+', help='9:16, 16:9, 1:1, 4:5 ya da ikisi (varsayılan: senaryodaki "format")')
            p.add_argument('--olcek', type=float, default=1.0)
    a = ap.parse_args(argv)
    with open(a.senaryo, encoding='utf-8') as f:
        s = json.load(f)
    cikti = a.cikti or os.path.join(os.path.dirname(os.path.abspath(a.senaryo)), 'cikti')
    if a.komut == 'seslendir' or (a.komut == 'uret' and s.get('seslendirme')
                                  and not os.path.exists(os.path.join(_ses_dizini(a.senaryo, s, cikti), 'seslendirme.json'))):
        k = seslendir(a.senaryo, cikti, a.saglayici, a.ses)
        for x in (k or {}).get('satirlar', []):
            print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
    hata, uyari = denetle(a.senaryo, render=a.komut in ('render', 'uret'), cikti=cikti)
    for h in uyari: print(f'UYARI: {h}', file=sys.stderr)
    for h in hata: print(f'HATA: {h}', file=sys.stderr)
    if hata: return 1
    if a.komut in ('denetle', 'seslendir'):
        print(f"tamam: {s.get('kimlik', '?')} · mekan/{varyant(s)} · {zaman_cizelgesi(s)[1]:g} sn"); return 0
    try:
        boyutlar = formatlar(getattr(a, 'format', None) or s.get('format') or ('16:9' if varyant(s) == 'tv' else '9:16'))
    except ValueError as e:
        print(f'HATA: {e}', file=sys.stderr); return 1
    if a.komut == 'kare':
        g = Gorunum(a.senaryo)
        klasor = os.path.join(cikti, 'kareler'); os.makedirs(klasor, exist_ok=True)
        W, H = motor.boyut(boyutlar[0])
        for t in a.an:
            yol = os.path.join(klasor, f"{s.get('kimlik', 'mekan')}-{boyutlar[0]}-{t:05.2f}.png")
            motor.kapak(lambda cv, t_, W_, H_: kare(cv, t_, W_, H_, g), yol, W, H, t); print(yol)
        return 0
    for yol in calistir(a.senaryo, cikti, boyutlar, a.olcek):
        print(yol)
    return 0


if __name__ == '__main__':
    sys.exit(main())
