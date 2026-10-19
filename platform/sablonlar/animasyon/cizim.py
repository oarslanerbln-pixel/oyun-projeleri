"""Animatik çıktıları: çekim SVG'leri, tarayıcıda oynayan animatik, manifest, altyazı.

Animatik zamanlamayı ve yerleşimi onaylatmak içindir (V1 kapısı), son görüntü
değildir: her karede `gorsel` ve `kamera` notu, teslim ön ayarının güvenli
alanı ve kırpma odağı kılavuz olarak görünür. `manifest.json` araçtan bağımsız
zaman çizelgesidir; Clipkit, DaVinci ya da Unity Timeline bağdaştırıcıları
bunu okur.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import _yollar  # noqa: F401
import marka as marka_mod
from cekimler import Zamanli, zaman_cizelgesi
from proje import Kurgu, Proje
from teslim import OnAyar

CHAR_WIDTH = 0.55  # ortalama glif genişliği / punto; satır kırmak için kaba ölçü
LINE_HEIGHT = 1.2


def wrap(text: str, size: float, max_width: float) -> list[str]:
    """Metni verilen genişliğe sığacak satırlara böler (açgözlü)."""
    limit = max(1, int(max_width / (size * CHAR_WIDTH)))
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) <= limit or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _text(lines: list[str], x: float, y: float, size: float, fill: str, family: str,
          weight: int, anchor: str = "middle", extra: str = "") -> str:
    spans = "".join(
        f'<tspan x="{x:g}" dy="{0 if i == 0 else size * LINE_HEIGHT:g}">{escape(line)}</tspan>'
        for i, line in enumerate(lines))
    return (f'<text x="{x:g}" y="{y:g}" fill="{fill}" font-family="{escape(family)}, sans-serif" '
            f'font-weight="{weight}" font-size="{size:g}" text-anchor="{anchor}"{extra}>{spans}</text>')


def timecode(seconds: float, sep: str = ",") -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def cekim_svg(z: Zamanli, a: OnAyar, p: Proje, dil: str, katman: bool = False) -> str:
    """Çekimin karesi. `katman=True` render için yalnız yazı katmanını verir:
    zemin ve kılavuz yok, arka plan saydam (altına klip ya da yer tutucu gelir)."""
    c, m = z.cekim, p.marka
    w, h = a.genislik, a.yukseklik
    base = min(w, h)
    left, right = w * a.guvenli_yan, w * (1 - a.guvenli_yan)
    top, bottom = h * a.guvenli_ust, h * (1 - a.guvenli_alt)
    usable, cx = right - left, w / 2
    bg, fg = m.renk_al(c.zemin), m.renk_al(c.on)
    head, body = m.yazi["baslik"], m.yazi["govde"]

    parts = [] if katman else [f'<rect width="{w}" height="{h}" fill="{bg}"/>']

    # Kılavuz katmanı: görsel notu, kırpma odağı, güvenli alan (animatikte gizlenebilir).
    note = base * 0.022
    guide = [f'<rect x="{left:g}" y="{top:g}" width="{usable:g}" height="{bottom - top:g}" fill="none" '
             f'stroke="{fg}" stroke-opacity=".35" stroke-dasharray="{note:g} {note / 2:g}" stroke-width="{note / 6:g}"/>']
    ox, oy, r = c.odak_x * w, c.odak_y * h, base * 0.02
    guide.append(f'<g stroke="{fg}" stroke-opacity=".5" stroke-width="{r / 5:g}" fill="none">'
                 f'<circle cx="{ox:g}" cy="{oy:g}" r="{r:g}"/>'
                 f'<line x1="{ox - 2 * r:g}" y1="{oy:g}" x2="{ox + 2 * r:g}" y2="{oy:g}"/>'
                 f'<line x1="{ox:g}" y1="{oy - 2 * r:g}" x2="{ox:g}" y2="{oy + 2 * r:g}"/></g>')
    label = " · ".join(x for x in (c.cekim, c.gorsel, c.kamera, c.sinif and f"YZ {c.sinif}") if x)
    guide.append(_text(wrap(label, note, w - 2 * note), note, note * 1.8, note, fg, body.aile, body.agirlik,
                       anchor="start", extra=' fill-opacity=".6"'))
    guide_layer = '<g class="kilavuz">' + "".join(guide) + "</g>"
    parts.append('<g class="icerik">')

    if c.logo and m.logo_metin:
        size = base * 0.05
        parts.append(_text([m.logo_metin], cx, top + size, size, fg, head.aile, head.agirlik))

    cta_h = 0.0
    if c.cagri and p.brif.cagri:
        size = base * 0.045
        pill_bg = m.renk.get("vurgu", m.renk_al(c.on))
        pill_fg = m.renk.get("vurgu-ustu", m.renk_al(c.zemin))
        pw = min(usable, len(p.brif.cagri) * size * CHAR_WIDTH + size * 2)
        cta_h = size * 2
        py = bottom - cta_h
        parts.append(f'<rect x="{cx - pw / 2:g}" y="{py:g}" width="{pw:g}" height="{cta_h:g}" '
                     f'rx="{cta_h / 2:g}" fill="{pill_bg}"/>')
        parts.append(_text([p.brif.cagri], cx, py + cta_h / 2 + size * 0.35, size, pill_fg,
                           head.aile, head.agirlik))

    if c.metin_anahtari:
        size = base * 0.032
        lines = wrap(p.tablo.al(c.metin_anahtari, dil), size, usable * 0.9)
        y = bottom - cta_h - (size * 1.5 if cta_h else 0) - (len(lines) - 1) * size * LINE_HEIGHT
        parts.append(f'<g class="altyazi">{_text(lines, cx, y, size, fg, body.aile, body.agirlik)}</g>')

    if c.ekran:
        size = base * 0.085
        lines = wrap(p.tablo.al(c.ekran, dil), size, usable)
        block = len(lines) * size * LINE_HEIGHT
        y = (top + bottom) / 2 - block / 2 + size
        parts.append(_text(lines, cx, y, size, fg, head.aile, head.agirlik))

    # Kamera hareketi yalnız içeriği ölçekler; zemin ve kılavuz yerinde kalır.
    parts += ["</g>"] if katman else ["</g>", guide_layer]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'data-cekim="{escape(c.cekim)}">' + "".join(parts) + "</svg>\n")


def hareket(kamera: str) -> str:
    """Kamera notundan animatikteki kaba hareket: 'itme' yaklaşır, 'çekme' uzaklaşır."""
    k = kamera.casefold()
    if "itme" in k:
        return "yaklas"
    if "çekme" in k or "cekme" in k:
        return "uzaklas"
    return "sabit"


def manifest(p: Proje, k: Kurgu) -> dict:
    tl = zaman_cizelgesi(list(k.cekimler), k.fps)
    return {
        "proje": p.kimlik,
        "kurgu": k.ad,
        "marka": p.marka.kimlik,
        "onerme": p.brif.onerme,
        "fps": k.fps,
        "sure": round(k.sure, 6),
        "kareler": tl[-1].son_kare if tl else 0,
        "teslim": [{"ad": a.ad, "genislik": a.genislik, "yukseklik": a.yukseklik, "oran": a.oran}
                   for a in k.teslim],
        "cekimler": [{
            "cekim": z.cekim.cekim,
            "bas": z.bas, "son": z.son, "bas_kare": z.bas_kare, "son_kare": z.son_kare,
            "metin_anahtari": z.cekim.metin_anahtari, "ekran": z.cekim.ekran,
            "gorsel": z.cekim.gorsel, "kamera": z.cekim.kamera, "hareket": hareket(z.cekim.kamera),
            "gecis": z.cekim.gecis, "odak": [z.cekim.odak_x, z.cekim.odak_y],
            "sinif": z.cekim.sinif, "durum": z.cekim.durum,
            "zemin": z.cekim.zemin, "on": z.cekim.on, "logo": z.cekim.logo, "cagri": z.cekim.cagri,
        } for z in tl],
    }


def altyazi(p: Proje, k: Kurgu, dil: str, vtt: bool = False) -> str:
    """Seslendirme satırlarından altyazı; zaman çekim listesinden gelir (mimari §4.2)."""
    out = ["WEBVTT", ""] if vtt else []
    n = 0
    for z in zaman_cizelgesi(list(k.cekimler), k.fps):
        key = z.cekim.metin_anahtari
        if not key:
            continue
        n += 1
        sep = "." if vtt else ","
        if not vtt:
            out.append(str(n))
        out += [f"{timecode(z.bas, sep)} --> {timecode(z.son, sep)}", p.tablo.al(key, dil), ""]
    return "\n".join(out)


_PLAYER_JS = """
const data = JSON.parse(document.getElementById('veri').textContent);
const scenes = [...document.querySelectorAll('.cekim')];
const bar = document.getElementById('bar'), tc = document.getElementById('tc');
const btn = document.getElementById('oynat'), guide = document.getElementById('kilavuz');
let t = 0, playing = true, last = performance.now();
const fmt = s => s.toFixed(2).padStart(5, '0') + ' sn';
function show(time) {
  scenes.forEach((el, i) => {
    const s = data.cekimler[i], on = time >= s.bas && time < s.son;
    el.classList.toggle('on', on);
    if (on && s.hareket !== 'sabit') {
      const k = (time - s.bas) / (s.son - s.bas);
      const scale = s.hareket === 'yaklas' ? 1 + 0.06 * k : 1.06 - 0.06 * k;
      const g = el.querySelector('.icerik'), vb = el.querySelector('svg').viewBox.baseVal;
      g.style.transformOrigin = (s.odak[0] * vb.width) + 'px ' + (s.odak[1] * vb.height) + 'px';
      g.style.transform = 'scale(' + scale + ')';
    }
  });
  bar.value = time / data.sure * 1000;
  tc.textContent = fmt(time) + ' / ' + fmt(data.sure) + ' · kare ' + Math.floor(time * data.fps);
}
function tick(now) {
  if (playing) { t = (t + (now - last) / 1000) % data.sure; show(t); }
  last = now; requestAnimationFrame(tick);
}
btn.onclick = () => { playing = !playing; btn.textContent = playing ? '❚❚' : '▶'; };
bar.oninput = () => { t = bar.value / 1000 * data.sure; show(t); };
guide.onchange = () => document.body.classList.toggle('kilavuzsuz', !guide.checked);
show(0); requestAnimationFrame(tick);
"""


def animatik_html(p: Proje, k: Kurgu, a: OnAyar, kareler: list[str]) -> str:
    m = manifest(p, k)
    sections = []
    for c, svg in zip(m["cekimler"], kareler):
        fade = min(0.4, (c["son"] - c["bas"]) / 3)
        sections.append(f'<section class="cekim g-{c["gecis"]}" style="--gecis:{fade:.2f}s">{svg}</section>')
    title = escape(f"{p.kimlik} · {k.ad} · {a.ad}")
    data = json.dumps(m, ensure_ascii=False).replace("</", "<\\/")  # <script> içinde güvenli
    ratio = a.genislik / a.yukseklik
    return f"""<!doctype html>
