"""Sinematik küre: three.js ile perspektif kamera, gerçek arazi, bulut, gece ışıkları, atmosfer, post FX ve
çekim dili (kamera anahtar kareleri + yere yapışık katmanlar + marka yazıları).

    python3 platform/sablonlar/dunya/sinema/sinema.py kare  ornekler/dunya-sinema/karadeniz.json --an 1 5 9 --format 16x9 -o cikti/
    python3 platform/sablonlar/dunya/sinema/sinema.py video ornekler/dunya-sinema/karadeniz.json --format 9x16 -o film.mp4
    python3 platform/sablonlar/dunya/sinema/sinema.py kontakt ornekler/dunya-sinema/*.json --formatlar 16x9 9x16 -o sayfa.png

Ayrıntı: README.md (sinema bölümü) ve platform/docs/harita-tasarim-dili.md.
"""
from __future__ import annotations

import argparse
import base64
import functools
import http.server
import io
import json
import math
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

BURADA = Path(__file__).resolve().parent
DUNYA = BURADA.parent
NM = DUNYA / "node_modules"
sys.path.insert(0, str(DUNYA.parent.parent / "ortak"))
sys.path.insert(0, str(BURADA))
import harita  # noqa: E402
import dokular  # noqa: E402

FORMATLAR = {"16x9": (1920, 1080), "9x16": (1080, 1920), "1x1": (1080, 1080), "4x5": (1080, 1350)}
YAZILAR = {"inter-tight": ["400", "500", "600", "700"], "barlow-condensed": ["500", "600", "700"],
           "source-serif-4": ["400-italic"], "ibm-plex-mono": ["400", "500", "600"],
           # anlatım grafiği stilleri (grafik.js)
           "cinzel": ["600", "700"], "eb-garamond": ["400", "400-italic", "500-italic", "600"], "caveat": ["500", "600", "700"],
           "space-grotesk": ["500", "700"], "instrument-serif": ["400", "400-italic"]}
AILE = {"inter-tight": "Inter Tight", "barlow-condensed": "Barlow Condensed", "source-serif-4": "Source Serif 4",
        "ibm-plex-mono": "IBM Plex Mono", "cinzel": "Cinzel", "eb-garamond": "EB Garamond", "caveat": "Caveat",
        "space-grotesk": "Space Grotesk", "instrument-serif": "Instrument Serif"}
GRAFIKLER = ["belgesel", "haber", "gravur", "istihbarat", "kroki", "editoryal"]
BETIKLER = ["d3-array/dist/d3-array.min.js", "d3-geo/dist/d3-geo.min.js", "topojson-client/dist/topojson-client.min.js"]
IRTIFA = {"dunya": 3.6, "kita": 1.6, "bolge": 0.75, "ulke": 0.45, "sehir": 0.12}


def _yazi_css() -> str:
    out = []
    for aile, agirliklar in YAZILAR.items():
        for a in agirliklar:
            css = (NM / "@fontsource" / aile / f"{a}.css").read_text()
            for blok in re.findall(r"@font-face\s*{[^}]*}", css):
                if not re.search(r"latin(-ext)?-\d", blok) or "vietnamese" in blok:
                    continue
                dosya = re.search(r"url\(\./files/([^)]+\.woff2)\)", blok).group(1)
                veri = base64.b64encode((NM / "@fontsource" / aile / "files" / dosya).read_bytes()).decode()
                out.append(re.sub(r"src:[^;]*;", f"src: url(data:font/woff2;base64,{veri}) format('woff2');", blok))
    return "\n".join(out)


# ---------------- sahne çözümü: yer adları -> koordinat, ülkeler -> geometri adı ----------------
def _konum(d, dil="tr"):
    """'Ankara' | 'Türkiye' | [lon, lat] | {ad, konum} -> (lon, lat, etiket)"""
    if isinstance(d, (list, tuple)) and len(d) == 2 and all(isinstance(x, (int, float)) for x in d):
        return float(d[0]), float(d[1]), None
    if isinstance(d, dict):
        if "konum" in d:
            return float(d["konum"][0]), float(d["konum"][1]), d.get("etiket", d.get("ad"))
        d = d["ad"]
    try:
        u = harita.ulke(d)
        b = u["ana_kutu"]
        return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, u.get(dil, u["ad"])
    except Exception:
        pass
    r = harita.durak({"ad": d})
    return float(r["konum"][0]), float(r["konum"][1]), d


