"""Kayıtlı efekt kütüphanesi: lisansı temiz (CC0) gerçek kayıtlar, yoksa sentez yedeği.

Neden: kâğıt, kalem, whoosh, tık gibi sesler sentezle üretildiğinde (ne kadar biçimlendirilse de)
yapay ve tekdüze duyuluyor (Atilla, 2026-10-19). Burada gerçek kayıtlardan küçük bir kütüphane
kurulur; her stil kendi "ses paletini" seçer, şablonlar `kayit(...)` ile ister. Kütüphane yoksa
(CI, ağ izni olmayan oturum) aynı çağrı sentez yedeğini döndürür, çıktı bugünküyle aynı kalır.

Kaynaklar (yalnız CC0 1.0; her kaydın kaynağı, yazarı ve sha256'sı `kutuphane.json`da):
- Kenney ses paketleri (kenney.nl, hepsi CC0, anahtar gerekmez)
- Freesound (freesound.org, lisans süzgeci "Creative Commons 0"; ücretsiz API anahtarı `FREESOUND_API_KEY`)
- Elle eklenen dosyalar (`ekle`, lisans ve kaynak zorunlu)

Dosyalar repoya girmez: `EFEKT_KUTUPHANESI`, yoksa /mnt/project-files/.onbellek/efekt-kutuphanesi,
o da yoksa ~/.cache/oyun-projeleri/efekt-kutuphanesi. İndirilen her kayıt kırpılır, 48 kHz'e
çevrilir ve kalite kapısının hışırtı ölçüsünden geçer; tekdüze cızırtılı kayıt alınmaz.

    python3 platform/ortak/kutuphane.py durum                 # kategori başına kayıt sayısı, ağ erişimi
    python3 platform/ortak/kutuphane.py indir [--kaynak kenney freesound] [--adet 6]
    python3 platform/ortak/kutuphane.py ekle dosya.wav --kategori kalem --kaynak <url> --yazar <ad> [--lisans CC0-1.0]
    python3 platform/ortak/kutuphane.py dene kalem            # kategorinin bütün kayıtları art arda: dene-kalem.wav

Şablonda:

    import kutuphane
    x = kutuphane.kayit("kalem", rng, yedek=lambda: kalem_cizgisi(d, rng), sure=d)
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

SR = 48000
BURADA = Path(__file__).resolve().parent
LISANS = "CC0-1.0"

# kategori → açıklama, süre aralığı (sn), Kenney paketleri (dosya adı deseni), Freesound sorgusu
KATALOG: dict[str, dict] = {
    "kalem":          {"aciklama": "kurşun kalem kâğıtta çizgi", "sure": (0.4, 6), "freesound": "pencil writing paper"},
    "kagit_cevir":    {"aciklama": "sayfa / kâğıt çevirme", "sure": (0.2, 2.5), "freesound": "page turn paper",
                       "kenney": [("rpg-audio", r"bookflip"), ("casino-audio", r"card-?slide")]},
    "kagit_hisirti":  {"aciklama": "kâğıt hışırtısı, kısa", "sure": (0.2, 2.5), "freesound": "paper rustle",
                       "kenney": [("casino-audio", r"card-?(shove|fan)")]},
    "kagit_katla":    {"aciklama": "kâğıt katlama (origami)", "sure": (0.2, 2.5), "freesound": "paper fold"},
    "makas":          {"aciklama": "makasla kâğıt kesme", "sure": (0.2, 2.5), "freesound": "scissors cutting paper"},
    "kart_koy":       {"aciklama": "kart / kâğıt masaya konur", "sure": (0.1, 1.2), "freesound": "card place table",
                       "kenney": [("casino-audio", r"card-?place")]},
    "tik":            {"aciklama": "küçük tık", "sure": (0.02, 0.6), "freesound": "click button",
                       "kenney": [("interface-sounds", r"^(tick|click)_")]},
    "secim":          {"aciklama": "yumuşak pop / seçim", "sure": (0.05, 0.8), "freesound": "pop bubble",
                       "kenney": [("interface-sounds", r"^(select|pluck|drop)_")]},
    "darbe_yumusak":  {"aciklama": "boğuk yumuşak darbe (vurgu)", "sure": (0.1, 1.5), "freesound": "soft thud impact",
                       "kenney": [("impact-sounds", r"impactsoft")]},
    "darbe_tahta":    {"aciklama": "tahta tok darbe", "sure": (0.05, 1.2), "freesound": "wood knock",
                       "kenney": [("impact-sounds", r"impactwood")]},
    "cam":            {"aciklama": "cam / kristal tını", "sure": (0.1, 2.5), "freesound": "glass ding",
                       "kenney": [("impact-sounds", r"impactglass_light"), ("interface-sounds", r"^glass_")]},
    "metal_tik":      {"aciklama": "metal mandal / kilit", "sure": (0.05, 1.0), "freesound": "metal click latch",
                       "kenney": [("rpg-audio", r"metal(click|latch)")]},
    "kumas":          {"aciklama": "kumaş hışırtısı", "sure": (0.2, 2.0), "freesound": "cloth movement",
                       "kenney": [("rpg-audio", r"cloth")]},
    "gecis_whoosh":   {"aciklama": "hava geçişi (whoosh)", "sure": (0.25, 2.0), "freesound": "whoosh"},
    "gecis_yumusak":  {"aciklama": "yumuşak swoosh", "sure": (0.25, 2.0), "freesound": "soft swoosh"},
    "daktilo":        {"aciklama": "daktilo / klavye tuşu", "sure": (0.05, 1.0), "freesound": "typewriter key"},
    "tabela":         {"aciklama": "kalkış tabelası kanat sesi", "sure": (0.2, 4.0), "freesound": "split flap display"},
    "ortam_kafe":     {"aciklama": "kafe ortam sesi (çok alçak)", "sure": (5, 40), "freesound": "cafe ambience",
                       "ortam": True},
    "ortam_doga":     {"aciklama": "kuş / doğa ortamı (çok alçak)", "sure": (5, 40), "freesound": "birds ambience",
                       "ortam": True},
}

# stil → rol → kategori. Kurgu geçişlerde hedef sahnenin `gecis` rolünü çalar.
PALETLER: dict[str, dict[str, str]] = {
    "varsayilan":   {"gecis": "gecis_yumusak", "vurgu": "darbe_yumusak", "tik": "tik"},
    "kinetik":      {"gecis": "gecis_whoosh", "vurgu": "darbe_yumusak", "tik": "tik", "pop": "secim"},
    "analiz":       {"gecis": "gecis_yumusak", "tik": "tik", "pop": "secim"},
    "karakalem":    {"cizgi": "kalem", "gecis": "kagit_cevir", "vurgu": "darbe_yumusak", "tik": "tik"},
    "tek_cizgi":    {"cizgi": "kalem", "gecis": "kagit_cevir", "vurgu": "darbe_yumusak"},
    "kolaj":        {"gecis": "kagit_hisirti", "kesme": "makas", "koy": "kart_koy"},
    "kagit":        {"gecis": "kagit_cevir", "kesme": "makas", "koy": "kart_koy"},
    "origami":      {"gecis": "kagit_hisirti", "katla": "kagit_katla"},
    "golge_oyunu":  {"gecis": "kumas", "vurgu": "darbe_tahta"},
    "minyatur":     {"gecis": "kagit_cevir", "vurgu": "cam"},
    "ekran":        {"gecis": "gecis_yumusak", "tus": "daktilo", "tabela": "tabela", "tik": "metal_tik"},
    "vitray":       {"gecis": "gecis_yumusak", "vurgu": "cam"},
    "cini":         {"gecis": "gecis_yumusak", "vurgu": "cam"},
    "linol":        {"gecis": "kagit_cevir", "vurgu": "darbe_tahta"},
    "teknik-cizim": {"gecis": "kagit_cevir", "cizgi": "kalem"},
}

KULLANIM: dict[str, dict[str, int]] = {}  # bu süreçte kategori başına kaç kez kayıt / sentez çaldı (kalite raporu)
_DIZIN: dict | None = None
_ONBELLEK: dict[str, np.ndarray] = {}


class KutuphaneHatasi(RuntimeError):
    pass


def kutuphane_yolu() -> Path:
    if os.environ.get("EFEKT_KUTUPHANESI"):
        return Path(os.environ["EFEKT_KUTUPHANESI"])
    ortak = Path("/mnt/project-files/.onbellek")
    if ortak.is_dir():
        return ortak / "efekt-kutuphanesi"
    return Path.home() / ".cache" / "oyun-projeleri" / "efekt-kutuphanesi"


def dizin(yenile: bool = False) -> dict:
    global _DIZIN
    if _DIZIN is None or yenile:
        yol = kutuphane_yolu() / "kutuphane.json"
        try:
            _DIZIN = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _DIZIN = {"surum": 1, "kayitlar": []}
    return _DIZIN


def kayitlar(kategori: str) -> list[dict]:
    return [k for k in dizin()["kayitlar"] if k["kategori"] == kategori and (kutuphane_yolu() / k["dosya"]).exists()]


def var_mi(kategori: str) -> bool:
    return bool(kayitlar(kategori))


def rol(stil: str, ad: str) -> str | None:
    """Stilin paletindeki rolün kategorisi (yoksa varsayılan paletten)."""
    return PALETLER.get(stil, {}).get(ad) or PALETLER["varsayilan"].get(ad)


def _oku(dosya: Path) -> np.ndarray:
    anahtar = str(dosya)
    if anahtar not in _ONBELLEK:
        import soundfile as sf
        x, r = sf.read(anahtar, always_2d=True)
        x = x.mean(axis=1)
        if r != SR:
            x = np.interp(np.arange(int(len(x) * SR / r)) * r / SR, np.arange(len(x)), x)
        _ONBELLEK[anahtar] = x
    return _ONBELLEK[anahtar]


def _kaydir(x: np.ndarray, oran: float) -> np.ndarray:
    """Hız/ton değişimi (yeniden örnekleme): aynı kayıt iki kez birebir aynı duyulmasın."""
    n = int(len(x) / oran)
    return np.interp(np.arange(n) * oran, np.arange(len(x)), x)


def sec(kategori: str, rng=None, sure: float | None = None) -> np.ndarray | None:
    """Kategoriden rastgele bir kayıt (mono, tepe ~0.9). Yoksa None.

    Her çağrı küçük bir ton (±3 %) ve seviye (±1.5 dB) farkıyla gelir. `sure` verilirse kayıt o
    süreye kısaltılır (yumuşak sönüm) ya da daha kısaysa farklı kayıtlardan çapraz geçişle uzatılır.
    """
    adaylar = kayitlar(kategori)
    if not adaylar:
        return None
    rng = rng if isinstance(rng, np.random.Generator) else np.random.default_rng(rng)

    def bir():
        k = adaylar[int(rng.integers(len(adaylar)))]
        x = _kaydir(_oku(kutuphane_yolu() / k["dosya"]), float(rng.uniform(0.97, 1.03)))
        return x * 10 ** (float(rng.uniform(-1.5, 1.5)) / 20)

    x = bir()
    if sure is not None:
        n = int(sure * SR)
        x0 = int(0.04 * SR)
        while len(x) < n:  # uzat: başka kayıt, 40 ms çapraz geçiş
            y = bir()
            if len(y) <= x0 * 2:
                break
            r = np.linspace(0, 1, x0)
            x = np.concatenate([x[:-x0], x[-x0:] * (1 - r) + y[:x0] * r, y[x0:]])
        if len(x) > n:
            x = x[:n].copy()
            s = min(len(x), int(0.08 * SR))
            x[-s:] *= np.linspace(1, 0, s) ** 2
    return x


def kayit(kategori: str | None, rng=None, yedek=None, sure: float | None = None, esle: bool = True) -> np.ndarray:
    """Kayıt varsa kayıt, yoksa `yedek()` (sentez). Hangisinin çaldığı `KULLANIM`a yazılır.

    `esle=True`: kayıt, yedeğin seviyesine (sesli kısımların RMS'i) getirilir; şablonun miks dengesi değişmez.
    """
    x = sec(kategori, rng, sure) if kategori else None
    say = KULLANIM.setdefault(kategori or "?", {"kayit": 0, "sentez": 0})
    if x is not None:
        say["kayit"] += 1
        if esle and yedek is not None:
            import miks
            hedef, simdi = miks.aktif_rms(yedek()), miks.aktif_rms(x)
            if hedef > 0 and simdi > 0:
                x = x * (hedef / simdi)
        return x
    say["sentez"] += 1
    if yedek is None:
        return np.zeros(int((sure or 0.1) * SR))
    return yedek()


# ---------------------------------------------------------------- kütüphaneyi kurmak

def _getir(url: str, zaman_asimi: float = 30) -> bytes:
    istek = urllib.request.Request(url, headers={"User-Agent": "oyun-projeleri-efekt-kutuphanesi/1"})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
        return r.read()


def _coz(veri: bytes) -> np.ndarray:
    """Herhangi bir ses dosyası (ogg, mp3, wav) → 48 kHz mono float (ffmpeg)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "pipe:1"], input=veri, capture_output=True)
    if r.returncode:
        raise KutuphaneHatasi(f"ses çözülemedi: {r.stderr.decode(errors='ignore')[-200:]}")
    return np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)


