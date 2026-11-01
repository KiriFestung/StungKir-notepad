# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Праздничное оформление: когда какой праздник, его цвета и настройки. Только данные и расчёты -
без окон и рисования (рисует fun/season_scene.py, настраивает fun/season_settings.py).
Настройки лежат в общих настройках (config) с ключами season*. Пока есть Рождество; Хэллоуин, лето и
свой праздник по датам встанут сюда же отдельными записями."""

import math
from datetime import date

SEASONS = {
    "xmas": {
        "name": "Рождество",
        "from": (12, 15), "to": (1, 14),           # с 15 декабря по 14 января
        "art": "xmas",
        # тёплая комната: шоколадные стены, сливочный текст, золото и клюква
        "palette": {"BG": "#1b1311", "PANEL": "#221815", "BORDER": "#3a2a22", "HOVER": "#2e211b",
                    "TEXT": "#efe3cc", "DIALOGUE": "#e8c169", "PUNCT": "#fff8ea", "SPELL": "#ff6b6b",
                    "REPEAT_BG": "#3b2c5e", "CRUTCH_BG": "#4d3a14", "MARKER": "#f0a08f", "MARKER_BG": "#3a2228",
                    "LORE": "#9cbf9f", "DIM": "#93806f", "MINOR": "#93806f", "ACCENT": "#7a1f2b",
                    "SELECT": "#5a1c26", "FOUND": "#4d4420", "IMPORTANT": "#e8c169",
                    "CLOCK_FACE": "#173322", "CLOCK_RING": "#e0b04a", "CLOCK_HANDS": "#f3e3c0",
                    "CLOCK_MINUTE": "#e8c169", "FOX": "#7a1f2b", "FOX_2": "#e8c169"},
    },
}

FIXED_TODAY = None      # проверки ставят сюда летний день: в декабре они идут так же, как летом

# выбор в настройках: само по датам, всегда один праздник или выключено
CHOICES = {"auto": "Само по датам", "xmas": "Всегда Рождество", "off": "Выключено"}

GARLAND_MODES = {"twinkle": "мерцают", "steady": "горят ровно", "chase": "бегут огоньки",
                 "wave": "волна", "breathe": "дышат", "random": "вразнобой"}
GARLAND_COLORS = {"multi": "разноцветные", "warm": "тёплые", "cold": "холодные", "gold": "золотые",
                  "custom": "свои"}
PALETTES = {"multi": ["#ff4d4d", "#ffcf4d", "#4dd27a", "#5aa8ff", "#ff8ad8"],
            "warm": ["#ffcf6b", "#ffb04d", "#ffe3a3", "#ff9a4d"],
            "cold": ["#9fd6ff", "#e8f4ff", "#7ab8ff", "#b9a6ff"],
            "gold": ["#ffd27a", "#ffe9b0", "#f2b84b"]}

DEFAULTS = {"season": "auto",            # auto / xmas / off
            "season_colors": True,       # цвета праздника вместо своей темы
            "season_room": True,         # комната: ёлка, камин, кресла, фонарь, пол
            "season_snow_under": True,   # снег под текстом
            "season_snow_over": True,    # редкий снег поверх (затихает, пока печатаешь)
            "season_motion": True,       # движение: огонь, снег, огоньки; выключено - неподвижная картинка
            "season_garland": "twinkle",
            "season_garland_colors": "multi",
            "season_custom_colors": ["#ff4d4d", "#ffffff", "#4dd27a"]}


def option(config, key):
    value = (config or {}).get(key, DEFAULTS[key])
    default = DEFAULTS[key]
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if key == "season":
        return value if value in CHOICES else default
    if key == "season_garland":
        return value if value in GARLAND_MODES else default
    if key == "season_garland_colors":
        return value if value in GARLAND_COLORS else default
    if key == "season_custom_colors":
        good = [c for c in value if isinstance(c, str) and c.startswith("#") and len(c) in (4, 7)] \
            if isinstance(value, list) else []
        return good[:8] or list(default)
    return value


def in_range(day, start, end):
    """Попадает ли день в праздник: (месяц, число) с - по, через Новый год тоже."""
    key = (day.month, day.day)
    if start <= end:
        return start <= key <= end
    return key >= start or key <= end


def active(config, today=None):
    """Какой праздник сейчас показывать: ключ из SEASONS или None."""
    choice = option(config, "season")
    if choice == "off":
        return None
    if choice in SEASONS:
        return choice
    today = today or FIXED_TODAY or date.today()
    for key, season in SEASONS.items():
        if in_range(today, season["from"], season["to"]):
            return key
    return None


def palette(key):
    return dict(SEASONS[key]["palette"])


def garland_colors(config):
    kind = option(config, "season_garland_colors")
    return option(config, "season_custom_colors") if kind == "custom" else list(PALETTES[kind])


def _hash(i):
    """Число 0..1 по номеру огонька - одинаковое при каждом запуске (без random)."""
    x = math.sin(i * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


def bulb_level(mode, index, count, t):
    """Яркость огонька 0..1 в момент t (секунды). Чистая функция - одна для гирлянды, ёлки и венка."""
    count = max(1, count)
    if mode == "steady":
        return 1.0
    if mode == "chase":                          # бегут: три огонька из каждых пяти, сдвиг 4 раза в секунду
        step = int(t * 4)
        return 1.0 if (index + step) % 5 < 3 else 0.18
    if mode == "wave":                           # по гирлянде идёт волна света
        return 0.25 + 0.75 * (0.5 + 0.5 * math.sin(t * 2.4 - index * 0.55))
    if mode == "breathe":                        # все вместе медленно разгораются и гаснут
        return 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 1.3))
    if mode == "random":                         # каждый сам по себе: включён или нет
        period = 0.8 + 1.6 * _hash(index)
        return 1.0 if (t / period + _hash(index + 99)) % 1.0 < 0.6 else 0.15
    # twinkle: горят, но каждый чуть мерцает в своём ритме
    return 0.72 + 0.28 * math.sin(t * (1.5 + 2.5 * _hash(index)) + _hash(index + 7) * 6.28)
