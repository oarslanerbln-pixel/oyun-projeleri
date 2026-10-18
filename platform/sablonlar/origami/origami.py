"""Origami şablon: katlanarak açılan düz renkli kâğıt nesneler, kısa marka/ürün videosu (6–15 sn).

Tek senaryo dosyasından (vitrin ve kapanış sahneleri, palet, müzik, seslendirme satırları) görüntü,
kâğıt efektleri ve müzik aynı anlara kilitli üretilir; hiçbir ücretli servis gerekmez.

    python3 platform/sablonlar/origami/origami.py denetle   origami.json
    python3 platform/sablonlar/origami/origami.py seslendir origami.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/origami/origami.py kare      origami.json --an 1.5 4.9
    python3 platform/sablonlar/origami/origami.py render    origami.json [--format 9x16 16x9]
Çıktı varsayılanı senaryonun yanındaki `cikti/` klasörü. Varsayılan format yalnız 9x16.
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
import zaman  # noqa: E402

FORMATLAR = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}
HEDEF_LUFS = -14.0


def sureler_oku(klasor: Path) -> dict[str, float]:
    k = klasor / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}


def cikti_klasoru(s: dict, arg: str | None) -> Path:
    return Path(arg) if arg else Path(s["_klasor"]) / "cikti"


def seslendir(s: dict, cikti: Path, saglayici: str, ses: str | None) -> dict:
    import seslendirme
    satirlar = [{"id": x["id"], "metin": x["metin"]} for x in s["seslendirme"]["satirlar"]]
    return seslendirme.uret(satirlar, cikti / "seslendirme", saglayici, {"ses": ses})


def master(gir: Path, ara: Path) -> None:
    """16 kHz üstü kesilir (AAC sonrası gerçek tepe aşımını önler), -14 LUFS, tepe -2.5 dBFS"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(gir), "-af", "lowpass=f=16000:poles=2,ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    lufs = float([x for x in r.stderr.splitlines() if x.strip().startswith("I:")][-1].split()[1])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(gir), "-af",
                    f"lowpass=f=16000:poles=2,volume={HEDEF_LUFS - lufs:.2f}dB,alimiter=limit=0.75:level=false",
                    "-ar", "48000", str(ara)], check=True)


def render(s: dict, cikti: Path, formatlar: list[str]) -> list[Path]:
    import cizim
    import sentez
    kimlik = s.get("kimlik", "origami")
    is_ = cikti / "is"
    bilgi = sentez.miksle(s, is_, cikti / "seslendirme")
    eksik = [x["id"] for x in s["seslendirme"].get("satirlar", []) if x["id"] not in bilgi["seslendirme"]]
    if eksik:
        print(f"UYARI: seslendirme yok ({', '.join(eksik)}); önce `seslendir` çalıştırın. Video seslendirmesiz çıkar.", file=sys.stderr)
    master(is_ / "ses.wav", is_ / "ses-master.wav")
    out = []
    for f in formatlar:
        W, H = FORMATLAR[f]
        sessiz = cizim.video(s, W, H, is_ / f"sessiz-{f}.mp4")
        hedef = cikti / f"{kimlik}-{f}.mp4"
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
    if a.komut == "denetle":
        print(f"tamam: {len(s['sahneler'])} sahne, {s['sure']} sn")
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
        import cizim
        for p in cizim.kareler(s, *FORMATLAR[a.format], a.an, cikti / "kareler"):
            print(p)
    else:
        for p in render(s, cikti, a.format):
            print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
