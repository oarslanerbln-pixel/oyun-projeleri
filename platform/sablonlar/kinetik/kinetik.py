"""Kinetik şablon: düz renkli hareketli grafik + kinetik tipografi, kısa sosyal video (6–15 sn).

Tek senaryo dosyasından (sahneler, palet, müzik, seslendirme satırları) görüntü, efekt ve müzik
aynı anlara kilitli üretilir; hiçbir ücretli servis gerekmez.

    python3 platform/sablonlar/kinetik/kinetik.py denetle   senaryo.json
    python3 platform/sablonlar/kinetik/kinetik.py seslendir senaryo.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/kinetik/kinetik.py kare      senaryo.json --an 1.5 4.9
    python3 platform/sablonlar/kinetik/kinetik.py render    senaryo.json [--format 9x16 16x9]
Çıktı varsayılanı senaryonun yanındaki `cikti/` klasörü.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
sys.path.insert(0, str(BURADA.parents[1] / "ses"))
sys.path.insert(0, str(BURADA.parents[1] / "ortak"))
import akis  # noqa: E402
import mastering  # noqa: E402
import zaman  # noqa: E402
from formatlar import FORMATLAR  # noqa: E402


# Ortak adımlar platform/ortak'ta; eski adlar başka modüller ve testler için kalıyor
sureler_oku = akis.sureler_oku
cikti_klasoru = akis.cikti_klasoru
seslendir = akis.seslendir
master = mastering.master


def render(s: dict, cikti: Path, formatlar: list[str]) -> list[Path]:
    import cizim
    import sentez
    kimlik = s.get("kimlik", "kinetik")
    is_ = cikti / "is"
    bilgi = sentez.miksle(s, is_, cikti / "seslendirme")
    akis.uyar_eksik(akis.eksik_seslendirme(s, bilgi))
    mastering.master(is_ / "ses.wav", is_ / "ses-master.wav")
    out = []
    for f in formatlar:
        W, H = FORMATLAR[f]
        sessiz = cizim.video(s, W, H, is_ / f"sessiz-{f}.mp4")
        hedef = cikti / f"{kimlik}-{f}.mp4"
        akis.birlestir(sessiz, is_ / "ses-master.wav", hedef)
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
            p.add_argument("--saglayici", default="otomatik"); p.add_argument("--ses")
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
            p.add_argument("--format", default="9x16", choices=sorted(FORMATLAR))
        if ad == "render":
            p.add_argument("--format", nargs="+", default=["9x16", "16x9"], choices=sorted(FORMATLAR))
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
