# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""План книги: у каждой главы статус («Идея», «Черновик», «Правка», «Готово») и пара строк о чём она.
Слева у главы - цветная точка статуса; «План книги» (Ctrl+P) - все главы таблицей со словами и итогом.
Хранится в .stungkir/plan.json по пути главы; сами тексты не меняются."""

from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QStyledItemDelegate, QTreeWidget,
    QTreeWidgetItem,
)

from . import config as C
from .dialogs import Sheet, ask_text
from .storage import LockedFile, files_in, read_text, save_order, save_plan
from .style import rounded_menu
from .textutil import WORD_RE, is_prose, plural

STATUSES = [("idea", "Идея"), ("draft", "Черновик"), ("edit", "Правка"), ("done", "Готово")]
STATUS_NAMES = dict(STATUSES)
STATUS_ROLE = Qt.UserRole + 1        # код статуса у главы в дереве слева


def status_color(code):
    """Цвет точки статуса - из темы, кроме «Готово»: оно всегда спокойно-зелёное."""
    return QColor({"idea": C.DIM, "draft": C.MARKER, "edit": C.DIALOGUE, "done": "#6fb97c"}.get(code, C.DIM))


def thousands(n):
    return f"{n:,}".replace(",", " ")


def plan_summary(rows, plan, key):
    """Итог по главам [(путь, слов)]: «Готово 3 из 12 · в правке 2 · …» и всего слов."""
    counts = {code: 0 for code, _name in STATUSES}
    for path, _words in rows:
        code = plan.get(key(path), {}).get("status")
        if code in counts:
            counts[code] += 1
    total = sum(words for _path, words in rows)
    parts = [f"Готово {counts['done']} из {len(rows)} {plural(len(rows), 'главы', 'глав', 'глав')}"]
    for code, label in (("edit", "в правке"), ("draft", "в черновике"), ("idea", "в идеях")):
        if counts[code]:
            parts.append(f"{label} {counts[code]}")
    parts.append(f"{thousands(total)} {plural(total, 'слово', 'слова', 'слов')}")
    return " · ".join(parts)


class StatusDelegate(QStyledItemDelegate):
    """Глава в дереве слева: справа от названия - цветная точка статуса."""

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        code = index.data(STATUS_ROLE)
        if not code:
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(status_color(code))
        rect = option.rect
        painter.drawEllipse(QPointF(rect.right() - 10, rect.center().y() + 0.5), 3.5, 3.5)
        painter.restore()


class PlanTree(QTreeWidget):
    """Главы по категориям. Перетаскивание - только внутри своей категории: это порядок глав."""

    def __init__(self, on_move):
        super().__init__()
        self.on_move = on_move
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event):
        source = self.currentItem()
        target = self.itemAt(event.position().toPoint())
        where = self.dropIndicatorPosition()
        event.setDropAction(Qt.IgnoreAction)      # двигаем сами и перерисовываем
        event.accept()
        if source is None or target is None or source is target or source.parent() is None:
            return
        QTimer.singleShot(0, self, lambda: self.on_move(source, target, where))


class PlanDialog(Sheet):
    """Все главы книги: статус, слова, о чём. Статус - щелчок по нему; «о чём» - двойной щелчок;
    двойной щелчок по названию открывает главу; перетаскивание меняет порядок глав."""

    NAME, STATUS, WORDS, ABOUT = range(4)

    def __init__(self, parent, chapters, plan, key, on_change, on_order):
        super().__init__(parent, "План книги")
        self.setMinimumSize(860, 560)
        self.chapters = chapters          # [(папка, [(путь, слов)])]
        self.plan, self.key = plan, key
        self.on_change, self.on_order = on_change, on_order
        self.open_target = None
        self._filling = False
        self.summary = QLabel()
        self.summary.setObjectName("Status")
        self.content.addWidget(self.summary)
        self.tree = PlanTree(self._moved)
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Глава", "Статус", "Слов", "О чём"])
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.itemClicked.connect(self._clicked)
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        self.tree.itemChanged.connect(self._changed)
        header = self.tree.header()
        header.setStretchLastSection(True)
        for column in (self.NAME, self.STATUS, self.WORDS):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.content.addWidget(self.tree, 1)
        hint = QLabel("Щелчок по статусу - сменить его. Двойной щелчок по «О чём» - написать, по названию - "
                      "открыть главу. Перетащи главу выше или ниже, чтобы поменять порядок.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close)
        self.content.addLayout(buttons)
        self.fill()

    def rows(self):
        return [row for _folder, rows in self.chapters for row in rows]

    def fill(self):
        self._filling = True
        self.tree.clear()
        bold = QFont(self.tree.font())
        bold.setBold(True)
        for folder, rows in self.chapters:
            top = QTreeWidgetItem([folder.name, "", thousands(sum(w for _p, w in rows)), ""])
            top.setData(0, Qt.UserRole, str(folder))
            top.setFont(0, bold)
            top.setFlags(Qt.ItemIsEnabled | Qt.ItemIsDropEnabled)
            top.setTextAlignment(self.WORDS, Qt.AlignRight | Qt.AlignVCenter)
            self.tree.addTopLevelItem(top)
            for path, words in rows:
                entry = self.plan.get(self.key(path), {})
                code = entry.get("status")
                item = QTreeWidgetItem([path.stem, STATUS_NAMES.get(code, "-"), thousands(words),
                                        entry.get("about", "")])
                item.setData(0, Qt.UserRole, str(path))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsEditable)
                item.setForeground(self.STATUS, status_color(code) if code else QColor(C.DIM))
                item.setTextAlignment(self.WORDS, Qt.AlignRight | Qt.AlignVCenter)
                item.setToolTip(self.ABOUT, entry.get("about", ""))
                top.addChild(item)
            top.setExpanded(True)
        self.summary.setText(plan_summary(self.rows(), self.plan, self.key))
        self._filling = False

    @staticmethod
    def path_of(item):
        return Path(item.data(0, Qt.UserRole))

    def _set(self, path, field, value):
        key = self.key(path)
        entry = dict(self.plan.get(key, {}))
        if value:
            entry[field] = value
        else:
            entry.pop(field, None)
        if entry:
            self.plan[key] = entry
        else:
            self.plan.pop(key, None)
        self.on_change()

    def _clicked(self, item, column):
        if item.parent() is None or column != self.STATUS:
            return
        menu = self.status_menu(item)
        menu.exec(self.tree.viewport().mapToGlobal(self.tree.visualItemRect(item).bottomLeft()))

    def status_menu(self, item):
        menu = rounded_menu(self)
        current = self.plan.get(self.key(self.path_of(item)), {}).get("status")
        path = self.path_of(item)
        for code, label in STATUSES + [(None, "Без статуса")]:
            # первым Qt передаёт «отмечено ли» - его в _c, иначе он попал бы в код статуса
            action = menu.addAction(label, lambda _c=False, c=code: self.choose_status(path, c))
            action.setCheckable(True)
            action.setChecked(code == current)
        return menu

    def choose_status(self, path, code):
        self._set(path, "status", code)
        self.fill()

    def _double_clicked(self, item, column):
        if item.parent() is None:
            return
        if column == self.ABOUT:
            self.tree.editItem(item, self.ABOUT)
        elif column == self.NAME:
            self.open_target = self.path_of(item)
            self.accept()

    def _changed(self, item, column):
        if self._filling or column != self.ABOUT or item.parent() is None:
            return
        about = " ".join(item.text(self.ABOUT).split())
        self._set(self.path_of(item), "about", about)
        self.summary.setText(plan_summary(self.rows(), self.plan, self.key))

    def _moved(self, source, target, where):
        """Глава встала выше или ниже другой главы той же категории; брошена на название категории - в конец,
        над ним - в начало."""
        folder = source.parent()
        if target.parent() is None:
            if target is not folder:
                return
            index = folder.childCount() if where == QAbstractItemView.OnItem else 0    # на категорию - в конец
        elif target.parent() is folder:
            index = folder.indexOfChild(target)
            if where == QAbstractItemView.BelowItem:
                index += 1
        else:
            return
        old = folder.indexOfChild(source)
        if index > old:
            index -= 1
        if index == old:
            return
        for path, rows in self.chapters:
            if str(path) == folder.data(0, Qt.UserRole):
                rows.insert(index, rows.pop(old))
                self.on_order(path, [p.name for p, _w in rows])
                break
        self.fill()


class PlanMixin:
    """Статусы глав и «План книги». Часть главного окна."""

    def chapter_plan(self, path):
        return self.plan.get(self._position_key(path), {})

    def plan_set(self, path, field, value):
        key = self._position_key(path)
        entry = dict(self.plan.get(key, {}))
        if value:
            entry[field] = value
        else:
            entry.pop(field, None)
        if entry:
            self.plan[key] = entry
        else:
            self.plan.pop(key, None)
        save_plan(self.plan)
        self.mark_tree_status()

    def plan_menu(self, menu, path):
        """Пункты для главы в правом клике слева: статус и «о чём»."""
        statuses = self._submenu(menu, "Статус")
        current = self.chapter_plan(path).get("status")
        for code, label in STATUSES + [(None, "Без статуса")]:
            self._toggle(statuses, label, lambda _c=False, c=code: self.plan_set(path, "status", c), code == current)
        menu.addAction("О чём глава…", lambda: self.edit_chapter_about(path))

    def edit_chapter_about(self, path):
        text, ok = ask_text(self, "О чём глава", f"Коротко, о чём «{path.stem}» (пусто - убрать):",
                            self.chapter_plan(path).get("about", ""))
        if ok:
            self.plan_set(path, "about", " ".join(text.split()))

    def plan_categories(self):
        return [f for f in self.categories() if f.name not in self.lore_cfg["categories"]]

    def mark_tree_status(self):
        """Точки статуса у глав слева и подсказка с «о чём»."""
        planned = {str(f) for f in self.plan_categories()}
        for i in range(self.tree.topLevelItemCount()):
            folder = self.tree.topLevelItem(i)
            in_plan = folder.data(0, Qt.UserRole) in planned
            for j in range(folder.childCount()):
                child = folder.child(j)
                path = self.item_path(child)
                if not in_plan or child.toolTip(0) and child.data(0, STATUS_ROLE) is None or not is_prose(path):
                    continue        # не глава книги или особый файл со своей подсказкой (конфликт, не текст)
                entry = self.chapter_plan(path)
                code = entry.get("status")
                child.setData(0, STATUS_ROLE, code or "")
                child.setToolTip(0, " · ".join(x for x in (STATUS_NAMES.get(code, ""), entry.get("about", "")) if x))

    def plan_chapters(self):
        """[(категория, [(глава, слов)])] - без справочников мира, таблиц, досок и хронологий."""
        chapters = []
        for folder in self.plan_categories():
            rows = []
            for path in files_in(folder):
                if not is_prose(path):
                    continue
                if path == self.path and self.view is None:
                    text = self.current_text()
                else:
                    try:
                        text = read_text(path)
                    except (OSError, LockedFile):
                        text = ""
                rows.append((path, len(WORD_RE.findall(text))))
            chapters.append((folder, rows))
        return chapters

    def show_plan(self):
        def reorder(folder, names):
            save_order(folder, names)
            self.refresh_tree()

        dialog = PlanDialog(self, self.plan_chapters(), self.plan, self._position_key,
                            lambda: (save_plan(self.plan), self.mark_tree_status()), reorder)
        dialog.exec()
        if dialog.open_target is not None:
            self.open_path(dialog.open_target)
