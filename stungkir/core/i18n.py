# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Язык интерфейса. Исходный - русский: в коде все надписи русские, tr("Сохранить") на английском
даёт "Save" из словаря lang_en. Нет перевода - остаётся русский текст: ничего не ломается,
просто где-то видно русское слово. Данные в файлах (статусы плана, шаблоны) не переводятся никогда -
только то, что на экране. Язык выбирается при первом запуске и меняется в «Настройках» (после перезапуска)."""

import re

LANGUAGES = {"ru": "Русский", "en": "English (US)", "en-GB": "English (UK)"}
DEFAULT = "ru"
LANG = DEFAULT
# британский - американский перевод с британским написанием: слово -> слово (заглавная буква сохраняется)
BRITISH = {"color": "colour", "colors": "colours", "colored": "coloured", "multicolored": "multicoloured", "neighbor": "neighbour",
           "neighbors": "neighbours", "favorite": "favourite", "favorites": "favourites", "gray": "grey",
           "center": "centre", "centered": "centred", "canceled": "cancelled", "minimized": "minimised",
           "maximized": "maximised", "recognized": "recognised", "organize": "organise", "organized": "organised",
           "customize": "customise", "behavior": "behaviour", "analyze": "analyse"}
# русские формы слова (1, 2, 5) -> английские (1, много): plural() из textutil берёт их отсюда
PLURALS = {
    ("слово", "слова", "слов"): ("word", "words"), ("слова", "слов", "слов"): ("word", "words"),
    ("день", "дня", "дней"): ("day", "days"), ("файле", "файлах", "файлах"): ("file", "files"),
    ("файл", "файла", "файлов"): ("file", "files"), ("глава", "главы", "глав"): ("chapter", "chapters"),
    ("главы", "глав", "глав"): ("chapter", "chapters"), ("главу", "главы", "глав"): ("chapter", "chapters"),
    ("главе", "главах", "главах"): ("chapter", "chapters"), ("место", "места", "мест"): ("place", "places"),
    ("реплика", "реплики", "реплик"): ("line", "lines"), ("год", "года", "лет"): ("year", "years"),
    ("раз", "раза", "раз"): ("time", "times"), ("предложение", "предложения", "предложений"): ("sentence", "sentences"),
    ("категории", "категориях", "категориях"): ("category", "categories"), ("знак", "знака", "знаков"): ("character", "characters"),
    ("абзац", "абзаца", "абзацев"): ("paragraph", "paragraphs"),
    ("абзац затронут", "абзаца затронуто", "абзацев затронуто"): ("paragraph affected", "paragraphs affected"),
    ("совпадение", "совпадения", "совпадений"): ("match", "matches"), ("пометка", "пометки", "пометок"): ("mark", "marks"),
}
_BRITISH_RE = re.compile(r"\b(" + "|".join(BRITISH) + r")\b", re.IGNORECASE)


def set_language(code):
    global LANG
    LANG = code if code in LANGUAGES else DEFAULT


def tr(text, lang=None):
    """Надпись на языке интерфейса (или на lang). С подстановкой - так: tr("Глав: {n}").format(n=3)."""
    lang = lang or LANG
    if lang == DEFAULT:
        return text
    from .lang_en import EN
    english = EN.get(text, text)
    return british(english) if lang == "en-GB" and english != text else english


def british(text):
    def swap(match):
        word = BRITISH[match.group(0).lower()]
        return word.capitalize() if match.group(0)[0].isupper() else word
    return _BRITISH_RE.sub(swap, text)


def english_plural(n, forms):
    """Английская форма для русских форм слова или None (тогда остаётся русская)."""
    if LANG == DEFAULT or forms not in PLURALS:
        return None
    one, many = PLURALS[forms]
    return one if abs(n) == 1 else many
