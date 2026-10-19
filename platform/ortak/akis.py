"""Kısa video şablonlarının ortak adımları: çıktı klasörü, seslendirme, ses + görüntü birleştirme.

Şablonlar bu modülü `sys.path`'e `platform/ortak` ekleyip `import akis` ile kullanır (`platform`
bir Python paketi olamaz, standart kütüphanedeki `platform` modülünü gölgeler).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
SES = BURADA.parent / "ses"


def cikti_klasoru(s: dict, arg: str | None) -> Path:
    return Path(arg) if arg else Path(s["_klasor"]) / "cikti"


def sureler_oku(klasor: Path) -> dict[str, float]:
    """`seslendirme.json`'daki satır süreleri (id → sn); dosya yoksa boş."""
    k = Path(klasor) / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}


def seslendir(s: dict, cikti: Path, saglayici: str | None = "otomatik", ses: str | None = None) -> dict:
    """Senaryonun satırlarını `cikti/seslendirme`ye seslendirir (bkz. `seslendirme.senaryodan`).

    `otomatik`: ElevenLabs; anahtar, ağ ya da kredi yoksa Piper yedeği (kalite raporunda uyarı). Senaryo
    `seslendirme.saglayici: "piper"` derse Piper. Ses ve dil komut satırından ya da senaryodan gelir.
    """
    if str(SES) not in sys.path:
        sys.path.insert(0, str(SES))
    import seslendirme
    return seslendirme.senaryodan(s, Path(cikti) / "seslendirme", saglayici, ses)


def eksik_seslendirme(s: dict, bilgi: dict) -> list[str]:
    return [x["id"] for x in s["seslendirme"].get("satirlar", []) if x["id"] not in bilgi.get("seslendirme", {})]


def uyar_eksik(eksik: list[str]) -> None:
    if eksik:
        print(f"UYARI: seslendirme yok ({', '.join(eksik)}); önce `seslendir` çalıştırın. Video seslendirmesiz çıkar.",
              file=sys.stderr)


def birlestir(sessiz: Path, ses: Path, hedef: Path, kalite: bool = True) -> Path:
    """Sessiz videoya master sesi ekler (görüntü kopyalanır, ses AAC 192k) ve kalite kapısından geçirir.

    Kalite raporu `hedef` yanına `<ad>.kalite.json` olarak yazılır; sorun varsa uyarı basılır,
    render durmaz (karar insanda). `kalite=False` ya da STUDYO_KALITE=0 kapatır.
    """
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(sessiz), "-i", str(ses),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(hedef)],
                   check=True)
    import okunabilirlik
    okunabilirlik.kaydi_tasi(sessiz, hedef)
    if kalite:
        import kalite as k
        k.render_sonrasi(hedef)
    return hedef
