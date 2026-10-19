"""Ortak miks araçları: konuşmada müziğin kendiliğinden kısılması, vuruş ızgarası, ses kökleri (stem).

Neden: her şablon müziği konuşma altında kendi yöntemiyle kısıyordu (kimi 0.12 sn'lik ortalamayla,
kimi sabit eşikle); kelime aralarında müzik pompalıyor, cümle aralarında ise geç açılıyordu. Burada
tek bir yan zincir var:

- **önden bakar** (konuşma başlamadan ~80 ms önce iner, ilk hece müziğin altında kalmaz);
- **tutar** (kelime aralarındaki kısa boşluklarda müzik zıplamaz);
- **cümle aralarında açılır** (boşluk ~0.6 sn'yi geçince müzik yumuşakça yükselir).

Vuruş tarafında `vurus_bul` bir müzik dosyasının temposunu ve ilk vuruşunu ölçer (kütüphaneden
gelen müzik için); sentez müzikte tempo zaten bilinir, `sonraki_vurus` kesme anlarını ızgaraya oturtur.

Yalnız numpy gerekir (`kok_yaz`/`kok_oku` için soundfile).

    import miks
    kazanc = miks.kisma(vo, derinlik_db=6)        # 1 = açık, konuşurken 10^(-6/20)
    muzik *= kazanc[:, None]
    t = miks.sonraki_vurus(12.31, bpm=100)       # 12.6
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

SR = 48000
KONTROL_HZ = 1000  # zarf bu hızda hesaplanır, sonra örnek hızına açılır


def _mono(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    return x.mean(axis=1) if x.ndim > 1 else x


def _genislet(a: np.ndarray, geri: int, ileri: int) -> np.ndarray:
    """İkili dizide her 1'i `geri` adım sonrasına ve `ileri` adım öncesine yayar (tutma + önden bakma)."""
    c = np.convolve(a, np.ones(geri + ileri + 1))  # c[i+ileri] = a[i-geri .. i+ileri] toplamı
    return (c[ileri:ileri + len(a)] > 0.5).astype(float)