def _ulke(ad, dil):
    u = harita.ulke(ad)
    b = u["ana_kutu"]
    return {"geo": u["ad"], "etiket": u.get(dil, u["ad"]), "etiketKonum": [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2],
            "genislik": max(2.0, (b[2] - b[0]) * 0.7), "kutu": b, "halkalar": u["h"] if len(u["h"]) < 40 else None}


def sahne_coz(s: dict, fmt: str, ss: float = 2.0) -> dict:
    W, H = FORMATLAR[fmt]
    dil = s.get("dil", "tr")
    sure = float(s.get("sure", 12))
    katmanlar, noktalar = [], []
    for k in s.get("katmanlar", []):
        k = dict(k)
        tip = k["tip"]
        if tip == "ulke":
            u = _ulke(k["ad"], dil)
            k = {**u, **k, "etiket": k.get("etiket", u["etiket"])}
            if k.get("etiket") is False:
                k.pop("etiket")
            noktalar += [(u["kutu"][0], u["kutu"][1]), (u["kutu"][2], u["kutu"][3])]
        elif tip == "bolge":
            k["ulkeler"] = [_ulke(a, dil) for a in k["ulkeler"]]
            if "etiketKonum" in k or "konum" in k:
                k["etiketKonum"] = list(_konum(k.get("etiketKonum") or k["konum"], dil)[:2])
        elif tip in ("ok", "rota", "birlik") and "yol" in k:
            k["yol"] = [list(_konum(p, dil)[:2]) for p in k["yol"]]
            noktalar += [tuple(p) for p in k["yol"]]
        if tip == "cephe":
            for d in k["durumlar"]:
                d["yol"] = [list(_konum(p, dil)[:2]) for p in d["yol"]]
                noktalar += [tuple(p) for p in d["yol"]]
        if "konum" in k and tip not in ("bolge",):
            lo, la, et = _konum(k["konum"], dil)
            k["konum"] = [lo, la]
            noktalar.append((lo, la))
            if tip in ("sehir", "nabiz", "deniz") and "etiket" not in k and (et or k.get("ad")):
                k["etiket"] = k.get("ad") or et
        if tip == "sehir" and "etiket" not in k:
            k["etiket"] = k.get("ad")
        katmanlar.append(k)

    # kamera anahtar kareleri: eksik alanlar öncekinden; irtifa adla ("dunya", "ulke"...) ya da sayı
    kam, onceki = [], {"hedef": [30.0, 30.0], "irtifa": 3.6, "egim": 0.0, "yon": 0.0, "kayX": 0.0, "kayY": 0.0}
    for a in s.get("kamera") or [{"t": 0}, {"t": sure}]:
        a = dict(a)
        if "hedef" in a:
            a["hedef"] = list(_konum(a["hedef"], dil)[:2])
        if isinstance(a.get("irtifa"), str):
            a["irtifa"] = IRTIFA[a["irtifa"]]
        if fmt in ("9x16", "4x5") and "kayX" in a:   # dikeyde yatay kaydırma yok, dikey kaydırma kullanılır
            a["kayY"] = a.get("kayY_dikey", a.get("kayY", 0.0)); a["kayX"] = 0.0
        elif fmt in ("9x16", "4x5"):
            a["kayY"] = a.get("kayY_dikey", a.get("kayY", 0.0))
        onceki = {**onceki, **{k: v for k, v in a.items() if k != "kayY_dikey"}}
        kam.append(dict(onceki))
    # odak kutusu: katmanların coğrafi kapsamı + pay (keskin katman tuvali)
    if s.get("odak"):
        odak = s["odak"]
    elif noktalar:
        lo = [p[0] for p in noktalar]; la = [p[1] for p in noktalar]
        odak = [max(-180, min(lo) - 8), max(-85, min(la) - 6), min(180, max(lo) + 8), min(85, max(la) + 6)]
    else:
        odak = [-30, 20, 60, 70]
    return {"W": W, "H": H, "ss": ss, "sure": sure, "dil": dil, "isik": s.get("isik", "gece"), "kamera": kam,
            "katmanlar": katmanlar, "odak": odak, "yazi": s.get("yazi", {}), "yorunge": s.get("yorunge", 0),
            "bulut": s.get("bulut"), "kabartma": s.get("kabartma", 1.0), "gunes": s.get("gunes"), "gunesHiz": s.get("gunesHiz", 0),
            "sondur": s.get("sondur", 0.35), "yildiz": s.get("yildiz"), "pozlama": s.get("pozlama"), "kalite": s.get("kalite"),
            "marka": s.get("marka", "varsayilan"), "grafik": s.get("grafik", "belgesel")}


