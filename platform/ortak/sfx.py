"""Ortak efekt ve vurmalı sesler: beyaz gürültü yerine biçimlendirilmiş, değişken sesler.

Neden: şablonlar hi-hat, whoosh, kâğıt hışırtısı, parıltı gibi sesleri ham beyaz gürültüden
(çoğu zaman bir de türevini alarak) üretiyordu. Beyaz gürültünün enerjisi 24 kHz'e kadar düz
yayılır; türev alınınca tizler daha da öne çıkar. Sonuç her vuruşta aynı, tekdüze bir cızırtı
(Atilla, 2026-10-19: "hışırtı veya ona benzer şeyler duyuluyor, tek düze"). Buradaki sesler:

- pembe/kahverengi gürültüden çıkar (tizde yumuşar), bantla sınırlanır;
- hi-hat metalik osilatörlerle yapılır (808 yöntemi), gürültü yalnız hava katmanıdır;
- whoosh ve yükselen ses, zamanla kayan rezonanslı süzgeçten geçer (hava akımı gibi duyulur);
- kâğıt hışırtısı tek düze bant gürültüsü değil, rastgele kısa tanelerden oluşur;
- parıltı gürültü değil, tiz sinüs çınlamalarıdır;
- her çağrı küçük bir rastgele farkla çalar (seviye, ton, süre): aynı vuruş iki kez aynı duyulmaz.

Yalnız numpy gerekir. Hepsi mono `float64` dizi döndürür, tepe değeri ~1 (kazanç çağıranın işi).
`gurultu_analizi` kalite kapısının "hışırtı" ölçüsüdür (bkz. kalite.py).

    sys.path.insert(0, str(BURADA.parents[1] / "ortak"))
    import sfx
    rng = np.random.default_rng(7)
    x = sfx.hat(rng)                 # kapalı hi-hat
    w = sfx.whoosh(rng, 0.4)          # yükselen whoosh
"""

from __future__ import annotations

import numpy as np

SR = 48000


# ---------------------------------------------------------------- temel yapı taşları

def _rng(rng) -> np.random.Generator:
    return rng if isinstance(rng, np.random.Generator) else np.random.default_rng(rng)


def _normal(x: np.ndarray, tepe: float = 1.0) -> np.ndarray:
    m = float(np.abs(x).max()) if len(x) else 0.0
    return x * (tepe / m) if m > 1e-12 else x


def renkli(n: int, rng=0, egim: float = -3.0) -> np.ndarray:
    """Renkli gürültü: `egim` dB/oktav güç eğimi (0 beyaz, -3 pembe, -6 kahverengi); RMS 1."""
    rng = _rng(rng)
    if n <= 0:
        return np.zeros(0)
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1] if len(f) > 1 else 1.0
    X *= (f / 1000.0) ** (egim / 6.02)
    x = np.fft.irfft(X, n)
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-12)


def bant(x: np.ndarray, alt: float | None = None, ust: float | None = None, derece: int = 2) -> np.ndarray:
    """Sıfır fazlı bant süzgeci (FFT); `derece` Butterworth benzeri dikliktir (2 → 12 dB/oktav)."""
    n = len(x)
    if n == 0:
        return x
    f = np.fft.rfftfreq(n, 1 / SR)
    g = np.ones_like(f)
    if alt:
        g *= 1 / np.sqrt(1 + (alt / np.maximum(f, 1e-3)) ** (2 * derece))
    if ust:
        g *= 1 / np.sqrt(1 + (f / ust) ** (2 * derece))
    return np.fft.irfft(np.fft.rfft(x) * g, n)


