"""Yayın paketi: teslim edilen her video için yüklemeye hazır klasör.

    python3 platform/ortak/yayin.py paket <video.mp4> --senaryo <senaryo.json> [--siparis siparis.json] [-o klasör]

`<sipariş klasörü>/yayin/<video adı>/` içine yazar:
- video (aynı dosyaya sabit bağ, yer kaplamaz; olmazsa kopya)
- `kapak.jpg` tam çözünürlük; 16:9'da ayrıca `kapak-youtube.jpg` (1280×720, < 2 MB). Kaynak: senaryonun `yayin.kapak`
  saniyesi, yoksa şablonun çizdiği `<ad>-kapak.png`, yoksa ilk başlık sahnesinin yazısı tam göründüğü an, yoksa
  sürenin %35'i.
- `altyazi.srt` + `altyazi.vtt`: şablonun yazdığı altyazı, yoksa seslendirme kaydı ve kelime zamanlarından
- `bolumler.txt`: uzun video (≥ 60 sn) için YouTube bölüm listesi (kurgunun listesi ya da sahne dilinin başlıkları)
- `metin.json` + `YUKLE.md`: YouTube / Instagram / TikTok için başlık, açıklama, etiket önerisi, sınır denetimi ve
  yasak ifade taraması (`platform/metin/temel.tsv`). Metin videonun dilindedir.

Öneriler senaryodan çıkar; thread daha iyisini yazmak isterse senaryoya (ya da siparişe) şu bloğu ekler, paket yeniden
yazılır. Senaryodaki blok dil varyantında çevrilir:

    "yayin": {"baslik": "...", "aciklama": "...", "etiketler": ["markalaşma", "marka"], "kapak": 4.2}

`uret.py` teslimde her video için paketi kendiliğinden yazar; `uret.py siparis.json --yayin` yalnız paketleri yeniler.
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA))
import altyazi  # noqa: E402

METIN = BURADA.parent / "metin" / "metin.py"
SAHNE_DIL = BURADA.parent / "sablonlar" / "sahne" / "dil.py"
UZUN_SN = 60.0

# Platform sınırları (2026): başlık, açıklama, etiket.
SINIR = {
    "youtube": {"baslik": 100, "aciklama": 5000, "etiket_toplam": 500},
    "instagram": {"aciklama": 2200, "etiket": 30, "onerilen_etiket": 5},
    "tiktok": {"aciklama": 2200, "onerilen_etiket": 5},
}
DOLGU = {
    "tr": set("""ve ile bir bu şu o da de ki mi mı mu mü için gibi kadar daha çok en her hiç ne ama fakat veya ya
    sadece bile çünkü sonra önce şimdi artık hem iken olan olarak değil var yok siz biz sen ben onlar size bizim sizin
    bunu şunu onu bunun şunun onun böyle şöyle nasıl neden niye hangi kim gün""".split()),
    "de": set("""und oder aber der die das den dem des ein eine einen einem einer eines ist sind war mit von zu zum zur
    für auf aus bei nach vor über unter nicht nur noch auch schon sehr mehr wie was wer wo warum wenn dann denn als
    sie wir ihr ich du er es man uns euch ihnen ihre ihr sein seine jeden jede jeder diese dieser dieses hier dort
    heute kann können wird werden hat haben kein keine keinen wegen dass damit jedem jedes jeden einfach immer
    ganz wirklich etwas alles alle""".split()),
    "en": set("""and or but the a an is are was with of to for on at by from not only also very more how what who
    where why when then than you we they it this that these those here there can will has have your our""".split()),
}


def _modul(ad: str, yol: Path):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp)
    sys.modules[ad] = m  # dataclass modülü kendini sys.modules'ta arar
    sp.loader.exec_module(m)
    return m


def sure(video: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def boyut(video: Path) -> tuple[int, int]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except ValueError:
        return 0, 0


def video_dili(s: dict, siparis: dict | None = None) -> str:
    sb = s.get("seslendirme") if isinstance(s.get("seslendirme"), dict) else {}
    d = (s.get("dil_varyanti") or {}).get("dil") or sb.get("dil") or s.get("dil")
    return d if d in DOLGU else (siparis or {}).get("dil") or "tr"


def _sahne_zamanlari(s: dict, ses_dizini: Path) -> dict | None:
    if s.get("dil") != "sahne":
        return None
    try:
        d = _modul("sahne_dil", SAHNE_DIL)
        return d.zamanla(s, d.sureler_oku(ses_dizini))
    except Exception:  # noqa: BLE001 - zaman yoksa kapak ve bölüm basit kurala düşer
        return None


# ---------------------------------------------------------------- metinler

def ekran_metinleri(s: dict) -> list[str]:
    """Ekrandaki ve seslendirilen metinler, senaryodaki sırayla (dil varyantının alan seçimiyle aynı)."""
    dv = _modul("dil_varyanti", BURADA / "dil_varyanti.py")
    return [a["kaynak"] for a in dv.alanlar({k: v for k, v in s.items() if k != "yayin"})]


def seslendirme_metni(s: dict) -> list[str]:
    if s.get("dil") == "sahne":
        return [sh["seslendirme"] for sh in s.get("sahneler") or [] if sh.get("seslendirme")]
    sb = s.get("seslendirme") if isinstance(s.get("seslendirme"), dict) else {}
    return [x["metin"] for x in sb.get("satirlar") or [] if x.get("metin")]


def _baslik_bul(s: dict) -> str | None:
    """sahne dili: ilk başlık sahnesi; saniyeli şablon: ilk seslendirme cümlesi kısaysa (çoğu zaman kanca sorusu),
    yoksa ilk başlık yazısı"""
    if s.get("dil") != "sahne":
        ilk = re.split(r"(?<=[.?!])\s+", (seslendirme_metni(s) or [""])[0].strip())[0]
        if 8 <= len(ilk) <= 70:
            return ilk
    for sh in s.get("sahneler") or []:
        if isinstance(sh, dict) and sh.get("tip") == "baslik" and sh.get("metin"):
            return sh["metin"]
    for sh in s.get("sahneler") or []:
        if isinstance(sh, dict) and isinstance(sh.get("baslik"), dict) and sh["baslik"].get("metin"):
            return sh["baslik"]["metin"]
    return None


def _cta_bul(s: dict) -> str | None:
    for sh in reversed(s.get("sahneler") or []):
        if isinstance(sh, dict) and sh.get("tip") == "cta":
            return " · ".join(x for x in (sh.get("metin"), sh.get("alt")) if x)
    return None


def anahtar_kelimeler(metinler: list[str], dil: str, n: int = 8, marka: str | None = None) -> list[str]:
    """Sık geçen anlamlı kelimeler (dolgu kelimeleri ve kısa kelimeler dışarıda), marka adı başta."""
    say = collections.Counter()
    ilk = {}
    for i, m in enumerate(metinler):
        for k in re.findall(r"[^\W\d_]{4,}", m):
            kk = altyazi.kucult(k) if dil == "tr" else k.lower()
            if kk in DOLGU.get(dil, set()):
                continue
            say[kk] += 1
            ilk.setdefault(kk, i)
    sira = sorted(say, key=lambda k: (-say[k], ilk[k]))
    out = []
    if marka:
        out.append(re.sub(r"\W+", "", altyazi.kucult(marka) if dil == "tr" else marka.lower()))
    for k in sira:
        if k not in out:
            out.append(k)
    return [x for x in out if x][:n]


def _cumleler(metinler: list[str], azami: int) -> str:
    out = ""
    for m in metinler:
        aday = (out + " " + m.strip()).strip()
        if len(aday) > azami and out:
            break
        out = aday
    return out


def oneriler(s: dict, siparis: dict | None, dil: str, bolumler: str | None, kisa: bool) -> dict:
    """Platform metinleri. Öncelik: senaryonun `yayin` bloğu → siparişin `yayin` bloğu (yalnız siparişin dilinde) →
    senaryodan çıkarım."""
    sp = siparis or {}
    ayni_dil = (sp.get("dil") or "tr") == dil
    y = dict((sp.get("yayin") or {}) if ayni_dil else {})
    y.update({k: v for k, v in (s.get("yayin") or {}).items() if v})
    marka = (s.get("marka") or {}).get("ad") if isinstance(s.get("marka"), dict) else None
    baslik = y.get("baslik") or (sp.get("baslik") if ayni_dil else None) or _baslik_bul(s) or s.get("kimlik", "")
    ses = seslendirme_metni(s)
    aciklama = y.get("aciklama") or _cumleler(ses or ekran_metinleri(s), 280)
    cta = _cta_bul(s)
    if cta and cta not in aciklama and not y.get("aciklama"):
        aciklama = f"{aciklama}\n\n{cta}"
    etiketler = [re.sub(r"[#\s]+", "", e) for e in (y.get("etiketler") or anahtar_kelimeler(ses + ekran_metinleri(s), dil, 10, marka))]
    etiketler = [e for e in etiketler if e]
    hash_ = lambda xs: " ".join(f"#{e}" for e in xs)  # noqa: E731
    yt_baslik = baslik if not kisa or "#shorts" in baslik.lower() else f"{baslik} #shorts"
    yt_aciklama = aciklama + (f"\n\n{bolumler.strip()}" if bolumler else "") + f"\n\n{hash_(etiketler[:3])}"
    on = SINIR["instagram"]["onerilen_etiket"]
    return {
        "dil": dil,
        "youtube": {"baslik": yt_baslik, "aciklama": yt_aciklama, "etiketler": etiketler[:15]},
        "instagram": {"aciklama": f"{baslik}\n\n{aciklama}\n\n{hash_(etiketler[:on])}"},
        "tiktok": {"aciklama": f"{baslik} {hash_(etiketler[:SINIR['tiktok']['onerilen_etiket']])}"},
        "kaynak": "senaryo.yayin" if s.get("yayin") else ("siparis.yayin" if y else "senaryodan çıkarım"),
    }


def denetle(m: dict) -> list[dict]:
    """Platform sınırları + temel yasak sözlük (kanıtsız üstünlük iddiası, mucize vaadi...)."""
    b = []
    yt, ig = m["youtube"], m["instagram"]
    if len(yt["baslik"]) > SINIR["youtube"]["baslik"]:
        b.append({"seviye": "hata", "yer": "youtube.baslik", "mesaj": f"{len(yt['baslik'])} karakter (en çok 100)"})
    if len(yt["aciklama"]) > SINIR["youtube"]["aciklama"]:
        b.append({"seviye": "hata", "yer": "youtube.aciklama", "mesaj": f"{len(yt['aciklama'])} karakter (en çok 5000)"})
    if sum(len(e) + 1 for e in yt["etiketler"]) > SINIR["youtube"]["etiket_toplam"]:
        b.append({"seviye": "hata", "yer": "youtube.etiketler", "mesaj": "etiketler toplam 500 karakteri aşıyor"})
    for p in ("instagram", "tiktok"):
        a = m[p]["aciklama"]
        if len(a) > SINIR[p]["aciklama"]:
            b.append({"seviye": "hata", "yer": f"{p}.aciklama", "mesaj": f"{len(a)} karakter (en çok {SINIR[p]['aciklama']})"})
    if ig["aciklama"].count("#") > SINIR["instagram"]["etiket"]:
        b.append({"seviye": "hata", "yer": "instagram.aciklama", "mesaj": "30'dan çok hashtag"})
    try:
        mt = _modul("metin", METIN)
        kurallar = mt.sozluk_oku(mt.TEMEL)
        for p in ("youtube", "instagram", "tiktok"):
            metin = " ".join([m[p].get("baslik", ""), m[p]["aciklama"]])
            for k, eslesen in mt.tara(metin, m["dil"], kurallar):
                b.append({"seviye": "hata" if k.seviye == mt.HATA else "uyari", "yer": p,
                          "mesaj": f"'{eslesen}': {k.gerekce} ({k.kimlik})"})
    except Exception as e:  # noqa: BLE001 - sözlük okunamazsa paket yine yazılır, not düşülür
        b.append({"seviye": "uyari", "yer": "metin", "mesaj": f"yasak ifade taraması yapılamadı: {e}"})
    return b


# ---------------------------------------------------------------- dosyalar

def kapak_ani(s: dict, z: dict | None, toplam: float) -> float:
    y = s.get("yayin") or {}
    if isinstance(y.get("kapak"), (int, float)):
        return max(0.0, min(float(y["kapak"]), max(toplam - 0.05, 0.0)))
    for sh in (z or {}).get("sahneler") or []:
        if sh.get("tip") == "baslik":
            return round(sh["bas"] + 0.75 * (sh["son"] - sh["bas"]), 2)
    return round(toplam * 0.35, 2)


def kare_al(video: Path, an: float, hedef: Path, olcek: tuple[int, int] | None = None) -> bool:
    vf = ["-vf", f"scale={olcek[0]}:{olcek[1]}:flags=lanczos"] if olcek else []
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{an:.3f}", "-i", str(video),
                        "-frames:v", "1", *vf, "-q:v", "2", str(hedef)], capture_output=True, text=True)
    return r.returncode == 0 and hedef.exists()


def _onek_bul(video: Path, desen: str) -> Path | None:
    """videonun yanında, adı videonun adının başı olan dosya (ör. `ad-kapak.png` ↔ `ad-9x16.mp4`)"""
    adaylar = [p for p in video.parent.glob(desen) if video.stem.startswith(p.name.split("-kapak")[0].rsplit(".", 1)[0])]
    return max(adaylar, key=lambda p: len(p.name)) if adaylar else None


def _altyazi_bul(video: Path) -> Path | None:
    tam = video.with_suffix(".srt")
    if tam.exists():
        return tam
    adaylar = [p for p in video.parent.glob("*.srt") if video.stem.startswith(p.stem)]
    return max(adaylar, key=lambda p: len(p.stem)) if adaylar else None


def altyazi_yaz(video: Path, s: dict, hedef: Path, z: dict | None = None) -> str | None:
    """şablonun altyazısını kopyalar ya da seslendirme kaydından kurar; dönüş: kaynak"""
    bulunan = _altyazi_bul(video)
    if bulunan:
        shutil.copyfile(bulunan, hedef / "altyazi.srt")
        vtt = bulunan.with_suffix(".vtt")
        if vtt.exists():
            shutil.copyfile(vtt, hedef / "altyazi.vtt")
        return "şablon"
    ses_dizini = video.parent / "seslendirme"
    sb = (z or s).get("seslendirme")
    sb = sb if isinstance(sb, dict) else {}
    satirlar = [x for x in sb.get("satirlar") or [] if isinstance(x.get("t"), (int, float))]
    if not satirlar or not (ses_dizini / "seslendirme.json").exists():
        return None
    gs = altyazi.gruplar(altyazi.kelimeler(satirlar, ses_dizini))
    if not gs:
        return None
    (hedef / "altyazi.srt").write_text(altyazi.srt(gs), encoding="utf-8")
    (hedef / "altyazi.vtt").write_text(altyazi.vtt(gs), encoding="utf-8")
    return "seslendirme"


def _zaman(t: float) -> str:
    t = int(round(t))
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def bolum_listesi(video: Path, z: dict | None, toplam: float) -> str | None:
    """Kurgunun yazdığı liste, yoksa sahne dilinin başlık/geçiş sahneleri. YouTube: ilk 0:00, ≥ 3 bölüm, her biri ≥ 10 sn."""
    if toplam < UZUN_SN:
        return None
    hazir = sorted(video.parent.glob("*-bolumler.txt"))
    if hazir:
        return hazir[0].read_text(encoding="utf-8")
    bas = []
    for sh in (z or {}).get("sahneler") or []:
        ad = sh.get("metin") if sh.get("tip") in ("baslik", "gecis") else None
        if ad and (not bas or sh["bas"] - bas[-1][0] >= 10):
            bas.append((0.0 if not bas else sh["bas"], ad))
    if len(bas) < 3:
        return None
    return "\n".join(f"{_zaman(t)} {ad}" for t, ad in bas) + "\n"


def _bagla(kaynak: Path, hedef: Path) -> None:
    if hedef.exists():
        if hedef.stat().st_ino == kaynak.stat().st_ino:
            return
        hedef.unlink()
    try:
        os.link(kaynak, hedef)
    except OSError:
        shutil.copyfile(kaynak, hedef)


def paketle(video: Path, senaryo: Path, siparis: dict | None = None, hedef: Path | None = None) -> dict:
    video, senaryo = Path(video), Path(senaryo)
    s = json.loads(senaryo.read_text(encoding="utf-8"))
    kok = Path((siparis or {}).get("_klasor") or video.parent.parent)
    hedef = Path(hedef) if hedef else kok / "yayin" / video.stem
    hedef.mkdir(parents=True, exist_ok=True)
    dil = video_dili(s, siparis)
    toplam = sure(video)
    w, h = boyut(video)
    z = _sahne_zamanlari(s, video.parent / "seslendirme")
    _bagla(video, hedef / video.name)
    dosyalar = [video.name]
    an = kapak_ani(s, z, toplam)
    sablon_kapak = None if isinstance((s.get("yayin") or {}).get("kapak"), (int, float)) else _onek_bul(video, "*-kapak.png")
    kaynak, kaynak_an = (sablon_kapak, 0.0) if sablon_kapak else (video, an)
    if kare_al(kaynak, kaynak_an, hedef / "kapak.jpg"):
        dosyalar.append("kapak.jpg")
    if w > h and kare_al(kaynak, kaynak_an, hedef / "kapak-youtube.jpg", (1280, 720)):
        dosyalar.append("kapak-youtube.jpg")
    alt = altyazi_yaz(video, s, hedef, z)
    if alt:
        dosyalar += ["altyazi.srt"] + (["altyazi.vtt"] if (hedef / "altyazi.vtt").exists() else [])
    bolumler = bolum_listesi(video, z, toplam)
    if bolumler:
        (hedef / "bolumler.txt").write_text(bolumler, encoding="utf-8")
        dosyalar.append("bolumler.txt")
    m = oneriler(s, siparis, dil, bolumler, kisa=h > w and toplam <= 180)
    bulgular = denetle(m)
    if not alt and seslendirme_metni(s):
        bulgular.append({"seviye": "uyari", "yer": "altyazi", "mesaj": "altyazı bulunamadı (seslendirme kaydı yok)"})
    paket = {"video": video.name, "kaynak_video": str(video), "senaryo": str(senaryo), "dil": dil,
             "sure_sn": round(toplam, 2), "boyut": [w, h],
             "kapak": sablon_kapak.name if sablon_kapak else f"{an:g} sn", "altyazi": alt, "dosyalar": dosyalar,
             "metin": m, "bulgular": bulgular}
    (hedef / "metin.json").write_text(json.dumps(paket, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (hedef / "YUKLE.md").write_text(yukle_md(paket), encoding="utf-8")
    paket["klasor"] = str(hedef)
    return paket


def yukle_md(p: dict) -> str:
    m = p["metin"]
    yt = m["youtube"]
    satir = [f"# Yayın paketi: {p['video']}", "",
             f"Dil: {p['dil']} · {p['sure_sn']:g} sn · {p['boyut'][0]}×{p['boyut'][1]} · metin kaynağı: {m['kaynak']}", "",
             "Dosyalar: " + ", ".join(f"`{d}`" for d in p["dosyalar"]), ""]
    if p["bulgular"]:
        satir += ["**Kontrol:**", *[f"- {b['seviye'].upper()} {b['yer']}: {b['mesaj']}" for b in p["bulgular"]], ""]
    satir += ["## YouTube", "", "Başlık:", "```", yt["baslik"], "```", "Açıklama:", "```", yt["aciklama"], "```",
              "Etiketler:", "```", ", ".join(yt["etiketler"]), "```", "",
              "## Instagram", "", "```", m["instagram"]["aciklama"], "```", "",
              "## TikTok", "", "```", m["tiktok"]["aciklama"], "```", ""]
    if "altyazi.srt" in p["dosyalar"]:
        satir += ["Altyazı: `altyazi.srt` YouTube'a (Altyazılar → Dosya yükle) ve TikTok'a yüklenir; Instagram "
                  "altyazıyı kendisi üretir ya da yakılı sürüm kullanılır.", ""]
    return "\n".join(satir)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    a1 = alt.add_parser("paket", help="bir video için yayın klasörü yaz")
    a1.add_argument("video")
    a1.add_argument("--senaryo", required=True)
    a1.add_argument("--siparis")
    a1.add_argument("-o", "--cikti")
    a = ap.parse_args(argv)
    sp = None
    if a.siparis:
        sp = json.loads(Path(a.siparis).read_text(encoding="utf-8"))
        sp["_klasor"] = str((Path(a.siparis).resolve().parent / sp.get("klasor", ".")).resolve())
    p = paketle(Path(a.video), Path(a.senaryo), sp, Path(a.cikti) if a.cikti else None)
    print(f"yayın paketi: {p['klasor']} ({', '.join(p['dosyalar'])})")
    for b in p["bulgular"]:
        print(f"  {b['seviye']} {b['yer']}: {b['mesaj']}")
    return 1 if any(b["seviye"] == "hata" for b in p["bulgular"]) else 0


if __name__ == "__main__":
    sys.exit(main())
