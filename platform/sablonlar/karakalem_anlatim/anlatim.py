"""Karakalem anlatım şablonu: uzun video için serbest uzunlukta kurşun kalem sahneleri.

Bölüm kartı, el çizimi harita, anlatıcı karakter (dudak senkronu), belge yakın planı, kalabalık/sokak,
sayaç, terazi (olasılık) ve takvim/zaman çizelgesi. Her sahnenin süresi serbesttir; senaryo tek başına
render edilir ya da kurgu.json içinde `"stil": "karakalem_anlatim"` sahnesi olur. Seslendirme platform/ses
adımından gelir (ElevenLabs; anahtar yoksa Piper).

    python3 platform/sablonlar/karakalem_anlatim/anlatim.py fontlar
    python3 platform/sablonlar/karakalem_anlatim/anlatim.py denetle   anlatim.json
    python3 platform/sablonlar/karakalem_anlatim/anlatim.py kontakt   anlatim.json [--format 16x9]   # her sahne bir kare, tek sayfa
    python3 platform/sablonlar/karakalem_anlatim/anlatim.py kare      anlatim.json --an 2.0 9.5
    python3 platform/sablonlar/karakalem_anlatim/anlatim.py seslendir anlatim.json
    python3 platform/sablonlar/karakalem_anlatim/anlatim.py render    anlatim.json [--format 16x9]
Format verilmezse senaryonun `format` listesi, o da yoksa 16x9. Çıktı varsayılanı senaryonun yanındaki `cikti/`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
sys.path.insert(1, str(BURADA.parents[1] / "ses"))
sys.path.append(str(BURADA.parents[1] / "ortak"))  # kalite kapısı
sys.path.append(str(BURADA.parent / "karakalem"))  # fontlar
import zaman  # noqa: E402

FORMATLAR = {"16x9": (1920, 1080), "9x16": (1080, 1920), "1x1": (1080, 1080), "4x5": (1080, 1350)}
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
    kimlik = s.get("kimlik", "anlatim")
    is_ = cikti / "is"
    bilgi = sentez.miksle(s, is_, cikti / "seslendirme")
    eksik = [x["id"] for x in s["seslendirme"].get("satirlar", []) if x["id"] not in bilgi["seslendirme"]]
    if eksik:
        print(f"UYARI: seslendirme yok ({', '.join(eksik)}); önce `seslendir` çalıştırın. Video seslendirmesiz ve altyazısız çıkar.", file=sys.stderr)
    master(is_ / "ses.wav", is_ / "ses-master.wav")
    out = []
    for f in formatlar:
        W, H = FORMATLAR[f]
        sessiz = cizim.video(s, W, H, is_ / f"sessiz-{f}.mp4")
        hedef = cikti / f"{kimlik}-{f}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(sessiz), "-i", str(is_ / "ses-master.wav"),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(hedef)], check=True)
        import kalite
        kalite.render_sonrasi(hedef)  # kalite.json + kontakt sayfası; render'ı durdurmaz
        out.append(hedef)
    W, H = FORMATLAR[formatlar[0]]
    ilk = s["sahneler"][0]
    out.append(cizim.kapak(s, W, H, s.get("kapak_t", ilk["_bas"] + min(ilk["sure"] - 0.2, zaman.cizim_suresi(ilk) + 1.5)),
                           cikti / f"{kimlik}-kapak.png"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("fontlar")
    for ad in ("denetle", "seslendir", "kare", "kontakt", "render"):
        p = alt.add_parser(ad)
        p.add_argument("senaryo")
        p.add_argument("-o", "--cikti")
        if ad == "seslendir":
            p.add_argument("--saglayici"); p.add_argument("--ses")
        if ad in ("kare", "kontakt"):
            p.add_argument("--format", default="16x9", choices=sorted(FORMATLAR))
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
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
    s["_sureler"] = sureler_oku(cikti / "seslendirme")
    hatalar = zaman.denetle(s, s["_sureler"])
    hatalar += [f"format {f} bilinmiyor ({', '.join(sorted(FORMATLAR))})" for f in s.get("format", []) if f not in FORMATLAR]
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    if a.komut == "denetle":
        print(f"tamam: {len(s['sahneler'])} sahne ({', '.join(x['tip'] for x in s['sahneler'])}), "
              f"{len(s['seslendirme'].get('satirlar', []))} seslendirme satırı, {s['sure']} sn")
        return 0
    if a.komut == "seslendir":
        import seslendirme
        try:
            k = seslendirme.senaryodan(s, cikti / "seslendirme", a.saglayici or "otomatik", a.ses)
        except seslendirme.SeslendirmeHatasi as e:
            print(f"HATA: {e}", file=sys.stderr)
            return 2
        for x in k["satirlar"]:
            print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
        hatalar = zaman.denetle(s, sureler_oku(cikti / "seslendirme"))
        for h in hatalar:
            print(f"HATA: {h}", file=sys.stderr)
        return 1 if hatalar else 0
    import fontlar
    if fontlar.eksikler():
        print(f"UYARI: yazı tipi eksik ({', '.join(fontlar.eksikler())}); önce `anlatim.py fontlar`. Yedek yazı tipiyle devam.", file=sys.stderr)
    import cizim
    if a.komut == "kare":
        for p in cizim.kareler(s, *FORMATLAR[a.format], a.an, cikti / "kareler"):
            print(p)
    elif a.komut == "kontakt":
        print(cizim.kontakt(s, *FORMATLAR[a.format], cikti / f"{s.get('kimlik', 'anlatim')}-kontakt-{a.format}.png"))
    else:
        for p in render(s, cikti, a.format or s.get("format") or ["16x9"]):
            print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
