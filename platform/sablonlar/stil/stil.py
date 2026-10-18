"""Stil şablonları (kâğıt kesik, izometrik): kinetik şablonla aynı senaryo.json → 10 sn, dört vuruşlu video.

    python3 platform/sablonlar/stil/stil.py denetle   senaryo.json --stil kagit-kesik
    python3 platform/sablonlar/stil/stil.py seslendir senaryo.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/stil/stil.py kare      senaryo.json --stil izometrik --an 1.5 4.7 [--format 16x9]
    python3 platform/sablonlar/stil/stil.py render    senaryo.json --stil izometrik [--format 9:16 | 16:9 | ikisi]
    python3 platform/sablonlar/stil/stil.py uret      senaryo.json --stil izometrik --format 16:9   # seslendirme yoksa üretir, sonra render
`--stil kinetik` aynı komutu kinetik şablona iletir. Stil verilmezse senaryodaki "stil" alanı kullanılır.
Format sırası: --format, yoksa senaryodaki "format" alanı ("9:16", "16:9", "ikisi" ya da liste), yoksa yalnız 9:16.
Çıktı varsayılanı senaryonun yanındaki `cikti/` klasörü; seslendirme `cikti/seslendirme/` (üç stilde ortak).
"""
import argparse, importlib, json, os, sys

BURADA = os.path.dirname(os.path.abspath(__file__))
SABLONLAR = os.path.dirname(BURADA)
sys.path.insert(0, BURADA)
import motor  # noqa: E402

TUM_STILLER = sorted(motor.STILLER) + ['kinetik', 'bumper', 'mekan']
VARSAYILAN_FORMAT = ['9x16']  # ikisi birden yalnız istenince (takvimde video başına seçilir)


def formatlar(secim):
    """'9:16' / '16x9' / 'ikisi' (ya da bunların listesi) → ['9x16', ...]; tanımsızsa ValueError."""
    if not secim:
        return list(VARSAYILAN_FORMAT)
    cikti = []
    for x in [secim] if isinstance(secim, str) else secim:
        x = str(x).strip().lower().replace(':', 'x')
        for f in (['9x16', '16x9'] if x in ('ikisi', 'both', 'hepsi') else [x]):
            if f not in motor.BOYUTLAR:
                raise ValueError(f'tanımsız format: {x} (9:16, 16:9, 1:1, 4:5 ya da ikisi)')
            if f not in cikti:
                cikti.append(f)
    return cikti


def _kinetik(argv):
    sys.path.insert(0, os.path.join(SABLONLAR, 'kinetik'))
    import kinetik
    return kinetik.main(argv)


def _bumper(a):
    """6 sn bumper / 3 sn imza: platform/sablonlar/bumper (seslendirme yok, metin marka.json + senaryo)."""
    if a.komut == 'seslendir':
        print('bumper: seslendirme kullanmaz (yalnız müzik)', file=sys.stderr); return 0
    sys.path.insert(0, os.path.join(SABLONLAR, 'bumper'))
    import bumper
    ileri = [a.komut, a.senaryo] + (['-o', a.cikti] if a.cikti else [])
    if a.komut == 'kare':
        ileri += ['--an'] + [str(t) for t in a.an] + ['--format', a.format]
    elif a.komut in ('render', 'uret'):
        ileri += ['--format'] + a.format + ['--olcek', str(a.olcek)]
    return bumper.main(ileri)


