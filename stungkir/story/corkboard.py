# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Пробковая доска: те же карточки, что в колонках, но лежат где угодно, приколоты булавками
и связаны нитками. Колонка у карточки остаётся (видна мелко внизу) - в колонках она на своём месте."""

import math
import random
import uuid
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsPathItem, QGraphicsScene, QGraphicsView

from ..core import config as C

CARD_W, CARD_H = 210, 120
GRID_X, GRID_Y = 250, 150


def card_id(card):
    """У каждой карточки свой номер - по нему держатся нитки."""
    if not card.get("id"):
        card["id"] = uuid.uuid4().hex[:8]
    return card["id"]


def default_position(column, row):
    """Где карточка лежит, пока её не двигали: колонки - столбиками, как на обычной доске."""
    return 40 + column * GRID_X, 40 + row * GRID_Y


def cork_tile(size=160):
    """Пробка: нарисованная плитка (art/cork.png), бесшовная. В тёмной теме притемнена под фон,
    чтобы не слепила. Нет картинки - пробка рисуется кодом, крапинками."""
    from ..fun.artwork import pixmap
    picture = pixmap("cork")
    if not picture.isNull():
        tile = picture.scaled(256, 256, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        veil = QColor(C.BG)
        veil.setAlphaF(0.22 if not C.is_light() else 0.0)
        p = QPainter(tile)
        p.fillRect(tile.rect(), veil)
        p.end()
        return tile
    dark = not C.is_light()
    base = QColor("#8a6440" if dark else "#c49a6c")
    base = C.mix(base, C.BG, 0.45 if dark else 0.12)
    tile = QPixmap(size, size)
    tile.fill(base)
    p = QPainter(tile)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    rng = random.Random(7)
    for _ in range(size * size // 18):
        x, y = rng.uniform(0, size), rng.uniform(0, size)
        shade = rng.choice((C.mix(base, "#000000", rng.uniform(0.15, 0.4)), C.mix(base, "#ffffff", rng.uniform(0.05, 0.2))))
        shade.setAlpha(rng.randint(60, 150))
        p.setBrush(shade)
        r = rng.uniform(0.4, 1.6)
        p.drawEllipse(QPointF(x, y), r, r * rng.uniform(0.6, 1.0))
    p.end()
    return tile


class CardItem(QGraphicsObject):
    """Карточка на пробке: чуть повёрнута, с тенью и булавкой."""

    moved = Signal()

    def __init__(self, board, card, column_title):
        super().__init__()
        self.board, self.card, self.column_title = board, card, column_title
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setCursor(Qt.OpenHandCursor)
        seed = sum(ord(c) for c in card_id(card))
        self.setRotation(((seed % 7) - 3) * 0.6)                   # чуть криво, как от руки
        self.setPos(card.get("x", 0), card.get("y", 0))
        self.setAcceptHoverEvents(True)
        self._hover = False

    def boundingRect(self):
        return QRectF(-8, -24, CARD_W + 18, CARD_H + 36)

    def pin(self):
        return self.mapToScene(QPointF(CARD_W / 2, 2))

    def paint(self, painter, _option, _widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, CARD_W, CARD_H)
        painter.setPen(Qt.NoPen)
        lift = 5 if self.isSelected() or self._hover else 3
        for i in range(4, 0, -1):                                   # мягкая тень на пробке
            painter.setBrush(QColor(0, 0, 0, 16 + 8 * (4 - i)))
            painter.drawRoundedRect(rect.translated(lift * 0.6, lift).adjusted(-i, -i, i, i), 6 + i, 6 + i)
        # кремовая бумажка с загнутым уголком - в любой теме (на пробке так и выглядит записка)
        paper = QColor("#f6efe2")
        fold = 14
        sheet = QPainterPath()
        sheet.moveTo(4, 0)
        sheet.lineTo(CARD_W - fold, 0)
        sheet.lineTo(CARD_W, fold)
        sheet.lineTo(CARD_W, CARD_H - 4)
        sheet.quadTo(CARD_W, CARD_H, CARD_W - 4, CARD_H)
        sheet.lineTo(4, CARD_H)
        sheet.quadTo(0, CARD_H, 0, CARD_H - 4)
        sheet.lineTo(0, 4)
        sheet.quadTo(0, 0, 4, 0)
        painter.setBrush(paper)
        border = QColor(C.IMPORTANT) if self.isSelected() else QColor("#d8ccb4")
        painter.setPen(QPen(border, 2 if self.isSelected() else 1))
        painter.drawPath(sheet)
        corner = QPainterPath()
        corner.moveTo(CARD_W - fold, 0)
        corner.lineTo(CARD_W - fold, fold)
        corner.lineTo(CARD_W, fold)
        corner.closeSubpath()
        painter.setPen(QPen(QColor("#d8ccb4"), 1))
        painter.setBrush(QColor("#e6dac3"))
        painter.drawPath(corner)
        color = dict(C.CARD_COLORS).get(self.card.get("color", "none"))
        if color and self.card.get("color", "none") != "none":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(0, 0, CARD_W - fold, 6), 3, 3)
        text_color = QColor("#2b241b")
        title = QFont(C.FONT_FAMILY, 10)
        title.setBold(True)
        painter.setFont(title)
        painter.setPen(text_color)
        name = painter.fontMetrics().elidedText(self.card.get("title") or "Без названия", Qt.ElideRight, CARD_W - 20)
        painter.drawText(QRectF(10, 12, CARD_W - 20, 20), Qt.AlignLeft | Qt.AlignVCenter, name)
        small = QFont(C.FONT_FAMILY, 8)
        painter.setFont(small)
        dim = C.mix(text_color, paper, 0.4)
        painter.setPen(dim)
        painter.drawText(QRectF(10, 34, CARD_W - 20, CARD_H - 56), Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
                         self.card.get("text", "")[:200])
        foot = self.column_title
        if self.card.get("chapter"):
            foot = "→ " + Path(self.card["chapter"]).stem + ("   · " + foot if foot else "")
        painter.setPen(C.mix(dim, paper, 0.25))
        foot = painter.fontMetrics().elidedText(foot, Qt.ElideRight, CARD_W - 20)
        painter.drawText(QRectF(10, CARD_H - 20, CARD_W - 20, 14), Qt.AlignLeft | Qt.AlignVCenter, foot)
        # булавка: нарисованная (индиго или охра, у каждой карточки своя), чуть наклонена
        from ..fun.artwork import scaled
        seed = sum(ord(c) for c in card_id(self.card))
        pin = scaled("pin-ochre" if seed % 2 else "pin-indigo", 20, painter.device().devicePixelRatioF()
                     if painter.device() else 1.0)
        if not pin.isNull():
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.save()
            painter.translate(CARD_W / 2, 2)
            painter.rotate(150 if seed % 3 else 205)                  # игла уходит вверх, в пробку
            high = 20 * pin.height() / pin.width()
            painter.drawPixmap(QRectF(-10, -10, 20, high), pin, QRectF(pin.rect()))
            painter.restore()
        else:
            head = QColor(color if color and self.card.get("color", "none") != "none" else C.IMPORTANT)
            painter.setPen(QPen(C.mix(head, "#000000", 0.5), 1))
            painter.setBrush(head)
            painter.drawEllipse(QPointF(CARD_W / 2, 2), 6.5, 6.5)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.board.card_moved(self)
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self._hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hover = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if self.board.linking is not None and event.button() == Qt.LeftButton:
            self.board.finish_link(self)
            event.accept()
            return
        self.setCursor(Qt.ClosedHandCursor)
        self.setZValue(self.board.top_z())                          # взятая карточка - наверх
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
        self.board.drop_finished()

    def mouseDoubleClickEvent(self, event):
        self.board.edit_requested.emit(self)


class LinkItem(QGraphicsPathItem):
    """Нитка от булавки к булавке, чуть провисает."""

    def __init__(self, first, second):
        super().__init__()
        self.first, self.second = first, second
        self.setZValue(1e6)                                         # нитки поверх карточек, как настоящие
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.refresh()

    def refresh(self):
        a, b = self.first.pin(), self.second.pin()
        path = QPainterPath(a)
        middle = (a + b) / 2
        sag = min(60.0, math.dist((a.x(), a.y()), (b.x(), b.y())) * 0.12)
        path.quadTo(QPointF(middle.x(), middle.y() + sag), b)
        self.setPath(path)
        self.setPen(QPen(QColor("#2e3a8c"), 3.0, Qt.SolidLine, Qt.RoundCap))

    def paint(self, painter, _option, _widget=None):
        """Нитка индиго, как на рисунке: тень на пробке, сама нить и светлые витки поверх."""
        painter.setRenderHint(QPainter.Antialiasing)
        path = self.path()
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 70), 3.4, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(path.translated(1.2, 2.0))
        painter.setPen(QPen(QColor("#2e3a8c"), 3.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(path)
        twist = QPen(QColor(255, 255, 255, 70), 1.0, Qt.CustomDashLine, Qt.FlatCap)
        twist.setDashPattern([1.6, 3.2])
        painter.setPen(twist)
        painter.drawPath(path)


class FreeBoard(QGraphicsView):
    """Свободная доска. Колесо с Ctrl - масштаб, перетаскивание пустого места - прокрутка."""

    edit_requested = Signal(object)
    new_requested = Signal(QPointF)
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.items_by_id = {}
        self.links = []                  # [LinkItem]
        self.linking = None              # карточка, от которой тянем нитку
        self._linking_id = None
        self._z = 1.0
        self._loading = False
        self._moved = False
        self.menu_callback = None
        self.refresh_colors()

    def refresh_colors(self):
        self.setBackgroundBrush(QBrush(cork_tile()))
        for link in self.links:
            link.refresh()
        self.viewport().update()

    def top_z(self):
        self._z += 1
        return self._z

    # ---- данные ----
    def load(self, columns, links):
        """columns: [(название колонки, [словарь карточки])]; links: [[id, id]]."""
        self._loading = True
        self.scene().clear()
        self.items_by_id, self.links = {}, []
        for ci, (title, cards) in enumerate(columns):
            for ri, card in enumerate(cards):
                if "x" not in card or "y" not in card:
                    card["x"], card["y"] = default_position(ci, ri)
                item = CardItem(self, card, title)
                self.scene().addItem(item)
                self.items_by_id[card_id(card)] = item
        for first, second in links:
            if first in self.items_by_id and second in self.items_by_id and first != second:
                self._add_link(self.items_by_id[first], self.items_by_id[second])
        bounds = self.scene().itemsBoundingRect().adjusted(-400, -400, 600, 600)
        self.scene().setSceneRect(bounds.united(QRectF(-200, -200, 1600, 1000)))
        self._loading = False

    def link_pairs(self):
        return [[card_id(link.first.card), card_id(link.second.card)] for link in self.links]

    def _add_link(self, first, second):
        link = LinkItem(first, second)
        self.scene().addItem(link)
        self.links.append(link)
        return link

    # ---- карточки ----
    def card_moved(self, item):
        if self._loading:
            return
        item.card["x"], item.card["y"] = round(item.pos().x()), round(item.pos().y())
        for link in self.links:
            if item in (link.first, link.second):
                link.refresh()
        self._moved = True

    def drop_finished(self):
        if self._moved:
            self._moved = False
            self.changed.emit()

    def add_card_item(self, card, title):
        item = CardItem(self, card, title)
        self.scene().addItem(item)
        self.items_by_id[card_id(card)] = item
        item.setZValue(self.top_z())
        return item

    def remove_card_item(self, item):
        for link in [l for l in self.links if item in (l.first, l.second)]:
            self.links.remove(link)
            self.scene().removeItem(link)
        self.items_by_id.pop(card_id(item.card), None)
        self.scene().removeItem(item)

    # ---- нитки ----
    def start_link(self, item):
        self.linking = item
        self._linking_id = card_id(item.card)
        self.viewport().setCursor(Qt.CrossCursor)

    def finish_link(self, item):
        first, self.linking = self.linking, None
        self.viewport().unsetCursor()
        if first is not None:
            # доску могли перечитать (сохранение, изменение снаружи), пока тянули нитку:
            # старая карточка уже удалена - берём ту же карточку с новой доски
            from shiboken6 import isValid
            first = self.items_by_id.get(self._linking_id) if not isValid(first) else first
        if first is None or first is item:
            return
        for link in self.links:
            if {link.first, link.second} == {first, item}:
                return                                              # уже связаны
        self._add_link(first, item)
        self.changed.emit()

    def remove_links(self, item):
        doomed = [l for l in self.links if item in (l.first, l.second)]
        for link in doomed:
            self.links.remove(link)
            self.scene().removeItem(link)
        if doomed:
            self.changed.emit()

    # ---- вид ----
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            scale = self.transform().m11() * factor
            if 0.25 <= scale <= 2.5:
                self.scale(factor, factor)
            return
        super().wheelEvent(event)

    def fit(self):
        bounds = self.scene().itemsBoundingRect()
        if bounds.isEmpty():
            self.setTransform(QTransform())
            return
        self.fitInView(bounds.adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio)
        if self.transform().m11() > 1.2:
            self.setTransform(QTransform.fromScale(1.2, 1.2))
            self.centerOn(bounds.center())

    def mouseDoubleClickEvent(self, event):
        if self.itemAt(event.position().toPoint()) is None:
            self.new_requested.emit(self.mapToScene(event.position().toPoint()))
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if self.linking is not None and self.itemAt(event.position().toPoint()) is None:
            self.linking = None                                     # щелчок мимо - нитку не тянем
            self.viewport().unsetCursor()
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton
                                                 and event.modifiers() & Qt.ShiftModifier):
            self.setDragMode(QGraphicsView.ScrollHandDrag)          # Shift или колёсико - двигать доску
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setDragMode(QGraphicsView.RubberBandDrag)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        while item is not None and not isinstance(item, CardItem):
            item = item.parentItem()
        if self.menu_callback is not None:
            self.menu_callback(item, self.mapToScene(event.pos()), event.globalPos())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.linking is not None:
            self.linking = None
            self.viewport().unsetCursor()
            return
        super().keyPressEvent(event)

