"""Sinematik küre dokuları: uydu rengi + gerçek arazi kabartması + gece ışıkları + bulut + normal/yükseklik.

    python3 platform/sablonlar/dunya/sinema/dokular.py hazirla      # indirir ve üretir (~/.cache/studyo/kure)

Kaynaklar (hepsi kamu malı ya da açık lisans, teslim künyesinde yazılır):
- Renk: NASA Blue Marble (three-globe örnek dokusu), NASA Black Marble gece ışıkları (three.js örnek dokusu),
  bulutlar NASA Visible Earth (webgl-earth), Natural Earth kabartma rengi (atlas ışığı için).
- Kabartma/derinlik: AWS Open Data Terrain Tiles (SRTM, GMTED, ETOPO1) z6 → 16384 genişlikte gölgelendirme,
  8192'ye lanczos (renk dokusundan 4× keskin dağ detayı).
Çıktılar 8192×4096 (SwiftShader doku sınırı): gunduz.jpg, atlas.jpg, kure.jpg (gece mavisi kabartma),
gece.png (yalnız ışıklar), bulut.png, normal.png (nesne uzayı), yukseklik.png, su.png.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA.parent))
import arazi  # noqa: E402

KURE = arazi.ONBELLEK.parent / "kure"
R = "https://raw.githubusercontent.com/"
KAYNAK = {
    "ham-gunduz.jpg": R + "vasturiano/three-globe/master/example/img/earth-blue-marble.jpg",
    "ham-atlas.jpg": R + "turban/webgl-earth/master/images/2_no_clouds_4k.jpg",
    "ham-gece.jpg": R + "mrdoob/three.js/dev/examples/textures/planets/earth_night_4096.jpg",
    "ham-bulut.png": R + "turban/webgl-earth/master/images/fair_clouds_4k.png",
}
W, H = 8192, 4096
SURUM = 3  # doku tarifi değişince artır


def indir():
    KURE.mkdir(parents=True, exist_ok=True)
    for ad, url in KAYNAK.items():
        if not (KURE / ad).exists():
            urllib.request.urlretrieve(url, KURE / ad)


def _yukseklik16k() -> np.ndarray:
    yol = arazi.ONBELLEK / "dunya-16384.npy"
    if not yol.exists():
        arazi.dunya(16384)
    return np.load(yol).astype(np.float32)


def _kucult(a: np.ndarray, w=W, h=H) -> np.ndarray:
    return np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((w, h), Image.LANCZOS))


def _rgb(ad, w=W, h=H) -> np.ndarray:
    return np.asarray(Image.open(KURE / ad).convert("RGB").resize((w, h), Image.LANCZOS), np.float32)


def _kaydet(a, ad, **kw):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(KURE / ad, **kw)


def hazirla(zorla: bool = False) -> Path:
    damga = KURE / "surum.json"
    if not zorla and damga.exists() and json.loads(damga.read_text()).get("surum") == SURUM:
        return KURE
    indir()
    kutu = (-180, -90, 180, 90)
    E16 = _yukseklik16k()
    kara16 = arazi.kara_maskesi(kutu, E16.shape[1], E16.shape[0])
    E16 = np.where(kara16, np.maximum(E16, 1), np.minimum(E16, -1))
    S = arazi.golge(E16, kutu, abart=1.5) - 0.53          # ~0 düz zemin, ±kabartma
    S = _kucult(S); E = _kucult(E16); del E16
    kara = _kucult(kara16.astype(np.float32)); del kara16
    karam = kara[..., None]

    # derinlik rampası (kıta sahanlığı görünsün)
    deniz = arazi._rampa(E, [(-8000, (6, 18, 46)), (-4500, (10, 30, 68)), (-2500, (14, 42, 86)), (-600, (22, 62, 112)),
                             (-150, (34, 92, 140)), (-1, (52, 116, 156))])
    ish = S[..., None]

    # 1) gündüz: Blue Marble + kabartma (çarpımsal, ölçülü) + derinlikli okyanus
    bm = _rgb("ham-gunduz.jpg")
    kara_r = bm * (1 + ish * 1.35)
    okyanus = bm * 0.45 + deniz * 0.55
    _kaydet(karam * kara_r + (1 - karam) * okyanus, "gunduz.jpg", quality=94)

    # 2) atlas: Natural Earth renkli kabartma + yeniden keskin gölge
    ne = _rgb("ham-atlas.jpg")
    _kaydet(karam * ne * (1 + ish * 1.1) + (1 - karam) * (ne * 0.5 + deniz * 0.5 + 18), "atlas.jpg", quality=94)

    # 3) kure: gece mavisi kabartma (Atilla'nın beğendiği dil), daha zengin ton
    kk = arazi._rampa(E, [(0, (38, 49, 64)), (400, (44, 56, 72)), (1500, (60, 72, 88)), (3200, (98, 108, 122)), (6000, (150, 158, 170))])
    kd = arazi._rampa(E, [(-8000, (4, 10, 24)), (-4000, (7, 17, 36)), (-1500, (10, 25, 48)), (-200, (15, 37, 64)), (-1, (22, 50, 80))])
    _kaydet(karam * kk * (1 + ish * 2.0) + (1 - karam) * kd, "kure.jpg", quality=95)

    # 4) gece ışıkları: arka planın lacivert tonunu at, yalnız ışık (L)
    g = _rgb("ham-gece.jpg").mean(axis=2)
    g = np.clip((g - 14) / (255 - 14), 0, 1) ** 1.15 * 255
    _kaydet(g, "gece.png")

    # 5) bulut (L), 6) su maskesi (deniz parlaması için)
    b = np.asarray(Image.open(KURE / "ham-bulut.png").convert("L").resize((W // 2, H // 2), Image.LANCZOS), np.float32)
    _kaydet(b, "bulut.png")
    _kaydet((1 - kara) * 255, "su.png")

    # 7) yükseklik (yer değiştirme, karekök ölçek) ve 8) nesne uzayı normal haritası
    w2, h2 = W // 2, H // 2
    E2 = _kucult(E, w2, h2)
    _kaydet(np.sqrt(np.clip(E2, 0, 8800) / 8800) * 255, "yukseklik.png")
    lat = np.radians(90 - (np.arange(h2) + 0.5) / h2 * 180)[:, None]
    lon = np.radians(-180 + (np.arange(w2) + 0.5) / w2 * 360)[None, :]
    Z = np.where(E2 > 0, E2 * 1.0, E2 * 0.12)  # deniz tabanı hafif
    gy, gx = np.gradient(Z)
    mx = (360 / w2 * 111320 * np.cos(lat)).clip(800); my = 180 / h2 * 110540
    dx = gx / mx * 25; dy = -gy / my * 25      # abartı 25× (küre ölçeğinde görünür)
    # ENU tabanı (three.js: y yukarı kutup; lon=0 → +x? sahne.js ile aynı formül)
    N = np.stack([np.cos(lat) * np.cos(lon) + 0 * lon, np.sin(lat) + 0 * lon, -np.cos(lat) * np.sin(lon)], -1)
    Ed = np.stack([-np.sin(lon) + 0 * lat, 0 * lon + 0 * lat, -np.cos(lon) + 0 * lat], -1)
    Nd = np.stack([-np.sin(lat) * np.cos(lon), np.cos(lat) + 0 * lon, np.sin(lat) * np.sin(lon)], -1)
    n = N - dx[..., None] * Ed - dy[..., None] * Nd
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    _kaydet((n * 0.5 + 0.5) * 255, "normal.png")
    damga.write_text(json.dumps({"surum": SURUM}))
    return KURE


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("komut", choices=["hazirla"]); ap.add_argument("--zorla", action="store_true")
    a = ap.parse_args(argv)
    print(hazirla(a.zorla))
    return 0


if __name__ == "__main__":
    sys.exit(main())