<html lang="{escape(p.diller[0])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · animatik</title>
<style>
{marka_mod.to_css(p.marka)}
html, body {{ margin: 0; height: 100%; background: #111; color: #eee; font: 14px system-ui, sans-serif; }}
main {{ display: grid; place-items: center; height: calc(100% - 56px); }}
.sahne {{ position: relative; overflow: hidden; aspect-ratio: {a.genislik} / {a.yukseklik};
  width: min(96vw, calc((100vh - 72px) * {ratio:.4f})); background: var(--renk-zemin); }}
.cekim {{ position: absolute; inset: 0; opacity: 0; visibility: hidden; }}
.cekim svg {{ width: 100%; height: 100%; display: block; }}
.cekim.on {{ opacity: 1; visibility: visible; }}
.cekim.g-erime.on {{ animation: erime var(--gecis) ease-out; }}
.cekim.g-kayma.on {{ animation: kayma var(--gecis) ease-out; }}
.kilavuzsuz .kilavuz {{ display: none; }}
@keyframes erime {{ from {{ opacity: 0; }} }}
@keyframes kayma {{ from {{ transform: translateX(12%); opacity: 0; }} }}
footer {{ display: flex; gap: 12px; align-items: center; padding: 12px 16px; }}
footer input[type=range] {{ flex: 1; }}
footer button {{ width: 40px; height: 32px; }}
@media (prefers-reduced-motion: reduce) {{ .cekim.on {{ animation: none !important; }} }}
</style>
</head>
<body>
<main><div class="sahne">{"".join(sections)}</div></main>
<footer><button id="oynat" aria-label="Oynat / duraklat">❚❚</button>
<input id="bar" type="range" min="0" max="1000" value="0" aria-label="Zaman">
<label><input id="kilavuz" type="checkbox" checked> kılavuz</label>
<span id="tc"></span></footer>
<script id="veri" type="application/json">{data}</script>
<script>{_PLAYER_JS}</script>
</body>
</html>
"""


def brif_md(p: Proje) -> str:
    b, m = p.brif, p.marka
    rows = [f"# {m.ad} · brif", "", f"**Önerme:** {b.onerme}", "",
            f"- **Hedef:** {b.hedef}", f"- **Kitle:** {b.kitle}",
            f"- **İçgörü:** {b.icgoru}", f"- **Ölçüt:** {b.olcut}"]
    if b.cagri:
        rows.append(f"- **Çağrı:** {b.cagri}")
    rows.append(f"- **Kurgular:** " + "; ".join(
        f"{k.ad} ({k.sure:g} sn → {', '.join(a.ad for a in k.teslim)})" for k in p.kurgular))
    if b.kanitlar:
        rows += ["", "## Kanıtlar", ""] + [f"- {r}" for r in b.kanitlar]
    if m.ton:
        rows += ["", f"**Marka sesi:** {', '.join(m.ton)}"]
    if m.yasak:
        rows += [f"**Kullanılmayacak ifadeler:** {', '.join(m.yasak)}"]
    return "\n".join(rows) + "\n"


def uret(p: Proje, out: str | Path) -> list[Path]:
    """Bütün çıktıları `out` altına yazar ve yazılan dosyaları döndürür."""
    out = Path(out)
    written: list[Path] = []

    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    for hedef, fn in marka_mod.EXPORTERS.items():
        write(out / "marka" / marka_mod.EXPORT_FILES[hedef], fn(p.marka))
    write(out / "brif.md", brif_md(p))

    dil = p.diller[0]
    for k in p.kurgular:
        write(out / k.ad / "manifest.json", json.dumps(manifest(p, k), ensure_ascii=False, indent=2) + "\n")
        if any(c.metin_anahtari for c in k.cekimler):
            for d in p.diller:
                write(out / k.ad / f"altyazi.{d}.srt", altyazi(p, k, d))
                write(out / k.ad / f"altyazi.{d}.vtt", altyazi(p, k, d, vtt=True))
        tl = zaman_cizelgesi(list(k.cekimler), k.fps)
        for a in k.teslim:
            kareler = [cekim_svg(z, a, p, dil) for z in tl]
            for i, (z, svg) in enumerate(zip(tl, kareler)):
                write(out / k.ad / a.ad / "kareler" / f"{i + 1:02d}-{z.cekim.cekim}.svg", svg)
            write(out / k.ad / a.ad / "animatik.html", animatik_html(p, k, a, kareler))
    return written
