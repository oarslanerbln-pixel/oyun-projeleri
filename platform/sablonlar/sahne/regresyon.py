"""Görsel regresyon testi: her stilin 3 sabit karesi kayıtlı referansla karşılaştırılır.

    R=platform/sablonlar/sahne/regresyon.py
    python3 $R karsilastir [--stiller hamur vitray] [-o fark/]   # CI bunu koşar; fark varsa 1 döner, fark sayfası yazar
    python3 $R guncelle    [--stiller hamur]                      # görünüm bilerek değiştiyse referansı yeniler

Senaryo `testler/regresyon/regresyon.json` (seslendirmesiz, süreler sözcük sayısından: makinede ses gerekmez),
referanslar `testler/regresyon/referans/<stil>.npz` (3 kare, 270×480 RGB, 9:16'nın dörtte biri; depoda
*.png Git LFS'e gittiği için sıkıştırılmış numpy). Stiller: bütün kaplamalar,
çeviriciler ve stil karışımı (`karisim`: sahne sınırında ve sahne ortasında stil geçişi).

Karşılaştırma piksel piksel değil, eşikli: yazı tipi kenar yumuşatmasındaki küçük farklar geçer, sahnenin kayması,
rengin, yazının ya da bir öğenin değişmesi geçmez. Bir stil bozulursa `fark/<stil>.png` sayfası referans | yeni | fark
olarak yazılır (CI'da iş akışının eklerinde). Referansı olmayan yeni stil uyarı verir ama CI'ı kırmaz; `guncelle`
ile referansını ekleyin.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import types
from pathlib import Path

import numpy as np

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
import cevir  # noqa: E402
import dil  # noqa: E402
import sahne  # noqa: E402

KLASOR = BURADA / "testler" / "regresyon"
SENARYO = KLASOR / "regresyon.json"
REFERANS = KLASOR / "referans"
FMT, OLCEK = "9x16", 4  # 1080×1920 / 4 = 270×480
W, H = 1080 // OLCEK, 1920 // OLCEK
KARISIM = "karisim"

# Eşikler (0–255): ortalama fark ve "belirgin değişen" piksel oranı. Yazı kenarlarındaki sürüm farkları ~0.3 ortalama
# ve <%0.5 piksel üretir; bir sahnenin 10 px kayması ya da renginin değişmesi ikisini de rahatça aşar.
ORTALAMA_ESIK = 1.5
PIKSEL_ESIK = 40
ORAN_ESIK = 0.01


def stiller() -> list[str]:
    return sahne.tum_stiller() + [KARISIM]


def _senaryo(stil: str) -> dict:
    s = dil.yukle(SENARYO)
    if stil == KARISIM:  # kinetik → (sınırda) piksel → (sahne ortasında) origami → (mürekkep) hamur
        s["sahneler"][1]["stil"] = "piksel"
        s["sahneler"][2]["donustur"] = "origami"
        s["sahneler"][3]["stil"] = "hamur"
    return sahne.senkron.bagla(dil.zamanla(s, {}), Path(tempfile.gettempdir()) / "regresyon-sesi-yok")


def anlar(z: dict, stil: str) -> list[float]:
    """liste sahnesinin bitmiş hali, karşılaştırmanın bitmiş hali, çağrının bitmiş hali; karışımda üç geçişin ortası"""
    shs = z["sahneler"]
    if stil == KARISIM:
        kap = sahne.kaplama_yap(z, "kinetik")
        b, d = kap.sure * 0.5, kap._donusum(2)
        return [shs[1]["bas"] + b, d[0] + d[1] * 0.5, shs[3]["bas"] + b]
    geri = 0.12 if stil not in cevir.STILLER else 0.6  # çeviriciler geçişini erken başlatır (kontakt ile aynı)
    return [shs[i]["son"] - min(geri, (shs[i]["son"] - shs[i]["bas"]) * 0.3) for i in (1, 2, 3)]


def kareler(stil: str, is_: Path) -> list[np.ndarray]:
    """stilin 3 karesi, 270×480 RGB (uint8)"""
    import skia
    z = _senaryo(stil)
    t = anlar(z, stil)
    if stil in cevir.STILLER:  # hedefin kendi aracı tam boy çizer; 4×4 blok ortalamasıyla küçültülür
        yollar: list = []
        if sahne._yonlendir("kare", z, stil, is_ / stil, types.SimpleNamespace(an=t, format=FMT), yollar):
            raise RuntimeError(f"{stil}: kare çizilemedi")
        out = []
        for p in yollar[:len(t)]:
            a = skia.Image.open(str(p)).convert(alphaType=skia.kUnpremul_AlphaType, colorType=skia.kRGBA_8888_ColorType)
            a = np.asarray(a)[..., :3].astype(np.float32)
            h, w = a.shape[0] // OLCEK * OLCEK, a.shape[1] // OLCEK * OLCEK
            a = a[:h, :w].reshape(h // OLCEK, OLCEK, w // OLCEK, OLCEK, 3).mean((1, 3))
            out.append(np.round(a).astype(np.uint8))
        return out
    kap = sahne.kaplama_yap(z, "kinetik" if stil == KARISIM else stil)
    out = []
    for x in t:
        surf = skia.Surface(W, H)
        with surf as cv:
            cv.clear(0xFF000000)
            kap.kare(cv, x, W, H, FMT)
        img = surf.makeImageSnapshot().convert(alphaType=skia.kUnpremul_AlphaType, colorType=skia.kRGBA_8888_ColorType)
        out.append(np.asarray(img)[..., :3].copy())
    return out


def referans(stil: str) -> list[np.ndarray] | None:
    p = REFERANS / f"{stil}.npz"
    if not p.exists():
        return None
    with np.load(p) as d:
        return [d[k] for k in sorted(d.files)]


def _yaz(a: np.ndarray, p: Path) -> None:
    import skia
    p.parent.mkdir(parents=True, exist_ok=True)
    rgba = np.dstack([a, np.full(a.shape[:2], 255, np.uint8)])
    skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType).save(str(p), skia.kPNG)


def olc(ref: np.ndarray, yeni: np.ndarray) -> dict:
    if ref.shape != yeni.shape:
        return {"ortalama": 255.0, "oran": 1.0, "gecti": False, "not": f"boyut {ref.shape} ≠ {yeni.shape}"}
    f = np.abs(ref.astype(np.int16) - yeni.astype(np.int16)).max(axis=2)
    ort, oran = float(f.mean()), float((f > PIKSEL_ESIK).mean())
    return {"ortalama": round(ort, 3), "oran": round(oran, 4), "gecti": ort <= ORTALAMA_ESIK and oran <= ORAN_ESIK}


def _fark_sayfasi(stil: str, refler: list, yeniler: list, hedef: Path) -> Path:
    """her kare bir satır: referans | yeni | fark (değişen pikseller kırmızı)"""
    satirlar = []
    for r, y in zip(refler, yeniler):
        if r is None or r.shape != y.shape:
            r = np.zeros_like(y)
        f = np.abs(r.astype(np.int16) - y.astype(np.int16)).max(axis=2) > PIKSEL_ESIK
        d = (y * 0.3).astype(np.uint8)
        d[f] = (255, 40, 40)
        bosluk = np.full((y.shape[0], 8, 3), 255, np.uint8)
        satirlar.append(np.hstack([r, bosluk, y, bosluk, d]))
    yol = hedef / f"{stil}.png"
    _yaz(np.vstack(satirlar), yol)
    return yol


def karsilastir(secim: list[str] | None = None, fark: Path | None = None) -> list[str]:
    """bozulan stillerin listesi (boşsa geçti)"""
    fark = fark or Path(os.environ.get("GORSEL_REGRESYON_FARK") or Path(tempfile.gettempdir()) / "gorsel-regresyon")
    bozuk = []
    with tempfile.TemporaryDirectory(prefix="regresyon-") as is_:
        for stil in secim or stiller():
            yeniler = kareler(stil, Path(is_))
            refler = referans(stil)
            if refler is None:
                print(f"UYARI: {stil}: referans yok; `regresyon.py guncelle --stiller {stil}` ile ekleyin", flush=True)
                continue
            sonuc = [olc(r, y) for r, y in zip(refler, yeniler)]
            ozet = "  ".join(f"{i + 1}: ort {x['ortalama']:.2f} · %{x['oran'] * 100:.2f}" for i, x in enumerate(sonuc))
            if all(x["gecti"] for x in sonuc):
                print(f"tamam  {stil:16} {ozet}", flush=True)
            else:
                bozuk.append(stil)
                print(f"BOZUK  {stil:16} {ozet}  → {_fark_sayfasi(stil, refler, yeniler, fark)}", flush=True)
    if bozuk:
        print(f"\nGörünüm değişti: {', '.join(bozuk)}. Bilerek değiştiyse: "
              f"python3 platform/sablonlar/sahne/regresyon.py guncelle --stiller {' '.join(bozuk)}", flush=True)
    return bozuk


def guncelle(secim: list[str] | None = None) -> list[Path]:
    out = []
    REFERANS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="regresyon-") as is_:
        for stil in secim or stiller():
            p = REFERANS / f"{stil}.npz"
            np.savez_compressed(p, **{f"kare{i + 1}": a for i, a in enumerate(kareler(stil, Path(is_)))})
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("karsilastir", "guncelle"):
        p = alt.add_parser(ad)
        p.add_argument("--stiller", nargs="+")
        if ad == "karsilastir":
            p.add_argument("-o", "--fark", help="fark sayfalarının klasörü")
    a = ap.parse_args(argv)
    bilinmeyen = [x for x in a.stiller or [] if x not in stiller()]
    if bilinmeyen:
        print(f"HATA: bilinmeyen stil {', '.join(bilinmeyen)} ({', '.join(stiller())})", file=sys.stderr)
        return 1
    if a.komut == "guncelle":
        for p in guncelle(a.stiller):
            print(p)
        return 0
    return 1 if karsilastir(a.stiller, Path(a.fark) if a.fark else None) else 0


if __name__ == "__main__":
    sys.exit(main())
