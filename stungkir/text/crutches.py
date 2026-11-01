# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Мои штампы: личный список слов-костылей автора, подсветка, поиск по главам, замена с просмотром."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ..ui.dialogs import Sheet, ask_text, show_warning
from ..core.storage import LockedFile, files_in, load_crutches, read_text, save_crutches, save_text, snapshot
from ..ui.style import rounded_menu
from ..core.textutil import WORD_RE, Crutches, is_prose, plural, position_map, py_index, replace_span
from ..core.i18n import tr


def parse_entries(text):
    """Строки окна -> список штампов без пустых и повторов (порядок сохраняется)."""
    seen, out = set(), []
    for line in text.split("\n"):
        entry = line.strip().strip(",;")
        key = entry.lower().replace("ё", "е")
        if entry and WORD_RE.search(entry) and key not in seen:
            seen.add(key)
            out.append(entry)
    return out


def crutch_places(crutches, texts):
    """Все места: [(путь, номер строки, начало, конец, найденное, штамп, кусок для показа)]."""
    places = []
    for path, text in texts:
        for number, line in enumerate(text.split("\n")):
            for start, end, entry in crutches.spans(line):
                left, right = max(0, start - 45), min(len(line), end + 45)
                snippet = ("…" if left else "") + line[left:right].strip() + ("…" if right < len(line) else "")
                places.append((path, number, start, end, line[start:end], entry, snippet))
    return places


def chapter_stats(crutches, texts):
    """[(путь, слов, штампов, на 1000 слов)] - больше всего штампов сверху."""
    rows = []
    for path, text in texts:
        words = len(WORD_RE.findall(text))
        found = sum(crutches.count(text).values())
        rows.append((path, words, found, found * 1000 / words if words else 0.0))
    rows.sort(key=lambda r: (-r[3], -r[2]))
    return rows


def apply_replacements(text, places, replacement):
    """Заменяет отмеченные места в тексте одной главы. Место пропускается, если текст там уже другой."""
    lines = text.split("\n")
    done = 0
    for _path, number, start, end, found, _entry, _snippet in sorted(places, key=lambda p: (p[1], p[2]), reverse=True):
        if number < len(lines) and lines[number][start:end] == found:
            lines[number], _ = replace_span(lines[number], start, end, replacement)
            done += 1
    return "\n".join(lines), done