def kayan_suzgec(x: np.ndarray, merkez, q: float = 1.4, pencere: int = 1024) -> np.ndarray:
    """Zamanla kayan rezonanslı bant geçiren (STFT ile, vektörel).

    `merkez`: sabit Hz ya da her örnek için Hz dizisi. `q` yüksekse ses daha "ıslıklı" ve tonal olur.
    """
    n = len(x)
    if n == 0:
        return x
    merkez = np.broadcast_to(np.asarray(merkez, dtype=float), (n,))
    hop = pencere // 4
    w = np.hanning(pencere + 1)[:-1]
    pad = pencere
    xp = np.concatenate([np.zeros(pad), x, np.zeros(pad + hop)])
    k = (len(xp) - pencere) // hop + 1
    idx = np.arange(pencere)[None, :] + hop * np.arange(k)[:, None]
    X = np.fft.rfft(xp[idx] * w, axis=1)
    f = np.fft.rfftfreq(pencere, 1 / SR)
    f[0] = 1.0
    orta = np.clip(np.arange(k) * hop + pencere // 2 - pad, 0, n - 1)
    fc = np.maximum(merkez[orta], 20.0)[:, None]
    G = 1 / np.sqrt(1 + (q * (f[None, :] / fc - fc / f[None, :])) ** 2)
    y_k = np.fft.irfft(X * G, pencere, axis=1) * w
    y = np.zeros(len(xp))
    np.add.at(y, idx.ravel(), y_k.ravel())
    y /= 1.5  # hann² toplamı (hop = pencere/4)
    return y[pad: pad + n]


def zarf(n: int, atak: float = 0.002, sonum: float = 0.1, egri: float = 1.0) -> np.ndarray:
    """Hızlı atak + üstel sönüm zarfı; `sonum` ~1/e süresi (sn)."""
    t = np.arange(n) / SR
    return np.minimum(t / max(atak, 1e-5), 1.0) * np.exp(-(t / max(sonum, 1e-5)) ** egri)


def _oynat(deger: float, rng: np.random.Generator, oran: float) -> float:
    """Küçük rastgele sapma: insan eli gibi aynı vuruşu iki kez aynı çalmaz."""
    return deger * (1 + rng.uniform(-oran, oran))


# ---------------------------------------------------------------- vurmalılar

_HAT_OSILATOR = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)  # TR-808 hi-hat oranları


def hat(rng=0, sure: float = 0.06, acik: bool = False, parlak: float = 1.0) -> np.ndarray:
    """Hi-hat: altı kare dalga osilatörü (metalik), 6–12 kHz bandı + az hava gürültüsü."""
    rng = _rng(rng)
    d = _oynat(0.32 if acik else sure, rng, 0.12)
    n = int(d * SR)
    t = np.arange(n) / SR
    ton = _oynat(1.0, rng, 0.02)
    x = sum(np.sign(np.sin(2 * np.pi * f * ton * t + rng.uniform(0, 6.28))) for f in _HAT_OSILATOR) / 6
    x = 0.8 * x + 0.2 * renkli(n, rng, -3.0) * 0.5
    x = bant(x, 6500 * parlak ** 0.5, 12500, 2)
    e = zarf(n, 0.0008, d / (2.2 if acik else 3.2), 1.0)
    return _normal(x * e) * _oynat(1.0, rng, 0.18)


