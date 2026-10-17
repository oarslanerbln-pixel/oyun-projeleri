"""Stratejik brif: her yaratıcı işin neden yapıldığını tek sayfada tutar.

Rasyonel kreatifin ilk kuralı: tek bir önerme (single-minded proposition)
ve ölçülebilir bir hedef olmadan storyboard üretilmez.
"""

from __future__ import annotations

from dataclasses import dataclass

from .issues import Issue, error, warning

REQUIRED_FIELDS = ("objective", "audience", "insight", "proposition", "kpi")
PROPOSITION_MAX_WORDS = 12


@dataclass(frozen=True)
class Brief:
    objective: str
    audience: str
    insight: str
    proposition: str
    kpi: str
    cta: str = ""
    channels: tuple[str, ...] = ()
    reasons_to_believe: tuple[str, ...] = ()


def validate_brief(data: object, known_formats: set[str]) -> list[Issue]:
    if not isinstance(data, dict):
        return [error("brif", "nesne olmalı")]
    issues: list[Issue] = []
    for name in REQUIRED_FIELDS:
        value = data.get(name)
        if not isinstance(value, str) or not value.strip():
            issues.append(error(f"brif.{name}", "zorunlu alan boş"))

    proposition = data.get("proposition")
    if isinstance(proposition, str):
        words = len(proposition.split())
        if words > PROPOSITION_MAX_WORDS:
            issues.append(warning("brif.proposition",
                                  f"{words} sözcük; tek önerme {PROPOSITION_MAX_WORDS} sözcüğü geçmemeli"))
        if " ve " in f" {proposition.casefold()} ":
            issues.append(warning("brif.proposition", "'ve' içeriyor; iki önerme olabilir"))

    channels = data.get("channels", [])
    if not isinstance(channels, list):
        issues.append(error("brif.channels", "liste olmalı"))
    else:
        for ch in channels:
            if ch not in known_formats:
                issues.append(error("brif.channels", f"bilinmeyen kanal biçimi {ch!r}"))

    rtb = data.get("reasons_to_believe", [])
    if not isinstance(rtb, list) or not all(isinstance(r, str) for r in rtb):
        issues.append(error("brif.reasons_to_believe", "metin listesi olmalı"))
    elif not rtb:
        issues.append(warning("brif.reasons_to_believe", "önermeyi destekleyen kanıt yok"))
    return issues


def parse_brief(data: dict) -> Brief:
    return Brief(
        objective=data["objective"],
        audience=data["audience"],
        insight=data["insight"],
        proposition=data["proposition"],
        kpi=data["kpi"],
        cta=data.get("cta", ""),
        channels=tuple(data.get("channels", [])),
        reasons_to_believe=tuple(data.get("reasons_to_believe", [])),
    )
