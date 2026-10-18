"""Minyatür şablonu: Osmanlı minyatürü dilinde kısa marka videosu (lokanta, kafe, mekân).

Altın gök, tezhipli çerçeve, düz perspektifli bir avlu. Anlatı "doluluk" üzerine kurulur: boş
minderler sahne sahne dolar, misafirler kapıdan girip yerlerine oturur, isteğe bağlı olarak gece
çöker, kapıda sıra oluşur ve video şemse (madalyon) içinde marka adıyla kapanır. Sosyal kanıtı
ekrana sayı yazmadan gösterir. Görüntü, efekt ve müzik aynı senaryodan, aynı anlara kilitli çıkar.

    python3 platform/sablonlar/minyatur/minyatur.py denetle   minyatur.json
    python3 platform/sablonlar/minyatur/minyatur.py seslendir minyatur.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/minyatur/minyatur.py kare      minyatur.json --an 1.5 6.5 --format 9:16
    python3 platform/sablonlar/minyatur/minyatur.py render    minyatur.json [--format 9:16|16:9|1:1|4:5|ikisi]
    python3 platform/sablonlar/minyatur/minyatur.py uret      minyatur.json     # seslendirme eksikse üretir, sonra render
Çıktı varsayılanı senaryonun yanındaki `cikti/` klasörü. Format verilmezse senaryonun `format`
alanı, o da yoksa 9:16 (kısa video varsayılanı) kullanılır; iki format ancak `ikisi` ile çıkar.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
sys.path.insert(0, str(BURADA.parents[1] / "ses"))

FORMATLAR = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}
HEDEF_LUFS = -14.0
TURLER = ("acilis", "avlu", "kapanis")
IKRAMLAR = ("yemek", "kahve")


def yukle(yol: str) -> dict:
    s = json.loads(Path(yol).read_text(encoding="utf-8"))
    s["_klasor"] = str(Path(yol).resolve().parent)
    s.setdefault("fps", 30)
    s.setdefault("seslendirme", {"satirlar": []})
    s.setdefault("muzik", {})
    s["muzik"].setdefault("bpm", 96)
    s.setdefault("marka", {})
    return s


def sureler_oku(klasor: Path) -> dict[str, float]:
    k = klasor / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    h = []
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or sure <= 0:
        return ["sure pozitif bir sayı olmalı"]
    if s.get("format") and s["format"] not in (*FORMATLAR, "ikisi"):
        h.append(f"format bilinmiyor: {s['format']}")
    if s.get("mekan", {}).get("ikram", "yemek") not in IKRAMLAR:
        h.append(f"mekan.ikram şunlardan biri olmalı: {', '.join(IKRAMLAR)}")
    sh = s.get("sahneler") or []
    if not sh:
        h.append("en az bir sahne gerekli")
    onceki = -1.0
    for i, x in enumerate(sh):
        ad = f"sahne {i + 1} ({x.get('tur')})"
        if x.get("tur") not in TURLER:
            h.append(f"{ad}: bilinmeyen tür; seçenekler: {', '.join(TURLER)}")
            continue
        if not isinstance(x.get("bas"), (int, float)) or x["bas"] <= onceki or x["bas"] >= sure:
            h.append(f"{ad}: bas artan sırada ve sürenin içinde olmalı")
        onceki = x.get("bas", onceki)
        d = x.get("doluluk")
        if d is not None and (not isinstance(d, (int, float)) or isinstance(d, bool) or not 0 <= d <= 1):
            h.append(f"{ad}: doluluk 0 ile 1 arasında bir sayı olmalı")
        k = x.get("kuyruk")
        if k is not None and (not isinstance(k, int) or isinstance(k, bool) or not 0 <= k <= 8):
            h.append(f"{ad}: kuyruk 0–8 arası bir kişi sayısı olmalı")
        if len(str(x.get("kartus", ""))) > 22:
            h.append(f"{ad}: kartuş yazısı en fazla 22 karakter (ekranda az yazı)")
    if sh and sh[0].get("bas") != 0:
        h.append("ilk sahne 0. saniyede başlamalı")
    if sh and sh[0].get("tur") != "acilis":
        h.append("ilk sahne `acilis` olmalı")
    if any(x.get("tur") == "kapanis" for x in sh) and not s["marka"].get("ad"):
        h.append("kapanış için marka.ad gerekli")
    satirlar = s["seslendirme"].get("satirlar", [])
    sureler = sureler or {}
    for a, b in zip(satirlar, satirlar[1:]):
        if a["id"] in sureler and a["t"] + sureler[a["id"]] > b["t"] - 0.05:
            h.append(f"seslendirme {a['id']} ({a['t'] + sureler[a['id']]:.2f} sn'de biter) {b['id']} ile çakışıyor ({b['t']:.2f})")
    if satirlar:
        son = satirlar[-1]
        if son["id"] in sureler and son["t"] + sureler[son["id"]] > sure - 0.15:
            h.append(f"seslendirme {son['id']} videonun sonuna taşıyor")
    return h


def cikti_klasoru(s: dict, arg: str | None) -> Path:
    return Path(arg) if arg else Path(s["_klasor"]) / "cikti"


def formatlar_coz(s: dict, arg: str | None) -> list[str]:
    f = arg or s.get("format") or "9:16"
    return ["9:16", "16:9"] if f == "ikisi" else [f]


def seslendir(s: dict, cikti: Path, saglayici: str, ses: str | None) -> dict:
    import seslendirme
    satirlar = [{"id": x["id"], "metin": x.get("okunus", x["metin"])} for x in s["seslendirme"]["satirlar"]]
    return seslendirme.uret(satirlar, cikti / "seslendirme", saglayici, {"ses": ses})


def master(gir: Path, ara: Path) -> None:
    """16 kHz üstü kesilir (AAC sonrası gerçek tepe aşımını önler), -14 LUFS, tepe sınırlı"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(gir), "-af", "lowpass=f=16000:poles=2,ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    lufs = float([x for x in r.stderr.splitlines() if x.strip().startswith("I:")][-1].split()[1])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(gir), "-af",
                    f"lowpass=f=16000:poles=2,volume={HEDEF_LUFS - lufs:.2f}dB,alimiter=limit=0.75:level=false",
                    "-ar", "48000", str(ara)], check=True)


