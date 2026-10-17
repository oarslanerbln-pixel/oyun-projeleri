#!/usr/bin/env python3
"""YZ üretim hattı: çekim listesindeki `sinif=C` çekimlerini sağlayıcıya gönderir.

Hat animasyon şablonunun (`platform/sablonlar/animasyon`) üstünde çalışır ve
projeyi önce onun bütün denetimlerinden geçirir; hatalı projede para harcanmaz.

  plan       her C çekimi için iş, faturalı süre ve maliyet; bütçeyi aşarsa HATA
  calistir   planı yürütür; her çıktı yz-kaydi'ye satır olarak yazılır
  denetle    lisans kapısı: onaylı ya da kilitli her C çekiminin kaydı var ve
             ticari teslime uygun

Kullanım:
  uretim.py plan <proje.json> [--saglayici AD]
  uretim.py calistir <proje.json> [--saglayici AD] [--yeniden]
  uretim.py denetle <proje.json>

`proje.json` içinde:
  "uretim": {"saglayici": "fal-kling", "butce_usd": 20, "azami_deneme": 2, "tohum": 1, "ticari": true}
  "yz_kaydi": "…/yz-kaydi.csv"   (verilmezse proje klasöründe yz-kaydi.csv)

Çıkış kodu: 0 temiz, 1 hata, 2 kullanım hatası. Yalnız Python standart kitaplığı.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sablonlar" / "animasyon"))

import _yollar  # noqa: E402,F401  (sablonlar/animasyon: marka, metin, medya)
import proje as proje_mod  # noqa: E402
import saglayici as saglayici_mod  # noqa: E402
from metin import HATA, UYARI, Bulgu, has_errors  # noqa: E402

KAYIT_SUTUNLARI = ("dosya", "sinif", "model", "tarih", "prompt", "kullanildigi_yer", "kaynak_ozeti", "arac",
                   "duzenleme", "istek_ozeti", "maliyet_usd", "lisans", "tohum")
VARSAYILAN = {"saglayici": "kuru", "butce_usd": 0.0, "azami_deneme": 2, "tohum": 1, "ticari": True}

# İş durumları
URETILECEK, ONBELLEK, KAYITTA, BEKLIYOR, KILITLI = "üretilecek", "önbellekte", "kayıtta", "V1 bekliyor", "kilitli"


@dataclass
class Plan:
    proje: proje_mod.Proje
    kok: Path
    ayar: dict
    saglayici: str
    sag: dict
    kayit_yolu: Path
    harcanan: float
    isler: list[dict] = field(default_factory=list)

    @property
    def tahmini(self) -> float:
        return round(sum(i["maliyet_usd"] for i in self.isler if i["durum"] == URETILECEK), 4)


def faturali_sure(sure: float, sureler: list | None) -> float | None:
    """Sağlayıcı yalnız belli süreler üretir; çekim en yakın üst süreden faturalanır."""
    if not sureler:
        return sure
    uygun = [s for s in sorted(sureler) if s >= sure]
    return float(uygun[0]) if uygun else None


def dosya_ozeti(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def istek_ozeti(saglayici: str, sag: dict, prompt: str, negatif: str, kare_ozeti: str,
                faturali_sn: float, tohum: int) -> str:
    """Aynı istek ikinci kez ödenmesin diye önbellek anahtarı. Çıktıyı değiştiren her
    girdi içindedir: model, prompt, negatif, kare içeriği, süre, tohum."""
    ham = json.dumps({"saglayici": saglayici, "model": sag.get("model", ""), "prompt": prompt, "negatif": negatif,
                      "kare": kare_ozeti, "sn": faturali_sn, "tohum": tohum}, ensure_ascii=False, sort_keys=True)
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


def lisans(sag: dict) -> str:
    if sag["tur"] == "kuru":
        return "kuru"
    return "ticari" if sag.get("ticari") else "ticari-degil"


def _prompt(marka, c) -> tuple[str, str]:
    parcalar = [marka.prompt_uslup.strip(), c.gorsel and f"Sahne: {c.gorsel}.", c.kamera and f"Kamera: {c.kamera}."]
    return " ".join(p for p in parcalar if p), ", ".join(marka.prompt_negatif)


def _ayar(data: dict, saglayicilar: dict, secilen: str | None) -> tuple[dict, list[Bulgu]]:
    b: list[Bulgu] = []
    raw = data.get("uretim") or {}
    if not isinstance(raw, dict):
        return dict(VARSAYILAN), [Bulgu(HATA, "proje.uretim", "nesne olmalı")]
    ayar = {**VARSAYILAN, **raw}
    if secilen:
        ayar["saglayici"] = secilen
    if ayar["saglayici"] not in saglayicilar:
        b.append(Bulgu(HATA, "proje.uretim.saglayici",
                       f"{ayar['saglayici']!r} bilinmiyor; {', '.join(saglayicilar)}"))
        return ayar, b
    for key, tip in (("butce_usd", (int, float)), ("azami_deneme", int), ("tohum", int), ("ticari", bool)):
        v = ayar[key]
        if not (isinstance(v, bool) if tip is bool else isinstance(v, tip) and not isinstance(v, bool)):
            b.append(Bulgu(HATA, f"proje.uretim.{key}", "türü yanlış"))
    if not has_errors(b) and ayar["azami_deneme"] < 1:
        b.append(Bulgu(HATA, "proje.uretim.azami_deneme", "en az 1"))
    sag = saglayicilar[ayar["saglayici"]]
    if sag["tur"] == "elle":
        b.append(Bulgu(HATA, "proje.uretim.saglayici", f"{ayar['saglayici']!r} araç dışında elle üretilir; çağrılamaz"))
    elif sag["tur"] == "henuz-yok":
        b.append(Bulgu(UYARI, "proje.uretim.saglayici", f"{ayar['saglayici']!r} için bağdaştırıcı yok; yalnız tahmin"))
    if ayar["ticari"] and sag["tur"] != "kuru" and not sag.get("ticari"):
        b.append(Bulgu(HATA, "proje.uretim.saglayici",
                       f"{ayar['saglayici']!r} ticari kullanıma izin vermiyor; proje ticari teslim istiyor"))
    return ayar, b


def plan_kur(proje_json: str | Path, secilen: str | None = None, kok: Path | None = None,
             yeniden: bool = False) -> tuple[Plan | None, list[Bulgu]]:
    proje_json = Path(proje_json).resolve()
    kok = (kok or proje_mod.depo_koku(proje_json.parent)).resolve()
    p, b = proje_mod.yukle(proje_json, kok)
    if p is None:
        return None, b
    data = json.loads(proje_json.read_text(encoding="utf-8"))
    saglayicilar = saglayici_mod.yukle()
    ayar, ab = _ayar(data, saglayicilar, secilen)
    b += ab
    if has_errors(ab):
        return None, b
    sag = saglayicilar[ayar["saglayici"]]
    kayit_yolu = kok / data["yz_kaydi"] if data.get("yz_kaydi") else p.klasor / "yz-kaydi.csv"
    kayitlar = kayit_oku(kayit_yolu)
    harcanan = round(sum(float(r.get("maliyet_usd") or 0) for r in kayitlar), 4)
    onceki = {r["istek_ozeti"]: r for r in kayitlar if r.get("istek_ozeti")}
    plan = Plan(p, kok, ayar, ayar["saglayici"], sag, kayit_yolu, harcanan)

    for k in p.kurgular:
        for c in k.cekimler:
            if c.sinif != "C":
                continue
            yer = f"{k.ad}:{c.cekim}"
            durum = {"animatik": BEKLIYOR, "onay": KILITLI, "kilit": KILITLI}.get(c.durum, URETILECEK)
            sn = faturali_sure(c.sure_sn, sag.get("sureler"))
            if sn is None:
                b.append(Bulgu(HATA, yer, f"{c.sure_sn:g} sn, '{ayar['saglayici']}' en çok "
                                          f"{max(sag['sureler']):g} sn üretir; çekimi bölün"))
                continue
            kare, kare_oz = "", ""
            if c.anahtar_kare:
                kp = Path(c.anahtar_kare)
                kp = kp if kp.is_absolute() else kok / kp
                if kp.is_file():
                    kare, kare_oz = str(kp), dosya_ozeti(kp)
                elif durum == URETILECEK:
                    b.append(Bulgu(HATA, yer, f"anahtar kare yok: {c.anahtar_kare}"))
                    continue
            elif sag.get("kare_gerekli") and durum == URETILECEK:
                b.append(Bulgu(HATA, yer, f"'{ayar['saglayici']}' görüntüden video üretir; anahtar_kare gerekli"))
                continue
            elif durum == URETILECEK:
                b.append(Bulgu(UYARI, yer, "anahtar kare yok; metinden video marka tutarlılığını düşürür"))
            prompt, negatif = _prompt(p.marka, c)
            oz = istek_ozeti(ayar["saglayici"], sag, prompt, negatif, kare_oz, sn, ayar["tohum"])
            if durum == URETILECEK and oz in onceki and not yeniden:
                durum = ONBELLEK if (kok / onceki[oz]["dosya"]).exists() else KAYITTA
            plan.isler.append({
                "kurgu": k.ad, "cekim": c.cekim, "durum": durum, "prompt": prompt, "negatif": negatif,
                "kare": kare, "sure_sn": c.sure_sn, "faturali_sn": sn, "tohum": ayar["tohum"], "istek_ozeti": oz,
                "maliyet_usd": round(sn * sag.get("usd_sn", 0), 4) if durum == URETILECEK else 0.0,
                "onceki": onceki.get(oz, {}).get("dosya", ""),
            })
            if durum == KAYITTA:
                b.append(Bulgu(UYARI, yer, f"kayıtta var ama dosya bu makinede yok ({onceki[oz]['dosya']}); "
                                           "yeniden üretmek için --yeniden"))

    if plan.harcanan + plan.tahmini > ayar["butce_usd"]:
        b.append(Bulgu(HATA, "proje.uretim.butce_usd",
                       f"harcanan {plan.harcanan:.2f} $ + bu plan {plan.tahmini:.2f} $ > bütçe {ayar['butce_usd']:.2f} $"))
    return plan, b


def calistir(plan: Plan, ag=saglayici_mod.http) -> list[Bulgu]:
    b: list[Bulgu] = []
    if plan.sag["tur"] not in saglayici_mod.BAGDASTIRICILAR:
        return [Bulgu(HATA, plan.saglayici, "bağdaştırıcı yok; çalıştırılamaz")]
    harcanan = plan.harcanan
    for is_ in plan.isler:
        if is_["durum"] != URETILECEK:
            continue
        yer = f"{is_['kurgu']}:{is_['cekim']}"
        if harcanan + is_["maliyet_usd"] > plan.ayar["butce_usd"]:
            b.append(Bulgu(HATA, yer, f"bütçe doldu ({harcanan:.2f} $); durduruldu"))
            break
        hedef = plan.proje.klasor / "cikti" / "uretim" / is_["kurgu"] / f"{is_['cekim']}-{is_['istek_ozeti'][:12]}"
        cikti = None
        for deneme in range(plan.ayar["azami_deneme"]):
            tohum = plan.ayar["tohum"] + deneme
            try:
                cikti = saglayici_mod.uret({**is_, "tohum": tohum}, hedef, plan.sag, ag)
                break
            except saglayici_mod.SaglayiciHatasi as e:
                b.append(Bulgu(UYARI, yer, f"deneme {deneme + 1}: {e}"))
        if cikti is None:
            b.append(Bulgu(HATA, yer, f"{plan.ayar['azami_deneme']} denemede üretilemedi"))
            continue
        harcanan = round(harcanan + is_["maliyet_usd"], 4)
        try:
            dosya = cikti.relative_to(plan.kok).as_posix()
        except ValueError:
            dosya = cikti.as_posix()
        kayit_ekle(plan.kayit_yolu, {
            "dosya": dosya, "sinif": "C", "model": plan.saglayici,
            "tarih": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "prompt": is_["prompt"],
            "kullanildigi_yer": f"{is_['kurgu']}/{is_['cekim']}", "kaynak_ozeti": dosya_ozeti(cikti),
            "arac": "platform/uretim", "istek_ozeti": is_["istek_ozeti"], "maliyet_usd": f"{is_['maliyet_usd']:g}",
            "lisans": lisans(plan.sag), "tohum": tohum,
        })
        is_["durum"], is_["dosya"] = "üretildi", dosya
    return b


def denetle(proje_json: str | Path, kok: Path | None = None) -> list[Bulgu]:
    """Lisans kapısı (V3): onaylı ya da kilitli her C çekiminin en son kaydı ticari teslime uygun olmalı."""
    proje_json = Path(proje_json).resolve()
    kok = (kok or proje_mod.depo_koku(proje_json.parent)).resolve()
    p, b = proje_mod.yukle(proje_json, kok)
    if p is None:
        return b
    data = json.loads(proje_json.read_text(encoding="utf-8"))
    ticari = (data.get("uretim") or {}).get("ticari", True)
    kayit_yolu = kok / data["yz_kaydi"] if data.get("yz_kaydi") else p.klasor / "yz-kaydi.csv"
    saglayicilar = saglayici_mod.yukle()
    son: dict[str, dict] = {}
    for n, r in enumerate(kayit_oku(kayit_yolu), start=2):
        if r.get("model") not in saglayicilar:
            b.append(Bulgu(HATA, f"{kayit_yolu.name}:{n}", f"bilinmeyen model {r.get('model')!r}"))
            continue
        beklenen = lisans(saglayicilar[r["model"]])
        if r.get("lisans") != beklenen:
            b.append(Bulgu(HATA, f"{kayit_yolu.name}:{n}", f"lisans {r.get('lisans')!r}, '{r['model']}' için {beklenen!r}"))
        son[r.get("kullanildigi_yer", "")] = r
    for k in p.kurgular:
        for c in k.cekimler:
            if c.sinif != "C" or c.durum not in ("onay", "kilit"):
                continue
            yer = f"{k.ad}:{c.cekim}"
            r = son.get(f"{k.ad}/{c.cekim}")
            if r is None:
                b.append(Bulgu(HATA, yer, f"durum {c.durum} ama yz-kaydi'de satırı yok"))
            elif ticari and r.get("lisans") != "ticari":
                b.append(Bulgu(HATA, yer, f"çıktı '{r['model']}' ile üretildi ({r.get('lisans')}); ticari teslime giremez"))
    return b


def _rapor(bulgular) -> None:
    for x in sorted(bulgular, key=lambda x: (x.seviye != HATA, x.yer)):
        print(f"  {x}")
    hata = sum(x.seviye == HATA for x in bulgular)
    print(f"HATA: {hata} · UYARI: {len(bulgular) - hata}")


def _plan_yaz(plan: Plan) -> None:
    print(f"Sağlayıcı: {plan.saglayici} · bütçe {plan.ayar['butce_usd']:.2f} $ · harcanan {plan.harcanan:.2f} $")
    for i in plan.isler:
        sure = f"{i['sure_sn']:g} sn" + (f" ({i['faturali_sn']:g} sn faturalı)" if i["faturali_sn"] != i["sure_sn"] else "")
        print(f"  {i['kurgu']}:{i['cekim']:<6} {sure:<24} {i['durum']:<12} {i['maliyet_usd']:.2f} $  {i['istek_ozeti'][:10]}")
    if not plan.isler:
        print("  sinif=C çekim yok")
    print(f"Bu plan: {plan.tahmini:.2f} $")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="uretim.py", description="YZ üretim hattı: plan, çalıştır, denetle.")
    sub = parser.add_subparsers(dest="komut", required=True)
    for ad in ("plan", "calistir", "denetle"):
        sp = sub.add_parser(ad)
        sp.add_argument("proje")
        if ad != "denetle":
            sp.add_argument("--saglayici")
            sp.add_argument("--yeniden", action="store_true", help="kayıttaki istekleri de yeniden üret")
    args = parser.parse_args(argv)

    if args.komut == "denetle":
        b = denetle(args.proje)
        _rapor(b)
        return 1 if has_errors(b) else 0
    plan, b = plan_kur(args.proje, args.saglayici, yeniden=args.yeniden)
    if plan is not None:
        _plan_yaz(plan)
    if has_errors(b) or plan is None:
        _rapor(b)
        return 1
    if args.komut == "calistir":
        b += calistir(plan)
        for i in plan.isler:
            if i.get("dosya"):
                print(f"  üretildi: {i['dosya']}")
    _rapor(b)
    return 1 if has_errors(b) else 0


if __name__ == "__main__":
    sys.exit(main())
