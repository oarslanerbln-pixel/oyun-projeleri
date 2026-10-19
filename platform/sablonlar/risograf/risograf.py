"""Risograf şablonu: üst üste basılan spot mürekkepler, baskı kayması ve tanecik, kısa video (6–15 sn).

Tek senaryo dosyasından (sayfalar, öğeler, mürekkepler, palet, müzik, seslendirme satırları) görüntü, efekt
ve müzik aynı anlara kilitli üretilir; hiçbir ücretli servis gerekmez.

    python3 platform/sablonlar/risograf/risograf.py fontlar
    python3 platform/sablonlar/risograf/risograf.py denetle   risograf.json
    python3 platform/sablonlar/risograf/risograf.py seslendir risograf.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/risograf/risograf.py kare      risograf.json --an 1.5 4.6 [--format 16x9]
    python3 platform/sablonlar/risograf/risograf.py render    risograf.json [--format 9x16 16x9]
Format verilmezse senaryonun `format` listesi, o da yoksa yalnız 9x16. Çıktı varsayılanı senaryonun yanındaki `cikti/`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
sys.path.insert(0, str(BURADA.parents[1] / "ses"))
sys.path.append(str(BURADA.parents[1] / "ortak"))  # kalite kapısı
import zaman  # noqa: E402

FORMATLAR = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}
HEDEF_LUFS = -14.0


def sureler_oku(klasor: Path) -> dict[str, float]:
    k = klasor / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}


def master(gir: Path, ara: Path) -> None:
    """16 kHz üstü kesilir (AAC sonrası gerçek tepe aşımını önler), -14 LUFS, tepe sınırlayıcı"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(gir), "-af", "lowpass=f=16000:poles=2,ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    lufs = float([x for x in r.stderr.splitlines() if x.strip().startswith("I:")][-1].split()[1])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(gir), "-af",
                    f"lowpass=f=16000:poles=2,volume={HEDEF_LUFS - lufs:.2f}dB,alimiter=limit=0.75:level=false",
                    "-ar", "48000", str(ara)], check=True)


def render(s: dict, cikti: Path, formatlar: list[str]) -> list[Path]:
    import cizim
    import sentez
    kimlik = s.get("kimlik", "risograf")
    is_ = cikti / "is"
    bilgi = sentez.miksle(s, is_, cikti / "seslendirme")
    eksik = [x["id"] for x in s["seslendirme"].get("satirlar", []) if x["id"] not in bilgi["seslendirme"]]
    if eksik:
        print(f"UYARI: seslendirme yok ({', '.join(eksik)}); önce `seslendir` çalıştırın. Video seslendirmesiz çıkar.", file=sys.stderr)
    master(is_ / "ses.wav", is_ / "ses-master.wav")
    out = []
    for f in formatlar:
        W, H = FORMATLAR[f]
        sessiz = cizim.video(s, f, W, H, is_ / f"sessiz-{f}.mp4")
        hedef = cikti / f"{kimlik}-{f}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(sessiz), "-i", str(is_ / "ses-master.wav"),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(hedef)], check=True)
        import kalite
        kalite.render_sonrasi(hedef)  # kalite.json + kontakt sayfası; render'ı durdurmaz
        out.append(hedef)
    f = formatlar[0]
    out.append(cizim.kapak(s, f, *FORMATLAR[f], s.get("kapak_t", s["sure"] - 0.4), cikti / f"{kimlik}-kapak.png"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("fontlar")
    for ad in ("denetle", "seslendir", "kare", "render"):
        p = alt.add_parser(ad)
        p.add_argument("senaryo")
        p.add_argument("-o", "--cikti")
        if ad == "seslendir":
            p.add_argument("--saglayici", default="otomatik"); p.add_argument("--ses")
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
            p.add_argument("--format", default="9x16", choices=sorted(FORMATLAR))
        if ad == "render":
            p.add_argument("--format", nargs="+", choices=sorted(FORMATLAR))
    a = ap.parse_args(argv)
    if a.komut == "fontlar":
        import fontlar
        for p in fontlar.indir():
            print(p)
        return 0
    s = zaman.yukle(a.senaryo)
    cikti = Path(a.cikti) if a.cikti else Path(s["_klasor"]) / "cikti"
    hatalar = zaman.denetle(s, sureler_oku(cikti / "seslendirme"))
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    if a.komut == "denetle":
        oge = sum(len(sy["ogeler"]) for sy in s["sayfalar"])
        print(f"tamam: {len(s['sayfalar'])} sayfa, {oge} öğe, {len(s['murekkepler'])} mürekkep, {len(zaman.damgalar(s))} damga, {s['sure']} sn")
    elif a.komut == "seslendir":
        import seslendirme
        try:
            k = seslendirme.senaryodan(s, cikti / "seslendirme", a.saglayici, a.ses)
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
        import cizim
        for p in cizim.kareler(s, a.format, *FORMATLAR[a.format], a.an, cikti / "kareler"):
            print(p)
    else:
        for p in render(s, cikti, a.format or s.get("format") or ["9x16"]):
            print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
