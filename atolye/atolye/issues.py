"""Doğrulama bulguları: her denetim aynı biçimde bulgu döndürür."""

from __future__ import annotations

from dataclasses import dataclass

ERROR = "HATA"
WARNING = "UYARI"


@dataclass(frozen=True)
class Issue:
    severity: str  # ERROR ya da WARNING
    where: str     # "marka.colors.primary", "storyboard.scenes[2]" gibi
    message: str

    def __str__(self) -> str:
        return f"{self.severity} {self.where}: {self.message}"


def error(where: str, message: str) -> Issue:
    return Issue(ERROR, where, message)


def warning(where: str, message: str) -> Issue:
    return Issue(WARNING, where, message)


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == ERROR for i in issues)
