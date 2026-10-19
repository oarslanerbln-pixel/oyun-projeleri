#!/usr/bin/env python3
"""Animasyon şablonu: brif → metin → çekim listesi → animatik (mimari §5.1).

Kullanım:
  animasyon.py denetle <proje.json>
  animasyon.py uret <proje.json> [-o <çıktı>]     varsayılan çıktı: <proje>/cikti/
  animasyon.py yeni <klasör> [--ad "Marka Adı"]  şablondan yeni proje
  animasyon.py render <proje.json> [-o <çıktı>] [--kurgu AD] [--teslim AD] [--dil tr] [--muzik dosya] [--yazdir]
                                                 MP4; varsayılan çıktı: <proje>/cikti/render/

Çıkış kodu: 0 temiz (uyarı olabilir), 1 doğrulama hatası, 2 kullanım hatası.
Yalnız Python standart kitaplığı; render ayrıca ffmpeg ister.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _yollar  # noqa: E402,F401
import cizim  # noqa: E402
import proje as proje_mod  # noqa: E402
import render as render_mod  # noqa: E402
from metin import HATA, has_errors  # noqa: E402

_TR = str.maketrans("çğıöşüâîû", "cgiosuaiu")
SABLON = Path(__file__).resolve().parent / "sablon"


def _rapor(bulgular) -> None:
    for x in sorted(bulgular, key=lambda x: (x.seviye != HATA, x.yer)):
        print(f"  {x}")
    hata = sum(x.seviye == HATA for x in bulgular)
    print(f"HATA: {hata} · UYARI: {len(bulgular) - hata}")


def cmd_denetle(args) -> int:
    p, b = proje_mod.yukle(args.proje)
    _rapor(b)
    if p is not None:
        print(f"Tamam: {p.marka.ad} · " + "; ".join(
            f"{k.ad} {k.sure:g} sn → {', '.join(a.ad for a in k.teslim)}" for k in p.kurgular))
    return 1 if has_errors(b) else 0


def cmd_uret(args) -> int:
    p, b = proje_mod.yukle(args.proje)
    _rapor(b)
    if p is None:
        print("Üretim yapılmadı: önce hataları düzeltin.")
        return 1
    out = Path(args.out) if args.out else p.klasor / "cikti"
    written = cizim.uret(p, out)
    print(f"{len(written)} dosya yazıldı: {out}")
    for k in p.kurgular:
        for a in k.teslim:
            print(f"  animatik: {out / k.ad / a.ad / 'animatik.html'}")
    return 0


def cmd_render(args) -> int:
    p, b = proje_mod.yukle(args.proje)
    if p is None or has_errors(b):
        _rapor(b)
        print("Render yapılmadı: önce hataları düzeltin.")
        return 1
    out = Path(args.out) if args.out else p.klasor / "cikti" / "render"
    kok = proje_mod.depo_koku(Path(args.proje).resolve().parent)
    try:
        yazilan, rb = render_mod.render(p, kok, out, args.kurgu, args.teslim, args.dil,
                                        Path(args.muzik) if args.muzik else None, args.yazdir)
    except (RuntimeError, FileNotFoundError) as e:
        print(f"Render başarısız: {e}", file=sys.stderr)
        return 1
    _rapor(b + rb)
    if has_errors(rb):
        return 1
    for f in yazilan:
        bilgi = render_mod.olcum(f)
        v = next(s for s in bilgi["streams"] if s["codec_type"] == "video")
        izler = ", ".join(sorted({s["codec_type"] for s in bilgi["streams"]}))
        print(f"  {f} · {v['width']}x{v['height']} · {float(bilgi['format']['duration']):.2f} sn · {izler}")
    return 0


def cmd_yeni(args) -> int:
    hedef = Path(args.klasor).resolve()
    if hedef.exists() and any(hedef.iterdir()):
        print(f"{hedef} boş değil; üstüne yazılmadı.", file=sys.stderr)
        return 2
    ad = args.ad or hedef.name
    kimlik = re.sub(r"[^a-z0-9]+", "-", ad.replace("İ", "i").casefold().translate(_TR)).strip("-") or "marka"
    kok = proje_mod.depo_koku(hedef.parent if not hedef.exists() else hedef)
    try:
        yol = hedef.relative_to(kok).as_posix()
    except ValueError:
        yol = hedef.as_posix()
    degerler = {"{{kimlik}}": kimlik, "{{ad}}": ad, "{{AD}}": ad.upper(), "{{yol}}": yol}
    for src in sorted(SABLON.rglob("*")):
        if src.is_dir():
            continue
        text = src.read_text(encoding="utf-8")
        for k, v in degerler.items():
            text = text.replace(k, v)
        dst = hedef / src.relative_to(SABLON)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
    print(f"Yeni animasyon projesi: {hedef}")
    print(f"  denetle: python3 platform/sablonlar/animasyon/animasyon.py denetle {yol}/proje.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="animasyon.py", description="Animasyon şablonu: denetle, üret, yeni.")
    sub = parser.add_subparsers(dest="komut", required=True)
    p = sub.add_parser("denetle", help="projeyi doğrula")
    p.add_argument("proje")
    p.set_defaults(func=cmd_denetle)
    p = sub.add_parser("uret", help="doğrula ve animatik, belirteç, altyazı üret")
    p.add_argument("proje")
    p.add_argument("-o", "--out")
    p.set_defaults(func=cmd_uret)
    p = sub.add_parser("render", help="doğrula ve her kurgu × ön ayar için MP4 yaz (ffmpeg)")
    p.add_argument("proje")
    p.add_argument("-o", "--out")
    p.add_argument("--kurgu", help="yalnız bu kurgu")
    p.add_argument("--teslim", help="yalnız bu ön ayar")
    p.add_argument("--dil", help="ekran yazısının dili (varsayılan: projenin ilk dili)")
    p.add_argument("--muzik", help="müzik dosyası; ön ayarın LUFS değerine çekilir")
    p.add_argument("--yazdir", action="store_true", help="ffmpeg komutlarını çalıştırmadan yaz")
    p.set_defaults(func=cmd_render)
    p = sub.add_parser("yeni", help="şablondan yeni proje")
    p.add_argument("klasor")
    p.add_argument("--ad")
    p.set_defaults(func=cmd_yeni)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
