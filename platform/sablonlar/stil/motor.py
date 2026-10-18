"""Kâğıt kesik ve izometrik stillerin ortak motoru: senaryo, zaman çizelgesi, kare akışı, ses sentezi, miks, kodlama.

Senaryo, kinetik şablonla aynı `senaryo.json` dosyasıdır (platform/sablonlar/kinetik/README.md); bir video
içerik değişmeden stil değiştirebilir. Bu iki stil sahneleri kendi çizimleriyle yorumlar ve ekran yazılarını
sahnelerden çıkarır (`metin_cikar`); stile özel ince ayar `stiller.<stil>.metin` ile verilir.

Her stil modülü `from motor import *` ile bu adları alır ve şunları tanımlar:
    kare(cv, t, W, H)      -> skia tuvaline t anındaki kareyi çizer (t'nin saf fonksiyonu; W x H herhangi bir oran)
    muzik(n) / sfx(n)      -> (n, 2) float dizileri (48 kHz)
    AYAR                   -> {'kapak_t': saniye, 'sfx_db': efektlerin konuşmaya göre düzeyi}

Biçim: 10 sn, dört vuruş (kanca → bileşik büyüme → küçük/büyük karşıtlığı → çağrı). Kamera, müzik ve
efektler vuruşlara kilitlidir; bu yüzden seslendirme satırları vuruş anlarında başlamalı ve yuvasına sığmalıdır.
"""
import json, math, os, subprocess
import numpy as np

FPS, SURE, SR = 30, 10.0, 48000
BURADA = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(BURADA, 'fonts')  # elle konan statik Inter-<ağırlık>.ttf (depoya girmez)
FONT_ONBELLEK = os.environ.get('STIL_FONT_DIZINI', os.path.join(os.path.expanduser('~'), '.cache', 'studyo', 'fonts'))
# Inter (SIL OFL 1.1), değişken yazı tipi; statik ağırlıklar ilk kullanımda fontTools ile çıkarılır
INTER_URL = 'https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf'

# dört vuruş: (seslendirme başlangıcı, satırın bitmesi gereken son an)
VURUSLAR = [(0.30, 2.85), (3.15, 5.90), (6.15, 8.15), (8.35, 9.85)]
VURUS_TOLERANS = 0.12  # senaryodaki satır başlangıcı vuruş anından en çok bu kadar sapabilir
SES = [(b, f'v{i}') for i, (b, _) in enumerate(VURUSLAR)]  # yukle() kimlikleri senaryodakilerle değiştirir
SAHNE = [0.0, 3.0, 6.0, 8.0, SURE]

# ekran yazısı yuvaları: ad -> (varsayılan, azami karakter). Sınırlar yerleşimin taşmaması için.
YUVALAR = {
    'kanca': ('%1', 4),              # 1. vuruş büyük etiket          ← buyuk-sayi.sayi
    'kanca_alt': ('her gün', 14),    # 1. vuruş küçük şerit           ← kelimeler
    'sayi': ('37x', 4),              # 2. vuruş büyük sayı            ← egri: (1+oran)^gun
    'sayi_alt': ('bir yıl sonra', 16),  #                              ← egri.alt (yoksa varsayılan)
    'sayac': (365, None),            # 2. vuruş sayaç sonu            ← egri.gun
    'kucuk': ('küçük adım', 14),     # 3. vuruş                       ← karsitlik.kucuk
    'buyuk': ('büyük fark', 12),     #                                ← karsitlik.buyuk
    'cagri': ('Bugün başla.', 14),   # 4. vuruş                       ← kapanis.satirlar
}
METIN = {k: v for k, (v, _) in YUVALAR.items()}
SES_DIZINI = None
STIL_AYAR = {}  # stiller.<stil> altındaki, metin dışı stile özel ayarlar (örn. hamur: kart, marka, dipnot)
STILLER = {'kagit-kesik': 'kagit_kesik', 'izometrik': 'izometrik', 'hamur': 'hamur', 'piksel': 'piksel'}
BOYUTLAR = {'9x16': (1080, 1920), '16x9': (1920, 1080), '1x1': (1080, 1080), '4x5': (1080, 1350)}


class SenaryoHatasi(ValueError):
    pass


