# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Шаблоны карточек справочника мира: персонаж, место, государство… и свои."""

import re

from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton
from PySide6.QtCore import Qt

from ..core import config as C
from ..ui.dialogs import Sheet, ask_question, ask_text
from ..core.storage import write_atomic

BUILTIN = {
    "Персонаж": "Кто: \nВозраст: \nВнешность: \nХарактер: \nЧего хочет: \nЧего боится: \nСвязи: \nПрошлое: \n",
    "Место": "Что это: \nГде: \nКак выглядит: \nКто там живёт: \nЧем важно для сюжета: \n",
    "Государство": ("Строй: \nПравитель: \nСтолица: \nНароды и расы: \nГраницы и соседи: \nЭкономика: \n"
                    "Войско: \nВера: \nИстория: \n"),
    "Раса": "Внешность: \nСколько живут: \nГде живут: \nОбычаи: \nЯзык: \nОтношения с другими: \n",
    "Предмет": "Что это: \nКак выглядит: \nОткуда: \nСвойства: \nУ кого сейчас: \n",
    "Пустой": "",
}
LABEL_RE = re.compile(r"^(\s*[^:\n]{1,40}:)")


def templates_dir():
    return C.service_path(".templates")


def user_templates():
    """{название: текст} из папки .templates (едет через Syncthing вместе с текстами)."""
    folder = templates_dir()
    found = {}
    if folder.is_dir():
        for path in sorted(folder.glob("*.txt")):
            try:
                found[path.stem] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
    return found


def skeleton(text):
    """Из заполненной заметки - пустой шаблон: «Кто: лучница» -> «Кто: ». Строка «Также:» не берётся."""
    lines = []
    for line in text.replace("\r\n", "\n").split("\n"):
        label = LABEL_RE.match(line)
        if label and not label.group(1).strip().lower().startswith(("также", "ещё", "еще", "другие имена")):
            lines.append(label.group(1) + " ")
        elif line.strip().startswith("#"):
            lines.append(line)
    return "\n".join(lines).rstrip("\n") + "\n" if lines else ""


def save_template(name, text):
    folder = templates_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.txt"
    write_atomic(path, text.encode("utf-8"))
    return path


class TemplateDialog(Sheet):
    """Выбор шаблона для новой карточки справочника, с образцом справа."""

    def __init__(self, parent):
        super().__init__(parent, "Шаблон карточки")
        self.setMinimumSize(640, 420)
        self.own = user_templates()
        hint = QLabel("Шаблон - пустые разделы, которые останется заполнить. Свой шаблон: правый клик "
                      "по готовой карточке слева → «Сохранить как шаблон».")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        body = QHBoxLayout()
        self.list = QListWidget()
        for name in BUILTIN:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, ("builtin", name))
            self.list.addItem(item)
        for name in self.own:
            item = QListWidgetItem(f"Свой: {name}")
            item.setData(Qt.UserRole, ("own", name))
            self.list.addItem(item)
        body.addWidget(self.list, 1)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        body.addWidget(self.preview, 2)
        self.content.addLayout(body, 1)
        row = QHBoxLayout()
        self.delete = QPushButton("Удалить свой шаблон")
        self.delete.clicked.connect(self._delete)
        row.addWidget(self.delete)
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Создать")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        self.content.addLayout(row)
        self.list.currentRowChanged.connect(self._show)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        self.list.setCurrentRow(0)

    def _kind(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else ("builtin", "Пустой")

    def text(self):
        kind, name = self._kind()
        return BUILTIN.get(name, "") if kind == "builtin" else self.own.get(name, "")

    def _show(self, _row):
        self.preview.setPlainText(self.text() or "(пустая карточка)")
        self.delete.setVisible(self._kind()[0] == "own")

    def _delete(self):
        kind, name = self._kind()
        if kind != "own":
            return
        from PySide6.QtWidgets import QMessageBox
        if ask_question(self, "Шаблон", f"Удалить шаблон «{name}»?") != QMessageBox.Yes:
            return
        (templates_dir() / f"{name}.txt").unlink(missing_ok=True)
        self.own.pop(name, None)
        self.list.takeItem(self.list.currentRow())


class TemplatesMixin:
    """Шаблоны карточек. Часть главного окна."""

    def choose_template(self):
        """Текст новой карточки справочника или None, если передумал."""
        dialog = TemplateDialog(self)
        return dialog.text() if dialog.exec() else None

    def save_as_template(self, path):
        from ..core.storage import read_text
        try:
            text = self.current_text() if path == self.path else read_text(path)
        except OSError as error:
            self.toast.show_message(f"Не прочиталось: {error}")
            return
        empty = skeleton(text)
        if not empty:
            self.toast.show_message("В карточке нет разделов вида «Название: …» - шаблону не из чего взяться")
            return
        name, ok = ask_text(self, "Сохранить как шаблон", "Название шаблона:", path.stem)
        name = name.strip().strip(".")
        if not ok or not name or any(ch in name for ch in '/\\:*?"<>|'):
            return
        save_template(name, empty)
        self.toast.show_message(f"Шаблон «{name}» сохранён")
