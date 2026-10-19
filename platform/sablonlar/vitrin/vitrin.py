"""3D ürün vitrini: ürün stüdyo ışığında döner, özellikleri sırayla belirir, marka ve çağrıyla biter (6–20 sn).

    python3 platform/sablonlar/vitrin/vitrin.py denetle   vitrin.json
    python3 platform/sablonlar/vitrin/vitrin.py kare      vitrin.json --an 2.5 9.8 [--format 16:9]
    python3 platform/sablonlar/vitrin/vitrin.py render    vitrin.json [--format 9:16 | 16:9 | 1:1 | 4:5 | ikisi] [--olcek 0.5]
    python3 platform/sablonlar/vitrin/vitrin.py uret      vitrin.json   # seslendirme satırı varsa ve yoksa üretir, sonra render
`stil.py <komut> vitrin.json --stil urun-vitrini` aynı komutlara iletilir.

Görüntü three.js ile başsız Chromium'da çizilir (render.mjs), müzik ve efektler numpy ile sentezlenir; ücretli servis yok.
Renkler marka.json'dan gelir; ürün kodla kurulur (`urun.tur`: paket, kutu, kitap) ya da `urun.model` ile glTF/GLB dosyasından yüklenir.
Zamanlar müzik ızgarasına oturtulur: giriş → her özellik bir bölüm → final (logo + çağrı).
"""
from __future__ import annotations

import argparse, json, math, os, shutil, subprocess, sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
KOK = BURADA.parents[2]
sys.path.insert(0, str(BURADA.parent / 'stil'))
sys.path.insert(0, str(BURADA.parents[1] / 'marka'))
import motor  # noqa: E402  (ses sentezi yardımcıları, miks ölçümü, -14 LUFS bitiş, Inter adresi)
import marka as marka_mod  # noqa: E402

FPS, SR = 30, motor.SR
BOYUTLAR = motor.BOYUTLAR
VARSAYILAN_FORMAT = ['9x16']
URUN_TURLERI = ('paket', 'kutu', 'kitap')
ODAKLAR = ('on', 'ust', 'yan', 'alt', 'ic')  # ic: yalnız kitap (kapak açılır, sayfalar görünür)
KAPAK_UZANTI = ('.png', '.jpg', '.jpeg', '.webp')
SUSLER = (None, 'kahve-cekirdegi')
# yazı sınırları (karakter): yerleşim taşmasın
SINIR = {'giris': 24, 'ozellik': 18, 'ozellik_alt': 32, 'logo': 18, 'cagri': 18, 'final_alt': 28, 'etiket': 10, 'urun_ust': 16, 'urun_alt': 26}
EN_AZ_BOLUM = 1.4  # bir özelliğin ekranda kalacağı en kısa süre (sn)


class SenaryoHatasi(ValueError):
    pass


def formatlar(secim):
    """stil.py ile aynı: '9:16' / '16x9' / 'ikisi' (ya da liste) → ['9x16', ...]"""
    if not secim:
        return list(VARSAYILAN_FORMAT)
    cikti = []
    for x in [secim] if isinstance(secim, str) else secim:
        x = str(x).strip().lower().replace(':', 'x')
        for f in (['9x16', '16x9'] if x in ('ikisi', 'both', 'hepsi') else [x]):
            if f not in BOYUTLAR:
                raise ValueError(f'tanımsız format: {x} (9:16, 16:9, 1:1, 4:5 ya da ikisi)')
            if f not in cikti:
                cikti.append(f)
    return cikti


def yol_coz(deger: str, senaryo: Path) -> Path:
    """proje.json kuralı: yollar depo köküne göre; yoksa senaryonun klasörüne göre."""
    p = Path(deger)
    if p.is_absolute():
        return p
    for aday in (KOK / p, senaryo.parent / p):
        if aday.exists():
            return aday
    return KOK / p


