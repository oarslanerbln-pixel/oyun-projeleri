"""CI çalıştırıcısı: modülleri kendisi bulur, yeni şablon iş akışı dosyasına dokunmadan CI'a girer.

    python3 platform/ci/calistir.py hazirla           # ci.json'lardaki pip paketleri ve hazırlık komutları
    python3 platform/ci/calistir.py test [--modul kinetik]   # testler + örnek denetimleri
    python3 platform/ci/calistir.py dizin             # şablon dizinini (Markdown tablo) basar

Kurallar:
- `platform/` altındaki her `testler/` klasörü (içinde `test_*.py` varsa) `unittest` ile koşar.
- Bir modül klasöründeki `ci.json` örnek dosyaların denetimini ve hazırlığı tarif eder:

    {"pip": ["numpy"],
     "hazirlik": [["{python}", "-c", "..."]],
     "denetle": [{"dosyalar": ["ornekler/*/origami.json"],
                  "komut": ["{python}", "{modul}/origami.py", "denetle", "{dosya}", "-o", "{gecici}/origami"]}]}

  Yer tutucular: {python} bu yorumlayıcı, {modul} ci.json'un klasörü, {dosya} eşleşen dosya,
  {ad} dosyanın bulunduğu klasörün adı, {gecici} geçici çıktı klasörü. Eşleşme yoksa adım atlanır.
- Şablon dizini her şablonun README'sinin ilk paragrafından üretilir ve depoya yazılmaz; böylece
  yeni şablon PR'ları ortak bir listeye satır eklemez ve birbiriyle çakışmaz.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEPO = Path(__file__).resolve().parents[2]
PLATFORM = DEPO / "platform"
SABLONLAR = PLATFORM / "sablonlar"
GH = os.environ.get("GITHUB_ACTIONS") == "true"


def _grup(ad: str) -> None:
    print(f"::group::{ad}" if GH else f"\n== {ad}", flush=True)


def _grup_bitir() -> None:
    if GH:
        print("::endgroup::", flush=True)


def _hata(mesaj: str) -> None:
    print(f"::error::{mesaj}" if GH else f"HATA: {mesaj}", flush=True)


def ci_dosyalari() -> list[tuple[Path, dict]]:
    out = []
    for p in sorted(PLATFORM.rglob("ci.json")):
        out.append((p.parent, json.loads(p.read_text(encoding="utf-8"))))
    return out


def test_klasorleri() -> list[Path]:
    return sorted(d for d in PLATFORM.rglob("testler") if d.is_dir() and any(d.glob("test_*.py")))


def _ad(klasor: Path) -> str:
    return klasor.relative_to(PLATFORM).as_posix()


def _yerlestir(komut: list[str], **deg: str) -> list[str]:
    return [x.format(**deg) for x in komut]


def hazirla() -> int:
    paketler: list[str] = []
    for _, c in ci_dosyalari():
        paketler += [p for p in c.get("pip", []) if p not in paketler]
    kod = 0
    if paketler:
        _grup(f"pip: {' '.join(paketler)}")
        kod |= subprocess.run([sys.executable, "-m", "pip", "install", "-q", *paketler]).returncode
        _grup_bitir()
    for klasor, c in ci_dosyalari():
        for komut in c.get("hazirlik", []):
            _grup(f"hazırlık: {_ad(klasor)}")
            r = subprocess.run(_yerlestir(komut, python=sys.executable, modul=klasor.relative_to(DEPO).as_posix()), cwd=DEPO)
            _grup_bitir()
            if r.returncode:
                _hata(f"{_ad(klasor)} hazırlığı başarısız: {' '.join(komut)}")
                kod = 1
    return kod


def test(secim: list[str] | None = None) -> int:
    def secili(k: Path) -> bool:
        return not secim or any(_ad(k) == s or _ad(k).endswith("/" + s) for s in secim)

    basarisiz: list[str] = []
    for d in test_klasorleri():
        if not secili(d.parent):
            continue
        _grup(f"testler: {_ad(d.parent)}")
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(d), "-v"], cwd=DEPO)
        _grup_bitir()
        if r.returncode:
            basarisiz.append(f"testler: {_ad(d.parent)}")
    gecici = Path(os.environ.get("RUNNER_TEMP") or tempfile.mkdtemp(prefix="studyo-ci-"))
    for klasor, c in ci_dosyalari():
        if not secili(klasor):
            continue
        for adim in c.get("denetle", []):
            dosyalar = sorted({p for desen in adim["dosyalar"] for p in DEPO.glob(desen)})
            if not dosyalar:
                continue
            _grup(f"denetle: {_ad(klasor)} ({len(dosyalar)} dosya)")
            for dosya in dosyalar:
                komut = _yerlestir(adim["komut"], python=sys.executable, modul=klasor.relative_to(DEPO).as_posix(),
                                   dosya=dosya.relative_to(DEPO).as_posix(), ad=dosya.parent.name, gecici=str(gecici))
                print("$", " ".join(komut), flush=True)
                if subprocess.run(komut, cwd=DEPO).returncode:
                    basarisiz.append(f"{_ad(klasor)}: {dosya.relative_to(DEPO).as_posix()}")
            _grup_bitir()
    for b in basarisiz:
        _hata(b)
    print(f"\n{'BAŞARISIZ' if basarisiz else 'tamam'}: {len(basarisiz)} sorun", flush=True)
    return 1 if basarisiz else 0


def _ozet(readme: Path) -> str:
    """README'nin başlıktan sonraki ilk paragrafının ilk cümlesi."""
    satirlar = readme.read_text(encoding="utf-8").splitlines()
    paragraf: list[str] = []
    for s in satirlar[1:]:
        if not s.strip():
            if paragraf:
                break
            continue
        if s.startswith(("#", "```", "|", "    ")):
            if paragraf:
                break
            continue
        paragraf.append(s.strip())
    metin = " ".join(paragraf)
    metin = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", metin)  # bağlantıları düz yazıya çevir
    m = re.search(r"(?<=[^0-9A-ZÇĞİÖŞÜ])[.!?](\s|$)", metin[30:])
    return (metin[: 30 + m.start() + 1] if m else metin).strip()


def dizin_metni() -> str:
    satir = ["| Şablon | Ne yapar |", "|---|---|"]
    for d in sorted(p for p in SABLONLAR.iterdir() if p.is_dir() and (p / "README.md").exists()):
        satir.append(f"| [`{d.name}`](platform/sablonlar/{d.name}/README.md) | {_ozet(d / 'README.md').replace('|', '/')} |")
    return "\n".join(satir)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("hazirla")
    t = alt.add_parser("test")
    t.add_argument("--modul", nargs="+", help="yalnız bu modüller (ör. kinetik, sablonlar/kolaj, ortak)")
    alt.add_parser("dizin")
    a = ap.parse_args(argv)
    if a.komut == "hazirla":
        return hazirla()
    if a.komut == "test":
        return test(a.modul)
    print(dizin_metni())
    return 0


if __name__ == "__main__":
    sys.exit(main())
