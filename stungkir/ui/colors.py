# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Окно «Цвета и темы»: все цвета подсветки, живой образец, контраст, теплота,
свои темы и дневная тема по расписанию с плавным переходом в ночную."""

from PySide6.QtCore import QSettings, QSize, QTime, Qt, QTimer
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QColorDialog, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QPushButton, QScrollArea, QSlider, QSpinBox, QTextEdit, QTimeEdit,
    QVBoxLayout, QWidget,
)

from ..core import config as C
from .dialogs import Sheet, ask_text, show_warning
from ..fun.dice import Die3D
from ..text.editor import ProseHighlighter
from ..world.lore import Lore, LoreTerm
from .style import build_style
from .widgets import ClockFace, FoxWheel, GoalStrip
from ..core.i18n import tr

SAMPLE = ("Утро было серым. Туман стелился над рекой, и туман пах тиной.\n"
          "— Лодки не будет, - сказала Тервена.\n"
          "В Давне звонили колокола [проверить сезон], и *никто* не ждал **гостей** с юга.\n"
          "Здесь ашибка, а тут выделенное слово.")
SLOTS = {"night": "Ночная (основная)", "day": "Дневная"}


class _SampleSpeller:
    available = True

    def ok(self, word):
        return word.lower() != "ашибка"


class _InPreview:
    """Рисуется цветами образца, а не цветами окна."""

    colors = None

    def paintEvent(self, event):
        if self.colors is None:
            return super().paintEvent(event)
        with C.palette_override(self.colors):
            return super().paintEvent(event)


class PreviewClock(_InPreview, ClockFace):
    pass


class PreviewDie(_InPreview, Die3D):
    def mousePressEvent(self, _event):
        import random
        self.roll(20, random.randint(1, 20))       # щёлкни - кубик бросится


class PreviewFox(_InPreview, FoxWheel):
    pass


class PreviewStrip(_InPreview, GoalStrip):
    """Полоски цели в цветах образца: день выполнен, глава на середине, книга в начале."""

    def __init__(self):
        super().__init__()
        for name, value, done in (("day", 1.0, True), ("chapter", 0.55, False), ("book", 0.2, False)):
            self.items[name].update(value=value, done=done, shown=True)


class ColorPreview(QFrame):
    """Образец: кусок панели и абзацы со всеми видами подсветки в выбранных цветах."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.panel = QFrame()
        self.panel.setObjectName("Panel")
        row = QHBoxLayout(self.panel)
        row.setContentsMargins(10, 8, 10, 8)
        self.button = QPushButton(tr("Кнопка"))
        self.important = QPushButton(tr("Важное"))
        self.important.setObjectName("Primary")
        self.checked = QPushButton(tr("Включено"))
        self.checked.setCheckable(True)
        self.checked.setChecked(True)
        self.listing = QListWidget()
        self.listing.addItems(["Глава 1", "Глава 2"])
        for i in range(self.listing.count()):        # строки не наезжают друг на друга
            self.listing.item(i).setSizeHint(QSize(0, 32))
        self.listing.item(1).setSelected(True)     # без прокрутки списка
        self.listing.setFixedSize(130, 76)
        row.addWidget(self.button)
        row.addWidget(self.important)
        row.addWidget(self.checked)
        row.addWidget(self.listing, 1)
        self.panel.setFixedHeight(96)            # образец панели не сжимается, когда окно невысокое
        layout.addWidget(self.panel)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText(SAMPLE)
        self.text.document().setDocumentMargin(16)
        self.text.setMinimumHeight(190)
        layout.addWidget(self.text, 1)
        self.highlighter = ProseHighlighter(self.text.document(), _SampleSpeller())
        lore = Lore(None)
        lore.build([LoreTerm("Тервена"), LoreTerm("Давнь")])
        self.highlighter.lore = lore
        objects = QHBoxLayout()
        objects.setSpacing(8)
        self.clock = PreviewClock()
        from datetime import datetime
        self.clock.set_time(datetime(2026, 1, 1, 10, 9))
        self.die = PreviewDie(116)
        self.die.setMinimumWidth(120)
        self.die.setCursor(Qt.PointingHandCursor)
        self.die.setToolTip(tr("Щёлкни - кубик бросится"))
        self.fox = PreviewFox()
        self.fox.set_running(True)
        objects.addWidget(self.clock)
        objects.addWidget(self.die, 1)
        objects.addWidget(self.fox, 2)
        layout.addLayout(objects)
        self.strip = PreviewStrip()
        layout.addWidget(self.strip)
        self.contrast = QLabel("")
        self.contrast.setWordWrap(True)
        layout.addWidget(self.contrast)

    def show_colors(self, colors, font):
        self.strip.set_style(QSettings(C.APP_ID, C.APP_ID).value("goal_style", "bright"))
        for widget in (self.clock, self.die, self.fox, self.strip):
            widget.colors = dict(colors)
            widget.update()
        with C.palette_override(colors):
            self.setStyleSheet(build_style())
            self.text.setFont(font)
            self.highlighter.refresh_colors()
            self.highlighter.rehighlight()
            doc = self.text.document()
            found = QTextCursor(doc)
            found = doc.find("колокола", found)
            mark = QTextEdit.ExtraSelection()
            mark.cursor = found
            mark.format = QTextCharFormat()
            mark.format.setBackground(QColor(C.FOUND))
            self.text.setExtraSelections([mark])
            chosen = doc.find("выделенное")
            self.text.setTextCursor(chosen)
        ratio = C.contrast(colors["BG"], colors["TEXT"])
        dialogue = C.contrast(colors["BG"], colors["DIALOGUE"])
        def number(x):
            return f"{x:.1f}".replace(".", ",")
        self.contrast.setText(tr("Контраст текста {n}:1 - {n2}.\nРеплики {n3}:1. Для долгого чтения удобно "
                                 "примерно 7–12.").format(n=number(ratio), n2=C.contrast_hint(ratio), n3=number(dialogue)))


