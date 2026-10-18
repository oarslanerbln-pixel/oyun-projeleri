"""Oyuncak şablonu: pastel 3D "oyuncak dünya"da küçük adımlardan büyük sonuca giden kısa video (6–20 sn).

Yuvarlak bir kahraman spiral kolonları tırmanır: birkaç sakin adım, dalga halinde büyüme ve doruk, küçük adımla
büyük farkın karşıtlığı, kapanışta ilk adıma dönüş. Tek bir senaryo dosyasından görüntü (three.js, başsız Chromium),
sentez müzik, efektler ve seslendirme aynı anlara kilitli üretilir; ücretli servis gerekmez.

    python3 platform/sablonlar/oyuncak/oyuncak.py denetle   oyuncak.json
    python3 platform/sablonlar/oyuncak/oyuncak.py seslendir oyuncak.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/oyuncak/oyuncak.py kare      oyuncak.json --an 1.5 4.8 [--format 16x9]
    python3 platform/sablonlar/oyuncak/oyuncak.py render    oyuncak.json [--format 9x16 16x9]
Çıktı varsayılanı senaryonun yanındaki `cikti/` klasörü. Varsayılan format yalnız 9x16.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
sys.path.insert(0, str(BURADA.parents[1] / "ses"))
import zaman  # noqa: E402

FORMATLAR = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}
HEDEF_LUFS = -14.0
# Inter (OFL). Depoya girmez (yazı tipleri LFS'e düşer): önce OYUNCAK_FONT_DIZINI, sonra kinetik şablonun dizini,
# önbellek ve sistem (`apt-get install fonts-inter`). Yoksa DejaVu Sans Bold'a düşer.
FONT_ADLARI = ["Inter-ExtraBold.otf", "Inter-800.ttf", "Inter-ExtraBold.ttf"]
FONT_DIZINLERI = [os.environ.get("OYUNCAK_FONT_DIZINI", ""), os.environ.get("KINETIK_FONT_DIZINI", ""),
                  str(Path.home() / ".cache" / "studyo" / "fonts"), "/usr/share/fonts/opentype/inter",
                  "/usr/share/fonts/truetype/inter", str(Path.home() / "Library/Fonts"), "/Library/Fonts"]
YEDEK_FONTLAR = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]


class KurulumHatasi(RuntimeError):
    pass


def font_bul() -> str:
    for d in filter(None, FONT_DIZINLERI):
        for ad in FONT_ADLARI:
            if (Path(d) / ad).exists():
                return str(Path(d) / ad)
    for y in YEDEK_FONTLAR:
        if Path(y).exists():
            print(f"UYARI: Inter bulunamadı, {y} kullanılıyor (`apt-get install fonts-inter` ya da OYUNCAK_FONT_DIZINI)", file=sys.stderr)
            return y
    raise KurulumHatasi("yazı tipi bulunamadı: `apt-get install fonts-inter` ya da OYUNCAK_FONT_DIZINI")


def node_kontrol() -> None:
    if not shutil.which("node"):
        raise KurulumHatasi("node bulunamadı (Node.js 18+ gerekli)")
    nm = Path(os.environ.get("NODE_MODULES", BURADA / "node_modules"))
    eksik = [p for p in ("three", "playwright") if not (nm / p).exists()]
    if eksik:
        raise KurulumHatasi(f"{', '.join(eksik)} yok: `cd {BURADA} && npm install` (Chromium için gerekirse `npx playwright install chromium`)")


def sureler_oku(klasor: Path) -> dict[str, float]:
    k = klasor / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}


def cikti_klasoru(s: dict, arg: str | None) -> Path:
    return Path(arg) if arg else Path(s["_klasor"]) / "cikti"


def ayar(s: dict, W: int, H: int) -> dict:
    """render.mjs → sahne.js'e giden her şey"""
    return {"W": W, "H": H, "fps": s["fps"], "sure": s["sure"], "palet": s["palet"], "kolonlar": s["kolonlar"],
            "c": zaman.cizelge(s), "font": font_bul()}


