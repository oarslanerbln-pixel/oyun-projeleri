"""Sessiz çalıştırıcı: uzun ya da çok yazan bir komutu çalıştırır, tam çıktıyı log dosyasına yazar,
ekrana yalnız çıkış kodunu, hata satırlarını ve son birkaç satırı basar.

    python3 platform/ortak/sessiz.py -- ffmpeg -i a.mp4 ... cikti.mp4
    python3 platform/ortak/sessiz.py --satir 5 --log /tmp/render.log -- python3 stil.py uret senaryo.json

Neden: Claude'un okuduğu her satır thread'in bağlamına girer ve sonraki her adımda yeniden okunur
(bkz. CLAUDE.md, platform/docs/uretim-standardi.md §5). Bir render logunun 2.000 satırı, thread
kapanana kadar her adımda tekrar ücretlendirilir. Gerekirse tam log sonradan `grep` ile okunur.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HATA = re.compile(r"error|hata|traceback|exception|failed|fatal|kaldi", re.I)


def ozet(satirlar: list[str], son: int, hata_siniri: int = 10) -> list[str]:
    """Hata içeren satırlardan en fazla `hata_siniri` tanesi + son `son` satır, tekrarsız ve sırayla."""
    hatalar = [i for i, s in enumerate(satirlar) if HATA.search(s)][:hata_siniri]
    secili = sorted(set(hatalar) | set(range(max(0, len(satirlar) - son), len(satirlar))))
    out, onceki = [], -1
    for i in secili:
        if onceki >= 0 and i != onceki + 1:
            out.append("…")
        out.append(satirlar[i][:300])
        onceki = i
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--satir", type=int, default=12, help="ekrana basılacak son satır sayısı")
    ap.add_argument("--log", type=Path, help="tam çıktının yazılacağı dosya (yoksa geçici dosya)")
    ap.add_argument("komut", nargs=argparse.REMAINDER, help="-- ardından çalıştırılacak komut")
    a = ap.parse_args(argv)
    komut = a.komut[1:] if a.komut[:1] == ["--"] else a.komut
    if not komut:
        ap.error("komut yok: sessiz.py -- <komut>")
    log = a.log or Path(tempfile.mkstemp(prefix="sessiz-", suffix=".log")[1])
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(log, "w") as f:
        kod = subprocess.run(komut, stdout=f, stderr=subprocess.STDOUT).returncode
    satirlar = log.read_text(errors="replace").splitlines()
    print(f"[sessiz] çıkış {kod} · {time.time() - t0:.0f} sn · {len(satirlar)} satır · log: {log}")
    for s in ozet(satirlar, a.satir):
        print(s)
    return kod


if __name__ == "__main__":
    sys.exit(main())