# ---------- zamanlama ----------
def zamanla(s: dict) -> dict:
    """giriş, özellik bölümleri ve final; hepsi vuruşa (60/tempo) oturtulur."""
    S = float(s.get('sure', 12))
    vur = 60.0 / float(s.get('muzik', {}).get('tempo', 96))
    snap = lambda t: round(t / vur) * vur
    oz = s.get('ozellikler', [])
    giris = snap(min(1.9, S * 0.2))
    final = snap(S - min(3.6, S * 0.42))
    bolum = (final - giris) / max(1, len(oz))
    anlar = [snap(giris + i * bolum) for i in range(len(oz))] + [final]
    return {'sure': S, 'vurus': vur, 'giris_son': giris, 'final': final, 'bolum': bolum,
            'ozellikler': [{'bas': anlar[i], 'son': anlar[i + 1]} for i in range(len(oz))]}


def ses_satirlari(s: dict, z: dict) -> list[dict]:
    """seslendirme satırları ve başlangıçları ("t": saniye ya da "final"; yoksa finalden hemen sonra)."""
    cikti = []
    for x in s.get('seslendirme', {}).get('satirlar', []):
        t = x.get('t', 'final')
        cikti.append({**x, 't': z['final'] + 0.35 if t == 'final' else float(t)})
    return cikti


def sureler_oku(klasor: Path) -> dict:
    k = klasor / 'seslendirme.json'
    if not k.exists():
        return {}
    return {x['id']: x['sure'] for x in json.loads(k.read_text(encoding='utf-8'))['satirlar']}


# ---------- denetim ----------
def denetle(s: dict, senaryo: Path, ses_dizini: Path, render=True):
    """(hatalar, uyarilar, marka). HATA üretimi durdurur."""
    hata, uyari = [], []
    S = s.get('sure', 12)
    if not isinstance(S, (int, float)) or not 6 <= S <= 20:
        hata.append(f'sure: 6–20 sn olmalı (senaryo: {S})')
        return hata, uyari, None
    tempo = s.get('muzik', {}).get('tempo', 96)
    if not 70 <= tempo <= 140:
        hata.append(f'muzik.tempo: 70–140 olmalı ({tempo})')
    m = None
    if not s.get('marka'):
        hata.append('marka: marka.json yolu gerekli (renkler ve logo buradan gelir)')
    else:
        m, bulgular = marka_mod.yukle(yol_coz(s['marka'], senaryo))
        for b in bulgular:
            (hata if b.seviye == marka_mod.HATA else uyari).append(f'marka: {b.yer}: {b.mesaj}')
        if m:
            for ad in ('ana', 'ana-ustu', 'vurgu', 'vurgu-ustu'):
                if ad not in m.renk:
                    hata.append(f'marka: "{ad}" rengi gerekli (sahne ve yazılar bu dört renkle kurulur)')
    u = s.get('urun', {})
    if u.get('model'):
        mp = yol_coz(u['model'], senaryo)
        if not mp.exists():
            hata.append(f'urun.model: {u["model"]} yok')
        elif mp.suffix.lower() not in ('.glb', '.gltf'):
            hata.append(f'urun.model: glTF (.glb/.gltf) bekleniyor ({mp.suffix})')
    elif u.get('tur', 'paket') not in URUN_TURLERI:
        hata.append(f'urun.tur: "{u.get("tur")}" tanımsız ({", ".join(URUN_TURLERI)}) ya da urun.model verin')
    kitap = not u.get('model') and u.get('tur') == 'kitap'
    if u.get('kapak'):
        kp = yol_coz(u['kapak'], senaryo)
        if not kitap:
            hata.append('urun.kapak: yalnız urun.tur "kitap" ile kullanılır')
        elif not kp.exists():
            hata.append(f'urun.kapak: {u["kapak"]} yok')
        elif kp.suffix.lower() not in KAPAK_UZANTI:
            hata.append(f'urun.kapak: görsel bekleniyor ({", ".join(KAPAK_UZANTI)})')
        else:
            uyari.extend(kapak_uyarisi(kp))
    if u.get('sus') not in SUSLER:
        hata.append(f'urun.sus: "{u.get("sus")}" tanımsız (kahve-cekirdegi ya da boş)')
    if not u.get('model') and not (kitap and u.get('kapak')):
        etiket = u.get('etiket') or (m.logo_metin if m else '')
        if not etiket:
            hata.append('urun.etiket: paket üstündeki ad gerekli (yoksa marka logo.metin)')
        sinir(hata, 'urun.etiket', etiket, SINIR['etiket'])
        sinir(hata, 'urun.ust', u.get('ust'), SINIR['urun_ust'])
        sinir(hata, 'urun.alt', u.get('alt'), SINIR['urun_alt'])
    oz = s.get('ozellikler', [])
    if len(oz) > 4:
        hata.append(f'ozellikler: en çok 4 ({len(oz)} var); az yazı kuralı')
    for i, o in enumerate(oz):
        if not str(o.get('metin', '')).strip():
            hata.append(f'ozellikler[{i}].metin: boş')
        sinir(hata, f'ozellikler[{i}].metin', o.get('metin'), SINIR['ozellik'])
        sinir(hata, f'ozellikler[{i}].alt', o.get('alt'), SINIR['ozellik_alt'])
        if o.get('odak', 'on') not in ODAKLAR:
            hata.append(f'ozellikler[{i}].odak: "{o.get("odak")}" tanımsız ({", ".join(ODAKLAR)})')
        elif o.get('odak') == 'ic' and not kitap:
            hata.append(f'ozellikler[{i}].odak: "ic" yalnız urun.tur "kitap" ile (kapak açılır)')
    sinir(hata, 'giris', s.get('giris'), SINIR['giris'])
    z = zamanla(s)
    if oz and z['bolum'] < EN_AZ_BOLUM:
        hata.append(f'{len(oz)} özellik için süre kısa: bölüm {z["bolum"]:.2f} sn, en az {EN_AZ_BOLUM} sn; süreyi artırın ya da özellik çıkarın')
    f = s.get('final', {})
    sinir(hata, 'final.logo', f.get('logo') or (m.logo_metin or m.ad if m else None), SINIR['logo'])
    sinir(hata, 'final.cagri', f.get('cagri'), SINIR['cagri'])
    sinir(hata, 'final.alt', f.get('alt'), SINIR['final_alt'])
    sureler = sureler_oku(ses_dizini)
    for x in ses_satirlari(s, z):
        d = sureler.get(x['id'])
        if d is None:
            if render: hata.append(f'{x["id"]}: seslendirme yok ({ses_dizini}); önce `seslendir` çalıştırın')
            continue
        if x['t'] + d > z['sure'] - 0.2:
            hata.append(f'{x["id"]}: {x["t"]:.2f}+{d:.2f} sn, video {z["sure"]:g} sn; satırı kısaltın ya da erken başlatın')
    if m:
        for x in s.get('seslendirme', {}).get('satirlar', []) + oz + [f]:
            for alan in ('metin', 'alt', 'cagri'):
                for yasak in m.yasak:
                    if yasak.lower() in str(x.get(alan, '')).lower():
                        hata.append(f'marka yasağı: "{yasak}" geçiyor ({x.get(alan)})')
    return hata, uyari, m


