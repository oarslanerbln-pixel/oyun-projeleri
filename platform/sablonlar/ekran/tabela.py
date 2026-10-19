"""Kalkış tabelası (split-flap): her hücrede iki yarım kapak; harf hedefe gelene kadar alfabe sırasıyla takırdayarak döner.

Ana tabela sahnenin metnini (büyük harf, kelime bölünmez, satırlar ortalı), altındaki küçük şerit `alt` satırını
gösterir. Hücreler soldan sağa ve yukarıdan aşağıya hafif gecikmeyle döner; uzun yolu olan hücre en çok
`EN_COK_DONUS` kez döner (her sahne geçişi ~1 sn'de oturur). Zemin, kasa ve hücreler düz renktir (degrade yok).
`takvim()` saf Python'dur; ses (`sentez.py`) takırtıları aynı anlardan üretir.
"""

from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image, ImageDraw

import zaman
from cizim import font, format_adi, guvenli, prog, rgb, tane

DONUS = 0.072          # bir kapağın düşme süresi (sn)
EN_COK_DONUS = 9
ALT_GECIKME = 0.45     # alt şerit ana tabeladan bu kadar sonra döner
EN_BOY = 0.70          # hücre genişliği / yüksekliği
L = len(zaman.ALFABE)


def _izgara_metni(satirlar, sutun: int, satir: int):
    """Satırları ızgaraya ortalar: (satır, sütun) → (harf, vurgu)."""
    out = {}
    r0 = (satir - len(satirlar)) // 2
    for i, sat in enumerate(satirlar):
        metin = " ".join(k for k, _ in sat)
        vurgu = []
        for k, v in sat:
            vurgu += [v] * len(k) + [False]
        c0 = (sutun - len(metin)) // 2
        for j, ch in enumerate(metin):
            out[(r0 + i, c0 + j)] = (ch, vurgu[j])
    return out


