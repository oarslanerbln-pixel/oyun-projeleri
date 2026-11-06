"""Harita sinemasının sesi: her grafik hareketine oturan efekt + aynı tonda müzik yatağı.

Efektler sahne JSON'undan çıkarılır, kareyle aynı zaman formülleri kullanılır (ok başı ne zaman oturuyorsa
sıçrama sesi o karede). Hepsi sentez; beyaz gürültü yok (bkz. platform/ortak/sfx.py ve kalite.py hışırtı ölçüsü):
fırça sesi alçak-orta bantta, hıza göre açılıp kapanan kâğıt lifi taneleridir, tiz cızırtı üretmez.

Uyum kuralı: ezgili her efekt (şehir damlası, başlık glissandosu, mühür) müziğin gamından seçilir; vurgu davulları
müziğin akor köküyle aynı perdededir. Müzik 72 BPM, D minör pentatonik (gergin: taiko nabzı) ya da D majör
pentatonik (sakin). Pad'ler D3'ün altına inmez, uzun alçak sinüs yok (Le Mariage'daki uğultu dersi).
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np

import sfx as fx

SR = fx.SR
# stil → (ok hızı, etiket süresi); grafik.js'teki değerlerle aynı tutulmalı
STIL = {"firca": (0.75, 0.9), "haber": (0.65, 0.55), "gravur": (1.0, 1.1), "neon": (0.85, 0.6)}
GAM = {"gergin": [50, 53, 55, 57, 60], "sakin": [50, 52, 54, 57, 59]}  # D minör / D majör pentatonik (D3 tabanı)
AKOR = {"gergin": [[62, 65, 69, 76], [58, 62, 65, 69], [55, 62, 65, 70], [57, 60, 64, 69]],  # Dm9 · B♭maj7 · Gm7 · Am7
        "sakin": [[62, 66, 69, 76], [59, 62, 66, 69], [55, 62, 66, 71], [57, 61, 64, 69]]}   # D6/9 · Bm7 · Gmaj7 · A
BPM = 72.0


def mtof(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _t(sure: float) -> np.ndarray:
    return np.arange(int(sure * SR)) / SR


def _yumusat(x: np.ndarray, bas: float = 0.003, son: float = 0.02) -> np.ndarray:
    n = len(x)
    e = np.ones(n)
    a, b = min(n, int(bas * SR)), min(n, int(son * SR))
    if a:
        e[:a] = np.linspace(0, 1, a)
    if b:
        e[n - b:] *= np.linspace(1, 0, b)
    return x * e


# ------------------------------------------------------------------ çalgılar
def koto(nota: float, sure: float = 2.4, rng=0, kok: float = 1.0) -> np.ndarray:
    """Telli koparma: kısmi sesler üst sıradan hızlı söner, başta çok hafif perde bükülmesi (oshi), kısa tırnak sesi."""
    rng = np.random.default_rng(rng)
    t = _t(sure)
    f = mtof(nota)
    egim = t + 0.012 * 0.06 * (1 - np.exp(-t / 0.06))  # ilk 60 ms'de ~%1.2 tiz, sonra oturur
    x = np.zeros_like(t)
    for k in range(1, 12):
        fk = f * k * (1 + 0.0006 * k * k)
        if fk > 12000:
            break
        x += (kok if k == 1 else 1.0) * (1 / k ** 1.15) * (0.65 if k % 3 == 0 else 1.0) * np.sin(2 * np.pi * fk * egim + k) * np.exp(-t / (1.7 / (1 + 0.6 * (k - 1))))
    tirnak = fx.bant(fx.renkli(len(t), rng, -3.0), 1200, 4500) * np.exp(-t / 0.004) * 0.25
    return _yumusat(x * np.minimum(t / 0.0015, 1) + tirnak, 0.0005, 0.05)


def taiko(f: float = 110.0, sure: float = 1.0, rng=0, deri: float = 0.35) -> np.ndarray:
    """Büyük davul: perdesi hızla inen gövde + deri vuruşu. Gövde A2 civarı ve 0.2 sn söner: 73 Hz gibi alçak,
    uzun sinüs uğultu olarak duyuluyordu (Le Mariage), o yüzden kök hiç bu kadar inmez."""
    rng = np.random.default_rng(rng)
    t = _t(sure)
    faz = 2 * np.pi * np.cumsum(f * (1 + 0.7 * np.exp(-t / 0.025))) / SR
    govde = np.sin(faz) * np.exp(-t / 0.2) + 0.45 * np.sin(2.32 * faz) * np.exp(-t / 0.08)
    vurus = fx.bant(fx.renkli(len(t), rng, -4.5), 180, 1400) * np.exp(-t / 0.018)
    return _yumusat(govde + fx._normal(vurus) * deri)


def tahta(f: float = 820.0, rng=0) -> np.ndarray:
    """Tahta tık (birlik işareti): iki kısmi, 40 ms."""
    t = _t(0.12)
    return _yumusat(np.sin(2 * np.pi * f * t) * np.exp(-t / 0.035) + 0.5 * np.sin(2 * np.pi * f * 2.71 * t) * np.exp(-t / 0.012), 0.0005)


def darbe(sure: float, profil: str = "expo", rng=0) -> np.ndarray:
    """Mürekkep fırçasının kâğıttaki sesi. Gövde: renkli gürültü, merkezi hızla 450→1900 Hz kayar; üstünde kâğıt lifi
    taneleri. Ses fırçanın hızını izler: expo profilde başta güçlü, uca doğru söner (görüntüdeki darbeyle aynı)."""
    rng = np.random.default_rng(rng)
    n = int((sure + 0.12) * SR)
    t = np.arange(n) / SR
    p = np.clip(t / sure, 0, 1)
    if profil == "expo":
        v = 2.0 ** (-10 * p)
    else:  # eio: ortası hızlı
        v = np.sin(np.pi * p) ** 1.5
    v = v * np.minimum(t / 0.012, 1) * np.where(t > sure, np.exp(-(t - sure) / 0.03), 1)
    v /= v.max() + 1e-9
    govde = fx.kayan_suzgec(fx.renkli(n, rng, -4.0), 450 + 1450 * v, 0.8)
    lif = fx.hisirti(rng, n / SR, yogunluk=110, parlak=0.55)[:n]
    x = (fx._normal(govde) * 0.9 + lif * 0.35 * np.sqrt(v)) * v ** 0.8
    return fx.bant(x, 110, 2600)


def sicrama(rng=0) -> np.ndarray:
    """Islak mürekkep sıçraması: 60 ms'ye yayılmış küçük ıslak tıklar + alçak 'tup'."""
    rng = np.random.default_rng(rng)
    t = _t(0.35)
    out = np.sin(2 * np.pi * np.cumsum(140 * (1 + 0.8 * np.exp(-t / 0.01))) / SR) * np.exp(-t / 0.05) * 0.8
    for _ in range(7):
        tk = fx.tik(rng, rng.uniform(700, 1900), rng.uniform(0.004, 0.01)) * rng.uniform(0.25, 0.6)
        i = int(rng.uniform(0, 0.07) * SR)
        out[i: i + len(tk)] += tk[: len(out) - i]
    return _yumusat(fx.bant(out, 60, 3500))