def isle(x: np.ndarray, kategori: str) -> tuple[np.ndarray | None, str]:
    """Kırp, normalle, denetle. (ses, '') ya da (None, ret nedeni)."""
    import sfx
    if not len(x) or not np.isfinite(x).all() or not np.any(x):
        return None, "boş"
    x = x - x.mean()
    tepe = np.abs(x).max()
    zarf = np.convolve(np.abs(x), np.ones(480) / 480, "same")
    canli = np.nonzero(zarf > tepe * 10 ** (-50 / 20))[0]
    a, b = max(0, canli[0] - int(0.01 * SR)), min(len(x), canli[-1] + int(0.05 * SR))
    x = x[a:b]
    alt, ust = KATALOG[kategori]["sure"]
    if not alt * 0.8 <= len(x) / SR <= ust * 1.5:
        return None, f"süre {len(x) / SR:.2f} sn ({alt}–{ust} dışında)"
    f = min(len(x) // 4, int(0.005 * SR))
    if f:
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
    x = x / np.abs(x).max() * 0.9
    if not KATALOG[kategori].get("ortam"):
        h = sfx.gurultu_analizi(x)
        if h["en_uzun_sn"] >= 1.0:
            return None, f"tekdüze cızırtı {h['en_uzun_sn']} sn"
    return x, ""


def _kaydet(x: np.ndarray, kategori: str, kimlik: str, ust: dict) -> dict:
    import soundfile as sf
    kok = kutuphane_yolu()
    dosya = Path(kategori) / f"{re.sub(r'[^a-z0-9_-]+', '-', kimlik.lower()).strip('-')}.wav"
    (kok / dosya).parent.mkdir(parents=True, exist_ok=True)
    tampon = io.BytesIO()
    sf.write(tampon, x.astype(np.float32), SR, format="WAV", subtype="PCM_24")
    veri = tampon.getvalue()
    (kok / dosya).write_bytes(veri)
    k = {"kimlik": kimlik, "kategori": kategori, "dosya": str(dosya), "sure": round(len(x) / SR, 3),
         "sha256": hashlib.sha256(veri).hexdigest(), **ust}
    d = dizin()
    d["kayitlar"] = [y for y in d["kayitlar"] if y["kimlik"] != kimlik] + [k]
    return k


def _dizin_yaz() -> None:
    kok = kutuphane_yolu()
    kok.mkdir(parents=True, exist_ok=True)
    d = dizin()
    d["kayitlar"].sort(key=lambda k: (k["kategori"], k["kimlik"]))
    (kok / "kutuphane.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    satir = ["# Efekt kütüphanesi: kaynaklar ve lisanslar", "",
             "Bütün kayıtlar CC0 1.0 (kamu malı). Atıf gerekmez; yine de kaynaklar burada.", "",
             "| Kategori | Kayıt | Yazar | Kaynak |", "| --- | --- | --- | --- |"]
    satir += [f"| {k['kategori']} | {k['kimlik']} | {k.get('yazar', '')} | {k.get('url', '')} |" for k in d["kayitlar"]]
    (kok / "LISANSLAR.md").write_text("\n".join(satir) + "\n", encoding="utf-8")


def kenney_indir(paket: str) -> dict[str, bytes]:
    """Kenney paket sayfasından zip bağlantısını bulur; lisans CC0 değilse durur. {dosya adı: ses verisi}."""
    sayfa = _getir(f"https://kenney.nl/assets/{paket}").decode("utf-8", errors="ignore")
    m = re.search(r"""["'](https?://kenney\.nl)?(/media/[^"']+?\.zip)["']""", sayfa)
    if not m:
        raise KutuphaneHatasi(f"kenney {paket}: indirme bağlantısı bulunamadı")
    z = zipfile.ZipFile(io.BytesIO(_getir("https://kenney.nl" + m.group(2), 120)))
    lisans = " ".join(z.read(n).decode("utf-8", errors="ignore") for n in z.namelist() if "license" in n.lower())
    if not re.search(r"CC0|Creative Commons Zero", lisans, re.I):
        raise KutuphaneHatasi(f"kenney {paket}: pakette CC0 lisans metni yok, alınmadı")
    return {Path(n).name: z.read(n) for n in z.namelist() if re.search(r"\.(ogg|wav|mp3)$", n, re.I)}


def freesound_ara(sorgu: str, sure: tuple[float, float], anahtar: str, adet: int) -> list[dict]:
    q = urllib.parse.urlencode({
        "query": sorgu, "filter": f'license:"Creative Commons 0" duration:[{sure[0]} TO {sure[1]}]',
        "fields": "id,name,username,license,previews,url", "sort": "rating_desc", "page_size": str(adet * 3),
        "token": anahtar})
    return json.loads(_getir(f"https://freesound.org/apiv2/search/text/?{q}"))["results"]


def indir(kaynaklar=("kenney", "freesound"), adet: int = 6, kategoriler=None, yaz=print) -> dict:
    """Kütüphaneyi kurar / tamamlar. Kategori başına en çok `adet` kayıt; var olanlar korunur."""
    kategoriler = kategoriler or list(KATALOG)
    sonuc = {"eklenen": 0, "reddedilen": 0, "hatalar": []}
    say = lambda kat: len(kayitlar(kat))  # noqa: E731
    if "kenney" in kaynaklar:
        paketler: dict[str, list[tuple[str, str]]] = {}
        for kat in kategoriler:
            for paket, desen in KATALOG[kat].get("kenney", []):
                paketler.setdefault(paket, []).append((kat, desen))
        for paket, eslesme in paketler.items():
            try:
                dosyalar = kenney_indir(paket)
            except Exception as e:  # ağ izni yoksa: URLError / 403
                sonuc["hatalar"].append(f"kenney {paket}: {e}")
                continue
            for kat, desen in eslesme:
                for ad, veri in sorted(dosyalar.items()):
                    if say(kat) >= adet or not re.search(desen, ad, re.I):
                        continue
                    x, neden = isle(_coz(veri), kat)
                    if x is None:
                        sonuc["reddedilen"] += 1
                        yaz(f"  ret {kat} {ad}: {neden}")
                        continue
                    _kaydet(x, kat, f"kenney-{paket}-{Path(ad).stem}",
                            {"kaynak": f"kenney:{paket}", "url": f"https://kenney.nl/assets/{paket}", "yazar": "Kenney",
                             "lisans": LISANS})
                    sonuc["eklenen"] += 1
            yaz(f"kenney {paket}: tamam")
    if "freesound" in kaynaklar:
        anahtar = os.environ.get("FREESOUND_API_KEY")
        if not anahtar:
            sonuc["hatalar"].append("freesound: FREESOUND_API_KEY ortam değişkeni yok (freesound.org/apiv2/apply, ücretsiz)")
        else:
            for kat in kategoriler:
                if say(kat) >= adet or not KATALOG[kat].get("freesound"):
                    continue
                try:
                    sonuclar = freesound_ara(KATALOG[kat]["freesound"], KATALOG[kat]["sure"], anahtar, adet)
                except Exception as e:
                    sonuc["hatalar"].append(f"freesound {kat}: {e}")
                    continue
                yazarlar: dict[str, int] = {}
                for r in sonuclar:
                    if say(kat) >= adet:
                        break
                    if "publicdomain/zero" not in r.get("license", "") or yazarlar.get(r["username"], 0) >= 2:
                        continue  # yalnız CC0; aynı yazardan en çok 2 kayıt (çeşitlilik)
                    try:
                        x, neden = isle(_coz(_getir(r["previews"]["preview-hq-ogg"])), kat)
                    except Exception as e:
                        sonuc["hatalar"].append(f"freesound {r['id']}: {e}")
                        continue
                    if x is None:
                        sonuc["reddedilen"] += 1
                        yaz(f"  ret {kat} freesound {r['id']}: {neden}")
                        continue
                    _kaydet(x, kat, f"freesound-{r['id']}",
                            {"kaynak": f"freesound:{r['id']}", "url": r["url"], "yazar": r["username"], "ad": r["name"],
                             "lisans": LISANS})
                    yazarlar[r["username"]] = yazarlar.get(r["username"], 0) + 1
                    sonuc["eklenen"] += 1
                yaz(f"freesound {kat}: {say(kat)} kayıt")
    _dizin_yaz()
    return sonuc


def ekle(dosya: str | Path, kategori: str, kaynak: str, yazar: str, lisans: str = LISANS) -> dict:
    """Elle bulunan bir kaydı ekler. Yalnız CC0 kabul edilir (müşteri işinde lisans riski olmasın)."""
    if kategori not in KATALOG:
        raise KutuphaneHatasi(f"kategori {', '.join(KATALOG)} olmalı")
    if lisans.upper().replace(" ", "") not in ("CC0", "CC0-1.0", "CC0/1.0"):
        raise KutuphaneHatasi("yalnız CC0 1.0 lisanslı kayıt eklenir")
    x, neden = isle(_coz(Path(dosya).read_bytes()), kategori)
    if x is None:
        raise KutuphaneHatasi(f"kayıt alınmadı: {neden}")
    k = _kaydet(x, kategori, f"elle-{Path(dosya).stem}", {"kaynak": "elle", "url": kaynak, "yazar": yazar, "lisans": LISANS})
    _dizin_yaz()
    return k


def ag_durumu() -> dict[str, bool]:
    out = {}
    for alan in ("kenney.nl", "freesound.org", "cdn.freesound.org"):
        try:
            _getir(f"https://{alan}/", 8)
            out[alan] = True
        except urllib.error.HTTPError as e:
            out[alan] = e.code not in (403, 407)  # vekil reddi: 403/407
        except Exception:
            out[alan] = False
    return out


def dene(kategori: str, hedef: Path) -> Path:
    import soundfile as sf
    parcalar = []
    for k in kayitlar(kategori):
        parcalar += [_oku(kutuphane_yolu() / k["dosya"]), np.zeros(int(0.4 * SR))]
    if not parcalar:
        raise KutuphaneHatasi(f"{kategori}: kayıt yok")
    sf.write(str(hedef), np.concatenate(parcalar).astype(np.float32), SR)
    return hedef


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("durum")
    p = alt.add_parser("indir")
    p.add_argument("--kaynak", nargs="+", default=["kenney", "freesound"], choices=["kenney", "freesound"])
    p.add_argument("--adet", type=int, default=6)
    p.add_argument("--kategori", nargs="+", choices=list(KATALOG))
    p = alt.add_parser("ekle")
    p.add_argument("dosya")
    p.add_argument("--kategori", required=True, choices=list(KATALOG))
    p.add_argument("--kaynak", required=True)
    p.add_argument("--yazar", required=True)
    p.add_argument("--lisans", default=LISANS)
    p = alt.add_parser("dene")
    p.add_argument("kategori", choices=list(KATALOG))
    a = ap.parse_args(argv)
    if a.komut == "durum":
        print(f"kütüphane: {kutuphane_yolu()}")
        for kat, b in KATALOG.items():
            print(f"  {kat:<15} {len(kayitlar(kat)):>2} kayıt  {b['aciklama']}")
        for alan, acik in ag_durumu().items():
            print(f"  ağ {alan:<18} {'açık' if acik else 'KAPALI (ortamın ağ iznine eklenmeli)'}")
        print(f"  FREESOUND_API_KEY {'var' if os.environ.get('FREESOUND_API_KEY') else 'yok'}")
        return 0
    try:
        if a.komut == "indir":
            r = indir(a.kaynak, a.adet, a.kategori)
            print(f"eklenen {r['eklenen']}, reddedilen {r['reddedilen']}")
            for h in r["hatalar"]:
                print(f"HATA: {h}", file=sys.stderr)
            return 0 if not r["hatalar"] or r["eklenen"] else 2
        if a.komut == "ekle":
            print(json.dumps(ekle(a.dosya, a.kategori, a.kaynak, a.yazar, a.lisans), ensure_ascii=False))
            return 0
        if a.komut == "dene":
            print(dene(a.kategori, Path(f"dene-{a.kategori}.wav")))
            return 0
    except KutuphaneHatasi as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
