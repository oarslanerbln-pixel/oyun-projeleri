"""Ortak sahne dili: tek senaryo biçimi, her stil aynı sahne tiplerini kendi görünümüyle çizer.

Senaryo (`"dil": "sahne"`) sahnelerden oluşur; her sahnenin bir `tip`i, ekran yazıları ve isteğe bağlı bir
seslendirme satırı vardır. Zaman çizelgesi seslendirmeden çıkar: sahne, satırı kadar (önünde ve arkasında kısa
nefesle) sürer; satır yoksa tipin en kısa süresi kullanılır. Böylece senaryoda saniye yazmak gerekmez.

Bağımlılık yok (CI'da senaryo denetimi için); çizim `kaplama.py`, ses `ses.py`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SURUM = "sahne"
FORMATLAR = {"9x16": (1080, 1920), "16x9": (1920, 1080), "1x1": (1080, 1080), "4x5": (1080, 1350)}
SURE = (4.0, 120.0)
ON, ARKA = 0.35, 0.45  # seslendirme sahne başından ON sn sonra başlar, bittikten ARKA sn sonra sahne değişir
TAHMINI_HIZ = 2.6  # seslendirme dosyası yokken süre tahmini (sözcük/sn)

# tip -> alan -> (zorunlu, en çok karakter). Sınırlar yerleşimin taşmaması için; çizim yine de sığdırır.
TIPLER: dict[str, dict] = {
    "baslik": {"alan": {"metin": (True, 28), "alt": (False, 40), "ust": (False, 20)}, "en_kisa": 1.8},
    "liste": {"alan": {"baslik": (False, 28)}, "en_kisa": 2.4},  # maddeler: 2–5 satır, her biri ≤ 28
    "sayi": {"alan": {"deger": (True, 8), "etiket": (False, 28), "ust": (False, 20)}, "en_kisa": 2.0},
    "alinti": {"alan": {"metin": (True, 90), "kaynak": (False, 30)}, "en_kisa": 2.6},
    "karsilastirma": {"alan": {"sol": (True, 16), "sag": (True, 16), "sol_deger": (False, 6), "sag_deger": (False, 6),
                               "baslik": (False, 28)}, "en_kisa": 2.4},
    "urun": {"alan": {"ad": (True, 24), "fiyat": (False, 12), "ozellik": (False, 32), "gorsel": (False, None)}, "en_kisa": 2.4},
    "cta": {"alan": {"metin": (True, 22), "alt": (False, 32)}, "en_kisa": 2.2},
    "gecis": {"alan": {"metin": (False, 20)}, "en_kisa": 0.8},  # sahneler arası kısa ara kart, seslendirme almaz
    # veri sahnesi: veri = CSV dosyası (etiket, değer) ya da [["Ocak", 12], ...]; birim "%{}" / "{} ₺" / "kg"
    "grafik": {"alan": {"baslik": (False, 28), "tur": (False, None), "birim": (False, 8), "kaynak": (False, 30)},
               "en_kisa": 3.0},
    # harita ve rota: duraklar = şehir adları ya da {"ad", "konum": [boylam, enlem]}; rota durak durak çizilir
    "harita": {"alan": {"baslik": (False, 28)}, "en_kisa": 3.5},
}
DURAK = (2, 8, 16)  # harita: en az, en çok durak, durak adı karakter
GRAFIK = {"cubuk": (2, 8), "cizgi": (3, 12), "pasta": (2, 6)}  # tür -> (en az, en çok satır)
ETIKET = 12  # grafik etiketi en çok karakter
KANCA = ("soru", "rakam", "sok")
MADDE = (2, 5, 28)  # liste: en az, en çok madde, madde başına karakter
ORTAK_ALANLAR = {"tip", "seslendirme", "okunus", "sure", "not", "stiller", "kanca", "stil", "donustur"}
ENERJI = {"baslik": 1, "liste": 1, "sayi": 2, "alinti": 0, "karsilastirma": 2, "urun": 1, "cta": 2, "gecis": 0,
          "grafik": 1, "harita": 1}


class SenaryoHatasi(ValueError):
    pass


def bu_dil_mi(s: dict) -> bool:
    """Senaryo ortak sahne dilinde mi (stil.py yönlendirmesi için)."""
    return s.get("dil") == SURUM or any(isinstance(x, dict) and "tip" in x for x in s.get("sahneler") or [])


def yukle(yol: str | Path) -> dict:
    yol = Path(yol)
    s = json.loads(yol.read_text(encoding="utf-8"))
    s["_klasor"] = str(yol.resolve().parent)
    s.setdefault("fps", 30)
    return s


def sozcuk(metin: str) -> int:
    return len(re.findall(r"\w+", metin or ""))


def tahmini_sure(metin: str) -> float:
    return sozcuk(metin) / TAHMINI_HIZ + 0.2 if metin else 0.0


def denetle(s: dict) -> list[str]:
    """Biçim denetimi (seslendirme dosyası gerekmez). Boş liste = geçerli."""
    h: list[str] = []
    shs = s.get("sahneler")
    if not isinstance(shs, list) or not shs:
        return ["sahneler: en az bir sahne gerekli"]
    if len(shs) > 24:
        h.append(f"sahneler: en çok 24 sahne ({len(shs)}); daha uzun video için kurgu şablonu")
    for f in ([s["format"]] if isinstance(s.get("format"), str) else s.get("format") or []):
        if str(f).replace(":", "x") not in FORMATLAR and f != "ikisi":
            h.append(f"format: {f} bilinmiyor (9:16, 16:9, 1:1, 4:5 ya da ikisi)")
    for k, v in (s.get("palet") or {}).items():
        if not (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)):
            h.append(f"palet.{k}: #RRGGBB olmalı")
    logo = (s.get("marka") or {}).get("logo")
    if logo and not (Path(s.get("_klasor", ".")) / logo).exists():
        h.append(f"marka.logo: {logo} bulunamadı (senaryoya göre)")
    for i, sh in enumerate(shs):
        ad = f"sahne {i + 1}"
        if not isinstance(sh, dict) or sh.get("tip") not in TIPLER:
            h.append(f"{ad}: tip {', '.join(TIPLER)} olmalı ({sh.get('tip') if isinstance(sh, dict) else sh})")
            continue
        tip = sh["tip"]
        ad = f"{ad} ({tip})"
        alan = TIPLER[tip]["alan"]
        for k in sh:
            ek = {"liste": ["maddeler"], "grafik": ["veri"], "harita": ["duraklar", "ulkeler", "mesafe"]}.get(tip, [])
            if k not in alan and k not in ORTAK_ALANLAR and k not in ek:
                h.append(f"{ad}: bilinmeyen alan {k} ({', '.join(list(alan) + ek)})")
        for k, (zorunlu, azami) in alan.items():
            v = sh.get(k)
            if v is None:
                if zorunlu:
                    h.append(f"{ad}: {k} gerekli")
                continue
            if not isinstance(v, str) or not v.strip():
                h.append(f"{ad}: {k} boş olmayan metin olmalı")
            elif azami and len(v) > azami:
                h.append(f"{ad}: {k} \"{v}\" {len(v)} karakter, en çok {azami} (az yazı kuralı)")
        if tip == "liste":
            m = sh.get("maddeler")
            if not isinstance(m, list) or not MADDE[0] <= len(m) <= MADDE[1]:
                h.append(f"{ad}: maddeler {MADDE[0]}–{MADDE[1]} satırlık liste olmalı")
            else:
                for j, x in enumerate(m):
                    if not isinstance(x, str) or not x.strip() or len(x) > MADDE[2]:
                        h.append(f"{ad}: madde {j + 1} boş olmamalı ve en çok {MADDE[2]} karakter olmalı")
        if tip == "harita":
            h += [f"{ad}: {x}" for x in harita_denetle(sh)]
        if tip == "grafik":
            if sh.get("tur", "cubuk") not in GRAFIK:
                h.append(f"{ad}: tur {', '.join(GRAFIK)} olmalı")
            else:
                try:
                    veri_oku(sh, s.get("_klasor", "."))
                except SenaryoHatasi as e:
                    h.append(f"{ad}: {e}")
        if "kanca" in sh and sh["kanca"] not in KANCA:
            h.append(f"{ad}: kanca {', '.join(KANCA)} olmalı")
        if tip == "urun" and sh.get("gorsel") and not (Path(s.get("_klasor", ".")) / sh["gorsel"]).exists():
            h.append(f"{ad}: gorsel {sh['gorsel']} bulunamadı (senaryoya göre)")
        if tip == "gecis" and sh.get("seslendirme"):
            h.append(f"{ad}: geçiş sahnesi seslendirme almaz")
        if "seslendirme" in sh and not (isinstance(sh["seslendirme"], str) and sh["seslendirme"].strip()):
            h.append(f"{ad}: seslendirme boş olmayan metin olmalı")
        if "sure" in sh and not (isinstance(sh["sure"], (int, float)) and 0.6 <= sh["sure"] <= 20):
            h.append(f"{ad}: sure 0,6–20 sn olmalı")
    if not h:
        sure = zamanla(s)["sure"]
        if not SURE[0] <= sure <= SURE[1]:
            h.append(f"toplam süre {sure:.1f} sn; {SURE[0]:g}–{SURE[1]:g} sn olmalı")
    return h


def sayi_oku(x) -> float:
    """12 / 12.5 / "1.200" / "1.200,5" / "12,5" / "%40" -> float (Türkçe ve Almanca ayraçlar)"""
    if isinstance(x, bool):
        raise ValueError(x)
    if isinstance(x, (int, float)):
        return float(x)
    m = re.search(r"-?\d[\d.,]*", str(x))
    if not m:
        raise ValueError(x)
    ham = m.group()
    if "," in ham:
        ham = ham.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", ham):
        ham = ham.replace(".", "")
    return float(ham)


def harita_anlari(sh: dict, d: float) -> list[float]:
    """harita sahnesinde rotanın her durağa vardığı an (senkron yoksa); kaplama.ciz_harita ile aynı"""
    n = len(sh["duraklar"])
    aralik = min(1.2, max(0.35, (d - 1.5) / max(1, n - 1)))
    return [0.45 + j * aralik for j in range(n)]


def harita_denetle(sh: dict) -> list[str]:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[2] / "ortak"))
    import harita
    d = sh.get("duraklar")
    if not isinstance(d, list) or not DURAK[0] <= len(d) <= DURAK[1]:
        return [f"duraklar {DURAK[0]}–{DURAK[1]} durak olmalı (şehir adı ya da {{\"ad\", \"konum\": [boylam, enlem]}})"]
    h = []
    try:
        for x in harita.duraklar(d):
            if len(x["ad"]) > DURAK[2]:
                h.append(f"durak \"{x['ad']}\" en çok {DURAK[2]} karakter (\"etiket\" ile kısaltın)")
    except (harita.HaritaHatasi, KeyError, TypeError, ValueError) as e:
        h.append(str(e) if isinstance(e, harita.HaritaHatasi) else f"durak biçimi hatalı: {e}")
    for u in sh.get("ulkeler") or []:
        try:
            harita.ulke(u)
        except harita.HaritaHatasi as e:
            h.append(str(e))
    if "mesafe" in sh and not isinstance(sh["mesafe"], bool):
        h.append("mesafe true/false olmalı")
    return h


def veri_oku(sh: dict, klasor: str | Path = ".") -> list[tuple[str, float]]:
    """Grafik sahnesinin verisi: [(etiket, değer)]. `veri` CSV dosyası (ilk iki sütun; başlık satırı atlanır,
    ; ya da , ayraç) ya da [[etiket, değer], ...] listesi. Hatalı veride SenaryoHatasi."""
    import csv
    v = sh.get("veri")
    if isinstance(v, str):
        yol = Path(klasor) / v
        if not yol.exists():
            raise SenaryoHatasi(f"veri {v} bulunamadı (senaryoya göre)")
        metin = yol.read_text(encoding="utf-8-sig")
        ayrac = ";" if metin.count(";") > metin.count(",") / 2 and ";" in metin else ","
        satirlar = [r for r in csv.reader(metin.splitlines(), delimiter=ayrac) if r and any(x.strip() for x in r)]
        if satirlar and len(satirlar[0]) >= 2:
            try:
                sayi_oku(satirlar[0][1])
            except ValueError:
                satirlar = satirlar[1:]  # başlık satırı
        v = satirlar
    if not isinstance(v, list) or not v:
        raise SenaryoHatasi("veri: CSV dosyası ya da [[etiket, değer], ...] listesi gerekli")
    out = []
    for j, r in enumerate(v):
        if not isinstance(r, (list, tuple)) or len(r) < 2:
            raise SenaryoHatasi(f"veri satır {j + 1}: etiket ve değer gerekli")
        e = str(r[0]).strip()
        try:
            d = sayi_oku(r[1])
        except ValueError:
            raise SenaryoHatasi(f"veri satır {j + 1}: değer sayı değil ({r[1]})") from None
        if not e or len(e) > ETIKET:
            raise SenaryoHatasi(f"veri satır {j + 1}: etiket boş olmamalı ve en çok {ETIKET} karakter olmalı ({e})")
        out.append((e, d))
    tur = sh.get("tur", "cubuk")
    az, cok = GRAFIK.get(tur, (2, 8))
    if not az <= len(out) <= cok:
        raise SenaryoHatasi(f"veri: {tur} için {az}–{cok} satır ({len(out)})")
    if tur in ("cubuk", "pasta") and any(d < 0 for _, d in out):
        raise SenaryoHatasi(f"veri: {tur} için değerler negatif olamaz")
    if tur == "pasta" and sum(d for _, d in out) <= 0:
        raise SenaryoHatasi("veri: pasta için toplam sıfırdan büyük olmalı")
    return out


def bicim(d: float, birim: str = "") -> str:
    """Grafik değeri ekran yazısı: binlik nokta, ondalık virgül; birim "%{}" / "{} ₺" kalıbı ya da sonek."""
    s = f"{int(round(d)):,}".replace(",", ".") if abs(d - round(d)) < 1e-9 else f"{d:.1f}".replace(".", ",")
    if not birim:
        return s
    return birim.replace("{}", s) if "{}" in birim else s + birim


def zamanla(s: dict, sureler: dict[str, float] | None = None) -> dict:
    """Sahnelere `bas`/`son` verir ve seslendirme satırlarını kurar. Satır süresi seslendirme dosyasından
    (`sureler`, id → sn), yoksa sözcük sayısından tahmin edilir. Senaryonun kopyasını döner."""
    sureler = sureler or {}
    out = dict(s)
    sb = dict(s.get("seslendirme") or {}) if isinstance(s.get("seslendirme"), dict) else {}
    satirlar, zs, t = [], [], 0.0
    for i, sh in enumerate(s["sahneler"]):
        sh = dict(sh)
        en_kisa = TIPLER[sh["tip"]]["en_kisa"] + (0.45 * len(sh.get("maddeler") or []) if sh["tip"] == "liste" else 0.0)
        if sh["tip"] == "grafik" and isinstance(sh.get("veri"), list):
            en_kisa += 0.25 * len(sh["veri"])
        d = en_kisa
        metin = sh.get("seslendirme")
        if metin:
            sid = f"s{i}"
            ses = sureler.get(sid, tahmini_sure(sh.get("okunus") or metin))
            satir = {"id": sid, "t": round(t + ON, 3), "metin": metin}
            if sh.get("okunus"):
                satir["okunus"] = sh["okunus"]
            satirlar.append(satir)
            sh["_ses"] = (t + ON, t + ON + ses)
            d = max(d, ON + ses + ARKA)
        if isinstance(sh.get("sure"), (int, float)):
            d = max(sh["sure"], d if metin else 0.0)
        sh["bas"], sh["son"] = round(t, 3), round(t + d, 3)
        zs.append(sh)
        t += d
    sb["satirlar"] = satirlar
    out["sahneler"], out["seslendirme"], out["sure"] = zs, sb, round(t, 3)
    return out


def sureler_oku(klasor: Path) -> dict[str, float]:
    k = Path(klasor) / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}
