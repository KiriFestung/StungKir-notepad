# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Доска сюжета с карточками."""

import json
from pathlib import Path
from PySide6.QtCore import QMimeData, QPoint, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QDrag, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QStyle,
    QStackedWidget, QStyledItemDelegate, QVBoxLayout, QWidget,
)

COLUMN_MIME = "application/x-stungkir-column"

from ..core import config as C
from ..ui.style import frameless_menu, rounded_menu
from ..ui.dialogs import Sheet, ask_question, ask_text
from ..ui.widgets import RussianLineEdit, RussianTextEdit
from .corkboard import FreeBoard, card_id
from ..core.i18n import tr


class CardDialog(Sheet):
    """Карточка сцены: название, описание, цвет, связанная глава."""

    def __init__(self, parent, card, chapters, on_foreign, existing):
        super().__init__(parent, tr("Карточка сцены"))
        self.setMinimumSize(480, 420)
        self.deleted = False
        layout = self.content
        self.title = RussianLineEdit(on_foreign)
        self.title.setPlaceholderText(tr("Название сцены"))
        self.title.setText(card.get("title", ""))
        layout.addWidget(self.title)
        self.text = RussianTextEdit(on_foreign)
        self.text.setPlaceholderText(tr("Что происходит в сцене…"))
        self.text.setPlainText(card.get("text", ""))
        layout.addWidget(self.text, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Цвет:")))
        self.swatches = []
        for name, color in C.CARD_COLORS:
            swatch = QPushButton("")
            swatch.setObjectName("Swatch")
            swatch.setCheckable(True)
            swatch.setAutoExclusive(True)
            swatch.setStyleSheet(f"background: {color};")
            swatch.setChecked(card.get("color", "none") == name)
            swatch.setProperty("color_name", name)
            row.addWidget(swatch)
            self.swatches.append(swatch)
        row.addStretch()
        layout.addLayout(row)
        self.chapter = QComboBox()
        self.chapter.addItem("Без главы", "")
        for key in chapters:
            self.chapter.addItem(key.replace("/", " · ").removesuffix(".txt"), key)
        index = self.chapter.findData(card.get("chapter", ""))
        self.chapter.setCurrentIndex(max(0, index))
        layout.addWidget(self.chapter)
        buttons = QHBoxLayout()
        if existing:
            delete = QPushButton(tr("Удалить карточку"))
            delete.clicked.connect(self._delete)
            buttons.addWidget(delete)
        buttons.addStretch()
        cancel = QPushButton(tr("Отмена"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("Готово"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)
        self.title.setFocus()

    def _delete(self):
        self.deleted = True
        self.accept()

    def card_data(self):
        color = next((s.property("color_name") for s in self.swatches if s.isChecked()), "none")
        return {"title": self.title.text().strip(), "text": self.text.toPlainText().strip(),
                "color": color, "chapter": self.chapter.currentData() or ""}


class CardDelegate(QStyledItemDelegate):
    """Рисует карточку: цветная полоска, название, начало описания, связанная глава."""

    def sizeHint(self, option, index):
        return QSize(max(option.rect.width(), 200), 92)

    def paint(self, painter, option, index):
        card = json.loads(index.data(Qt.UserRole) or "{}")
        rect = QRectF(option.rect).adjusted(4, 4, -4, -4)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        selected = option.state & QStyle.State_Selected
        hovered = option.state & QStyle.State_MouseOver
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(C.SELECT if selected else (C.HOVER if hovered else C.PANEL)))
        painter.drawRoundedRect(rect, 10, 10)
        color = dict(C.CARD_COLORS).get(card.get("color", "none"), C.BORDER)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(QRectF(rect.left(), rect.top(), 5, rect.height()), 2.5, 2.5)
        title_font = QFont(C.FONT_FAMILY, 10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor(C.TEXT))
        title = card.get("title") or "Без названия"
        title = painter.fontMetrics().elidedText(title, Qt.ElideRight, int(rect.width() - 22))
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 8, rect.width() - 22, 20),
                         Qt.AlignLeft | Qt.AlignVCenter, title)
        small = QFont(C.FONT_FAMILY, 9)
        painter.setFont(small)
        painter.setPen(QColor(C.DIM))
        bottom = 22 if card.get("chapter") else 8
        painter.drawText(QRectF(rect.left() + 14, rect.top() + 30, rect.width() - 22,
                                rect.height() - 30 - bottom),
                         Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, card.get("text", "")[:220])
        if card.get("chapter"):
            painter.setPen(QColor(C.DIALOGUE))
            label = "→ " + Path(card["chapter"]).stem
            label = painter.fontMetrics().elidedText(label, Qt.ElideRight, int(rect.width() - 22))
            painter.drawText(QRectF(rect.left() + 14, rect.bottom() - 20, rect.width() - 22, 16),
                             Qt.AlignLeft | Qt.AlignVCenter, label)
        painter.restore()