def _mekan(a):
    """Fotoğraflı mekân şablonu ( TV döngüsü / Reel): platform/sablonlar/mekan. Biçim varsayılanı varyanta göre."""
    sys.path.insert(0, os.path.join(SABLONLAR, 'mekan'))
    import mekan
    ileri = [a.komut, a.senaryo] + (['-o', a.cikti] if a.cikti else [])
    if a.komut in ('seslendir', 'uret'):
        ileri += ['--saglayici', a.saglayici] + (['--ses', a.ses] if a.ses else [])
    if a.komut == 'kare':
        ileri += ['--an'] + [str(t) for t in a.an] + (['--format', a.format] if a.format else [])
    elif a.komut in ('render', 'uret'):
        ileri += (['--format'] + a.format if a.format else []) + ['--olcek', str(a.olcek)]
    return mekan.main(ileri)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    alt = ap.add_subparsers(dest='komut', required=True)
    for ad in ('denetle', 'seslendir', 'kare', 'render', 'uret'):
        p = alt.add_parser(ad)
        p.add_argument('senaryo'); p.add_argument('-o', '--cikti'); p.add_argument('--stil', choices=TUM_STILLER)
        if ad in ('seslendir', 'uret'):
            p.add_argument('--saglayici', default='otomatik'); p.add_argument('--ses')
        if ad == 'kare':
            p.add_argument('--an', type=float, nargs='+', required=True)
            p.add_argument('--format', default='9x16', type=lambda x: formatlar(x)[0])
        if ad in ('render', 'uret'):
            p.add_argument('--format', nargs='+', help='9:16, 16:9, 1:1, 4:5 ya da ikisi (varsayılan: senaryodaki "format", yoksa 9:16)')
            p.add_argument('--olcek', type=float, default=1.0, help='hızlı prova için çözünürlük çarpanı (örn. 0.25)')
    a = ap.parse_args(argv)
    with open(a.senaryo, encoding='utf-8') as f:
        s = json.load(f)
    if (a.stil or s.get('stil')) == 'mekan':  # biçim varsayılanı varyanta göre (tv → 16:9), mekan.py çözer
        if a.komut == 'kare' and '--format' not in argv: a.format = None
        return _mekan(a)
    if a.komut in ('render', 'uret'):
        try:
            a.format = formatlar(a.format or s.get('format'))
        except ValueError as e:
            print(f'HATA: {e}', file=sys.stderr); return 1
    if (a.stil or s.get('stil')) == 'bumper':
        return _bumper(a)
    if a.komut == 'uret':  # tek adım: seslendirme yoksa üret, sonra render (üç stilde aynı)
        ortak = [a.senaryo] + (['-o', a.cikti] if a.cikti else []) + (['--stil', a.stil] if a.stil else [])
        cikti = a.cikti or os.path.join(os.path.dirname(os.path.abspath(a.senaryo)), 'cikti')
        if not os.path.exists(os.path.join(cikti, 'seslendirme', 'seslendirme.json')):
            ses = ['--saglayici', a.saglayici] + (['--ses', a.ses] if a.ses else [])
            r = main(['seslendir'] + ortak + ses)
            if r: return r
        return main(['render'] + ortak + ['--format'] + a.format + ['--olcek', str(a.olcek)])
    stil_ad = a.stil or s.get('stil')
    if stil_ad == 'kinetik':
        ileri, atla, coklu = [], False, False  # --stil, --olcek (kinetikte yok) ve --format çıkarılır
        for x in argv:
            if atla: atla = False; continue
            if coklu and not x.startswith('-'): continue
            coklu = False
            if x in ('--stil', '--olcek'): atla = True; continue
            if x == '--format': coklu = a.komut == 'render'; atla = not coklu; continue
            ileri.append(x)
        if a.komut == 'render':  # çözülen format açıkça iletilir; kinetiğin "ikisi" varsayılanı devreye girmez
            ileri += ['--format'] + a.format
        elif a.komut == 'kare':
            ileri += ['--format', a.format]
        return _kinetik(ileri)
    cikti = a.cikti or os.path.join(os.path.dirname(os.path.abspath(a.senaryo)), 'cikti')
    ses_dizini = os.path.join(cikti, 'seslendirme')

    if a.komut == 'seslendir':  # stile bağlı değil: platform/ses adımı
        sys.path.insert(0, os.path.join(os.path.dirname(SABLONLAR), 'ses'))
        import seslendirme
        satirlar = [{'id': x['id'], 'metin': x['metin']} for x in s.get('seslendirme', {}).get('satirlar', [])]
        try:
            k = seslendirme.uret(satirlar, __import__('pathlib').Path(ses_dizini), a.saglayici,
                                 {'ses': a.ses, 'saglayici': s.get('seslendirme', {}).get('saglayici')})
        except seslendirme.SeslendirmeHatasi as e:
            print(f'HATA: {e}', file=sys.stderr); return 2
        for x in k['satirlar']:
            print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
        if not stil_ad:
            return 0

    if not stil_ad:
        print(f'HATA: --stil gerekli ({", ".join(TUM_STILLER)})', file=sys.stderr); return 1
    hata, uyari = motor.denetle(s, stil_ad, ses_dizini, render=a.komut in ('render', 'seslendir'))
    for h in uyari: print(f'UYARI: {h}', file=sys.stderr)
    for h in hata: print(f'HATA: {h}', file=sys.stderr)
    if hata: return 1
    if a.komut in ('denetle', 'seslendir'):
        if a.komut == 'denetle': print(f"tamam: {s.get('kimlik', '?')} · {stil_ad} · {motor.SURE:g} sn")
        return 0
    motor.kur(s, stil_ad, ses_dizini)
    stil = importlib.import_module(motor.STILLER[stil_ad])
    ad = f"{s.get('kimlik', 'video')}-{stil_ad}"
    if a.komut == 'kare':
        klasor = os.path.join(cikti, 'kareler'); os.makedirs(klasor, exist_ok=True)
        W, H = motor.boyut(a.format)
        for t in a.an:
            yol = os.path.join(klasor, f'{ad}-{a.format}-{t:05.2f}.png')
            motor.kapak(stil.kare, yol, W, H, t); print(yol)
        return 0
    for yol in motor.calistir(ad, stil, cikti, a.format, a.olcek):
        print(yol)
    return 0


if __name__ == '__main__':
    sys.exit(main())
