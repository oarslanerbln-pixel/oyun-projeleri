"""Minyatür şablonunun görüntüsü: Osmanlı minyatürü dilinde bir mekân avlusu (skia).

Düz perspektif (uzak olan yukarıda, boyu küçülmez), ince koyu konturlar, düz boya alanları, altın
gök ve tezhipli çerçeve. Degrade ya da ışık parlaması yok: her yüzey tek renk; gece geçişinde bile
bütün gök tek renk olarak değişir. Her kare t'nin saf fonksiyonudur. Ölçüler 1080 piksellik kısa
kenara göre verilir; dikey ve yatay yerleşim aynı tanımdan çıkar (`Yerlesim`).

Anlatının omurgası "doluluk"tur (0–1): avludaki minderler boşken başlar, sahneler doluluğu
yükselttikçe misafirler kapıdan girip yürüyerek yerlerine oturur. Gerekenler: skia-python
(Linux'ta libegl1, libgl1). Yazı tipleri (SIL OFL) ilk kullanımda indirilir, depoya girmez.
"""

from __future__ import annotations

import math
import os
import random
import subprocess
import urllib.request
from pathlib import Path

# ---------- palet (minyatür boyaları: altın, lacivert, zencefre kırmızısı, malakit yeşili) ----------
KAGIT, KENAR = 0xFFF2E7CC, 0xFFE4D2A8
ALTIN, ALTIN_ACIK, ALTIN_KOYU = 0xFFCFA542, 0xFFEBCB72, 0xFF9E7A28
LAJ, LAJ_KOYU, GECE = 0xFF223F8F, 0xFF16295C, 0xFF1B2C64
KIRMIZI, KIRMIZI_KOYU = 0xFFC2412D, 0xFF8E2A1E
YESIL, YESIL_KOYU, SERVI = 0xFF4A9461, 0xFF2D6443, 0xFF1F4A33
PEMBE, TURKUAZ, MOR, TURUNCU = 0xFFE7A9A1, 0xFF3C9FA3, 0xFF74507F, 0xFFDB8A2E
TEN, KONTUR, BEYAZ = 0xFFF1CFAA, 0xFF3A2416, 0xFFFBF6EA
TAS, TAS_CIZGI, SOKAK = 0xFFEBDCBC, 0xFFD6C098, 0xFFDCC59C
DUVAR, KUBBE, AHSAP, CINI = 0xFFF0E2C4, 0xFF8399AC, 0xFF7A4A2A, 0xFF2F6FB0
KEMER_GUN, KEMER_GECE = 0xFF3D2E4E, 0xFFF0C25A

KAFTANLAR = [KIRMIZI, LAJ, YESIL, MOR, TURUNCU, PEMBE, TURKUAZ, ALTIN_KOYU, KIRMIZI_KOYU, YESIL_KOYU]
ICLER = [BEYAZ, ALTIN_ACIK, PEMBE, 0xFFB9D3E8, 0xFFE9D8A6]
BASLIKLAR = ["sarik", "sarik", "bork", "yemeni", "yemeni", "kavuk"]

# ---------- yazı tipleri (SIL OFL; depoya girmez, önbelleğe indirilir) ----------
FONTLAR = {"marka": ("CinzelDecorative-Bold.ttf", "cinzeldecorative"), "metin": ("CormorantSC-Bold.ttf", "cormorantsc")}
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/{dizin}/{ad}"
FONT_ONBELLEK = Path(os.environ.get("MINYATUR_FONT_DIZINI", Path.home() / ".cache" / "studyo" / "fontlar"))


def font_bul(rol: str) -> str:
    ad, dizin = FONTLAR[rol]
    yol = FONT_ONBELLEK / ad
    if yol.exists():
        return str(yol)
    r = subprocess.run(["fc-match", "-f", "%{file}", ad.split("-")[0]], capture_output=True, text=True)
    if r.returncode == 0 and Path(r.stdout.strip()).name == ad:
        return r.stdout.strip()
    FONT_ONBELLEK.mkdir(parents=True, exist_ok=True)
    try:
        for dosya, hedef in ((ad, yol), ("OFL.txt", FONT_ONBELLEK / f"OFL-{dizin}.txt")):
            with urllib.request.urlopen(FONT_URL.format(dizin=dizin, ad=dosya), timeout=60) as y:
                hedef.write_bytes(y.read())
    except OSError as e:
        raise RuntimeError(f"{ad} indirilemedi ({e}); dosyayı MINYATUR_FONT_DIZINI klasörüne koyun") from e
    return str(yol)


# ---------- yardımcılar ----------
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, p): return a + (b - a) * p
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def out_cubic(p): return 1 - (1 - p) ** 3
def in_out_cubic(p): return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2
def out_back(p, s=1.7): p -= 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


def renk_karis(a: int, b: int, p: float) -> int:
    """iki ARGB rengin doğrusal karışımı (bütün yüzey tek renk kalır)"""
    out = 0xFF000000
    for kay in (16, 8, 0):
        out |= int(round(lerp((a >> kay) & 255, (b >> kay) & 255, clamp(p)))) << kay
    return out


def boya(renk, a=1.0, cizgi=0.0):
    import skia
    p = skia.Paint(AntiAlias=True, Color=renk)
    p.setAlphaf(clamp(a))
    if cizgi:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(cizgi)
        p.setStrokeJoin(skia.Paint.kRound_Join)
        p.setStrokeCap(skia.Paint.kRound_Cap)
    return p


def yol(noktalar, kapali=True):
    import skia
    p = skia.Path()
    p.moveTo(*noktalar[0])
    for n in noktalar[1:]:
        p.lineTo(*n)
    if kapali:
        p.close()
    return p


def egri(noktalar, kapali=True):
    """noktalardan geçen yumuşak yol (Catmull-Rom → kübik Bezier)"""
    import skia
    p = skia.Path()
    n = len(noktalar)
    p.moveTo(*noktalar[0])
    son = n if kapali else n - 1
    for i in range(son):
        p0, p1 = noktalar[i - 1] if (i or kapali) else noktalar[0], noktalar[i]
        p2 = noktalar[(i + 1) % n]
        p3 = noktalar[(i + 2) % n] if (kapali or i + 2 < n) else p2
        p.cubicTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                  p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1])
    if kapali:
        p.close()
    return p


def badem(x0, y0, x1, y1, w):
    """iki uç arasında badem (yaprak / taç yaprağı) biçimi"""
    import skia
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L * w, dx / L * w
    p = skia.Path()
    p.moveTo(x0, y0)
    p.quadTo(mx + nx, my + ny, x1, y1)
    p.quadTo(mx - nx, my - ny, x0, y0)
    p.close()
    return p


def dolgu(cv, p, renk, a=1.0, kalin=2.0, kontur=KONTUR):
    cv.drawPath(p, boya(renk, a))
    if kalin:
        cv.drawPath(p, boya(kontur, a, kalin))


def yildiz4(x, y, r):
    return yol([(x, y - r), (x + r * .25, y - r * .25), (x + r, y), (x + r * .25, y + r * .25),
                (x, y + r), (x - r * .25, y + r * .25), (x - r, y), (x - r * .25, y - r * .25)])


# ---------- zaman: sahneler, doluluk, gece, kuyruk, usul ----------
def sahne_bitisleri(s: dict) -> list[tuple[dict, float, float]]:
    sh = s["sahneler"]
    return [(x, x["bas"], sh[i + 1]["bas"] if i + 1 < len(sh) else s["sure"]) for i, x in enumerate(sh)]


def doluluk_anahtarlari(s: dict) -> list[tuple[float, float, float]]:
    """(başlangıç, süre, hedef) rampaları; ilk değer ilk sahneden"""
    out = []
    for i, (x, bas, son) in enumerate(sahne_bitisleri(s)):
        if "doluluk" not in x:
            continue
        if i == 0:
            out.append((-1.0, 0.0, float(x["doluluk"])))
        else:
            out.append((bas + 0.1, min(1.3, (son - bas) * 0.6), float(x["doluluk"])))
    return out or [(-1.0, 0.0, 0.0)]


