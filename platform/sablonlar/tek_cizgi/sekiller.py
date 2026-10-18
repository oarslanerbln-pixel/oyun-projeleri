"""Tek çizgi şablonunun geometrisi: şekil kütüphanesi, tek çizgi rakamlar, SVG yol ayrıştırıcı.

Her poz (şekil ya da sayı) soldaki ekran kenarından gelen, şekli çizip sağ kenara çıkan TEK bir
açık çizgiye çevrilir ve yay uzunluğuna göre aynı sayıda noktaya örneklenir. Böylece iki poz
arasındaki dönüşüm nokta nokta ara değerlemedir ve çizgi hiçbir anda kopmaz.
Şekiller 0–100 kutusunda SVG yol verisidir (y aşağı); senaryo kendi yolunu da verebilir (`"M ..."`).
Gerekenler: numpy (skia gerekmez; ses de aynı geometriden kalem hızını okur).
"""

from __future__ import annotations

import math
import re

import numpy as np

N_NOKTA = 1400  # bir pozun toplam nokta sayısı (kuyruklar dahil)

def _buhar(x0: float, x1: float, y: float, h: float) -> str:
    """x0'dan yükselip x1'e geri inen dar, kıvrımlı buhar/koku teli (yol parçası, kalem kalkmaz)"""
    m = (x0 + x1) / 2
    return (f" C {x0 - 6} {y - h * .25}, {m + 7} {y - h * .45}, {m} {y - h * .62} C {m - 5} {y - h * .78}, {m + 2} {y - h * .92}, {m + 5} {y - h}"
            f" C {m - 3} {y - h * .9}, {m - 9} {y - h * .74}, {m - 3} {y - h * .58} C {m + 4} {y - h * .42}, {x1 - 4} {y - h * .25}, {x1} {y}")


def _tane(y: float, yon: int) -> str:
    """başak tanesi: saptaki (50, y) noktasından yana açılan yaprak biçimli döngü"""
    x = 50 + 20 * yon
    return f" C {50 + 10 * yon} {y}, {50 + 18 * yon} {y - 8}, {x} {y - 16} C {50 + 10 * yon} {y - 16}, {50 + 2 * yon} {y - 10}, 50 {y}"


