"""Seslendirme adımı: metin satırlarından teslime hazır, 48 kHz WAV dosyaları.

    python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme
    python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme --saglayici elevenlabs --ses <voice_id>
    python3 platform/ses/seslendirme.py sesler
    python3 platform/ses/seslendirme.py kullanim          # ElevenLabs'te harcanan karakterler (iş başına)
    python3 platform/ses/seslendirme.py kredi             # ElevenLabs hesabında kalan kredi ve plan

`satirlar.json`: {"satirlar": [{"id": "v0", "metin": "Her gün, sadece yüzde bir daha iyi ol."}, ...]}
Her satır `<id>.wav` olur; aynı klasöre süreleri içeren `seslendirme.json` yazılır (kurgu zamanlaması buradan okur).

Sağlayıcılar (`SAGLAYICILAR`):
  otomatik    varsayılan: elevenlabs (Atilla, 2026-10-19: "diğer sesler çok mekanik"). Anahtar yoksa, ElevenLabs'e
              ulaşılamazsa ya da kalan kredi işe yetmezse bütün iş Piper ile üretilir (render durmaz);
              `seslendirme.json`'a `yedek` yazılır, kalite raporu bunu uyarı olarak gösterir.
              Senaryo `"seslendirme": {"saglayici": "piper"}` derse o iş bilerek Piper'la yapılır.
  piper       yerel, ücretsiz. Ses modeli ilk kullanımda GitHub'dan indirilir (huggingface.co kapalı olabilir).
  elevenlabs  ücretli API. ELEVENLABS_API_KEY yoksa açık bir hatayla durur. Her satır önbelleğe yazılır:
              aynı metin + ses + ayar ikinci kez kredi harcamaz. Harcanan karakterler kullanim.jsonl'a yazılır.
              İş başlamadan önce kalan kredi sorulur; önbellekte olmayan satırlar sığmıyorsa tek kredi harcanmaz.
Her iki sağlayıcının ham çıktısı aynı "cila" zincirinden geçer: gövde temizliği, varlık, yumuşak
sıkıştırma, satır başına -16 LUFS ve soxr ile 48 kHz'e çevirme.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telaffuz  # noqa: E402

ORNEKLEME = 48000
HEDEF_LUFS = -16.0

# Piper sesleri: lisans ticari işte kullanılabilirliği belirler (lisans kapısı).
PIPER_SESLERI = {
    "fahrettin": {"dil": "tr", "kod": "tr_TR", "lisans": "CC0", "ticari": True, "cinsiyet": "erkek"},
    "fettah": {"dil": "tr", "kod": "tr_TR", "lisans": "CC0", "ticari": True, "cinsiyet": "erkek"},
    "dfki": {"dil": "tr", "kod": "tr_TR", "lisans": "CC BY-NC-SA 4.0", "ticari": False, "cinsiyet": "erkek"},
    "thorsten": {"dil": "de", "kod": "de_DE", "lisans": "CC0", "ticari": True, "cinsiyet": "erkek"},
    "kerstin": {"dil": "de", "kod": "de_DE", "lisans": "CC0", "ticari": True, "cinsiyet": "kadin", "kalite": "low"},  # yalnız low var
}
PIPER_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-{kod}-{ses}-{kalite}.tar.bz2"
PIPER_ONBELLEK = Path(os.environ.get("PIPER_SES_DIZINI", Path.home() / ".cache" / "studyo" / "piper"))

# Ücretsiz ve Starter planda pcm_44100 yok (403 "only available on the Pro tier"); mp3 indirilip ffmpeg ile açılır.
# with-timestamps: aynı kredi, ses + harf zamanları (karakter şablonlarında ağız senkronu için, bkz. hizalama_yaz).
ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{ses}/with-timestamps?output_format=mp3_44100_128"
ELEVEN_ABONELIK_URL = "https://api.elevenlabs.io/v1/user/subscription"
ELEVEN_MODEL = "eleven_multilingual_v2"
# Dil zorlaması (language_code) yalnız bu modellerde var; multilingual_v2 dili metinden anlar, alanı görürse reddeder.
ELEVEN_DIL_ZORLAYAN = ("eleven_turbo_v2_5", "eleven_flash_v2_5")
ELEVEN_AYAR = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True}
# Satır tonu (senaryoda satır ya da sahne başına `ton`): bütün satırlar aynı ayarla okununca anlatım tekdüze
# kalır. Düşük stability + yüksek style daha duygulu, speed (0.7–1.2) temposu. Ton verilen işte her satır
# komşu satırları previous_text/next_text olarak da gönderir; ElevenLabs cümleyi akışın içinde tonlar.
ELEVEN_TONLAR = {
    "notr": {},
    "sakin": {"stability": 0.55, "style": 0.15, "speed": 0.93},
    "duygusal": {"stability": 0.3, "style": 0.55, "speed": 0.88},
    "vurgulu": {"stability": 0.35, "style": 0.6, "speed": 0.95},
    "enerjik": {"stability": 0.3, "style": 0.65, "speed": 1.06},
}
# Varsayılan sesler: ElevenLabs'in hazır, çok dilli sesleri (multilingual_v2 ile Türkçe ve Almanca okur).
# Dile özel seçim (ör. e-kitap testinde beğenilen Almanca ses) ELEVEN_DIL_SESLERI'ne, kanal ya da müşteri
# sesi senaryonun `seslendirme.ses` alanına (voice_id) yazılır. Ortam: ELEVENLABS_VOICE_ID[_TR|_DE].
ELEVEN_SESLERI = {
    "erkek": {"ad": "George", "id": "JBFqnCBsd6RMkjVDRZzb"},
    "kadin": {"ad": "Matilda", "id": "XrExE9yKIg1WjnnlVkGX"},
}
ELEVEN_DIL_SESLERI: dict[str, dict[str, dict]] = {
    "tr": {"erkek": ELEVEN_SESLERI["erkek"]},  # Atilla 2026-10-19 Türkçe denemede George'u seçti
}
# Senaryoda `seslendirme.ses` olarak adla seçilebilen sesler (stüdyo ses havuzu). Hepsi ücretsiz planda çalışır;
# ElevenLabs kütüphanesinden eklenen sesler (Ömer, Cahit...) ücretsiz planda 402/400 verir, buraya girmez.
ELEVEN_ADLI_SESLER = {
    "george": {"id": "JBFqnCBsd6RMkjVDRZzb", "cinsiyet": "erkek", "not": "sıcak anlatıcı; Türkçe anlatım varsayılanı"},
    "turk-haber": {"id": "2LDViBMBCwziwFCATi3r", "cinsiyet": "erkek", "not": "İstanbul aksanlı haber sesi (hesapta üretilmiş ses)"},
    "bella": {"id": "hpp4J3VqNfWAUOO0d1Us", "cinsiyet": "kadin", "not": "parlak, sıcak; Almanca reklamlarda kullanıldı"},
    "matilda": {"id": "XrExE9yKIg1WjnnlVkGX", "cinsiyet": "kadin", "not": "bilgilendirici; kadın varsayılanı"},
    "liam": {"id": "TX3LPaxmHKxFdv7VOQHJ", "cinsiyet": "erkek", "not": "enerjik, sosyal medya"},
}


def _onbellek_koku() -> Path:
    """Ücretli seslerin önbelleği. Proje klasörü varsa orada (bütün oturumlar paylaşır), yoksa ~/.cache."""
    if os.environ.get("STUDYO_SES_ONBELLEK"):
        return Path(os.environ["STUDYO_SES_ONBELLEK"])
    proje = Path("/mnt/project-files")
    if proje.is_dir() and os.access(proje, os.W_OK):
        return proje / ".onbellek" / "ses"
    return Path.home() / ".cache" / "studyo" / "ses"

# Konuşmayı netleştiren zincir (ffmpeg). Sıra: gövde temizliği → çamur → varlık → hava → sıkıştırma.
CILA = ",".join([
    "highpass=f=80",
    "equalizer=f=250:t=q:w=1.2:g=-2.5",
    "equalizer=f=3200:t=q:w=1.0:g=3",
    "treble=g=2:f=9000",
    "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2",
    "silenceremove=start_periods=1:start_threshold=-50dB",
    "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse",
])


class SeslendirmeHatasi(RuntimeError):
    pass


# ---------- sağlayıcılar: (metin, ayar) -> (pcm int16 bayt, örnekleme hızı) ----------
def piper(metin: str, ayar: dict) -> tuple[bytes, int]:
    ses = ayar.get("ses") or "fahrettin"
    bilgi = PIPER_SESLERI.get(ses)
    if bilgi is None:
        raise SeslendirmeHatasi(f"bilinmeyen Piper sesi: {ses} (seçenekler: {', '.join(PIPER_SESLERI)})")
    if ayar.get("ticari", True) and not bilgi["ticari"]:
        raise SeslendirmeHatasi(f"{ses} sesi {bilgi['lisans']} lisanslı; ticari işte kullanılamaz")
    try:
        import numpy as np
        import sherpa_onnx
    except ImportError as e:
        raise SeslendirmeHatasi("Piper için `pip install sherpa-onnx numpy` gerekli") from e
    klasor = piper_indir(ses)
    model = next(klasor.glob("*.onnx"))
    cfg = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
            model=str(model), tokens=str(klasor / "tokens.txt"), data_dir=str(klasor / "espeak-ng-data"),
            length_scale=float(ayar.get("hiz", 1.0)) ** -1,  # hız > 1 daha hızlı konuşur
            noise_scale=float(ayar.get("canlilik", 0.6)), noise_scale_w=0.7)))
    sonuc = sherpa_onnx.OfflineTts(cfg).generate(metin, sid=0, speed=1.0)
    x = np.clip(np.asarray(sonuc.samples), -1, 1)
    return (x * 32767).astype("<i2").tobytes(), sonuc.sample_rate


def piper_indir(ses: str) -> Path:
    kod, kalite = PIPER_SESLERI[ses]["kod"], PIPER_SESLERI[ses].get("kalite", "medium")
    hedef = PIPER_ONBELLEK / f"vits-piper-{kod}-{ses}-{kalite}"
    if any(hedef.glob("*.onnx")):
        return hedef
    PIPER_ONBELLEK.mkdir(parents=True, exist_ok=True)
    url = PIPER_URL.format(kod=kod, ses=ses, kalite=kalite)
    try:
        with urllib.request.urlopen(url, timeout=300) as r:
            veri = r.read()
    except urllib.error.URLError as e:
        raise SeslendirmeHatasi(f"Piper sesi indirilemedi: {url} ({e})") from e
    with tarfile.open(fileobj=io.BytesIO(veri), mode="r:bz2") as tar:
        tar.extractall(PIPER_ONBELLEK, filter="data") if sys.version_info >= (3, 12) else tar.extractall(PIPER_ONBELLEK)
    return hedef


def eleven_ayar(ayar: dict) -> dict:
    """Ayarı istek parametrelerine çözer: ses kimliği, model, dil, ses ayarları.

    `ses` stüdyo havuzundan bir adsa (`ELEVEN_ADLI_SESLER`: george, turk-haber, bella...) onun kimliği,
    bir ElevenLabs voice_id ise o kullanılır. Piper ses adıysa (senaryolar `kerstin` gibi Piper adları
    taşır) dili ve cinsiyeti alınır, o dilin varsayılan ElevenLabs sesi seçilir.
    """
    ses = ayar.get("ses") or ""
    if ses.lower() in ELEVEN_ADLI_SESLER:
        ses = ELEVEN_ADLI_SESLER[ses.lower()]["id"]
    piper_bilgi = PIPER_SESLERI.get(ses)
    dil = ayar.get("dil") or (piper_bilgi or {}).get("dil") or "tr"
    if not ses or piper_bilgi:
        cinsiyet = ayar.get("cinsiyet") or (piper_bilgi or {}).get("cinsiyet") or "erkek"
        ses = (os.environ.get(f"ELEVENLABS_VOICE_ID_{dil.upper()}") or os.environ.get("ELEVENLABS_VOICE_ID")
               or ELEVEN_DIL_SESLERI.get(dil, {}).get(cinsiyet, {}).get("id") or ELEVEN_SESLERI[cinsiyet]["id"])
    model = ayar.get("model") or ELEVEN_MODEL
    ton = ayar.get("ton")
    if ton and ton not in ELEVEN_TONLAR:
        raise SeslendirmeHatasi(f"bilinmeyen ton: {ton} ({', '.join(ELEVEN_TONLAR)})")
    e = {"ses": ses, "model": model, "dil": dil,
         "voice_settings": {**ELEVEN_AYAR, **ELEVEN_TONLAR.get(ton or "notr", {}), **(ayar.get("voice_settings") or {})}}
    for k in ("onceki", "sonraki"):  # yalnız varsa: tonsuz işlerin önbellek anahtarı değişmez
        if ayar.get(k):
            e[k] = ayar[k]
    return e


def elevenlabs(metin: str, ayar: dict, ag=None) -> tuple[bytes, int, dict | None]:
    anahtar = os.environ.get("ELEVENLABS_API_KEY", "")
    if not anahtar:
        raise SeslendirmeHatasi("ELEVENLABS_API_KEY ortam değişkeni yok; anahtar eklenene kadar --saglayici piper kullanın")
    e = eleven_ayar(ayar)
    govde = {"text": metin, "model_id": e["model"], "voice_settings": e["voice_settings"]}
    if e.get("onceki"):
        govde["previous_text"] = e["onceki"]
    if e.get("sonraki"):
        govde["next_text"] = e["sonraki"]
    if e["model"] in ELEVEN_DIL_ZORLAYAN:
        govde["language_code"] = e["dil"]
    istek = urllib.request.Request(ELEVEN_URL.format(ses=e["ses"]), data=json.dumps(govde).encode("utf-8"), method="POST",
                                   headers={"xi-api-key": anahtar, "Content-Type": "application/json"})
    try:
        cevap = (ag or _ac)(istek)
    except urllib.error.HTTPError as h:
        raise SeslendirmeHatasi(f"ElevenLabs {h.code}: {h.read()[:300].decode('utf-8', 'replace')}") from h
    except (urllib.error.URLError, OSError) as h:
        raise SeslendirmeHatasi(f"ElevenLabs'e ulaşılamadı ({h}); ağ izni: api.elevenlabs.io") from h
    mp3, hizalama = cevap, None
    if cevap[:1] == b"{":  # with-timestamps: {"audio_base64", "alignment": {characters, character_*_times_seconds}}
        d = json.loads(cevap)
        mp3 = base64.b64decode(d["audio_base64"])
        h = d.get("alignment") or d.get("normalized_alignment")
        if h and h.get("characters"):
            hizalama = {"karakterler": h["characters"], "bas": h["character_start_times_seconds"],
                        "son": h["character_end_times_seconds"]}
    return mp3_coz(mp3), 44100, hizalama


def mp3_coz(mp3: bytes, sr: int = 44100) -> bytes:
    """mp3 → mono int16 PCM (ffmpeg)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1",
                        "-ar", str(sr), "pipe:1"], input=mp3, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise SeslendirmeHatasi(f"ElevenLabs sesi çözülemedi: {r.stderr[:200].decode('utf-8', 'replace')}")
    return r.stdout


