"""Proje klasörü: `marka.json`, `brif.json` ve bir ya da daha çok `storyboard*.json`.

Tek brif, birden çok storyboard: aynı önerme her kanal için ayrı kurgulanır
(örn. 30 sn YouTube, 15 sn hikâye, 6 sn bumper).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .brand import Brand, parse_brand, validate_brand
from .brief import Brief, parse_brief, validate_brief
from .formats import FORMATS
from .issues import Issue, error, has_errors
from .storyboard import Storyboard, parse_storyboard, validate_storyboard

BRAND_FILE = "marka.json"
BRIEF_FILE = "brif.json"
STORYBOARD_GLOB = "storyboard*.json"


@dataclass(frozen=True)
class Project:
    root: Path
    brand: Brand
    brief: Brief
    storyboards: dict[str, Storyboard]  # dosya adı (uzantısız) → storyboard


def _read_json(path: Path, issues: list[Issue]) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issues.append(error(path.name, "dosya yok"))
    except json.JSONDecodeError as e:
        issues.append(error(path.name, f"geçersiz JSON (satır {e.lineno}, sütun {e.colno}): {e.msg}"))
    return None


def load(root: str | Path) -> tuple[Project | None, list[Issue]]:
    """Projeyi okur ve doğrular. Hata varsa proje None döner; uyarılar her durumda döner."""
    root = Path(root)
    issues: list[Issue] = []

    brand_raw = _read_json(root / BRAND_FILE, issues)
    brief_raw = _read_json(root / BRIEF_FILE, issues)
    brand = brief = None
    if brand_raw is not None:
        found = validate_brand(brand_raw)
        issues.extend(found)
        if not has_errors(found):
            brand = parse_brand(brand_raw)
    if brief_raw is not None:
        found = validate_brief(brief_raw, set(FORMATS))
        issues.extend(found)
        if not has_errors(found):
            brief = parse_brief(brief_raw)

    paths = sorted(root.glob(STORYBOARD_GLOB))
    if not paths:
        issues.append(error(STORYBOARD_GLOB, "en az bir storyboard dosyası gerekli"))
    boards: dict[str, Storyboard] = {}
    for path in paths:
        raw = _read_json(path, issues)
        if raw is None:
            continue
        found = [Issue(i.severity, f"{path.stem}:{i.where}", i.message)
                 for i in validate_storyboard(raw, brand, brief)]
        issues.extend(found)
        if not has_errors(found):
            boards[path.stem] = parse_storyboard(raw)

    if has_errors(issues) or brand is None or brief is None:
        return None, issues
    return Project(root, brand, brief, boards), issues