def kapak_uyarisi(yol: Path) -> list[str]:
    """Kapak görseli küçükse ekranda yumuşak görünür: 9:16'da kitap kapağı ~900 px boya çıkar."""
    try:
        from PIL import Image
        with Image.open(yol) as im:
            w, h = im.size
    except Exception:  # PIL yoksa ya da okunamıyorsa denetim render'a bırakılır
        return []
    return [f'urun.kapak: {w}x{h} px küçük; en az 1000 px boy önerilir (yoksa kapak yumuşak görünür)'] if h < 1000 else []


def sinir(hata, ad, deger, azami):
    if deger is not None and len(str(deger)) > azami:
        hata.append(f'{ad}: "{deger}" {len(str(deger))} karakter, en çok {azami}')


# ---------- yazı tipi ----------
def font_yolu(agirlik: int) -> Path:
    """Inter (SIL OFL 1.1) statik ağırlık: stil şablonunun klasörü/önbelleği, yoksa indir + fontTools ile örnekle."""
    ad = f'Inter-{agirlik}.ttf'
    for d in (Path(motor.FONTS), Path(motor.FONT_ONBELLEK)):
        if (d / ad).exists():
            return d / ad
    import urllib.request
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    on = Path(motor.FONT_ONBELLEK); on.mkdir(parents=True, exist_ok=True)
    degisken = on / 'Inter-degisken.ttf'
    if not degisken.exists():
        urllib.request.urlretrieve(motor.INTER_URL, str(degisken) + '.indiriliyor')
        os.replace(str(degisken) + '.indiriliyor', degisken)
    instantiateVariableFont(TTFont(degisken), {'wght': agirlik, 'opsz': 32}).save(on / ad)
    return on / ad