def eleven_kredi(ag=None) -> dict:
    """Hesabın planı ve kalan kredisi. Anahtar yoksa ya da hesap sorulamazsa SeslendirmeHatasi."""
    anahtar = os.environ.get("ELEVENLABS_API_KEY", "")
    if not anahtar:
        raise SeslendirmeHatasi("ELEVENLABS_API_KEY ortam değişkeni yok")
    istek = urllib.request.Request(ELEVEN_ABONELIK_URL, headers={"xi-api-key": anahtar})
    try:
        d = json.loads((ag or _ac)(istek))
    except urllib.error.HTTPError as h:
        raise SeslendirmeHatasi(f"ElevenLabs hesabı sorulamadı ({h.code}): {h.read()[:200].decode('utf-8', 'replace')}") from h
    except (urllib.error.URLError, OSError, ValueError) as h:
        raise SeslendirmeHatasi(f"ElevenLabs'e ulaşılamadı ({h}); ağ izni: api.elevenlabs.io") from h
    limit, harcanan = int(d.get("character_limit") or 0), int(d.get("character_count") or 0)
    return {"plan": d.get("tier"), "limit": limit, "harcanan": harcanan, "kalan": max(0, limit - harcanan),
            "yenilenme": d.get("next_character_count_reset_unix")}