def damga(rng=0) -> np.ndarray:
    """Hanko mührü: tahta sapın masaya inişi (tok, kısa) + kâğıdın hafif sesi."""
    rng = np.random.default_rng(rng)
    t = _t(0.5)
    tok = np.sin(2 * np.pi * np.cumsum(175 * (1 + 0.5 * np.exp(-t / 0.008))) / SR) * np.exp(-t / 0.07)
    klik = np.sin(2 * np.pi * 1150 * t) * np.exp(-t / 0.01) * 0.35
    kagit = np.zeros_like(t)
    h = fx.hisirti(rng, 0.18, yogunluk=60, parlak=0.6)
    kagit[: len(h)] = h * 0.18
    return _yumusat(fx.bant(tok + klik + kagit, 70, 4000))


def hava(sure: float, rng=0) -> np.ndarray:
    """Kamera hareketi: alçak, yavaş hava; tepesi 1 kHz'i geçmez (tıslama yok)."""
    return fx.whoosh(rng, max(0.6, sure), yukari=True, alt=110, ust=950, q=0.9)


# ------------------------------------------------------------------ olaylar
def _baslik_a(s: dict) -> float:
    return float((s.get("yazi") or {}).get("baslikZaman", [0.4])[0])


def olaylar(s: dict) -> list[dict]:
    """Sahneden ses olayları: {t, tur, ...}. Zamanlar sahne.js / grafik.js'teki formüllerle aynıdır."""
    hiz, etiket = STIL.get(s.get("grafik", ""), (1.0, 1.1))
    Y = s.get("yazi") or {}
    o: list[dict] = []
    if Y.get("baslik"):
        a = _baslik_a(s)
        if Y.get("ust"):
            o.append({"t": a, "tur": "damga"})
        o.append({"t": a + 0.15, "tur": "darbe", "sure": 0.6, "kaz": 0.8})
        o.append({"t": a + 0.25, "tur": "baslik"})
    tarih = Y.get("tarih")
    if isinstance(tarih, list):
        o += [{"t": float(d["t"]), "tur": "sayfa"} for d in tarih if float(d.get("t", 0)) > 0.5]
    kam = s.get("kamera") or []
    for k0, k1 in zip(kam, kam[1:]):
        if k1["t"] - k0["t"] >= 1.5:
            o.append({"t": k0["t"], "tur": "hava", "sure": k1["t"] - k0["t"]})
    sehir_i = 0
    for k in sorted(s.get("katmanlar", []), key=lambda k: (k.get("t") or [0])[0]):
        a0 = float((k.get("t") or [0])[0])
        tip = k.get("tip")
        if tip == "ok":
            d = float(k.get("cizim", 2.2)) * hiz
            o.append({"t": a0, "tur": "darbe", "sure": d})
            o.append({"t": a0 + 0.29 * d, "tur": "sicrama"})
            o.append({"t": a0 + 0.27 * d, "tur": "vurgu"})
        elif tip == "rota":
            o.append({"t": a0, "tur": "darbe", "sure": float(k.get("cizim", 3.0)), "profil": "eio", "kaz": 0.7})
        elif tip == "cephe":
            o.append({"t": a0, "tur": "vurgu", "kaz": 1.2})
            o.append({"t": a0 + 0.05, "tur": "darbe", "sure": 0.8, "kaz": 0.7})
            for d in (k.get("durumlar") or [])[1:]:
                o.append({"t": float(d["t"]) - 0.4, "tur": "hava", "sure": 1.4, "kaz": 0.55})
        elif tip == "sehir":
            o.append({"t": a0, "tur": "damla", "sira": sehir_i, "onem": k.get("onem")})
            sehir_i += 1
        elif tip in ("ulke", "bolge"):
            o.append({"t": a0 + 0.5, "tur": "darbe", "sure": etiket * 0.8, "kaz": 0.55})
        elif tip == "deniz":
            o.append({"t": a0, "tur": "damla", "sira": -2})
        elif tip == "nabiz":
            o += [{"t": a0 + i * 60 / BPM, "tur": "nabiz", "kaz": 1 - 0.25 * i} for i in range(2)]
        elif tip == "birlik":
            o.append({"t": a0, "tur": "tahta"})
        elif tip == "not":
            o.append({"t": a0, "tur": "darbe", "sure": 0.55, "kaz": 0.6})
            o.append({"t": a0, "tur": "damga", "kaz": 0.7})
        elif tip == "yolyazi":
            o.append({"t": a0, "tur": "darbe", "sure": float(k.get("sure", 1.4)), "profil": "eio", "kaz": 0.4})
        elif tip == "kart":
            o.append({"t": a0 + 0.3, "tur": "darbe", "sure": 0.6, "kaz": 0.75})
            o.append({"t": a0 + 0.8, "tur": "damga"})
    return sorted(o, key=lambda e: e["t"])


