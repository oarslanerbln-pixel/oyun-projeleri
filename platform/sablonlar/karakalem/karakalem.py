"""Karakalem şablonu: kurşun kalemle çizilen karikatürlü kişisel gelişim anlatımı (8–20 sn).

Bir defter sayfasında kalem önce büyük bir hedefi (dağ) çizer, karakter korkar; sonra her vuruşta bir
basamak çizilir ve karakter üstüne zıplar; sonunda kamera geri çekilir, basamakların tepeleri zirveye
çıkan bir eğridir, damga vurulur ve başlık el yazısıyla yazılır. Metin, karakterin görünüşü, renkler,
süre ve format tek senaryo dosyasından gelir; görüntü, kalem sesi, efektler, müzik ve seslendirme
aynı anlara kilitlidir. Seslendirme platform/ses adımından gelir (ElevenLabs; anahtar yoksa Piper "fahrettin").

    python3 platform/sablonlar/karakalem/karakalem.py fontlar
    python3 platform/sablonlar/karakalem/karakalem.py denetle   karakalem.json
    python3 platform/sablonlar/karakalem/karakalem.py seslendir karakalem.json   # sağlayıcı: seslendirme.saglayici (varsayılan ElevenLabs, yedek Piper)
    python3 platform/sablonlar/karakalem/karakalem.py kare      karakalem.json --an 1.0 4.2 8.6
    python3 platform/sablonlar/karakalem/karakalem.py render    karakalem.json [--format 9x16 16x9]
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
    return seslendirme.senaryodan(s, cikti / "seslendirme", saglayici, ses)


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
    kimlik = s.get("kimlik", "karakalem")
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
        out.append(hedef)
    W, H = FORMATLAR[formatlar[0]]  # kapak: damga ve başlık yazılmış son hâl, ilk formatta
    out.append(cizim.kapak(s, W, H, s.get("kapak_t", s["sure"] - 0.4), cikti / f"{kimlik}-kapak.png"))
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
            p.add_argument("--saglayici", help="senaryodaki seslendirme.saglayici yerine (varsayılan otomatik: ElevenLabs, yedek Piper)"); p.add_argument("--ses")
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
    cikti = cikti_klasoru(s, a.cikti)
    s["_sureler"] = sureler_oku(cikti / "seslendirme")
    hatalar = zaman.denetle(s, s["_sureler"])
    hatalar += [f"format {f} bilinmiyor ({', '.join(sorted(FORMATLAR))})" for f in s.get("format", []) if f not in FORMATLAR]
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    if a.komut == "denetle":
        ad = zaman.sahne(s, "adimlar")
        print(f"tamam: {ad['adet']} basamak, {len(s['seslendirme'].get('satirlar', []))} seslendirme satırı, {s['sure']} sn")
    elif a.komut == "seslendir":
        import seslendirme
        try:
            k = seslendir(s, cikti, a.saglayici or "otomatik", a.ses)
        except seslendirme.SeslendirmeHatasi as e:
            print(f"HATA: {e}", file=sys.stderr)
            return 2
        for x in k["satirlar"]:
            print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
        hatalar = zaman.denetle(s, sureler_oku(cikti / "seslendirme"))
        for h in hatalar:
            print(f"HATA: {h}", file=sys.stderr)
        return 1 if hatalar else 0
    else:
        import fontlar
        if fontlar.eksikler():
            print(f"UYARI: yazı tipi eksik ({', '.join(fontlar.eksikler())}); önce `karakalem.py fontlar`. Yedek yazı tipiyle devam.", file=sys.stderr)
        if a.komut == "kare":
            import cizim
            for p in cizim.kareler(s, *FORMATLAR[a.format], a.an, cikti / "kareler"):
                print(p)
        else:
            for p in render(s, cikti, a.format or s.get("format") or ["9x16"]):
                print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
