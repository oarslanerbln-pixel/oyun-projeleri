"""Kanca (hook) varyantları: aynı videonun üç farklı açılışı, A/B testi için.

    K=platform/sablonlar/sahne/kanca.py
    python3 $K yaz     ornek/sahne.json [--turler soru rakam sok]     # <ad>-kanca-<tür>.json senaryoları
    # çıktı: cikti/kanca-<tür>/ (her varyantın kendi seslendirme klasörü)
    python3 $K kontakt ornek/sahne.json --stil kinetik [--format 9:16] # üç açılışın ilk iki sahnesi tek sayfada
    python3 $K uret    ornek/sahne.json --stil kinetik --format 9:16  # üç video (ses önbellekten, yalnız kanca satırı yeni)

| Tür | Açılış |
| --- | --- |
| `soru` | yeni ilk sahne: izleyiciye soru ("Bunu biliyor muydun?"); videonun konusu alt satırda |
| `rakam` | videodaki en çarpıcı sayı (`sayi` sahnesi ya da grafiğin en büyük değeri) başa alınır |
| `sok` | ilk sahne "görsel şok" olur: ekran vurgu rengiyle dolar, yazı büyükten oturur (`"kanca": "sok"`) |

Kanca metnini kendin yazmak için senaryoya: `"kancalar": {"soru": {"metin": "Hâlâ sabah kahvesi mi?", "seslendirme": "..."}}`
(alanlar o sahne tipinin alanları; `tip` verilmezse soru → baslik). Videonun geri kalanı aynıdır, seslendirme satırları
önbellekten gelir (ElevenLabs kredisi yalnız yeni kanca satırına harcanır).
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
import dil  # noqa: E402

TURLER = dil.KANCA
SORU = {"tr": ("Bunu biliyor muydun?", "Bunu biliyor muydun?"), "de": ("Wusstest du das?", "Wusstest du das?")}


def dil_kodu(s: dict) -> str:
    """Senaryonun dili (seslendirme metninden): Almanca sözcükler baskınsa de, yoksa tr."""
    metin = " ".join(sh.get("seslendirme", "") for sh in s["sahneler"]).lower()
    de = len(re.findall(r"\b(und|der|die|das|ist|nicht|mit|du|ein|eine|für|auf)\b", metin))
    tr = len(re.findall(r"[ışğ]|\b(ve|bir|bu|için|ile|çok|daha)\b", metin))
    return "de" if de > tr else "tr"


def _konu(s: dict) -> str:
    for sh in s["sahneler"]:
        if sh["tip"] in ("baslik", "cta") and sh.get("metin"):
            return sh["metin"]
    return (s.get("marka") or {}).get("ad", "")


def _rakam(s: dict) -> tuple[dict, int | None] | None:
    """(kanca sahnesi, çıkarılacak sahne sırası): ilk sayı sahnesi, yoksa grafiğin en büyük değeri"""
    for i, sh in enumerate(s["sahneler"]):
        if sh["tip"] == "sayi":
            return {**copy.deepcopy(sh), "kanca": "rakam"}, i
    for sh in s["sahneler"]:
        if sh["tip"] == "grafik":
            try:
                e, v = max(dil.veri_oku(sh, s.get("_klasor", ".")), key=lambda r: r[1])
            except dil.SenaryoHatasi:
                continue
            deger = dil.bicim(v, sh.get("birim", ""))
            if len(deger) > 8:  # birim sığmazsa yalnız sayı (birim seslendirmede kalır)
                deger = dil.bicim(v)
            if len(deger) <= 8:
                out = {"tip": "sayi", "deger": deger, "etiket": e[:28], "kanca": "rakam"}
                if sh.get("baslik"):
                    out["ust"] = sh["baslik"][:20]
                out["seslendirme"] = f"{e}: {dil.bicim(v, sh.get('birim', ''))}."
                return out, None
    return None


def varyant(s: dict, tur: str) -> dict | None:
    """Senaryonun `tur` açılışlı kopyası (yoksa None: ör. rakamı olmayan video)."""
    if tur not in TURLER:
        raise ValueError(f"kanca türü {tur} ({', '.join(TURLER)})")
    v = copy.deepcopy({k: x for k, x in s.items() if k != "kancalar"})
    shs = v["sahneler"]
    ozel = (s.get("kancalar") or {}).get(tur)
    if ozel:
        sh = {"tip": "baslik", **ozel, "kanca": tur} if isinstance(ozel, dict) else {"tip": "baslik", "metin": ozel[:28], "seslendirme": ozel, "kanca": tur}
        if tur == "sok":
            shs[0] = {**sh}
        else:
            shs.insert(0, sh)
    elif tur == "soru":
        metin, oku = SORU[dil_kodu(s)]
        sh = {"tip": "baslik", "metin": metin, "seslendirme": oku, "kanca": "soru"}
        konu = _konu(s)
        if konu and len(konu) <= 40 and shs[0].get("metin") != konu:
            sh["alt"] = konu
        shs.insert(0, sh)
    elif tur == "rakam":
        r = _rakam(s)
        if not r:
            return None
        sh, cikar = r
        if cikar is not None:
            del shs[cikar]
        shs.insert(0, sh)
    else:  # sok: aynı ilk sahne, şok görünümüyle
        shs[0] = {**shs[0], "kanca": "sok"}
    v["kimlik"] = f"{s.get('kimlik', 'sahne')}-kanca-{tur}"
    return v


def yaz(yol: Path, turler: list[str]) -> list[Path]:
    s = dil.yukle(yol)
    out = []
    for tur in turler:
        v = varyant(s, tur)
        if v is None:
            print(f"atlandı: {tur} (videoda sayı ya da grafik yok; `kancalar.rakam` ile yaz)", file=sys.stderr)
            continue
        hedef = yol.with_name(f"{yol.stem}-kanca-{tur}.json")
        hedef.write_text(json.dumps({k: x for k, x in v.items() if not k.startswith("_")}, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
        v["_klasor"] = s["_klasor"]
        hatalar = dil.denetle(v)
        for h in hatalar:
            print(f"HATA ({tur}): {h}", file=sys.stderr)
        if hatalar:
            raise SystemExit(1)
        out.append(hedef)
    return out


def kontakt(yollar: list[Path], stil: str, fmt: str, cikti: Path) -> Path:
    """Her varyant bir satır: kanca sahnesinin ortası ve sonu, ardından ikinci sahne."""
    import skia
    import kaplama
    import sahne
    import senkron
    W, H = sahne._boyut(fmt, 0.34)
    etiket, ara = 230, 14
    SW, SH = etiket + 3 * (W + ara) + ara, 70 + len(yollar) * (H + ara)
    surf = skia.Surface(SW, SH)
    f = skia.Font(kaplama.motor.yazi_tipi(700), 30)
    with surf as cv:
        cv.clear(0xFFF6F1E4)
        for j, ad in enumerate(("kanca", "kanca sonu", "devamı")):
            cv.drawString(ad, etiket + ara + j * (W + ara), 46, f, skia.Paint(AntiAlias=True, Color=0xFF555046))
        for i, yol in enumerate(yollar):
            s = dil.yukle(yol)
            ses = cikti / f"kanca-{yol.stem.rsplit('-', 1)[-1]}" / "seslendirme"
            z = senkron.bagla(dil.zamanla(s, dil.sureler_oku(ses)), ses)
            a, b = z["sahneler"][0], z["sahneler"][1]
            anlar = [(a["bas"] + a["son"]) / 2, a["son"] - 0.12, b["son"] - 0.12]
            y = 70 + i * (H + ara)
            cv.drawString(yol.stem.rsplit("-", 1)[-1], 20, y + H / 2 + 10, f, skia.Paint(AntiAlias=True, Color=0xFF1F1B16))
            for j, img in enumerate(sahne._kareler(z, stil, fmt, W, H, anlar, cikti)):
                if img is not None:
                    cv.drawImageRect(img, skia.Rect.MakeXYWH(etiket + ara + j * (W + ara), y, W, H), skia.SamplingOptions(skia.FilterMode.kLinear))
    cikti.mkdir(parents=True, exist_ok=True)
    hedef = cikti / f"{yollar[0].stem.rsplit('-kanca-', 1)[0]}-kancalar-{stil}-{fmt}.png"
    surf.makeImageSnapshot().save(str(hedef), skia.kPNG)
    return hedef


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("komut", choices=("yaz", "kontakt", "uret"))
    ap.add_argument("senaryo")
    ap.add_argument("--turler", nargs="+", default=list(TURLER), choices=TURLER)
    ap.add_argument("--stil"); ap.add_argument("--format", default="9:16")
    ap.add_argument("-o", "--cikti")
    a = ap.parse_args(argv)
    yol = Path(a.senaryo)
    yollar = yaz(yol, a.turler)
    if a.komut == "yaz":
        for p in yollar:
            print(p)
        return 0
    if not a.stil:
        print("HATA: --stil gerekli", file=sys.stderr); return 1
    cikti = Path(a.cikti) if a.cikti else yol.parent / "cikti"
    if a.komut == "kontakt":
        sys.path.append(str(BURADA.parents[1] / "ortak"))
        import formatlar
        print(kontakt(yollar, a.stil, formatlar.anahtar(a.format), cikti))
        return 0
    kod = 0
    for p in yollar:  # her varyant kendi klasöründe (satır kimlikleri kayar); ses önbelleği satır metniyle eşleşir
        kod |= subprocess.call([sys.executable, str(BURADA / "sahne.py"), "uret", str(p), "--stil", a.stil,
                                "--format", a.format, "-o", str(cikti / f"kanca-{p.stem.rsplit('-', 1)[-1]}")])
    return kod


if __name__ == "__main__":
    sys.exit(main())