def konusma_zarfi(vo: np.ndarray, sr: int = SR, esik_db: float = -35.0, onden: float = 0.08,
                  tutma: float = 0.30, atak: float = 0.05, birakma: float = 0.40) -> np.ndarray:
    """0–1 arası zarf: 1 konuşma var. Uzunluğu `vo` ile aynı.

    `esik_db` konuşmanın en yüksek 20 ms RMS'ine göre; `onden` konuşmadan önce inmeye başlama,
    `tutma` konuşma bittikten sonra bekleme (kelime arası), `atak`/`birakma` iniş/çıkış zaman sabitleri.
    """
    x = _mono(vo)
    n = len(x)
    if n == 0 or not np.any(x):
        return np.zeros(n)
    adim = max(1, sr // KONTROL_HZ)
    m = n // adim + 1
    kare = np.zeros(m * adim)
    kare[:n] = x ** 2
    guc = kare.reshape(m, adim).mean(axis=1)
    p = 20  # 20 ms RMS penceresi (kontrol hızında)
    c = np.cumsum(np.concatenate([np.zeros(p), guc]))
    rms = np.sqrt(np.maximum((c[p:] - c[:-p]) / p, 0))
    rms = np.roll(rms, -(p // 2))
    aktif = (rms > rms.max() * 10 ** (esik_db / 20)).astype(float)
    hz = sr / adim
    aktif = _genislet(aktif, geri=int(tutma * hz), ileri=int(onden * hz))
    a_k, b_k = math.exp(-1 / (atak * hz)), math.exp(-1 / (birakma * hz))
    z = np.empty(m)
    y = 0.0
    for i, v in enumerate(aktif):  # asimetrik tek kutuplu süzgeç (kontrol hızında: 60 sn ≈ 60k adım)
        y = v + (y - v) * (a_k if v > y else b_k)
        z[i] = y
    return np.interp(np.arange(n) / adim, np.arange(m), z)


def kisma(vo: np.ndarray, derinlik_db: float = 6.0, sr: int = SR, **ayar) -> np.ndarray:
    """Müzik kazanç eğrisi: konuşma yokken 1, konuşurken `derinlik_db` kadar aşağıda."""
    z = konusma_zarfi(vo, sr, **ayar)
    return 1.0 - (1.0 - 10 ** (-derinlik_db / 20)) * z


def rms(x: np.ndarray, maske: np.ndarray | None = None) -> float:
    x = _mono(x)
    if maske is not None:
        x = x[maske]
    return math.sqrt(float(np.mean(x ** 2))) if len(x) else 0.0


def aktif_rms(x: np.ndarray, esik_db: float = -50.0) -> float:
    """Yalnız sesin olduğu yerlerin RMS'i (efekt izinde sessiz aralar ortalamayı düşürmesin)."""
    m = np.abs(_mono(x))
    if not m.any():
        return 0.0
    return rms(x, m > m.max() * 10 ** (esik_db / 20))


# ---------------------------------------------------------------- vuruş

def sonraki_vurus(t: float, bpm: float, ofset: float = 0.0, her: int = 1, tolerans: float = 0.02) -> float:
    """`t` anına eşit ya da sonraki vuruş. `her=4` yalnız ölçü başları, `her=2` 1. ve 3. vuruş."""
    aralik = 60.0 / bpm * her
    k = math.ceil((t - ofset - tolerans) / aralik)
    return ofset + k * aralik


def izgara(bpm: float, sure: float, ofset: float = 0.0) -> np.ndarray:
    aralik = 60.0 / bpm
    return np.arange(ofset % aralik, sure, aralik)


def vurus_bul(x: np.ndarray, sr: int = SR, bpm_aralik: tuple[float, float] = (70.0, 180.0)) -> dict:
    """Müzik dosyasının temposu ve ilk vuruşu: spektral akış + otokorelasyon + tarak hizalama.

    Döndürür: `bpm`, `ofset` (ilk vuruş, sn), `guven` (0–1; < 0.2 ise tempo belirsiz).
    """
    x = _mono(x)
    hop, pencere = 512, 2048
    if len(x) < pencere * 8:
        return {"bpm": 0.0, "ofset": 0.0, "guven": 0.0}
    k = (len(x) - pencere) // hop
    idx = np.arange(pencere)[None, :] + hop * np.arange(k)[:, None]
    S = np.log1p(np.abs(np.fft.rfft(x[idx] * np.hanning(pencere), axis=1)) * 100)
    akis = np.maximum(np.diff(S, axis=0), 0).sum(axis=1)
    akis = np.concatenate([[0], akis])
    akis -= np.convolve(akis, np.ones(16) / 16, "same")  # yavaş değişimi çıkar
    akis = np.maximum(akis, 0)
    if not akis.any():
        return {"bpm": 0.0, "ofset": 0.0, "guven": 0.0}
    hz = sr / hop
    f = np.fft.rfft(akis - akis.mean(), 2 * len(akis))
    ak = np.fft.irfft(np.abs(f) ** 2)[: len(akis)]
    ak /= ak[0] + 1e-12
    gecikme = np.arange(len(ak))
    bpm_ = 60 * hz / np.maximum(gecikme, 1)
    aday = (bpm_ >= bpm_aralik[0]) & (bpm_ <= bpm_aralik[1])
    agirlik = np.exp(-0.5 * (np.log2(np.maximum(bpm_, 1) / 115)) ** 2 / 0.9 ** 2)  # 115 civarı daha olası
    skor = np.where(aday, ak * agirlik, -np.inf)
    g = int(np.argmax(skor))
    if 1 < g < len(ak) - 1:  # parabolik ince ayar
        a, b, c = ak[g - 1], ak[g], ak[g + 1]
        d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
        g_ince = g + float(np.clip(d, -0.5, 0.5))
    else:
        g_ince = float(g)
    donem = g_ince / hz
    fazlar = np.linspace(0, donem, 64, endpoint=False)
    t_akis = np.arange(len(akis)) / hz
    puan = [np.interp(np.arange(f0, t_akis[-1], donem), t_akis, akis).sum() for f0 in fazlar]
    ofset = float(fazlar[int(np.argmax(puan))])
    # akış pencere merkezine göre ölçülür: yarım pencere ileri
    ofset = (ofset + (pencere / 2 - hop / 2) / sr) % donem
    return {"bpm": round(60 / donem, 2), "ofset": round(ofset, 3), "guven": round(float(max(ak[g], 0)), 3)}


# ---------------------------------------------------------------- kökler (stem)

def kok_yaz(klasor: str | Path, ad: str, x: np.ndarray, sr: int = SR) -> Path | None:
    """Miks öncesi bir izi (ör. efektler) `klasor/<ad>.wav` olarak yazar; kurgu sahne efektlerini buradan alır."""
    import soundfile as sf
    x = np.asarray(x, dtype=np.float64)
    if not np.isfinite(x).all() or not np.any(x):
        return None
    yol = Path(klasor) / f"{ad}.wav"
    yol.parent.mkdir(parents=True, exist_ok=True)
    tepe = float(np.abs(x).max())
    sf.write(str(yol), (x / tepe * 0.9 if tepe > 0.9 else x).astype(np.float32), sr)
    return yol


def kok_oku(yol: str | Path, sr: int = SR, kanal: int = 2) -> np.ndarray:
    import soundfile as sf
    x, r = sf.read(str(yol), always_2d=True)
    if r != sr:
        n = int(len(x) * sr / r)
        x = np.stack([np.interp(np.arange(n) * r / sr, np.arange(len(x)), x[:, c]) for c in range(x.shape[1])], 1)
    if x.shape[1] == 1 and kanal == 2:
        x = np.repeat(x, 2, axis=1)
    return x[:, :kanal]