class ColorRow:
    """Строка одного цвета: квадратик (палитра по клику), код и ползунок «темнее - светлее»."""

    def __init__(self, dialog, key, grid, row):
        self.dialog, self.key = dialog, key
        grid.addWidget(QLabel(C.COLOR_NAMES[key]), row, 0)
        self.swatch = QPushButton("")
        self.swatch.setFixedSize(38, 24)
        self.swatch.setCursor(Qt.PointingHandCursor)
        self.swatch.setToolTip(tr("Выбрать цвет в палитре"))
        self.swatch.clicked.connect(self._pick)
        self.code = QLineEdit()
        self.code.setFixedWidth(104)
        self.code.setMaxLength(7)
        self.code.editingFinished.connect(self._typed)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 255)
        self.slider.setToolTip(tr("Темнее - светлее"))
        self.slider.valueChanged.connect(self._moved)
        grid.addWidget(self.swatch, row, 1)
        grid.addWidget(self.code, row, 2)
        grid.addWidget(self.slider, row, 3)

    def show(self, color):
        c = QColor(color)
        self.swatch.setStyleSheet(f"background: {c.name()}; border: 1px solid {C.BORDER}; border-radius: 6px;")
        self.code.setText(c.name())
        self.slider.blockSignals(True)
        self.slider.setValue(c.lightness())
        self.slider.blockSignals(False)

    def _pick(self):
        color = QColorDialog.getColor(QColor(self.code.text()), self.dialog, C.COLOR_NAMES[self.key],
                                      QColorDialog.DontUseNativeDialog)
        if color.isValid():
            self.dialog.set_color(self.key, color.name())

    def _typed(self):
        text = self.code.text().strip()
        if not text.startswith("#"):
            text = "#" + text
        if QColor.isValidColorName(text) and len(text) == 7:
            self.dialog.set_color(self.key, QColor(text).name())
        else:
            self.code.setText(self.dialog.colors()[self.key])

    def _moved(self, lightness):
        c = QColor(self.dialog.colors()[self.key])
        h, s, _l, _a = c.getHsl()
        self.dialog.set_color(self.key, QColor.fromHsl(max(0, h), s, lightness).name(), keep_slider=True)


