"""Render süresi ölçümü: kalite raporuna stil başına sn/kare yazar (beyin fırtınası 4.4).

Ölçümü başlatan taraf (`uret.py`) şablonu çalıştırmadan önce ortama `STUDYO_RENDER_BASLANGIC` (epoch sn) ve
`STUDYO_STIL` yazar; şablon render sonunda `kalite.render_sonrasi` ile bu modülü çağırır. Ortamda başlangıç
yoksa (şablon elle çalıştırıldıysa) rapora bir şey eklenmez.
"""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path

ALANLAR = ["tarih", "is", "stil", "format", "sure_sn", "kare", "render_sn", "sn_kare", "dosya"]


def olc(r: dict, simdi: float | None = None) -> dict | None:
    """Ortamdaki başlangıçtan bu ana geçen süre ve videonun kare sayısı → {"stil", "render_sn", "kare", "sn_kare"}."""
    bas = os.environ.get("STUDYO_RENDER_BASLANGIC")
    if not bas:
        return None
    try:
        gecen = (simdi or time.time()) - float(bas)
    except ValueError:
        return None
    v = r.get("akis", {}).get("video") or {}
    kare = round((v.get("fps") or 0) * (r.get("akis", {}).get("sure") or 0))
    return {"stil": os.environ.get("STUDYO_STIL") or None, "render_sn": round(gecen, 1), "kare": kare,
            "sn_kare": round(gecen / kare, 3) if kare else None}


def ekle(r: dict) -> dict:
    """Kalite raporuna `render` alanını ekler (ölçüm yoksa raporu olduğu gibi bırakır)."""
    o = olc(r)
    if o:
        r["render"] = o
    return r


def kaydet(csv_yolu: Path, is_adi: str, fmt: str, r: dict) -> None:
    """Ölçümü ortak tabloya bir satır olarak ekler; takvim yavaş stilleri buradan görür."""
    o = r.get("render")
    if not o:
        return
    csv_yolu = Path(csv_yolu)
    csv_yolu.parent.mkdir(parents=True, exist_ok=True)
    yeni = not csv_yolu.exists()
    with csv_yolu.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if yeni:
            w.writerow(ALANLAR)
        w.writerow([time.strftime("%Y-%m-%d"), is_adi, o.get("stil") or "", fmt, round(r["akis"].get("sure") or 0, 2),
                    o["kare"], o["render_sn"], o["sn_kare"] if o["sn_kare"] is not None else "", Path(r["dosya"]).name])
