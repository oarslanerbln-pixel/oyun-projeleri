"""Desen/zanaat stilleri: vitray, linol baskı, çini, teknik çizim — tek senaryo, serbest süre (6–20 sn).

Senaryo sahneleri (motif + başlık + alt satır) ve seslendirme satırlarından görüntü, müzik ve efekt aynı anlara kilitli
üretilir; ücretli servis gerekmez (seslendirme ElevenLabs, yoksa Piper yedeği).

    python3 platform/sablonlar/desen/desen.py denetle   vitray.json
    python3 platform/sablonlar/desen/desen.py seslendir vitray.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/desen/desen.py kare      vitray.json --an 1.5 4.6 [--format 16x9]
    python3 platform/sablonlar/desen/desen.py render    vitray.json [--format 9:16 | 16:9 | 1:1 | 4:5 | ikisi]
    python3 platform/sablonlar/desen/desen.py uret      vitray.json --format 16:9      # seslendirme yoksa üretir, sonra render
`--stil` senaryodaki stili ezer (aynı içerik başka stilde). Format verilmezse senaryonun `format` alanı, o da yoksa 9:16.
Çıktı varsayılanı senaryonun yanındaki `cikti/`; seslendirme `cikti/seslendirme/`.
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
sys.path.append(str(BURADA.parents[1] / "ortak"))
import zaman  # noqa: E402


def sureler_oku(klasor: Path) -> dict[str, float]:
    k = klasor / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}


def _boyut(fmt: str, olcek: float) -> tuple[int, int]:
    W, H = zaman.FORMATLAR[fmt]
    return int(W * olcek) // 2 * 2, int(H * olcek) // 2 * 2


def render(s: dict, cikti: Path, formatlar: list[str], olcek: float = 1.0) -> list[Path]:
    import cizim

    import mastering
    import sentez
    kimlik = s.get("kimlik", f"desen-{s['stil']}")
    is_ = cikti / "is"
    bilgi = sentez.miksle(s, is_, cikti / "seslendirme")
    eksik = [x["id"] for x in s["seslendirme"].get("satirlar", []) if x["id"] not in bilgi["seslendirme"]]
    if eksik:
        print(f"UYARI: seslendirme yok ({', '.join(eksik)}); önce `seslendir`. Video seslendirmesiz çıkar.", file=sys.stderr)
    mastering.master(is_ / "ses.wav", is_ / "ses-master.wav")
    out = []
    for f in formatlar:
        W, H = _boyut(f, olcek)
        sessiz = cizim.video(s, W, H, is_ / f"sessiz-{f}.mp4", fmt=f)
        hedef = cikti / f"{kimlik}-{f}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(sessiz), "-i", str(is_ / "ses-master.wav"),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(hedef)], check=True)
        sessiz.unlink()
        import kalite
        kalite.render_sonrasi(hedef)  # kalite.json + kontakt sayfası; render'ı durdurmaz
        out.append(hedef)
    f = formatlar[0]
    kapak = cikti / f"{kimlik}-kapak.png"
    cizim.tek_kare(s, f, *_boyut(f, olcek), s.get("kapak_t", s["sure"] - 0.3)).save(kapak)
    out.append(kapak)
    for x in ("ses.wav", "ses-master.wav"):
        (is_ / x).unlink(missing_ok=True)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("denetle", "seslendir", "kare", "render", "uret"):
        p = alt.add_parser(ad)
        p.add_argument("senaryo")
        p.add_argument("-o", "--cikti")
        p.add_argument("--stil", choices=zaman.STILLER)
        if ad in ("seslendir", "uret"):
            p.add_argument("--saglayici", default="otomatik"); p.add_argument("--ses")
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
            p.add_argument("--format", default="9x16")
        if ad in ("render", "uret"):
            p.add_argument("--format", nargs="+", help="9:16, 16:9, 1:1, 4:5 ya da ikisi")
            p.add_argument("--olcek", type=float, default=1.0, help="hızlı prova için çözünürlük çarpanı (örn. 0.25)")
    a = ap.parse_args(argv)
    s = zaman.yukle(a.senaryo)
    if a.stil:
        s["stil"] = a.stil
    cikti = Path(a.cikti) if a.cikti else Path(s["_klasor"]) / "cikti"
    ses_dizini = cikti / "seslendirme"
    hatalar = zaman.denetle(s, sureler_oku(ses_dizini))
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    if a.komut == "denetle":
        print(f"tamam: {s.get('kimlik', '?')} · {s['stil']} · {len(s['sahneler'])} sahne · {s['sure']:g} sn")
        return 0
    if a.komut in ("seslendir", "uret") and (a.komut == "seslendir" or not (ses_dizini / "seslendirme.json").exists()):
        import seslendirme
        try:
            k = seslendirme.senaryodan(s, ses_dizini, a.saglayici, a.ses)
        except seslendirme.SeslendirmeHatasi as e:
            print(f"HATA: {e}", file=sys.stderr)
            return 2
        for x in k["satirlar"]:
            print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
        hatalar = zaman.denetle(s, sureler_oku(ses_dizini))
        for h in hatalar:
            print(f"HATA: {h}", file=sys.stderr)
        if hatalar or a.komut == "seslendir":
            return 1 if hatalar else 0
    if a.komut == "kare":
        import cizim
        import formatlar
        f = formatlar.anahtar(a.format)
        for p in cizim.kareler(s, f, *zaman.FORMATLAR[f], a.an, cikti / "kareler"):
            print(p)
        return 0
    import formatlar
    try:
        fmt = formatlar.coz(a.format if a.format and len(a.format) > 1 else (a.format[0] if a.format else None), s)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    for p in render(s, cikti, fmt, a.olcek):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
