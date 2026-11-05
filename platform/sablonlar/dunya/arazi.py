"""Gerçek arazi: yükseklik + deniz derinliği karoları -> eşdikdörtgen yükseklik, gölgelendirme ve stil dokuları.

    python3 platform/sablonlar/dunya/arazi.py dunya              # z5 dünya (8192×4096) yükseklik önbelleği
    python3 platform/sablonlar/dunya/arazi.py bolge -12 28 48 62  # z7 bölge yaması (boylam0 enlem0 boylam1 enlem1)
    python3 platform/sablonlar/dunya/arazi.py doku kure           # kaplama dokusu (dunya + varsa bölge yamaları)

Kaynak: AWS Open Data "Terrain Tiles" (Mapzen/Tilezen terrarium biçimi; SRTM, GMTED, ETOPO1 ve diğerleri).
Teslimde künye: "Arazi: Mapzen Terrain Tiles (SRTM, GMTED, ETOPO1...)". Karolar ve dokular önbellekte
(`$STUDYO_ONBELLEK` ya da ~/.cache/studyo/arazi), repoya girmez.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

KARO = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
ONBELLEK = Path(os.environ.get("STUDYO_ONBELLEK", Path.home() / ".cache" / "studyo")) / "arazi"
MERC_LAT = 85.0511287798


def _karo(z: int, x: int, y: int) -> np.ndarray:
    yol = ONBELLEK / "karo" / str(z) / str(x) / f"{y}.png"
    if not yol.exists():
        yol.parent.mkdir(parents=True, exist_ok=True)
        for deneme in range(4):
            try:
                with urllib.request.urlopen(KARO.format(z=z, x=x, y=y), timeout=60) as r:
                    veri = r.read()
                break
            except Exception:
                if deneme == 3:
                    raise
        yol.write_bytes(veri)
    a = np.asarray(Image.open(yol).convert("RGB"), dtype=np.float32)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768


def _merc_y(lat):
    lat = np.clip(lat, -MERC_LAT, MERC_LAT)
    return (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / math.pi) / 2


def yukseklik(z: int, kutu=(-180, -90, 180, 90), en: int = 8192) -> tuple[np.ndarray, tuple]:
    """kutu (boylam0, enlem0, boylam1, enlem1) için eşdikdörtgen yükseklik (m); genişlik `en` piksel"""
    lo0, la0, lo1, la1 = kutu
    n = 2 ** z
    x0, x1 = int(math.floor((lo0 + 180) / 360 * n)), int(math.ceil((lo1 + 180) / 360 * n)) - 1
    y0 = int(math.floor(_merc_y(min(la1, MERC_LAT)) * n)); y1 = int(math.ceil(_merc_y(max(la0, -MERC_LAT)) * n)) - 1
    x1, y1 = min(x1, n - 1), min(y1, n - 1)
    isler = [(z, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
    with ThreadPoolExecutor(24) as ex:
        karolar = list(ex.map(lambda a: _karo(*a), isler))
    M = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.float32)
    for (zz, x, y), k in zip(isler, karolar):
        M[(y - y0) * 256:(y - y0 + 1) * 256, (x - x0) * 256:(x - x0 + 1) * 256] = k
    boy = int(round(en * (la1 - la0) / (lo1 - lo0)))
    # satırlar: enlem -> mercator y (doğrusal ara değer); sütunlar: boylam doğrusal
    lat = la1 - (np.arange(boy) + 0.5) / boy * (la1 - la0)
    my = _merc_y(lat) * n * 256 - y0 * 256 - 0.5
    lon = lo0 + (np.arange(en) + 0.5) / en * (lo1 - lo0)
    mx = (lon + 180) / 360 * n * 256 - x0 * 256 - 0.5
    my = np.clip(my, 0, M.shape[0] - 1.001); mx = np.clip(mx, 0, M.shape[1] - 1.001)
    r0 = np.floor(my).astype(int); fr = (my - r0)[:, None]
    c0 = np.floor(mx).astype(int); fc = (mx - c0)[None, :]
    A = M[r0][:, c0] * (1 - fc) + M[r0][:, c0 + 1] * fc
    B = M[r0 + 1][:, c0] * (1 - fc) + M[r0 + 1][:, c0 + 1] * fc
    E = A * (1 - fr) + B * fr
    # mercatorun dışı (kutuplar): en yakın satır zaten kırpıldı; Antarktika iç kısmı yaklaşık kalır
    return E.astype(np.float32), (lo0, la0, lo1, la1)


def golge(E: np.ndarray, kutu, abart: float = 1.0, yonler=((315, 45, 0.6), (270, 50, 0.25), (0, 60, 0.15))) -> np.ndarray:
    """çok yönlü gölgelendirme 0..1 (0.5 düz). Piksel boyu enleme göre metre."""
    lo0, la0, lo1, la1 = kutu
    h, w = E.shape
    dx_der = (lo1 - lo0) / w
    lat = la1 - (np.arange(h) + 0.5) / h * (la1 - la0)
    mx = (dx_der * 111320 * np.cos(np.radians(lat)))[:, None].clip(50)
    my = (la1 - la0) / h * 110540
    Z = np.maximum(E, 0) * abart  # yalnız kara
    gy, gx = np.gradient(Z)
    gx = gx / mx; gy = gy / my
    egim = np.arctan(np.hypot(gx, gy))
    bakis = np.arctan2(gy, -gx)  # ESRI: atan2(dz/dy (güney+), -dz/dx)
    S = np.zeros_like(E)
    for az, alt, a in yonler:
        az_r, alt_r = math.radians(360 - az + 90), math.radians(alt)
        S += a * (math.sin(alt_r) * np.cos(egim) + math.cos(alt_r) * np.sin(egim) * np.cos(az_r - bakis))
    return np.clip(S, 0, 1)


def _kaydet(dizi: np.ndarray, ad: str) -> Path:
    yol = ONBELLEK / ad
    yol.parent.mkdir(parents=True, exist_ok=True)
    np.save(yol, dizi.astype(np.float16))
    return yol.with_suffix(".npy")


def dunya(en: int = 8192) -> Path:
    E, kutu = yukseklik(5, (-180, -85, 180, 85), en)
    # tam küre için kutup bantlarını ekle (85..90): son satırı uzat
    h = int(round(en / 2)); ek = (h - E.shape[0]) // 2
    E = np.pad(E, ((ek, h - E.shape[0] - ek), (0, 0)), mode="edge")
    return _kaydet(E, f"dunya-{en}")


def bolge(kutu, z: int = 7, en: int = 6144) -> Path:
    E, kutu = yukseklik(z, tuple(kutu), en)
    ad = "bolge-" + "_".join(f"{v:g}" for v in kutu)
    (ONBELLEK / f"{ad}.json").parent.mkdir(parents=True, exist_ok=True)
    (ONBELLEK / f"{ad}.json").write_text(json.dumps({"kutu": kutu, "z": z}))
    return _kaydet(E, ad)


# ---------------- kaplama dokuları ----------------
def _rampa(deger, duraklar):
    """deger dizisini [(eşik, (r,g,b))] rampasıyla renklendir"""
    xs = np.array([d[0] for d in duraklar], np.float32)
    out = np.zeros(deger.shape + (3,), np.float32)
    for k in range(3):
        out[..., k] = np.interp(deger, xs, np.array([d[1][k] for d in duraklar], np.float32))
    return out


def _gurultu(sekil, tohum=1, olcek=1.0):
    r = np.random.default_rng(tohum)
    return r.standard_normal(sekil).astype(np.float32) * olcek


def kara_maskesi(kutu, w: int, h: int) -> np.ndarray:
    """Natural Earth 1:50m ülke halkalarından kara maskesi (vektör kıyılarla aynı çizgi)"""
    from PIL import ImageDraw
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ortak"))
    import harita
    lo0, la0, lo1, la1 = kutu
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for u in harita.veri()["ulkeler"]:
        for halka in u["h"]:
            d.polygon([((q[0] - lo0) / (lo1 - lo0) * w, (la1 - q[1]) / (la1 - la0) * h) for q in halka], fill=255)
    return np.asarray(im) > 127


def doku(kaplama: str, E: np.ndarray, kutu) -> Image.Image:
    kara = kara_maskesi(kutu, E.shape[1], E.shape[0])
    E = np.where(kara, np.maximum(E, 1), np.minimum(E, -1))
    S = golge(E, kutu, abart=1.6)
    S = S - golge(np.zeros((3, 3), np.float32), kutu)[1, 1] + 0.55  # düz zemin = 0.55 (rampalar bunu nötr sayar)
    if kaplama == "kure":
        deniz = _rampa(E, [(-8000, (5, 12, 28)), (-4000, (8, 20, 42)), (-1500, (11, 28, 54)), (-200, (16, 40, 70)), (-1, (22, 52, 84))])
        karar = _rampa(E, [(0, (40, 50, 62)), (500, (46, 56, 68)), (1500, (62, 72, 84)), (3500, (104, 112, 122)), (6000, (150, 156, 164))])
        ish = (S - 0.55)[..., None]
        renk = np.where(kara[..., None], karar * (1 + ish * 2.0), deniz)
    elif kaplama == "atlas":
        # deniz: hafif basamaklı derinlik (gravür atlas), kara: sıcak kâğıt + belirgin gölgelendirme
        seviye = np.searchsorted(np.array([-5000, -3000, -1500, -200]), E)
        deniz = np.array([(178, 196, 204), (188, 204, 210), (198, 212, 216), (208, 220, 222), (220, 229, 228)], np.float32)[seviye]
        karar = _rampa(E, [(0, (240, 231, 210)), (800, (232, 219, 194)), (2500, (218, 200, 170)), (5000, (205, 186, 156))])
        ish = (S - 0.55)[..., None]
        renk = np.where(kara[..., None], karar * (1 + ish * 1.9), deniz)
        renk += _gurultu(E.shape, 5, 2.0)[..., None]
    elif kaplama == "kagit":
        # katmanlar: derinlik ve yükseklik eşikleri; her katman üstündekine gölge düşürür
        esik = [-6000, -4000, -2500, -1000, -150, 0, 600, 1600, 3000]
        renkler = [(38, 92, 102), (47, 104, 114), (60, 118, 126), (79, 136, 140), (104, 158, 157), (135, 182, 176),
                   (244, 236, 220), (236, 224, 202), (226, 210, 184), (214, 196, 168)]
        seviye = np.searchsorted(np.array(esik), E).astype(np.int16)
        renk = np.array(renkler, np.float32)[seviye]
        # gölge: ışık sol üstten; daha yüksek seviyenin sağ alt tarafa düşen gölgesi
        h, w = E.shape
        px = max(2, int(round(w / 8192 * 5)))
        golgem = np.zeros((h, w), np.float32)
        for k in range(1, 6):
            kay = np.roll(np.roll(seviye, px * k // 2, axis=0), px * k // 2, axis=1)
            golgem += (kay > seviye) * (0.16 / k)
        renk *= (1 - np.clip(golgem, 0, 0.45))[..., None]
        # katman kenarında ince açık çizgi (kesik kâğıt kenarı)
        ust = np.roll(np.roll(seviye, -1, axis=0), -1, axis=1)
        renk += ((seviye > ust) * 18)[..., None]
        renk *= (1 + (S - 0.55) * np.where(kara, 0.35, 0))[..., None]
        renk += _gurultu(E.shape, 3, 3.5)[..., None]
    else:
        raise SystemExit(f"doku yok: {kaplama}")
    return Image.fromarray(np.clip(renk, 0, 255).astype(np.uint8))


def doku_yaz(kaplama: str) -> list[Path]:
    """dünya + bölge yamaları için kaplama dokuları (jpg). Döner: [dosya]; bölge json'ları yanında"""
    out = []
    for npy in sorted(ONBELLEK.glob("*.npy")):
        E = np.load(npy).astype(np.float32)
        if npy.stem.startswith("dunya"):
            kutu = (-180, -90, 180, 90)
        else:
            kutu = tuple(json.loads(npy.with_suffix(".json").read_text())["kutu"])
        hedef = ONBELLEK / "doku" / f"{kaplama}-{npy.stem}.jpg"
        if not hedef.exists() or hedef.stat().st_mtime < Path(__file__).stat().st_mtime:
            hedef.parent.mkdir(parents=True, exist_ok=True)
            doku(kaplama, E, kutu).save(hedef, quality=93)
            (hedef.with_suffix(".json")).write_text(json.dumps({"kutu": kutu}))
        out.append(hedef)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    alt = ap.add_subparsers(dest="k", required=True)
    alt.add_parser("dunya")
    b = alt.add_parser("bolge"); b.add_argument("kutu", type=float, nargs=4); b.add_argument("--z", type=int, default=7)
    d = alt.add_parser("doku"); d.add_argument("kaplama")
    a = ap.parse_args(argv)
    if a.k == "dunya":
        print(dunya())
    elif a.k == "bolge":
        print(bolge(a.kutu, a.z))
    else:
        print("\n".join(map(str, doku_yaz(a.kaplama))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
