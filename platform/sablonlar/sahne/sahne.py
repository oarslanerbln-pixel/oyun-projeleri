"""Ortak sahne dili: tek senaryo (`"dil": "sahne"`), her stilde aynı sahne tipleri (baslik, liste, sayi, alinti,
karsilastirma, urun, cta, gecis, grafik). Zaman çizelgesi seslendirmeden çıkar; senaryoda saniye yazılmaz.

    S=platform/sablonlar/sahne/sahne.py
    python3 $S denetle   ornek.json [--stil izometrik]          # biçim + (verilirse) stilin kendi sınırları
    python3 $S seslendir ornek.json [--saglayici elevenlabs --ses <id>]
    python3 $S kontakt   ornek.json [--stiller kinetik piksel vitray ...] [--format 9:16]   # her stilden kareler tek sayfada
    python3 $S kare      ornek.json --stil hamur --an 1.5 4.0 [--format 16x9]
    python3 $S render    ornek.json --stil origami [--format 9:16 | 16:9 | 1:1 | 4:5 | ikisi] [--olcek 0.25]
    python3 $S uret      ornek.json --stil piksel --format 16:9  # seslendirme yoksa üretir, sonra render
    python3 $S yeni-stil <ad>                                     # yeni stil kiti: kaplamalar/<ad>.py iskeleti

Kendi çizimiyle (kaplama) çalışan stiller: kinetik, kagit-kesik, izometrik, hamur, piksel, origami (+ kaplamalar/
klasörüne eklenen her stil). Çeviriciyle: vitray, linol, cini, teknik-cizim (desen), kalkis-tabelasi, vhs,
akis-alani (ekran). `stil.py` bu biçimdeki senaryoları buraya iletir.
Çıktı varsayılanı senaryonun yanındaki `cikti/`; seslendirme `cikti/seslendirme/` (bütün stillerde ortak).
Öğeler anlatıcı kendi kelimesini söylediği an girer (senkron.py). Her renderın yanına `.srt`/`.vtt` altyazı yazılır;
senaryoda `"altyazi": true` kelime kelime altyazıyı videoya da yakar (kaplamalar kendi çizer, çeviriciler libass ile).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
sys.path.insert(0, str(BURADA.parents[1] / "ses"))
sys.path.append(str(BURADA.parents[1] / "ortak"))
import altyazi  # noqa: E402
import cevir  # noqa: E402
import dil  # noqa: E402
import karisim  # noqa: E402
import senkron  # noqa: E402


def kaplama_adlari() -> list[str]:
    """skia yüklemeden: taban (kinetik) + kaplamalar/*.py içindeki `ad = "..."`."""
    out = ["kinetik"]
    for p in sorted((BURADA / "kaplamalar").glob("*.py")):
        m = re.search(r'^\s+ad = "([^"]+)"', p.read_text(encoding="utf-8"), re.M)
        if m and not p.stem.startswith("_"):
            out.append(m.group(1))
    return out


def tum_stiller() -> list[str]:
    return kaplama_adlari() + list(cevir.STILLER)


def kaplama_yap(s: dict, stil: str):
    """tek stil ya da (sahnelerde `stil` / `donustur` varsa) stil karışımı"""
    import kaplama
    if karisim.var_mi(s):
        return karisim.Karisim(s, stil, kaplama.kaplamalar())
    return kaplama.kaplamalar()[stil](s)


def _boyut(fmt: str, olcek: float) -> tuple[int, int]:
    W, H = dil.FORMATLAR[fmt]
    return int(W * olcek) // 2 * 2, int(H * olcek) // 2 * 2


def video(kap, W: int, H: int, fmt: str, yol: Path) -> None:
    import skia
    s = kap.s
    fps = s.get("fps", 30)
    surf = skia.Surface(W, H)
    pf = "bgra" if surf.imageInfo().colorType() == skia.kBGRA_8888_ColorType else "rgba"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pf, "-s", f"{W}x{H}", "-r", str(fps),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(yol)],
                          stdin=subprocess.PIPE)
    onceki, veri = None, None
    for i in range(int(round(s["sure"] * fps))):
        t = i / fps
        anahtar = kap.poz(min(t, s["sure"] - 1e-3)) if kap.POZ else t
        if anahtar != onceki:  # stop-motion: aynı pozdaki kareler bir kez çizilir
            with surf as cv:
                cv.clear(0xFF000000)
                kap.kare(cv, t, W, H, fmt)
            veri, onceki = surf.makeImageSnapshot().tobytes(), anahtar
        ff.stdin.write(veri)
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError(f"ffmpeg kodlaması başarısız: {yol}")


def tek_kare(kap, fmt: str, W: int, H: int, t: float, yol: Path) -> Path:
    import skia
    surf = skia.Surface(W, H)
    with surf as cv:
        cv.clear(0xFF000000)
        kap.kare(cv, t, W, H, fmt)
    yol.parent.mkdir(parents=True, exist_ok=True)
    surf.makeImageSnapshot().save(str(yol), skia.kPNG)
    return yol


def render(z: dict, stil: str, cikti: Path, formatlar: list[str], olcek: float = 1.0) -> list[Path]:
    import kalite
    import mastering
    import ses
    kap = kaplama_yap(z, stil)
    is_ = cikti / "is"
    bilgi = ses.miksle(z, kap.MUZIK, kap.SFX, is_, cikti / "seslendirme")
    eksik = [x["id"] for x in z["seslendirme"]["satirlar"] if x["id"] not in bilgi["seslendirme"]]
    if eksik:
        print(f"UYARI: seslendirme yok ({', '.join(eksik)}); önce `seslendir`. Video o satırlar olmadan çıkar.", file=sys.stderr)
    mastering.master(is_ / "ses.wav", is_ / "ses-master.wav")
    ad = f"{z.get('kimlik', 'sahne')}-{stil}"
    out = []
    for f in formatlar:
        W, H = _boyut(f, olcek)
        sessiz = is_ / f"sessiz-{f}.mp4"
        video(kap, W, H, f, sessiz)
        hedef = cikti / f"{ad}-{f}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(sessiz), "-i", str(is_ / "ses-master.wav"),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(hedef)], check=True)
        sessiz.unlink()
        kalite.render_sonrasi(hedef)
        out.append(hedef)
    son = z["sahneler"][-1]
    out.append(tek_kare(kap, formatlar[0], *_boyut(formatlar[0], olcek), z.get("kapak_t", son["son"] - 0.2), cikti / f"{ad}-kapak.png"))
    for x in ("ses.wav", "ses-master.wav"):
        (is_ / x).unlink(missing_ok=True)
    return out + altyazi_yaz(z, cikti / ad)


def altyazi_yaz(z: dict, kok: Path) -> list[Path]:
    """platformlara yüklenecek altyazı (.srt, .vtt) + yeniden yakmak için gruplar (.altyazi.json)"""
    if not z.get("_altyazi"):
        return []
    if "tahmin" in z.get("_altyazi_kaynak", []):
        print("UYARI: bazı satırlarda kelime zamanı yok (Piper ya da eski önbellek); altyazı zamanları tahmini.", file=sys.stderr)
    return altyazi.yaz(z["_altyazi"], kok)


def _yonlendir(komut: str, z: dict, stil: str, cikti: Path, a, yakala: list | None = None) -> int:
    """Çeviricili stil: senaryoyu hedef biçime yazar, hedefin kendi aracını aynı çıktı klasörüyle çalıştırır."""
    yol = cevir.yaz(z, stil, cikti / "cevrilmis" / f"{stil}.json")
    d = cevir.modul_klasoru(stil)
    arac = d / ("desen.py" if stil in cevir.DESEN else "ekran.py")
    arg = [sys.executable, str(arac), "render" if komut == "uret" else komut, str(yol), "-o", str(cikti)]
    if komut == "kare":
        arg += ["--an", *map(str, a.an), "--format", a.format]
    elif komut in ("render", "uret"):
        arg += ["--format", *a.format] + (["--olcek", str(a.olcek)] if stil in cevir.DESEN else [])
    if komut in ("render", "uret") and yakala is None:  # çıktı yollarını yakalayıp altyazıyı ekler
        r = subprocess.run(arg, stdout=subprocess.PIPE, text=True)
        videolar = [Path(x.strip()) for x in r.stdout.splitlines() if x.strip().endswith(".mp4") and Path(x.strip()).exists()]
        print(r.stdout, end="")
        if r.returncode:
            return r.returncode
        for p in altyazi_yaz(z, cikti / f"{z.get('kimlik', 'sahne')}-{stil}"):
            print(p)
        if senkron.acik(z) and z.get("_altyazi"):
            import kalite
            sys.path.insert(0, str(BURADA.parent / "stil"))
            import motor
            for v in videolar:
                altyazi.yak(v, z["_altyazi"], v, yazi_dizini=motor.FONT_ONBELLEK)
                kalite.render_sonrasi(v)
        return 0
    if yakala is None:
        return subprocess.run(arg).returncode
    r = subprocess.run(arg, capture_output=True, text=True)
    yakala += [x.strip() for x in r.stdout.splitlines() if x.strip().endswith(".png")]
    if r.returncode:
        print(r.stderr, file=sys.stderr)
    return r.returncode


def kontakt(z: dict, stiller: list[str], fmt: str, cikti: Path, olcek: float = 0.34) -> Path:
    """Her stil bir satır, her sahne bir sütun (sahnenin bittiği an): stil seçimi için tek sayfa."""
    import skia
    W, H = _boyut(fmt, olcek)
    sahneler = [sh for sh in z["sahneler"] if sh["tip"] != "gecis"]
    etiket, ara = 230, 14
    SW = etiket + len(sahneler) * (W + ara) + ara
    SH = ara + len(stiller) * (H + ara) + 70
    surf = skia.Surface(SW, SH)
    import kaplama
    f = skia.Font(kaplama.motor.yazi_tipi(700), 30)
    with surf as cv:
        cv.clear(0xFFF6F1E4)
        for j, sh in enumerate(sahneler):
            cv.drawString(f"{j + 1}. {sh['tip']}", etiket + ara + j * (W + ara), 46, f, skia.Paint(AntiAlias=True, Color=0xFF555046))
        for i, stil in enumerate(stiller):
            y = 70 + i * (H + ara)
            cv.drawString(stil, 20, y + H / 2 + 10, f, skia.Paint(AntiAlias=True, Color=0xFF1F1B16))
            # kaplamalarda sahnenin bitmiş hali; çeviricili stiller kendi geçişini erken başlattığı için biraz önce
            anlar = [sh["son"] - (0.12 if stil not in cevir.STILLER else min(0.6, (sh["son"] - sh["bas"]) * 0.3)) for sh in sahneler]
            for j, img in enumerate(_kareler(z, stil, fmt, W, H, anlar, cikti)):
                if img is not None:
                    cv.drawImageRect(img, skia.Rect.MakeXYWH(etiket + ara + j * (W + ara), y, W, H),
                                     skia.SamplingOptions(skia.FilterMode.kLinear))
    hedef = cikti / f"{z.get('kimlik', 'sahne')}-kontakt-{fmt}.png"
    cikti.mkdir(parents=True, exist_ok=True)
    surf.makeImageSnapshot().save(str(hedef), skia.kPNG)
    return hedef


def _kareler(z, stil, fmt, W, H, anlar, cikti):
    import skia
    if stil in cevir.STILLER:
        import types
        a = types.SimpleNamespace(an=anlar, format=fmt)
        gecici = cikti / "is" / f"kontakt-{stil}"
        yollar: list = []
        _yonlendir("kare", z, stil, gecici, a, yollar)
        return [skia.Image.open(str(p)) for p in yollar[:len(anlar)]] + [None] * max(0, len(anlar) - len(yollar))
    kap = kaplama_yap(z, stil)
    out = []
    for t in anlar:
        surf = skia.Surface(W, H)
        with surf as cv:
            cv.clear(0xFF000000)
            kap.kare(cv, t, W, H, fmt)
        out.append(surf.makeImageSnapshot())
    return out


KIT = '''"""{ad}: <bir cümlede görünüm>. Ortak sahne dilinin bütün tiplerini çizer; ezilmeyen her şey tabandan (kinetik) gelir.

Önce temel taşları ezin (fon, panel, yazi, isaret, nesne, gecis_ciz); bir tip özel bir sahne isterse ciz_<tip>.
Deneme: `sahne.py kontakt ornekler/kucuk-aliskanliklar/sahne.json --stiller {ad} kinetik`
"""

import skia

from kaplama import Kaplama, alfa, out_back, prog  # noqa: F401


class {sinif}(Kaplama):
    ad = "{ad}"
    aciklama = "<kısa açıklama>"
    POZ = None  # stop-motion için 12
    PALET = {{**Kaplama.PALET, "zemin": "#F4EEDC", "yuzey": "#FFFFFF", "murekkep": "#1F1B16", "soluk": "#6B6458",
              "vurgu": "#E2603F", "vurgu_yazi": "#FFFFFF"}}
    MUZIK = {{**Kaplama.MUZIK, "bpm": 100, "enstruman": "marimba"}}  # sinus, can, marimba, mizrap, kalimba, kare
    SFX = "whoosh"  # whoosh, kagit, pop, blip, tok, katla

    def fon(self, cv, VW, VH, t, i):
        cv.drawColor(self.p["zemin"])

    def panel(self, cv, r, renk_, p=1.0, kimlik=0, t=0.0):
        super().panel(cv, r, renk_, p, kimlik, t)


KAPLAMA = {sinif}
'''


def yeni_stil(ad: str) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9-]*", ad):
        raise ValueError("ad: küçük harf, rakam ve tire (örn. sulu-boya)")
    if ad in tum_stiller():
        raise ValueError(f"{ad} zaten var")
    hedef = BURADA / "kaplamalar" / f"{ad.replace('-', '_')}.py"
    sinif = "".join(x.capitalize() for x in ad.split("-"))
    hedef.write_text(KIT.format(ad=ad, sinif=sinif), encoding="utf-8")
    return hedef


def main(argv: list[str] | None = None) -> int:
    import formatlar
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("denetle", "seslendir", "kare", "render", "uret", "kontakt", "yeni-stil"):
        p = alt.add_parser(ad)
        if ad == "yeni-stil":
            p.add_argument("ad"); continue
        p.add_argument("senaryo")
        p.add_argument("-o", "--cikti")
        if ad == "kontakt":
            p.add_argument("--stiller", nargs="+")
            p.add_argument("--format", default="9x16")
            continue
        p.add_argument("--stil")
        if ad in ("seslendir", "uret"):
            p.add_argument("--saglayici", default="otomatik"); p.add_argument("--ses")
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
            p.add_argument("--format", default="9x16")
        if ad in ("render", "uret"):
            p.add_argument("--format", nargs="+")
            p.add_argument("--olcek", type=float, default=1.0, help="hızlı prova için çözünürlük çarpanı (örn. 0.25)")
    a = ap.parse_args(argv)
    if a.komut == "yeni-stil":
        try:
            print(yeni_stil(a.ad))
        except ValueError as e:
            print(f"HATA: {e}", file=sys.stderr); return 1
        return 0
    s = dil.yukle(a.senaryo)
    stil = getattr(a, "stil", None) or s.get("stil")
    hatalar = dil.denetle(s)
    if not hatalar and stil and stil not in tum_stiller():
        hatalar.append(f"stil: {stil} bilinmiyor ({', '.join(tum_stiller())})")
    cikti = Path(a.cikti) if a.cikti else Path(s["_klasor"]) / "cikti"
    ses_dizini = cikti / "seslendirme"
    if not hatalar:
        hatalar += karisim.denetle(s, stil, kaplama_adlari())
    if not hatalar and stil in cevir.STILLER:
        hatalar += cevir.denetle(dil.zamanla(s, dil.sureler_oku(ses_dizini)), stil)
    if "altyazi" in s and not (isinstance(s["altyazi"], bool) or isinstance(s["altyazi"], dict)):
        hatalar.append("altyazi: true/false olmalı")
    if "senkron" in s and not isinstance(s["senkron"], bool):
        hatalar.append("senkron: true/false olmalı")
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    if a.komut == "denetle":
        z = dil.zamanla(s, dil.sureler_oku(ses_dizini))
        print(f"tamam: {s.get('kimlik', '?')} · {stil or 'stil seçilmedi'} · {len(s['sahneler'])} sahne · ~{z['sure']:g} sn")
        return 0
    eksik = [x["id"] for x in dil.zamanla(s)["seslendirme"]["satirlar"] if x["id"] not in dil.sureler_oku(ses_dizini)]
    if a.komut == "seslendir" or (a.komut == "uret" and eksik):
        import seslendirme
        try:
            k = seslendirme.senaryodan(dil.zamanla(s), ses_dizini, a.saglayici, a.ses)
        except seslendirme.SeslendirmeHatasi as e:
            print(f"HATA: {e}", file=sys.stderr); return 2
        for x in k["satirlar"]:
            print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
        if a.komut == "seslendir":
            return 0
    z = senkron.bagla(dil.zamanla(s, dil.sureler_oku(ses_dizini)), ses_dizini)
    if a.komut == "kontakt":
        try:
            fmt = formatlar.anahtar(a.format)
        except ValueError as e:
            print(f"HATA: {e}", file=sys.stderr); return 1
        stiller = a.stiller or kaplama_adlari()
        bilinmeyen = [x for x in stiller if x not in tum_stiller()]
        if bilinmeyen:
            print(f"HATA: bilinmeyen stil {', '.join(bilinmeyen)}", file=sys.stderr); return 1
        print(kontakt(z, stiller, fmt, cikti))
        return 0
    if not stil:
        print(f"HATA: --stil gerekli ({', '.join(tum_stiller())})", file=sys.stderr); return 1
    if a.komut == "kare":
        a.format = formatlar.anahtar(a.format)
        if stil in cevir.STILLER:
            return _yonlendir("kare", z, stil, cikti, a)
        kap = kaplama_yap(z, stil)
        W, H = dil.FORMATLAR[a.format]
        for t in a.an:
            print(tek_kare(kap, a.format, W, H, t, cikti / "kareler" / f"{z.get('kimlik', 'sahne')}-{stil}-{a.format}-{t:05.2f}.png"))
        return 0
    try:
        a.format = formatlar.coz(a.format if a.format and len(a.format) > 1 else (a.format[0] if a.format else None), s)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr); return 1
    if stil in cevir.STILLER:
        return _yonlendir(a.komut, z, stil, cikti, a)
    for p in render(z, stil, cikti, a.format, a.olcek):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