# ---------- sahne ayarı ----------
def ayar(s: dict, senaryo: Path, m, W: int, H: int) -> dict:
    z = zamanla(s)
    u, f = dict(s.get('urun', {})), s.get('final', {})
    dosyalar = {'/font/Inter-800.ttf': str(font_yolu(800)), '/font/Inter-500.ttf': str(font_yolu(500))}
    model = None
    if u.get('model'):
        mp = yol_coz(u['model'], senaryo)
        model = f'/model/{mp.name}'
        dosyalar[model] = str(mp)
    kapak = None
    if u.get('kapak'):
        kp = yol_coz(u['kapak'], senaryo)
        kapak = f'/kapak/kapak{kp.suffix.lower()}'
        dosyalar[kapak] = str(kp)
    r = m.renk
    return {
        'W': W, 'H': H, 'fps': FPS, 'sure': z['sure'], 'giris_son': z['giris_son'],
        'renk': {'ana': r['ana'], 'anaUstu': r['ana-ustu'], 'vurgu': r['vurgu'], 'vurguUstu': r['vurgu-ustu'],
                 'isik': r.get('isik.sicak', r['vurgu']), 'zemin': r['zemin'], 'metin': r['metin']},
        'urun': {'tur': u.get('tur', 'paket'), 'model': model, 'model_boy': u.get('model_boy'),
                 'etiket': u.get('etiket') or m.logo_metin or m.ad, 'ust': u.get('ust'), 'alt': u.get('alt'),
                 'agirlik': u.get('agirlik'), 'govde': u.get('govde'), 'sus': u.get('sus'), 'kapak': kapak,
                 'sayfa': u.get('sayfa')},
        'giris': s.get('giris'),
        'ozellikler': [{'metin': o['metin'], 'alt': o.get('alt'), 'odak': o.get('odak', 'on'), **zz}
                       for o, zz in zip(s.get('ozellikler', []), z['ozellikler'])],
        'final': {'bas': z['final'], 'logo': f.get('logo') or m.logo_metin or m.ad, 'cagri': f.get('cagri'), 'alt': f.get('alt')},
        'fontlar': {'800': '/font/Inter-800.ttf', '500': '/font/Inter-500.ttf'},
        'dosyalar': dosyalar,
    }


