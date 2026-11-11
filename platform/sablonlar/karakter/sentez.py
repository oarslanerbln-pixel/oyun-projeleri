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


def piyano(nota: float, d: float, hiz: float = 0.7) -> np.ndarray:
    """Keçe piyano: harmonikli sinüs, yumuşak atak (8 ms), yüksek harmonikler hızlı söner; gürültü yok."""
    n = int(d * SR); tt = np.arange(n) / SR; f = mtof(nota)
    x = np.zeros(n)
    for h, (g, son) in enumerate(((1.0, 1.6), (0.42, 0.9), (0.18, 0.55), (0.08, 0.35), (0.04, 0.22)), 1):
        if f * h > 9000:
            break
        x += g * np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * tt) * np.exp(-tt / (son * (1.4 - 0.4 * hiz)))
    x *= np.minimum(tt / 0.008, 1) * np.minimum(1, (d - tt) / 0.12)
    return x * hiz * 0.5


def can(nota: float, d: float) -> np.ndarray:
    """Yumuşak çan: uyumsuz kısmi tonlar, uzun sönüm, sinüs (hışırtısız)."""
    n = int(d * SR); tt = np.arange(n) / SR; f = mtof(nota)
    x = sum(g * np.sin(2 * np.pi * f * k * tt) * np.exp(-tt / s_) for k, g, s_ in ((1, 1, 0.9), (2.76, 0.35, 0.4), (5.4, 0.12, 0.2)))
    return x * np.minimum(tt / 0.004, 1) * np.minimum(1, (d - tt) / 0.1) * 0.5


def _piyano_muzik(s, muzik, ekle, akorlar, vurus, son_an):
    """Yalnız temiz keçe piyano (Atilla 2026-11-11: arkada "uvuvu" sesi olmasın): sürekli pad, vibrato, detune ve
    derin vuruş yok; bas notası ≥ C3. Sakin: ölçü başında yumuşak akor. Orta/enerjik: sekizlik arpej (enerjikte daha dolu)."""
    olcu = 4 * vurus
    k = 0
    while k * olcu < son_an:
        tb = k * olcu; a = akorlar[k % len(akorlar)]
        en = senaryo.enerji(s, tb + 0.01)
        ust = [m + 12 for m in a]
        ekle(muzik, tb, piyano(max(min(a), 48), olcu * 1.1, 0.5), 0.14, pan=-0.1)
        if en == "sakin":
            for j, m in enumerate(ust):
                ekle(muzik, tb + j * 0.03, piyano(m, olcu * 0.9, 0.45), 0.09, pan=(j - 1.5) * 0.15)
        else:
            sira = ust + [ust[0] + 12, ust[2] + 12, ust[1] + 12, ust[3]]
            for v in range(8):
                t = tb + v * vurus / 2
                if t < son_an:
                    ekle(muzik, t, piyano(sira[v % len(sira)], vurus * 1.4, 0.6 if v % 2 == 0 else 0.45),
                         0.11 if en == "enerjik" else 0.09, pan=0.25 if v % 2 else -0.25)
            if en == "enerjik":
                for j, m in enumerate(ust[:3]):
                    ekle(muzik, tb, piyano(m, olcu, 0.5), 0.07, pan=(j - 1) * 0.2)
        k += 1


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

    piyano_modu = s.get("stil") == "zarif" or s["muzik"].get("tur") == "piyano"
    if piyano_modu:
        _piyano_muzik(s, muzik, ekle, akorlar, vurus, son_an)
    # tel: her vuruşta akorun bir sesi (yumuşak arpej), ölçü başında tam akor; pad sürekli
    k = 0
    while not piyano_modu and k * olcu < son_an:
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
    for i in range(0 if piyano_modu else int(son_an / adim)):
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
        if piyano_modu:
            ekle(muzik, son_an - 0.5 + j * 0.06, piyano(nota + 12, 2.6, 0.8), 0.16, pan=(j - 2) * 0.18)
        else:
            ekle(muzik, son_an + j * 0.03, tel(nota + 12, 0.9, rng), 0.12, pan=(j - 2) * 0.2)

    def pop():  # yumuşak "blop": aşağı kayan kısa ton
        tt = np.arange(int(0.12 * SR)) / SR
        return np.sin(2 * np.pi * np.cumsum(420 + 600 * np.exp(-tt / 0.02)) / SR) * np.minimum(tt / 0.001, 1) * np.exp(-tt / 0.03)

    uret = {"pop": pop,
            "tik": lambda: fx.tik(rng, 2600, 0.015) * 0.5,
            "hisirti": lambda: fx.whoosh(rng, 0.28, alt=300, ust=1800) * 0.35,
            "parilti": lambda: fx.parilti(rng, 1.0) * 0.6}
    if piyano_modu:   # gürültüsüz: yalnız yumuşak çan (nesne, sevinç); poz ve yazı sessiz
        uret = {"pop": lambda: can(84, 1.4) * 0.5, "parilti": lambda: sum(can(m, 2.0) for m in (84, 88, 91)) * 0.3}
    for an, ad in senaryo.ses_olaylari(s):
        if ad in uret:
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
