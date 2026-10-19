"""piksel: 16-bit oyun. Düşük iç çözünürlükte 16 renkli palet, kendi bitmap fontu (Türkçe harfler dahil), kayan
dağlar ve tepeler, yürüyen kahraman, RPG diyalog kutuları; yazılar daktilo gibi gelir, geçişler blok blok silinir.
Gerçek görseller (ürün fotoğrafı, logo) pikselleştirilmez: büyütmeden sonra tam çözünürlükte üste konur."""

import math

import numpy as np
import skia

import piksel as px
from kaplama import GUVENLI, Kaplama, clamp, out_back, prog, say



class Piksel(Kaplama):
    ad = "piksel"
    aciklama = "16-bit oyun: bitmap font, kayan dağlar, diyalog kutuları"
    GECIS = 0.4
    MUZIK = {**Kaplama.MUZIK, "bpm": 128, "kok": 60, "enstruman": "kare"}
    SFX = "blip"

    # ---------- bitmap yazı ----------
    DEGIS = {"·": "/", "₺": "TL", "–": "-", "—": "-", "“": "'", "”": "'", '"': "'", "’": "'", "€": "EUR", "→": ">"}

    def duzelt(self, s):
        """Bitmap fontta olmayan işaretlerin karşılığı (soru işareti çıkmasın)."""
        return "".join(self.DEGIS.get(c, c) for c in s)
    def _sar(self, s, gen, k_en, azami=3):
        s = px.ekran(self.duzelt(s))
        for k in range(k_en, 0, -1):
            sat, cur = [], ""
            for w in s.split():
                aday = (cur + " " + w).strip()
                if cur and px.metin_gen(aday, k) > gen:
                    sat.append(cur); cur = w
                else:
                    cur = aday
            sat.append(cur)
            if len(sat) <= azami and max(px.metin_gen(x, k) for x in sat) <= gen:
                return sat, k
        return sat, 1

    def _yaz(self, buf, s, cx, y, renk_, k, p=1.0, hiza="orta", golge=px.SIYAH):
        """Daktilo: p oranında harf görünür; konum tam metne göre sabit kalır."""
        if p <= 0 or not s:
            return
        w = px.metin_gen(s, k)
        x = cx - w // 2 if hiza == "orta" else cx - w if hiza == "sag" else cx
        n = max(1, int(math.ceil(len(s) * clamp(p))))
        px.yaz(buf, s[:n], x, y, renk_, k, golge=golge)

    def _blok(self, buf, sat, cx, y, renk_, k, u, t0, hiz=22.0):
        n = sum(len(x) for x in sat)
        yy = y
        for j, s in enumerate(sat):
            once = sum(len(x) for x in sat[:j])
            self._yaz(buf, s, cx, yy, renk_, k, prog(u, t0, n / hiz) * n / max(1, len(s)) - once / max(1, len(s)))
            yy += px.SATIR * k + k * 2
        return yy - y

    def _kutu(self, buf, x, y, w, h, dolgu, p=1.0, kenar=px.BEYAZ):
        if p <= 0:
            return
        hh = max(3, int(h * out_back(p, 1.2)))
        y = int(y + (h - hh) / 2)
        px.kutu(buf, x - 1, y - 1, w + 2, hh + 2, px.SIYAH)
        px.kutu(buf, x, y, w, hh, kenar)
        px.kutu(buf, x + 1, y + 1, w - 2, hh - 2, dolgu)
        px.kutu(buf, x + 2, y + hh - 2, w - 3, 1, px.KOYUGRI if dolgu != px.KOYUGRI else px.SIYAH)

    # ---------- arka plan ----------
    def _fon(self, buf, t):
        h, w = buf.shape
        kam = t * 14
        px.gok(buf, [px.LACI, px.MAVI, px.ACIKMAVI, px.CYAN], 0, int(h * 0.8))
        px.bulutlar(buf, kam, int(h * 0.05), t)
        px.daglar(buf, kam, int(h * 0.9), px.KOYUGRI, px.GRI, kar=px.BEYAZ)
        px.tepeler(buf, kam, int(h * 0.95), px.YESIL, px.CAMGOBEGI)
        px.kutu(buf, 0, int(h * 0.965), w, h, px.MOR)
        spr = px.KAHRAMAN[px.YURU[int(t * 8) % 4]]
        px.ciz_sprite(buf, spr, int((t * 16) % (w + 30)) - 15, int(h * 0.965) - spr[0].shape[0])

    # ---------- sahneler (iç piksel koordinatı) ----------
    def _sahne(self, buf, sh, u, d, A, ust_katman):
        x0, y0, x1, y1 = A
        gen, cx, cy = x1 - x0, (x0 + x1) // 2, (y0 + y1) // 2
        tip = sh["tip"]
        L = px.SATIR
        if tip == "baslik":
            sat, k = self._sar(sh["metin"], gen, 4)
            h = len(sat) * (L * k + 2 * k)
            y = cy - h // 2
            if sh.get("ust"):
                s2, k2 = self._sar(sh["ust"], gen, 1, 1)
                self._yaz(buf, s2[0], cx, y - L * k2 - 4, px.SARI, k2, prog(u, 0, 0.5))
            self._blok(buf, sat, cx, y, px.BEYAZ, k, u, 0.2)
            if sh.get("alt"):
                s2, k2 = self._sar(sh["alt"], gen, 2, 2)
                self._blok(buf, s2, cx, y + h + 4, px.SARI, k2, u, self.an(sh, "alt", 0.6))
        elif tip == "sayi":
            td = self.an(sh, "deger", 0.1)
            deger = say(sh["deger"], prog(u, td + 0.1, min(1.2, d * 0.45)))
            k = px.sigdir([px.ekran(sh["deger"])], 7, gen)
            alt_h = (2 * (L * 2 + 4) + 6 if sh.get("etiket") else 0) + (L + 6 if sh.get("ust") else 0)
            k = max(1, min(k, (y1 - y0 - alt_h) // L))  # etiket alanın (altyazı bandının) üstünde kalsın
            y = cy - (L * k) // 2 - (8 if sh.get("etiket") else 0)
            if sh.get("ust"):
                s2, k2 = self._sar(sh["ust"], gen, 1, 1)
                self._yaz(buf, s2[0], cx, y - L - 6, px.BEYAZ, k2, prog(u, 0, 0.4))
            self._yaz(buf, px.ekran(deger), cx, y, px.SARI, k, prog(u, td, 0.05))
            if u > td + 0.1 + min(1.2, d * 0.45) and int(u * 6) % 2 == 0:
                for j, (dx, dy) in enumerate(((-0.42, -0.1), (0.44, 0.0), (0.38, 0.9))):
                    px.ciz_sprite(buf, px._YILDIZ, cx + int(dx * px.metin_gen(px.ekran(sh["deger"]), k)), y + int(dy * L * k))
            if sh.get("etiket"):
                s2, k2 = self._sar(sh["etiket"], gen, 2, 2)
                self._blok(buf, s2, cx, y + L * k + 6, px.BEYAZ, k2, u, self.an(sh, "etiket", max(0.6, td + 0.3)))
        elif tip == "liste":
            y = y0 + 4
            if sh.get("baslik"):
                s2, k2 = self._sar(sh["baslik"], gen, 3, 2)
                y += self._blok(buf, s2, cx, y, px.SARI, k2, u, 0.0) + 6
            m = sh["maddeler"]
            sat_h = min(34, (y1 - y) // len(m))
            aralik = min(0.55, max(0.25, (d - 1.0) / (len(m) + 1)))
            km = min(self._sar(x, gen - 22, 2, 1)[1] for x in m)  # bütün maddeler aynı boyda
            km = max(1, min(km, (sat_h - 6) // L))  # satır kutusuna sığsın
            for j, x in enumerate(m):
                tj = self.an(sh, f"madde{j}", 0.35 + j * aralik)
                pp = prog(u, tj, 0.25)
                yy = y + j * sat_h
                self._kutu(buf, x0, yy, gen, sat_h - 4, px.LACI, pp)
                if pp >= 1:
                    px.ciz_sprite(buf, px.PARA[int(u * 10 + j) % 4], x0 + 5, yy + (sat_h - 4) // 2 - 4)
                    s2, k2 = self._sar(x, gen - 22, km, 1)
                    self._yaz(buf, s2[0], x0 + 16, yy + (sat_h - 4 - L * k2) // 2, px.BEYAZ, k2,
                              prog(u, tj + 0.1, 0.4), hiza="sol")
        elif tip == "karsilastirma":
            y = y0
            if sh.get("baslik"):
                s2, k2 = self._sar(sh["baslik"], gen, 2, 2)
                y += self._blok(buf, s2, cx, y, px.BEYAZ, k2, u, 0.0) + 6
            dik = (y1 - y0) > gen * 1.2
            bos = 10
            if dik:
                ph = (y1 - y - bos) // 2
                kutular = [(x0, y, gen, ph), (x0, y + ph + bos, gen, ph)]
            else:
                pw = (gen - bos) // 2
                kutular = [(x0, y, pw, y1 - y), (x1 - pw, y, pw, y1 - y)]
            for j, ((bx, by, bw, bh), ad, deger, dolgu, t0) in enumerate(zip(kutular, (sh["sol"], sh["sag"]),
                                                                            (sh.get("sol_deger"), sh.get("sag_deger")),
                                                                            (px.KOYUGRI, px.KIRMIZI), (self.an(sh, "sol", 0.1), self.an(sh, "sag", 0.55)))):
                pp = prog(u, t0, 0.3)
                self._kutu(buf, bx, by, bw, bh, dolgu, pp)
                if pp < 1:
                    continue
                bcx = bx + bw // 2
                s2, k2 = self._sar(ad, bw - 8, 2, 2)
                hh = len(s2) * (L * k2 + 2 * k2)
                if deger:
                    k3 = px.sigdir([px.ekran(deger)], 5, bw - 8)
                    top = L * k3 + 4 + hh
                    yy = by + (bh - top) // 2
                    self._yaz(buf, px.ekran(say(deger, prog(u, t0 + 0.1, 0.6))), bcx, yy, px.SARI if j else px.ACIKGRI, k3, 1.0)
                    self._blok(buf, s2, bcx, yy + L * k3 + 4, px.BEYAZ, k2, u, t0 + 0.2)
                else:
                    self._blok(buf, s2, bcx, by + (bh - hh) // 2, px.BEYAZ, k2, u, t0 + 0.1)
        elif tip == "alinti":
            sat, k = self._sar(sh["metin"], gen - 12, 2, 6)
            h = len(sat) * (L * k + 2 * k) + 14 + (L + 4 if sh.get("kaynak") else 0)
            by = cy - h // 2
            self._kutu(buf, x0, by, gen, h, px.LACI, prog(u, 0, 0.3))
            if u > 0.3:
                self._blok(buf, sat, cx, by + 7, px.BEYAZ, k, u, 0.3, hiz=26)
                if sh.get("kaynak"):
                    self._yaz(buf, "- " + px.ekran(self.duzelt(sh["kaynak"])), x1 - 6, by + h - L - 5, px.SARI, 1, prog(u, 0.4 + len(sh["metin"]) / 26, 0.3),
                              hiza="sag")
        elif tip == "urun":
            dik = (y1 - y0) > gen * 1.2
            g = (x0, y0, gen, int((y1 - y0) * 0.55)) if dik else (x0, y0, gen // 2 - 4, y1 - y0)
            pg = prog(u, 0, 0.35)
            self._kutu(buf, *g, px.BEYAZ, pg, kenar=px.SARI)
            if sh.get("gorsel"):
                ust_katman.append(("gorsel", self.klasor / sh["gorsel"], (g[0] + 3, g[1] + 3, g[2] - 6, g[3] - 6), pg))
            elif pg >= 1:
                s2, k2 = self._sar(sh["ad"][:1], g[2], 8, 1)
                self._yaz(buf, s2[0], g[0] + g[2] // 2, g[1] + (g[3] - L * k2) // 2, px.TURUNCU, k2)
            tx0, ty0 = (x0, g[1] + g[3] + 8) if dik else (x0 + gen // 2 + 4, y0)
            tg = (x1 - tx0)
            tcx = tx0 + tg // 2
            sat, k = self._sar(sh["ad"], tg, 3, 2)
            parcalar = [(sat, k, px.SARI)]
            if sh.get("ozellik"):
                parcalar.append((*self._sar(sh["ozellik"], tg, 1, 2), px.BEYAZ))
            top = sum(len(s) * (L * k + 2 * k) + 6 for s, k, _ in parcalar) + (L * 2 + 8 if sh.get("fiyat") else 0)
            yy = ty0 + max(0, ((y1 - ty0) - top) // 2)
            for j, (s, k, r) in enumerate(parcalar):
                yy += self._blok(buf, s, tcx, yy, r, k, u, 0.3 + 0.3 * j) + 6
            if sh.get("fiyat"):
                f = px.ekran(self.duzelt(sh["fiyat"])); k = px.sigdir([f], 2, tg - 10)
                w = px.metin_gen(f, k) + 10
                pp = prog(u, self.an(sh, "fiyat", 0.8), 0.25)
                self._kutu(buf, tcx - w // 2, yy, w, L * k + 6, px.TURUNCU, pp)
                if pp >= 1:
                    self._yaz(buf, f, tcx, yy + 3, px.BEYAZ, k)
        elif tip == "cta":
            if self.marka.get("logo"):
                ust_katman.append(("logo", self.klasor / self.marka["logo"], (cx - gen // 4, y0, gen // 2, (y1 - y0) // 4), prog(u, 0, 0.4)))
                cy += (y1 - y0) // 10
            sat, k = self._sar(sh["metin"], gen - 16, 4, 2)
            h = len(sat) * (L * k + 2 * k) + 10
            w = max(px.metin_gen(x, k) for x in sat) + 16
            pp = prog(u, 0.1, 0.3)
            kenar = px.SARI if int(u * 3) % 2 == 0 or u < 0.8 else px.BEYAZ
            self._kutu(buf, cx - w // 2, cy - h // 2, w, h, px.KIRMIZI, pp, kenar=kenar)
            if pp >= 1:
                self._blok(buf, sat, cx, cy - h // 2 + 5, px.BEYAZ, k, u, 0.25, hiz=30)
            alt = sh.get("alt") or self.marka.get("ad")
            if alt:
                s2, k2 = self._sar(alt, gen, 1, 2)
                self._blok(buf, s2, cx, cy + h // 2 + 8, px.SARI, k2, u, 0.6)
        elif tip == "gecis" and sh.get("metin"):
            sat, k = self._sar(sh["metin"], gen, 3, 2)
            self._blok(buf, sat, cx, cy - len(sat) * L * k // 2, px.SARI, k, u, 0.05, hiz=30)

    def _ic(self, t, w, h, fmt):
        buf = np.zeros((h, w), np.int16)
        self._fon(buf, t)
        sol, sag, ust, alt = GUVENLI.get(fmt, GUVENLI["1x1"])
        if self.altyazi:  # altyazı bandı (tasarım biriminde, kısa kenar 1080)
            alt -= self.altyazi_bandi(fmt)[0] / (1080 * h / min(w, h))
        A = (int(w * sol), int(h * ust), int(w * (1 - sag)), int(h * alt))
        shs = self.s["sahneler"]
        i = self.sahne_sirasi(t)
        katman = []
        sh = shs[i]
        if i > 0 and t - sh["bas"] < self.GECIS:
            eski = buf.copy(); kk = []
            self._sahne(eski, shs[i - 1], t - shs[i - 1]["bas"], shs[i - 1]["son"] - shs[i - 1]["bas"], A, kk)
            self._sahne(buf, sh, t - sh["bas"], sh["son"] - sh["bas"], A, katman)
            sinir = int(((t - sh["bas"]) / self.GECIS) * (w + 8)) // 8 * 8
            buf[:, sinir:] = eski[:, sinir:]
            katman = [x for x in katman if x[2][0] < sinir] + [x for x in kk if x[2][0] >= sinir]
        else:
            self._sahne(buf, sh, t - sh["bas"], sh["son"] - sh["bas"], A, katman)
        return buf, katman

    def kare(self, cv, t, W, H, fmt):
        t = min(t, self.s["sure"] - 1e-3)
        S = max(1, min(W, H) // 135)
        w, h = -(-W // S), -(-H // S)
        buf, katman = self._ic(t, w, h, fmt)
        big = np.repeat(np.repeat(px.PAL[np.clip(buf, 0, 15)], S, 0), S, 1)[:H, :W]
        cv.drawImage(skia.Image.fromarray(np.ascontiguousarray(big), colorType=skia.kRGBA_8888_ColorType), 0, 0)
        for tur, yol, (x, y, gw, gh), p in katman:  # gerçek görseller tam çözünürlükte
            self.gorsel(cv, yol, skia.Rect.MakeXYWH(x * S, y * S, gw * S, gh * S), p, cerceve=False)
        if self.altyazi:
            u = min(W, H) / 1080
            cv.save(); cv.scale(u, u)
            self.altyazi_ciz(cv, W / u, H / u, t, fmt)
            cv.restore()


KAPLAMA = Piksel
