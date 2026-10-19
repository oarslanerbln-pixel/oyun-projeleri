"""İki stil testinin müziği (numpy ile sentez, telifsiz). Aynı dosya iki test klasöründe de var.

  python3 muzik.py gercekci CIKTI.wav   # LÉVA: sıcak pad + keçeli piyano, ışık süpürmesinde cam parıltısı
  python3 muzik.py ebru     CIKTI.wav   # Desenhane: Hicaz kanun arpejleri (Karplus-Strong), ney benzeri dem, damla sesleri
Çıktı 48 kHz stereo; sonra ffmpeg loudnorm ile -14 LUFS / -1.5 dBTP.
"""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR, SURE = 48000, 10.0
N = int(SR * SURE)
rng = np.random.default_rng(5)


def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def bos(): return np.zeros((N, 2), np.float32)


def ekle(buf, t0, x, g=1.0, pan=0.0):
    i = int(t0 * SR); x = x[: max(0, N - i)]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(x), 0] += x * g * l; buf[i:i + len(x), 1] += x * g * r


def filtre(x, lo=None, hi=None, o=2):
    if lo and hi: sos = butter(o, [lo, hi], 'band', fs=SR, output='sos')
    elif lo: sos = butter(o, lo, 'high', fs=SR, output='sos')
    else: sos = butter(o, hi, 'low', fs=SR, output='sos')
    return sosfilt(sos, x, axis=0)


def pad(f, d, a=1.2, r=1.5):
    t = np.arange(int(d * SR)) / SR
    x = sum(np.sin(2 * np.pi * f * (1 + dt) * t + rng.uniform(0, 6)) for dt in (-0.003, 0, 0.0035))
    x += 0.3 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(1, t / a) * np.minimum(1, (d - t) / r).clip(0)
    return (x * env / 3).astype(np.float32)


def piyano(f, d=2.5):
    t = np.arange(int(d * SR)) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) * (0.6 ** (k - 1)) * np.exp(-t * (1.6 + 1.2 * k)) for k in range(1, 6))
    return (x * np.minimum(1, t / 0.004)).astype(np.float32)


def kanun(f, d=2.0, parlak=0.5):
    """Karplus-Strong telli çalgı."""
    n = int(d * SR); p = int(SR / f)
    buf = rng.uniform(-1, 1, p); out = np.zeros(n, np.float32)
    for i in range(n):
        v = buf[i % p]; out[i] = v
        buf[i % p] = 0.996 * (parlak * v + (1 - parlak) * 0.5 * (v + buf[(i + 1) % p]))
    return out


def ney(f, d):
    t = np.arange(int(d * SR)) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t / 0.8)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    x = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    nefes = filtre(rng.standard_normal(len(t)), f * 0.8, f * 3.5) * 0.25
    env = np.minimum(1, t / 0.5) * np.minimum(1, (d - t) / 0.8).clip(0)
    return ((x + nefes) * env * 0.4).astype(np.float32)


def damla(f=1400, g=1.0):
    t = np.arange(int(0.25 * SR)) / SR
    fr = f * (1 + 1.2 * np.exp(-t * 40))
    return (np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 22) * g).astype(np.float32)


def parilti(d, lo=3000, hi=9000):
    x = filtre(rng.standard_normal(int(d * SR)), lo, hi)
    t = np.arange(len(x)) / SR
    return (x * np.sin(np.pi * t / d) ** 2 * 0.25).astype(np.float32)


def vurus(f=55, d=1.2):
    t = np.arange(int(d * SR)) / SR
    return (np.sin(2 * np.pi * np.cumsum(f * (1 + 1.5 * np.exp(-t * 25))) / SR) * np.exp(-t * 4)).astype(np.float32)


def yanki(buf, gec=0.23, fb=0.32, mix=0.25):
    out = buf.copy(); d = int(gec * SR)
    for k in range(1, 6):
        g = mix * fb ** (k - 1); out[d * k:, 0] += buf[:-d * k, 1] * g; out[d * k:, 1] += buf[:-d * k, 0] * g
    return out


