"""Tek çizgi şablonunun görüntüsü: düz zemin üstünde kopmayan tek bir çizgi + az yazı (skia).

Her kare t'nin saf fonksiyonudur. Zemin düz renktir (gradyan ve parlama yok, bantlaşma olmaz),
çizgi yuvarlak uçlu ve kenar yumuşatmalı çizilir. Ölçüler kısa kenara (`u`) göre verilir; dikey ve
yatay yerleşim aynı senaryodan çıkar. Gerekenler: skia-python (Linux'ta libegl1, libgl1), numpy.
"""

from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

import numpy as np

import sekiller
import zaman

# Inter (OFL). Depoya girmez (yazı tipleri LFS'e düşer): önce TEK_CIZGI_FONT_DIZINI / KINETIK_FONT_DIZINI,
# sonra sistem (`apt-get install fonts-inter`), sonra fontconfig.
FONT_ADLARI = {800: ["Inter-ExtraBold.otf", "Inter-800.ttf", "Inter-ExtraBold.ttf"],
               500: ["Inter-Medium.otf", "Inter-500.ttf", "Inter-Medium.ttf", "Inter-Regular.otf", "Inter-700.ttf"]}
FONT_DIZINLERI = [os.environ.get("TEK_CIZGI_FONT_DIZINI", ""), os.environ.get("KINETIK_FONT_DIZINI", ""),
                  "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
                  str(Path.home() / "Library/Fonts"), "/Library/Fonts"]


def font_bul(agirlik: int) -> str:
    for d in FONT_DIZINLERI:
        for ad in FONT_ADLARI[agirlik]:
            if d and (Path(d) / ad).exists():
                return str(Path(d) / ad)
    r = subprocess.run(["fc-match", "-f", "%{file}", f"Inter:weight={205 if agirlik == 800 else 100}"], capture_output=True, text=True)
    if r.returncode == 0 and "inter" in r.stdout.lower():
        return r.stdout.strip()
    raise RuntimeError("Inter yazı tipi bulunamadı: `apt-get install fonts-inter` ya da TEK_CIZGI_FONT_DIZINI")


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def out_back(p, s=1.6): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def renk(hex_: str) -> int:
    return 0xFF000000 | int(hex_.lstrip("#"), 16)


