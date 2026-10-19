"""Karakter şablonunun sesi: sentez müzik (sahnenin enerjisine göre) + efektler + seslendirme → miks.

Müzik yumuşak, arkadaşça: tınılı tel (Karplus-Strong) akorları ve pad sürekli; "enerjik" sahnelerde kick,
shaker ve bas girer, "sakin" sahnelerde yalnız tel ve pad kalır. Efektler zaman çizelgesinden (senaryo.ses_olaylari).
Müzik konuşmanın ~8 dB altında, konuşurken 3 dB daha kısılır. Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ortak"))
import sfx as fx  # noqa: E402

import senaryo  # noqa: E402

SR = 48000
AKORLAR = [[48, 52, 55, 59], [45, 48, 52, 55], [41, 45, 48, 52], [43, 47, 50, 53]]   # Cmaj7 Am7 Fmaj7 G7


def mtof(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def tel(nota: float, d: float, rng) -> np.ndarray:
    """Karplus-Strong telli çalgı (ukulele/gitar arası): parlak atak, yumuşak sönüm."""
    n = int(d * SR); p = max(2, int(SR / mtof(nota)))
    buf = rng.uniform(-1, 1, p); buf = np.convolve(buf, np.ones(3) / 3, "same")
    out = np.empty(n); i = 0
    while i < n:
        k = min(p, n - i); out[i:i + k] = buf[:k]
        buf = 0.996 * 0.5 * (buf + np.roll(buf, -1)); i += k
    return out * np.minimum(1, (n - np.arange(n)) / (0.05 * SR))


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None, muzik_alti_db: float = 8.0) -> dict:
    import soundfile as sf
    sure = s["sure"]; n = int(SR * sure)
    rng = np.random.default_rng(23)
    muzik = np.zeros((n, 2)); efekt = np.zeros((n, 2))
    akorlar = s["muzik"].get("akorlar", AKORLAR)
    vurus = 60 / s["muzik"]["bpm"]; olcu = 4 * vurus
    son_an = sure - 0.6

    def ekle(buf, t0, x, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= n or i < 0: return
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * gain * l * 1.414
        buf[i:i + len(x), 1] += x * gain * r * 1.414

    def pad(notalar, d):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / 0.5, 1) * np.minimum((d - tt) / 0.4, 1)
        x = sum(np.sin(2 * np.pi * mtof(k) * (1 + det) * tt) for k in notalar for det in (-0.003, 0.003))
        return fx.bant(x, ust=1600) * e / (len(notalar) * 2)

    def kick():
        tt = np.arange(int(0.3 * SR)) / SR
        return np.sin(2 * np.pi * np.cumsum(48 + 70 * np.exp(-tt / 0.03)) / SR) * np.exp(-tt / 0.1)

    def bas(nota, d):
        tt = np.arange(int(d * SR)) / SR
        return np.sin(2 * np.pi * mtof(nota) * tt) * np.exp(-tt / 0.4) * np.minimum(1, (d - tt) / 0.04)

    # tel: her vuruşta akorun bir sesi (yumuşak arpej), ölçü başında tam akor; pad sürekli
    k = 0
    while k * olcu < son_an:
        tb = k * olcu; a = akorlar[k % len(akorlar)]
        ekle(muzik, tb, pad(a, min(olcu + 0.3, son_an - tb + 0.4)), 0.22)
        for j, nota in enumerate(a):
            ekle(muzik, tb + j * 0.018, tel(nota + 12, 1.6, rng), 0.11, pan=(j - 1.5) * 0.2)
        for v in range(1, 8):
            t = tb + v * vurus / 2
            if t < son_an:
                ekle(muzik, t, tel(a[(v * 3) % 4] + 24, 0.8, rng), 0.07 if v % 2 else 0.05, pan=0.3 if v % 2 else -0.3)
        k += 1
    adim = vurus / 2
    for i in range(int(son_an / adim)):
        t = i * adim
        en = senaryo.enerji(s, t)
        if en == "sakin":
            continue
        a = akorlar[int(t / olcu) % len(akorlar)]
        if i % 2 == 0:
            ekle(muzik, t, kick(), 0.42 if en == "enerjik" else 0.22)
            ekle(muzik, t, bas(min(a) - 12, vurus * 0.9), 0.2)
        if en == "enerjik":
            ekle(muzik, t + adim / 2, fx.shaker(rng, 0.07), 0.05, pan=0.2)
    # final: parlak akor
    for j, nota in enumerate(akorlar[0] + [akorlar[0][0] + 24]):
        ekle(muzik, son_an + j * 0.03, tel(nota + 12, 0.9, rng), 0.12, pan=(j - 2) * 0.2)

    def pop():  # yumuşak "blop": aşağı kayan kısa ton
        tt = np.arange(int(0.12 * SR)) / SR
        return np.sin(2 * np.pi * np.cumsum(420 + 600 * np.exp(-tt / 0.02)) / SR) * np.minimum(tt / 0.001, 1) * np.exp(-tt / 0.03)

    uret = {"pop": pop,
            "tik": lambda: fx.tik(rng, 2600, 0.015) * 0.5,
            "hisirti": lambda: fx.whoosh(rng, 0.28, alt=300, ust=1800) * 0.35,
            "parilti": lambda: fx.parilti(rng, 1.0) * 0.6}
    for an, ad in senaryo.ses_olaylari(s):
        ekle(efekt, an, uret[ad](), 1.0, pan=0.15)

    vo = np.zeros(n); bulunan = []
    for satir in s["seslendirme"]["satirlar"]:
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
    muzik *= ref * 10 ** (-muzik_alti_db / 20) / rms(muzik)
    kk = int(0.12 * SR)
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske.astype(float), np.ones(kk) / kk, "same"), 0, 1)
    muzik *= duk[:, None]
    dolu = np.abs(efekt).sum(1) > 1e-6
    if dolu.any():
        efekt *= ref * 10 ** (-10 / 20) / max(rms(efekt[dolu]), 1e-9)
    miks = vo[:, None] + muzik + efekt
    f = int(0.02 * SR); miks[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.4 * SR); miks[-f:] *= np.linspace(1, 0, f)[:, None]
    cikti.mkdir(parents=True, exist_ok=True)
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
