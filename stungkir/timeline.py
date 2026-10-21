# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Хронология мира: лента событий в своём летоисчислении. «Когда» пишется свободно,
а для порядка у события есть число - год (может быть и отрицательным)."""

import json
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QStyle, QStyledItemDelegate, QVBoxLayout, QWidget,
)

from . import config as C
from .dialogs import Sheet
from .style import frameless_menu, rounded_menu
from .widgets import RussianLineEdit, RussianTextEdit


def year_label(year):
    return f"{year:g}".replace(".", ",")


def sort_events(events):
    """По году; при одинаковом - в том порядке, в каком добавлены."""
    return sorted(events, key=lambda e: float(e.get("year", 0)))


def timeline_text(events):
    """Хронология обычным текстом: для поиска, счёта слов и «Копировать всё»."""
    lines = []
    for event in sort_events(events):
        when = event.get("when") or year_label(float(event.get("year", 0)))
        lines.append(f"{when} - {event.get('title', '')}".strip(" -"))
        if event.get("text"):
            lines.append(event["text"])
    return "\n".join(lines)


def load_events(text):
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError:
        return []
    events = data.get("events", []) if isinstance(data, dict) else []
    return [e for e in events if isinstance(e, dict)]


class EventDialog(Sheet):
    """Событие: когда, год для порядка, название, описание, цвет, связанная глава."""

    def __init__(self, parent, event, chapters, on_foreign, existing):
        super().__init__(parent, "Событие")
        self.setMinimumSize(520, 460)
        self.deleted = False
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.addWidget(QLabel("Когда:"), 0, 0)
        self.when = RussianLineEdit(on_foreign)
        self.when.setPlaceholderText("как в твоём мире: «312 г. Второй эры, весна»")
        self.when.setText(event.get("when", ""))
        grid.addWidget(self.when, 0, 1)
        grid.addWidget(QLabel("Год (для порядка):"), 1, 0)
        self.year = QDoubleSpinBox()
        self.year.setRange(-1_000_000, 1_000_000)
        self.year.setDecimals(2)
        self.year.setValue(float(event.get("year", 0)))
        self.year.setToolTip("По этому числу события встают по порядку. Дробное - если в одном году несколько")
        grid.addWidget(self.year, 1, 1)
        self.content.addLayout(grid)
        self.title = RussianLineEdit(on_foreign)
        self.title.setPlaceholderText("Что случилось")
        self.title.setText(event.get("title", ""))
        self.content.addWidget(self.title)
        self.text = RussianTextEdit(on_foreign)
        self.text.setPlaceholderText("Подробности…")
        self.text.setPlainText(event.get("text", ""))
        self.content.addWidget(self.text, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel("Цвет:"))
        self.swatches = []
        for name, color in C.CARD_COLORS:
            swatch = QPushButton("")
            swatch.setObjectName("Swatch")
            swatch.setCheckable(True)
            swatch.setAutoExclusive(True)
            swatch.setStyleSheet(f"background: {color};")
            swatch.setChecked(event.get("color", "none") == name)
            swatch.setProperty("color_name", name)
            row.addWidget(swatch)
            self.swatches.append(swatch)
        row.addStretch()
        self.content.addLayout(row)
        self.chapter = QComboBox()
        self.chapter.addItem("Без главы", "")
        for key in chapters:
            self.chapter.addItem(key.replace("/", " · ").removesuffix(".txt"), key)
        self.chapter.setCurrentIndex(max(0, self.chapter.findData(event.get("chapter", ""))))
        self.content.addWidget(self.chapter)
        buttons = QHBoxLayout()
        if existing:
            delete = QPushButton("Удалить событие")
            delete.clicked.connect(self._delete)
            buttons.addWidget(delete)
        buttons.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Готово")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        self.content.addLayout(buttons)
        self.when.setFocus()

    def _delete(self):
        self.deleted = True
        self.accept()

    def event_data(self):
        color = next((s.property("color_name") for s in self.swatches if s.isChecked()), "none")
        return {"when": self.when.text().strip(), "year": self.year.value(), "title": self.title.text().strip(),
                "text": self.text.toPlainText().strip(), "color": color, "chapter": self.chapter.currentData() or ""}


class EventDelegate(QStyledItemDelegate):
    """Слева год, посередине линия с точкой цвета события, справа карточка."""

    YEAR = 110

    def sizeHint(self, option, index):
        event = json.loads(index.data(Qt.UserRole) or "{}")
        return QSize(400, 96 if event.get("text") else 70)

    def paint(self, painter, option, index):
        event = json.loads(index.data(Qt.UserRole) or "{}")
        rect = QRectF(option.rect)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        line_x = rect.left() + self.YEAR + 14
        painter.setPen(QPen(QColor(C.BORDER), 2))
        painter.drawLine(int(line_x), int(rect.top()), int(line_x), int(rect.bottom()))
        color = QColor(dict(C.CARD_COLORS).get(event.get("color", "none"), C.BORDER))
        if event.get("color", "none") == "none":
            color = QColor(C.DIM)
        painter.setPen(QPen(QColor(C.BG), 2))
        painter.setBrush(color)
        painter.drawEllipse(QRectF(line_x - 6, rect.top() + 22, 12, 12))
        bold = QFont(C.FONT_FAMILY, 10)
        bold.setBold(True)
        painter.setFont(bold)
        painter.setPen(QColor(C.DIALOGUE))
        painter.drawText(QRectF(rect.left() + 4, rect.top() + 14, self.YEAR - 4, 28), Qt.AlignRight | Qt.AlignVCenter,
                         year_label(float(event.get("year", 0))))
        card = QRectF(line_x + 18, rect.top() + 6, rect.width() - self.YEAR - 40, rect.height() - 12)
        selected = option.state & QStyle.State_Selected
        hovered = option.state & QStyle.State_MouseOver
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(C.SELECT if selected else (C.HOVER if hovered else C.PANEL)))
        painter.drawRoundedRect(card, 10, 10)
        painter.setPen(QColor(C.TEXT))
        title = event.get("title") or "Без названия"
        when = event.get("when", "")
        painter.drawText(QRectF(card.left() + 14, card.top() + 8, card.width() - 28, 20), Qt.AlignLeft | Qt.AlignVCenter,
                         painter.fontMetrics().elidedText(title, Qt.ElideRight, int(card.width() - 28)))
        small = QFont(C.FONT_FAMILY, 9)
        painter.setFont(small)
        painter.setPen(QColor(C.DIM))
        meta = when
        if event.get("chapter"):
            meta = (meta + "   → " if meta else "→ ") + Path(event["chapter"]).stem
        painter.drawText(QRectF(card.left() + 14, card.top() + 28, card.width() - 28, 16), Qt.AlignLeft | Qt.AlignVCenter,
                         painter.fontMetrics().elidedText(meta, Qt.ElideRight, int(card.width() - 28)))
        if event.get("text"):
            painter.drawText(QRectF(card.left() + 14, card.top() + 46, card.width() - 28, card.height() - 50),
                             Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, event["text"][:200])
        painter.restore()


class TimelineView(QWidget):
    """Хронология: события по годам. Двойной клик - изменить, по пустому месту - новое."""

    def __init__(self, on_change, on_foreign, toast, chapters, open_chapter):
        super().__init__()
        self.setObjectName("Board")
        self.on_change, self.on_foreign, self.toast = on_change, on_foreign, toast
        self.chapters, self.open_chapter = chapters, open_chapter
        self.modified = False
        self._loading = False
        self._found = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 6)
        layout.setSpacing(10)
        bar = QWidget()
        bar.setObjectName("TableBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        add = QPushButton("+ событие")
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(self.new_event)
        row.addWidget(add)
        row.addSpacing(14)
        hint = QLabel("события идут по году; двойной клик - изменить, по пустому месту - новое")
        hint.setObjectName("Status")
        row.addWidget(hint)
        row.addStretch()
        layout.addWidget(bar)
        self.list = QListWidget()
        self.list.setItemDelegate(EventDelegate(self.list))
        self.list.setMouseTracking(True)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.itemDoubleClicked.connect(self.edit_event)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.menu)
        self.list.mouseDoubleClickEvent = self._double_click
        layout.addWidget(self.list, 1)

    def _double_click(self, event):
        item = self.list.itemAt(event.position().toPoint())
        if item is None:
            self.new_event()
        else:
            self.edit_event(item)

    # ---- данные ----
    def events(self):
        return [json.loads(self.list.item(i).data(Qt.UserRole) or "{}") for i in range(self.list.count())]

    def _fill(self, events, select=None):
        self._loading = True
        self.list.clear()
        for event in sort_events(events):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, json.dumps(event, ensure_ascii=False))
            self.list.addItem(item)
            if select is not None and event is select:
                self.list.setCurrentItem(item)
        self._loading = False

    def load(self, text):
        self._fill(load_events(text))
        self.set_modified(False)

    def text(self):
        return json.dumps({"events": self.events()}, ensure_ascii=False, indent=1) + "\n"

    def words_text(self):
        return timeline_text(self.events())

    def copy_text(self):
        return timeline_text(self.events()) + "\n", "Хронология скопирована текстом"

    def set_modified(self, value):
        self.modified = value
        self.on_change()

    def changed(self):
        if not self._loading:
            self.set_modified(True)

    def focus_widget(self):
        return self.list

    def kind(self):
        return "Хронология"

    # ---- события ----
    def new_event(self):
        current = self.list.currentItem()
        start = {}
        if current is not None:                    # новое - сразу после выбранного по году
            start = {"year": json.loads(current.data(Qt.UserRole) or "{}").get("year", 0)}
        dialog = EventDialog(self, start, self.chapters(), self.on_foreign, existing=False)
        if dialog.exec():
            event = dialog.event_data()
            if event["title"] or event["text"] or event["when"]:
                self._fill(self.events() + [event], select=event)
                self.changed()

    def edit_event(self, item):
        old = json.loads(item.data(Qt.UserRole) or "{}")
        dialog = EventDialog(self, old, self.chapters(), self.on_foreign, existing=True)
        if not dialog.exec():
            return
        events = self.events()
        index = self.list.row(item)
        if dialog.deleted:
            events.pop(index)
            self._fill(events)
        else:
            event = dialog.event_data()
            events[index] = event
            self._fill(events, select=event)
        self.changed()

    def set_color(self, item, color):
        events = self.events()
        events[self.list.row(item)]["color"] = color
        self._fill(events)
        self.changed()

    def menu(self, pos):
        item = self.list.itemAt(pos)
        menu = rounded_menu(self)
        if item is None:
            menu.addAction("Новое событие", self.new_event)
        else:
            event = json.loads(item.data(Qt.UserRole) or "{}")
            menu.addAction("Изменить", lambda: self.edit_event(item))
            if event.get("chapter"):
                menu.addAction("Открыть главу", lambda: self.open_chapter(event["chapter"]))
            colors = frameless_menu(menu.addMenu("Цвет"))
            names = {"none": "Без цвета", "purple": "Фиолетовый", "amber": "Янтарный",
                     "green": "Зелёный", "coral": "Коралловый"}
            for name, _ in C.CARD_COLORS:
                colors.addAction(names[name], lambda n=name: self.set_color(item, n))
            menu.addSeparator()
            menu.addAction("Новое событие", self.new_event)
            menu.addAction("Удалить", lambda: (self._fill([e for i, e in enumerate(self.events())
                                                            if i != self.list.row(item)]), self.changed()))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    # ---- поиск и знаки ----
    def _matches(self, query):
        query = query.lower()
        return [i for i, e in enumerate(self.events())
                if query in " ".join(str(e.get(k, "")) for k in ("when", "title", "text")).lower()]

    def reset_find(self):
        self._found = None

    def find(self, query, backward=False):
        rows = self._matches(query) if query else []
        if not rows:
            return 0, 0
        current = self._found if self._found is not None else (-1 if not backward else 10 ** 9)
        if backward:
            earlier = [r for r in rows if r < current]
            target = earlier[-1] if earlier else rows[-1]
        else:
            later = [r for r in rows if r > current]
            target = later[0] if later else rows[0]
        self._found = target
        self.list.setCurrentRow(target)
        return rows.index(target) + 1, len(rows)

    def count(self, query):
        rows = self._matches(query)
        return (rows.index(self._found) + 1 if self._found in rows else 0), len(rows)

    def insert(self, value):
        self.toast("Знаки ставятся в событие: открой его двойным кликом")