def render(s: dict, cikti: Path, formatlar: list[str]) -> list[Path]:
    import cizim
    import muzik
    kimlik = s.get("kimlik", "minyatur")
    is_ = cikti / "is"
    bilgi = muzik.miksle(s, is_, cikti / "seslendirme")
    eksik = [x["id"] for x in s["seslendirme"].get("satirlar", []) if x["id"] not in bilgi["seslendirme"]]
    if eksik:
        print(f"UYARI: seslendirme yok ({', '.join(eksik)}); önce `seslendir` çalıştırın. Video seslendirmesiz çıkar.", file=sys.stderr)
    if bilgi["ses_ustu_db"] is not None:
        print(f"ses dengesi: konuşma müziğin {bilgi['ses_ustu_db']:.1f} dB üstünde")
    master(is_ / "ses.wav", is_ / "ses-master.wav")
    out = []
    for f in formatlar:
        W, H = FORMATLAR[f]
        ek = f.replace(":", "x")
        sessiz = cizim.video(s, W, H, is_ / f"sessiz-{ek}.mp4")
        hedef = cikti / f"{kimlik}-{ek}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(sessiz), "-i", str(is_ / "ses-master.wav"),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(hedef)], check=True)
        out.append(hedef)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("denetle", "seslendir", "kare", "render", "uret"):
        p = alt.add_parser(ad)
        p.add_argument("senaryo")
        p.add_argument("-o", "--cikti")
        if ad in ("seslendir", "uret"):
            p.add_argument("--saglayici", default="piper")
            p.add_argument("--ses")
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
        if ad in ("kare", "render", "uret"):
            p.add_argument("--format", choices=[*FORMATLAR, "ikisi"])
    a = ap.parse_args(argv)
    s = yukle(a.senaryo)
    cikti = cikti_klasoru(s, a.cikti)
    hatalar = denetle(s, sureler_oku(cikti / "seslendirme"))
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    if a.komut == "denetle":
        print(f"tamam: {len(s['sahneler'])} sahne, {s['sure']} sn")
        return 0
    if a.komut in ("seslendir", "uret"):
        eksik = [x for x in s["seslendirme"]["satirlar"] if not (cikti / "seslendirme" / f"{x['id']}.wav").exists()]
        if a.komut == "seslendir" or eksik:
            import seslendirme
            try:
                k = seslendir(s, cikti, a.saglayici, a.ses)
            except seslendirme.SeslendirmeHatasi as e:
                print(f"HATA: {e}", file=sys.stderr)
                return 2
            for x in k["satirlar"]:
                print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
            hatalar = denetle(s, sureler_oku(cikti / "seslendirme"))
            for h in hatalar:
                print(f"HATA: {h}", file=sys.stderr)
            if hatalar:
                return 1
        if a.komut == "seslendir":
            return 0
    if a.komut == "kare":
        import cizim
        for f in formatlar_coz(s, a.format):
            for p in cizim.kareler(s, *FORMATLAR[f], a.an, cikti / "kareler"):
                print(p)
        return 0
    for p in render(s, cikti, formatlar_coz(s, a.format)):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
