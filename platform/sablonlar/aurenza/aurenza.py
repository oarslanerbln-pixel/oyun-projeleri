"""Aurenza bindirme stili (kuyumcu Ferhat videoları, TR ve DE): veri.json → katman kareleri → kaynak videoya bindirme.

    python3 aurenza.py denetle <veri.json>                       # yapı, süre, güvenli alan kuralları
    python3 aurenza.py son-kare <kaynak.mp4> <son.jpg>            # finalin donmuş karesi (2160x3840)
    python3 aurenza.py kareler <veri.json> <kare_klasoru> [--kanca C] [--paralel 6]
    python3 aurenza.py bindir <kaynak.mp4> <kare_klasoru> <veri.json> <cikti.mp4> [--boyut 1440x2560]
    python3 aurenza.py srt <veri.json> <cikti.srt>

Kareler 30 fps, 2160x3840 saydam PNG; `son.t0` sonrası kareler opaktır (dede/fotoğraf finali + marka + takip kartı).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

KLASOR = Path(__file__).resolve().parent
TIPLER = {"alinti": ("metin", "imza"), "baslik": ("ust", "metin"), "kural": ("no", "metin"),
          "isim": ("ust", "ad", "s1"), "etiket": ("metin",)}
SON_ALANLAR = ("t0", "cta", "kare", "foto", "alinti", "imza", "marka", "markaAlt", "takip", "takipAlt")


def oku(yol: str | Path) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def denetle(v: dict) -> list[str]:
    """Hata listesi döndürür (boş = geçti)."""
    h: list[str] = []
    sure = v.get("sure")
    if not isinstance(sure, (int, float)) or sure <= 0:
        h.append("sure eksik")
        sure = 1e9
    kancalar = v.get("kancalar") or {}
    if not kancalar:
        h.append("kancalar boş: en az bir kanca başlık gerekir (ilk saniye)")
    for ad, k in kancalar.items():
        for alan in ("t0", "t1", "ust", "s1", "s2"):
            if alan not in k:
                h.append(f"kanca {ad}: {alan} eksik")
        if k.get("t1", 0) > 3.5:
            h.append(f"kanca {ad}: 3,5 sn'den uzun kalmamalı")
    if v.get("kancaSecim", "A") not in kancalar:
        h.append("kancaSecim kancalar içinde yok")
    for i, o in enumerate(v.get("ogeler", [])):
        tip = o.get("tip")
        if tip not in TIPLER:
            h.append(f"oge {i}: bilinmeyen tip {tip!r}")
            continue
        for alan in ("t0", "t1", *TIPLER[tip]):
            if alan not in o:
                h.append(f"oge {i} ({tip}): {alan} eksik")
        if o.get("t1", 0) <= o.get("t0", 0):
            h.append(f"oge {i} ({tip}): t1 <= t0")
        y = o.get("y")
        if y is not None and not 256 <= y <= 1997 - 380:
            h.append(f"oge {i} ({tip}): y={y} güvenli alanın dışında (256..1617)")
    onceki = -1.0
    for i, (a, b, metin) in enumerate(v.get("altyazi", [])):
        if b <= a or a < onceki - 1e-6:
            h.append(f"altyazı {i + 1}: zaman sırası bozuk")
        if not metin.strip():
            h.append(f"altyazı {i + 1}: boş")
        onceki = b
    s = v.get("son")
    if not s:
        h.append("son eksik: takip kartı stilin sabit parçasıdır")
    else:
        for alan in SON_ALANLAR:
            if alan not in s:
                h.append(f"son: {alan} eksik")
        if s.get("cta", 0) <= s.get("t0", 0):
            h.append("son: cta, t0'dan sonra olmalı")
        if sure - s.get("cta", 0) < 2.0:
            h.append("son: takip kartı en az 2 sn ekranda kalmalı")
    return h


def _zaman(s: float) -> str:
    ms = round(s * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt(v: dict) -> str:
    return "\n".join(f"{i}\n{_zaman(a)} --> {_zaman(b)}\n{m}\n" for i, (a, b, m) in enumerate(v["altyazi"], 1))


def son_kare(kaynak: str, cikti: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-sseof", "-0.05", "-i", kaynak,
                    "-vf", "scale=2160:3840:flags=lanczos", "-frames:v", "1", "-q:v", "1", cikti], check=True)


def kareler(veri: str, klasor: str, kanca: str | None, paralel: int, fps: int = 30) -> int:
    v = oku(veri)
    toplam = round(v["sure"] * fps)
    parca = -(-toplam // paralel)
    env = None
    if kanca:
        import os
        env = {**os.environ, "KANCA": kanca}
    islemler = [subprocess.Popen(["node", str(KLASOR / "kare.js"), veri, klasor, "all", str(fps), str(v["sure"]),
                                  str(s), str(min(s + parca, toplam))], env=env)
                for s in range(0, toplam, parca)]
    return max(p.wait() for p in islemler)


def bindir(kaynak: str, klasor: str, veri: str, cikti: str, boyut: str = "1440x2560", fps: int = 30) -> None:
    v = oku(veri)
    w, h = boyut.split("x")
    son = v["son"]["t0"]
    # -reinit_filter 0 + format=rgba: opak final PNG'leri RGB kaydedilir; yoksa geçişte siyah kare çıkar.
    fc = (f"color=c=black:s={boyut}:r={fps}:d={v['sure']}[bg];[0:v]scale={w}:{h}:flags=lanczos,setsar=1[s];"
          f"[bg][s]overlay=eof_action=pass[b];[1:v]format=rgba,scale={w}:{h}:flags=lanczos[o];"
          f"[b][o]overlay=eof_action=pass,format=yuv420p[v];[0:a]afade=t=out:st={son - 0.3:.2f}:d=0.3,apad[a]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", kaynak, "-framerate", str(fps),
                    "-reinit_filter", "0", "-i", f"{klasor}/%05d.png", "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-t", str(v["sure"]), "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
                    "-tune", "film", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-r", str(fps), cikti],
                   check=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("denetle").add_argument("veri")
    a = alt.add_parser("son-kare"); a.add_argument("kaynak"); a.add_argument("cikti")
    a = alt.add_parser("kareler"); a.add_argument("veri"); a.add_argument("klasor")
    a.add_argument("--kanca"); a.add_argument("--paralel", type=int, default=6)
    a = alt.add_parser("bindir"); a.add_argument("kaynak"); a.add_argument("klasor"); a.add_argument("veri")
    a.add_argument("cikti"); a.add_argument("--boyut", default="1440x2560")
    a = alt.add_parser("srt"); a.add_argument("veri"); a.add_argument("cikti")
    g = ap.parse_args(argv)
    if g.komut == "denetle":
        hatalar = denetle(oku(g.veri))
        for x in hatalar:
            print("HATA:", x)
        print("geçti" if not hatalar else f"{len(hatalar)} hata")
        return 1 if hatalar else 0
    if g.komut == "son-kare":
        son_kare(g.kaynak, g.cikti)
    elif g.komut == "kareler":
        return kareler(g.veri, g.klasor, g.kanca, g.paralel)
    elif g.komut == "bindir":
        bindir(g.kaynak, g.klasor, g.veri, g.cikti, g.boyut)
    elif g.komut == "srt":
        Path(g.cikti).write_text(srt(oku(g.veri)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
