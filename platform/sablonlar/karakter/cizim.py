"""Karakter şablonunun görüntüsü: düz zemin, vurgu dairesi, karakter (görünüm katmanı), nesne ve az yazı (skia).

Sahne düzeni, yazı ve video kodlama bütün görünümlerde ortaktır; karakterin ve nesnelerin nasıl çizileceğini
`gorunumler/<stil>.py` içindeki `Gorunum` sınıfı belirler. Her kare `t` anının saf fonksiyonudur.
"""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import agiz as agiz_mod
import senaryo

# Format düzeni: karakter boyu (H oranı), ayak çizgisi, karakterin yatay merkezi ve gezinme payı (W oranı),
# yazı kutusu (merkez x, merkez y, en fazla genişlik, punto: W oranı). Dikeyde her şey Reels güvenli alanında:
# üst %10 ve alt %22 boş kalır (yazının alt kenarı ≤ 0.77 H), yazı sağdaki beğen/yorum sütununa taşmaz.
DUZEN = {
    "9x16": dict(boy=0.46, ayak=0.635, cx=0.50, gez=0.20, yazi=(0.47, 0.715, 0.74, 0.088)),
    "16x9": dict(boy=0.70, ayak=0.875, cx=0.30, gez=0.10, yazi=(0.68, 0.50, 0.50, 0.052)),
    "1x1": dict(boy=0.58, ayak=0.715, cx=0.50, gez=0.20, yazi=(0.48, 0.835, 0.78, 0.070)),
    "4x5": dict(boy=0.56, ayak=0.680, cx=0.50, gez=0.20, yazi=(0.48, 0.810, 0.78, 0.074)),
}
FONT_YOLLARI = ["/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", "/usr/share/fonts/truetype/inter/Inter-ExtraBold.ttf"]


def font_bul() -> str:
    for p in FONT_YOLLARI:
        if Path(p).exists():
            return p
    r = subprocess.run(["fc-match", "-f", "%{file}", "Inter:weight=205"], capture_output=True, text=True)
    if r.returncode == 0 and "inter" in r.stdout.lower():
        return r.stdout.strip()
    raise RuntimeError("Inter yazı tipi bulunamadı: `apt-get install fonts-inter`")


def renk(hex_: str, alfa: float = 1.0) -> int:
    import skia
    h = hex_.lstrip("#")
    return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(255 * max(0.0, min(1.0, alfa))))


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def out_back(p, s=1.7): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def format_adi(W: int, H: int) -> str:
    oran = W / H
    return min(DUZEN, key=lambda f: abs(oran - {"9x16": 9 / 16, "16x9": 16 / 9, "1x1": 1, "4x5": 0.8}[f]))


