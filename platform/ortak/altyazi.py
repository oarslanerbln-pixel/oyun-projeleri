"""Kelimeye senkron zamanlar ve ortak altyazı (kelime kelime).

ElevenLabs her satır için harf zamanlarını verir (`<id>.hizalama.json`, bkz. platform/ses/seslendirme.py). Bu modül
onları kelime zamanlarına çevirir, kısa altyazı gruplarına böler ve üç biçimde verir:

- şablonlar için veri: `kelimeler()` (satır satır, mutlak saniye), `gruplar()`, `etkin()` (t anında görünen grup ve
  söylenmekte olan kelime). Çizim şablonun işidir (ör. sahne/kaplama.py `altyazi_ciz`), stilin yazı tipi ve paletiyle.
- platformlara yüklenecek dosya: `.srt` ve `.vtt` (sessiz izleyen için, YouTube/Instagram altyazısı).
- her videoya yakılabilen katman: `.ass` (karaoke) + `yak()`; kendi çizimi olmayan şablonlar için (ffmpeg libass).

Hizalama yoksa (Piper, eski önbellek) zamanlar satır süresinden hecelere göre tahmin edilir (Türkçe/Almanca: her ünlü
bir hece). Okunan metin ekrandakinden farklıysa (`okunus`, telaffuz sözlüğü) ve kelime sayıları tutmazsa ekrandaki
kelimeler okunan aralığa hecelerine göre yayılır.

    python3 platform/ortak/altyazi.py srt  <altyazi.json> [-o x.srt]
    python3 platform/ortak/altyazi.py yak  <video.mp4> <altyazi.json> [--format 9x16] [-o cikti.mp4]

Bağımlılık yok (yakmak için ffmpeg).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

SESLI = set("aeıioöuüâîûäAEIİOÖUÜÂÎÛÄ")
NOKTALAMA = ".,;:!?…—–"
AZAMI_KARAKTER = 24  # bir altyazı grubu (9:16'da tek satıra sığar)
AZAMI_KELIME = 4
DURAK = 0.35  # kelimeler arası bu kadar sessizlik grubu böler
TUTMA = 0.45  # grup, son kelimesinden sonra en çok bu kadar ekranda kalır
# Rakamla yazılıp sözle okunan değerler ("37x" → "otuz yedi kat", "%40" → "yüzde kırk") için eşleşme.
SAYI_SOZ = set("""sıfır bir iki üç dört beş altı yedi sekiz dokuz on yirmi otuz kırk elli altmış yetmiş seksen doksan
yüz bin milyon milyar yüzde kat buçuk null eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf zwanzig dreißig
vierzig fünfzig hundert tausend million prozent mal ein""".split())


# ---------- kelimeler ----------
def kucult(s: str) -> str:
    s = s.replace("I", "ı").replace("İ", "i").lower()
    return "".join(c for c in unicodedata.normalize("NFC", s) if c.isalnum() or c in "%")


def hece(k: str) -> int:
    return max(1, sum(c in SESLI for c in k))


def hizalamadan(h: dict) -> list[dict]:
    """harf zamanları → [{"k", "bas", "son"}] (satırın başından saniye). Noktalama kelimeye yapışık kalır, süresi sayılmaz."""
    out, kel, bas, son = [], "", None, None
    for c, b, e in zip(h["karakterler"], h["bas"], h["son"]):
        if c.isspace():
            if kel.strip():
                out.append({"k": kel, "bas": bas, "son": son if son is not None else e})
            kel, bas, son = "", None, None
            continue
        kel += c
        if c not in NOKTALAMA and c not in "\"'“”„«»()":
            bas = b if bas is None else bas
            son = e
    if kel.strip():
        out.append({"k": kel, "bas": bas if bas is not None else 0.0, "son": son if son is not None else bas or 0.0})
    for i, w in enumerate(out):  # yalnız noktalamadan oluşan "kelime" (— gibi): bir öncekinin bittiği an
        if w["bas"] is None:
            w["bas"] = w["son"] = out[i - 1]["son"] if i else 0.0
    return out


def yay(kelimeler: list[str], bas: float, son: float) -> list[dict]:
    """kelimeleri [bas, son] aralığına hecelerine göre yayar"""
    he = [hece(k) for k in kelimeler]
    top, acc, out = sum(he) or 1, 0, []
    for k, h_ in zip(kelimeler, he):
        out.append({"k": k, "bas": bas + acc / top * (son - bas), "son": bas + (acc + h_) / top * (son - bas)})
        acc += h_
    return out


def satir_kelimeleri(metin: str, sure: float, hizalama: dict | None) -> tuple[list[dict], str]:
    """Ekrandaki `metin`in kelimeleri ve satır içi zamanları; (kelimeler, kaynak) — kaynak 'hizalama' ya da 'tahmin'."""
    ekran = metin.split()
    if hizalama and hizalama.get("karakterler"):
        ok = [w for w in hizalamadan(hizalama) if kucult(w["k"])]
        if len(ok) == len([k for k in ekran if kucult(k)]):
            it = iter(ok)
            out = []
            for k in ekran:
                if kucult(k):
                    w = next(it)
                    out.append({"k": k, "bas": w["bas"], "son": w["son"]})
                else:  # yalnız noktalama: öncekine yapışır
                    if out:
                        out[-1]["k"] += " " + k
            return out, "hizalama"
        if ok:
            return yay(ekran, ok[0]["bas"], ok[-1]["son"]), "hizalama"
    return yay(ekran, 0.0, sure), "tahmin"


def kelimeler(satirlar: list[dict], ses_dizini: Path) -> list[dict]:
    """Şablonun seslendirme satırları ({id, t, metin[, okunus]}) + ses klasörü (`seslendirme.json`, `<id>.hizalama.json`)
    → [{"id", "t", "son", "kaynak", "kelimeler": [{"k", "bas", "son"}]}], zamanlar videonun başından saniye."""
    ses_dizini = Path(ses_dizini)
    kayit = ses_dizini / "seslendirme.json"
    bilgi = {x["id"]: x for x in json.loads(kayit.read_text(encoding="utf-8"))["satirlar"]} if kayit.exists() else {}
    out = []
    for x in satirlar:
        b = bilgi.get(x["id"])
        if not b:
            continue
        h = None
        hy = ses_dizini / b["hizalama"] if b.get("hizalama") else None
        if hy and hy.exists():
            h = json.loads(hy.read_text(encoding="utf-8"))
        ws, kaynak = satir_kelimeleri(x["metin"], b["sure"], h)
        t0 = x["t"]
        out.append({"id": x["id"], "t": t0, "son": t0 + b["sure"], "kaynak": kaynak,
                    "kelimeler": [{"k": w["k"], "bas": round(t0 + w["bas"], 3), "son": round(t0 + w["son"], 3)} for w in ws]})
    return out


# ---------- gruplar ----------
def gruplar(satirlar: list[dict], azami_karakter: int = AZAMI_KARAKTER, azami_kelime: int = AZAMI_KELIME) -> list[dict]:
    """Kelimeleri okunur altyazı gruplarına böler: noktalamada, uzun durakta ya da sınır dolunca.
    [{"bas", "son", "kelimeler": [{"k", "bas", "son"}]}]; gruplar zamanda örtüşmez."""
    out: list[dict] = []
    for x in satirlar:
        g: list[dict] = []
        for i, w in enumerate(x["kelimeler"]):
            uzun = len(" ".join(v["k"] for v in g + [w])) > azami_karakter
            if g and (uzun or len(g) >= azami_kelime or w["bas"] - g[-1]["son"] > DURAK):
                out.append(g); g = []
            g.append(w)
            if w["k"][-1:] in ".!?…;:" or (w["k"][-1:] == "," and len(g) >= 2):
                out.append(g); g = []
        if g:
            out.append(g)
    bas = [round(max(0.0, g[0]["bas"] - 0.06), 3) for g in out]
    sonuc = []
    for j, g in enumerate(out):
        son = g[-1]["son"] + TUTMA
        if j + 1 < len(out):
            son = min(son, bas[j + 1])
        sonuc.append({"bas": bas[j], "son": round(max(son, min(g[-1]["son"], bas[j + 1] if j + 1 < len(out) else 1e9)), 3),
                      "kelimeler": g})
    return sonuc


def etkin(gs: list[dict], t: float) -> tuple[dict | None, int, float]:
    """t anında ekrandaki grup, söylenen kelimenin sırası (-1: henüz değil / bitti) ve o kelimenin ilerleyişi (0..1)."""
    for g in gs:
        if g["bas"] <= t < g["son"]:
            for i, w in enumerate(g["kelimeler"]):
                nxt = g["kelimeler"][i + 1]["bas"] if i + 1 < len(g["kelimeler"]) else w["son"]
                if w["bas"] <= t < max(w["son"], nxt):
                    return g, i, min(1.0, (t - w["bas"]) / max(0.05, w["son"] - w["bas"]))
            return g, -1, 0.0
    return None, -1, 0.0


# ---------- eşleşme (öğe, söylendiği an girsin) ----------
def _benzer(a: str, b: str) -> bool:
    """aynı kelime ya da Türkçe/Almanca ekleriyle (ör. 'adım' ~ 'adımlar', 'başla' ~ 'başlayın')"""
    if not a or not b:
        return False
    if a == b:
        return True
    k = min(len(a), len(b))
    return k >= 4 and a[:max(4, k - 1)] == b[:max(4, k - 1)]


def an(kelimeler: list[dict], metin: str, sonra: float = -1.0) -> float | None:
    """`metin`deki ilk anlamlı kelimenin `sonra`dan sonra söylendiği an; rakamlı değerler sayı sözcükleriyle eşleşir."""
    hedef = [kucult(x) for x in metin.split()]
    hedef = [x for x in hedef if x]
    if not hedef:
        return None
    rakam = "".join(c for c in "".join(hedef) if c.isdigit())
    # "bir"/"ein" aynı zamanda belirsiz tanımlık: yalnız değer 1 ise sayı sayılır ("Bir yıl sonra, otuz yedi kat")
    sozler = SAYI_SOZ if rakam == "1" else SAYI_SOZ - {"bir", "ein", "eins"}
    for w in kelimeler:
        if w["bas"] < sonra - 1e-6:
            continue
        k = kucult(w["k"])
        if rakam and (k in sozler or any(c.isdigit() for c in k)):
            return w["bas"]
        if any(_benzer(k, h) for h in hedef if len(h) >= 2 or h == k):
            return w["bas"]
    return None


# ---------- dosyalar ----------
def _zd(t: float, ayrac: str = ",") -> str:
    t = max(0.0, t)
    s, ms = divmod(int(round(t * 1000)), 1000)
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}{ayrac}{ms:03d}"


def srt(gs: list[dict]) -> str:
    return "".join(f"{i}\n{_zd(g['bas'])} --> {_zd(g['son'])}\n{' '.join(w['k'] for w in g['kelimeler'])}\n\n"
                   for i, g in enumerate(gs, 1))


def vtt(gs: list[dict]) -> str:
    return "WEBVTT\n\n" + "".join(f"{_zd(g['bas'], '.')} --> {_zd(g['son'], '.')}\n{' '.join(w['k'] for w in g['kelimeler'])}\n\n"
                                  for g in gs)


def _ass_renk(h: str, a: float = 1.0) -> str:
    h = h.lstrip("#")
    return f"&H{int(255 * (1 - a)):02X}{h[4:6]}{h[2:4]}{h[0:2]}"


# kısa kenar 1080 tasarım biriminde altyazı bandının alt kenarı (güvenli alanın altı) ve yazı boyu
BANT = {"9x16": (0.78, 62), "16x9": (0.92, 48), "1x1": (0.93, 54), "4x5": (0.92, 56)}


def ass(gs: list[dict], W: int, H: int, fmt: str = "9x16", renkler: dict | None = None, yazi_tipi: str = "Inter") -> str:
    """Karaoke altyazı (libass): grup görünür, söylenen kelime vurgu rengine döner. Kutulu zemin (BorderStyle 3)
    her videoda okunur kalır; alt kenar güvenli alanın içinde."""
    r = {"yazi": "#FFFFFF", "vurgu": "#FFD23F", "zemin": "#15122E", **(renkler or {})}
    alt, boy = BANT.get(fmt, BANT["9x16"])
    u = min(W, H) / 1080
    stil = (f"Style: K,{yazi_tipi},{boy * u:.0f},{_ass_renk(r['vurgu'])},{_ass_renk(r['yazi'])},{_ass_renk(r['zemin'], 0.86)},"
            f"{_ass_renk(r['zemin'], 0.86)},-1,0,0,0,100,100,0,0,3,{14 * u:.0f},0,2,{W * 0.08:.0f},{W * 0.08:.0f},"
            f"{H * (1 - alt) + 24 * u:.0f},1")
    satir = []
    for g in gs:
        parca, t = [], g["bas"]
        for w in g["kelimeler"]:
            bekle = max(0, int(round((w["bas"] - t) * 100)))
            if bekle:
                parca.append(f"{{\\k{bekle}}}")
            d = max(1, int(round((w["son"] - w["bas"]) * 100)))
            parca.append(f"{{\\k{d}}}{w['k']} ")
            t = w["bas"] + d / 100
        satir.append(f"Dialogue: 0,{_zd(g['bas'], '.')[1:-1]},{_zd(g['son'], '.')[1:-1]},K,,0,0,0,,{''.join(parca).rstrip()}")
    return ("[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
            f"PlayResX: {W}\nPlayResY: {H}\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, "
            f"MarginV, Encoding\n{stil}\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            + "\n".join(satir) + "\n")


def yaz(gs: list[dict], hedef_kok: Path) -> list[Path]:
    """`<kök>.altyazi.json` (yakmak ve yeniden kullanmak için), `.srt`, `.vtt`"""
    hedef_kok = Path(hedef_kok)
    hedef_kok.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for son, icerik in ((".altyazi.json", json.dumps(gs, ensure_ascii=False, indent=1) + "\n"), (".srt", srt(gs)), (".vtt", vtt(gs))):
        p = hedef_kok.with_name(hedef_kok.name + son)
        p.write_text(icerik, encoding="utf-8")
        out.append(p)
    return out


def _boyut(video: Path) -> tuple[int, int]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                        str(video)], capture_output=True, text=True, check=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def yak(video: Path, gs: list[dict], cikti: Path, fmt: str | None = None, renkler: dict | None = None,
        yazi_dizini: str | None = None) -> Path:
    """Altyazıyı videoya yakar (ses kopyalanır). Kendi çizimi olmayan şablonlar ve kurgu için."""
    import tempfile
    W, H = _boyut(Path(video))
    fmt = fmt or {(9, 16): "9x16", (16, 9): "16x9", (1, 1): "1x1", (4, 5): "4x5"}.get(_oran(W, H), "9x16")
    with tempfile.TemporaryDirectory() as g:
        a = Path(g) / "a.ass"
        a.write_text(ass(gs, W, H, fmt, renkler), encoding="utf-8")
        filtre = f"ass={a}" + (f":fontsdir={yazi_dizini}" if yazi_dizini else "")
        gecici = Path(cikti).with_suffix(".yakiliyor.mp4")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vf", filtre, "-c:v", "libx264",
                        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                        str(gecici)], check=True)
        gecici.replace(cikti)
    return Path(cikti)


def _oran(W: int, H: int) -> tuple[int, int]:
    from math import gcd
    k = gcd(W, H)
    return W // k, H // k


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("srt"); p.add_argument("altyazi"); p.add_argument("-o", "--cikti")
    p = alt.add_parser("yak"); p.add_argument("video"); p.add_argument("altyazi"); p.add_argument("--format")
    p.add_argument("-o", "--cikti")
    a = ap.parse_args(argv)
    gs = json.loads(Path(a.altyazi).read_text(encoding="utf-8"))
    if a.komut == "srt":
        hedef = Path(a.cikti or Path(a.altyazi).with_suffix("").with_suffix(".srt"))
        hedef.write_text(srt(gs), encoding="utf-8")
    else:
        hedef = yak(Path(a.video), gs, Path(a.cikti or Path(a.video).with_name(Path(a.video).stem + "-altyazili.mp4")),
                    a.format.replace(":", "x") if a.format else None)
    print(hedef)
    return 0


if __name__ == "__main__":
    sys.exit(main())
