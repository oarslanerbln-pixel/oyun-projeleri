"""Oyuncak şablonunun sesi: sentez müzik + oyuncak efektleri + seslendirme → miks (ses.wav).

Müzik ızgarası `muzik.bpm` ve `muzik.ilk_vurus`; dinamik `zaman.enerji` eğrisini izler: sakin giriş, yükseliş,
dorukta alt bas düşüşü ve zil, sakin karşıtlık, parlak kapanış. Efektler `zaman.cizelge` anlarından üretilir.
Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import zaman

SR = 48000


def filtre(x: np.ndarray, lo: float | None = None, hi: float | None = None) -> np.ndarray:
    """FFT maskesiyle yumuşak kenarlı bant filtresi (kısa tamponlar için; scipy gerektirmez)"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi:
        m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def mtof(m: float) -> float:
    return 440 * 2 ** ((m - 69) / 12)


def zarf(d: float, a: float = 0.003, dec: float | None = None):
    tt = np.arange(int(d * SR)) / SR
    e = np.minimum(tt / a, 1.0)
    return e * (np.exp(-tt / dec) if dec else 1.0), tt


def gurultu(d: float, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(int(d * SR))


def bell(f, d, idx=1.2, oran=3.5, dec=0.5):
    e, tt = zarf(d, a=0.002, dec=dec)
    return np.sin(2 * np.pi * f * tt + idx * np.exp(-tt * 6) * np.sin(2 * np.pi * f * oran * tt)) * e


def marimba(f, d=0.6):
    e, tt = zarf(d, a=0.001, dec=0.16)
    return (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 4 * tt) * np.exp(-tt * 30)) * e