# ---------------- sayfa + yerel sunucu ----------------
class _Sunucu:
    """file:// modül kısıtları olmasın diye: /nm -> node_modules, /kure -> doku önbelleği, /is -> geçici klasör"""

    def __init__(self, klasor: Path):
        kokler = {"/nm/": NM, "/kure/": dokular.KURE, "/is/": klasor, "/sinema/": BURADA}

        class Isleyici(http.server.SimpleHTTPRequestHandler):
            def translate_path(self, yol):
                yol = yol.split("?")[0]
                for on, kok in kokler.items():
                    if yol.startswith(on):
                        return str(kok / yol[len(on):])
                return str(klasor / "yok")

            def log_message(self, *a):
                pass

            def guess_type(self, path):
                return "text/javascript" if str(path).endswith((".js", ".mjs")) else super().guess_type(path)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Isleyici)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def kapat(self):
        self.httpd.shutdown()


def _birlestir(a: dict, b: dict) -> dict:
    """b'yi a'nın üstüne derin yazar (grafik stili -> marka)"""
    out = dict(a)
    for k, v in b.items():
        out[k] = _birlestir(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def sayfa_yaz(sahne: dict, klasor: Path) -> None:
    if not NM.joinpath("three").exists():
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=DUNYA, check=True)
    dokular.hazirla()
    mj = json.loads((BURADA / "marka.json").read_text())
    marka = _birlestir(mj[sahne["marka"]], mj.get("grafikler", {}).get(sahne.get("grafik", "belgesel"), {}))
    marka["grafik"] = sahne.get("grafik", "belgesel")
    topo = json.loads((NM / "world-atlas" / "countries-50m.json").read_text())
    d = {"gunduz": "gunduz.jpg", "kure": "kure.jpg", "atlas": "atlas.jpg", "gece": "gece.png", "normal": "normal.png",
         "su": "su.png", "bulut": "bulut.png", "yukseklik": "yukseklik.png"}
    veri = {"sahne": sahne, "marka": marka, "topo": topo, "dokular": {k: f"/kure/{v}" for k, v in d.items()}}
    (klasor / "veri.js").write_text("window.__VERI = " + json.dumps(veri, ensure_ascii=False) + ";", encoding="utf-8")
    betik = "\n".join(f'<script src="/nm/{b}"></script>' for b in BETIKLER)
    (klasor / "sayfa.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>{_yazi_css()}
html,body{{margin:0;background:#000}} canvas{{display:block}}</style>
<script type="importmap">{{"imports":{{"three":"/nm/three/build/three.module.js","three/addons/":"/nm/three/examples/jsm/"}}}}</script>
</head><body><canvas id="gl"></canvas><canvas id="ek"></canvas><canvas id="son"></canvas>
{betik}<script src="/is/veri.js"></script><script type="module" src="/sinema/sahne.js"></script></body></html>""", encoding="utf-8")


class Cizer:
    def __init__(self, sahne: dict):
        from playwright.sync_api import sync_playwright
        self.sahne = sahne
        self.tmp = tempfile.TemporaryDirectory()
        sayfa_yaz(sahne, Path(self.tmp.name))
        self.sunucu = _Sunucu(Path(self.tmp.name))
        self.pw = sync_playwright().start()
        arg = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--disable-gpu-sandbox"]
        try:
            self.tarayici = self.pw.chromium.launch(args=arg)
        except Exception:
            self.tarayici = self.pw.chromium.launch(args=arg, executable_path="/opt/pw-browsers/chromium")
        self.sayfa = self.tarayici.new_page(viewport={"width": 400, "height": 300})
        self.hatalar = []
        self.sayfa.on("pageerror", lambda e: self.hatalar.append(str(e)))
        self.sayfa.on("console", lambda m: m.type == "error" and self.hatalar.append(m.text))
        self.sayfa.goto(f"http://127.0.0.1:{self.sunucu.port}/is/sayfa.html")
        aileler = [("italic " if "italic" in w else "") + f'{w.split("-")[0]} 20px "{AILE[p]}"' for p, ws in YAZILAR.items() for w in ws]
        self.sayfa.evaluate("async (a) => { for (const f of a) await document.fonts.load(f, 'ĞğŞşİıÇçÖöÜü'); }", aileler)
        try:
            self.sayfa.wait_for_function("window.hazir === true", timeout=180000)
        except Exception:
            raise RuntimeError("sahne.js hazır olmadı: " + "; ".join(self.hatalar[:3]))

    def ham(self, sn: float, no: int = 0) -> bytes:
        url = self.sayfa.evaluate("([s, k]) => window.ciz(s, k)", [sn, no])
        if self.hatalar:
            raise RuntimeError("sahne.js: " + self.hatalar[0])
        return base64.b64decode(url.split(",", 1)[1])

    def kare(self, sn: float, no: int = 0):
        from PIL import Image
        return Image.open(io.BytesIO(self.ham(sn, no))).convert("RGB")

    def kapat(self):
        self.tarayici.close(); self.pw.stop(); self.sunucu.kapat(); self.tmp.cleanup()


def _oku(yol) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def kareler(s: dict, anlar, fmt: str, hedef: Path, ss: float = 2.0, ad: str = "kare") -> list[Path]:
    hedef.mkdir(parents=True, exist_ok=True)
    c = Cizer(sahne_coz(s, fmt, ss))
    out = []
    try:
        for t in anlar:
            p = hedef / f"{ad}-{fmt}-{t:05.1f}.png"
            p.write_bytes(c.ham(t, round(t * 30)))
            out.append(p)
    finally:
        c.kapat()
    return out


def video(s: dict, fmt: str, cikti: Path, ss: float = 2.0, fps: int = 30, olcek: float = 1.0) -> Path:
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
        c.kapat(); ff.stdin.close(); ff.wait()
    return cikti


def kontakt(sahneler: list[Path], formatlar, anlar, hedef: Path, ss: float = 2.0) -> Path:
    """her sahne × format için kareler, tek sayfa (satır = sahne). 9:16 kareleri yan yana küçük."""
    from PIL import Image, ImageDraw, ImageFont
    satirlar = []
    with tempfile.TemporaryDirectory() as tmp:
        for yol in sahneler:
            s = _oku(yol)
            ts = s.get("anlar", anlar)
            for fmt in formatlar:
                ps = kareler(s, ts, fmt, Path(tmp), ss, Path(yol).stem)
                satirlar.append((f"{Path(yol).stem} · {fmt} · {s.get('isik', 'gece')}", [Image.open(p).convert("RGB") for p in ps]))
        yuk = 540
        kucuk = [(et, [im.resize((round(im.width * yuk / im.height), yuk), Image.LANCZOS) for im in ims]) for et, ims in satirlar]
        gen = max(sum(im.width for im in ims) + 24 * (len(ims) + 1) for _, ims in kucuk)
        sayfa = Image.new("RGB", (gen, sum(yuk + 70 for _ in kucuk) + 20), (14, 16, 20))
        d = ImageDraw.Draw(sayfa)
        try:
            f = ImageFont.truetype("DejaVuSans.ttf", 22)
        except Exception:
            f = ImageFont.load_default()
        y = 20
        for et, ims in kucuk:
            d.text((24, y), et, fill=(230, 230, 230), font=f)
            x = 24
            for im in ims:
                sayfa.paste(im, (x, y + 36)); x += im.width + 24
            y += yuk + 70
        hedef.parent.mkdir(parents=True, exist_ok=True)
        sayfa.save(hedef, quality=92)
    return hedef


def grafik_kontakt(hucreler: list[str], grafikler: list[str], hedef: Path, ss: float = 2.0, yuk: int = 460) -> Path:
    """aynı sahne(ler) her grafik stilinde: satır = stil, sütun = hücre ("sahne.json:16x9:9.4").
    Atilla'ya stil seçtirmek için tek sayfa; tam video yalnız seçilen stil için."""
    from PIL import Image, ImageDraw, ImageFont
    mj = json.loads((BURADA / "marka.json").read_text())
    gruplar: dict = {}
    for h in hucreler:
        yol, fmt, t = h.rsplit(":", 2)
        gruplar.setdefault((yol, fmt), []).append(float(t))
    satirlar = []
    for gr in grafikler:
        kareler_ = {}
        for (yol, fmt), ts in gruplar.items():
            s = {**_oku(yol), "grafik": gr}
            c = Cizer(sahne_coz(s, fmt, ss))
            try:
                for t in ts:
                    kareler_[(yol, fmt, t)] = Image.open(io.BytesIO(c.ham(t, round(t * 30)))).convert("RGB")
            finally:
                c.kapat()
            print(f"  {gr}: {Path(yol).stem} {fmt} tamam", file=sys.stderr, flush=True)
        ims = [kareler_[(h.rsplit(":", 2)[0], h.rsplit(":", 2)[1], float(h.rsplit(":", 2)[2]))] for h in hucreler]
        satirlar.append((gr, mj.get("grafikler", {}).get(gr, {}).get("_not", ""), ims))
    kucuk = [(a, n, [im.resize((round(im.width * yuk / im.height), yuk), Image.LANCZOS) for im in ims]) for a, n, ims in satirlar]
    gen = max(sum(im.width for im in ims) + 28 * (len(ims) + 1) for _, _, ims in kucuk)
    sayfa = Image.new("RGB", (gen, len(kucuk) * (yuk + 96) + 24), (14, 16, 20))
    d = ImageDraw.Draw(sayfa)
    try:
        f1, f2 = ImageFont.truetype("DejaVuSans-Bold.ttf", 30), ImageFont.truetype("DejaVuSans.ttf", 21)
    except Exception:
        f1 = f2 = ImageFont.load_default()
    y = 24
    for i, (a, n, ims) in enumerate(kucuk, 1):
        d.text((28, y), f"{i}. {a.upper()}", fill=(255, 255, 255), font=f1)
        d.text((28 + d.textlength(f"{i}. {a.upper()}", font=f1) + 18, y + 8), n, fill=(170, 176, 186), font=f2)
        x = 28
        for im in ims:
            sayfa.paste(im, (x, y + 50)); x += im.width + 28
        y += yuk + 96
    hedef.parent.mkdir(parents=True, exist_ok=True)
    sayfa.save(hedef, quality=90)
    return hedef


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    alt = ap.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kare"); k.add_argument("sahne"); k.add_argument("--an", type=float, nargs="+", default=[1, 5, 9])
    k.add_argument("--format", default="16x9"); k.add_argument("-o", default="cikti"); k.add_argument("--ss", type=float, default=2.0)
    k.add_argument("--grafik", choices=GRAFIKLER, help="anlatım grafiği stili (sahnedekini ezer)")
    v = alt.add_parser("video"); v.add_argument("sahne"); v.add_argument("--format", default="16x9"); v.add_argument("-o", required=True)
    v.add_argument("--grafik", choices=GRAFIKLER)
    v.add_argument("--ss", type=float, default=2.0); v.add_argument("--fps", type=int, default=30); v.add_argument("--olcek", type=float, default=1.0)
    c = alt.add_parser("kontakt"); c.add_argument("sahneler", nargs="+"); c.add_argument("--formatlar", nargs="+", default=["16x9"])
    c.add_argument("--an", type=float, nargs="+", default=[1, 5, 9]); c.add_argument("-o", default="kontakt.jpg"); c.add_argument("--ss", type=float, default=2.0)
    gk = alt.add_parser("grafik-kontakt", help="aynı sahne her grafik stilinde tek sayfada")
    gk.add_argument("hucreler", nargs="+", help='"sahne.json:16x9:9.4" biçiminde hücreler')
    gk.add_argument("--grafikler", nargs="+", default=GRAFIKLER, choices=GRAFIKLER); gk.add_argument("-o", default="grafik-kontakt.jpg"); gk.add_argument("--ss", type=float, default=2.0)
    d = alt.add_parser("doku"); d.add_argument("--zorla", action="store_true")
    a = ap.parse_args(argv)
    if a.komut == "kare":
        s = _oku(a.sahne)
        if a.grafik:
            s["grafik"] = a.grafik
        for p in kareler(s, a.an, a.format, Path(a.o), a.ss, Path(a.sahne).stem + (f"-{a.grafik}" if a.grafik else "")):
            print(p)
    elif a.komut == "video":
        s = _oku(a.sahne)
        if a.grafik:
            s["grafik"] = a.grafik
        print(video(s, a.format, Path(a.o), a.ss, a.fps, a.olcek))
    elif a.komut == "grafik-kontakt":
        print(grafik_kontakt(a.hucreler, a.grafikler, Path(a.o), a.ss))
    elif a.komut == "kontakt":
        print(kontakt([Path(x) for x in a.sahneler], a.formatlar, a.an, Path(a.o), a.ss))
    else:
        print(dokular.hazirla(a.zorla))
    return 0


if __name__ == "__main__":
    sys.exit(main())
