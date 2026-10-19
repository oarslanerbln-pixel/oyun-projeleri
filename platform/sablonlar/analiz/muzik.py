"""Analiz şablonunun sesi: haber müziği yatağı + grafik efektleri + seslendirme → miks.

Müzik `muzik.bpm` hızında, `muzik.akorlar` dizisini ölçü başına bir akor çalar. Katmanlar sahnenin
`enerji` değerine (0–1) göre açılır: pad hep çalar; nabız (16'lık arpej) 0,25, bas 0,35, hi-hat 0,4,
kick 0,5, trampet 0,75 üstünde girer. Böylece sakin açılış, gerilen piyasa/sokak bölümü ve sakin
kapanış aynı senaryodan çıkar. Efektler (geçiş, sayaç tıkı, grafik belirme sesi) çizimle aynı
anlardan (`cizim.oge_anlari`) hesaplanır. Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import sfx as fx  # noqa: E402  (platform/ortak/sfx.py: beyaz gürültüsüz efektler)

import cizim

SR = 48000
VARSAYILAN_ENERJI = {"baslik": 0.3, "cubuk": 0.55, "cizgi": 0.6, "sayac": 0.8, "harita": 0.9, "karsilastirma": 0.85,
                     "zaman": 0.5, "alinti": 0.35, "kapanis": 0.2}


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


def kutu_suzgec(x, n):
    """kayan ortalama (alçak geçiren); n örnek"""
    n = max(1, int(n))
    c = np.cumsum(np.concatenate([[0.0], x]))
    y = (c[n:] - c[:-n]) / n
    return np.concatenate([y, np.full(n - 1, y[-1] if len(y) else 0.0)])


def enerji_egrisi(s: dict, n: int) -> np.ndarray:
    e = np.zeros(n)
    for sahne, bas, son in cizim.sahne_bitisleri(s):
        e[int(bas * SR):int(son * SR)] = sahne.get("enerji", VARSAYILAN_ENERJI.get(sahne["tur"], 0.5))
    return e


def efekt_anlari(s: dict) -> list[tuple[float, str, dict]]:
    """(an, tür, ek) — çizimdeki giriş anlarıyla aynı hesap"""
    olay = []
    for i, (sahne, bas, son) in enumerate(cizim.sahne_bitisleri(s)):
        tur = sahne["tur"]
        if i:
            olay.append((bas - 0.22, "whoosh", {}))
        if tur == "baslik":
            olay.append((bas + 0.45, "vurus", {}))
        if tur == "cubuk":
            for k, an in enumerate(cizim.oge_anlari(sahne, sahne["cubuklar"], 0.9, 0.5)):
                olay.append((an, "blip", {"nota": 74 + 2 * k}))
        if tur == "cizgi":
            t0, d = sahne.get("cizim_t", bas + 0.9), sahne.get("cizim_sure", 2.6)
            n = len(sahne["noktalar"]) - 1
            for k in range(n + 1):
                olay.append((t0 + d * k / max(1, n), "blip", {"nota": 74 + 3 * k}))
        if tur == "sayac":
            for k, an in zip(sahne["kartlar"], cizim.oge_anlari(sahne, sahne["kartlar"], 0.9, 0.9)):
                olay.append((an, "sayac", {"sure": k.get("sure", 1.4)}))
        if tur == "karsilastirma":
            for an in cizim.oge_anlari(sahne, [sahne["sol"], sahne["sag"]], 0.9, 1.0):
                olay.append((an, "sayac", {"sure": 1.4}))
        if tur == "harita":
            for an in cizim.oge_anlari(sahne, sahne.get("noktalar", []), 2.0, 0.6):
                olay.append((an, "blip", {"nota": 81}))
            if sahne.get("kpi"):
                olay.append((sahne["kpi"].get("t", bas + 1.2), "sayac", {"sure": 1.3}))
        if tur == "zaman":
            for k, an in enumerate(cizim.oge_anlari(sahne, sahne["olaylar"], 0.8, 0.55)):
                olay.append((an, "blip", {"nota": 72 + 2 * k}))
    return olay


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None) -> dict:
    import soundfile as sf
    sure = s["sure"]
    n = int(SR * sure)
    rng = np.random.default_rng(11)
    muzik = np.zeros((n, 2))
    sfx = np.zeros((n, 2))

    def ekle(buf, t0, x, kazanc=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= n or i + len(x) <= 0:
            return
        if i < 0:
            x, i = x[-i:], 0
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * kazanc * l * 1.414
        buf[i:i + len(x), 1] += x * kazanc * r * 1.414

    def zarf(d, a=0.004, dec=None, rel=0.02):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / a, 1.0) * np.clip((d - tt) / rel, 0, 1)
        return e * (np.exp(-tt / dec) if dec else 1.0), tt

    def pad(notalar, d):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / 0.6, 1) * np.clip((d - tt) / 0.5, 0, 1)
        x = sum(np.sin(2 * np.pi * mtof(m) * (1 + det) * tt) + 0.18 * np.sin(4 * np.pi * mtof(m) * tt)
                for m in notalar for det in (-0.003, 0.003))
        return x * e / (len(notalar) * 2)

    def pluck(m, d=0.22):
        e, tt = zarf(d, a=0.002, dec=0.07)
        ph = 2 * np.pi * mtof(m) * tt
        return (np.sin(ph) + 0.35 * np.sin(2 * ph) * np.exp(-tt / 0.03) + 0.12 * np.sin(3 * ph)) * e

    def bas_(m, d):
        e, tt = zarf(d, a=0.005, dec=0.3, rel=0.03)
        ph = 2 * np.pi * mtof(m) * tt
        return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * e

    def kick():
        e, tt = zarf(0.38, a=0.001, dec=0.13)
        f = 46 + 95 * np.exp(-tt / 0.03)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * e

    def hat(d=0.05): return fx.hat(rng, d) * 0.25

    def trampet():
        e, tt = zarf(0.22, a=0.001, dec=0.06)
        gur = fx.bant(fx.renkli(len(tt), rng), 1200, 7000) * 0.5
        ton = np.sin(2 * np.pi * 190 * tt) * np.exp(-tt / 0.03)
        return (gur + ton) * e * 0.6

    # --- müzik ---
    bpm = s["muzik"].get("bpm", 96)
    vurus = 60 / bpm
    olcu = 4 * vurus
    akorlar = s["muzik"]["akorlar"]
    enerji = enerji_egrisi(s, n)
    son_an = sure - 2.2

    def e_at(tb): return enerji[min(n - 1, int(tb * SR))]

    k = 0
    while k * olcu < son_an:
        tb = k * olcu
        ekle(muzik, tb, pad(akorlar[k % len(akorlar)], min(olcu + 0.6, son_an - tb + 0.6)), 0.20)
        k += 1
    adim = vurus / 4
    arp = [0, 2, 1, 3, 2, 1, 3, 2]
    for i in range(int(son_an / adim)):
        tb = i * adim
        e = e_at(tb)
        notalar = akorlar[int(tb / olcu) % len(akorlar)]
        if e >= 0.25:
            ekle(muzik, tb, pluck(notalar[arp[i % 8] % len(notalar)] + 12), 0.06 + 0.06 * e, pan=-0.35 if i % 2 else 0.35)
        if i % 2 == 0 and e >= 0.35 and i % 8 in (0, 6):
            ekle(muzik, tb, bas_(min(notalar) - 12, adim * 2.6), 0.30)
        if i % 4 == 2 and e >= 0.4:
            ekle(muzik, tb, hat(), 0.9, pan=0.25)
        if i % 4 == 0 and e >= 0.5 and (e >= 0.8 or i % 8 == 0):
            ekle(muzik, tb, kick(), 0.75)
        if i % 8 == 4 and e >= 0.75:
            ekle(muzik, tb, trampet(), 0.55, pan=-0.05)
    kok = akorlar[0]
    ekle(muzik, son_an, pad([min(kok) - 12] + list(kok), 2.2), 0.28)
    ekle(muzik, son_an, bas_(min(kok) - 12, 1.8), 0.3)

    # --- efektler ---
    def whoosh(d=0.5): return fx.whoosh(rng, d) * 0.6

    def vurus_():
        e, tt = zarf(1.2, a=0.002, dec=0.35)
        sub = np.sin(2 * np.pi * np.cumsum(62 * np.exp(-tt / 0.4) + 30) / SR) * e
        return sub + kutu_suzgec(rng.standard_normal(len(tt)), 30) * np.exp(-tt / 0.05) * 1.5

    def blip(m):
        e, tt = zarf(0.25, a=0.001, dec=0.06)
        return (np.sin(2 * np.pi * mtof(m) * tt) + 0.2 * np.sin(4 * np.pi * mtof(m) * tt)) * e

    def tik():
        e, tt = zarf(0.02, a=0.0003, dec=0.004)
        return np.sin(2 * np.pi * 2400 * tt) * e

    for an, tur, ek in efekt_anlari(s):
        if tur == "whoosh":
            ekle(sfx, an - 0.2, whoosh(), 0.35)
        elif tur == "vurus":
            ekle(sfx, an, vurus_(), 0.7)
        elif tur == "blip":
            ekle(sfx, an, blip(ek["nota"]), 0.16, pan=0.15)
        elif tur == "sayac":
            d = ek["sure"]
            for j in range(16):  # sayacın yavaşlayan ritmine uyan tıklar (out_quint tersi)
                ekle(sfx, an + d * (1 - (1 - j / 16) ** 0.2), tik(), 0.10)

    # --- seslendirme (platform/ses çıktısı: 48 kHz, -16 LUFS) ---
    ses = np.zeros(n)
    bulunan = []
    for satir in s["seslendirme"].get("satirlar", []):
        yol = (seslendirme or Path()) / f"{satir['id']}.wav"
        if not seslendirme or not yol.exists():
            continue
        x, sr = sf.read(str(yol))
        if x.ndim > 1:
            x = x.mean(1)
        if sr != SR:
            x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
        i = int(satir["t"] * SR)
        ses[i:i + len(x)] += x[: max(0, n - i)]
        bulunan.append(satir["id"])
    # konuşurken müzik ~8 dB altta (yumuşak yan zincir)
    kaba = np.abs(ses[::480])
    acik = (kutu_suzgec(kaba, 10) > 0.01).astype(float)
    acik = kutu_suzgec(np.maximum(acik, np.roll(acik, -8)), 20)
    duck = 1 - (1 - 10 ** (-8 / 20)) * np.clip(np.interp(np.arange(n) / 480, np.arange(len(acik)), acik), 0, 1)
    t_all = np.arange(n) / SR
    sonum = np.clip((sure - t_all) / 1.2, 0, 1)[:, None]
    giris = np.clip(t_all / 0.3, 0, 1)[:, None]
    yatak = (muzik * duck[:, None] + sfx * 0.9) * sonum * giris
    # yatak kazancı: konuşma anlarında ses, müzik+efektin `ses_ustu_db` (varsayılan 8 dB) üstünde kalır
    fark = None
    konusma = np.abs(ses) > 0 if bulunan else None
    if bulunan and konusma.any():
        rms = lambda x: float(np.sqrt(np.mean(x ** 2)) + 1e-12)  # noqa: E731
        hedef = s["muzik"].get("ses_ustu_db", 8.0)
        kazanc = rms(ses[konusma]) / rms(yatak.mean(1)[konusma]) / 10 ** (hedef / 20)
        yatak *= kazanc
        fark = 20 * math.log10(rms(ses[konusma]) / rms(yatak.mean(1)[konusma]))
    else:
        yatak *= 0.5
    miks = yatak + ses[:, None]
    cikti.mkdir(parents=True, exist_ok=True)
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.95).astype(np.float32), SR)
    return {"seslendirme": bulunan, "ses_ustu_db": fark}
