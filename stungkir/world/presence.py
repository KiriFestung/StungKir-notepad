# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Кто в какой главе: персонажи и термины мира по главам. Видно, кто надолго пропал."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem

from ..core import config as C
from ..ui.dialogs import Sheet
from ..core.textutil import position_map


def presence(lore, texts):
    """{имя термина: [сколько раз в каждой главе]} и [(термин, первое место по главам)]."""
    counts = {term.name: [0] * len(texts) for term in lore.terms}
    first = {}
    for column, (_path, text) in enumerate(texts):
        for number, line in enumerate(text.split("\n")):
            for start, _end, term in lore.spans(line):
                counts[term.name][column] += 1
                first.setdefault((term.name, column), (number, start))
    return counts, first


def longest_gap(row):
    """Сколько глав подряд термин не упоминается между первым и последним упоминанием."""
    seen = [i for i, n in enumerate(row) if n]
    if len(seen) < 2:
        return 0
    return max(b - a - 1 for a, b in zip(seen, seen[1:]))


class PresenceDialog(Sheet):
    """Строки - персонажи и термины, столбцы - главы. Ярче клетка - чаще упоминание."""

    def __init__(self, parent, lore, texts, open_place):
        super().__init__(parent, "Кто в какой главе")
        self.setMinimumSize(900, 560)
        self.lore, self.texts, self.open_place = lore, texts, open_place
        self.counts, self.first = presence(lore, texts)
        row = QHBoxLayout()
        self.kind = QComboBox()
        self.kind.addItems(["Все", "Персонажи", "Справочник мира"])
        self.order = QComboBox()
        self.order.addItems(["По первому появлению", "Сначала самые частые", "Сначала надолго пропавшие"])
        for combo in (self.kind, self.order):
            combo.currentIndexChanged.connect(self.fill)
            row.addWidget(combo)
        row.addStretch()
        self.content.addLayout(row)
        hint = QLabel("Число - сколько раз упомянут в главе. Клик по клетке - открыть главу на этом месте. "
                      "Справа - сколько глав подряд термин отсутствовал посреди книги.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.cellClicked.connect(self._clicked)
        self.content.addWidget(self.table, 1)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close)
        self.content.addLayout(buttons)
        self.fill()

    def rows(self):
        kind = self.kind.currentIndex()
        terms = [t for t in self.lore.terms
                 if kind == 0 or (kind == 1 and not t.source) or (kind == 2 and t.source)]
        terms = [t for t in terms if any(self.counts.get(t.name, []))]
        order = self.order.currentIndex()
        if order == 0:
            terms.sort(key=lambda t: next(i for i, n in enumerate(self.counts[t.name]) if n))
        elif order == 1:
            terms.sort(key=lambda t: -sum(self.counts[t.name]))
        else:
            terms.sort(key=lambda t: -longest_gap(self.counts[t.name]))
        return terms

    def fill(self):
        terms = self.rows()
        self.terms = terms
        chapters = len(self.texts)
        self.table.clear()
        self.table.setRowCount(len(terms))
        self.table.setColumnCount(chapters + 2)
        headers = [f"{i + 1}" for i in range(chapters)] + ["Всего", "Пропал"]
        self.table.setHorizontalHeaderLabels(headers)
        for i, (path, _text) in enumerate(self.texts):
            self.table.horizontalHeaderItem(i).setToolTip(f"{path.parent.name} · {path.stem}")
        self.table.setVerticalHeaderLabels([t.name for t in terms])
        top = max((max(self.counts[t.name]) for t in terms), default=1) or 1
        base, strong = QColor(C.BG), QColor(C.ACCENT)
        for r, term in enumerate(terms):
            row = self.counts[term.name]
            for c, n in enumerate(row):
                cell = QTableWidgetItem(str(n) if n else "")
                cell.setTextAlignment(Qt.AlignCenter)
                if n:
                    share = 0.25 + 0.75 * (n / top) ** 0.5
                    cell.setBackground(C.mix(base, strong, share))
                    cell.setToolTip(f"{term.name}: {n} в «{self.texts[c][0].stem}»")
                self.table.setItem(r, c, cell)
            total = QTableWidgetItem(str(sum(row)))
            total.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, chapters, total)
            gap = longest_gap(row)
            missing = QTableWidgetItem(f"{gap} гл." if gap else "")
            missing.setTextAlignment(Qt.AlignCenter)
            if gap >= 3:
                missing.setForeground(QColor(C.SPELL))
            self.table.setItem(r, chapters + 1, missing)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(34)

    def _clicked(self, row, column):
        if column >= len(self.texts) or row >= len(self.terms):
            return
        place = self.first.get((self.terms[row].name, column))
        if place:
            self.accept()
            self.open_place(self.texts[column][0], *place)


class PresenceMixin:
    """Кто в какой главе. Часть главного окна."""

    def show_presence(self):
        self.rebuild_lore()
        texts = self.crutch_texts()          # главы - те же, что для штампов: без справочника, досок и таблиц
        PresenceDialog(self, self.lore, texts, self._open_line_place).exec()

    def _open_line_place(self, path, number, start):
        if not self.open_path(path):
            return
        block = self.editor.document().findBlockByNumber(number)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.setPosition(block.position() + position_map(block.text())(start))
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.editor.setFocus()
