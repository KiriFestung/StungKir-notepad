# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Настройки: пути, цвета тем, шрифты, размеры. Окно «Настройки» меняет их через apply_config."""

import json
import os
import sys
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QFont


APP_NAME = "StungKir"
APP_ID = "stungkir"
FLATPAK_ID = "page.codeberg.kirifestung.StungKir"


PORTABLE_MARK = "portable.txt"


def _portable_dir():
    """Переносная версия (с флешки): рядом с StungKir.exe лежит portable.txt. Тогда тексты,
    копии и настройки живут рядом с программой, а на чужом компьютере не остаётся ничего."""
    if not getattr(sys, "frozen", False):
        return None
    folder = Path(sys.executable).resolve().parent
    return folder if (folder / PORTABLE_MARK).is_file() else None


PORTABLE_DIR = _portable_dir()


def _data_dir():
    """Где программа хранит свои копии и журнал: на Windows - в AppData, на Linux - по XDG."""
    if PORTABLE_DIR is not None:
        return PORTABLE_DIR / "Данные"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_ID


DATA_DIR = _data_dir()


def cache_dir():
    """Звуки и картинки, которые программа рисует себе сама (можно удалить - нарисует снова)."""
    if PORTABLE_DIR is not None:
        return DATA_DIR / "кэш"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / APP_ID

# ================= настройки, всё меняется здесь =================
ROOT = Path.home() / "StungKir"  # где хранятся категории и файлы
OLD_ROOT = Path.home() / "Блокнот"   # старая папка: при первом запуске переедет сюда
if PORTABLE_DIR is not None:
    ROOT = PORTABLE_DIR / "StungKir"
    OLD_ROOT = PORTABLE_DIR / "Блокнот"
    # настройки - файлом рядом с программой, а не в реестре Windows
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(DATA_DIR / "настройки"))
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_KEEP = 14                 # сколько дневных архивов хранить
SNAPSHOT_DIR = DATA_DIR / "snapshots"   # снимки всей книги
COLUMN_WIDTH = 740               # ширина колонки текста, как страница книги
FONT_FAMILY = "DejaVu Sans"
FONT_SIZE = 15                   # стартовый размер, дальше Ctrl+колесо / Ctrl+=/-
FONT_WEIGHT = QFont.Normal       # плотнее: «Настройки» → «Насыщенность» (средний, полужирный, жирный)
LINE_HEIGHT = 150                # межстрочный интервал в процентах
ONLY_RUSSIAN = False             # True - в тексте нельзя набрать латиницу (включается в настройках)
AUTOSAVE = True                  # сохранять само: после паузы в наборе и не реже раза в полминуты
AUTOSAVE_PAUSE_MS = 3000         # пауза в наборе, после которой глава сохраняется
AUTOSAVE_MAX_S = 30              # дольше этого несохранённым текст не бывает, даже если печатаешь без пауз
TEXTURE = "none"                 # фон под текстом: none, paper (бумага), linen (лён)
FLAT_WINDOWS = False             # окошки без прозрачной тени (сама включается, если композитора нет)
AUTOSAVE_VERSION_S = 600         # автосохранение делает версию главы не чаще раза в 10 минут
DAILY_GOAL = 500                 # цель на день по умолчанию (0 = без цели), меняется в «Ещё»
CHAPTER_GOAL = 3000              # что предлагать, когда ставишь цель для главы
TABLE_COLUMNS = ["Имя", "Описание", "Заметки"]   # столбцы новой таблицы
TABLE_ROWS = 6                   # сколько пустых строк в новой таблице
BOARD_COLUMNS = ["Завязка", "Развитие", "Кульминация", "Развязка"]   # колонки новой доски
BOOK_FONT = "DejaVu Serif"       # шрифт книги в PDF
BOOK_FONT_DOCX = "Times New Roman"   # шрифт книги в Word

