"""Akış alanı (generatif): binlerce ipçik yumuşak bir rüzgâr alanında akar, kelimenin çevresinden dolaşır.

Alan üç sinüs dalgasının toplamıdır (pürüzsüz, zamanla yavaşça döner). Yazının bulanık maskesinin eğimi
kenarda teğet yön verir: ipçikler harflerin içine girmez, kenarı sarar; kenara değen ipçik vurgu rengine
döner, böylece kelime boşluk + parlayan dış hat olarak belirir; üstüne net yazı yumuşakça oturur. İzler her
karede söner (yoğunluk birikimi, 1 - e^-d ile doyar). Tema "gece" (koyu zemin) ya da "kagit" (krem zemin,
mürekkep). Zemin düz renk; her karede tane eklenir. Benzetim durumludur: tek kare için 3 sn önceden ısıtılır.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from cizim import guvenli, prog, rgb, sahne_no, sigdir, tane, yazi_ciz

ISITMA = 3.0
SONUM = 0.955          # iz yoğunluğunun kare başına kalan oranı
ADIM = 3               # kare başına alt adım (ipçik çizgisi kesintisiz görünsün)
YAZI_GIRIS = 0.7       # net yazının belirme süresi
MASKE_GECIS = 0.6


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        self.s, self.W, self.H = s, W, H
        self.P = {k: np.array(rgb(v), np.float32) for k, v in s["palet"].items()}
        self.u = min(W, H) / 1080
        self.kucuk = 4  # maske ve alan bu oranda küçük ızgarada tutulur
        self.mw, self.mh = W // self.kucuk, H // self.kucuk
        self.n = int(7000 * W * H / (1080 * 1920))
        self._yazi, self._maske = {}, {}
        self.kagit = s.get("tema") == "kagit"
        self.sifirla(0.0)

    def sifirla(self, t: float):
        self.rng = np.random.default_rng(int(t * 1000) + 11)
        self.x = self.rng.random(self.n) * self.W
        self.y = self.rng.random(self.n) * self.H
        self.renk = (self.rng.random(self.n) < 0.28).astype(np.int8)  # 0 çizgi, 1 çizgi2
        self.D = np.zeros((3, self.H * self.W), np.float32)               # çizgi, çizgi2, vurgu yoğunlukları
        self.t = t

    # ---------- yazı ve maske
    def _yazi_katmani(self, i: int):
        if i not in self._yazi:
            sh = self.s["sahneler"][i]
            x0, y0, x1, y1 = guvenli(self.W, self.H)
            im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            alt_h = (y1 - y0) * 0.14 if sh.get("alt") else 0
            f, sat, sh_, gen = sigdir(sh["metin"], "bold", (x1 - x0) * 0.92, (y1 - y0) * 0.5, 200 * self.u, satir_ara=1.08)
            blok = sh_ * len(sat) + alt_h
            cy = (y0 + y1) / 2 - blok / 2 + sh_ * len(sat) / 2
            metin, vurgu = tuple(self.P["metin"].astype(int)), tuple(self.P["vurgu"].astype(int))
            yazi_ciz(d, f, sat, sh_, gen, self.W / 2, cy, metin, vurgu)
            maske = Image.new("L", (self.W, self.H), 0)
            yazi_ciz(ImageDraw.Draw(maske), f, sat, sh_, gen, self.W / 2, cy, 255, 255)
            if alt_h:
                fa, sa, sha, ga = sigdir(sh["alt"], "medium", x1 - x0, alt_h, 54 * self.u)
                ya = cy + sh_ * len(sat) / 2 + alt_h * 0.5
                yazi_ciz(d, fa, sa, sha, ga, self.W / 2, ya, metin, vurgu)
                yazi_ciz(ImageDraw.Draw(maske), fa, sa, sha, ga, self.W / 2, ya, 255, 255)
            self._yazi[i] = np.asarray(im).copy()
            m = maske.resize((self.mw, self.mh), Image.BILINEAR)
            yumusak = np.asarray(m.filter(ImageFilter.GaussianBlur(28 * self.u / self.kucuk)), np.float32) / 255
            yumusak = np.minimum(1.0, yumusak * 2.2)
            gy, gx = np.gradient(yumusak)
            self._maske[i] = (np.asarray(m, np.float32) / 255, yumusak, gx, gy)
        return self._yazi[i], self._maske[i]

    def _maske_an(self, t: float):
        """Sahne geçişinde iki maske harmanlanır."""
        i = sahne_no(self.s, t)
        _, m = self._yazi_katmani(i)
        p = prog(t, self.s["sahneler"][i]["bas"], MASKE_GECIS)
        if i == 0 or p >= 1:
            return m
        _, e = self._yazi_katmani(i - 1)
        return tuple(a * p + b * (1 - p) for a, b in zip(m, e))

    # ---------- benzetim
    def _adim(self, t: float, dt: float):
        W, H, k = self.W, self.H, self.kucuk
        sert, yumusak, gx, gy = self._maske_an(t)
        s = 1.0 / min(W, H)
        X, Y = self.x * s, self.y * s
        aci = math.pi * (np.sin(X * 2.3 + t * 0.21) + np.sin(Y * 1.7 - t * 0.17 + 1.3) + 0.6 * np.sin((X + Y) * 3.1 + 2.0))
        vx, vy = np.cos(aci) + 0.35, np.sin(aci) * 0.8  # hafif soldan sağa rüzgâr
        ix = np.clip((self.x / k).astype(int), 0, self.mw - 1)
        iy = np.clip((self.y / k).astype(int), 0, self.mh - 1)
        nx, ny = gx[iy, ix], gy[iy, ix]
        nn = np.hypot(nx, ny) + 1e-6
        nx, ny = nx / nn, ny / nn
        yakin = yumusak[iy, ix]
        # kenarda: yazıya doğru olan bileşen silinir, teğet yön eklenir
        icer = np.maximum(0, vx * nx + vy * ny)
        vx, vy = vx - icer * nx * yakin * 1.6, vy - icer * ny * yakin * 1.6
        vx, vy = vx - ny * yakin * 0.9, vy + nx * yakin * 0.9
        vn = np.hypot(vx, vy) + 1e-6
        hiz = 260 * self.u * dt
        self.x += vx / vn * hiz
        self.y += vy / vn * hiz
        # yazının içine düşen, kenardan çıkan ya da ömrü dolan ipçik rastgele yere doğar
        yeni = (sert[iy, ix] > 0.4) | (self.x < 0) | (self.x >= W) | (self.y < 0) | (self.y >= H) | \
               (self.rng.random(self.n) < 0.004)
        if yeni.any():
            c = int(yeni.sum())
            self.x[yeni] = self.rng.random(c) * W
            self.y[yeni] = self.rng.random(c) * H
        return yakin, yeni

    def _iz(self, yakin, yeni, biriken):
        W = self.W
        x, y = self.x.astype(int), self.y.astype(int)
        ok = ~yeni & (x >= 0) & (x < W - 1) & (y >= 0) & (y < self.H - 1)
        kenar = (yakin > 0.25) & ok
        cizgi = ok & ~kenar
        for katman, sec in ((0, cizgi & (self.renk == 0)), (1, cizgi & (self.renk == 1)), (2, kenar)):
            biriken[katman].append(y[sec] * W + x[sec])

    def ilerle(self, t: float):
        """Benzetimi t anına getirir (kare süresince ADIM alt adım)."""
        fps = self.s["fps"]
        kal = max(1, int(round(2 * self.u)))  # ipçik kalınlığı (piksel)
        N = self.D.shape[1]
        while self.t < t - 1e-9:
            self.D *= SONUM
            biriken = ([], [], [])
            for j in range(ADIM):
                yakin, yeni = self._adim(self.t + j / (fps * ADIM), 1 / (fps * ADIM))
                self._iz(yakin, yeni, biriken)
            for katman, parca in enumerate(biriken):
                idx = np.concatenate(parca)
                idx = np.concatenate([idx + dy * self.W + dx for dy in range(kal) for dx in range(kal)])
                self.D[katman] += np.bincount(idx, minlength=N)[:N].astype(np.float32) * 0.22
            self.t += 1 / fps

    def _goruntu(self, t: float) -> np.ndarray:
        H, W = self.H, self.W
        alfa = 1 - np.exp(-self.D.reshape(3, H, W))
        toplam = np.clip(alfa.sum(0), 1e-6, None)
        olcek = np.minimum(1.0, 0.9 / toplam) if not self.kagit else np.minimum(1.0, 0.75 / toplam)
        alfa *= olcek
        a = self.P["zemin"] * (1 - alfa.sum(0))[..., None]
        for i, ad in enumerate(("cizgi", "cizgi2", "vurgu")):
            a += self.P[ad] * alfa[i][..., None]
        i = sahne_no(self.s, t)
        y, _ = self._yazi_katmani(i)
        p = prog(t, self.s["sahneler"][i]["bas"] + 0.15, YAZI_GIRIS)
        son = self.s["sahneler"][i]["_son"]
        if i + 1 < len(self.s["sahneler"]):
            p *= 1 - prog(t, son - 0.35, 0.3)
        if p > 0:
            ya = y[:, :, 3:4].astype(np.float32) / 255 * p
            a = a * (1 - ya) + y[:, :, :3] * ya
        k = min(prog(t, 0, 0.4), 1 - prog(t, self.s["sure"] - 0.4, 0.4) * 0.7)
        if k < 1:
            a = a * k + self.P["zemin"] * (1 - k)
        return tane(np.clip(a, 0, 255).astype(np.uint8), self.rng, 3.0)

    def kare(self, t: float) -> np.ndarray:
        if t < self.t - 1e-9:
            self.sifirla(max(0.0, t - ISITMA))
        self.ilerle(t)
        return self._goruntu(t)

    def tek_kare(self, t: float) -> np.ndarray:
        self.sifirla(max(0.0, t - ISITMA))
        return self.kare(t)
