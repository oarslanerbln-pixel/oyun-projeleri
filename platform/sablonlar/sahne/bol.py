"""Senaryodan sahne bölme: düz metin senaryo → ortak sahne dilinde (`"dil": "sahne"`) sahne.json taslağı.

Sen yalnız metni yazarsın; her cümle (ya da blok) bir sahne olur, tipini metnin biçimi seçer. Okunan satır
(`seslendirme`) metnin kendisidir, ekran yazısı ondan kısaltılır (az yazı kuralı). Taslak önizlemeye hazırdır;
beğenmediğin ekran yazısını JSON'da düzeltirsin.

    python3 platform/sablonlar/sahne/bol.py metin.txt [-o sahne.json] [--kimlik ad] [--format 9:16] [--marka "Ad"]

| Metinde | Sahne |
| --- | --- |
| ilk satır / `# Başlık` | `baslik` |
| `- madde` / `1. madde` satırları (öncesinde `Başlık:` satırı olabilir) | `liste` |
| `Ocak: 120` gibi en az iki "etiket: sayı" satırı (`Başlık:` + `tur: pasta` isteğe bağlı) | `grafik` |
| `> söz — kaynak`, tırnak içinde cümle ya da `*vurgulu*` öbek | `alinti` |
| sayı içeren cümle (`%40`, `37 kat`, `1.200 kişi`, `yüzde 40`) | `sayi` |
| `X yerine Y`, `X değil Y`, `statt X Y`, `X vs Y` | `karsilastirma` |
| son paragraf çağrı sözcüğü içeriyorsa (takip et, abone, kaydet, link, folge, jetzt...) | `cta` |
| `---` satırı | `gecis` |
| diğer cümleler | `baslik` (ekran yazısı cümlenin ilk öbeği) |

24 sahneyi aşan metin `-1`, `-2` ... diye birden çok senaryoya bölünür (uzun videoda `kurgu.json` sahnesi olur).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
import dil  # noqa: E402

CTA = re.compile(r"\b(takip|abone|kaydet|paylaş|link|bağlantı|rezervasyon|sipariş ver|hemen|ara\b|yorum|dm|"
                 r"folg|abonn|jetzt|besuch|reserv|bestell|link in bio|teile|speicher|kommentier)", re.I)
MADDE = re.compile(r"^\s*(?:[-*•–]|\d+[.)])\s+(.+)$")
VERI = re.compile(r"^\s*([^:;=]{1,%d})\s*[:=]\s*(-?[%%]?\s*\d[\d.,]*\s*%%?)\s*([^\d\s].{0,6})?$" % dil.ETIKET)
CUMLE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÇĞİÖŞÜÄÖÜ0-9\"“'«])")
KARSI = [re.compile(p, re.I) for p in (r"^(.+?)\s+yerine\s+(.+?)[.!?]*$", r"^(.+?),?\s+değil\s*,?\s+(.+?)[.!?]*$",
                                       r"^statt\s+(.+?),\s*(.+?)[.!?]*$", r"^(.+?)\s+(?:vs\.?|versus|ya da|oder)\s+(.+?)[.!?]*$")]
# sayı: (%|yüzde)? rakam (ayraçlı) (x|kat|%|birim)?
SAYI = re.compile(r"(?:(%|yüzde\s+)\s*)?(\d[\d.,]*)\s*(%|x\b|kat\b|katı\b|fach\b|prozent\b|mal\b|₺|€|\$|tl\b)?", re.I)
BAGLAC = {"ve", "ile", "veya", "ya", "da", "de", "bir", "için", "ama", "and", "und", "oder", "mit", "für", "der", "die", "das", "ein", "eine"}
ON_EK = re.compile(r"^(?:ve|ama|fakat|çünkü|yani|peki|işte|und|aber|denn|also)\s+", re.I)


def kisalt(s: str, azami: int) -> str:
    """Ekran yazısı: önce ilk öbek (virgül, iki nokta, tire), sığmazsa sözcük sınırında kesilir; sonda noktalama yok."""
    s = ON_EK.sub("", re.sub(r"\s+", " ", s.replace("*", "")).strip())
    s = s[:1].upper() + s[1:]
    for parca in re.split(r"\s*[,;:–—]\s+|\s+-\s+", s):
        if 0 < len(parca.rstrip(".!?…")) <= azami and len(parca.split()) >= 2:
            return parca.rstrip(".!?…")
    s = s.rstrip(".!?…")
    if len(s) <= azami:
        return s
    out = ""
    for w in s.split():
        if len((out + " " + w).strip()) > azami:
            break
        out = (out + " " + w).strip()
    return out.rstrip(",;:") or s[:azami]


def ikiye(s: str, a1: int, a2: int) -> tuple[str, str]:
    """Uzun başlık: ana yazı (≤ a1) + alt satır (≤ a2), sözcük sınırında ve olabildiğince dengeli bölünür."""
    s = ON_EK.sub("", re.sub(r"\s+", " ", s.replace("*", "")).strip()).rstrip(".!?…")
    s = s[:1].upper() + s[1:]
    if len(s) <= a1:
        return s, ""
    w = s.split()
    adaylar = [(" ".join(w[:k]), " ".join(w[k:])) for k in range(1, len(w))]
    uygun = [x for x in adaylar if len(x[0]) <= a1 and len(x[1]) <= a2]
    if uygun:
        bas, alt = min(uygun, key=lambda x: (x[0].split()[-1].lower() in BAGLAC, abs(len(x[0]) - len(x[1])) - (8 if x[0].endswith(",") else 0)))
        return bas.rstrip(",;:"), alt
    return kisalt(s, a1), ""


def _baslik(c: str, tip: str = "baslik") -> dict:
    a1, a2 = (28, 40) if tip == "baslik" else (22, 32)
    bas, alt = ikiye(c, a1, a2)
    sh = {"tip": tip, "metin": bas}
    if alt:
        sh["alt"] = alt
    return sh


def _sayi(cumle: str) -> dict | None:
    """cümledeki son anlamlı sayı (vurucu rakam çoğu zaman sonda: "... bir yılda 37 kat")"""
    for m in reversed(list(SAYI.finditer(cumle))):
        on, ham, son = m.group(1), m.group(2).rstrip(".,"), (m.group(3) or "").lower()
        if not re.search(r"\d", ham) or (re.fullmatch(r"(19|20)\d\d", ham) and not (on or son)):
            continue  # yıllar sayı sahnesi değil
        if on:
            deger = f"%{ham}"
        elif son in ("%", "prozent"):  # yazıldığı gibi: Almanca 40 %, Türkçe %40
            deger = f"{ham}%"
        elif son in ("x", "kat", "katı", "fach", "mal"):
            deger = f"{ham}x"
        elif son in ("₺", "€", "$", "tl"):
            deger = f"{ham}{'₺' if son == 'tl' else son}"
        else:
            deger = ham
        if len(deger) > 8:
            continue
        bas = max([0] + [k.end() for k in re.finditer(r"[,;:]\s+", cumle[:m.start()])])  # sayının geçtiği öbek
        bit = re.search(r"[,;:]\s+", cumle[m.end():])
        bit = m.end() + bit.start() if bit else len(cumle)
        kalan = re.sub(r"\s+", " ", cumle[bas:m.start()] + " " + cumle[m.end():bit]).strip()
        sh = {"tip": "sayi", "deger": deger}
        etiket = kisalt(kalan, 28)
        if etiket:
            sh["etiket"] = etiket
        return sh
    return None


def _cumle_sahnesi(c: str) -> dict:
    c = c.strip()
    m = re.match(r'^[“"«](.+?)[”"»]\s*(?:[—–-]\s*(.+))?$', c) or re.match(r"^>\s*(.+?)(?:\s+[—–-]\s+(.+))?$", c)
    if m and len(m.group(1)) <= 90:
        sh = {"tip": "alinti", "metin": m.group(1).strip()}
        if m.group(2):
            sh["kaynak"] = kisalt(m.group(2), 30)
        return sh
    v = re.search(r"\*([^*]{3,90})\*", c)
    if v:
        return {"tip": "alinti", "metin": v.group(1).strip()}
    for k in KARSI:
        m = k.match(c)
        if m:
            sol, sag = (" ".join(x.split()[-2:]) for x in (m.group(1), m.group(2)))
            sag = " ".join(m.group(2).split()[:2]).rstrip(".,!?")
            if len(sol) <= 16 and len(sag) <= 16:
                return {"tip": "karsilastirma", "sol": kisalt(sol, 16), "sag": kisalt(sag, 16)}
    s = _sayi(c)
    if s:
        return s
    return _baslik(c)


def _okunus(c: str) -> str:
    """seslendirme: işaretler atılır (> , *vurgu*, tırnak)"""
    return re.sub(r"^\s*>\s*", "", c.replace("*", "")).strip()


def bol(metin: str) -> list[dict]:
    """Metni sahnelere böler (sahne sözlükleri, seslendirmeli)."""
    paragraflar = [p.strip("\n") for p in re.split(r"\n\s*\n", metin.replace("\r", "")) if p.strip()]
    out: list[dict] = []
    for pi, p in enumerate(paragraflar):
        satirlar = [x.rstrip() for x in p.split("\n") if x.strip()]
        son_par = pi == len(paragraflar) - 1
        i = 0
        while i < len(satirlar):
            x = satirlar[i]
            if re.fullmatch(r"\s*-{3,}\s*", x):
                out.append({"tip": "gecis"}); i += 1; continue
            if x.lstrip().startswith("#"):
                b = x.lstrip("# ").strip()
                out.append({**_baslik(b), "seslendirme": b}); i += 1; continue
            baslik = None
            if x.rstrip().endswith(":") and i + 1 < len(satirlar) and (MADDE.match(satirlar[i + 1]) or VERI.match(satirlar[i + 1])
                                                                       or satirlar[i + 1].lower().startswith("tur:")):
                baslik = x.rstrip(": ").strip(); i += 1
            tur = None
            if i < len(satirlar) and re.match(r"^\s*tur\s*:\s*(cubuk|cizgi|pasta)\s*$", satirlar[i], re.I):
                tur = satirlar[i].split(":")[1].strip().lower(); i += 1
            # "etiket: sayı" bloğu → grafik
            j = i
            while j < len(satirlar) and VERI.match(satirlar[j]):
                j += 1
            if j - i >= 2:
                eslesen = [VERI.match(y) for y in satirlar[i:j]]
                veri = [[m.group(1).strip(), dil.sayi_oku(m.group(2))] for m in eslesen]
                birim = next((m.group(3).strip() for m in eslesen if m.group(3)), "")
                if any("%" in m.group(2) for m in eslesen):
                    birim = "%{}"
                tur = tur or ("cizgi" if len(veri) > 8 else "cubuk")
                az, cok = dil.GRAFIK[tur]
                veri = veri[:cok]
                sh = {"tip": "grafik", "tur": tur, "veri": veri}
                if baslik:
                    sh["baslik"] = kisalt(baslik, 28)
                if birim and len(birim) <= 8:
                    sh["birim"] = birim if "{}" in birim else ("{} " + birim if birim[0].isalpha() else birim)
                enb = max(veri, key=lambda r: r[1])
                sh["seslendirme"] = (baslik + ". " if baslik else "") + f"En yüksek: {enb[0]}, {dil.bicim(enb[1], sh.get('birim', ''))}."
                out.append(sh); i = j; continue
            # madde listesi → liste
            j = i
            while j < len(satirlar) and MADDE.match(satirlar[j]):
                j += 1
            if j - i >= 2:
                maddeler = [MADDE.match(y).group(1).strip() for y in satirlar[i:j]]
                for k in range(0, len(maddeler), dil.MADDE[1]):  # 5'ten uzun liste ikiye bölünür
                    parca = maddeler[k:k + dil.MADDE[1]]
                    if len(parca) < dil.MADDE[0]:
                        out[-1]["maddeler"].append(kisalt(parca[0], dil.MADDE[2])) if out and out[-1]["tip"] == "liste" and len(out[-1]["maddeler"]) < dil.MADDE[1] else out.append({"tip": "baslik", "metin": kisalt(parca[0], 28), "seslendirme": parca[0]})
                        continue
                    sh = {"tip": "liste", "maddeler": [kisalt(m, dil.MADDE[2]) for m in parca]}
                    if baslik:
                        sh["baslik"] = kisalt(baslik, 28)
                    sh["seslendirme"] = ((baslik + ": ") if baslik and not k else "") + ", ".join(m.rstrip(".") for m in parca) + "."
                    out.append(sh)
                i = j; continue
            if baslik:  # iki noktalı satırın ardından liste gelmedi: o satır düz cümle
                i -= 2 if tur else 1
            # düz metin: cümle cümle
            metin_ = " ".join(satirlar[i:i + 1])
            cumleler = [c for c in CUMLE.split(metin_) if c.strip()]
            for ci, c in enumerate(cumleler):
                son = son_par and i == len(satirlar) - 1 and ci == len(cumleler) - 1
                if son and CTA.search(c):
                    sh = _baslik(c, "cta")
                elif not out:
                    sh = _baslik(c)
                else:
                    sh = _cumle_sahnesi(c)
                sh["seslendirme"] = _okunus(c)
                out.append(sh)
            i += 1
    for sh in out:  # ekran yazısında Türkçe büyük harf yerine düzgün yazım; boş yazı kalmasın
        for k in ("metin", "etiket", "sol", "sag"):
            if k in sh and not sh[k]:
                sh[k] = "…"
    return out


def senaryo(sahneler: list[dict], kimlik: str, fmt: str | None, marka: str | None) -> dict:
    s = {"dil": "sahne", "kimlik": kimlik}
    if fmt:
        s["format"] = fmt
    if marka:
        s["marka"] = {"ad": marka}
    s["sahneler"] = sahneler
    return s


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("metin", help="düz metin (.txt/.md); - = stdin")
    ap.add_argument("-o", "--cikti", help="sahne.json yolu (varsayılan metnin yanında <ad>.sahne.json)")
    ap.add_argument("--kimlik"); ap.add_argument("--format"); ap.add_argument("--marka")
    a = ap.parse_args(argv)
    metin = sys.stdin.read() if a.metin == "-" else Path(a.metin).read_text(encoding="utf-8")
    kok = Path(a.metin).stem if a.metin != "-" else "senaryo"
    hedef = Path(a.cikti) if a.cikti else (Path(a.metin).parent if a.metin != "-" else Path(".")) / f"{kok}.sahne.json"
    kimlik = a.kimlik or re.sub(r"[^a-z0-9]+", "-", kok.lower()).strip("-") or "senaryo"
    shs = bol(metin)
    if not shs:
        print("HATA: metin boş", file=sys.stderr); return 1
    parcalar = [shs[k:k + 24] for k in range(0, len(shs), 24)]
    kod = 0
    for n, parca in enumerate(parcalar):
        yol = hedef if len(parcalar) == 1 else hedef.with_name(hedef.name.replace(".json", f"-{n + 1}.json"))
        s = senaryo(parca, kimlik if len(parcalar) == 1 else f"{kimlik}-{n + 1}", a.format, a.marka)
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        s["_klasor"] = str(yol.resolve().parent)
        hatalar = dil.denetle(s)
        z = dil.zamanla(s)
        print(f"{yol} · {len(parca)} sahne · ~{z['sure']:.0f} sn")
        for k, sh in enumerate(parca):
            ekran = sh.get("metin") or sh.get("deger") or sh.get("baslik") or " / ".join(sh.get("maddeler") or []) or \
                f"{sh.get('sol', '')} → {sh.get('sag', '')}"
            print(f"  {k + 1:2d}. {sh['tip']:<13} {ekran}")
        for h in hatalar:
            print(f"  UYARI: {h}"); kod = 1
    return kod


if __name__ == "__main__":
    sys.exit(main())
