# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Язык интерфейса. Исходный - русский: в коде все надписи русские, tr("Сохранить") на английском
даёт "Save" из словаря lang_en. Нет перевода - остаётся русский текст: ничего не ломается,
просто где-то видно русское слово. Данные в файлах (статусы плана, шаблоны) не переводятся никогда -
только то, что на экране. Язык выбирается при первом запуске и меняется в «Настройках» (после перезапуска)."""

LANGUAGES = {"ru": "Русский", "en": "English"}
DEFAULT = "ru"
LANG = DEFAULT


def set_language(code):
    global LANG
    LANG = code if code in LANGUAGES else DEFAULT


def tr(text, lang=None):
    """Надпись на языке интерфейса (или на lang). С подстановкой - так: tr("Глав: {n}").format(n=3)."""
    if (lang or LANG) == DEFAULT:
        return text
    from .lang_en import EN
    return EN.get(text, text)