# Kütüphane: her şekil TEK alt yol (kalem kalkmaz) ve alt kenarda biter; giriş/çıkış kuyrukları
# taban çizgisinden gelir, şeklin altından geçen çıkış kuyruğu tezgâh/tepsi çizgisi olur.
SEKILLER = {
    # yandan hilal kruvasan: dilimli dış kavis, dönüşte zikzak dilim çizgileri
    "kruvasan": (
        "M 6 86 C 10 74, 16 64, 26 58 C 26 48, 32 40, 40 37 C 44 30, 56 30, 60 37 C 68 40, 74 48, 74 58"
        " C 84 64, 90 74, 94 86 C 88 80, 80 70, 74 58 C 72 64, 68 70, 64 72 C 62 60, 61 48, 60 37"
        " C 58 52, 54 66, 50 74 C 46 66, 42 52, 40 37 C 39 48, 38 62, 36 72 C 32 68, 28 62, 26 58"
        " C 20 66, 12 76, 8 86"
    ),
    # tabaklı fincan, kulp ve ağızdan yükselen iki buhar teli
    "fincan": (
        "M 6 90 C 30 98, 70 98, 94 90 C 82 86, 72 86, 64 86 C 74 80, 78 66, 78 52"
        " C 90 50, 96 58, 92 66 C 88 74, 80 74, 76 70 C 77 62, 78 56, 78 52 L 60 52"
        + _buhar(60, 52, 52, 40) + " L 46 52" + _buhar(46, 38, 52, 30) + " L 22 52"
        " C 22 66, 26 80, 36 86 C 26 86, 14 87, 6 90"
    ),
    # boş tabak (yandan): ayak tabandan yükselir, arka kenarından üç koku teli çıkar, öbür ayaktan iner
    "tabak": (
        "M 14 90 C 8 86, 4 80, 2 74 C 12 68, 22 66, 30 66" + _buhar(30, 38, 66, 34) + " L 46 66"
        + _buhar(46, 56, 66, 48) + " L 64 66" + _buhar(64, 72, 66, 34) + " C 78 66, 90 68, 98 74 C 96 80, 92 86, 86 90"
    ),
    # buğday başağı: sapta karşılıklı taneler, tepede tek tane, sonra sap boyunca geri iner
    "basak": (
        "M 50 98 L 50 80" + _tane(80, -1) + _tane(80, 1) + " L 50 62" + _tane(62, -1) + _tane(62, 1)
        + " L 50 44" + _tane(44, -1) + _tane(44, 1) + " L 50 26 C 44 20, 44 10, 50 4 C 56 10, 56 20, 50 26 L 50 98"
    ),
    # duvar saati 9'u gösterir: giriş çizgisi akrep olur, yelkovan 12'de, kadran alttan biter
    "saat": (
        "M 8 50 L 50 50 L 50 16 L 50 8 C 74 8, 92 26, 92 50 C 92 74, 74 92, 50 92 C 26 92, 8 74, 8 50"
        " C 8 26, 26 8, 50 8 C 74 8, 92 26, 92 50 C 92 74, 74 92, 50 92"
    ),
    # kâğıt alışveriş çantası; tabanı taban çizgisinin kendisi
    "canta": "M 14 96 L 20 34 L 34 34 C 34 10, 66 10, 66 34 L 80 34 L 86 96",
    # çorba kâsesi (yandan): ayaktan yükselir, ağız çizgisinden üç buhar teli çıkar, öbür ayaktan iner
    "kase": (
        "M 32 92 C 30 88, 32 85, 36 84 C 18 76, 6 62, 4 46 L 22 46" + _buhar(22, 32, 46, 30) + " L 44 46"
        + _buhar(44, 56, 46, 42) + " L 68 46" + _buhar(68, 78, 46, 30) + " L 96 46 C 94 62, 82 76, 64 84 C 68 85, 70 88, 68 92"
    ),
    # aşçı şapkası: bant solundan yükselir, üç kabarık tepe, bant sağından iner
    "sapka": (
        "M 28 96 L 28 66 C 12 64, 4 52, 8 40 C 12 28, 24 24, 32 28 C 32 14, 44 6, 54 10 C 62 4, 76 8, 78 22"
        " C 90 22, 98 34, 94 46 C 90 58, 82 64, 72 66 L 72 96"
    ),
    # kalp
    "kalp": (
        "M 50 92 C 30 76, 6 60, 6 36 C 6 20, 18 10, 30 10 C 40 10, 46 16, 50 24 C 54 16, 60 10, 70 10"
        " C 82 10, 94 20, 94 36 C 94 60, 70 76, 50 92"
    ),
}