def zil(rng=0, sure: float = 1.6) -> np.ndarray:
    """Zil / crash: metalik osilatörler halkalı çarpımla, 3.5–12 kHz; uzun ama yumuşayan kuyruk."""
    rng = _rng(rng)
    n = int(_oynat(sure, rng, 0.08) * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in _HAT_OSILATOR:
        x += np.sign(np.sin(2 * np.pi * f * 1.47 * t + rng.uniform(0, 6.28)))
    x = x / 6 * np.sign(np.sin(2 * np.pi * 1130 * t))
    x = 0.65 * x + 0.35 * renkli(n, rng, -3.0) * 0.5
    x = bant(x, 3500, 12000, 2)
    e = zarf(n, 0.001, sure / 3.0, 0.8)
    x = x * e
    # kuyrukta tizler daha hızlı söner (gerçek zil gibi): son yarı yumuşar
    x = x * (1 - 0.5 * t / max(t[-1], 1e-6)) + bant(x, None, 5000, 1) * 0.5 * t / max(t[-1], 1e-6)
    return _normal(x)


def shaker(rng=0, sure: float = 0.09) -> np.ndarray:
    """Shaker / maraka: pembe gürültüden yumuşak ataklı, 4–9 kHz bantlı kısa tane."""
    rng = _rng(rng)
    n = int(_oynat(sure, rng, 0.15) * SR)
    t = np.arange(n) / SR
    e = np.sin(np.pi * np.minimum(t / (n / SR), 1)) ** 1.5 * np.exp(-t / 0.05)
    return _normal(bant(renkli(n, rng, -3.0), 3500, 9000, 2) * e) * _oynat(1.0, rng, 0.2)


def clap(rng=0, sure: float = 0.28) -> np.ndarray:
    """El çırpma: 0.8–3.5 kHz bantlı üç hızlı vuruş + kısa oda kuyruğu."""
    rng = _rng(rng)
    n = int(sure * SR)
    g = bant(renkli(n, rng, -1.5), 800, 3500, 2)
    e = np.zeros(n)
    for k in (0.0, 0.009, 0.019):
        i = int(_oynat(k, rng, 0.2) * SR)
        e[i:] += zarf(n - i, 0.0005, 0.006) * (0.7 if k else 1.0)
    i = int(0.026 * SR)
    e[i:] += 0.35 * zarf(n - i, 0.002, 0.07)
    return _normal(g * e) * _oynat(1.0, rng, 0.12)


def tik(rng=0, frekans: float = 3200, sure: float = 0.012) -> np.ndarray:
    """Kısa tık / çıt (kick atağı, kalem ucu): bantlı tek darbe, tıslama bırakmaz."""
    rng = _rng(rng)
    n = int(sure * SR)
    return _normal(bant(renkli(n, rng, -3.0), frekans * 0.5, frekans * 2.0, 2) * zarf(n, 0.0003, sure / 4))


def kick(rng=0, sure: float = 0.42, kok: float = 48.0, tik_kazanc: float = 0.18) -> np.ndarray:
    """Kick: frekansı düşen sinüs + bantlı küçük atak tıkı (beyaz gürültü yok)."""
    rng = _rng(rng)
    n = int(sure * SR)
    t = np.arange(n) / SR
    f = kok + 110 * np.exp(-t / 0.035)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * zarf(n, 0.002, sure / 2.6)
    tk = tik(rng, 2600, 0.01)
    x[: len(tk)] += tk * tik_kazanc
    return _normal(x)


def boom(rng=0, sure: float = 0.9) -> np.ndarray:
    """Düşüş vuruşu: alt bas + kahverengi gürültüden boğuk gövde."""
    rng = _rng(rng)
    n = int(sure * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t / 0.25) + 32) / SR) * zarf(n, 0.002, 0.28)
    govde = bant(renkli(n, rng, -6.0), 40, 700, 2) * zarf(n, 0.001, 0.06)
    return _normal(sub + 0.5 * _normal(govde))


# ---------------------------------------------------------------- geçiş efektleri

def whoosh(rng=0, sure: float = 0.35, yukari: bool = True, alt: float = 250, ust: float = 3200,
           q: float = 1.6) -> np.ndarray:
    """Hava akımı geçişi: pembe gürültü, kayan rezonanslı süzgeç, asimetrik kabarma.

    `yukari=True`: ton yükselir, sese doğru gelir (zirve %65'te); False: uzaklaşır (zirve %35'te).
    """
    rng = _rng(rng)
    sure = _oynat(sure, rng, 0.08)
    n = int(sure * SR)
    p = np.arange(n) / max(n - 1, 1)
    yol = p if yukari else 1 - p
    fc = alt * (ust / alt) ** (yol ** 1.3)
    zirve = 0.65 if yukari else 0.35
    e = np.where(p < zirve, np.sin(0.5 * np.pi * p / zirve), np.cos(0.5 * np.pi * (p - zirve) / (1 - zirve))) ** 2
    x = kayan_suzgec(renkli(n, rng, -3.0), fc, q)
    return _normal(x * e)


