"""Tasarım belirteçleri: tek marka kitinden web, tasarım aracı ve oyun motoru çıktısı.

- CSS özel özellikleri (web sitesi, açılış sayfası, HTML animatik)
- W3C Design Tokens (DTCG) JSON (Figma Tokens Studio, Style Dictionary)
- Unity C# sabitleri (oyun arayüzü ve marka içi oyunlar)
"""

from __future__ import annotations

import json

from . import color
from .brand import Brand


def _kebab(name: str) -> str:
    return name.replace("_", "-")


def pascal(name: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in name.replace("-", "_").split("_") if p)


def to_css(brand: Brand) -> str:
    lines = [f"/* {brand.name} — atolye tarafından üretildi, elle düzenlemeyin. */", ":root {"]
    for role, value in brand.colors.items():
        lines.append(f"  --color-{_kebab(role)}: {value};")
    for role, style in brand.typography.items():
        lines.append(f"  --font-{_kebab(role)}-family: {json.dumps(style.family)};")
        lines.append(f"  --font-{_kebab(role)}-weight: {style.weight};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def to_dtcg(brand: Brand) -> str:
    doc = {
        "$description": f"{brand.name} marka belirteçleri (atolye)",
        "color": {role: {"$type": "color", "$value": value} for role, value in brand.colors.items()},
        "font": {
            role: {
                "family": {"$type": "fontFamily", "$value": style.family},
                "weight": {"$type": "fontWeight", "$value": style.weight},
            }
            for role, style in brand.typography.items()
        },
    }
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def to_unity(brand: Brand, namespace: str = "Atolye.Brand") -> str:
    cls = pascal(brand.id) + "Tokens"
    out = [
        "// atolye tarafından üretildi, elle düzenlemeyin.",
        "using UnityEngine;",
        "",
        f"namespace {namespace}",
        "{",
        f"    /// <summary>{brand.name} marka belirteçleri.</summary>",
        f"    public static class {cls}",
        "    {",
    ]
    for role, value in brand.colors.items():
        r, g, b = color.to_rgb(value)
        out.append(f"        public static readonly Color32 {pascal(role)} = new Color32({r}, {g}, {b}, 255);")
    for role, style in brand.typography.items():
        out.append(f"        public const string {pascal(role)}FontFamily = {json.dumps(style.family)};")
        out.append(f"        public const int {pascal(role)}FontWeight = {style.weight};")
    out += ["    }", "}"]
    return "\n".join(out) + "\n"