def yazi_tipi(agirlik=800):
    """Inter'in istenen ağırlığı (skia.Typeface). Sıra: fonts/ → önbellek → indir + örnekle → sistem yazı tipi (uyarıyla)."""
    import skia
    ad = f'Inter-{agirlik}.ttf'
    for d in (FONTS, FONT_ONBELLEK):
        if os.path.exists(os.path.join(d, ad)):
            return skia.Typeface.MakeFromFile(os.path.join(d, ad))
    try:
        import urllib.request
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
        os.makedirs(FONT_ONBELLEK, exist_ok=True)
        degisken = os.path.join(FONT_ONBELLEK, 'Inter-degisken.ttf')
        if not os.path.exists(degisken):
            urllib.request.urlretrieve(INTER_URL, degisken + '.indiriliyor')
            os.replace(degisken + '.indiriliyor', degisken)
        instantiateVariableFont(TTFont(degisken), {'wght': agirlik, 'opsz': 14}).save(os.path.join(FONT_ONBELLEK, ad))
        return skia.Typeface.MakeFromFile(os.path.join(FONT_ONBELLEK, ad))
    except Exception as e:  # ağ ya da fontTools yoksa yine çalışsın; görünüm farklı olur
        import sys
        print(f'UYARI Inter {agirlik} yüklenemedi ({e}); sistem yazı tipi kullanılıyor. '
              f'`pip install fonttools` ya da {FONTS}/{ad}', file=sys.stderr)
        return skia.Typeface('', skia.FontStyle.Bold())


def tr_buyuk(s):
    return s.replace('i', 'İ').replace('ı', 'I').upper()


def tr_kucuk(s):
    return s.replace('I', 'ı').replace('İ', 'i').lower()


def cumle(s):
    s = tr_kucuk(s.strip())
    return tr_buyuk(s[:1]) + s[1:]


def metin_cikar(s, stil):
    """Kinetik senaryonun sahnelerinden bu stillerin yazı yuvalarını çıkarır; stiller.<stil>.metin üstüne yazar."""
    m = {}
    for sh in s.get('sahneler', []):
        tur = sh.get('tur')
        if tur == 'kelimeler' and sh.get('kelimeler'):
            m['kanca_alt'] = tr_kucuk(' '.join(k['metin'] for k in sh['kelimeler']))
        elif tur == 'buyuk-sayi' and sh.get('sayi'):
            m['kanca'] = sh['sayi']
        elif tur == 'egri':
            if 'gun' in sh: m['sayac'] = int(sh['gun'])
            if 'gun' in sh and 'oran' in sh: m['sayi'] = f"{int((1 + sh['oran']) ** sh['gun'])}x"
            if sh.get('alt'): m['sayi_alt'] = sh['alt']
        elif tur == 'karsitlik':
            if sh.get('kucuk'): m['kucuk'] = tr_kucuk(sh['kucuk'])
            if sh.get('buyuk'): m['buyuk'] = tr_kucuk(sh['buyuk'])
        elif tur == 'kapanis' and sh.get('satirlar'):
            m['cagri'] = cumle(' '.join(x['metin'] for x in sh['satirlar']))
    m.update(s.get('stiller', {}).get(stil, {}).get('metin', {}))
    return m


def sureler_oku(klasor):
    k = os.path.join(klasor, 'seslendirme.json')
    if not os.path.exists(k):
        return {}
    with open(k, encoding='utf-8') as f:
        return {x['id']: x['sure'] for x in json.load(f)['satirlar']}


def denetle(s, stil, ses_dizini, render=True):
    """(hatalar, uyarilar). HATA üretimi durdurur. render=False: seslendirme dosyaları henüz aranmaz."""
    hata, uyari = [], []
    if stil not in STILLER:
        hata.append(f'stil: "{stil}" bilinmiyor (geçerli: {", ".join(STILLER)}; kinetik için platform/sablonlar/kinetik)')
    if s.get('sure', SURE) != SURE:
        hata.append(f'sure: bu stiller {SURE:g} sn sabit biçimde (senaryo: {s.get("sure")})')
    m = metin_cikar(s, stil)
    for k in m:
        if k not in YUVALAR: hata.append(f"stiller.{stil}.metin.{k}: tanımsız yuva (geçerli: {', '.join(YUVALAR)})")
    for k, (_, azami) in YUVALAR.items():
        v = m.get(k)
        if v is None: continue
        if k == 'sayac':
            if not isinstance(v, int) or v < 1: hata.append('sayac (egri.gun): pozitif tam sayı olmalı')
        elif not isinstance(v, str) or not v.strip(): hata.append(f'{k}: boş')
        elif len(v) > azami: hata.append(f'{k}: "{v}" {len(v)} karakter, bu stilde en çok {azami}')
    satirlar = s.get('seslendirme', {}).get('satirlar', [])
    if len(satirlar) != len(VURUSLAR):
        hata.append(f'seslendirme.satirlar: {len(VURUSLAR)} satır gerekli (her vuruşa bir), {len(satirlar)} var')
        return hata, uyari
    sureler = sureler_oku(ses_dizini)
    for i, (x, (bas, son)) in enumerate(zip(satirlar, VURUSLAR)):
        if abs(x.get('t', bas) - bas) > VURUS_TOLERANS:
            hata.append(f'{x["id"]}: t={x.get("t")} ama {i + 1}. vuruş {bas} sn\'de (bu stilde vuruş anları sabit)')
        d = sureler.get(x['id'])
        if d is None:
            if render: hata.append(f'{x["id"]}: seslendirme yok ({ses_dizini}); önce `seslendir` çalıştırın')
            continue
        if not os.path.exists(os.path.join(ses_dizini, x['id'] + '.wav')): hata.append(f'{x["id"]}.wav yok')
        if d > son - bas:
            hata.append(f'{x["id"]}: {d:.2f} sn, {i + 1}. vuruşun yuvası {son - bas:.2f} sn; satırı kısaltın')
        hiz = len(x.get('metin', '').split()) / max(d, 1e-6)
        if hiz > 4.0: uyari.append(f'{x["id"]}: {hiz:.1f} sözcük/sn, hızlı')
    return hata, uyari


