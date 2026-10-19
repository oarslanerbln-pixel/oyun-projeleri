"""Analiz şablonu: haber / veri anlatımı videosu (30–90 sn), kaynaklı grafikler + seslendirme.

Tek senaryo dosyasından (sahneler, sayılar, kaynaklar, seslendirme satırları) görüntü, efekt ve
müzik aynı anlara kilitli üretilir; hiçbir ücretli servis gerekmez.

    python3 platform/sablonlar/analiz/analiz.py denetle   analiz.json
    python3 platform/sablonlar/analiz/analiz.py seslendir analiz.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/analiz/analiz.py kare      analiz.json --an 3 12.5 --format 16:9
    python3 platform/sablonlar/analiz/analiz.py render    analiz.json [--format 16:9|9:16|1:1|4:5|ikisi]
    python3 platform/sablonlar/analiz/analiz.py uret      analiz.json     # seslendirme eksikse üretir, sonra render
Çıktı varsayılanı senaryonun yanındaki `cikti/` klasörü. Format verilmezse senaryonun `format`
alanı, o da yoksa 16:9 (uzun video varsayılanı) kullanılır; iki format ancak `ikisi` ile çıkar.
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
sys.path.append(str(BURADA.parents[1] / "ortak"))  # kalite kapısı

FORMATLAR = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}
HEDEF_LUFS = -14.0
TURLER = {
    "baslik": [], "cubuk": ["cubuklar"], "cizgi": ["noktalar"], "sayac": ["kartlar"], "harita": [],
    "karsilastirma": ["sol", "sag"], "zaman": ["olaylar"], "alinti": ["metin"], "kapanis": [],
}
# Bu sahneler sayı gösterir: kaynak satırı zorunlu (ekrandaki her sayının kaynağı görünür).
KAYNAK_ZORUNLU = {"cubuk", "cizgi", "sayac", "harita", "karsilastirma", "zaman", "alinti"}


def yukle(yol: str) -> dict:
    s = json.loads(Path(yol).read_text(encoding="utf-8"))
    s["_klasor"] = str(Path(yol).resolve().parent)
    s.setdefault("fps", 30)
    s.setdefault("seslendirme", {"satirlar": []})
    s.setdefault("muzik", {"bpm": 96, "akorlar": [[50, 53, 57, 62], [46, 50, 53, 58], [53, 57, 60, 65], [48, 52, 55, 60]]})
    return s


def sureler_oku(klasor: Path) -> dict[str, float]:
    k = klasor / "seslendirme.json"
    if not k.exists():
        return {}
    return {x["id"]: x["sure"] for x in json.loads(k.read_text(encoding="utf-8"))["satirlar"]}


def _sayilar(sahne: dict) -> list:
    """sahnedeki ekrana çıkan bütün sayılar (deger alanları)"""
    out = []

    def gez(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "deger":
                    out.append(v)
                else:
                    gez(v)
        elif isinstance(x, list):
            for v in x:
                gez(v)
    gez(sahne)
    return out


def denetle(s: dict, sureler: dict[str, float] | None = None) -> list[str]:
    h = []
    sure = s.get("sure")
    if not isinstance(sure, (int, float)) or sure <= 0:
        return ["sure pozitif bir sayı olmalı"]
    if s.get("format") and s["format"] not in (*FORMATLAR, "ikisi"):
        h.append(f"format bilinmiyor: {s['format']}")
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
        for alan in TURLER[x["tur"]]:
            if not x.get(alan):
                h.append(f"{ad}: `{alan}` gerekli")
        if x["tur"] in KAYNAK_ZORUNLU and not str(x.get("kaynak", "")).strip():
            h.append(f"{ad}: `kaynak` gerekli (ekrandaki sayıların kaynağı alt bantta görünmeli)")
        for v in _sayilar(x):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                h.append(f"{ad}: deger sayı olmalı ({v!r})")
        if x["tur"] == "harita":
            for nk in x.get("noktalar", []):
                if not (-180 <= nk.get("lon", 999) <= 180 and -90 <= nk.get("lat", 999) <= 90):
                    h.append(f"{ad}: {nk.get('ad')} için lon/lat eksik ya da hatalı")
    if sh and sh[0].get("bas") != 0:
        h.append("ilk sahne 0. saniyede başlamalı")
    satirlar = s["seslendirme"].get("satirlar", [])
    sureler = sureler or {}
    for a, b in zip(satirlar, satirlar[1:]):
        if a["id"] in sureler and a["t"] + sureler[a["id"]] > b["t"] - 0.05:
            h.append(f"seslendirme {a['id']} ({a['t'] + sureler[a['id']]:.2f} sn'de biter) {b['id']} ile çakışıyor ({b['t']:.2f})")
    if satirlar:
        son = satirlar[-1]
        if son["id"] in sureler and son["t"] + sureler[son["id"]] > sure - 0.3:
            h.append(f"seslendirme {son['id']} videonun sonuna taşıyor")
    return h


def cikti_klasoru(s: dict, arg: str | None) -> Path:
    return Path(arg) if arg else Path(s["_klasor"]) / "cikti"


def formatlar_coz(s: dict, arg: str | None) -> list[str]:
    f = arg or s.get("format") or "16:9"
    return ["16:9", "9:16"] if f == "ikisi" else [f]


def seslendir(s: dict, cikti: Path, saglayici: str, ses: str | None) -> dict:
    import seslendirme
    return seslendirme.senaryodan(s, cikti / "seslendirme", saglayici, ses)


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
    kimlik = s.get("kimlik", "analiz")
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
        import kalite
        kalite.render_sonrasi(hedef)  # kalite.json + kontakt sayfası; render'ı durdurmaz
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
            p.add_argument("--saglayici", default="otomatik")
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