def _ac(istek) -> bytes:
    with urllib.request.urlopen(istek, timeout=120) as r:
        return r.read()


SAGLAYICILAR = {"piper": piper, "elevenlabs": elevenlabs}
UCRETLI = {"elevenlabs"}  # satır önbelleği ve karakter kaydı bunlar için
KREDI = {"elevenlabs": eleven_kredi}  # iş başlamadan kalan kredi sorgusu
VARSAYILAN = "elevenlabs"
YEDEK = "piper"


class KrediYetersiz(SeslendirmeHatasi):
    pass


def saglayici_coz(saglayici: str | None, ayar: dict | None = None) -> str:
    """`otomatik` (ya da boş): işin istediği sağlayıcı (`ayar["saglayici"]`, senaryodan gelir), yoksa ElevenLabs."""
    if saglayici in (None, "", "otomatik"):
        return (ayar or {}).get("saglayici") or VARSAYILAN
    return saglayici


def senaryodan(s: dict, cikti: Path, saglayici: str | None = "otomatik", ses: str | None = None) -> dict:
    """Bir senaryonun `seslendirme.satirlar`ını seslendirir; şablonların ortak girişi.

    `okunus` varsa ekrandaki metin yerine o okunur. Ses ve dil komut satırından, yoksa senaryonun
    `seslendirme.ses` / `seslendirme.dil` (ya da `dil`) alanından; sağlayıcı `seslendirme.saglayici`dan gelir.
    """
    sb = s.get("seslendirme") or {}
    satirlar = [{"id": x["id"], "metin": x.get("okunus", x["metin"]), **({"ton": x["ton"]} if x.get("ton") else {})}
                for x in sb.get("satirlar", [])]
    dil = sb.get("dil") or (s.get("dil") if s.get("dil") != "sahne" else None)  # ortak sahne dilinde "dil" biçimdir
    ayar = {"ses": ses or sb.get("ses"), "dil": dil, "saglayici": sb.get("saglayici"),
            "telaffuz": sb.get("telaffuz"), "klasor": s.get("_klasor")}
    return uret(satirlar, Path(cikti), saglayici, ayar)