def kur(s, stil, ses_dizini):
    """Motor durumunu (METIN, STIL_AYAR, SES, SES_DIZINI) senaryoya göre yerinde kurar."""
    global SES_DIZINI
    METIN.clear(); METIN.update({k: v for k, (v, _) in YUVALAR.items()}); METIN.update(metin_cikar(s, stil))
    STIL_AYAR.clear(); STIL_AYAR.update({k: v for k, v in s.get('stiller', {}).get(stil, {}).items() if k != 'metin'})
    SES[:] = [(b, x['id']) for (b, _), x in zip(VURUSLAR, s['seslendirme']['satirlar'])]
    SES_DIZINI = str(ses_dizini)


# ---------- yardımcılar ----------
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, p): return a + (b - a) * p
def prog(t, t0, d): return clamp((t - t0) / d)
def out_cubic(p): return 1 - (1 - p) ** 3
def in_cubic(p): return p ** 3
def in_out_cubic(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_back(p, s=1.9): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2
def out_elastic(p):
    if p <= 0: return 0
    if p >= 1: return 1
    return 2 ** (-10 * p) * math.sin((p * 10 - .75) * (2 * math.pi) / 3) + 1


# ---------- ses sentezi yardımcıları ----------
def mtof(m): return 440 * 2 ** ((m - 69) / 12)


def ekle(buf, t0, x, gain=1.0, pan=0.0):
    n = len(buf); i = int(t0 * SR)
    if i >= n or i < 0: return
    x = x[: n - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414


def zarf(d, a=0.003, dec=None):
    tt = np.arange(int(d * SR)) / SR
    e = np.minimum(tt / a, 1.0)
    return e * (np.exp(-tt / dec) if dec else 1.0), tt


def lp(x, cut):  # tek kutuplu alçak geçiren
    a = math.exp(-2 * math.pi * cut / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y


def lp_hizli(x, cut):  # tek kutuplu, vektörel (scipy yoksa döngü)
    try:
        from scipy.signal import lfilter
        a = math.exp(-2 * math.pi * cut / SR)
        return lfilter([1 - a], [1, -a], x)
    except ImportError:
        return lp(x, cut)


def gurultu(d, seed=0):
    return np.random.default_rng(seed).standard_normal(int(d * SR))


# ---------- miks ----------
def _oku(yol):
    import soundfile as sf
    x, sr = sf.read(yol, always_2d=True)
    if sr != SR:
        raise SenaryoHatasi(f'{yol}: {sr} Hz, {SR} Hz bekleniyor (platform/ses/seslendirme.py 48 kHz üretir)')
    return x if x.shape[1] == 2 else np.repeat(x, 2, axis=1)


def miks(cikti, muzik, sfx, muzik_alti_db=8.0, sfx_db=-4.0):
    """Seslendirme + müzik (konuşmanın ~8 dB altında, konuşurken ek kısma) + efektler -> ses.wav"""
    import soundfile as sf
    n = int(SR * SURE)
    vo = np.zeros((n, 2)); maske = np.zeros(n)
    for t0, vid in SES:
        x = _oku(os.path.join(SES_DIZINI, vid + '.wav'))
        i = int(t0 * SR); x = x[: n - i]
        vo[i:i + len(x)] += x; maske[i:i + len(x)] = 1.0
    rms = lambda a: math.sqrt(float(np.mean(a ** 2)) + 1e-12)
    vo_rms = rms(vo[maske > 0])
    m = muzik * (vo_rms * 10 ** (-muzik_alti_db / 20) / rms(muzik))
    # konuşurken 3 dB ek kısma, 120 ms yumuşak geçiş
    k = int(0.12 * SR); pen = np.ones(k) / k
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske, pen, 'same'), 0, 1)
    m *= duk[:, None]
    s = sfx * (vo_rms * 10 ** (sfx_db / 20) / max(rms(sfx[np.abs(sfx).sum(1) > 1e-6]) if np.any(sfx) else 1, 1e-9))
    karisim = vo + m + s
    f = int(0.02 * SR); karisim[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.25 * SR); karisim[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(os.path.join(cikti, 'ses.wav'), (karisim / max(1e-9, np.abs(karisim).max()) * 0.9).astype(np.float32), SR)


def _lufs(yol):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', yol, '-af', 'lowpass=f=16000:poles=2,ebur128=framelog=quiet', '-f', 'null', '-'],
                       capture_output=True, text=True)
    satir = [s for s in r.stderr.splitlines() if s.strip().startswith('I:')][-1]
    return float(satir.split()[1])


def ses_bitir(cikti, hedef=-14.0):
    """-14 LUFS; limitlemeden önce 16 kHz alçak geçiren (yoksa AAC sonrası gerçek tepe taşar)."""
    gir = os.path.join(cikti, 'ses.wav'); ara = os.path.join(cikti, 'ses_14.wav')
    kazanc = hedef - _lufs(gir)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', gir, '-af',
                    f'lowpass=f=16000:poles=2,volume={kazanc:.2f}dB,alimiter=limit=0.84:level=false', '-ar', str(SR), ara], check=True)
    return ara


