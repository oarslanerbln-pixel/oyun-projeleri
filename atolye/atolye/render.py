"""Çıktı üretimi: sahne SVG'leri, tarayıcıda oynayan animatik ve kurgu manifesti.

SVG kareler sunum ve müşteri onayı içindir; animatik zamanlamayı ve geçişleri
gösterir; `manifest.json` ise asıl kurgu aracına (Clipkit, After Effects,
Remotion, Unity Timeline) aktarılacak, araçtan bağımsız zaman çizelgesidir.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from . import __version__, tokens
from .brand import Brand
from .brief import Brief
from .project import Project
from .storyboard import Storyboard, TimedScene, timeline

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


def _text_block(lines: list[str], x: float, y: float, size: float, fill: str,
                family: str, weight: int) -> str:
    spans = "".join(
        f'<tspan x="{x:g}" dy="{0 if i == 0 else size * LINE_HEIGHT:g}">{escape(line)}</tspan>'
        for i, line in enumerate(lines))
    return (f'<text x="{x:g}" y="{y:g}" fill="{fill}" font-family="{escape(family)}" '
            f'font-weight="{weight}" font-size="{size:g}" text-anchor="middle">{spans}</text>')


def scene_svg(ts: TimedScene, board: Storyboard, brand: Brand, brief: Brief) -> str:
    fmt = board.format
    s = ts.scene
    w, h = fmt.width, fmt.height
    base = min(w, h)
    left, right = w * fmt.safe_side, w * (1 - fmt.safe_side)
    top, bottom = h * fmt.safe_top, h * (1 - fmt.safe_bottom)
    usable = right - left
    cx = w / 2
    bg, fg = brand.color(s.background), brand.color(s.foreground)
    head, body = brand.typography["heading"], brand.typography["body"]

    parts = [f'<rect width="{w}" height="{h}" fill="{bg}"/>']
    if s.show_logo and brand.logo_text:
        size = base * 0.05
        parts.append(_text_block([brand.logo_text], cx, top + size, size, fg, head.family, head.weight))

    h_size, b_size = base * 0.085, base * 0.045
    h_lines = wrap(s.headline, h_size, usable) if s.headline else []
    b_lines = wrap(s.body, b_size, usable) if s.body else []
    gap = b_size if h_lines and b_lines else 0
    block = (len(h_lines) * h_size * LINE_HEIGHT + gap + len(b_lines) * b_size * LINE_HEIGHT)
    y = (top + bottom) / 2 - block / 2
    if h_lines:
        parts.append(_text_block(h_lines, cx, y + h_size, h_size, fg, head.family, head.weight))
        y += len(h_lines) * h_size * LINE_HEIGHT + gap
    if b_lines:
        parts.append(_text_block(b_lines, cx, y + b_size, b_size, fg, body.family, body.weight))

    if s.cta and brief.cta:
        size = base * 0.045
        pill_bg = brand.colors.get("accent", brand.colors["primary"])
        pill_fg = brand.colors.get("on_accent", brand.colors["background"])
        pw = min(usable, len(brief.cta) * size * CHAR_WIDTH + size * 2)
        ph = size * 2
        py = bottom - ph
        parts.append(f'<rect x="{cx - pw / 2:g}" y="{py:g}" width="{pw:g}" height="{ph:g}" '
                     f'rx="{ph / 2:g}" fill="{pill_bg}"/>')
        parts.append(_text_block([brief.cta], cx, py + ph / 2 + size * 0.35, size, pill_fg,
                                 head.family, head.weight))

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'data-scene="{escape(s.id)}">' + "".join(parts) + "</svg>\n")


def manifest(name: str, board: Storyboard, project: Project) -> dict:
    tl = timeline(board)
    return {
        "generator": f"atolye {__version__}",
        "storyboard": name,
        "title": board.title,
        "brand": project.brand.id,
        "proposition": project.brief.proposition,
        "format": {"id": board.format.id, "width": board.format.width,
                   "height": board.format.height, "aspect": board.format.aspect},
        "fps": board.fps,
        "duration": round(board.duration, 6),
        "frames": tl[-1].end_frame if tl else 0,
        "scenes": [{
            "id": t.scene.id,
            "start": t.start, "end": t.end,
            "start_frame": t.start_frame, "end_frame": t.end_frame,
            "background": t.scene.background, "foreground": t.scene.foreground,
            "headline": t.scene.headline, "body": t.scene.body,
            "cta": t.scene.cta, "show_logo": t.scene.show_logo,
            "transition": t.scene.transition, "motion": t.scene.motion,
            "frame_file": f"kareler/{i + 1:02d}-{t.scene.id}.svg",
        } for i, t in enumerate(tl)],
    }


_PLAYER_JS = """
const data = JSON.parse(document.getElementById('timeline').textContent);
const scenes = [...document.querySelectorAll('.scene')];
const bar = document.getElementById('bar'), tc = document.getElementById('tc');
const btn = document.getElementById('play');
let t = 0, playing = true, last = performance.now();
const fmt = s => s.toFixed(2).padStart(5, '0') + ' sn';
function show(time) {
  scenes.forEach((el, i) => {
    const s = data.scenes[i], on = time >= s.start && time < s.end;
    el.classList.toggle('on', on);
    if (on && s.motion === 'zoom') {
      el.style.transform = 'scale(' + (1 + 0.05 * (time - s.start) / (s.end - s.start)) + ')';
    }
  });
  bar.value = time / data.duration * 1000;
  tc.textContent = fmt(time) + ' / ' + fmt(data.duration) + ' · kare ' + Math.floor(time * data.fps);
}
function tick(now) {
  if (playing) { t = (t + (now - last) / 1000) % data.duration; show(t); }
  last = now; requestAnimationFrame(tick);
}
btn.onclick = () => { playing = !playing; btn.textContent = playing ? '❚❚' : '▶'; };
bar.oninput = () => { t = bar.value / 1000 * data.duration; show(t); };
show(0); requestAnimationFrame(tick);
"""


def animatic_html(name: str, board: Storyboard, project: Project, frames: list[str]) -> str:
    m = manifest(name, board, project)
    fmt = board.format
    ratio = fmt.width / fmt.height
    sections = []
    for t, svg in zip(m["scenes"], frames):
        cls = f"scene t-{t['transition']} m-{t['motion']}"
        sections.append(f'<section class="{cls}" style="--fade:{min(0.4, (t["end"] - t["start"]) / 3):.2f}s">'
                        f"{svg}</section>")
    title = escape(board.title or name)
    # JSON'u <script> içinde güvenle taşımak için </ dizisini kaçır.
    data = json.dumps(m, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · animatik</title>
<style>
{tokens.to_css(project.brand)}
html, body {{ margin: 0; height: 100%; background: #111; color: #eee; font: 14px system-ui, sans-serif; }}
main {{ display: grid; place-items: center; height: calc(100% - 56px); }}
.stage {{ position: relative; overflow: hidden; aspect-ratio: {fmt.width} / {fmt.height};
  width: min(96vw, calc((100vh - 72px) * {ratio:.4f})); background: var(--color-background); }}
.scene {{ position: absolute; inset: 0; opacity: 0; visibility: hidden; }}
.scene svg {{ width: 100%; height: 100%; display: block; }}
.scene.on {{ opacity: 1; visibility: visible; }}
.scene.t-fade.on {{ animation: fade var(--fade) ease-out; }}
.scene.t-slide.on {{ animation: slide var(--fade) ease-out; }}
.scene.m-rise.on svg text {{ animation: rise .6s ease-out; }}
@keyframes fade {{ from {{ opacity: 0; }} }}
@keyframes slide {{ from {{ transform: translateX(12%); opacity: 0; }} }}
@keyframes rise {{ from {{ transform: translateY(4%); opacity: 0; }} }}
footer {{ display: flex; gap: 12px; align-items: center; padding: 12px 16px; }}
footer input {{ flex: 1; }}
footer button {{ width: 40px; height: 32px; }}
@media (prefers-reduced-motion: reduce) {{ .scene.on, .scene.on svg text {{ animation: none !important; }} }}
</style>
</head>
<body>
<main><div class="stage">{"".join(sections)}</div></main>
<footer><button id="play" aria-label="Oynat / duraklat">❚❚</button>
<input id="bar" type="range" min="0" max="1000" value="0" aria-label="Zaman">
<span id="tc"></span></footer>
<script id="timeline" type="application/json">{data}</script>
<script>{_PLAYER_JS}</script>
</body>
</html>
"""


