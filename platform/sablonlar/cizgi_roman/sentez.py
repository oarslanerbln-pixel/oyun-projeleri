"""Çizgi roman şablonunun sesi: funk/pop-rock sentez müzik + çizgi roman efektleri + seslendirme → miks.

Müzik dinamiği: ilk vuruşa kadar gerilim (hihat + yükselen bas), sonra hafif groove; `muzik.yukselis`
anında tam davul ve bas; `muzik.sakin` anında yalnız tıkırtı ve uzun bas (bir sonraki vuruşa kadar);
`muzik.final` anında tam groove ve parlak bakır kapanışı. Her vuruşta (zaman.vuruslar: çarpan yazılar,
patlamalar, panel darbeleri) bakır üflemeli akor ve kick çalar, sayaçlı patlamadan önce bakır yükselir.
Konuşma sırasında müzik sesin ~8 dB altında durur. Gerekenler: numpy, scipy, soundfile.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import sfx as fx  # noqa: E402  (platform/ortak/sfx.py: beyaz gürültüsüz efektler)
from scipy.signal import butter, lfilter

import zaman

SR = 48000


def mtof(m: float) -> float:
    return 440 * 2 ** ((m - 69) / 12)


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None, muzik_alti_db: float = 8.0) -> dict:
    import soundfile as sf
    sure = s["sure"]; n = int(SR * sure)
    rng = np.random.default_rng(11)
    muzik = np.zeros((n, 2)); sfx = np.zeros((n, 2))
    m = s["muzik"]; V = 60 / m["bpm"]; olcu = 4 * V
    yuk, sak, fin = m["yukselis"], m["sakin"], m["final"]
    son_an = sure - 0.68
    vur = zaman.vuruslar(s)

    def ekle(buf, t0, x, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= n or i < 0: return
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * gain * l * 1.414
        buf[i:i + len(x), 1] += x * gain * r * 1.414

    def zarf(d, a=0.003, dec=None):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / a, 1.0)
        return e * (np.exp(-tt / dec) if dec else 1.0), tt

    def gurultu(d): return fx.renkli(int(d * SR), rng)  # pembe: beyaz gürültünün tiz cızırtısı yok
    def bant(x, a, b): return lfilter(*butter(2, [a / (SR / 2), b / (SR / 2)], "band"), x)
    def yuksek(x, f): return lfilter(*butter(2, f / (SR / 2), "high"), x)
    def alcak(x, f): return lfilter(*butter(1, f / (SR / 2)), x)

    # --- çalgılar ---
    def kick():
        e, tt = zarf(0.32, a=0.001, dec=0.11)
        return np.sin(2 * np.pi * np.cumsum(52 + 110 * np.exp(-tt / 0.025)) / SR) * e

    def trampet():
        e, tt = zarf(0.22, a=0.001, dec=0.06)
        return (bant(gurultu(0.22), 1500, 9000) * 1.6 + np.sin(2 * np.pi * 190 * tt) * 0.6 * np.exp(-tt / 0.03)) * e

    def hihat(d=0.05): return fx.hat(rng, d) * 0.45

    def zil(): return fx.zil(rng, 1.6) * 0.45

    def testere(f, d, k=3, ayar=0.12):
        tt = np.arange(int(d * SR)) / SR; y = np.zeros_like(tt)
        for j in range(k):
            ff = f * 2 ** ((j - (k - 1) / 2) * ayar / 12)
            y += 2 * ((tt * ff + j * 0.31) % 1) - 1
        return y / k, tt

    def bas(nota, d):
        y, tt = testere(mtof(nota), d, 1)
        y = alcak(y, 500) * 1.4 + np.sin(2 * np.pi * mtof(nota) * tt) * 0.7
        return y * np.minimum(1, tt / 0.004) * np.clip((d - tt) / 0.03, 0, 1)

    def bakir(akor, d, parlak=1.0):
        """bakır üflemeli vuruş: ayarsız testereler, kapanan süzgeç (bloklar halinde)"""
        out = sum(testere(mtof(x), d)[0] for x in akor)
        tt = np.arange(len(out)) / SR
        kes = 600 + 3400 * parlak * np.exp(-tt / 0.12)
        y = np.empty_like(out); z = 0.0
        for i in range(0, len(out), 256):
            a = math.exp(-2 * math.pi * kes[i] / SR)
            seg, _ = lfilter([1 - a], [1, -a], out[i:i + 256], zi=[z * a])
            y[i:i + 256] = seg; z = seg[-1]
        return y * np.minimum(1, tt / 0.012) * np.clip((d - tt) / 0.06, 0, 1) / len(akor)

    akorlar = m["akorlar"]
    def akor(tb): return akorlar[int(tb / olcu) % len(akorlar)]

    def groove(bas_t, son_t, yogun=1.0):
        tb = bas_t
        while tb < son_t - 1e-6:
            for k in range(8):
                tt = tb + k * V / 2
                if tt >= son_t: break
                if k in (0, 3, 4) and yogun >= 0.5: ekle(muzik, tt, kick(), 0.55)
                if k in (2, 6): ekle(muzik, tt, trampet(), 0.32 * yogun, pan=0.05)
                ekle(muzik, tt, hihat(), 0.14 * yogun, pan=0.35)
                kalip = [0, 0, 12, 0, 7, 0, 10, 12]
                ekle(muzik, tt, bas(min(akor(tt)) - 24 + kalip[k], V / 2 * 0.9), 0.36 * (0.7 + 0.3 * yogun))
            tb += olcu

    ilk = vur[0] if vur else yuk
    # giriş gerilimi: hızlanan hihat + yükselen bas notaları
    for i in range(int(ilk / (V / 2))):
        ekle(muzik, i * V / 2, hihat(0.04), 0.18 + 0.1 * i / max(1, int(ilk / (V / 2))), pan=0.3)
    kok = min(akorlar[0]) - 24
    for j, d in enumerate((0, 2, 4)):
        if 0.35 + j * 0.33 < ilk: ekle(muzik, 0.35 + j * 0.33, bas(kok + d, 0.28), 0.4)
    groove(ilk + 0.15, yuk, 0.7)
    groove(yuk, sak, 1.0)
    sakin_vurus = next((v for v in vur if sak <= v < fin), None)
    for k in range(int(((sakin_vurus or fin) - sak) / (V / 2))):
        ekle(muzik, sak + k * V / 2, hihat(0.03), 0.08, pan=-0.3)
    ekle(muzik, sak + 0.05, bas(min(akor(sak)) - 24, 0.7), 0.35)
    if sakin_vurus: groove(sakin_vurus + 0.15, fin, 0.8)
    groove(fin, son_an - 0.3, 1.0)
    for v in vur:  # her vuruşta bakır akoru + kick + zil
        a = akor(v)
        ekle(muzik, v, bakir([x + 0 for x in a] + [a[0] + 12], 0.5), 0.5); ekle(muzik, v, kick(), 0.6); ekle(muzik, v, zil(), 0.22)
    for sh in s["sahneler"]:  # sayaçlı patlamadan önce bakır yükselir
        for p in sh["paneller"]:
            for o in p["ogeler"]:
                if o["tur"] == "patlama" and "sayac" in o:
                    v = zaman.vurus_ani(o); a = akor(v)
                    for j in range(4):
                        ekle(muzik, v - 0.6 + j * 0.15, bakir([a[2] + j * 2, a[3] + j * 2], 0.13, 0.7), 0.28)
    # final: üç basamaklı bakır yükselişi ve tok son vuruş
    a = akorlar[0]
    for j, d in enumerate((0, 2, 4)):
        ekle(muzik, son_an - 0.32 + j * 0.16, bakir([a[0] + 12 + d, a[1] + 12 + d, a[2] + 12 + d], 0.14 if j < 2 else 0.9), 0.4)
    ekle(muzik, son_an, kick(), 0.6); ekle(muzik, son_an, zil(), 0.35); ekle(muzik, son_an, bas(min(a) - 24, 0.6), 0.45)

    # --- efektler ---
    def vuus(d=0.45, yukari=False):
        g = gurultu(d); f = np.linspace(700, 4200, len(g)) if yukari else np.linspace(4200, 700, len(g))
        y = np.empty_like(g)
        for i in range(0, len(g), 256):
            y[i:i + 256] = bant(g[i:i + 256], max(60, f[i] * 0.7), min(SR / 2 - 100, f[i] * 1.4))
        return y * np.sin(np.pi * np.arange(len(g)) / len(g)) ** 2

    def darbe():
        e, tt = zarf(0.4, a=0.001, dec=0.12)
        return (np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-tt / 0.03)) / SR) * 1.2 + alcak(gurultu(0.4), 1800) * 0.7) * e

    def pop(f=900):
        e, tt = zarf(0.12, a=0.001, dec=0.04)
        return np.sin(2 * np.pi * np.cumsum(f + 900 * np.exp(-tt / 0.02)) / SR) * e

    def tik(f=2400):
        e, tt = zarf(0.03, a=0.0005, dec=0.006)
        return np.sin(2 * np.pi * f * tt) * e

    def yaprak():
        return yuksek(gurultu(0.07), 2500) * np.exp(-np.arange(int(0.07 * SR)) / SR / 0.02)

    uret = {"kayma": lambda e: vuus(0.55), "darbe": lambda e: darbe(), "pop": lambda e: pop(e.get("f", 900)),
            "tik": lambda e: tik(2000 + 60 * e.get("k", 0)), "yaprak": lambda e: yaprak(),
            "vuus": lambda e: vuus(min(0.6, e.get("sure", 0.3)), e.get("yukari", True))}
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
    if np.any(sfx):
        sfx *= ref * 10 ** (-6 / 20) / max(rms(sfx[np.abs(sfx).sum(1) > 1e-6]), 1e-9)
    miks = vo[:, None] + muzik + sfx
    f = int(0.02 * SR); miks[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.25 * SR); miks[-f:] *= np.linspace(1, 0, f)[:, None]
    cikti.mkdir(parents=True, exist_ok=True)
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