# Палитра без чистого чёрного и яркого зелёного: контраст хватает для чтения,
# но текст не "светится" на фоне.
BG = "#171b18"          # фон
TEXT = "#93bf9c"        # мягкий зелёный текст
DIALOGUE = "#d2b47c"    # реплики (строки, которые начинаются с «—»): мягкий янтарный
SPELL = "#e0645a"       # слово с ошибкой: красное
PUNCT = "#e6ede4"       # знаки препинания: мягкий почти белый, чтобы не сливались с текстом
CRUTCH_BG = "#4a3a1c"   # мои штампы: янтарная подложка и черта
REPEAT_BG = "#403670"   # повтор слова рядом: фиолетовая подложка и черта под словом
MARKER = "#e3a08f"      # пометки [вот такие]: коралловый текст
MARKER_BG = "#3a2723"   # ...на тёмно-красной подложке
LORE = "#5f7e66"        # пунктир под терминами мира
DIM = "#5a7360"         # приглушённый текст (статус, подписи)
PANEL = "#1f2420"       # панели
BORDER = "#2a322c"
HOVER = "#273029"
ACCENT = "#355a41"
IMPORTANT = "#7c3aed"   # важное: главные кнопки («Сохранить»), включённые режимы, галочки
MINOR = "#5a7360"       # неважное: «Отмена», «Стереть историю» - видно, но не тянет взгляд
SELECT = "#2b4535"      # выделение
FOUND = "#46552a"       # найденное в поиске
HINT = "rgba(147, 191, 156, 38)"     # еле заметные язычки у краёв окна
SCROLL = "rgba(147, 191, 156, 30)"   # полоса прокрутки
# кубики, колесо таймера и часы - в индиго и охре, как рисунки ласки и монетки:
# вместе они заметны на любом фоне (на тёмном держит охра, на светлом - индиго)
DICE_BODY = "#3b3590"   # грани кубика
DICE_TEXT = "#f6d27a"   # числа на кубике
FOX = "#2e2a6e"         # колесо таймера: обод и спицы (ключ FOX - со времён лисы)
FOX_2 = "#d4a02e"       # колесо: перекладины, контур и бегущий круг
CLOCK_FACE = "#1e2160"  # циферблат
CLOCK_RING = "#d29a2a"  # ободок и риски
CLOCK_HANDS = "#d29a2a"  # часовая стрелка
CLOCK_MINUTE = "#f3e7cf"  # минутная стрелка
BAR_DAY = "#7c3aed"     # полоска цели дня (у каждой темы свои, подобранные - см. bar_defaults)
BAR_CHAPTER = "#e6b967"  # полоска цели главы
BAR_BOOK = "#67e684"    # полоска дедлайна книги
CRIT_HIGH = "#c8d37a"   # выпал максимум
CRIT_LOW = "#c98575"    # выпала единица

DIALOGUE_MARKS = ("—", "–")   # с чего начинается реплика
FOCUS_DIM = 0.62        # режим фокуса: насколько гасить остальные абзацы (0..1)
TYPEWRITER_POS = 0.42   # печатная машинка: где держать строку (доля высоты окна сверху)
MAX_VERSIONS = 50       # сколько версий хранить на файл
REPEAT_WINDOW = 15      # повтор ищется среди стольких соседних слов
REPEAT_MIN_LEN = 4      # слова короче не проверяются на повтор
TIMER_MINUTES = 10      # таймер по умолчанию
STATS_DAYS = 30         # сколько дней показывать в статистике
NIGHT_FROM = 21         # ночной режим (если «авто»): с какого часа
NIGHT_TO = 7            # ...и до какого
NIGHT_STRENGTH = 1.0    # насколько тёплым и тусклым делать вечером (0..1.5)


LEFT_WIDTH = 280
MARGIN = 12             # отступ выдвижных панелей от краёв окна
EDGE = 10               # сколько пикселей от края окна выдвигает панель
STATUS_IDLE_MS = 2500   # через сколько после набора статус снова становится ярче
DICE = [4, 6, 8, 10, 12, 20, 100]

# знаки на правой панели: (надпись, что вставить, подсказка)
# если вставка из двух частей через "|", выделенный текст оборачивается
SYMBOLS = [
    ("—", "—", "Тире для реплики   Alt+-"),
    ("-", "-", "Короткое тире / дефис"),
    ("…", "…", "Многоточие   Alt+."),
    ("«»", "«|»", "Кавычки-ёлочки   Alt+9"),
    ("„“", "„|“", "Кавычки-лапки"),
    ("а́", "\u0301", "Ударение на гласную перед курсором. Ещё раз - убрать"),
    ("[ ]", "[|]", "Пометка   F7. Ещё раз - убрать или выйти из скобок"),
    ("*к*", "*|*", "Курсив   Ctrl+I. Выдели слова или нажми внутри слова; ещё раз - снять.\n"
                   "Без выделения: нажал - пишешь курсивом, нажал снова - курсив кончился"),
    ("**ж**", "**|**", "Жирный   Ctrl+B. Работает так же, как курсив"),
    ("ё", "ё", "ё, а в начале предложения - Ё. Если выделена «е» - заменит её на «ё»"),
    ("?!", "?!", ""),
    ("!..", "!..", ""),
]
# ================================================================

