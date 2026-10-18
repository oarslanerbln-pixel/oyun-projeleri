"""Analiz şablonunun görüntüsü: haber / veri gazeteciliği grafikleri (skia).

Her kare t'nin saf fonksiyonudur. Ölçüler 1080 piksellik kısa kenara göre (`u`) verilir; yatay ve
dikey yerleşim aynı sahne tanımından çıkar. Zeminler düz renktir (degrade, parlama ve halka yok);
ekrandaki her sayı senaryodan gelir. Gerekenler: skia-python (Linux'ta libegl1, libgl1).
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path

BURADA = Path(__file__).resolve().parent

# Inter (OFL). Depoya girmez (yazı tipleri LFS'e düşer): önce ANALIZ_FONT_DIZINI, sonra sistem
# (`apt-get install fonts-inter`, macOS'ta Inter yüklü olmalı), sonra fontconfig.
FONT_ADLARI = {
    400: ["Inter-Regular.otf", "Inter-Regular.ttf"],
    500: ["Inter-Medium.otf", "Inter-Medium.ttf"],
    600: ["Inter-SemiBold.otf", "Inter-SemiBold.ttf"],
    700: ["Inter-Bold.otf", "Inter-700.ttf", "Inter-Bold.ttf"],
    800: ["Inter-ExtraBold.otf", "Inter-800.ttf", "Inter-ExtraBold.ttf"],
    "baslik": ["InterDisplay-ExtraBold.otf", "Inter-ExtraBold.otf", "Inter-800.ttf"],
}
FONT_DIZINLERI = [os.environ.get("ANALIZ_FONT_DIZINI", ""), "/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
                  str(Path.home() / "Library/Fonts"), "/Library/Fonts"]

# Renk rolleri. Marka değişince yalnız palet değişir; senaryodaki "palet" bunların üstüne yazılır.
TEMALAR = {
    "koyu": {"zemin": "#0E141B", "panel": "#161F29", "cizgi": "#263443", "metin": "#F3F1EC", "soluk": "#8E9AA8",
             "notr": "#566577", "vurgu": "#E5383B", "ikinci": "#5AA9E6", "kara": "#FFFFFF"},
    "acik": {"zemin": "#F5F2EA", "panel": "#FFFFFF", "cizgi": "#DDD7CA", "metin": "#14171C", "soluk": "#6B7380",
             "notr": "#A3ABB6", "vurgu": "#D62F32", "ikinci": "#2F6FA8", "kara": "#FFFFFF"},
}


def font_bul(agirlik) -> str:
    for d in FONT_DIZINLERI:
        for ad in FONT_ADLARI[agirlik]:
            if d and (Path(d) / ad).exists():
                return str(Path(d) / ad)
    w = {400: 80, 500: 100, 600: 180, 700: 200, 800: 205, "baslik": 205}[agirlik]
    r = subprocess.run(["fc-match", "-f", "%{file}", f"Inter:weight={w}"], capture_output=True, text=True)
    if r.returncode == 0 and "inter" in r.stdout.lower():
        return r.stdout.strip()
    raise RuntimeError("Inter yazı tipi bulunamadı: `apt-get install fonts-inter` ya da ANALIZ_FONT_DIZINI")


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, p): return a + (b - a) * p
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def in_out_cubic(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_quint(p): return 1 - (1 - p) ** 5


def sayi_yaz(v: float, basamak: int = 0, ondalik: str = ",", binlik: str = ".") -> str:
    """Türkçe sayı yazımı: 550000 → 550.000, 5.4 → 5,4"""
    s = f"{abs(v):,.{basamak}f}".replace(",", "\0").replace(".", ondalik).replace("\0", binlik)
    return ("-" if v < 0 else "") + s


def buyuk(metin: str) -> str:
    """Türkçe büyük harf: i → İ, ı → I"""
    return metin.replace("i", "İ").replace("ı", "I").upper()


def harita_verisi() -> dict:
    return json.loads((BURADA / "veri" / "bati-avrupa.json").read_text(encoding="utf-8"))["halkalar"]


def sahne_bitisleri(s: dict) -> list[tuple[dict, float, float]]:
    sh = s["sahneler"]
    return [(x, x["bas"], sh[i + 1]["bas"] if i + 1 < len(sh) else s["sure"]) for i, x in enumerate(sh)]


def oge_anlari(sahne: dict, ogeler: list, ilk: float = 0.9, ara: float = 0.45) -> list[float]:
    """öğe başına giriş anı: senaryodaki `t` (videonun başından), yoksa sahne başından kademeli"""
    return [o.get("t", sahne["bas"] + ilk + i * ara) for i, o in enumerate(ogeler)]


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        import skia
        self.sk = skia
        self.s, self.W, self.H = s, W, H
        self.u = u = min(W, H) / 1080
        self.dikey = H > W
        self.M = (64 if self.dikey else 110) * u
        self.Y0 = (170 if self.dikey else 150) * u          # içerik üstü (üst bant altı)
        self.Y1 = H - (190 if self.dikey else 150) * u      # içerik altı (kaynak bandı üstü)
        tema = dict(TEMALAR[s.get("tema", "koyu")])
        tema.update(s.get("palet", {}))
        self.p = {k: skia.Color(*(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))) for k, v in tema.items()}
        self.tf = {k: skia.Typeface.MakeFromFile(font_bul(k)) for k in FONT_ADLARI}
        self.ond = s.get("ondalik", ",")
        self.bin = s.get("binlik", ".")
        self.sahneler = sahne_bitisleri(s)
        self._harita = None
        self._fontlar = {}

    # ---------- temel araçlar ----------
    def font(self, agirlik, boy):
        k = (agirlik, round(boy, 2))
        if k not in self._fontlar:
            f = self.sk.Font(self.tf[agirlik], boy)
            f.setEdging(self.sk.Font.Edging.kSubpixelAntiAlias)
            f.setSubpixel(True)
            f.setHinting(self.sk.FontHinting.kNone)
            self._fontlar[k] = f
        return self._fontlar[k]

    def boya(self, rol, a=1.0, stroke=0.0, cap="butt"):
        sk = self.sk
        c = self.p[rol] if isinstance(rol, str) else rol
        p = sk.Paint(AntiAlias=True, Color=c)
        p.setAlphaf(clamp(a) * (sk.Color4f(c).fA))
        if stroke:
            p.setStyle(sk.Paint.kStroke_Style)
            p.setStrokeWidth(stroke)
            p.setStrokeCap({"butt": sk.Paint.kButt_Cap, "round": sk.Paint.kRound_Cap}[cap])
            p.setStrokeJoin(sk.Paint.kRound_Join)
        return p

    def genislik(self, metin, font, aralik=0.0):
        return font.measureText(metin) + aralik * max(0, len(metin) - 1)

    def yaz(self, c, metin, x, y, font, rol="metin", a=1.0, hiza="sol", aralik=0.0):
        if a <= 0 or not metin:
            return 0.0
        w = self.genislik(metin, font, aralik)
        x0 = x - (w if hiza == "sag" else w / 2 if hiza == "orta" else 0)
        p = self.boya(rol, a)
        if aralik:
            for ch in metin:
                c.drawString(ch, x0, y, font, p)
                x0 += font.measureText(ch) + aralik
        else:
            c.drawString(metin, x0, y, font, p)
        return w

    def sigdir(self, metin, agirlik, boy, maxw, aralik=0.0):
        f = self.font(agirlik, boy)
        while self.genislik(metin, f, aralik) > maxw and boy > 10:
            boy *= 0.95
            f = self.font(agirlik, boy)
        return f

    def sar(self, metin, font, maxw) -> list[str]:
        satirlar = []
        for parca in metin.split("\n"):
            sat = ""
            for k in parca.split():
                aday = f"{sat} {k}".strip()
                if sat and font.measureText(aday) > maxw:
                    satirlar.append(sat)
                    sat = k
                else:
                    sat = aday
            satirlar.append(sat)
        return satirlar

    def sayi_ciz(self, c, metin, son_metin, x, y, font, rol="metin", a=1.0, hiza="sol"):
        """Rakamlar sabit genişlikte (sayaç sayarken titremez); konum son değerin genişliğine göre"""
        w0 = max(font.measureText(d) for d in "0123456789")

        def gen(m): return sum(w0 if ch.isdigit() else font.measureText(ch) for ch in m)
        son_w, w = gen(son_metin), gen(metin)
        kutu = x - (son_w if hiza == "sag" else son_w / 2 if hiza == "orta" else 0)
        xx = kutu + (son_w - w if hiza != "sol" else 0)
        p = self.boya(rol, a)
        for ch in metin:
            if ch.isdigit():
                c.drawString(ch, xx + (w0 - font.measureText(ch)) / 2, y, font, p)
                xx += w0
            else:
                c.drawString(ch, xx, y, font, p)
                xx += font.measureText(ch)
        return son_w

    def dikdortgen(self, c, x, y, w, h, rol, a=1.0, r=0.0):
        p = self.boya(rol, a)
        if r:
            c.drawRRect(self.sk.RRect.MakeRectXY(self.sk.Rect.MakeXYWH(x, y, w, h), r, r), p)
        else:
            c.drawRect(self.sk.Rect.MakeXYWH(x, y, w, h), p)

    def cizgi(self, c, x0, y0, x1, y1, rol, kalin, a=1.0, kesik=None, cap="butt"):
        p = self.boya(rol, a, stroke=kalin, cap=cap)
        if kesik:
            p.setPathEffect(self.sk.DashPathEffect.Make(kesik, 0))
        c.drawLine(x0, y0, x1, y1, p)

    def iz(self, c, yol, oran, rol, kalin, a=1.0, kesik=None):
        """yolun ilk `oran` kadarını çiz (çizgi grafikler, harita kıyısı)"""
        sk = self.sk
        if oran <= 0:
            return
        olc = sk.PathMeasure(yol, False)
        p = self.boya(rol, a, stroke=kalin, cap="round")
        if kesik:
            p.setPathEffect(sk.DashPathEffect.Make(kesik, 0))
        while True:
            L = olc.getLength()
            parca = sk.Path()
            if olc.getSegment(0, L * clamp(oran), parca, True):
                c.drawPath(parca, p)
            if not olc.nextContour():
                break

    # ---------- kare ----------
    def kare(self, c, t: float):
        c.clear(self.p["zemin"])
        for sahne, bas, son in self.sahneler:
            if bas - 1e-6 <= t < son or (sahne is self.sahneler[-1][0] and t >= bas):
                self.sahne(c, sahne, t, bas, son)
                break
        self.serit(c, t)
        self.gecis(c, t)

    def sahne(self, c, sahne, t, bas, son):
        u = self.u
        cikis = out_cubic(prog(t, son - 0.3, 0.3)) if sahne is not self.sahneler[-1][0] else 0.0
        c.save()
        if cikis > 0:
            c.saveLayerAlpha(None, int(255 * (1 - cikis)))
            c.translate(0, -18 * u * cikis)
        getattr(self, "s_" + sahne["tur"].replace("-", "_"))(c, sahne, t, bas, son)
        if cikis > 0:
            c.restore()
        c.restore()
        if sahne.get("kaynak"):
            self.kaynak_bandi(c, sahne, t, bas, son)

    def gecis(self, c, t):
        """sahne değişiminde içerik alanını soldan sağa geçen ince vurgu çubuğu"""
        u = self.u
        for sahne, bas, son in self.sahneler[1:]:
            p = prog(t, bas - 0.22, 0.5)
            if 0 < p < 1:
                x = lerp(-0.05 * self.W, 1.05 * self.W, in_out_cubic(p))
                self.dikdortgen(c, x - 5 * u, self.Y0 - 30 * u, 10 * u, self.Y1 - self.Y0 + 60 * u, "vurgu")

    def serit(self, c, t):
        """sabit haber çerçevesi: üst bant (seri adı, tarih) ve en altta ilerleme çizgisi"""
        u, W, H, M = self.u, self.W, self.H, self.M
        s = self.s
        a = out_cubic(prog(t, 0.15, 0.5))
        if a <= 0:
            return
        y = (78 if self.dikey else 70) * u
        self.dikdortgen(c, M, y - 22 * u, 22 * u, 22 * u, "vurgu", a)
        f = self.font(800, 26 * u)
        x = M + 36 * u
        x += self.yaz(c, buyuk(s.get("seri", "ANALİZ")), x, y, f, "metin", a, aralik=4 * u) + 22 * u
        konu = s.get("konu", "")
        if konu and not self.dikey:
            self.dikdortgen(c, x, y - 22 * u, 2 * u, 24 * u, "cizgi", a)
            x += 22 * u
            self.yaz(c, buyuk(konu), x, y, self.font(600, 22 * u), "soluk", a, aralik=2.5 * u)
        if s.get("tarih"):
            self.yaz(c, s["tarih"], W - M, y, self.font(500, 24 * u), "soluk", a, hiza="sag")
        if self.dikey and konu:
            self.yaz(c, buyuk(konu), M, y + 46 * u, self.font(600, 22 * u), "soluk", a, aralik=2.5 * u)
        cy = y + (78 if self.dikey else 30) * u
        self.cizgi(c, M, cy, lerp(M, W - M, out_quint(prog(t, 0.15, 0.9))), cy, "cizgi", 2 * u)
        # ilerleme: sahne sınırlarında küçük çentikler
        ih = 5 * u
        self.dikdortgen(c, 0, H - ih, W, ih, "panel", a)
        self.dikdortgen(c, 0, H - ih, W * clamp(t / s["sure"]), ih, "vurgu", a)
        for _, bas, _ in self.sahneler[1:]:
            self.dikdortgen(c, W * bas / s["sure"] - 1 * u, H - ih, 2 * u, ih, "zemin", a)

    def kaynak_bandi(self, c, sahne, t, bas, son):
        u, M = self.u, self.M
        giris = out_cubic(prog(t, bas + 0.55, 0.5))
        cik = out_cubic(prog(t, son - 0.35, 0.3)) if sahne is not self.sahneler[-1][0] else 0
        a = giris * (1 - cik)
        if a <= 0:
            return
        y = self.H - (112 if self.dikey else 78) * u
        h = 40 * u
        etiket = self.s.get("kaynak_etiketi", "KAYNAK")
        fe = self.font(800, 19 * u)
        ew = self.genislik(etiket, fe, 2.5 * u) + 28 * u
        kayma = (1 - giris) * -24 * u
        self.dikdortgen(c, M + kayma, y - h, ew, h, "vurgu", a)
        self.yaz(c, etiket, M + 14 * u + kayma, y - h / 2 + 7 * u, fe, "kara", a, aralik=2.5 * u)
        maxw = self.W - 2 * M - ew - 24 * u - (110 * u if not self.dikey else 0)
        fk = self.font(500, 24 * u)
        satirlar = self.sar(sahne["kaynak"], fk, maxw)[:2] if self.dikey else [sahne["kaynak"]]
        if not self.dikey:
            fk = self.sigdir(sahne["kaynak"], 500, 24 * u, maxw)
        for i, sat in enumerate(satirlar):
            self.yaz(c, sat, M + ew + 18 * u + kayma, y - h / 2 + 8 * u + i * 32 * u, fk, "soluk", a)
        if not self.dikey:
            no = [x for x, _, _ in self.sahneler].index(sahne) + 1
            self.yaz(c, f"{no:02d} / {len(self.sahneler):02d}", self.W - M, y - h / 2 + 8 * u, self.font(600, 22 * u), "soluk", a,
                     hiza="sag", aralik=1.5 * u)

    def baslik_blogu(self, c, sahne, t, bas) -> float:
        """grafik sahnelerinin başlığı + alt satırı; içeriğin başlayacağı y'yi döndürür"""
        u, M = self.u, self.M
        maxw = self.W - 2 * M
        fb = self.font(800, (60 if self.dikey else 58) * u)
        y = self.Y0 + 62 * u
        satirlar = self.sar(sahne.get("baslik", ""), fb, maxw)
        for i, sat in enumerate(satirlar):
            p = out_cubic(prog(t, bas + 0.02 + i * 0.08, 0.5))
            self.yaz(c, sat, M, y + (1 - p) * 22 * u, fb, "metin", p)
            y += 70 * u
        if sahne.get("alt"):
            p = out_cubic(prog(t, bas + 0.18, 0.5))
            fa = self.font(500, 30 * u)
            for sat in self.sar(sahne["alt"], fa, maxw):
                self.yaz(c, sat, M, y - 14 * u + (1 - p) * 16 * u, fa, "soluk", p)
                y += 40 * u
        return y + 10 * u

    # ---------- sahne türleri ----------
    def s_baslik(self, c, sahne, t, bas, son):
        u, M, W, H = self.u, self.M, self.W, self.H
        if sahne.get("harita") and not self.dikey:
            self.ulke_silueti(c, t, bas, W * 0.60, self.Y0 + 10 * u, W * 0.36, self.Y1 - self.Y0 - 20 * u)
        elif sahne.get("harita"):
            self.ulke_silueti(c, t, bas, M, self.Y0 + 70 * u, W - 2 * M, H * 0.34)
        maxw = (W * 0.55 if not self.dikey else W - 2 * M)
        y = (H * 0.50 if self.dikey else H * 0.36)
        if sahne.get("ust"):
            p = out_cubic(prog(t, bas + 0.25, 0.5))
            f = self.font(800, 24 * u)
            w = self.genislik(buyuk(sahne["ust"]), f, 3 * u) + 32 * u
            self.dikdortgen(c, M, y - 44 * u, w * p, 46 * u, "vurgu")
            c.save()
            c.clipRect(self.sk.Rect.MakeXYWH(M, y - 44 * u, w * p, 46 * u))
            self.yaz(c, buyuk(sahne["ust"]), M + 16 * u, y - 12 * u, f, "kara", 1, aralik=3 * u)
            c.restore()
            y += 40 * u
        boy = (112 if self.dikey else 122) * u
        fb = self.font("baslik", boy)
        satirlar = self.sar(sahne.get("baslik", ""), fb, maxw)
        if max(self.genislik(x, fb) for x in satirlar) > maxw:
            fb = self.sigdir(max(satirlar, key=len), "baslik", boy, maxw)
            boy = fb.getSize()
        for i, sat in enumerate(satirlar):
            y += boy * 1.04
            p = out_quint(prog(t, bas + 0.45 + i * 0.14, 0.75))
            c.save()
            c.clipRect(self.sk.Rect.MakeLTRB(0, y - boy * 1.02, W, y + boy * 0.28))
            self.yaz(c, sat, M, y + (1 - p) * boy * 1.1, fb, "metin", 1)
            c.restore()
        y += 44 * u
        pr = out_quint(prog(t, bas + 1.0, 0.8))
        self.dikdortgen(c, M, y, 220 * u * pr, 8 * u, "vurgu")
        y += 70 * u
        if sahne.get("alt"):
            p = out_cubic(prog(t, bas + 1.25, 0.6))
            fa = self.font(500, 38 * u)
            for sat in self.sar(sahne["alt"], fa, maxw):
                self.yaz(c, sat, M, y + (1 - p) * 18 * u, fa, "soluk", p)
                y += 50 * u

    def eksen_araligi(self, enk, enb, sayi=5, sifirdan=True):
        if sifirdan:
            enk = min(0.0, enk)
        aralik = (enb - enk) or 1
        ham = aralik / sayi
        k = 10 ** math.floor(math.log10(ham))
        adim = next(m * k for m in (1, 2, 5, 10) if m * k >= ham)
        alt = math.floor(enk / adim) * adim
        ust = math.ceil(enb / adim) * adim
        if ust - enb < adim * 0.15:
            ust += adim
        return alt, ust, adim

    def s_cubuk(self, c, sahne, t, bas, son):
        u, M, W = self.u, self.M, self.W
        y0 = self.baslik_blogu(c, sahne, t, bas) + 50 * u
        y1 = self.Y1 - 120 * u
        cub = sahne["cubuklar"]
        basamak = sahne.get("basamak", 1)
        alt, ust, adim = self.eksen_araligi(min(x["deger"] for x in cub), max(x["deger"] for x in cub), 4)
        alt, ust = sahne.get("eksen_min", alt), sahne.get("eksen_max", ust)
        x0, x1 = M + 70 * u, W - M

        def Y(v): return lerp(y1, y0, (v - alt) / (ust - alt))
        ga = out_cubic(prog(t, bas + 0.4, 0.6))
        fe = self.font(500, 22 * u)
        v = alt
        while v <= ust + 1e-9:
            yy = Y(v)
            self.cizgi(c, x0, yy, lerp(x0, x1, out_quint(ga)), yy, "cizgi", (2.5 if v == 0 else 1.2) * u, ga)
            self.yaz(c, sayi_yaz(v, 0 if float(adim).is_integer() else 1, self.ond, self.bin), x0 - 18 * u, yy + 8 * u, fe, "soluk", ga, hiza="sag")
            v += adim
        n = len(cub)
        aralik = (x1 - x0) / n
        bw = min(200 * u, aralik * 0.56)
        anlar = oge_anlari(sahne, cub, 0.9, 0.5)
        fd = self.font(800, (46 if n <= 4 else 36) * u)
        fl = self.font(700, 28 * u)
        fn = self.font(500, 22 * u)
        for i, (x, an) in enumerate(zip(cub, anlar)):
            cx = x0 + aralik * (i + 0.5)
            p = out_cubic(prog(t, an, 0.8))
            la = out_cubic(prog(t, an - 0.1, 0.4))
            rol = "vurgu" if x.get("vurgu") else x.get("renk", "notr")
            ytop = lerp(Y(0 if alt <= 0 else alt), Y(x["deger"]), p)
            ytaban = Y(0 if alt <= 0 else alt)
            if x.get("tahmin"):
                self.dikdortgen(c, cx - bw / 2, ytop, bw, ytaban - ytop, rol, 0.28 * la)
                kp = self.boya(rol, la, stroke=3 * u)
                kp.setPathEffect(self.sk.DashPathEffect.Make([10 * u, 7 * u], 0))
                c.drawRect(self.sk.Rect.MakeLTRB(cx - bw / 2 + 1.5 * u, ytop + 1.5 * u, cx + bw / 2 - 1.5 * u, ytaban), kp)
            else:
                self.dikdortgen(c, cx - bw / 2, ytop, bw, ytaban - ytop, rol, la)
            on, ek = sahne.get("on_ek", ""), sahne.get("ek", "")
            son_m = on + sayi_yaz(x["deger"], basamak, self.ond, self.bin) + ek
            m = on + sayi_yaz(x["deger"] * p, basamak, self.ond, self.bin) + ek
            self.sayi_ciz(c, m, son_m, cx, ytop - 20 * u, fd, "vurgu" if x.get("vurgu") else "metin", la, hiza="orta")
            self.yaz(c, x["etiket"], cx, y1 + 46 * u, fl, "metin", la, hiza="orta")
            if x.get("not"):
                self.yaz(c, x["not"], cx, y1 + 80 * u, fn, "soluk", la, hiza="orta")

    def s_cizgi(self, c, sahne, t, bas, son):
        sk, u, M, W = self.sk, self.u, self.M, self.W
        y0 = self.baslik_blogu(c, sahne, t, bas) + 70 * u
        y1 = self.Y1 - 110 * u
        nok = sahne["noktalar"]
        basamak = sahne.get("basamak", 1)
        degerler = [x["deger"] for x in nok]
        pay = (max(degerler) - min(degerler)) * 0.25
        alt, ust, adim = self.eksen_araligi(min(degerler) - pay, max(degerler), 4, sifirdan=sahne.get("sifirdan", False))
        x0, x1 = M + 80 * u, W - M - 40 * u

        def X(i): return lerp(x0 + 110 * u, x1 - 80 * u, i / max(1, len(nok) - 1))
        def Y(v): return lerp(y1, y0, (v - alt) / (ust - alt))
        ga = out_cubic(prog(t, bas + 0.4, 0.6))
        fe = self.font(500, 22 * u)
        # tahmin bölgesi: düz, yarı saydam kolon (degrade yok)
        ilk_tahmin = next((i for i, x in enumerate(nok) if x.get("tahmin")), None)
        if ilk_tahmin is not None:
            bx = (X(ilk_tahmin - 1) + X(ilk_tahmin)) / 2 if ilk_tahmin else x0
            self.dikdortgen(c, bx, y0 - 30 * u, x1 - bx, y1 - y0 + 30 * u, "panel", ga)
            self.yaz(c, sahne.get("tahmin_etiketi", "TAHMİN"), bx + 18 * u, y0 - 2 * u, self.font(800, 20 * u), "soluk", ga, aralik=3 * u)
        v = alt
        while v <= ust + 1e-9:
            yy = Y(v)
            self.cizgi(c, x0, yy, lerp(x0, x1, out_quint(ga)), yy, "cizgi", 1.2 * u, ga)
            self.yaz(c, sayi_yaz(v, 0 if float(adim).is_integer() else 1, self.ond, self.bin), x0 - 18 * u, yy + 8 * u, fe, "soluk", ga, hiza="sag")
            v += adim
        fl = self.font(700, 28 * u)
        for i, x in enumerate(nok):
            self.yaz(c, x["etiket"], X(i), y1 + 48 * u, fl, "soluk" if x.get("tahmin") else "metin", ga, hiza="orta")
        # çizgi: gerçekleşen düz, tahmin kesikli; tek bir ilerleme her ikisini sırayla çizer
        t0 = sahne.get("cizim_t", bas + 0.9)
        d = sahne.get("cizim_sure", 2.6)
        pr = in_out_cubic(prog(t, t0, d))
        n = len(nok) - 1
        bolum = pr * n
        rol = sahne.get("renk", "ikinci")
        son_gercek = (ilk_tahmin - 1) if ilk_tahmin else n
        alan = sk.Path()
        alan.moveTo(X(0), y1)
        for i in range(n + 1):
            if i <= bolum:
                alan.lineTo(X(i), Y(nok[i]["deger"]))
        if bolum < n:
            k = int(bolum)
            f = bolum - k
            alan.lineTo(lerp(X(k), X(k + 1), f), lerp(Y(nok[k]["deger"]), Y(nok[k + 1]["deger"]), f))
        uc_x = X(min(n, bolum))
        alan.lineTo(uc_x, y1)
        alan.close()
        c.drawPath(alan, self.boya(rol, 0.10))
        for i in range(n):
            if bolum <= i:
                break
            f = clamp(bolum - i)
            xa, ya, xb, yb = X(i), Y(nok[i]["deger"]), X(i + 1), Y(nok[i + 1]["deger"])
            kesik = [16 * u, 11 * u] if i >= son_gercek else None
            yol = sk.Path()
            yol.moveTo(xa, ya)
            yol.lineTo(xb, yb)
            self.iz(c, yol, f, rol, 6 * u, kesik=kesik)
        fd = self.font(800, 36 * u)
        fs = self.font(800, 50 * u)
        for i, x in enumerate(nok):
            if bolum + 1e-6 < i:
                continue
            p = out_cubic(prog(t, t0 + d * i / max(1, n), 0.4))
            son_mu = i == n and sahne.get("vurgu_son", True)
            cx, cy = X(i), Y(x["deger"])
            c.drawCircle(cx, cy, 11 * u * p, self.boya("zemin"))
            c.drawCircle(cx, cy, 11 * u * p, self.boya("vurgu" if son_mu else rol, 1, stroke=5 * u))
            metin = sahne.get("on_ek", "") + sayi_yaz(x["deger"], basamak, self.ond, self.bin) + sahne.get("ek", "")
            self.yaz(c, metin, cx, cy - 32 * u - (1 - p) * 10 * u, fs if son_mu else fd, "vurgu" if son_mu else "metin", p, hiza="orta")

    def s_sayac(self, c, sahne, t, bas, son):
        u, M, W = self.u, self.M, self.W
        y0 = self.baslik_blogu(c, sahne, t, bas) + 40 * u
        kartlar = sahne["kartlar"]
        n = len(kartlar)
        bosluk = 36 * u
        anlar = oge_anlari(sahne, kartlar, 0.9, 0.9)
        if self.dikey:
            kw, kh = W - 2 * M, min(300 * u, (self.Y1 - 60 * u - y0 - bosluk * (n - 1)) / n)
            yerler = [(M, y0 + i * (kh + bosluk)) for i in range(n)]
        else:
            kw = (W - 2 * M - bosluk * (n - 1)) / n
            kh = min(400 * u, self.Y1 - 40 * u - y0)
            yerler = [(M + i * (kw + bosluk), y0 + 20 * u) for i in range(n)]
        for k, an, (x, y) in zip(kartlar, anlar, yerler):
            a = out_cubic(prog(t, an - 0.25, 0.45))
            p = out_quint(prog(t, an, k.get("sure", 1.4)))
            if a <= 0:
                continue
            y += (1 - a) * 24 * u
            self.dikdortgen(c, x, y, kw, kh, "panel", a)
            self.dikdortgen(c, x, y, kw * out_quint(a), 6 * u, "vurgu" if k.get("vurgu") else "cizgi", a)
            pad = 36 * u
            fl = self.font(700, 26 * u)
            self.yaz(c, buyuk(k["etiket"]), x + pad, y + 62 * u, self.sigdir(buyuk(k["etiket"]), 700, 26 * u, kw - 2 * pad, 1.5 * u), "soluk", a, aralik=1.5 * u)
            basamak = k.get("basamak", 0)
            son_m = sayi_yaz(k["deger"], basamak, self.ond, self.bin)
            once = k.get("baslangic", 0)
            m = sayi_yaz(lerp(once, k["deger"], p), basamak, self.ond, self.bin) if not k.get("yil") else str(round(lerp(once, k["deger"], p)))
            if k.get("yil"):
                son_m = str(k["deger"])
            boy = (150 if not self.dikey else 130) * u
            fs = self.sigdir(son_m + " " + k.get("birim", ""), 800, boy, kw - 2 * pad)
            fb = self.font(700, fs.getSize() * 0.42)
            ny = y + (kh * 0.62 if not self.dikey else kh * 0.68)
            w = self.sayi_ciz(c, m, son_m, x + pad, ny, fs, "vurgu" if k.get("vurgu") else "metin", a)
            if k.get("birim"):
                self.yaz(c, k["birim"], x + pad + w + 14 * u, ny, fb, "soluk", a)
            if k.get("not"):
                fn = self.font(500, 24 * u)
                for i, sat in enumerate(self.sar(k["not"], fn, kw - 2 * pad)[:2]):
                    self.yaz(c, sat, x + pad, y + kh - 34 * u - (len(self.sar(k["not"], fn, kw - 2 * pad)[:2]) - 1 - i) * 32 * u, fn, "soluk",
                             a * out_cubic(prog(t, an + 0.6, 0.5)))

    # --- harita ---
    def harita_yollari(self):
        if self._harita is None:
            self._harita = harita_verisi()
        return self._harita

    def izdusum(self, kutu, x, y, w, h):
        """eşdikdörtgen izdüşüm, enlem düzeltmeli; `kutu` (lon0, lat0, lon1, lat1) çerçeveye sığar"""
        lon0, lat0, lon1, lat1 = kutu
        k = math.cos(math.radians((lat0 + lat1) / 2))
        gw, gh = (lon1 - lon0) * k, lat1 - lat0
        olcek = min(w / gw, h / gh)
        ox = x + (w - gw * olcek) / 2
        oy = y + (h - gh * olcek) / 2
        return lambda lon, lat: (ox + (lon - lon0) * k * olcek, oy + (lat1 - lat) * olcek)

    def ulke_yolu(self, iso, P):
        sk = self.sk
        yol = sk.Path()
        for halka in self.harita_yollari().get(iso, []):
            for i, (lon, lat) in enumerate(halka):
                x, y = P(lon, lat)
                (yol.moveTo if i == 0 else yol.lineTo)(x, y)
            yol.close()
        return yol

    def ulke_silueti(self, c, t, bas, x, y, w, h, iso="FR"):
        P = self.izdusum((-5.2, 41.3, 9.6, 51.2), x, y, w, h)
        yol = self.ulke_yolu(iso, P)
        pr = in_out_cubic(prog(t, bas + 0.3, 1.8))
        c.drawPath(yol, self.boya("panel", out_cubic(prog(t, bas + 1.2, 0.8))))
        self.iz(c, yol, pr, "cizgi", 3 * self.u)

    def s_harita(self, c, sahne, t, bas, son):
        sk, u, M, W = self.sk, self.u, self.M, self.W
        y0 = self.baslik_blogu(c, sahne, t, bas) + 10 * u
        if self.dikey:
            mx, my, mw, mh = M, y0, W - 2 * M, (self.Y1 - y0) * 0.68
        else:
            mx, my, mw, mh = M, y0, (W - 2 * M) * 0.58, self.Y1 - y0 - 10 * u
        kutu = sahne.get("kutu", [-5.4, 41.2, 9.8, 51.3])
        P = self.izdusum(kutu, mx, my, mw, mh)
        ga = out_cubic(prog(t, bas + 0.3, 0.6))
        c.save()
        c.clipRect(sk.Rect.MakeXYWH(mx - 40 * u, my, mw + 80 * u, mh))
        ana = sahne.get("ulke", "FR")
        for iso in self.harita_yollari():
            if iso == ana:
                continue
            yol = self.ulke_yolu(iso, P)
            c.drawPath(yol, self.boya("panel", ga * 0.7))
            c.drawPath(yol, self.boya("cizgi", ga, stroke=1.4 * u))
        c.restore()
        yol = self.ulke_yolu(ana, P)
        pr = in_out_cubic(prog(t, bas + 0.5, 1.6))
        c.drawPath(yol, self.boya("cizgi", out_cubic(prog(t, bas + 1.4, 0.7)) * 0.75))
        self.iz(c, yol, pr, "ikinci", 3 * u)
        noktalar = sahne.get("noktalar", [])
        anlar = oge_anlari(sahne, noktalar, 2.0, 0.6)
        fa = self.font(800, 28 * u)
        fe = self.font(500, 22 * u)
        for nk, an in zip(noktalar, anlar):
            a = out_cubic(prog(t, an, 0.4))
            if a <= 0:
                continue
            x, y = P(nk["lon"], nk["lat"])
            rol = "vurgu" if nk.get("vurgu", True) else "metin"
            # tek seferlik nabız: ince, keskin kenarlı bir halka (degrade değil) ve hızla söner
            nb = prog(t, an, 0.9)
            if 0 < nb < 1:
                c.drawCircle(x, y, lerp(10, 46, out_cubic(nb)) * u, self.boya(rol, (1 - nb) * 0.8, stroke=3 * u))
            c.drawCircle(x, y, 10 * u * out_cubic(a), self.boya(rol))
            c.drawCircle(x, y, 10 * u * out_cubic(a), self.boya("zemin", 1, stroke=3 * u))
            yon = nk.get("yon", "sag")
            satir2 = nk.get("etiket", "")
            bw = max(self.genislik(nk["ad"], fa), self.genislik(satir2, fe)) + 32 * u
            bh = (84 if satir2 else 52) * u
            dx = {"sag": 34, "sol": -34}.get(yon, 0) * u
            bx = x + dx if yon != "sol" else x + dx - bw
            by = y - bh / 2
            if yon == "ust":
                bx, by = x - bw / 2, y - bh - 34 * u
            if yon == "alt":
                bx, by = x - bw / 2, y + 34 * u
            la = out_cubic(prog(t, an + 0.15, 0.4))
            self.cizgi(c, x, y, bx if yon == "sag" else bx + bw if yon == "sol" else x, by + bh / 2 if yon in ("sag", "sol") else (by + bh if yon == "ust" else by), "metin", 2 * u, la)
            self.dikdortgen(c, bx, by, bw, bh, "zemin", la * 0.92)
            p = self.boya(rol, la, stroke=2 * u)
            c.drawRect(sk.Rect.MakeXYWH(bx, by, bw, bh), p)
            self.yaz(c, nk["ad"], bx + 16 * u, by + 38 * u, fa, "metin", la)
            if satir2:
                self.yaz(c, satir2, bx + 16 * u, by + 70 * u, fe, "soluk", la)
        k = sahne.get("kpi")
        if k:
            an = k.get("t", bas + 1.2)
            a = out_cubic(prog(t, an - 0.2, 0.5))
            p = out_quint(prog(t, an, 1.3))
            if self.dikey:
                kx, ky, kw = M, my + mh + 40 * u, W - 2 * M
            else:
                kx, ky, kw = mx + mw + 70 * u, my + mh * 0.22, W - M - (mx + mw + 70 * u)
            self.dikdortgen(c, kx, ky, 8 * u, 230 * u if not self.dikey else 190 * u, "vurgu", a)
            son_m = sayi_yaz(k["deger"], k.get("basamak", 0), self.ond, self.bin)
            fs = self.sigdir(son_m, 800, (190 if not self.dikey else 150) * u, kw - 40 * u)
            self.sayi_ciz(c, sayi_yaz(k["deger"] * p, k.get("basamak", 0), self.ond, self.bin), son_m, kx + 36 * u,
                          ky + fs.getSize() * 0.78, fs, "metin", a)
            fl = self.font(600, 32 * u)
            for i, sat in enumerate(self.sar(k["etiket"], fl, kw - 40 * u)):
                self.yaz(c, sat, kx + 36 * u, ky + fs.getSize() * 0.78 + 52 * u + i * 42 * u, fl, "soluk", a)
            for j, ek in enumerate(k.get("ekler", [])):
                ea = out_cubic(prog(t, ek.get("t", an + 1.0 + j * 0.6), 0.45))
                ey = ky + (330 if not self.dikey else 0) * u + j * 96 * u
                if self.dikey:
                    continue
                self.cizgi(c, kx + 36 * u, ey - 52 * u, kx + kw, ey - 52 * u, "cizgi", 1.5 * u, ea)
                self.yaz(c, ek["baslik"], kx + 36 * u, ey - 6 * u, self.font(800, 30 * u), "metin", ea)
                self.yaz(c, ek["metin"], kx + 36 * u, ey + 30 * u, self.sigdir(ek["metin"], 500, 24 * u, kw - 40 * u), "soluk", ea)

    def s_karsilastirma(self, c, sahne, t, bas, son):
        u, M, W = self.u, self.M, self.W
        y0 = self.baslik_blogu(c, sahne, t, bas) + 40 * u
        taraflar = [sahne["sol"], sahne["sag"]]
        enb = max(x["deger"] for x in taraflar)
        anlar = oge_anlari(sahne, taraflar, 0.9, 1.0)
        basamak = sahne.get("basamak", 0)
        renkler = [sahne["sol"].get("renk", "ikinci"), sahne["sag"].get("renk", "vurgu")]
        if self.dikey:
            kw = W - 2 * M
            kh = (self.Y1 - y0 - 40 * u) / 2
            yerler = [(M, y0), (M, y0 + kh + 40 * u)]
        else:
            kw = (W - 2 * M - 80 * u) / 2
            kh = self.Y1 - y0 - 40 * u
            yerler = [(M, y0), (M + kw + 80 * u, y0)]
            ga = out_cubic(prog(t, bas + 0.5, 0.6))
            mx = M + kw + 40 * u
            self.cizgi(c, mx, y0, mx, lerp(y0, y0 + kh, ga), "cizgi", 2 * u, ga)
        icerik_h = 400 * u
        yerler = [(kx, ky + max(0.0, (kh - icerik_h) / 2) - 30 * u) for kx, ky in yerler]
        for x, an, (kx, ky), rol in zip(taraflar, anlar, yerler, renkler):
            a = out_cubic(prog(t, an - 0.2, 0.45))
            p = out_quint(prog(t, an, 1.4))
            if a <= 0:
                continue
            fl = self.font(700, 30 * u)
            self.yaz(c, buyuk(x["etiket"]), kx, ky + 50 * u, self.sigdir(buyuk(x["etiket"]), 700, 30 * u, kw, 2 * u), "soluk", a, aralik=2 * u)
            son_m = sayi_yaz(x["deger"], basamak, self.ond, self.bin)
            fs = self.sigdir(son_m, 800, (170 if not self.dikey else 150) * u, kw)
            ny = ky + 50 * u + fs.getSize() * 0.95
            self.sayi_ciz(c, sayi_yaz(x["deger"] * p, basamak, self.ond, self.bin), son_m, kx, ny, fs, "metin", a)
            by = ny + 44 * u
            self.dikdortgen(c, kx, by, kw, 26 * u, "panel", a)
            self.dikdortgen(c, kx, by, kw * x["deger"] / enb * p, 26 * u, rol, a)
            if x.get("not"):
                self.yaz(c, x["not"], kx, by + 76 * u, self.font(500, 28 * u), "soluk", a * out_cubic(prog(t, an + 0.5, 0.5)))

    def s_zaman(self, c, sahne, t, bas, son):
        u, M, W = self.u, self.M, self.W
        y0 = self.baslik_blogu(c, sahne, t, bas) + 30 * u
        olaylar = sahne["olaylar"]
        n = len(olaylar)
        anlar = oge_anlari(sahne, olaylar, 0.8, 0.55)
        ilk_gelecek = next((i for i, x in enumerate(olaylar) if x.get("durum") == "gelecek"), n)
        fd = self.font(800, 30 * u)
        fm = self.font(500, 26 * u)
        if self.dikey:
            ax = M + 20 * u
            ys = [lerp(y0 + 40 * u, self.Y1 - 120 * u, i / max(1, n - 1)) for i in range(n)]
            pos = [(ax, y) for y in ys]
        else:
            ay = y0 + (self.Y1 - y0) * 0.42
            yarim = (W - 2 * M) / n / 2
            xs = [lerp(M + yarim, W - M - yarim, i / max(1, n - 1)) for i in range(n)]
            pos = [(x, ay) for x in xs]
        # eksen: geçmiş düz, gelecek kesikli; ilerleme olayların anlarına göre
        ilerleme = 0.0
        for i, an in enumerate(anlar):
            ilerleme = max(ilerleme, i + out_cubic(prog(t, an, 0.45)) - 1 if i else out_cubic(prog(t, an - 0.4, 0.4)))
        for i in range(n - 1):
            f = clamp(ilerleme - i)
            if f <= 0:
                break
            (xa, ya), (xb, yb) = pos[i], pos[i + 1]
            gel = i + 1 >= ilk_gelecek
            self.cizgi(c, xa, ya, lerp(xa, xb, f), lerp(ya, yb, f), "soluk" if gel else "metin", 4 * u, 1,
                       kesik=[12 * u, 10 * u] if gel else None)
        for i, (x, an) in enumerate(zip(olaylar, anlar)):
            a = out_cubic(prog(t, an, 0.45))
            if a <= 0:
                continue
            px, py = pos[i]
            gel = x.get("durum") == "gelecek"
            rol = "ikinci" if gel else ("vurgu" if x.get("vurgu") else "metin")
            c.drawCircle(px, py, 14 * u * a, self.boya("zemin"))
            c.drawCircle(px, py, 14 * u * a, self.boya(rol, 1, stroke=5 * u) if gel else self.boya(rol))
            if self.dikey:
                tx = px + 44 * u
                self.yaz(c, x["tarih"], tx, py + 4 * u, fd, rol if rol != "metin" else "metin", a)
                for j, sat in enumerate(self.sar(x["metin"], fm, W - M - tx)[:2]):
                    self.yaz(c, sat, tx, py + 42 * u + j * 34 * u, fm, "soluk", a)
            else:
                colw = (W - 2 * M) / n - 20 * u
                ust = i % 2 == 0
                ty = py - 60 * u if ust else py + 76 * u
                self.cizgi(c, px, py + (-18 if ust else 18) * u, px, py + (-34 if ust else 34) * u, "cizgi", 2 * u, a)
                self.yaz(c, x["tarih"], px, ty + (1 - a) * (10 if ust else -10) * u, fd, rol, a, hiza="orta")
                satirlar = self.sar(x["metin"], fm, colw)[:3]
                for j, sat in enumerate(satirlar):
                    yy = (ty - 44 * u - (len(satirlar) - 1 - j) * 34 * u) if ust else (ty + 40 * u + j * 34 * u)
                    self.yaz(c, sat, px, yy, fm, "soluk", a, hiza="orta")
        if sahne.get("bugun") is not None:
            i = sahne["bugun"]  # bugün, olay i ile i+1 arasında
            a = out_cubic(prog(t, anlar[min(i + 1, n - 1)] - 0.2, 0.4))
            if a > 0 and i + 1 < n:
                (xa, ya), (xb, yb) = pos[i], pos[i + 1]
                bx, by = (xa + xb) / 2, (ya + yb) / 2
                f = self.font(800, 18 * u)
                et = sahne.get("bugun_etiketi", "BUGÜN")
                w = self.genislik(et, f, 2 * u) + 20 * u
                if self.dikey:
                    self.dikdortgen(c, bx + 30 * u, by - 16 * u, w, 30 * u, "vurgu", a)
                    self.yaz(c, et, bx + 40 * u, by + 5 * u, f, "kara", a, aralik=2 * u)
                else:
                    self.dikdortgen(c, bx - w / 2, by - 15 * u, w, 30 * u, "vurgu", a)
                    self.yaz(c, et, bx - w / 2 + 10 * u, by + 6 * u, f, "kara", a, aralik=2 * u)

    def s_alinti(self, c, sahne, t, bas, son):
        u, M, W = self.u, self.M, self.W
        maxw = W - 2 * M - (0 if self.dikey else 300 * u)
        x = M + (0 if self.dikey else 150 * u)
        y = self.Y0 + (260 if self.dikey else 170) * u
        a = out_cubic(prog(t, bas + 0.2, 0.5))
        self.yaz(c, "“", x - 10 * u, y + 40 * u, self.font("baslik", 220 * u), "vurgu", a)
        y += 120 * u
        fm = self.font(600, (56 if not self.dikey else 52) * u)
        for i, sat in enumerate(self.sar(sahne["metin"], fm, maxw)):
            p = out_cubic(prog(t, bas + 0.4 + i * 0.12, 0.6))
            self.yaz(c, sat, x, y + (1 - p) * 16 * u, fm, "metin", p)
            y += 74 * u
        p = out_cubic(prog(t, bas + 1.0, 0.6))
        self.dikdortgen(c, x, y + 10 * u, 60 * u * p, 4 * u, "vurgu", p)
        self.yaz(c, sahne.get("kisi", ""), x, y + 70 * u, self.font(800, 32 * u), "metin", p)
        self.yaz(c, sahne.get("unvan", ""), x, y + 112 * u, self.font(500, 26 * u), "soluk", p)

    def s_kapanis(self, c, sahne, t, bas, son):
        u, M, W, H = self.u, self.M, self.W, self.H
        maxw = W - 2 * M
        y = H * (0.42 if not self.dikey else 0.36)
        a = out_cubic(prog(t, bas + 0.15, 0.5))
        fb = self.font("baslik", (96 if not self.dikey else 88) * u)
        for i, sat in enumerate(self.sar(sahne.get("baslik", ""), fb, maxw)):
            p = out_quint(prog(t, bas + 0.2 + i * 0.12, 0.7))
            self.yaz(c, sat, M, y + (1 - p) * 30 * u, fb, "metin", p)
            y += fb.getSize() * 1.06
        self.dikdortgen(c, M, y - 20 * u, 160 * u * out_quint(prog(t, bas + 0.5, 0.6)), 8 * u, "vurgu")
        y += 50 * u
        if sahne.get("alt"):
            self.yaz(c, sahne["alt"], M, y, self.font(600, 36 * u), "soluk", a)
            y += 80 * u
        if sahne.get("kaynaklar"):
            ka = out_cubic(prog(t, bas + 0.7, 0.6))
            self.yaz(c, sahne.get("kaynaklar_etiketi", "KAYNAKLAR"), M, y, self.font(800, 20 * u), "vurgu", ka, aralik=3 * u)
            y += 40 * u
            fk = self.font(500, 24 * u)
            for sat in self.sar(" · ".join(sahne["kaynaklar"]), fk, maxw):
                self.yaz(c, sat, M, y, fk, "soluk", ka)
                y += 34 * u


def yuzey(W, H):
    import skia
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))


def video(s: dict, W: int, H: int, hedef: Path) -> Path:
    c = Cizici(s, W, H)
    surf = yuzey(W, H)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                           "-r", str(s["fps"]), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "15",
                           "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                           str(hedef)], stdin=subprocess.PIPE)
    for i in range(int(round(s["sure"] * s["fps"]))):
        c.kare(surf.getCanvas(), i / s["fps"])
        ff.stdin.write(surf.makeImageSnapshot().tobytes())
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("ffmpeg görüntüyü kodlayamadı")
    return hedef


def kareler(s: dict, W: int, H: int, anlar: list[float], klasor: Path) -> list[Path]:
    import skia
    c = Cizici(s, W, H)
    surf = yuzey(W, H)
    klasor.mkdir(parents=True, exist_ok=True)
    out = []
    for t in anlar:
        c.kare(surf.getCanvas(), t)
        yol = klasor / f"kare-{W}x{H}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(yol), skia.kPNG)
        out.append(yol)
    return out
