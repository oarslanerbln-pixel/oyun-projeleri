"""Kurgu: uzun video için sahne birleştirici; birden çok şablonun sahneleri tek videoda, tek müzik ve tek ses izinde.

Bir `kurgu.json` sahneleri sıralar; her sahne kendi şablonunun senaryo dosyasıdır (kinetik, analiz,
karakalem). Sahneler kendi şablonuyla sessiz çizilir, geçişlerle (erime, kaydırma, kesme) birleşir;
seslendirme bütün sahnelerin satırlarından tek seferde üretilir, müzik baştan sona tek parça çalar ve
her sahnenin `enerji`sine göre sakinleşir ya da coşar.

    python3 platform/sablonlar/kurgu/kurgu.py denetle   kurgu.json
    python3 platform/sablonlar/kurgu/kurgu.py onizle    kurgu.json        # her sahneden 3 kare, tek sayfa
    python3 platform/sablonlar/kurgu/kurgu.py kare      kurgu.json --an 5 30   # kurgu zamanında tek tek kareler
    python3 platform/sablonlar/kurgu/kurgu.py seslendir kurgu.json [--saglayici elevenlabs --ses <id>]
    python3 platform/sablonlar/kurgu/kurgu.py render    kurgu.json [--format 16:9|9:16|1:1|4:5|ikisi]
    python3 platform/sablonlar/kurgu/kurgu.py uret      kurgu.json        # seslendirme eksikse üretir, sonra render
Çıktı varsayılanı kurgu dosyasının yanındaki `cikti/`. Format verilmezse kurgunun `format` alanı, o da yoksa 16:9.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BURADA = Path(__file__).resolve().parent
SABLONLAR = BURADA.parent
sys.path.insert(0, str(BURADA))
sys.path.insert(0, str(SABLONLAR.parent / "ortak"))
sys.path.insert(0, str(SABLONLAR.parent / "ses"))
import akis  # noqa: E402
from formatlar import FORMATLAR, bilinmeyenler, coz  # noqa: E402

# sahne olarak kullanılabilen şablonlar: klasör, senaryoyu yükleyen modül, komut satırı
STILLER = {
    "kinetik": {"klasor": "kinetik", "yukle": "zaman", "komut": "kinetik.py"},
    "analiz": {"klasor": "analiz", "yukle": "analiz", "komut": "analiz.py", "iki_nokta": True, "ses": "muzik"},
    "karakalem": {"klasor": "karakalem", "yukle": "zaman", "komut": "karakalem.py"},
    "karakalem_anlatim": {"klasor": "karakalem_anlatim", "yukle": "zaman", "komut": "anlatim.py"},  # serbest karakalem sahneleri
    "tek_cizgi": {"klasor": "tek_cizgi", "yukle": "zaman", "komut": "tek_cizgi.py"},
    "kolaj": {"klasor": "kolaj", "yukle": "zaman", "komut": "kolaj.py"},
    "golge_oyunu": {"klasor": "golge_oyunu", "yukle": "zaman", "komut": "golge_oyunu.py"},
    "origami": {"klasor": "origami", "yukle": "zaman", "komut": "origami.py"},
    "ekran": {"klasor": "ekran", "yukle": "zaman", "komut": "ekran.py"},  # kalkış tabelası, VHS, akış alanı
    **{ad: {"klasor": "desen", "yukle": "zaman", "komut": "desen.py"} for ad in ("vitray", "linol", "cini", "teknik-cizim")},
}
# her şablonun `miksle(s, klasor, seslendirme)` işlevini taşıyan modül (sahne efektleri `efekt.wav` kökü olarak alınır)
SES_MODULU = "sentez"
AZAMI_UZATMA = 1.25  # sn; kesmeyi vuruşa oturtmak için sahnenin son karesi en çok bu kadar tutulur
# İmza stil geçişleri (sahne dilindeki karisim.py ile aynı biçim): xfade özel ifadesi, P 1 → 0 akar. Yeni sahne dalgalı
# kenarlı çapraz bir fırça darbesiyle (firca) ya da ortadan yayılan bir mürekkep lekesiyle (murekkep) gelir; kenarda
# ince koyu mürekkep çizgisi. Karakalemden vitraya, çiniden VHS'e: farklı şablonlar arasında stil değişimini gösterir.
# xfade ifadeyi dilim dilim paralel çalıştırır; st()/ld() kayıtları iş parçacıkları arasında paylaşıldığı için
# kullanılmaz, ara değerler metin olarak yerine konur.
def _ifade(uzaklik: str) -> str:
    q = "((1-P)*(1-P)*(1+2*P))"  # yumuşak başlayıp biten ilerleme (smoothstep)
    d = uzaklik.replace("Q", q)  # maske kenarına işaretli uzaklık (piksel/2); artıda yeni sahne
    a = f"clip({d}+0.5,0,1)"
    c = f"((1-clip(abs({d})/3,0,1))*sin(PI*{q}))"  # mürekkep çizgisi
    v = f"(B*{a}+A*(1-{a}))"
    return f"if(eq(PLANE,0),{v}*(1-0.85*{c})+18.7*{c},{v}*(1-{c})+128*{c})"


_FIRCA = _ifade("((Q*1.38-0.08-0.22*Y/H+0.08*(0.55*sin(Y/H*8.17+1.1)+0.3*sin(Y/H*23.2+0.4)+0.15*sin(Y/H*57.2))"
                "-X/W)*W/2)")
_ACI = "atan2(Y/H-0.46,(X/W-0.5)*W/H)"
_MUREKKEP = _ifade(f"((Q*0.62*hypot(W,H)/H*(1+0.1*sin(5*{_ACI})+0.05*sin(11*{_ACI}+1.3)+0.025*sin(23*{_ACI}))"
                   "-hypot((X/W-0.5)*W/H,Y/H-0.46))*H/2)")
GECISLER = {"kesme": None, "erime": "fade", "kaydir": "slideleft", "silme": "wipeleft",
            "firca": f"custom:expr='{_FIRCA}'", "murekkep": f"custom:expr='{_MUREKKEP}'"}
ENERJI = {"sakin": 0, "orta": 1, "enerjik": 2}
VARSAYILAN_AKORLAR = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 52, 55, 60], [55, 59, 62, 67]]  # Am F C G


class KurguHatasi(ValueError):
    pass


def yukle(yol: str | Path) -> dict:
    """kurgu.json + sahne senaryoları; zaman çizelgesi (`_bas`, `_sure`, `_gecis`) hesaplanır."""
    yol = Path(yol)
    k = json.loads(yol.read_text(encoding="utf-8"))
    k["_klasor"] = str(yol.resolve().parent)
    k.setdefault("fps", 30)
    k.setdefault("seslendirme", {})
    k.setdefault("muzik", {})
    k["muzik"].setdefault("bpm", 100)
    k["muzik"].setdefault("akorlar", VARSAYILAN_AKORLAR)
    k["muzik"].setdefault("vurusa_otur", True)
    k["muzik"].setdefault("gecis_sesi", "otomatik")
    vg = {"tur": "erime", "sure": 0.5, **(k.get("gecis") or {})}
    bas = 0.0
    for i, sh in enumerate(k.get("sahneler") or []):
        sh.setdefault("id", f"s{i + 1}")
        sh.setdefault("enerji", "orta")
        sh["_yol"] = str(Path(k["_klasor"]) / sh.get("senaryo", ""))
        try:
            sh["_s"] = json.loads(Path(sh["_yol"]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            sh["_s"] = {}
            sh["_yukleme_hatasi"] = str(e)
        sure = sh["_s"].get("sure")
        if sure is None and sh["_s"].get("sahneler"):  # karakalem_anlatim: süre sahnelerin toplamı
            sure = sum(x.get("sure", 0) for x in sh["_s"]["sahneler"] if isinstance(x.get("sure"), (int, float)))
        # kare sayısına yuvarlanır: birleştirmede sahneler kare kare art arda gelir
        sh["_sure"] = round(sure * k["fps"]) / k["fps"] if isinstance(sure, (int, float)) and sure > 0 else 0.0
        g = sh.get("gecis", vg) if i else {"tur": "kesme", "sure": 0}
        g = {"tur": g, "sure": vg["sure"]} if isinstance(g, str) else {**vg, **g}
        if g["tur"] == "kesme":
            g["sure"] = 0.0
        g["sure"] = round(g["sure"] * k["fps"]) / k["fps"]
        sh["_gecis"] = g
        sh["_uzat"] = 0.0
        if i and k["muzik"]["vurusa_otur"] and sh["_sure"] and isinstance(k["muzik"]["bpm"], (int, float)):
            bas += _vurusa_uzat(k, k["sahneler"][i - 1], sh, bas, g["sure"])
        bas = max(0.0, bas - g["sure"])
        sh["_bas"] = round(bas, 6)
        sh["_kesme"] = round(bas + g["sure"] / 2, 6) if i else 0.0
        bas += sh["_sure"]
    k["sure"] = round(bas, 6)
    return k


def _vurusa_uzat(k: dict, onceki: dict, sh: dict, son: float, gecis: float) -> float:
    """Kesme anını (geçişin ortası) müziğin vuruşuna oturtur: önceki sahnenin son karesi biraz tutulur.

    Müzik t=0'da başlar, ızgara bpm'den bellidir. Enerji yükseliyorsa kesme güçlü vuruşa (1. ya da 3.)
    gider, yoksa en yakın sonraki vuruşa. Uzatma kare sayısına yuvarlanır ve `AZAMI_UZATMA`yı geçmez.
    """
    import miks
    kesme = son - gecis / 2
    bpm = k["muzik"]["bpm"]
    yukselir = ENERJI.get(sh.get("enerji"), 1) > ENERJI.get(onceki.get("enerji"), 1)
    hedef = miks.sonraki_vurus(kesme, bpm, her=2 if yukselir else 1)
    if hedef - kesme > AZAMI_UZATMA:
        hedef = miks.sonraki_vurus(kesme, bpm)
    uzat = round(max(0.0, hedef - kesme) * k["fps"]) / k["fps"]
    if uzat > AZAMI_UZATMA:
        return 0.0
    onceki["_sure"] = round(onceki["_sure"] + uzat, 6)
    onceki["_uzat"] = round(onceki["_uzat"] + uzat, 6)
    return uzat


def satirlar(k: dict) -> list[dict]:
    """Bütün sahnelerin seslendirme satırları, kurgu zamanında; kimlik `<sahne>-<satır>`."""
    out = []
    for sh in k["sahneler"]:
        for x in sh["_s"].get("seslendirme", {}).get("satirlar", []):
            y = {"id": f"{sh['id']}-{x['id']}", "metin": x["metin"], "t": round(sh["_bas"] + x["t"], 3),
                 "_sahne": sh["id"], "_yerel": x["id"], "_son": sh["_bas"] + sh["_sure"]}
            if "okunus" in x:
                y["okunus"] = x["okunus"]
            out.append(y)
    return out


def bolumler(k: dict) -> list[dict]:
    """Müzik ve YouTube bölümleri için sahne sınırları."""
    return [{"id": sh["id"], "baslik": sh.get("baslik", sh["id"]), "bas": sh["_bas"], "son": sh["_bas"] + sh["_sure"],
             "kesme": sh.get("_kesme", sh["_bas"]), "enerji": ENERJI.get(sh["enerji"], 1), "stil": sh.get("stil")}
            for sh in k["sahneler"]]


def _sahne_denetle(sh: dict) -> list[str]:
    st = STILLER[sh["stil"]]
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([sys.executable, str(SABLONLAR / st["klasor"] / st["komut"]), "denetle", sh["_yol"], "-o", tmp],
                           capture_output=True, text=True)
    if r.returncode == 0:
        return []
    satir = [x.removeprefix("HATA: ") for x in r.stderr.splitlines() if x.strip()]
    return satir[-6:] or [f"{st['komut']} denetle çıkış kodu {r.returncode}"]


def denetle(k: dict, sureler: dict[str, float] | None = None, sahneler: bool = True) -> list[str]:
    """HATA listesi; boşsa kurgu render'a hazır. `sahneler=True` her sahneyi kendi şablonunun denetimiyle de geçirir."""
    h = []
    if k.get("format") and bilinmeyenler(k["format"]):
        h.append(f"format bilinmiyor: {k['format']}")
    if not isinstance(k["fps"], int) or not 24 <= k["fps"] <= 60:
        h.append("fps 24–60 arasında tam sayı olmalı")
    bpm = k["muzik"]["bpm"]
    if not isinstance(bpm, (int, float)) or not 60 <= bpm <= 160:
        h.append("muzik.bpm 60–160 arasında olmalı")
    sh_ler = k.get("sahneler") or []
    if not sh_ler:
        return h + ["en az bir sahne gerekli"]
    gorulen = set()
    for i, sh in enumerate(sh_ler):
        ad = f"sahne {sh['id']}"
        if sh["id"] in gorulen:
            h.append(f"{ad}: kimlik tekrar ediyor")
        gorulen.add(sh["id"])
        if sh.get("stil") not in STILLER:
            h.append(f"{ad}: stil {', '.join(STILLER)} olmalı")
            continue
        if "_yukleme_hatasi" in sh:
            h.append(f"{ad}: senaryo okunamadı ({sh['_yukleme_hatasi']})")
            continue
        if sh["enerji"] not in ENERJI:
            h.append(f"{ad}: enerji {', '.join(ENERJI)} olmalı")
        g = sh["_gecis"]
        if g["tur"] not in GECISLER:
            h.append(f"{ad}: geçiş {', '.join(GECISLER)} olmalı")
        elif i and g["sure"] and not (0 < g["sure"] <= min(sh["_sure"], sh_ler[i - 1]["_sure"]) / 3):
            h.append(f"{ad}: geçiş süresi iki sahnenin de üçte birinden kısa olmalı")
        if not sh["_sure"]:
            h.append(f"{ad}: senaryoda `sure` yok")
        if sahneler:
            h += [f"{ad} ({sh['stil']}): {x}" for x in _sahne_denetle(sh)]
    if h:
        return h
    sat = satirlar(k)
    sureler = sureler or {}
    for a, b in zip(sat, sat[1:]):
        if a["id"] in sureler and a["t"] + sureler[a["id"]] > b["t"] - 0.05:
            h.append(f"seslendirme {a['id']} ({a['t'] + sureler[a['id']]:.2f} sn'de biter) {b['id']} ile çakışıyor ({b['t']:.2f})")
    for a in sat:
        if a["id"] in sureler and a["t"] + sureler[a["id"]] > a["_son"]:
            h.append(f"seslendirme {a['id']} kendi sahnesi bitince hâlâ konuşuyor ({a['t'] + sureler[a['id']]:.2f} > {a['_son']:.2f})")
    return h


