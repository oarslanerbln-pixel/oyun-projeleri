"""Dünya haritası motion graphic: dönen küre / düz atlas, kamera bölgeye iner, rota çizilir, yerler belirir.

    python3 platform/sablonlar/dunya/dunya.py kur                                   # npm bağımlılıkları (bir kez)
    python3 platform/sablonlar/dunya/dunya.py kare ornekler/dunya/sahne.json --an 1 6 11 --format 16x9 -o cikti/
    python3 platform/sablonlar/dunya/dunya.py video ornekler/dunya/sahne.json --format 9x16 -o film.mp4
    python3 platform/sablonlar/dunya/dunya.py kontakt ornekler/dunya/sahne.json --kaplamalar atlas kure neon -o sayfa.png

Çizim tarayıcıda (başsız Chromium) d3-geo ile yapılır: gerçek projeksiyonlar (ortografik küre, Equal Earth, Robinson,
Natural Earth...), Natural Earth 1:50m ülke sınırları (world-atlas TopoJSON), Türkçe/Almanca/Arapça yazı. Tuval
`--ss` kat büyük çizilir ve lanczos ile küçültülür (temiz kenar). Kaplamalar (görsel diller) motor.js'te:
atlas, kure, nokta, karakalem, parsomen, neon, kagit, izometrik. `"kure": false` düz haritaya geçer
(kure kaplaması her zaman küre, izometrik her zaman düz).

Sahne alanları: kaplama, sure, dil (tr/de), ust/baslik/altbaslik, rota [yer adı | {ad, konum}],
vurgu [ülke adı], noktalar [yer adı], sayacNot, yaylar [yer adı] (neon), bolge {lon, lat, k} (elle kamera).
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

BURADA = Path(__file__).resolve().parent
NM = BURADA / "node_modules"
ORTAK = BURADA.parent.parent / "ortak"
sys.path.insert(0, str(ORTAK))
import harita  # noqa: E402

KAPLAMALAR = ["atlas", "kure", "nokta", "karakalem", "parsomen", "neon", "kagit", "izometrik"]
FORMATLAR = {"16x9": (1920, 1080), "9x16": (1080, 1920), "1x1": (1080, 1080), "4x5": (1080, 1350)}
YAZILAR = {"fraunces": ["500", "600", "700"], "instrument-serif": ["400", "400-italic"], "eb-garamond": ["400", "400-italic"],
           "caveat": ["500", "600", "700"], "space-grotesk": ["400", "500", "600", "700"], "ibm-plex-mono": ["500"],
           "cinzel": ["600", "700"]}
BETIKLER = ["d3-array/dist/d3-array.min.js", "d3-geo/dist/d3-geo.min.js", "d3-geo-projection/dist/d3-geo-projection.min.js",
            "topojson-client/dist/topojson-client.min.js"]
VARSAYILAN_YAYLAR = ["Londra", "New York", "Tokyo", "Kahire", "Moskova", "Dubai", "Lagos", "Mumbai", "Pekin", "Toronto",
                     "Johannesburg", "Singapur", "Buenos Aires", "Sidney", "Los Angeles", "Tahran"]


def kur() -> None:
    subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=BURADA, check=True)


def _yazi_css() -> str:
    """fontsource CSS'lerini (latin + latin-ext) base64 gömülü @font-face'e çevirir"""
    out = []
    for aile, agirliklar in YAZILAR.items():
        for a in agirliklar:
            css = (NM / "@fontsource" / aile / f"{a}.css").read_text()
            for blok in re.findall(r"@font-face\s*{[^}]*}", css):
                if not re.search(r"latin(-ext)?-\d", blok) or "vietnamese" in blok:
                    continue
                dosya = re.search(r"url\(\./files/([^)]+\.woff2)\)", blok).group(1)
                veri = base64.b64encode((NM / "@fontsource" / aile / "files" / dosya).read_bytes()).decode()
                blok = re.sub(r"src:[^;]*;", f"src: url(data:font/woff2;base64,{veri}) format('woff2');", blok)
                out.append(blok)
    return "\n".join(out)


def _yer(d, dil: str) -> dict:
    """'İstanbul' ya da {"ad": ..., "konum": [lon, lat], "etiket": ...} -> {etiket, lon, lat, nufus}"""
    if isinstance(d, str):
        d = {"ad": d}
    r = harita.durak(d)
    lon, lat = r["konum"]
    nufus = d.get("nufus")
    if nufus is None and "konum" not in d:
        try:
            nufus = harita.adaylar(d["ad"])[0][5]
        except Exception:
            nufus = None
    return {"etiket": d.get("etiket") or r["ad"], "lon": lon, "lat": lat, "nufus": nufus, "deger": d.get("deger")}


def sahne_coz(s: dict, fmt: str, ss: float) -> dict:
    W, H = FORMATLAR[fmt]
    dil = s.get("dil", "tr")
    rota = [_yer(d, dil) for d in s.get("rota", [])]
    vurgu = []
    for v in s.get("vurgu", []):
        ad = v if isinstance(v, str) else v["ad"]
        u = harita.ulke(ad)
        b = u["ana_kutu"]
        vurgu.append({"ad": u["ad"], "etiket": u.get(dil, u["ad"]), "nokta": [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2],
                      **({} if isinstance(v, str) else {k: x for k, x in v.items() if k != "ad"})})
    yaylar = []
    for y in s.get("yaylar", VARSAYILAN_YAYLAR):
        try:
            yaylar.append(list(harita.sehir(y)))
        except Exception:
            pass
    return {"W": W, "H": H, "ss": ss, "stil": s.get("kaplama", "kure"), "sure": float(s.get("sure", 12)), "dil": dil,
            "kure": s.get("kure", True), "ust": s.get("ust"), "baslik": s.get("baslik"), "altbaslik": s.get("altbaslik"),
            "sayacNot": s.get("sayacNot"), "veriNot": s.get("veriNot"), "rota": rota, "vurgu": vurgu,
            "noktalar": [_yer(d, dil) for d in s.get("noktalar", [])], "yaylar": yaylar,
            "km": round(harita.mesafe([(r["lon"], r["lat"]) for r in rota])) if len(rota) > 1 and s.get("sayac", True) else 0,
            "bolge": s.get("bolge")}


def sayfa_yaz(sahne: dict, klasor: Path) -> Path:
    if not NM.exists():
        kur()
    wa = NM / "world-atlas"
    veri = {"sahne": sahne, "ulkeler": json.loads((wa / "countries-50m.json").read_text()),
            "kara": json.loads((wa / "land-50m.json").read_text())}
    (klasor / "veri.js").write_text("window.__VERI = " + json.dumps(veri, ensure_ascii=False) + ";", encoding="utf-8")
    betik = "\n".join(f'<script src="{(NM / b).as_uri()}"></script>' for b in BETIKLER)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{_yazi_css()}
html,body{{margin:0;background:#000}}</style></head><body><canvas id="c"></canvas>
<div style="position:absolute;opacity:0;font-family:Fraunces">.</div>
{betik}<script src="veri.js"></script><script src="{(BURADA / 'motor.js').as_uri()}"></script></body></html>"""
    yol = klasor / "sayfa.html"
    yol.write_text(html, encoding="utf-8")
    return yol