def _node(s: dict, W: int, H: int, is_: Path, *arglar: str) -> None:
    node_kontrol()
    is_.mkdir(parents=True, exist_ok=True)
    a = is_ / f"ayar-{W}x{H}.json"
    a.write_text(json.dumps(ayar(s, W, H), ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", str(BURADA / "render.mjs"), str(a), *arglar], check=True)


def seslendir(s: dict, cikti: Path, saglayici: str, ses: str | None) -> dict:
    import seslendirme
    satirlar = [{"id": x["id"], "metin": x["metin"]} for x in s["seslendirme"]["satirlar"]]
    return seslendirme.uret(satirlar, cikti / "seslendirme", saglayici, {"ses": ses})


def master(gir: Path, ara: Path) -> None:
    """16 kHz üstü kesilir (AAC sonrası gerçek tepe aşımını önler), -14 LUFS, tepe sınırlayıcı"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(gir), "-af", "lowpass=f=16000:poles=2,ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    lufs = float([x for x in r.stderr.splitlines() if x.strip().startswith("I:")][-1].split()[1])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(gir), "-af",
                    f"lowpass=f=16000:poles=2,volume={HEDEF_LUFS - lufs:.2f}dB,alimiter=limit=0.84:level=false",
                    "-ar", "48000", str(ara)], check=True)


def kareler(s: dict, cikti: Path, format_: str, anlar: list[float]) -> list[Path]:
    W, H = FORMATLAR[format_]
    hedef = cikti / "kareler"
    hedef.mkdir(parents=True, exist_ok=True)
    yol = hedef / f"{s['kimlik']}-{format_}.png"
    _node(s, W, H, cikti / "is", "kare", str(yol), *[str(t) for t in anlar])
    return [yol] if len(anlar) == 1 else [hedef / f"{s['kimlik']}-{format_}-{t:.2f}.png" for t in anlar]


def render(s: dict, cikti: Path, formatlar: list[str]) -> list[Path]:
    import sentez
    node_kontrol()
    is_ = cikti / "is"
    bilgi = sentez.miksle(s, is_, cikti / "seslendirme")
    eksik = [x["id"] for x in s["seslendirme"].get("satirlar", []) if x["id"] not in bilgi["seslendirme"]]
    if eksik:
        print(f"UYARI: seslendirme yok ({', '.join(eksik)}); önce `seslendir` çalıştırın. Video seslendirmesiz çıkar.", file=sys.stderr)
    master(is_ / "ses.wav", is_ / "ses-master.wav")
    out = []
    for f in formatlar:
        W, H = FORMATLAR[f]
        sessiz = is_ / f"sessiz-{f}.mp4"
        _node(s, W, H, is_, "video", str(sessiz))
        hedef = cikti / f"{s['kimlik']}-{f}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(sessiz), "-i", str(is_ / "ses-master.wav"),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(hedef)], check=True)
        out.append(hedef)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("denetle", "seslendir", "kare", "render"):
        p = alt.add_parser(ad)
        p.add_argument("senaryo")
        p.add_argument("-o", "--cikti")
        if ad == "seslendir":
            p.add_argument("--saglayici", default="piper"); p.add_argument("--ses")
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
            p.add_argument("--format", default="9x16", choices=sorted(FORMATLAR))
        if ad == "render":
            p.add_argument("--format", nargs="+", default=["9x16"], choices=sorted(FORMATLAR))
    a = ap.parse_args(argv)
    s = zaman.yukle(a.senaryo)
    cikti = cikti_klasoru(s, a.cikti)
    hatalar = zaman.denetle(s, sureler_oku(cikti / "seslendirme"))
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    try:
        if a.komut == "denetle":
            c = zaman.cizelge(s)
            print(f"tamam: {len(s['sahneler'])} sahne, {s['sure']} sn, {s['kolonlar']['adet']} kolon, doruk {c['doruk']} sn")
        elif a.komut == "seslendir":
            import seslendirme
            try:
                k = seslendir(s, cikti, a.saglayici, a.ses)
            except seslendirme.SeslendirmeHatasi as e:
                print(f"HATA: {e}", file=sys.stderr)
                return 2
            for x in k["satirlar"]:
                print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
            hatalar = zaman.denetle(s, sureler_oku(cikti / "seslendirme"))
            for h in hatalar:
                print(f"HATA: {h}", file=sys.stderr)
            return 1 if hatalar else 0
        elif a.komut == "kare":
            for p in kareler(s, cikti, a.format, a.an):
                print(p)
        else:
            for p in render(s, cikti, a.format):
                print(p)
    except KurulumHatasi as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