# ---------- görüntü ----------
def video(kare, yol, W, H, n_kare=None):
    import skia
    surf = skia.Surface(W, H)
    # skia'nın yerel düzeni çoğu makinede BGRA; ffmpeg'e doğru bildir (yoksa kırmızı/mavi yer değiştirir)
    pf = 'bgra' if surf.imageInfo().colorType() == skia.kBGRA_8888_ColorType else 'rgba'
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', pf, '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', yol],
                          stdin=subprocess.PIPE)
    for i in range(n_kare or int(FPS * SURE)):
        with surf as cv:
            cv.clear(0xFF000000)
            kare(cv, i / FPS, W, H)
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError(f'ffmpeg kodlaması başarısız: {yol}')


def kapak(kare, yol, W, H, t):
    import skia
    surf = skia.Surface(W, H)
    with surf as cv:
        kare(cv, t, W, H)
    surf.makeImageSnapshot().save(yol, skia.kPNG)


def boyut(ad, olcek=1.0):
    W, H = BOYUTLAR[ad]
    return int(W * olcek) // 2 * 2, int(H * olcek) // 2 * 2  # libx264 çift boyut ister


def calistir(ad, stil, cikti, boyutlar=('9x16', '16x9'), olcek=1.0):
    """stil: kare/muzik/sfx/AYAR taşıyan modül. Çıktı: <ad>-<boyut>.mp4 ve <ad>-kapak.png; ara dosyalar cikti/is/"""
    is_ = os.path.join(cikti, 'is')
    os.makedirs(is_, exist_ok=True)
    n = int(SR * SURE)
    ayar = getattr(stil, 'AYAR', {})
    miks(is_, stil.muzik(n), stil.sfx(n), sfx_db=ayar.get('sfx_db', -4.0))
    ses = ses_bitir(is_)
    W, H = boyut(boyutlar[0], olcek)
    kapak(stil.kare, os.path.join(cikti, f'{ad}-kapak.png'), W, H, ayar.get('kapak_t', 6.9))
    ciktilar = []
    for b in boyutlar:
        W, H = boyut(b, olcek)
        sessiz = os.path.join(is_, f'sessiz-{b}.mp4')
        video(stil.kare, sessiz, W, H)
        hedef = os.path.join(cikti, f'{ad}-{b}.mp4')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', sessiz, '-i', ses, '-c:v', 'copy',
                        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', hedef], check=True)
        os.remove(sessiz)
        ciktilar.append(hedef)
    for f in ('ses.wav', 'ses_14.wav'):
        os.remove(os.path.join(is_, f))
    return ciktilar
