# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: поиск в главе, по всем файлам и пометки."""

import re
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QListWidgetItem, QTextEdit

from . import config as C
from .style import fade
from .textutil import MARKER_FILLED_RE, plural, searchable_text, utf16_len
from .storage import LockedFile, files_in, read_text


class SearchMixin:
    """Поиск в главе, по всем файлам и пометки. Часть главного окна."""

    # ---------------- поиск в файле ----------------
    def show_search(self):
        selected = "" if self.table_mode else self.editor.textCursor().selectedText()
        if selected and " " not in selected:
            self.find_edit.setText(selected)
        if not self.search_bar.isVisible():
            self.place_overlays()
            self.search_bar.show()
            self.search_bar.raise_()
            fade(self.search_bar, 0.0, 1.0, 180)
        self.find_edit.setFocus()
        self.find_edit.selectAll()
        self.update_matches()

    def hide_search(self):
        if self.search_bar.isVisible():
            fade(self.search_bar, None, 0.0, 160, self.search_bar.hide)
        self.editor.setExtraSelections([])
        (self.view.focus_widget() if self.view else self.editor).setFocus()

    def _on_find_text(self):
        if self.view:
            self.view.reset_find()
            self.find_next()
            return
        cursor = self.editor.textCursor()
        cursor.setPosition(cursor.selectionStart())
        self.editor.setTextCursor(cursor)
        self.find_next()

    def _find(self, backward):
        query = self.find_edit.text()
        if self.table_mode:
            current, total = self.view.find(query, backward) if query else (0, 0)
            self.find_count.setText("" if not query else (f"{current} из {total}" if total else "нет"))
            return
        if query:
            doc = self.editor.document()
            flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
            found = doc.find(query, self.editor.textCursor(), flags)
            if found.isNull():
                start = QTextCursor(doc)
                if backward:
                    start.movePosition(QTextCursor.End)
                found = doc.find(query, start, flags)
            if not found.isNull():
                self.editor.setTextCursor(found)
        self.update_matches()

    def find_next(self):
        self._find(False)

    def find_prev(self):
        self._find(True)

    def update_matches(self):
        query = self.find_edit.text()
        if self.table_mode:
            current, total = self.view.count(query) if query else (0, 0)
            self.find_count.setText("" if not query else (f"{current} из {total}" if total else "нет"))
            return
        selections, total, current = [], 0, 0
        if query:
            doc = self.editor.document()
            active = self.editor.textCursor()
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(C.FOUND))
            cursor = QTextCursor(doc)
            while total < 5000:
                cursor = doc.find(query, cursor)
                if cursor.isNull():
                    break
                total += 1
                if (cursor.selectionStart(), cursor.selectionEnd()) == (
                        active.selectionStart(), active.selectionEnd()):
                    current = total
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                selection.format = fmt
                selections.append(selection)
        self.editor.setExtraSelections(selections)
        if not query:
            self.find_count.setText("")
        elif total:
            self.find_count.setText(f"{current} из {total}")
        else:
            self.find_count.setText("нет")

    # ---------------- поиск по всем файлам и пометки ----------------
    def _open_overlay(self, mode):
        self.overlay_mode = mode
        is_search = mode == "search"
        self.global_title.setText({"search": "Поиск по всем файлам", "markers": "Пометки во всех файлах",
                                   "variants": "Имена, написанные иначе",
                                   "crutches": "Мои штампы во всех главах",
                                   "speakers": "Кто говорит: реплики, где легко запутаться"}[mode])
        self.global_edit.setVisible(is_search)
        self.replace_button.setVisible(is_search)
        if not self.global_search.isVisible():
            self.place_overlays()
            self.global_search.show()
            self.global_search.raise_()
            fade(self.global_search, 0.0, 1.0, 180)

    def show_global_search(self):
        selected = self.editor.textCursor().selectedText()
        if selected and " " not in selected:
            self.global_edit.setText(selected)
        self._open_overlay("search")
        self.global_edit.setFocus()
        self.global_edit.selectAll()
        self.run_global_search()

    def show_markers(self):
        self._open_overlay("markers")
        self.global_results.setFocus()
        self._fill_results(MARKER_FILLED_RE)

    def hide_global_search(self):
        if self.global_search.isVisible():
            fade(self.global_search, None, 0.0, 160, self.global_search.hide)
        self.editor.setFocus()

    def run_global_search(self):
        if self.overlay_mode != "search":
            return
        query = self.global_edit.text().strip()
        if len(query) < 2:
            self.global_results.clear()
            self.global_count.setText("Напиши хотя бы две буквы")
            return
        self._fill_results(re.compile(re.escape(query), re.IGNORECASE))

    def _fill_results(self, pattern, limit=300, only=None):
        """pattern - регулярное выражение или функция текст -> [(начало, конец, подпись)].
        only - если задано, искать только в этих файлах."""
        self.global_results.clear()
        total, files_hit = 0, 0
        per_label = {}
        for folder in self.categories():
            for f in files_in(folder):
                if only is not None and f not in only:
                    continue
                if f == self.path:
                    text = self.current_text()
                else:
                    try:
                        text = read_text(f)
                    except (OSError, LockedFile):
                        continue
                text = searchable_text(f, text.replace("\r\n", "\n").replace("\r", "\n"))
                hit_here = False
                if hasattr(pattern, "finditer"):
                    matches = ((m.start(), m.end(), m.group()) for m in pattern.finditer(text))
                else:
                    matches = pattern(text)
                for i, j, label in matches:
                    per_label[label] = per_label.get(label, 0) + 1
                    if total >= limit:
                        continue                    # показываем не больше limit, но считаем все
                    hit_here = True
                    total += 1
                    left, right = max(0, i - 50), min(len(text), j + 50)
                    snippet = text[left:right].replace("\n", " ").strip()
                    snippet = ("…" if left else "") + snippet + ("…" if right < len(text) else "")
                    if self.overlay_mode == "speakers":        # кусок разговора: реплики через «·»
                        part = " · ".join(x.strip() for x in text[i:j].split("\n") if x.strip())
                        snippet = part if len(part) <= 200 else part[:200] + "…"
                    name = f.stem if f.suffix == ".txt" else f.name
                    header = f"{folder.name} · {name}"
                    if self.overlay_mode == "markers":
                        header += f"   {text[i:j]}"
                    elif self.overlay_mode == "variants":
                        header += f"   «{text[i:j]}» - может, «{self.variant_terms.get(text[i:j], '?')}»?"
                    elif self.overlay_mode == "crutches":
                        header += f"   «{text[i:j]}»"
                    elif self.overlay_mode == "speakers":
                        header += f"   {label}"
                    item = QListWidgetItem(f"{header}\n{snippet}")
                    item.setData(Qt.UserRole, (str(f), utf16_len(text[:i]), utf16_len(text[i:j]),
                                               text[i:j], label))
                    self.global_results.addItem(item)
                files_hit += hit_here
        if total:
            what = {"search": plural(total, "совпадение", "совпадения", "совпадений"),
                    "markers": plural(total, "пометка", "пометки", "пометок"),
                    "variants": plural(total, "место", "места", "мест"),
                    "crutches": plural(total, "место", "места", "мест"),
                    "speakers": plural(total, "место", "места", "мест")}[self.overlay_mode]
            extra = f" (показаны первые {limit})" if total >= limit else ""
            if self.overlay_mode == "variants":
                extra += ". Правый клик - если так и задумано"
            if self.overlay_mode == "crutches":
                extra += ": " + " · ".join(f"{k} {v}" for k, v in sorted(per_label.items(), key=lambda x: -x[1]))
                extra += ". Правый клик - убрать или заменить"
            self.global_count.setText(
                f"{total} {what} в {files_hit} {plural(files_hit, 'файле', 'файлах', 'файлах')}{extra}")
        elif self.overlay_mode == "markers":
            self.global_count.setText("Пометок нет. Поставь [вот так] в тексте или нажми F7")
        elif self.overlay_mode == "crutches":
            self.global_count.setText("Ни одного штампа из списка - чисто")
        elif self.overlay_mode == "speakers":
            self.global_count.setText("Везде понятно, кто говорит")
        else:
            self.global_count.setText("Ничего не нашлось")

    def _open_global_result(self, item):
        path, position, length, found = item.data(Qt.UserRole)[:4]
        if not self.open_path(Path(path)):
            return
        mode = self.overlay_mode
        self.hide_global_search()
        if self.view:
            self.view.reset_find()
            self.view.find(found)
            return
        end = self.editor.document().characterCount() - 1
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(min(position, end))
        cursor.setPosition(min(position + length, end), QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        if mode == "search":
            self.show_search()