# Темы: полный набор цветов. Свои темы хранятся в настройках и устроены так же.
COLOR_KEYS = ["BG", "TEXT", "DIALOGUE", "PUNCT", "SPELL", "REPEAT_BG", "CRUTCH_BG", "MARKER", "MARKER_BG", "LORE",
              "FOUND", "SELECT", "DIM", "PANEL", "BORDER", "HOVER", "ACCENT", "IMPORTANT", "MINOR",
              "DICE_BODY", "DICE_TEXT", "FOX", "FOX_2", "CLOCK_FACE", "CLOCK_RING", "CLOCK_HANDS", "CLOCK_MINUTE",
              "BAR_DAY", "BAR_CHAPTER", "BAR_BOOK"]
# группы в окне «Цвета и темы»
COLOR_GROUPS = [
    ("Текст", ["BG", "TEXT", "DIALOGUE", "PUNCT", "SPELL", "LORE", "DIM"]),
    ("Подсветка", ["REPEAT_BG", "CRUTCH_BG", "MARKER", "MARKER_BG", "FOUND", "SELECT"]),
    ("Окно и кнопки", ["PANEL", "BORDER", "HOVER", "ACCENT", "IMPORTANT", "MINOR"]),
    ("Кубики и колесо таймера", ["DICE_BODY", "DICE_TEXT", "FOX", "FOX_2"]),
    ("Часы", ["CLOCK_FACE", "CLOCK_RING", "CLOCK_HANDS", "CLOCK_MINUTE"]),
    ("Полоски цели", ["BAR_DAY", "BAR_CHAPTER", "BAR_BOOK"]),
]
BAR_KEYS = ("BAR_DAY", "BAR_CHAPTER", "BAR_BOOK")
OBJECT_COLORS = {"DICE_BODY": "#3b3590", "DICE_TEXT": "#f6d27a", "FOX": "#2e2a6e", "FOX_2": "#d4a02e",
                 "CLOCK_FACE": "#1e2160", "CLOCK_RING": "#d29a2a", "CLOCK_HANDS": "#d29a2a",
                 "CLOCK_MINUTE": "#f3e7cf"}
# «важное» в каждой теме - заметный цвет, который из неё выбивается
IMPORTANT_COLORS = {"Индиго и охра": "#d4a02e", "Мох": "#7c3aed", "Сирень": "#e11d48", "Сепия": "#c2410c", "Дневная бумага": "#7c3aed",
                    "Полночь": "#e11d48", "Чернила": "#2563eb", "Пергамент": "#9a3412", "Графит": "#7c3aed",
                    "Высокий контраст": "#ffd400"}