def seslendir(k: dict, cikti: Path, saglayici: str | None = "otomatik", ses: str | None = None) -> dict:
    """Bütün satırlar tek seferde, tek sesle; satır önbelleği sayesinde yalnız değişen satır yeniden üretilir."""
    sahte = {"seslendirme": {**k["seslendirme"], "satirlar": satirlar(k)}, "dil": k.get("dil")}
    return akis.seslendir(sahte, cikti, saglayici, ses)


# ---------------------------------------------------------------- görüntü

def _imza(sh: dict, W: int, H: int, fps: int, yerel: dict) -> str:
    """Sahne videosunun önbellek anahtarı: senaryo, boyut, ses süreleri ve şablon kodu değişmedikçe aynı."""
    h = hashlib.sha256(json.dumps([sh["stil"], sh["_s"], W, H, fps, yerel], sort_keys=True, ensure_ascii=False).encode())
    for p in sorted((SABLONLAR / STILLER[sh["stil"]]["klasor"]).glob("*.py")):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def sahne_videosu(sh: dict, W: int, H: int, fps: int, sureler: dict[str, float], klasor: Path) -> Path:
    yerel = {x["_yerel"]: sureler[x["id"]] for x in satirlar({"sahneler": [sh]}) if x["id"] in sureler}
    hedef = klasor / f"{sh['id']}-{W}x{H}-{_imza(sh, W, H, fps, yerel)}.mp4"
    if hedef.exists():
        return hedef
    klasor.mkdir(parents=True, exist_ok=True)
    ara = hedef.with_suffix(".yarim.mp4")
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "_sahne", sh["stil"], sh["_yol"], str(W), str(H),
                        str(fps), json.dumps(yerel), str(ara)], capture_output=True, text=True)
    if r.returncode:
        raise KurguHatasi(f"sahne {sh['id']} çizilemedi:\n{r.stderr[-800:]}")
    ara.replace(hedef)
    return hedef


