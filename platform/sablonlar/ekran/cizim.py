"""Ekran stillerinin görüntüsü: ortak yardımcılar (yazı tipi, güvenli alan, yazı sığdırma), kare ve video akışı.

Çizim numpy + Pillow ile yapılır (skia gerekmez), her stil kendi modülünde bir `Cizici` sınıfıdır:
`tabela.py` (kalkış tabelası), `vhs.py`, `akis_alani.py`. Kalkış tabelası ve VHS karesi `t` anının saf
fonksiyonudur; akış alanı bir parçacık benzetimidir, tek kare istenince 3 sn önceden ısıtılarak çizilir.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import zaman

FONT_DIZINLERI = [os.environ.get("KINETIK_FONT_DIZINI", ""), "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
                  str(Path.home() / ".cache" / "studyo" / "fonts"), str(Path.home() / ".fonts"), "/Library/Fonts",
                  str(Path.home() / "Library/Fonts")]
FONTLAR = {
    "black": ["Inter-Black.otf", "InterDisplay-Black.otf", "Inter-ExtraBold.otf", "Inter-800.ttf", "Inter-ExtraBold.ttf"],
    "bold": ["Inter-Bold.otf", "Inter-ExtraBold.otf", "Inter-700.ttf", "Inter-Bold.ttf", "Inter-800.ttf"],
    "medium": ["Inter-Medium.otf", "Inter-SemiBold.otf", "Inter-600.ttf", "Inter-Regular.otf", "Inter-Bold.otf"],
    "mono": ["DejaVuSansMono-Bold.ttf"],
}
MONO_DIZINLERI = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/Library/Fonts"]


def font_yolu(tur: str) -> str:
    dizinler = MONO_DIZINLERI + FONT_DIZINLERI if tur == "mono" else FONT_DIZINLERI
    for d in dizinler:
        for ad in FONTLAR[tur]:
            if d and os.path.exists(os.path.join(d, ad)):
                return os.path.join(d, ad)
    if tur == "mono":
        return font_yolu("bold")
    raise RuntimeError("Inter yazı tipi bulunamadı: `apt-get install fonts-inter` ya da KINETIK_FONT_DIZINI")


_FONT_ONBELLEK: dict = {}


def font(tur: str, boy: float) -> ImageFont.FreeTypeFont:
    k = (tur, int(round(boy)))
    if k not in _FONT_ONBELLEK:
        _FONT_ONBELLEK[k] = ImageFont.truetype(font_yolu(tur), max(4, k[1]))
    return _FONT_ONBELLEK[k]


def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3


def format_adi(W: int, H: int) -> str:
    return min(zaman.FORMATLAR, key=lambda f: abs(int(f.split("x")[0]) / int(f.split("x")[1]) - W / H))


def guvenli(W: int, H: int) -> tuple[float, float, float, float]:
    """Yazının durabileceği kutu (x0, y0, x1, y1): platform arayüzlerinin altında kalmaz."""
    ust, alt, yan = zaman.GUVENLI[format_adi(W, H)]
    return yan * W, ust * H, (1 - yan) * W, (1 - alt) * H


def sahne_no(s: dict, t: float) -> int:
    i = 0
    for j, sh in enumerate(s["sahneler"]):
        if sh["bas"] <= t + 1e-9:
            i = j
    return i


def tane(a: np.ndarray, rng: np.random.Generator, guc: float) -> np.ndarray:
    """Her karede değişen üçgen dağılımlı tane: düz zemin ve sönümlenen izlerde 8 bit basamaklanmasını kırar."""
    n = (rng.random(a.shape[:2], np.float32) - rng.random(a.shape[:2], np.float32)) * guc
    return np.clip(a.astype(np.float32) + n[:, :, None], 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- yazı sığdırma

def sigdir(metin: str, tur: str, max_w: float, max_h: float, boy: float, buyuk: bool = False,
           satir_ara: float = 1.12, harf_ara: float = 0.0, en_az: float = 10):
    """Kelimeleri max_w içine sarar, toplam yükseklik max_h'yi aşarsa yazıyı küçültür.
    Döner: (font, satırlar [[(kelime, vurgu), ...]], satır yüksekliği, satır genişlikleri). Kelime bölünmez."""
    satirlar0 = zaman.parcala(zaman.tr_buyuk(metin) if buyuk else metin)
    while True:
        f = font(tur, boy)
        bosluk = f.getlength(" ") + harf_ara * boy
        olc = lambda k: f.getlength(k) + harf_ara * boy * max(0, len(k) - 1)  # noqa: E731
        out, sigmadi = [], False
        for satir in satirlar0:
            cur, w = [], 0.0
            for k, v in satir:
                kw = olc(k)
                if kw > max_w:
                    sigmadi = True
                ek = kw + (bosluk if cur else 0)
                if cur and w + ek > max_w:
                    out.append((cur, w)); cur, w = [], 0.0; ek = kw
                cur.append((k, v)); w += ek
            out.append((cur, w))
        sh = boy * satir_ara
        if not sigmadi and sh * len(out) <= max_h or boy <= en_az:
            return f, [o[0] for o in out], sh, [o[1] for o in out]
        boy *= 0.94


def yazi_ciz(d: ImageDraw.ImageDraw, f, satirlar, sh, genislikler, cx, cy, renk, vurgu, harf_ara=0.0, hiza="orta", x0=None,
             golge=None):
    """Satırları (cx, cy) merkezli bloğa çizer; vurgulu kelimeler `vurgu` rengiyle."""
    boy = f.size
    ust = cy - sh * len(satirlar) / 2
    for i, (satir, w) in enumerate(zip(satirlar, genislikler)):
        x = cx - w / 2 if hiza == "orta" else x0
        y = ust + i * sh + sh / 2 + 0.36 * boy  # taban çizgisi: büyük harf yüksekliği (~0,72 boy) satırda ortalanır
        for j, (k, v) in enumerate(satir):
            if j:
                x += f.getlength(" ") + harf_ara * boy
            for ch in (k if harf_ara else [k]):
                if golge:
                    d.text((x + golge[0], y + golge[1]), ch, font=f, fill=golge[2], anchor="ls")
                d.text((x, y), ch, font=f, fill=vurgu if v else renk, anchor="ls")
                x += f.getlength(ch) + (harf_ara * boy if harf_ara else 0)
            if harf_ara:
                x -= harf_ara * boy


# ---------------------------------------------------------------- akış

def cizici(s: dict, W: int, H: int):
    st = s["stil"]
    if st == "kalkis-tabelasi":
        import tabela as m
    elif st == "vhs":
        import vhs as m
    else:
        import akis_alani as m
    return m.Cizici(s, W, H)


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    klasor.mkdir(parents=True, exist_ok=True)
    out = []
    for t in anlar:
        c = cizici(s, W, H)
        a = c.tek_kare(t) if hasattr(c, "tek_kare") else c.kare(t)
        p = klasor / f"{s.get('kimlik', 'ekran')}-{W}x{H}-{t:05.2f}.png"
        Image.fromarray(a).save(p)
        out.append(p)
    return out


def video(s: dict, W: int, H: int, yol_: Path) -> Path:
    yol_ = Path(yol_)
    yol_.parent.mkdir(parents=True, exist_ok=True)
    c = cizici(s, W, H)
    fps = s["fps"]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-tune", "grain",
                           "-pix_fmt", "yuv420p", str(yol_)], stdin=subprocess.PIPE)
    for i in range(int(round(fps * s["sure"]))):
        ff.stdin.write(np.ascontiguousarray(c.kare(i / fps)).tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise RuntimeError(f"ffmpeg başarısız: {yol_}")
    return yol_
