# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""План книги: у каждой главы статус («Идея», «Черновик», «Правка», «Готово»), чей взгляд, год в истории,
пара строк о чём она и флажок «не в книгу». Слева у главы - цветная точка статуса; «План книги» (Ctrl+P) -
все главы таблицей со словами и итогом. Хранится в .stungkir/plan.json по пути главы; тексты не меняются."""

import math
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QStyledItemDelegate, QTreeWidget,
    QTreeWidgetItem,
)

from . import config as C
from .dialogs import Sheet, ask_text
from .lore import age_label
from .storage import LockedFile, files_in, read_text, save_order, save_plan
from .style import rounded_menu
from .textutil import WORD_RE, is_prose, is_timeline, plural
from .timeline import load_events, year_label

STATUSES = [("idea", "Идея"), ("draft", "Черновик"), ("edit", "Правка"), ("done", "Готово")]
STATUS_NAMES = dict(STATUSES)
STATUS_ROLE = Qt.UserRole + 1        # код статуса у главы в дереве слева


def status_color(code):
    """Цвет точки статуса - из темы, кроме «Готово»: оно всегда спокойно-зелёное."""
    return QColor({"idea": C.DIM, "draft": C.MARKER, "edit": C.DIALOGUE, "done": "#6fb97c"}.get(code, C.DIM))


def thousands(n):
    return f"{n:,}".replace(",", " ")


def parse_year(text):
    """Год главы из того, что написал человек: «1203», «-40», «1203,5». Не число - None."""
    try:
        value = float(str(text).strip().replace(",", ".").replace("−", "-"))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def plan_summary(rows, plan, key):
    """Итог по главам [(путь, слов)]: «Готово 3 из 12 · в правке 2 · …» и всего слов.
    Главы «не в книгу» не считаются, только упоминаются в конце."""
    counts = {code: 0 for code, _name in STATUSES}
    book = [(path, words) for path, words in rows if not plan.get(key(path), {}).get("skip")]
    for path, _words in book:
        code = plan.get(key(path), {}).get("status")
        if code in counts:
            counts[code] += 1
    total = sum(words for _path, words in book)
    parts = [f"Готово {counts['done']} из {len(book)} {plural(len(book), 'главы', 'глав', 'глав')}"]
    for code, label in (("edit", "в правке"), ("draft", "в черновике"), ("idea", "в идеях")):
        if counts[code]:
            parts.append(f"{label} {counts[code]}")
    parts.append(f"{thousands(total)} {plural(total, 'слово', 'слова', 'слов')}")
    if len(book) < len(rows):
        parts.append(f"не в книгу {len(rows) - len(book)}")
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
    """Все главы книги: статус, чей взгляд, год, слова, о чём. Щелчок по статусу или взгляду - выбрать;
    двойной по году или «о чём» - написать; по названию - открыть главу; перетаскивание - порядок глав."""

    NAME, STATUS, POV, YEAR, WORDS, ABOUT = range(6)

    def __init__(self, parent, chapters, plan, key, on_change, on_order, people=(), years=None, born=None):
        super().__init__(parent, "План книги")
        self.setMinimumSize(980, 580)
        self.chapters = chapters          # [(папка, [(путь, слов)])]
        self.plan, self.key = plan, key
        self.on_change, self.on_order = on_change, on_order
        self.people = list(people)        # кого предложить в «Чей взгляд»
        self.years = years or {}          # год главы из хронологии, если в плане не написан
        self.born = born or {}            # имя -> год рождения
        self.open_target = None
        self._filling = False
        self.summary = QLabel()
        self.summary.setObjectName("Status")
        self.content.addWidget(self.summary)
        self.tree = PlanTree(self._moved)
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(["Глава", "Статус", "Чей взгляд", "Год", "Слов", "О чём"])
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.itemClicked.connect(self._clicked)
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        self.tree.itemChanged.connect(self._changed)
        header = self.tree.header()
        header.setStretchLastSection(True)
        for column in (self.NAME, self.STATUS, self.POV, self.YEAR, self.WORDS):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.content.addWidget(self.tree, 1)
        hint = QLabel("Щелчок по статусу или «Чей взгляд» - выбрать. Двойной щелчок по году или «О чём» - "
                      "написать, по названию - открыть главу. Перетащи главу, чтобы поменять порядок. "
                      "Год главы - в летоисчислении книги; без него возраст героев не посчитать.")
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

    def entry(self, path):
        return self.plan.get(self.key(path), {})

    def year_of(self, path):
        """(год, написан ли в плане): из плана, иначе из хронологии."""
        own = parse_year(self.entry(path).get("year", ""))
        if own is not None:
            return own, True
        return self.years.get(self.key(path)), False

    def fill(self):
        self._filling = True
        self.tree.clear()
        bold = QFont(self.tree.font())
        bold.setBold(True)
        for folder, rows in self.chapters:
            words = sum(w for p, w in rows if not self.entry(p).get("skip"))
            top = QTreeWidgetItem([folder.name, "", "", "", thousands(words), ""])
            top.setData(0, Qt.UserRole, str(folder))
            top.setFont(0, bold)
            top.setFlags(Qt.ItemIsEnabled | Qt.ItemIsDropEnabled)
            top.setTextAlignment(self.WORDS, Qt.AlignRight | Qt.AlignVCenter)
            self.tree.addTopLevelItem(top)
            for path, words in rows:
                top.addChild(self._row(path, words))
            top.setExpanded(True)
        self.summary.setText(plan_summary(self.rows(), self.plan, self.key))
        self._filling = False

    def _row(self, path, words):
        entry = self.entry(path)
        code, pov = entry.get("status"), entry.get("pov", "")
        year, own = self.year_of(path)
        pov_text = pov
        if pov and year is not None and self.born.get(pov) is not None:
            pov_text = f"{pov} ({age_label(year - self.born[pov])})"
        item = QTreeWidgetItem([path.stem, STATUS_NAMES.get(code, "-"), pov_text or "-",
                                "" if year is None else year_label(year), thousands(words), entry.get("about", "")])
        item.setData(0, Qt.UserRole, str(path))
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsEditable)
        item.setForeground(self.STATUS, status_color(code) if code else QColor(C.DIM))
        if not pov:
            item.setForeground(self.POV, QColor(C.DIM))
        if year is not None and not own:
            item.setForeground(self.YEAR, QColor(C.DIM))
            item.setToolTip(self.YEAR, "Из хронологии: событие, связанное с этой главой")
        item.setTextAlignment(self.WORDS, Qt.AlignRight | Qt.AlignVCenter)
        item.setTextAlignment(self.YEAR, Qt.AlignRight | Qt.AlignVCenter)
        item.setToolTip(self.ABOUT, entry.get("about", ""))
        if entry.get("skip"):
            italic = QFont(self.tree.font())
            italic.setItalic(True)
            item.setFont(self.NAME, italic)
            item.setForeground(self.NAME, QColor(C.DIM))
            item.setToolTip(self.NAME, "Не в книгу: при сборке эта глава не отмечена")
        return item

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
        if item.parent() is None or column not in (self.STATUS, self.POV):
            return
        menu = self.status_menu(item) if column == self.STATUS else self.pov_menu(item)
        menu.exec(self.tree.viewport().mapToGlobal(self.tree.visualItemRect(item).bottomLeft()))

    def status_menu(self, item):
        menu = rounded_menu(self)
        path = self.path_of(item)
        current = self.entry(path).get("status")
        for code, label in STATUSES + [(None, "Без статуса")]:
            # первым Qt может передать «отмечено ли» - его в _c, чтобы не попал в код статуса
            action = menu.addAction(label, lambda _c=False, c=code: self.choose(path, "status", c))
            action.setCheckable(True)
            action.setChecked(code == current)
        menu.addSeparator()
        skip = menu.addAction("Не в книгу", lambda _c=False: self.choose(path, "skip", "" if self.entry(path).get(
            "skip") else "yes"))
        skip.setCheckable(True)
        skip.setChecked(bool(self.entry(path).get("skip")))
        return menu

    def pov_menu(self, item):
        menu = rounded_menu(self)
        path = self.path_of(item)
        current = self.entry(path).get("pov", "")
        names = list(dict.fromkeys(self.people + ([current] if current else [])))
        for name in names:
            action = menu.addAction(name, lambda _c=False, n=name: self.choose(path, "pov", n))
            action.setCheckable(True)
            action.setChecked(name == current)
        if names:
            menu.addSeparator()
        menu.addAction("Другое имя…", lambda: self.ask_pov(path))
        menu.addAction("Ничей", lambda: self.choose(path, "pov", ""))
        return menu

    def ask_pov(self, path):
        name, ok = ask_text(self, "Чей взгляд", f"От чьего лица «{path.stem}»:", self.entry(path).get("pov", ""))
        if ok:
            self.choose(path, "pov", " ".join(name.split()))

    def choose(self, path, field, value):
        self._set(path, field, value)
        self.fill()

    def _double_clicked(self, item, column):
        if item.parent() is None:
            return
        if column == self.ABOUT:
            self.tree.editItem(item, self.ABOUT)
        elif column == self.YEAR:
            if not self.year_of(self.path_of(item))[1]:
                self._filling = True
                item.setText(self.YEAR, "")              # год из хронологии - подсказка, а не то, что пишут
                self._filling = False
            self.tree.editItem(item, self.YEAR)
        elif column == self.NAME:
            self.open_target = self.path_of(item)
            self.accept()

    def _changed(self, item, column):
        if self._filling or item.parent() is None:
            return
        path = self.path_of(item)
        if column == self.ABOUT:
            self._set(path, "about", " ".join(item.text(self.ABOUT).split()))
            self.summary.setText(plan_summary(self.rows(), self.plan, self.key))
        elif column == self.YEAR:
            text = item.text(self.YEAR).strip()
            year = parse_year(text)
            if text and year is None:
                QTimer.singleShot(0, self, self.fill)      # не число - вернуть как было
                return
            self._set(path, "year", "" if year is None else year_label(year))
            QTimer.singleShot(0, self, self.fill)          # возраст во «Чей взгляд» пересчитается

    def _moved(self, source, target, where):
        """Глава встала выше или ниже другой главы той же категории; брошена на название категории - в конец,
        над ним - в начало."""
        folder = source.parent()
        if target.parent() is None:
            if target is not folder:
                return
            index = folder.childCount() if where == QAbstractItemView.OnItem else 0
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
    """Статусы глав, «не в книгу», чей взгляд, год главы и «План книги». Часть главного окна."""

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
        """Пункты для главы в правом клике слева: статус, чей взгляд, «не в книгу», год, «о чём»."""
        entry = self.chapter_plan(path)
        statuses = self._submenu(menu, "Статус")
        for code, label in STATUSES + [(None, "Без статуса")]:
            self._toggle(statuses, label, lambda _c=False, c=code: self.plan_set(path, "status", c),
                         code == entry.get("status"))
        pov = self._submenu(menu, "Чей взгляд")
        for name in dict.fromkeys(self.plan_people() + ([entry["pov"]] if entry.get("pov") else [])):
            self._toggle(pov, name, lambda _c=False, n=name: self.plan_set(path, "pov", n), name == entry.get("pov"))
        pov.addSeparator()
        pov.addAction("Другое имя…", lambda: self.ask_plan_field(path, "pov"))
        pov.addAction("Ничей", lambda: self.plan_set(path, "pov", ""))
        self._toggle(menu, "Не в книгу", lambda _c=False: self.plan_set(
            path, "skip", "" if self.chapter_plan(path).get("skip") else "yes"), bool(entry.get("skip")))
        menu.addAction("Год главы…", lambda: self.ask_plan_field(path, "year"))
        menu.addAction("О чём глава…", lambda: self.ask_plan_field(path, "about"))

    def edit_chapter_about(self, path):
        self.ask_plan_field(path, "about")

    def ask_plan_field(self, path, field):
        title, label = {
            "about": ("О чём глава", f"Коротко, о чём «{path.stem}» (пусто - убрать):"),
            "pov": ("Чей взгляд", f"От чьего лица «{path.stem}»:"),
            "year": ("Год главы", f"В каком году истории идёт «{path.stem}» (в летоисчислении книги; "
                                  "пусто - убрать):"),
        }[field]
        text, ok = ask_text(self, title, label, self.chapter_plan(path).get(field, ""))
        if not ok:
            return
        value = " ".join(text.split())
        if field == "year" and value:
            year = parse_year(value)
            if year is None:
                self.toast.show_message("Год - это число, например 1203 или -40")
                return
            value = year_label(year)
        self.plan_set(path, field, value)

    def plan_people(self):
        """Кого предлагать в «Чей взгляд»: персонажи из списка и те, у кого в справочнике есть год рождения."""
        born = [t.name for t in self.lore.terms if getattr(t, "born", None) is not None]
        return list(dict.fromkeys(list(self.names) + born))

    def plan_categories(self):
        return [f for f in self.categories() if f.name not in self.lore_cfg["categories"]]

    def timeline_years(self):
        """{глава: год} из хронологий: год самого раннего события, связанного с главой."""
        years = {}
        for folder in self.categories():
            for path in files_in(folder):
                if not is_timeline(path):
                    continue
                try:
                    events = load_events(read_text(path))
                except (OSError, LockedFile):
                    continue
                for event in events:
                    chapter, year = event.get("chapter"), parse_year(event.get("year", ""))
                    if isinstance(chapter, str) and chapter and year is not None:
                        years[chapter] = min(year, years.get(chapter, year))
        return years

    def story_year(self, path):
        """В каком году истории идёт глава: из плана, иначе из хронологии; неизвестно - None."""
        own = parse_year(self.chapter_plan(path).get("year", ""))
        return own if own is not None else self.timeline_years().get(self._position_key(path))

    def skipped_chapters(self):
        return {C.ROOT / key for key, entry in self.plan.items() if entry.get("skip")}

    def mark_tree_status(self):
        """Точки статуса у глав слева, бледные «не в книгу» и подсказка: статус, взгляд, год, о чём."""
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
                child.setData(0, Qt.ForegroundRole, QColor(C.DIM) if entry.get("skip") else None)
                tip = [STATUS_NAMES.get(code, ""), entry.get("pov", ""), entry.get("year", "") and
                       f"год {entry['year']}", "не в книгу" if entry.get("skip") else "", entry.get("about", "")]
                child.setToolTip(0, " · ".join(x for x in tip if x))

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

        self.rebuild_lore()
        born = {t.name: t.born for t in self.lore.terms if getattr(t, "born", None) is not None}
        dialog = PlanDialog(self, self.plan_chapters(), self.plan, self._position_key,
                            lambda: (save_plan(self.plan), self.mark_tree_status()), reorder,
                            self.plan_people(), self.timeline_years(), born)
        dialog.exec()
        if dialog.open_target is not None:
            self.open_path(dialog.open_target)
