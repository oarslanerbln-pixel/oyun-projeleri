"""Render'dan önce önizleme: her stil için birkaç kare, tek karşılaştırma sayfasında.

    python3 platform/ortak/onizleme.py ornekler/tuzak-fiyat-origami/origami.json ornekler/hamurkar-firin/tek-cizgi.json
    python3 platform/ortak/onizleme.py kolaj=is/senaryo-kolaj.json izometrik=is/senaryo-izo.json --an 2 6 9 -o onizleme.png

Her senaryo kendi şablonunun `kare` komutuyla çizilir (video, ses ve kodlama yok; birkaç saniye sürer).
Şablon `ad=yol` ile verilir; verilmezse senaryonun `stil` alanından, o da yoksa dosya adından bulunur.
Satırlar stil, sütunlar an; dikey formatta platform arayüzünün kapattığı bölgeler taralıdır. Her kareye
kalite kapısının banding ve netlik ölçüsü uygulanır, sorunlu kare etiketinde yazar.

Amaç: stil seçimi ve senaryo onayı tam render'dan önce, tek görüntüyle yapılsın (bkz. platform/docs/uretim-standardi.md).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BURADA = Path(__file__).resolve().parent
SABLONLAR = BURADA.parent / "sablonlar"
sys.path.insert(0, str(BURADA))
import kalite  # noqa: E402
from formatlar import anahtar  # noqa: E402

# kendi komut satırı olan şablonlar; geri kalan her stil `stil.py --stil <ad>` üzerinden çizilir
KOMUTLAR = {
    "kinetik": "kinetik/kinetik.py",
    "origami": "origami/origami.py",
    "tek-cizgi": "tek_cizgi/tek_cizgi.py",
    "minyatur": "minyatur/minyatur.py",
    "kolaj": "kolaj/kolaj.py",
}
IKI_NOKTALI = {"minyatur"}  # format seçeneklerini "9:16" yazımıyla bekleyenler
VARSAYILAN_ANLAR = (0.15, 0.5, 0.85)  # süreye oranla


def _stil_secenekleri() -> set[str]:
    sys.path.insert(0, str(SABLONLAR / "stil"))
    try:
        import motor
        return set(motor.STILLER) | {"bumper", "mekan"}
    except Exception:
        return {"bumper", "mekan"}


def sablon_bul(senaryo: dict, yol: Path, ad: str | None) -> str:
    if ad:
        return ad
    if senaryo.get("stil"):
        return senaryo["stil"]
    bilinen = set(KOMUTLAR) | _stil_secenekleri()
    for parca in [yol.stem, *reversed(yol.resolve().parent.parts)]:  # önce dosya adı, sonra klasörler
        if parca.replace("_", "-") in bilinen:
            return parca.replace("_", "-")
    return "kinetik"


def komut(ad: str, yol: Path, anlar: list[float], fmt: str, cikti: Path) -> list[str]:
    f = fmt.replace("x", ":") if ad in IKI_NOKTALI else fmt
    ortak = ["kare", str(yol), "--an", *[f"{t:g}" for t in anlar], "--format", f, "-o", str(cikti)]
    if ad in KOMUTLAR:
        return [sys.executable, str(SABLONLAR / KOMUTLAR[ad]), *ortak]
    return [sys.executable, str(SABLONLAR / "stil" / "stil.py"), *ortak, "--stil", ad]


def anlar_bul(senaryo: dict, istek: list[float] | None) -> list[float]:
    if istek:
        return istek
    sure = senaryo.get("sure")
    if isinstance(sure, (int, float)) and sure > 0:
        return [round(sure * o, 1) for o in VARSAYILAN_ANLAR]
    return [1.0, 5.0, 9.0]


def onizle(girdiler: list[str], hedef: Path, anlar: list[float] | None = None, fmt: str = "9x16") -> dict:
    import numpy as np
    from PIL import Image
    fmt = anahtar(fmt)
    kareler, rapor = [], {"format": fmt, "sayfa": str(hedef), "stiller": []}
    sutun = 1
    with tempfile.TemporaryDirectory() as tmp:
        for i, g in enumerate(girdiler):
            ad, _, yol = g.rpartition("=")
            yol = Path(yol)
            s = json.loads(yol.read_text(encoding="utf-8"))
            ad = sablon_bul(s, yol, ad or None)
            an = anlar_bul(s, anlar)
            sutun = max(sutun, len(an))
            r = subprocess.run(komut(ad, yol, an, fmt, Path(tmp) / str(i)), capture_output=True, text=True)
            pngler = [Path(x.strip()) for x in r.stdout.splitlines() if x.strip().endswith(".png")]
            kayit = {"stil": ad, "senaryo": str(yol), "anlar": an, "kareler": []}
            if r.returncode != 0 or not pngler:
                kayit["hata"] = (r.stderr.strip().splitlines() or [f"çıkış kodu {r.returncode}"])[-1]
                rapor["stiller"].append(kayit)
                continue
            for t, p in zip(an, pngler):
                k = np.asarray(Image.open(p).convert("RGB"))
                b, n = kalite.banding_orani(k), kalite.netlik(k)
                notlar = []
                if b >= kalite.ESIK["banding_uyari"]:
                    notlar.append(f"banding %{b * 100:.0f}")
                if n is not None and n < kalite.ESIK["netlik_uyari"]:
                    notlar.append("yumuşak")
                etiket = " · ".join([ad, f"{t:g} sn", *notlar])
                kareler.append((etiket, k))
                kayit["kareler"].append({"an": t, "banding": round(b, 4), "netlik": None if n is None else round(n, 3)})
            # satırlar hizalı kalsın: eksik kare yerine boş hücre
            for _ in range(sutun - len(pngler[:len(an)])):
                kareler.append(("", np.full_like(kareler[-1][1], 245)))
            rapor["stiller"].append(kayit)
        if kareler:
            kalite.kontakt_yaz(kareler, hedef, dikey=fmt == "9x16", sutun=sutun)
    return rapor


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("senaryolar", nargs="+", help="senaryo.json ya da stil=senaryo.json")
    ap.add_argument("--an", type=float, nargs="+", help="saniye cinsinden anlar (varsayılan: sürenin %%15, %%50, %%85'i)")
    ap.add_argument("--format", default="9x16")
    ap.add_argument("-o", "--cikti", default="onizleme.png")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = onizle(a.senaryolar, Path(a.cikti), a.an, a.format)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        for s in r["stiller"]:
            print(f"{s['stil']:<12} {'HATA: ' + s['hata'] if 'hata' in s else str(len(s['kareler'])) + ' kare'}")
        print(r["sayfa"])
    return 1 if any("hata" in s for s in r["stiller"]) else 0


if __name__ == "__main__":
    sys.exit(main())
