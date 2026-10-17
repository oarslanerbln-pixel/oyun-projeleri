"""Storyboard: sahneler, zaman çizelgesi ve rasyonel kreatif denetimleri.

Denetimler tat değil kural denetler: okunabilir mi (kontrast, okuma hızı),
platforma sığıyor mu (süre), marka erken görünüyor mu, marka sesine aykırı
söz var mı, brifteki çağrı (CTA) ekranda mı.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import color
from .brand import Brand
from .brief import Brief
from .formats import FORMATS, Format
from .issues import Issue, error, warning

FPS_ALLOWED = (24, 25, 30, 60)
TRANSITIONS = ("cut", "fade", "slide")
MOTIONS = ("none", "rise", "zoom")
# Ekrandaki metin için rahat okuma hızı (sözcük/saniye). Üstü uyarı.
READING_WPS = 3.0
# Kısa biçimlerde markanın görünmesi gereken süre (saniye).
BRAND_WITHIN_SECONDS = 3.0
SHORT_FORM_MAX = 90


@dataclass(frozen=True)
class Scene:
    id: str
    duration: float
    background: str = "background"
    foreground: str = "text"
    headline: str = ""
    body: str = ""
    cta: bool = False
    show_logo: bool = False
    transition: str = "cut"
    motion: str = "none"

    @property
    def words(self) -> int:
        return len(self.headline.split()) + len(self.body.split())


@dataclass(frozen=True)
class Storyboard:
    title: str
    format: Format
    fps: int
    scenes: tuple[Scene, ...]

    @property
    def duration(self) -> float:
        return sum(s.duration for s in self.scenes)


@dataclass(frozen=True)
class TimedScene:
    scene: Scene
    start: float
    end: float
    start_frame: int
    end_frame: int  # dahil değil

    @property
    def frames(self) -> int:
        return self.end_frame - self.start_frame


def timeline(board: Storyboard) -> list[TimedScene]:
    """Sahneleri art arda dizer. Kare sınırları birikimli süreden yuvarlanır,
    böylece yuvarlama hatası birikmez ve sahneler arasında boşluk kalmaz."""
    out: list[TimedScene] = []
    t = 0.0
    for s in board.scenes:
        start, end = t, t + s.duration
        out.append(TimedScene(s, round(start, 6), round(end, 6),
                              round(start * board.fps), round(end * board.fps)))
        t = end
    return out


def _scene_fields(raw: dict) -> dict:
    keys = Scene.__dataclass_fields__.keys()
    return {k: raw[k] for k in keys if k in raw}


def validate_storyboard(data: object, brand: Brand | None, brief: Brief | None) -> list[Issue]:
    if not isinstance(data, dict):
        return [error("storyboard", "nesne olmalı")]
    issues: list[Issue] = []

    fmt = FORMATS.get(data.get("format"))
    if fmt is None:
        issues.append(error("storyboard.format",
                            f"bilinmeyen biçim {data.get('format')!r}; seçenekler: {', '.join(FORMATS)}"))
    fps = data.get("fps", 30)
    if fps not in FPS_ALLOWED:
        issues.append(error("storyboard.fps", f"{fps!r} desteklenmiyor; {FPS_ALLOWED}"))

    raw_scenes = data.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        issues.append(error("storyboard.scenes", "en az bir sahne gerekli"))
        return issues

    seen: set[str] = set()
    total = 0.0
    logo_at: float | None = None
    has_cta = False
    for i, raw in enumerate(raw_scenes):
        where = f"storyboard.scenes[{i}]"
        if not isinstance(raw, dict):
            issues.append(error(where, "nesne olmalı"))
            continue
        sid = raw.get("id")
        if not isinstance(sid, str) or not sid:
            issues.append(error(where, "id zorunlu"))
        elif sid in seen:
            issues.append(error(where, f"id {sid!r} tekrar ediyor"))
        else:
            seen.add(sid)
            where = f"storyboard.scenes[{sid}]"

        duration = raw.get("duration")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
            issues.append(error(where, "duration pozitif saniye olmalı"))
            continue

        for key, allowed in (("transition", TRANSITIONS), ("motion", MOTIONS)):
            if key in raw and raw[key] not in allowed:
                issues.append(error(where, f"{key} {raw[key]!r} bilinmiyor; {allowed}"))
        for key in ("headline", "body"):
            if key in raw and not isinstance(raw[key], str):
                issues.append(error(where, f"{key} metin olmalı"))

        scene = Scene(**_scene_fields(raw))
        if scene.show_logo and logo_at is None:
            logo_at = total
        has_cta = has_cta or scene.cta

        if scene.words and scene.words / scene.duration > READING_WPS:
            issues.append(warning(where, f"{scene.words} sözcük {scene.duration} sn'de okunmaz "
                                         f"(en çok {READING_WPS:g} sözcük/sn)"))

        if brand is not None:
            issues.extend(_check_scene_brand(where, scene, brand))
        total += scene.duration

    if fmt is not None:
        if total > fmt.max_seconds:
            issues.append(error("storyboard", f"toplam {total:g} sn, {fmt.label} en çok {fmt.max_seconds:g} sn"))
        if fmt.max_seconds <= SHORT_FORM_MAX and (logo_at is None or logo_at > BRAND_WITHIN_SECONDS):
            issues.append(warning("storyboard",
                                  f"kısa biçimde marka ilk {BRAND_WITHIN_SECONDS:g} sn içinde görünmeli "
                                  "(bir sahnede show_logo: true)"))
    if brief is not None:
        if brief.cta and not has_cta:
            issues.append(warning("storyboard", f"brifte CTA var ({brief.cta!r}) ama hiçbir sahne cta: true değil"))
        if fmt is not None and brief.channels and fmt.id not in brief.channels:
            issues.append(warning("storyboard.format", f"{fmt.id!r} brifin kanalları arasında değil"))
    return issues


def _check_scene_brand(where: str, scene: Scene, brand: Brand) -> list[Issue]:
    issues: list[Issue] = []
    bg, fg = scene.background, scene.foreground
    for role in (bg, fg):
        if role not in brand.colors:
            issues.append(error(where, f"marka kitinde {role!r} renk rolü yok"))
    if bg in brand.colors and fg in brand.colors:
        ratio = color.contrast_ratio(brand.color(fg), brand.color(bg))
        if scene.headline and ratio < color.CONTRAST_LARGE:
            issues.append(error(where, f"başlık kontrastı {ratio:.2f} ({bg} üstünde {fg}), "
                                       f"en az {color.CONTRAST_LARGE}"))
        if scene.body and ratio < color.CONTRAST_TEXT:
            issues.append(error(where, f"gövde kontrastı {ratio:.2f} ({bg} üstünde {fg}), "
                                       f"en az {color.CONTRAST_TEXT}"))
    for text in (scene.headline, scene.body):
        for hit in brand.forbidden_hits(text):
            issues.append(error(where, f"marka sesine aykırı ifade: {hit!r}"))
    return issues


def parse_storyboard(data: dict) -> Storyboard:
    return Storyboard(
        title=data.get("title", ""),
        format=FORMATS[data["format"]],
        fps=data.get("fps", 30),
        scenes=tuple(Scene(**_scene_fields(s)) for s in data["scenes"]),
    )
