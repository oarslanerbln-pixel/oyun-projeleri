"""Ortak sahne dilinin müziği, efektleri ve miksi (48 kHz stereo, numpy).

Müzik sahnelere kilitlidir: her sahnenin tipi bir enerji düzeyi verir (alıntı/geçiş sakin, başlık/liste/ürün orta,
sayı/karşılaştırma/çağrı enerjik), akorlar ölçü başında değişir, son sahnede final akoru çalar. Enstrüman ve tempo
kaplamanın `MUZIK` profilinden, sahne başı efekti `SFX`ten gelir. Konuşurken müzik kısılır; çıktı -14 LUFS.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np

BURADA = Path(__file__).resolve().parent
sys.path.append(str(BURADA.parents[1] / "ortak"))
import sfx as fx  # noqa: E402

from dil import ENERJI, harita_anlari  # noqa: E402

_sp = importlib.util.spec_from_file_location("desen_sentez", BURADA.parent / "desen" / "sentez.py")
_ds = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_ds)  # noqa: E702  (can, mizrap, marimba, sinus, ped)
SR, mtof, ekle, ped = _ds.SR, _ds.mtof, _ds.ekle, _ds.ped


def _zarf(n, atak, sonum):
    t = np.arange(n) / SR
    return np.minimum(t / max(atak, 1e-4), 1.0) * np.exp(-t / sonum), t


def kalimba(f, d=0.9, parlak=1.0):
    e, t = _zarf(int(d * SR), 0.002, 0.28)
    return (np.sin(2 * np.pi * f * t) + 0.35 * parlak * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.04)
            + 0.12 * np.sin(2 * np.pi * f * 2 * t)) * e


def kare(f, d=0.22, duty=0.5):
    n = int(d * SR); t = np.arange(n) / SR
    x = np.where(((f * t) % 1) < duty, 1.0, -1.0)
    return x * np.minimum(t / 0.004, 1) * np.clip((d - t) / 0.04, 0, 1) * np.exp(-t / 0.35) * 0.55


ENSTRUMAN = {
    "sinus": lambda f, d: _ds.sinus(f, min(d, 0.5)),
    "can": lambda f, d: _ds.can(f, 1.4),
    "marimba": lambda f, d: _ds.marimba(f, 0.6),
    "mizrap": lambda f, d: _ds.mizrap(f, 1.0),
    "kalimba": lambda f, d: kalimba(f, 0.9),
    "kare": lambda f, d: kare(f, min(d * 0.9, 0.25), 0.25),
}


def _efekt(tur, rng):
    if tur == "kagit":
        return fx.bant(fx.hisirti(rng, 0.28, 60, 0.7), 900, 6000) * 0.8
    if tur == "pop":
        n = int(0.14 * SR); t = np.arange(n) / SR
        return np.sin(2 * np.pi * np.cumsum(380 * np.exp(-t / 0.05) + 140) / SR) * np.exp(-t / 0.05)
    if tur == "blip":
        return np.concatenate([kare(mtof(84), 0.06), kare(mtof(91), 0.08)])
    if tur == "tok":
        n = int(0.12 * SR); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 820 * t) * 0.6 + np.sin(2 * np.pi * 1630 * t) * 0.3) * np.exp(-t / 0.025)
    if tur == "katla":
        return fx.bant(fx.hisirti(rng, 0.2, 90, 1.0), 1500, 7000) * 0.7 + np.pad(_efekt("tok", rng)[:int(0.12 * SR)] * 0.4,
                                                                             (int(0.08 * SR), 0))[:int(0.2 * SR)]
    return fx.whoosh(rng, 0.35)


def muzik(s: dict, prof: dict, sfx_tur: str) -> tuple[np.ndarray, np.ndarray]:
    """(müzik, efektler), ikisi de (n, 2)."""
    sure = s["sure"]
    n = int(sure * SR)
    m = np.zeros((n, 2)); e = np.zeros((n, 2))
    rng = np.random.default_rng(11)
    bpm, kok, dizi = prof["bpm"], prof["kok"], prof["dizi"]
    calgi = ENSTRUMAN[prof.get("enstruman", "sinus")]
    vurus = 60.0 / bpm; adim = vurus / 2; olcu = vurus * 4
    shs = s["sahneler"]
    son_bas = shs[-1]["bas"]

    def enerji(t):
        for sh in reversed(shs):
            if t >= sh["bas"]:
                return 2 if sh is shs[-1] and sh["tip"] == "cta" else ENERJI[sh["tip"]]
        return 1

    def akor(t):
        a = prof.get("akor", [0, 9, 5, 7])[int(t / olcu) % len(prof.get("akor", [0, 9, 5, 7]))]
        minor = a in (2, 4, 9)
        return kok + a, [0, 3, 7] if minor else [0, 4, 7]

    for b in range(int(math.ceil(sure / olcu))):
        t0 = b * olcu
        k, ak = akor(t0)
        ekle(m, t0, ped([k - 12 + x for x in ak], min(olcu + 0.6, sure - t0), 0.5), 0.16)
    k = 0; t = 0.0
    while t < sure - 0.4:
        en = enerji(t)
        kk, ak = akor(t)
        if en == 0 and k % 4:
            k += 1; t += adim; continue
        if en == 1 and k % 2 and k % 8 not in (3, 7):
            k += 1; t += adim; continue
        ton = kk + 12 + ak[[0, 1, 2, 1, 2, 0, 1, 2][k % 8]] + (12 if k % 8 == 6 else 0)
        ekle(m, t, calgi(mtof(ton), adim), (0.13, 0.18, 0.21)[en], pan=0.35 * math.sin(k * 0.9))
        if k % 4 == 0:
            ekle(m, t, calgi(mtof(kk - 12), vurus * 2), (0.16, 0.22, 0.25)[en])
        if en == 2 and k % 2 == 0:
            ekle(e, t, fx.kick(rng, 0.3, 50, 0.06), 0.22)
        if en == 2 and k % 2 == 1:
            ekle(e, t, fx.hat(rng, 0.05), 0.06, pan=0.3)
        k += 1; t += adim
    for i, sh in enumerate(shs):  # sahne vurguları
        if i:
            ekle(e, max(0.0, sh["bas"] - 0.08), _efekt(sfx_tur, rng), 0.22)
        u = sh["son"] - sh["bas"]
        an = sh.get("_an") or {}
        if sh["tip"] == "liste":
            aralik = min(0.55, max(0.25, (u - 1.0) / (len(sh["maddeler"]) + 1)))
            for j in range(len(sh["maddeler"])):  # madde söylendiği an girer (senkron.py); efekt onunla
                ekle(e, sh["bas"] + an.get(f"madde{j}", 0.35 + j * aralik), _efekt("pop" if sfx_tur != "blip" else "blip", rng), 0.16)
        elif sh["tip"] == "harita" and isinstance(sh.get("duraklar"), list):
            for j in range(1, len(sh["duraklar"])):  # rota durağa vardığı an
                ekle(e, sh["bas"] + an.get(f"durak{j}", harita_anlari(sh, u)[j]), _efekt("pop" if sfx_tur != "blip" else "blip", rng), 0.12)
        elif sh["tip"] == "grafik" and isinstance(sh.get("veri"), list) and sh.get("tur", "cubuk") != "cizgi":
            aralik = min(0.45, max(0.15, (u - 1.4) / (len(sh["veri"]) + 1)))
            for j in range(len(sh["veri"])):  # çubuk/dilim girdiği an
                ekle(e, sh["bas"] + an.get(f"veri{j}", 0.35 + j * aralik), _efekt("pop" if sfx_tur != "blip" else "blip", rng), 0.12)
        elif sh["tip"] == "sayi":
            d = min(1.2, u * 0.45)
            t0 = sh["bas"] + an.get("deger", 0.12) + 0.08
            for j in range(10):
                ekle(e, t0 + d * (1 - (1 - j / 10) ** (1 / 3)), fx.tik(rng, 2600 + 120 * j, 0.012), 0.10)
            ekle(m, t0 + d, calgi(mtof(kok + 24), 1.0), 0.14)
    ekle(e, son_bas, fx.zil(rng, 1.8), 0.08)
    kk, ak = akor(son_bas)
    for j, x in enumerate(ak + [12]):
        ekle(m, son_bas + 0.25 + j * 0.05, calgi(mtof(kok + 12 + x), 1.2), 0.12, pan=(j - 1.5) * 0.25)
    f = int(0.6 * SR)
    m[-f:] *= np.linspace(1, 0, f)[:, None]
    return m, e


def _oku(yol: Path) -> np.ndarray:
    import soundfile as sf
    x, sr = sf.read(str(yol), always_2d=True)
    if sr != SR:  # basit yeniden örnekleme (seslendirme 48 kHz değilse)
        n = int(len(x) * SR / sr)
        x = np.stack([np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x[:, c]) for c in range(x.shape[1])], 1)
    return x if x.shape[1] == 2 else np.repeat(x, 2, axis=1)


def miksle(s: dict, prof: dict, sfx_tur: str, is_: Path, ses_dizini: Path) -> dict:
    """Seslendirme + müzik (konuşmanın ~9 dB altında, konuşurken ek 4 dB kısma; `"muzik": false` ise yok) + efektler → is_/ses.wav"""
    import soundfile as sf
    is_.mkdir(parents=True, exist_ok=True)
    n = int(s["sure"] * SR)
    vo = np.zeros((n, 2)); maske = np.zeros(n); bulunan = []
    for x in s["seslendirme"].get("satirlar", []):
        yol = ses_dizini / f"{x['id']}.wav"
        if not yol.exists():
            continue
        a = _oku(yol)
        i = int(x["t"] * SR); a = a[: n - i]
        vo[i:i + len(a)] += a; maske[i:i + len(a)] = 1.0
        bulunan.append(x["id"])
    m, e = muzik(s, prof, sfx_tur)
    if s.get("muzik") is False:  # `"muzik": false`: müzik yatağı yok, yalnız ses + efektler
        m[:] = 0
    rms = lambda a: math.sqrt(float(np.mean(a ** 2)) + 1e-12)  # noqa: E731
    ref = rms(vo[maske > 0]) if bulunan else 0.08
    if np.any(m):
        m *= ref * 10 ** (-9 / 20) / rms(m)
    k = int(0.15 * SR)
    duk = 1 - (1 - 10 ** (-4 / 20)) * np.clip(np.convolve(maske, np.ones(k) / k, "same"), 0, 1)
    m *= duk[:, None]
    if np.any(e):
        e *= ref * 10 ** (-7 / 20) / max(rms(e[np.abs(e).sum(1) > 1e-6]), 1e-9)
    karisim = vo + m + e
    f = int(0.02 * SR); karisim[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.3 * SR); karisim[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(str(is_ / "ses.wav"), (karisim / max(1e-9, np.abs(karisim).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}