class CardList(QListWidget):
    """Список карточек колонки. Двойной клик по пустому месту - новая карточка;
    колонку, которую тащат за заголовок, можно бросить и сюда."""

    def __init__(self, column):
        super().__init__()
        self.column = column

    def mouseDoubleClickEvent(self, event):
        if self.itemAt(event.position().toPoint()) is None:
            self.column.board.new_card(self.column)
            return
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            self.column.board.column_dragged_to(self.mapTo(self.column.board.holder, event.position().toPoint()))
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class ColumnHeader(QWidget):
    """Заголовок колонки: за него колонку перетаскивают, двойной клик - переименовать."""

    def __init__(self, column):
        super().__init__()
        self.column = column
        self._press = None
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(tr("Перетащи, чтобы поменять колонки местами. Двойной клик - переименовать"))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self._press is None or not event.buttons() & Qt.LeftButton:
            return
        if (event.position().toPoint() - self._press).manhattanLength() >= QApplication.startDragDistance():
            self._press = None
            self.column.board.drag_column(self.column)

    def mouseReleaseEvent(self, _event):
        self._press = None

    def mouseDoubleClickEvent(self, _event):
        self._press = None
        self.column.board.rename_column(self.column)


class BoardColumn(QFrame):
    def __init__(self, board, title):
        super().__init__()
        self.board = board
        self.setObjectName("Column")
        self.setFixedWidth(270)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        self.header = ColumnHeader(self)
        top = QHBoxLayout(self.header)
        top.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel(title)
        self.title.setObjectName("Title")
        self.title.setAttribute(Qt.WA_TransparentForMouseEvents)   # клики уходят заголовку
        top.addWidget(self.title, 1)
        add = QPushButton("+")
        add.setToolTip(tr("Новая карточка"))
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(lambda: self.board.new_card(self))
        top.addWidget(add)
        more = QPushButton("⋯")
        more.setCursor(Qt.PointingHandCursor)
        more.clicked.connect(lambda: self.board.column_menu(self, more))
        top.addWidget(more)
        layout.addWidget(self.header)
        self.list = CardList(self)
        self.list.setItemDelegate(CardDelegate(self.list))
        self.list.setDragDropMode(QAbstractItemView.DragDrop)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setDropIndicatorShown(True)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setMouseTracking(True)
        self.list.itemDoubleClicked.connect(lambda item: self.board.edit_card(self, item))
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(lambda pos: self.board.card_menu(self, pos))
        model = self.list.model()
        for signal in (model.rowsInserted, model.rowsRemoved, model.rowsMoved, model.dataChanged):
            signal.connect(lambda *_: self.board.changed())
        layout.addWidget(self.list, 1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            self.board.column_dragged_to(self.mapTo(self.board.holder, event.position().toPoint()))
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()

    def cards(self):
        return [json.loads(self.list.item(i).data(Qt.UserRole) or "{}") for i in range(self.list.count())]

    def add_card(self, card, row=None):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, json.dumps(card, ensure_ascii=False))
        item.setSizeHint(QSize(240, 92))
        if row is None:
            self.list.addItem(item)
        else:
            self.list.insertItem(row, item)
        return item


class BoardHolder(QWidget):
    """Полотно под колонками: принимает перетаскиваемую колонку и на пустом месте справа."""

    def __init__(self, board):
        super().__init__()
        self.board = board
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            self.board.column_dragged_to(event.position().toPoint())
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()


