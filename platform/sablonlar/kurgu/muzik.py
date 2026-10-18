"""Kurgunun sesi: baştan sona tek müzik yatağı + bütün sahnelerin seslendirmesi → miks.

Müzik bir müzikal gibi bölüm bölüm değişir: her sahnenin `enerji`si (sakin, orta, enerjik) o bölümde
hangi katmanların çaldığını seçer. Akorlar ve tempo bütün video boyunca kesintisiz sürer; enerji
yükselmeden önceki ölçüde yükselen bir dalga, enerjik bölümün girişinde alçak bir vuruş çalar.

    sakin    pad + çeyrek arpej
    orta     + 1. ve 3. vuruşta davul, offbeat hi-hat, uzun bas
    enerjik  + her vuruşta davul, clap, sekizlik bas, yan zincir pompası

Konuşma sırasında müzik kısılır; konuşma müziğin `muzik.ses_ustu_db` (varsayılan 8 dB) üstünde kalır.
Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

SR = 48000
ACIK_DB = 6.0  # konuşma yokken müzik bu kadar yükselir


def _ortalama(x: np.ndarray, pencere: int) -> np.ndarray:
    """Hareketli ortalama (kümülatif toplamla; uzun seste de hızlı)."""
    pencere = max(1, pencere)
    c = np.cumsum(np.concatenate([np.zeros(pencere), x]))
    y = (c[pencere:] - c[:-pencere]) / pencere
    return np.roll(y, -(pencere // 2))


def muzik_yatagi(sure: float, bolumler: list[dict], bpm: float, akorlar: list[list[int]], tohum: int = 11) -> np.ndarray:
    n = int(SR * sure)
    m = np.zeros((n, 2))
    rng = np.random.default_rng(tohum)
    vurus = 60 / bpm
    olcu = 4 * vurus
    adim = vurus / 2
    son_an = max(0.0, sure - 1.6)  # son ölçü: final akoru

    def ekle(t0, x, kazanc=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= n or i < 0:
            return
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        m[i:i + len(x), 0] += x * kazanc * l * 1.414
        m[i:i + len(x), 1] += x * kazanc * r * 1.414

    def zarf(d, a=0.003, dec=None):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / a, 1.0)
        return e * (np.exp(-tt / dec) if dec else 1.0), tt

    def mtof(nota):
        return 440 * 2 ** ((nota - 69) / 12)

    def kick():
        e, tt = zarf(0.4, dec=0.15)
        f = 46 + 100 * np.exp(-tt / 0.03)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * e

    def clap():
        e, tt = zarf(0.22, dec=0.06)
        x = rng.standard_normal(len(tt))
        return np.diff(np.concatenate([[0], x])) * e * 0.5

    def hat(d=0.05):
        e, tt = zarf(d, dec=d / 3)
        x = rng.standard_normal(len(tt))
        return np.diff(np.concatenate([[0, 0], x]), 2) * e * 0.1

    def pluck(nota, parlak):
        e, tt = zarf(0.5, a=0.002, dec=0.12 + 0.06 * parlak)
        ph = 2 * np.pi * mtof(nota) * tt
        ust = 3 + 2 * parlak  # bant sınırlı testere: parlaklık = harmonik sayısı
        return sum(np.sin(h * ph) / h ** 1.3 for h in range(1, ust + 1)) * e * 0.7

    def bas(nota, d):
        e, tt = zarf(d, a=0.005, dec=max(0.12, d * 0.6))
        ph = 2 * np.pi * mtof(nota) * tt
        return (np.sin(ph) + 0.3 * np.sin(2 * ph)) * e * np.minimum((d - tt) / 0.02, 1)

    def pad(notalar, d):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / 0.4, 1) * np.minimum((d - tt) / 0.4, 1)
        x = sum(np.sin(2 * np.pi * mtof(nt) * (1 + det) * tt) + 0.2 * np.sin(4 * np.pi * mtof(nt) * tt)
                for nt in notalar for det in (-0.003, 0.003))
        return x * e / (len(notalar) * 2)

    def dalga(d):  # enerji yükselmeden önce: yükselen ton + açılan hışırtı
        tt = np.arange(int(d * SR)) / SR
        p = tt / d
        ton = np.sin(2 * np.pi * np.cumsum(180 * 2 ** (2 * p)) / SR)
        hisirti = np.diff(np.concatenate([[0], rng.standard_normal(len(tt))]))
        return (ton * 0.35 + hisirti * 0.25) * p ** 2.2

    def vurgu():  # enerjik bölüm girişi: alçak, yumuşak vuruş
        e, tt = zarf(1.2, a=0.004, dec=0.4)
        return np.sin(2 * np.pi * np.cumsum(55 * np.exp(-tt / 0.5) + 30) / SR) * e

    def seviye(t):
        s = bolumler[0]["enerji"]
        for b in bolumler:
            if t >= b["bas"] - 1e-6:
                s = b["enerji"]
        return s

    def akor(t):
        return akorlar[int(t / olcu) % len(akorlar)]

    arp = [0, 1, 2, 3, 2, 1, 3, 2]
    for i in range(int(son_an / adim) + 1):
        tb = i * adim
        if tb >= son_an:
            break
        sv, nt = seviye(tb), akor(tb)
        vurusta = i % 2 == 0
        if sv == 0 and not vurusta:
            pass
        else:
            ekle(tb, pluck(nt[arp[i % 8] % len(nt)] + 12, sv), (0.10, 0.12, 0.13)[sv], pan=-0.35 if i % 2 else 0.35)
        if sv >= 1:
            if (sv == 2 and vurusta) or i % 8 in (0, 4):
                ekle(tb, kick(), 0.85)
            if not vurusta:
                ekle(tb, hat(), 0.8, pan=0.25)
        if sv == 2:
            if i % 8 in (2, 6):
                ekle(tb, clap(), 0.6, pan=-0.1)
            if vurusta:
                ekle(tb, hat(0.025), 0.45, pan=-0.25)
            if not vurusta:
                ekle(tb, bas(min(nt) - 12, adim * 0.9), 0.30)
        elif sv == 1 and i % 8 == 0:
            ekle(tb, bas(min(nt) - 12, min(olcu, son_an - tb)), 0.26)
    k = 0
    while k * olcu < son_an:
        t0 = k * olcu
        ekle(t0, pad(akorlar[k % len(akorlar)], min(olcu + 0.4, son_an - t0 + 0.4)), (0.20, 0.16, 0.14)[seviye(t0)])
        k += 1
    for onceki, b in zip(bolumler, bolumler[1:]):
        if b["enerji"] > onceki["enerji"]:
            d = min(olcu, 2.0, b["bas"] - onceki["bas"])
            ekle(b["bas"] - d, dalga(d), 0.22)
        if b["enerji"] == 2 and onceki["enerji"] < 2:
            ekle(b["bas"], vurgu(), 0.45)
    kok = akorlar[0]
    ekle(son_an, pad([min(kok) - 12, *kok, kok[1] + 12], sure - son_an), 0.30)
    if seviye(son_an) >= 1:
        ekle(son_an, kick(), 0.8)

    pompa = np.ones(n)  # enerjik bölümlerde her vuruşta yan zincir
    for i in range(int(son_an / vurus)):
        tb = i * vurus
        if seviye(tb) == 2:
            a = int(tb * SR)
            tt = np.arange(min(int(0.22 * SR), n - a)) / SR
            pompa[a:a + len(tt)] = np.minimum(pompa[a:a + len(tt)], 1 - 0.4 * np.exp(-tt / 0.07))
    m *= pompa[:, None]
    # iki yankı (noktalı sekizlik): kuru sentezi odaya koyar
    for gec, kaz, yon in ((0.75 * vurus, 0.22, 1), (1.5 * vurus, 0.1, 0)):
        g = int(gec * SR)
        m[g:, 0] += m[:-g, yon] * kaz
        m[g:, 1] += m[:-g, 1 - yon] * kaz
    sonum = np.clip((sure - np.arange(n) / SR) / 0.6, 0, 1)
    return m * sonum[:, None]


def miksle(k: dict, bolumler: list[dict], satirlar: list[dict], ses_klasoru: Path, hedef: Path) -> dict:
    import soundfile as sf
    sure = k["sure"]
    n = int(SR * sure)
    muzik = muzik_yatagi(sure, bolumler, k["muzik"]["bpm"], k["muzik"]["akorlar"])
    ses = np.zeros(n)
    bulunan = []
    for x in satirlar:
        yol = Path(ses_klasoru) / f"{x['id']}.wav"
        if not yol.exists():
            continue
        y, sr = sf.read(str(yol))
        if y.ndim > 1:
            y = y.mean(1)
        if sr != SR:
            y = np.interp(np.arange(int(len(y) * SR / sr)) * sr / SR, np.arange(len(y)), y)
        i = int(x["t"] * SR)
        ses[i:i + len(y)] += y[: max(0, n - i)]
        bulunan.append(x["id"])
    konusma = _ortalama((_ortalama(np.abs(ses), int(0.05 * SR)) > 0.01).astype(float), int(0.3 * SR))
    konusma = np.clip(konusma * 1.5, 0, 1)
    m_rms = float(np.sqrt(np.mean(muzik ** 2)) + 1e-9)
    ustu = k["muzik"].get("ses_ustu_db", 8.0)
    aktif = konusma > 0.5
    if aktif.any():
        v_rms = float(np.sqrt(np.mean(ses[aktif] ** 2)) + 1e-9)
        hedef_m = v_rms * 10 ** ((ACIK_DB - ustu) / 20)  # konuşma yokken; konuşurken ACIK_DB kadar iner
    else:
        hedef_m = 10 ** (-18 / 20)
    kazanc = (hedef_m / m_rms) * (1 - (1 - 10 ** (-ACIK_DB / 20)) * konusma)
    miks = muzik * kazanc[:, None] + ses[:, None]
    tepe = float(np.abs(miks).max()) or 1.0
    hedef.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(hedef), (miks / tepe * 0.95).astype(np.float32), SR)
    olcum = None
    if aktif.any():
        mk = muzik[aktif] * kazanc[aktif, None]
        olcum = 20 * math.log10(v_rms / (float(np.sqrt(np.mean(mk ** 2))) + 1e-9))
    return {"seslendirme": bulunan, "konusma_ustu_db": olcum}
