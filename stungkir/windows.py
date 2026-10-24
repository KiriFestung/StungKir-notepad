# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Большие окна: статистика, сборка книги, настройки, версии главы."""

import json
from datetime import date, timedelta
from pathlib import Path
from PySide6.QtCore import QRectF, QSettings, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFontComboBox, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSpinBox, QStackedWidget, QTextEdit, QToolTip, QVBoxLayout, QWidget,
)

from . import config as C
from .textutil import WORD_RE, diff_html, is_prose, words_label
from .storage import LockedFile, files_in, read_text, version_label
from .dialogs import Sheet, show_warning
from .export import FB2_GENRES, LAYOUT, PAGE_SIZES, TEMPLATES


class StatsChart(QWidget):
    """Столбики: сколько слов написано по дням."""

    def __init__(self, days, goal):
        super().__init__()
        self.days = days
        self.goal = goal
        self.setMinimumHeight(240)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        left, right, top, bottom = 10, 10, 26, 26
        width = self.width() - left - right
        height = self.height() - top - bottom
        values = [max(0, v) for _, v in self.days]
        top_value = max(values + [self.goal, 1])
        step = width / len(values)
        small = QFont(C.FONT_FAMILY, 9)
        small.setBold(True)
        painter.setFont(small)

        if self.goal:
            y = top + height - height * self.goal / top_value
            pen = QPen(QColor(C.DIALOGUE))
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(left, int(y), left + width, int(y))
            painter.drawText(left, int(y) - 6, f"цель {self.goal}")

        painter.setPen(Qt.NoPen)
        for i, ((_day, _), value) in enumerate(zip(self.days, values)):
            bar_height = height * value / top_value
            x = left + i * step + step * 0.18
            reached = self.goal and value >= self.goal
            is_today = i == len(values) - 1
            color = QColor(C.TEXT if reached else C.ACCENT)
            if is_today and not reached:
                color = QColor(C.mix(C.ACCENT, C.TEXT, 0.4))
            painter.setBrush(color)
            if bar_height > 0:
                painter.drawRoundedRect(QRectF(x, top + height - bar_height, step * 0.64,
                                               max(bar_height, 3)), 3, 3)
        painter.setPen(QColor(C.DIM))
        metrics = painter.fontMetrics()
        for i, (day, _) in enumerate(self.days):
            if i % 5 == 0 or i == len(self.days) - 1:
                label = day.strftime("%d.%m")
                x = min(int(left + i * step), self.width() - right - metrics.horizontalAdvance(label))
                painter.drawText(x, self.height() - 6, label)
        painter.drawText(left, 14, f"макс. {max(values)}")


def year_summary(stats, marks, today):
    """За последний год: (слов, дней с текстом, лучший месяц «Октябрь 2026», слов в нём)."""
    from .storage import wrote_on
    start = today - timedelta(days=364)
    words, days, months = 0, 0, {}
    for n in range(365):
        day = start + timedelta(days=n)
        value = max(0, stats.get(day.isoformat(), 0))
        words += value
        days += bool(value) or wrote_on(day, stats, marks)
        months[(day.year, day.month)] = months.get((day.year, day.month), 0) + value
    (year, month), best = max(months.items(), key=lambda item: (item[1], item[0]))
    return words, days, f"{MONTHS[month - 1]} {year}", best