def node_hazirla():
    if not (BURADA / 'node_modules' / 'three').exists() or not (BURADA / 'node_modules' / 'playwright').exists():
        env = {**os.environ, 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD': '1'}
        subprocess.run(['npm', 'install', '--no-audit', '--no-fund', '--silent'], cwd=BURADA, check=True, env=env)


def sahne_calistir(ayar_d: dict, is_: Path, kip: str, cikti: Path, anlar=()):
    node_hazirla()
    is_.mkdir(parents=True, exist_ok=True)
    ay = is_ / f'ayar-{ayar_d["W"]}x{ayar_d["H"]}.json'
    ay.write_text(json.dumps(ayar_d, ensure_ascii=False), encoding='utf-8')
    subprocess.run(['node', str(BURADA / 'render.mjs'), str(ay), kip, str(cikti), *map(str, anlar)], check=True)


# ---------- müzik ve efektler ----------
AKOR = [[50, 57, 61, 64, 66], [47, 54, 57, 62, 66], [43, 50, 54, 59, 62], [45, 52, 57, 61, 64]]  # Dmaj9 Bm7(11) Gmaj7 A6


def muzik(n: int, z: dict):
    import numpy as np
    from motor import ekle, zarf, mtof, gurultu, lp_hizli
    buf = np.zeros((n, 2)); S, vur = z['sure'], z['vurus']; olcu = vur * 4
    gs, fin = z['giris_son'], z['final']
    def guc(t):  # dinamik: sakin giriş → özelliklerde dolgun → finalde zirve, sonra iner
        return 0.45 + 0.4 * min(1, max(0, (t - gs) / 1.0)) + 0.25 * math.exp(-max(0, t - fin) * 1.2) * (t >= fin)
    # pad: her ölçüde bir akor, yumuşak giriş/çıkış
    k = 0; t = 0.0
    while t < S:
        akor = AKOR[k % 4]; d = min(olcu + 0.6, S - t + 0.4)
        e, tt = zarf(d, a=0.5); e = e * np.minimum(1, (d - tt) / 0.6)
        x = sum(np.sin(2 * math.pi * mtof(m) * tt * (1 + 0.0015 * j) + j) * (0.5 if m < 52 else 0.32)
                for j, m in enumerate(akor)) * e
        x += 0.12 * sum(np.sin(4 * math.pi * mtof(m) * tt) for m in akor[2:]) * e  # biraz parlaklık
        ekle(buf, t, x * 0.16 * guc(t), 0.25 if k % 2 else -0.25)
        k += 1; t += olcu
    # elektrik piyano (FM) vuruşları + bas: girişten sonra
    t = gs; i = 0
    while t < S - 0.3:
        akor = AKOR[int(t / olcu) % 4]
        for vurus_ici in (0, 1.5):
            t0 = t + vurus_ici * vur
            if t0 >= S - 0.3 or (fin - 0.2 < t0 < fin): continue
            d = 1.4; e, tt = zarf(d, a=0.004, dec=0.45)
            for m in akor[2:]:
                fm = mtof(m + 12)
                x = np.sin(2 * math.pi * fm * tt + 1.6 * np.exp(-tt * 6) * np.sin(2 * math.pi * fm * tt)) * e
                ekle(buf, t0, x * 0.07 * guc(t0), 0.3 * math.sin(m))
        e, tt = zarf(0.9, a=0.01, dec=0.35)
        b = np.sin(2 * math.pi * mtof(akor[0] - 12) * tt) + 0.25 * np.sin(4 * math.pi * mtof(akor[0] - 12) * tt)
        ekle(buf, t, b * e * 0.22 * guc(t)); ekle(buf, t + 2 * vur, b * e * 0.16 * guc(t))
        t += olcu; i += 1
    # davul: yumuşak kick (1 ve 3), hi-hat (ara vuruşlar) özelliklerde
    t = gs
    while t < fin - 0.05:
        j = round((t - gs) / vur)
        if j % 2 == 0:
            d = 0.35; tt = np.arange(int(d * SR)) / SR
            f = 45 + 75 * np.exp(-tt * 30); x = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)
            ekle(buf, t, x * 0.32)
        if z['ozellikler'] and t >= z['ozellikler'][0]['bas'] - 0.01:
            h = gurultu(0.06, seed=j); h = h - lp_hizli(h, 6000); h *= np.exp(-np.arange(len(h)) / SR * 60)
            ekle(buf, t + vur / 2, h * 0.05, 0.4)
        t += vur
    # final: son akor uzun ve parlak
    d = S - fin + 0.2; e, tt = zarf(d, a=0.02, dec=2.2)
    for j, m in enumerate(AKOR[0] + [74, 78]):
        ekle(buf, fin, np.sin(2 * math.pi * mtof(m) * tt + j) * e * (0.1 if m > 70 else 0.08), (j - 3) * 0.12)
    return buf


