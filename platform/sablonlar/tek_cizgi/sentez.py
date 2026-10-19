"""Tek çizgi şablonunun sesi: sentez müzik + kalem sesi + zaman çizelgesindeki efektler + seslendirme → miks.

Müzik dinamiği (Atilla'nın "müzikal gibi" isteği): sakin giriş (e-piyano + pad), `muzik.yukselis`
anında marimba arpeji, yumuşak kick ve bas girer; `muzik.sakin` anında yeniden yalnız piyanoya iner;
`muzik.final` anında parlak akor, çan ve hafif ritimle kapanır. Kalem sesi çizginin o anki hızından
üretilir (sessiz bir sürtünme; hız yoksa ses yok). Konuşma sırasında müzik sesin ~8 dB altında durur.
Gerekenler: numpy, soundfile (scipy varsa filtreler hızlanır).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import sfx as fx  # noqa: E402  (platform/ortak/sfx.py: beyaz gürültüsüz efektler)

import sekiller
import zaman

SR = 48000


def _lp(x: np.ndarray, cut: float) -> np.ndarray:
    a = math.exp(-2 * math.pi * cut / SR)
    try:
        from scipy.signal import lfilter
        return lfilter([1 - a], [1, -a], x)
    except ImportError:
        y = np.empty_like(x); v = 0.0
        for i in range(len(x)): v = (1 - a) * x[i] + a * v; y[i] = v
        return y


def _hp(x: np.ndarray, cut: float) -> np.ndarray:
    return x - _lp(x, cut)


def mtof(m: float) -> float:
    return 440 * 2 ** ((m - 69) / 12)


def kalem_hizi(s: dict, n: int, W: int = 540, H: int = 960, adim: float = 1 / 120) -> np.ndarray:
    """örnek başına 0..1 kalem hızı: çizginin noktalarının ortalama yer değiştirmesi (ilk çizimde uç hızı)"""
    c = sekiller.Cizgi(zaman.pozlar(s), W, H, n=500)
    tt = np.arange(0, s["sure"] + adim, adim)
    hiz = np.zeros(len(tt)); onceki = None
    for i, t in enumerate(tt):
        x, oran, _, _ = c.an(t)
        uc = x[min(len(x) - 1, int(oran * (len(x) - 1)))]
        if onceki is not None:
            px, po, puc = onceki
            if oran < 1.0 or po < 1.0:
                hiz[i] = np.hypot(*(uc - puc)) / adim / (min(W, H) * 1.5)
            else:
                hiz[i] = float(np.hypot(*(x - px).T).mean()) / adim / (min(W, H) * 0.8)
        onceki = (x, oran, uc)
    hiz = np.clip(hiz, 0, 1.2)
    return np.interp(np.arange(n) / SR, tt, hiz)


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None, muzik_alti_db: float = 8.0) -> dict:
    import soundfile as sf
    sure = s["sure"]
    n = int(SR * sure)
    rng = np.random.default_rng(11)
    muzik = np.zeros((n, 2)); sfx = np.zeros((n, 2))
    m = s["muzik"]
    vurus = 60 / m["bpm"]; olcu = 4 * vurus
    yuk, sak, fin = m["yukselis"], m["sakin"], m["final"]
    son_an = sure - 0.7

    def ekle(buf, t0, x, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= n or i < 0: return
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * gain * l * 1.414
        buf[i:i + len(x), 1] += x * gain * r * 1.414

    def env(d, a=0.004, dec=None):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / a, 1.0)
        return e * (np.exp(-tt / dec) if dec else 1.0), tt

    # --- çalgılar ---
    def epiano(nota, d=1.6):
        e, tt = env(d, a=0.006, dec=0.55)
        f = mtof(nota); ph = 2 * np.pi * f * tt
        ton = np.sin(ph + 0.6 * np.sin(ph) * np.exp(-tt / 0.25)) + 0.18 * np.sin(2 * ph) * np.exp(-tt / 0.3)
        return ton * e * np.minimum(1, (d - tt) / 0.08)

    def marimba(nota, d=0.45):
        e, tt = env(d, a=0.002, dec=0.11)
        ph = 2 * np.pi * mtof(nota) * tt
        return (np.sin(ph) + 0.25 * np.sin(4 * ph) * np.exp(-tt / 0.03)) * e

    def pad(notalar, d):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / 0.6, 1) * np.minimum((d - tt) / 0.5, 1)
        x = sum(np.sin(2 * np.pi * mtof(k) * (1 + det) * tt) for k in notalar for det in (-0.003, 0.003))
        return _lp(x, 1800) * e / (len(notalar) * 2)

    def kick():
        e, tt = env(0.35, a=0.002, dec=0.12)
        return np.sin(2 * np.pi * np.cumsum(46 + 70 * np.exp(-tt / 0.03)) / SR) * e

    def shaker():
        return fx.shaker(rng, 0.07) * 0.22

    def bas(nota, d):
        e, tt = env(d, a=0.01, dec=0.5)
        ph = 2 * np.pi * mtof(nota) * tt
        return (np.sin(ph) + 0.2 * np.sin(2 * ph)) * e * np.minimum(1, (d - tt) / 0.05)

    def can(nota, d=1.4):
        e, tt = env(d, a=0.001, dec=0.4)
        f = mtof(nota)
        return (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt / 0.15)) * e

    akorlar = m["akorlar"]
    def akor(tb): return akorlar[int(tb / olcu) % len(akorlar)]
    def enerjik(tb): return yuk <= tb < sak or fin <= tb < son_an

    # piyano: her ölçünün 1. ve 2.5. vuruşu; pad sürekli
    k = 0
    while k * olcu < son_an:
        tb = k * olcu; a = akor(tb)
        for off, g in ((0, 0.22), (1.5 * vurus, 0.14), (3 * vurus, 0.1)):
            if tb + off < son_an:
                for j, nota in enumerate(a):
                    ekle(muzik, tb + off + j * 0.012, epiano(nota + 12), g, pan=(j - 1.5) * 0.25)
        ekle(muzik, tb, pad(a, min(olcu + 0.3, son_an - tb + 0.3)), 0.2)
        k += 1
    # enerji bölümleri: marimba arpeji, kick, shaker, bas
    adim = vurus / 2; arp = [0, 2, 1, 3, 2, 1, 3, 2]
    for i in range(int(son_an / adim) + 1):
        tb = i * adim
        if not enerjik(tb) or tb >= son_an:
            continue
        a = akor(tb)
        ekle(muzik, tb, marimba(a[arp[i % 8] % len(a)] + 24), 0.13, pan=0.35 if i % 2 else -0.35)
        if i % 2 == 0:
            ekle(muzik, tb, kick(), 0.5)
            ekle(muzik, tb, bas(min(a) - 12, vurus * 0.9), 0.22)
        ekle(muzik, tb + adim / 2, shaker(), 0.25 if i % 4 == 1 else 0.16, pan=0.2)
    # final: parlak akor (add9) + çan arpeji
    kok = akorlar[0]
    final = [min(kok) - 12] + list(kok) + [kok[0] + 14, kok[2] + 12]
    for j, nota in enumerate(final):
        ekle(muzik, son_an + j * 0.02, epiano(nota + 12, 0.75), 0.18)
    ekle(muzik, son_an, pad(final, 0.75), 0.3)
    for j, nota in enumerate([84, 88, 91, 96]):
        ekle(muzik, fin + 0.35 + j * 0.09, can(nota), 0.06, pan=(j - 1.5) * 0.3)

    # --- kalem sesi: çizginin hızıyla açılan, kâğıtta keçe uç sürtünmesi (kısık) ---
    hiz = kalem_hizi(s, n)
    hiz = np.convolve(hiz, np.ones(int(0.03 * SR)) / int(0.03 * SR), "same")
    # sabit bant gürültüsü yerine sık, kısa taneler: keçe uç kâğıtta tek düze cızırdamaz
    surt = fx.hisirti(rng, n / SR, yogunluk=260, parlak=0.8)[:n] * 0.32
    kalem = surt * np.sqrt(np.clip(hiz, 0, 1)) * 0.10
    sfx[:, 0] += kalem; sfx[:, 1] += kalem * 0.9

    # --- efektler ---
    def tik():
        e, tt = env(0.06, a=0.0005, dec=0.012)
        return (np.sin(2 * np.pi * 1900 * tt) + 0.5 * np.sin(2 * np.pi * 2950 * tt)) * e

    def vurus_():  # yumuşak, tok iniş: alçak "tum" + keçe vuruşu
        e, tt = env(0.7, a=0.002, dec=0.2)
        alt = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-tt / 0.04)) / SR) * e
        return alt + _lp(fx.renkli(len(tt), rng), 1200) * np.exp(-tt / 0.02) * 0.2

    def kayma(d):
        tt = np.arange(int(d * SR)) / SR; p = tt / d
        return _lp(fx.renkli(len(tt), rng), 2400) * np.sin(np.pi * p) ** 2 * 0.35

    def pop():
        e, tt = env(0.12, a=0.001, dec=0.03)
        return np.sin(2 * np.pi * np.cumsum(700 * np.exp(-tt / 0.02) + 300) / SR) * e

    def parilti():
        out = np.zeros(int(0.9 * SR))
        for j, nota in enumerate([88, 91, 95, 100]):
            x = can(nota, 0.6); i = int(j * 0.05 * SR); out[i:i + len(x)] += x[: len(out) - i]
        return out

    uret = {"tik": lambda e: tik(), "vurus": lambda e: vurus_(), "kayma": lambda e: kayma(e.get("sure", 0.6)),
            "pop": lambda e: pop(), "parilti": lambda e: parilti(), "cinlama": lambda e: parilti()}
    for an, ad, kaz, pan, ek in zaman.ses_olaylari(s):
        ekle(sfx, an, uret[ad](ek), kaz, pan)

    # --- seslendirme (platform/ses çıktısı: 48 kHz, seviyelenmiş) ---
    vo = np.zeros(n); bulunan = []
    for satir in s["seslendirme"].get("satirlar", []):
        yol = (seslendirme or Path()) / f"{satir['id']}.wav"
        if not seslendirme or not yol.exists():
            continue
        x, sr = sf.read(str(yol))
        if x.ndim > 1: x = x.mean(1)
        if sr != SR:
            x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
        i = int(satir["t"] * SR); vo[i:i + len(x)] += x[: max(0, n - i)]
        bulunan.append(satir["id"])
    rms = lambda a: math.sqrt(float(np.mean(a ** 2)) + 1e-12)
    maske = np.convolve((np.abs(vo) > 1e-4).astype(float), np.ones(int(0.15 * SR)) / int(0.15 * SR), "same") > 0.05
    ref = rms(vo[maske]) if maske.any() else 0.1
    muzik *= ref * 10 ** (-muzik_alti_db / 20) / rms(muzik)  # müzik konuşmanın ~8 dB altında
    k = int(0.12 * SR)
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske.astype(float), np.ones(k) / k, "same"), 0, 1)
    muzik *= duk[:, None]  # konuşurken 3 dB ek kısma
    sfx *= ref * 10 ** (-8 / 20) / max(rms(sfx[np.abs(sfx).sum(1) > 1e-6]), 1e-9)
    miks = vo[:, None] + muzik + sfx
    f = int(0.02 * SR); miks[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.3 * SR); miks[-f:] *= np.linspace(1, 0, f)[:, None]
    cikti.mkdir(parents=True, exist_ok=True)
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