class YearHeatmap(QWidget):
    """Год клеточками, как на GitHub: столбец - неделя, строка - день недели; чем больше слов, тем ярче."""

    WEEKS = 53

    def __init__(self, stats, marks, goal, today):
        super().__init__()
        self.stats, self.marks, self.goal, self.today = stats, set(marks or ()), goal or C.DAILY_GOAL or 500, today
        self.start = today - timedelta(days=today.weekday()) - timedelta(weeks=self.WEEKS - 1)   # понедельник
        self.setMinimumHeight(200)
        self.setMouseTracking(True)

    def _geometry(self):
        left, top = 26, 22
        cell = max(6.0, min(16.0, (self.width() - left - 4) / self.WEEKS))
        return left, top, cell

    def _rect(self, day):
        left, top, cell = self._geometry()
        index = (day - self.start).days
        return QRectF(left + (index // 7) * cell, top + (index % 7) * cell, cell - 2, cell - 2)

    def level(self, day):
        """0 - ничего, 1 - отмечен вручную или немного, 2 - до половины цели, 3 - до цели, 4 - цель, 5 - две цели."""
        words = max(0, self.stats.get(day.isoformat(), 0))
        if words >= self.goal * 2:
            return 5
        if words >= self.goal:
            return 4
        if words >= self.goal / 2:
            return 3
        if words > 0:
            return 2
        return 1 if day.isoformat() in self.marks else 0

    def day_at(self, point):
        left, top, cell = self._geometry()
        column, row = int((point.x() - left) // cell), int((point.y() - top) // cell)
        if not (0 <= column < self.WEEKS and 0 <= row < 7):
            return None
        day = self.start + timedelta(days=column * 7 + row)
        return day if day <= self.today else None

    def mouseMoveEvent(self, event):
        day = self.day_at(event.position())
        if day is None:
            QToolTip.hideText()
            return
        words = max(0, self.stats.get(day.isoformat(), 0))
        text = f"{day.day} {MONTHS_OF[day.month - 1]} {day.year}: " + (
            words_label(words) if words else ("писал (отмечено)" if day.isoformat() in self.marks else "ничего"))
        QToolTip.showText(event.globalPosition().toPoint(), text, self)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        left, top, cell = self._geometry()
        shades = [C.mix(C.TEXT, C.BG, 0.93), C.mix(C.TEXT, C.BG, 0.8), C.mix(C.TEXT, C.BG, 0.68),
                  C.mix(C.TEXT, C.BG, 0.5), C.mix(C.TEXT, C.BG, 0.3), QColor(C.TEXT)]
        small = QFont(C.FONT_FAMILY, 8)
        painter.setFont(small)
        painter.setPen(QColor(C.DIM))
        for row, name in ((0, "пн"), (2, "ср"), (4, "пт")):
            painter.drawText(QRectF(0, top + row * cell - 2, left - 4, cell + 2), Qt.AlignRight | Qt.AlignVCenter, name)
        shown_month = None
        for n in range(self.WEEKS * 7):
            day = self.start + timedelta(days=n)
            if day > self.today:
                break
            if n % 7 == 0 and day.month != shown_month and day.day <= 7:     # подпись месяца над первой неделей
                shown_month = day.month
                painter.setPen(QColor(C.DIM))
                painter.drawText(QRectF(left + (n // 7) * cell, 0, cell * 4, top - 4), Qt.AlignLeft | Qt.AlignBottom,
                                 MONTHS[day.month - 1][:3].lower())
            painter.setPen(Qt.NoPen)
            painter.setBrush(shades[self.level(day)])
            painter.drawRoundedRect(self._rect(day), 2.5, 2.5)
        today = self._rect(self.today)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(C.DIALOGUE), 1.5))
        painter.drawRoundedRect(today.adjusted(-1, -1, 1, 1), 3, 3)
        # подсказка цветов
        y = top + 7 * cell + 10
        x = self.width() - 4 - 6 * (cell + 1) - 74
        painter.setPen(QColor(C.DIM))
        painter.drawText(QRectF(x - 90, y - 2, 86, cell + 4), Qt.AlignRight | Qt.AlignVCenter, "меньше")
        for i, shade in enumerate(shades):
            painter.setPen(Qt.NoPen)
            painter.setBrush(shade)
            painter.drawRoundedRect(QRectF(x + i * (cell + 1), y, cell - 2, cell - 2), 2.5, 2.5)
        painter.setPen(QColor(C.DIM))
        painter.drawText(QRectF(x + 6 * (cell + 1) + 4, y - 2, 70, cell + 4), Qt.AlignLeft | Qt.AlignVCenter, "больше")


MONTHS_OF = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
             "ноября", "декабря"]
MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь",
          "Октябрь", "Ноябрь", "Декабрь"]


class WritingCalendar(QWidget):
    """Месяц: закрашены дни, когда писал (от STREAK_WORDS слов или отмечено вручную).
    Клик по дню - отметить или снять отметку «писал»."""

    CELL = 38

    def __init__(self, stats, marks, today, on_toggle):
        super().__init__()
        self.stats, self.marks, self.today = stats, marks, today
        self.on_toggle = on_toggle
        self.month = today.replace(day=1)
        self.setFixedSize(self.CELL * 7 + 4, self.CELL * 7 + 34)
        self.setMouseTracking(True)
        self._hover = None

    def shift(self, step):
        month = self.month.month - 1 + step
        target = date(self.month.year + month // 12, month % 12 + 1, 1)
        if target <= self.today.replace(day=1):
            self.month = target
            self.update()

    def title(self):
        return f"{MONTHS[self.month.month - 1]} {self.month.year}"

    def _cells(self):
        first = self.month
        start = first - timedelta(days=first.weekday())
        return [start + timedelta(days=n) for n in range(42)]

    def _rect(self, index):
        row, column = divmod(index, 7)
        return QRectF(2 + column * self.CELL, 30 + row * self.CELL, self.CELL - 4, self.CELL - 4)

    def day_at(self, point):
        for index, day in enumerate(self._cells()):
            if self._rect(index).contains(point):
                return day if day.month == self.month.month else None
        return None

    def mouseMoveEvent(self, event):
        day = self.day_at(event.position())
        if day != self._hover:
            self._hover = day
            self.setCursor(Qt.PointingHandCursor if day and day <= self.today else Qt.ArrowCursor)
            if day:
                words = self.stats.get(day.isoformat(), 0)
                mark = " · отмечено вручную" if day.isoformat() in self.marks else ""
                self.setToolTip(f"{day:%d.%m}: {words_label(max(words, 0))}{mark}")
            self.update()

    def leaveEvent(self, _event):
        self._hover = None
        self.update()

    def mousePressEvent(self, event):
        day = self.day_at(event.position())
        if day and day <= self.today and event.button() == Qt.LeftButton:
            self.on_toggle(day)
            self.update()

    def paintEvent(self, _event):
        from .storage import wrote_on
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        small = QFont(C.FONT_FAMILY, 8)
        small.setBold(True)
        painter.setFont(small)
        painter.setPen(QColor(C.DIM))
        for column, name in enumerate(["пн", "вт", "ср", "чт", "пт", "сб", "вс"]):
            painter.drawText(QRectF(2 + column * self.CELL, 8, self.CELL - 4, 18), Qt.AlignCenter, name)
        font = QFont(C.FONT_FAMILY, 10)
        font.setBold(True)
        painter.setFont(font)
        for index, day in enumerate(self._cells()):
            if day.month != self.month.month:
                continue
            rect = self._rect(index)
            future = day > self.today
            words = self.stats.get(day.isoformat(), 0)
            marked = day.isoformat() in self.marks
            done = wrote_on(day, self.stats, self.marks)
            painter.setPen(Qt.NoPen)
            if done:
                painter.setBrush(C.mix(C.TEXT, C.BG, 0.35))
            elif words > 0:
                painter.setBrush(C.mix(C.TEXT, C.BG, 0.8))     # писал, но меньше нормы
            else:
                painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 8, 8)
            if day == self._hover and not future:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(C.DIM), 1))
                painter.drawRoundedRect(rect, 8, 8)
            if day == self.today:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(C.DIALOGUE), 2))
                painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
            painter.setPen(QColor(C.BG if done else (C.mix(C.DIM, C.BG, 0.5) if future else C.TEXT)))
            painter.drawText(rect, Qt.AlignCenter, str(day.day))
            if marked:
                painter.setPen(QPen(QColor(C.BG if done else C.TEXT), 1.6))
                x, y = rect.right() - 9, rect.top() + 7
                painter.drawLine(int(x), int(y), int(x + 2), int(y + 2))
                painter.drawLine(int(x + 2), int(y + 2), int(x + 6), int(y - 3))