def ruh(s: dict) -> str:
    """Cephe ya da askerî birlik varsa gergin (minör + taiko nabzı), yoksa sakin (majör pentatonik)."""
    return "gergin" if any(k.get("tip") in ("cephe", "birlik") for k in s.get("katmanlar", [])) else "sakin"


# ------------------------------------------------------------------ miks
class Iz:
    def __init__(self, sure: float):
        self.x = np.zeros((int((sure + 3) * SR), 2))

    def ekle(self, t: float, sig: np.ndarray, kaz: float = 1.0, pan: float = 0.0):
        i = int(round(t * SR))
        if i >= len(self.x) or len(sig) == 0:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        n = min(len(sig), len(self.x) - i)
        sol, sag = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        self.x[i: i + n, 0] += sig[:n] * kaz * sol * 1.414
        self.x[i: i + n, 1] += sig[:n] * kaz * sag * 1.414


def oda(x: np.ndarray, sure: float = 0.9, islak: float = 0.15, rng=0) -> np.ndarray:
    """Küçük oda: kısa, karanlık yansıma (anlatımda yankı istenmez; burada yalnız müzik ve efekti birbirine bağlar)."""
    rng = np.random.default_rng(rng)
    t = _t(sure)
    out = np.copy(x)
    for c in range(2):
        ir = fx.bant(rng.standard_normal(len(t)), None, 3200) * np.exp(-t / (sure / 6.9))
        ir /= math.sqrt(float(np.sum(ir ** 2))) + 1e-12
        m = 1 << int(math.ceil(math.log2(len(x) + len(ir))))
        out[:, c] += islak * np.fft.irfft(np.fft.rfft(x[:, c], m) * np.fft.rfft(ir, m), m)[: len(x)]
    return out


