"""Okunabilirlik: yazı ekranda okunacak kadar kalıyor mu, zeminden ayrılıyor mu, ilk 2 saniye kancalı mı.

Kalite kapısı (`kalite.py`) bunu her videoda çağırır. Üç ölçü:

- **Kanca** (her video, kayıt gerekmez): ilk 2 saniyede görüntü kıpırdıyor mu, ilk kare boş mu.
- **Okuma süresi, kontrast, sığma** (metin kaydı varsa): şablon render sırasında çizdiği her yazıyı
  `MetinKaydi` ile kaydeder; kayıt videonun yanına `<ad>.metin.json` olarak yazılır. Kapı her yazının
  ekranda kalma süresini metnin gerektirdiği okuma süresiyle karşılaştırır, yazı rengiyle zeminin
  WCAG kontrastını videonun kendi karesinden ölçer (en az 4.5:1) ve kutunun kadraja ve dikey videoda
  Reels/TikTok arayüzünün dışına sığıp sığmadığına bakar. Pikselden yazı ayırt etmek güvenilir
  olmadığı için yazının yeri ve süresi şablondan gelir, kontrast ise gerçek kareden ölçülür.

Şablona bağlama (örnek: kinetik/cizim.py):

    kayit = okunabilirlik.MetinKaydi(W, H)
    for i in range(n):
        kayit.kare(i / fps)                    # her kare başında
        ...  kayit.ciz(metin, (x, y, w, h), renk=(r, g, b), alfa=a)   # yazı çizen yerde, piksel kutusu
    kayit.yaz(sessiz_video)                    # sessiz-x.metin.json; akis.birlestir hedefin yanına taşır
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ESIK = {
    "kontrast_uyari": 4.5,     # WCAG AA, normal yazı; altı uyarı
    "kontrast_uyari_buyuk": 3.0,   # WCAG AA, büyük yazı
    "kontrast_hata": 3.0,      # normal yazıda altı hata
    "kontrast_hata_buyuk": 2.0,
    "buyuk_yazi": 0.042,       # kutu yüksekliği / kısa kenar; üstü büyük yazı (telefonda ~24 px ve üstü harf)
    "okuma_hata": 0.6,         # ekranda kalma / gereken süre; altı hata
    "kelime_sn": 0.30,         # kelime başına okuma süresi (≈ 3.3 kelime/sn; kısa video izleyicisi hızlı okur)
    "harf_sn": 1 / 15,         # harf başına (altyazı ölçüsü 15 harf/sn); uzun Türkçe kelimeler için
    "okuma_taban": 0.5,        # tek kelimenin bile en az görünmesi gereken süre (sn)
    "alfa_gorunur": 0.6,       # bundan saydam çizimler (hayalet iz, giriş/çıkış) sayılmaz
    "kanca_sn": 2.0,
    "kanca_hareket": 1.5,      # ardışık küçük karelerde ortalama mutlak fark (0–255); altı "kıpırtısız"
    "bos_kare_std": 3.0,       # ilk karenin parlaklık sapması bunun altındaysa ekran boş
    "arayuz_hata": 0.25,       # yazı kutusunun bu oranı arayüz bölgesindeyse hata
    "arayuz_uyari": 0.02,
}
# Dikey videoda yazının girmemesi gereken üst ve alt bant (kalite.ARAYUZ_9X16 ile aynı; yan butonlar
# yazıyı kapatmaz, sayılmaz)
ARAYUZ_UST, ARAYUZ_ALT = 0.10, 0.22


def _bul(seviye: str, kontrol: str, mesaj: str, an: float | None = None) -> dict:
    b = {"seviye": seviye, "kontrol": kontrol, "mesaj": mesaj}
    if an is not None:
        b["an"] = round(an, 2)
    return b


# ---------------------------------------------------------------- kayıt (şablon tarafı)

class MetinKaydi:
    """Render sırasında çizilen yazıları kare kare toplar, `yaz` ile görünme aralıklarına çevirir."""

    def __init__(self, W: int, H: int):
        self.W, self.H = W, H
        self.t = 0.0
        self._kareler: list[float] = []
        self._ham: list[tuple[int, str, tuple, tuple | None, int]] = []
        self._sira: dict[str, int] = {}

    def kare(self, t: float) -> None:
        self.t = t
        self._kareler.append(t)
        self._sira = {}

    def ciz(self, metin: str, kutu, renk=None, alfa: float = 1.0) -> None:
        """`kutu`: (x, y, w, h) ekran pikseli; `renk`: (r, g, b) 0–255. Saydam çizimler sayılmaz."""
        metin = " ".join(str(metin).split())
        if not metin or alfa < ESIK["alfa_gorunur"] or not self._kareler:
            return
        sablon = _sayac(metin)  # sayaç gibi değişen yazı (1,00× → 37,78×) tek yazı sayılır
        n = self._sira.get(sablon, 0)  # aynı karede aynı yazı iki kez varsa ayrı say
        self._sira[sablon] = n + 1
        k = tuple(round(float(v), 1) for v in kutu)
        r = None if renk is None else tuple(int(v) for v in renk[:3])
        self._ham.append((len(self._kareler) - 1, metin, k, r, n))

    def olaylar(self) -> list[dict]:
        """Aynı yazının ardışık karelerdeki görünüşlerini tek olayda birleştirir."""
        if not self._kareler:
            return []
        adim = (self._kareler[-1] - self._kareler[0]) / max(1, len(self._kareler) - 1) or 1 / 30
        acik: dict[tuple[str, int], dict] = {}
        biten: list[dict] = []
        for ki, metin, kutu, renk, n in self._ham:
            anahtar = (_sayac(metin), n)
            o = acik.get(anahtar)
            if o is not None and ki - o["_son"] <= 1:
                o["_son"] = ki
                o["metin"] = metin  # sayaçta son değer kalır
                o["_kutular"].append((ki, kutu, renk))
                continue
            if o is not None:
                biten.append(o)
            acik[anahtar] = {"metin": metin, "_ilk": ki, "_son": ki, "_kutular": [(ki, kutu, renk)]}
        biten += acik.values()
        out = []
        for o in sorted(biten, key=lambda x: (x["_ilk"], x["metin"])):
            orta = o["_kutular"][len(o["_kutular"]) // 2]
            out.append({"metin": o["metin"], "bas": round(self._kareler[o["_ilk"]], 3),
                        "bit": round(self._kareler[o["_son"]] + adim, 3), "an": round(self._kareler[orta[0]], 3),
                        "kutu": list(orta[1]), "renk": None if orta[2] is None else list(orta[2])})
        return out

    def yaz(self, video: str | Path) -> Path:
        hedef = Path(video).with_suffix(".metin.json")
        hedef.write_text(json.dumps({"W": self.W, "H": self.H, "metinler": self.olaylar()}, ensure_ascii=False,
                                    indent=1), encoding="utf-8")
        return hedef


def _sayac(metin: str) -> str:
    return re.sub(r"\d+", "#", metin)


def kaydi_tasi(kaynak_video: Path, hedef_video: Path) -> None:
    """Sessiz videonun metin kaydını birleştirilmiş videonun yanına kopyalar (akis.birlestir çağırır)."""
    k = Path(kaynak_video).with_suffix(".metin.json")
    if k.exists():
        Path(hedef_video).with_suffix(".metin.json").write_text(k.read_text(encoding="utf-8"), encoding="utf-8")


# ---------------------------------------------------------------- ölçüler

def okuma_suresi(metin: str) -> float:
    """Bir yazının rahat okunması için gereken saniye (kelime ve harf ölçüsünün büyüğü)."""
    kelime = len(re.findall(r"\w+", metin)) or 1
    harf = len(re.sub(r"\s", "", metin))
    return round(max(ESIK["okuma_taban"], 0.25 + kelime * ESIK["kelime_sn"], harf * ESIK["harf_sn"]), 2)


def _goreli_parlaklik(rgb) -> float:
    def kanal(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (float(x) for x in rgb[:3])
    return 0.2126 * kanal(r) + 0.7152 * kanal(g) + 0.0722 * kanal(b)


def kontrast(a, b) -> float:
    la, lb = _goreli_parlaklik(a), _goreli_parlaklik(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def kontrast_olc(kare, kutu, renk=None) -> dict | None:
    """Karede kutunun içindeki yazı rengi ile zemin rengini ayırıp WCAG oranını verir.

    Renk biliniyorsa ona yakın pikseller yazı, uzak olanlar zemin sayılır; renk yoksa ya da zemine çok
    yakınsa parlaklık iki kümeye ayrılır (Otsu) ve renge yakın (renk yoksa az olan) küme yazıdır. Harflerin arası dar olabileceği için kutu çevresinde
    %25 pay da zemine katılır. Ölçülemezse None.
    """
    import numpy as np
    H, W, _ = kare.shape
    x, y, w, h = kutu
    px, py = w * 0.25, h * 0.25
    x0, y0 = max(0, int(x - px)), max(0, int(y - py))
    x1, y1 = min(W, int(x + w + px)), min(H, int(y + h + py))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    p = kare[y0:y1, x0:x1, :3].reshape(-1, 3).astype(np.float32)
    yazi = zemin = None
    if renk is not None:
        d = np.sqrt(((p - np.array(renk[:3], dtype=np.float32)) ** 2).sum(axis=1))
        if (d < 40).sum() >= 20 and (d > 90).sum() >= 20:
            yazi, zemin = p[d < 40], p[d > 90]
    if yazi is None:  # renk yok ya da zemine çok yakın: parlaklığı iki kümeye ayır
        lum = np.rint(p @ np.array([0.299, 0.587, 0.114], dtype=np.float32)).astype(np.int32).clip(0, 255)
        hist = np.bincount(lum, minlength=256).astype(np.float64)
        om = np.cumsum(hist)
        mu = np.cumsum(hist * np.arange(256))
        toplam, mt = om[-1], mu[-1]
        with np.errstate(divide="ignore", invalid="ignore"):
            ara = (mt * om / toplam - mu) ** 2 / (om * (toplam - om))
        ara[~np.isfinite(ara)] = np.nan
        if np.isnan(ara).all():
            return None  # tek ton: yazı yok
        esik = int(np.nanargmax(ara))
        koyu, acik = p[lum <= esik], p[lum > esik]
        if len(koyu) < 20 or len(acik) < 20:
            return None
        if renk is not None:  # renge yakın küme yazıdır
            r = np.array(renk[:3], dtype=np.float32)
            koyu_yakin = np.abs(np.median(koyu, axis=0) - r).sum() <= np.abs(np.median(acik, axis=0) - r).sum()
            yazi, zemin = (koyu, acik) if koyu_yakin else (acik, koyu)
        else:  # az olan küme yazıdır
            yazi, zemin = (koyu, acik) if len(koyu) < len(acik) else (acik, koyu)
    y_renk = np.median(yazi, axis=0)
    z_renk = np.median(zemin, axis=0)
    return {"oran": round(kontrast(y_renk, z_renk), 2), "yazi": [int(v) for v in y_renk],
            "zemin": [int(v) for v in z_renk]}


def sigma_olc(kutu, W: int, H: int) -> dict:
    """Kutunun kadraj dışında ve dikey videoda arayüz bandında kalan oranları."""
    x, y, w, h = kutu
    alan = max(1e-6, w * h)
    ix = max(0.0, min(x + w, W) - max(x, 0))
    iy = max(0.0, min(y + h, H) - max(y, 0))
    disari = 1 - ix * iy / alan
    arayuz = 0.0
    if H > W:
        ust = max(0.0, min(y + h, H * ARAYUZ_UST) - max(y, 0)) * ix
        alt = max(0.0, min(y + h, H) - max(y, H * (1 - ARAYUZ_ALT))) * ix
        arayuz = (ust + alt) / alan
    return {"disari": round(disari, 3), "arayuz": round(arayuz, 3)}


def kanca_olc(yol: Path, sure: float) -> dict | None:
    """İlk 2 saniyeyi 160 px genişlikte 10 kare/sn gri okuyup hareket ve boşluk ölçer."""
    import numpy as np
    d = min(ESIK["kanca_sn"], sure)
    if d <= 0:
        return None
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-t", f"{d:.3f}", "-i", str(yol),
                        "-vf", "fps=10,scale=160:-2", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "csv=p=0", str(yol)], capture_output=True, text=True)
    if r.returncode or pr.returncode or not r.stdout:
        return None
    W, H = (int(v) for v in pr.stdout.strip().split(",")[:2])
    h = int(round(H * 160 / W / 2) * 2)
    n = len(r.stdout) // (160 * h)
    if n < 2:
        return None
    k = np.frombuffer(r.stdout[: n * 160 * h], dtype=np.uint8).reshape(n, h, 160).astype(np.float32)
    fark = np.abs(np.diff(k, axis=0)).mean(axis=(1, 2))
    hareketli = fark >= ESIK["kanca_hareket"]
    ilk_hareket = float((np.argmax(hareketli) + 1) / 10) if hareketli.any() else None
    gorunur = k.std(axis=(1, 2)) >= ESIK["bos_kare_std"]
    return {"hareket_en": round(float(fark.max()), 2), "ilk_hareket_sn": ilk_hareket,
            "ilk_kare_bos": bool(not gorunur[0]),
            "ilk_gorunur_sn": float(np.argmax(gorunur) / 10) if gorunur.any() else None}


# ---------------------------------------------------------------- kapı

def kanca_kontrol(yol: Path, sure: float) -> tuple[list[dict], dict | None]:
    k = kanca_olc(yol, sure)
    if k is None:
        return [], None
    out = []
    if k["ilk_hareket_sn"] is None:
        out.append(_bul("uyari", "kanca", f"ilk {ESIK['kanca_sn']:.0f} saniyede görüntü kıpırdamıyor; akışta kaydırılıp "
                        "geçilir. Açılışa hareket, sayı ya da soru koyun", 0.0))
    if k["ilk_gorunur_sn"] is None:
        out.append(_bul("uyari", "kanca", f"ilk {ESIK['kanca_sn']:.0f} saniye boş ekran", 0.0))
    elif k["ilk_kare_bos"] and k["ilk_gorunur_sn"] > 0.5:
        out.append(_bul("uyari", "kanca", f"ilk kare boş, görüntü {k['ilk_gorunur_sn']:.1f} sn'de geliyor; akıştaki "
                        "küçük resim boş görünür", 0.0))
    return out, k


def metin_kontrol(yol: Path, kare_al) -> tuple[list[dict], dict | None]:
    """`<video>.metin.json` varsa her yazı için okuma süresi, kontrast ve sığma. `kare_al(t)` → RGB dizi."""
    k = Path(yol).with_suffix(".metin.json")
    if not k.exists():
        return [_bul("bilgi", "okunabilirlik", "metin kaydı yok (şablon MetinKaydi yazmıyor); okuma süresi ve yazı "
                     "kontrastı ölçülmedi, kontakt sayfasına bakın")], None
    try:
        j = json.loads(k.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [_bul("uyari", "okunabilirlik", f"metin kaydı okunamadı ({e})")], None
    W, H = j["W"], j["H"]
    out, satirlar = [], []
    kare_onbellek: dict[float, object] = {}
    en_dusuk = None
    for m in j.get("metinler", []):
        gor = round(m["bit"] - m["bas"], 2)
        ger = okuma_suresi(m["metin"])
        s = {"metin": m["metin"], "bas": m["bas"], "sure": gor, "gereken": ger}
        kisa = m["metin"] if len(m["metin"]) <= 40 else m["metin"][:37] + "…"
        if gor < ger * ESIK["okuma_hata"]:
            out.append(_bul("hata", "okuma", f"\"{kisa}\" {gor:.1f} sn görünüyor, okumak için {ger:.1f} sn gerekir", m["bas"]))
        elif gor < ger:
            out.append(_bul("uyari", "okuma", f"\"{kisa}\" {gor:.1f} sn görünüyor, rahat okuma {ger:.1f} sn", m["bas"]))
        sg = sigma_olc(m["kutu"], W, H)
        s.update(sg)
        if sg["disari"] > 0.01:
            out.append(_bul("hata", "sigma", f"\"{kisa}\" kadrajdan taşıyor (%{sg['disari'] * 100:.0f}'i dışarıda)", m["an"]))
        if sg["arayuz"] >= ESIK["arayuz_hata"]:
            out.append(_bul("hata", "sigma", f"\"{kisa}\" Reels/TikTok arayüzünün altında kalıyor "
                            f"(%{sg['arayuz'] * 100:.0f}'i üst %10 / alt %22 bantta)", m["an"]))
        elif sg["arayuz"] >= ESIK["arayuz_uyari"]:
            out.append(_bul("uyari", "sigma", f"\"{kisa}\" arayüz bandına değiyor (%{sg['arayuz'] * 100:.0f})", m["an"]))
        t = m["an"]
        if t not in kare_onbellek:
            kare_onbellek[t] = kare_al(t)
        kare = kare_onbellek[t]
        ko = None if kare is None else kontrast_olc(kare, m["kutu"], m.get("renk"))
        if ko is not None:
            s["kontrast"] = ko["oran"]
            buyuk = m["kutu"][3] >= ESIK["buyuk_yazi"] * min(W, H)
            ek = "_buyuk" if buyuk else ""
            gerek = ESIK["kontrast_uyari" + ek]
            tur = "büyük yazı" if buyuk else "yazı"
            if ko["oran"] < ESIK["kontrast_hata" + ek]:
                out.append(_bul("hata", "kontrast", f"\"{kisa}\" zeminden ayrılmıyor: kontrast {ko['oran']:.1f}:1 "
                                f"({tur} için en az {gerek:.1f}:1)", t))
            elif ko["oran"] < gerek:
                out.append(_bul("uyari", "kontrast", f"\"{kisa}\" kontrastı {ko['oran']:.1f}:1, {tur} için en az "
                                f"{gerek:.1f}:1 olmalı", t))
            en_dusuk = ko["oran"] if en_dusuk is None else min(en_dusuk, ko["oran"])
        satirlar.append(s)
    ozet = {"metin_sayisi": len(satirlar), "en_dusuk_kontrast": en_dusuk,
            "okuma_eksik": sum(1 for s in satirlar if s["sure"] < s["gereken"]), "metinler": satirlar}
    return out, ozet