def gercekci():
    m, s = bos(), bos()
    akor = [(0.0, 3.6, [50, 57, 61, 64, 66]), (3.6, 7.2, [47, 54, 57, 62, 64]), (7.2, 10.0, [43, 50, 54, 59, 62, 69])]
    for t0, t1, notalar in akor:
        for n in notalar: ekle(m, t0, pad(mtof(n), t1 - t0 + 0.8), 0.09, rng.uniform(-0.5, 0.5))
    # keçeli piyano motifi
    motif = [(0.6, 74), (1.2, 73), (1.8, 69), (2.7, 66), (3.9, 71), (4.5, 69), (5.1, 66), (6.0, 64), (7.25, 74), (8.0, 78), (8.6, 76), (9.1, 74)]
    for t, n in motif: ekle(m, t, piyano(mtof(n)), 0.16, rng.uniform(-0.3, 0.3))
    ekle(m, 7.2, piyano(mtof(38), 3.0), 0.22)
    m = filtre(m, hi=9000)
    ekle(s, 0.3, parilti(3.4), 0.9, 0.0)        # şerit ışığın camda süpürmesi
    ekle(s, 7.15, vurus(48, 1.6), 0.5)          # geri çekiliş
    ekle(s, 8.0, piyano(mtof(90), 1.5), 0.05, 0.4)
    return yanki(m + s, 0.31, 0.35, 0.22)


def ebru():
    m, s = bos(), bos()
    # Hicaz (re): re mi♭ fa# sol la si♭ do re
    H = [62, 63, 66, 67, 69, 70, 72, 74]
    ekle(m, 0.0, pad(mtof(38), 10.0, 1.5, 1.5), 0.08)       # dem
    ekle(m, 0.0, pad(mtof(45), 10.0, 2.0, 1.5), 0.04)
    ekle(m, 2.8, ney(mtof(74), 2.6), 0.30, -0.2)
    ekle(m, 5.4, ney(mtof(70), 1.0), 0.22, -0.2); ekle(m, 6.3, ney(mtof(69), 1.4), 0.22, -0.2)
    ekle(m, 7.6, ney(mtof(66), 1.1), 0.22, -0.2); ekle(m, 8.6, ney(mtof(62), 1.4), 0.26, -0.2)
    # kanun arpejleri (hızlanan, gelgitte yoğun)
    t, i = 0.35, 0
    desen = [0, 2, 4, 7, 4, 2, 3, 1]
    while t < 7.4:
        n = H[desen[i % len(desen)]] + (12 if 4.4 < t < 6.7 and i % 3 == 0 else 0)
        ekle(m, t, kanun(mtof(n), 1.6), 0.20, 0.35 * np.sin(i)); i += 1
        t += 0.30 if t < 4.4 else 0.15 if t < 6.7 else 0.25
    for k, n in enumerate([50, 57, 62, 66, 69, 74]):
        ekle(m, 8.05 + 0.06 * k, kanun(mtof(n), 2.2, 0.6), 0.22, -0.5 + 0.2 * k)
    # bendir (kalp atışı gibi yumuşak)
    for t in np.arange(0.4, 7.4, 1.2): ekle(m, t, vurus(60, 0.6), 0.18); ekle(m, t + 0.45, vurus(70, 0.4), 0.10)
    ekle(m, 8.05, vurus(50, 1.5), 0.35)
    # damlalar: battal serpintisinin bir kısmı + halka damlaları
    for t in sorted(rng.uniform(0.3, 2.9, 14)): ekle(s, t, damla(rng.uniform(900, 1700)), 0.10, rng.uniform(-0.7, 0.7))
    for k in range(3):
        for j in range(6): ekle(s, 3.0 + 0.09 * k + 0.2 * j, damla(1100 + 120 * j), 0.11, -0.5 + 0.5 * k)
    # iğne/tarak: su yüzeyinde fısıltı
    ekle(s, 4.4, parilti(1.4, 1200, 4000), 0.6, -0.3); ekle(s, 5.8, parilti(0.95, 1500, 5000), 0.6, 0.3)
    return yanki(m + s, 0.27, 0.3, 0.2)


if __name__ == '__main__':
    x = gercekci() if sys.argv[1] == 'gercekci' else ebru()
    fade = np.minimum(1, (SURE - np.arange(N) / SR) / 0.6)[:, None]
    x = x * fade; x = x / (np.abs(x).max() + 1e-9) * 0.7
    wavfile.write(sys.argv[2], SR, x.astype(np.float32))
