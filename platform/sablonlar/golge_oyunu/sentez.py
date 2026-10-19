"""Gölge oyunu şablonunun sesi: ud (Karplus-Strong), darbuka (düyek), nareke, tahta tıkırtısı, zil, perde hışırtısı.

Müzik sahnelerin `muzik` kipinden çıkar: `taksim` serbest ud cümlesi ve dem, `ritim` düyek usulü ile sekizlik ud
ezgisi, `sakin` iki uzun nota ve ardından yumuşak ritim. Son sahnenin ritmi bir oktav yukarıda çalar; video
makamın dağıtılmış akoruyla biter. Efektler `zaman.ses_olaylari` anlarından üretilir. Konuşma, müziğin ve
efektlerin yaklaşık 8 dB üstünde tutulur.
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
MUZIK_ALTI_DB = 8.0
SFX_DB = -9.0


def _lfilter(b, a, x):
    try:
        from scipy.signal import lfilter
        return lfilter(b, a, x)
    except ImportError:  # yavaş ama bağımlılıksız
        b = list(b) + [0.0] * (len(a) - len(b)); a = list(a); y = np.zeros(len(x)); n = len(a)
        for i in range(len(x)):
            acc = sum(b[k] * x[i - k] for k in range(min(len(b), i + 1)))
            acc -= sum(a[k] * y[i - k] for k in range(1, min(n, i + 1)))
            y[i] = acc / a[0]
        return y


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


def zarf(d, a=0.003, dec=None):
    tt = np.arange(int(d * SR)) / SR
    e = np.minimum(tt / a, 1.0)
    return e * (np.exp(-tt / dec) if dec else 1.0), tt


def gurultu(d, seed=0):
    return fx.renkli(int(d * SR), seed)  # pembe: beyaz gürültünün tiz cızırtısı yok


def ud(m, d=1.2, parlak=0.5, seed=0):
    """Karplus-Strong telli çalgı; parlak: mızrap sertliği"""
    f = mtof(m); N = max(2, int(SR / f))
    rng = np.random.default_rng(seed)
    x = np.zeros(int(d * SR)); x[:N] = rng.uniform(-1, 1, N)
    x[:N] = _lfilter([parlak, 1 - parlak], [1], x[:N])
    # y[n] = x[n] + 0.4985 (y[n-N] + y[n-N-1]); N'lik bloklar halinde vektörel (scipy gerekmez)
    y = np.zeros(len(x) + N + 1); y[N + 1:] = x
    for i in range(N + 1, len(y), N):
        j = min(i + N, len(y))
        y[i:j] += 0.4985 * (y[i - N:j - N] + y[i - N - 1:j - N - 1])
    y = y[N + 1:]
    return y * np.minimum(1, (d - np.arange(len(y)) / SR) / 0.05)


def dum():
    e, tt = zarf(0.35, a=0.001, dec=0.12)
    return np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-tt / 0.02)) / SR) * e


def tek(seed=0):
    e, tt = zarf(0.07, a=0.0005, dec=0.012)
    return (_lfilter([1, -1], [1, -0.2], gurultu(0.07, seed)) * 0.5 + np.sin(2 * np.pi * 620 * tt) * 0.6) * e


def zil(d=1.0):
    e, tt = zarf(d, a=0.001, dec=0.18)
    return sum(np.sin(2 * np.pi * f * tt) * w for f, w in ((2350, .5), (3410, .35), (5120, .25), (6730, .15))) * e


def nareke():
    """Karagöz'ün açılış düdüğü: kısa, titreşimli"""
    d = 0.55; tt = np.arange(int(d * SR)) / SR
    f = 1900 + 500 * np.sin(2 * np.pi * 9 * tt) * np.minimum(tt / 0.1, 1) + 300 * (tt / d)
    e = np.minimum(tt / 0.02, 1) * np.clip((d - tt) / 0.1, 0, 1)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * e * 0.5


def tahta(f=900):
    e, tt = zarf(0.06, a=0.0005, dec=0.01)
    return (np.sin(2 * np.pi * f * tt) + _lfilter([1, -1], [1], gurultu(0.06, 3)) * 0.3) * e


def hisirti(d, seed):
    """perde/deri hışırtısı: kısa taneler (türevi alınmış beyaz gürültü tek düze cızırdıyordu)"""
    return fx.hisirti(seed, d, yogunluk=90, parlak=0.8) * 0.45


def ekle(buf, t0, x, gain=1.0, pan=0.0):
    n = len(buf); i = int(t0 * SR)
    if i >= n:
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: n - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414