class Cizer:
    """tek tarayıcı sayfası; kare(sn) -> PIL.Image (W×H, küçültülmüş)"""

    def __init__(self, sahne: dict):
        from playwright.sync_api import sync_playwright
        self.sahne = sahne
        self.tmp = tempfile.TemporaryDirectory()
        yol = sayfa_yaz(sahne, Path(self.tmp.name))
        self.pw = sync_playwright().start()
        arg = ["--allow-file-access-from-files", "--disable-web-security"]
        try:
            self.tarayici = self.pw.chromium.launch(args=arg)
        except Exception:  # bulut kabında Playwright sürümü kurulu Chromium'la eşleşmeyebilir
            self.tarayici = self.pw.chromium.launch(args=arg, executable_path="/opt/pw-browsers/chromium")
        self.sayfa = self.tarayici.new_page(viewport={"width": 400, "height": 300})
        hatalar = []
        self.sayfa.on("pageerror", lambda e: hatalar.append(str(e)))
        self.sayfa.goto(yol.as_uri())
        # yazı tiplerini önceden yükle
        self.sayfa.evaluate("""async () => { const a = ['500 20px Fraunces','600 20px Fraunces','700 20px Fraunces','400 20px "Instrument Serif"','italic 400 20px "Instrument Serif"',
          '400 20px "EB Garamond"','italic 400 20px "EB Garamond"','500 20px Caveat','600 20px Caveat','700 20px Caveat','400 20px "Space Grotesk"','500 20px "Space Grotesk"',
          '600 20px "Space Grotesk"','700 20px "Space Grotesk"','500 20px "IBM Plex Mono"','600 20px Cinzel','700 20px Cinzel'];
          for (const f of a) await document.fonts.load(f, 'ĞğŞşİıÇçÖöÜü'); }""")
        if hatalar:
            raise RuntimeError("motor.js: " + hatalar[0])
        self.sayfa.evaluate("() => window.hazir")

    def kare(self, sn: float, no: int = 0):
        from PIL import Image
        url = self.sayfa.evaluate("([s, k]) => { window.ciz(s, k); return document.getElementById('c').toDataURL('image/png'); }", [sn, no])
        im = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB")
        W, H = self.sahne["W"], self.sahne["H"]
        return im if im.size == (W, H) else im.resize((W, H), Image.LANCZOS)

    def ham(self, sn: float, no: int = 0) -> bytes:
        url = self.sayfa.evaluate("([s, k]) => { window.ciz(s, k); return document.getElementById('c').toDataURL('image/png'); }", [sn, no])
        return base64.b64decode(url.split(",", 1)[1])

    def kapat(self):
        self.tarayici.close()
        self.pw.stop()
        self.tmp.cleanup()