class CrutchesDialog(Sheet):
    """Список штампов и сколько их в каждой главе."""

    def __init__(self, parent, entries, texts, key_of):
        super().__init__(parent, tr("Мои штампы"))
        self.setMinimumSize(980, 560)
        self.texts = texts
        self.key_of = key_of
        self.action = None
        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        hint = QLabel(tr("По слову или обороту в строке. Формы слова находятся сами: «вздохнул» - это и "
                      "«вздохнула», и «вздохнули». Добавлять можно и из текста: правый клик по слову."))
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        left.addWidget(hint)
        self.edit = QPlainTextEdit("\n".join(entries))
        self.edit.setPlaceholderText(tr("вдруг\nвнезапно\nоднако\nвздохнул\nпочувствовал, как"))
        left.addWidget(self.edit, 1)
        self.totals = QLabel("")
        self.totals.setWordWrap(True)
        left.addWidget(self.totals)
        body.addLayout(left, 1)
        right = QVBoxLayout()
        title = QLabel(tr("По главам: больше всего штампов сверху"))
        title.setObjectName("Section")
        right.addWidget(title)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr(name) for name in ["Глава", "Слов", "Штампов", "На 1000 слов"]])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        right.addWidget(self.table, 1)
        body.addLayout(right, 2)
        self.content.addLayout(body, 1)
        tools = QHBoxLayout()
        find = QPushButton(tr("Найти все места"))
        find.setToolTip(tr("Список мест по всем главам: клик - открыть, правый клик - убрать или заменить"))
        find.clicked.connect(lambda: self._finish("find"))
        tools.addWidget(find)
        tools.addSpacing(18)
        tools.addWidget(QLabel(tr("Заменить везде:")))
        self.which = QComboBox()
        self.which.setMinimumWidth(200)
        tools.addWidget(self.which)
        replace = QPushButton(tr("Выбрать места…"))
        replace.clicked.connect(lambda: self._finish("replace"))
        tools.addWidget(replace)
        tools.addStretch()
        self.content.addLayout(tools)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton(tr("Отмена"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(tr("Сохранить"))
        save.setDefault(True)
        save.clicked.connect(lambda: self._finish("save"))
        row.addWidget(cancel)
        row.addWidget(save)
        self.content.addLayout(row)
        self.timer = QTimer(self, singleShot=True, interval=400)
        self.timer.timeout.connect(self.recount)
        self.edit.textChanged.connect(self.timer.start)
        self.recount()

    def entries(self):
        return parse_entries(self.edit.toPlainText())

    def recount(self):
        entries = self.entries()
        crutches = Crutches(entries)
        totals = {}
        for _path, text in self.texts:
            for entry, n in crutches.count(text).items():
                totals[entry] = totals.get(entry, 0) + n
        shown = sorted(entries, key=lambda e: -totals.get(e, 0))
        self.totals.setText("   ·   ".join(f"{e} {totals.get(e, 0)}" for e in shown) or "Список пуст")
        current = self.which.currentText()
        self.which.clear()
        self.which.addItems(shown)
        if current in shown:
            self.which.setCurrentText(current)
        rows = chapter_stats(crutches, self.texts)
        self.table.setRowCount(len(rows))
        for i, (path, words, found, rate) in enumerate(rows):
            name = f"{path.parent.name} · {path.stem}"
            for column, value in enumerate((name, str(words), str(found), f"{rate:.1f}".replace(".", ","))):
                cell = QTableWidgetItem(value)
                if column:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, column, cell)

    def _finish(self, action):
        if action == "replace" and not self.which.currentText():
            return
        self.action = action
        self.accept()


class ReplaceAllDialog(Sheet):
    """Все места одного штампа с галочками: заменяются только отмеченные."""

    def __init__(self, parent, entry, places, key_of):
        super().__init__(parent, tr("Заменить «{entry}»").format(entry=entry))
        self.setMinimumSize(720, 520)
        self.places = places
        text = QLabel(tr("Найдено: {n}. Сними галочки там, где «{entry}» нужно оставить. Перед заменой каждая "
                         "глава кладётся в «Версии файла» - всё можно вернуть.").format(n=len(places), entry=entry))
        text.setWordWrap(True)
        self.content.addWidget(text)
        self.list = QListWidget()
        self.list.setWordWrap(True)
        for place in places:
            path, _number, _start, _end, found, _entry, snippet = place
            item = QListWidgetItem(f"{path.parent.name} · {path.stem}   «{found}»\n{snippet}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list.addItem(item)
        self.content.addWidget(self.list, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Заменить на:")))
        self.replacement = QLineEdit()
        self.replacement.setPlaceholderText(tr("пусто - просто убрать слово"))
        row.addWidget(self.replacement, 1)
        none = QPushButton(tr("Снять все"))
        none.clicked.connect(lambda: self._check_all(Qt.Unchecked))
        every = QPushButton(tr("Отметить все"))
        every.clicked.connect(lambda: self._check_all(Qt.Checked))
        row.addWidget(none)
        row.addWidget(every)
        self.content.addLayout(row)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(tr("Отмена"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("Заменить отмеченные"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        self.content.addLayout(buttons)

    def _check_all(self, state):
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(state)

    def chosen(self):
        return [p for i, p in enumerate(self.places) if self.list.item(i).checkState() == Qt.Checked]


class CrutchesMixin:
    """Мои штампы. Часть главного окна."""

    def init_crutches(self):
        self.crutch_entries = load_crutches()
        self.editor.crutch_callback = self.add_crutch
        self.apply_crutches()

    def apply_crutches(self):
        crutches = Crutches(self.crutch_entries)
        self.highlighter.crutches = crutches
        self.side.highlighter.crutches = crutches
        self._rehighlight()
        self.side.rehighlight()

    def add_crutch(self, phrase):
        phrase = " ".join(phrase.split())
        if phrase.lower().replace("ё", "е") in {e.lower().replace("ё", "е") for e in self.crutch_entries}:
            self.toast.show_message(tr("«{phrase}» уже в моих штампах").format(phrase=phrase))
            return
        self.crutch_entries.append(phrase)
        save_crutches(self.crutch_entries)
        self.apply_crutches()
        found = sum(Crutches([phrase]).count(text).get(phrase, 0) for _p, text in self.crutch_texts())
        self.toast.show_message(tr("«{phrase}» в моих штампах: по главам {found} {n}").format(phrase=phrase, found=found, n=plural(found, 'раз', 'раза', 'раз')), 3000)

    def crutch_texts(self):
        """Главы для штампов: все текстовые файлы, кроме справочников мира, досок и таблиц."""
        texts = []
        for folder in self.categories():
            if folder.name in self.lore_cfg["categories"]:
                continue
            for path in files_in(folder):
                if not is_prose(path):
                    continue
                if path == self.path and self.view is None:
                    texts.append((path, self.current_text()))
                    continue
                try:
                    texts.append((path, read_text(path)))
                except (OSError, LockedFile):
                    continue
        return texts

    def show_crutches(self):
        dialog = CrutchesDialog(self, self.crutch_entries, self.crutch_texts(), self._position_key)
        if not dialog.exec():
            return
        self.crutch_entries = dialog.entries()
        save_crutches(self.crutch_entries)
        self.apply_crutches()
        if dialog.action == "find":
            self.show_crutch_places()
        elif dialog.action == "replace":
            self.replace_crutch_everywhere(dialog.which.currentText())

    # ---- места по всем главам ----
    def show_crutch_places(self):
        self._open_overlay("crutches")
        self.global_results.setFocus()
        if not self.crutch_entries:
            self.global_results.clear()
            self.global_count.setText(tr("Список пуст: «Ещё → Мои штампы» или правый клик по слову в тексте"))
            return
        crutches = Crutches(self.crutch_entries)
        paths = {p for p, _t in self.crutch_texts()}

        def finder(text):
            offset = 0
            for line in text.split("\n"):
                for start, end, entry in crutches.spans(line):
                    yield offset + start, offset + end, entry
                offset += len(line) + 1
        self._fill_results(finder, only=paths)

    def crutch_menu(self, item, pos):
        path, position, length, found, entry = item.data(Qt.UserRole)
        menu = rounded_menu(self)
        menu.addAction(tr("Убрать «{found}» здесь").format(found=found), lambda: self._edit_place(item, ""))
        menu.addAction(tr("Заменить здесь на…"), lambda: self._replace_here(item))
        menu.addSeparator()
        menu.addAction(tr("Заменить «{entry}» везде…").format(entry=entry), lambda: self.replace_crutch_everywhere(entry))
        menu.exec(self.global_results.viewport().mapToGlobal(pos))

    def _replace_here(self, item):
        found = item.data(Qt.UserRole)[3]
        text, ok = ask_text(self, tr("Заменить"), tr("Чем заменить «{found}»? Пусто - просто убрать.").format(found=found))
        if ok:
            self._edit_place(item, text)

    def _edit_place(self, item, replacement):
        from pathlib import Path
        path, position, length, found, _entry = item.data(Qt.UserRole)
        if not self.open_path(Path(path)):
            return
        doc = self.editor.document()
        block = doc.findBlock(position)
        line = block.text()
        start = py_index(line, position - block.position())
        end = start + len(found)
        if line[start:end] != found:
            show_warning(self, tr("Мои штампы"), tr("Текст в этом месте уже изменился. Обновляю список."))
            self.show_crutch_places()
            return
        new, cursor_at = replace_span(line, start, end, replacement)
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        self._replace_line(block, new)
        edit.endEditBlock()
        cursor = self.editor.textCursor()
        cursor.setPosition(block.position() + position_map(new)(cursor_at))
        self.editor.setTextCursor(cursor)
        self.show_crutch_places()          # места ниже в этой строке сдвинулись - пересчитываем

    def replace_crutch_everywhere(self, entry):
        crutches = Crutches([entry])
        if self.is_modified() and not self.save():
            return
        places = crutch_places(crutches, self.crutch_texts())
        if not places:
            show_warning(self, tr("Мои штампы"), tr("«{entry}» в главах не встречается.").format(entry=entry))
            return
        dialog = ReplaceAllDialog(self, entry, places, self._position_key)
        if not dialog.exec():
            return
        chosen, replacement = dialog.chosen(), dialog.replacement.text()
        by_file = {}
        for place in chosen:
            by_file.setdefault(place[0], []).append(place)
        done, files = 0, 0
        changes = []
        for path, file_places in by_file.items():
            try:
                old = read_text(path)
                new, count = apply_replacements(old, file_places, replacement)
                if count:
                    snapshot(path, old)            # прежний текст - в «Версии файла»
                    save_text(path, new)
                    changes.append((path, old, new))
                    done += count
                    files += 1
            except (OSError, LockedFile) as error:
                show_warning(self, tr("Мои штампы"), tr("«{n}» не изменена:\n{error}").format(n=self._position_key(path), error=error))
        if self.path in by_file and self.view is None:
            self.check_external()                  # открытая глава перечитывается с диска
        self.remember_replace(changes)
        self.toast.show_message(tr("Заменено {done} в {files} {n}. Нажми сюда - отменить").format(done=done, files=files, n=plural(files, 'главе', 'главах', 'главах')), 6000, action=self.undo_replace)
        if self.global_search.isVisible() and self.overlay_mode == "crutches":
            self.show_crutch_places()