def sahne_efekti(sh: dict, sureler: dict[str, float], klasor: Path) -> Path | None:
    """Sahnenin kendi efekt sesleri (whoosh, kalem, pop...): şablonun miksinden `efekt` kökü, önbellekli.

    Görüntüden bağımsızdır (format değişince yeniden üretilmez). Şablonun efekti yoksa None.
    """
    yerel = {x["_yerel"]: sureler[x["id"]] for x in satirlar({"sahneler": [sh]}) if x["id"] in sureler}
    hedef = klasor / f"{sh['id']}-efekt-{_imza(sh, 0, 0, 0, yerel)}.wav"
    bos = hedef.with_suffix(".yok")
    if bos.exists():
        return None
    if not hedef.exists():
        klasor.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "_efekt", sh["stil"], sh["_yol"],
                            json.dumps(yerel), str(hedef)], capture_output=True, text=True)
        if r.returncode:
            print(f"uyarı: sahne {sh['id']} efektleri alınamadı, kurguda yalnız müzik çalar:\n{r.stderr[-400:]}",
                  file=sys.stderr)
            return None
        if not hedef.exists():
            bos.write_text("şablonun efekt kökü yok\n", encoding="utf-8")
            return None
    return hedef


def _sahne_ciz(stil: str, yol: str, W: int, H: int, fps: int, yerel: dict, hedef: str) -> None:
    """Ayrı süreçte çalışır: her şablonun kendi `cizim` modülü var, aynı süreçte çakışırlar."""
    d = SABLONLAR / STILLER[stil]["klasor"]
    sys.path[:0] = [str(d), str(SABLONLAR.parent / "ses")]
    s = importlib.import_module(STILLER[stil]["yukle"]).yukle(yol)
    s["fps"] = fps
    s["_sureler"] = yerel  # karakalem kelime altyazısını ses sürelerine kilitler
    import cizim
    cizim.video(s, W, H, Path(hedef))


