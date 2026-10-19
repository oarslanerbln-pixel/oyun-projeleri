"""Karakalem şablonunun sesi: duyulan bir kalem + kamera, iniş ve damga efektleri + lo-fi müzik + seslendirme.

Kalem sesi her çizginin o anki hızından üretilir (kâğıt dokusu, hızlandıkça parlaklaşan grafit sürtünmesi)
ve kalem keskin bir köşeyi döndüğü an küçük bir tık çalar. Tarama hızlı ileri-geri vuruşlardır (~12/sn).
Kamera geri çekilirken ya da yaklaşırken hava sesi; karakter her basamağa indiğinde marimba notası,
tok bir "tum" ve pop; eğri çizilirken yükselen e-piyano; damgada tok vuruş, alt bas ve müzik kutusu akoru.
Müzik: sakin lo-fi akorlar ve pad, basamaklarla birlikte davul ve bas girer; damgadan hemen önce bir
nefeslik sessizlik. Konuşma sırasında müzik sesin ~8 dB altında durur. Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import miks as ortak_miks  # noqa: E402  (platform/ortak/miks.py: kökler)
import kutuphane  # noqa: E402  (kayıtlı CC0 efektler; yoksa sentez)
import sfx as fx  # noqa: E402  (platform/ortak/sfx.py: beyaz gürültüsüz efektler)

import zaman

SR = 48000
BASAMAK_NOTALARI = [60, 64, 67, 72, 76, 79, 84, 88]  # Do majör arpej: her iniş bir üst nota
EGRI_NOTALARI = [60, 64, 67, 71, 72, 76, 79]
DAMGA_AKORU = [72, 76, 79, 84]


def mtof(m: float) -> float:
    return 440 * 2 ** ((m - 69) / 12)


def zamanlar(d: float) -> np.ndarray:
    return np.arange(int(d * SR)) / SR


def bant(n: int, merkez: float, oktav: float, rng, rms: float = 1.0) -> np.ndarray:
    """merkez frekans çevresinde (oktav genişliğinde) süzülmüş gürültü; frekans uzayında, bağımlılıksız"""
    if n <= 0:
        return np.zeros(0)
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR); f[0] = 1.0
    X *= np.exp(-0.5 * (np.log2(f / merkez) / oktav) ** 2)
    x = np.fft.irfft(X, n)
    return x / (math.sqrt(float(np.mean(x ** 2))) + 1e-12) * rms


def alcak(x: np.ndarray, kesim: float) -> np.ndarray:
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / kesim) ** 4), len(x))


def yanki(x: np.ndarray, sure: float, rng, parlak: float = 4500) -> np.ndarray:
    """basit oda yankısı: üstel sönen gürültü dürtü yanıtıyla FFT evrişimi (stereo, iki ayrı yanıt)"""
    tt = zamanlar(sure)
    out = np.zeros((len(x), 2))
    for c in range(2):
        ir = alcak(rng.standard_normal(len(tt)), parlak) * np.exp(-tt / (sure / 6.9))
        ir /= math.sqrt(float(np.sum(ir ** 2))) + 1e-12
        m = 1 << int(math.ceil(math.log2(len(x) + len(ir))))
        out[:, c] = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return out


# ---------- kalem ----------
def kalem_cizgisi(d: float, rng, noktali: bool = False) -> np.ndarray:
    """yumuşak (in-out) bir kalemin hızı: ortada en hızlı; ses hızla parlaklaşır ve yükselir"""
    tt = zamanlar(d + 0.06)
    p = np.clip(tt / d, 0, 1)
    v = np.where(p < 0.5, 4 * p, 4 * (1 - p)) / 2
    v = np.where(tt > d, np.maximum(0, 1 - (tt - d) / 0.05) * 0.2, v)
    n = len(tt)
    alt, ust = bant(n, 1900, 0.5, rng), bant(n, 4000, 0.5, rng)
    govde = (alt * (1 - v) + ust * v) * 1.3 + bant(n, 6500, 0.35, rng, 0.06) + bant(n, 300, 0.8, rng, 0.5) * v
    tane = np.repeat(0.55 + 0.45 * rng.random(n // 240 + 1), 240)[:n]  # kâğıdın dişi, 5 ms'de bir değişir
    kesik = np.where(np.sin(2 * np.pi * 14 * tt) > -0.2, 1.0, 0.15) if noktali else 1.0
    return govde * np.power(v, 0.7) * tane * kesik * np.minimum(1, tt / 0.01)


def kose_tiki(rng) -> np.ndarray:
    tt = zamanlar(0.03)
    return bant(len(tt), 4800, 0.4, rng) * np.exp(-tt / 0.004) * 2.2


def tarama_sesi(d: float, rng, hiz: float = 11.5) -> np.ndarray:
    tt = zamanlar(d)
    return bant(len(tt), 3200, 0.55, rng) * np.abs(np.sin(2 * np.pi * hiz * tt)) ** 0.6 * np.sin(np.pi * np.clip(tt / d, 0, 1)) * 1.4


def hava(d: float, f0: float, f1: float, rng, kare: bool = False) -> np.ndarray:
    """kamera hareketi: merkezi f0'dan f1'e kayan pembe gürültü"""
    tt = zamanlar(d); n = len(tt)
    p = tt / d
    merkez = np.log2(f0) + (np.log2(f1) - np.log2(f0)) * (p * p if kare else p)
    out = np.zeros(n)
    for m in np.linspace(np.log2(180), np.log2(6000), 9):
        w = np.exp(-0.5 * ((merkez - m) / 0.6) ** 2)
        out += bant(n, 2 ** m, 0.35, rng) * w / math.sqrt(2 ** m / 180)
    return out * np.sin(np.pi * p) ** 2 * 0.9


# ---------- çalgılar ----------
def epiano(nota: float, d: float = 1.6, sonum: float = 0.55) -> np.ndarray:
    tt = zamanlar(d); f = mtof(nota); ph = 2 * np.pi * f * tt
    ton = np.sin(ph + 0.6 * np.sin(ph) * np.exp(-tt / 0.25)) + 0.18 * np.sin(2 * ph) * np.exp(-tt / 0.3)
    return ton * np.minimum(tt / 0.006, 1) * np.exp(-tt / sonum) * np.minimum(1, (d - tt) / 0.08)


def marimba(nota: float, rng) -> np.ndarray:
    tt = zamanlar(0.6); ph = 2 * np.pi * mtof(nota) * tt
    x = (np.sin(ph) + 0.25 * np.sin(4 * ph) * np.exp(-tt / 0.03)) * np.minimum(tt / 0.002, 1) * np.exp(-tt / 0.16)
    return x + bant(len(tt), 1500, 0.8, rng, 0.3) * np.exp(-tt / 0.006)


def pad(notalar, d: float) -> np.ndarray:
    tt = zamanlar(d)
    e = np.minimum(tt / 0.5, 1) * np.minimum(np.maximum(d - tt, 0) / 1.2, 1)
    x = sum(np.sin(2 * np.pi * mtof(k) * (1 + det) * tt) for k in notalar for det in (-0.003, 0.003))
    return alcak(x, 900) * e / (len(notalar) * 2)


def tum(f: float, d: float) -> np.ndarray:  # tok iniş / vuruş
    tt = zamanlar(d * 5)
    return np.sin(2 * np.pi * np.cumsum(f * (1 + 2 * np.exp(-tt / 0.02))) / SR) * np.exp(-tt / d) * np.minimum(tt / 0.002, 1)


def pop(f: float) -> np.ndarray:
    tt = zamanlar(0.1)
    return np.sin(2 * np.pi * np.cumsum(f * (0.6 + 0.8 * np.exp(-tt / 0.015))) / SR) * np.exp(-tt / 0.03)


def alt_bas(d: float, f0: float, f1: float) -> np.ndarray:
    tt = zamanlar(d)
    return np.sin(2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-tt / 0.15)) / SR) * np.exp(-tt / (d / 3)) * np.minimum(tt / 0.004, 1)


def muzik_kutusu(nota: float) -> np.ndarray:
    tt = zamanlar(1.6); ph = 2 * np.pi * mtof(nota) * tt
    return (np.sin(ph) + 0.3 * np.sin(3 * ph) * np.exp(-tt / 0.2)) * np.exp(-tt / 0.5) * np.minimum(tt / 0.001, 1)


def kick() -> np.ndarray:
    tt = zamanlar(0.35)
    return np.sin(2 * np.pi * np.cumsum(46 + 70 * np.exp(-tt / 0.03)) / SR) * np.minimum(tt / 0.002, 1) * np.exp(-tt / 0.12)


def trampet(rng) -> np.ndarray:
    tt = zamanlar(0.25)
    return (bant(len(tt), 1900, 0.9, rng, 0.6) * np.exp(-tt / 0.06) + np.sin(2 * np.pi * 190 * tt) * np.exp(-tt / 0.04) * 0.5)


def zil(rng) -> np.ndarray:  # metalik hi-hat (bant gürültüsü her sekizlikte tıslıyordu)
    return fx.hat(rng, 0.06) * 0.3


def bas(nota: float, d: float) -> np.ndarray:
    tt = zamanlar(d); ph = 2 * np.pi * mtof(nota) * tt
    return (np.sin(ph) + 0.2 * np.sin(2 * ph)) * np.minimum(tt / 0.01, 1) * np.exp(-tt / 0.6) * np.minimum(1, (d - tt) / 0.05)


def miksle(s: dict, cikti: Path, seslendirme: Path | None = None, muzik_alti_db: float = 8.0) -> dict:
    import soundfile as sf
    sure = s["sure"]
    n = int(SR * sure)
    rng = np.random.default_rng(11)
    vurus = zaman.vurus(s); olcu = 4 * vurus
    ad = zaman.sahne(s, "adimlar"); sn = zaman.sahne(s, "sonuc")
    damga_t = sn["damga"]["t"] if sn.get("damga") else None
    ofset = ad["bas"] % olcu  # müzik ızgarası: adımlar bir ölçü başında başlar
    tus, ped, dav, bs, ezgi, yank, sfx = (np.zeros((n, 2)) for _ in range(7))

    def ekle(buf, t0, x, kaz=1.0, pan=0.0):
        i = int(round(t0 * SR))
        if i < 0:
            x, i = x[-i:], 0
        if i >= n or not len(x):
            return
        x = x[: n - i]
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        buf[i:i + len(x), 0] += x * kaz * l * 1.414
        buf[i:i + len(x), 1] += x * kaz * r * 1.414

    # --- kalem: her çizgi, köşe tıkları, tarama, başlığın yazılışı ---
    for adi, c in zaman.cizgiler(s).items():
        x = kutuphane.kayit("kalem", rng, sure=c["d"], yedek=lambda: kalem_cizgisi(c["d"], rng, c.get("noktali", False)))
        ekle(sfx, c["t"], x, 0.55 if adi.startswith("basamak") else 0.7, 0.15 if adi == "dag" else -0.1)
        for tc in zaman.koseler(c):
            ekle(sfx, tc, kose_tiki(rng), 0.35)
    ta, td = zaman.tarama(s)
    ekle(sfx, ta, kutuphane.kayit("kalem", rng, sure=td, yedek=lambda: tarama_sesi(td, rng)), 0.55, 0.2)

    # --- zaman çizelgesindeki efektler ---
    for an, ad_, kaz, pan, ek in zaman.ses_olaylari(s):
        if ad_ == "uzaklas":
            ekle(sfx, an, hava(ek["sure"], 4400, 270, rng), kaz)
        elif ad_ == "yakinlas":
            ekle(sfx, an - 0.05, hava(ek["sure"], 300, 3800, rng, kare=True), kaz * 0.8)
        elif ad_ == "inis":
            i = ek["adim"]
            x = marimba(BASAMAK_NOTALARI[i % len(BASAMAK_NOTALARI)], rng)
            ekle(ezgi, an, x, 0.42, pan); ekle(yank, an, x, 0.16)
            ekle(sfx, an, tum(110 - i * 6, 0.05), 0.35)
            ekle(sfx, an, pop(1800 + i * 250), 0.25, pan)
        elif ad_ == "tirmanis":
            for j, nota in enumerate(EGRI_NOTALARI):
                x = epiano(nota, 0.9, 0.35)
                ekle(ezgi, an + j / len(EGRI_NOTALARI) * ek["sure"], x, 0.13, -0.4 + j * 0.13); ekle(yank, an + j / len(EGRI_NOTALARI) * ek["sure"], x, 0.05)
        elif ad_ == "damga":
            ekle(sfx, an, tum(68, 0.13), 0.9)
            ekle(sfx, an, alt_bas(1.3, 66, 32), 0.5)
            ekle(sfx, an - 0.02, hava(0.3, 900, 6000, rng), 0.3)
            for nota in DAMGA_AKORU:
                x = muzik_kutusu(nota); ekle(ezgi, an, x, 0.2); ekle(yank, an, x, 0.22)
        elif ad_ == "yazi":
            ekle(sfx, an, tarama_sesi(ek["sure"], rng, 9.0), 0.35)

    # --- lo-fi yatak: akorlar ve pad baştan; davul ve bas adımlarla girer ---
    akorlar = s["muzik"]["akorlar"]
    k = 0
    while ofset + k * olcu < sure:
        tb = ofset + k * olcu
        a = akorlar[k % len(akorlar)]
        for off, g in ((0, 0.2), (1.5 * vurus, 0.12)):
            for j, nota in enumerate(a["notalar"]):
                ekle(tus, tb + off + j * 0.018, epiano(nota, olcu * 0.9), g, (j - 1) * 0.3)
        ekle(ped, tb, pad(a["notalar"], olcu + 1.2), 0.35)
        if tb >= ad["bas"] - 1e-6:
            for b_ in range(4):
                tv = tb + b_ * vurus
                if b_ in (0, 2):
                    ekle(dav, tv, kick(), 0.55)
                    ekle(bs, tv, bas(a["bas"], vurus * 1.8), 0.32)
                else:
                    ekle(dav, tv, trampet(rng), 0.22, 0.1)
                for h_ in (0, 1):  # sekizlik ziller, hafif sallantılı
                    ekle(dav, tv + h_ * vurus * 0.56, zil(rng), 0.3 if h_ == 0 else 0.18, -0.25)
        k += 1
    if ofset > 0.05:  # ızgaradan önceki kısa giriş: son akorun pad'i
        ekle(ped, 0, pad(akorlar[-1]["notalar"], ofset + 0.8), 0.3)
    if damga_t:  # damgadan önce bir nefeslik sessizlik
        a0, a1 = int((damga_t - zaman.NEFES_SN) * SR), int(damga_t * SR)
        for b_ in (tus, ped, dav, bs):
            b_[a0:a1] *= np.linspace(1, 0, a1 - a0)[:, None] ** 3 if a1 > a0 else 1
    # plak: yalnız seyrek çıtırtı; sürekli hışırtı zemini yok (tek düze cızırtı olarak duyuluyordu)
    plak = fx.citirti(rng, n / SR, 6)[:n] * 0.25
    tus = alcak_stereo(tus, 4800)
    muzik = tus * 1.3 + ped * 2.0 + dav * 0.6 + bs * 0.7 + ezgi + yanki(yank[:, 0] + yank[:, 1], 2.2, rng) * 0.9
    muzik[:, 0] += plak * 0.3; muzik[:, 1] += np.roll(plak, 811) * 0.3

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
    kk = int(0.12 * SR)
    duk = 1 - (1 - 10 ** (-3 / 20)) * np.clip(np.convolve(maske.astype(float), np.ones(kk) / kk, "same"), 0, 1)
    muzik *= duk[:, None]  # konuşurken 3 dB ek kısma
    sfx *= ref * 10 ** (-12 / 20) / max(rms(sfx[np.abs(sfx).sum(1) > 1e-6]), 1e-9)
    oda = yanki(vo, 0.6, rng, 3500) * 0.12  # sese hafif oda
    miks = vo[:, None] + oda + muzik + sfx
    miks -= alcak_stereo(miks, 25)  # 25 Hz altı kesilir
    f = int(0.02 * SR); miks[:f] *= np.linspace(0, 1, f)[:, None]
    f = int(0.9 * SR); miks[-f:] *= np.linspace(1, 0, f)[:, None] ** 1.5
    cikti.mkdir(parents=True, exist_ok=True)
    ortak_miks.kok_yaz(cikti, "efekt", sfx)  # kurgu bu sahnenin efektlerini buradan alır
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.9).astype(np.float32), SR)
    return {"seslendirme": bulunan}


def alcak_stereo(x: np.ndarray, kesim: float) -> np.ndarray:
    return np.stack([alcak(x[:, 0], kesim), alcak(x[:, 1], kesim)], 1)