def takvim(s: dict, fmt: str) -> dict:
    """Her hücre için dönüş listesi: hucre → [(başlangıç, [harfler], [vurgu]), ...] (zamana göre sıralı).
    Hücreler 'ana' (satır, sütun) ve 'alt' (0, sütun) anahtarlarıyla iki ızgarada."""
    sutun, satir, alt_sutun = zaman.IZGARA[fmt]
    rng = random.Random(7)
    durum = {}
    out = {}
    for i, sh in enumerate(s["sahneler"]):
        hedef = {("ana",) + k: v for k, v in _izgara_metni(zaman.tabela_satirlari(sh["metin"], sutun) or [], sutun, satir).items()}
        alt = zaman.tr_buyuk(sh.get("alt", ""))[:alt_sutun]
        c0 = (alt_sutun - len(alt)) // 2
        hedef.update({("alt", 0, c0 + j): (ch, False) for j, ch in enumerate(alt)})
        hucreler = [("ana", r, c) for r in range(satir) for c in range(sutun)] + [("alt", 0, c) for c in range(alt_sutun)]
        for h in hucreler:
            a = durum.get(h, (" ", False))
            b = hedef.get(h, (" ", False))
            if a == b:
                continue
            ia, ib = zaman.ALFABE.index(a[0]), zaman.ALFABE.index(b[0])
            n = (ib - ia) % L or L
            m = min(n, EN_COK_DONUS)
            harfler = [a[0]] + [zaman.ALFABE[(ib - k) % L] for k in range(m - 1, 0, -1)] + [b[0]]
            vurgu = [a[1]] + [False] * (m - 1) + [b[1]]
            if h[0] == "ana":
                t0 = sh["bas"] + 0.10 + h[2] * 0.028 + h[1] * 0.05 + rng.uniform(0, 0.07)
            else:
                t0 = sh["bas"] + ALT_GECIKME + h[2] * 0.018 + rng.uniform(0, 0.05)
            out.setdefault(h, []).append((t0, harfler, vurgu))
            durum[h] = b
    return out


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        self.s, self.W, self.H = s, W, H
        self.P = {k: rgb(v) for k, v in s["palet"].items()}
        fmt = format_adi(W, H)
        self.sutun, self.satir, self.alt_sutun = zaman.IZGARA[fmt]
        self.takvim = takvim(s, fmt)
        self.rng = np.random.default_rng(3)
        x0, y0, x1, y1 = guvenli(W, H)
        # bütün ölçüler hücre genişliği (cw) cinsinden; önce cw=1 için toplam, sonra güvenli kutuya ölçeklenir
        bosluk, pay = 0.09, 0.42
        ana_w = self.sutun + (self.sutun - 1) * bosluk + 2 * pay
        ana_h = self.satir / EN_BOY + (self.satir - 1) * bosluk + 2 * pay
        acw = (ana_w - 2 * pay - (self.alt_sutun - 1) * bosluk * 0.5) / self.alt_sutun
        alt_h = acw / EN_BOY + 2 * pay * 0.6
        etiket_h = 0.75 if s.get("baslik") else 0.0
        top_h = etiket_h + ana_h + 0.55 + alt_h
        cw = min((x1 - x0) / ana_w, (y1 - y0) / top_h)
        self.cw, self.ch = int(cw), int(cw / EN_BOY) // 2 * 2
        self.g = max(2, int(round(cw * bosluk)))
        self.acw = int(acw * cw)
        self.ach = int(acw * cw / EN_BOY) // 2 * 2
        self.ag = max(1, int(round(cw * bosluk * 0.5)))
        bw = self.sutun * self.cw + (self.sutun - 1) * self.g + 2 * int(pay * cw)
        bh = self.satir * self.ch + (self.satir - 1) * self.g + 2 * int(pay * cw)
        abw = self.alt_sutun * self.acw + (self.alt_sutun - 1) * self.ag + 2 * int(pay * cw * 0.6)
        abh = self.ach + 2 * int(pay * cw * 0.6)
        toplam = etiket_h * cw + bh + 0.55 * cw + abh
        ust = (y0 + y1) / 2 - toplam / 2
        self.etiket_y = ust
        self.bx, self.by = int(W / 2 - bw / 2), int(ust + etiket_h * cw)
        self.abx, self.aby = int(W / 2 - abw / 2), int(self.by + bh + 0.55 * cw)
        self.bw, self.bh, self.abw, self.abh = bw, bh, abw, abh
        self.pay, self.apay = int(pay * cw), int(pay * cw * 0.6)
        self._kutu = {}
        self.zemin = self._zemin_ciz()

    # ---------- statik katman
    def _zemin_ciz(self) -> np.ndarray:
        im = Image.new("RGB", (self.W, self.H), self.P["zemin"])
        d = ImageDraw.Draw(im)
        u = self.cw
        for x, y, w, h in ((self.bx, self.by, self.bw, self.bh), (self.abx, self.aby, self.abw, self.abh)):
            d.rectangle([x + int(0.12 * u), y + int(0.16 * u), x + w + int(0.12 * u), y + h + int(0.16 * u)],
                        fill=tuple(int(c * 0.55) for c in self.P["zemin"]))  # düz gölge
            d.rectangle([x, y, x + w, y + h], fill=self.P["kasa"])
            # kasa vidaları
            for vx, vy in ((x + 0.18 * u, y + 0.18 * u), (x + w - 0.18 * u, y + 0.18 * u),
                           (x + 0.18 * u, y + h - 0.18 * u), (x + w - 0.18 * u, y + h - 0.18 * u)):
                r = 0.06 * u
                d.ellipse([vx - r, vy - r, vx + r, vy + r], fill=self.P["hucre"])
        b = self.s.get("baslik")
        if b:
            f = font("bold", 0.36 * u)
            metin = zaman.tr_buyuk(b)
            x = self.bx
            y = self.etiket_y + 0.36 * u
            # küçük uçak simgesi: gövde + kanat (düz şekiller)
            s_ = 0.34 * u
            cy = y - 0.13 * u
            d.polygon([(x, cy), (x + s_ * 0.9, cy - s_ * 0.08), (x + s_, cy), (x + s_ * 0.9, cy + s_ * 0.08)], fill=self.P["etiket"])
            d.polygon([(x + s_ * 0.38, cy), (x + s_ * 0.62, cy), (x + s_ * 0.3, cy - s_ * 0.45), (x + s_ * 0.18, cy - s_ * 0.45)],
                      fill=self.P["etiket"])
            d.polygon([(x + s_ * 0.38, cy), (x + s_ * 0.62, cy), (x + s_ * 0.3, cy + s_ * 0.45), (x + s_ * 0.18, cy + s_ * 0.45)],
                      fill=self.P["etiket"])
            d.text((x + s_ * 1.35, y), metin, font=f, fill=self.P["etiket"], anchor="ls")
        return np.asarray(im).copy()

    def _hucre(self, ch: str, vurgu: bool, kucuk: bool) -> np.ndarray:
        k = (ch, vurgu, kucuk)
        if k not in self._kutu:
            w, h = (self.acw, self.ach) if kucuk else (self.cw, self.ch)
            ss = 3  # harf kenarları yumuşasın diye 3 kat büyük çizilip küçültülür
            im = Image.new("RGB", (w * ss, h * ss), self.P["hucre"])
            d = ImageDraw.Draw(im)
            ust = tuple(min(255, c + 6) for c in self.P["hucre"])  # üst kapak bir ton açık (düz renk)
            d.rectangle([0, 0, w * ss, h * ss // 2], fill=ust)
            if ch != " ":
                f = font("bold", h * ss * 0.66)
                d.text((w * ss / 2, h * ss / 2), ch, font=f, fill=self.P["vurgu"] if vurgu else self.P["harf"], anchor="mm")
            cizgi = max(ss, int(h * ss * 0.025))
            d.rectangle([0, h * ss // 2 - cizgi // 2, w * ss, h * ss // 2 + cizgi // 2], fill=self.P["ayrac"])
            # menteşe çentikleri
            mw = int(w * ss * 0.07)
            d.rectangle([0, h * ss // 2 - cizgi * 2, mw, h * ss // 2 + cizgi * 2], fill=self.P["ayrac"])
            d.rectangle([w * ss - mw, h * ss // 2 - cizgi * 2, w * ss, h * ss // 2 + cizgi * 2], fill=self.P["ayrac"])
            self._kutu[k] = np.asarray(im.resize((w, h), Image.LANCZOS)).copy()
        return self._kutu[k]

    def _hucre_an(self, h, t: float, kucuk: bool) -> np.ndarray:
        olaylar = self.takvim.get(h, [])
        son = None
        for o in olaylar:
            if o[0] <= t:
                son = o
        if son is None:
            return self._hucre(" ", False, kucuk)
        t0, harfler, vurgu = son
        k = (t - t0) / DONUS
        m = len(harfler) - 1
        if k >= m:
            return self._hucre(harfler[-1], vurgu[-1], kucuk)
        i, p = int(k), k - int(k)
        A = self._hucre(harfler[i], vurgu[i], kucuk)
        B = self._hucre(harfler[i + 1], vurgu[i + 1], kucuk)
        hh = A.shape[0] // 2
        out = np.empty_like(A)
        out[:hh] = B[:hh]
        out[hh:] = A[hh:]
        if p < 0.5:  # A'nın üst kapağı menteşe üstünde öne düşer
            s_ = math.cos(p * math.pi)
            n = max(1, int(round(hh * s_)))
            satirlar = (np.arange(n) * hh / n).astype(int)
            out[hh - n:hh] = (A[:hh][satirlar] * (1 - 0.45 * (1 - s_))).astype(np.uint8)
            out[hh:] = (out[hh:] * (1 - 0.25 * (1 - s_))).astype(np.uint8)  # düşen kapağın gölgesi
        else:        # B'nin alt kapağı aşağı açılır
            s_ = -math.cos(p * math.pi)
            n = max(1, int(round(hh * s_)))
            satirlar = (np.arange(n) * hh / n).astype(int)
            out[hh:hh + n] = (B[hh:][satirlar] * (1 - 0.45 * (1 - s_))).astype(np.uint8)
        return out

    def kare(self, t: float) -> np.ndarray:
        a = self.zemin.copy()
        for r in range(self.satir):
            for c in range(self.sutun):
                x = self.bx + self.pay + c * (self.cw + self.g)
                y = self.by + self.pay + r * (self.ch + self.g)
                a[y:y + self.ch, x:x + self.cw] = self._hucre_an(("ana", r, c), t, False)
        for c in range(self.alt_sutun):
            x = self.abx + self.apay + c * (self.acw + self.ag)
            y = self.aby + self.apay
            a[y:y + self.ach, x:x + self.acw] = self._hucre_an(("alt", 0, c), t, True)
        # açılış: karanlıktan 0,25 sn'de gelir; son 0,3 sn hafif kararır
        k = min(prog(t, 0, 0.25), 1 - 0.6 * prog(t, self.s["sure"] - 0.3, 0.3))
        if k < 1:
            a = (a * k).astype(np.uint8)
        return tane(a, self.rng, 3.0)
