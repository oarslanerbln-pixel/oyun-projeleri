"""Ekran stillerinin sesi: her stilin kendi müziği ve efektleri, seslendirme ile miks.

- Kalkış tabelası: havalimanı anons çanı (üç nota), sakin elektronik nabız + ped; her kapak dönüşü bir tık
  (takvimdeki anlardan, sütuna göre stereo), dönüşler bitince alçak "oturma" tıkı.
- VHS: synthwave (bas sekizlikleri, yumuşak kare dalga arpej, kick/clap/hat), kasetin "klak" sesiyle başlar,
  her kesikte kısa bant cızırtısı, sonda bant durma (perde düşer). Testere dalga yok (vızıltı gibi duyuluyordu).
- Akış alanı: sinüs pedleri yavaşça kabarıp söner, rüzgâr (yumuşak renkli gürültü, yavaş dalgalanma), sahne
  başlarında cam çan.
Konuşma müziğin ~8 dB üstünde, konuşurken müzik 3 dB daha kısılır.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import sfx as fx  # noqa: E402  (platform/ortak/sfx.py: beyaz gürültüsüz efektler)

SR = 48000
MUZIK_ALTI_DB = 8.0
SFX_DB = {"kalkis-tabelasi": -6.0, "vhs": -9.0, "akis-alani": -12.0}
AKORLAR = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 52, 55, 60], [55, 59, 62, 67]]  # Am F C G


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


def ekle(buf, t0, x, gain=1.0, pan=0.0):
    n = len(buf); i = int(t0 * SR)
    if i >= n or not len(x):
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: n - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414


def topla(a, b, kb=1.0):
    """uzunlukları farklı iki sesi üst üste koyar"""
    out = np.zeros(max(len(a), len(b)))
    out[:len(a)] += a
    out[:len(b)] += b * kb
    return out


def ton(f, d, atak=0.01, sonum=None, harmonik=(1.0,), faz=0.0):
    t = np.arange(int(d * SR)) / SR
    x = sum(a * np.sin(2 * np.pi * f * (k + 1) * t + faz) for k, a in enumerate(harmonik))
    z = np.minimum(1, t / max(atak, 1e-4))
    z *= np.exp(-t / sonum) if sonum else np.minimum(1, (d - t) / 0.08)
    return x * z


def ped(notalar, d, atak=0.8):
    t = np.arange(int(d * SR)) / SR
    x = sum(np.sin(2 * np.pi * mtof(n) * t * (1 + 0.0015 * j)) for j, n in enumerate(notalar)) / len(notalar)
    z = np.minimum(1, t / atak) * np.minimum(1, (d - t) / min(atak, d / 2))
    return x * z


def can(m, d=1.8):
    """yumuşak çan: temel + uyumsuz kısmi"""
    return ton(mtof(m), d, 0.004, 0.6, (1.0, 0.0, 0.25)) + 0.15 * ton(mtof(m) * 2.76, d, 0.002, 0.25)


def _akor(s, t):
    bpm = s["muzik"]["bpm"]
    olcu = 4 * 60 / bpm
    return AKORLAR[int(t / olcu) % 4]


# ---------------------------------------------------------------- kalkış tabelası

def _tabela_muzik(s, n):
    buf = np.zeros((n, 2)); sure = n / SR
    bpm = s["muzik"]["bpm"]; vurus = 60 / bpm
    olcu = 4 * vurus
    for k in range(int(sure / olcu) + 1):
        ak = AKORLAR[k % 4]
        ekle(buf, k * olcu, ped([a - 12 for a in ak], min(olcu + 0.6, sure - k * olcu + 0.01), 0.5), 0.35)
    for k in range(int(sure / (vurus / 2))):
        t = k * vurus / 2
        ak = _akor(s, t)
        nota = ak[(k * 3) % 4] + (12 if k % 8 >= 6 else 0)
        ekle(buf, t, ton(mtof(nota), 0.25, 0.004, 0.09, (1.0, 0.3)), 0.12, 0.4 * math.sin(k))
        if k % 2 == 0:
            ekle(buf, t, fx.kick(k, 0.3, 50, 0.05), 0.35 if k % 4 == 0 else 0.15)
    return buf


def _tabela_sfx(s, n):
    import tabela
    import zaman
    buf = np.zeros((n, 2))
    fmt = s.get("format", "9x16")
    sutun = zaman.IZGARA[fmt][0]
    rng = np.random.default_rng(4)
    # anons çanı: Sol-Mi-Do
    for i, m in enumerate((79, 76, 72)):
        ekle(buf, 0.05 + i * 0.28, can(m, 1.6), 0.5, 0)
    tiklar = [topla(fx.tik(i, 1600 + 260 * i, 0.010), fx.tik(i + 9, 700, 0.018), 0.5) for i in range(8)]
    for h, olaylar in tabela.takvim(s, fmt).items():
        pan = -0.7 + 1.4 * h[2] / max(1, (sutun if h[0] == "ana" else 2 * sutun) - 1)
        kazanc = 0.10 if h[0] == "ana" else 0.06
        for t0, harfler, _ in olaylar:
            m = len(harfler) - 1
            for k in range(m):
                ekle(buf, t0 + k * tabela.DONUS, tiklar[int(rng.integers(8))], kazanc * rng.uniform(0.7, 1.0), pan)
            ekle(buf, t0 + m * tabela.DONUS, fx.tik(int(rng.integers(99)), 520, 0.03), kazanc * 1.4, pan)
    return buf


# ---------------------------------------------------------------- VHS

def _kare_dalga(f, d, sonum=0.25):
    t = np.arange(int(d * SR)) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5, 7))  # yumuşatılmış kare
    return x * np.exp(-t / sonum) * np.minimum(1, t / 0.004)


def _vhs_muzik(s, n):
    buf = np.zeros((n, 2)); sure = n / SR
    vurus = 60 / s["muzik"]["bpm"]
    for k in range(int(sure / (vurus / 2)) + 1):
        t = k * vurus / 2
        ak = _akor(s, t)
        ekle(buf, t, ton(mtof(ak[0] - 24), vurus / 2 * 0.95, 0.005, 0.18, (1.0, 0.5, 0.2)), 0.45)   # bas
        ekle(buf, t, _kare_dalga(mtof(ak[(k % 4)] + 12), 0.3, 0.12), 0.07, -0.4 if k % 2 else 0.4)  # arpej
        ekle(buf, t, fx.hat(k, 0.05), 0.08)
        if k % 2 == 0:
            vk = (k // 2) % 4
            if vk in (0, 2):
                ekle(buf, t, fx.kick(k, 0.4, 46), 0.6)
            else:
                ekle(buf, t, fx.clap(k), 0.3)
    olcu = 4 * vurus
    for k in range(int(sure / olcu) + 1):
        ekle(buf, k * olcu, ped([a for a in AKORLAR[k % 4]], min(olcu, sure - k * olcu + 0.01), 0.3), 0.16)
    # bant titremesi: tüm müziğe çok hafif genlik dalgalanması
    t = np.arange(n) / SR
    buf *= (1 + 0.03 * np.sin(2 * np.pi * 0.7 * t))[:, None]
    return buf


def _vhs_sfx(s, n):
    buf = np.zeros((n, 2))
    sure = n / SR
    ekle(buf, 0.0, topla(fx.tik(1, 900, 0.02), fx.tik(2, 300, 0.04), 0.6), 0.8)        # kaset "klak"
    ekle(buf, 0.0, fx.renkli(int(sure * SR), 3, -4.5) * 0.04, 1.0)                 # alçak bant hışırtısı
    for i, sh in enumerate(s["sahneler"]):
        if i:
            ekle(buf, sh["bas"] - 0.02, fx.bant(fx.renkli(int(0.3 * SR), i, -1.5), 900, 5000) * fx.zarf(int(0.3 * SR), 0.004, 0.12),
                 0.6, 0.0)
            ekle(buf, sh["bas"], fx.whoosh(i, 0.3, False), 0.3)
    return buf


# ---------------------------------------------------------------- akış alanı

def _akis_muzik(s, n):
    buf = np.zeros((n, 2)); sure = n / SR
    olcu = 4 * 60 / s["muzik"]["bpm"]
    for k in range(int(sure / olcu) + 1):
        ak = AKORLAR[k % 4]
        d = min(olcu * 1.4, sure - k * olcu + 0.01)
        ekle(buf, k * olcu, ped(ak, d, 1.2), 0.30, -0.2)
        ekle(buf, k * olcu + olcu / 2, ped([ak[0] + 12, ak[2] + 12], min(olcu, sure - k * olcu), 0.9), 0.10, 0.3)
        for j, m in enumerate((ak[1] + 12, ak[3] + 12, ak[2] + 24)):
            ekle(buf, k * olcu + j * olcu / 3 + 0.2, ton(mtof(m), 1.6, 0.01, 0.7), 0.06, -0.5 + j * 0.5)
    return buf


def _akis_sfx(s, n):
    buf = np.zeros((n, 2))
    t = np.arange(n) / SR
    for kanal, faz in ((0, 0.0), (1, 1.7)):
        r = fx.bant(fx.renkli(n, 5 + kanal, -6.0), 200, 1800)
        buf[:, kanal] += r * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t + faz)) * 0.25
    for i, sh in enumerate(s["sahneler"]):
        ekle(buf, sh["bas"] + 0.15, can(84 + (i % 3) * 3, 2.2), 0.35, -0.3 + 0.3 * (i % 3))
    return buf


MUZIK = {"kalkis-tabelasi": _tabela_muzik, "vhs": _vhs_muzik, "akis-alani": _akis_muzik}
SFX = {"kalkis-tabelasi": _tabela_sfx, "vhs": _vhs_sfx, "akis-alani": _akis_sfx}


def muzik(s, n):
    return MUZIK[s["stil"]](s, n)


def sfx(s, n):
    return SFX[s["stil"]](s, n)


# ---------------------------------------------------------------- miks

def _oku(yol: Path) -> np.ndarray:
    import soundfile as sf
    x, sr = sf.read(str(yol), always_2d=True)
    if sr != SR:  # basit yeniden örnekleme (Piper 22,05 kHz verir)
        idx = np.arange(int(len(x) * SR / sr)) * sr / SR
        x = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(x.shape[1])], axis=1)
    return x if x.shape[1] == 2 else np.repeat(x, 2, axis=1)


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None) -> dict:
    """Seslendirme + müzik + efektler → cikti/ses.wav. Döner: {"seslendirme": [bulunan satır kimlikleri]}"""
    import soundfile as sf
    cikti.mkdir(parents=True, exist_ok=True)
    n = int(SR * s["sure"])
    vo = np.zeros((n, 2)); maske = np.zeros(n); bulunan = []
    for st in s["seslendirme"].get("satirlar", []):
        w = seslendirme / f"{st['id']}.wav" if seslendirme else None
        if not (w and w.exists()):
            continue
        x = _oku(w); i = int(st["t"] * SR); x = x[: max(0, n - i)]
        vo[i:i + len(x)] += x; maske[i:i + len(x)] = 1.0; bulunan.append(st["id"])
    rms = lambda a: math.sqrt(float(np.mean(a ** 2)) + 1e-12)  # noqa: E731
    m = muzik(s, n); e = sfx(s, n)
    ref = rms(vo[maske > 0]) if bulunan else rms(m) * 10 ** (MUZIK_ALTI_DB / 20)
    m *= ref * 10 ** (-MUZIK_ALTI_DB / 20) / rms(m)
    k = int(0.12 * SR)
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske, np.ones(k) / k, "same"), 0, 1)
    m *= duk[:, None]
    dolu = np.abs(e).sum(1) > 1e-6
    if dolu.any():
        e *= ref * 10 ** (SFX_DB[s["stil"]] / 20) / rms(e[dolu])
    karisim = vo + m + e
    f = int(0.02 * SR); karisim[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.25 * SR); karisim[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(str(cikti / "ses.wav"), (karisim / max(1e-9, np.abs(karisim).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
