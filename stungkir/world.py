# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: персонажи, справочник мира, заметки на полях."""

import json
import os
import re
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout,
)

from . import config as C
from .style import fade, rounded_menu
from .textutil import (
    has_foreign, is_board, is_table, is_timeline, name_key,
    position_map, stem,
)
from .storage import (
    LockedFile, files_in, notes_path, read_text, report_problem, save_names,
    save_text,
)
from .lore import Lore, LoreTerm, birth_year, lore_note, lore_terms_from_table, lore_tooltip, save_lore_config
from .dialogs import NoteDialog, ask_text, show_warning


class WorldMixin:
    """Персонажи, справочник мира, заметки на полях. Часть главного окна."""

    # ---------------- заметки на полях ----------------
    def load_notes(self):
        self.notes_margin.clear()
        if self.path is None or self.view is not None:
            return
        file = notes_path(self.path)
        if not file.exists():
            return
        try:
            data = json.loads(read_text(file))
            if not isinstance(data, list):
                raise ValueError("внутри не список")
        except LockedFile:
            report_problem(f"Заметки к «{self.path.stem}» зашифрованы другим паролем")
            return
        except (OSError, ValueError) as error:
            # откладываем испорченный файл в сторону, чтобы новые заметки его не затёрли
            spare = file.with_name(file.name + ".broken")
            try:
                os.replace(file, spare)
            except OSError:
                spare = file
            report_problem(f"Заметки на полях к «{self.path.stem}» не прочитались, файл сохранён как {spare}",
                           error)
            return
        self.notes_margin.load(data)

    def save_notes(self):
        if self.path is None or self.view is not None:
            return True
        file = notes_path(self.path)
        data = self.notes_margin.data()
        try:
            if data:
                file.parent.mkdir(parents=True, exist_ok=True)
                save_text(file, json.dumps(data, ensure_ascii=False, indent=1))
            elif file.exists():
                file.unlink()
            return True
        except OSError as error:
            report_problem(f"Заметки на полях к «{self.path.stem}» не сохранились", error)
            return False

    def note_for_block(self, block):
        if self.view is not None:
            return
        if self.path is None:
            self.toast.show_message("Сначала сохрани главу: заметки хранятся рядом с ней")
            return
        index = self.notes_margin.index_for(block)
        if index is not None:
            self.edit_note(index)
            return
        dialog = NoteDialog(self, paragraph=block.text())
        if dialog.exec() and dialog.action == "save" and dialog.text():
            if not self.notes_margin.shown:
                self.toggle_margin_notes()
            self.notes_margin.add(block, dialog.text())
            self.save_notes()
        self.editor.setFocus()

    def edit_note(self, index):
        cursor, text = self.notes_margin.notes[index]
        dialog = NoteDialog(self, text, existing=True, paragraph=self.notes_margin.block_of(index).text())
        if dialog.exec():
            if dialog.action == "delete" or (dialog.action == "save" and not dialog.text()):
                del self.notes_margin.notes[index]
            elif dialog.action == "save":
                self.notes_margin.notes[index][1] = dialog.text()
            self.notes_margin.update()
            self.save_notes()
        self.editor.setFocus()

    def toggle_margin_notes(self):
        self.notes_margin.shown = not self.notes_margin.shown
        self.settings.setValue("margin_notes", "true" if self.notes_margin.shown else "false")
        self.notes_margin.update()

    def toggle_line_numbers(self):
        self.line_numbers.set_shown(not self.line_numbers.shown)
        self.settings.setValue("line_numbers", "true" if self.line_numbers.shown else "false")

    def toggle_lore_underline(self):
        self.highlighter.lore_underline = not self.highlighter.lore_underline
        self.settings.setValue("lore_underline", "true" if self.highlighter.lore_underline else "false")
        self.side.highlighter.lore_underline = self.highlighter.lore_underline
        self._rehighlight()
        self.side.rehighlight()

    # ---------------- справочник мира ----------------
    def lore_categories(self):
        names = set(self.lore_cfg["categories"])
        return [c for c in self.categories() if c.name in names]

    def rebuild_lore(self):
        """Собирает термины из категорий-справочников и списка персонажей."""
        terms, seen = [], set()

        def add(term):
            if name_key(term.name) not in seen:
                seen.add(name_key(term.name))
                terms.append(term)

        for folder in self.lore_categories():
            for f in files_in(folder):
                if is_board(f) or is_timeline(f) or f.stem.startswith("_"):
                    continue   # «_Общее.txt» - просто файл в справочнике, не термин
                try:
                    text = read_text(f)
                except (OSError, LockedFile):
                    continue
                if is_table(f):
                    for term in lore_terms_from_table(text, f"{folder.name} · {f.stem}", f):
                        add(term)
                else:
                    note, aliases = lore_note(text)
                    add(LoreTerm(f.stem, note, f, folder.name, aliases, birth_year(text)))
        for name in self.names:
            add(LoreTerm(name))
        if self.lore.build(terms):
            self._rehighlight()
            self.side.rehighlight()

    def toggle_lore_category(self, folder):
        categories = self.lore_cfg["categories"]
        if folder.name in categories:
            categories.remove(folder.name)
            message = f"«{folder.name}» больше не справочник"
        else:
            categories.append(folder.name)
            message = f"«{folder.name}» теперь справочник мира: наведи мышь на имя в тексте"
        save_lore_config(self.lore_cfg)
        self.refresh_tree()
        self.toast.show_message(message, 4000)

    def lore_term_at(self, pos):
        if self.view is not None or not self.lore.terms:
            return None
        cursor = self.editor.cursorForPosition(pos)
        block = cursor.block()
        text = block.text()
        to_qt = position_map(text)
        at = cursor.positionInBlock()
        for start, end, term in self.lore.spans(text):
            a, b = to_qt(start), to_qt(end)
            if not a <= at <= b:
                continue
            # курсор встаёт и в пустоту за концом строки: проверяем, что мышь правда над словом
            left, right = QTextCursor(block), QTextCursor(block)
            left.setPosition(block.position() + a)
            right.setPosition(block.position() + b)
            first, last = self.editor.cursorRect(left), self.editor.cursorRect(right)
            if first.top() == last.top():
                inside = first.left() <= pos.x() <= last.right() and first.top() <= pos.y() <= first.bottom()
            else:
                inside = first.top() <= pos.y() <= last.bottom()
            return term if inside else None
        return None

    def _lore_tip(self, pos):
        term = self.lore_term_at(pos)
        if term is None:
            return None
        year = self.story_year(self.path) if term.born is not None and self.path is not None else None
        return lore_tooltip(term, bool(self.lore_categories()), None if year is None else year - term.born)

    def _lore_open(self, pos):
        term = self.lore_term_at(pos)
        if term is None:
            return False
        if term.path is None:
            self.toast.show_message(f"У «{term.name}» пока нет заметки в справочнике")
            return True
        QTimer.singleShot(0, self, lambda: self.open_lore_term(term))
        return True

    def open_lore_term(self, term):
        """Ctrl+клик по термину: заметка открывается рядом, а глава остаётся на месте."""
        self.open_beside(term.path)

    # ---------------- панель рядом ----------------
    def open_beside(self, path):
        if path is None or not path.is_file():
            return
        self.side.set_font(self.editor.font())
        self.side.show_path(path)
        self.place_side("left" if self.settings.value("side_left", "false") == "true" else "right")
        if not self.side.isVisible():
            self.side.show()
            try:
                left, right = [int(x) for x in self.settings.value("side_sizes", [])]
            except (TypeError, ValueError):
                left, right = 0, 0
            total = max(self.split.width(), 600)
            if left < 300 or right < 200:
                left, right = total * 3 // 5, total * 2 // 5
            self.split.setSizes([left, right])
        self.settings.setValue("side_file", str(path))
        self.settings.setValue("side_open", "true")
        self.place_overlays()

    def compare_with_version(self, index=None):
        """«Сравнить с версией»: прошлое сохранение главы - в панели рядом с текстом (по умолчанию
        слева), ушедшее подсвечено; ◀ ▶ - листать версии. Писать можно дальше, сравнение обновляется."""
        if self.path is None or self.view is not None:
            self.toast.show_message("Сравнивать можно главу: открой её")
            return
        from .storage import list_versions
        if self.is_modified():
            self.save(auto=True)
        versions = list_versions(self.path)
        if not versions:
            self.toast.show_message("Версий пока нет: они появляются при сохранении", 3000)
            if hasattr(self, "picture_pop"):
                self.picture_pop.play("empty-versions", 3000, width=260)
            return
        # самая свежая версия часто совпадает с текстом - берём первую, которая отличается
        if index is None:
            index = 0
            now = self.current_text()
            for i, version in enumerate(versions):
                try:
                    if read_text(version) != now:
                        index = i
                        break
                except (OSError, LockedFile):
                    continue
        self.side.set_font(self.editor.font())
        self.side.show_version(self.path, versions, min(index, len(versions) - 1), self.current_text)
        if self.side.isVisible():
            return
        if self.settings.value("side_left_for_versions", "true") == "true":
            self.place_side("left")
        self.side.show()
        total = max(self.split.width(), 600)
        self.split.setSizes([total // 2, total // 2])

    def place_side(self, where):
        """Панель рядом - слева или справа от текста."""
        index = 0 if where == "left" else 1
        if self.split.indexOf(self.side) != index:
            self.split.insertWidget(index, self.side)
            self.split.setStretchFactor(index, 2)
            self.split.setStretchFactor(1 - index, 3)

    def flip_side(self):
        left = self.split.indexOf(self.side) == 0
        self.place_side("right" if left else "left")
        if self.side.showing_version:
            self.settings.setValue("side_left_for_versions", "false" if left else "true")
        else:
            self.settings.setValue("side_left", "false" if left else "true")

    def close_side(self):
        if self.side.isVisible():
            self.settings.setValue("side_sizes", self.split.sizes())
            self.side.hide()
        self.settings.setValue("side_open", "false")
        self.place_overlays()
        self.editor.setFocus()

    def toggle_side(self):
        if self.side.isVisible():
            self.close_side()
            return
        last = self.settings.value("side_file", "")
        if last and Path(last).is_file() and Path(last) != self.path:
            self.open_beside(Path(last))
            return
        for folder in self.lore_categories() + self.categories():
            for f in files_in(folder):
                if f != self.path:
                    self.open_beside(f)
                    return
        self.toast.show_message("Рядом пока нечего открыть: нужен ещё хотя бы один файл")

    def open_from_side(self, path):
        """«Открыть здесь»: файл из панели идёт в основное окно, а текущий - в панель."""
        current = self.path
        if self.open_path(path) and current is not None and current != path and current.is_file():
            self.open_beside(current)

    def refresh_side(self, changed=None):
        """Обновляет панель, если показанный в ней файл изменился, переехал или пропал."""
        if not self.side.isVisible() or self.side.path is None:
            return
        if not self.side.path.exists():
            self.close_side()
            return
        if self.side.showing_version:                # в панели версия этой главы - обновить сравнение
            if self.side.path != self.path:
                self.close_side()                    # ушли в другую главу - версия чужая
            else:
                self.side.refresh_version(keep_place=True)
            return
        if changed is None or changed == self.side.path:
            self.side.show_path(self.side.path)

    def check_term_spelling(self):
        """Ищет по всем файлам имена и названия, написанные не так, как в справочнике."""
        self.rebuild_lore()
        if not self.lore.terms:
            show_warning(self, "Написание имён",
                         "Пока не с чем сравнивать. Добавь имена в «Персонажи» или сделай категорию "
                         "справочником мира: правый клик по ней в списке слева.")
            return
        texts = []
        for folder in self.categories():
            for f in files_in(folder):
                if is_board(f) or is_timeline(f):
                    continue
                try:
                    texts.append(self.current_text() if f == self.path else read_text(f))
                except (OSError, LockedFile):
                    continue
        self.variant_terms = self.lore.variants(texts, self.lore_cfg["ignore"])
        self._open_overlay("variants")
        self.global_results.setFocus()
        if not self.variant_terms:
            self.global_results.clear()
            self.global_count.setText("Всё сходится: каждое имя везде написано одинаково")
            return
        words = sorted(self.variant_terms, key=len, reverse=True)
        self._fill_results(re.compile(r"(?<![А-Яа-яЁё\u0301])(?:" + "|".join(map(re.escape, words))
                                      + r")(?![А-Яа-яЁё\u0301])"))

    def _results_menu(self, pos):
        item = self.global_results.itemAt(pos)
        if item and item.data(Qt.UserRole) and self.overlay_mode == "crutches":
            self.crutch_menu(item, pos)
            return
        if self.overlay_mode != "variants" or not item or not item.data(Qt.UserRole):
            return
        word = item.data(Qt.UserRole)[3]
        menu = rounded_menu(self)
        menu.addAction(f"«{word}» - так и задумано", lambda: self._ignore_variant(word))
        menu.exec(self.global_results.viewport().mapToGlobal(pos))

    def _ignore_variant(self, word):
        if word not in self.lore_cfg["ignore"]:
            self.lore_cfg["ignore"].append(word)
            save_lore_config(self.lore_cfg)
        self.check_term_spelling()

    # ---------------- персонажи ----------------
    def _build_characters(self, parent):
        box = QFrame(parent)
        box.setObjectName("Overlay")
        box.setFixedSize(640, 460)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        top = QHBoxLayout()
        title = QLabel("Персонажи и имена")
        title.setObjectName("Title")
        top.addWidget(title)
        top.addStretch()
        close_button = QPushButton("✕")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setStyleSheet("background: transparent; padding: 4px 10px;")
        close_button.clicked.connect(self.hide_characters)
        top.addWidget(close_button)
        layout.addLayout(top)
        row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Добавить имя, например Ольга")
        self.name_edit.returnPressed.connect(self._add_name_from_edit)
        row.addWidget(self.name_edit, 1)
        add = QPushButton("Добавить")
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(self._add_name_from_edit)
        row.addWidget(add)
        layout.addLayout(row)
        self.names_info = QLabel("")
        self.names_info.setObjectName("Status")
        self.names_info.setWordWrap(True)
        layout.addWidget(self.names_info)
        self.names_list = QListWidget()
        self.names_list.itemClicked.connect(self._search_name)
        self.names_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.names_list.customContextMenuRequested.connect(self._names_menu)
        layout.addWidget(self.names_list, 1)
        check = QPushButton("Проверить, не написано ли где-то имя иначе")
        check.setCursor(Qt.PointingHandCursor)
        check.clicked.connect(lambda: (self.hide_characters(), self.check_term_spelling()))
        layout.addWidget(check)
        close = QShortcut(QKeySequence(Qt.Key_Escape), box)
        close.setContext(Qt.WidgetWithChildrenShortcut)
        close.activated.connect(self.hide_characters)
        box.hide()
        return box

    def show_characters(self):
        if not self.characters.isVisible():
            self.place_overlays()
            self.characters.show()
            self.characters.raise_()
            self.veil.raise_()
            fade(self.characters, 0.0, 1.0, 180)
        self.refresh_characters()
        self.name_edit.setFocus()

    def hide_characters(self):
        if self.characters.isVisible():
            fade(self.characters, None, 0.0, 160, self.characters.hide)
        self.editor.setFocus()

    def name_from_text(self, word):
        """«Считать персонажем» из текста: даём поправить форму слова, прежде чем записать."""
        word = word.strip().replace("\u0301", "")
        if word.isupper() and len(word) > 1:
            word = word[0] + word[1:].lower()       # ТЕРВЕНА -> Тервена
        name, ok = ask_text(self, "Новый персонаж",
                            "Как записать имя? Лучше в начальной форме: «Кира», а не «Киры» - "
                            "остальные падежи найдутся сами.", text=word)
        if ok:
            self.track_name(name)

    def track_name(self, name):
        name = name.strip().replace("\u0301", "")
        if name.isupper() and len(name) > 1:
            name = name[0] + name[1:].lower()
        if not name or has_foreign(name):
            self.toast.show_message("Имя должно быть русскими буквами")
            return
        if name_key(name) in {name_key(n) for n in self.names}:
            self.toast.show_message(f"«{name}» уже в списке")
            return
        known = Lore(self.speller)
        known.build([LoreTerm(n) for n in self.names])
        match = known.spans(name)
        if match and match[0][0] == 0 and match[0][1] == len(name):
            self.toast.show_message(f"«{name}» - это форма имени «{match[0][2].name}», оно уже в списке", 3500)
            return
        self.names.append(name)
        save_names(self.names)
        self.highlighter.set_names(self.names)
        self.rebuild_lore()
        self._rehighlight()
        if self.speller.available and not self.speller.ok(name):
            self.speller.add(name, as_name=True)
            self._rehighlight()
        self.toast.show_message(f"Слежу за персонажем «{name}»")
        if self.characters.isVisible():
            self.refresh_characters()

    def _add_name_from_edit(self):
        text = self.name_edit.text().strip()
        if text:
            self.track_name(text)
            self.name_edit.clear()

    def _names_menu(self, pos):
        item = self.names_list.itemAt(pos)
        if not item or item.data(Qt.UserRole) is None:
            return
        name = item.data(Qt.UserRole)
        menu = rounded_menu(self)
        menu.addAction(f"Не считать «{name}»", lambda: self._untrack(name))
        menu.exec(self.names_list.viewport().mapToGlobal(pos))

    def _untrack(self, name):
        self.names = [n for n in self.names if n != name]
        save_names(self.names)
        self.highlighter.set_names(self.names)
        self.rebuild_lore()
        self._rehighlight()
        self.refresh_characters()

    def count_names(self, text):
        """Сколько раз каждое имя встречается в тексте - по тем же правилам, что и подсветка:
        с падежами («Кира», «Киры», «Кирой») и без ложных совпадений с обычными словами."""
        counter = self._name_counter
        found = {}
        for line in text.split("\n"):
            for _start, _end, term in counter.spans(line):
                found[term.name] = found.get(term.name, 0) + 1
        return found

    def refresh_characters(self):
        self.names_list.clear()
        if not self.names:
            self.names_info.setText("Пока никого. Добавь имя здесь или нажми правой кнопкой "
                                    "на имя в тексте → «Считать персонажем».")
            return
        self._name_counter = Lore(self.speller)
        self._name_counter.build([LoreTerm(name) for name in self.names])
        chapter, in_folder, total = {}, {}, {}

        def add(target, counts):
            for name, n in counts.items():
                target[name] = target.get(name, 0) + n

        folder = self.path.parent if self.path else None
        for category in self.categories():
            for f in files_in(category):
                if f == self.path:
                    continue
                try:
                    counts = self.count_names(read_text(f))
                except (OSError, LockedFile):
                    continue
                add(total, counts)
                if category == folder:
                    add(in_folder, counts)
        # открытая глава - как она сейчас на экране, даже если ещё не сохранена
        if self.view is None:
            chapter = self.count_names(self.current_text())
            add(total, chapter)
            add(in_folder, chapter)
        rows = sorted(((total.get(n, 0), in_folder.get(n, 0), chapter.get(n, 0), n) for n in self.names),
                      key=lambda r: (-r[0], r[3]))
        where = f"в «{folder.name}»" if folder else "в категории"
        for count_all, count_folder, count_chapter, name in rows:
            item = QListWidgetItem(f"{name}\nв главе {count_chapter}   ·   {where} {count_folder}"
                                   f"   ·   всего {count_all}")
            item.setData(Qt.UserRole, name)
            if count_all == 0:
                item.setForeground(QColor(C.DIM))
            self.names_list.addItem(item)
        self.names_info.setText("Считаются и падежи: «Кира», «Киры», «Кирой». "
                                "Клик ищет имя по всем главам, правый клик убирает из списка.")

    def _search_name(self, item):
        name = item.data(Qt.UserRole)
        if not name:
            return
        self.hide_characters()
        base = name[:len(stem(name_key(name)))]
        self.global_edit.setText(base)
        self.show_global_search()
