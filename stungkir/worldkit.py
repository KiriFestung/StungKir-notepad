# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Заготовки для мира: одним нажатием - пустые таблицы и карточки для бестиария, государств,
народов, персонажей, мест, магии, вер и хронология. Все поля пустые: мир - твой."""

import json

from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton

from .dialogs import Sheet
from .storage import append_to_order, save_text, unique_path
from .textutil import table_to_text

# название: ("table", столбцы) | ("card", текст карточки) | ("timeline", None)
KITS = {
    "Бестиарий": ("table", ["Существо", "Где водится", "Как выглядит", "Повадки", "Чем опасно", "Слабости",
                            "Заметки"]),
    "Государства": ("table", ["Название", "Строй", "Правитель", "Столица", "Народы", "Соседи и отношения",
                              "Заметки"]),
    "Народы и расы": ("table", ["Название", "Внешность", "Сколько живут", "Где живут", "Обычаи",
                                "Отношения с другими", "Заметки"]),
    "Персонажи": ("table", ["Имя", "Роль в сюжете", "Возраст", "Внешность", "Характер", "Чего хочет", "Тайна"]),
    "Места": ("table", ["Место", "Что это", "Климат", "Кто живёт", "Чем известно", "Заметки"]),
    "Магия": ("card", "Источник: \nКто может: \nЦена: \nОграничения: \nКак выглядит со стороны: \n"
                      "Чем опасна: \nКак к ней относятся: \n"),
    "Веры и культы": ("card", "Во что верят: \nБоги или силы: \nОбряды: \nСлужители: \nЗапреты: \n"
                              "Кто не верит и что с ними: \n"),
    "Языки": ("card", "Кто говорит: \nКак звучит: \nПисьменность: \nЧастые слова: \nКак ругаются: \n"),
    "Хронология мира": ("timeline", None),
}


def create_kit(category, names):
    """Создать выбранные заготовки в категории. Занятое имя не затирается - рядом появится «… (2)».
    Возвращает пути новых файлов."""
    made = []
    for name in names:
        kind, data = KITS[name]
        if kind == "table":
            path, text = category / f"{name}.csv", table_to_text(list(data), [])
        elif kind == "card":
            # «_» в начале - общая карточка справочника: «магия» и «языки» в тексте не подчёркиваются
            path, text = category / f"_{name}.txt", data
        else:
            path, text = category / f"{name}.timeline", json.dumps({"events": []}, ensure_ascii=False, indent=1) + "\n"
        path = unique_path(path)
        save_text(path, text)
        append_to_order(category, path.name)
        made.append(path)
    return made


class WorldKitDialog(Sheet):
    """Галочки - что создать."""

    def __init__(self, parent, category_name, is_lore):
        super().__init__(parent, f"Заготовки для мира · {category_name}")
        self.setMinimumWidth(480)
        hint = QLabel("Пустые таблицы и карточки - заполнишь своим. Таблицы можно дополнять столбцами, "
                      "карточки - своими пунктами.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        self.boxes = {}
        for name, (kind, _data) in KITS.items():
            what = {"table": "таблица", "card": "карточка", "timeline": "хронология"}[kind]
            box = QCheckBox(f"{name}  ·  {what}")
            box.setChecked(True)
            self.boxes[name] = box
            self.content.addWidget(box)
        self.lore = QCheckBox("Сделать категорию справочником мира (имена подчёркиваются в тексте)")
        self.lore.setChecked(not is_lore)
        self.lore.setVisible(not is_lore)
        self.content.addWidget(self.lore)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Создать")
        ok.setObjectName("Primary")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        self.content.addLayout(row)

    def chosen(self):
        return [name for name, box in self.boxes.items() if box.isChecked()]
