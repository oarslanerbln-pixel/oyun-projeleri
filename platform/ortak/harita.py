"""Harita ve rota: herhangi bir ülke/şehir, animasyonlu rota çizgisi, durak adları, mesafe.

Al-Andalus sunumu için yazılan harita kodunun (PF/al-andalus/kaynak/harita.py) genel hali. Stil yok: geometri
(kamera, kara, rota yolu, kırpma, mesafe) ve yer adı arama. Boyamayı çağıran yapar (sahne dilinde `harita` tipi:
her kaplama kendi paletiyle çizer).

    python3 platform/ortak/harita.py bul Sevilla Kurtuba İstanbul     # konum (boylam, enlem) ve ülke
    python3 platform/ortak/harita.py mesafe Málaga Ronda Sevilla       # duraklar arası kuş uçuşu km
    python3 platform/ortak/harita.py veri-yenile                       # Natural Earth verisini yeniden indirir

Veri: `veri/dunya-50m.json.gz` (Natural Earth 1:50m, kamu malı): 242 ülke (Türkçe ve Almanca adlarıyla), 7.342
şehir. Şehir adları İngilizce; yaygın Türkçe/Almanca adlar (Kurtuba, München, Viyana...) eşanlam tablosunda.
Listede olmayan yer için durakta `"konum": [boylam, enlem]` verilir.
"""

from __future__ import annotations

import gzip
import json
import math
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

VERI = Path(__file__).resolve().parent / "veri" / "dunya-50m.json.gz"
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"

# yaygın Türkçe / Almanca / yerel adlar -> Natural Earth adı
ES_AD = {
    "istanbul": "Istanbul", "kurtuba": "Cordoba", "cordoba": "Cordoba", "sevilla": "Seville", "isbiliye": "Seville",
    "girnata": "Granada", "lizbon": "Lisbon", "lissabon": "Lisbon", "lisboa": "Lisbon", "munih": "Munich",
    "munchen": "Munich", "koln": "Cologne", "viyana": "Vienna", "wien": "Vienna", "roma": "Rome", "rom": "Rome",
    "atina": "Athens", "athen": "Athens", "kahire": "Cairo", "kairo": "Cairo", "mekke": "Mecca", "mekka": "Mecca",
    "medine": "Medina", "prag": "Prague", "praha": "Prague", "varsova": "Warsaw", "warschau": "Warsaw",
    "bruksel": "Brussels", "brussel": "Brussels", "londra": "London", "moskova": "Moscow", "moskau": "Moscow",
    "venedik": "Venice", "venedig": "Venice", "floransa": "Florence", "florenz": "Florence", "napoli": "Naples",
    "neapel": "Naples", "kopenhag": "Copenhagen", "kopenhagen": "Copenhagen", "bukres": "Bucharest",
    "bukarest": "Bucharest", "belgrad": "Belgrade", "sofya": "Sofia", "tahran": "Tehran", "teheran": "Tehran",
    "bagdat": "Baghdad", "bagdad": "Baghdad", "sam": "Damascus", "damaskus": "Damascus", "kudus": "Jerusalem",
    "halep": "Aleppo", "tiflis": "Tbilisi", "baku": "Baku", "cenevre": "Geneva", "genf": "Geneva",
    "zurih": "Zurich", "nurnberg": "Nuremberg", "milano": "Milan", "mailand": "Milan", "selanik": "Thessaloniki",
    "uskup": "Skopje", "saraybosna": "Sarajevo", "budapeste": "Budapest", "lahey": "The Hague",
    "den haag": "The Hague", "fes": "Fez", "fas": "Fez", "marakes": "Marrakesh", "marrakesch": "Marrakesh",
    "tanca": "Tangier", "tanger": "Tangier", "tunus": "Tunis", "cezayir": "Algiers", "algier": "Algiers",
}


class HaritaHatasi(KeyError):
    def __str__(self):
        return self.args[0] if self.args else ""


def _anahtar(s: str) -> str:
    s = s.replace("ı", "i").replace("İ", "I")
    s = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


@lru_cache(maxsize=1)
def veri() -> dict:
    v = json.loads(gzip.open(VERI, "rt", encoding="utf-8").read())
    for u in v["ulkeler"]:  # görünür alan seçimi için sınır kutusu
        xs = [p[0] for h in u["h"] for p in h]
        ys = [p[1] for h in u["h"] for p in h]
        u["kutu"] = (min(xs), min(ys), max(xs), max(ys)) if xs else (0, 0, 0, 0)
        # ana kara: en büyük halka (İspanya'da Kanarya, Fransa'da Guyana kadrajı büyütmesin)
        ana = max(u["h"], key=lambda h: abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(h, h[1:] + h[:1])))) if u["h"] else []
        u["ana_kutu"] = (min(p[0] for p in ana), min(p[1] for p in ana), max(p[0] for p in ana), max(p[1] for p in ana)) if ana else u["kutu"]
    return v


@lru_cache(maxsize=1)
def _sehir_dizini() -> dict[str, list]:
    d: dict[str, list] = {}
    for s in veri()["sehirler"]:
        for ad in {_anahtar(s[0]), _anahtar(s[1])}:
            d.setdefault(ad, []).append(s)
    return d