class ColorsDialog(Sheet):
    """Цвета и темы. Ничего не меняется в окне, пока не нажата «Сохранить»."""

    def __init__(self, parent, config, font):
        super().__init__(parent, tr("Цвета и темы"))
        self.setMinimumSize(1120, 760)
        self.config = dict(config)
        self.font = font
        self.slot = "night"
        self.names = {"night": C.theme_name(self.config.get("theme")) or C.DEFAULT_THEME,
                      "day": C.theme_name(self.config.get("day_theme")) or C.DAY_THEME}
        self.edits = {"night": {}, "day": {}}
        # «свои цвета» из старых настроек становятся правками основной темы
        for key in ("TEXT", "BG", "DIALOGUE", "PUNCT"):
            if self.config.get(key) and QColor(self.config[key]).isValid():
                self.edits["night"][key] = QColor(self.config[key]).name()
        self.preview_timer = QTimer(self, singleShot=True, interval=60)
        self.preview_timer.timeout.connect(self._update_preview)

        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(8)

        slots = QHBoxLayout()
        slots.addWidget(QLabel(tr("Настраиваю:")))
        self.slot_group = QButtonGroup(self)
        self.slot_buttons = {}
        for key, label in SLOTS.items():
            button = QPushButton(label)
            button.setCheckable(True)
            button.setStyleSheet(f"QPushButton:checked {{ background: {C.IMPORTANT}; "
                                 f"color: {C.on_color(C.IMPORTANT)}; }}")
            button.setChecked(key == "night")
            button.clicked.connect(lambda _c=False, k=key: self._switch_slot(k))
            self.slot_group.addButton(button)
            self.slot_buttons[key] = button
            slots.addWidget(button)
        slots.addStretch()
        left.addLayout(slots)

        themes = QHBoxLayout()
        self.theme = QComboBox()
        self.theme.setMinimumWidth(210)
        self.theme.currentTextChanged.connect(self._theme_chosen)
        themes.addWidget(self.theme, 2)
        save_as = QPushButton(tr("Как свою…"))
        save_as.setToolTip(tr("Сохранить эти цвета как свою тему с именем"))
        save_as.clicked.connect(self._save_as)
        self.delete = QPushButton(tr("Удалить"))
        self.delete.clicked.connect(self._delete_theme)
        reset = QPushButton(tr("Сбросить"))
        reset.setToolTip(tr("Вернуть цвета выбранной темы, убрать мои правки"))
        reset.clicked.connect(self._reset)
        for button in (save_as, self.delete, reset):
            themes.addWidget(button)
        left.addLayout(themes)

        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 8, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(5)
        grid.setColumnStretch(3, 1)
        self.rows = {}
        line = 0
        for title, keys in C.COLOR_GROUPS:
            section = QLabel(title)
            section.setObjectName("Section")
            grid.addWidget(section, line, 0, 1, 4)
            line += 1
            for key in keys:
                self.rows[key] = ColorRow(self, key, grid, line)
                line += 1
        scroll = QScrollArea()
        scroll.setWidget(holder)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        left.addWidget(scroll, 1)

        warm_row = QHBoxLayout()
        warm_row.addWidget(QLabel(tr("Холоднее")))
        self.warmth = QSlider(Qt.Horizontal)
        self.warmth.setRange(-100, 100)
        self.warmth.setValue(int(self.config.get("warmth", 0) or 0))
        self.warmth.setToolTip(tr("Сдвигает все цвета обеих тем разом"))
        self.warmth.valueChanged.connect(lambda _v: self.preview_timer.start())
        warm_row.addWidget(self.warmth, 1)
        warm_row.addWidget(QLabel(tr("Теплее")))
        left.addLayout(warm_row)

        schedule = QGridLayout()
        schedule.setHorizontalSpacing(8)
        self.use_day = QCheckBox(tr("Днём включать дневную тему"))
        self.use_day.setChecked(bool(self.config.get("day_theme")))
        schedule.addWidget(self.use_day, 0, 0, 1, 6)
        self.day_from = QTimeEdit(self._time(self.config.get("day_from"), 8 * 60))
        self.day_to = QTimeEdit(self._time(self.config.get("day_to"), 20 * 60))
        for edit in (self.day_from, self.day_to):
            edit.setDisplayFormat("HH:mm")
        self.transition = QSpinBox()
        self.transition.setRange(0, 120)
        self.transition.setSingleStep(5)
        self.transition.setSuffix(tr(" мин"))
        self.transition.setValue(int(self.config.get("transition", 40) or 0))
        for col, widget in enumerate((QLabel(tr("с")), self.day_from, QLabel(tr("до")), self.day_to,
                                      QLabel(tr("переход")), self.transition)):
            schedule.addWidget(widget, 1, col)
        hint = QLabel(tr("Перед сменой дневная тема плавно темнеет, а потом за пару секунд перетекает в ночную. "
                      "Утром наоборот. Прочитать текст можно в любой момент перехода."))
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        schedule.addWidget(hint, 2, 0, 1, 6)
        left.addLayout(schedule)

        right = QVBoxLayout()
        title = QLabel(tr("Как будет выглядеть"))
        title.setObjectName("Section")
        right.addWidget(title)
        self.preview = ColorPreview()
        right.addWidget(self.preview, 1)

        body.addLayout(left, 5)
        body.addLayout(right, 4)
        self.content.addLayout(body, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(tr("Отмена"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("Сохранить"))
        ok.setObjectName("Primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        self.content.addLayout(buttons)
        self._fill_themes()
        self._show_rows()

    # ---- данные ----
    @staticmethod
    def _time(value, default):
        minutes = value if isinstance(value, int) and 0 <= value < 1440 else default
        return QTime(minutes // 60, minutes % 60)

    def colors(self, slot=None):
        slot = slot or self.slot
        colors = C.theme_colors(self.config, self.names[slot])
        colors.update(self.edits[slot])
        return colors

    def set_color(self, key, color, keep_slider=False):
        self.edits[self.slot][key] = color
        row = self.rows[key]
        if keep_slider:
            c = QColor(color)
            row.swatch.setStyleSheet(f"background: {c.name()}; border: 1px solid {C.BORDER}; border-radius: 6px;")
            row.code.setText(c.name())
        else:
            row.show(color)
        self.preview_timer.start()

    def _fill_themes(self):
        self.theme.blockSignals(True)
        self.theme.clear()
        self.theme.addItems(list(C.all_themes(self.config)))
        self.theme.setCurrentText(self.names[self.slot])
        self.theme.blockSignals(False)
        self.delete.setEnabled(self.names[self.slot] in (self.config.get("custom_themes") or {}))

    def _show_rows(self):
        colors = self.colors()
        for key, row in self.rows.items():
            row.show(colors[key])
        self._update_preview()

    def _update_preview(self):
        colors = C.warm(self.colors(), self.warmth.value() / 100)
        self.preview.show_colors(colors, self.font)

    # ---- действия ----
    def _switch_slot(self, slot):
        self.slot = slot
        self.slot_buttons[slot].setChecked(True)
        self._fill_themes()
        self._show_rows()

    def _theme_chosen(self, name):
        if not name:
            return
        self.names[self.slot] = name
        self.edits[self.slot] = {}
        self.delete.setEnabled(name in (self.config.get("custom_themes") or {}))
        self._show_rows()

    def _reset(self):
        self.edits[self.slot] = {}
        self._show_rows()

    def _save_as(self):
        name, ok = ask_text(self, tr("Своя тема"), tr("Как назвать тему?"), text=f"{self.names[self.slot]} (своя)")
        name = name.strip()
        if not ok or not name:
            return
        if name in C.THEMES:
            show_warning(self, tr("Своя тема"), tr("Так называется встроенная тема, выбери другое имя."))
            return
        self._store(name, self.colors())
        self.names[self.slot] = name
        self.edits[self.slot] = {}
        self._fill_themes()

    def _delete_theme(self):
        name = self.names[self.slot]
        custom = self.config.get("custom_themes") or {}
        if name in custom:
            del custom[name]
            for slot in SLOTS:
                if self.names[slot] == name:
                    self.names[slot] = C.DAY_THEME if slot == "day" else C.DEFAULT_THEME
                    self.edits[slot] = {}
            self._fill_themes()
            self._show_rows()

    def _store(self, name, colors):
        custom = dict(self.config.get("custom_themes") or {})
        custom[name] = {k: colors[k] for k in C.COLOR_KEYS}
        self.config["custom_themes"] = custom

    def values(self):
        """Новые настройки: правки встроенной темы сохраняются как своя тема «… (своя)»."""
        config = dict(self.config)
        for key in ("TEXT", "BG", "DIALOGUE", "PUNCT"):
            config.pop(key, None)
        for slot in SLOTS:
            if self.edits[slot]:
                name = self.names[slot]
                if name in C.THEMES:
                    name = f"{name} (своя)"
                colors = self.colors(slot)
                custom = dict(config.get("custom_themes") or {})
                custom[name] = {k: colors[k] for k in C.COLOR_KEYS}
                config["custom_themes"] = custom
                self.names[slot] = name
        config["theme"] = self.names["night"]
        config["day_theme"] = self.names["day"] if self.use_day.isChecked() else ""
        config["day_from"] = self.day_from.time().hour() * 60 + self.day_from.time().minute()
        config["day_to"] = self.day_to.time().hour() * 60 + self.day_to.time().minute()
        config["transition"] = self.transition.value()
        config["warmth"] = self.warmth.value()
        return config