THEMES = {
    # основная: глубокий индиго и охра - как иконка, ласка и кубики
    "Индиго и охра": {"BG": "#121429", "TEXT": "#c6cbe9", "DIALOGUE": "#e2b65a", "PUNCT": "#f5efe0",
                      "SPELL": "#ef6b6b", "REPEAT_BG": "#3d3274", "CRUTCH_BG": "#4d3a14", "MARKER": "#f0a08f",
                      "MARKER_BG": "#3a2228", "LORE": "#7f87c6",
                      "DIM": "#6a6f9c", "PANEL": "#181b37", "BORDER": "#282c55", "HOVER": "#212549",
                      "ACCENT": "#2e2a6e", "SELECT": "#2c3268", "FOUND": "#4d4420"},
    "Мох": {"BG": "#171b18", "TEXT": "#93bf9c", "DIALOGUE": "#d2b47c", "PUNCT": "#e6ede4",
                "SPELL": "#e0645a", "REPEAT_BG": "#403670", "CRUTCH_BG": "#4a3a1c", "MARKER": "#e3a08f", "MARKER_BG": "#3a2723",
                "LORE": "#5f7e66",
                "DIM": "#5a7360", "PANEL": "#1f2420", "BORDER": "#2a322c", "HOVER": "#273029",
                "ACCENT": "#355a41", "SELECT": "#2b4535", "FOUND": "#46552a"},
    "Сирень": {"BG": "#16141b", "TEXT": "#b9a6e8", "DIALOGUE": "#e0b77c", "PUNCT": "#efeaf8",
             "SPELL": "#e86a6a", "REPEAT_BG": "#2f4a5c", "CRUTCH_BG": "#4d3b22", "MARKER": "#e3a08f", "MARKER_BG": "#3a2629",
             "LORE": "#7a6d9e",
             "DIM": "#6e6488", "PANEL": "#1e1b25", "BORDER": "#2d2838", "HOVER": "#29243a",
             "ACCENT": "#4c3a7a", "SELECT": "#3a2f5c", "FOUND": "#4a3f2a"},
    "Сепия": {"BG": "#1b1814", "TEXT": "#d4c4a4", "DIALOGUE": "#e3a86f", "PUNCT": "#f3ece0",
              "SPELL": "#e0645a", "REPEAT_BG": "#453c78", "CRUTCH_BG": "#4f3d1e", "MARKER": "#e3a08f", "MARKER_BG": "#3a2723",
              "LORE": "#8a7f69",
              "DIM": "#7d7058", "PANEL": "#23201a", "BORDER": "#332d24", "HOVER": "#2c2720",
              "ACCENT": "#5a4a33", "SELECT": "#43382a", "FOUND": "#4f4a24"},
    # светлая тёплая «бумага» для дня: не белая, контраст около 10:1
    # знаки - спокойный сине-серый: на светлом фоне «почти белые» знаки, как в тёмной теме, не видны
    "Дневная бумага": {"BG": "#f3ecdb", "TEXT": "#3b342b", "DIALOGUE": "#70400f", "PUNCT": "#35587a",
                       "SPELL": "#c0392b", "REPEAT_BG": "#d3bdf0", "CRUTCH_BG": "#f2d38f", "MARKER": "#9a3f25", "MARKER_BG": "#f1cfc1",
                       "LORE": "#9c8f76",
                       "DIM": "#857a68", "PANEL": "#e3d5b8", "BORDER": "#b9a67c", "HOVER": "#d9c9a6",
                       "ACCENT": "#c2a878", "SELECT": "#d8c69c", "FOUND": "#eedd8a"},
    # тёмная фиолетовая в цвет иконки, тёмно-синяя «ночное небо», тёплая светлая мягче «бумаги»,
    # нейтральная серая и высокий контраст (для яркого солнца и усталых глаз - контраст выше обычного)
    "Полночь": {"BG": "#120f1a", "TEXT": "#c3b4ef", "DIALOGUE": "#f2a7b8", "PUNCT": "#f4f0ff",
               "SPELL": "#ff5c74", "REPEAT_BG": "#3d2f6e", "CRUTCH_BG": "#55361a", "MARKER": "#f0a08f", "MARKER_BG": "#3f1f2a",
               "LORE": "#8a76c4",
               "DIM": "#75689a", "PANEL": "#1a1526", "BORDER": "#2c2442", "HOVER": "#251d3a",
               "ACCENT": "#5b2fb3", "SELECT": "#3a2a6a", "FOUND": "#4f2c48"},
    "Чернила": {"BG": "#0f1520", "TEXT": "#b8c7dc", "DIALOGUE": "#e6c07b", "PUNCT": "#eef3fa",
               "SPELL": "#ef6b6b", "REPEAT_BG": "#3b3570", "CRUTCH_BG": "#4a3a1c", "MARKER": "#e3a08f", "MARKER_BG": "#3a2626",
               "LORE": "#6f86a6",
               "DIM": "#5f7189", "PANEL": "#151d2b", "BORDER": "#22304a", "HOVER": "#1d2840",
               "ACCENT": "#2e4a78", "SELECT": "#24395e", "FOUND": "#4a4a22"},
    "Пергамент": {"BG": "#efe4cc", "TEXT": "#3d3326", "DIALOGUE": "#6a320d", "PUNCT": "#2f5a7a",
                 "SPELL": "#b3261e", "REPEAT_BG": "#d6c2ee", "CRUTCH_BG": "#edc77f", "MARKER": "#93361c", "MARKER_BG": "#ecc6b4",
                 "LORE": "#9a8667",
                 "DIM": "#84755b", "PANEL": "#e2d2b0", "BORDER": "#b5a079", "HOVER": "#d8c49c",
                 "ACCENT": "#b89a62", "SELECT": "#d3bd8c", "FOUND": "#e8d37a"},
    "Графит": {"BG": "#1c1c1e", "TEXT": "#c8c8c8", "DIALOGUE": "#d9b98a", "PUNCT": "#f2f2f2",
              "SPELL": "#e5675e", "REPEAT_BG": "#3e3a5e", "CRUTCH_BG": "#4a3d22", "MARKER": "#e3a08f", "MARKER_BG": "#3b2a28",
              "LORE": "#7c7c84",
              "DIM": "#707074", "PANEL": "#242426", "BORDER": "#333336", "HOVER": "#2c2c2f",
              "ACCENT": "#48484e", "SELECT": "#3a3a40", "FOUND": "#4c4a28"},
    "Высокий контраст": {"BG": "#0a0a0a", "TEXT": "#f0f0f0", "DIALOGUE": "#ffd27a", "PUNCT": "#ffffff",
                         "SPELL": "#ff6b6b", "REPEAT_BG": "#4b3c9a", "CRUTCH_BG": "#6b4a10", "MARKER": "#ffb199", "MARKER_BG": "#4a2016",
                         "LORE": "#a3a8ff",
                         "DIM": "#a0a0a0", "PANEL": "#141414", "BORDER": "#5a5a5a", "HOVER": "#262626",
                         "ACCENT": "#5a5a5a", "SELECT": "#3a3a6a", "FOUND": "#6a6a10"},
}
COLOR_NAMES = {
    "BG": "Фон", "TEXT": "Текст", "DIALOGUE": "Реплики", "PUNCT": "Знаки препинания",
    "SPELL": "Ошибки", "REPEAT_BG": "Повторы (подложка)", "CRUTCH_BG": "Мои штампы (подложка)", "MARKER": "Пометки [ ]",
    "MARKER_BG": "Пометки (подложка)", "LORE": "Термины мира (подчёркивание)", "FOUND": "Найденное",
    "SELECT": "Выделение", "DIM": "Приглушённое", "PANEL": "Панели", "BORDER": "Рамки",
    "HOVER": "Под мышкой", "ACCENT": "Акцент (кнопки, полоски)",
    "IMPORTANT": "Важное (главные кнопки, режимы)",
    "MINOR": "Неважное (Отмена, Стереть…)",
    "DICE_BODY": "Кубик", "DICE_TEXT": "Числа на кубике", "FOX": "Колесо: обод и спицы", "FOX_2": "Колесо: перекладины и круг таймера",
    "CLOCK_FACE": "Циферблат", "CLOCK_RING": "Ободок", "CLOCK_HANDS": "Часовая стрелка и риски",
    "CLOCK_MINUTE": "Минутная стрелка",
    "BAR_DAY": "Цель дня", "BAR_CHAPTER": "Цель главы", "BAR_BOOK": "Дедлайн книги",
}
def vivid_on(color, bg, fallback, minimum=3.0):
    """Тот же оттенок, но сочный и заметный на фоне bg (серый - заменяется на fallback)."""
    c = QColor(color)
    hue, sat, val = c.hsvHueF(), c.hsvSaturationF(), c.valueF()
    if hue < 0 or sat < 0.08:
        c = QColor(fallback)
        hue, sat, val = c.hsvHueF(), c.hsvSaturationF(), c.valueF()
    light = QColor(bg).lightness() > 128
    sat = max(sat, 0.75 if light else 0.55)
    val = min(max(val, 0.68), 0.8) if light else max(val, 0.9)       # на светлом - не в коричневый
    out = QColor.fromHsvF(max(hue, 0.0), min(sat, 1.0), val)
    away = QColor("#000000" if light else "#ffffff")
    for _ in range(12):                          # всё ещё сливается с фоном - сдвигаем от фона
        if contrast(out, bg) >= minimum:
            break
        out = mix(out, away, 0.12)
    return out


