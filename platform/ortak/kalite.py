"""Kalite kapısı: teslimden önce videoyu makine kontrol eder, insan yalnız sonuca bakar.

Kontroller: çözünürlük, kare hızı, kodek ve piksel biçimi; ses var mı, ses yüksekliği -14 LUFS
ve gerçek tepe; tekdüze tiz cızırtı (hışırtı); videonun ortasında siyah, donmuş kare ya da sessizlik; degrade zeminlerde
banding (dairesel/düz basamak); büyütülmüş, yumuşak görüntü. Sonunda bir kontakt sayfası çıkar:
8 örnek kare, dikey videoda Reels/TikTok/Shorts arayüzünün kapattığı bölgeler kırmızı taralı
(yazının o bölgeye düşüp düşmediğine insan bakar; yazıyı makine güvenilir ayırt edemiyor).

    python3 platform/ortak/kalite.py video.mp4 [video2.mp4 ...] [--sessiz] [--kontakt kontakt.png] [--json]

Çıkış kodu: 0 geçti (uyarı olabilir), 1 en az bir hata var. Gerekenler: ffmpeg/ffprobe, numpy;
Pillow varsa kontakt sayfasına zaman etiketi yazılır.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
if str(BURADA) not in sys.path:
    sys.path.insert(0, str(BURADA))
import mastering  # noqa: E402
from formatlar import FORMATLAR  # noqa: E402

HEDEF_LUFS = mastering.HEDEF_LUFS
ESIK = {
    "kisa_kenar": 1080,         # px; altı hata
    "fps_alt": 23.9,
    "lufs_uyari": 1.0,          # hedeften sapma (LU)
    "lufs_hata": 3.0,
    "tepe_uyari": -1.0,         # dBTP; üstü uyarı (platformlar yeniden kodlar)
    "tepe_hata": 0.0,
    "ses_kayma": 0.25,          # sn; ses ve görüntü süresi farkı
    "siyah_sn": 0.4,
    "donma_bilgi": 2.5,         # sn; sondaki tutuş (CTA) sayılmaz
    "donma_uyari": 4.0,
    "sessizlik_sn": 1.0,
    "hisirti_uyari": 1.0,       # sn; kesintisiz gürültü gibi tiz bant (konuşmadaki s/ş < 0.2 sn)
    "hisirti_hata": 2.0,
    "banding_uyari": 0.03,      # banding'li karo oranı
    "banding_hata": 0.12,
    "banding_parlak": 200,      # bu parlaklığın üstündeki karolar sayılmaz (tek kod basamağı açık zeminde seçilmez)
    "netlik_uyari": 0.48,       # kenar dikliği medyanı: keskin çizim ~0.7–0.8, yarım çözünürlükten büyütülmüş ~0.4
}
# Dikey videoda Reels / TikTok / Shorts arayüzünün kapattığı yaklaşık pay (üst, alt, sol, sağ)
ARAYUZ_9X16 = {"ust": 0.10, "alt": 0.22, "sol": 0.04, "sag": 0.13}
ORNEK_KARE = 8
KARO = 64


# ---------------------------------------------------------------- yardımcılar

def _calistir(arg: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(arg, capture_output=True, text=True)


def _bul(seviye: str, kontrol: str, mesaj: str, an: float | None = None) -> dict:
    b = {"seviye": seviye, "kontrol": kontrol, "mesaj": mesaj}
    if an is not None:
        b["an"] = round(an, 2)
    return b


def akis_bilgisi(yol: Path) -> dict:
    r = _calistir(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(yol)])
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe okuyamadı: {yol}\n{r.stderr[-300:]}")
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)

    def oran(x: str | None) -> float:
        if not x or x == "0/0":
            return 0.0
        p, q = (x.split("/") + ["1"])[:2]
        return float(p) / float(q) if float(q) else 0.0

    return {
        "sure": float(j["format"].get("duration", 0) or 0),
        "bit_hizi": int(j["format"].get("bit_rate", 0) or 0),
        "video": None if v is None else {
            "w": int(v["width"]), "h": int(v["height"]), "kodek": v.get("codec_name"),
            "piksel": v.get("pix_fmt"), "fps": oran(v.get("avg_frame_rate") or v.get("r_frame_rate")),
            "sure": float(v.get("duration", 0) or 0)},
        "ses": None if a is None else {
            "kodek": a.get("codec_name"), "hz": int(a.get("sample_rate", 0) or 0),
            "kanal": int(a.get("channels", 0) or 0), "sure": float(a.get("duration", 0) or 0)},
    }


# ---------------------------------------------------------------- akış ve ses

def akis_kontrol(b: dict, sessiz_olabilir: bool) -> list[dict]:
    out = []
    v = b["video"]
    if v is None:
        return [_bul("hata", "akis", "videoda görüntü akışı yok")]
    kisa = min(v["w"], v["h"])
    if kisa < ESIK["kisa_kenar"]:
        out.append(_bul("hata", "cozunurluk", f"{v['w']}x{v['h']}: kısa kenar {kisa} px, en az {ESIK['kisa_kenar']} olmalı"))
    elif (v["w"], v["h"]) not in FORMATLAR.values():
        out.append(_bul("uyari", "cozunurluk", f"{v['w']}x{v['h']} standart formatlardan biri değil (9x16, 16x9, 1x1, 4x5)"))
    if v["fps"] < ESIK["fps_alt"]:
        out.append(_bul("hata", "fps", f"kare hızı {v['fps']:.2f}, en az 24 olmalı"))
    if v["kodek"] not in ("h264", "hevc"):
        out.append(_bul("uyari", "kodek", f"görüntü kodeği {v['kodek']}; platformlar için h264 önerilir"))
    if v["piksel"] != "yuv420p":
        out.append(_bul("uyari", "piksel", f"piksel biçimi {v['piksel']}; bazı oynatıcılar yalnız yuv420p açar"))
    s = b["ses"]
    if s is None:
        if not sessiz_olabilir:
            out.append(_bul("hata", "ses", "ses akışı yok (sessiz sürüm bilerek ise --sessiz)"))
        return out
    if s["kodek"] != "aac":
        out.append(_bul("uyari", "ses", f"ses kodeği {s['kodek']}; AAC önerilir"))
    if s["hz"] and s["hz"] != 48000:
        out.append(_bul("bilgi", "ses", f"örnekleme {s['hz']} Hz (hedef 48000)"))
    if v["sure"] and s["sure"] and abs(v["sure"] - s["sure"]) > ESIK["ses_kayma"]:
        out.append(_bul("uyari", "ses", f"ses ({s['sure']:.2f} sn) ve görüntü ({v['sure']:.2f} sn) süreleri farklı"))
    return out


def ses_kontrol(yol: Path, b: dict) -> tuple[list[dict], dict]:
    if b["ses"] is None:
        return [], {}
    o = mastering.olc(yol, on_filtre=None)
    out = []
    if o["lufs"] in (None, float("-inf")):
        return [_bul("hata", "ses", "ses tamamen sessiz")], o
    sapma = o["lufs"] - HEDEF_LUFS
    if abs(sapma) > ESIK["lufs_hata"]:
        out.append(_bul("hata", "lufs", f"ses yüksekliği {o['lufs']:.1f} LUFS, hedef {HEDEF_LUFS:.0f} (fark {sapma:+.1f} LU)"))
    elif abs(sapma) > ESIK["lufs_uyari"]:
        out.append(_bul("uyari", "lufs", f"ses yüksekliği {o['lufs']:.1f} LUFS, hedef {HEDEF_LUFS:.0f} (fark {sapma:+.1f} LU)"))
    tp = o["tepe_dbtp"]
    if tp is not None and tp > ESIK["tepe_hata"]:
        out.append(_bul("hata", "tepe", f"gerçek tepe {tp:.1f} dBTP: kırpılma var"))
    elif tp is not None and tp > ESIK["tepe_uyari"]:
        out.append(_bul("uyari", "tepe", f"gerçek tepe {tp:.1f} dBTP; platform yeniden kodlayınca kırpılabilir (≤ -1)"))
    # ortada sessizlik
    r = _calistir(["ffmpeg", "-hide_banner", "-nostats", "-i", str(yol), "-vn", "-af",
                   f"silencedetect=noise=-50dB:d={ESIK['sessizlik_sn']}", "-f", "null", "-"])
    bas = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    bit = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    sure = b["sure"]
    for i, t0 in enumerate(bas):
        t1 = bit[i] if i < len(bit) else sure
        if t0 > 0.3 and t1 < sure - 0.3:
            out.append(_bul("uyari", "sessizlik", f"{t0:.1f}–{t1:.1f} sn arası sessiz", t0))
    h = hisirti_olc(yol)
    if h is not None:
        o["hisirti"] = h
        mesaj = (f"{h['en_uzun_an']:.1f} sn'den itibaren {h['en_uzun_sn']:.1f} sn tekdüze tiz cızırtı (gürültü gibi "
                 "tiz bant müzik kadar yüksek); efekti platform/ortak/sfx.py'deki biçimli seslerle yapın")
        if h["en_uzun_sn"] >= ESIK["hisirti_hata"]:
            out.append(_bul("hata", "hisirti", mesaj, h["en_uzun_an"]))
        elif h["en_uzun_sn"] >= ESIK["hisirti_uyari"]:
            out.append(_bul("uyari", "hisirti", mesaj, h["en_uzun_an"]))
    return out, o


def hisirti_olc(yol: Path) -> dict | None:
    """Sesi mono 48 kHz çözüp `sfx.gurultu_analizi` ile ölçer (en uzun kesintisiz cızırtı, oranı)."""
    try:
        import numpy as np
        import sfx
    except ImportError:
        return None
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(yol), "-vn", "-ac", "1", "-ar", "48000",
                        "-f", "f32le", "-"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return sfx.gurultu_analizi(np.frombuffer(r.stdout, dtype=np.float32), 48000)


# ---------------------------------------------------------------- siyah ve donma

def zaman_kontrol(yol: Path, sure: float) -> list[dict]:
    vf = (f"scale=480:-2,blackdetect=d={ESIK['siyah_sn']}:pic_th=0.98:pix_th=0.08,"
          f"freezedetect=n=-60dB:d={ESIK['donma_bilgi']}")
    r = _calistir(["ffmpeg", "-hide_banner", "-nostats", "-i", str(yol), "-an", "-vf", vf, "-f", "null", "-"])
    out = []
    for t0, t1 in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr):
        t0, t1 = float(t0), float(t1)
        if t0 > 0.1 and t1 < sure - 0.1:  # açılış ve kapanış kararmaları normal
            out.append(_bul("uyari", "siyah", f"{t0:.1f}–{t1:.1f} sn siyah kare", t0))
    bas = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", r.stderr)]
    sur = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", r.stderr)]
    for i, t0 in enumerate(bas):
        d = sur[i] if i < len(sur) else sure - t0
        if t0 + d >= sure - 0.2:
            continue  # sondaki tutuş (logo, çağrı) bilerek yapılır
        seviye = "uyari" if d >= ESIK["donma_uyari"] else "bilgi"
        out.append(_bul(seviye, "donma", f"{t0:.1f} sn'den itibaren {d:.1f} sn görüntü kıpırdamıyor; bilerek mi?", t0))
    return out


# ---------------------------------------------------------------- kare analizi

def kare_al(yol: Path, t: float, w: int, h: int):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(yol),
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    if r.returncode != 0 or len(r.stdout) < w * h * 3:
        return None
    return np.frombuffer(r.stdout[: w * h * 3], dtype=np.uint8).reshape(h, w, 3)


def banding_orani(kare, karo: int = KARO) -> float:
    """Degrade zeminde basamaklaşan karoların oranı (0–1).

    Bir karo şu durumda banding'li sayılır: tonu yumuşak değişir (aralık 2–16 kod değeri),
    en az iki ton karonun %10'undan fazlasını kaplar ve komşu pikseller %90'dan fazla aynıdır
    (geniş düz şeritler; titreşimli/dither'lı degradede komşular sık farklıdır). Düz dolgu ve
    dokulu yüzeyler sayılmaz. Kanal kanal bakılır; herhangi birinde basamak varsa karo sayılır.
    Çok açık karolar (ortalama > ESIK["banding_parlak"]) sayılmaz: kâğıt dokusu ve yumuşak gölge
    orada yanlış alarm verir, basamak ise koyu ve orta tonlarda göze batar.
    """
    import numpy as np
    h, w, _ = kare.shape
    H, W = h // karo, w // karo
    if H == 0 or W == 0:
        return 0.0
    k = kare[: H * karo, : W * karo].astype(np.int16)
    bantli = np.zeros(H * W, dtype=bool)
    # karo bütün kanallarda yumuşak olmalı: iki düz rengin keskin sınırı (sarı/turuncu gibi, tek kanalda
    # fark ≤ 16) degrade değildir, eskiden yanlış alarm veriyordu
    tum = k.reshape(H, karo, W, karo, 3).transpose(0, 2, 1, 3, 4).reshape(H * W, -1, 3)
    hepsi_yumusak = (tum.max(axis=1) - tum.min(axis=1)).max(axis=1) <= 16
    parlak = (k @ np.array([0.299, 0.587, 0.114])).reshape(H, karo, W, karo).mean(axis=(1, 3)).ravel() > ESIK["banding_parlak"]
    for c in range(3):
        t = k[:, :, c].reshape(H, karo, W, karo).transpose(0, 2, 1, 3).reshape(H * W, karo, karo)
        mn = t.min(axis=(1, 2))
        aralik = t.max(axis=(1, 2)) - mn
        yumusak = (aralik >= 1) & (aralik <= 16) & hepsi_yumusak
        if not yumusak.any():
            continue
        i = np.nonzero(yumusak)[0]
        ts = t[i]
        esit = ((ts[:, :, 1:] == ts[:, :, :-1]).mean(axis=(1, 2)) + (ts[:, 1:, :] == ts[:, :-1, :]).mean(axis=(1, 2))) / 2
        goreli = (ts - mn[i][:, None, None]).reshape(len(i), -1)
        sayim = np.bincount((np.arange(len(i))[:, None] * 17 + goreli).ravel(), minlength=len(i) * 17).reshape(len(i), 17)
        buyuk = (sayim / goreli.shape[1] > 0.10).sum(axis=1)
        bantli[i[(esit > 0.90) & (buyuk >= 2)]] = True
    return float((bantli & ~parlak).mean())


def _pencere(a, f, r: int):
    """(2r+1)x(2r+1) kayan pencerede f (np.maximum / np.minimum), ayrılabilir; kenarlar uzatılır."""
    import numpy as np
    h, w = a.shape
    p = np.pad(a, ((r, r), (0, 0)), mode="edge")
    o = p[0:h]
    for s in range(1, 2 * r + 1):
        o = f(o, p[s: s + h])
    p = np.pad(o, ((0, 0), (r, r)), mode="edge")
    o2 = p[:, 0:w]
    for s in range(1, 2 * r + 1):
        o2 = f(o2, p[:, s: s + w])
    return o2


def netlik(kare) -> float | None:
    """Güçlü kenarlarda tek pikseldeki ton değişiminin, 5x5 çevredeki toplam değişime oranı (medyan).

    Kenar keskin çizilmişse geçiş 1–2 pikselde biter (oran yüksek); görüntü küçük çizilip
    büyütüldüyse geçiş yayılır (oran düşer). Güçlü kenar yoksa None.
    """
    import numpy as np
    g = kare.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    h, w = g.shape
    if h < 8 or w < 8:
        return None
    dx = np.abs(np.diff(g, axis=1))[:-1, :]
    dy = np.abs(np.diff(g, axis=0))[:, :-1]
    adim = np.maximum(dx, dy)
    mx = _pencere(g, np.maximum, 2)[: h - 1, : w - 1]
    mn = _pencere(g, np.minimum, 2)[: h - 1, : w - 1]
    ar = mx - mn
    m = ar >= 80
    if m.sum() < 200:
        return None
    # her kenar bölgesinde en dik adımı al: adım, çevrenin en dik noktasıysa say
    tepe = adim >= _pencere(adim, np.maximum, 1) - 1e-3
    sec = m & tepe & (adim > 0)
    if sec.sum() < 100:
        return None
    return float(np.median(adim[sec] / ar[sec]))


def kare_kontrol(yol: Path, b: dict, kontakt: Path | None) -> tuple[list[dict], dict]:
    import numpy as np
    v = b["video"]
    w, h, sure = v["w"], v["h"], b["sure"] or v["sure"]
    anlar = [sure * (i + 0.5) / ORNEK_KARE for i in range(ORNEK_KARE)]
    kareler, olcum = [], {"banding": [], "netlik": []}
    for t in anlar:
        k = kare_al(yol, t, w, h)
        if k is None:
            continue
        kareler.append((t, k))
        olcum["banding"].append(round(banding_orani(k), 4))
        n = netlik(k)
        olcum["netlik"].append(None if n is None else round(n, 3))
    out = []
    if not kareler:
        return [_bul("hata", "kare", "kare okunamadı")], olcum
    en = int(np.argmax(olcum["banding"]))
    bmax = olcum["banding"][en]
    if bmax >= ESIK["banding_hata"]:
        out.append(_bul("hata", "banding", f"degrade zeminde basamak (banding): karoların %{bmax * 100:.0f}'i; "
                        "düz dolgu ya da titreşim (dither) kullanın", kareler[en][0]))
    elif bmax >= ESIK["banding_uyari"]:
        out.append(_bul("uyari", "banding", f"degrade zeminde hafif basamak (banding): karoların %{bmax * 100:.0f}'i",
                        kareler[en][0]))
    ns = [x for x in olcum["netlik"] if x is not None]
    if ns and float(np.median(ns)) < ESIK["netlik_uyari"]:
        out.append(_bul("uyari", "netlik", f"kenarlar yumuşak (netlik {float(np.median(ns)):.2f}); "
                        "görüntü küçük çizilip büyütülmüş olabilir"))
    if kontakt:
        kontakt_yaz(kareler, kontakt, dikey=h > w)
    return out, olcum


def arayuz_tara(kk):
    """Dikey karede Reels / TikTok / Shorts arayüzünün kapattığı bölgeleri kırmızıya boyar (yerinde)."""
    import numpy as np
    hh, ww, _ = kk.shape
    a = ARAYUZ_9X16
    for sl in (np.s_[: int(hh * a["ust"]), :], np.s_[hh - int(hh * a["alt"]):, :],
               np.s_[:, ww - int(ww * a["sag"]):], np.s_[:, : int(ww * a["sol"])]):
        bolge = kk[sl].astype(np.float32)
        bolge[..., 0] = bolge[..., 0] * 0.75 + 255 * 0.25
        bolge[..., 1:] *= 0.75
        kk[sl] = bolge.astype(np.uint8)
    return kk


def kontakt_yaz(kareler: list, hedef: Path, dikey: bool, sutun: int = 4) -> Path:
    """`kareler`: (an ya da etiket, RGB dizi) çiftleri. Saniye verilirse etiket "x.xx sn" olur."""
    import numpy as np
    yuk = 480 if dikey else 270
    kucukler = []
    for t, k in kareler:
        h, w, _ = k.shape
        adim = max(1, round(h / yuk))
        kk = k[::adim, ::adim].copy()
        if dikey:
            arayuz_tara(kk)
        kucukler.append((t, kk))
    hh = max(k.shape[0] for _, k in kucukler)
    ww = max(k.shape[1] for _, k in kucukler)
    satir = (len(kucukler) + sutun - 1) // sutun
    bos = 12
    tuval = np.full((satir * (hh + bos + 28) + bos, sutun * (ww + bos) + bos, 3), 245, dtype=np.uint8)
    yerler = []
    for i, (t, k) in enumerate(kucukler):
        y = bos + (i // sutun) * (hh + bos + 28)
        x = bos + (i % sutun) * (ww + bos)
        tuval[y: y + k.shape[0], x: x + k.shape[1]] = k
        yerler.append((x, y + hh + 4, t))
    hedef = Path(hedef)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageDraw
        im = Image.fromarray(tuval)
        d = ImageDraw.Draw(im)
        for x, y, t in yerler:
            d.text((x, y), f"{t:5.2f} sn" if isinstance(t, (int, float)) else str(t), fill=(30, 30, 30))
        im.save(hedef)
    except ImportError:
        H, W, _ = tuval.shape
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                        "-s", f"{W}x{H}", "-i", "-", "-frames:v", "1", str(hedef)], input=tuval.tobytes(), check=True)
    return hedef


def seslendirme_kontrol(yol: Path) -> tuple[list[dict], dict | None]:
    """Videonun yanındaki `seslendirme/seslendirme.json`: ElevenLabs yerine Piper yedeği kullanıldıysa uyarı."""
    k = Path(yol).parent / "seslendirme" / "seslendirme.json"
    if not k.exists():
        return [], None
    try:
        j = json.loads(k.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], None
    bilgi = {"saglayici": j.get("saglayici"), "ses": j.get("ses"), "yedek": j.get("yedek")}
    if j.get("yedek"):
        y = j["yedek"]
        return [_bul("uyari", "seslendirme", f"{y.get('istenen', 'elevenlabs')} yerine {j.get('saglayici')} yedeğiyle "
                     f"seslendirildi ({y.get('neden', '?')}); teslimden önce yeniden seslendirin")], bilgi
    if j.get("saglayici") == "piper":
        return [_bul("bilgi", "seslendirme", "seslendirme bilerek Piper ile (senaryo ya da komut satırı)")], bilgi
    return [], bilgi


# ---------------------------------------------------------------- ana akış

def denetle(yol: str | Path, sessiz_olabilir: bool = False, kontakt: str | Path | None = None) -> dict:
    yol = Path(yol)
    b = akis_bilgisi(yol)
    bulgular = akis_kontrol(b, sessiz_olabilir)
    olcum: dict = {}
    if b["video"] is not None:
        s, o = ses_kontrol(yol, b)
        bulgular += s
        olcum["ses"] = o
        bulgular += zaman_kontrol(yol, b["sure"])
        k, ko = kare_kontrol(yol, b, Path(kontakt) if kontakt else None)
        bulgular += k
        olcum["kareler"] = ko
    sk, so = seslendirme_kontrol(yol)
    bulgular += sk
    if so:
        olcum["seslendirme"] = so
    sev = {x["seviye"] for x in bulgular}
    sonuc = "kaldi" if "hata" in sev else ("uyarili" if "uyari" in sev else "gecti")
    return {"dosya": str(yol), "sonuc": sonuc, "akis": b, "olcum": olcum, "bulgular": bulgular,
            "kontakt": str(kontakt) if kontakt else None}


ETIKET = {"gecti": "GEÇTİ", "uyarili": "GEÇTİ (uyarılı)", "kaldi": "KALDI"}
ISARET = {"hata": "HATA ", "uyari": "UYARI", "bilgi": "bilgi"}


def ozet(r: dict) -> str:
    b = r["akis"]
    v = b["video"] or {}
    satir = [f"{ETIKET[r['sonuc']]}: {Path(r['dosya']).name}"]
    bas = f"  {v.get('w')}x{v.get('h')}, {v.get('fps', 0):.0f} fps, {b['sure']:.1f} sn"
    o = r["olcum"].get("ses") or {}
    if o.get("lufs") is not None:
        bas += f", {o['lufs']:.1f} LUFS, tepe {o['tepe_dbtp']:.1f} dBTP"
    satir.append(bas)
    for x in r["bulgular"]:
        satir.append(f"  {ISARET[x['seviye']]} {x['kontrol']}: {x['mesaj']}")
    if r.get("kontakt"):
        satir.append(f"  kontakt sayfası: {r['kontakt']}")
    return "\n".join(satir)


def render_sonrasi(hedef: Path) -> dict | None:
    """Şablonların render sonunda çağırdığı kapı: rapor + kontakt sayfası yazar, durmaz."""
    if os.environ.get("STUDYO_KALITE", "1") == "0":
        return None
    hedef = Path(hedef)
    try:
        r = denetle(hedef, kontakt=hedef.with_suffix(".kontakt.png"))
    except Exception as e:  # kapı render'ı asla düşürmez
        print(f"UYARI: kalite kapısı çalışmadı ({e})", file=sys.stderr)
        return None
    import render_suresi  # sn/kare ölçümü (uret.py başlatır; elle render'da boş kalır)
    render_suresi.ekle(r)
    hedef.with_suffix(".kalite.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(ozet(r), file=sys.stderr if r["sonuc"] != "gecti" else sys.stdout)
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video", nargs="+")
    ap.add_argument("--sessiz", action="store_true", help="ses akışı olmaması hata sayılmaz (sessiz TV döngüsü gibi)")
    ap.add_argument("--kontakt", help="kontakt sayfası yolu (birden çok videoda klasör)")
    ap.add_argument("--json", action="store_true", help="raporu JSON bas")
    a = ap.parse_args(argv)
    kod = 0
    raporlar = []
    for v in a.video:
        k = None
        if a.kontakt:
            k = Path(a.kontakt) / f"{Path(v).stem}.kontakt.png" if len(a.video) > 1 else Path(a.kontakt)
        r = denetle(v, a.sessiz, k)
        raporlar.append(r)
        if not a.json:
            print(ozet(r))
        if r["sonuc"] == "kaldi":
            kod = 1
    if a.json:
        print(json.dumps(raporlar if len(raporlar) > 1 else raporlar[0], ensure_ascii=False, indent=1))
    return kod


if __name__ == "__main__":
    sys.exit(main())
