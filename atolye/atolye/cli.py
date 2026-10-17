"""Komut satırı: `python -m atolye <komut>`.

  denetle <proje>            Marka, brif ve storyboard'ları doğrular.
  uret <proje> [-o çıktı]    Doğrular, sonra belirteçleri, kareleri ve animatiği üretir.
  yeni <klasör> [--ad ...]   Örnek dosyalarla yeni bir proje klasörü açar.
  bicimler                   Desteklenen kanal biçimlerini listeler.

Çıkış kodu: 0 temiz, 1 doğrulama hatası, 2 kullanım hatası.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import __version__, project, render
from .formats import FORMATS
from .issues import ERROR, has_errors


def _report(issues, stream) -> None:
    for i in sorted(issues, key=lambda i: (i.severity != ERROR, i.where)):
        print(f"  {i}", file=stream)
    errors = sum(i.severity == ERROR for i in issues)
    print(f"{errors} hata, {len(issues) - errors} uyarı", file=stream)


def cmd_check(args) -> int:
    proj, issues = project.load(args.project)
    _report(issues, sys.stdout)
    if proj is not None:
        boards = ", ".join(f"{n} ({b.format.id}, {b.duration:g} sn)" for n, b in proj.storyboards.items())
        print(f"Tamam: {proj.brand.name} · {boards}")
    return 1 if has_errors(issues) else 0


def cmd_build(args) -> int:
    proj, issues = project.load(args.project)
    _report(issues, sys.stdout)
    if proj is None:
        print("Üretim yapılmadı: önce hataları düzeltin.")
        return 1
    out = Path(args.out) if args.out else Path(args.project) / "cikti"
    written = render.build(proj, out)
    print(f"{len(written)} dosya yazıldı: {out}")
    for name in proj.storyboards:
        print(f"  animatik: {out / name / 'animatik.html'}")
    return 0


def cmd_new(args) -> int:
    root = Path(args.folder)
    if root.exists() and any(root.iterdir()):
        print(f"{root} boş değil; üstüne yazılmadı.", file=sys.stderr)
        return 2
    name = args.ad or root.name
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "marka"
    root.mkdir(parents=True, exist_ok=True)
    files = {
        project.BRAND_FILE: {
            "id": slug, "name": name,
            "colors": {"primary": "#1f3a5f", "accent": "#f2a541", "on_accent": "#1b1b1b",
                       "background": "#fbf8f3", "text": "#1b1b1b", "on_primary": "#ffffff"},
            "typography": {"heading": {"family": "Inter", "weight": 700},
                           "body": {"family": "Inter", "weight": 400}},
            "voice": {"tone": ["net", "sıcak"], "forbidden": []},
            "logo": {"text": name.upper()},
        },
        project.BRIEF_FILE: {
            "objective": "Neyi değiştirmek istiyoruz? (örn. deneme kaydını %20 artırmak)",
            "audience": "Kime konuşuyoruz?",
            "insight": "Kitlenin söylemeden bildiği gerçek ne?",
            "proposition": "Tek cümlelik önerme",
            "kpi": "Hangi sayıyla ölçeceğiz?",
            "cta": "Şimdi dene",
            "channels": ["reels"],
            "reasons_to_believe": ["Önermeyi destekleyen kanıt"],
        },
        "storyboard.json": {
            "title": f"{name} · tanıtım", "format": "reels", "fps": 30,
            "scenes": [
                {"id": "acilis", "duration": 2, "background": "primary", "foreground": "on_primary",
                 "headline": name, "show_logo": True, "transition": "fade"},
                {"id": "onerme", "duration": 3, "headline": "Tek cümlelik önerme", "motion": "rise"},
                {"id": "cagri", "duration": 2.5, "headline": "Şimdi sıra sende", "cta": True,
                 "transition": "slide"},
            ],
        },
    }
    for fname, data in files.items():
        (root / fname).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Yeni proje: {root} ({', '.join(files)})")
    return 0


def cmd_formats(args) -> int:
    for f in FORMATS.values():
        print(f"  {f.id:<14} {f.width}×{f.height} ({f.aspect}), en çok {f.max_seconds:g} sn · {f.label}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atolye", description="Marka, animasyon ve oyun işleri için altyapı.")
    parser.add_argument("--version", action="version", version=f"atolye {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("denetle", help="projeyi doğrula")
    p.add_argument("project")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("uret", help="doğrula ve çıktıları üret")
    p.add_argument("project")
    p.add_argument("-o", "--out", help="çıktı klasörü (varsayılan: <proje>/cikti)")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("yeni", help="yeni proje klasörü aç")
    p.add_argument("folder")
    p.add_argument("--ad", help="marka adı (varsayılan: klasör adı)")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("bicimler", help="kanal biçimlerini listele")
    p.set_defaults(func=cmd_formats)

    args = parser.parse_args(argv)
    return args.func(args)