def karistir(a: str, b: str, p: float) -> int:
    x, y = int(a.lstrip("#"), 16), int(b.lstrip("#"), 16)
    c = [round(((x >> s) & 255) * (1 - p) + ((y >> s) & 255) * p) for s in (16, 8, 0)]
    return 0xFF000000 | (c[0] << 16) | (c[1] << 8) | c[2]


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        import skia
        self.skia, self.s, self.W, self.H = skia, s, W, H
        self.u = min(W, H)
        self.pal = s["palet"]
        self.pz = zaman.pozlar(s)
        self.cizgi = sekiller.Cizgi(self.pz, W, H)
        self.zeminler = zaman.zemin_degisimleri(s)
        self.kalin = 0.0118 * self.u
        self.yazi_tipi = {a: skia.Typeface.MakeFromFile(font_bul(a)) for a in (800, 500)}
        self.gorseller = {}  # sahne → skia.Image (gerçek fotoğraf, daire içine kırpılır)
        for i, sh in enumerate(s["sahneler"]):
            if "gorsel" in sh:
                self.gorseller[i] = skia.Image.open(str(Path(s["_klasor"]) / sh["gorsel"]["dosya"]))
        # sayaç inişi: kamera hafifçe öne iter
        self.darbeler = [p["t"] + p["sure"] * 0.55 for p in self.pz if p.get("son")]

    # ---------- yardımcılar ----------
    def _zemin(self, cv, t: float, merkez) -> None:
        skia = self.skia
        rol = "zemin"
        for an, r in self.zeminler:
            if t >= an + zaman.IRIS_SN:
                rol = r
        cv.drawColor(renk(self.pal[rol]))
        for an, r in self.zeminler:  # açılmakta olan iris: düz renk daire, kenarı yumuşatılmış
            if an <= t < an + zaman.IRIS_SN:
                p = out_cubic(prog(t, an, zaman.IRIS_SN))
                R = p * math.hypot(self.W, self.H)
                cv.drawCircle(merkez[0], merkez[1], R, skia.Paint(Color=renk(self.pal[r]), AntiAlias=True))

    def _yazi(self, cv, metin: str, agirlik: int, punto: float, x: float, y: float, rgb: int, alfa: float) -> None:
        skia = self.skia
        f = skia.Font(self.yazi_tipi[agirlik], punto)
        f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias)
        w = f.measureText(metin)
        sinir = self.W * 0.86
        if w > sinir:  # uzun yazı sahneye sığacak kadar küçülür
            f.setSize(punto * sinir / w); w = sinir
        p = skia.Paint(Color=rgb, AntiAlias=True); p.setAlphaf(alfa)
        cv.drawString(metin, x - w / 2, y, f, p)

    def _gorsel(self, cv, t: float) -> None:
        """`daire` sahnesinin fotoğrafı: çizginin dairesi içinde merkezden açılır, sahne biterken kapanır.
        `odak` [x, y] (0–1) kare kırpmanın merkezi; fotoğraf sahne boyunca çok hafif yakınlaşır."""
        skia = self.skia
        for i, img in self.gorseller.items():
            sh = self.s["sahneler"][i]
            g = sh["gorsel"]
            ac = out_cubic(prog(t, g["t"], 0.55)) * (1 - out_cubic(prog(t, sh["_son"] - 0.05, 0.3)))
            if ac <= 0:
                continue
            R = sh.get("olcek", 1.0) * 0.58 * self.u / 2 - self.kalin * 1.6
            cx, cy = self.W / 2, self.H * sh.get("y", 0.44)
            iw, ih = img.width(), img.height()
            k = min(iw, ih) / (1 + 0.06 * prog(t, g["t"], sh["_son"] - g["t"]))
            ox, oy = g.get("odak", [0.5, 0.5])
            sx = clamp(ox * iw - k / 2, 0, iw - k); sy = clamp(oy * ih - k / 2, 0, ih - k)
            cv.save()
            yol = skia.Path(); yol.addCircle(cx, cy, R * ac)
            cv.clipPath(yol, skia.ClipOp.kIntersect, True)
            cv.drawImageRect(img, skia.Rect.MakeXYWH(sx, sy, k, k), skia.Rect.MakeLTRB(cx - R, cy - R, cx + R, cy + R),
                             skia.SamplingOptions(skia.CubicResampler.Mitchell()), skia.Paint(AntiAlias=True))
            cv.restore()

    def _cizgi_rengi(self, k: int, q: float) -> int:
        onceki = self.pal[self.pz[k - 1]["renk"]] if k else self.pal[self.pz[0]["renk"]]
        return karistir(onceki, self.pal[self.pz[k]["renk"]], clamp(q * 1.6))

    # ---------- kare ----------
    def kare(self, cv, t: float) -> None:
        skia = self.skia
        x, oran, k, q = self.cizgi.an(t)
        sh = self.s["sahneler"][self.pz[k]["sahne"]]
        govde = x[(x[:, 0] > 0) & (x[:, 0] < self.W)]
        merkez = ((govde[:, 0].min() + govde[:, 0].max()) / 2, (govde[:, 1].min() + govde[:, 1].max()) / 2) if len(govde) else (self.W / 2, self.H / 2)
        self._zemin(cv, t, merkez)
        cv.save()
        # kamera: çok yavaş yakınlaşma + sayaç inişinde kısa itme
        z = 1.0 + 0.012 * math.sin(t * 0.35)
        for d in self.darbeler:
            if d <= t < d + 0.6:
                z += 0.035 * math.exp(-(t - d) / 0.12) * math.sin(math.pi * min(1, (t - d) / 0.08))
        cv.translate(self.W / 2, self.H * 0.46); cv.scale(z, z); cv.translate(-self.W / 2, -self.H * 0.46)
        self._gorsel(cv, t)
        # çizgi
        m = max(2, int(round(oran * len(x))))
        y = x[:m]
        yol = skia.Path(); yol.moveTo(*y[0])
        for a in y[1:]:
            yol.lineTo(float(a[0]), float(a[1]))
        boya = skia.Paint(Color=self._cizgi_rengi(k, q), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=self.kalin,
                          StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
        cv.drawPath(yol, boya)
        if oran < 1.0:  # çizilirken kalemin ucu vurgu renginde bir nokta
            cv.drawCircle(float(y[-1][0]), float(y[-1][1]), self.kalin * 1.05, skia.Paint(Color=renk(self.pal["vurgu"]), AntiAlias=True))
        cv.restore()
        # yazılar: taban çizgisinin altında, yukarı kayarak belirir
        taban = float(x[0][1])
        ek = 0.12 if "baslik" in sh and "yazi" in sh else 0.0  # ikisi birden varsa yazı başlığın altına iner
        for alan, agirlik, punto, aralik in (("baslik", 800, 0.118, 0.13), ("yazi", 800, 0.085, 0.11 + ek), ("alt", 500, 0.042, 0.22 + ek)):
            if alan not in sh:
                continue
            y_ = sh[alan]
            p = prog(t, y_["t"], zaman.YAZI_SN)
            if p <= 0:
                continue
            e = out_cubic(p)
            self._yazi(cv, y_["metin"], agirlik, punto * self.u, self.W / 2, taban + aralik * self.u + (1 - e) * 0.03 * self.u,
                       renk(self.pal[y_.get("renk", "murekkep")]), e)


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    import skia
    klasor.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H); out = []
    for t in anlar:
        surf = skia.Surface(W, H)
        with surf as cv:
            c.kare(cv, t)
        p = klasor / f"{s.get('kimlik', 'tek-cizgi')}-{W}x{H}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(p), skia.kPNG); out.append(p)
    return out


def kapak(s: dict, W: int, H: int, t: float, yol: Path) -> Path:
    import skia
    surf = skia.Surface(W, H)
    with surf as cv:
        Cizici(s, W, H).kare(cv, t)
    surf.makeImageSnapshot().save(str(yol), skia.kPNG)
    return yol


def video(s: dict, W: int, H: int, yol: Path) -> Path:
    import skia
    yol.parent.mkdir(parents=True, exist_ok=True)
    c = Cizici(s, W, H)
    surf = skia.Surface(W, H)
    # skia'nın yerel düzeni çoğu makinede BGRA; ffmpeg'e doğru bildir (yoksa kırmızı/mavi yer değiştirir)
    pf = "bgra" if surf.imageInfo().colorType() == skia.kBGRA_8888_ColorType else "rgba"
    fps = s["fps"]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pf, "-s", f"{W}x{H}", "-r", str(fps),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(yol)],
                          stdin=subprocess.PIPE)
    for i in range(int(round(fps * s["sure"]))):
        with surf as cv:
            c.kare(cv, i / fps)
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        raise RuntimeError("ffmpeg görüntü kodlaması başarısız")
    return yol