class Tampon:
    def __init__(self, sure: float):
        self.n = int(SR * sure)
        self.x = np.zeros((self.n, 2))

    def ekle(self, t0: float, x: np.ndarray, gain: float = 1.0, pan: float = 0.0) -> None:
        i = int(t0 * SR)
        if i >= self.n:
            return
        if i < 0:
            x, i = x[-i:], 0
        x = x[: self.n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        self.x[i:i + len(x), 0] += x * gain * l * 1.414
        self.x[i:i + len(x), 1] += x * gain * r * 1.414


def muzik(s: dict) -> np.ndarray:
    sure = s["sure"]
    b = Tampon(sure)
    c = zaman.cizelge(s)
    en = lambda t: zaman.enerji(s, t)
    bolumler = zaman.akor_bolumleri(s)
    akor_at = lambda t: next((a for x, y, a in bolumler if x <= t < y), bolumler[-1][2])
    vur = 60 / s["muzik"]["bpm"]
    b0 = s["muzik"]["ilk_vurus"]
    buyume = zaman.sahne(s, "buyume")["bas"]
    d = c["doruk"]
    k = c["karsitlik"]["bas"] if c["karsitlik"] else None
    p = c["kapanis"]["bas"] if c["kapanis"] else None
    durgun_son = k if k is not None else (p if p is not None else sure)

    # pad + bas: her akor kendi bölümünde
    for t0, t1, notalar in bolumler:
        kuyruk = 0.6 if t1 >= sure else 0.25
        dur = t1 - t0 + kuyruk
        tt = np.arange(int(dur * SR)) / SR
        atk = 0.7 if t0 == 0 else 0.06 if t0 in (d, p) else 0.25
        e = np.minimum(tt / atk, 1) * np.clip((dur - tt) / kuyruk, 0, 1)
        if t1 >= sure:
            e = np.minimum(tt / atk, 1) * np.exp(-np.maximum(tt - 1.0, 0) * 0.9)
        g = en(t0 + 0.05)
        x = np.zeros((len(tt), 2))
        for m in notalar[1:]:
            for det, ch in ((-0.07, 0), (0.07, 1)):
                f = mtof(m + det)
                x[:, ch] += sum(np.sin(2 * np.pi * f * h * tt + h * ch) / h ** 1.3 for h in range(1, 6))
        for ch in (0, 1):
            x[:, ch] = filtre(x[:, ch] * e, hi=500 + 2800 * g)
        i0 = int(t0 * SR); m_ = min(len(tt), b.n - i0)
        b.x[i0:i0 + m_] += x[:m_] * 0.03 * (0.4 + 0.9 * g)
        f = mtof(notalar[0])
        b.ekle(t0, (np.sin(2 * np.pi * f * tt) + 0.2 * np.sin(4 * np.pi * f * tt)) * e * 0.17 * (0.3 + 0.8 * g))

    # marimba + çan arpeji: yoğunluk dinamiği izler
    olay = []
    t = b0 + vur
    while t < buyume - 0.05: olay.append((t, 0.5)); t += vur
    t = buyume
    orta = buyume + (d - buyume) / 2
    while t < orta - 1e-6: olay.append((t, 0.55)); t += vur / 2
    while t < d - 1e-6: olay.append((t, 0.7)); t += vur / 4
    t = d
    while t < durgun_son - 0.05: olay.append((t, 0.85)); t += vur / 2
    if k is not None:
        vinc = c["karsitlik"]["vinc_t"]
        olay += [(k + 0.1, 0.4), (vinc + 0.1, 0.4), (vinc + 0.6, 0.4)]
        if p is not None:
            t = p - 0.5
            while t < p - 1e-6: olay.append((t, 0.5)); t += vur / 4
    if p is not None:
        t = p
        while t < min(sure - 0.6, p + 1.3): olay.append((t, 0.85)); t += vur / 4 if t < p + 0.75 else vur / 2
    desen = [1, 2, 3, 4, 3, 2, 4, 3]
    for i, (t, v) in enumerate(olay):
        ak = akor_at(t + 1e-3)
        yuksel = 12 if orta <= t < d else 0
        m = ak[desen[i % 8]] + 12 + yuksel
        pan = 0.45 * math.sin(i * 0.9)
        b.ekle(t, marimba(mtof(m)) * 0.16 * v, pan=pan)
        b.ekle(t, bell(mtof(m + 12), 1.2, idx=0.8, oran=2.0, dec=0.35) * 0.05 * v, pan=-pan)

    # davul: yalnız enerjik bölümler (büyüme ve kapanış)
    def tekme(t0, g):
        e, tt = zarf(0.32, a=0.002, dec=0.1)
        b.ekle(t0, np.sin(2 * np.pi * np.cumsum(46 + 90 * np.exp(-tt * 30)) / SR) * e * g)

    def alkis(t0, g, sd):
        e, _ = zarf(0.2, a=0.001, dec=0.05)
        b.ekle(t0, filtre(gurultu(0.2, sd) * e, lo=900, hi=4500) * g, pan=-0.1)

    def ciz(t0, g, sd):
        e, _ = zarf(0.06, a=0.002, dec=0.018)
        b.ekle(t0, filtre(gurultu(0.06, sd) * e, lo=7000) * g, pan=0.3)

    kb = 0
    while b0 + kb * vur < sure:
        bt = b0 + kb * vur
        enerjik = buyume - 1e-6 <= bt < durgun_son - 0.05
        kapanista = p is not None and p - 1e-6 <= bt < sure - 0.4
        if enerjik or kapanista:
            tekme(bt, 0.5 if bt < d else 0.65)
            if d <= bt < durgun_son and kb % 2 == 0:
                alkis(bt + vur, 0.18, kb)
            ciz(bt + vur / 2, 0.08, 100 + kb)
            if d <= bt < durgun_son:
                ciz(bt + vur / 4, 0.04, 200 + kb); ciz(bt + 3 * vur / 4, 0.04, 300 + kb)
        kb += 1

    # doruk: alt bas düşüşü + zil; öncesinde filtreli gürültü süpürmesi
    e, tt = zarf(1.6, a=0.003, dec=0.45)
    b.ekle(d, np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-tt * 8)) / SR) * e * 0.6)
    e, _ = zarf(2.2, a=0.002, dec=0.7)
    b.ekle(d, filtre(gurultu(2.2, 9) * e, lo=5000) * 0.09, pan=-0.3)
    b.ekle(d, filtre(gurultu(2.2, 10) * e, lo=5000) * 0.09, pan=0.3)
    dur = d - buyume - 0.1
    tt = np.arange(int(dur * SR)) / SR
    b.ekle(buyume + 0.1, filtre(gurultu(dur, 11) * (tt / dur) ** 2, lo=1500, hi=9000) * 0.12)
    if p is not None:  # kapanış akoru çanları
        for j, m in enumerate([72, 76, 77, 81, 84]):
            b.ekle(p + 0.02 * j, bell(mtof(m), 1.9, idx=0.7, oran=2.0, dec=0.9) * 0.05, pan=-0.4 + 0.2 * j)
    return b.x


