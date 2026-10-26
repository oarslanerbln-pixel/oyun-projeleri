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


# anlatım cilası: gürültü/uğultu kesilir, oda tınısı (250–400 Hz) azaltılır, netlik bandı açılır, sesler eşitlenir,
# kelime sonlarındaki kuyruk bastırılır. Gecikmesiz süzgeçler: zamanlama ve dudak senkronu değişmez.
# 2026-10-26 (Atilla: "videoda yine yankılı"): ham kayıt kuruydu; kompresörün makeup'ı kelime kuyruklarını 3–7 dB
# kaldırıyordu. Kompresör yumuşadı, kuyruk kapısı sıkılaştı.
CILA = ("highpass=f=90:poles=2,equalizer=f=320:t=q:w=1.2:g=-3,equalizer=f=3500:t=q:w=1.4:g=2.5,"
        "deesser=i=0.35,acompressor=threshold=-18dB:ratio=2:attack=8:release=60:makeup=1,"
        "agate=threshold=0.02:ratio=2.5:range=0.12:attack=3:release=70")


def ses_cilala(vo: np.ndarray) -> np.ndarray:
    import subprocess, tempfile
    import soundfile as sf
    with tempfile.TemporaryDirectory() as d:
        g, c = Path(d) / "g.wav", Path(d) / "c.wav"
        sf.write(str(g), vo.astype(np.float32), SR)
        try:
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(g), "-af", CILA, "-c:a", "pcm_f32le", str(c)],
                           check=True)
        except (OSError, subprocess.CalledProcessError):
            return vo
        y, _ = sf.read(str(c))
    y = y.mean(1) if y.ndim > 1 else y
    return np.pad(y, (0, max(0, len(vo) - len(y))))[: len(vo)]


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None, muzik_alti_db: float | None = None) -> dict:
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

    efekt = s.get("efekt", True)  # `"efekt": false`: kalem ve kâğıt sesleri yok, yalnız ses + müzik
    for i, (t, d) in enumerate(zaman.cizim_olaylari(s) if efekt else []):
        x = kk.kutuphane.kayit("kalem", rng, sure=d, yedek=lambda: kk.kalem_cizgisi(d, rng))
        ekle(sfx, t, x, 0.6, (i * 0.37) % 1 * 0.6 - 0.3)
    for sh in s["sahneler"][1:] if efekt else []:  # sahne girişinde kâğıt hışırtısı
        ekle(sfx, max(0.0, sh["_bas"] - 0.1), kk.hava(0.35, 900, 2600, rng), 0.35)
    # Müzik konuşmanın `muzik.alti_db` (varsayılan 16) dB altında, konuşurken `muzik.kisma_db` (6) dB daha kısılır.
    # 2026-10-26: e-piano vuruşları ve pad erkek sesinin perde aralığında; 8 dB altta kelime sonlarına yankı gibi
    # biniyordu. E-piano artık ayrı bir izde, konuşma sırasında 10 dB daha kısılır.
    if muzik_alti_db is None:
        muzik_alti_db = float(s["muzik"].get("alti_db", 16.0))
    kisma_db = float(s["muzik"].get("kisma_db", 6.0))
    ep = np.zeros((n, 2))
    vurus = 60 / s["muzik"].get("bpm", 84); olcu = 4 * vurus
    akor = s["muzik"].get("akorlar", AKORLAR)
    k, tb = 0, 0.0
    while tb < sure:
        a = akor[k % len(akor)]
        notalar = a["notalar"] if isinstance(a, dict) else a
        ekle(muzik, tb, kk.pad(notalar, olcu + 0.6), 0.35)
        for b_ in range(4):
            ekle(ep, tb + b_ * vurus, kk.epiano(notalar[(b_ * 2 + k) % len(notalar)] + 12, 1.4, 0.5), 0.12, (-0.3, 0.3)[b_ % 2])
        tb += olcu; k += 1
    muzik = kk.alcak_stereo(muzik, 4500); ep = kk.alcak_stereo(ep, 4500)

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
    olcek = ref * 10 ** (-muzik_alti_db / 20) / rms(muzik + ep)
    kk_ = int(0.12 * SR)
    konusma = np.clip(np.convolve(maske.astype(float), np.ones(kk_) / kk_, "same"), 0, 1)
    if len(konusma):  # kısma kelime bitiminden sonra 0,4 sn tutulur: kuyruğun altına nota binmesin
        h = int(0.4 * SR); c = np.r_[0.0, np.cumsum(konusma)]
        geri = (c[1:] - c[np.maximum(0, np.arange(1, len(c)) - h)]) / h  # son 0,4 sn ortalaması
        konusma = np.maximum(konusma, np.clip(geri * 3, 0, 1))
    kis = lambda db: (1 - (1 - 10 ** (-db / 20)) * konusma)[:, None]
    muzik = (muzik * kis(kisma_db) + ep * kis(kisma_db + 10)) * olcek
    dolu = np.abs(sfx).sum(1) > 1e-6
    if dolu.any():
        sfx *= ref * 10 ** (-14 / 20) / max(rms(sfx[dolu]), 1e-9)
    if s.get("ses_cilasi", True) and bulunan:
        vo = ses_cilala(vo)
    yanki = float(s.get("yanki", 0))  # Atilla 2026-10-25: anlatımdaki oda yankısı iyi gelmiyor; varsayılan kuru ses
    miks = vo[:, None] + (kk.yanki(vo, 0.6, rng, 3500) * yanki if yanki else 0) + muzik + sfx
    miks -= kk.alcak_stereo(miks, 25)
    f = int(0.02 * SR); miks[:f] *= np.linspace(0, 1, f)[:, None]
    f = min(n, int(0.9 * SR)); miks[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
    cikti.mkdir(parents=True, exist_ok=True)
    kk.ortak_miks.kok_yaz(cikti, "efekt", sfx)
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}
