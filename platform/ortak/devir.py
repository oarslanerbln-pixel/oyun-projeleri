"""Devir özeti: bir işin teslim klasörüne kısa `DEVIR.md` yazar.

    python3 platform/ortak/devir.py /mnt/project-files/lezzet-dunyasi --not "Atilla tabak fotoğrafının büyük olmasını istedi"
    python3 platform/ortak/devir.py <klasör> --goster        # yazmadan ekrana bas

Revizyon ya da devam işi yeni bir thread'de bu dosyayla başlar; eski konuşma okunmaz (bkz.
platform/docs/uretim-standardi.md). Dosyanın olgusal kısmı her çalıştırmada klasörden yeniden üretilir:
teslim edilen videolar (format, süre, kalite sonucu), senaryolar ve yeniden üretme komutu, seslendirme
(sağlayıcı, ses, harcanan karakter). "Kararlar ve geri bildirim" bölümü elle tutulur: önceki satırlar
korunur, `--not` ile verilenler eklenir.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
import kalite  # noqa: E402
import onizleme  # noqa: E402

DOSYA = "DEVIR.md"
NOT_BASLIGI = "## Kararlar ve geri bildirim"
ATLA = {"is", "kareler", "seslendirme"}  # ara çıktı klasörleri
SENARYO_DISI = (".kalite.json", "seslendirme.json", "proje.json", "marka.json")


def _ara_mi(yol: Path, kok: Path) -> bool:
    parcalar = yol.relative_to(kok).parts
    return any(p in ATLA for p in parcalar[:-1]) or "sessiz" in yol.stem


def videolar(kok: Path) -> list[Path]:
    return sorted(p for p in kok.rglob("*.mp4") if not _ara_mi(p, kok))


def senaryolar(kok: Path) -> list[tuple[Path, dict]]:
    out = []
    for p in sorted(kok.rglob("*.json")):
        if _ara_mi(p, kok) or p.name.endswith(SENARYO_DISI) or re.search(r"\.v\d+$", p.stem):  # eski sürümler
            continue
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(s, dict) and ("sahneler" in s or "seslendirme" in s or "stil" in s):
            out.append((p, s))
    # kurgunun sahne dosyaları ayrı ayrı üretilmez; kurgu.json'un satırı yeter
    sahne = {(p.parent / x["senaryo"]).resolve() for p, s in out for x in s.get("sahneler", [])
             if isinstance(x, dict) and isinstance(x.get("senaryo"), str)}
    return [(p, s) for p, s in out if p.resolve() not in sahne]


def yeniden_uret(yol: Path, s: dict) -> str:
    ad = onizleme.sablon_bul(s, yol, None)
    if ad in onizleme.KOMUTLAR:
        return f"python3 platform/sablonlar/{onizleme.KOMUTLAR[ad]} render {yol}"
    return f"python3 platform/sablonlar/stil/stil.py uret {yol} --stil {ad}"


def video_satiri(p: Path, kok: Path) -> str:
    rapor = p.with_suffix(".kalite.json")
    if rapor.exists():
        r = json.loads(rapor.read_text(encoding="utf-8"))
        b, sonuc = r["akis"], r["sonuc"]
        sorun = [x["kontrol"] for x in r["bulgular"] if x["seviye"] in ("hata", "uyari")]
    else:
        b, sonuc, sorun = kalite.akis_bilgisi(p), "rapor yok", []
    v = b.get("video") or {}
    boyut = f"{v.get('w')}x{v.get('h')}" if v else "?"
    ek = f" ({', '.join(sorun)})" if sorun else ""
    return f"- `{p.relative_to(kok)}` · {boyut} · {b.get('sure', 0):.1f} sn · kalite: {sonuc}{ek}"


def ses_satirlari(kok: Path) -> list[str]:
    out = []
    for p in sorted(kok.rglob("seslendirme.json")):
        try:
            k = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if "satirlar" not in k:
            continue
        kul = k.get("kullanim", {})
        harc = f", {kul.get('karakter', 0)} karakter" if kul else ""
        out.append(f"- `{p.parent.relative_to(kok)}`: {k.get('saglayici', '?')} / {k.get('ses', '?')}, "
                   f"{len(k['satirlar'])} satır{harc}")
    return out


def eski_notlar(hedef: Path) -> list[str]:
    if not hedef.exists():
        return []
    metin = hedef.read_text(encoding="utf-8")
    if NOT_BASLIGI not in metin:
        return []
    bolum = metin.split(NOT_BASLIGI, 1)[1].split("\n## ", 1)[0]
    return [x for x in bolum.strip().splitlines() if x.startswith("- ")]


def metin(kok: Path, notlar: list[str]) -> str:
    kok = Path(kok)
    satir = [f"# Devir: {kok.name}", "",
             f"Güncellendi {time.strftime('%Y-%m-%d %H:%M')}. Revizyon ya da devam işi buradan başlar; "
             "eski thread okunmaz. Kurallar: platform/docs/uretim-standardi.md", "", "## Teslim edilenler"]
    satir += [video_satiri(p, kok) for p in videolar(kok)] or ["- (henüz video yok)"]
    satir += ["", "## Senaryolar ve yeniden üretme"]
    satir += [f"- `{p.relative_to(kok)}` → `{yeniden_uret(p, s)}`" for p, s in senaryolar(kok)] or ["- (senaryo yok)"]
    ses = ses_satirlari(kok)
    if ses:
        satir += ["", "## Seslendirme", *ses]
    satir += ["", NOT_BASLIGI, *(notlar or ["- (yok)"]), ""]
    return "\n".join(satir)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("klasor")
    ap.add_argument("--not", dest="notlar", action="append", default=[],
                    help="karar ya da geri bildirim satırı (tekrarlanabilir)")
    ap.add_argument("--goster", action="store_true", help="dosyaya yazmadan bas")
    a = ap.parse_args(argv)
    kok = Path(a.klasor)
    hedef = kok / DOSYA
    notlar = [x for x in eski_notlar(hedef) if x != "- (yok)"]
    notlar += [f"- {time.strftime('%Y-%m-%d')}: {x}" for x in a.notlar]
    m = metin(kok, notlar)
    if a.goster:
        print(m)
    else:
        hedef.write_text(m, encoding="utf-8")
        print(hedef)
    return 0


if __name__ == "__main__":
    sys.exit(main())