TAKSIM = [7, 6, 5, 4, 5, 4, 3, 2, 3]                        # makam derecesi (0 = durak)
EZGI = [0, 2, 3, 4, 5, 4, 3, 2, 3, 4, 5, 6, 7, 6, 5, 4]
DUYEK = [(0, "d"), (1.5, "t"), (2, "t"), (3, "d"), (4, "t"), (5.5, "t"), (6, "d"), (7, "t")]  # sekizlik birimde


def muzik(s: dict, n: int) -> np.ndarray:
    m = np.zeros((n, 2))
    sure = s["sure"]
    olcek = zaman.MAKAMLAR[s["muzik"]["makam"]]
    vurus = 60 / s["muzik"]["bpm"]
    olcu = 4 * vurus
    durak = olcek[0] - 12
    son_akor = sure - 0.65
    sahneler = s["sahneler"]
    k_ezgi = 0

    def ritim(bas, son, oktav):
        nonlocal k_ezgi
        tb = bas
        while tb < son - 0.05:
            for off, tur in DUYEK:
                tt = tb + off * vurus / 2
                if tt < son:
                    ekle(m, tt, dum() if tur == "d" else tek(int(tt * 100)), 0.5 if tur == "d" else 0.28, pan=0 if tur == "d" else 0.3)
            for j in range(8):
                tt = tb + j * vurus / 2
                if tt < son:
                    ekle(m, tt, ud(olcek[EZGI[(k_ezgi * 8 + j) % len(EZGI)]] + oktav, 0.5, 0.55, k_ezgi * 8 + j), 0.24, pan=0.2 * math.sin(j))
            ekle(m, tb, ud(durak, min(olcu, son - tb + 0.3), 0.3, 90 + k_ezgi), 0.3, pan=-0.2)
            k_ezgi += 1; tb += olcu

    for i, sh in enumerate(sahneler):
        bas = sh["bas"]
        son = min(sh["_son"], son_akor) - (0.05 if i + 1 < len(sahneler) else 0)
        if son <= bas:
            continue
        oktav = 12 if i == len(sahneler) - 1 and len(sahneler) > 1 else 0
        if sh["muzik"] == "taksim":
            tt = bas + 0.55
            for j, d in enumerate(TAKSIM):
                if tt > son - 0.25:
                    break
                ekle(m, tt, ud(olcek[d], 1.0, 0.6, j + 10 * i), 0.32, pan=0.15)
                tt += (0.35, 0.25, 0.25, 0.45, 0.2, 0.2, 0.2, 0.25, 0.3)[j]
            t_dem = bas + 0.5
            while t_dem < son - 0.3:
                ekle(m, t_dem, ud(durak, 2.0, 0.3, 50 + int(t_dem * 10)), 0.35, pan=-0.2)
                t_dem += 1.5
        elif sh["muzik"] == "sakin":
            ekle(m, bas + 0.05, ud(olcek[4], 1.0, 0.5, 7 + i), 0.3)
            ekle(m, bas + 0.4, ud(olcek[2], 1.0, 0.5, 8 + i), 0.26)
            if son - bas > 1.5:
                ritim(bas + 0.75, son, oktav)
        else:
            ritim(bas, son, oktav)
    for j, d in enumerate((None, 0, 2, 4, 7)):
        mm = durak if d is None else olcek[d]
        ekle(m, son_akor + j * 0.035, ud(mm, 0.65, 0.5, 200 + j), 0.3, pan=(j - 2) * 0.2)
    return m


def sfx(s: dict, n: int) -> np.ndarray:
    x = np.zeros((n, 2))
    for i, (t0, olay, a) in enumerate(zaman.ses_olaylari(s)):
        if olay == "nareke":
            ekle(x, t0, nareke(), 0.7, pan=0.2)
        elif olay == "zil":
            ekle(x, t0, zil(), 0.5)
        elif olay == "tahta":
            ekle(x, t0, tahta(a.get("f", 900)), a.get("kazanc", 0.6), pan=a.get("pan", 0.0))
        elif olay == "hisirti":
            ekle(x, t0, hisirti(a["sure"], 60 + i), a.get("kazanc", 0.4), pan=math.sin(i) * 0.3)
    return x


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
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske, np.ones(k) / k, "same"), 0, 1)  # konuşurken 3 dB ek kısma
    m *= duk[:, None]
    dolu = np.abs(e).sum(1) > 1e-6
    if dolu.any():
        e *= ref * 10 ** (SFX_DB / 20) / rms(e[dolu])
    karisim = vo + m + e
    f = int(0.02 * SR); karisim[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.25 * SR); karisim[-f:] *= np.linspace(1, 0, f)[:, None]
    ortak_miks.kok_yaz(cikti, "efekt", e)  # kurgu bu sahnenin efektlerini buradan alır
    sf.write(str(cikti / "ses.wav"), (karisim / max(1e-9, np.abs(karisim).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
