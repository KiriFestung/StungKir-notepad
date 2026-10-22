# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Своя корзина: удалённые главы и категории 30 дней лежат в StungKir/.trash и возвращаются
одной кнопкой. Версии и заметки главы не удаляются - вернулась глава, вернулась и её история."""

import json
import os
import secrets
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton

from . import config as C
from .dialogs import Sheet, ask_question
from .storage import append_to_order, log_error, unique_path
from .textutil import plural

DAYS = 30
META = "meta.json"


def trash_dir():
    return C.service_path(".trash")


def move_to_trash(path):
    """Глава или категория - в корзину. Возвращает папку записи в корзине."""
    entry = trash_dir() / f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
    entry.mkdir(parents=True)
    try:
        relative = path.relative_to(C.ROOT).as_posix()
    except ValueError:
        relative = path.name
    meta = {"from": relative, "when": datetime.now().isoformat(timespec="seconds"),
            "kind": "folder" if path.is_dir() else "file"}
    (entry / META).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    try:
        os.replace(path, entry / path.name)
    except OSError:
        shutil.rmtree(entry, ignore_errors=True)
        raise
    return entry


def trash_entries():
    """[(папка записи, что лежит, откуда (относительный путь), когда удалено)] - новые сверху."""
    out = []
    folder = trash_dir()
    if not folder.is_dir():
        return out
    for entry in sorted(folder.iterdir(), reverse=True):
        try:
            meta = json.loads((entry / META).read_text(encoding="utf-8"))
            when = datetime.fromisoformat(meta["when"])
            item = next(p for p in entry.iterdir() if p.name != META)
        except (OSError, ValueError, KeyError, StopIteration):
            continue
        out.append((entry, item, meta.get("from", item.name), when))
    return out


def restore(entry):
    """Вернуть на место. Если имя уже занято - рядом, с пометкой «(из корзины)». Возвращает путь."""
    item = next(p for p in entry.iterdir() if p.name != META)
    meta = json.loads((entry / META).read_text(encoding="utf-8"))
    target = C.ROOT / meta.get("from", item.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        stem, suffix = (target.name, "") if item.is_dir() else (target.stem, target.suffix)
        target = unique_path(target.with_name(f"{stem} (из корзины){suffix}"))
    os.replace(item, target)
    shutil.rmtree(entry, ignore_errors=True)
    if target.parent != C.ROOT:
        append_to_order(target.parent, target.name)
    else:
        append_to_order(C.ROOT, target.name)
    return target


def forget(entry):
    shutil.rmtree(entry, ignore_errors=True)


def purge_old(days=DAYS, now=None):
    """Чистка: всё, что лежит дольше срока, удаляется насовсем. Возвращает, сколько удалено."""
    now = now or datetime.now()
    removed = 0
    for entry, _item, _origin, when in trash_entries():
        if now - when > timedelta(days=days):
            try:
                shutil.rmtree(entry)
                removed += 1
            except OSError as error:
                log_error("Корзина не почистилась", error)
    return removed


def age_label(when, now=None):
    days = ((now or datetime.now()) - when).days
    left = max(0, DAYS - days)
    ago = "сегодня" if days == 0 else "вчера" if days == 1 else f"{days} {plural(days, 'день', 'дня', 'дней')} назад"
    return f"удалено {ago}, исчезнет через {left} {plural(left, 'день', 'дня', 'дней')}"


class TrashDialog(Sheet):
    def __init__(self, parent, on_restored):
        super().__init__(parent, "Корзина")
        self.setMinimumSize(780, 460)
        self.on_restored = on_restored
        hint = QLabel(f"Удалённое лежит здесь {DAYS} дней, потом исчезает само. Вернулась глава - "
                      "вернулись и её версии с заметками.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        self.listing = QListWidget()
        self.listing.itemDoubleClicked.connect(lambda _i: self._restore())
        self.content.addWidget(self.listing, 1)
        from .widgets import EmptyPicture
        self.empty_picture = EmptyPicture(self.listing)
        row = QHBoxLayout()
        self.empty = QPushButton("Очистить корзину")
        self.empty.clicked.connect(self._empty)
        self.forget = QPushButton("Удалить насовсем")
        self.forget.clicked.connect(self._forget)
        row.addWidget(self.empty)
        row.addWidget(self.forget)
        row.addStretch()
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        self.back = QPushButton("Вернуть")
        self.back.setObjectName("Primary")
        self.back.setDefault(True)
        self.back.clicked.connect(self._restore)
        row.addWidget(close)
        row.addWidget(self.back)
        self.content.addLayout(row)
        self.fill()

    def fill(self):
        self.listing.clear()
        for entry, item, origin, when in trash_entries():
            kind = "категория" if item.is_dir() else "глава"
            name = item.name if item.is_dir() else Path(item.name).stem
            where = Path(origin).parent.as_posix()
            place = f" из «{where}»" if where not in ("", ".") else ""
            line = QListWidgetItem(f"{name}   ·   {kind}{place}\n{age_label(when)}")
            line.setData(Qt.UserRole, str(entry))
            self.listing.addItem(line)
        has = self.listing.count() > 0
        if has:
            self.listing.setCurrentRow(0)
            self.empty_picture.hide()
        else:
            self.listing.addItem("Корзина пуста")
            self.listing.item(0).setFlags(Qt.NoItemFlags)
            self.empty_picture.show_picture("empty-trash")
        for button in (self.back, self.forget, self.empty):
            button.setEnabled(has)

    def _chosen(self):
        item = self.listing.currentItem()
        return Path(item.data(Qt.UserRole)) if item and item.data(Qt.UserRole) else None

    def _restore(self):
        entry = self._chosen()
        if entry is None:
            return
        try:
            target = restore(entry)
        except (OSError, StopIteration, ValueError) as error:
            log_error("Не вернулось из корзины", error)
            return
        self.fill()
        self.on_restored(target)

    def _forget(self):
        entry = self._chosen()
        if entry is None:
            return
        if ask_question(self, "Удалить насовсем", "Удалить насовсем? Вернуть будет нельзя.") != QMessageBox.Yes:
            return
        forget(entry)
        self.fill()

    def _empty(self):
        count = len(trash_entries())
        if ask_question(self, "Очистить корзину",
                        f"Удалить насовсем всё, что в корзине ({count})? Вернуть будет нельзя.") != QMessageBox.Yes:
            return
        for entry, *_rest in trash_entries():
            forget(entry)
        self.fill()
