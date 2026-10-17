"""Marka kiti: renk rolleri, tipografi ve marka sesi.

Renkler değerle değil rolle anılır (`primary`, `background`, `text`…);
storyboard ve oyun kodu yalnız rolleri bilir. Marka yenilendiğinde tek dosya
değişir, bütün çıktılar yeniden üretilir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import color
from .issues import Issue, error, warning

REQUIRED_COLOR_ROLES = ("primary", "background", "text")
REQUIRED_TYPE_ROLES = ("heading", "body")
_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def fold(text: str) -> str:
    """Türkçe ve İngilizce için büyük/küçük harf katlama.

    `str.casefold()` "İ" harfini "i" + birleşik nokta yapar ve "I"yı "ı" değil "i"
    yapar; bu yüzden "EN İYİ" ile "en iyi" eşleşmez. Yasak sözcük denetimi
    kaçırmaktansa fazla yakalamayı seçer: i/ı/İ/I hepsi "i" sayılır.
    """
    return text.replace("İ", "i").casefold().replace("\u0307", "").replace("ı", "i")


@dataclass(frozen=True)
class TypeStyle:
    family: str
    weight: int = 400


@dataclass(frozen=True)
class Brand:
    id: str
    name: str
    colors: dict[str, str]
    typography: dict[str, TypeStyle]
    tone: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()
    logo_text: str = ""
    extra: dict = field(default_factory=dict)

    def color(self, role: str) -> str:
        return self.colors[role]

    def forbidden_hits(self, text: str) -> list[str]:
        """Metinde geçen yasak ifadeler (büyük/küçük harf duyarsız, sözcük sınırıyla)."""
        folded = fold(text)
        return [w for w in self.forbidden
                if re.search(rf"(?<!\w){re.escape(fold(w))}(?!\w)", folded)]


def validate_brand(data: object) -> list[Issue]:
    if not isinstance(data, dict):
        return [error("marka", "nesne olmalı")]
    issues: list[Issue] = []

    bid = data.get("id")
    if not isinstance(bid, str) or not _ID.match(bid):
        issues.append(error("marka.id", "küçük harf, rakam ve tire olmalı (örn. demli-kahve)"))
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        issues.append(error("marka.name", "boş olamaz"))

    colors = data.get("colors")
    if not isinstance(colors, dict):
        issues.append(error("marka.colors", "nesne olmalı"))
        colors = {}
    for role in REQUIRED_COLOR_ROLES:
        if role not in colors:
            issues.append(error(f"marka.colors.{role}", "zorunlu renk rolü eksik"))
    for role, value in colors.items():
        if not _ID.match(str(role).replace("_", "-")):
            issues.append(error(f"marka.colors.{role}", "rol adı küçük harf ve alt çizgi olmalı"))
        if not color.is_hex(value):
            issues.append(error(f"marka.colors.{role}", f"#RRGGBB olmalı, {value!r} geldi"))
    if all(color.is_hex(colors.get(r)) for r in ("text", "background")):
        ratio = color.contrast_ratio(colors["text"], colors["background"])
        if ratio < color.CONTRAST_TEXT:
            issues.append(error("marka.colors",
                                f"text/background kontrastı {ratio:.2f}, en az {color.CONTRAST_TEXT} olmalı"))

    typo = data.get("typography")
    if not isinstance(typo, dict):
        issues.append(error("marka.typography", "nesne olmalı"))
        typo = {}
    for role in REQUIRED_TYPE_ROLES:
        if role not in typo:
            issues.append(error(f"marka.typography.{role}", "zorunlu yazı rolü eksik"))
    for role, style in typo.items():
        where = f"marka.typography.{role}"
        if not isinstance(style, dict) or not isinstance(style.get("family"), str) or not style["family"].strip():
            issues.append(error(where, "family alanı zorunlu"))
            continue
        weight = style.get("weight", 400)
        if not isinstance(weight, int) or isinstance(weight, bool) or weight % 100 or not 100 <= weight <= 900:
            issues.append(error(where, f"weight 100–900 arası yüzlük olmalı, {weight!r} geldi"))

    voice = data.get("voice", {})
    if not isinstance(voice, dict):
        issues.append(error("marka.voice", "nesne olmalı"))
    else:
        for key in ("tone", "forbidden"):
            value = voice.get(key, [])
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
                issues.append(error(f"marka.voice.{key}", "boş olmayan metinlerden oluşan liste olmalı"))
        if not voice.get("tone"):
            issues.append(warning("marka.voice.tone", "marka sesi tanımsız; metin yazarı neye göre yazacak?"))

    return issues


def parse_brand(data: dict) -> Brand:
    """`validate_brand` hata vermediyse çağrılır."""
    voice = data.get("voice", {})
    return Brand(
        id=data["id"],
        name=data["name"],
        colors={k: v.lower() for k, v in data["colors"].items()},
        typography={k: TypeStyle(v["family"], v.get("weight", 400)) for k, v in data["typography"].items()},
        tone=tuple(voice.get("tone", [])),
        forbidden=tuple(voice.get("forbidden", [])),
        logo_text=data.get("logo", {}).get("text", ""),
        extra={k: v for k, v in data.items()
               if k not in ("id", "name", "colors", "typography", "voice", "logo")},
    )