def muzik(s: dict, sure: float, mod: str, olay: list[dict]) -> np.ndarray:
    """72 BPM yatak: pad + koto arpeji (+ gerginde taiko nabzı). Enerji ilk harita hareketiyle yükselir."""
    iz = Iz(sure)
    vurus = 60 / BPM
    olcu = vurus * 4
    akorlar = AKOR[mod]
    ilk = min([e["t"] for e in olay if e["tur"] in ("darbe", "vurgu") and e["t"] > 2] or [sure * 0.4])
    enerji = lambda t: 0.45 + 0.55 * min(1.0, max(0.0, (t - ilk + 1.0) / 2.0))  # noqa: E731
    rng = np.random.default_rng(7)
    n_olcu = int(math.ceil(sure / olcu)) + 1
    desen = [0, 2, 1, 3, 2, 1, 3, 2]  # sekizlik arpej sırası (akor notalarının indeksi)
    for b in range(n_olcu):
        t0 = b * olcu
        ak = akorlar[b % len(akorlar)]
        # pad: D3 altına inmez; ölçüler üst üste biner, kesik duyulmaz
        tt = _t(olcu + 1.6)
        e = np.minimum(tt / 0.9, 1) * np.minimum(np.maximum(olcu + 1.6 - tt, 0) / 1.4, 1)
        pad = sum(np.sin(2 * np.pi * mtof(k) * (1 + d) * tt + k) for k in ak for d in (-0.0015, 0.0015))
        pad = fx.bant(pad, 140, 1400) * e / (len(ak) * 2)
        iz.ekle(t0 - 0.3, pad, 0.22)
        # kök: koparılmış alçak koto (sönen), uzun sinüs yok
        iz.ekle(t0, koto(ak[0] - 12, 1.8, rng=b, kok=0.45), 0.3 * enerji(t0), -0.1)
        for i in range(8):
            ti = t0 + i * vurus / 2
            if ti > sure - 1.2:
                break
            if rng.random() > 0.35 + 0.5 * enerji(ti) or (i % 2 and enerji(ti) < 0.6):
                continue
            nota = ak[desen[i] % len(ak)] + (12 if i in (3, 6) else 0)
            iz.ekle(ti + rng.uniform(-0.008, 0.008), koto(nota, 2.0, rng=b * 8 + i), 0.16 * (0.7 + 0.3 * rng.random()) * enerji(ti),
                    0.35 if i % 2 else -0.3)
        if mod == "gergin":
            for i, kaz in ((0, 0.55), (2, 0.25), (2.5, 0.2), (3.5, 0.18)):
                ti = t0 + i * vurus
                if ti < ilk - 0.5 or ti > sure - 1.0:
                    continue
                iz.ekle(ti, taiko(mtof(ak[0] - 17), rng=b * 4 + int(i * 2)), kaz * 0.8 * enerji(ti))
    # kapanış: kök akor koto ile tek tek, son 1.2 sn sönerek
    son = akorlar[0]
    for j, k in enumerate(son):
        iz.ekle(sure - 1.6 + j * 0.06, koto(k, 2.5, rng=90 + j), 0.18, -0.4 + j * 0.25)
    x = iz.x[: int(sure * SR)]
    fade = np.ones(len(x))
    m = int(1.0 * SR)
    fade[-m:] = np.linspace(1, 0, m) ** 1.5
    return x * fade[:, None]