class Cizici:
    def __init__(self, s: dict, W: int, H: int, seslendirme: Path | None = None):
        import skia
        self.s, self.W, self.H = s, W, H
        self.d = DUZEN[format_adi(W, H)]
        self.boy = self.d["boy"] * H
        self.pal = s["palet"]
        self.yazi_tipi = skia.Typeface.MakeFromFile(font_bul())
        gor = importlib.import_module(f"gorunumler.{s['stil']}")
        self.gorunum = gor.Gorunum(s, self)
        self.agiz = agiz_mod.Agiz()
        self.agiz_kaynak = {}
        for x in senaryo.konusan_satirlar(s):
            if seslendirme:
                self.agiz_kaynak[x["id"]] = self.agiz.ekle(x["t"], seslendirme / f"{x['id']}.wav",
                                                           seslendirme / f"{x['id']}.hizalama.json")

    # karakter birimi → ekran
    def ekran(self, x_konum: float):
        cx = (self.d["cx"] + self.d["gez"] * x_konum) * self.W
        ay = self.d["ayak"] * self.H
        return lambda p: (cx + p[0] * self.boy, ay - p[1] * self.boy)

    def yazi(self, cv, metin: str, punto: float, x: float, y: float, renk_: int, maks_gen: float):
        """Ortalanmış, gerekirse iki satıra bölünen ve genişliğe sığdırılan yazı; y satır bloğunun ortası."""
        import skia
        f = skia.Font(self.yazi_tipi, punto)
        satirlar = [metin]
        if f.measureText(metin) > maks_gen and " " in metin:
            k = metin.split(" ")
            en_iyi = min(range(1, len(k)), key=lambda i: max(f.measureText(" ".join(k[:i])), f.measureText(" ".join(k[i:]))))
            satirlar = [" ".join(k[:en_iyi]), " ".join(k[en_iyi:])]
        gen = max(f.measureText(x_) for x_ in satirlar)
        if gen > maks_gen:
            f = skia.Font(self.yazi_tipi, punto * maks_gen / gen)
        aralik = f.getSize() * 1.12
        paint = skia.Paint(AntiAlias=True, Color=renk_)
        y0 = y - aralik * (len(satirlar) - 1) / 2 + f.getSize() * 0.36
        for i, x_ in enumerate(satirlar):
            cv.drawString(x_, x - f.measureText(x_) / 2, y0 + i * aralik, f, paint)

    def kare(self, cv, t: float):
        import skia
        s = self.s
        cv.clear(renk(self.pal["zemin"]))
        g, y, xk = senaryo.durum(s, t, self.agiz)
        ekr = self.ekran(xk)
        # vurgu dairesi: düz dolgu (gradyan yok, bantlanmaz); başlangıçta açılır
        p = out_back(prog(t, 0.08, 0.45), 1.3)
        if p > 0:
            mx, my = ekr((g.boyun[0], g.boyun[1] - 0.06))
            cv.drawCircle(mx, my, 0.30 * self.boy * p, skia.Paint(AntiAlias=True, Color=renk(self.pal["vurgu"])))
        sh = senaryo.sahne_at(s, t)
        n = sh.get("nesne")
        self.gorunum.karakter(cv, g, y, ekr)
        if n:
            son = n.get("son", sh["_son"])
            gir = out_back(prog(t, n["t"], 0.32))
            cik = 1 - prog(t, son - 0.16, 0.16) if son < s["sure"] else 1.0
            if gir * cik > 0.001:
                self.gorunum.nesne(cv, n, g, ekr, gir * cik, t - n["t"])
        self._yazilar(cv, t)

    def _yazilar(self, cv, t: float):
        yx, yy, ymaks, punto = self.d["yazi"]
        for sh in self.s["sahneler"]:
            yz = sh.get("yazi")
            if not yz or t < yz["t"]:
                continue
            son = yz.get("son", sh["_son"])
            if t >= son:
                continue
            gir = out_cubic(prog(t, yz["t"], senaryo.YAZI_SN))
            cik = 1 - prog(t, son - 0.18, 0.18) if son < self.s["sure"] else 1.0
            a = gir * cik
            if a <= 0:
                continue
            self.yazi(cv, yz["metin"], punto * self.W, yx * self.W, yy * self.H + (1 - gir) * 0.02 * self.H,
                      renk(self.pal["yazi"], a), ymaks * self.W)


def _yuzey(W, H):
    import skia
    return skia.Surface(W, H)


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path, seslendirme: Path | None = None) -> list[Path]:
    import skia
    klasor.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H, seslendirme); out = []
    for t in anlar:
        surf = _yuzey(W, H)
        with surf as cv:
            c.kare(cv, t)
        p = klasor / f"{s.get('kimlik', 'karakter')}-{W}x{H}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(p), skia.kPNG); out.append(p)
    return out


def video(s: dict, W: int, H: int, yol: Path, seslendirme: Path | None = None) -> tuple[Path, dict]:
    import skia
    yol.parent.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H, seslendirme)
    surf = _yuzey(W, H)
    pf = "bgra" if surf.imageInfo().colorType() == skia.kBGRA_8888_ColorType else "rgba"
    fps = s["fps"]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pf, "-s", f"{W}x{H}",
                           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                           "-pix_fmt", "yuv420p", str(yol)], stdin=subprocess.PIPE)
    for i in range(int(round(fps * s["sure"]))):
        with surf as cv:
            c.kare(cv, i / fps)
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise RuntimeError("ffmpeg görüntü kodlaması başarısız")
    return yol, c.agiz_kaynak


def kapak(s: dict, W: int, H: int, t: float, yol: Path, seslendirme: Path | None = None) -> Path:
    import skia
    surf = _yuzey(W, H)
    with surf as cv:
        Cizici(s, W, H, seslendirme).kare(cv, t)
    surf.makeImageSnapshot().save(str(yol), skia.kPNG)
    return yol

