# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Таблица как отдельный тип файла."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QHeaderView, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from ..core import config as C
from ..ui.style import rounded_menu
from ..core.textutil import has_foreign, parse_table, table_to_text
from ..ui.dialogs import ask_question, ask_text


class CellDelegate(QStyledItemDelegate):
    """Редактор ячейки: тоже без латиницы, если это включено."""

    def __init__(self, parent, on_foreign):
        super().__init__(parent)
        self.on_foreign = on_foreign

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        if C.ONLY_RUSSIAN:
            def clean(text, e=editor):
                if has_foreign(text):
                    position = e.cursorPosition()
                    cleaned = "".join(ch for ch in text if not (ch.isalpha() and has_foreign(ch)))
                    e.setText(cleaned)
                    e.setCursorPosition(max(0, position - (len(text) - len(cleaned))))
                    self.on_foreign()
            editor.textEdited.connect(clean)
        return editor


class TableView(QWidget):
    """Таблица: сетка ячеек, хранится как .csv, читается и на телефоне."""

    def __init__(self, on_change, on_foreign, toast):
        super().__init__()
        self.on_change = on_change
        self.toast = toast
        self.modified = False
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 18, 40, 6)
        layout.setSpacing(8)
        bar = QWidget()
        bar.setObjectName("TableBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        for text, callback in [("+ строка", self.add_row), ("+ столбец", self.add_column),
                               ("− строка", self.remove_row), ("− столбец", self.remove_column)]:
            button = QPushButton(text)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, c=callback: c())
            row.addWidget(button)
        row.addStretch()
        hint = QLabel("двойной клик по заголовку - переименовать, правый клик - ещё")
        hint.setObjectName("Status")
        row.addWidget(hint)
        layout.addWidget(bar)
        self.table = QTableWidget()
        self.table.setItemDelegate(CellDelegate(self.table, on_foreign))
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(38)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.setDefaultSectionSize(200)
        header.sectionDoubleClicked.connect(self.rename_column)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._header_menu)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._cell_menu)
        self.table.itemChanged.connect(self._changed)
        layout.addWidget(self.table, 1)

    # ---- данные ----
    def load(self, text):
        header, rows = parse_table(text)
        self._loading = True
        self.table.clear()
        self.table.setColumnCount(len(header))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(header)
        for r, values in enumerate(rows):
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
        self._loading = False
        self.table.resizeRowsToContents()
        self.set_modified(False)

    def headers(self):
        result = []
        for c in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(c)
            result.append(item.text() if item else "")
        return result

    def rows(self):
        result = []
        for r in range(self.table.rowCount()):
            result.append([self.table.item(r, c).text() if self.table.item(r, c) else ""
                           for c in range(self.table.columnCount())])
        return result

    def text(self):
        return table_to_text(self.headers(), self.rows())

    def tsv(self):
        lines = ["\t".join(self.headers())] + ["\t".join(r) for r in self.rows()]
        return "\n".join(lines)

    # общий интерфейс для главного окна
    def words_text(self):
        return self.text()

    def copy_text(self):
        return self.tsv(), "Таблица скопирована: вставится и в LibreOffice"

    def focus_widget(self):
        return self.table

    def reset_find(self):
        self.table.setCurrentCell(0, -1)

    def kind(self):
        return "Таблица"

    def set_modified(self, value):
        self.modified = value
        self.on_change()

    def _changed(self, _item=None):
        if not self._loading:
            self.table.resizeRowsToContents()
            self.set_modified(True)

    # ---- строки и столбцы ----
    def add_row(self, at=None):
        at = self.table.rowCount() if at is None else at
        self.table.insertRow(at)
        self._changed()

    def remove_row(self, at=None):
        at = self.table.currentRow() if at is None else at
        if at < 0:
            at = self.table.rowCount() - 1
        if at >= 0 and self.table.rowCount() > 1:
            self.table.removeRow(at)
            self._changed()

    def add_column(self, at=None):
        name, ok = ask_text(self, "Новый столбец", "Название столбца:")
        if not ok:
            return
        at = self.table.columnCount() if at is None else at
        self.table.insertColumn(at)
        self.table.setHorizontalHeaderItem(at, QTableWidgetItem(name.strip()))
        self._changed()

    def remove_column(self, at=None):
        at = self.table.currentColumn() if at is None else at
        if at < 0:
            at = self.table.columnCount() - 1
        if at < 0 or self.table.columnCount() <= 1:
            return
        title = self.headers()[at] or "без названия"
        answer = ask_question(self, "Удалить столбец",
                                      f"Удалить столбец «{title}» со всеми ячейками?")
        if answer == QMessageBox.Yes:
            self.table.removeColumn(at)
            self._changed()

    def rename_column(self, column):
        old = self.headers()[column]
        name, ok = ask_text(self, "Столбец", "Название столбца:", text=old)
        if ok:
            self.table.setHorizontalHeaderItem(column, QTableWidgetItem(name.strip()))
            self._changed()

    def sort(self, column, descending):
        rows = self.rows()
        filled = sorted([r for r in rows if r[column].strip()], key=lambda r: r[column].lower(),
                        reverse=descending)
        empty = [r for r in rows if not r[column].strip()]
        self._loading = True
        for r, values in enumerate(filled + empty):
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(value))
        self._loading = False
        self._changed()

    def _header_menu(self, pos):
        column = self.table.horizontalHeader().logicalIndexAt(pos)
        if column < 0:
            return
        menu = rounded_menu(self)
        menu.addAction("Переименовать", lambda: self.rename_column(column))
        menu.addAction("Сортировать А → Я", lambda: self.sort(column, False))
        menu.addAction("Сортировать Я → А", lambda: self.sort(column, True))
        menu.addSeparator()
        menu.addAction("Вставить столбец слева", lambda: self.add_column(column))
        menu.addAction("Вставить столбец справа", lambda: self.add_column(column + 1))
        menu.addAction("Удалить столбец", lambda: self.remove_column(column))
        menu.exec(self.table.horizontalHeader().mapToGlobal(pos))

    def _cell_menu(self, pos):
        row = self.table.rowAt(pos.y())
        menu = rounded_menu(self)
        if row >= 0:
            menu.addAction("Вставить строку выше", lambda: self.add_row(row))
            menu.addAction("Вставить строку ниже", lambda: self.add_row(row + 1))
            menu.addAction("Удалить строку", lambda: self.remove_row(row))
        else:
            menu.addAction("Добавить строку", self.add_row)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    # ---- поиск и вставка знаков ----
    def _matches(self, query):
        query = query.lower()
        return [(r, c) for r in range(self.table.rowCount()) for c in range(self.table.columnCount())
                if self.table.item(r, c) and query in self.table.item(r, c).text().lower()]

    def find(self, query, backward=False):
        """Переходит к следующей ячейке с текстом. Возвращает (номер, всего)."""
        cells = self._matches(query) if query else []
        if not cells:
            return 0, 0
        current = (self.table.currentRow(), self.table.currentColumn())
        if backward:
            earlier = [cell for cell in cells if cell < current]
            target = earlier[-1] if earlier else cells[-1]
        else:
            later = [cell for cell in cells if cell > current]
            target = later[0] if later else cells[0]
        self.table.setCurrentCell(*target)
        self.table.scrollToItem(self.table.item(*target))
        return cells.index(target) + 1, len(cells)

    def count(self, query):
        cells = self._matches(query)
        current = (self.table.currentRow(), self.table.currentColumn())
        return (cells.index(current) + 1 if current in cells else 0), len(cells)

    def insert(self, value):
        editor = QApplication.focusWidget()
        if not isinstance(editor, QLineEdit) or not self.table.isAncestorOf(editor):
            row, column = self.table.currentRow(), self.table.currentColumn()
            if row < 0 or column < 0:
                self.toast("Выбери ячейку")
                return
            item = self.table.item(row, column)
            if item is None:
                item = QTableWidgetItem("")
                self.table.setItem(row, column, item)
            self.table.editItem(item)
            editor = QApplication.focusWidget()
            if not isinstance(editor, QLineEdit):
                return
            editor.end(False)
        if "|" in value:
            opening, closing = value.split("|", 1)
            selected = editor.selectedText()
            editor.insert(opening + selected + closing)
            if not selected:
                editor.setCursorPosition(editor.cursorPosition() - len(closing))
        else:
            editor.insert(value)
