"""Tek komutla sipariş: siparis.json → önizleme → (Atilla onayından sonra) ses + render + kalite + DEVIR + maliyet.

    python3 platform/ortak/uret.py siparis.json                 # 1. denetim + önizleme sayfası, onayda durur
    python3 platform/ortak/uret.py siparis.json --onay [--stil a,b]  # 2. ses, render, kalite kapısı, DEVIR.md
    python3 platform/ortak/uret.py siparis.json --kapat --usd 1.42 --cevap 4 --cikti-token 21000 --okuma-token 2400000
    python3 platform/ortak/uret.py siparis.json --durum

Önizlemeden sonra komut durur: tam render Atilla onay vermeden yapılmaz (uretim-standardi.md §1). Siparişte
`"direkt": true` varsa (Atilla "direkt üret" dediyse) ya da `--direkt` verilirse önizlemeden sonra sürer.
Birden çok stil varsa önizleme hepsini tek sayfada gösterir; `--onay --stil` yalnız seçilenleri render eder.
Kalite kapısında `kaldi` çıkan video teslim edilmez: durum `kaldi` olur, DEVIR yazılmaz, çıkış kodu 1.

siparis.json (yollar siparişin klasörüne göredir):

    {"is": "markalasma-nedir", "baslik": "Markalaşma nedir?",
     "senaryolar": [{"stil": "tek-cizgi", "senaryo": "tek-cizgi.json"}],   # ya da tek: "senaryo": "a.json"
     "format": "9:16", "ses": {"saglayici": "otomatik", "ses": "liam"},
     "klasor": ".", "direkt": false, "tur": "uretim", "notlar": ["kanal 1, 'siz' hitabı"]}

Durum `<klasor>/siparis-durum.json` dosyasındadır; yeni bir thread oradan ve DEVIR.md'den devam eder.
Önizlemeyle birlikte her stil için küçük, sessiz bir animatik (`animatik.mp4`, hareketi onaydan önce görmek
için) çizilir; siparişte `"animatik": false` bunu kapatır. Teslim edilen videolar teslim kataloğuna
(`katalog.py`) yazılır. Sipariş stüdyo panelinden geldiyse (`"panel": {"id": ...}`, `panel.py siparis` yazar)
her aşamada `panel-durum.json` yazılır; thread onu `ArtifactData` ile panele geri yazar.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BURADA = Path(__file__).resolve().parent
SABLONLAR = BURADA.parent / "sablonlar"
sys.path.insert(0, str(BURADA))
import animatik  # noqa: E402
import kalite  # noqa: E402
import katalog  # noqa: E402
import onizleme  # noqa: E402
import panel  # noqa: E402
import render_suresi  # noqa: E402
from formatlar import coz  # noqa: E402

PAYLASIM = Path(os.environ.get("STUDYO_PAYLASIM", "/mnt/project-files"))
MALIYET_ALANLARI = ["tarih", "is", "tur", "stil_sayisi", "video_sayisi", "revizyon_turu", "cevap_sayisi",
                    "cikti_token", "onbellek_okuma_token", "kullanim_usd", "elevenlabs_karakter"]
TEK_ADIM = {"neon", "karusel"}  # ayrı seslendir/render komutu yok, `uret` çalışır
DURUM = "siparis-durum.json"


# ---------------------------------------------------------------- sipariş

def oku(yol: Path) -> dict:
    yol = Path(yol).resolve()
    s = json.loads(yol.read_text(encoding="utf-8"))
    hata = []
    if not s.get("is"):
        hata.append('"is" (kısa iş adı) yok')
    girdiler = s.get("senaryolar") or ([{"stil": s.get("stil"), "senaryo": s["senaryo"]}] if s.get("senaryo") else [])
    if not girdiler:
        hata.append('"senaryo" ya da "senaryolar" yok')
    for g in girdiler:
        g["senaryo"] = str((yol.parent / g["senaryo"]).resolve())
        if not Path(g["senaryo"]).exists():
            hata.append(f"senaryo bulunamadı: {g['senaryo']}")
            continue
        senaryo = json.loads(Path(g["senaryo"]).read_text(encoding="utf-8"))
        g["stil"] = stil_bul(senaryo, Path(g["senaryo"]), g.get("stil"))
        if g["stil"] not in bilinen_stiller():
            hata.append(f"tanımsız stil: {g['stil']} ({g['senaryo']}); siparişte \"stil\" yazın")
    if hata:
        raise ValueError("; ".join(hata))
    s["senaryolar"] = girdiler
    s["_yol"] = str(yol)
    s["_klasor"] = str((yol.parent / s.get("klasor", ".")).resolve())
    return s


def bilinen_stiller() -> set[str]:
    sys.path.insert(0, str(SABLONLAR / "stil"))
    try:
        import stil
        return set(stil.TUM_STILLER) | set(onizleme.KOMUTLAR)
    except Exception:  # stil motoru yüklenemezse (skia yok) yalnız kendi komutu olan şablonlar
        return set(onizleme.KOMUTLAR) | onizleme._stil_secenekleri()


def stil_bul(senaryo: dict, yol: Path, ad: str | None) -> str:
    """Sipariş → senaryonun "stil" alanı → dosya adı (risograf.json) → önizlemenin klasör tahmini."""
    if ad or senaryo.get("stil"):
        return ad or senaryo["stil"]
    kok = yol.stem.replace("_", "-")
    return kok if kok in bilinen_stiller() else onizleme.sablon_bul(senaryo, yol, None)


def durum_oku(s: dict) -> dict:
    p = Path(s["_klasor"]) / DURUM
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"is": s["is"], "gecmis": []}


def durum_yaz(s: dict, d: dict, asama: str, **ek) -> dict:
    d.update(ek, asama=asama, zaman=time.strftime("%Y-%m-%dT%H:%M:%S"))
    d.setdefault("gecmis", []).append(f"{d['zaman']} {asama}")
    p = Path(s["_klasor"]) / DURUM
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    panel.durum_yaz(s, d)
    return d


# ---------------------------------------------------------------- şablon komutları

def sablon_komutu(stil: str, alt: str, senaryo: str, cikti: Path, ek: list[str] = ()) -> list[str]:
    if stil in onizleme.KOMUTLAR:
        return [sys.executable, str(SABLONLAR / onizleme.KOMUTLAR[stil]), alt, senaryo, "-o", str(cikti), *ek]
    return [sys.executable, str(SABLONLAR / "stil" / "stil.py"), alt, senaryo, "-o", str(cikti), *ek, "--stil", stil]


def ses_bayraklari(s: dict) -> list[str]:
    ses = s.get("ses") or {}
    return (["--saglayici", ses["saglayici"]] if ses.get("saglayici") else []) + (["--ses", ses["ses"]] if ses.get("ses") else [])


def fmt_yazimi(stil: str, f: str) -> str:
    return f.replace("x", ":") if stil in onizleme.IKI_NOKTALI else f


def calistir(cmd: list[str], ortam: dict | None = None) -> tuple[int, str]:
    """Şablonu çalıştırır; tam log dosyaya değil, yalnız son satırlar geri döner (token disiplini)."""
    r = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, **(ortam or {})})
    kuyruk = "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])
    return r.returncode, kuyruk


def cikti_klasoru(s: dict, g: dict) -> Path:
    tek = len(s["senaryolar"]) == 1
    return Path(s["_klasor"]) / ("cikti" if tek else f"cikti-{g['stil']}")


def mp4ler(k: Path) -> dict[Path, float]:
    return {p: p.stat().st_mtime for p in k.glob("*.mp4")} if k.exists() else {}


# ---------------------------------------------------------------- aşamalar

def asama_onizleme(s: dict, d: dict) -> int:
    for g in s["senaryolar"]:
        kod, kuyruk = calistir(sablon_komutu(g["stil"], "denetle", g["senaryo"], cikti_klasoru(s, g)))
        if kod:
            print(f"HATA: {g['stil']} senaryosu denetimden geçmedi:\n{kuyruk}", file=sys.stderr)
            durum_yaz(s, d, "senaryo-hatali", hata=kuyruk.splitlines()[-1:] or [])
            return 1
    fmt = coz(s.get("format"), json.loads(Path(s["senaryolar"][0]["senaryo"]).read_text(encoding="utf-8")))[0]
    hedef = Path(s["_klasor"]) / "onizleme.png"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    rapor = onizleme.onizle([f"{g['stil']}={g['senaryo']}" for g in s["senaryolar"]], hedef, fmt=fmt)
    hatali = [x for x in rapor["stiller"] if x.get("hata")]
    notlar = [f"{x['stil']} {k['an']:g} sn banding %{k['banding'] * 100:.0f}" for x in rapor["stiller"]
              for k in x["kareler"] if k["banding"] >= kalite.ESIK["banding_uyari"]]
    if hatali:
        durum_yaz(s, d, "onizleme-hatali", onizleme=None, onizleme_notlari=notlar)
        for x in hatali:
            print(f"HATA: {x['stil']} karesi çizilemedi: {x['hata']}", file=sys.stderr)
        return 1
    animatikler = animatik_yap(s, fmt) if s.get("animatik", True) else []
    durum_yaz(s, d, "onizleme", onizleme=str(hedef), onizleme_notlari=notlar, animatik=animatikler,
              stiller=[g["stil"] for g in s["senaryolar"]])
    print(f"önizleme: {hedef}" + (f" (uyarı: {', '.join(notlar)})" if notlar else ""))
    for a in animatikler:
        print(f"animatik: {a['dosya']} ({a['animatik_sn']} sn, {a['hiz']}x hız)" if a.get("dosya")
              else f"animatik yok ({a['stil']}): {a['hata']}")
    return 0


def animatik_yap(s: dict, fmt: str) -> list[dict]:
    """Her stil için küçük animatik; hata önizlemeyi durdurmaz, yalnız not edilir."""
    tek = len(s["senaryolar"]) == 1
    sonuc = []
    for g in s["senaryolar"]:
        hedef = Path(s["_klasor"]) / ("animatik.mp4" if tek else f"animatik-{g['stil']}.mp4")
        try:
            r = animatik.animatik(f"{g['stil']}={g['senaryo']}", hedef, fmt=fmt)
        except Exception as e:  # noqa: BLE001 - animatik yardımcıdır, sipariş akışını kesmez
            r = {"stil": g["stil"], "dosya": None, "hata": str(e)}
        sonuc.append({k: r.get(k) for k in ("stil", "dosya", "animatik_sn", "hiz", "hata") if r.get(k) is not None})
    return sonuc


def asama_uretim(s: dict, d: dict, secim: list[str] | None) -> int:
    girdiler = [g for g in s["senaryolar"] if not secim or g["stil"] in secim]
    if not girdiler:
        print(f"HATA: seçilen stil siparişte yok ({', '.join(secim)}); siparişte: "
              f"{', '.join(g['stil'] for g in s['senaryolar'])}", file=sys.stderr)
        return 1
    if not d.get("onizleme"):
        print("HATA: önce önizleme (komutu bayraksız çalıştırın); onaydan önce render yok", file=sys.stderr)
        return 1
    durum_yaz(s, d, "onaylandi", secilen=[g["stil"] for g in girdiler])
    paylasim_csv = PAYLASIM / "gelistirme" / "render-sureleri.csv"
    videolar, karakter = [], 0
    for g in girdiler:
        cikti = cikti_klasoru(s, g)
        senaryo = json.loads(Path(g["senaryo"]).read_text(encoding="utf-8"))
        if g["stil"] not in TEK_ADIM and senaryo.get("seslendirme"):
            kod, kuyruk = calistir(sablon_komutu(g["stil"], "seslendir", g["senaryo"], cikti, ses_bayraklari(s)))
            if kod:
                print(f"HATA: {g['stil']} seslendirmesi:\n{kuyruk}", file=sys.stderr)
                durum_yaz(s, d, "ses-hatali")
                return 1
            sj = cikti / "seslendirme" / "seslendirme.json"
            if sj.exists():
                kayit = json.loads(sj.read_text(encoding="utf-8"))
                karakter += (kayit.get("kullanim") or {}).get("karakter", 0)
                bilerek = (s.get("ses") or {}).get("saglayici") == kayit.get("saglayici")
                if kayit.get("saglayici") != "elevenlabs" and not bilerek:
                    print(f"HATA: {g['stil']} sesi {kayit.get('saglayici')} yedeğiyle üretildi (ElevenLabs anahtarı, ağı "
                          "ya da kredisi yok); yedek ses teslim edilmez, render yapılmadı", file=sys.stderr)
                    durum_yaz(s, d, "ses-yedek")
                    return 1
        for f in coz(s.get("format"), senaryo):
            once = mp4ler(cikti)
            alt = "uret" if g["stil"] in TEK_ADIM else "render"
            ortam = {"STUDYO_RENDER_BASLANGIC": str(time.time()), "STUDYO_STIL": g["stil"]}
            ek = [] if g["stil"] == "karusel" else ["--format", fmt_yazimi(g["stil"], f)]
            print(f"render: {g['stil']} {f} ...", flush=True)
            kod, kuyruk = calistir(sablon_komutu(g["stil"], alt, g["senaryo"], cikti, ek), ortam)
            if kod:
                print(f"HATA: {g['stil']} {f} render:\n{kuyruk}", file=sys.stderr)
                durum_yaz(s, d, "render-hatali", hata=kuyruk.splitlines()[-1:] or [])
                return 1
            for p, t in mp4ler(cikti).items():
                if once.get(p) != t:
                    videolar.append(kapi(p, s, f, g["stil"], paylasim_csv))
    kalan = [v for v in videolar if v["sonuc"] == "kaldi"]
    d = durum_yaz(s, d, "kaldi" if kalan else "teslim", videolar=videolar, elevenlabs_karakter=karakter)
    for v in videolar:
        sure = f", render {v['render_sn']} sn ({v['sn_kare']} sn/kare)" if v.get("render_sn") is not None else ""
        print(f"{kalite.ETIKET[v['sonuc']]}: {v['dosya']}{sure}")
        for b in v["bulgular"]:
            print(f"  {b}")
    if kalan:
        print("KALDI: teslim edilmez. Sorunu düzeltip `--onay` ile yeniden çalıştırın.", file=sys.stderr)
        return 1
    if PAYLASIM.exists():
        katalog.ekle(katalog.siparisten(s, d), katalog.yol(PAYLASIM))
    notlar = [*s.get("notlar", []), f"stil: {', '.join(g['stil'] for g in girdiler)}"]
    subprocess.run([sys.executable, str(BURADA / "devir.py"), s["_klasor"], *sum((["--not", n] for n in notlar), [])],
                   check=True, capture_output=True)
    print(f"DEVIR.md yazıldı. ElevenLabs: {karakter} karakter. Kapanışta maliyet satırı: "
          f"uret.py {Path(s['_yol']).name} --kapat --usd <get_session> --cevap <n> --cikti-token <n> --okuma-token <n>")
    return 0


def kapi(video: Path, s: dict, fmt: str, stil: str, csv_yolu: Path) -> dict:
    """Şablonun yazdığı kalite raporunu okur (yoksa kapıyı burada çalıştırır) ve render süresini kaydeder."""
    rj = video.with_suffix(".kalite.json")
    if rj.exists() and rj.stat().st_mtime >= video.stat().st_mtime:
        r = json.loads(rj.read_text(encoding="utf-8"))
    else:  # şablon kapıyı çalıştırmadıysa (STUDYO_KALITE=0 ya da eski şablon) burada çalışır
        r = kalite.denetle(video, kontakt=video.with_suffix(".kontakt.png"))
        rj.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    if PAYLASIM.exists():
        render_suresi.kaydet(csv_yolu, s["is"], fmt, r)
    o = r.get("render") or {}
    return {"dosya": str(video), "stil": stil, "format": fmt, "sonuc": r["sonuc"],
            "kontakt": r.get("kontakt"), "render_sn": o.get("render_sn"), "sn_kare": o.get("sn_kare"),
            "bulgular": [f"{b['seviye']} {b['kontrol']}: {b['mesaj']}" for b in r["bulgular"] if b["seviye"] != "bilgi"]}


def maliyet_satiri(s: dict, d: dict, a: argparse.Namespace) -> list:
    videolar = d.get("videolar") or []
    return [time.strftime("%Y-%m-%d"), s.get("baslik") or s["is"], s.get("tur", "uretim"),
            len({v["stil"] for v in videolar}) or len(s["senaryolar"]), len(videolar), a.revizyon, a.cevap,
            a.cikti_token, a.okuma_token, f"{a.usd:.2f}", d.get("elevenlabs_karakter", 0)]


def asama_kapat(s: dict, d: dict, a: argparse.Namespace) -> int:
    if d.get("asama") != "teslim":
        print(f"HATA: sipariş teslim aşamasında değil ({d.get('asama')}); maliyet satırı teslimden sonra yazılır",
              file=sys.stderr)
        return 1
    hedef = Path(a.maliyet_csv) if a.maliyet_csv else PAYLASIM / "gelistirme" / "maliyet.csv"
    yeni = not hedef.exists()
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with hedef.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if yeni:
            w.writerow(MALIYET_ALANLARI)
        w.writerow(maliyet_satiri(s, d, a))
    durum_yaz(s, d, "kapandi", maliyet=str(hedef))
    if PAYLASIM.exists():
        katalog.ekle(katalog.siparisten(s, d, a.usd), katalog.yol(PAYLASIM))
    print(f"maliyet satırı eklendi: {hedef}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("siparis")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--onay", action="store_true", help="Atilla önizlemeyi onayladı: ses, render, kalite, DEVIR")
    g.add_argument("--kapat", action="store_true", help="teslimden sonra maliyet satırını yaz")
    g.add_argument("--durum", action="store_true", help="siparişin aşamasını göster")
    ap.add_argument("--direkt", action="store_true", help='önizlemede durma (Atilla "direkt üret" dediyse)')
    ap.add_argument("--stil", help="birden çok stilden onaylananlar, virgülle")
    ap.add_argument("--usd", type=float, help="get_session → external_metadata.usage (tahmin edilmez)")
    ap.add_argument("--cevap", type=int, default=0)
    ap.add_argument("--cikti-token", type=int, default=0)
    ap.add_argument("--okuma-token", type=int, default=0)
    ap.add_argument("--revizyon", type=int, default=0)
    ap.add_argument("--maliyet-csv")
    a = ap.parse_args(argv)
    try:
        s = oku(Path(a.siparis))
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"HATA: sipariş okunamadı: {e}", file=sys.stderr)
        return 2
    d = durum_oku(s)
    if a.durum:
        print(json.dumps({k: d.get(k) for k in ("asama", "zaman", "onizleme", "secilen", "videolar")},
                         ensure_ascii=False, indent=1))
        return 0
    if a.kapat:
        if a.usd is None:
            print("HATA: --usd gerekli (get_session kullanımından)", file=sys.stderr)
            return 2
        kod = asama_kapat(s, d, a)
        if not kod and (s.get("panel") or {}).get("id"):
            print(panel.hatirlatma(s))
        return kod
    secim = [x.strip() for x in a.stil.split(",")] if a.stil else None
    kod = asama_uretim(s, d, secim) if a.onay else asama_onizleme(s, d)
    if not a.onay and not kod:
        if a.direkt or s.get("direkt"):
            kod = asama_uretim(s, d, secim)
        else:
            print(f"Atilla onayı bekleniyor. Onaydan sonra: uret.py {Path(s['_yol']).name} --onay"
                  + (" --stil <seçilen>" if len(s["senaryolar"]) > 1 else ""))
    if (s.get("panel") or {}).get("id"):
        print(panel.hatirlatma(s))
    return kod


if __name__ == "__main__":
    sys.exit(main())