def hue_gap(a, b):
    gap = abs(max(QColor(a).hsvHueF(), 0.0) - max(QColor(b).hsvHueF(), 0.0))
    return min(gap, 1.0 - gap)


def bar_defaults(colors):
    """Цвета полосок цели для темы: день - «важный», глава - реплики, книга - мир, сочнее и
    обязательно три разных, даже если в теме реплики и мир одного тона."""
    out = {}
    taken = []
    for key, base in zip(BAR_KEYS, (colors["IMPORTANT"], colors["DIALOGUE"], colors["LORE"])):
        color = vivid_on(base, colors["BG"], colors["IMPORTANT"])
        for _ in range(4):
            if all(hue_gap(color, t) >= 0.09 for t in taken):
                break
            color = vivid_on(QColor.fromHsvF((max(color.hsvHueF(), 0.0) + 0.3) % 1.0, color.hsvSaturationF(),
                                             color.valueF()), colors["BG"], colors["IMPORTANT"])
        taken.append(color)
        out[key] = color.name()
    return out


DEFAULT_THEME = "Индиго и охра"
SEASON = None            # идущий праздник (core/seasons.py) - его комната под текстом и снег
SEASON_ROOM = False      # комната праздника под текстом: поле текста прозрачное, комнату рисует оно само
# старые имена тем (из прошлых версий) -> новые: выбранная тема не слетает
THEME_RENAMES = {"Зелёная": "Мох", "Лиса": "Сирень"}


def theme_name(name):
    return THEME_RENAMES.get(name, name) if name else name
DUSK = 0.24              # насколько темнеет дневная тема к концу дня перед сменой на ночную
DAY_THEME = "Дневная бумага"
WEIGHTS = {"Обычный": QFont.Normal, "Средний": QFont.Medium, "Полужирный": QFont.DemiBold,
           "Жирный": QFont.Bold}