# Tek çizgi rakamlar: 60x100 hücre, y aşağı. Rakamlar yan yana dizilip uçtan uca bağlanır.
RAKAMLAR = {
    "0": "M 30 100 C 8 100, 2 76, 2 50 C 2 24, 12 0, 30 0 C 48 0, 58 24, 58 50 C 58 76, 52 100, 30 100",
    "1": "M 34 100 L 34 0 L 12 18 L 34 0 L 34 100",
    "2": "M 6 24 C 8 8, 20 0, 32 0 C 48 0, 56 12, 56 26 C 56 46, 30 64, 6 100 L 58 100",
    "3": "M 6 12 C 14 4, 22 0, 32 0 C 48 0, 56 10, 56 24 C 56 38, 44 46, 26 48 C 46 48, 58 60, 58 74 C 58 90, 46 100, 30 100 C 18 100, 8 94, 4 86",
    "4": "M 42 100 L 42 0 L 2 68 L 60 68",
    "5": "M 54 2 L 12 2 L 8 44 C 16 38, 26 36, 34 36 C 50 36, 58 50, 58 66 C 58 86, 46 100, 28 100 C 18 100, 8 96, 2 88",
    "6": "M 50 4 C 26 14, 6 38, 6 66 C 6 88, 18 100, 32 100 C 48 100, 58 88, 58 72 C 58 56, 48 46, 34 46 C 20 46, 10 54, 6 66",
    "7": "M 2 2 L 58 2 C 42 30, 30 62, 24 100",
    "8": "M 30 48 C 12 44, 6 34, 6 24 C 6 10, 16 0, 30 0 C 44 0, 54 10, 54 24 C 54 34, 48 44, 30 48 C 10 52, 2 64, 2 76 C 2 90, 14 100, 30 100 C 46 100, 58 90, 58 76 C 58 64, 50 52, 30 48",
    "9": "M 54 34 C 54 14, 44 0, 30 0 C 14 0, 4 12, 4 30 C 4 46, 16 56, 30 56 C 42 56, 52 48, 54 34 C 56 64, 44 94, 12 100",
}
KAPALI = {"0", "8"}  # döngü rakamlar: her noktadan başlanabilir
RAKAM_ADIM = 74  # hücre aralığı (60 genişlik + boşluk)


class SekilHatasi(ValueError):
    pass


# ---------- SVG yol verisi → çoklu çizgi ----------
_TOKEN = re.compile(r"[MLHVCSQTZmlhvcsqtz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")