def doluluk(s: dict, t: float) -> float:
    v = 0.0
    for t0, d, hedef in doluluk_anahtarlari(s):
        if t >= t0:
            v = lerp(v, hedef, in_out_cubic(prog(t, t0, d)))
    return v


def gece(s: dict, t: float) -> float:
    v = 0.0
    for x, bas, _ in sahne_bitisleri(s):
        if "gece" in x:
            v = lerp(v, 1.0 if x["gece"] else 0.0, in_out_cubic(prog(t, bas, 1.0)))
    return v


def kuyruk_bilgisi(s: dict) -> tuple[int, float]:
    """(kişi sayısı, geliş anı): kapıda sıra bekleyenler bir kez gelir ve kalır"""
    for x, bas, _ in sahne_bitisleri(s):
        if x.get("kuyruk"):
            return int(x["kuyruk"]), bas + 0.9
    return 0, 0.0


def usul(s: dict) -> list[tuple[float, str]]:
    """def vuruşları (an, 'dum'|'tek'|'ke'): müzik ve defzenin eli aynı listeden"""
    sb = sahne_bitisleri(s)
    bas = next((b for x, b, _ in sb if x["tur"] == "avlu"), None)
    if bas is None:
        return []
    son = next((b for x, b, _ in sb if x["tur"] == "kapanis"), s["sure"])
    tepe = [(b, e) for x, b, e in sb if x["tur"] == "avlu" and (x.get("gece") or x.get("kuyruk"))]
    onaltilik = 15 / s["muzik"].get("bpm", 96)
    desen = {0: "dum", 4: "tek", 6: "ke", 8: "dum", 12: "tek", 14: "ke"}  # sofyan, on altılık ızgarada
    out, k = [], 0
    t = bas
    while t < son - 0.05:
        tur = desen.get(k % 16)
        if tur is None and any(b <= t < e for b, e in tepe) and k % 2:
            tur = "ke"  # zirvede araya sıkışan hafif vuruşlar
        if tur:
            out.append((round(t, 4), tur))
        k += 1
        t = bas + k * onaltilik
    return out


# ---------- yerleşim ----------
class Yerlesim:
    def __init__(self, VW: float, VH: float):
        self.VW, self.VH = VW, VH
        self.dik = dik = VH > VW
        self.m = 30
        self.bant = 60 if dik else 52
        ic = self.m + self.bant
        self.panel = (ic, ic, VW - ic, VH - ic)
        cx = VW / 2
        if dik:
            self.fs = 1.0
            self.gok_alt, self.kosk = 640, (cx, 712, 1.0)
            self.duvar, self.duvar_h, self.sokak = 1586, 56, 1790
            self.bahce = 100
            satirlar, sutunlar = [930, 1104, 1278, 1452], [cx - 212, cx + 212]
            self.kartus, self.semse, self.serit = (cx, 214), (cx, 1080, 318), (cx, 1500)
            self.ay = (VW - ic - 70, ic + 215)
        else:
            self.fs = 0.76
            self.gok_alt, self.kosk = 352, (cx, 408, 0.74)
            self.duvar, self.duvar_h, self.sokak = 876, 42, 990
            self.bahce = 150
            satirlar, sutunlar = [560, 736], [cx - 650, cx - 370, cx + 370, cx + 650]
            self.kartus, self.semse, self.serit = (cx - 560, 214), (cx, 548, 270), (cx, 892)
            self.ay = (VW - ic - 150, ic + 100)
        self.zemin_ust = self.kosk[1]
        self.fk = self.fs * 1.3  # insan ölçeği (masalardan biraz iri: minyatürde kişi öne çıkar)
        self.masalar = [(x, y) for y in satirlar for x in sutunlar]
        self.koridor = 120 * self.fs  # halı yolunun genişliği
        self.kapi = (cx, self.duvar + self.duvar_h)


KOLTUKLAR = [(-94, 12, 1), (94, 12, -1), (0, -42, 0)]  # masa başına: sol (sağa bakar), sağ, arka (öne bakar)
YURUME = 1.4


