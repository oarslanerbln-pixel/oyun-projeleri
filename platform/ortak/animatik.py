"""Hızlı taslak (animatik): onaydan önce hareketi gösteren küçük, sessiz bir video (beyin fırtınası 4.3).

    python3 platform/ortak/animatik.py ornekler/hamurkar-firin/tek-cizgi.json -o animatik.mp4
    python3 platform/ortak/animatik.py vhs=is/vhs.json --format 16x9 --kare-hizi 6 -o is/animatik-vhs.mp4

Videonun bütün süresinden saniyede `--kare-hizi` kare şablonun `kare` komutuyla çizilir (ses, efekt ve
kodlama yok), kareler küçültülüp `--oynatma` fps ile art arda oynatılır. Varsayılan 4 kare/sn örnek ve 12 fps
oynatma, yani 3 kat hızlı bir özet: 10 sn'lik video ~3,5 sn'lik animatik olur. Her karenin altında videodaki
saniyesi yazar. Tam render değildir; yalnız akışı, geçişleri ve yazıların yerini görmek içindir.

Kare sayısı `--en-fazla` ile sınırlanır (uzun videoda örnek seyrekleşir). Carousel gibi saniyesi olmayan
şablonlarda animatik yapılmaz.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
import onizleme  # noqa: E402
from formatlar import anahtar  # noqa: E402

VARSAYILAN_SURE = 10.0


def sure_bul(senaryo: dict) -> float | None:
    """Senaryonun süresi: "sure", yoksa sahnelerin toplamı. Carousel (slayt) için None."""
    if isinstance(senaryo.get("slaytlar"), list):
        return None
    if isinstance(senaryo.get("sure"), (int, float)) and senaryo["sure"] > 0:
        return float(senaryo["sure"])
    sahneler = senaryo.get("sahneler")
    if isinstance(sahneler, list):
        toplam = sum(float(x.get("sure", 0)) for x in sahneler if isinstance(x, dict))
        if toplam > 0:
            return toplam
    return VARSAYILAN_SURE


def anlar(sure: float, kare_hizi: float, en_fazla: int) -> list[float]:
    n = max(8, min(en_fazla, round(sure * kare_hizi)))
    adim = sure / n
    return [round(adim * (i + 0.5), 2) for i in range(n)]


def _etiketle(k, metin: str):
    from PIL import ImageDraw, ImageFont
    try:
        yazi = ImageFont.load_default(size=14)
    except TypeError:  # Pillow < 10.1
        yazi = ImageFont.load_default()
    d = ImageDraw.Draw(k)
    y = k.height - 24
    d.rectangle([0, y, k.width, k.height], fill=(20, 20, 20))
    d.text((8, y + 4), metin, fill=(250, 250, 250), font=yazi)
    return k


def animatik(girdi: str, hedef: Path, fmt: str = "9x16", kare_hizi: float = 4.0, oynatma: int = 12,
             genislik: int = 360, en_fazla: int = 48) -> dict:
    """`girdi` = "senaryo.json" ya da "stil=senaryo.json". Rapor döner; hata varsa "hata" alanı dolu."""
    from PIL import Image
    ad, _, yol = girdi.rpartition("=")
    yol = Path(yol)
    senaryo = json.loads(yol.read_text(encoding="utf-8"))
    ad = onizleme.sablon_bul(senaryo, yol, ad or None)
    rapor = {"stil": ad, "senaryo": str(yol), "dosya": None}
    sure = sure_bul(senaryo)
    if sure is None:
        rapor["hata"] = "saniyesi olmayan şablon (carousel), animatik yok"
        return rapor
    if not shutil.which("ffmpeg"):
        rapor["hata"] = "ffmpeg yok"
        return rapor
    an = anlar(sure, kare_hizi, en_fazla)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        r = subprocess.run(onizleme.komut(ad, yol, an, anahtar(fmt), tmp / "k"), capture_output=True, text=True)
        pngler = [Path(x.strip()) for x in r.stdout.splitlines() if x.strip().endswith(".png")]
        if r.returncode != 0 or not pngler:
            rapor["hata"] = (r.stderr.strip().splitlines() or [f"çıkış kodu {r.returncode}"])[-1]
            return rapor
        for i, (t, p) in enumerate(zip(an, pngler)):
            k = Image.open(p).convert("RGB")
            h = round(k.height * genislik / k.width / 2) * 2
            _etiketle(k.resize((genislik, h), Image.LANCZOS), f"{ad} · {t:.1f} / {sure:g} sn").save(tmp / f"{i:04d}.png")
        hedef = Path(hedef)
        hedef.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(oynatma),
                            "-i", str(tmp / "%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
                            "-movflags", "+faststart", str(hedef)], capture_output=True, text=True)
        if r.returncode != 0:
            rapor["hata"] = (r.stderr.strip().splitlines() or ["ffmpeg hatası"])[-1]
            return rapor
    rapor.update(dosya=str(hedef), kare=len(pngler), sure=sure, animatik_sn=round(len(pngler) / oynatma, 1),
                 hiz=round(sure / (len(pngler) / oynatma), 1))
    return rapor


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("senaryo", help="senaryo.json ya da stil=senaryo.json")
    ap.add_argument("--format", default="9x16")
    ap.add_argument("--kare-hizi", type=float, default=4.0, help="videonun saniyesi başına çizilen kare")
    ap.add_argument("--oynatma", type=int, default=12, help="animatiğin fps'i")
    ap.add_argument("--genislik", type=int, default=360)
    ap.add_argument("--en-fazla", type=int, default=48)
    ap.add_argument("-o", "--cikti", default="animatik.mp4")
    a = ap.parse_args(argv)
    r = animatik(a.senaryo, Path(a.cikti), a.format, a.kare_hizi, a.oynatma, a.genislik, a.en_fazla)
    if r.get("hata"):
        print(f"HATA: {r['stil']}: {r['hata']}", file=sys.stderr)
        return 1
    print(f"{r['dosya']} ({r['kare']} kare, {r['animatik_sn']} sn, {r['hiz']}x hız)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
