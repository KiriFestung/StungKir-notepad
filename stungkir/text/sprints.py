# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Спринты: таймер с лаской - это и есть спринт. Каждый таймер, который дошёл до конца, ложится в историю:
когда, сколько минут, сколько слов. Видно лучший спринт и свой обычный темп. История - в
StungKir/.stungkir/sprints.json (едет вместе с текстами), до 500 последних."""

import json
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem

from ..core import config as C
from ..core import i18n
from ..core.i18n import tr
from ..core.storage import write_atomic
from ..core.textutil import plural, signed, words_label
from ..ui.dialogs import Sheet

FILE = "sprints.json"
KEEP = 500
RECORD_MINUTES = 5          # рекорд скорости - только у спринтов от 5 минут: минутный рывок не в счёт


def sprints_path():
    return C.ROOT / C.SERVICE_DIR / FILE


def load_sprints():
    """[{"when": "2026-11-01T10:00", "minutes": 25, "words": 430}] - старые сначала. Испорченный файл - пусто."""
    try:
        data = json.loads(sprints_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    good = []
    for item in data if isinstance(data, list) else []:
        try:
            good.append({"when": str(item["when"]), "minutes": int(item["minutes"]), "words": int(item["words"])})
        except (KeyError, TypeError, ValueError):
            continue
    return good


def number(value):
    """Скорость с одним знаком после запятой: по-русски «20,5», по-английски «20.5»."""
    text = f"{value:.1f}"
    return text.replace(".", ",") if i18n.LANG == i18n.DEFAULT else text


def speed(entry):
    """Слов в минуту."""
    return entry["words"] / max(1, entry["minutes"])


def best_sprint(sprints):
    counted = [s for s in sprints if s["minutes"] >= RECORD_MINUTES and s["words"] > 0]
    return max(counted, key=speed) if counted else None


def record_sprint(minutes, words, when=None):
    """Записать спринт. Возвращает (запись, побит ли рекорд скорости). Ноль минут - не спринт: None, False."""
    if minutes < 1:
        return None, False
    sprints = load_sprints()
    before = best_sprint(sprints)
    entry = {"when": (when or datetime.now()).isoformat(timespec="minutes"), "minutes": int(minutes),
             "words": int(words)}
    sprints = (sprints + [entry])[-KEEP:]
    try:
        path = sprints_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(path, json.dumps(sprints, ensure_ascii=False, indent=0).encode("utf-8"))
    except OSError:
        pass                                    # не записалось - спринт всё равно прошёл, сообщение покажем
    record = (minutes >= RECORD_MINUTES and words > 0 and before is not None and speed(entry) > speed(before))
    return entry, record


def sprint_result(minutes, written, record):
    """Что сказать, когда таймер дошёл до конца."""
    text = tr("Время вышло. За {minutes} мин: {n} {words}").format(
        minutes=minutes, n=signed(written), words=plural(written, "слово", "слова", "слов"))
    if minutes >= 1 and written > 0:
        text += tr(" ({per} в минуту)").format(per=number(written / minutes))
    if record:
        text += tr(". Рекорд скорости!")
    return text


class SprintsDialog(Sheet):
    """История спринтов: последние сверху, лучший - цветом."""

    def __init__(self, parent=None):
        super().__init__(parent, tr("Спринты"))
        self.setMinimumSize(560, 460)
        sprints = load_sprints()
        best = best_sprint(sprints)
        summary = QLabel(self._summary(sprints, best))
        summary.setWordWrap(True)
        self.content.addWidget(summary)
        self.table = QTableWidget(len(sprints), 4)
        self.table.setHorizontalHeaderLabels([tr(name) for name in ("Когда", "Минут", "Слов", "В минуту")])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        strong = QColor(C.IMPORTANT)
        for row, entry in enumerate(reversed(sprints)):
            when = entry["when"].replace("T", " ")
            cells = [when, str(entry["minutes"]), signed(entry["words"]), number(speed(entry))]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column:
                    item.setTextAlignment(Qt.AlignCenter)
                if entry is best:
                    item.setForeground(strong)
                self.table.setItem(row, column, item)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.content.addWidget(self.table, 1)
        hint = QLabel(tr("Спринт - это таймер с лаской слева: поставь минуты и жми «Старт». Дошёл до конца - "
                         "спринт записан. Рекорд скорости считается у спринтов от {n} минут.").format(n=RECORD_MINUTES))
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        row = QHBoxLayout()
        row.addStretch()
        close = QPushButton(tr("Закрыть"))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        row.addWidget(close)
        self.content.addLayout(row)

    @staticmethod
    def _summary(sprints, best):
        if not sprints:
            return tr("Спринтов пока не было.")
        total = sum(max(0, s["words"]) for s in sprints)
        minutes = sum(s["minutes"] for s in sprints)
        text = tr("Спринтов: {count} · написано {n} за {minutes} мин · в среднем {per} в минуту").format(
            count=len(sprints), n=words_label(total), minutes=minutes, per=number(total / max(1, minutes)))
        if best is not None:
            text += "\n" + tr("Лучший: {n} за {minutes} мин ({per} в минуту), {when}").format(
                n=words_label(best["words"]), minutes=best["minutes"], per=number(speed(best)),
                when=best["when"].split("T")[0])
        return text
