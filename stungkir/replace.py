# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Поиск и замена по всем главам: с галочками у каждого места, целым словом, по всем падежам."""

import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
)

from .dialogs import Sheet, show_warning
from .lore import Lore, LoreTerm, lore_stem
from .storage import LockedFile, files_in, read_text, save_text, snapshot
from .textutil import is_prose, name_key, plural, replace_span


def _case_like(word, sample):
    """Регистр как у найденного: «КИРЫ» -> «МИРЫ», «Киры» -> «Миры»."""
    if sample.isupper() and len(sample) > 1:
        return word.upper()
    if sample[:1].isupper():
        return word[:1].upper() + word[1:]
    if sample[:1].islower():
        return word[:1].lower() + word[1:]
    return word


def transfer_form(old, new, found):
    """Ставит новое слово в ту же форму, что и найденное: «Кира»->«Мира», найдено «Кирой» -> «Мирой».
    Для оборотов из нескольких слов - по каждому слову. Не вышло - новое как есть."""
    old_words, new_words, found_words = old.split(), new.split(), found.split()
    if not new_words:
        return ""
    if len(old_words) != len(found_words) or len(old_words) != len(new_words):
        return _case_like(new, found)
    out = []
    for old_word, new_word, found_word in zip(old_words, new_words, found_words):
        stem = lore_stem(name_key(old_word))
        found_key = name_key(found_word)
        ending = found_key[len(stem):] if found_key.startswith(stem) else ""
        old_ending = name_key(old_word)[len(stem):]
        if ending == old_ending:                      # форма та же, что и в запросе
            word = new_word
        else:
            new_stem = lore_stem(name_key(new_word))
            word = new_word[:len(new_stem)] + ending
        out.append(_case_like(word, found_word))
    return " ".join(out)


def find_places(texts, query, case=False, whole=False, forms=False, speller=None):
    """[(путь, номер строки, начало, конец, найденное, кусок для показа)]."""
    query = query.strip()
    if not query:
        return []
    if forms:
        lore = Lore(speller)
        lore.build([LoreTerm(query)])
        finder = lore.spans
    else:
        pattern = re.escape(query)
        if whole:
            pattern = rf"(?<![\ẃ]){pattern}(?![\ẃ])"
        regex = re.compile(pattern, 0 if case else re.IGNORECASE)

        def finder(line):
            return [(m.start(), m.end(), None) for m in regex.finditer(line)]
    places = []
    for path, text in texts:
        for number, line in enumerate(text.split("\n")):
            for start, end, _term in finder(line):
                left, right = max(0, start - 45), min(len(line), end + 45)
                snippet = ("…" if left else "") + line[left:right].strip() + ("…" if right < len(line) else "")
                places.append((path, number, start, end, line[start:end], snippet))
    return places


def replacement_for(place, query, new, forms, case=False):
    """Чем заменить это место: с формой слова (если «все падежи») и с регистром найденного."""
    found = place[4]
    if not new.strip():
        return ""
    if forms:
        return transfer_form(query, new.strip(), found)
    return new if case else _case_like(new, found) if new[:1].islower() or new.islower() else new


def apply_places(text, places, query, new, forms, case=False):
    """Заменяет отмеченные места в тексте одного файла. Возвращает (текст, сколько заменено).
    Место пропускается, если текст там уже другой."""
    lines = text.split("\n")
    done = 0
    for place in sorted(places, key=lambda p: (p[1], p[2]), reverse=True):
        _path, number, start, end, found, _snippet = place
        if number >= len(lines) or lines[number][start:end] != found:
            continue
        replacement = replacement_for(place, query, new, forms, case)
        if replacement:
            lines[number] = lines[number][:start] + replacement + lines[number][end:]
        else:
            lines[number], _ = replace_span(lines[number], start, end, "")   # убрать без двойных пробелов
        done += 1
    return "\n".join(lines), done


