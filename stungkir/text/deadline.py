# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Дедлайн книги: столько-то слов к дате. Блокнот считает нужный темп и показывает его."""

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QComboBox, QDateEdit, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox

from ..ui.dialogs import Sheet
from ..core.storage import LockedFile, deadline_pace, files_in, load_deadlines, read_text, save_deadlines
from ..core.textutil import WORD_RE, is_prose, plural, words_label
from ..core.i18n import tr


def pace_text(name, words_now, deadline, today=None):
    today = today or date.today()
    until = date.fromisoformat(deadline["date"])
    left, days, per_day = deadline_pace(words_now, deadline["words"], until, today)
    head = f"«{name}»: {words_now:,} из {deadline['words']:,}".replace(",", " ")
    if not left:
        return head + " - готово!"
    if per_day is None:
        return head + f" - срок {until:%d.%m.%Y} прошёл, осталось {words_label(left)}"
    return head + (f" · до {until:%d.%m.%Y} {days} {plural(days, 'день', 'дня', 'дней')}"
                   f" · нужно {words_label(per_day)} в день")


class DeadlineDialog(Sheet):
    def __init__(self, parent, categories, current, deadlines, words_of):
        super().__init__(parent, tr("Дедлайн книги"))
        self.setMinimumWidth(520)
        self.deadlines, self.words_of = deadlines, words_of
        self.removed = False
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.addWidget(QLabel(tr("Книга (категория):")), 0, 0)
        self.category = QComboBox()
        for folder in categories:
            self.category.addItem(folder.name, folder)
        if current is not None:
            self.category.setCurrentIndex(max(0, self.category.findText(current.name)))
        grid.addWidget(self.category, 0, 1)
        grid.addWidget(QLabel(tr("Сколько слов:")), 1, 0)
        self.words = QSpinBox()
        self.words.setRange(1000, 2_000_000)
        self.words.setSingleStep(5000)
        self.words.setGroupSeparatorShown(True)
        grid.addWidget(self.words, 1, 1)
        grid.addWidget(QLabel(tr("К какому числу:")), 2, 0)
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd.MM.yyyy")
        self.date.setMinimumDate(QDate.currentDate())
        grid.addWidget(self.date, 2, 1)
        self.content.addLayout(grid)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.content.addWidget(self.info)
        row = QHBoxLayout()
        self.remove = QPushButton(tr("Убрать дедлайн"))
        self.remove.clicked.connect(self._remove)
        row.addWidget(self.remove)
        row.addStretch()
        cancel = QPushButton(tr("Отмена"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("Сохранить"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        self.content.addLayout(row)
        self.category.currentIndexChanged.connect(self._load)
        self.words.valueChanged.connect(self._update)
        self.date.dateChanged.connect(self._update)
        self._load()

    def _load(self):
        name = self.category.currentText()
        existing = self.deadlines.get(name)
        self.words.setValue(existing["words"] if existing else 80_000)
        if existing:
            until = date.fromisoformat(existing["date"])
            self.date.setDate(QDate(until.year, until.month, until.day))
        else:
            self.date.setDate(QDate.currentDate().addMonths(6))
        self.remove.setVisible(existing is not None)
        self._update()

    def chosen(self):
        d = self.date.date()
        return self.category.currentText(), {"words": self.words.value(),
                                             "date": date(d.year(), d.month(), d.day()).isoformat()}

    def _update(self, *_):
        folder = self.category.currentData()
        if folder is None:
            return
        name, deadline = self.chosen()
        self.info.setText(pace_text(name, self.words_of(folder), deadline))

    def _remove(self):
        self.removed = True
        self.accept()


class DeadlineMixin:
    """Дедлайн книги. Часть главного окна."""

    def init_deadlines(self):
        self.deadlines = load_deadlines()
        self._words_cache = {}

    def book_words(self, folder):
        """Слов во всей категории: открытая глава - как сейчас в окне, остальные - с диска (с кешем)."""
        total = 0
        for path in files_in(folder):
            if not is_prose(path):
                continue
            if path == self.path and self.view is None:
                total += self.words
                continue
            try:
                stamp = path.stat().st_mtime_ns
            except OSError:
                continue
            cached = self._words_cache.get(path)
            if cached is None or cached[0] != stamp:
                try:
                    cached = (stamp, len(WORD_RE.findall(read_text(path))))
                except (OSError, LockedFile):
                    cached = (stamp, 0)
                self._words_cache[path] = cached
            total += cached[1]
        return total

    def current_deadline(self):
        """(папка, дедлайн) для книги, где открыта глава, или (None, None)."""
        if self.path is None or self.path.parent.name not in getattr(self, "deadlines", {}):
            return None, None
        return self.path.parent, self.deadlines[self.path.parent.name]

    def deadline_lines(self):
        lines = []
        for folder in self.categories():
            if folder.name in self.deadlines:
                lines.append(pace_text(folder.name, self.book_words(folder), self.deadlines[folder.name]))
        return lines

    def show_deadline(self):
        categories = [f for f in self.categories() if f.name not in self.lore_cfg["categories"]]
        if not categories:
            self.toast.show_message(tr("Сначала создай категорию для книги"))
            return
        current = self.path.parent if self.path else None
        dialog = DeadlineDialog(self, categories, current, self.deadlines, self.book_words)
        if not dialog.exec():
            return
        name, deadline = dialog.chosen()
        if dialog.removed:
            self.deadlines.pop(name, None)
        else:
            self.deadlines[name] = deadline
        save_deadlines(self.deadlines)
        self.update_status()

    def update_book_strip(self):
        folder, deadline = self.current_deadline()
        if folder is None:
            self.goal_strip.set("book", 0, False, False)
            self.goal_strip.setToolTip("")
            return
        words = self.book_words(folder)
        self.goal_strip.set("book", words / deadline["words"], words >= deadline["words"], True)
        self.goal_strip.setToolTip(pace_text(folder.name, words, deadline))