def adaylar(ad: str) -> list:
    """adı tutan şehirler, kalabalıktan aza; 'Ad, ÜLKE' (ISO3) ile ülke seçilir"""
    ulke = None
    if "," in ad:
        ad, ulke = (x.strip() for x in ad.rsplit(",", 1))
    k = _anahtar(ad)
    out = _sehir_dizini().get(k) or _sehir_dizini().get(_anahtar(ES_AD.get(k, "")), [])
    if ulke:
        out = [s for s in out if s[2] == ulke.upper()]
    if not out:
        yakin = sorted({s[0] for a, ss in _sehir_dizini().items() if a[:3] == k[:3] for s in ss})[:6]
        raise HaritaHatasi(f"şehir bulunamadı: {ad}" + (f" (benzer: {', '.join(yakin)})" if yakin else "")
                           + '; durağa "konum": [boylam, enlem] yazın')
    return sorted(out, key=lambda x: -x[5])


def sehir(ad: str, yakin: tuple[float, float] | None = None) -> tuple[float, float]:
    """(boylam, enlem). Aynı adlı şehirlerde `yakin` verilirse ona en yakını, yoksa en kalabalığı."""
    a = adaylar(ad)
    s = min(a, key=lambda x: km((x[3], x[4]), yakin)) if yakin and len(a) > 1 else a[0]
    return s[3], s[4]


def ulke(ad: str) -> dict:
    k = _anahtar(ad)
    for u in veri()["ulkeler"]:
        if k in {_anahtar(u["iso"]), _anahtar(u["ad"]), _anahtar(u.get("tr") or ""), _anahtar(u.get("de") or "")}:
            return u
    raise HaritaHatasi(f"ülke bulunamadı: {ad}")


def durak(d, yakin: tuple[float, float] | None = None) -> dict:
    """{"ad": görünen ad, "konum": (boylam, enlem)}; d şehir adı ya da {"ad", "konum"?, "ara"?, "etiket"?}"""
    if isinstance(d, str):
        d = {"ad": d}
    konum = d.get("konum")
    if konum is None:
        konum = sehir(d.get("ara", d["ad"]), yakin)
    lon, lat = float(konum[0]), float(konum[1])
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise HaritaHatasi(f"{d['ad']}: konum [boylam, enlem] olmalı")
    return {"ad": d.get("etiket", d["ad"].split(",")[0].strip()), "konum": (lon, lat)}


def duraklar(liste) -> list[dict]:
    """Bir rotanın durakları. Aynı adlı şehirler (Córdoba İspanya/Arjantin) rotanın geri kalanına en yakın olandan
    seçilir: önce tek anlamlı duraklar ve konumu verilenler, sonra belirsizler onların ortasına göre."""
    def tek(d):
        if isinstance(d, dict) and d.get("konum") is not None:
            return True
        ad = d if isinstance(d, str) else d.get("ara", d["ad"])
        return len(adaylar(ad)) == 1
    sabit = [durak(d)["konum"] for d in liste if tek(d)]
    if not sabit:  # hepsi belirsiz: ilk durak en kalabalık adayından, diğerleri ona göre
        sabit = [durak(liste[0])["konum"]]
    orta = (sum(p[0] for p in sabit) / len(sabit), sum(p[1] for p in sabit) / len(sabit))
    return [durak(d, orta) for d in liste]


