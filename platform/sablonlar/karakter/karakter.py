"""Karakter şablonu: ortak iskelet (poz, ifade, ağız senkronu) + görünüm katmanı; ilk görünüm çizgisel insan.

Tek senaryo dosyasından görüntü, müzik, efekt ve seslendirme aynı anlara kilitli üretilir; karakterin ağzı
seslendirmeyle oynar (ElevenLabs harf zamanları, yoksa ses genliği).

    python3 platform/sablonlar/karakter/karakter.py denetle   cizgisel.json
    python3 platform/sablonlar/karakter/karakter.py seslendir cizgisel.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/karakter/karakter.py kare      cizgisel.json --an 1.5 4.3 [--format 16x9]
    python3 platform/sablonlar/karakter/karakter.py render    cizgisel.json [--format 9x16 16x9]
    python3 platform/sablonlar/karakter/karakter.py uret      cizgisel.json [--format 9x16]   # seslendirme yoksa üretir, sonra render
Format verilmezse senaryonun `format` listesi, o da yoksa yalnız 9x16. Çıktı varsayılanı senaryonun yanındaki `cikti/`.
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
import senaryo  # noqa: E402
from formatlar import FORMATLAR  # noqa: E402


def render(s: dict, cikti: Path, formatlar: list[str]) -> list[Path]:
    import cizim
    import mastering
    import sentez
    kimlik = s.get("kimlik", "karakter")
    is_, ses = cikti / "is", cikti / "seslendirme"
    bilgi = sentez.miksle(s, is_, ses)
    akis.uyar_eksik(akis.eksik_seslendirme(s, bilgi))
    mastering.master(is_ / "ses.wav", is_ / "ses-master.wav")
    out = []
    for f in formatlar:
        W, H = FORMATLAR[f]
        sessiz, kaynak = cizim.video(s, W, H, is_ / f"sessiz-{f}.mp4", ses)
        if any(v == "genlik" for v in kaynak.values()):
            print(f"bilgi: ağız senkronu ses genliğinden ({', '.join(k for k, v in kaynak.items() if v == 'genlik')}); "
                  "harf zamanı yok (Piper ya da eski önbellek)", file=sys.stderr)
        hedef = cikti / f"{kimlik}-{f}.mp4"
        akis.birlestir(sessiz, is_ / "ses-master.wav", hedef)
        out.append(hedef)
    W, H = FORMATLAR[formatlar[0]]
    out.append(cizim.kapak(s, W, H, s.get("kapak_t", s["sure"] - 0.5), cikti / f"{kimlik}-kapak.png", ses))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("denetle", "seslendir", "kare", "render", "uret"):
        p = alt.add_parser(ad)
        p.add_argument("senaryo")
        p.add_argument("-o", "--cikti")
        if ad in ("seslendir", "uret"):
            p.add_argument("--saglayici", default="otomatik"); p.add_argument("--ses")
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
            p.add_argument("--format", default="9x16", choices=sorted(FORMATLAR))
        if ad in ("render", "uret"):
            p.add_argument("--format", nargs="+", choices=sorted(FORMATLAR))
    a = ap.parse_args(argv)
    s = senaryo.yukle(a.senaryo)
    cikti = akis.cikti_klasoru(s, a.cikti)
    hatalar = senaryo.denetle(s, akis.sureler_oku(cikti / "seslendirme"))
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    if a.komut == "denetle":
        print(f"tamam: {s['stil']} · {len(s['sahneler'])} sahne · {s['sure']} sn")
        return 0
    if a.komut in ("seslendir", "uret"):
        if a.komut == "seslendir" or not (cikti / "seslendirme" / "seslendirme.json").exists():
            import seslendirme
            try:
                k = akis.seslendir(s, cikti, a.saglayici, a.ses)
            except seslendirme.SeslendirmeHatasi as e:
                print(f"HATA: {e}", file=sys.stderr)
                return 2
            for x in k["satirlar"]:
                print(f"{x['id']}\t{x['sure']:.2f} sn\t{'harf' if x.get('hizalama') else 'genlik'}\t{x['metin']}")
            hatalar = senaryo.denetle(s, akis.sureler_oku(cikti / "seslendirme"))
            for h in hatalar:
                print(f"HATA: {h}", file=sys.stderr)
            if hatalar or a.komut == "seslendir":
                return 1 if hatalar else 0
    if a.komut == "kare":
        import cizim
        for p in cizim.kareler(s, *FORMATLAR[a.format], a.an, cikti / "kareler", cikti / "seslendirme"):
            print(p)
        return 0
    for p in render(s, cikti, a.format or s.get("format") or ["9x16"]):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
