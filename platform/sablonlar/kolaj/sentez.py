"""Kolaj şablonunun sesi: kodla sentezlenen oyuncu müzik (çekilen gitar, kontrbas, alkış, şıklatma,
çan) + kâğıt efektleri (yırtılma, bant, kayma, mühür, fiş yazıcısı) + seslendirme miksi.

Müzik `zaman.ses_olaylari` ile aynı anlara kilitlidir: tam ritim `muzik.dusus` anında (yırtılmayla)
girer, `muzik.zirve` anında çan akoru vurur, `muzik.sakin` aralığında davul susar, sonda tonik akor çınlar.
Gerekenler: numpy, soundfile; scipy varsa süzgeçler hızlanır.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import miks as ortak_miks  # noqa: E402  (platform/ortak/miks.py: kökler)
import sfx as fx  # noqa: E402  (platform/ortak/sfx.py: beyaz gürültüsüz efektler)

import zaman

SR = 48000


def _lfilter(b, a, x):
    try:
        from scipy.signal import lfilter
        return lfilter(b, a, x)
    except ImportError:  # tek kutuplu süzgeçler için yavaş ama doğru yedek
        y = np.zeros_like(x); v = 0.0
        for i in range(len(x)):
            v = b[0] * x[i] - a[1] * v; y[i] = v
        return y


def lp(x, f):
    a = math.exp(-2 * math.pi * f / SR)
    return _lfilter([1 - a], [1, -a], x)


def hp(x, f):
    return x - lp(x, f)


def bp(x, f0, f1):
    return lp(hp(x, f0), f1)


def zarf(d, a=0.003, dec=None):
    tt = np.arange(int(d * SR)) / SR
    e = np.minimum(tt / a, 1.0)
    return e * (np.exp(-tt / dec) if dec else 1.0), tt


def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


class Ses:
    def __init__(self, sure: float, tohum: int = 7):
        self.n = int(SR * sure)
        self.rng = np.random.default_rng(tohum)

    def bos(self):
        return np.zeros((self.n, 2))

    def ekle(self, buf, t0, x, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= self.n or i < 0:
            return
        x = x[: self.n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * gain * l * 1.414
        buf[i:i + len(x), 1] += x * gain * r * 1.414

    def gur(self, d):  # pembe gürültü: beyaz gürültünün tiz cızırtısı yok
        return fx.renkli(int(d * SR), self.rng)

    # --- çalgılar ---
    def cekme(self, m, d=0.9, parlak=0.5):
        """Karplus-Strong çekilen tel (naylon gitar havası)."""
        f = mtof(m); N = max(2, int(SR / f))
        n = int(d * SR)
        x = np.zeros(n)
        x[:N] = lp(self.rng.uniform(-1, 1, N), 2500 + 5000 * parlak)
        g = 0.996
        b = [1.0]; a = np.zeros(N + 2); a[0] = 1; a[N] = -g * 0.5; a[N + 1] = -g * 0.5
        y = _lfilter(b, a, x)
        e, _ = zarf(d, a=0.001, dec=d * 0.45)
        return y * e * 0.8

    def bas(self, m, d=0.5):
        e, tt = zarf(d, a=0.004, dec=0.22)
        ph = 2 * math.pi * mtof(m) * tt
        return (np.sin(ph) * 0.85 + np.sin(2 * ph) * 0.18 + np.sin(3 * ph) * 0.06) * e

    def can(self, m, d=1.4):
        """Glokenşpil: temel + uyumsuz kısmi."""
        e, tt = zarf(d, a=0.001, dec=0.45)
        f = mtof(m)
        return (np.sin(2 * math.pi * f * tt) + 0.35 * np.sin(2 * math.pi * f * 2.76 * tt) * np.exp(-tt / 0.12)) * e * 0.5

    def ped(self, notalar, d):
        e, tt = zarf(d, a=0.5)
        e *= np.minimum(1, (d - tt) / 0.4)
        x = sum(np.sin(2 * math.pi * mtof(m) * tt + k) + 0.25 * np.sin(4 * math.pi * mtof(m) * tt) for k, m in enumerate(notalar))
        return lp(x * e / len(notalar), 1800)

    def kick(self):
        e, tt = zarf(0.35, dec=0.12)
        f = 50 + 90 * np.exp(-tt / 0.03)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * e

    def alkis(self):
        e, tt = zarf(0.22, dec=0.06)
        x = bp(self.gur(0.22), 900, 3200)
        for k in (0.0, 0.009, 0.019):
            x[int(k * SR):int(k * SR) + 260] *= 2.5
        return x * e * 0.9

    def sikla(self):
        e, tt = zarf(0.09, a=0.0005, dec=0.018)
        return bp(self.gur(0.09), 1800, 5000) * e * 1.4

    def shaker(self):
        return fx.shaker(self.rng, 0.07) * 0.16

    # --- kâğıt efektleri ---
    def efekt(self, tur):
        g = self.gur
        if tur == "harf":
            e, tt = zarf(0.05, a=0.0008, dec=0.012)
            return bp(g(0.05), 700, 4500) * e * 0.8 + np.sin(2 * math.pi * 210 * tt) * np.exp(-tt / 0.015) * 0.25
        if tur == "yazici":
            n = int(0.16 * SR); x = np.zeros(n)
            for k in range(11):
                i = int(k * SR / 70); x[i:i + 90] += self.rng.uniform(0.6, 1.0)
            return bp(x * g(0.16), 1500, 4500) * 0.5
        if tur == "bant":
            e, tt = zarf(0.2, a=0.01, dec=0.06)
            am = 0.5 + 0.5 * np.sin(2 * math.pi * 95 * tt)
            return bp(g(0.2), 1500, 4000) * am * e * 0.7
        if tur == "kaydir":
            d = 0.3; tt = np.arange(int(d * SR)) / SR
            e = np.sin(np.pi * tt / d) ** 2
            return lp(hp(g(d), 300), 2200) * e * 0.32
        if tur == "damga":
            e, tt = zarf(0.25, a=0.001, dec=0.07)
            return np.sin(2 * math.pi * (75 + 40 * np.exp(-tt / 0.02)) * tt) * e + bp(g(0.25), 400, 2500) * np.exp(-tt / 0.01) * 0.5
        if tur == "carp":
            e, tt = zarf(0.45, a=0.001, dec=0.12)
            return (np.sin(2 * math.pi * (55 + 60 * np.exp(-tt / 0.03)) * tt) * e * 1.1
                    + bp(g(0.45), 300, 3000) * np.exp(-tt / 0.035) * 0.6)
        if tur == "yirt":
            d = 0.42; n = int(d * SR); tt = np.arange(n) / SR
            tane = np.zeros(n)
            yogun = self.rng.random(n) < (0.004 + 0.02 * np.sin(np.pi * tt / d))
            tane[yogun] = self.rng.uniform(0.3, 1.0, yogun.sum())
            tane = lp(tane, 900) * 25
            e = np.minimum(tt / 0.03, 1) * np.exp(-np.maximum(tt - 0.22, 0) / 0.06)
            return bp(g(d), 900, 7000) * (0.25 + tane) * e * 0.8
        if tur == "kalem":
            d = 0.32; tt = np.arange(int(d * SR)) / SR
            e = np.sin(np.pi * tt / d) * (0.6 + 0.4 * np.sin(2 * math.pi * 7 * tt))
            return bp(g(d), 2500, 6000) * e * 0.35
        if tur == "esit":
            x = np.zeros(int(0.12 * SR)); h = self.efekt("harf")
            x[:len(h)] += h; x[int(0.07 * SR):int(0.07 * SR) + len(h)] += h[: len(x) - int(0.07 * SR)]
            return x
        raise ValueError(tur)


def muzik(s: dict, S: Ses) -> np.ndarray:
    m = s["muzik"]
    sure = s["sure"]
    vurus = 60 / m["bpm"]
    olcu = 4 * vurus
    dusus, zirve, sakin = m["dusus"], m.get("zirve"), m.get("sakin")
    akorlar = m["akorlar"]
    final = sure - 1.6

    def akor(t):
        return akorlar[0] if t >= final else akorlar[int(t / olcu) % len(akorlar)]

    def davul_var(t):
        return t >= dusus and not (sakin and sakin[0] <= t < sakin[1]) and t < sure - 0.6

    out = S.bos()
    # ped: her akor değişiminde yumuşak katman
    t = 0.0
    while t < sure:
        son = min(sure, (int(t / olcu) + 1) * olcu if t < final else sure)
        if t < final <= son:
            son = final
        S.ekle(out, t, S.ped([n + 12 for n in akor(t)[:3]], son - t + 0.3), 0.16 if t < dusus else 0.08)
        t = son
    # sekizlik çekme arpeji
    desen = [0, 2, 1, 3, 2, 1, 3, 2]
    k = 0
    t = 0.0
    while t < sure - 0.5:
        if not (dusus - 0.15 <= t < dusus):  # düşüşten hemen önce nefes
            a = akor(t)
            nota = a[desen[k % 8] % len(a)] + 12
            S.ekle(out, t, S.cekme(nota, 0.7, 0.4 + 0.3 * (t >= dusus)), 0.75 if t < dusus else 0.26, pan=0.25 * (1 if k % 2 else -1))
        k += 1
        t = k * vurus / 2
    # ritim
    for j in range(int(sure / vurus * 4) + 1):
        t = j * vurus / 4
        v = j % 16
        if t < dusus:
            if v in (4, 12) and t < dusus - 0.15:
                S.ekle(out, t, S.sikla(), 0.7, -0.3)
            continue
        if not davul_var(t):
            continue
        if v in (0, 8, 10):
            S.ekle(out, t, S.kick(), 0.9 if v != 10 else 0.55)
        if v in (4, 12):
            S.ekle(out, t, S.alkis(), 0.45, 0.15)
        if v % 2 == 1:
            S.ekle(out, t, S.shaker(), 0.6, 0.4)
    # kontrbas: kök ve beşli
    for j in range(int(sure / vurus * 2) + 1):
        t = j * vurus / 2
        if t < dusus or t >= sure - 0.5:
            continue
        a = akor(t)
        if sakin and sakin[0] <= t < sakin[1]:
            if j % 8 == 0:
                S.ekle(out, t, S.bas(a[0] - 12, 2.0), 0.4)
            continue
        if j % 8 in (0, 3, 4, 6):
            S.ekle(out, t, S.bas(a[0] - 12 + (7 if j % 8 == 6 else 0), 0.45), 0.55)
    # zirve: yükselen çan akoru + ek darbe
    if zirve is not None:
        a = akor(zirve)
        for i, n in enumerate(sorted(a)):
            S.ekle(out, zirve + 0.05 * i, S.can(n + 24), 0.22, -0.4 + 0.25 * i)
        S.ekle(out, zirve, S.kick(), 0.8)
    # kapanış motifi (kapanış sahnesinde) + final akoru
    kap = [sh["bas"] for sh in s["sahneler"] if sh["tur"] == "kapanis"]
    if kap:
        t0 = math.ceil(kap[0] / vurus) * vurus
        for i, (dt, ad) in enumerate([(0, 2), (0.5, 1), (1.0, 0), (1.5, 1), (2.0, 3)]):
            if t0 + dt * vurus * 2 < final:
                n = sorted(akor(t0 + dt * vurus * 2))[ad]
                S.ekle(out, t0 + dt * vurus * 2, S.can(n + 24, 1.0), 0.14, 0.3)
    for i, n in enumerate(sorted(akorlar[0])):
        S.ekle(out, final + 0.4 + 0.03 * i, S.cekme(n + 12, 1.6, 0.6), 0.45, -0.3 + 0.2 * i)
        S.ekle(out, final + 0.4, S.can(n + 24, 1.6), 0.12)
    S.ekle(out, final + 0.4, S.bas(akorlar[0][0] - 12, 1.2), 0.5)
    return out


def efektler(s: dict, S: Ses) -> np.ndarray:
    out = S.bos()
    duzey = {"harf": 0.35, "yazici": 0.3, "bant": 0.35, "kaydir": 0.45, "damga": 0.8, "carp": 1.0, "yirt": 0.9, "kalem": 0.5, "esit": 0.4}
    for t, tur in zaman.ses_olaylari(s):
        S.ekle(out, t, S.efekt(tur), duzey[tur], float(S.rng.uniform(-0.3, 0.3)))
    return out


def miksle(s: dict, cikti: Path, seslendirme: Path, muzik_alti_db: float = 8.0, efekt_db: float = -10.5) -> dict:
    """Seslendirme + müzik (konuşmanın ~8 dB altında, konuşurken 3 dB ek kısma) + efektler → cikti/ses.wav"""
    import soundfile as sf
    cikti.mkdir(parents=True, exist_ok=True)
    S = Ses(s["sure"])
    n = S.n
    vo = S.bos(); maske = np.zeros(n); bulunan = {}
    for x in s["seslendirme"].get("satirlar", []):
        yol = seslendirme / f"{x['id']}.wav"
        if not yol.exists():
            continue
        a, sr = sf.read(str(yol), always_2d=True)
        if sr != SR:
            raise RuntimeError(f"{yol}: {sr} Hz (48 kHz bekleniyor)")
        a = a.mean(axis=1)
        i = int(x["t"] * SR); a = a[: max(0, n - i)]
        vo[i:i + len(a)] += a[:, None]; maske[i:i + len(a)] = 1.0
        bulunan[x["id"]] = str(yol)
    rms = lambda z: math.sqrt(float(np.mean(z ** 2)) + 1e-12)
    m = muzik(s, S); e = efektler(s, S)
    vo_rms = rms(vo[maske > 0]) if maske.any() else 0.1
    m *= vo_rms * 10 ** (-muzik_alti_db / 20) / rms(m)
    k = int(0.12 * SR)
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske, np.ones(k) / k, "same"), 0, 1)
    m *= duk[:, None]
    dolu = np.abs(e).sum(1) > 1e-6
    if dolu.any():
        e *= vo_rms * 10 ** (efekt_db / 20) / rms(e[dolu])
    x = vo + m + e
    f = int(0.02 * SR); x[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.3 * SR); x[-f:] *= np.linspace(1, 0, f)[:, None]
    ortak_miks.kok_yaz(cikti, "efekt", e)  # kurgu bu sahnenin efektlerini buradan alır
    sf.write(str(cikti / "ses.wav"), (x / max(1e-9, np.abs(x).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