def _oku(yol: str) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def kareler(s: dict, anlar, fmt: str, hedef: Path, ss: float = 2.0, fps: int = 30) -> list[Path]:
    hedef.mkdir(parents=True, exist_ok=True)
    c = Cizer(sahne_coz(s, fmt, ss))
    out = []
    try:
        for t in anlar:
            p = hedef / f"{s.get('kaplama', 'kure')}-{fmt}-{t:05.1f}.png"
            c.kare(t, round(t * fps)).save(p)
            out.append(p)
    finally:
        c.kapat()
    return out


def video(s: dict, fmt: str, cikti: Path, ss: float = 1.5, fps: int = 30, olcek: float = 1.0) -> Path:
    """olcek < 1: onay öncesi küçük hareket taslağı (animatik)"""
    sahne = sahne_coz(s, fmt, ss)
    W, H = round(sahne["W"] * olcek / 2) * 2, round(sahne["H"] * olcek / 2) * 2
    cikti.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps),
                           "-c:v", "png", "-i", "-", "-vf", f"scale={W}:{H}:flags=lanczos", "-c:v", "libx264", "-preset", "slow",
                           "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(cikti)], stdin=subprocess.PIPE)
    c = Cizer(sahne)
    try:
        n = round(sahne["sure"] * fps)
        for i in range(n):
            ff.stdin.write(c.ham(i / fps, i))
            if i % (fps * 2) == 0:
                print(f"  {cikti.name}: {i}/{n}", file=sys.stderr, flush=True)
    finally:
        c.kapat()
        ff.stdin.close()
        ff.wait()
    return cikti