def _kubik(p0, p1, p2, p3, n):
    t = np.linspace(0, 1, n)[1:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def yol_ayristir(d: str) -> list[np.ndarray]:
    """M L H V C S Q T Z (mutlak/göreli) → alt yol listesi; her biri (k, 2) nokta dizisi. Yay (A) desteklenmez."""
    toks = _TOKEN.findall(d)
    if not toks or toks[0] not in "Mm":
        raise SekilHatasi("yol 'M' ile başlamalı")
    parcalar, cur, i = [], None, 0
    pos = np.zeros(2); bas = np.zeros(2); son_kontrol = None; komut = None

    def sayi():
        nonlocal i
        if i >= len(toks) or toks[i].isalpha():
            raise SekilHatasi(f"'{komut}' için sayı eksik")
        v = float(toks[i]); i += 1
        return v

    while i < len(toks):
        if toks[i].isalpha():
            komut = toks[i]; i += 1
        elif komut is None:
            raise SekilHatasi("komutsuz sayı")
        rel = komut.islower(); K = komut.upper()
        o = pos.copy() if rel else np.zeros(2)
        if K == "M":
            pos = o + [sayi(), sayi()]; bas = pos.copy()
            cur = [pos.copy()]; parcalar.append(cur)
            komut = "l" if rel else "L"; son_kontrol = None
        elif K == "Z":
            cur.append(bas.copy()); pos = bas.copy(); son_kontrol = None
        elif K in "LHV":
            if K == "L": pos = o + [sayi(), sayi()]
            elif K == "H": pos = np.array([(pos[0] if rel else 0) + sayi(), pos[1]])
            else: pos = np.array([pos[0], (pos[1] if rel else 0) + sayi()])
            cur.append(pos.copy()); son_kontrol = None
        elif K in "CS":
            if K == "C":
                c1 = o + [sayi(), sayi()]
            else:
                c1 = 2 * pos - son_kontrol if son_kontrol is not None else pos.copy()
            c2 = o + [sayi(), sayi()]; p3 = o + [sayi(), sayi()]
            cur.extend(_kubik(pos, c1, c2, p3, 24)); pos = p3; son_kontrol = c2
        elif K in "QT":
            q = (o + [sayi(), sayi()]) if K == "Q" else (2 * pos - son_kontrol if son_kontrol is not None else pos.copy())
            p3 = o + [sayi(), sayi()]
            cur.extend(_kubik(pos, pos + 2 / 3 * (q - pos), p3 + 2 / 3 * (q - p3), p3, 20)); pos = p3; son_kontrol = q
        else:
            raise SekilHatasi(f"desteklenmeyen komut {komut}")
    return [np.asarray(p, float) for p in parcalar if len(p) > 1]


def birlestir(parcalar: list[np.ndarray]) -> np.ndarray:
    """alt yolları sırayla düz bağlantılarla tek çizgiye çevirir (tek çizgi çizimin 'kalemi kaldırmadan' kuralı)"""
    return np.concatenate(parcalar, axis=0)


def sekil_noktalari(ad_ya_da_yol: str) -> np.ndarray:
    if ad_ya_da_yol in SEKILLER:
        return birlestir(yol_ayristir(SEKILLER[ad_ya_da_yol]))
    if ad_ya_da_yol.lstrip()[:1] in ("M", "m"):
        return birlestir(yol_ayristir(ad_ya_da_yol))
    raise SekilHatasi(f"bilinmeyen şekil '{ad_ya_da_yol}' ({', '.join(SEKILLER)} ya da SVG yol verisi)")


def _yonler(p: np.ndarray, kapali: bool) -> list[np.ndarray]:
    """bir rakamın çizilebileceği yönler: ileri, geri; kapalı döngüde (0, 8) her başlangıç noktası ve
    döngüyü tamamladıktan sonra üstünden geçerek (görünmez) istenen çıkış noktasına uzanma"""
    if kapali:
        q = p[:-1]; n = len(q); adim = max(1, n // 16)
        adaylar = []
        for yon in (q, q[::-1]):
            for k in range(0, n, adim):
                r = np.r_[yon[k:], yon[:k]]
                for m in range(0, n, adim):
                    adaylar.append(np.r_[r, r[:m + 1]])
        return adaylar
    # açık rakam: ileri ya da geri; gerekirse sonunda kendi üstünden geri dönerek (görünmez) uygun uca iner
    n = len(p); adim = max(1, n // 12)
    return [np.r_[yon, yon[::-1][1:m + 1]] for yon in (p, p[::-1]) for m in range(0, n - 1, adim)]


def _kesisim(seg: np.ndarray, glifler: list[np.ndarray]) -> float:
    """bağlantı çizgisi bir rakamın gövdesinden geçiyorsa ceza (uçların hemen yanı sayılmaz)"""
    a, b = seg[0], seg[-1]
    uzak = (np.hypot(*(seg - a).T) > 12) & (np.hypot(*(seg - b).T) > 12)
    seg = seg[uzak]
    if not len(seg):
        return 0.0
    for g in glifler:
        if (np.hypot(seg[:, None, 0] - g[None, :, 0], seg[:, None, 1] - g[None, :, 1]).min(1) < 3.5).any():
            return 300.0
    return 0.0


def _baglantilar(a: np.ndarray, b: np.ndarray, alt: float) -> list[np.ndarray]:
    """iki rakam arasında aday bağlantılar: düz çizgi ya da rakamların altından dolanan kavis"""
    duz = a + (b - a) * np.linspace(0, 1, 48)[:, None]
    alttan = np.r_[a[None], _kubik(a, np.array([a[0], alt + 40]), np.array([b[0], alt + 40]), b, 47)]
    return [duz, alttan]


def _uzunluk(p: np.ndarray) -> float:
    return float(np.hypot(*np.diff(p, axis=0).T).sum())


def sayi_noktalari(metin: str) -> np.ndarray:
    """rakamları yan yana dizer; her rakamın yönünü ve bağlantı biçimini, bağlantılar kısa olacak ve
    hiçbir bağlantı ya da kuyruk bir rakamın gövdesini kesmeyecek şekilde seçer"""
    for ch in metin:
        if ch not in RAKAMLAR:
            raise SekilHatasi(f"tek çizgi sayı yalnız rakam içerir: '{metin}'")
    glifler = [yeniden_ornekle(birlestir(yol_ayristir(RAKAMLAR[ch])), 160) + [k * RAKAM_ADIM, 0] for k, ch in enumerate(metin)]
    x1 = max(g[:, 0].max() for g in glifler); alt = 100.0
    giris, cikis = np.array([-150.0, alt + 12]), np.array([x1 + 150, alt + 12])
    onceki, parca = giris, []
    for k, g in enumerate(glifler):
        komsu = glifler[max(0, k - 1):k + 2]
        en_iyi = None
        for p in _yonler(g, metin[k] in KAPALI):
            ust = 0.3 * _uzunluk(p)  # üst üste çizilen geri dönüş de bedava değil
            if k == 0:
                c = _kivrim(giris, p[0], alt + 12)
                m, bag = _uzunluk(c) + _kesisim(c, komsu), p[:1]
            else:
                m, bag = min(((_uzunluk(c) + _kesisim(c, komsu), c) for c in _baglantilar(onceki, p[0], alt)), key=lambda x: x[0])
            if k + 1 < len(glifler):
                hedef = glifler[k + 1][np.hypot(*(glifler[k + 1] - p[-1]).T).argmin()]
                m += min(_uzunluk(c) + _kesisim(c, komsu) for c in _baglantilar(p[-1], hedef, alt))
            else:  # çıkış kuyruğu tabana inip sağa gider (poz_cizgisi ile aynı kavis)
                c = _kivrim(p[-1], cikis, alt + 12, ters=True)
                m += _uzunluk(c) + _kesisim(c, komsu)
            m += ust
            if en_iyi is None or m < en_iyi[0]:
                en_iyi = (m, bag, p)
        parca += [en_iyi[1], en_iyi[2]]; onceki = en_iyi[2][-1]
    return birlestir(parca)


# ---------- poz → ekran çizgisi ----------
def yeniden_ornekle(p: np.ndarray, n: int) -> np.ndarray:
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    if d[-1] <= 0:
        return np.repeat(p[:1], n, axis=0)
    u = np.linspace(0, d[-1], n)
    return np.c_[np.interp(u, d, p[:, 0]), np.interp(u, d, p[:, 1])]


def poz_cizgisi(poz: dict, W: int, H: int, n: int = N_NOKTA) -> np.ndarray:
    """poz {'tur': 'sekil'|'sayi', 'deger', 'olcek', 'y'} → ekranı soldan sağa geçen tek çizgi (n, 2) piksel"""
    ham = sayi_noktalari(poz["deger"]) if poz["tur"] == "sayi" else sekil_noktalari(poz["deger"])
    u = min(W, H)
    mn, mx = ham.min(0), ham.max(0)
    if poz["tur"] == "sayi":  # rakam yüksekliği sabit; uzun sayılar ekrana sığacak kadar küçülür
        olcek = min(poz.get("olcek", 1.0) * 0.30 * u / 100, 0.80 * W / max(1e-9, mx[0] - mn[0]))
    else:
        olcek = poz.get("olcek", 1.0) * 0.58 * u / max(mx - mn)
    merkez = np.array([W / 2, H * poz.get("y", 0.44)])
    p = (ham - (mn + mx) / 2) * olcek + merkez
    taban = p[:, 1].max() + 0.035 * u  # kuyruklar şeklin biraz altındaki taban çizgisinden gelir
    sol, sag = np.array([-0.08 * W, taban]), np.array([1.08 * W, taban])
    # giriş ve çıkış: taban çizgisinde yürüyüp şeklin ucuna yumuşakça kıvrılır
    giris = _kivrim(sol, p[0], taban); cikis = _kivrim(p[-1], sag, taban, ters=True)
    cizgi = np.concatenate([giris, p, cikis], axis=0)
    return yeniden_ornekle(cizgi, n)


def _kivrim(a, b, taban, ters=False):
    """taban çizgisinden şekle (ya da şekilden tabana) yumuşak geçiş: yatay teğetle başlayan kübik"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    dx = b[0] - a[0]
    if not ters:
        c1 = np.array([a[0] + dx * 0.55, taban]); c2 = np.array([b[0] - dx * 0.15, b[1] + (taban - b[1]) * 0.6])
    else:
        c1 = np.array([a[0] + dx * 0.15, a[1] + (taban - a[1]) * 0.6]); c2 = np.array([b[0] - dx * 0.55, taban])
    return np.concatenate([a[None], _kubik(a, c1, c2, b, 40)], axis=0)


# ---------- zaman içinde çizgi: pozlar arası dönüşüm ----------
def _yumusat(x: np.ndarray, sigma: float) -> np.ndarray:
    """nokta dizisini dizin boyunca Gauss ile yumuşatır (uçlar sabit kalır)"""
    r = int(3 * sigma); k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    pad = np.r_[np.repeat(x[:1], r, 0), x, np.repeat(x[-1:], r, 0)]
    return np.c_[np.convolve(pad[:, 0], k, "valid"), np.convolve(pad[:, 1], k, "valid")]


def _in_out(p: float) -> float:
    return 4 * p ** 3 if p < .5 else 1 - (-2 * p + 2) ** 3 / 2


class Cizgi:
    """zaman.pozlar listesinden t anındaki çizgiyi verir. Görüntü ve kalem sesi aynı sınıfı kullanır.

    Bir dönüşüm öncekinden önce başlarsa (hızlanan sayaç) çizgi o anki ara biçimden devam eder, sıçramaz.
    """

    def __init__(self, pz: list[dict], W: int, H: int, n: int = N_NOKTA):
        self.pz, self.W, self.H, self.n = pz, W, H, n
        self.hedef = [poz_cizgisi(p, W, H, n) for p in pz]
        u = min(W, H)
        k = np.arange(n) / (n - 1)
        self._dalga = np.sin(k * 2 * math.pi * 5.0)          # dönüşümde çizgiye binen yay dalgası
        self._nefes = (np.sin(k * 2 * math.pi * 2.3), np.cos(k * 2 * math.pi * 1.7))
        self._genlik = 0.022 * u
        self.baslangic = [self.hedef[0]]
        for j in range(1, len(pz)):
            self.baslangic.append(self._ara(j - 1, pz[j]["t"]))

    def _ara(self, j: int, t: float) -> np.ndarray:
        p = self.pz[j]
        if j == 0:
            return self.hedef[0]
        q = max(0.0, min(1.0, (t - p["t"]) / p["sure"]))
        e = _in_out(q)
        a, b = self.baslangic[j], self.hedef[j]
        x = a + (b - a) * e
        if 0 < q < 1:
            # ara biçim düğüm düğüm karışmasın: dönüşümün ortasında çizgi akıcı bir kavise yumuşar,
            # normal yönünde hafif bir dalga ile ip gibi kıvrılarak yeni biçimini alır
            w = math.sin(math.pi * q)
            x = x + (_yumusat(x, 28) - x) * (0.8 * w)
            d = np.gradient(x, axis=0); d /= np.hypot(*d.T)[:, None] + 1e-9
            x = x + np.c_[-d[:, 1], d[:, 0]] * (self._dalga * w * self._genlik * 0.6)[:, None]
        return x

    def an(self, t: float) -> tuple[np.ndarray, float, int, float]:
        """(noktalar, görünen oran 0..1, poz indeksi, dönüşüm ilerlemesi) — oran yalnız ilk çizimde < 1"""
        k = 0
        for j, p in enumerate(self.pz):
            if t >= p["t"]:
                k = j
        p = self.pz[k]
        q = max(0.0, min(1.0, (t - p["t"]) / p["sure"]))
        x = self._ara(k, t)
        # nefes: çizgi canlı dursun diye çok yavaş, birkaç piksellik salınım (titreme değil)
        u = min(self.W, self.H) * 0.0016
        x = x + np.c_[self._nefes[0] * math.sin(t * 1.3), self._nefes[1] * math.cos(t * 1.1)] * u
        oran = _in_out(q) if k == 0 and p.get("ilk") else 1.0
        if k == 0 and p.get("ilk") and t < p["t"]:
            oran = 0.0
        return x, oran, k, q