def riser(rng=0, sure: float = 1.5) -> np.ndarray:
    """Yükselen gerilim: oktav kayan testere + üstte açılan süzgeçli hava (beyaz gürültü yok)."""
    rng = _rng(rng)
    n = int(sure * SR)
    p = np.arange(n) / max(n - 1, 1)
    faz = np.cumsum(200 * 2 ** (3 * p)) / SR
    testere = sum(np.sin(2 * np.pi * k * faz) / k for k in range(1, 9)) * 0.6
    hava = kayan_suzgec(renkli(n, rng, -3.0), 400 * 10 ** (1.0 * p), 1.2)
    return _normal((testere * 0.5 + _normal(hava) * 0.5) * p ** 2)


def hisirti(rng=0, sure: float = 1.0, yogunluk: float = 70.0, parlak: float = 1.0) -> np.ndarray:
    """Kâğıt / kumaş hışırtısı: rastgele kısa taneler (tek düze bant gürültüsü değil).

    `yogunluk` saniyedeki tane sayısı; ortası kabarık bir zarfla çoğalır, uçlarda seyrelir.
    Altında çok kısık (−26 dB), tizi kesilmiş bir zemin vardır, taneler arasında boşluk duyulmaz.
    """
    rng = _rng(rng)
    n = int(sure * SR)
    if n <= 0:
        return np.zeros(0)
    out = np.zeros(n)
    kaynak = renkli(n + SR // 10, rng, -3.0)
    bantlar = [bant(kaynak, lo * parlak, hi * parlak, 2) for lo, hi in ((900, 2600), (1600, 4200), (2500, 6500))]
    p = np.arange(n) / n
    kabarma = np.sin(np.pi * p) ** 0.7
    adet = rng.poisson(max(1.0, yogunluk * sure))
    for _ in range(adet):
        an = rng.random()
        if rng.random() > kabarma[int(an * (n - 1))]:
            continue
        uz = int(rng.uniform(0.004, 0.028) * SR)
        i = int(an * n)
        j = min(n, i + uz)
        if j - i < 16:
            continue
        b = bantlar[rng.integers(len(bantlar))]
        k = rng.integers(0, len(b) - (j - i))
        tane = b[k: k + (j - i)] * np.hanning(j - i) ** 0.5
        out[i:j] += tane * rng.lognormal(0, 0.5)
    zemin = bant(kaynak[:n], 300, 2500 * parlak, 2) * kabarma * 0.05
    return _normal(out + zemin)


def parilti(rng=0, sure: float = 1.5, alt: float = 2500, ust: float = 7000, yogunluk: float = 18.0) -> np.ndarray:
    """Işıltı / cam parıltısı: tiz sinüs çınlamaları (gürültü değil), ortası yoğun.

    Eskiden 3–9 kHz bant gürültüsüydü; bu, ışık süpürmesi boyunca düz bir "şşş" olarak duyuluyordu.
    """
    rng = _rng(rng)
    n = int(sure * SR)
    out = np.zeros(n)
    p = np.arange(n) / max(n, 1)
    kabarma = np.sin(np.pi * p) ** 2
    adet = rng.poisson(max(2.0, yogunluk * sure))
    for _ in range(adet):
        an = rng.random()
        if rng.random() > kabarma[int(an * (n - 1))] + 0.08:
            continue
        f = alt * (ust / alt) ** rng.random()
        d = rng.uniform(0.08, 0.35)
        m = int(d * SR)
        i = int(an * n)
        j = min(n, i + m)
        if j <= i:
            continue
        t = np.arange(j - i) / SR
        ton = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.03))
        out[i:j] += ton * zarf(j - i, 0.001, d / 3.5) * rng.lognormal(0, 0.35)
    hava = bant(renkli(n, rng, -3.0), alt, ust, 2) * kabarma * 0.04
    return _normal(out + hava)