def sfx(n: int, z: dict):
    import numpy as np
    from motor import ekle, mtof, gurultu, lp_hizli
    buf = np.zeros((n, 2)); fin, gs = z['final'], z['giris_son']
    def nefes(t0, d, cut0, cut1, g, seed, yon=1):  # süzgeci açılan/kapanan gürültü: süpürme, yükseliş
        x = gurultu(d, seed); tt = np.arange(len(x)) / SR; p = tt / d
        parca = 8; out = np.zeros_like(x)
        for k in range(parca):  # süzgeç frekansını parçalar halinde değiştir
            a, b = int(len(x) * k / parca), int(len(x) * (k + 1) / parca)
            out[a:b] = lp_hizli(x, cut0 + (cut1 - cut0) * (k / parca))[a:b]
        e = np.sin(np.pi * p) ** 1.5 if yon == 0 else p ** 2
        ekle(buf, t0, out * e * g, 0)
    nefes(0.05, gs * 0.95, 300, 2600, 0.5, 1, yon=0)               # giriş: ışık açılırken süpürme
    tt = np.arange(int(1.6 * SR)) / SR                              # giriş: derin alt dalga
    ekle(buf, 0.1, np.sin(2 * math.pi * 41 * tt) * np.sin(np.pi * np.minimum(tt / 1.6, 1)) * 0.5)
    for i, o in enumerate(z['ozellikler']):                         # her özellik: zil
        tt = np.arange(int(1.2 * SR)) / SR; f = mtof([81, 83, 86, 88][i % 4])
        x = (np.sin(2 * math.pi * f * tt) + 0.35 * np.sin(2 * math.pi * f * 2.76 * tt) * np.exp(-tt * 6)) * np.exp(-tt * 3.5)
        ekle(buf, o['bas'], x * 0.5, (-0.3, 0.3)[i % 2])
    nefes(fin - 1.2, 1.2, 400, 5000, 0.35, 2, yon=1)                 # finale yükseliş
    tt = np.arange(int(1.2 * SR)) / SR                              # final vuruşu
    f = 40 + 60 * np.exp(-tt * 18)
    ekle(buf, fin, np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-tt * 3) * 0.9)
    return buf


