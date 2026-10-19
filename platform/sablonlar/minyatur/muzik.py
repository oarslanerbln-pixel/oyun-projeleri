"""Minyatür şablonunun sesi: rast makamında ince saz + avlu efektleri + seslendirme → miks.

Bölümler sahnelerden çıkar: açılışta serbest ney taksimi ve ud demi; ilk `avlu` sahnesiyle def
usulü (`cizim.usul`, defzenin eli de aynı listeden vurur), kanun ezgisi ve ud basları girer;
gece/kuyruk sahnesinde ezgi bir oktav çıkar, def dolgu vuruşları ve kalabalık uğultusu artar;
kapanışta davul susar, kanun rast dizisinde yukarı süzülür ve sol (Rast) akoru parlak bir zil
sesiyle çınlar. Uğultu avlunun doluluğuyla birlikte yükselir; misafir oturdukça hafif bardak
şıngırtıları duyulur. Rast'ın segâh ve eviç perdeleri çeyrek ses yaklaşımıyla çalınır.
Gerekenler: numpy, soundfile.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
import miks as ortak_miks  # noqa: E402  (platform/ortak/miks.py: kökler)
import sfx as fx  # noqa: E402  (platform/ortak/sfx.py: beyaz gürültüsüz efektler)

import cizim

SR = 48000
RAST = [0, 2, 3.5, 5, 7, 9, 10.5, 12]  # sol rast: sol la si(segâh) do re mi fa#(eviç) sol


def mtof(m): return 440 * 2 ** ((m - 69) / 12)


def perde(derece: int, kok: float = 67) -> float:
    o, d = divmod(derece, 7)
    return kok + 12 * o + RAST[d]


def kutu_suzgec(x, n):
    """kayan ortalama (alçak geçiren); n örnek"""
    n = max(1, int(n))
    c = np.cumsum(np.concatenate([[0.0], x]))
    y = (c[n:] - c[:-n]) / n
    return np.concatenate([y, np.full(n - 1, y[-1] if len(y) else 0.0)])


def zarf(d, a=0.003, dec=None):
    tt = np.arange(int(d * SR)) / SR
    e = np.minimum(tt / a, 1.0)
    return e * (np.exp(-tt / dec) if dec else 1.0), tt


def ekle(buf, t0, x, gain=1.0, pan=0.0):
    n = len(buf)
    i = int(t0 * SR)
    if i >= n:
        return
    if i < 0:
        x, i = x[-i:], 0
    x = x[: n - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:i + len(x), 0] += x * gain * l * 1.414
    buf[i:i + len(x), 1] += x * gain * r * 1.414


# ---------- sazlar ----------
def tel(m, d=1.2, parlak=0.5, kayip=0.4985, seed=0):
    """Karplus-Strong telli (ud: koyu, kanun: parlak); geri besleme blok blok vektörel"""
    N = max(2, int(round(SR / mtof(m))))
    L = int(d * SR)
    rng = np.random.default_rng(seed)
    y = np.zeros(L + N + 1)
    ates = rng.uniform(-1, 1, N)
    ates -= ates.mean()  # DC kalırsa döngüde neredeyse hiç sönmez
    ates = parlak * ates + (1 - parlak) * np.concatenate([[0.0], ates[:-1]])  # mızrap / tezene parlaklığı
    y[1:N + 1] = ates
    for i in range(N + 1, len(y), N):
        j = min(i + N, len(y))
        y[i:j] = kayip * (y[i - N:j - N] + y[i - N - 1:j - N - 1])
    y = y[1:L + 1]
    return y * np.clip((d - np.arange(L) / SR) / 0.04, 0, 1)


def ud(m, d=1.2, seed=0):
    return tel(m, d, 0.35, 0.4975, seed) * 0.9


def kanun(m, d=0.6, seed=0):
    x = tel(m, d, 0.75, 0.497, seed)
    ust = tel(m + 12, d * 0.6, 0.8, 0.496, seed + 500)  # oktav teli (kanunun çift telli parlaklığı)
    x[: len(ust)] += 0.35 * ust
    return x


def ney(m, d, gurultu_seed=0):
    """nefesli: hafif üst harmonikler, geç başlayan titreşim, süzülmüş nefes gürültüsü"""
    n = int(d * SR)
    tt = np.arange(n) / SR
    vib = 0.12 * np.sin(2 * np.pi * 5.2 * tt) * np.clip((tt - 0.25) / 0.3, 0, 1)
    f = mtof(m) * 2 ** (vib / 12)
    faz = 2 * np.pi * np.cumsum(f) / SR
    ton = np.sin(faz) + 0.28 * np.sin(2 * faz) + 0.1 * np.sin(3 * faz)
    rng = np.random.default_rng(gurultu_seed)
    g = rng.standard_normal(n)
    nefes = kutu_suzgec(g, 6) - kutu_suzgec(g, 40)
    e = np.clip(tt / 0.14, 0, 1) * np.clip((d - tt) / 0.25, 0, 1)
    return (ton * 0.8 + nefes * 1.6) * e * (0.85 + 0.15 * np.sin(2 * np.pi * 0.7 * tt))


def def_(tur, seed=0):
    rng = np.random.default_rng(seed)
    if tur == "dum":
        e, tt = zarf(0.45, a=0.001, dec=0.13)
        govde = np.sin(2 * np.pi * np.cumsum(78 + 55 * np.exp(-tt / 0.025)) / SR)
        deri = kutu_suzgec(rng.standard_normal(len(tt)), 12) * np.exp(-tt / 0.03)
        zil = _halka(0.25, seed) * 0.25
        x = govde * e + deri * 0.8
        x[: len(zil)] += zil
        return x
    e, tt = zarf(0.12 if tur == "tek" else 0.08, a=0.0006, dec=0.02 if tur == "tek" else 0.013)
    g = fx.renkli(len(tt), rng)  # pembe: beyaz gürültünün tiz cızırtısı yok
    x = (g - kutu_suzgec(g, 5)) * 1.0 + np.sin(2 * np.pi * 1150 * tt) * 0.35
    zil = _halka(0.22, seed + 7) * (0.5 if tur == "tek" else 0.3)
    x = x * e
    x[: len(zil)] += zil[: len(x)]
    return x * (1.0 if tur == "tek" else 0.6)


def _halka(d, seed):
    """defin çenesindeki halkaların şıngırtısı"""
    e, tt = zarf(d, a=0.001, dec=0.05)
    rng = np.random.default_rng(seed)
    g = fx.renkli(len(tt), rng)
    return ((g - kutu_suzgec(g, 3)) * 0.15 + sum(np.sin(2 * np.pi * f * tt) * 0.15 for f in (5300, 6900, 8100))) * e


def zil(d=1.4):
    """parmak zili: parlak, uzun çınlayan"""
    e, tt = zarf(d, a=0.001, dec=0.4)
    return sum(np.sin(2 * np.pi * f * tt) * w for f, w in ((2630, .5), (3950, .32), (5480, .22), (7120, .12))) * e


def bardak(seed):
    rng = np.random.default_rng(seed)
    e, tt = zarf(0.25, a=0.0005, dec=0.05)
    k = rng.uniform(0.9, 1.15)
    return sum(np.sin(2 * np.pi * f * k * tt) * w for f, w in ((3100, .5), (4700, .3), (6900, .15))) * e


def ugultu(n, egri, seed=3):
    """kalabalık sohbeti: konuşma bandına süzülmüş gürültü, rastgele hece zarfları, doluluğa bağlı"""
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    tt = np.arange(n) / SR
    for k in range(7):
        g = fx.renkli(n, rng)
        bant = kutu_suzgec(g, rng.integers(8, 14)) - kutu_suzgec(g, rng.integers(30, 60))
        hiz = rng.uniform(3.5, 5.5)
        hece = np.clip(np.sin(2 * np.pi * hiz * tt + rng.uniform(0, 6)) + np.sin(2 * np.pi * hiz * 0.37 * tt + rng.uniform(0, 6)), 0, None)
        out += bant * hece
    return out * egri


# ---------- düzenleme ----------
def bolumler(s: dict) -> dict:
    sb = cizim.sahne_bitisleri(s)
    ritim = next((b for x, b, _ in sb if x["tur"] == "avlu"), s["sure"])
    tepe = next((b for x, b, _ in sb if x["tur"] == "avlu" and (x.get("gece") or x.get("kuyruk"))), None)
    kap = next((b for x, b, _ in sb if x["tur"] == "kapanis"), s["sure"])
    return {"ritim": ritim, "tepe": tepe if tepe is not None else kap, "kapanis": kap}


def muzik_uret(s: dict, n: int) -> np.ndarray:
    m = np.zeros((n, 2))
    b = bolumler(s)
    sekiz = 30 / s["muzik"].get("bpm", 96)
    # açılış: ney taksimi + ud demi
    taksim = [(0.15, 0, 0.9), (0.95, 1, 0.45), (1.35, 2, 0.4), (1.7, 3, 0.7), (2.35, 2, 0.35), (2.65, 1, 0.5)]
    for i, (t0, d_, dur) in enumerate(taksim):
        if t0 < b["ritim"]:
            ekle(m, t0, ney(perde(d_), min(dur + 0.15, b["ritim"] - t0 + 0.2), i), 0.22, pan=-0.15)
    for t0, mm in ((0.1, 43), (0.13, 50), (0.16, 55)):
        ekle(m, t0, ud(mm, min(2.6, b["ritim"] + 0.4), int(mm)), 0.22, pan=0.1)
    # usul: def vuruşları (çizimdeki defzenle aynı liste)
    for an, tur in cizim.usul(s):
        guc = 1.0 if an >= b["tepe"] else 0.8
        ekle(m, an, def_(tur, int(an * 1000)), {"dum": 0.8, "tek": 0.55, "ke": 0.3}[tur] * guc, pan=0.25 if tur != "dum" else 0.05)
    # kanun ezgisi ve ud basları (ritim → kapanış)
    alt = [4, 3, 4, 5, 4, 3, 2, 3, 2, 1, 2, 3, 2, 1, 0, 1]
    ust = [7, 6, 7, 8, 7, 6, 5, 6, 5, 4, 5, 6, 7, 6, 5, 4]
    k = 0
    t = b["ritim"]
    while t < b["kapanis"] - 0.02:
        tepe = t >= b["tepe"]
        desen = ust if tepe else alt
        mm = perde(desen[k % 16])
        ekle(m, t, kanun(mm, 0.55, k), 0.34 if tepe else 0.3, pan=0.3)
        if tepe:
            ekle(m, t, kanun(mm - 12, 0.5, k + 900), 0.18, pan=-0.3)
        if k % 4 == 0:
            ekle(m, t, ud(perde([0, 3, 4, 0][(k // 4) % 4], 43), sekiz * 4.2, 300 + k), 0.42, pan=-0.1)
        k += 1
        t = b["ritim"] + k * sekiz
    # ney karşı ezgisi (uzun notalar)
    for t0, d_ in ((b["ritim"] + 0.1, 4), (b["ritim"] + 1.3, 3), (b["tepe"] + 0.05, 7), (b["tepe"] + 1.25, 8)):
        if t0 < b["kapanis"] - 0.3:
            ekle(m, t0, ney(perde(d_), min(1.2, b["kapanis"] - t0), int(t0 * 10)), 0.16, pan=-0.2)
    # kapanış: kanun süzülüşü, sol rast akoru, ney son notası
    kp = b["kapanis"]
    for j in range(15):
        ekle(m, kp - 0.32 + j * 0.022, kanun(perde(j), 0.5, 700 + j), 0.16, pan=-0.4 + j * 0.055)
    for j, mm in enumerate((43, 55, 62, 67, 71 - 0.5, 74, 79)):
        ekle(m, kp + 0.02 + j * 0.03, kanun(mm, 2.2, 800 + j) if j > 1 else ud(mm, 2.4, 800 + j), 0.24, pan=(j - 3) * 0.12)
    ekle(m, kp + 0.02, def_("dum", 4242), 0.9, pan=0.05)
    for j in range(int((s["sure"] - kp - 0.6) / (sekiz / 2))):  # kanun tremolosu: tepe sesinde sönerek
        ekle(m, kp + 0.35 + j * sekiz / 2, kanun(perde(7 + (j % 2) * -3), 0.4, 950 + j), 0.2 * math.exp(-j / 9), pan=0.25)
    ekle(m, kp + 0.3, ney(perde(7), max(0.6, s["sure"] - kp - 0.4), 99), 0.2)
    for ch in range(2):  # DC ve 20 Hz altı temizliği
        m[:, ch] -= kutu_suzgec(m[:, ch], SR // 20)
    return m


def efekt_uret(s: dict, n: int, c: "cizim.Cizici | None" = None) -> np.ndarray:
    sfx = np.zeros((n, 2))
    egri = np.array([cizim.doluluk(s, i / 100) for i in range(int(n / SR * 100) + 2)])
    egri = np.interp(np.arange(n) / SR * 100, np.arange(len(egri)), egri)
    sfx[:, 0] += ugultu(n, egri, 3) * 0.09  # kalabalık sürekli bir zemin: kısık kalmalı
    sfx[:, 1] += ugultu(n, egri, 4) * 0.09
    b = bolumler(s)
    if c is not None:
        for i, k in enumerate(c.koltuk):
            if 0 < k["oturma"] < s["sure"] and i % 2 == 0:
                ekle(sfx, k["oturma"] + 0.15, bardak(i), 0.1, pan=(k["x"] / c.VW - 0.5))
    for x, bas, _ in cizim.sahne_bitisleri(s):
        if x.get("kartus"):
            ekle(sfx, bas + 0.4, zil(1.1), 0.10, pan=0.2)
    ekle(sfx, b["kapanis"] + 0.5, zil(1.6), 0.13, pan=-0.1)
    return sfx


def miksle(s: dict, cikti: Path, seslendirme: Path | None) -> dict:
    import soundfile as sf
    sure = s["sure"]
    n = int(sure * SR)
    c = None
    try:
        c = cizim.Cizici(s, 1080, 1920)  # oturma anları (bardak sesleri) görüntüyle aynı hesaptan
    except Exception:  # noqa: BLE001 (yazı tipi indirilemezse bardak sesleri atlanır)
        c = None
    muzik = muzik_uret(s, n)
    sfx = efekt_uret(s, n, c)
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
    # konuşurken müzik ~6 dB ek kısılır (yumuşak yan zincir)
    kaba = np.abs(ses[::480])
    acik = (kutu_suzgec(kaba, 10) > 0.01).astype(float)
    acik = kutu_suzgec(np.maximum(acik, np.roll(acik, -8)), 20)
    duck = 1 - (1 - 10 ** (-6 / 20)) * np.clip(np.interp(np.arange(n) / 480, np.arange(len(acik)), acik), 0, 1)
    t_all = np.arange(n) / SR
    sonum = np.clip((sure - t_all) / 0.5, 0, 1)[:, None]
    giris = np.clip(t_all / 0.05, 0, 1)[:, None]
    yatak = (muzik * duck[:, None] + sfx) * sonum * giris
    fark = None
    konusma = np.abs(ses) > 0 if bulunan else None
    if bulunan and konusma.any():
        rms = lambda x: float(np.sqrt(np.mean(x ** 2)) + 1e-12)  # noqa: E731
        hedef = s["muzik"].get("ses_ustu_db", 8.0)
        yatak *= rms(ses[konusma]) / rms(yatak.mean(1)[konusma]) / 10 ** (hedef / 20)
        fark = 20 * math.log10(rms(ses[konusma]) / rms(yatak.mean(1)[konusma]))
    else:
        yatak *= 0.5
    miks = yatak + ses[:, None]
    cikti.mkdir(parents=True, exist_ok=True)
    ortak_miks.kok_yaz(cikti, "efekt", sfx)  # kurgu bu sahnenin efektlerini buradan alır
    sf.write(str(cikti / "ses.wav"), (miks / max(1e-9, np.abs(miks).max()) * 0.95).astype(np.float32), SR)
    return {"seslendirme": bulunan, "ses_ustu_db": fark}
