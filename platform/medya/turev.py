#!/usr/bin/env python3
"""Tek geniş klipten teslim ön ayarına türev: odak merkezli kırpma, ölçek, loudness.

YZ klibi bir kez en geniş oranda üretilir; dikey, kare ve 4:5 sürümleri çekim
listesindeki `odak_x/odak_y`'ye göre kırpılır (her oran için ayrı üretimden
ucuz). Loudness ön ayarın `lufs` değerine çekilir; `lufs` boşsa ses atılır.

Kullanım:
  turev.py <girdi> <çıktı> <ön ayar> [--odak X Y] [--yazdir]

`--yazdir` ffmpeg komutunu çalıştırmadan yazar. ffmpeg ve ffprobe gerekir.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

import teslim

BUYUTME_SINIRI = 1.5  # bunun üstünde büyütme gözle görülür yumuşar


def kirpma(iw: int, ih: int, ow: int, oh: int, odak_x: float = 0.5, odak_y: float = 0.5) -> tuple[int, int, int, int]:
    """Girdiden hedef oranda en büyük pencere: (w, h, x, y). Odak noktası pencerenin
    ortasına gelecek biçimde kaydırılır, kenarda durur. Boyutlar çifttir (yuv420p)."""
    hedef = ow / oh
    if iw / ih > hedef:
        h, w = ih, round(ih * hedef)
    else:
        w, h = iw, round(iw / hedef)
    w, h = min(w - w % 2, iw - iw % 2), min(h - h % 2, ih - ih % 2)
    x = min(max(round(odak_x * iw - w / 2), 0), iw - w)
    y = min(max(round(odak_y * ih - h / 2), 0), ih - h)
    return w, h, x, y


def olc(girdi: str | Path) -> tuple[int, int, bool]:
    """ffprobe ile (genişlik, yükseklik, ses var mı)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                          "-of", "json", str(girdi)], check=True, capture_output=True, text=True).stdout
    akislar = json.loads(out).get("streams", [])
    video = next(s for s in akislar if s.get("codec_type") == "video")
    return video["width"], video["height"], any(s.get("codec_type") == "audio" for s in akislar)


def komut(girdi: str | Path, cikti: str | Path, a: teslim.OnAyar, iw: int, ih: int, ses: bool,
          odak_x: float = 0.5, odak_y: float = 0.5) -> list[str]:
    w, h, x, y = kirpma(iw, ih, a.genislik, a.yukseklik, odak_x, odak_y)
    vf = f"crop={w}:{h}:{x}:{y},scale={a.genislik}:{a.yukseklik}:flags=lanczos,setsar=1"
    cmd = ["ffmpeg", "-y", "-i", str(girdi), "-vf", vf, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p"]
    if ses and a.lufs is not None:
        cmd += ["-af", f"loudnorm=I={a.lufs:g}:TP=-1:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        cmd += ["-an"]
    return cmd + [str(cikti)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="turev.py", description="Teslim ön ayarına türev üretir.")
    parser.add_argument("girdi")
    parser.add_argument("cikti")
    parser.add_argument("on_ayar")
    parser.add_argument("--odak", nargs=2, type=float, default=(0.5, 0.5), metavar=("X", "Y"))
    parser.add_argument("--yazdir", action="store_true")
    args = parser.parse_args(argv)
    on_ayarlar = teslim.yukle()
    if args.on_ayar not in on_ayarlar:
        print(f"bilinmeyen ön ayar {args.on_ayar!r}; {', '.join(on_ayarlar)}", file=sys.stderr)
        return 2
    a = on_ayarlar[args.on_ayar]
    iw, ih, ses = olc(args.girdi)
    w = kirpma(iw, ih, a.genislik, a.yukseklik, *args.odak)[0]
    if a.genislik / w > BUYUTME_SINIRI:
        print(f"UYARI: kırpılan pencere {w} px, {a.genislik} px'e {a.genislik / w:.1f} kat büyütülüyor; "
              "bu oran için klibi daha yüksek çözünürlükte ya da doğrudan bu oranda üretin", file=sys.stderr)
    cmd = komut(args.girdi, args.cikti, a, iw, ih, ses, *args.odak)
    if args.yazdir:
        print(shlex.join(cmd))
        return 0
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
