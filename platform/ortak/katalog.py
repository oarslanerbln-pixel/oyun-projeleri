"""Teslim kataloğu: teslim edilen her video tek listede (beyin fırtınası 9.1).

    python3 platform/ortak/katalog.py ara kahve                # konu, stil, müşteri, dosya adında arar
    python3 platform/ortak/katalog.py ara markalaşma --dil de --stil tek-cizgi
    python3 platform/ortak/katalog.py liste [--son 20]
    python3 platform/ortak/katalog.py tara [/mnt/project-files]  # eski teslimleri klasörlerden ekler

Kayıtlar `/mnt/project-files/gelistirme/katalog.jsonl` dosyasındadır (her satır bir video, anahtar dosya
yolu); okunabilir hali her yazımda `katalog.md` olarak yenilenir. `uret.py` teslimde videoları buraya yazar,
`--kapat` maliyeti ekler; elle bir şey yapmak gerekmez. "Geçen ay yaptığımız kahve videosunu Almanca yap"
gibi bir istekte önce `ara`, sonra bulunan kaydın `senaryo` ve `klasor` alanından devam edilir.

Alanlar: tarih, is, baslik, tur (musteri/kendi/ornek), stil, format, sure_sn, dil, ses, dosya, senaryo,
klasor, kalite, maliyet_usd, elevenlabs_karakter, panel_id, kaynak (siparis/tarama).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PAYLASIM = Path(os.environ.get("STUDYO_PAYLASIM", "/mnt/project-files"))
ALANLAR = ["tarih", "is", "baslik", "tur", "stil", "format", "sure_sn", "dil", "ses", "dosya", "senaryo",
           "klasor", "kalite", "maliyet_usd", "elevenlabs_karakter", "panel_id", "kaynak"]

# taramada klasörden tahmin: ilk klasör → tür ve dil (siparişten gelen kayıtta bunlar siparişte yazar)
MUSTERI = {"the-leaf", "le-mariage", "lezzet-dunyasi"}
KENDI = {"atilla-ebook", "markalasma-nedir", "al-andalus", "uzun-video"}
KLASOR_DIL = {"the-leaf": "de", "le-mariage": "de", "al-andalus": "de", "atilla-ebook": "de"}
ATLA = {"is", "sahneler", ".onbellek", "uploads", "havuz"}  # ara dosyalar ve önbellek
STIL_ESANLAM = {"3d-oyuncak": "oyuncak", "tabela": "kalkis-tabelasi", "akis": "akis-alani", "imza": "bumper",
                "vitrin": "urun-vitrini", "golge": "golge-oyunu", "uzun": "kurgu", "sahne": "sahne", "atlas": "minyatur"}
STILLER = ["akis-alani", "analiz", "bumper", "cini", "cizgi-roman", "cizgisel", "ebru", "gercekci-3d", "golge-oyunu",
           "hamur", "izometrik", "kagit-kesik", "kalkis-tabelasi", "karakalem", "karusel", "kinetik", "kolaj", "linol",
           "maskot", "mekan", "minyatur", "neon", "origami", "oyuncak", "piksel", "risograf", "siluet", "teknik-cizim",
           "tek-cizgi", "urun-vitrini", "vhs", "vitray"]


def yol(kok: Path | None = None) -> Path:
    return (kok or PAYLASIM) / "gelistirme" / "katalog.jsonl"


def oku(hedef: Path | None = None) -> list[dict]:
    p = hedef or yol()
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def yaz(kayitlar: list[dict], hedef: Path | None = None) -> Path:
    p = hedef or yol()
    p.parent.mkdir(parents=True, exist_ok=True)
    kayitlar = sorted(kayitlar, key=lambda k: (k.get("tarih") or "", k.get("dosya") or ""))
    gecici = p.with_suffix(".tmp")
    gecici.write_text("".join(json.dumps({a: k.get(a) for a in ALANLAR}, ensure_ascii=False) + "\n"
                              for k in kayitlar), encoding="utf-8")
    gecici.replace(p)
    p.with_suffix(".md").write_text(tablo(kayitlar), encoding="utf-8")
    return p


def ekle(yeni: list[dict], hedef: Path | None = None) -> list[dict]:
    """Dosya yoluna göre ekler ya da günceller; boş (None) alan eski değeri silmez."""
    kayitlar = {k["dosya"]: k for k in oku(hedef)}
    for k in yeni:
        eski = kayitlar.get(k["dosya"], {})
        kayitlar[k["dosya"]] = {**eski, **{a: v for a, v in k.items() if v is not None}}
    sonuc = list(kayitlar.values())
    yaz(sonuc, hedef)
    return sonuc


# ---------------------------------------------------------------- siparişten

def siparisten(s: dict, d: dict, maliyet_usd: float | None = None) -> list[dict]:
    """uret.py siparişi ve durumu → her teslim videosu için bir kayıt. Maliyet ve karakter videolara bölünür."""
    videolar = [v for v in d.get("videolar") or [] if v.get("sonuc") != "kaldi"]
    n = max(1, len(videolar))
    senaryolar = {g["stil"]: g["senaryo"] for g in s.get("senaryolar") or []}
    kayitlar = []
    for v in videolar:
        r = _kalite_oku(Path(v["dosya"]))
        kayitlar.append({
            "tarih": time.strftime("%Y-%m-%d"), "is": s.get("is"), "baslik": s.get("baslik") or s.get("is"),
            "tur": s.get("tur_katalog") or ("musteri" if s.get("musteri") else "kendi"), "stil": v.get("stil"),
            "format": v.get("format"), "sure_sn": _sure(r), "dil": v.get("dil") or s.get("dil") or "tr",
            "ses": (s.get("ses") or {}).get("ses"), "dosya": v["dosya"],
            "senaryo": v.get("senaryo") or senaryolar.get(v.get("stil")),
            "klasor": s.get("_klasor"), "kalite": v.get("sonuc"),
            "maliyet_usd": None if maliyet_usd is None else round(maliyet_usd / n, 2),
            "elevenlabs_karakter": round((d.get("elevenlabs_karakter") or 0) / n),
            "panel_id": (s.get("panel") or {}).get("id"), "kaynak": "siparis"})
    return kayitlar


def _kalite_oku(video: Path) -> dict:
    rj = video.with_suffix(".kalite.json")
    try:
        return json.loads(rj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _sure(r: dict) -> float | None:
    s = (r.get("akis") or {}).get("sure")
    return round(s, 1) if s else None


# ---------------------------------------------------------------- tarama

def _ffprobe_sure(p: Path) -> float | None:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                           capture_output=True, text=True, timeout=30)
        return round(float(r.stdout.strip()), 1)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def stil_tahmin(goreli: Path) -> str | None:
    """Yoldaki parçalardan stil: önce dosya adı, sonra klasörler; tire ile bölünmüş adlar da aranır."""
    for parca in [goreli.stem, *reversed(goreli.parent.parts)]:
        parca = parca.lower().replace("_", "-")
        for ad in sorted(STILLER, key=len, reverse=True):
            if parca == ad or f"-{ad}-" in f"-{parca}-":
                return ad
        for es, ad in STIL_ESANLAM.items():
            if f"-{es}-" in f"-{parca}-":
                return ad
    return None


def _yandaki_senaryo(video: Path) -> str | None:
    """Videonun ya da üst klasörün yanında adı stil olan bir senaryo (ör. tek-cizgi.json) varsa o stil."""
    for k in (video.parent, video.parent.parent):
        adlar = {p.stem.replace("_", "-") for p in k.glob("*.json")} & set(STILLER)
        if len(adlar) == 1:
            return adlar.pop()
    return None


def format_tahmin(ad: str) -> str | None:
    for f in ("9x16", "16x9", "1x1", "4x5"):
        if f in ad:
            return f
    return None


def tara(kok: Path | None = None) -> list[dict]:
    """Ortak klasördeki teslim videolarını bulur (ara dosyalar, sessiz kopyalar ve önbellek hariç)."""
    kok = kok or PAYLASIM
    kayitlar = []
    for p in sorted(kok.rglob("*.mp4")):
        g = p.relative_to(kok)
        if ATLA & set(g.parts[:-1]) or "sessiz" in p.stem or p.name.startswith("animatik"):
            continue
        ilk = g.parts[0]
        r = _kalite_oku(p)
        almanca = any("de" in x.lower().split("-") for x in [p.stem, *g.parts[:-1]])
        dil = "de" if almanca else KLASOR_DIL.get(ilk, "tr")
        kayitlar.append({
            "tarih": time.strftime("%Y-%m-%d", time.localtime(p.stat().st_mtime)), "is": ilk,
            "baslik": " / ".join(g.parts[:-1]) or p.stem,
            "tur": "musteri" if ilk in MUSTERI else "kendi" if ilk in KENDI else "ornek",
            "stil": (r.get("render") or {}).get("stil") or stil_tahmin(g) or _yandaki_senaryo(p), "format": format_tahmin(p.stem), "sure_sn": _sure(r) or _ffprobe_sure(p),
            "dil": dil, "dosya": str(p), "klasor": str(p.parent), "kalite": r.get("sonuc"), "kaynak": "tarama"})
    return kayitlar


# ---------------------------------------------------------------- arama ve gösterim

_KATLA = str.maketrans("çğıöşüâîûÇĞİÖŞÜÂÎÛ", "cgiosuaiuCGIOSUAIU")


def katla(metin: str) -> str:
    return str(metin or "").translate(_KATLA).lower()


def ara(kayitlar: list[dict], sorgu: list[str], stil: str | None = None, dil: str | None = None,
        fmt: str | None = None, tur: str | None = None) -> list[dict]:
    terimler = [katla(t) for t in sorgu]
    sonuc = []
    for k in kayitlar:
        if (stil and k.get("stil") != stil) or (dil and k.get("dil") != dil) or (tur and k.get("tur") != tur):
            continue
        if fmt and (k.get("format") or "").replace(":", "x") != fmt.replace(":", "x"):
            continue
        metin = katla(" ".join(str(k.get(a) or "") for a in ("is", "baslik", "stil", "dosya", "ses", "tur")))
        if all(t in metin for t in terimler):
            sonuc.append(k)
    return sonuc


def satir(k: dict) -> str:
    sure = f"{k['sure_sn']:g} sn" if k.get("sure_sn") else "? sn"
    usd = f" · {k['maliyet_usd']:.2f} $" if k.get("maliyet_usd") is not None else ""
    return (f"{k.get('tarih', '')} · {k.get('stil') or '?'} · {k.get('format') or '?'} · {sure} · {k.get('dil') or '?'}"
            f"{usd} · {k.get('baslik')}\n    {k['dosya']}")


def tablo(kayitlar: list[dict]) -> str:
    sat = ["# Teslim kataloğu", "",
           "`platform/ortak/katalog.py` yazar; elle düzenleme (her yazımda yenilenir). Arama: "
           "`python3 platform/ortak/katalog.py ara <kelime>`.", "",
           "| Tarih | İş | Tür | Stil | Format | Süre | Dil | Maliyet | Dosya |", "|---|---|---|---|---|---|---|---|---|"]
    for k in sorted(kayitlar, key=lambda k: (k.get("tarih") or "", k["dosya"]), reverse=True):
        dosya = k["dosya"].replace(str(PAYLASIM) + "/", "PF/")
        usd = f"{k['maliyet_usd']:.2f} $" if k.get("maliyet_usd") is not None else ""
        sat.append(f"| {k.get('tarih') or ''} | {k.get('baslik') or k.get('is')} | {k.get('tur') or ''} | "
                   f"{k.get('stil') or '?'} | {k.get('format') or ''} | {k.get('sure_sn') or ''} | {k.get('dil') or ''} | "
                   f"{usd} | `{dosya}` |")
    return "\n".join(sat) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    a_ara = alt.add_parser("ara", help="kelimelerin hepsini içeren kayıtlar (Türkçe harfler katlanır)")
    a_ara.add_argument("sorgu", nargs="*")
    for p in (a_ara,):
        p.add_argument("--stil")
        p.add_argument("--dil")
        p.add_argument("--format")
        p.add_argument("--tur", choices=["musteri", "kendi", "ornek"])
        p.add_argument("--json", action="store_true")
    a_liste = alt.add_parser("liste")
    a_liste.add_argument("--son", type=int, default=20)
    a_tara = alt.add_parser("tara", help="ortak klasördeki eski teslimleri kataloğa ekler (var olanı ezmez)")
    a_tara.add_argument("kok", nargs="?")
    ap.add_argument("--katalog", help="katalog.jsonl yolu (varsayılan: PF/gelistirme/katalog.jsonl)")
    a = ap.parse_args(argv)
    hedef = Path(a.katalog) if a.katalog else None
    if a.komut == "tara":
        kok = Path(a.kok) if a.kok else PAYLASIM
        var = {k["dosya"] for k in oku(hedef)}
        yeni = [k for k in tara(kok) if k["dosya"] not in var]  # siparişten gelen kaydı tahminle ezme
        hepsi = ekle(yeni, hedef)
        print(f"{len(yeni)} yeni kayıt, toplam {len(hepsi)}: {hedef or yol()}")
        return 0
    kayitlar = oku(hedef)
    if a.komut == "liste":
        for k in sorted(kayitlar, key=lambda k: k.get("tarih") or "", reverse=True)[:a.son]:
            print(satir(k))
        return 0
    bulunan = ara(kayitlar, a.sorgu, a.stil, a.dil, a.format, a.tur)
    if a.json:
        print(json.dumps(bulunan, ensure_ascii=False, indent=1))
    else:
        for k in bulunan[-20:]:
            print(satir(k))
        print(f"{len(bulunan)} kayıt" + (" (son 20 gösterildi)" if len(bulunan) > 20 else ""))
    return 0 if bulunan else 1


if __name__ == "__main__":
    sys.exit(main())