def _kontakt_is(a):
    s, kaplama, fmt, anlar, hedef, ss = a
    s = {**s, "kaplama": kaplama}
    return kaplama, fmt, kareler(s, anlar, fmt, Path(hedef), ss)


def kontakt(s: dict, kaplamalar, formatlar, anlar, hedef: Path, ss: float = 2.0, is_sayisi: int = 4) -> dict:
    """her kaplama × format için kareler; her format ayrı tek sayfa (satır = kaplama). kalite ölçüleri etikette"""
    import numpy as np
    from PIL import Image
    sys.path.insert(0, str(ORTAK))
    import kalite
    tmp = hedef.parent / (hedef.stem + "-kareler")
    isler = [(s, k, f, anlar, str(tmp / f), ss) for f in formatlar for k in kaplamalar]
    with ProcessPoolExecutor(is_sayisi) as ex:
        sonuc = list(ex.map(_kontakt_is, isler))
    rapor = {"sayfalar": [], "kareler": []}
    for f in formatlar:
        hucre = []
        for k, ff, pngler in sonuc:
            if ff != f:
                continue
            for t, p in zip(anlar, pngler):
                a = np.asarray(Image.open(p).convert("RGB"))
                b, n = kalite.banding_orani(a), kalite.netlik(a)
                notlar = [f"banding %{b * 100:.0f}"] if b >= kalite.ESIK["banding_uyari"] else []
                hucre.append((" · ".join([k, f"{t:g} sn", *notlar]), a))
                rapor["kareler"].append({"kaplama": k, "format": f, "an": t, "banding": round(b, 4), "netlik": n, "dosya": str(p)})
        sayfa = hedef.with_name(f"{hedef.stem}-{f}{hedef.suffix}")
        kalite.kontakt_yaz(hucre, sayfa, dikey=f == "9x16", sutun=len(anlar))
        rapor["sayfalar"].append(str(sayfa))
    return rapor


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("kur")
    k = alt.add_parser("kare")
    k.add_argument("sahne"); k.add_argument("--an", type=float, nargs="+", default=[2, 6, 10])
    k.add_argument("--format", default="16x9"); k.add_argument("-o", default="cikti"); k.add_argument("--ss", type=float, default=2.0)
    k.add_argument("--kaplama")
    v = alt.add_parser("video")
    v.add_argument("sahne"); v.add_argument("--format", default="16x9"); v.add_argument("-o", required=True)
    v.add_argument("--ss", type=float, default=1.5); v.add_argument("--fps", type=int, default=30); v.add_argument("--kaplama"); v.add_argument("--olcek", type=float, default=1.0)
    c = alt.add_parser("kontakt")
    c.add_argument("sahne"); c.add_argument("--kaplamalar", nargs="+", default=KAPLAMALAR)
    c.add_argument("--formatlar", nargs="+", default=["16x9"]); c.add_argument("--an", type=float, nargs="+", default=[1.5, 6, 10.5])
    c.add_argument("-o", default="kontakt.png"); c.add_argument("--ss", type=float, default=2.0); c.add_argument("--is", type=int, default=4)
    a = ap.parse_args(argv)
    if a.komut == "kur":
        kur()
        return 0
    s = _oku(a.sahne)
    fmt = getattr(a, "format", "16x9").replace(":", "x")
    if getattr(a, "kaplama", None):
        s["kaplama"] = a.kaplama
    if a.komut == "kare":
        for p in kareler(s, a.an, fmt, Path(a.o), a.ss):
            print(p)
    elif a.komut == "video":
        print(video(s, fmt, Path(a.o), a.ss, a.fps, a.olcek))
    else:
        r = kontakt(s, a.kaplamalar, [f.replace(":", "x") for f in a.formatlar], a.an, Path(a.o), a.ss, getattr(a, "is"))
        Path(a.o).with_suffix(".json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\n".join(r["sayfalar"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