class ReplaceDialog(Sheet):
    """Что искать, на что менять, и список всех мест с галочками."""

    def __init__(self, parent, query, texts, speller):
        super().__init__(parent, "Найти и заменить во всех главах")
        self.setMinimumSize(760, 600)
        self.texts = texts
        self.speller = speller
        self.places = []
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.addWidget(QLabel("Найти:"), 0, 0)
        self.find = QLineEdit(query)
        grid.addWidget(self.find, 0, 1)
        grid.addWidget(QLabel("Заменить на:"), 1, 0)
        self.new = QLineEdit()
        self.new.setPlaceholderText("пусто - просто убрать")
        grid.addWidget(self.new, 1, 1)
        self.content.addLayout(grid)
        boxes = QHBoxLayout()
        self.case = QCheckBox("С учётом регистра")
        self.whole = QCheckBox("Целое слово")
        self.whole.setChecked(True)
        self.forms = QCheckBox("Все падежи (для имён и названий)")
        self.forms.setToolTip("«Кира → Мира» заменит и «Киры» на «Миры», и «Кирой» на «Мирой»")
        for box in (self.case, self.whole, self.forms):
            boxes.addWidget(box)
            box.toggled.connect(self._later)
        boxes.addStretch()
        self.content.addLayout(boxes)
        self.count = QLabel("")
        self.count.setObjectName("Status")
        self.count.setWordWrap(True)
        self.content.addWidget(self.count)
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.content.addWidget(self.list, 1)
        row = QHBoxLayout()
        none = QPushButton("Снять все")
        none.clicked.connect(lambda: self._check_all(Qt.Unchecked))
        every = QPushButton("Отметить все")
        every.clicked.connect(lambda: self._check_all(Qt.Checked))
        row.addWidget(none)
        row.addWidget(every)
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        self.ok = QPushButton("Заменить отмеченные")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(self.ok)
        self.content.addLayout(row)
        self.timer = QTimer(self, singleShot=True, interval=350)
        self.timer.timeout.connect(self.refresh)
        self.find.textChanged.connect(self._later)
        self.new.textChanged.connect(self._later)
        self.refresh()

    def _later(self, *_):
        self.timer.start()

    def _check_all(self, state):
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(state)

    def settings(self):
        return self.find.text().strip(), self.new.text(), self.case.isChecked(), self.whole.isChecked(), \
            self.forms.isChecked()

    def refresh(self):
        query, new, case, whole, forms = self.settings()
        self.places = find_places(self.texts, query, case, whole, forms, self.speller)
        self.list.clear()
        files = {p[0] for p in self.places}
        for place in self.places:
            path, _number, _start, _end, found, snippet = place
            target = replacement_for(place, query, new, forms, case) or "(убрать)"
            item = QListWidgetItem(f"{path.parent.name} · {path.stem}   «{found}» → «{target}»\n{snippet}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list.addItem(item)
        if not query:
            self.count.setText("Напиши, что искать")
        elif self.places:
            self.count.setText(f"{len(self.places)} {plural(len(self.places), 'место', 'места', 'мест')} в "
                               f"{len(files)} {plural(len(files), 'файле', 'файлах', 'файлах')}. Сними галочки там, "
                               "где менять не надо. Перед заменой каждый файл кладётся в «Версии файла».")
        else:
            self.count.setText("Ничего не нашлось")
        self.ok.setEnabled(bool(self.places))

    def chosen(self):
        return [p for i, p in enumerate(self.places) if self.list.item(i).checkState() == Qt.Checked]


class ReplaceMixin:
    """Замена по всем главам. Часть главного окна."""

    def replace_texts(self):
        """Все текстовые файлы во всех категориях, включая справочник мира (там тоже бывают имена)."""
        texts = []
        for folder in self.categories():
            for path in files_in(folder):
                if not is_prose(path):
                    continue
                try:
                    texts.append((path, read_text(path)))
                except (OSError, LockedFile):
                    continue
        return texts

    def remember_replace(self, changes):
        """Последняя замена во всех главах: [(файл, было, стало)] - чтобы отменить одной кнопкой."""
        self.last_replace = changes or None

    def undo_replace(self):
        """Отменить последнюю замену везде. Главы, которые с тех пор правили, не трогаются."""
        changes = getattr(self, "last_replace", None)
        if not changes:
            self.toast.show_message("Нечего отменять: замен во всех главах ещё не было")
            return
        if self.is_modified():
            self.save()
        restored, skipped = 0, []
        for path, before, after in changes:
            try:
                current = read_text(path)
                if current != after:
                    skipped.append(path.stem)
                    continue
                snapshot(path, current)
                save_text(path, before)
                restored += 1
            except (OSError, LockedFile) as error:
                skipped.append(f"{path.stem} ({error})")
        self.last_replace = None
        if self.view is None and any(p == self.path for p, _b, _a in changes):
            self.check_external()
        self.rebuild_lore()
        text = f"Замена отменена в {restored} {plural(restored, 'файле', 'файлах', 'файлах')}"
        if skipped:
            text += f". Не тронуты (их уже правили): {', '.join(skipped[:3])}{'…' if len(skipped) > 3 else ''}"
        self.toast.show_message(text, 5000)

    def show_replace_all(self):
        if self.is_modified() and not self.save():
            return
        query = self.global_edit.text().strip() if self.global_search.isVisible() else ""
        if not query:
            query = self.editor.textCursor().selectedText().strip()
        dialog = ReplaceDialog(self, query, self.replace_texts(), self.speller)
        if not dialog.exec():
            return
        query, new, case, _whole, forms = dialog.settings()
        by_file = {}
        for place in dialog.chosen():
            by_file.setdefault(place[0], []).append(place)
        done, files = 0, 0
        changes = []
        for path, places in by_file.items():
            try:
                old = read_text(path)
                text, count = apply_places(old, places, query, new, forms, case)
                if count:
                    snapshot(path, old)
                    save_text(path, text)
                    changes.append((path, old, text))
                    done += count
                    files += 1
            except (OSError, LockedFile) as error:
                show_warning(self, "Замена", f"«{path.stem}» не изменён:\n{error}")
        if self.path in by_file and self.view is None:
            self.check_external()
        self.rebuild_lore()
        self.remember_replace(changes)
        self.toast.show_message(f"Заменено {done} в {files} {plural(files, 'файле', 'файлах', 'файлах')}. "
                                "Нажми сюда - отменить", 6000, action=self.undo_replace)
        if self.global_search.isVisible() and self.overlay_mode == "search":
            self.run_global_search()
