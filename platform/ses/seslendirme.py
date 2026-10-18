"""Seslendirme adımı: metin satırlarından teslime hazır, 48 kHz WAV dosyaları.

    python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme
    python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme --saglayici elevenlabs --ses <voice_id>
    python3 platform/ses/seslendirme.py sesler
    python3 platform/ses/seslendirme.py kullanim          # ElevenLabs'te harcanan karakterler (iş başına)

`satirlar.json`: {"satirlar": [{"id": "v0", "metin": "Her gün, sadece yüzde bir daha iyi ol."}, ...]}
Her satır `<id>.wav` olur; aynı klasöre süreleri içeren `seslendirme.json` yazılır (kurgu zamanlaması buradan okur).

Sağlayıcılar (`SAGLAYICILAR`):
  otomatik    varsayılan: piper. İş ElevenLabs isterse (senaryoda `"seslendirme": {"saglayici": "elevenlabs"}`)
              elevenlabs; anahtar yoksa ya da ElevenLabs'e ulaşılamazsa uyarıp piper'a döner (render durmaz).
              ElevenLabs her işte değil, seçilen işlerde (müşteri işi, öne çıkan video) kullanılır.
  piper       yerel, ücretsiz. Ses modeli ilk kullanımda GitHub'dan indirilir (huggingface.co kapalı olabilir).
  elevenlabs  ücretli API. ELEVENLABS_API_KEY yoksa açık bir hatayla durur. Her satır önbelleğe yazılır:
              aynı metin + ses + ayar ikinci kez kredi harcamaz. Harcanan karakterler kullanim.jsonl'a yazılır.
Her iki sağlayıcının ham çıktısı aynı "cila" zincirinden geçer: gövde temizliği, varlık, yumuşak
sıkıştırma, satır başına -16 LUFS ve soxr ile 48 kHz'e çevirme.
"""

from __future__ import annotations

import argparse
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

ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{ses}?output_format={bicim}"
# pcm_44100 yalnız Pro ve üstünde; ücretsiz ve Starter planlarda en iyi biçim mp3_44100_128 (ffmpeg ile çözülür).
# Pro hesapta ELEVENLABS_OUTPUT_FORMAT=pcm_44100 ile kayıpsız alınır.
ELEVEN_BICIM = os.environ.get("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
ELEVEN_MODEL = "eleven_multilingual_v2"
# Dil zorlaması (language_code) yalnız bu modellerde var; multilingual_v2 dili metinden anlar, alanı görürse reddeder.
ELEVEN_DIL_ZORLAYAN = ("eleven_turbo_v2_5", "eleven_flash_v2_5")
ELEVEN_AYAR = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True}
# Varsayılan sesler: ElevenLabs'in hazır, çok dilli sesleri (multilingual_v2 ile Türkçe ve Almanca okur).
# Dile özel seçim (ör. e-kitap testinde beğenilen Almanca ses) ELEVEN_DIL_SESLERI'ne, kanal ya da müşteri
# sesi senaryonun `seslendirme.ses` alanına (voice_id) yazılır. Ortam: ELEVENLABS_VOICE_ID[_TR|_DE].
ELEVEN_SESLERI = {
    "erkek": {"ad": "George", "id": "JBFqnCBsd6RMkjVDRZzb"},
    "kadin": {"ad": "Matilda", "id": "XrExE9yKIg1WjnnlVkGX"},
}
ELEVEN_DIL_SESLERI: dict[str, dict[str, dict]] = {}


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

    `ses` bir ElevenLabs voice_id ise o kullanılır. Piper ses adıysa (senaryolar `kerstin` gibi
    Piper adları taşır) dili ve cinsiyeti alınır, o dilin varsayılan ElevenLabs sesi seçilir.
    """
    ses = ayar.get("ses") or ""
    piper_bilgi = PIPER_SESLERI.get(ses)
    dil = ayar.get("dil") or (piper_bilgi or {}).get("dil") or "tr"
    if not ses or piper_bilgi:
        cinsiyet = ayar.get("cinsiyet") or (piper_bilgi or {}).get("cinsiyet") or "erkek"
        ses = (os.environ.get(f"ELEVENLABS_VOICE_ID_{dil.upper()}") or os.environ.get("ELEVENLABS_VOICE_ID")
               or ELEVEN_DIL_SESLERI.get(dil, {}).get(cinsiyet, {}).get("id") or ELEVEN_SESLERI[cinsiyet]["id"])
    model = ayar.get("model") or ELEVEN_MODEL
    return {"ses": ses, "model": model, "dil": dil, "bicim": ayar.get("bicim") or ELEVEN_BICIM,
            "voice_settings": dict(ELEVEN_AYAR, **(ayar.get("voice_settings") or {}))}


def elevenlabs(metin: str, ayar: dict, ag=None) -> tuple[bytes, int]:
    anahtar = os.environ.get("ELEVENLABS_API_KEY", "")
    if not anahtar:
        raise SeslendirmeHatasi("ELEVENLABS_API_KEY ortam değişkeni yok; anahtar eklenene kadar --saglayici piper kullanın")
    e = eleven_ayar(ayar)
    govde = {"text": metin, "model_id": e["model"], "voice_settings": e["voice_settings"]}
    if e["model"] in ELEVEN_DIL_ZORLAYAN:
        govde["language_code"] = e["dil"]
    pcm_mi = e["bicim"].startswith("pcm_")
    istek = urllib.request.Request(ELEVEN_URL.format(ses=e["ses"], bicim=e["bicim"]), data=json.dumps(govde).encode("utf-8"),
                                   method="POST", headers={"xi-api-key": anahtar, "Content-Type": "application/json",
                                                           "Accept": "audio/pcm" if pcm_mi else "audio/mpeg"})
    try:
        veri = (ag or _ac)(istek)
    except urllib.error.HTTPError as h:
        raise SeslendirmeHatasi(f"ElevenLabs {h.code}: {h.read()[:300].decode('utf-8', 'replace')}") from h
    except (urllib.error.URLError, OSError) as h:
        raise SeslendirmeHatasi(f"ElevenLabs'e ulaşılamadı ({h}); ağ izni: api.elevenlabs.io") from h
    if pcm_mi:
        return veri, int(e["bicim"].split("_")[1])
    return _coz(veri, 44100), 44100


def _coz(veri: bytes, sr: int) -> bytes:
    """Sıkıştırılmış ses (mp3) → mono int16 PCM."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1",
                        "-ar", str(sr), "pipe:1"], input=veri, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise SeslendirmeHatasi(f"ElevenLabs sesi çözülemedi: {r.stderr[:200].decode('utf-8', 'replace')}")
    return r.stdout


