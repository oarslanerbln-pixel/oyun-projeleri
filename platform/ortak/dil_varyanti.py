"""Dil varyantı: bir senaryodan aynı kurgunun başka dildeki senaryosu (TR → DE, DE → TR).

Çeviriyi thread yazar (makine çevirisi yok); bu modül çevrilecek metni çıkarır, çeviriyi geri yerleştirir, dile göre
ses ayarını kurar ve uzunluğu denetler:

    python3 platform/ortak/dil_varyanti.py tablo  tek-cizgi.json --dil de        # → tek-cizgi.ceviri-de.json (boş)
    # thread tablodaki her "ceviri": null alanını doldurur (değişmeyecek ad için kaynağı aynen yazar)
    python3 platform/ortak/dil_varyanti.py uygula tek-cizgi.json --dil de [--ses liam]   # → tek-cizgi.de.json

Siparişte `"diller": ["tr", "de"]` yazınca `uret.py` bunu kendisi yapar: tablo yoksa boş tabloyu yazıp durur,
doluysa varyantı üretir ve aynı kurgudan her dil için ayrı video çıkarır (`cikti-de/`).

Uzunluk: Almanca metin Türkçeden ~%20–35 uzundur.
- Ortak sahne dilinde (`"dil": "sahne"`) sahne süresi seslendirmeden çıkar, uzayan ses sahneyi kendiliğinden uzatır;
  ekrandaki yazının sınırı (dil.TIPLER) burada ölçülür, aşan alan HATA olur (kısaltılarak çevrilmeli).
- Saniyeli şablonlarda (`seslendirme.satirlar[].t`) uzayan satır sonraki satıra ya da videonun sonuna taşarsa bütün
  zaman çizelgesi aynı oranla uzatılır (`esnet`, en çok x1.5); rapor oranı yazar.

`okunus` alanları dile özgüdür: çevrilmediyse varyantta silinir; adların okunuşu `platform/ses/telaffuz/<dil>.tsv`'den
gelir. Yalnız Python standart kitaplığı.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
SAHNE_DIL = BURADA.parent / "sablonlar" / "sahne" / "dil.py"

# Çevrilmeyen anahtarlar: kimlik, yol, renk, ayar. Değeri metin olsa da ekranda görünmez ya da dile bağlı değildir.
ATLA = {"kimlik", "id", "tip", "stil", "stiller", "dil", "format", "formatlar", "gorsel", "gorseller", "resim", "logo",
        "dosya", "yol", "url", "renk", "renkler", "palet", "font", "yazi_tipi", "agirlik", "ses", "saglayici", "model",
        "muzik", "enstruman", "efekt", "efektler", "gecis", "kamera", "hiza", "konum", "kaplama", "not", "notlar",
        "voice_settings", "telaffuz", "okunus", "kaynak_dil", "sablon", "tur", "enerji", "mod", "duzen", "yon", "sekil",
        "glb", "kalip", "desen", "kapak", "an", "fps", "tohum", "zemin", "arka", "isaret"}
SABIT_KOK = {"marka"}  # marka adı, adres: tabloya girer ama "sabit" işaretlidir (çoğu zaman aynen kalır)
DILLER = {"tr": "Türkçe", "de": "Almanca", "en": "İngilizce"}
HIZ = {"tr": 2.6, "de": 2.4, "en": 2.8}  # sözcük/sn; Almanca sözcükleri uzun, daha yavaş okunur
UZUN_ORAN = 1.35  # hedef metin kaynaktan bu kadar uzunsa uyarı


def _sahne_dil():
    import importlib.util
    sp = importlib.util.spec_from_file_location("sahne_dil", SAHNE_DIL)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _metin_mi(v: str) -> bool:
    if not re.search(r"[^\W\d_]", v):  # harf yok: "1.200", "9:16", "3 ay" değil
        return bool(re.search(r"\d", v)) and bool(re.search(r"[^\d\s.,:%₺€$x×+\-]", v))
    if re.fullmatch(r"#[0-9a-fA-F]{3,8}", v):
        return False
    if re.search(r"\.(json|png|jpe?g|webp|svg|glb|mp3|mp4|wav|ttf|otf|tsv|csv)$", v, re.I) or "://" in v:
        return False
    return not (("/" in v or "\\" in v) and " " not in v)


def alanlar(s: dict) -> list[dict]:
    """Senaryodaki çevrilecek metinler: [{"yol": "sahneler/0/metin", "kaynak": "...", "azami": 28, "sabit": False}]"""
    sahne = s.get("dil") == "sahne"
    sinir = _sinirlar(s) if sahne else {}
    out: list[dict] = []

    def gez(v, yol: list):
        if isinstance(v, dict):
            for k, x in v.items():
                if k in ATLA or k.startswith("_"):
                    continue
                gez(x, yol + [k])
        elif isinstance(v, list):
            for i, x in enumerate(v):
                gez(x, yol + [i])
        elif isinstance(v, str) and v.strip() and _metin_mi(v):
            y = "/".join(map(str, yol))
            kayit = {"yol": y, "kaynak": v, "azami": sinir.get(y)}
            if yol and yol[0] in SABIT_KOK:
                kayit["sabit"] = True
            out.append(kayit)

    gez(s, [])
    return out


def _sinirlar(s: dict) -> dict[str, int]:
    """sahne dilinde ekrandaki alanların en çok karakteri (dil.TIPLER)"""
    try:
        d = _sahne_dil()
    except Exception:  # noqa: BLE001 - sınırlar yardımcıdır
        return {}
    out = {}
    for i, sh in enumerate(s.get("sahneler") or []):
        tip = d.TIPLER.get(sh.get("tip"), {}).get("alan", {})
        for k, (_, azami) in tip.items():
            if azami:
                out[f"sahneler/{i}/{k}"] = azami
        for j, _ in enumerate(sh.get("maddeler") or []):
            out[f"sahneler/{i}/maddeler/{j}"] = d.MADDE[2]
    return out


def tablo_yolu(senaryo: Path, dil: str) -> Path:
    return senaryo.with_name(f"{senaryo.stem}.ceviri-{dil}.json")


def varyant_yolu(senaryo: Path, dil: str) -> Path:
    return senaryo.with_name(f"{senaryo.stem}.{dil}.json")


def kaynak_dili(s: dict, varsayilan: str = "tr") -> str:
    sb = s.get("seslendirme") if isinstance(s.get("seslendirme"), dict) else {}
    d = sb.get("dil") or s.get("dil")
    return d if d in DILLER else varsayilan


def tablo(senaryo: Path, dil: str, kaynak: str | None = None) -> Path:
    """Boş çeviri tablosu yazar; varsa eski çevirileri (aynı yol + aynı kaynak metin) korur."""
    s = json.loads(senaryo.read_text(encoding="utf-8"))
    hedef = tablo_yolu(senaryo, dil)
    eski = {}
    if hedef.exists():
        eski = {(a["yol"], a["kaynak"]): a.get("ceviri") for a in json.loads(hedef.read_text(encoding="utf-8"))["alanlar"]}
    a = alanlar(s)
    for x in a:
        x["ceviri"] = eski.get((x["yol"], x["kaynak"]))
        if x.get("azami") is None:
            x.pop("azami")
    t = {"senaryo": senaryo.name, "kaynak_dil": kaynak or kaynak_dili(s), "hedef_dil": dil,
         "not": "Her 'ceviri' alanını doldurun; aynen kalacak adlara kaynağı yazın. 'azami' ekrandaki karakter sınırı.",
         "alanlar": a}
    hedef.write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return hedef


def eksikler(t: dict) -> list[str]:
    return [a["yol"] for a in t["alanlar"] if not isinstance(a.get("ceviri"), str) or not a["ceviri"].strip()]


def _koy(s: dict, yol: str, deger: str) -> bool:
    parcalar = [int(p) if p.isdigit() else p for p in yol.split("/")]
    hedef = s
    try:
        for p in parcalar[:-1]:
            hedef = hedef[p]
        if not isinstance(hedef[parcalar[-1]], str):
            return False
        hedef[parcalar[-1]] = deger
        return True
    except (KeyError, IndexError, TypeError):
        return False


def _okunuslari_temizle(s: dict, cevrilen: set[str]) -> int:
    """çevrilmemiş `okunus` alanlarını siler (kaynak dilin okunuşu hedef dilde yanlış okunur)"""
    n = 0

    def gez(v, yol: list):
        nonlocal n
        if isinstance(v, dict):
            if "okunus" in v and "/".join(map(str, yol + ["okunus"])) not in cevrilen:
                del v["okunus"]
                n += 1
            for k, x in v.items():
                gez(x, yol + [k])
        elif isinstance(v, list):
            for i, x in enumerate(v):
                gez(x, yol + [i])

    gez(s, [])
    return n


def _sure(metin: str, dil: str) -> float:
    return len(re.findall(r"\w+", metin or "")) / HIZ.get(dil, 2.6) + 0.2 if metin else 0.0


ZAMAN_ANAHTARI = re.compile(r"^(t|bas|son|sure|baslangic|bitis)$|_(t|sure)$")
AZAMI_ESNEME = 1.5


def esnet(s: dict, dil: str, pay: float = 0.25) -> float:
    """Saniyeli şablon: hedef dilde uzayan satır sonrakine (ya da videonun sonuna) taşıyorsa bütün zaman çizelgesini
    aynı oranla uzatır (`t`, `bas`, `sure`, `*_t`, `*_sure`). Tek oran, satır içi ve sahne içi ilişkileri korur;
    anahtarın mutlak mı göreli mi olduğunu bilmek gerekmez. Dönüş: oran (1.0 = değişmedi)."""
    sb = s.get("seslendirme") if isinstance(s.get("seslendirme"), dict) else None
    satirlar = sorted((x for x in (sb or {}).get("satirlar") or [] if isinstance(x.get("t"), (int, float))),
                      key=lambda x: x["t"])
    if not satirlar:
        return 1.0
    sonlar = [b["t"] for b in satirlar[1:]] + ([s["sure"]] if isinstance(s.get("sure"), (int, float)) else [])
    oran = 1.0
    for a, son in zip(satirlar, sonlar):
        bosluk = son - a["t"]
        if bosluk > 0:
            oran = max(oran, (_sure(a.get("okunus") or a.get("metin", ""), dil) + pay) / bosluk)
    oran = round(min(oran, AZAMI_ESNEME), 3)
    if oran <= 1.0:
        return 1.0

    def gez(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(x, (int, float)) and not isinstance(x, bool) and ZAMAN_ANAHTARI.search(k):
                    v[k] = round(x * oran, 3)
                else:
                    gez(x)
        elif isinstance(v, list):
            for x in v:
                gez(x)

    gez(s)
    return oran


def uygula(senaryo: Path, dil: str, ses: str | None = None, tablo_dosyasi: Path | None = None,
           hedef: Path | None = None) -> dict:
    """Tablodaki çevirileri yerleştirir → `<ad>.<dil>.json`. Dönüş: rapor {"dosya", "hatalar", "uyarilar", ...}."""
    s = json.loads(senaryo.read_text(encoding="utf-8"))
    tp = tablo_dosyasi or tablo_yolu(senaryo, dil)
    if not tp.exists():
        raise FileNotFoundError(f"çeviri tablosu yok: {tp} (önce `dil_varyanti.py tablo`)")
    t = json.loads(tp.read_text(encoding="utf-8"))
    eksik = eksikler(t)
    if eksik:
        raise ValueError(f"{tp.name}: {len(eksik)} alan çevrilmedi ({', '.join(eksik[:4])}"
                         + (" …" if len(eksik) > 4 else "") + ")")
    kaynak = t.get("kaynak_dil") or kaynak_dili(s)
    v = copy.deepcopy(s)
    hatalar, uyarilar, cevrilen = [], [], set()
    guncel = {a["yol"]: a["kaynak"] for a in alanlar(s)}
    for a in t["alanlar"]:
        if guncel.get(a["yol"]) != a["kaynak"]:
            hatalar.append(f"{a['yol']}: senaryodaki metin tablodan sonra değişmiş; tabloyu yenileyin (`tablo`)")
            continue
        if not _koy(v, a["yol"], a["ceviri"].strip()):
            hatalar.append(f"{a['yol']}: senaryoda yok")
            continue
        cevrilen.add(a["yol"])
        azami = a.get("azami")
        if azami and len(a["ceviri"].strip()) > azami:
            hatalar.append(f"{a['yol']}: {len(a['ceviri'].strip())} karakter, en çok {azami} (kısaltın): {a['ceviri']!r}")
    yeni = [y for y in guncel if y not in {a["yol"] for a in t["alanlar"]}]
    if yeni:
        hatalar.append(f"tabloda olmayan yeni metin: {', '.join(yeni[:4])} (tabloyu yenileyin)")
    silinen = _okunuslari_temizle(v, cevrilen)
    if silinen:
        uyarilar.append(f"{silinen} 'okunus' alanı kaynak dile özgü olduğu için silindi (telaffuz/{dil}.tsv kullanılır)")
    sb = v.get("seslendirme") if isinstance(v.get("seslendirme"), dict) else {}
    sb["dil"] = dil
    if ses:
        sb["ses"] = ses
    v["seslendirme"] = sb
    v["dil_varyanti"] = {"kaynak": senaryo.name, "kaynak_dil": kaynak, "dil": dil}
    if v.get("kimlik"):
        v["kimlik"] = f"{s['kimlik']}-{dil}"
    # uzunluk: ekran metni ve seslendirme
    k_metin = sum(len(a["kaynak"]) for a in t["alanlar"])
    h_metin = sum(len(a["ceviri"]) for a in t["alanlar"])
    oran = round(h_metin / k_metin, 2) if k_metin else 1.0
    if oran > UZUN_ORAN:
        uyarilar.append(f"çeviri kaynaktan %{(oran - 1) * 100:.0f} uzun; ekrana sığmayan yazı kalite kapısında görünür")
    k_ses = sum(_sure(x, kaynak) for x in _seslendirmeler(s))
    h_ses = sum(_sure(x, dil) for x in _seslendirmeler(v))
    esneme = 1.0 if v.get("dil") == "sahne" else esnet(v, dil)
    if esneme > 1.0:
        uyarilar.append(f"uzayan seslendirme için zaman çizelgesi x{esneme:g} uzatıldı"
                        + (" (en çok; yine sığmayan satırı kısaltın)" if esneme >= AZAMI_ESNEME else ""))
    hedef = hedef or varyant_yolu(senaryo, dil)
    if not hatalar:
        hedef.write_text(json.dumps(v, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"dosya": str(hedef) if not hatalar else None, "kaynak_dil": kaynak, "dil": dil, "metin_orani": oran,
            "tahmini_ses_sn": {kaynak: round(k_ses, 1), dil: round(h_ses, 1)}, "esneme": esneme,
            "hatalar": hatalar, "uyarilar": uyarilar}


def _seslendirmeler(s: dict) -> list[str]:
    if s.get("dil") == "sahne":
        return [sh.get("okunus") or sh["seslendirme"] for sh in s.get("sahneler") or [] if sh.get("seslendirme")]
    sb = s.get("seslendirme") if isinstance(s.get("seslendirme"), dict) else {}
    return [x.get("okunus") or x.get("metin", "") for x in sb.get("satirlar") or []]


def hazirla(senaryo: Path, dil: str, ses: str | None = None, kaynak: str | None = None) -> tuple[Path | None, str]:
    """uret.py için: tablo yoksa boş tabloyu yazar (None, mesaj); doluysa ve varyant eskiyse yeniden üretir."""
    tp, vp = tablo_yolu(senaryo, dil), varyant_yolu(senaryo, dil)
    if not tp.exists():
        tablo(senaryo, dil, kaynak)
        return None, f"{tp.name} yazıldı: {DILLER.get(dil, dil)} çevirileri doldurulunca sipariş yeniden çalıştırılır"
    t = json.loads(tp.read_text(encoding="utf-8"))
    if eksikler(t):
        return None, f"{tp.name}: {len(eksikler(t))} alan çevrilmedi"
    guncel = vp.exists() and vp.stat().st_mtime >= max(tp.stat().st_mtime, senaryo.stat().st_mtime)
    if guncel and (not ses or (json.loads(vp.read_text(encoding="utf-8")).get("seslendirme") or {}).get("ses") == ses):
        return vp, "güncel"
    r = uygula(senaryo, dil, ses)
    if r["hatalar"]:
        return None, f"{senaryo.name} → {dil}: " + "; ".join(r["hatalar"])
    return vp, "; ".join(r["uyarilar"]) or "üretildi"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    a1 = alt.add_parser("tablo", help="çevrilecek metinleri tabloya çıkar")
    a1.add_argument("senaryo")
    a1.add_argument("--dil", required=True)
    a1.add_argument("--kaynak-dil")
    a2 = alt.add_parser("uygula", help="çeviriyi yerleştir, <ad>.<dil>.json yaz")
    a2.add_argument("senaryo")
    a2.add_argument("--dil", required=True)
    a2.add_argument("--ses", help="hedef dilin sesi (ör. liam)")
    a2.add_argument("--tablo")
    a2.add_argument("-o", "--cikti")
    a = ap.parse_args(argv)
    yol = Path(a.senaryo)
    if a.komut == "tablo":
        p = tablo(yol, a.dil, a.kaynak_dil)
        t = json.loads(p.read_text(encoding="utf-8"))
        print(f"{p} · {len(t['alanlar'])} alan, {len(eksikler(t))} çevrilecek")
        return 0
    try:
        r = uygula(yol, a.dil, a.ses, Path(a.tablo) if a.tablo else None, Path(a.cikti) if a.cikti else None)
    except (FileNotFoundError, ValueError) as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    for h in r["hatalar"]:
        print(f"HATA {h}", file=sys.stderr)
    for u in r["uyarilar"]:
        print(f"UYARI {u}")
    if r["dosya"]:
        sn = r["tahmini_ses_sn"]
        print(f"{r['dosya']} · metin oranı {r['metin_orani']} · tahmini ses " + ", ".join(f"{k} {v} sn" for k, v in sn.items()))
    return 1 if r["hatalar"] else 0


if __name__ == "__main__":
    sys.exit(main())
