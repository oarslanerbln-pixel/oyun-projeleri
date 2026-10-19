"""Kinetik şablonun sesi: sentez müzik + zaman çizelgesindeki efektler + seslendirme → miks.

Müzik: `muzik.bpm` hızında sekizlik arpej, pad, offbeat hi-hat; `muzik.dusus` anından sonra clap,
pompalayan bas ve yan zincir. Akorlar `muzik.akorlar` listesinden birer ölçü (4 vuruş) çalar.
Vurmalılar ve efektler `platform/ortak/sfx.py`'den gelir (beyaz gürültü cızırtısı yok).
Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import miks as ortak_miks  # noqa: E402  (platform/ortak/miks.py: kökler)
import kutuphane  # noqa: E402  (kayıtlı CC0 efektler; yoksa sentez)
import sfx as fx  # noqa: E402  (yerel "sfx" efekt izi adıyla çakışmasın)
import zaman  # noqa: E402

SR = 48000


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None) -> dict:
    import soundfile as sf
    sure = s["sure"]
    n = int(SR * sure)
    t_all = np.arange(n) / SR
    muzik = np.zeros((n, 2)); sfx = np.zeros((n, 2)); rng = np.random.default_rng(7)
    vurus = 60 / s["muzik"]["bpm"]
    dusus = s["muzik"]["dusus"]
    son_an = sure - 0.5  # son yarım saniye: final akoru

    def ekle(buf, t0, x, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= n or i < 0: return
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * gain * l * 1.414
        buf[i:i + len(x), 1] += x * gain * r * 1.414

    def env(d, a=0.003, dec=None):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / a, 1.0)
        return e * (np.exp(-tt / dec) if dec else 1.0), tt

    def mtof(m): return 440 * 2 ** ((m - 69) / 12)

    # --- davul ---
    def kick(): return fx.kick(rng, 0.42)
    def clap(): return fx.clap(rng, 0.25) * 1.65
    def hat(d=0.06): return fx.hat(rng, d) * 0.33

    # --- tonal ---
    def pluck(m, d=0.32, br=1.0):
        e, tt = env(d, a=0.002, dec=0.09 * br)
        ph = 2 * np.pi * mtof(m) * tt
        return (np.sign(np.sin(ph)) * 0.35 + np.sin(2 * ph) * 0.3 + np.sin(ph) * 0.6) * e

    def bas(m, d):
        e, tt = env(d, a=0.004, dec=0.25)
        ph = 2 * np.pi * mtof(m) * tt
        return (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sign(np.sin(ph))) * e

    def pad(ms, d):
        tt = np.arange(int(d * SR)) / SR
        e = np.minimum(tt / 0.25, 1) * np.minimum((d - tt) / 0.3, 1)
        x = sum(np.sin(2 * np.pi * mtof(m) * (1 + det) * tt) for m in ms for det in (-0.004, 0.004))
        return x * e / (len(ms) * 2)

    akorlar = s["muzik"]["akorlar"]
    olcu = 4 * vurus

    def akor_at(tb): return akorlar[int(tb / olcu) % len(akorlar)]

    bosluk = zaman.davul_bosluklari(s)
    def bosta(tb): return any(a <= tb < b for a, b in bosluk)

    adim = vurus / 2
    arp = [0, 1, 2, 3, 2, 1, 3, 2]
    for i in range(int(son_an / adim) + 1):
        tb = i * adim
        if tb >= son_an: break
        notlar = akor_at(tb); vur = i % 2 == 0; tam = tb >= dusus
        if vur and not bosta(tb): ekle(muzik, tb, kick(), 0.9)
        if not vur: ekle(muzik, tb, hat(), 0.9, pan=0.3)
        if tam and i % 4 == 2: ekle(muzik, tb, clap(), 0.7, pan=-0.1)
        if tam and i % 4 == 3: ekle(muzik, tb, fx.shaker(rng) * 0.2, 0.6, pan=-0.3)
        ekle(muzik, tb, pluck(notlar[arp[i % 8] % len(notlar)] + 12, br=1.4 if tam else 1.0), 0.16, pan=(-0.4 if i % 2 else 0.4))
        if tam and not bosta(tb):
            ekle(muzik, tb, bas(min(notlar) - 24 + (12 if not vur else 0), adim * 0.95), 0.32)
    k = 0
    while k * olcu < son_an:
        ekle(muzik, k * olcu, pad(akorlar[k % len(akorlar)], min(olcu + 0.05, son_an - k * olcu + 0.05)), 0.16)
        k += 1
    kok = akorlar[0]
    ekle(muzik, son_an, pad([min(kok) - 12] + list(kok) + [kok[1] + 12], 0.5), 0.3)
    ekle(muzik, son_an, kick(), 0.8)

    duck = np.ones(n)  # yan zincir: düşüşten sonra her vuruşta pompalama
    for i in range(int(sure / vurus)):
        tb = i * vurus
        if dusus <= tb < son_an:
            a = int(tb * SR); tt = np.arange(min(int(0.22 * SR), n - a)) / SR
            duck[a:a + len(tt)] = np.minimum(duck[a:a + len(tt)], 1 - 0.45 * np.exp(-tt / 0.07))

    # --- efektler ---
    def pop():
        e, tt = env(0.18, a=0.001, dec=0.045)
        return np.sin(2 * np.pi * np.cumsum(900 * np.exp(-tt / 0.03) + 220) / SR) * e

    def whoosh(d=0.35, up=True):
        yedek = lambda: fx.whoosh(rng, d, yukari=up) * 2.3  # noqa: E731
        kayitli = kutuphane.var_mi("gecis_whoosh")
        x = kutuphane.kayit("gecis_whoosh", rng, yedek=yedek, sure=d + 0.25)
        return x[::-1].copy() if kayitli and not up else x  # "whoosh-in": kayıt ters çalar, sese doğru kabarır
    def boom(d=0.9): return fx.boom(rng, d) * 1.2

    def tick(f):
        e, tt = env(0.03, a=0.0005, dec=0.008)
        return np.sin(2 * np.pi * f * tt) * e

    def riser(d): return fx.riser(rng, d) * 0.66

    def sparkle():
        out = np.zeros(int(0.8 * SR))
        for k, m in enumerate([84, 88, 91, 96, 100]):
            e, tt = env(0.5, a=0.001, dec=0.12); x = np.sin(2 * np.pi * mtof(m) * tt) * e
            i = int(k * 0.045 * SR); out[i:i + len(x)] += x[: len(out) - i]
        return out

    def slam():
        return boom(0.6) * 0.8 + np.concatenate([clap(), np.zeros(int(0.35 * SR))])[: int(0.6 * SR)] * 1.5

    uret = {
        "pop": lambda e: pop(), "slam": lambda e: slam(), "sparkle": lambda e: sparkle(),
        "boom": lambda e: boom(e.get("sure", 0.9)), "whoosh": lambda e: whoosh(e.get("sure", 0.3)),
        "whoosh-in": lambda e: whoosh(e.get("sure", 0.25), up=False), "riser": lambda e: riser(e["sure"]),
        "tick": lambda e: tick(e["frekans"]),
    }
    for an, ad, kaz, pan, ek in zaman.ses_olaylari(s):
        ekle(sfx, an, uret[ad](ek), kaz, pan)

    # --- seslendirme (platform/ses çıktısı: 48 kHz, seviyelenmiş) ---
    ses_iz = np.zeros(n)
    bulunan = []
    for satir in s["seslendirme"].get("satirlar", []):
        yol = (seslendirme or Path()) / f"{satir['id']}.wav"
        if not seslendirme or not yol.exists():
            continue
        x, sr = sf.read(str(yol))
        if x.ndim > 1: x = x.mean(1)
        if sr != SR:
            x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
        x = x / (np.abs(x).max() + 1e-9) * 0.9
        i = int(satir["t"] * SR); ses_iz[i:i + len(x)] += x[: max(0, n - i)]
        bulunan.append(satir["id"])
    ses_iz = np.tanh(ses_iz * 1.2) / np.tanh(1.2)
    zarf = np.convolve(np.abs(ses_iz), np.ones(int(0.05 * SR)) / int(0.05 * SR), "same")
    zarf = np.convolve((zarf > 0.02).astype(float), np.ones(int(0.15 * SR)) / int(0.15 * SR), "same")
    muzik_k = muzik * (duck * (1 - 0.45 * np.clip(zarf, 0, 1)))[:, None]  # konuşurken müzik ~8 dB altta
    sonum = np.clip((sure - t_all) / 0.25, 0, 1)[:, None]
    miks = np.tanh((muzik_k * 0.8 + sfx * 0.65 + ses_iz[:, None] * 1.05) * sonum * 1.1)
    cikti.mkdir(parents=True, exist_ok=True)
    ortak_miks.kok_yaz(cikti, "efekt", sfx)  # kurgu bu sahnenin efektlerini buradan alır
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.95).astype(np.float32), SR)
    return {"seslendirme": bulunan}
