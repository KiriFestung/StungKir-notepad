# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Конфликты синхронизации и не-текстовые файлы.

Syncthing, Dropbox и Nextcloud, если глава поменялась на двух устройствах сразу, кладут рядом копию:
«Глава 3.sync-conflict-20261015-101010-ABC.txt», «Глава 3 (conflicted copy 2026-10-15).txt».
Блокнот показывает такие копии значком и даёт сравнить и выбрать: свою, ту или обе."""

import os

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextBrowser

from .dialogs import Sheet
from .storage import LockedFile, conflict_original, read_text, save_text, snapshot, unique_path
from .textutil import WORD_RE, diff_html, plural

NOT_TEXT_HINT = ("Блокнот открывает только тексты, таблицы, доски и хронологии. Файлы Word и RTF можно "
                 "добавить через «Ещё → Файлы и импорт → Добавить файлы».")


def find_conflicts(folders, files_of):
    """[(копия, оригинал)] во всех категориях."""
    found = []
    for folder in folders:
        for path in files_of(folder):
            original = conflict_original(path)
            if original is not None:
                found.append((path, original))
    return found


class ConflictDialog(Sheet):
    """Две версии главы: что в копии по сравнению с твоей. Выбрать: свою, ту или обе."""

    def __init__(self, parent, copy, original):
        super().__init__(parent, "Конфликт синхронизации")
        self.setMinimumSize(820, 600)
        self.copy, self.original = copy, original
        self.choice = None
        try:
            mine = read_text(original) if original.exists() else ""
            theirs = read_text(copy)
        except (OSError, LockedFile):
            mine, theirs = "", ""
        self.mine, self.theirs = mine, theirs
        words = (len(WORD_RE.findall(mine)), len(WORD_RE.findall(theirs)))
        info = QLabel(f"Глава «{original.stem}» поменялась на двух устройствах, и программа синхронизации "
                      f"оставила вторую версию рядом. Здесь - {words[0]} {plural(words[0], 'слово', 'слова', 'слов')}, "
                      f"в копии - {words[1]}. Ниже - чем копия отличается: зачёркнутого в ней нет, "
                      "выделенное в ней добавлено.")
        info.setWordWrap(True)
        self.content.addWidget(info)
        view = QTextBrowser()
        html, summary = diff_html(mine, theirs)
        view.setHtml(html)
        self.content.addWidget(view, 1)
        note = QLabel(summary + ". Что бы ни выбрал, проигравшая версия останется: копия - в корзине, "
                      "твоя - в «Версиях файла».")
        note.setObjectName("Status")
        note.setWordWrap(True)
        self.content.addWidget(note)
        row = QHBoxLayout()
        both = QPushButton("Оставить обе")
        both.setToolTip("Копия станет отдельной главой «… (вторая версия)»")
        both.clicked.connect(lambda: self._done("both"))
        theirs_button = QPushButton("Взять ту")
        theirs_button.setToolTip("Текст копии встанет в главу, а твой уйдёт в «Версии файла»")
        theirs_button.clicked.connect(lambda: self._done("theirs"))
        mine_button = QPushButton("Оставить мою")
        mine_button.setObjectName("Primary")
        mine_button.setDefault(True)
        mine_button.setToolTip("Копия уйдёт в корзину")
        mine_button.clicked.connect(lambda: self._done("mine"))
        later = QPushButton("Позже")
        later.clicked.connect(self.reject)
        row.addWidget(later)
        row.addStretch()
        for button in (both, theirs_button, mine_button):
            row.addWidget(button)
        self.content.addLayout(row)

    def _done(self, choice):
        self.choice = choice
        self.accept()


def resolve(copy, original, choice, mine=None, theirs=None, to_trash=None):
    """Применить выбор. Возвращает главу, которую стоит открыть."""
    if choice == "both":
        target = unique_path(original.with_name(f"{original.stem} (вторая версия){original.suffix}"))
        os.replace(copy, target)
        return target
    if choice == "theirs":
        theirs = read_text(copy) if theirs is None else theirs
        if original.exists():
            snapshot(original, read_text(original) if mine is None else mine)
        save_text(original, theirs)
    (to_trash or (lambda p: p.unlink()))(copy)
    return original


class ConflictsMixin:
    """Конфликты синхронизации и чужие файлы в папках. Часть главного окна."""

    def check_conflicts(self, quiet=False):
        """Ищет копии-конфликты. О новых (которых не было при прошлой проверке) говорит плашкой."""
        found = find_conflicts(self.categories(), self._all_files)
        known = getattr(self, "_conflicts", {})
        self._conflicts = {copy: original for copy, original in found}
        fresh = [(c, o) for c, o in found if c not in known]
        if fresh and not quiet:
            copy, original = fresh[0]
            more = f" (и ещё {len(fresh) - 1})" if len(fresh) > 1 else ""
            self.toast.show_message(f"Конфликт синхронизации в «{original.stem}»{more}. Нажми сюда - разобрать",
                                    7000, action=lambda c=copy, o=original: self.open_conflict(c, o))
        return found

    def announce_conflicts(self):
        """При запуске: конфликты, которые уже лежат в папках."""
        self._conflicts = {}
        self.check_conflicts()

    @staticmethod
    def _all_files(folder):
        from .storage import files_in
        return files_in(folder, everything=True)

    def open_conflict(self, copy, original):
        if self.path == original and self.is_modified():
            self.save()
        dialog = ConflictDialog(self, copy, original)
        if not dialog.exec() or dialog.choice is None:
            return
        from .trash import move_to_trash
        reopen = self.path == original
        if reopen:
            self.path = None                     # глава перечитается с диска уже с выбранным текстом
        target = resolve(copy, original, dialog.choice, dialog.mine, dialog.theirs, move_to_trash)
        self.refresh_tree()
        self.open_path(target)
        self.toast.show_message({"mine": "Оставлена твоя версия, копия в корзине",
                                 "theirs": "Взята версия из копии, твоя - в «Версиях файла»",
                                 "both": "Обе версии оставлены"}[dialog.choice], 3500)

    def refuse_not_text(self, path):
        self.toast.show_message(f"«{path.name}» - не текст, его не открыть. " + NOT_TEXT_HINT, 5000)