def brief_md(project: Project) -> str:
    b, brand = project.brief, project.brand
    rows = [f"# {brand.name} · brif", "",
            f"**Önerme:** {b.proposition}", "",
            f"- **Hedef:** {b.objective}",
            f"- **Kitle:** {b.audience}",
            f"- **İçgörü:** {b.insight}",
            f"- **Ölçüt (KPI):** {b.kpi}"]
    if b.cta:
        rows.append(f"- **Çağrı:** {b.cta}")
    if b.channels:
        rows.append(f"- **Kanallar:** {', '.join(b.channels)}")
    if b.reasons_to_believe:
        rows += ["", "## İnandırıcı kanıtlar", ""] + [f"- {r}" for r in b.reasons_to_believe]
    if brand.tone:
        rows += ["", f"**Marka sesi:** {', '.join(brand.tone)}"]
    if brand.forbidden:
        rows += [f"**Kullanılmayacak ifadeler:** {', '.join(brand.forbidden)}"]
    return "\n".join(rows) + "\n"


def build(project: Project, out: str | Path) -> list[Path]:
    """Bütün çıktıları `out` altına yazar ve yazılan dosyaları döndürür."""
    out = Path(out)
    written: list[Path] = []

    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    brand = project.brand
    write(out / "belirtecler" / "tokens.css", tokens.to_css(brand))
    write(out / "belirtecler" / "tokens.json", tokens.to_dtcg(brand))
    write(out / "belirtecler" / f"{tokens.pascal(brand.id)}Tokens.cs", tokens.to_unity(brand))
    write(out / "brif.md", brief_md(project))

    for name, board in project.storyboards.items():
        tl = timeline(board)
        frames = [scene_svg(t, board, brand, project.brief) for t in tl]
        for i, (t, svg) in enumerate(zip(tl, frames)):
            write(out / name / "kareler" / f"{i + 1:02d}-{t.scene.id}.svg", svg)
        write(out / name / "manifest.json",
              json.dumps(manifest(name, board, project), ensure_ascii=False, indent=2) + "\n")
        write(out / name / "animatik.html", animatic_html(name, board, project, frames))
    return written