def on_color(color):
    """Цвет надписи поверх заливки: белый или почти чёрный - что читается лучше."""
    return "#ffffff" if contrast(color, "#ffffff") >= contrast(color, "#141414") else "#141414"


def rgba(color, alpha):
    c = QColor(color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


def load_config():
    """Настройки из окна «Настройки» поверх значений в начале файла."""
    try:
        config = json.loads(QSettings(APP_ID, APP_ID).value("config", "") or "{}")
    except ValueError:
        config = {}
    apply_config(config)
    from .i18n import set_language
    set_language(config.get("LANGUAGE"))     # язык - только при запуске: на ходу окна стали бы наполовину чужими
    return config


def all_themes(config):
    """Встроенные темы и свои (из настроек). Свои с тем же именем перекрывают встроенные."""
    themes = {name: dict(colors) for name, colors in THEMES.items()}
    for name, colors in (config.get("custom_themes") or {}).items():
        if isinstance(colors, dict):
            base = dict(THEMES[DEFAULT_THEME])
            base.update({k: v for k, v in colors.items() if k in COLOR_KEYS and QColor(v).isValid()})
            if "MINOR" not in colors:
                base["MINOR"] = base["DIM"]          # тема из прошлых версий: «неважное» - как приглушённое
            if not all(k in colors for k in BAR_KEYS):
                base.update(bar_defaults(base))      # своя тема без цветов полосок - подбираем под неё
            themes[name] = base
    return themes


def theme_colors(config, name):
    themes = all_themes(config)
    return dict(themes.get(name) or themes.get(theme_name(name)) or themes[DEFAULT_THEME])


def blend(night, day, share):
    """Цвета между двумя темами: share=0 - первая, 1 - вторая."""
    if share <= 0:
        return dict(night)
    if share >= 1:
        return dict(day)
    return {k: mix(night[k], day[k], share).name() for k in COLOR_KEYS}


def warm(colors, amount):
    """Сдвиг всей палитры: amount от -1 (холоднее) до 1 (теплее)."""
    if not amount:
        return dict(colors)
    out = {}
    for key, value in colors.items():
        c = QColor(value)
        r = c.red() * (1 + 0.07 * amount)
        g = c.green() * (1 + 0.015 * amount)
        b = c.blue() * (1 - 0.16 * amount)
        out[key] = QColor(*(max(0, min(255, round(x))) for x in (r, g, b))).name()
    return out


def _minutes(value, default):
    if isinstance(value, int) and 0 <= value < 24 * 60:
        return value
    return default


def day_share(config, now=None):
    """Насколько сейчас «день»: 0 - ночная тема, 1 - дневная, между ними - плавный переход,
    растянутый на config["transition"] минут вокруг границы."""
    if not config.get("day_theme"):
        return 0.0
    from datetime import datetime
    now = now or datetime.now()
    m = now.hour * 60 + now.minute + now.second / 60
    start = _minutes(config.get("day_from"), 8 * 60)
    end = _minutes(config.get("day_to"), 20 * 60)
    if start == end:
        return 1.0
    inside = start <= m < end if start < end else (m >= start or m < end)

    def distance(a, b):
        d = abs(a - b) % 1440
        return min(d, 1440 - d)
    signed = min(distance(m, start), distance(m, end)) * (1 if inside else -1)
    span = max(0, int(config.get("transition", 40) or 0))
    if span == 0:
        return 1.0 if inside else 0.0
    t = max(0.0, min(1.0, 0.5 + signed / span))
    return t * t * (3 - 2 * t)      # мягкое начало и конец перехода


def contrast(a, b):
    """Контраст двух цветов, как в стандарте WCAG: от 1 до 21."""
    def lum(color):
        c = QColor(color)
        parts = []
        for x in (c.red(), c.green(), c.blue()):
            x /= 255
            parts.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
        return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]
    high, low = sorted((lum(a), lum(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def contrast_hint(ratio):
    if ratio < 4.5:
        return "тяжело читать: текст сливается с фоном"
    if ratio < 7:
        return "читается, но для долгой работы бледновато"
    if ratio <= 12:
        return "удобно для долгого чтения"
    if ratio <= 15:
        return "контрастно: можно чуть мягче"
    return "слишком резко: глаза быстро устанут"


def current_palette(config, now=None):
    """Цвета на этот момент: ночная (основная) тема, днём - дневная, плюс теплота.
    Идёт праздник с его цветами - его цвета вместо тем (свои цвета и теплота - поверх, как обычно)."""
    from . import seasons
    season = seasons.active(config, now.date() if now else None)
    if season and seasons.option(config, "season_colors"):
        colors = dict(THEMES[DEFAULT_THEME])
        colors.update(seasons.palette(season))
        colors.update(bar_defaults(colors))
        try:
            amount = max(-100, min(100, int(config.get("warmth", 0) or 0))) / 100
        except (TypeError, ValueError):
            amount = 0
        return warm(colors, amount)
    night = theme_colors(config, config.get("theme") or DEFAULT_THEME)
    # старые «свои цвета» из первых версий настроек кладутся поверх основной темы
    for key in ("TEXT", "BG", "DIALOGUE", "PUNCT"):
        if config.get(key) and QColor(config[key]).isValid():
            night[key] = config[key]
    colors = night
    if config.get("day_theme"):
        share = day_share(config, now)
        if share >= 0.5:
            # прямое смешивание светлой и тёмной темы дало бы серый текст на сером фоне,
            # поэтому в переходе дневная тема плавно темнеет (контраст остаётся удобным),
            # а саму смену на ночную окно делает быстрой анимацией
            day = theme_colors(config, config["day_theme"])
            dusk = {k: mix(v, "#000000", DUSK).name() for k, v in day.items()}
            colors = blend(dusk, day, (share - 0.5) * 2)
    try:
        amount = max(-100, min(100, int(config.get("warmth", 0) or 0))) / 100
    except (TypeError, ValueError):
        amount = 0
    return warm(colors, amount)


def set_palette(colors):
    """Ставит цвета в настройки модуля и пересчитывает производные."""
    g = globals()
    g.update({k: v for k, v in colors.items() if k in COLOR_KEYS})
    g["HINT"] = rgba(g["TEXT"], 38)
    g["SCROLL"] = rgba(g["TEXT"], 30)
    g["CARD_COLORS"] = [("none", g["BORDER"]), ("purple", "#8b5cf6"), ("amber", g["DIALOGUE"]),
                        ("green", g["TEXT"]), ("coral", g["MARKER"])]


def palette():
    g = globals()
    return {k: g[k] for k in COLOR_KEYS}


def is_light():
    return QColor(BG).lightness() > 128


def vivid(color, minimum=3.0):
    """vivid_on для нынешней темы: для цифр и всего, что должно быть заметно на фоне."""
    return vivid_on(color, BG, IMPORTANT, minimum)


RAINBOW_HUES = (0.0, 0.08, 0.15, 0.33, 0.5, 0.62, 0.78)   # красный, оранжевый, жёлтый, зелёный, голубой, синий, фиолетовый


def rainbow():
    """Цвета радуги, подобранные под фон: на тёмном - светлые и сочные, на светлом - темнее."""
    light = is_light()
    out = []
    for hue in RAINBOW_HUES:
        color = QColor.fromHsvF(hue, 0.95 if light else 0.72, 0.9 if light else 0.98)
        for _ in range(8):                       # жёлтый на кремовом почти не виден - чуть темнее
            if contrast(color, BG) >= (1.9 if light else 3.0):
                break
            color = toward_contrast(color, 0.1)
        out.append(color)
    return out


def toward_contrast(color, amount):
    """Сдвигает цвет от фона: на тёмном - к белому, на светлом - к чёрному."""
    return mix(color, "#000000" if is_light() else "#ffffff", amount)


class palette_override:
    """На время блока подставляет другие цвета (для предпросмотра в настройках)."""

    def __init__(self, colors):
        self.colors = colors

    def __enter__(self):
        g = globals()
        self.saved = {k: g[k] for k in COLOR_KEYS + ["HINT", "SCROLL", "CARD_COLORS"]}
        set_palette(self.colors)

    def __exit__(self, *exc):
        globals().update(self.saved)


def apply_config(config):
    g = globals()
    from . import seasons
    g["SEASON"] = seasons.active(config)
    set_palette(current_palette(config))
    if config.get("FONT_FAMILY"):
        g["FONT_FAMILY"] = config["FONT_FAMILY"]
    if config.get("FONT_WEIGHT") in WEIGHTS:
        g["FONT_WEIGHT"] = WEIGHTS[config["FONT_WEIGHT"]]
    for key in ("FONT_SIZE", "COLUMN_WIDTH", "LINE_HEIGHT", "NIGHT_FROM", "NIGHT_TO"):
        if isinstance(config.get(key), int):
            g[key] = config[key]
    for key in ("ONLY_RUSSIAN", "AUTOSAVE", "FLAT_WINDOWS"):
        if isinstance(config.get(key), bool):
            g[key] = config[key]
    if config.get("BACKUP_DIR") and not backup_dir_problem(config["BACKUP_DIR"]):
        g["BACKUP_DIR"] = Path(config["BACKUP_DIR"]).expanduser()


def backup_dir_problem(text):
    """Почему папка для резервных копий не годится, или None. Пустое поле - копии на старом месте."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        folder = Path(text).expanduser()
    except (RuntimeError, ValueError):
        return "Не похоже на путь к папке."
    if not folder.is_absolute():
        return ("Нужен полный путь, например /home/имя/Копии. Иначе копии легли бы неизвестно куда - "
                "туда, откуда запущена программа.")
    if folder.exists() and not folder.is_dir():
        return "Это файл, а не папка."
    root = ROOT.resolve()
    target = folder.resolve()
    if target == root or root in target.parents:
        return ("Копии внутри папки с текстами копировали бы сами себя, и каждая следующая была бы "
                "больше прежней. Выбери папку снаружи.")
    return None


def save_config(config):
    QSettings(APP_ID, APP_ID).setValue("config", json.dumps(config, ensure_ascii=False))


ORDER_FILE = ".order"
STATS_FILE = ".stats.json"
GOALS_FILE = ".goals.json"
PLAN_FILE = ".plan.json"         # план книги: глава -> статус и о чём она
MARKS_FILE = ".days.json"
CRUTCHES_FILE = ".crutches.json"
DEADLINES_FILE = ".deadlines.json"  # дедлайны книг: категория -> слов к дате   # мои штампы: слова-костыли автора          # дни, отмеченные «писал» вручную
STREAK_WORDS = 250                 # с какого числа слов день засчитывается сам (примерно страница книги)
NAMES_FILE = ".names.json"
LOCK_FILE = ".lock.json"
# всё служебное - в одной скрытой папке внутри StungKir, чтобы рядом с категориями не лежала куча файлов.
# Имена слева - как было раньше (прямо в StungKir); так они и записываются в точки возврата
SERVICE_DIR = ".stungkir"
LEGACY_NAMES = {".stats.json": "stats.json", ".goals.json": "goals.json", ".days.json": "days.json",
                ".crutches.json": "crutches.json", ".plan.json": "plan.json", ".deadlines.json": "deadlines.json",
                ".names.json": "names.json", ".lock.json": "lock.json", ".lore.json": "lore.json",
                ".dictionary.txt": "dictionary.txt", ".sample.json": "sample.json", ".versions": "versions",
                ".notes": "notes", ".trash": "trash", ".templates": "templates", ".covers": "covers"}


def service_path(legacy):
    """Где теперь лежит служебный файл или папка: service_path(".versions") -> StungKir/.stungkir/versions."""
    return ROOT / SERVICE_DIR / LEGACY_NAMES[legacy]


VERSION_STAMP = "%Y-%m-%d_%H-%M-%S_%f"   # с микросекундами, чтобы порядок был точным
MAGIC = b"STUNGKIR-ENC1\n"               # с этого начинается зашифрованный файл
CHECK_PHRASE = b"stungkir-ok"


def mix(color, other, amount):
    a, b = QColor(color), QColor(other)
    return QColor(
        round(a.red() + (b.red() - a.red()) * amount),
        round(a.green() + (b.green() - a.green()) * amount),
        round(a.blue() + (b.blue() - a.blue()) * amount),
    )


ERROR_LOG = DATA_DIR / "errors.log"


# ---------------- справочник мира ----------------
LORE_FILE = ".lore.json"


CARD_COLORS = [("none", BORDER), ("purple", "#8b5cf6"), ("amber", DIALOGUE),
               ("green", TEXT), ("coral", MARKER)]


# темы дополняются производными цветами, когда все помощники уже определены
for _name, _colors in THEMES.items():
    _colors.setdefault("IMPORTANT", IMPORTANT_COLORS.get(_name, IMPORTANT))
    _colors.setdefault("MINOR", _colors["DIM"])
    for _key, _value in OBJECT_COLORS.items():
        _colors.setdefault(_key, _value)
    for _key, _value in bar_defaults(_colors).items():
        _colors.setdefault(_key, _value)


def toy_colors():
    """Цвета игрушек и стола для бросков под текущую тему: «тело» (сукно, пульт, спиннер)
    и «огонёк» (лампочки, клавиши, ободки). Тёмные темы - тёплый цвет реплик, светлые - важный."""
    dark = QColor(BG).lightness() < 128
    return {"body": QColor(ACCENT), "glow": QColor(DIALOGUE if dark else IMPORTANT), "dark": dark,
            "bg": QColor(BG)}