def miks(is_: Path, m, e, satirlar, ses_dizini: Path, sure: float, muzik_alti_db=9.0, sfx_db=-5.0):
    """Müzik + efektler (+ varsa seslendirme, müziği altında kısar) → is_/ses.wav"""
    import numpy as np, soundfile as sf
    n = len(m); vo = np.zeros((n, 2)); maske = np.zeros(n)
    for x in satirlar:
        v, sr = sf.read(ses_dizini / f'{x["id"]}.wav', always_2d=True)
        if sr != SR: raise SenaryoHatasi(f'{x["id"]}.wav: {sr} Hz, {SR} Hz bekleniyor')
        v = v if v.shape[1] == 2 else np.repeat(v, 2, axis=1)
        i = int(x['t'] * SR); v = v[: n - i]; vo[i:i + len(v)] += v; maske[i:i + len(v)] = 1
    rms = lambda a: math.sqrt(float(np.mean(a ** 2)) + 1e-12)
    if maske.any():
        ref = rms(vo[maske > 0]); m = m * (ref * 10 ** (-muzik_alti_db / 20) / rms(m))
        k = int(0.15 * SR); duk = 1 - (1 - 10 ** (-4 / 20)) * np.clip(np.convolve(maske, np.ones(k) / k, 'same'), 0, 1)
        m = m * duk[:, None]
    else:
        ref = rms(m) * 10 ** (muzik_alti_db / 20)
    e = e * (ref * 10 ** (sfx_db / 20) / max(rms(e[np.abs(e).sum(1) > 1e-6]), 1e-9))
    k = vo + m + e
    f = int(0.02 * SR); k[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.3 * SR); k[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(is_ / 'ses.wav', (k / max(1e-9, np.abs(k).max()) * 0.9).astype(np.float32), SR)


# ---------- komutlar ----------
def render(s, senaryo: Path, m, cikti: Path, boyutlar, olcek=1.0) -> list[Path]:
    z = zamanla(s); is_ = cikti / 'is'; is_.mkdir(parents=True, exist_ok=True)
    ses_dizini = cikti / 'seslendirme'
    n = int(SR * z['sure'])
    miks(is_, muzik(n, z), sfx(n, z), ses_satirlari(s, z), ses_dizini, z['sure'])
    ses = Path(motor.ses_bitir(str(is_)))
    ad = f"{s.get('kimlik', 'vitrin')}-urun-vitrini"
    ciktilar = []
    for i, b in enumerate(boyutlar):
        W, H = motor.boyut(b, olcek)
        a = ayar(s, senaryo, m, W, H)
        if i == 0:
            sahne_calistir(a, is_, 'kare', cikti / f'{ad}-kapak.png', [min(z['sure'] - 0.4, z['final'] + 1.8)])
        sessiz = is_ / f'sessiz-{b}.mp4'
        sahne_calistir(a, is_, 'video', sessiz)
        hedef = cikti / f'{ad}-{b}.mp4'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(sessiz), '-i', str(ses), '-c:v', 'copy',
                        '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(hedef)], check=True)
        sessiz.unlink(); ciktilar.append(hedef)
    for f in ('ses.wav', 'ses_14.wav'):
        (is_ / f).unlink(missing_ok=True)
    return ciktilar


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    alt = ap.add_subparsers(dest='komut', required=True)
    for ad in ('denetle', 'seslendir', 'kare', 'render', 'uret'):
        p = alt.add_parser(ad)
        p.add_argument('senaryo'); p.add_argument('-o', '--cikti')
        if ad in ('seslendir', 'uret'):
            p.add_argument('--saglayici', default='otomatik'); p.add_argument('--ses')
        if ad == 'kare':
            p.add_argument('--an', type=float, nargs='+', required=True)
            p.add_argument('--format', default='9x16')
        if ad in ('render', 'uret'):
            p.add_argument('--format', nargs='+', help='9:16, 16:9, 1:1, 4:5 ya da ikisi (varsayılan: senaryodaki "format", yoksa 9:16)')
        if ad in ('kare', 'render', 'uret'):
            p.add_argument('--olcek', type=float, default=1.0, help='hızlı prova için çözünürlük çarpanı (örn. 0.5)')
    a = ap.parse_args(argv)
    senaryo = Path(a.senaryo).resolve()
    s = json.loads(senaryo.read_text(encoding='utf-8'))
    cikti = Path(a.cikti).resolve() if a.cikti else senaryo.parent / 'cikti'
    ses_dizini = cikti / 'seslendirme'
    try:
        if a.komut in ('render', 'uret'):
            a.format = formatlar(a.format or s.get('format'))
        elif a.komut == 'kare':
            a.format = formatlar(a.format)[0]
    except ValueError as e:
        print(f'HATA: {e}', file=sys.stderr); return 1

    if a.komut in ('seslendir', 'uret'):
        satirlar = [{'id': x['id'], 'metin': x['metin']} for x in s.get('seslendirme', {}).get('satirlar', [])]
        if satirlar and (a.komut == 'seslendir' or not (ses_dizini / 'seslendirme.json').exists()):
            sys.path.insert(0, str(BURADA.parents[1] / 'ses'))
            import seslendirme
            try:
                k = seslendirme.senaryodan(s, ses_dizini, a.saglayici, a.ses)
            except seslendirme.SeslendirmeHatasi as e:
                print(f'HATA: {e}', file=sys.stderr); return 2
            for x in k['satirlar']:
                print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
        if a.komut == 'uret':
            a.komut = 'render'

    hata, uyari, m = denetle(s, senaryo, ses_dizini, render=a.komut in ('render', 'seslendir'))
    for h in uyari: print(f'UYARI: {h}', file=sys.stderr)
    for h in hata: print(f'HATA: {h}', file=sys.stderr)
    if hata: return 1
    if a.komut in ('denetle', 'seslendir'):
        z = zamanla(s)
        anlar = ', '.join(f"{o['bas']:.2f}" for o in z['ozellikler']) or '-'
        print(f"tamam: {s.get('kimlik', '?')} · urun-vitrini · {z['sure']:g} sn · giriş {z['giris_son']:.2f} · "
              f"özellikler {anlar} · final {z['final']:.2f}")
        return 0
    if not shutil.which('node') or not shutil.which('ffmpeg'):
        print('HATA: node ve ffmpeg gerekli', file=sys.stderr); return 1
    if a.komut == 'kare':
        W, H = motor.boyut(a.format, a.olcek)
        klasor = cikti / 'kareler'; klasor.mkdir(parents=True, exist_ok=True)
        hedef = klasor / f"{s.get('kimlik', 'vitrin')}-urun-vitrini-{a.format}.png"
        sahne_calistir(ayar(s, senaryo, m, W, H), cikti / 'is', 'kare', hedef, a.an)
        return 0
    for yol in render(s, senaryo, m, cikti, a.format, a.olcek):
        print(yol)
    return 0


if __name__ == '__main__':
    sys.exit(main())
