"""VHS / glitch: kasetten oynayan görüntü; renk kayması, tarama çizgileri, kayan iz bandı, alt kenarda kafa gürültüsü.

Her sahne bir "kesik" ile girer: 0,35 sn boyunca görüntü yatay dilimlere bölünüp kayar, renk kanalları açılır,
ilk iki karede renk çubukları parlar; sonra yazı oturur ve yalnız hafif titrer. Sol üstte ekran yazısı (▶ PLAY ve
sayaç) güvenli alanın içindedir. Zemin düz renktir; her karede değişen tane basamaklanmayı kırar. Kare `t`'nin
saf fonksiyonudur (rastgelelik kare numarasıyla tohumlanır).
"""

from __future__ import annotations


import numpy as np
from PIL import Image, ImageDraw

from cizim import font, guvenli, prog, rgb, sahne_no, sigdir, yazi_ciz

KESIK = 0.35
CUBUKLAR = ["#C0C0C0", "#C0C000", "#00C0C0", "#00C000", "#C000C0", "#C00000", "#0000C0"]


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        self.s, self.W, self.H = s, W, H
        self.P = {k: rgb(v) for k, v in s["palet"].items()}
        self.u = min(W, H) / 1080
        self.kutu = guvenli(W, H)
        self.zemin = np.empty((H, W, 3), np.uint8)
        self.zemin[:] = self.P["zemin"]
        y = np.arange(H)
        self.tarama = np.where((y // max(2, int(round(2 * self.u)))) % 2 == 0, 0.90, 1.0).astype(np.float32)[:, None, None]
        self._yazi = {}
        cub = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(cub)
        for i, c in enumerate(CUBUKLAR):
            d.rectangle([i * W / 7, 0, (i + 1) * W / 7, H], fill=rgb(c))
        self.cubuklar = np.asarray(cub).copy()

    def _yazi_katmani(self, i: int) -> np.ndarray:
        """Sahnenin yazısı: tam kare RGBA (alfa 0–255)."""
        if i not in self._yazi:
            sh = self.s["sahneler"][i]
            x0, y0, x1, y1 = self.kutu
            im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            alt_h = (y1 - y0) * 0.12 if sh.get("alt") else 0
            ana_h = (y1 - y0) * 0.55
            f, sat, sh_, gen = sigdir(sh["metin"], "black", x1 - x0, ana_h, 230 * self.u, buyuk=True, satir_ara=1.02)
            blok = sh_ * len(sat) + (alt_h * 0.9 if alt_h else 0)
            cy = (y0 + y1) / 2 - blok / 2 + sh_ * len(sat) / 2
            yazi_ciz(d, f, sat, sh_, gen, self.W / 2, cy, self.P["metin"], self.P["vurgu"])
            if alt_h:
                fa, sa, sha, ga = sigdir(sh["alt"], "mono", x1 - x0, alt_h, 52 * self.u, buyuk=True)
                yazi_ciz(d, fa, sa, sha, ga, self.W / 2, cy + sh_ * len(sat) / 2 + alt_h * 0.55, self.P["ikincil"], self.P["ikincil"])
            self._yazi[i] = np.asarray(im).copy()
        return self._yazi[i]

    def _osd(self, a: np.ndarray, t: float) -> np.ndarray:
        x0, y0, _, _ = self.kutu
        im = Image.fromarray(a)
        d = ImageDraw.Draw(im)
        boy = 46 * self.u
        f = font("mono", boy)
        x, y = x0, y0 + boy
        golge = (0, 0, 0)
        k = boy * 0.7
        for dx, renk in ((3 * self.u, golge), (0, self.P["osd"])):
            d.polygon([(x + dx, y - k + dx), (x + dx, y + dx), (x + k * 0.85 + dx, y - k / 2 + dx)], fill=renk)
            d.text((x + k * 1.3 + dx, y + dx), "PLAY", font=f, fill=renk, anchor="ls")
            sn = int(t)
            d.text((x + dx, y + boy * 1.35 + dx), f"SP {sn // 3600}:{sn // 60 % 60:02d}:{sn % 60:02d}", font=f, fill=renk,
                   anchor="ls")
        return np.asarray(im)

    def kare(self, t: float) -> np.ndarray:
        W, H, u = self.W, self.H, self.u
        fps = self.s["fps"]
        n = int(round(t * fps))
        rng = np.random.default_rng(1000 + n)
        i = sahne_no(self.s, t)
        bas = self.s["sahneler"][i]["bas"]
        g = max(0.0, 1 - (t - bas) / KESIK) ** 1.6 if t >= bas else 0.0
        if n % 53 in (0, 1) and g < 0.2:  # ara sıra kısa bir sekme
            g = 0.25
        a = self.zemin.astype(np.float32)
        y = self._yazi_katmani(i)
        alfa = y[:, :, 3:4].astype(np.float32) / 255
        # sahneye giriş: yazı ilk karelerde parlayarak oturur
        a = a * (1 - alfa) + y[:, :, :3] * alfa
        if t - bas < 2 / fps and i > 0 or t < 2 / fps:
            a = a * 0.45 + self.cubuklar * 0.55
        # sabit hafif titreme (dikey 0–1 px), kesikte yatay dilim kayması
        if n % 7 == 0:
            a = np.roll(a, int(rng.integers(-1, 2) * u), axis=0)
        if g > 0:
            ys = 0
            while ys < H:
                h = int(rng.integers(int(0.01 * H), int(0.08 * H)))
                if rng.random() < 0.6:
                    a[ys:ys + h] = np.roll(a[ys:ys + h], int(rng.normal(0, 0.09 * W * g)), axis=1)
                ys += h
        # iz bandı: yukarıdan aşağı yavaşça kayar
        bh = int(0.05 * H)
        by = int(((t * 0.11) % 1.3 - 0.15) * H)
        b0, b1 = max(0, by), min(H, by + bh)
        if b1 > b0:
            satir = np.arange(b0, b1)
            kay = (np.sin(satir * 0.21 + t * 40) * 7 * u).astype(int)
            for r, k in zip(satir[::2], kay[::2]):
                a[r:r + 2] = np.roll(a[r:r + 2], k, axis=1)
            a[b0:b1] += 14
            for _ in range(int(rng.integers(2, 6))):  # beyaz çizik
                r = int(rng.integers(b0, b1)); x = int(rng.integers(0, W)); w = int(rng.integers(20, 160) * u)
                a[r:r + max(1, int(u)), x:x + w] = 225
        # alt kenarda kafa değiştirme gürültüsü (Reels arayüzünün altında kalan şerit)
        hb = int(0.012 * H)
        a[H - hb:] = np.roll(a[H - hb:], int(0.03 * W), axis=1) * 0.8 + rng.random((hb, W, 1)) * 60
        # renk kanalı kayması
        d = int(round((2 + 14 * g) * u))
        if d:
            a[:, :, 0] = np.roll(a[:, :, 0], d, axis=1)
            a[:, :, 2] = np.roll(a[:, :, 2], -d, axis=1)
        a *= self.tarama
        a += (rng.random((H, W, 1), np.float32) - rng.random((H, W, 1), np.float32)) * (6 + 24 * g)
        # son 0,3 sn: bant durur, görüntü kararır
        k = 1 - prog(t, self.s["sure"] - 0.3, 0.3)
        if k < 1:
            a *= k
        a = np.clip(a, 0, 255).astype(np.uint8)
        return self._osd(a, t)
