"""Risograf şablonunun sesi: lo-fi sentez müzik + riso makinesi efektleri + seslendirme → miks.

Müzik dinamiği: girişte yalnız FM elektrikli piyano ve shaker; `muzik.yukselis` anında yumuşak davul ve
sub bas girer, sayaçtan önce çan arpeji yükselir; `muzik.sakin` anında davul susar, uzun bir akor kalır;
`muzik.final` anında davul döner ve çan arpejiyle parlak bir akorla kapanır. `muzik.akorlar` dört bölümün
(giriş, yükseliş, sakin, final) akor listeleridir; bölüm içinde iki vuruşta bir sıradaki akor çalar.
Sayfa geçişlerinde riso tamburu (gümleme + tık + kâğıt hışırtısı), büyük baskılarda tok damga ve çan.
Konuşma sırasında müzik sesin ~8 dB altında durur. Gerekenler: numpy, scipy, soundfile.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.signal import butter, lfilter

import zaman

SR = 48000


def mtof(m: float) -> float:
    return 440 * 2 ** ((m - 69) / 12)


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None, muzik_alti_db: float = 8.0) -> dict:
    import soundfile as sf
    sure = s["sure"]; n = int(SR * sure)
    rng = np.random.default_rng(13)
    muzik = np.zeros((n, 2)); sfx = np.zeros((n, 2))
    m = s["muzik"]; V = 60 / m["bpm"]
    son_an = sure - 0.65
    bolumler = [(0.0, m["yukselis"]), (m["yukselis"], m["sakin"]), (m["sakin"], m["final"]), (m["final"], son_an)]

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

    def gurultu(d): return rng.standard_normal(int(d * SR))
    def bant(x, a, b): return lfilter(*butter(2, [a / (SR / 2), b / (SR / 2)], "band"), x)
    def yuksek(x, f): return lfilter(*butter(2, f / (SR / 2), "high"), x)
    def alcak(x, f): return lfilter(*butter(1, f / (SR / 2)), x)

    # --- çalgılar ---
    def epiyano(nota, d=1.6):
        f = mtof(nota); tt = np.arange(int(d * SR)) / SR
        y = np.sin(2 * np.pi * f * tt + 1.8 * np.exp(-tt / 0.25) * np.sin(2 * np.pi * f * tt)) * np.exp(-tt / 1.1)
        y += 0.25 * np.sin(2 * np.pi * f * 14 * tt) * np.exp(-tt / 0.05)  # tını vuruşu
        return y * np.minimum(1, tt / 0.004) * np.clip((d - tt) / 0.08, 0, 1)

    def akor_cal(t0, notalar, d, g, arp=0.018):
        for j, x in enumerate(notalar):
            ekle(muzik, t0 + j * arp, epiyano(x, d), g / len(notalar) * 2.2, pan=(j - len(notalar) / 2) * 0.12)

    def kick():
        e, tt = zarf(0.35, a=0.002, dec=0.14)
        return np.sin(2 * np.pi * np.cumsum(48 + 60 * np.exp(-tt / 0.03)) / SR) * e

    def firca():
        e, _ = zarf(0.25, a=0.004, dec=0.07)
        return bant(gurultu(0.25), 900, 5000) * e

    def shaker():
        e, _ = zarf(0.06, a=0.006, dec=0.018)
        return yuksek(gurultu(0.06), 6000) * e

    def sub(nota, d):
        tt = np.arange(int(d * SR)) / SR
        return np.sin(2 * np.pi * mtof(nota) * tt) * np.minimum(1, tt / 0.01) * np.clip((d - tt) / 0.08, 0, 1)

    def can(nota, d=1.4):
        tt = np.arange(int(d * SR)) / SR; f = mtof(nota)
        return sum(np.sin(2 * np.pi * f * r * tt) * w * np.exp(-tt / (0.6 / r)) for r, w in ((1, 1), (2.76, .4), (5.4, .2)))

    def davul(bas_t, son_t, yogun=1.0):
        b = bas_t
        while b < son_t - 1e-6:
            for k in range(16):
                tt = b + k * V / 4
                if tt >= son_t: break
                if k in (0, 7, 10): ekle(muzik, tt, kick(), 0.5 * yogun)
                if k in (4, 12): ekle(muzik, tt, firca(), 0.22 * yogun, pan=0.1)
                ekle(muzik, tt + (0.02 if k % 2 else 0), shaker(), (0.07 if k % 2 else 0.1) * yogun, pan=0.4)
            b += 4 * V

    # akorlar: her bölümde iki vuruşta bir (sakin bölümde tek uzun akor)
    for bi, (b0, b1) in enumerate(bolumler):
        if b1 <= b0: continue
        liste = m["akorlar"][bi % len(m["akorlar"])]
        adim = (b1 - b0) if bi == 2 else 2 * V
        k = 0; tb = b0 + 0.05 * (bi == 0)
        while tb < b1 - 0.2:
            a = liste[k % len(liste)]
            d = min(adim, b1 - tb) + 0.1
            akor_cal(tb, a if k % 2 == 0 else a[1:] + [a[0] + 12], d, 0.5 if bi != 2 else 0.42)
            if bi != 0 or k == 0:
                ekle(muzik, tb, sub(min(a) - 12, d - 0.05), 0.38 if bi else 0.35)
            k += 1; tb += adim
    b0, b1 = bolumler[0]
    for k in range(int((b1 - b0 - 1.5) / (V / 4))):  # girişin ikinci yarısında shaker
        ekle(muzik, 1.5 + k * V / 4, shaker(), 0.06, pan=0.4)
    davul(*bolumler[1], 1.0)
    davul(m["final"], son_an - 0.5, 0.9)
    for d in zaman.damgalar(s):  # büyük baskılarda çan
        ekle(muzik, d, can(84, 1.2), 0.18)
    for sy in s["sayfalar"]:  # sayaçtan önce yükselen çan arpeji
        for o in sy["ogeler"]:
            if o["tur"] == "sayac":
                for j, x in enumerate((64, 67, 69, 71, 72, 74, 76, 79)):
                    ekle(muzik, o["bitis_t"] - 0.9 + j * 0.11, can(x, 0.5), 0.10 + j * 0.012, pan=-0.3 + j * 0.08)
                ekle(muzik, o["bitis_t"], can(91, 1.2), 0.12)
    # final: çan arpeji + açık akor
    for j, x in enumerate((72, 76, 79, 84)):
        ekle(muzik, son_an + j * 0.06, can(x, 0.9), 0.14, pan=(j - 1.5) * 0.25)
    kok = m["akorlar"][-1][0]
    akor_cal(son_an, [min(kok) - 12] + sorted(kok)[1:], 0.65, 0.5, arp=0.03)

    # --- efektler ---
    def makine():
        """riso tamburu: alçak gümleme + mekanik tık + kâğıt hışırtısı"""
        d = 0.6; e, tt = zarf(d, a=0.002, dec=0.09)
        gum = np.sin(2 * np.pi * np.cumsum(70 + 30 * np.exp(-tt / 0.05)) / SR) * e
        tik = np.zeros_like(tt); i = int(0.11 * SR)
        te, ttt = zarf(0.05, a=0.0005, dec=0.008)
        tik[i:i + len(te)] = (np.sin(2 * np.pi * 1800 * ttt) * 0.6 + gurultu(0.05)[:len(te)] * 0.4) * te
        hs = bant(gurultu(d), 1500, 7000) * np.sin(np.pi * tt / d) ** 2 * 0.9
        return gum * 0.9 + tik + hs

    def damga():
        e, tt = zarf(0.2, a=0.001, dec=0.04)
        return (np.sin(2 * np.pi * 110 * tt) + alcak(gurultu(0.2), 2500) * 1.5) * e

    def pop(f=700):
        e, tt = zarf(0.1, a=0.001, dec=0.035)
        return np.sin(2 * np.pi * np.cumsum(f + 500 * np.exp(-tt / 0.02)) / SR) * e

    uret = {"makine": lambda e: makine(), "damga": lambda e: damga(), "pop": lambda e: pop(e.get("f", 700))}
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
        sfx *= ref * 10 ** (-7 / 20) / max(rms(sfx[np.abs(sfx).sum(1) > 1e-6]), 1e-9)
    miks = vo[:, None] + muzik + sfx
    f = int(0.02 * SR); miks[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.25 * SR); miks[-f:] *= np.linspace(1, 0, f)[:, None]
    cikti.mkdir(parents=True, exist_ok=True)
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