class StatsDialog(Sheet):
    def __init__(self, parent, stats, goal, marks=None, on_marks=None, extra=()):
        super().__init__(parent, f"Статистика · {C.APP_NAME}")
        self.setMinimumSize(920, 580)
        today = date.today()
        self.stats = stats
        self.marks = set(marks or ())
        self.on_marks = on_marks
        days = [(today - timedelta(days=n), 0) for n in range(C.STATS_DAYS - 1, -1, -1)]
        days = [(d, stats.get(d.isoformat(), 0)) for d, _ in days]
        values = [v for _, v in days]
        written = sum(max(0, v) for v in values)
        active = [v for v in values if v > 0]
        best_day, best = max(days, key=lambda item: item[1])

        layout = self.content
        summary = QLabel(
            f"За {C.STATS_DAYS} дней: {words_label(written)}   ·   "
            f"в среднем {round(sum(active) / len(active)) if active else 0} в день письма   ·   "
            f"лучший день: {best} ({best_day:%d.%m})" + "".join("\n" + line for line in extra))
        summary.setWordWrap(True)
        layout.addWidget(summary)
        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        head = QHBoxLayout()
        back = QPushButton("‹")
        forward = QPushButton("›")
        self.month_label = QLabel("")
        self.month_label.setObjectName("Section")
        self.month_label.setAlignment(Qt.AlignCenter)
        head.addWidget(back)
        head.addWidget(self.month_label, 1)
        head.addWidget(forward)
        left.addLayout(head)
        self.calendar = WritingCalendar(stats, self.marks, today, self.toggle_day)
        back.clicked.connect(lambda: self._shift(-1))
        forward.clicked.connect(lambda: self._shift(1))
        left.addWidget(self.calendar)
        self.streak = QLabel("")
        self.streak.setObjectName("Section")
        left.addWidget(self.streak)
        hint = QLabel(f"День засчитан от {C.STREAK_WORDS} слов. Писал на телефоне или от руки - "
                      "кликни по дню, появится галочка.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        hint.setMaximumWidth(self.calendar.width())
        left.addWidget(hint)
        left.addStretch()
        body.addLayout(left)
        # справа - 30 дней столбиками или год клеточками
        right = QVBoxLayout()
        switch = QHBoxLayout()
        self.period = QButtonGroup(self)
        for index, text in enumerate(("30 дней", "Год")):
            button = QPushButton(text)
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setProperty("noIcon", True)
            button.setStyleSheet(f"QPushButton:checked {{ background: {C.IMPORTANT}; "      # как вкладки антистресса
                                 f"color: {C.on_color(C.IMPORTANT)}; }}")
            button.setChecked(index == 0)
            self.period.addButton(button, index)
            switch.addWidget(button)
        switch.addStretch()
        right.addLayout(switch)
        self.charts = QStackedWidget()
        self.charts.addWidget(StatsChart(days, goal))
        year = QWidget()
        year_layout = QVBoxLayout(year)
        year_layout.setContentsMargins(0, 8, 0, 0)
        self.heatmap = YearHeatmap(stats, self.marks, goal, today)
        self.heatmap.setFixedHeight(140)
        year_layout.addWidget(self.heatmap)
        total, active_days, best_month, best_month_words = year_summary(stats, self.marks, today)
        self.year_label = QLabel(f"За год: {words_label(total)}   ·   дней с текстом: {active_days}"
                                 + (f"   ·   лучший месяц: {best_month} ({best_month_words})" if best_month_words else ""))
        self.year_label.setObjectName("Status")
        self.year_label.setWordWrap(True)
        year_layout.addWidget(self.year_label)
        year_layout.addStretch()
        self.charts.addWidget(year)
        right.addWidget(self.charts, 1)
        self.period.idClicked.connect(self.charts.setCurrentIndex)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)
        self._shift(0)
        self._update_streak()
        row = QHBoxLayout()
        row.addStretch()
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        layout.addLayout(row)

    def _shift(self, step):
        self.calendar.shift(step)
        self.month_label.setText(self.calendar.title())

    def _update_streak(self):
        from .storage import streaks
        current, best = streaks(self.stats, self.marks, date.today())
        self.streak.setText(f"Дней подряд: {current}   ·   рекорд: {best}")

    def toggle_day(self, day):
        key = day.isoformat()
        if key in self.marks:
            self.marks.discard(key)
        else:
            self.marks.add(key)
        if self.on_marks:
            self.on_marks(set(self.marks))
        self.heatmap.marks = set(self.marks)
        self.heatmap.update()
        self._update_streak()


