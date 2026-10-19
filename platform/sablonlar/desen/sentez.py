"""Desen şablonunun müziği, efektleri ve miksi (48 kHz stereo, numpy).

Her stilin kendi enstrümanı ve dizisi var; vuruşlar sahne başlarına kilitlidir, son sahnede müzik açılır:
    vitray        cam çan arpeji + yumuşak ped (Re majör pentatonik), hücreler yanarken parıltı
    linol         marimba ostinatosu + bas (La minör pentatonik), merdane gümbürtüsü, damga vuruşu
    cini          mızraplı ud benzeri ezgi (Re hicaz) + def (düm-tek), dem sesi
    teknik-cizim  yumuşak sinüs darbeleri (Fa minör 7), cetvel tıkları
Efektler platform/ortak/sfx.py'den (beyaz gürültüsüz). Seslendirme konuşurken müzik kısılır.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import sfx as fx  # noqa: E402

SR = 48000


def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)


def _zarf(n, atak, sonum):
    t = np.arange(n) / SR
    return np.minimum(t / max(atak, 1e-4), 1.0) * np.exp(-t / sonum)


def can(f, d=1.6):
    n = int(d * SR); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * math.pi * f * k * t) * np.exp(-t / (d * s)) for k, a, s in ((1, 1, .45), (2.76, .35, .18), (5.4, .15, .08)))
    return x * np.minimum(t / 0.004, 1)


def mizrap(f, d=1.2, parlak=1.0):
    n = int(d * SR); t = np.arange(n) / SR
    x = sum((0.8 ** k) * np.sin(2 * math.pi * f * k * t + k) * np.exp(-t * (2.2 + 1.6 * k / parlak)) for k in range(1, 9))
    return x * np.minimum(t / 0.003, 1)


def marimba(f, d=0.6):
    n = int(d * SR); t = np.arange(n) / SR
    return (np.sin(2 * math.pi * f * t) * np.exp(-t / 0.22) + 0.25 * np.sin(2 * math.pi * f * 3.93 * t) * np.exp(-t / 0.04)) * np.minimum(t / 0.002, 1)


def sinus(f, d=0.5):
    n = int(d * SR); t = np.arange(n) / SR
    return (np.sin(2 * math.pi * f * t) + 0.2 * np.sin(4 * math.pi * f * t)) * _zarf(n, 0.01, 0.16)


def ped(notalar, d, atak=1.2):
    n = int(d * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for m in notalar:
        f = mtof(m)
        for dt in (-0.07, 0.0, 0.07):
            x += np.sin(2 * math.pi * f * (1 + dt / 100) * t + dt * 9)
    e = np.minimum(t / atak, 1) * np.minimum((d - t) / 0.6, 1).clip(0, 1)
    return x / (3 * len(notalar)) * e


def ekle(buf, t0, x, kazanc=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= len(buf) or i < 0:
        return
    x = x[: len(buf) - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:i + len(x), 0] += x * kazanc * l * 1.414
    buf[i:i + len(x), 1] += x * kazanc * r * 1.414


STILLER = {
    "vitray": {"bpm": 76, "kok": 62, "dizi": [0, 2, 4, 7, 9, 12, 14], "ped": [50, 57, 62, 66]},
    "linol": {"bpm": 92, "kok": 57, "dizi": [0, 3, 5, 7, 10, 12], "ped": [45, 52, 57]},
    "cini": {"bpm": 96, "kok": 62, "dizi": [0, 1, 4, 5, 7, 8, 10, 12], "ped": [50, 57]},
    "teknik-cizim": {"bpm": 100, "kok": 53, "dizi": [0, 3, 7, 10, 12, 15], "ped": [41, 48, 51, 55]},
}


def muzik(s: dict) -> tuple[np.ndarray, np.ndarray]:
    """(müzik, efektler) — ikisi de (n, 2)."""
    stil = s["stil"]
    p = {**STILLER[stil], **{k: v for k, v in s.get("muzik", {}).items() if k in ("bpm", "kok")}}
    sure = s["sure"]
    n = int(sure * SR)
    m = np.zeros((n, 2)); e = np.zeros((n, 2))
    rng = np.random.default_rng(5)
    vurus = 60.0 / p["bpm"]
    sahne_t = [x["t"] for x in s["sahneler"]]
    son_t = sahne_t[-1]
    kok, dizi = p["kok"], p["dizi"]
    ekle(m, 0.0, ped(p["ped"], sure, 1.5), 0.20)
    ekle(m, son_t, ped([x + 12 for x in p["ped"][1:]], sure - son_t, 0.3), 0.10)
    k = 0
    t = 0.0
    while t < sure - 0.3:
        enerji = 1.0 if t >= son_t else 0.75 + 0.25 * (sum(1 for x in sahne_t if x <= t) / len(sahne_t))
        adim = vurus / 2
        if stil == "vitray":
            nota = kok + 12 + dizi[(k * 3 + (k // 8)) % len(dizi)]
            ekle(m, t, can(mtof(nota), 1.4), 0.16 * enerji, pan=0.5 * math.sin(k * 0.9))
        elif stil == "linol":
            desen = [0, 2, 3, 2, 4, 3, 1, 2]
            ekle(m, t, marimba(mtof(kok + 12 + dizi[desen[k % 8]])), 0.22 * enerji, pan=0.3 * (-1) ** k)
            if k % 4 == 0:
                ekle(m, t, marimba(mtof(kok - 12 + (0 if (k // 8) % 2 == 0 else 5)), 0.9), 0.30 * enerji)
            if k % 4 == 0:
                ekle(e, t, fx.kick(rng, 0.3, 52, 0.05), 0.20 * enerji)
            elif k % 4 == 2 and t >= sahne_t[min(1, len(sahne_t) - 1)]:
                ekle(e, t, fx.tik(rng, 1800, 0.02), 0.10 * enerji)
        elif stil == "cini":
            ezgi = [0, 1, 2, 1, 3, 2, 1, 0, 4, 3, 2, 3, 2, 1, 0, -1]
            dd = ezgi[k % 16]
            if k % 2 == 0 or k % 16 in (5, 13):
                ekle(m, t, mizrap(mtof(kok + 12 + dizi[dd % len(dizi)] - (12 if dd < 0 else 0)), 1.0), 0.20 * enerji, pan=-0.2)
            duz = k % 8
            if duz in (0, 3, 4):
                ekle(e, t, fx.kick(rng, 0.35, 70, 0.08), 0.22 * enerji)  # düm
            elif duz in (2, 6):
                ekle(e, t, fx.tik(rng, 2600, 0.03), 0.16 * enerji, pan=0.3)  # tek
        else:  # teknik-cizim
            if k % 2 == 0:
                ekle(m, t, sinus(mtof(kok + 12 + dizi[(k // 2) % len(dizi)]), 0.45), 0.20 * enerji, pan=0.35 * (-1) ** (k // 2))
            if k % 8 == 0:
                ekle(m, t, sinus(mtof(kok - 12), 0.9), 0.30 * enerji)
            ekle(e, t, fx.tik(rng, 5200, 0.008), 0.05 * enerji)
        k += 1
        t += adim
    for i, t0 in enumerate(sahne_t):  # sahne vurguları
        if stil == "vitray":
            ekle(e, t0 + 0.05, fx.parilti(rng, 1.4), 0.12)
        elif stil == "linol":
            ekle(e, t0 + 0.02, fx.boom(rng, 0.7), 0.14)  # merdane
            ekle(e, t0 + 0.85, fx.kick(rng, 0.25, 90, 0.4), 0.30)  # damga
        elif stil == "cini":
            ekle(m, t0 + (1.05 if i == 0 else 0.0), can(mtof(kok + 24), 2.0), 0.10)
        else:
            for j in range(3):
                ekle(e, t0 + 1.0 + j * 0.12, fx.tik(rng, 3400, 0.012), 0.20)
    ekle(e, son_t, fx.zil(rng, 1.8), 0.10)
    yumusat = int(0.6 * SR)
    m[-yumusat:] *= np.linspace(1, 0, yumusat)[:, None]
    return m, e


def _oku(yol: Path) -> np.ndarray:
    import soundfile as sf
    x, sr = sf.read(str(yol), always_2d=True)
    if sr != SR:
        raise ValueError(f"{yol}: {sr} Hz, {SR} Hz bekleniyor")
    return x if x.shape[1] == 2 else np.repeat(x, 2, axis=1)


def miksle(s: dict, is_: Path, ses_dizini: Path) -> dict:
    """Seslendirme + müzik (konuşmanın ~9 dB altında, konuşurken ek kısma) + efektler → is_/ses.wav"""
    import soundfile as sf
    is_.mkdir(parents=True, exist_ok=True)
    n = int(s["sure"] * SR)
    vo = np.zeros((n, 2)); maske = np.zeros(n)
    bulunan = []
    for x in s["seslendirme"].get("satirlar", []):
        yol = ses_dizini / f"{x['id']}.wav"
        if not yol.exists():
            continue
        a = _oku(yol)
        i = int(x["t"] * SR); a = a[: n - i]
        vo[i:i + len(a)] += a; maske[i:i + len(a)] = 1.0
        bulunan.append(x["id"])
    m, e = muzik(s)
    rms = lambda a: math.sqrt(float(np.mean(a ** 2)) + 1e-12)  # noqa: E731
    ref = rms(vo[maske > 0]) if bulunan else 0.08
    m *= ref * 10 ** (-9 / 20) / rms(m)
    k = int(0.12 * SR)
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske, np.ones(k) / k, "same"), 0, 1)
    m *= duk[:, None]
    if np.any(e):
        e *= ref * 10 ** (-6 / 20) / max(rms(e[np.abs(e).sum(1) > 1e-6]), 1e-9)
    karisim = vo + m + e
    f = int(0.02 * SR); karisim[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.25 * SR); karisim[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(str(is_ / "ses.wav"), (karisim / max(1e-9, np.abs(karisim).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