def _efekt_ciz(stil: str, yol: str, yerel: dict, hedef: str) -> None:
    """Ayrı süreçte: şablonun kendi miksini seslendirmesiz çalıştırır, yazdığı `efekt.wav` kökünü alır."""
    d = SABLONLAR / STILLER[stil]["klasor"]
    sys.path[:0] = [str(d), str(SABLONLAR.parent / "ses")]
    s = importlib.import_module(STILLER[stil]["yukle"]).yukle(yol)
    s["_sureler"] = yerel
    ses = importlib.import_module(STILLER[stil].get("ses", SES_MODULU))
    with tempfile.TemporaryDirectory() as tmp:
        ses.miksle(s, Path(tmp), Path(tmp) / "seslendirme-yok")
        kok = Path(tmp) / "efekt.wav"
        if kok.exists():
            Path(hedef).write_bytes(kok.read_bytes())


def birlestir_goruntu(k: dict, parcalar: list[Path], hedef: Path) -> Path:
    """Sahne videolarını geçişlerle tek sessiz videoya çevirir (tek kodlama)."""
    fps = k["fps"]
    girdi, filtre = [], []
    for i, p in enumerate(parcalar):
        girdi += ["-i", str(p)]
        tut = k["sahneler"][i].get("_uzat", 0)  # vuruşa oturtma: son kare biraz tutulur
        ek = f",tpad=stop_mode=clone:stop_duration={tut:.4f}" if tut > 0 else ""
        filtre.append(f"[{i}:v]fps={fps},format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS{ek}[p{i}]")
    son = "p0"
    for i, sh in enumerate(k["sahneler"][1:], 1):
        g = sh["_gecis"]
        if GECISLER[g["tur"]] is None or not g["sure"]:
            filtre.append(f"[{son}][p{i}]concat=n=2:v=1:a=0[a{i}]")
        else:
            filtre.append(f"[{son}][p{i}]xfade=transition={GECISLER[g['tur']]}:duration={g['sure']:.4f}"
                          f":offset={sh['_bas']:.4f}[a{i}]")
        son = f"a{i}"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *girdi, "-filter_complex", ";".join(filtre),
                    "-map", f"[{son}]", "-t", f"{k['sure']:.4f}", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                    "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                    "-r", str(fps), str(hedef)], check=True)
    return hedef


