"""Ses yönetmeni: her seslendirmede satır satır ElevenLabs ayarı, metin düzeltmesi ve tempo denetimi.

    python3 platform/ses/yonetmen.py plan satirlar.json [--tarz ciddi-analiz] [--ses eric] [--dil tr]   # kredi harcamaz
    python3 platform/ses/yonetmen.py tarzlar

Atilla (2026-10-21, 2026-10-25): "ses tonlama çok mekanik, hep aynı tonlama"; ElevenLabs'te uzman bir motor
her ses üretiminde kullanılsın. Neden tekdüze: her satır aynı ayarla ve tek başına okunuyordu. Yönetmen bunu
dört katmanda çözer, `seslendirme.uret` her ElevenLabs işinde kendiliğinden çağırır:

  1. Tarz (video türü, `seslendirme.tarz`): taban ayar ve tonların ne kadar açılabileceği. "ciddi-analiz"
     Atilla'nın denediği ciddi ayardan (stability 0.6, style 0.1, speed 0.92) başlar, vurguyu yarıya kısar.
  2. Rol ve duygu: ilk satır kanca, son satır kapanış, "?" soru, rakam ve yüzde bilgi, "!" vurgu; hasret,
     ölüm, gurbet gibi kelimeler duygusal. Rol, tarzın o rol için seçtiği tonu verir. Senaryoda satırın ya da
     sahnenin `ton`u varsa o geçerlidir (yönetmen yalnız türe göre ölçekler).
  3. Ses profili: her havuz sesinin kendi eğilimi (Eric hızlı ve parlak okur, George sıcak ama dağılabilir).
  4. Akış: komşu satırlar previous_text/next_text olarak gider; aynı ayarı iki satır üst üste almasın diye
     metinden türeyen küçük, sabit bir sapma eklenir (aynı metin hep aynı ayarı alır, önbellek bozulmaz).

Metin düzeltmesi yalnız sese gider (ekrandaki yazı değişmez): eksik son noktalama, uzun tire, yüzde işareti,
kısaltmalar. Üretimden sonra `denetle` her satırın temposunu (harf/sn) tarzın aralığıyla karşılaştırır;
sonuç `seslendirme.json` içinde `yonetmen` alanına, aykırılıklar kalite raporuna uyarı olarak gider.
Senaryoda `"seslendirme": {"yonetmen": false}` eski davranışı (tek ayar, önbellekteki eski satırlar) korur.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Tonun taban ayara eklediği fark. Tarzın `serbestlik` katsayısıyla çarpılır: ciddi işte vurgu yarım açılır.
TON_FARK = {
    "notr": {},
    "sakin": {"stability": 0.08, "style": -0.1, "speed": -0.03},
    "duygusal": {"stability": -0.12, "style": 0.15, "speed": -0.06},
    "vurgulu": {"stability": -0.1, "style": 0.2, "speed": -0.01},
    "enerjik": {"stability": -0.12, "style": 0.22, "speed": 0.06},
}

# Anlatım tarzları (video türüne göre). `taban`: voice_settings; `roller`: rol → ton; `tempo`: beklenen harf/sn aralığı (Türkçe ve
# Almanca anlatımda ölçülen ElevenLabs temposu ~13–17 harf/sn); `stil_ust`: style için tavan (yüksek style
# multilingual_v2'de dalgalanma ve tutarsızlık getirir).
TARZLAR = {
    "anlatim": {
        "not": "genel anlatım, varsayılan: sıcak ve sakin",
        "taban": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.25, "speed": 0.97},
        "serbestlik": 1.0, "stil_ust": 0.5, "tempo": (11.5, 17.5),
        "roller": {"kanca": "vurgulu", "govde": "notr", "bilgi": "sakin", "soru": "vurgulu", "kapanis": "sakin"},
    },
    "ciddi-analiz": {
        "not": "haber, analiz, siyaset: ağırbaşlı, düz, vurgu yalnız kanca ve kapanış sorusunda",
        "taban": {"stability": 0.6, "similarity_boost": 0.8, "style": 0.1, "speed": 0.95},  # 0.92 denendi: Atilla "bazı yerlerde çok bekliyor"
        "serbestlik": 0.5, "stil_ust": 0.25, "tempo": (11.0, 16.0),
        "roller": {"kanca": "vurgulu", "govde": "notr", "bilgi": "sakin", "soru": "vurgulu", "kapanis": "vurgulu"},
    },
    "belgesel": {
        "not": "göç hikâyesi, tarih, anı: yavaş, sıcak, duyguya yer bırakan",
        "taban": {"stability": 0.52, "similarity_boost": 0.8, "style": 0.22, "speed": 0.9},
        "serbestlik": 0.8, "stil_ust": 0.45, "tempo": (10.0, 15.5),
        "roller": {"kanca": "duygusal", "govde": "notr", "bilgi": "sakin", "soru": "duygusal", "kapanis": "duygusal"},
    },
    "sicak-reklam": {
        "not": "marka, restoran, ürün: gülümseyen, davetkâr",
        "taban": {"stability": 0.42, "similarity_boost": 0.8, "style": 0.38, "speed": 1.0},
        "serbestlik": 1.0, "stil_ust": 0.6, "tempo": (12.0, 18.0),
        "roller": {"kanca": "enerjik", "govde": "notr", "bilgi": "notr", "soru": "vurgulu", "kapanis": "vurgulu"},
    },
    "enerjik-sosyal": {
        "not": "kısa sosyal medya videosu: canlı, hızlı",
        "taban": {"stability": 0.36, "similarity_boost": 0.8, "style": 0.48, "speed": 1.05},
        "serbestlik": 1.1, "stil_ust": 0.7, "tempo": (13.0, 19.5),
        "roller": {"kanca": "enerjik", "govde": "notr", "bilgi": "vurgulu", "soru": "enerjik", "kapanis": "enerjik"},
    },
}
VARSAYILAN_TARZ = "anlatim"

# Ses profilleri (voice_id → taban ayara eklenen fark). Kaynak: 2026-10-19 Türkçe ve 2026-10-25 ciddi ses
# denemeleri. Yeni ses havuza girince buraya da kısa bir satır eklenir; yoksa fark sıfırdır.
SES_PROFILLERI = {
    "cjVigY5qzO86Huf0OWal": {"ad": "eric", "fark": {"speed": -0.03, "style": -0.05}, "not": "hızlı ve parlak okur; biraz frenlenir"},
    "JBFqnCBsd6RMkjVDRZzb": {"ad": "george", "fark": {"stability": 0.03}, "not": "sıcak; düşük stability'de dağılır"},
    "onwK4e9ZLuTAKqWW03F9": {"ad": "daniel", "fark": {"style": -0.03}, "not": "haber spikeri tınısı, kendiliğinden ciddi"},
    "nPczCjzI2devNBz1zQrb": {"ad": "brian", "fark": {"speed": -0.02}, "not": "derin, anlatıcı"},
    "hpp4J3VqNfWAUOO0d1Us": {"ad": "bella", "fark": {"stability": 0.04, "style": -0.04}, "not": "parlak; fazla style'da yapay gülümser"},
    "TX3LPaxmHKxFdv7VOQHJ": {"ad": "liam", "fark": {"stability": 0.03}, "not": "enerjik; kendi temposu hızlı"},
    "XrExE9yKIg1WjnnlVkGX": {"ad": "matilda", "fark": {}, "not": "dengeli"},
    "2LDViBMBCwziwFCATi3r": {"ad": "turk-haber", "fark": {"style": -0.05}, "not": "üretilmiş ses; style'a hassas"},
}

SINIR = {"stability": (0.25, 0.85), "similarity_boost": (0.5, 0.95), "style": (0.0, 1.0), "speed": (0.8, 1.15)}

DUYGU = {
    "tr": r"hasret|özlem|gurbet|ölüm|öldü|kayb|yalnız|ağla|gözyaş|acı|veda|anne|baba|çocukluğ|memleket|hatıra|unutul|kırgın",
    "de": r"sehnsucht|heimweh|tod|starb|verlor|einsam|weinen|träne|schmerz|abschied|mutter|vater|kindheit|heimat|erinner|vergess",
}
VURGU = {
    "tr": r"\b(ama|fakat|oysa|asla|hiç|tam|sadece|yalnızca|ilk kez|şimdi|bugün)\b",
    "de": r"\b(aber|doch|niemals|nie|genau|nur|erstmals|jetzt|heute)\b",
}
KISALTMA = {
    "tr": {"vb.": "ve benzeri", "vs.": "vesaire", "örn.": "örneğin", "yy.": "yüzyıl", "Dr.": "Doktor", "Prof.": "Profesör"},
    "de": {"z. B.": "zum Beispiel", "z.B.": "zum Beispiel", "bzw.": "beziehungsweise", "usw.": "und so weiter",
           "ca.": "circa", "Nr.": "Nummer", "Dr.": "Doktor", "d. h.": "das heißt"},
}


def _sinirla(ad: str, x: float) -> float:
    lo, hi = SINIR[ad]
    return round(min(hi, max(lo, x)), 3)


def duzelt(metin: str, dil: str = "tr", uc_nokta: int = 0) -> str:
    """Sese giden metin: eksik son noktalama (yoksa cümle soru gibi yükselir), uzun tire → virgül, yüzde, kısaltma.

    Duraklama kontrolü (Atilla 2026-10-25): satır içindeki "..." ElevenLabs'te hem 1 sn'yi aşan bekleme ("bazı
    yerlerde çok bekliyor") hem de cümle bitişi gibi düşen ses verir ("Jetzt richten sich die Blicke ... nach
    Berlin" iki cümle gibi okundu). O yüzden virgüle döner; durak gerekiyorsa satır ikiye bölünür. Bir tarz
    bilerek izin verirse (`uc_nokta`) ilk o kadarı kalır.
    """
    m = re.sub(r"\s+", " ", metin).strip()
    m = re.sub(r"\.{3,}|…", "…", m)
    kalan = [uc_nokta]

    def _uc(x):
        son = x.end() >= len(m.rstrip())
        if son:
            return "."
        if kalan[0] > 0:
            kalan[0] -= 1
            return "..."
        # Almancada küçük harfle süren cümlenin ortasına virgül girmez ("die Blicke nach Berlin")
        if dil == "de" and re.match(r"\s*[a-zäöüß]", m[x.end():]):
            return " "
        return ","
    m = re.sub(r"…", _uc, m)
    m = re.sub(r",\s*,", ",", m)
    m = re.sub(r"\s+([,.!?])", r"\1", re.sub(r" {2,}", " ", m))
    for k, v in KISALTMA.get(dil, {}).items():
        m = re.sub(r"(?<!\w)" + re.escape(k) + r"(?=\s|$)", v, m)
    if dil == "de":
        m = re.sub(r"(\d+(?:[.,]\d+)?)\s?%", r"\1 Prozent", m)
    else:
        m = re.sub(r"%\s?(\d+(?:[.,]\d+)?)", r"yüzde \1", m)
        m = re.sub(r"(\d+(?:[.,]\d+)?)\s?%", r"yüzde \1", m)
    m = re.sub(r"\s*[—–]\s*", ", ", m).replace(" ,", ",")
    if m and m[-1] not in ".!?…\"'»”":
        m += "."
    return m


def rol(i: int, n: int, metin: str) -> str:
    """kanca (ilk satır), kapanis (son satır), soru, bilgi (rakam, yüzde), govde."""
    if metin.rstrip().endswith("?"):
        return "soru" if 0 < i < n - 1 or n == 1 else ("kanca" if i == 0 else "kapanis")
    if i == 0 and n > 1:
        return "kanca"
    if i == n - 1 and n > 1:
        return "kapanis"
    if re.search(r"\d", metin):
        return "bilgi"
    return "govde"


def duygu(metin: str, dil: str = "tr") -> str | None:
    k = metin.lower()
    if re.search(DUYGU.get(dil, DUYGU["tr"]), k):
        return "duygusal"
    if "!" in metin:
        return "vurgulu"
    return None


def _sapma(metin: str) -> tuple[float, float]:
    """Metinden türeyen, -1..1 arası iki sabit sayı: aynı metin hep aynı ayarı alır (önbellek anahtarı sabit)."""
    h = hashlib.sha256(metin.encode("utf-8")).digest()
    return h[0] / 127.5 - 1, h[1] / 127.5 - 1


def ayar(metin: str, tarz: str, ton: str, ses_id: str | None, uzunluk: int) -> dict:
    t = TARZLAR[tarz]
    vs = dict(t["taban"])
    for k, v in TON_FARK[ton].items():
        vs[k] = vs[k] + v * t["serbestlik"]
    for k, v in (SES_PROFILLERI.get(ses_id or "", {}).get("fark") or {}).items():
        vs[k] = vs[k] + v
    if uzunluk < 30:  # kısa satır ağırlık ister: biraz yavaş
        vs["speed"] -= 0.02
    a, b = _sapma(metin)
    vs["stability"] += 0.03 * a
    vs["style"] = min(t["stil_ust"], vs["style"] + 0.03 * b)
    out = {k: _sinirla(k, v) for k, v in vs.items()}
    out["use_speaker_boost"] = True
    return out


def yonet(satirlar: list[dict], tarz: str | None = None, ses_id: str | None = None, dil: str = "tr") -> list[dict]:
    """Satır başına karar: {"metin" (sese giden), "rol", "ton", "neden", "voice_settings", "onceki", "sonraki"}.

    Satırın `ton`u (senaryodan) önce gelir; yoksa duygu, o da yoksa tarzın rol tonu.
    """
    tarz = tarz or VARSAYILAN_TARZ
    if tarz not in TARZLAR:
        raise ValueError(f"bilinmeyen tarz: {tarz} ({', '.join(TARZLAR)})")
    metinler = [duzelt(s["metin"], dil, TARZLAR[tarz].get("uc_nokta", 0)) for s in satirlar]
    out = []
    for i, (s, m) in enumerate(zip(satirlar, metinler)):
        r = rol(i, len(satirlar), m)
        d = duygu(m, dil)
        if s.get("ton"):
            ton, neden = s["ton"], "senaryo"
        elif d:
            ton, neden = d, "duygu"
        else:
            ton, neden = TARZLAR[tarz]["roller"][r], "rol"
        if ton not in TON_FARK:
            raise ValueError(f"bilinmeyen ton: {ton} ({', '.join(TON_FARK)})")
        out.append({"id": s["id"], "metin": m, "rol": r, "ton": ton, "neden": neden,
                    "voice_settings": ayar(m, tarz, ton, ses_id, len(m)),
                    "onceki": metinler[i - 1] if i else None,
                    "sonraki": metinler[i + 1] if i + 1 < len(metinler) else None})
    return out


# Satır içinde bundan uzun sessizlik "bekliyor" diye duyulur.
EN_UZUN_DURAK = {"ciddi-analiz": 0.5, "belgesel": 0.7, "enerjik-sosyal": 0.4}


def duraklar(wav: Path, esik_db: float = -40.0, en_kisa: float = 0.35) -> list[float]:
    """Dosya içindeki sessizliklerin süreleri (sn), ffmpeg silencedetect ile."""
    import subprocess
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", f"silencedetect=n={esik_db}dB:d={en_kisa}",
                        "-f", "null", "-"], capture_output=True, text=True)
    return [round(float(x), 2) for x in re.findall(r"silence_duration: ([\d.]+)", r.stderr)]


def duraklari_kisalt(wav: Path, ust: float, hizalama: Path | None = None, esik_db: float = -40.0) -> list[list[float]]:
    """Satır içinde `ust` sn'den uzun sessizlikleri `ust`e indirir (cümle arası 0.9 sn bekleme "çok bekliyor" diye
    duyuldu). Kesilen parça sessizliğin ortasından alınır; harf zamanları (`hizalama`) aynı kaydırmayla düzeltilir.
    Dönüş: kesilen aralıklar [[başlangıç, süre], ...] (sn, kesimden önceki zamanda)."""
    import array
    import wave
    with wave.open(str(wav), "rb") as w:
        sr, ham = w.getframerate(), w.readframes(w.getnframes())
    a = array.array("h", ham)
    pencere = sr // 100  # 10 ms
    esik = 32768 * 10 ** (esik_db / 20)
    sessiz = [max((abs(x) for x in a[i:i + pencere]), default=0) < esik for i in range(0, len(a), pencere)]
    kesimler, i = [], 0
    while i < len(sessiz):
        if not sessiz[i]:
            i += 1
            continue
        j = i
        while j < len(sessiz) and sessiz[j]:
            j += 1
        sure = (j - i) * pencere / sr
        if i > 0 and j < len(sessiz) and sure > ust:  # baştaki ve sondaki sessizlik cila zincirinde kırpılır
            fazla = sure - ust
            kesimler.append([round(i * pencere / sr + ust / 2, 3), round(fazla, 3)])
        i = j
    if not kesimler:
        return []
    yeni, onceki = array.array("h"), 0
    for bas, fazla in kesimler:
        b = int(bas * sr)
        yeni.extend(a[onceki:b])
        onceki = b + int(fazla * sr)
    yeni.extend(a[onceki:])
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(yeni.tobytes())
    if hizalama and hizalama.exists():
        h = json.loads(hizalama.read_text(encoding="utf-8"))

        def kay(t):
            for bas, fazla in reversed(kesimler):
                if t >= bas + fazla:
                    return round(t - sum(f for b, f in kesimler if b <= bas), 4)
                if t > bas:  # kesilen sessizliğin içi: kesimin başına
                    return round(bas - sum(f for b, f in kesimler if b < bas), 4)
            return t
        h["bas"], h["son"] = [kay(t) for t in h["bas"]], [kay(t) for t in h["son"]]
        hizalama.write_text(json.dumps(h, ensure_ascii=False), encoding="utf-8")
    return kesimler


# Almanca kelimeler uzun ve ünsüz kümeli: aynı doğal tempo daha çok harf/sn eder (2026-10-25 Eric ölçümü).
DIL_TEMPO = {"de": 1.15}


def denetle(kayit_satirlari: list[dict], tarz: str | None = None, klasor: Path | None = None,
            dil: str = "tr") -> list[dict]:
    """Üretilmiş satırların temposu (harf/sn, boşluksuz) ve satır içi duraklar: aykırılar uyarı olur."""
    tarz = tarz or VARSAYILAN_TARZ
    k = DIL_TEMPO.get(dil, 1.0)
    lo, hi = (round(x * k, 1) for x in TARZLAR[tarz]["tempo"])
    durak_ust = EN_UZUN_DURAK.get(tarz, 0.55)
    uyarilar = []
    for s in kayit_satirlari:
        if klasor and (klasor / f"{s['id']}.wav").exists():
            uzun = [d for d in duraklar(klasor / f"{s['id']}.wav") if d > durak_ust + 0.08]
            if uzun:
                s["uzun_durak"] = uzun
                uyarilar.append({"id": s["id"], "sorun": "uzun durak", "tempo": max(uzun), "aralik": [0, durak_ust]})
        harf = len(re.sub(r"[\s\W]", "", s["metin"]))
        if not s.get("sure") or harf < 12:  # çok kısa satırda tempo ölçülmez
            continue
        hiz = harf / s["sure"]
        s["tempo"] = round(hiz, 1)
        if hiz > hi * 1.1:
            uyarilar.append({"id": s["id"], "sorun": "hızlı", "tempo": round(hiz, 1), "aralik": [lo, hi]})
        elif hiz < lo * 0.85:
            uyarilar.append({"id": s["id"], "sorun": "yavaş", "tempo": round(hiz, 1), "aralik": [lo, hi]})
    return uyarilar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("plan", help="satırların rol, ton ve ayarlarını gösterir (kredi harcamaz)")
    p.add_argument("satirlar"); p.add_argument("--tarz"); p.add_argument("--ses"); p.add_argument("--dil", default="tr")
    alt.add_parser("tarzlar")
    a = ap.parse_args(argv)
    if a.komut == "tarzlar":
        for ad, t in TARZLAR.items():
            b = t["taban"]
            print(f"{ad:15} stab {b['stability']:.2f} style {b['style']:.2f} speed {b['speed']:.2f}  {t['not']}")
        return 0
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import seslendirme
    veri = json.loads(Path(a.satirlar).read_text(encoding="utf-8"))
    sb = veri.get("seslendirme") or veri
    satirlar = [{"id": x["id"], "metin": x.get("okunus", x["metin"]), "ton": x.get("ton")} for x in sb["satirlar"]]
    ses_id = seslendirme.eleven_ayar({"ses": a.ses or sb.get("ses"), "dil": a.dil})["ses"]
    for k in yonet(satirlar, a.tarz or sb.get("tarz"), ses_id, a.dil):
        v = k["voice_settings"]
        print(f"{k['id']:6} {k['rol']:8} {k['ton']:9} ({k['neden']:7}) stab {v['stability']:.2f} style {v['style']:.2f} "
              f"speed {v['speed']:.2f}  {k['metin'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
