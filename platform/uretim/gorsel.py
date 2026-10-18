#!/usr/bin/env python3
"""YZ görsel üretimi: Flux ve Recraft ile hero görsel, foto zemin, ikon ve logo taslağı (fal.ai).

Kodla çizilemeyen durağan görseller içindir; yazı, logo ve hareket yine şablonlarda kalır.
Akış önizleme → final: önce `flux-schnell` ile birkaç ucuz varyant (`--adet 4`), seçilen
fikir `flux-ultra` (foto) ya da `recraft` / `recraft-svg` (illüstrasyon, vektör) ile finale gider.

  plan  ne üretilecek, kaç para; harcamaz
  uret  üretir, hedef ölçüye küçültüp kırpar (final modellerde büyütme yok), kayda yazar

Kullanım:
  gorsel.py plan "prompt" --model flux-ultra --boyut 9:16 [--adet 4] [--marka marka.json]
  gorsel.py uret "prompt" --model flux-ultra --boyut 9:16 -o hero.png [--tohum 1] [--adet 4]
                 [--marka marka.json] [--stil realistic_image] [--yer "Lezzet reel, açılış"]
                 [--kayit gorsel-kaydi.csv] [--butce 1.0] [--yeniden]

`--boyut` 9:16 | 16:9 | 1:1 | 4:5 ya da 1080x1920. `--marka` markanın `prompt.uslup` cümlesini
başa ekler, Recraft'ta marka renklerini palet olarak verir. Kayıt (`gorsel-kaydi.csv`, varsayılan
çıktının yanında) `yz-kaydi` sütunlarını taşır: aynı istek ikinci kez ödenmez, lisans izlenir.
Çıkış kodu: 0 tamam, 1 hata (bütçe, büyütme, sağlayıcı), 2 kullanım hatası. Gerekenler: Pillow.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "ortak"))
sys.path.insert(0, str(HERE.parent / "marka"))

import formatlar  # noqa: E402
import saglayici  # noqa: E402

DOSYA = HERE / "gorseller.json"
KAYIT_SUTUNLARI = ("dosya", "sinif", "model", "tarih", "prompt", "kullanildigi_yer", "kaynak_ozeti", "arac",
                   "duzenleme", "istek_ozeti", "maliyet_usd", "lisans", "tohum")


class Hata(RuntimeError):
    pass


def yukle(path: str | Path = DOSYA) -> dict[str, dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["modeller"]


def hedef_boyut(deger: str) -> tuple[int, int]:
    if "x" in deger and deger.replace("x", "").isdigit():
        w, h = (int(v) for v in deger.split("x"))
        return w, h
    try:
        return formatlar.boyut(deger)
    except ValueError as e:
        raise Hata(f"boyut {deger!r}: 9:16, 16:9, 1:1, 4:5 ya da GENxYUK") from e


def en_yakin_oran(w: int, h: int, oranlar: list[str]) -> str:
    def fark(o: str) -> float:
        a, b = (int(v) for v in o.split(":"))
        return abs(math.log((a / b) / (w / h)))
    return min(oranlar, key=fark)


def istek_boyutu(w: int, h: int, m: dict) -> tuple[int, int]:
    """Piksel alan modelde istenecek ölçü: hedef oranında, en uzun kenar sınırı ve kat kuralıyla."""
    olcek = min(1.0, m["azami_kenar"] / max(w, h))
    kat = m.get("kat", 1)
    return (max(kat, round(w * olcek / kat) * kat), max(kat, round(h * olcek / kat) * kat))


def maliyet(m: dict, w: int, h: int) -> float:
    if "usd_mp" in m:
        iw, ih = istek_boyutu(w, h, m)
        return round(m["usd_mp"] * math.ceil(iw * ih / 1_000_000), 4)
    return float(m.get("usd_gorsel", 0))


def marka_bilgisi(yol: str | None) -> tuple[str, list[str]]:
    if not yol:
        return "", []
    import marka as marka_mod
    m, bulgular = marka_mod.yukle(yol)
    if m is None:
        raise Hata(f"marka okunamadı: {'; '.join(str(b) for b in bulgular)}")
    renkler = list(dict.fromkeys(v for v in m.renk.values() if isinstance(v, str) and v.startswith("#")))[:5]
    return m.prompt_uslup.strip(), renkler


def govde(prompt: str, m: dict, w: int, h: int, tohum: int, stil: str | None, renkler: list[str]) -> dict:
    b = {"prompt": prompt, **m.get("govde", {})}
    if m["boyut"] == "oran":
        b["aspect_ratio"] = en_yakin_oran(w, h, m["oranlar"])
    else:
        iw, ih = istek_boyutu(w, h, m)
        b["image_size"] = {"width": iw, "height": ih}
    if m["tur"] == "fal" and not m.get("model", "").startswith("fal-ai/recraft"):
        b["seed"] = tohum
        b["num_images"] = 1
    if stil:
        b["style"] = stil
    if m.get("renkler") and renkler:
        b["colors"] = [{"r": int(c[1:3], 16), "g": int(c[3:5], 16), "b": int(c[5:7], 16)} for c in renkler]
    return b


def istek_ozeti(ad: str, m: dict, b: dict) -> str:
    ham = json.dumps({"ad": ad, "model": m.get("model", ""), "govde": b}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()


def kayit_oku(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def kayit_ekle(path: Path, satir: dict) -> None:
    yeni = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KAYIT_SUTUNLARI)
        if yeni:
            w.writeheader()
        w.writerow({k: satir.get(k, "") for k in KAYIT_SUTUNLARI})


def _ozet_dosya(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sonlandir(ham: Path, hedef: Path, w: int, h: int, taslak: bool) -> str:
    """Hamı hedef ölçüye getirir: kapla (cover), ortadan kırp, Lanczos. Final modelde büyütme hatadır."""
    from PIL import Image
    im = Image.open(ham)
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    olcek = max(w / im.width, h / im.height)
    if olcek > 1.01 and not taslak:
        raise Hata(f"{ham.name} {im.width}x{im.height}, hedef {w}x{h}: büyütmek gerekir (bulanıklaşır); "
                   "daha büyük üreten model ya da daha küçük hedef seçin")
    yw, yh = max(w, round(im.width * olcek)), max(h, round(im.height * olcek))
    im = im.resize((yw, yh), Image.LANCZOS)
    x, y = (yw - w) // 2, (yh - h) // 2
    im.crop((x, y, x + w, y + h)).save(hedef)
    return f"{'büyütme' if olcek > 1.01 else 'küçültme'} ×{olcek:.2f} + orta kırpma → {w}x{h}"


def isler(a: argparse.Namespace, m: dict) -> list[dict]:
    w, h = hedef_boyut(a.boyut)
    uslup, renkler = marka_bilgisi(a.marka)
    prompt = " ".join(p for p in (uslup, a.prompt.strip()) if p)
    out = []
    for i in range(a.adet):
        tohum = a.tohum + i
        b = govde(prompt, m, w, h, tohum, a.stil, renkler)
        out.append({"tohum": tohum, "govde": b, "ozet": istek_ozeti(a.model, m, b), "w": w, "h": h,
                    "usd": maliyet(m, w, h)})
    return out


def plan(a: argparse.Namespace, modeller: dict) -> int:
    m = modeller[a.model]
    ii = isler(a, m)
    w, h = ii[0]["w"], ii[0]["h"]
    istek = ii[0]["govde"].get("aspect_ratio") or "{width}x{height}".format(**ii[0]["govde"].get("image_size", {}))
    print(f"{a.model} ({m.get('model', 'kuru')}): {a.adet} görsel, hedef {w}x{h}, istek {istek}")
    print(f"  tahmini {sum(i['usd'] for i in ii):.3f} $  ({ii[0]['usd']:.3f} $/görsel), "
          f"lisans {'ticari' if m.get('ticari') else 'ticari değil'}{', taslak' if m.get('taslak') else ''}")
    print(f"  prompt: {ii[0]['govde']['prompt']}")
    return 0


def uret(a: argparse.Namespace, modeller: dict, ag=saglayici.http) -> int:
    m = modeller[a.model]
    hedef = Path(a.cikti)
    kayit = Path(a.kayit) if a.kayit else hedef.parent / "gorsel-kaydi.csv"
    satirlar = kayit_oku(kayit)
    ii = isler(a, m)
    svg = m.get("cikti") == "svg"
    odenecek = [i for i in ii if a.yeniden or not any(r["istek_ozeti"] == i["ozet"] for r in satirlar)]
    toplam = round(sum(i["usd"] for i in odenecek), 4)
    if toplam > a.butce:
        print(f"HATA: tahmini {toplam:.3f} $ bütçeyi ({a.butce:.2f} $) aşıyor; --butce ile artırın", file=sys.stderr)
        return 1
    hedef.parent.mkdir(parents=True, exist_ok=True)
    kod = 0
    for n, i in enumerate(ii, 1):
        ad = hedef.stem if len(ii) == 1 else f"{hedef.stem}-{n}"
        son = hedef.with_name(ad + (".svg" if svg else hedef.suffix or ".png"))
        eski = next((r for r in reversed(satirlar) if r["istek_ozeti"] == i["ozet"]), None)
        ham = None
        if eski and not a.yeniden:
            aday = kayit.parent / eski["dosya"]
            if not aday.exists():
                print(f"HATA: {ad}: aynı istek kayıtta ({eski['dosya']}) ama dosya yok; yeniden ödemek için --yeniden",
                      file=sys.stderr)
                kod = 1
                continue
            ham, maliyet_usd = aday, 0.0
            print(f"önbellek: {ad} ← {eski['dosya']} (ödeme yok)")
        else:
            try:
                ham = _indir(i, m, son, ag)
            except saglayici.SaglayiciHatasi as e:
                print(f"HATA: {ad}: {e}", file=sys.stderr)
                kod = 1
                continue
            maliyet_usd = i["usd"]
            kayit_ekle(kayit, {
                "dosya": _goreli(ham, kayit.parent), "sinif": "gorsel", "model": m.get("model", a.model),
                "tarih": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "prompt": i["govde"]["prompt"],
                "kullanildigi_yer": a.yer or "", "kaynak_ozeti": _ozet_dosya(ham), "arac": "gorsel.py",
                "duzenleme": "ham", "istek_ozeti": i["ozet"], "maliyet_usd": f"{maliyet_usd:.4f}",
                "lisans": "kuru" if m["tur"] == "kuru" else ("ticari" if m.get("ticari") else "ticari-degil"),
                "tohum": i["tohum"]})
        if m["tur"] == "kuru":
            print(f"kuru: {ham}")
            continue
        if svg:
            if ham != son:
                son.write_bytes(ham.read_bytes())
            print(f"{son} (vektör, {maliyet_usd:.3f} $)")
            continue
        try:
            not_ = sonlandir(ham, son, i["w"], i["h"], bool(m.get("taslak")))
        except Hata as e:
            print(f"HATA: {e}", file=sys.stderr)
            kod = 1
            continue
        print(f"{son}: {not_} ({maliyet_usd:.3f} $){' — taslak, teslime girmez' if m.get('taslak') else ''}")
    return kod


def _goreli(p: Path, kok: Path) -> str:
    try:
        return p.resolve().relative_to(kok.resolve()).as_posix()
    except ValueError:
        return str(p.resolve())


def _indir(i: dict, m: dict, son: Path, ag) -> Path:
    if m["tur"] == "kuru":
        out = son.with_suffix(".kuru.json")
        out.write_text(json.dumps(i["govde"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return out
    sonuc = saglayici.fal_kuyruk(m["model"], i["govde"], ag, m.get("anahtar", "FAL_KEY"))
    try:
        g = (sonuc.get("images") or [sonuc.get("image")])[0]
        url, tip = g["url"], g.get("content_type", "")
        veri = ag("GET", url, None, None)
    except (OSError, KeyError, IndexError, TypeError, ValueError) as e:
        raise saglayici.SaglayiciHatasi(f"fal.ai sonucu okunamadı: {e}") from e
    uzanti = ".svg" if ("svg" in tip or m.get("cikti") == "svg") else (".jpg" if "jpeg" in tip else ".png")
    out = son.with_name(son.stem + ".ham" + uzanti)
    out.write_bytes(veri)
    return out


def main(argv: list[str] | None = None, ag=saglayici.http) -> int:
    modeller = yukle()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("plan", "uret"):
        p = alt.add_parser(ad)
        p.add_argument("prompt")
        p.add_argument("--model", required=True, choices=list(modeller))
        p.add_argument("--boyut", default="9:16")
        p.add_argument("--adet", type=int, default=1)
        p.add_argument("--tohum", type=int, default=1)
        p.add_argument("--marka", help="marka.json: üslup cümlesi ve (Recraft) renk paleti")
        p.add_argument("--stil", help="Recraft stili, ör. realistic_image, digital_illustration/hand_drawn")
        if ad == "uret":
            p.add_argument("-o", "--cikti", required=True)
            p.add_argument("--kayit")
            p.add_argument("--yer", help="kullanıldığı yer (kayda yazılır)")
            p.add_argument("--butce", type=float, default=1.0, help="bu komutun harcayabileceği en çok USD")
            p.add_argument("--yeniden", action="store_true", help="kayıttaki aynı isteği yeniden öde")
    a = ap.parse_args(argv)
    if a.adet < 1:
        ap.error("--adet en az 1")
    try:
        return plan(a, modeller) if a.komut == "plan" else uret(a, modeller, ag)
    except Hata as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
