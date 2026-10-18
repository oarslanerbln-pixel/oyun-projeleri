"""Seslendirme adımı: metin satırlarından teslime hazır, 48 kHz WAV dosyaları.

    python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme
    python3 platform/ses/seslendirme.py uret satirlar.json -o cikti/seslendirme --saglayici elevenlabs --ses <voice_id>
    python3 platform/ses/seslendirme.py sesler

`satirlar.json`: {"satirlar": [{"id": "v0", "metin": "Her gün, sadece yüzde bir daha iyi ol."}, ...]}
Her satır `<id>.wav` olur; aynı klasöre süreleri içeren `seslendirme.json` yazılır (kurgu zamanlaması buradan okur).

Sağlayıcılar (`SAGLAYICILAR`):
  piper       yerel, ücretsiz. Ses modeli ilk kullanımda GitHub'dan indirilir (huggingface.co kapalı olabilir).
  elevenlabs  ücretli API. ELEVENLABS_API_KEY yoksa açık bir hatayla durur.
Her iki sağlayıcının ham çıktısı aynı "cila" zincirinden geçer: gövde temizliği, varlık, yumuşak
sıkıştırma, satır başına -16 LUFS ve soxr ile 48 kHz'e çevirme.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path

ORNEKLEME = 48000
HEDEF_LUFS = -16.0

# Piper sesleri: lisans ticari işte kullanılabilirliği belirler (lisans kapısı).
PIPER_SESLERI = {
    "fahrettin": {"dil": "tr", "kod": "tr_TR", "lisans": "CC0", "ticari": True},
    "fettah": {"dil": "tr", "kod": "tr_TR", "lisans": "CC0", "ticari": True},
    "dfki": {"dil": "tr", "kod": "tr_TR", "lisans": "CC BY-NC-SA 4.0", "ticari": False},
    "thorsten": {"dil": "de", "kod": "de_DE", "lisans": "CC0", "ticari": True},
    "kerstin": {"dil": "de", "kod": "de_DE", "lisans": "CC0", "ticari": True, "kalite": "low"},  # kadın sesi; yalnız low var
}
PIPER_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-{kod}-{ses}-{kalite}.tar.bz2"
PIPER_ONBELLEK = Path(os.environ.get("PIPER_SES_DIZINI", Path.home() / ".cache" / "studyo" / "piper"))

ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{ses}?output_format=pcm_44100"
ELEVEN_MODEL = "eleven_multilingual_v2"

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


def elevenlabs(metin: str, ayar: dict, ag=None) -> tuple[bytes, int]:
    anahtar = os.environ.get("ELEVENLABS_API_KEY", "")
    if not anahtar:
        raise SeslendirmeHatasi("ELEVENLABS_API_KEY ortam değişkeni yok; anahtar eklenene kadar --saglayici piper kullanın")
    ses = ayar.get("ses") or os.environ.get("ELEVENLABS_VOICE_ID", "")
    if not ses:
        raise SeslendirmeHatasi("ElevenLabs ses kimliği yok: --ses <voice_id> ya da ELEVENLABS_VOICE_ID verin")
    govde = {
        "text": metin,
        "model_id": ayar.get("model") or ELEVEN_MODEL,
        "language_code": ayar.get("dil", "tr"),
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True},
    }
    istek = urllib.request.Request(ELEVEN_URL.format(ses=ses), data=json.dumps(govde).encode("utf-8"), method="POST",
                                   headers={"xi-api-key": anahtar, "Content-Type": "application/json", "Accept": "audio/pcm"})
    try:
        pcm = (ag or _ac)(istek)
    except urllib.error.HTTPError as e:
        raise SeslendirmeHatasi(f"ElevenLabs {e.code}: {e.read()[:300].decode('utf-8', 'replace')}") from e
    return pcm, 44100


def _ac(istek) -> bytes:
    with urllib.request.urlopen(istek, timeout=120) as r:
        return r.read()


SAGLAYICILAR = {"piper": piper, "elevenlabs": elevenlabs}


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


def uret(satirlar: list[dict], cikti: Path, saglayici: str = "piper", ayar: dict | None = None) -> dict:
    if saglayici not in SAGLAYICILAR:
        raise SeslendirmeHatasi(f"bilinmeyen sağlayıcı: {saglayici}")
    ayar = ayar or {}
    cikti.mkdir(parents=True, exist_ok=True)
    kayit = {"saglayici": saglayici, "ses": ayar.get("ses"), "satirlar": []}
    with tempfile.TemporaryDirectory() as tmp:
        for s in satirlar:
            ham = Path(tmp) / f"{s['id']}.ham.wav"
            ara = Path(tmp) / f"{s['id']}.ara.wav"
            son = cikti / f"{s['id']}.wav"
            pcm, sr = SAGLAYICILAR[saglayici](s["metin"], ayar)
            wav_yaz(ham, pcm, sr)
            subprocess.run(cila_komutu(ham, ara), check=True)
            subprocess.run(seviye_komutu(ara, son, HEDEF_LUFS - olc_lufs(ara)), check=True)
            kayit["satirlar"].append({"id": s["id"], "metin": s["metin"], "sure": round(sure(son), 3)})
    (cikti / "seslendirme.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return kayit


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    u = alt.add_parser("uret")
    u.add_argument("satirlar"); u.add_argument("-o", "--cikti", required=True)
    u.add_argument("--saglayici", default="piper", choices=sorted(SAGLAYICILAR))
    u.add_argument("--ses"); u.add_argument("--hiz", type=float, default=1.0)
    u.add_argument("--ticari-degil", action="store_true", help="ticari olmayan lisanslı seslere izin ver")
    alt.add_parser("sesler")
    a = ap.parse_args(argv)
    if a.komut == "sesler":
        for ad, b in PIPER_SESLERI.items():
            print(f"piper  {ad:10} {b['dil']}  {b['lisans']:16} {'ticari' if b['ticari'] else 'ticari değil'}")
        print("elevenlabs  --ses <voice_id>  (ELEVENLABS_API_KEY gerekir)")
        return 0
    veri = json.loads(Path(a.satirlar).read_text(encoding="utf-8"))
    try:
        k = uret(veri["satirlar"], Path(a.cikti), a.saglayici, {"ses": a.ses, "hiz": a.hiz, "ticari": not a.ticari_degil})
    except SeslendirmeHatasi as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2
    for s in k["satirlar"]:
        print(f"{s['id']}\t{s['sure']:.2f} sn\t{s['metin']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