def bolum_listesi(k: dict) -> str:
    """YouTube açıklamasına yapıştırılan bölüm listesi (00:00 Açılış ...)."""
    def zaman(t):
        t = int(t + 0.5)
        return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"
    return "\n".join(f"{zaman(0 if i == 0 else b['bas'])} {b['baslik']}" for i, b in enumerate(bolumler(k))) + "\n"


def render(k: dict, cikti: Path, formatlar: list[str], paralel: int | None = None) -> list[Path]:
    import mastering
    import muzik
    kimlik = k.get("kimlik", "kurgu")
    is_ = cikti / "is"
    sureler = akis.sureler_oku(cikti / "seslendirme")
    sat = satirlar(k)
    akis.uyar_eksik([x["id"] for x in sat if x["id"] not in sureler])
    efektler = []
    for sh in k["sahneler"]:
        yol = sahne_efekti(sh, sureler, is_ / "efektler")
        if yol:
            efektler.append({"yol": yol, "bas": sh["_bas"], "son": sh["_bas"] + sh["_sure"],
                             "db": sh.get("efekt_db", k["muzik"].get("efekt_db", -12.0))})
    bilgi = muzik.miksle(k, bolumler(k), sat, cikti / "seslendirme", is_ / "ses.wav", efektler)
    if bilgi.get("konusma_ustu_db") is not None:
        print(f"ses dengesi: konuşma müziğin {bilgi['konusma_ustu_db']:.1f} dB üstünde")
    print(f"sahne efektleri: {len(efektler)}/{len(k['sahneler'])} sahne; geçiş sesi: {bilgi.get('gecis_sesi', 0)} "
          f"(kayıtlı kütüphane: {'var' if bilgi.get('kutuphane') else 'yok'})")
    (is_ / "ses-raporu.json").write_text(json.dumps(bilgi, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    mastering.master(is_ / "ses.wav", is_ / "ses-master.wav")
    paralel = paralel or max(1, (os.cpu_count() or 2) // 2)
    out = []
    for f in formatlar:
        W, H = FORMATLAR[f]
        with ThreadPoolExecutor(paralel) as havuz:
            parcalar = list(havuz.map(lambda sh: sahne_videosu(sh, W, H, k["fps"], sureler, is_ / "sahneler"), k["sahneler"]))
        sessiz = birlestir_goruntu(k, parcalar, is_ / f"sessiz-{f}.mp4")
        out.append(akis.birlestir(sessiz, is_ / "ses-master.wav", cikti / f"{kimlik}-{f}.mp4"))
    (cikti / f"{kimlik}-bolumler.txt").write_text(bolum_listesi(k), encoding="utf-8")
    return out


def kareler(k: dict, anlar: list[float], fmt: str, klasor: Path) -> list[Path]:
    """Kurgu zamanındaki anların kareleri; her an kendi sahnesinin şablonuyla çizilir."""
    out = []
    for t in anlar:
        sh = [x for x in k["sahneler"] if x["_bas"] <= t][-1]
        st = STILLER[sh["stil"]]
        f = fmt.replace("x", ":") if st.get("iki_nokta") else fmt
        yerel = min(max(0.0, t - sh["_bas"]), sh["_sure"] - 1 / k["fps"])
        r = subprocess.run([sys.executable, str(SABLONLAR / st["klasor"] / st["komut"]), "kare", sh["_yol"],
                            "--an", f"{yerel:.3f}", "--format", f, "-o", str(klasor / sh["id"])],
                           capture_output=True, text=True)
        if r.returncode:
            raise KurguHatasi(f"sahne {sh['id']} karesi çizilemedi: {r.stderr.strip()[-300:]}")
        out += [Path(x.strip()) for x in r.stdout.splitlines() if x.strip().endswith(".png")]
    return out


def onizleme_anlari(sh: dict, adet: int = 3) -> list[float]:
    """Sahnenin iç bölümleri bitmeden hemen önceki anlar: öğeler girmiş, sahne tam kurulmuş hâlde.

    Bölüm sayısı fazlaysa ilk bölüm (çoğunlukla başlık) atlanır ve kalanlardan eşit aralıkla seçilir.
    """
    ic = sh["_s"].get("sahneler") or []
    sonlar = [round(max(0.1, (ic[i + 1]["bas"] if i + 1 < len(ic) else sh["_sure"]) - 0.4), 2) for i in range(len(ic))]
    if len(sonlar) > adet:
        aday = sonlar[1:]
        sonlar = [aday[round(j * (len(aday) - 1) / (adet - 1))] for j in range(adet)]
    return sonlar or [round(sh["_sure"] * o, 1) for o in (0.15, 0.5, 0.85)]


def onizle(k: dict, hedef: Path, fmt: str) -> dict:
    import onizleme
    return onizleme.onizle([f"{sh['stil']}={sh['_yol']}" for sh in k["sahneler"]], hedef, None, fmt,
                           [onizleme_anlari(sh) for sh in k["sahneler"]])


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["_sahne"]:
        stil, yol, W, H, fps, yerel, hedef = argv[1:8]
        _sahne_ciz(stil, yol, int(W), int(H), int(fps), json.loads(yerel), hedef)
        return 0
    if argv[:1] == ["_efekt"]:
        stil, yol, yerel, hedef = argv[1:5]
        _efekt_ciz(stil, yol, json.loads(yerel), hedef)
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    for ad in ("denetle", "onizle", "kare", "seslendir", "render", "uret"):
        p = alt.add_parser(ad)
        p.add_argument("kurgu")
        p.add_argument("-o", "--cikti")
        if ad in ("seslendir", "uret"):
            p.add_argument("--saglayici", default="otomatik")
            p.add_argument("--ses")
        if ad in ("onizle", "kare", "render", "uret"):
            p.add_argument("--format")
        if ad == "kare":
            p.add_argument("--an", type=float, nargs="+", required=True)
        if ad in ("render", "uret"):
            p.add_argument("--paralel", type=int, help="aynı anda çizilen sahne sayısı (varsayılan: çekirdek/2)")
    a = ap.parse_args(argv)
    k = yukle(a.kurgu)
    cikti = akis.cikti_klasoru(k, a.cikti)
    hatalar = denetle(k, akis.sureler_oku(cikti / "seslendirme"))
    for h in hatalar:
        print(f"HATA: {h}", file=sys.stderr)
    if hatalar:
        return 1
    formatlar = coz(getattr(a, "format", None), k, ["16x9"])
    if a.komut == "denetle":
        print(f"tamam: {len(k['sahneler'])} sahne, {k['sure']:.1f} sn")
        print(bolum_listesi(k), end="")
        return 0
    if a.komut == "kare":
        try:
            for p in kareler(k, a.an, formatlar[0], cikti / "kareler"):
                print(p)
        except KurguHatasi as e:
            print(f"HATA: {e}", file=sys.stderr)
            return 1
        return 0
    if a.komut == "onizle":
        r = onizle(k, cikti / f"{k.get('kimlik', 'kurgu')}-onizleme.png", formatlar[0])
        print(r["sayfa"])
        return 1 if any("hata" in s for s in r["stiller"]) else 0
    if a.komut in ("seslendir", "uret"):
        eksik = [x for x in satirlar(k) if not (cikti / "seslendirme" / f"{x['id']}.wav").exists()]
        if a.komut == "seslendir" or eksik:
            import seslendirme
            try:
                b = seslendir(k, cikti, a.saglayici, a.ses)
            except seslendirme.SeslendirmeHatasi as e:
                print(f"HATA: {e}", file=sys.stderr)
                return 2
            for x in b["satirlar"]:
                print(f"{x['id']}\t{x['sure']:.2f} sn\t{x['metin']}")
            hatalar = denetle(k, akis.sureler_oku(cikti / "seslendirme"), sahneler=False)
            for h in hatalar:
                print(f"HATA: {h}", file=sys.stderr)
            if hatalar:
                return 1
        if a.komut == "seslendir":
            return 0
    for p in render(k, cikti, formatlar, getattr(a, "paralel", None)):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