def km(a, b) -> float:
    (lo1, la1), (lo2, la2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def mesafe(konumlar) -> float:
    return sum(km(a, b) for a, b in zip(konumlar, konumlar[1:]))


class Kamera:
    """Eşdikdörtgen izdüşüm (enlem ortasında cos düzeltmesi), bir dikdörtgene sığdırılmış."""

    def __init__(self, lon: float, lat: float, olcek: float, cx: float, cy: float):
        self.lon, self.lat, self.olcek, self.cx, self.cy = lon, lat, olcek, cx, cy
        self.k = math.cos(math.radians(lat))

    def xy(self, lon: float, lat: float) -> tuple[float, float]:
        return self.cx + (lon - self.lon) * self.olcek * self.k, self.cy - (lat - self.lat) * self.olcek

    def kutu(self, x0, y0, x1, y1) -> tuple[float, float, float, float]:
        """ekran dikdörtgeninin coğrafi kutusu (boylam0, enlem0, boylam1, enlem1)"""
        return (self.lon + (x0 - self.cx) / (self.olcek * self.k), self.lat - (y1 - self.cy) / self.olcek,
                self.lon + (x1 - self.cx) / (self.olcek * self.k), self.lat - (y0 - self.cy) / self.olcek)

    @staticmethod
    def sigdir(konumlar, x0, y0, x1, y1, pay=0.18, en_az=1.2, ulkeler=()) -> "Kamera":
        """durakları (ve verilen ülkeleri) dikdörtgene sığdırır; en_az: kutunun en kısa kenarı en az bu kadar derece"""
        xs = [p[0] for p in konumlar]
        ys = [p[1] for p in konumlar]
        for u in ulkeler:
            b = u["ana_kutu"]
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
        lat = (min(ys) + max(ys)) / 2
        k = math.cos(math.radians(lat))
        gx = max((max(xs) - min(xs)) * k, en_az)
        gy = max(max(ys) - min(ys), en_az)
        W, H = (x1 - x0) * (1 - 2 * pay), (y1 - y0) * (1 - 2 * pay)
        return Kamera((min(xs) + max(xs)) / 2, lat, min(W / gx, H / gy), (x0 + x1) / 2, (y0 + y1) / 2)


def kara(kam: Kamera, kutu, isolar=None):
    """görünen ülkelerin skia yolları: [(ülke, yol)]; isolar verilirse yalnız onlar"""
    import skia
    lo0, la0, lo1, la1 = kutu
    out = []
    for u in veri()["ulkeler"]:
        b = u["kutu"]
        if (isolar is not None and u["iso"] not in isolar) or b[2] < lo0 or b[0] > lo1 or b[3] < la0 or b[1] > la1:
            continue
        p = skia.Path()
        for h in u["h"]:
            p.addPoly([skia.Point(*kam.xy(*q)) for q in h], True)
        out.append((u, p))
    return out


def rota(kam: Kamera, konumlar, bukum: float = 0.16):
    """duraklar arasında hafif kavisli rota; (yol, her durağın yol üzerindeki oranı)"""
    import skia
    pts = [kam.xy(*k) for k in konumlar]
    p = skia.Path()
    p.moveTo(*pts[0])
    uzun = [0.0]
    for i in range(1, len(pts)):
        (x0, y0), (x1, y1) = pts[i - 1], pts[i]
        isaret = 1 if i % 2 else -1
        cx, cy = (x0 + x1) / 2 - (y1 - y0) * bukum * isaret, (y0 + y1) / 2 + (x1 - x0) * bukum * isaret
        p.quadTo(cx, cy, x1, y1)
        parca = skia.Path()
        parca.moveTo(x0, y0)
        parca.quadTo(cx, cy, x1, y1)
        uzun.append(uzun[-1] + skia.PathMeasure(parca, False).getLength())
    toplam = uzun[-1] or 1.0
    return p, [x / toplam for x in uzun]


def kirp(yol, t: float):
    """yolun baştan t oranı (çizilerek beliren rota)"""
    import skia
    if t >= 1:
        return yol
    olc = skia.PathMeasure(yol, False)
    out = skia.Path()
    if t > 0:
        olc.getSegment(0, olc.getLength() * t, out, True)
    return out


def uc(yol, t: float) -> tuple[float, float]:
    import skia
    olc = skia.PathMeasure(yol, False)
    pos = olc.getPosTan(olc.getLength() * max(0.0, min(1.0, t)))
    return (pos[0].x(), pos[0].y()) if pos else (0.0, 0.0)


def veri_yenile() -> Path:
    """Natural Earth 1:50m ülke ve şehir verisini indirip sıkıştırılmış tek dosyaya yazar."""
    import urllib.request

    def al(ad):
        with urllib.request.urlopen(NE + ad + ".geojson", timeout=60) as r:
            return json.loads(r.read())

    ulkeler = []
    for ft in al("ne_50m_admin_0_countries")["features"]:
        g = ft["geometry"]
        halkalar = []
        for poly in g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]:
            q: list = []
            for x, y in poly[0]:
                pt = [round(x, 2), round(y, 2)]
                if not q or q[-1] != pt:
                    q.append(pt)
            if len(q) >= 4:
                halkalar.append(q)
        P = ft["properties"]
        ulkeler.append({"iso": P["ADM0_A3"], "ad": P["NAME"], "tr": P.get("NAME_TR"), "de": P.get("NAME_DE"), "h": halkalar})
    sehirler = [[P["name"], P["nameascii"], P["adm0_a3"], round(P["longitude"], 4), round(P["latitude"], 4), int(P["pop_max"] or 0)]
                for P in (ft["properties"] for ft in al("ne_10m_populated_places_simple")["features"])]
    v = {"kaynak": "Natural Earth 1:50m ülkeler, 1:10m şehirler (kamu malı), naturalearthdata.com", "ulkeler": ulkeler, "sehirler": sehirler}
    with gzip.open(VERI, "wt", encoding="utf-8") as f:
        f.write(json.dumps(v, ensure_ascii=False, separators=(",", ":")))
    return VERI


def main(argv: list[str] | None = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] not in ("bul", "mesafe", "veri-yenile"):
        print(__doc__)
        return 1
    if a[0] == "veri-yenile":
        print(veri_yenile())
        return 0
    try:
        dd = duraklar(a[1:])
    except HaritaHatasi as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    if a[0] == "bul":
        for d in dd:
            print(f"{d['ad']}\t{d['konum'][0]:.4f}, {d['konum'][1]:.4f}")
    else:
        k = [d["konum"] for d in dd]
        for x, y, d in zip(k, k[1:], dd[1:]):
            print(f"→ {d['ad']}\t{km(x, y):,.0f} km".replace(",", "."))
        print(f"toplam\t{mesafe(k):,.0f} km".replace(",", "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
