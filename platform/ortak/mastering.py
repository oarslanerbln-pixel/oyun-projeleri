"""Ses mastering: ölçüm (EBU R128) ve sosyal video hedefine (-14 LUFS) getirme.

Bütün şablonlar aynı zinciri kullanır: 16 kHz üstü kesilir (AAC sonrası gerçek tepe aşımını
önler), kazanç hedef LUFS'a göre ayarlanır, tepe sınırlayıcıdan geçer, 48 kHz yazılır; gerçek tepe
-2 dBTP'yi aşarsa sınır indirilip yeniden yazılır.

    python3 platform/ortak/mastering.py olc   ses.wav
    python3 platform/ortak/mastering.py master ses.wav ses-master.wav [--hedef -14]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HEDEF_LUFS = -14.0
TEPE_HEDEF = -2.0  # dBTP, master WAV için; AAC sonrası teslimde ≤ -1 kalır
ON_FILTRE = "lowpass=f=16000:poles=2"


def olc(yol: str | Path, on_filtre: str | None = ON_FILTRE) -> dict:
    """Bütünleşik ses yüksekliği (LUFS), ses yüksekliği aralığı (LU) ve gerçek tepe (dBTP)."""
    af = ",".join(x for x in (on_filtre, "ebur128=framelog=quiet:peak=true") if x)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(yol), "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True)
    ozet = r.stderr[r.stderr.rfind("Summary:"):]
    if r.returncode != 0 or "Summary:" not in r.stderr:
        raise RuntimeError(f"ses ölçülemedi: {yol}\n{r.stderr[-400:]}")

    def sayi(ad: str) -> float | None:
        m = re.search(rf"{ad}:\s+(-?[\d.]+|-inf)", ozet)
        if not m:
            return None
        return float("-inf") if m.group(1) == "-inf" else float(m.group(1))

    return {"lufs": sayi("I"), "lra": sayi("LRA"), "tepe_dbtp": sayi("Peak")}


def lufs(yol: str | Path) -> float:
    return olc(yol)["lufs"]


def master(gir: str | Path, cik: str | Path, hedef: float = HEDEF_LUFS, limit: float = 0.75, sr: int = 48000,
           tepe_hedef: float = TEPE_HEDEF) -> dict:
    """`gir` sesini `hedef` LUFS'a getirip `cik`'a yazar; ölçülen giriş değerlerini döndürür.

    Sınırlayıcı örnek tepesine bakar; örnekler arası (gerçek) tepe yine de taşabilir ve AAC
    kodlaması üstüne ~1 dB ekler. Bu yüzden çıktının gerçek tepesi ölçülür; `tepe_hedef` aşılırsa
    sınır o kadar indirilip bir kez daha yazılır (platform yeniden kodlayınca kırpılmasın).
    """
    o = olc(gir)
    kazanc = hedef - o["lufs"] if o["lufs"] not in (None, float("-inf")) else 0.0
    for _ in range(3):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(gir), "-af",
                        f"{ON_FILTRE},volume={kazanc:.2f}dB,alimiter=limit={limit:.4f}:level=false",
                        "-ar", str(sr), str(cik)], check=True)
        tp = olc(cik, on_filtre=None)["tepe_dbtp"]
        if tp is None or tp <= tepe_hedef:
            break
        limit *= 10 ** ((tepe_hedef - tp - 0.1) / 20)
    return o


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("olc").add_argument("ses")
    m = alt.add_parser("master")
    m.add_argument("gir")
    m.add_argument("cik")
    m.add_argument("--hedef", type=float, default=HEDEF_LUFS)
    a = ap.parse_args(argv)
    if a.komut == "olc":
        o = olc(a.ses)
        print(f"{o['lufs']:.1f} LUFS, LRA {o['lra']:.1f} LU, gerçek tepe {o['tepe_dbtp']:.1f} dBTP")
    else:
        master(a.gir, a.cik, a.hedef)
        print(a.cik)
    return 0


if __name__ == "__main__":
    sys.exit(main())