def _onbellek_anahtari(saglayici: str, metin: str, ayar: dict) -> str:
    cozulmus = eleven_ayar(ayar) if saglayici == "elevenlabs" else ayar
    ham = json.dumps({"s": saglayici, "m": metin, "a": cozulmus}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()[:32]


def _onbellek_yolu(saglayici: str, metin: str, ayar: dict) -> Path:
    return _onbellek_koku() / saglayici / f"{_onbellek_anahtari(saglayici, metin, ayar)}.wav"


def satir_ayarlari(satirlar: list[dict], ayar: dict) -> list[dict]:
    """Satır başına ayar: işte bir satırın `ton`u varsa her satır kendi tonunu ve komşu satırları alır."""
    if not any(s.get("ton") for s in satirlar):
        return [ayar] * len(satirlar)
    out = []
    for i, s in enumerate(satirlar):
        a = dict(ayar, ton=s.get("ton") or ayar.get("ton"))
        a["onceki"] = satirlar[i - 1]["metin"] if i else None
        a["sonraki"] = satirlar[i + 1]["metin"] if i + 1 < len(satirlar) else None
        out.append(a)
    return out


def kredi_kontrol(saglayici: str, satirlar: list[dict], ayar: dict | list[dict]) -> dict | None:
    """Önbellekte olmayan satırların kredisi hesapta kalandan fazlaysa iş başlamadan durur (1 karakter ≈ 1 kredi).

    Bütün satırlar önbellekteyse hesap sorulmaz. Dönüş: {"gerekli", "kalan", "plan"} ya da None.
    """
    ayarlar = ayar if isinstance(ayar, list) else [ayar] * len(satirlar)
    gerekli = sum(len(s["metin"]) for s, a in zip(satirlar, ayarlar) if not _onbellek_yolu(saglayici, s["metin"], a).exists())
    if not gerekli or saglayici not in KREDI:
        return None
    k = KREDI[saglayici]()
    if gerekli > k["kalan"]:
        raise KrediYetersiz(f"{saglayici} kredisi yetmiyor: bu iş {gerekli} kredi istiyor, hesapta {k['kalan']} kaldı "
                            f"({k['plan']} planı, {k['limit']} kredi/ay)")
    return {"gerekli": gerekli, "kalan": k["kalan"], "plan": k["plan"]}


def _ucretli_uret(saglayici: str, metin: str, ayar: dict, sayac: dict) -> tuple[bytes, int, dict | None]:
    """Önbellekte varsa oradan okur (kredi harcamaz); yoksa API'den alıp önbelleğe yazar.

    Harf zamanları (varsa) wav'ın yanına `<anahtar>.hizalama.json` olarak yazılır. Zamanlar eklenmeden önce
    önbelleğe girmiş satırlarda yoktur; karakter şablonu o zaman ağzı ses genliğinden oynatır.
    """
    yol = _onbellek_yolu(saglayici, metin, ayar)
    kok = yol.parent
    hiz_yol = yol.with_suffix(".hizalama.json")
    if yol.exists():
        with wave.open(str(yol), "rb") as w:
            sayac["onbellek"] += 1
            hizalama = json.loads(hiz_yol.read_text(encoding="utf-8")) if hiz_yol.exists() else None
            return w.readframes(w.getnframes()), w.getframerate(), hizalama
    pcm, sr, *ek = SAGLAYICILAR[saglayici](metin, ayar)
    hizalama = ek[0] if ek else None
    kok.mkdir(parents=True, exist_ok=True)
    if hizalama:
        hiz_yol.write_text(json.dumps(hizalama, ensure_ascii=False), encoding="utf-8")
    gecici = yol.with_suffix(".yaziliyor")
    wav_yaz(gecici, pcm, sr)
    gecici.replace(yol)
    sayac["karakter"] += len(metin)
    sayac["api"] += 1
    return pcm, sr, hizalama


def bastaki_sessizlik(pcm: bytes, sr: int, esik_db: float = -50.0) -> float:
    """Cila zincirinin baştan kestiği sessizlik (sn): ilk örnek -50 dBFS'i geçene kadar (silenceremove ile aynı eşik)."""
    import array
    a = array.array("h", pcm[: len(pcm) - len(pcm) % 2])
    esik = 32768 * 10 ** (esik_db / 20)
    for i, x in enumerate(a):
        if abs(x) > esik:
            return i / sr
    return 0.0


def hizalama_yaz(yol: Path, hizalama: dict, kayma: float) -> None:
    """Harf zamanlarını cilalı dosyanın zamanına kaydırıp yazar: {"karakterler", "bas", "son"} (sn)."""
    kay = lambda xs: [round(max(0.0, x - kayma), 4) for x in xs]
    yol.write_text(json.dumps({"karakterler": hizalama["karakterler"], "bas": kay(hizalama["bas"]),
                               "son": kay(hizalama["son"])}, ensure_ascii=False), encoding="utf-8")


def kullanim_yaz(kayit: dict) -> None:
    yol = _onbellek_koku() / "kullanim.jsonl"
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


# ---------- cila ve yazma ----------
def _ffmpeg(girdi: Path, cikti: Path, zincir: str) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(girdi), "-af", zincir,
            "-ac", "1", "-c:a", "pcm_s16le", str(cikti)]