def efektler(s: dict, sure: float, mod: str, olay: list[dict]) -> np.ndarray:
    iz = Iz(sure)
    gam = GAM[mod]
    for j, e in enumerate(olay):
        t, tur, kaz = e["t"], e["tur"], e.get("kaz", 1.0)
        pan = ((j * 0.37) % 1.0 - 0.5) * 0.5
        if tur == "darbe":
            iz.ekle(t, darbe(e["sure"], e.get("profil", "expo"), rng=j), 0.55 * kaz, pan)
        elif tur == "sicrama":
            iz.ekle(t, sicrama(rng=j), 0.5 * kaz, pan)
        elif tur == "vurgu":  # ok başı oturunca / cephe çizilince: akor kökünde taiko
            iz.ekle(t, taiko(mtof(gam[0] - 5), rng=j, deri=0.5), 0.7 * kaz)
        elif tur == "damga":
            iz.ekle(t + 0.12, damga(rng=j), 0.6 * kaz, pan)
        elif tur == "baslik":  # başlık: fırça swash'ıyla birlikte yükselen üç nota + taiko
            for i, k in enumerate((0, 2, 4)):
                iz.ekle(t + i * 0.07, koto(gam[k] + 24, 2.4, rng=50 + i), 0.22, -0.3 + i * 0.3)
            iz.ekle(t + 0.05, taiko(mtof(gam[0] - 5), rng=j, deri=0.4), 0.5)
        elif tur == "damla":  # şehir mürekkep damlası: gamdan yükselen nota, önemli şehir bir oktav + çift
            sira = e.get("sira", 0)
            k = gam[sira % len(gam)] + 24 + 12 * (sira // len(gam)) if sira >= 0 else gam[0] + 12
            iz.ekle(t, koto(k, 2.2, rng=j), 0.24 * kaz, ((sira * 0.41) % 1 - 0.5) * 0.8)
            if e.get("onem") == 1:
                iz.ekle(t + 0.09, koto(k + 12, 1.6, rng=j + 1), 0.12, 0.2)
        elif tur == "nabiz":
            iz.ekle(t, taiko(mtof(gam[0]), 0.8, rng=j, deri=0.15), 0.4 * kaz)
        elif tur == "tahta":
            iz.ekle(t, tahta(mtof(gam[2] + 24) * 1.0), 0.22 * kaz, pan)
        elif tur == "sayfa":
            h = fx.hisirti(j, 0.3, yogunluk=70, parlak=0.6)
            iz.ekle(t - 0.1, fx.bant(h, 200, 3000), 0.2 * kaz, pan)
            iz.ekle(t, koto(gam[3] + 12, 1.6, rng=j), 0.14)
        elif tur == "hava":
            iz.ekle(t, hava(e["sure"], rng=j), 0.16 * kaz)
    return iz.x[: int(sure * SR)]


def uret(s: dict, cikti: Path, lufs: float = -14.0) -> dict:
    """Sahnenin ses izini yazar (48 kHz stereo WAV, loudnorm). Döndürür: olay sayısı, ruh hâli, hışırtı ölçüsü."""
    sure = float(s["sure"])
    olay = olaylar(s)
    mod = ruh(s)
    m = muzik(s, sure, mod, olay)
    e = efektler(s, sure, mod, olay)
    x = oda(m * 0.5 + e * 0.9, 0.9, 0.12)
    x = np.stack([fx.bant(x[:, c], 50, None) for c in range(2)], axis=1)  # 50 Hz altı yalnız uğultu taşır
    x /= np.max(np.abs(x)) + 1e-9
    cikti = Path(cikti)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    # ham örnekler ffmpeg'e borudan gider (soundfile bağımlılığı yok)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af",
                    f"loudnorm=I={lufs}:TP=-1.5:LRA=11", "-ar", str(SR), "-c:a", "pcm_s24le", str(cikti)],
                   input=(x * 0.7).astype("<f4").tobytes(), check=True)
    return {"olay": len(olay), "ruh": mod, "hisirti": fx.gurultu_analizi(x)}


def ekle(video: Path, wav: Path, cikti: Path) -> Path:
    """Sessiz videoya ses izini ekler (görüntü yeniden kodlanmaz)."""
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(cikti)], check=True)
    return cikti