class Cizici:
    def __init__(self, s: dict, W: int, H: int):
        import skia
        self.s, self.W, self.H = s, W, H
        self.u = min(W, H) / 1080
        self.VW, self.VH = W / self.u, H / self.u
        self.L = Yerlesim(self.VW, self.VH)
        self.mekan = s.get("mekan", {})
        self.ikram = self.mekan.get("ikram", "yemek")
        self.marka = s.get("marka", {})
        self._tf = {r: skia.Typeface.MakeFromFile(font_bul(r)) for r in FONTLAR}
        self._resim: dict = {}
        self._koltuklar()
        self._kuyruk()

    # ----- hazırlık -----
    def font(self, rol, boy):
        import skia
        f = skia.Font(self._tf[rol], boy)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setSubpixel(True)
        return f

    def _kisi(self, rng) -> dict:
        return {"renk": rng.choice(KAFTANLAR), "ic": rng.choice(ICLER), "bas": rng.choice(BASLIKLAR),
                "bas_renk": rng.choice([KIRMIZI, LAJ, YESIL, MOR, TURUNCU, ALTIN]), "sakal": rng.random() < 0.45,
                "faz": rng.random() * 6.28, "hiz": rng.uniform(0.35, 0.6)}

    def _koltuklar(self):
        L, fs = self.L, self.L.fs
        rng = random.Random(self.s.get("tohum", 7))
        self.koltuk = []
        for mi, (mx, my) in enumerate(L.masalar):
            for dx, dy, yon in KOLTUKLAR:
                k = self._kisi(rng)
                k.update(x=mx + dx * fs, y=my + dy * fs, yon=yon, masa=mi, mx=mx, my=my)
                if k["bas"] == "yemeni":
                    k["sakal"] = False
                self.koltuk.append(k)
        # dostlar birlikte gelir: masalar karışık sırayla, her masanın koltukları art arda dolar
        masalar = list(range(len(L.masalar)))
        rng.shuffle(masalar)
        sira = []
        for mi in masalar:
            ks = [i for i, k in enumerate(self.koltuk) if k["masa"] == mi]
            rng.shuffle(ks)
            sira += ks
        n = len(sira)
        adim = 1 / 60
        anlar = [doluluk(self.s, i * adim) for i in range(int(self.s["sure"] / adim) + 2)]
        for k, i in enumerate(sira):
            esik = (k + 0.5) / n
            k_ = self.koltuk[i]
            if anlar[0] >= esik:
                k_["oturma"] = -99.0
            else:
                j = next((j for j, v in enumerate(anlar) if v >= esik), None)
                k_["oturma"] = j * adim + YURUME * 0.4 if j is not None else 1e9
            k_["yol"] = self._yol(k_, rng, KOLTUKLAR.index(next(x for x in KOLTUKLAR if x[2] == k_["yon"])))

    def _yol(self, k, rng, sira):
        """sokaktan kapıya, halı yolundan sıra arasına, oradan mindere; masa arkadaşları yan yana yürür"""
        L, fs = self.L, self.L.fs
        gx, gy = L.kapi
        serit = gx + (sira - 1) * 0.3 * L.koridor + rng.uniform(-6, 6)
        yan = -1  # misafirler soldan gelir; kapının sağı sıra bekleyenlere kalır
        koridor_y = k["my"] + (-92 if k["yon"] == 0 else 88) * fs
        return [(gx + yan * 210 * fs, L.sokak - 6), (serit, L.sokak - 6), (serit, gy - 10), (serit, koridor_y),
                (k["x"], koridor_y), (k["x"], k["y"])]

    def _kuyruk(self):
        n, t0 = kuyruk_bilgisi(self.s)
        rng = random.Random(99)
        L, fs = self.L, self.L.fs
        self.sira = []
        for i in range(n):
            k = self._kisi(rng)
            k.update(hedef=L.kapi[0] + (90 + i * 76) * fs, gelis=t0 + i * 0.16)
            self.sira.append(k)

    # ----- ana çizim -----
    def kare(self, cv, t: float):
        import skia
        cv.save()
        cv.clear(0xFF000000 | (KAGIT & 0xFFFFFF))
        cv.scale(self.u, self.u)
        L = self.L
        x0, y0, x1, y1 = L.panel
        ac = prog(t, 0.1, 0.55)  # sahnenin boyası kâğıda oturur
        g = gece(self.s, t)
        cv.save()
        cv.clipRect(skia.Rect.MakeLTRB(x0, y0, x1, y1))
        if ac > 0:
            cv.saveLayerAlpha(None, int(255 * out_cubic(ac)))
            self.gok(cv, t, g)
            self.resim(cv, "zemin", self._zemin)
            self.resim(cv, "duvar", self._duvar)
            cv.restore()
        self.bahce(cv, t, g)
        self.kosk(cv, t, g)
        self.avlu(cv, t)
        cv.restore()
        self.kartus(cv, t)
        self.kapanis(cv, t)
        self.cerceve(cv, t)
        cv.restore()

    def resim(self, cv, ad, fn):
        """değişmeyen katmanı bir kez kaydet, her karede yeniden oynat"""
        import skia
        if ad not in self._resim:
            kayit = skia.PictureRecorder()
            fn(kayit.beginRecording(skia.Rect.MakeWH(self.VW, self.VH)))
            self._resim[ad] = kayit.finishRecordingAsPicture()
        cv.drawPicture(self._resim[ad])

    # ----- gök: altın gündüz, lacivert gece, Çin bulutları, yıldız, hilal -----
    def gok(self, cv, t, g):
        import skia
        L = self.L
        x0, y0, x1, _ = L.panel
        cv.drawRect(skia.Rect.MakeLTRB(x0, y0, x1, L.gok_alt + 40), boya(renk_karis(ALTIN, GECE, g)))
        if g < 1:
            for i, (bx, by, uz) in enumerate(self._bulutlar()):
                self.bulut(cv, bx + 14 * math.sin(t * 0.35 + i) + t * 6 * (1 if i % 2 else -1), by, uz, 1 - g)
        if g > 0:
            rng = random.Random(5)
            for i in range(26):
                sx, sy = rng.uniform(x0 + 20, x1 - 20), rng.uniform(y0 + 20, L.gok_alt - 60)
                pp = clamp((g - 0.3 - rng.random() * 0.4) / 0.3)
                if pp <= 0:
                    continue
                r = (4 + 3 * rng.random()) * (0.75 + 0.25 * math.sin(t * 3 + i * 1.7)) * pp
                cv.drawPath(yildiz4(sx, sy, r * 1.6), boya(ALTIN_ACIK, pp))
            # hilal
            mx, my = L.ay
            pp = clamp((g - 0.4) / 0.5)
            ay = skia.Op(skia.Path.Circle(mx, my, 40), skia.Path.Circle(mx + 17, my - 9, 34), skia.PathOp.kDifference_PathOp)
            dolgu(cv, ay, ALTIN_ACIK, pp, 1.6)

    def _bulutlar(self):
        L = self.L
        x0, y0, x1, _ = L.panel
        if L.dik:
            return [(x0 + 70, y0 + 120, 260), (x1 - 330, y0 + 70, 230), (x0 + 210, y0 + 300, 190), (x1 - 250, y0 + 330, 180)]
        return [(x0 + 80, y0 + 70, 300), (x0 + 470, y0 + 170, 220), (x1 - 640, y0 + 60, 260), (x1 - 330, y0 + 170, 240)]

    def bulut(self, cv, x, y, uz, a):
        """Çin bulutu: dalgalı şerit ve iki ucunda kıvrım"""
        nok = [(x + uz * i / 24, y + 9 * math.sin(i / 24 * math.pi * 3)) for i in range(25)]

        def kivrim(cx_, cy_, r, yon):
            return [(cx_ + yon * r * (1 - k / 18) * math.cos(k / 18 * 4.4 + 1.6), cy_ + r * (1 - k / 18) * math.sin(k / 18 * 4.4 + 1.6) * -1)
                    for k in range(19)]
        sol = kivrim(x, y - 16, 16, -1)[::-1]
        sag = kivrim(x + uz, y - 16 + 9 * math.sin(math.pi * 3), 16, 1)
        p = egri(sol + nok + sag, kapali=False)
        cv.drawPath(p, boya(KONTUR, a * 0.9, 17))
        cv.drawPath(p, boya(BEYAZ, a, 12))
        cv.drawPath(p, boya(0xFFB9D3E8, a, 3))

    # ----- köşk -----
    def kosk(self, cv, t, g):
        import skia
        cx, by, s = self.L.kosk
        p = out_cubic(prog(t, 0.3, 0.7))
        if p <= 0:
            return
        cv.save()
        cv.translate(cx, by + (1 - p) * 50)
        cv.scale(s, s)
        cv.saveLayerAlpha(None, int(255 * p))
        # yan köşk çatıları ve kubbe (gövdenin arkasında)
        for yx in (-250, 250):
            dolgu(cv, yol([(yx - 56, -270), (yx + 56, -270), (yx, -346)]), KUBBE, 1, 2.2)
            cv.drawLine(yx, -346, yx, -372, boya(ALTIN_KOYU, 1, 3))
            cv.drawCircle(yx, -374, 6, boya(ALTIN))
        dolgu(cv, yol([(-96, -276), (96, -276), (96, -316), (-96, -316)]), DUVAR, 1, 2)
        pencere = renk_karis(KEMER_GUN, KEMER_GECE, g)
        for wx in (-62, -21, 21, 62):
            dolgu(cv, egri([(wx - 9, -284), (wx - 9, -300), (wx, -310), (wx + 9, -300), (wx + 9, -284)]), pencere, 1, 1.5)
        kubbe = skia.Path()
        kubbe.moveTo(-104, -314)
        kubbe.cubicTo(-104, -396, -48, -430, 0, -432)
        kubbe.cubicTo(48, -430, 104, -396, 104, -314)
        kubbe.close()
        dolgu(cv, kubbe, KUBBE, 1, 2.4)
        for k in (-60, -25, 25, 60):
            cv.drawLine(k, -316, k * 0.35, -428, boya(0xFF6A8095, 1, 1.6))
        cv.drawLine(0, -432, 0, -470, boya(ALTIN_KOYU, 1, 3.4))
        cv.drawCircle(0, -462, 7, boya(ALTIN))
        hil = skia.Op(skia.Path.Circle(0, -486, 13), skia.Path.Circle(5, -490, 11), skia.PathOp.kDifference_PathOp)
        dolgu(cv, hil, ALTIN, 1, 1.2)
        # saçak
        dolgu(cv, yol([(-326, -248), (326, -248), (300, -276), (-300, -276)]), AHSAP, 1, 2.2)
        for k in range(-300, 301, 30):
            cv.drawLine(k, -248, k * 0.97, -240, boya(KONTUR, 1, 1.4))
        # gövde ve basamaklar
        dolgu(cv, yol([(-284, -248), (284, -248), (284, -30), (-284, -30)]), DUVAR, 1, 2.2)
        dolgu(cv, yol([(-336, -30), (336, -30), (336, 0), (-336, 0)]), TAS, 1, 2)
        cv.drawLine(-336, -15, 336, -15, boya(TAS_CIZGI, 1, 2))
        # friz: altın bant, geometrik desen (yazı yok)
        dolgu(cv, yol([(-284, -238), (284, -238), (284, -214), (-284, -214)]), ALTIN, 1, 1.6)
        for k in range(-272, 273, 24):
            dolgu(cv, yol([(k, -226 - 7), (k + 7, -226), (k, -226 + 7), (k - 7, -226)]), LAJ, 1, 0)
        # çini panolar
        for px in (-262, 204):
            dolgu(cv, yol([(px, -200), (px + 58, -200), (px + 58, -44), (px, -44)]), CINI, 1, 2)
            cv.drawRect(skia.Rect.MakeLTRB(px + 6, -194, px + 52, -50), boya(BEYAZ, 1, 1.4))
            for ry in range(-180, -50, 26):
                for rx in (px + 18, px + 40):
                    for k in range(4):
                        a_ = k * math.pi / 2 + math.pi / 4
                        cv.drawPath(badem(rx, ry, rx + 9 * math.cos(a_), ry + 9 * math.sin(a_), 3.2), boya(BEYAZ))
                    cv.drawCircle(rx, ry, 2.4, boya(KIRMIZI))
        # kemerler, sütunlar, kandiller
        ic = renk_karis(KEMER_GUN, KEMER_GECE, g)
        for ax in (-130, 0, 130):
            kemer = egri([(ax - 48, -30), (ax - 48, -136), (ax - 30, -176), (ax, -198), (ax + 30, -176), (ax + 48, -136), (ax + 48, -30)])
            dolgu(cv, kemer, ic, 1, 2.2)
            cv.drawPath(kemer, boya(ALTIN_KOYU, 1, 1.4))
            cv.drawLine(ax, -198, ax, -150, boya(KONTUR, 1, 1.2))
            dolgu(cv, egri([(ax - 8, -150), (ax + 8, -150), (ax + 4, -128), (ax, -122), (ax - 4, -128)]),
                  renk_karis(ALTIN_KOYU, BEYAZ, g), 1, 1.2)
        for sx in (-195, -65, 65, 195):
            dolgu(cv, yol([(sx - 9, -30), (sx + 9, -30), (sx + 9, -170), (sx - 9, -170)]), BEYAZ, 1, 1.6)
            dolgu(cv, yol([(sx - 15, -170), (sx + 15, -170), (sx + 9, -182), (sx - 9, -182)]), ALTIN, 1, 1.4)
        cv.restore()
        cv.restore()

    # ----- bahçe şeritleri: servi, çiçekli ağaç, lale ve karanfil -----
    def bahce(self, cv, t, g):
        import skia
        L = self.L
        x0, _, x1, _ = L.panel
        p = out_cubic(prog(t, 0.35, 0.7))
        if p <= 0:
            return
        cv.saveLayerAlpha(None, int(255 * p))
        for sx in (x0, x1 - L.bahce):
            cv.drawRect(skia.Rect.MakeLTRB(sx, L.zemin_ust - 20, sx + L.bahce, L.duvar), boya(YESIL))
            cv.drawLine(sx + (L.bahce if sx == x0 else 0), L.zemin_ust - 20, sx + (L.bahce if sx == x0 else 0), L.duvar,
                        boya(YESIL_KOYU, 1, 3))
            rng = random.Random(int(sx))
            for yy in range(int(L.zemin_ust + 40), int(L.duvar - 10), 46):
                for xx in (sx + L.bahce * 0.25, sx + L.bahce * 0.75):
                    ox = xx + rng.uniform(-8, 8)
                    self.cicek(cv, ox, yy + rng.uniform(-6, 6), rng.choice((KIRMIZI, PEMBE, BEYAZ, ALTIN)), t, ox)
        servi_y = [L.zemin_ust + k * (L.duvar - L.zemin_ust) / 3 + 120 * L.fs for k in range(3)] if L.dik else [L.zemin_ust + 150, L.duvar - 60]
        for i, sx in enumerate((x0 + L.bahce / 2, x1 - L.bahce / 2)):
            for j, yy in enumerate(servi_y):
                self.servi(cv, sx, yy, (220 if L.dik else 190) * L.fs * (1.1 if j == 0 else 1), t, i * 3 + j)
        cv.restore()

    def cicek(self, cv, x, y, renk, t, tohum):
        cv.save()
        cv.translate(x, y)
        cv.rotate(4 * math.sin(t * 1.6 + tohum * 0.05))
        cv.drawLine(0, 0, 0, -16, boya(YESIL_KOYU, 1, 2))
        cv.drawPath(badem(0, -6, -9, -12, 3), boya(YESIL_KOYU))
        dolgu(cv, egri([(-6, -14), (-7, -24), (-2, -20), (0, -27), (2, -20), (7, -24), (6, -14)]), renk, 1, 1.2)
        cv.restore()

    def servi(self, cv, x, y, h, t, i):
        cv.save()
        cv.translate(x, y)
        cv.rotate(1.5 * math.sin(t * 0.9 + i))
        w = h * 0.17
        p = egri([(0, 0), (w * 0.9, -h * 0.2), (w, -h * 0.5), (w * 0.55, -h * 0.82), (0, -h), (-w * 0.55, -h * 0.82), (-w, -h * 0.5), (-w * 0.9, -h * 0.2)])
        dolgu(cv, p, SERVI, 1, 2.2)
        for k in range(1, 7):
            yy = -h * k / 7.5
            ww = w * (0.85 - 0.08 * k)
            cv.drawPath(egri([(-ww, yy + 8), (0, yy - 4), (ww, yy + 8)], kapali=False), boya(YESIL, 1, 1.6))
        cv.drawLine(0, 0, 0, 10, boya(AHSAP, 1, 5))
        cv.restore()

    # ----- zemin: taş döşeme, halı yolu (kaydedilir) -----
    def _zemin(self, cv):
        import skia
        L = self.L
        x0, _, x1, _ = L.panel
        r = skia.Rect.MakeLTRB(x0 + L.bahce, L.zemin_ust - 20, x1 - L.bahce, L.duvar)
        cv.drawRect(r, boya(TAS))
        cv.save()
        cv.clipRect(r)
        ad = 64
        for k in range(-40, 40):
            b = k * ad
            cv.drawLine(x0 + b, L.zemin_ust - 20, x0 + b + 1400, L.zemin_ust + 1380, boya(TAS_CIZGI, 1, 1.6))
            cv.drawLine(x1 - b, L.zemin_ust - 20, x1 - b - 1400, L.zemin_ust + 1380, boya(TAS_CIZGI, 1, 1.6))
        cv.restore()
        cx, w = self.VW / 2, L.koridor
        hali = skia.Rect.MakeLTRB(cx - w / 2, L.zemin_ust + 10, cx + w / 2, L.duvar)
        cv.drawRect(hali, boya(KIRMIZI))
        cv.drawRect(hali, boya(KONTUR, 1, 2))
        ic = skia.Rect.MakeLTRB(cx - w / 2 + 10, L.zemin_ust + 20, cx + w / 2 - 10, L.duvar)
        cv.drawRect(ic, boya(ALTIN, 1, 3))
        for yy in range(int(L.zemin_ust + 50), int(L.duvar - 10), 54):
            dolgu(cv, yol([(cx, yy - 18), (cx + 18, yy), (cx, yy + 18), (cx - 18, yy)]), ALTIN, 1, 1.4)
            cv.drawCircle(cx, yy, 5, boya(LAJ))
        # müzisyen sekisi
        my = L.zemin_ust + 54 * L.fs
        seki = skia.Rect.MakeLTRB(cx - 150 * L.fs, my - 34 * L.fs, cx + 150 * L.fs, my + 14 * L.fs)
        cv.drawRect(seki, boya(LAJ))
        cv.drawRect(seki, boya(KONTUR, 1, 2))
        cv.drawRect(seki.makeInset(6, 6), boya(ALTIN, 1, 2.5))

    # ----- duvar, kapı, sokak (kaydedilir) -----
    def _duvar(self, cv):
        import skia
        L = self.L
        x0, _, x1, y1 = L.panel
        cv.drawRect(skia.Rect.MakeLTRB(x0, L.duvar + L.duvar_h, x1, y1), boya(SOKAK))
        rng = random.Random(3)
        for _ in range(60):
            cv.drawCircle(rng.uniform(x0, x1), rng.uniform(L.duvar + L.duvar_h + 12, y1 - 6), rng.uniform(1.5, 3.2), boya(TAS_CIZGI))
        gx, gw = self.VW / 2, L.koridor * 0.62 + 30
        for a, b in ((x0, gx - gw), (gx + gw, x1)):
            r = skia.Rect.MakeLTRB(a, L.duvar, b, L.duvar + L.duvar_h)
            cv.drawRect(r, boya(DUVAR))
            for yy in (L.duvar + L.duvar_h / 3, L.duvar + 2 * L.duvar_h / 3):
                cv.drawLine(a, yy, b, yy, boya(TAS_CIZGI, 1, 1.4))
            for k, xx in enumerate(range(int(a), int(b), 38)):
                o = 19 if k % 2 else 0
                cv.drawLine(xx + o, L.duvar, xx + o, L.duvar + L.duvar_h / 3, boya(TAS_CIZGI, 1, 1.2))
            cv.drawRect(r, boya(KONTUR, 1, 2))
            for xx in range(int(a) + 8, int(b) - 10, 30):  # mazgal
                dolgu(cv, yol([(xx, L.duvar), (xx + 16, L.duvar), (xx + 16, L.duvar - 10), (xx + 8, L.duvar - 16), (xx, L.duvar - 10)]), DUVAR, 1, 1.4)
        for px in (gx - gw, gx + gw):  # kapı ayakları
            dolgu(cv, yol([(px - 16, L.duvar + L.duvar_h + 4), (px + 16, L.duvar + L.duvar_h + 4), (px + 16, L.duvar - 30), (px - 16, L.duvar - 30)]), TAS, 1, 2)
            dolgu(cv, egri([(px - 16, L.duvar - 30), (px, L.duvar - 62), (px + 16, L.duvar - 30)]), KUBBE, 1, 1.8)
            cv.drawCircle(px, L.duvar - 66, 5, boya(ALTIN))

    # ----- avlu: masalar, minderler, misafirler, garsonlar, müzisyenler, kuyruk (y'ye göre sıralı) -----
    def avlu(self, cv, t):
        L, fs, fk = self.L, self.L.fs, self.L.fk
        isler = []
        for mi, (mx, my) in enumerate(L.masalar):
            pm = out_back(prog(t, 0.55 + mi * 0.06, 0.4), 1.4)
            if pm <= 0:
                continue
            isler.append((my - 2, lambda c, mx=mx, my=my, pm=pm: self.sini(c, mx, my, fs * pm)))
            for k in self.koltuk:
                if k["masa"] != mi:
                    continue
                isler.append((k["y"] - 0.5, lambda c, k=k, pm=pm: self.minder(c, k["x"], k["y"], fs * pm)))
                if t >= k["oturma"]:
                    isler.append((k["y"], lambda c, k=k, pm=pm: self.oturan(c, k["x"], k["y"], fk * min(1, pm), k["yon"], k, t)))
        for k in self.koltuk:
            if k["oturma"] - YURUME <= t < k["oturma"]:
                q = (t - k["oturma"] + YURUME) / YURUME
                (x, y), yon, d = self.yol_uzerinde(k["yol"], 0.35 * q + 0.65 * in_out_cubic(q))
                isler.append((y, lambda c, x=x, y=y, yon=yon, d=d, k=k, a=clamp(q / 0.1): self.ayakta(c, x, y, fk, yon, k, d / 9, 1.0, a=a)))
        # garsonlar: sıra aralarında tepsiyle gidip gelir
        pg = prog(t, 1.0, 0.4)
        if pg > 0:
            rng = random.Random(41)
            for i in range(2 if L.dik else 3):
                mx, my = L.masalar[min(len(L.masalar) - 1, i * (len(L.masalar) // (2 if L.dik else 3)) + (1 if L.dik else 0))]
                yy = my + 88 * fs
                a, b = L.panel[0] + L.bahce + 40, L.panel[2] - L.bahce - 40
                faz = t * 0.16 + i * 0.37
                u = 0.5 - 0.5 * math.cos(2 * math.pi * faz)
                yon = 1 if math.sin(2 * math.pi * faz) > 0 else -1
                k = self._kisi(rng)
                k.update(renk=[LAJ, KIRMIZI, YESIL][i], ic=BEYAZ, bas="kavuk", sakal=False)
                x = lerp(a, b, u)
                isler.append((yy, lambda c, x=x, yy=yy, yon=yon, k=k, d=u * (b - a): self.ayakta(c, x, yy, fk, yon, k, d / 9, pg, tepsi=True)))
        # müzisyenler
        pmz = out_back(prog(t, 0.7, 0.4), 1.4)
        if pmz > 0:
            my = L.zemin_ust + 54 * fs
            for i, (dx, alet) in enumerate(((-62, "ud"), (62, "def"))):
                k = {"renk": [MOR, KIRMIZI][i], "ic": BEYAZ, "bas": "sarik", "bas_renk": [YESIL, LAJ][i], "sakal": True, "faz": i, "hiz": 0}
                isler.append((my - 10, lambda c, dx=dx, alet=alet, k=k, my=my: self.muzisyen(c, self.VW / 2 + dx * fs, my - 8 * fs, fk * pmz, alet, k, t)))
        # kapıda sıra bekleyenler
        for i, k in enumerate(self.sira):
            if t < k["gelis"]:
                continue
            u = in_out_cubic(prog(t, k["gelis"], 1.3))
            bas_x = L.panel[2] + 40
            x = lerp(bas_x, k["hedef"], u)
            yuru = 1.0 if u < 1 else 0.0
            yon = -1
            isler.append((L.sokak - 2, lambda c, x=x, k=k, yuru=yuru, yon=yon: self.ayakta(c, x, L.sokak - 2, fk, yon, k, (x - bas_x) / 9, yuru,
                                                                                              bekle=(t + k["faz"]))))
        isler.sort(key=lambda x: x[0])
        for _, fn in isler:
            fn(cv)

    def yol_uzerinde(self, noktalar, u):
        """kırık çizgide yay uzunluğuna göre u (0–1) noktası, bakış yönü ve katedilen mesafe"""
        parcalar = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(noktalar, noktalar[1:])]
        d = clamp(u) * sum(parcalar)
        kalan, yon = d, 1
        for (a, b), l in zip(zip(noktalar, noktalar[1:]), parcalar):
            if abs(b[0] - a[0]) > 1:
                yon = 1 if b[0] > a[0] else -1
            if kalan <= l:
                q = kalan / l if l else 1.0
                return (lerp(a[0], b[0], q), lerp(a[1], b[1], q)), yon, d
            kalan -= l
        return noktalar[-1], yon, d

    # ----- nesneler -----
    def sini(self, cv, x, y, s):
        import skia
        cv.save()
        cv.translate(x, y)
        cv.scale(s, s)
        dolgu(cv, yol([(-20, -4), (20, -4), (28, 8), (-28, 8)]), AHSAP, 1, 1.6)
        r = skia.Rect.MakeLTRB(-66, -40, 66, 0)
        cv.drawOval(r, boya(ALTIN))
        cv.drawOval(r.makeInset(9, 6), boya(ALTIN_KOYU, 1, 2.2))
        cv.drawOval(r, boya(KONTUR, 1, 2.2))
        if self.ikram == "kahve":
            for k, (dx, dy) in enumerate(((-34, -20), (0, -27), (34, -20), (-12, -12), (18, -11))):
                if k % 2:
                    dolgu(cv, yol([(dx - 6, dy - 16), (dx + 6, dy - 16), (dx + 3, dy - 7), (dx + 5, dy), (dx - 5, dy), (dx - 3, dy - 7)]), 0xFFB2472E, 0.92, 1.2)
                else:
                    dolgu(cv, egri([(dx - 8, dy - 9), (dx + 8, dy - 9), (dx + 6, dy), (dx - 6, dy)]), BEYAZ, 1, 1.3)
                    cv.drawLine(dx - 7, dy - 6, dx + 7, dy - 6, boya(KIRMIZI, 1, 1.6))
        else:
            for dx, dy, rx, ry, renk in ((-30, -20, 15, 8, BEYAZ), (4, -26, 14, 7, KIRMIZI), (30, -18, 13, 7, YESIL), (-4, -12, 12, 6, TURUNCU)):
                o = skia.Rect.MakeLTRB(dx - rx, dy - ry, dx + rx, dy + ry)
                cv.drawOval(o, boya(renk))
                cv.drawOval(o, boya(KONTUR, 1, 1.3))
            cv.drawOval(skia.Rect.MakeLTRB(-50, -26, -40, -18), boya(ALTIN_KOYU))
        cv.restore()

    def minder(self, cv, x, y, s):
        import skia
        cv.save()
        cv.translate(x, y)
        cv.scale(s, s)
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(-30, -10, 30, 6), 7, 7)
        cv.drawRRect(rr, boya(KIRMIZI_KOYU))
        cv.drawRRect(rr, boya(KONTUR, 1, 1.6))
        for k in (-22, -11, 0, 11, 22):
            cv.drawCircle(k, -2, 2, boya(ALTIN))
        cv.restore()

    def bas_giy(self, cv, hx, hy, k, profil):
        """başlık: sarık, börk, kavuk ya da yemeni (yüzü açık başörtüsü)"""
        tur, r2 = k["bas"], k["bas_renk"]
        if tur == "sarik":
            dolgu(cv, egri([(hx - 15, hy - 6), (hx - 13, hy - 18), (hx, hy - 24), (hx + 13, hy - 18), (hx + 15, hy - 6), (hx, hy - 3)]), BEYAZ, 1, 1.5)
            cv.drawPath(egri([(hx - 13, hy - 12), (hx, hy - 9), (hx + 13, hy - 14)], kapali=False), boya(0xFFC9C0AE, 1, 1.4))
            dolgu(cv, egri([(hx - 6, hy - 20), (hx, hy - 29), (hx + 6, hy - 20)]), r2, 1, 1.3)
        elif tur == "bork":
            dolgu(cv, yol([(hx - 11, hy - 8), (hx - 8, hy - 38), (hx + 7, hy - 40), (hx + 11, hy - 8)]), BEYAZ, 1, 1.5)
            dolgu(cv, yol([(hx - 12, hy - 12), (hx + 12, hy - 12), (hx + 12, hy - 6), (hx - 12, hy - 6)]), ALTIN, 1, 1.2)
            cv.drawLine(hx + 2, hy - 38, hx + 2 - 14 * (1 if profil >= 0 else -1), hy - 20, boya(BEYAZ, 1, 4))
        elif tur == "kavuk":
            dolgu(cv, egri([(hx - 11, hy - 6), (hx - 10, hy - 22), (hx, hy - 28), (hx + 10, hy - 22), (hx + 11, hy - 6)]), r2, 1, 1.5)
            cv.drawLine(hx - 11, hy - 8, hx + 11, hy - 8, boya(BEYAZ, 1, 3.4))
        else:
            cv.drawLine(hx - 8 * profil, hy - 4, hx - 16 * profil - (0 if profil else 10), hy + 24, boya(r2, 1, 10))
            dolgu(cv, egri([(hx - 15, hy + 4), (hx - 16, hy - 12), (hx, hy - 22), (hx + 16, hy - 12), (hx + 15, hy + 4), (hx, hy + 8)]), r2, 1, 1.5)
            dolgu(cv, egri([(hx - 7, hy - 19), (hx, hy - 30), (hx + 7, hy - 19)]), ALTIN, 1, 1.2)

    def bas(self, cv, hx, hy, k, profil):
        """yüz: badem göz, ince kaş; profil = 1 sağa bakar, 0 öne bakar"""
        if k["bas"] == "yemeni":
            self.bas_giy(cv, hx, hy, k, profil)
            cv.drawCircle(hx + 2 * profil, hy, 10.5, boya(TEN))
            cv.drawCircle(hx + 2 * profil, hy, 10.5, boya(KONTUR, 1, 1.3))
        else:
            cv.drawCircle(hx, hy, 12, boya(TEN))
            cv.drawCircle(hx, hy, 12, boya(KONTUR, 1, 1.5))
            if k["sakal"]:
                dolgu(cv, egri([(hx - 9 + 3 * profil, hy + 4), (hx + 9 + 3 * profil, hy + 4), (hx + 3 * profil, hy + 17)]), KONTUR, 1, 0)
        if profil:
            ex = hx + 5 * profil
            cv.drawCircle(ex, hy - 1, 1.6, boya(KONTUR))
            cv.drawLine(ex - 3, hy - 5, ex + 3, hy - 5, boya(KONTUR, 1, 1.1))
        else:
            for ex in (hx - 4.5, hx + 4.5):
                cv.drawCircle(ex, hy - 1, 1.5, boya(KONTUR))
                cv.drawLine(ex - 3, hy - 5, ex + 3, hy - 5, boya(KONTUR, 1, 1.1))
        if k["bas"] != "yemeni":
            self.bas_giy(cv, hx, hy, k, profil)

    def oturan(self, cv, x, y, s, yon, k, t):
        cv.save()
        cv.translate(x, y)
        cv.scale(s * (-1 if yon < 0 else 1), s)
        profil = 1 if yon else 0
        if profil:
            govde = egri([(-30, 0), (-31, -28), (-20, -50), (6, -55), (18, -42), (40, -16), (42, 0)])
        else:
            govde = egri([(-34, 0), (-33, -26), (-22, -48), (-10, -55), (10, -55), (22, -48), (33, -26), (34, 0)])
        dolgu(cv, govde, k["renk"], 1, 1.8)
        cv.drawPath(yol([(-6 + 4 * profil, -54), (0 + 4 * profil, -40), (6 + 4 * profil, -54)]), boya(k["ic"]))
        cv.drawLine(-20 + 6 * profil, -30, 20 + 8 * profil, -30, boya(ALTIN, 1, 3))
        # yeme / sohbet hareketi: el sofraya uzanır, ağza gelir, dizine döner
        e = (t * k["hiz"] + k["faz"]) % 1.0
        dinlen = (14, -20) if profil else (-10, -22)
        if e < 0.25:
            el = (lerp(dinlen[0], 40, out_cubic(e / 0.25)), lerp(dinlen[1], -30, out_cubic(e / 0.25)))
        elif e < 0.45:
            q = in_out_cubic((e - 0.25) / 0.2)
            el = (lerp(40, 12, q), lerp(-30, -58, q))
        elif e < 0.65:
            q = in_out_cubic((e - 0.45) / 0.2)
            el = (lerp(12, dinlen[0], q), lerp(-58, dinlen[1], q))
        else:
            el = dinlen
        if not profil:
            el = (el[0] * 0.3 - 8, el[1])
        omuz = (8, -46) if profil else (-14, -46)
        cv.drawLine(*omuz, *el, boya(KONTUR, 1, 11))
        cv.drawLine(*omuz, *el, boya(k["renk"], 1, 8))
        cv.drawCircle(*el, 4.6, boya(TEN))
        cv.drawCircle(*el, 4.6, boya(KONTUR, 1, 1.1))
        if not profil:
            cv.drawCircle(13, -22, 4.6, boya(TEN))
            cv.drawCircle(13, -22, 4.6, boya(KONTUR, 1, 1.1))
        egim = 2.0 * math.sin(t * 1.3 + k["faz"])
        cv.save()
        cv.rotate(egim)
        self.bas(cv, 5 * profil, -68, k, profil)
        cv.restore()
        cv.restore()

    def ayakta(self, cv, x, y, s, yon, k, faz, yuru, tepsi=False, bekle=None, a=1.0):
        cv.save()
        if a < 1:
            cv.saveLayerAlpha(None, int(255 * a))
        cv.translate(x, y)
        cv.scale(s * (-1 if yon < 0 else 1), s)
        sw = math.sin(faz) * yuru
        bob = abs(math.sin(faz)) * 3 * yuru
        for ay in (-1, 1):
            cv.drawOval(_oval(ay * 7 + ay * sw * 9, -2, 8, 4), boya(KIRMIZI_KOYU))
        cv.translate(0, -bob)
        kaftan = egri([(-15, -80), (15, -80), (19, -44), (25, -6), (0, -2), (-24, -6), (-18, -44)])
        arka_el = (-4 - sw * 13, -40)
        cv.drawLine(-2, -74, *arka_el, boya(KONTUR, 1, 10))
        cv.drawLine(-2, -74, *arka_el, boya(k["renk"], 1, 7))
        dolgu(cv, kaftan, k["renk"], 1, 1.8)
        cv.drawPath(yol([(2, -79), (9, -79), (13, -6), (6, -4)]), boya(k["ic"]))
        cv.drawLine(-17, -50, 19, -50, boya(ALTIN, 1, 4))
        if tepsi:
            el = (12, -110)
            cv.drawLine(6, -74, *el, boya(KONTUR, 1, 10))
            cv.drawLine(6, -74, *el, boya(k["renk"], 1, 7))
            import skia
            o = skia.Rect.MakeLTRB(-22, -124, 42, -112)
            cv.drawOval(o, boya(ALTIN))
            cv.drawOval(o, boya(KONTUR, 1, 1.4))
            for dx, renk in ((-6, BEYAZ), (10, KIRMIZI), (26, YESIL)):
                cv.drawOval(_oval(dx, -124, 7, 5), boya(renk))
                cv.drawOval(_oval(dx, -124, 7, 5), boya(KONTUR, 1, 1))
        else:
            sallan = 0
            if bekle is not None and yuru == 0:
                sallan = max(0, math.sin(bekle * 1.7)) ** 3  # sırada bekleyen ara sıra kapıyı gösterir
            el = (lerp(6 + sw * 13, 30, sallan), lerp(-40, -66, sallan))
            cv.drawLine(6, -74, *el, boya(KONTUR, 1, 10))
            cv.drawLine(6, -74, *el, boya(k["renk"], 1, 7))
        cv.drawCircle(*el, 4.6, boya(TEN))
        cv.drawCircle(*el, 4.6, boya(KONTUR, 1, 1.1))
        self.bas(cv, 4, -92, k, 1)
        if a < 1:
            cv.restore()
        cv.restore()

    def muzisyen(self, cv, x, y, s, alet, k, t):
        import skia
        cv.save()
        cv.translate(x, y)
        cv.scale(s, s)
        govde = egri([(-34, 0), (-33, -26), (-22, -48), (-10, -55), (10, -55), (22, -48), (33, -26), (34, 0)])
        dolgu(cv, govde, k["renk"], 1, 1.8)
        cv.drawPath(yol([(-6, -54), (0, -40), (6, -54)]), boya(k["ic"]))
        if alet == "ud":
            tel = math.sin(t * 9) * 2
            cv.save()
            cv.rotate(-24)
            dolgu(cv, egri([(-22, -24), (-6, -40), (20, -36), (26, -24), (14, -10), (-12, -10)]), AHSAP, 1, 1.6)
            cv.drawCircle(4, -26, 4, boya(KONTUR))
            dolgu(cv, yol([(20, -34), (58, -40), (58, -34), (22, -28)]), 0xFF5C3A20, 1, 1.4)
            cv.restore()
            for el in ((-6 + tel, -26), (24, -42)):
                cv.drawCircle(*el, 4.6, boya(TEN))
                cv.drawCircle(*el, 4.6, boya(KONTUR, 1, 1.1))
        else:
            vur = 0.0
            for an, tur in self._usul():
                if 0 <= t - an < 0.16:
                    vur = (1 - (t - an) / 0.16) * (1.0 if tur == "dum" else 0.6)
            o = skia.Rect.MakeLTRB(-6, -64, 30, -24)
            cv.drawOval(o, boya(0xFFF3DFB8))
            cv.drawOval(o, boya(ALTIN_KOYU, 1, 5))
            cv.drawOval(o, boya(KONTUR, 1, 1.4))
            for a_ in range(0, 360, 60):
                cv.drawCircle(12 + 18 * math.cos(math.radians(a_)), -44 + 20 * math.sin(math.radians(a_)), 2.4, boya(ALTIN_ACIK))
            el = (lerp(-18, 4, vur), lerp(-58, -46, vur))
            cv.drawCircle(*el, 4.6, boya(TEN))
            cv.drawCircle(*el, 4.6, boya(KONTUR, 1, 1.1))
        cv.save()
        cv.rotate(2 * math.sin(t * 2.2 + k["faz"]))
        self.bas(cv, 0, -68, k, 0)
        cv.restore()
        cv.restore()

    def _usul(self):
        if not hasattr(self, "_usul_"):
            self._usul_ = usul(self.s)
        return self._usul_

    # ----- lale (marka amblemi) -----
    def lale(self, cv, x, y, s, a=1.0):
        cv.save()
        cv.translate(x, y)
        cv.scale(s, s)
        cv.drawPath(egri([(0, -16), (3, 14), (-2, 44)], kapali=False), boya(YESIL_KOYU, a, 5))
        dolgu(cv, badem(0, 36, -38, -14, 9), YESIL, a, 1.6)
        dolgu(cv, badem(0, 26, 34, -26, 8), YESIL, a, 1.6)
        dolgu(cv, badem(-3, -14, -30, -84, 12), KIRMIZI, a, 1.8)
        dolgu(cv, badem(3, -14, 30, -84, 12), KIRMIZI, a, 1.8)
        dolgu(cv, badem(0, -12, 0, -100, 14), KIRMIZI, a, 1.8)
        cv.drawLine(0, -24, 0, -78, boya(KIRMIZI_KOYU, a, 1.6))
        cv.restore()

    # ----- kartuş (zirvedeki tek cümle) -----
    def lobe(self, w, h, uc=36):
        return egri([(-w / 2 - uc, 0), (-w / 2, -h / 2), (0, -h / 2 - 4), (w / 2, -h / 2), (w / 2 + uc, 0), (w / 2, h / 2), (0, h / 2 + 4), (-w / 2, h / 2)])

    def kartus(self, cv, t):
        for x, bas, son in sahne_bitisleri(self.s):
            metin = x.get("kartus")
            if not metin or not (bas <= t < son + 0.01):
                continue
            p = prog(t, bas + 0.35, 0.45)
            q = 1 - prog(t, son - 0.25, 0.25) if x is not self.s["sahneler"][-1] else 1
            if p <= 0 or q <= 0:
                continue
            cx, cy = self.L.kartus
            boy = 66 if self.L.dik else 58
            f = self.font("metin", boy)
            tw = f.measureText(metin)
            cv.save()
            cv.translate(cx, cy)
            k = out_back(p, 1.6)
            cv.scale(lerp(0.6, 1, k), lerp(0.6, 1, k))
            a = clamp(p * 2) * q
            sekil = self.lobe(tw + 60, boy * 1.45)
            dolgu(cv, sekil, BEYAZ, a, 0)
            cv.drawPath(sekil, boya(ALTIN, a, 8))
            cv.drawPath(sekil, boya(KONTUR, a, 2))
            cv.drawString(metin, -tw / 2, boy * 0.33, f, boya(KIRMIZI_KOYU, a))
            for sx in (-1, 1):
                cv.drawCircle(sx * (tw / 2 + 50), 0, 6, boya(LAJ, a))
            cv.restore()

    # ----- kapanış: şemse (madalyon), marka, çağrı şeridi -----
    def kapanis(self, cv, t):
        kap = next(((b, e) for x, b, e in sahne_bitisleri(self.s) if x["tur"] == "kapanis"), None)
        if not kap or t < kap[0]:
            return
        bas = kap[0]
        p = prog(t, bas + 0.05, 0.6)
        cx, cy, R = self.L.semse
        cv.save()
        cv.translate(cx, cy)
        k = out_back(p, 1.5)
        cv.scale(lerp(0.55, 1, k), lerp(0.55, 1, k))
        cv.rotate(lerp(-8, 0, out_cubic(p)))
        a = clamp(p * 2.5)
        for sy in (-1, 1):  # salbekler (uç süsleri)
            cv.drawLine(0, sy * R * 0.95, 0, sy * (R + 46), boya(KONTUR, a, 3))
            uc = self.lobe(30, 46, 22)
            uc.offset(0, sy * (R + 52))
            dolgu(cv, uc, ALTIN, a, 2)
            dolgu(cv, yildiz4(0, sy * (R + 52), 12), LAJ, a, 0)

        def lobeli(r, n=16, d=0.045):
            return yol([(r * (1 + d * math.cos(n * th)) * math.sin(th), -r * (1 + d * math.cos(n * th)) * math.cos(th))
                        for th in (2 * math.pi * i / 320 for i in range(320))])
        dolgu(cv, lobeli(R), ALTIN, a, 2.6)
        dolgu(cv, lobeli(R * 0.86, 16, 0.03), LAJ, a, 2)
        for i in range(16):
            th = 2 * math.pi * i / 16
            px, py = 0.79 * R * math.sin(th), -0.79 * R * math.cos(th)
            ux, uy = math.sin(th), -math.cos(th)
            cv.drawPath(badem(px - ux * 16, py - uy * 16, px + ux * 16, py + uy * 16, 7), boya(ALTIN, a))
            th2 = th + math.pi / 16
            cv.drawCircle(0.79 * R * math.sin(th2), -0.79 * R * math.cos(th2), 3.5, boya(ALTIN_ACIK, a))
        dolgu(cv, lobeli(R * 0.71, 12, 0.025), BEYAZ, a, 2)
        cv.drawPath(lobeli(R * 0.66, 12, 0.025), boya(ALTIN, a, 2))
        # içerik: marka.logo verilirse (yuvarlak, saydam PNG) göbeği doldurur; yoksa lale, ad ve alt satır
        logo = self.marka.get("logo")
        if logo:
            import skia
            if not hasattr(self, "_logo"):
                self._logo = skia.Image.open(str(Path(self.s["_klasor"]) / logo))
            r = R * 0.645
            h = r * self._logo.height() / self._logo.width()
            cv.drawImageRect(self._logo, skia.Rect(-r, -h, r, h), skia.SamplingOptions(skia.CubicResampler.Mitchell()),
                             boya(BEYAZ, a))
        else:
            self._semse_icerik(cv, R, a)
        cv.restore()
        self._piriltilar_ve_cagri(cv, t, bas, p, cx, cy, R)

    def _semse_icerik(self, cv, R, a):
        self.lale(cv, 0, -R * 0.3, R * 0.0025, a)
        ad = self.marka.get("ad", "")
        satirlar = ad.split() if len(ad) > 11 else [ad]
        boy = R * (0.27 if len(satirlar) > 1 else 0.24)
        f = self.font("marka", boy)
        while max(f.measureText(x) for x in satirlar) > R * 1.18 and boy > 20:
            boy *= 0.94
            f = self.font("marka", boy)
        y = R * 0.04 if len(satirlar) > 1 else R * 0.16
        for x in satirlar:
            w = f.measureText(x)
            cv.drawString(x, -w / 2, y + boy * 0.35, f, boya(LAJ_KOYU, a))
            y += boy * 1.05
        alt = self.marka.get("alt")
        if alt:
            boy2 = R * 0.11
            f2 = self.font("metin", boy2)
            while f2.measureText(alt) > R * 1.1 and boy2 > 16:  # uzun alt satır beyaz göbekten taşmasın
                boy2 *= 0.95
                f2 = self.font("metin", boy2)
            w = f2.measureText(alt)
            cv.drawString(alt, -w / 2, y + R * 0.07, f2, boya(ALTIN_KOYU, a))

    def _piriltilar_ve_cagri(self, cv, t, bas, p, cx, cy, R):
        # pırıltılar
        if p >= 1:
            rng = random.Random(17)
            for i in range(10):
                th = rng.uniform(0, 2 * math.pi)
                rr = R * rng.uniform(1.05, 1.22)
                sx, sy = cx + rr * math.sin(th), cy - rr * math.cos(th)
                z = math.sin(clamp((t - bas - 0.6 - i * 0.09) / 0.7) * math.pi)
                if z > 0:
                    dolgu(cv, yildiz4(sx, sy, 16 * z), ALTIN_ACIK, z, 1.2)
        # çağrı şeridi
        cagri = self.marka.get("cagri")
        if cagri:
            q = out_cubic(prog(t, bas + 0.45, 0.5))
            if q > 0:
                sx, sy = self.L.serit
                boy = 56 if self.L.dik else 46
                f = self.font("metin", boy)
                tw = f.measureText(cagri)
                cv.save()
                cv.translate(sx, sy + (1 - q) * 40)
                sekil = self.lobe(tw + 50, boy * 1.5, 30)
                dolgu(cv, sekil, KIRMIZI, q, 0)
                cv.drawPath(sekil, boya(ALTIN, q, 6))
                cv.drawPath(sekil, boya(KONTUR, q, 2))
                cv.drawString(cagri, -tw / 2, boy * 0.33, f, boya(BEYAZ, q))
                cv.restore()

    # ----- tezhipli çerçeve: cetvel çizgileri ve lacivert bantta hatayi çiçekleri -----
    def cerceve(self, cv, t):
        import skia
        L = self.L
        VW, VH, m, b = self.VW, self.VH, L.m, L.bant
        kenar = boya(KENAR)
        for r in (skia.Rect.MakeLTRB(0, 0, VW, m + b), skia.Rect.MakeLTRB(0, VH - m - b, VW, VH),
                  skia.Rect.MakeLTRB(0, 0, m + b, VH), skia.Rect.MakeLTRB(VW - m - b, 0, VW, VH)):
            cv.drawRect(r, kenar)
        p = out_cubic(prog(t, 0.0, 0.9))
        cv.saveLayerAlpha(None, int(255 * clamp(p * 1.6)))
        self.resim(cv, "cerceve", self._cerceve)
        cv.restore()
        if p < 1:  # çizgiler köşelerden uzayarak çekilir; bitince kayıtlı resim kalır
            for ic, renk, kalin in ((m, ALTIN, 7), (m + b, ALTIN, 6)):
                r = skia.Rect.MakeLTRB(ic, ic, VW - ic, VH - ic)
                pt = skia.Path()
                pt.addRect(r)
                pp = boya(renk, 1, kalin)
                pp.setPathEffect(skia.TrimPathEffect.Make(0, p))
                cv.drawPath(pt, pp)

    def _cerceve(self, cv):
        import skia
        L = self.L
        VW, VH, m, b = self.VW, self.VH, L.m, L.bant
        bant = skia.Path()
        bant.addRect(skia.Rect.MakeLTRB(m, m, VW - m, VH - m))
        bant.addRect(skia.Rect.MakeLTRB(m + b, m + b, VW - m - b, VH - m - b))
        bant.setFillType(skia.PathFillType.kEvenOdd)
        cv.drawPath(bant, boya(LAJ))
        orta = m + b / 2

        def rozet(x, y, r):
            for k in range(8):
                a_ = k * math.pi / 4
                cv.drawPath(badem(x, y, x + r * math.cos(a_), y + r * math.sin(a_), r * 0.28), boya(ALTIN))
            cv.drawCircle(x, y, r * 0.3, boya(KIRMIZI))
            cv.drawCircle(x, y, r * 0.3, boya(ALTIN_KOYU, 1, 1))

        r = b * 0.3
        ara = b * 1.15
        for kenar_ in ("ust", "alt", "sol", "sag"):
            uz = (VW if kenar_ in ("ust", "alt") else VH) - 2 * (m + b)
            n = max(1, int(uz / ara))
            for i in range(n + 1):
                u = m + b + i * uz / n
                for j, (px, py) in enumerate(((u, orta) if kenar_ == "ust" else (u, VH - orta) if kenar_ == "alt" else (orta, u) if kenar_ == "sol" else (VW - orta, u),)):
                    rozet(px, py, r)
                if i < n:
                    v = u + uz / n / 2
                    yer = (v, orta) if kenar_ == "ust" else (v, VH - orta) if kenar_ == "alt" else (orta, v) if kenar_ == "sol" else (VW - orta, v)
                    yatay = kenar_ in ("ust", "alt")
                    dx, dy = (r * 0.9, 0) if yatay else (0, r * 0.9)
                    cv.drawPath(badem(yer[0] - dx, yer[1] - dy, yer[0] + dx, yer[1] + dy, r * 0.32), boya(ALTIN_ACIK))
        for px, py in ((orta, orta), (VW - orta, orta), (orta, VH - orta), (VW - orta, VH - orta)):
            cv.drawRect(skia.Rect.MakeLTRB(px - b / 2, py - b / 2, px + b / 2, py + b / 2), boya(KIRMIZI))
            rozet(px, py, r * 1.25)
        for ic, renk, kalin in ((m, KONTUR, 1.6), (m, ALTIN, 7), (m + 5, KONTUR, 1.2), (m + b, ALTIN, 6), (m + b - 4.5, KONTUR, 1.2),
                                (m + b + 4, KONTUR, 1.4), (m + b + 7, KIRMIZI, 2.2)):
            cv.drawRect(skia.Rect.MakeLTRB(ic, ic, VW - ic, VH - ic), boya(renk, 1, kalin))


def _oval(x, y, rx, ry):
    import skia
    return skia.Rect.MakeLTRB(x - rx, y - ry, x + rx, y + ry)


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
        yol_ = klasor / f"kare-{W}x{H}-{t:05.2f}.png"
        surf.makeImageSnapshot().save(str(yol_), skia.kPNG)
        out.append(yol_)
    return out