def cila_komutu(girdi: Path, cikti: Path) -> list[str]:
    """ham çıktı → temizlenmiş, 48 kHz (soxr) ara dosya"""
    return _ffmpeg(girdi, cikti, f"{CILA},aresample={ORNEKLEME}:resampler=soxr")


def seviye_komutu(girdi: Path, cikti: Path, kazanc_db: float) -> list[str]:
    """ara dosya → hedef loudness, tepe sınırlı son dosya"""
    return _ffmpeg(girdi, cikti, f"volume={kazanc_db:.2f}dB,alimiter=limit=0.89:level=false")


def olc_lufs(yol: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(yol), "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True)
    satir = [s for s in r.stderr.splitlines() if s.strip().startswith("I:")]
    if not satir:
        raise SeslendirmeHatasi(f"loudness ölçülemedi: {yol}")
    return float(satir[-1].split()[1])


def wav_yaz(yol: Path, pcm: bytes, sr: int) -> None:
    with wave.open(str(yol), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)


def sure(yol: Path) -> float:
    with wave.open(str(yol), "rb") as w:
        return w.getnframes() / w.getframerate()


def uret(satirlar: list[dict], cikti: Path, saglayici: str | None = "otomatik", ayar: dict | None = None) -> dict:
    otomatik = saglayici in (None, "", "otomatik")
    ayar = dict(ayar or {})
    saglayici = saglayici_coz(saglayici, ayar)
    ayar.pop("saglayici", None)
    # telaffuz sözlüğü (platform/ses/telaffuz.py): sese giden metinde marka ve yer adları okunuşuyla değişir
    satirlar = telaffuz.uygula(satirlar, eleven_ayar(ayar)["dil"], ayar.pop("klasor", None), ayar.pop("telaffuz", None))
    if saglayici not in SAGLAYICILAR:
        raise SeslendirmeHatasi(f"bilinmeyen sağlayıcı: {saglayici}")
    try:
        return _uret(satirlar, cikti, saglayici, ayar)
    except SeslendirmeHatasi as e:
        if not (otomatik and saglayici != YEDEK):
            raise
        print(f"UYARI: {saglayici} kullanılamadı ({e}). Bütün iş {YEDEK.capitalize()} ile seslendiriliyor; "
              f"kalite raporu bunu uyarı olarak gösterir, teslimden önce {saglayici} ile yeniden seslendirin.",
              file=sys.stderr)
        p_ayar = dict(ayar)
        if p_ayar.get("ses") not in PIPER_SESLERI:  # voice_id Piper'da yok: dile ve cinsiyete göre Piper sesi
            de = (ayar.get("dil") or "tr") == "de"
            p_ayar["ses"] = ("kerstin" if ayar.get("cinsiyet") == "kadin" else "thorsten") if de else None
        kayit = _uret(satirlar, cikti, YEDEK, p_ayar)
        kayit["yedek"] = {"istenen": saglayici, "neden": str(e)}
        (cikti / "seslendirme.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return kayit


def _uret(satirlar: list[dict], cikti: Path, saglayici: str, ayar: dict) -> dict:
    cikti.mkdir(parents=True, exist_ok=True)
    ses = eleven_ayar(ayar)["ses"] if saglayici == "elevenlabs" else (ayar.get("ses") or "fahrettin")
    kayit = {"saglayici": saglayici, "ses": ses, "satirlar": []}
    sayac = {"karakter": 0, "api": 0, "onbellek": 0}
    satir_ayar = satir_ayarlari(satirlar, ayar) if saglayici == "elevenlabs" else [ayar] * len(satirlar)
    kredi = kredi_kontrol(saglayici, satirlar, satir_ayar) if saglayici in UCRETLI else None
    with tempfile.TemporaryDirectory() as tmp:
        for s, s_ayar in zip(satirlar, satir_ayar):
            ham = Path(tmp) / f"{s['id']}.ham.wav"
            ara = Path(tmp) / f"{s['id']}.ara.wav"
            son = cikti / f"{s['id']}.wav"
            if saglayici in UCRETLI:
                pcm, sr, hizalama = _ucretli_uret(saglayici, s["metin"], s_ayar, sayac)
            else:
                pcm, sr, *ek = SAGLAYICILAR[saglayici](s["metin"], ayar)
                hizalama = ek[0] if ek else None
            wav_yaz(ham, pcm, sr)
            subprocess.run(cila_komutu(ham, ara), check=True)
            subprocess.run(seviye_komutu(ara, son, HEDEF_LUFS - olc_lufs(ara)), check=True)
            satir = {"id": s["id"], "metin": s["metin"], "sure": round(sure(son), 3)}
            hiz_yol = cikti / f"{s['id']}.hizalama.json"
            if hizalama:
                hizalama_yaz(hiz_yol, hizalama, bastaki_sessizlik(pcm, sr))
                satir["hizalama"] = hiz_yol.name
            elif hiz_yol.exists():
                hiz_yol.unlink()  # eski bir üretimden kalan zamanlar bu sese ait değil
            kayit["satirlar"].append(satir)
    if saglayici in UCRETLI:
        kayit["kullanim"] = dict(sayac)
        kullanim_yaz({"zaman": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "saglayici": saglayici, "ses": ses,
                      "is": str(cikti.resolve()), **sayac})
        kalan = f", hesapta ~{kredi['kalan'] - sayac['karakter']} kredi kaldı" if kredi else ""
        print(f"{saglayici}: {sayac['karakter']} karakter harcandı ({sayac['api']} satır API, "
              f"{sayac['onbellek']} satır önbellekten{kalan})", file=sys.stderr)
    (cikti / "seslendirme.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return kayit


def kullanim_ozeti() -> dict:
    yol = _onbellek_koku() / "kullanim.jsonl"
    toplam = {"karakter": 0, "api": 0, "onbellek": 0, "is": 0}
    if yol.exists():
        for satir in yol.read_text(encoding="utf-8").splitlines():
            k = json.loads(satir)
            toplam["is"] += 1
            for a in ("karakter", "api", "onbellek"):
                toplam[a] += k.get(a, 0)
    return toplam


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    u = alt.add_parser("uret")
    u.add_argument("satirlar"); u.add_argument("-o", "--cikti", required=True)
    u.add_argument("--saglayici", default="otomatik", choices=["otomatik", *sorted(SAGLAYICILAR)])
    u.add_argument("--ses"); u.add_argument("--dil", help="tr, de, ... (ElevenLabs varsayılan sesi için)")
    u.add_argument("--hiz", type=float, default=1.0)
    u.add_argument("--ticari-degil", action="store_true", help="ticari olmayan lisanslı seslere izin ver")
    alt.add_parser("sesler")
    alt.add_parser("kullanim")
    alt.add_parser("kredi")
    a = ap.parse_args(argv)
    if a.komut == "kredi":
        try:
            k = eleven_kredi()
        except SeslendirmeHatasi as e:
            print(f"HATA: {e}", file=sys.stderr)
            return 2
        yenilenme = time.strftime("%Y-%m-%d", time.gmtime(k["yenilenme"])) if k.get("yenilenme") else "?"
        print(f"ElevenLabs {k['plan']}: {k['harcanan']} / {k['limit']} kredi harcandı, {k['kalan']} kaldı (yenilenme {yenilenme})")
        return 0
    if a.komut == "kullanim":
        t = kullanim_ozeti()
        print(f"ElevenLabs: {t['karakter']} karakter, {t['is']} iş, {t['api']} satır API, {t['onbellek']} satır önbellekten"
              f" (kayıt: {_onbellek_koku() / 'kullanim.jsonl'})")
        return 0
    if a.komut == "sesler":
        for ad, b in PIPER_SESLERI.items():
            print(f"piper  {ad:10} {b['dil']}  {b['lisans']:16} {'ticari' if b['ticari'] else 'ticari değil'}")
        for c, b in ELEVEN_SESLERI.items():
            print(f"elevenlabs {b['ad']:10} {c:6} varsayılan ({b['id']})")
        for ad, b in ELEVEN_ADLI_SESLER.items():
            print(f"elevenlabs --ses {ad:12} {b['cinsiyet']:6} {b['not']} ({b['id']})")
        for dil, c in ELEVEN_DIL_SESLERI.items():
            for cins, b in c.items():
                print(f"elevenlabs {b['ad']:10} {cins:6} {dil} varsayılanı ({b['id']})")
        print("elevenlabs  --ses <ad ya da voice_id>  (varsayılan sağlayıcı; ELEVENLABS_API_KEY yoksa Piper yedeği)")
        return 0
    veri = json.loads(Path(a.satirlar).read_text(encoding="utf-8"))
    try:
        k = uret(veri["satirlar"], Path(a.cikti), a.saglayici, {"ses": a.ses, "dil": a.dil, "hiz": a.hiz, "ticari": not a.ticari_degil,
                                                            "saglayici": veri.get("saglayici")})
    except SeslendirmeHatasi as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2
    for s in k["satirlar"]:
        print(f"{s['id']}\t{s['sure']:.2f} sn\t{s['metin']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
