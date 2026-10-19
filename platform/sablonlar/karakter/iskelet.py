"""Ortak karakter iskeleti: eklemler, pozlar, yüz ifadeleri ve aralarında yumuşak geçiş (yalnız standart kütüphane).

Görünüm katmanları (`gorunumler/*.py`) yalnız buradan çıkan `Govde` ve `Yuz` değerlerini çizer; aynı iskelet
çizgisel insanı, konuşan maskotu ya da silueti oynatır. Birimler karakter boyudur: ayaklar y=0'da, baş tepesi
y≈1'de, y yukarı doğru artar, x ekranın sağına doğru. "sol"/"sag" ekranın solu/sağıdır.

Açılar derece. Kol: `a` kolun aşağı sarkan hâlden dışa doğru açısı (0 = yanda sarkık, 90 = yana yatay,
180 = yukarı), `b` dirseğin aynı yönde ek bükümü (eksi değer ön kolu içe, gövdeye doğru katlar).
Bacak: `a` dışa açılma, `b` diz bükümü (eksi içe). Gövde ve baş: sağa eğilme pozitif.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# Oranlar (karakter boyu = 1). Görünüm katmanı bunları kendi bedenine göre değiştirebilir (Oranlar(...)).
@dataclass(frozen=True)
class Oranlar:
    ust_bacak: float = 0.155
    alt_bacak: float = 0.15
    kalca_genislik: float = 0.06
    govde: float = 0.31          # kalça → boyun dibi
    omuz_genislik: float = 0.095
    ust_kol: float = 0.16
    alt_kol: float = 0.15
    boyun: float = 0.03
    bas_yaricap: float = 0.095


POZ_ALANLARI = ("govde", "bas", "kol_sol_a", "kol_sol_b", "kol_sag_a", "kol_sag_b",
                "bacak_sol_a", "bacak_sol_b", "bacak_sag_a", "bacak_sag_b", "bakis_x", "bakis_y", "zipla")

_TEMEL = dict(govde=0, bas=0, kol_sol_a=22, kol_sol_b=-8, kol_sag_a=22, kol_sag_b=-8,
              bacak_sol_a=5, bacak_sol_b=0, bacak_sag_a=5, bacak_sag_b=0, bakis_x=0, bakis_y=0, zipla=0)

# Anahtar pozlar. `salinim`: pozun kendi hareketi (yürüyüş adımı, el sallama, zıplama), zamana bağlı ek.
POZLAR: dict[str, dict] = {
    "ayakta": {},
    "el_kaldir": dict(kol_sag_a=128, kol_sag_b=-6, kol_sol_a=55, kol_sol_b=-82, bakis_x=0.3, bakis_y=0.2),
    "isaret": dict(kol_sag_a=96, kol_sag_b=-4, kol_sol_a=55, kol_sol_b=-82, govde=-3, bas=-4, bakis_x=1),
    "dusun": dict(kol_sag_a=-53, kol_sag_b=-150, kol_sol_a=55, kol_sol_b=-82, bas=9, bakis_x=-0.5, bakis_y=0.8),
    "sevin": dict(kol_sag_a=128, kol_sag_b=12, kol_sol_a=128, kol_sol_b=12, bacak_sol_a=10, bacak_sag_a=10, bas=-3,
                  bakis_y=0.3, salinim="zipla"),
    "yuru": dict(salinim="yuru"),
    "selam": dict(kol_sag_a=118, kol_sag_b=26, bas=-4, bakis_x=0.2, salinim="selam"),
    "omuz": dict(kol_sag_a=30, kol_sag_b=68, kol_sol_a=30, kol_sol_b=68, bas=7, bakis_y=0.2),
}
POZ_ADLARI = tuple(POZLAR)

# Yüz ifadeleri. kas: kaş yüksekliği (-1..1), kas_aci: iç uçların yönü (+ üzgün, - kızgın/kararlı),
# goz: göz açıklığı (1 normal), mutlu_goz: 0..1 gözlerin hilal (gülen) biçime kayması,
# egri: ağız kavsi (+ gülümseme, - somurtma), agiz_ac: konuşmadan bağımsız açıklık (şaşkınlıkta "o").
IFADE_ALANLARI = ("kas", "kas_aci", "goz", "mutlu_goz", "egri", "agiz_ac", "agiz_gen")
IFADELER: dict[str, dict] = {
    "notr": dict(kas=0, kas_aci=0, goz=1, mutlu_goz=0, egri=0.25, agiz_ac=0, agiz_gen=1),
    "gulumse": dict(kas=0.15, kas_aci=0, goz=1, mutlu_goz=0.35, egri=0.85, agiz_ac=0, agiz_gen=1.1),
    "sevincli": dict(kas=0.2, kas_aci=0, goz=1, mutlu_goz=1, egri=1, agiz_ac=0.35, agiz_gen=1.25),
    "sasir": dict(kas=0.9, kas_aci=0, goz=1.35, mutlu_goz=0, egri=0, agiz_ac=0.55, agiz_gen=0.6),
    "uzgun": dict(kas=-0.2, kas_aci=0.9, goz=0.85, mutlu_goz=0, egri=-0.7, agiz_ac=0, agiz_gen=0.9),
    "kararli": dict(kas=-0.35, kas_aci=-0.8, goz=0.9, mutlu_goz=0, egri=0.05, agiz_ac=0, agiz_gen=0.85),
    "dusunceli": dict(kas=0.25, kas_aci=0.3, goz=0.95, mutlu_goz=0, egri=-0.1, agiz_ac=0, agiz_gen=0.6),
}
IFADE_ADLARI = tuple(IFADELER)

GECIS_SN = 0.38   # poz ya da ifade değişimi
GOZ_KIRP_SN = 0.13


def poz(ad: str) -> dict:
    p = dict(_TEMEL); p.update({k: v for k, v in POZLAR[ad].items() if k != "salinim"})
    p["salinim"] = POZLAR[ad].get("salinim")
    return p


def ifade(ad: str) -> dict:
    return dict(IFADELER[ad])


def yumusak(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def karistir(a: dict, b: dict, p: float, alanlar) -> dict:
    return {k: a[k] + (b[k] - a[k]) * p for k in alanlar}


def salinim(ad: str | None, faz: float, guc: float = 1.0) -> dict:
    """Pozun kendi hareketi: faz saniye, guc 0..1 (geçişte yavaşça devreye girer)."""
    if not ad or guc <= 0:
        return {}
    if ad == "yuru":
        s = math.sin(faz * math.tau * 1.7)  # ~1.7 adım çifti/sn
        return {k: v * guc for k, v in dict(bacak_sol_a=-20 * s, bacak_sag_a=20 * s,
                                              bacak_sol_b=-14 * max(0.0, s), bacak_sag_b=-14 * max(0.0, -s),
                                              kol_sol_a=16 * s, kol_sag_a=-16 * s,
                                              zipla=0.012 * abs(math.cos(faz * math.tau * 1.7))).items()}
    if ad == "selam":
        return {"kol_sag_b": 28 * math.sin(faz * math.tau * 2.2) * guc}
    if ad == "zipla":
        z = abs(math.sin(faz * math.tau * 1.25))
        return {"zipla": 0.06 * z * guc, "bacak_sol_b": 16 * z * guc, "bacak_sag_b": 16 * z * guc}
    raise ValueError(f"bilinmeyen salınım: {ad}")


@dataclass
class Govde:
    """Çizime hazır eklem konumları (karakter birimi, ayak tabanı y=0)."""
    kalca: tuple
    boyun: tuple                 # boyun dibi = omuz çizgisinin ortası
    bas: tuple                   # baş merkezi
    bas_aci: float               # derece, sağa eğilme +
    govde_aci: float
    omuz: dict                   # "sol"/"sag" → (x, y)
    dirsek: dict
    el: dict
    kalca_eklem: dict
    diz: dict
    ayak: dict
    bakis: tuple = (0.0, 0.0)
    oran: Oranlar = field(default_factory=Oranlar)


@dataclass
class Yuz:
    kas: float = 0.0
    kas_aci: float = 0.0
    goz: float = 1.0             # göz kırpınca 0'a iner
    mutlu_goz: float = 0.0
    egri: float = 0.25
    agiz_ac: float = 0.0         # ifade + konuşma birleşik açıklık (0..1)
    agiz_gen: float = 1.0
    agiz_bicim: str = "A"        # konuşmada ağız biçimi: A (geniş açık), E (yayvan), O (yuvarlak), M (kapalı), F
    konusuyor: bool = False


def _yon(aci_derece: float) -> tuple:
    """0 = aşağı, 90 = sağ, 180 = yukarı (saat yönünün tersi). Sağa eğilme saat yönündedir: açıdan çıkarılır."""
    r = math.radians(aci_derece)
    return math.sin(r), -math.cos(r)


def _ekle(p, d, uzunluk):
    return p[0] + d[0] * uzunluk, p[1] + d[1] * uzunluk


def govde_kur(p: dict, o: Oranlar = Oranlar()) -> Govde:
    """İleri kinematik: poz değerleri → eklem konumları. En alçak ayak y=0'a oturur (zıplama hariç)."""
    egim = p["govde"]
    yukari = _yon(180 - egim)                # gövdenin yukarı yönü
    sag = (yukari[1], -yukari[0])            # gövdeye dik, ekranın sağı
    kalca = (0.0, 0.0)
    boyun = _ekle(kalca, yukari, o.govde)
    bas_yon = _yon(180 - egim - p["bas"])
    bas = _ekle(boyun, bas_yon, o.boyun + o.bas_yaricap)
    omuz, dirsek, el, kal, diz, ayak = {}, {}, {}, {}, {}, {}
    for taraf, isaret in (("sol", -1), ("sag", 1)):
        omuz[taraf] = (boyun[0] + sag[0] * o.omuz_genislik * isaret, boyun[1] + sag[1] * o.omuz_genislik * isaret)
        a, b = p[f"kol_{taraf}_a"], p[f"kol_{taraf}_b"]
        d1 = _yon(isaret * a - egim)
        dirsek[taraf] = _ekle(omuz[taraf], d1, o.ust_kol)
        el[taraf] = _ekle(dirsek[taraf], _yon(isaret * (a + b) - egim), o.alt_kol)
        kal[taraf] = (kalca[0] + sag[0] * o.kalca_genislik * isaret, kalca[1] + sag[1] * o.kalca_genislik * isaret)
        a, b = p[f"bacak_{taraf}_a"], p[f"bacak_{taraf}_b"]
        diz[taraf] = _ekle(kal[taraf], _yon(isaret * a), o.ust_bacak)
        ayak[taraf] = _ekle(diz[taraf], _yon(isaret * (a + b)), o.alt_bacak)
    zemin = min(ayak["sol"][1], ayak["sag"][1]) - p.get("zipla", 0.0)
    kay = lambda q: (q[0], q[1] - zemin)
    kd = lambda d: {k: kay(v) for k, v in d.items()}
    return Govde(kalca=kay(kalca), boyun=kay(boyun), bas=kay(bas), bas_aci=egim + p["bas"], govde_aci=egim,
                 omuz=kd(omuz), dirsek=kd(dirsek), el=kd(el), kalca_eklem=kd(kal), diz=kd(diz), ayak=kd(ayak),
                 bakis=(p["bakis_x"], p["bakis_y"]), oran=o)


def goz_kirp(t: float, tohum: int = 7) -> float:
    """Göz kapağı çarpanı (1 açık, 0 kapalı): ~3 sn'de bir, düzensiz aralıkla, kısa kırpma."""
    aralik = 2.6
    i = int(t // aralik)
    kay = ((i * 7919 + tohum * 104729) % 1000) / 1000 * 1.4   # her aralıkta farklı an
    d = t - (i * aralik + kay)
    if 0 <= d < GOZ_KIRP_SN:
        return abs(1 - 2 * d / GOZ_KIRP_SN)
    return 1.0


def nefes(t: float) -> dict:
    """Durağan pozda bile canlılık: hafif nefes ve sallanma."""
    return {"govde": 1.2 * math.sin(t * 1.3), "bas": 1.5 * math.sin(t * 0.9 + 1.0),
            "kol_sol_b": 2 * math.sin(t * 1.3 + 0.5), "kol_sag_b": 2 * math.sin(t * 1.3 + 0.9)}