class CompileDialog(Sheet):
    """Собрать главы категории в одну книгу: PDF, Word, EPUB или текст, по готовому шаблону."""

    SPACINGS = [1.0, 1.15, 1.25, 1.5, 2.0]

    def __init__(self, parent, categories, current, author, skipped=()):
        super().__init__(parent, "Собрать книгу")
        self.skipped = {str(p) for p in skipped}       # «не в книгу» из плана: сначала без галочки
        self.setMinimumSize(720, 600)
        self.store = QSettings(C.APP_ID, C.APP_ID)
        layout = self.content
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        self.template = QComboBox()
        self.template.addItems(list(TEMPLATES))
        self.category = QComboBox()
        for category in categories:
            self.category.addItem(category.name, str(category))
        if current is not None:
            self.category.setCurrentIndex(max(0, self.category.findData(str(current))))
        self.category.currentIndexChanged.connect(self._fill)
        self.title = QLineEdit()
        self.title.setPlaceholderText("Название книги")
        self.author = QLineEdit(author)
        self.author.setPlaceholderText("Можно оставить пустым")
        for column, (label, widget) in enumerate((("Шаблон:", self.template), ("Из какой категории:", self.category))):
            grid.addWidget(QLabel(label), 0, column)
            grid.addWidget(widget, 1, column)
        for column, (label, widget) in enumerate((("Название книги:", self.title), ("Автор:", self.author))):
            grid.addWidget(QLabel(label), 2, column)
            grid.addWidget(widget, 3, column)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        hint = QLabel("Главы идут в том же порядке, что и в списке слева. Сними галочку, "
                      "чтобы главу не включать.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.chapters = QListWidget()
        self.chapters.setMinimumHeight(120)
        layout.addWidget(self.chapters, 1)
        self.format = QComboBox()
        self.format.addItem("PDF - чтение и печать", "pdf")
        self.format.addItem("Word (.docx) - издательство", "docx")
        self.format.addItem("EPUB - читалки, самиздат", "epub")
        self.format.addItem("FB2 - русские читалки и площадки", "fb2")
        self.format.addItem("Текст (.txt)", "txt")
        look = QHBoxLayout()
        self.page = QComboBox()
        self.page.addItems(list(PAGE_SIZES))
        self.page.setToolTip("Размер страницы (для PDF и Word)")
        self.size = QDoubleSpinBox()
        self.size.setAlignment(Qt.AlignCenter)
        self.size.setRange(8, 18)
        self.size.setSingleStep(0.5)
        self.size.setDecimals(1)
        self.size.setSuffix(" пт")
        self.size.setToolTip("Размер шрифта")
        self.spacing = QComboBox()
        for value in self.SPACINGS:
            self.spacing.addItem(f"интервал {value:g}".replace(".", ","), value)
        layout.addWidget(self.format)
        self.genre = QComboBox()
        for key, label in FB2_GENRES.items():
            self.genre.addItem(f"Жанр для FB2: {label}", key)
        saved_genre = self.store.value("fb2_genre", "prose_contemporary")
        self.genre.setCurrentIndex(max(0, self.genre.findData(saved_genre)))
        layout.addWidget(self.genre)
        self.format.currentIndexChanged.connect(lambda _i: self.genre.setVisible(self.format.currentData() == "fb2"))
        self.genre.setVisible(False)
        for widget in (self.page, self.size, self.spacing):
            look.addWidget(widget, 1)
        layout.addLayout(look)
        self.contacts = QLineEdit(self.store.value("contacts", ""))
        self.contacts.setPlaceholderText("Контакты для титула рукописи: почта, телефон")
        self.contacts_label = self.contacts    # отдельной подписи нет, подсказка внутри поля
        layout.addWidget(self.contacts)
        self.new_page = QCheckBox("Глава с новой страницы")
        self.new_page.setChecked(True)
        self.headings = QCheckBox("Заголовки глав")
        self.headings.setChecked(True)
        self.strip_markers = QCheckBox("Без пометок [ … ]")
        self.strip_markers.setChecked(True)
        boxes = QHBoxLayout()
        for box in (self.new_page, self.headings, self.strip_markers):
            boxes.addWidget(box)
        boxes.addStretch()
        layout.addLayout(boxes)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Собрать")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        layout.addLayout(row)
        self._fill()
        self.template.currentTextChanged.connect(self._apply_template)
        saved = self.store.value("compile_template", "Обычная книга")
        self.template.setCurrentText(saved if saved in TEMPLATES else "Обычная книга")
        self._apply_template(self.template.currentText())

    def _apply_template(self, name):
        template = TEMPLATES.get(name, {})
        look = {**LAYOUT, **template}
        self.format.setCurrentIndex(max(0, self.format.findData(template.get("format", "pdf"))))
        self.page.setCurrentText(look["page"])
        self.size.setValue(look["size"])
        self.spacing.setCurrentIndex(min(range(len(self.SPACINGS)),
                                         key=lambda i: abs(self.SPACINGS[i] - look["spacing"])))
        for box, key in ((self.new_page, "new_page"), (self.headings, "headings")):
            if key in template:
                box.setChecked(template[key])
        manuscript = look["title_page"] == "manuscript"
        self.contacts_label.setVisible(manuscript)
        self.contacts.setVisible(manuscript)

    def _fill(self):
        self.chapters.clear()
        data = self.category.currentData()
        if not data:
            return
        folder = Path(data)
        self.title.setText(folder.name)
        for f in files_in(folder):
            if not is_prose(f):
                continue
            item = QListWidgetItem(f.stem)
            item.setData(Qt.UserRole, str(f))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if str(f) in self.skipped:
                item.setCheckState(Qt.Unchecked)
                item.setToolTip("В плане книги отмечена «не в книгу». Поставь галочку, если всё же нужна")
            else:
                item.setCheckState(Qt.Checked)
            self.chapters.addItem(item)

    def options(self):
        chapters = [Path(self.chapters.item(i).data(Qt.UserRole)) for i in range(self.chapters.count())
                    if self.chapters.item(i).checkState() == Qt.Checked]
        template = TEMPLATES.get(self.template.currentText(), {})
        look = {k: v for k, v in template.items() if k in LAYOUT}
        look.update(page=self.page.currentText(), size=self.size.value(), spacing=self.spacing.currentData(),
                    contacts=self.contacts.text().strip())
        self.store.setValue("compile_template", self.template.currentText())
        self.store.setValue("contacts", self.contacts.text().strip())
        self.store.setValue("fb2_genre", self.genre.currentData())
        return {"title": self.title.text().strip() or "Книга", "author": self.author.text().strip(),
                "category": self.category.currentData(),
                "chapters": chapters, "format": self.format.currentData(),
                "new_page": self.new_page.isChecked(), "headings": self.headings.isChecked(),
                "strip_markers": self.strip_markers.isChecked(), "layout": look,
                "genre": self.genre.currentData()}


def load_config_raw():
    try:
        return json.loads(QSettings(C.APP_ID, C.APP_ID).value("config", "") or "{}")
    except ValueError:
        return {}


class SettingsDialog(Sheet):
    """Шрифт, колонка, цели, копии. Цвета - в отдельном окне «Цвета и темы»."""

    def __init__(self, parent, config, goal):
        super().__init__(parent, "Настройки")
        self.setMinimumWidth(640)
        self.config = dict(config)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnMinimumWidth(0, 190)
        row = 0

        def section(text):
            nonlocal row
            label = QLabel(text)
            label.setObjectName("Section")
            grid.addWidget(label, row, 0, 1, 2)
            row += 1

        def add(label, widget):
            nonlocal row
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
            row += 1

        section("Оформление")
        colors = QPushButton("Цвета и темы…")
        colors.setToolTip("Все цвета, свои темы, дневная тема по времени, теплота - с образцом")
        colors.clicked.connect(lambda: parent.show_colors() if parent else None)
        add("Цвета", colors)

        section("Текст")
        self.font = QFontComboBox()
        self.font.setCurrentFont(QFont(self.config.get("FONT_FAMILY", C.FONT_FAMILY)))
        add("Шрифт", self.font)
        self.size = QSpinBox()
        self.size.setRange(10, 32)
        self.size.setValue(int(self.config.get("FONT_SIZE", parent.font_size if parent else C.FONT_SIZE)))
        add("Размер", self.size)
        self.weight = QComboBox()
        self.weight.addItems(list(C.WEIGHTS))
        current_weight = next((k for k, v in C.WEIGHTS.items() if v == C.FONT_WEIGHT), "Обычный")
        self.weight.setCurrentText(self.config.get("FONT_WEIGHT", current_weight))
        add("Насыщенность", self.weight)
        self.column = QSpinBox()
        self.column.setRange(400, 1600)
        self.column.setSingleStep(20)
        self.column.setSuffix(" px")
        self.column.setValue(int(self.config.get("COLUMN_WIDTH", C.COLUMN_WIDTH)))
        add("Ширина колонки", self.column)
        self.line = QSpinBox()
        self.line.setRange(100, 250)
        self.line.setSingleStep(10)
        self.line.setSuffix(" %")
        self.line.setValue(int(self.config.get("LINE_HEIGHT", C.LINE_HEIGHT)))
        add("Межстрочный интервал", self.line)
        self.russian = QCheckBox("Только русские буквы в тексте")
        self.russian.setChecked(bool(self.config.get("ONLY_RUSSIAN", C.ONLY_RUSSIAN)))
        grid.addWidget(self.russian, row, 0, 1, 2)
        row += 1
        self.autosave = QCheckBox("Сохранять само (после паузы в наборе)")
        self.autosave.setChecked(bool(self.config.get("AUTOSAVE", C.AUTOSAVE)))
        grid.addWidget(self.autosave, row, 0, 1, 2)
        row += 1
        self.speech_rate = QComboBox()
        self.speech_rate.addItems(["Медленно", "Обычно", "Быстрее", "Быстро"])
        self.speech_rate.setCurrentText(QSettings(C.APP_ID, C.APP_ID).value("speech_rate", "Обычно"))
        add("Чтение вслух (F5)", self.speech_rate)
        self.voice = QComboBox()
        voices = []
        speech = getattr(parent, "_speech", None)
        tts = speech() if callable(speech) else None
        if tts is not None:
            try:
                voices = [v.name() for v in tts.availableVoices()]
            except Exception:
                voices = []
        self.voice.addItem("Как в системе", "")
        for name in voices:
            self.voice.addItem(name, name)
        self.voice.setCurrentIndex(max(0, self.voice.findData(QSettings(C.APP_ID, C.APP_ID).value("speech_voice", ""))))
        self.voice.setToolTip("Русские голоса, которые стоят в системе. На Debian получше звучат голоса RHVoice "
                              "(sudo apt install rhvoice-russian): Александр, Анна, Елена, Ирина")
        self.voice.setEnabled(bool(voices))
        add("Голос", self.voice)
        from .sounds import DEFAULT_VOLUME, VOLUMES
        self.dice_sound = QComboBox()
        self.dice_sound.addItems(list(VOLUMES))
        self.dice_sound.setCurrentText(QSettings(C.APP_ID, C.APP_ID).value("dice_sound", DEFAULT_VOLUME))
        add("Звук кубиков и монетки", self.dice_sound)
        self.flat = QCheckBox("Окошки без теней (если вокруг них чёрная рамка)")
        self.flat.setChecked(bool(self.config.get("FLAT_WINDOWS", C.FLAT_WINDOWS)))
        grid.addWidget(self.flat, row, 0, 1, 2)
        row += 1

        section("Разное")
        self.goal = QSpinBox()
        self.goal.setRange(0, 100000)
        self.goal.setSingleStep(50)
        self.goal.setSuffix(" слов")
        self.goal.setSpecialValueText("без цели")
        self.goal.setValue(goal)
        add("Цель на день", self.goal)
        night = QHBoxLayout()
        night.setContentsMargins(0, 0, 0, 0)
        self.night_from = QSpinBox()
        self.night_from.setRange(0, 23)
        self.night_from.setSuffix(":00")
        self.night_from.setValue(int(self.config.get("NIGHT_FROM", C.NIGHT_FROM)))
        self.night_to = QSpinBox()
        self.night_to.setRange(0, 23)
        self.night_to.setSuffix(":00")
        self.night_to.setValue(int(self.config.get("NIGHT_TO", C.NIGHT_TO)))
        night.addWidget(QLabel("с"))
        night.addWidget(self.night_from)
        night.addWidget(QLabel("до"))
        night.addWidget(self.night_to)
        night.addStretch()
        holder = QWidget()
        holder.setLayout(night)
        add("Тёплый фильтр (авто)", holder)
        backup = QHBoxLayout()
        backup.setContentsMargins(0, 0, 0, 0)
        self.backup = QLineEdit(self.config.get("BACKUP_DIR", str(C.BACKUP_DIR)))
        browse = QPushButton("…")
        browse.clicked.connect(self._browse)
        backup.addWidget(self.backup, 1)
        backup.addWidget(browse)
        holder = QWidget()
        holder.setLayout(backup)
        add("Резервные копии", holder)
        weekly = QHBoxLayout()
        weekly.setContentsMargins(0, 0, 0, 0)
        self.weekly = QLineEdit(QSettings(C.APP_ID, C.APP_ID).value("weekly_dir", "") or "")
        self.weekly.setPlaceholderText("не делать - или папка на флешке, в облаке")
        self.weekly.setToolTip("Раз в неделю вся книга архивом копируется сюда. Флешки нет - "
                               "копия сделается в следующий раз, когда папка найдётся. Хранятся последние 8.")
        browse_weekly = QPushButton("…")
        browse_weekly.clicked.connect(self._browse_weekly)
        weekly.addWidget(self.weekly, 1)
        weekly.addWidget(browse_weekly)
        holder = QWidget()
        holder.setLayout(weekly)
        add("Копия раз в неделю", holder)
        self.content.addLayout(grid)

        buttons = QHBoxLayout()
        reset = QPushButton("Сбросить всё")
        reset.clicked.connect(self._reset)
        buttons.addWidget(reset)
        buttons.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Сохранить")
        ok.setObjectName("Primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        self.content.addLayout(buttons)

    def accept(self):
        problem = C.backup_dir_problem(self.backup.text())
        if problem:
            self.backup.setFocus()
            self.backup.selectAll()
            show_warning(self, "Папка для копий", problem)
            return
        super().accept()

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка для резервных копий", self.backup.text())
        if folder:
            self.backup.setText(folder)

    def _browse_weekly(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка для недельной копии", self.weekly.text())
        if folder:
            self.weekly.setText(folder)

    def _reset(self):
        self.font.setCurrentFont(QFont("DejaVu Sans"))
        self.size.setValue(15)
        self.weight.setCurrentText("Обычный")
        self.column.setValue(740)
        self.line.setValue(150)
        self.russian.setChecked(False)
        self.autosave.setChecked(True)
        self.flat.setChecked(False)
        self.night_from.setValue(21)
        self.night_to.setValue(7)
        self.backup.setText(str(C.DATA_DIR / "backups"))

    def values(self):
        QSettings(C.APP_ID, C.APP_ID).setValue("speech_rate", self.speech_rate.currentText())
        QSettings(C.APP_ID, C.APP_ID).setValue("speech_voice", self.voice.currentData() or "")
        QSettings(C.APP_ID, C.APP_ID).setValue("dice_sound", self.dice_sound.currentText())
        weekly = self.weekly.text().strip()
        if weekly != (QSettings(C.APP_ID, C.APP_ID).value("weekly_dir", "") or ""):
            QSettings(C.APP_ID, C.APP_ID).setValue("weekly_last", "")     # новая папка - копия сразу
        QSettings(C.APP_ID, C.APP_ID).setValue("weekly_dir", weekly)
        config = {"FONT_FAMILY": self.font.currentFont().family(),
                  "FONT_SIZE": self.size.value(), "FONT_WEIGHT": self.weight.currentText(),
                  "COLUMN_WIDTH": self.column.value(), "LINE_HEIGHT": self.line.value(),
                  "ONLY_RUSSIAN": self.russian.isChecked(), "AUTOSAVE": self.autosave.isChecked(),
                  "FLAT_WINDOWS": self.flat.isChecked(),
                  "NIGHT_FROM": self.night_from.value(),
                  "NIGHT_TO": self.night_to.value(), "BACKUP_DIR": self.backup.text().strip()}
        return config, self.goal.value()


class VersionsDialog(Sheet):
    """Список сохранённых версий файла с просмотром и сравнением."""

    MODES = ["Текст версии", "Что изменило это сохранение", "Отличия от текущего текста"]
    last_mode = 1

    def __init__(self, parent, path, versions, font, current=None):
        super().__init__(parent, f"Версии · {path.stem}")
        self.setMinimumSize(900, 580)
        self.versions = []
        self.texts = []
        for version in versions:
            try:
                self.texts.append(read_text(version))
                self.versions.append(version)
            except (OSError, LockedFile):
                continue
        self.chosen = None

        layout = self.content
        row = QHBoxLayout()
        row.setSpacing(12)
        self.list = QListWidget()
        self.list.setFixedWidth(250)
        for version, text in zip(self.versions, self.texts):
            self.list.addItem(f"{version_label(version)}\n{words_label(len(WORD_RE.findall(text)))}")
        self.current = current
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(font)
        self.preview.document().setDocumentMargin(20)
        right = QVBoxLayout()
        right.setSpacing(6)
        top = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(self.MODES if current is not None else self.MODES[:2])
        self.mode.setCurrentIndex(min(VersionsDialog.last_mode, self.mode.count() - 1))
        self.mode.currentIndexChanged.connect(lambda _i: self._show(self.list.currentRow()))
        self.summary = QLabel("")
        self.summary.setObjectName("Status")
        top.addWidget(self.mode)
        top.addStretch()
        right.addLayout(top)
        right.addWidget(self.summary)
        right.addWidget(self.preview, 1)
        row.addWidget(self.list)
        row.addLayout(right, 1)
        layout.addLayout(row, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton("Закрыть")
        close.clicked.connect(self.reject)
        restore = QPushButton("Вернуть эту версию")
        restore.clicked.connect(self._restore)
        beside = QPushButton("Рядом с текстом")
        beside.setToolTip("Эта версия - в панели рядом с главой: пиши и сверяйся")
        beside.clicked.connect(self._beside)
        self.beside_index = None
        buttons.addWidget(close)
        buttons.addWidget(beside)
        buttons.addWidget(restore)
        layout.addLayout(buttons)

        self.list.currentRowChanged.connect(self._show)
        self.list.setCurrentRow(0)

    def _show(self, row):
        if not 0 <= row < len(self.texts):
            return
        mode = self.mode.currentIndex()
        VersionsDialog.last_mode = mode
        if mode == 0:
            self.preview.setPlainText(self.texts[row])
            self.summary.setText("")
            return
        if mode == 1:
            # версии идут от новых к старым: предыдущая лежит строкой ниже
            before = self.texts[row + 1] if row + 1 < len(self.texts) else ""
            after = self.texts[row]
        else:
            before, after = self.texts[row], self.current
        body, summary = diff_html(before, after)
        if mode == 1 and row + 1 >= len(self.texts):
            summary = "Самая первая версия   ·   " + summary
        self.preview.setHtml(body)
        self.summary.setText(summary)

    def _beside(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.versions):
            self.beside_index = self.versions[row]
            self.accept()

    def _restore(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.texts):
            self.chosen = self.texts[row]
            self.accept()


class SnapshotsDialog(Sheet):
    """Точки возврата: вся книга на момент - поставить, вернуться, удалить. (В коде - «снимки».)"""

    def __init__(self, owner):
        super().__init__(owner, "Точки возврата")
        self.owner = owner
        self.setMinimumSize(700, 460)
        hint = QLabel("Точка возврата - вся книга целиком на этот момент: главы, справочник, заметки, доски. "
                      "Поставь её перед большой правкой, а если не понравится - вернись. История версий глав "
                      "и статистика при возврате не меняются.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _item: self._restore())
        self.content.addWidget(self.list, 1)
        row = QHBoxLayout()
        take = QPushButton("Новая точка")
        take.clicked.connect(self._take)
        self.remove = QPushButton("Удалить")
        self.remove.clicked.connect(self._delete)
        self.back = QPushButton("Вернуться к точке")
        self.back.clicked.connect(self._restore)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.reject)
        for button in (take, self.remove):
            row.addWidget(button)
        row.addStretch()
        row.addWidget(close)
        row.addWidget(self.back)
        self.content.addLayout(row)
        self.fill()

    def fill(self):
        from .snapshots import list_snapshots
        self.list.clear()
        self.items = list_snapshots()
        for path, info in self.items:
            created = info.get("created", "")
            when = f"{created[8:10]}.{created[5:7]}.{created[:4]}   {created[11:16]}" if len(created) >= 16 else created
            if info.get("broken"):
                text = f"{path.name}\nповреждён: {info['broken']}"
            else:
                size = info["size"] / 1024
                shown = f"{size / 1024:.1f} МБ".replace(".", ",") if size >= 1024 else f"{max(1, round(size))} КБ"
                details = [words_label(info.get("words", 0)), f"глав: {info.get('chapters', 0)}", shown]
                if info.get("encrypted"):
                    details.append("зашифрован")
                text = f"{info.get('title', path.stem)}\n{when}   ·   " + "   ·   ".join(details)
            self.list.addItem(QListWidgetItem(text))
        if self.items:
            self.list.setCurrentRow(0)
        else:
            self.list.addItem("Точек возврата пока нет")
        for button in (self.remove, self.back):
            button.setEnabled(bool(self.items))

    def _current(self):
        row = self.list.currentRow()
        return self.items[row] if 0 <= row < len(self.items) else (None, None)

    def _take(self):
        if self.owner.take_snapshot():
            self.fill()

    def _restore(self):
        path, info = self._current()
        if path is not None and not info.get("broken") and self.owner.restore_snapshot(path, info):
            self.accept()

    def _delete(self):
        path, info = self._current()
        if path is not None and self.owner.delete_snapshot(path, info):
            self.fill()


class CoverDialog(Sheet):
    """Обложка категории крупно: поставить свою картинку или убрать."""

    def __init__(self, owner, folder):
        super().__init__(owner, f"Обложка · {folder.name}")
        self.folder = folder
        self.setMinimumSize(420, 520)
        self.picture = QLabel()
        self.picture.setAlignment(Qt.AlignCenter)
        self.picture.setMinimumSize(360, 400)
        self.content.addWidget(self.picture, 1)
        hint = QLabel("Картинка книги или категории: видна значком в списке слева и становится обложкой, "
                      "когда собираешь книгу в PDF или EPUB. С паролем шифруется вместе с текстами.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        row = QHBoxLayout()
        choose = QPushButton("Выбрать картинку…")
        choose.clicked.connect(self._choose)
        self.remove = QPushButton("Убрать обложку")
        self.remove.clicked.connect(self._remove)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        row.addWidget(choose)
        row.addWidget(self.remove)
        row.addStretch()
        row.addWidget(close)
        self.content.addLayout(row)
        self._show()

    def _show(self):
        from .covers import cover_pixmap, has_cover
        picture = cover_pixmap(self.folder) if has_cover(self.folder) else QPixmap()
        if picture.isNull():
            self.picture.setPixmap(QPixmap())
            self.picture.setText("Обложки пока нет")
        else:
            self.picture.setPixmap(picture.scaled(360, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.remove.setEnabled(not picture.isNull())

    def choose_file(self, path):
        from .covers import save_cover
        if not save_cover(self.folder, path):
            show_warning(self, "Обложка", "Эту картинку не получилось открыть. Подойдут JPG, PNG, WebP, BMP.")
            return False
        self._show()
        return True

    def _choose(self):
        path, _ = QFileDialog.getOpenFileName(self, "Картинка для обложки", str(Path.home()),
                                              "Картинки (*.jpg *.jpeg *.png *.webp *.bmp *.gif)")
        if path:
            self.choose_file(path)

    def _remove(self):
        from .covers import remove_cover
        remove_cover(self.folder)
        self._show()

