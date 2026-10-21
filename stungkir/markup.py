# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: знаки, разметка *курсив* и **жирный**, ударение."""

from PySide6.QtGui import QTextCursor

from .textutil import (
    STRESS, markup_range, markup_wrapped, position_map, py_index, smart_yo,
    toggle_markup, toggle_stress, utf16_len,
)



class MarkupMixin:
    """Вставка знаков и разметка в тексте. Часть главного окна."""

    def insert_symbol(self, value):
        """Вставляет знак. "открытие|закрытие" оборачивает выделенное или ставит курсор внутрь.
        Курсив, жирный и пометка в тексте главы переключаются, ударение и «ё» - с умом."""
        if self.view:
            self.view.insert(value)
            return
        if value in self.MARKUP:
            self.toggle_markup(self.MARKUP[value])
            return
        if value == STRESS:
            self.toggle_stress()
            return
        cursor = self.editor.textCursor()
        if value == "ё":
            block = cursor.block()
            line = block.text()
            start = py_index(line, cursor.selectionStart() - block.position())
            end = py_index(line, cursor.selectionEnd() - block.position())
            if cursor.selectionStart() < block.position() or cursor.selectionEnd() > block.position() + len(line):
                start = end
            value = smart_yo(line, start, end)
        if "|" in value:
            opening, closing = value.split("|", 1)
            selected = cursor.selectedText()
            cursor.insertText(opening + selected + closing)
            if not selected:
                cursor.movePosition(QTextCursor.Left, n=utf16_len(closing))
        else:
            cursor.insertText(value)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _replace_line(self, block, text):
        if block.text() == text:
            return
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.insertText(text)

    def _select_in(self, block, start, end):
        line = block.text()
        to_qt = position_map(line)
        cursor = self.editor.textCursor()
        cursor.setPosition(block.position() + to_qt(start))
        if end != start:
            cursor.setPosition(block.position() + to_qt(end), QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)

    def toggle_markup(self, mark):
        """Ctrl+I, Ctrl+B, F7 и кнопки: включают и выключают разметку, а не копят звёздочки."""
        cursor = self.editor.textCursor()
        doc = self.editor.document()
        first = doc.findBlock(cursor.selectionStart())
        last = doc.findBlock(cursor.selectionEnd())
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        try:
            if first.blockNumber() == last.blockNumber():
                line = first.text()
                start = py_index(line, cursor.selectionStart() - first.position())
                end = py_index(line, cursor.selectionEnd() - first.position())
                new, start, end = toggle_markup(line, start, end, mark)
                self._replace_line(first, new)
                self._select_in(doc.findBlockByNumber(first.blockNumber()), start, end)
            else:
                # несколько абзацев: каждый оборачивается отдельно, снимается - только если везде есть
                parts, block = [], first
                while block.isValid() and block.blockNumber() <= last.blockNumber():
                    line = block.text()
                    a = py_index(line, max(cursor.selectionStart() - block.position(), 0))
                    b = py_index(line, min(cursor.selectionEnd() - block.position(), utf16_len(line)))
                    a, b = markup_range(line, a, b, mark)
                    if a != b:
                        parts.append((block.blockNumber(), a, b, markup_wrapped(line, a, b, mark)))
                    block = block.next()
                action = "remove" if parts and all(p[3] for p in parts) else "add"
                for number, a, b, has in reversed(parts):
                    if action == "add" and has:
                        continue
                    block = doc.findBlockByNumber(number)
                    new, _a, _b = toggle_markup(block.text(), a, b, mark, action)
                    self._replace_line(block, new)
                end_block = doc.findBlockByNumber(last.blockNumber())
                self._select_in(end_block, len(end_block.text()), len(end_block.text()))
        finally:
            edit.endEditBlock()
        self.editor.setFocus()

    def toggle_stress(self):
        cursor = self.editor.textCursor()
        block = cursor.block()
        line = block.text()
        position = py_index(line, cursor.selectionEnd() - block.position())
        if cursor.selectionEnd() > block.position() + utf16_len(line):
            position = len(line)
        result = toggle_stress(line, position)
        if result is None:
            self.toast.show_message("Ударение ставится сразу после гласной: поставь курсор за ней")
            self.editor.setFocus()
            return
        new, position = result
        edit = QTextCursor(block)
        edit.beginEditBlock()
        self._replace_line(block, new)
        edit.endEditBlock()
        self._select_in(self.editor.document().findBlockByNumber(block.blockNumber()), position, position)
        self.editor.setFocus()