class BoardView(QWidget):
    """Доска сюжета: колонки с карточками сцен, их можно перетаскивать мышкой."""

    def __init__(self, on_change, on_foreign, toast, chapters, open_chapter):
        super().__init__()
        self.setObjectName("Board")
        self.on_change = on_change
        self.on_foreign = on_foreign
        self.toast = toast
        self.chapters = chapters          # функция: список глав для привязки
        self.open_chapter = open_chapter
        self.modified = False
        self._loading = False
        self.columns = []
        self._found = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 6)
        layout.setSpacing(10)
        bar = QWidget()
        bar.setObjectName("TableBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        self.mode = "columns"
        self.links = []                   # нитки пробковой доски: [[id, id]]
        self.mode_buttons = {}
        for key, title, tip in (("columns", tr("Колонки"), tr("Карточки стопками по колонкам")),
                                ("free", tr("Пробка"), tr("Карточки лежат где угодно, их можно связать нитками"))):
            button = QPushButton(title)
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolTip(tip)
            button.setProperty("noIcon", True)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(f"QPushButton:checked {{ background: {C.IMPORTANT}; color: {C.on_color(C.IMPORTANT)}; }}")
            button.clicked.connect(lambda _c=False, k=key: self.set_mode(k))
            row.addWidget(button)
            self.mode_buttons[key] = button
        self.mode_buttons["columns"].setChecked(True)
        row.addSpacing(10)
        self.add_button = QPushButton(tr("+ колонка"))
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.add_column)
        row.addWidget(self.add_button)
        self.fit_button = QPushButton(tr("Вписать"))
        self.fit_button.setToolTip(tr("Показать все карточки целиком"))
        self.fit_button.setCursor(Qt.PointingHandCursor)
        self.fit_button.clicked.connect(lambda: self.free.fit())
        row.addWidget(self.fit_button)
        row.addSpacing(14)
        self.hint = QLabel("")
        self.hint.setObjectName("Status")
        row.addWidget(self.hint, 1)
        layout.addWidget(bar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        holder = BoardHolder(self)
        holder.setObjectName("Board")
        self.holder = holder
        self._dragged = None
        self.row = QHBoxLayout(holder)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(12)
        self.row.addStretch()
        self.scroll.setWidget(holder)
        self.free = FreeBoard()
        self.free.edit_requested.connect(self.edit_free_card)
        self.free.new_requested.connect(self.new_free_card)
        self.free.changed.connect(self.changed)
        self.free.menu_callback = self.free_menu
        self.pages = QStackedWidget()
        self.pages.addWidget(self.scroll)
        self.pages.addWidget(self.free)
        layout.addWidget(self.pages, 1)
        self._show_mode()

    # ---- данные ----
    def load(self, text):
        try:
            data = json.loads(text) if text.strip() else {}
        except ValueError:
            data = {}
        columns = data.get("columns") or [{"title": t, "cards": []} for t in C.BOARD_COLUMNS]
        self.links = [pair for pair in data.get("links", []) if isinstance(pair, list) and len(pair) == 2]
        mode = data.get("mode") if data.get("mode") in ("columns", "free") else "columns"
        self._loading = True
        for column in self.columns:
            column.setParent(None)
            column.deleteLater()
        self.columns = []
        for column in columns:
            widget = self._make_column(column.get("title", ""))
            for card in column.get("cards", []):
                card_id(card)
                widget.add_card(card)
        self._loading = False
        self.mode = mode
        self._enter_mode(fit=True)
        self.set_modified(False)

    def _make_column(self, title, index=None):
        column = BoardColumn(self, title)
        index = len(self.columns) if index is None else index
        self.columns.insert(index, column)
        self.row.insertWidget(index, column)
        return column

    def data(self):
        if self.mode == "free":
            self._sync_from_free()
        data = {"columns": [{"title": c.title.text(), "cards": c.cards()} for c in self.columns]}
        if self.mode == "free" or self.links:
            data["mode"] = self.mode
            data["links"] = self.free.link_pairs() if self.mode == "free" else self.links
        return data

    # ---- пробковая доска ----
    def set_mode(self, mode):
        if mode == self.mode:
            return
        if self.mode == "free":
            self._sync_from_free()
            self.links = self.free.link_pairs()
        self.mode = mode
        self._enter_mode(fit=True)
        self.changed()

    def _enter_mode(self, fit=False):
        if self.mode == "free":
            columns = [(c.title.text(), c.cards()) for c in self.columns]
            self.free.load(columns, self.links)
            if fit:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, self.free, self.free.fit)      # когда доска уже на экране
        self._show_mode()

    def _show_mode(self):
        free = self.mode == "free"
        self.mode_buttons[self.mode].setChecked(True)
        self.pages.setCurrentWidget(self.free if free else self.scroll)
        self.add_button.setVisible(not free)
        self.fit_button.setVisible(free)
        self.hint.setText(tr("двойной клик - карточка · правый клик - нитка, цвет · Ctrl+колесо - масштаб · "
                          "Shift+мышь - двигать") if free else
                          tr("двойной клик - новая карточка или изменить; карточки и колонки (за заголовок) "
                          "перетаскиваются мышкой"))

    def _sync_from_free(self):
        """Что поменялось на пробке (место, правки) - обратно в карточки колонок."""
        was, self._loading = self._loading, True
        try:
            for column in self.columns:
                for i in range(column.list.count()):
                    item = column.list.item(i)
                    card = json.loads(item.data(Qt.UserRole) or "{}")
                    placed = self.free.items_by_id.get(card.get("id"))
                    if placed is not None and placed.card != card:
                        item.setData(Qt.UserRole, json.dumps(placed.card, ensure_ascii=False))
        finally:
            self._loading = was

    def _list_item_of(self, card):
        for column in self.columns:
            for i in range(column.list.count()):
                item = column.list.item(i)
                if json.loads(item.data(Qt.UserRole) or "{}").get("id") == card.get("id"):
                    return column, item
        return None, None

    def edit_free_card(self, placed):
        dialog = CardDialog(self, placed.card, self.chapters(), self.on_foreign, existing=True)
        if not dialog.exec():
            return
        column, item = self._list_item_of(placed.card)
        if dialog.deleted:
            if column is not None:
                column.list.takeItem(column.list.row(item))
            self.free.remove_card_item(placed)
        else:
            placed.card.update(dialog.card_data())
            placed.update()
            if item is not None:
                item.setData(Qt.UserRole, json.dumps(placed.card, ensure_ascii=False))
        self.changed()

    def new_free_card(self, where):
        dialog = CardDialog(self, {}, self.chapters(), self.on_foreign, existing=False)
        if not dialog.exec():
            return
        card = dialog.card_data()
        if not (card["title"] or card["text"]):
            return
        if not self.columns:
            self._make_column(C.BOARD_COLUMNS[0] if C.BOARD_COLUMNS else "Сцены")
        column = self.columns[0]
        card_id(card)
        card["x"], card["y"] = round(where.x() - 105), round(where.y() - 20)
        column.add_card(card)
        self.free.add_card_item(card, column.title.text())
        self.changed()

    def free_menu(self, placed, where, global_pos):
        menu = rounded_menu(self)
        if placed is None:
            menu.addAction(tr("Новая карточка здесь"), lambda: self.new_free_card(where))
            menu.addAction(tr("Вписать всё"), self.free.fit)
        else:
            card = placed.card
            menu.addAction(tr("Изменить"), lambda: self.edit_free_card(placed))
            menu.addAction(tr("Протянуть нитку… (потом щёлкни другую карточку)"), lambda: self.free.start_link(placed))
            if any(placed in (l.first, l.second) for l in self.free.links):
                menu.addAction(tr("Убрать нитки"), lambda: self.free.remove_links(placed))
            if card.get("chapter"):
                menu.addAction(tr("Открыть главу"), lambda: self.open_chapter(card["chapter"]))
            colors = frameless_menu(menu.addMenu(tr("Цвет")))
            names = {"none": "Без цвета", "purple": "Фиолетовый", "amber": "Янтарный",
                     "green": "Зелёный", "coral": "Коралловый"}
            for name, _ in C.CARD_COLORS:
                colors.addAction(names[name], lambda n=name: self._free_color(placed, n))
            menu.addSeparator()
            menu.addAction(tr("Удалить"), lambda: self._free_delete(placed))
        menu.exec(global_pos)

    def _free_color(self, placed, color):
        placed.card["color"] = color
        placed.update()
        self._sync_from_free()
        self.changed()

    def _free_delete(self, placed):
        column, item = self._list_item_of(placed.card)
        if column is not None:
            column.list.takeItem(column.list.row(item))
        self.free.remove_card_item(placed)
        self.changed()

    def refresh_colors(self):
        self.free.refresh_colors()
        for button in self.mode_buttons.values():
            button.setStyleSheet(f"QPushButton:checked {{ background: {C.IMPORTANT}; color: {C.on_color(C.IMPORTANT)}; }}")

    def text(self):
        return json.dumps(self.data(), ensure_ascii=False, indent=1) + "\n"

    def words_text(self):
        parts = []
        for column in self.columns:
            for card in column.cards():
                parts += [card.get("title", ""), card.get("text", "")]
        return "\n".join(parts)

    def copy_text(self):
        lines = []
        for column in self.columns:
            lines.append(column.title.text())
            for card in column.cards():
                line = "  • " + (card.get("title") or "Без названия")
                if card.get("text"):
                    line += " - " + card["text"].replace("\n", " ")
                lines.append(line)
            lines.append("")
        return "\n".join(lines).strip() + "\n", "План доски скопирован текстом"

    def set_modified(self, value):
        self.modified = value
        self.on_change()

    def changed(self):
        if not self._loading:
            self.set_modified(True)

    def focus_widget(self):
        return self.columns[0].list if self.columns else self

    def kind(self):
        return "Доска"

    # ---- колонки ----
    def add_column(self, index=None):
        name, ok = ask_text(self, tr("Новая колонка"), tr("Название колонки:"))
        if ok:
            self._make_column(name.strip() or "Без названия", index)
            self.changed()

    def rename_column(self, column):
        name, ok = ask_text(self, tr("Колонка"), tr("Название колонки:"), text=column.title.text())
        if ok:
            column.title.setText(name.strip() or "Без названия")
            self.changed()

    def remove_column(self, column):
        if column.list.count():
            answer = ask_question(self, tr("Удалить колонку"),
                                          tr("Удалить колонку «{n}» вместе с карточками?").format(n=column.title.text()))
            if answer != QMessageBox.Yes:
                return
        self.columns.remove(column)
        column.setParent(None)
        column.deleteLater()
        self.changed()

    def move_column(self, column, step):
        target = self.columns.index(column) + step
        if 0 <= target < len(self.columns) and self._place_column(column, target):
            self.changed()

    def _place_column(self, column, target):
        index = self.columns.index(column)
        if target == index:
            return False
        self.columns.insert(target, self.columns.pop(index))
        self.row.removeWidget(column)
        self.row.insertWidget(target, column)
        return True

    def column_target(self, x, column):
        """Куда встанет перетаскиваемая колонка, если отпустить мышь на высоте x."""
        others = [c for c in self.columns if c is not column]
        return sum(1 for c in others if c.geometry().center().x() < x)

    def column_dragged_to(self, point):
        column = self._dragged
        if column is not None and self._place_column(column, self.column_target(point.x(), column)):
            self.holder.layout().activate()

    def drag_column(self, column):
        """Тащим колонку за заголовок: она переезжает прямо во время перетаскивания,
        а если бросить мимо доски (или нажать Esc), возвращается на место."""
        start = self.columns.index(column)
        self._dragged = column
        fade = QGraphicsOpacityEffect(column)
        fade.setOpacity(0.45)
        column.setGraphicsEffect(fade)
        drag = QDrag(column.header)
        mime = QMimeData()
        mime.setData(COLUMN_MIME, column.title.text().encode("utf-8"))
        drag.setMimeData(mime)
        picture = column.header.grab()
        drag.setPixmap(picture)
        drag.setHotSpot(QPoint(picture.width() // 2, picture.height() // 2))
        result = drag.exec(Qt.MoveAction)
        column.setGraphicsEffect(None)
        self._dragged = None
        if result != Qt.MoveAction:
            self._place_column(column, start)
        elif self.columns.index(column) != start:
            self.changed()

    def column_menu(self, column, button):
        menu = rounded_menu(self)
        menu.addAction(tr("Новая карточка"), lambda: self.new_card(column))
        menu.addAction(tr("Переименовать"), lambda: self.rename_column(column))
        menu.addAction(tr("Сдвинуть влево"), lambda: self.move_column(column, -1))
        menu.addAction(tr("Сдвинуть вправо"), lambda: self.move_column(column, 1))
        menu.addAction(tr("Вставить колонку справа"), lambda: self.add_column(self.columns.index(column) + 1))
        menu.addSeparator()
        menu.addAction(tr("Удалить колонку"), lambda: self.remove_column(column))
        menu.exec(button.mapToGlobal(QPoint(0, button.height())))

    # ---- карточки ----
    def new_card(self, column):
        dialog = CardDialog(self, {}, self.chapters(), self.on_foreign, existing=False)
        if dialog.exec():
            card = dialog.card_data()
            if card["title"] or card["text"]:
                item = column.add_card(card)
                column.list.setCurrentItem(item)
                self.changed()

    def edit_card(self, column, item):
        card = json.loads(item.data(Qt.UserRole) or "{}")
        dialog = CardDialog(self, card, self.chapters(), self.on_foreign, existing=True)
        if not dialog.exec():
            return
        if dialog.deleted:
            column.list.takeItem(column.list.row(item))
        else:
            item.setData(Qt.UserRole, json.dumps(dialog.card_data(), ensure_ascii=False))
        self.changed()

    def set_color(self, item, color):
        card = json.loads(item.data(Qt.UserRole) or "{}")
        card["color"] = color
        item.setData(Qt.UserRole, json.dumps(card, ensure_ascii=False))
        self.changed()

    def card_menu(self, column, pos):
        item = column.list.itemAt(pos)
        menu = rounded_menu(self)
        if item is None:
            menu.addAction(tr("Новая карточка"), lambda: self.new_card(column))
        else:
            card = json.loads(item.data(Qt.UserRole) or "{}")
            menu.addAction(tr("Изменить"), lambda: self.edit_card(column, item))
            if card.get("chapter"):
                menu.addAction(tr("Открыть главу"), lambda: self.open_chapter(card["chapter"]))
            colors = frameless_menu(menu.addMenu(tr("Цвет")))
            names = {"none": "Без цвета", "purple": "Фиолетовый", "amber": "Янтарный",
                     "green": "Зелёный", "coral": "Коралловый"}
            for name, _ in C.CARD_COLORS:
                colors.addAction(names[name], lambda n=name: self.set_color(item, n))
            menu.addSeparator()
            menu.addAction(tr("Удалить"), lambda: (column.list.takeItem(column.list.row(item)), self.changed()))
        menu.exec(column.list.viewport().mapToGlobal(pos))

    # ---- поиск и знаки ----
    def _matches(self, query):
        query = query.lower()
        found = []
        for ci, column in enumerate(self.columns):
            for ri, card in enumerate(column.cards()):
                if query in (card.get("title", "") + " " + card.get("text", "")).lower():
                    found.append((ci, ri))
        return found

    def reset_find(self):
        self._found = None

    def find(self, query, backward=False):
        cells = self._matches(query) if query else []
        if not cells:
            return 0, 0
        current = self._found if self._found is not None else ((-1, -1) if not backward else (10 ** 6, 0))
        if backward:
            earlier = [c for c in cells if c < current]
            target = earlier[-1] if earlier else cells[-1]
        else:
            later = [c for c in cells if c > current]
            target = later[0] if later else cells[0]
        self._found = target
        column = self.columns[target[0]]
        if self.mode == "free":
            card = json.loads(column.list.item(target[1]).data(Qt.UserRole) or "{}")
            placed = self.free.items_by_id.get(card.get("id"))
            if placed is not None:
                self.free.scene().clearSelection()
                placed.setSelected(True)
                self.free.centerOn(placed)
            return cells.index(target) + 1, len(cells)
        for other in self.columns:
            other.list.clearSelection()
        column.list.setCurrentRow(target[1])
        self.scroll.ensureWidgetVisible(column)
        return cells.index(target) + 1, len(cells)

    def count(self, query):
        cells = self._matches(query)
        return (cells.index(self._found) + 1 if self._found in cells else 0), len(cells)

    def insert(self, value):
        self.toast("Знаки ставятся в карточку: открой её двойным кликом")