def _ac(istek) -> bytes:
    with urllib.request.urlopen(istek, timeout=120) as r:
        return r.read()


SAGLAYICILAR = {"piper": piper, "elevenlabs": elevenlabs}
UCRETLI = {"elevenlabs"}  # satır önbelleği ve karakter kaydı bunlar için


def saglayici_coz(saglayici: str | None, ayar: dict | None = None) -> str:
    """`otomatik` (ya da boş): işin istediği sağlayıcı (`ayar["saglayici"]`, senaryodan gelir), yoksa piper."""
    if saglayici in (None, "", "otomatik"):
        return (ayar or {}).get("saglayici") or "piper"
    return saglayici


def _onbellek_anahtari(saglayici: str, metin: str, ayar: dict) -> str:
    cozulmus = eleven_ayar(ayar) if saglayici == "elevenlabs" else ayar
    ham = json.dumps({"s": saglayici, "m": metin, "a": cozulmus}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()[:32]


def _ucretli_uret(saglayici: str, metin: str, ayar: dict, sayac: dict) -> tuple[bytes, int]:
    """Önbellekte varsa oradan okur (kredi harcamaz); yoksa API'den alıp önbelleğe yazar."""
    kok = _onbellek_koku() / saglayici
    yol = kok / f"{_onbellek_anahtari(saglayici, metin, ayar)}.wav"
    if yol.exists():
        with wave.open(str(yol), "rb") as w:
            sayac["onbellek"] += 1
            return w.readframes(w.getnframes()), w.getframerate()
    pcm, sr = SAGLAYICILAR[saglayici](metin, ayar)
    kok.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".yaziliyor")
    wav_yaz(gecici, pcm, sr)
    gecici.replace(yol)
    sayac["karakter"] += len(metin)
    sayac["api"] += 1
    return pcm, sr


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
    if saglayici not in SAGLAYICILAR:
        raise SeslendirmeHatasi(f"bilinmeyen sağlayıcı: {saglayici}")
    try:
        return _uret(satirlar, cikti, saglayici, ayar)
    except SeslendirmeHatasi as e:
        if not (otomatik and saglayici != "piper"):
            raise
        print(f"UYARI: {saglayici} kullanılamadı ({e}); Piper ile devam ediliyor", file=sys.stderr)
        p_ayar = dict(ayar)
        if p_ayar.get("ses") not in PIPER_SESLERI:  # voice_id Piper'da yok: dile göre Piper sesi
            p_ayar["ses"] = "thorsten" if (ayar.get("dil") or "tr") == "de" else None
        return _uret(satirlar, cikti, "piper", p_ayar)


def _uret(satirlar: list[dict], cikti: Path, saglayici: str, ayar: dict) -> dict:
    cikti.mkdir(parents=True, exist_ok=True)
    ses = eleven_ayar(ayar)["ses"] if saglayici == "elevenlabs" else (ayar.get("ses") or "fahrettin")
    kayit = {"saglayici": saglayici, "ses": ses, "satirlar": []}
    sayac = {"karakter": 0, "api": 0, "onbellek": 0}
    with tempfile.TemporaryDirectory() as tmp:
        for s in satirlar:
            ham = Path(tmp) / f"{s['id']}.ham.wav"
            ara = Path(tmp) / f"{s['id']}.ara.wav"
            son = cikti / f"{s['id']}.wav"
            if saglayici in UCRETLI:
                pcm, sr = _ucretli_uret(saglayici, s["metin"], ayar, sayac)
            else:
                pcm, sr = SAGLAYICILAR[saglayici](s["metin"], ayar)
            wav_yaz(ham, pcm, sr)
            subprocess.run(cila_komutu(ham, ara), check=True)
            subprocess.run(seviye_komutu(ara, son, HEDEF_LUFS - olc_lufs(ara)), check=True)
            kayit["satirlar"].append({"id": s["id"], "metin": s["metin"], "sure": round(sure(son), 3)})
    if saglayici in UCRETLI:
        kayit["kullanim"] = dict(sayac)
        kullanim_yaz({"zaman": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "saglayici": saglayici, "ses": ses,
                      "is": str(cikti.resolve()), **sayac})
        print(f"{saglayici}: {sayac['karakter']} karakter harcandı ({sayac['api']} satır API, "
              f"{sayac['onbellek']} satır önbellekten)", file=sys.stderr)
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
    a = ap.parse_args(argv)
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
        print("elevenlabs  --ses <voice_id>  (ELEVENLABS_API_KEY gerekir; varsayılan değil, işe göre seçilir)")
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
