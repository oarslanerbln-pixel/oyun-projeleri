"""Karakalem anlatımının sesi: her sahnenin çizimi duyulan bir kalem, sahne girişinde kâğıt, sakin lo-fi akorlar.

Ses parçaları karakalem şablonunun sentezinden gelir (kalem çizgisi, e-piano, pad). Kurgu içinde müziği
kurgu çalar; bu modülün `efekt.wav` kökü (kalem + kâğıt) sahneye yerleşir. Tek başına render'da müzik
konuşmanın ~8 dB altında, konuşurken 3 dB daha kısılır. Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np

import zaman

_y = Path(__file__).resolve().parent.parent / "karakalem" / "sentez.py"
_spec = importlib.util.spec_from_file_location("karakalem_sentez", _y)
kk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kk)  # yardımcılar karakalemin zaman modülünü kullanmaz
SR = kk.SR
AKORLAR = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 60], [55, 59, 62, 67]]  # Am7 – Fmaj7 – C – G


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None, muzik_alti_db: float = 8.0) -> dict:
    import soundfile as sf
    sure = s["sure"]
    n = int(SR * sure)
    rng = np.random.default_rng(13)
    muzik, sfx = np.zeros((n, 2)), np.zeros((n, 2))

    def ekle(buf, t0, x, kaz=1.0, pan=0.0):
        i = int(round(t0 * SR))
        if i >= n or not len(x):
            return
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * kaz * l * 1.414
        buf[i:i + len(x), 1] += x * kaz * r * 1.414

    for i, (t, d) in enumerate(zaman.cizim_olaylari(s)):
        x = kk.kutuphane.kayit("kalem", rng, sure=d, yedek=lambda: kk.kalem_cizgisi(d, rng))
        ekle(sfx, t, x, 0.6, (i * 0.37) % 1 * 0.6 - 0.3)
    for sh in s["sahneler"][1:]:  # sahne girişinde kâğıt hışırtısı
        ekle(sfx, max(0.0, sh["_bas"] - 0.1), kk.hava(0.35, 900, 2600, rng), 0.35)
    vurus = 60 / s["muzik"].get("bpm", 84); olcu = 4 * vurus
    akor = s["muzik"].get("akorlar", AKORLAR)
    k, tb = 0, 0.0
    while tb < sure:
        a = akor[k % len(akor)]
        notalar = a["notalar"] if isinstance(a, dict) else a
        ekle(muzik, tb, kk.pad(notalar, olcu + 0.6), 0.35)
        for b_ in range(4):
            ekle(muzik, tb + b_ * vurus, kk.epiano(notalar[(b_ * 2 + k) % len(notalar)] + 12, 1.4, 0.5), 0.12, (-0.3, 0.3)[b_ % 2])
        tb += olcu; k += 1
    muzik = kk.alcak_stereo(muzik, 4500)

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
    muzik *= ref * 10 ** (-muzik_alti_db / 20) / rms(muzik)
    kk_ = int(0.12 * SR)
    muzik *= (1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske.astype(float), np.ones(kk_) / kk_, "same"), 0, 1))[:, None]
    dolu = np.abs(sfx).sum(1) > 1e-6
    if dolu.any():
        sfx *= ref * 10 ** (-14 / 20) / max(rms(sfx[dolu]), 1e-9)
    miks = vo[:, None] + kk.yanki(vo, 0.6, rng, 3500) * 0.12 + muzik + sfx
    miks -= kk.alcak_stereo(miks, 25)
    f = int(0.02 * SR); miks[:f] *= np.linspace(0, 1, f)[:, None]
    f = min(n, int(0.9 * SR)); miks[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
    cikti.mkdir(parents=True, exist_ok=True)
    kk.ortak_miks.kok_yaz(cikti, "efekt", sfx)
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