def sfx(s: dict) -> np.ndarray:
    b = Tampon(s["sure"])
    c = zaman.cizelge(s)

    def pop(t0, f, g, pan=0.0):
        e, tt = zarf(0.12, a=0.001, dec=0.03)
        b.ekle(t0, np.sin(2 * np.pi * np.cumsum(f * (1 + 1.2 * np.exp(-tt * 40))) / SR) * e * g, pan=pan)

    def boing(t0, g, f0=320):
        e, tt = zarf(0.35, a=0.003, dec=0.12)
        f = f0 * (0.7 + 0.6 * tt / 0.35) * (1 + 0.04 * np.sin(2 * np.pi * 18 * tt))
        b.ekle(t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * e * g)

    def tok(t0, g):  # yumuşak iniş
        e, tt = zarf(0.15, a=0.001, dec=0.035)
        x = np.sin(2 * np.pi * np.cumsum(140 + 120 * np.exp(-tt * 50)) / SR) + filtre(gurultu(0.15, int(t0 * 100)), hi=1500) * 0.3
        b.ekle(t0, x * e * g)

    def whoosh(t0, dur, g, lo=400, hi=3500):
        tt = np.arange(int(dur * SR)) / SR
        b.ekle(t0, filtre(gurultu(dur, int(t0 * 10)) * np.sin(np.pi * tt / dur) ** 2, lo=lo, hi=hi) * g)

    kb = c["kolon_bas"]
    n_adim = c["adim_sayisi"]
    for i in range(1, n_adim):  # adım kolonları yükselir, kahraman zıplar
        pop(kb[i], 420 + 20 * i, 0.5)
    for j, z in enumerate(c["ziplamalar"]):
        boing(z, 0.35, 320 + 20 * j); tok(z + zaman.ZIPLA_SN, 0.5)
    y = c["yazilar"]["adim"]
    if y:
        pop(y["t"], 660, 0.45); pop(y["t"] + 0.05, 880, 0.3)
    n = len(kb)
    for i in range(n_adim, n):  # dalga: yükselen tıkırtılar
        u = (i - n_adim) / max(1, n - n_adim - 1)
        pop(kb[i], 300 * 2 ** (1.6 * u), 0.16 + 0.12 * u, pan=0.6 * math.sin(i * 0.5))
    buyume = zaman.sahne(s, "buyume")["bas"]
    whoosh(buyume, min(1.2, c["doruk"] - buyume), 0.25)
    d = c["doruk"]
    tok(d, 0.8)
    for k in range(60):  # konfeti çıtırtısı
        r = np.random.default_rng(k)
        t0 = d + 0.05 + r.random() * 1.4
        e, _ = zarf(0.02, a=0.0005, dec=0.006)
        b.ekle(t0, filtre(gurultu(0.02, 400 + k), lo=3000) * e * 0.25 * math.exp(-(t0 - d)), pan=r.random() * 1.4 - 0.7)
    for z in c["kutlama"]:
        boing(z, 0.18, 380); tok(z + zaman.KUTLAMA_SN, 0.25)
    if c["karsitlik"]:
        whoosh(c["karsitlik"]["vinc_t"] - 0.12, 1.1, 0.28, lo=300, hi=2500)
    if c["kapanis"]:
        p = c["kapanis"]
        dur = max(0.1, p["inis_t"] - p["bas"])
        tt = np.arange(int(dur * SR)) / SR
        b.ekle(p["bas"], np.sin(2 * np.pi * np.cumsum(900 - 2000 * tt / dur * 0.26) / SR) * np.sin(np.pi * tt / dur) * 0.18)
        tok(p["inis_t"], 0.75); boing(p["zipla_t"], 0.4, 360); tok(p["zipla_t"] + 0.4, 0.5)
        y = c["yazilar"]["kapanis"]
        if y:
            pop(y["t"], 700, 0.4); pop(y["t"] + 0.06, 1050, 0.3)
            for j, m in enumerate([84, 88, 91, 96]):
                b.ekle(y["t"] + 0.08 + 0.06 * j, bell(mtof(m), 1.0, idx=0.5, oran=2.0, dec=0.4) * 0.12, pan=-0.3 + 0.2 * j)
    return b.x


def _oku(yol: Path) -> np.ndarray:
    import soundfile as sf
    x, sr = sf.read(str(yol), always_2d=True)
    if sr != SR:  # doğrusal yeniden örnekleme (platform/ses zaten 48 kHz yazar)
        t = np.arange(int(len(x) * SR / sr)) / SR
        x = np.stack([np.interp(t, np.arange(len(x)) / sr, x[:, ch]) for ch in range(x.shape[1])], 1)
    return x if x.shape[1] == 2 else np.repeat(x, 2, axis=1)


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None, muzik_alti_db: float = 8.0, sfx_db: float = -6.0) -> dict:
    """seslendirme + müzik (konuşmanın ~8 dB altında, konuşurken 3 dB ek kısma) + efektler -> cikti/ses.wav"""
    import soundfile as sf
    cikti.mkdir(parents=True, exist_ok=True)
    n = int(SR * s["sure"])
    vo = np.zeros((n, 2)); maske = np.zeros(n)
    bulunan = {}
    for satir in s["seslendirme"].get("satirlar", []):
        yol = (seslendirme or Path()) / f"{satir['id']}.wav"
        if not seslendirme or not yol.exists():
            continue
        x = _oku(yol)
        i = int(satir["t"] * SR); x = x[: n - i]
        vo[i:i + len(x)] += x; maske[i:i + len(x)] = 1.0
        bulunan[satir["id"]] = len(x) / SR
    rms = lambda a: math.sqrt(float(np.mean(a ** 2)) + 1e-12)
    ref = rms(vo[maske > 0]) if maske.any() else 0.08
    m = muzik(s)
    m *= ref * 10 ** (-muzik_alti_db / 20) / rms(m)
    k = int(0.12 * SR)
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske, np.ones(k) / k, "same"), 0, 1)
    m *= duk[:, None]
    e = sfx(s)
    dolu = np.abs(e).sum(1) > 1e-6
    if dolu.any():
        e *= ref * 10 ** (sfx_db / 20) / rms(e[dolu])
    x = vo + m + e
    f = int(0.02 * SR); x[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.25 * SR); x[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(str(cikti / "ses.wav"), (x / max(1e-9, np.abs(x).max()) * 0.9).astype(np.float32), SR)
    (cikti / "ses.json").write_text(json.dumps({"seslendirme": bulunan}, ensure_ascii=False), encoding="utf-8")
    return {"seslendirme": bulunan}