def citirti(rng=0, sure: float = 1.0, yogunluk: float = 6.0) -> np.ndarray:
    """Plak / ateş çıtırtısı: seyrek kısa çıtlar; aralarında tıslayan zemin yok."""
    rng = _rng(rng)
    n = int(sure * SR)
    out = np.zeros(n)
    for _ in range(rng.poisson(max(1.0, yogunluk * sure))):
        tk = tik(rng, rng.uniform(1500, 5000), rng.uniform(0.002, 0.008)) * rng.lognormal(0, 0.6)
        i = rng.integers(0, max(1, n - len(tk)))
        out[i: i + len(tk)] += tk[: n - i]
    return _normal(out)


# ---------------------------------------------------------------- ölçüm (kalite kapısı)

def gurultu_analizi(x: np.ndarray, sr: int = SR, alt: float = 2500, ust: float = 8000,
                    duzluk_esik: float = 0.5, pay_esik: float = -15.0) -> dict:
    """Tekdüze cızırtı ölçüsü: tiz bantta gürültü gibi (düz spektrumlu) ve baskın kalan anlar.

    ~0.1 sn'lik pencerelerde 2.5–8 kHz bandının spektral düzlüğüne (gürültü ≈ 0.6–0.9, tonal ses
    < 0.3) ve toplam enerjideki payına bakılır. Düzlük > `duzluk_esik` ve pay > `pay_esik` dB ise
    an "cızırtılı" sayılır. Konuşmadaki s/ş sesleri de cızırtılıdır ama 0.2 sn'yi geçmez; bu yüzden
    asıl ölçü en uzun kesintisiz cızırtı süresidir.

    Döndürür: `en_uzun_sn`, `en_uzun_an` (başlangıç sn), `oran` (cızırtılı anların payı).
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    pencere, hop, ort = 2048, 1024, 5
    if len(x) < pencere * 2:
        return {"en_uzun_sn": 0.0, "en_uzun_an": 0.0, "oran": 0.0}
    w = np.hanning(pencere)
    k = (len(x) - pencere) // hop
    idx = np.arange(pencere)[None, :] + hop * np.arange(k)[:, None]
    P = np.abs(np.fft.rfft(x[idx] * w, axis=1)) ** 2 + 1e-18
    c = np.cumsum(np.vstack([np.zeros(P.shape[1]), P]), axis=0)
    P = np.maximum((c[ort:] - c[:-ort]) / ort, 1e-18)  # ~0.1 sn ortalama: gürültünün düzlüğü kararlı ölçülür
    f = np.fft.rfftfreq(pencere, 1 / sr)
    hb = (f >= alt) & (f < ust)
    toplam = P.sum(axis=1)
    hf = P[:, hb]
    duzluk = np.exp(np.log(hf).mean(axis=1)) / hf.mean(axis=1)
    pay = 10 * np.log10(hf.sum(axis=1) / toplam)
    seviye = 10 * np.log10(toplam)
    canli = seviye > seviye.max() - 40
    c_an = (duzluk > duzluk_esik) & (pay > pay_esik) & canli
    dt = hop / sr
    en, bas, i0 = 0, 0, None
    for i, v in enumerate(c_an):
        if v and i0 is None:
            i0 = i
        if (not v or i == len(c_an) - 1) and i0 is not None:
            son = i + (1 if v else 0)
            if son - i0 > en:
                en, bas = son - i0, i0
            i0 = None
    return {"en_uzun_sn": round(en * dt, 2), "en_uzun_an": round(bas * dt, 2),
            "oran": round(float(c_an.sum() / max(1, canli.sum())), 3)}
