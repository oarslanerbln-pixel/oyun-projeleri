"""Origami şablonunun sesi: sentez müzik + kâğıt efektleri + seslendirme → miks.

Müzik: `muzik.bpm` hızında marimba arpeji, yumuşak pad ve shaker ile sakin başlar; `muzik.dusus`
anında yumuşak kick, parmak şıklatma ve yuvarlak bas girer (zirve). Sahne geçişinden hemen önce
davul ve bas susar, kapanış parlak bir akorla açılır. Efektler (katlanma, hışırtı, fiske, kayma)
`zaman.ses_olaylari` listesinden üretilir. Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import sfx as fx  # noqa: E402  (platform/ortak/sfx.py: beyaz gürültüsüz efektler)

import zaman

SR = 48000


def _tek_kutup(x: np.ndarray, cut) -> np.ndarray:
    """tek kutuplu alçak geçiren; cut sabit ya da örnek başına dizi"""
    cut = np.broadcast_to(np.asarray(cut, dtype=float), x.shape)
    a = np.exp(-2 * np.pi * cut / SR)
    if np.all(a == a.flat[0]):
        try:
            from scipy.signal import lfilter
            return lfilter([1 - a.flat[0]], [1, -a.flat[0]], x)
        except ImportError:
            pass
    y = np.empty_like(x); v = 0.0
    for i in range(len(x)): v = (1 - a[i]) * x[i] + a[i] * v; y[i] = v
    return y


def gecis_bosluklari(s: dict) -> list[tuple[float, float]]:
    """katla geçişinden önce kick ve bas susar; yeni sahne daha dolu girer"""
    return [(sh["bas"] - zaman.KATLA_SN, sh["bas"]) for sh in s["sahneler"][1:] if sh["gecis"] == "katla"]


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None) -> dict:
    import soundfile as sf
    sure = s["sure"]
    n = int(SR * sure)
    t_all = np.arange(n) / SR
    muzik = np.zeros((n, 2)); sfx = np.zeros((n, 2)); rng = np.random.default_rng(3)
    vurus = 60 / s["muzik"]["bpm"]
    dusus = s["muzik"]["dusus"]
    son_an = sure - 0.6  # son akor

    def ekle(buf, t0, x, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= n: return
        if i < 0: x, i = x[-i:], 0
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * gain * l * 1.414
        buf[i:i + len(x), 1] += x * gain * r * 1.414

    def env(d, a=0.003, dec=None):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / a, 1.0)
        return e * (np.exp(-tt / dec) if dec else 1.0), tt

    def mtof(m): return 440 * 2 ** ((m - 69) / 12)

    def bant(x, lo, hi): return _tek_kutup(x, hi) - _tek_kutup(x, lo)

    # --- tonal ---
    def marimba(m, d=0.6, parlak=1.0):
        e, tt = env(d, a=0.0015, dec=0.22)
        f = mtof(m)
        x = np.sin(2 * np.pi * f * tt) + 0.35 * parlak * np.sin(2 * np.pi * f * 3.93 * tt) * np.exp(-tt / 0.05)
        x += 0.12 * parlak * np.sin(2 * np.pi * f * 9.2 * tt) * np.exp(-tt / 0.015)
        return x * e

    def pad(ms, d):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / 0.4, 1) * np.minimum((d - tt) / 0.4, 1)
        x = sum(np.sin(2 * np.pi * mtof(m) * (1 + det) * tt) + 0.2 * np.sin(4 * np.pi * mtof(m) * (1 + det) * tt)
                for m in ms for det in (-0.003, 0.003))
        return x * e / (len(ms) * 2)

    def bas(m, d):
        e, tt = env(d, a=0.006, dec=0.3)
        ph = 2 * np.pi * mtof(m) * tt
        return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * e * np.minimum((d - tt) / 0.03, 1)

    # --- davul ---
    def kick():
        e, tt = env(0.35, dec=0.12)
        f = 52 + 70 * np.exp(-tt / 0.03)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * e

    def shaker(d=0.07): return fx.shaker(rng, d) * 0.18

    def snap():  # parmak şıklatma
        e, tt = env(0.12, a=0.0005, dec=0.02)
        return bant(fx.renkli(len(tt), rng), 1500, 4500) * e * 2.2 + np.sin(2 * np.pi * 1800 * tt) * e * 0.3

    akorlar = s["muzik"]["akorlar"]
    olcu = 4 * vurus
    kapanis = next((sh["bas"] for sh in s["sahneler"][1:] if sh["tur"] == "kapanis"), sure)

    def akor_at(tb):
        if tb >= kapanis:  # kapanış: ilk akora dön (parlak çözülme)
            return akorlar[0]
        return akorlar[int(tb / olcu) % len(akorlar)]

    bosluk = gecis_bosluklari(s)
    def bosta(tb): return any(a <= tb < b for a, b in bosluk)

    adim = vurus / 2
    arp = [0, 2, 1, 3, 2, 1, 3, 2]
    for i in range(int(son_an / adim) + 1):
        tb = i * adim
        if tb >= son_an: break
        notlar = akor_at(tb); vur = i % 2 == 0; tam = tb >= dusus
        nota = notlar[arp[i % 8] % len(notlar)] + 12
        ekle(muzik, tb, marimba(nota, parlak=1.3 if tam else 0.8), 0.20 if tam else 0.16, pan=(-0.35 if i % 2 else 0.35))
        if tam and i % 4 == 3:  # oktav süsü
            ekle(muzik, tb + adim / 2, marimba(nota + 12, 0.4, 1.4), 0.07, pan=0.5)
        ekle(muzik, tb, shaker(), 0.5 if tam else 0.28, pan=0.25)
        if tam and i % 4 == 1:
            ekle(muzik, tb + adim / 2, shaker(0.05), 0.3, pan=-0.25)
        if tam and not bosta(tb):
            if vur: ekle(muzik, tb, kick(), 0.85)
            if i % 4 == 2: ekle(muzik, tb, snap(), 0.55, pan=-0.15)
            if vur: ekle(muzik, tb, bas(min(notlar) - 24, adim * 1.8), 0.34)
    k = 0
    while k * olcu < son_an:
        ekle(muzik, k * olcu, pad(akor_at(k * olcu), min(olcu + 0.1, son_an - k * olcu + 0.1)), 0.14)
        k += 1
    if kapanis < son_an:  # kapanış girişinde akor vuruşu
        kok = akorlar[0]
        for j, m in enumerate(kok):
            ekle(muzik, kapanis + j * 0.012, marimba(m + 12, 1.0, 1.2), 0.12)
        ekle(muzik, kapanis, pad(kok, min(1.4, son_an - kapanis)), 0.10)
    kok = akorlar[0]
    for j, m in enumerate([min(kok) - 12] + list(kok) + [kok[1] + 12]):
        ekle(muzik, son_an + j * 0.03, marimba(m + 12, 1.2, 1.1), 0.11)
    ekle(muzik, son_an, pad(kok, 0.6), 0.25)
    ekle(muzik, son_an, kick(), 0.6)

    # --- kâğıt efektleri ---
    def kat():  # kâğıt katlanma: kısa, parlak hışırtı + alçak tok
        e, tt = env(0.11, a=0.004, dec=0.03)
        x = bant(fx.renkli(len(tt), rng), 1800, 6000) * e * 2.0
        e2, t2 = env(0.06, a=0.002, dec=0.015)
        x[: len(t2)] += np.sin(2 * np.pi * 180 * t2) * e2 * 0.5
        return x

    def hisirti(d):  # kâğıt sürtünmesi: kısa taneler, ortası kabarık (tek düze bant gürültüsü değil)
        return fx.hisirti(rng, d, yogunluk=120) * 0.6

    def kayma(d):
        tt = np.arange(int(d * SR)) / SR; p = tt / d
        return bant(fx.renkli(len(tt), rng, -6.0), 250, 1600) * np.sin(np.pi * p) ** 2 * 1.6

    def fiske():  # kart sallanması: tık + küçük ahşap ton
        e, tt = env(0.08, a=0.0004, dec=0.012)
        return bant(fx.renkli(len(tt), rng), 2500, 7000) * e * 1.2 + np.sin(2 * np.pi * 950 * tt) * e * 0.6

    def tik(f):
        e, tt = env(0.04, a=0.0005, dec=0.01)
        return np.sin(2 * np.pi * f * tt) * e

    def pat():  # yumuşak darbe: alçak tok + kâğıt şaplağı
        e, tt = env(0.5, a=0.002, dec=0.12)
        sub = np.sin(2 * np.pi * np.cumsum(60 + 60 * np.exp(-tt / 0.05)) / SR) * e
        return sub + bant(fx.renkli(len(tt), rng), 600, 3500) * np.exp(-tt / 0.03) * 1.2

    def parilti():
        out = np.zeros(int(0.9 * SR))
        for j, m in enumerate([86, 90, 93, 98, 102]):
            x = marimba(m, 0.6, 1.5)
            i = int(j * 0.05 * SR); out[i:i + len(x)] += x[: len(out) - i]
        return out * 0.6

    uret = {
        "kat": lambda e: kat(), "hisirti": lambda e: hisirti(e.get("sure", 0.4)), "kayma": lambda e: kayma(e.get("sure", 0.5)),
        "fiske": lambda e: fiske(), "tik": lambda e: tik(e["frekans"]), "pat": lambda e: pat(), "parilti": lambda e: parilti(),
    }
    for an, ad, kaz, pan, ek in zaman.ses_olaylari(s):
        ekle(sfx, an, uret[ad](ek), kaz, pan)

    # --- seslendirme (platform/ses çıktısı: 48 kHz, seviyelenmiş) ---
    ses_iz = np.zeros(n)
    bulunan = []
    for satir in s["seslendirme"].get("satirlar", []):
        yol = (seslendirme or Path()) / f"{satir['id']}.wav"
        if not seslendirme or not yol.exists():
            continue
        x, sr = sf.read(str(yol))
        if x.ndim > 1: x = x.mean(1)
        if sr != SR:
            x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
        x = x / (np.abs(x).max() + 1e-9) * 0.9
        i = int(satir["t"] * SR); ses_iz[i:i + len(x)] += x[: max(0, n - i)]
        bulunan.append(satir["id"])
    ses_iz = np.tanh(ses_iz * 1.2) / np.tanh(1.2)
    zarf = np.convolve(np.abs(ses_iz), np.ones(int(0.05 * SR)) / int(0.05 * SR), "same")
    zarf = np.convolve((zarf > 0.02).astype(float), np.ones(int(0.15 * SR)) / int(0.15 * SR), "same")
    muzik_k = muzik * (1 - 0.6 * np.clip(zarf, 0, 1))[:, None]  # konuşurken müzik ~8 dB altta
    sonum = np.clip((sure - t_all) / 0.3, 0, 1)[:, None]
    miks = np.tanh((muzik_k * 0.85 + sfx * 0.6 + ses_iz[:, None] * 1.05) * sonum * 1.1)
    cikti.mkdir(parents=True, exist_ok=True)
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.95).astype(np.float32), SR)
    return {"seslendirme": bulunan}
