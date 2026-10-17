"""Testler için geçerli en küçük marka, brif ve storyboard."""

import copy

BRAND = {
    "id": "test-marka",
    "name": "Test Marka",
    "colors": {"primary": "#000000", "on_primary": "#ffffff", "accent": "#ffcc00",
               "background": "#ffffff", "text": "#111111"},
    "typography": {"heading": {"family": "Inter", "weight": 700}, "body": {"family": "Inter"}},
    "voice": {"tone": ["net"], "forbidden": ["en iyi", "mucize"]},
    "logo": {"text": "TEST"},
}

BRIEF = {
    "objective": "Kaydı artırmak",
    "audience": "Öğrenciler",
    "insight": "Vakitleri yok",
    "proposition": "Beş dakikada hazır",
    "kpi": "Haftalık kayıt",
    "cta": "Hemen dene",
    "channels": ["reels"],
    "reasons_to_believe": ["Ortalama kurulum 4 dk"],
}

BOARD = {
    "title": "Test",
    "format": "reels",
    "fps": 30,
    "scenes": [
        {"id": "a", "duration": 2, "background": "primary", "foreground": "on_primary",
         "headline": "Merhaba", "show_logo": True},
        {"id": "b", "duration": 3, "headline": "Beş dakikada hazır", "cta": True},
    ],
}


def brand(**over):
    d = copy.deepcopy(BRAND); d.update(over); return d


def brief(**over):
    d = copy.deepcopy(BRIEF); d.update(over); return d


def board(**over):
    d = copy.deepcopy(BOARD); d.update(over); return d


def messages(issues, severity=None):
    return [f"{i.where}: {i.message}" for i in issues if severity is None or i.severity == severity]
