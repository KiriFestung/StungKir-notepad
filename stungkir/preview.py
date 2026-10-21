# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Как глава будет выглядеть у читателя: страница книги A5, экран телефона 6" и электронная
читалка 6". Текст вёрстается настоящими размерами (миллиметры страницы, кегль, поля) и листается
по страницам - видно, сколько страниц выйдет и где ломаются абзацы и реплики."""

import html

from PySide6.QtCore import QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QAbstractTextDocumentLayout, QColor, QFont, QPainter, QPainterPath, QPalette, QPen, QTextDocument,
)
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QPushButton, QWidget

from . import config as C
from .dialogs import Sheet
from .export import book_paragraphs, heading_of, is_scene_break
from .textutil import markup_runs

MM = 96 / 25.4                       # экранных точек в миллиметре (вёрстка в «настоящем» размере)

# вид: (название, ширина и высота страницы в мм, поля мм (верх, право, низ, лево), шрифт, кегль,
#       межстрочный %, отступ абзаца em, выравнивание, бумага, чернила, рамка устройства)
DEVICES = {
    "book": ("Книга A5", 148, 210, (17, 15, 20, 18), "DejaVu Serif", 10.5, 135, 1.5, "justify",
             "#fbf7ee", "#1d1a16", "book"),
    "phone": ("Телефон 6\"", 68, 140, (6, 5, 6, 5), "DejaVu Sans", 9.5, 150, 1.2, "left",
              "#ffffff", "#202124", "phone"),
    "reader": ("Читалка 6\"", 90, 122, (7, 7, 8, 7), "DejaVu Serif", 9.5, 140, 1.3, "justify",
               "#efede6", "#222222", "reader"),
}


def chapter_html(title, text):
    """Глава в HTML для вёрстки: заголовок, абзацы с отступом, разрывы сцен, курсив и жирный."""
    out = [f"<h2>{html.escape(title)}</h2>"] if title else []
    first = True
    for paragraph in book_paragraphs(text, strip_markers=True):
        if is_scene_break(paragraph):
            out.append('<p class="scene">* * *</p>')
            first = True
            continue
        heading = heading_of(paragraph)
        if heading:
            out.append(f"<h3>{html.escape(heading[1])}</h3>")
            first = True
            continue
        pieces = []
        for piece, bold, italic in markup_runs(paragraph):
            piece = html.escape(piece)
            if bold:
                piece = f"<b>{piece}</b>"
            if italic:
                piece = f"<i>{piece}</i>"
            pieces.append(piece)
        out.append(('<p class="first">' if first else "<p>") + "".join(pieces) + "</p>")
        first = False
    return "".join(out)


class Pages:
    """Глава, свёрстанная под устройство: сколько страниц и как нарисовать любую."""

    def __init__(self, device, title, text):
        (self.name, width, height, margins, family, size, spacing, indent, align,
         self.paper, self.ink, self.frame) = DEVICES[device]
        top, right, bottom, left = margins
        self.page = QSizeF(width * MM, height * MM)
        self.margins = (top * MM, right * MM, bottom * MM, left * MM)
        self.document = QTextDocument()
        font = QFont(family)
        font.setPointSizeF(size)
        self.document.setDefaultFont(font)
        self.document.setDocumentMargin(0)
        self.document.setDefaultStyleSheet(
            f"p {{ margin: 0; text-indent: {indent * size * 1.33:.1f}px; line-height: {spacing}%; text-align: {align}; }}"
            "p.first { text-indent: 0px; }"
            "p.scene { text-indent: 0px; text-align: center; margin: 8px 0; }"
            f"h2 {{ text-align: center; font-size: {size + 4:g}pt; margin: 18px 0 14px; }}"
            f"h3 {{ text-align: center; font-size: {size + 2:g}pt; margin: 12px 0 8px; }}")
        self.document.setHtml(chapter_html(title, text))
        self.inner = QSizeF(self.page.width() - left * MM - right * MM, self.page.height() - top * MM - bottom * MM)
        self.document.setPageSize(self.inner)

    def count(self):
        return max(1, self.document.pageCount())

    def paint(self, painter, rect, number):
        """Страница number (с нуля) в прямоугольник rect, с масштабом по нему."""
        scale = min(rect.width() / self.page.width(), rect.height() / self.page.height())
        painter.save()
        painter.translate(rect.x() + (rect.width() - self.page.width() * scale) / 2,
                          rect.y() + (rect.height() - self.page.height() * scale) / 2)
        painter.scale(scale, scale)
        painter.fillRect(QRectF(0, 0, self.page.width(), self.page.height()), QColor(self.paper))
        top, _right, bottom, left = self.margins
        painter.translate(left, top - number * self.inner.height())
        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette.setColor(QPalette.Text, QColor(self.ink))
        context.clip = QRectF(0, number * self.inner.height(), self.inner.width(), self.inner.height() - 1)
        painter.setClipRect(context.clip)
        self.document.documentLayout().draw(painter, context)
        painter.restore()
        painter.save()
        small = QFont(self.document.defaultFont())
        small.setPointSizeF(7)
        painter.setFont(small)
        painter.setPen(QColor(self.ink).lighter(250))
        footer = QRectF(rect.x(), rect.y() + (rect.height() + self.page.height() * scale) / 2 - bottom * scale * 0.8,
                        rect.width(), bottom * scale * 0.6)
        painter.drawText(footer, Qt.AlignCenter, str(number + 1))
        painter.restore()


class DeviceView(QWidget):
    """Страница в рамке устройства: книга с тенью, телефон с вырезом, читалка с толстыми полями."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(420, 520)
        self.pages, self.number = None, 0

    def show_page(self, pages, number):
        self.pages, self.number = pages, number
        self.update()

    def paintEvent(self, _event):
        if self.pages is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        area = QRectF(self.rect()).adjusted(16, 10, -16, -10)
        frame = self.pages.frame
        left, top, right, bottom = {"book": (0, 0, 0, 0), "phone": (12, 34, 12, 30), "reader": (24, 24, 24, 58)}[frame]
        ratio = self.pages.page.width() / self.pages.page.height()
        height = area.height() - top - bottom
        width = height * ratio
        if width > area.width() - left - right:
            width = area.width() - left - right
            height = width / ratio
        x = area.center().x() - (width + left + right) / 2
        y = area.center().y() - (height + top + bottom) / 2
        body = QRectF(x, y, width + left + right, height + top + bottom)
        screen = QRectF(x + left, y + top, width, height)
        if frame == "book":                                     # лист с мягкой тенью
            for k in range(6, 0, -1):
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, 10))
                p.drawRoundedRect(body.adjusted(-k, -k + 3, k, k + 3), 3, 3)
        else:
            radius = body.width() * (0.12 if frame == "phone" else 0.04)
            case = QPainterPath()
            case.addRoundedRect(body, radius, radius)
            p.setPen(QPen(QColor("#0b0b0e"), 2))
            p.setBrush(QColor("#1b1b20") if frame == "phone" else QColor("#4a4a4f"))
            p.drawPath(case)
            p.setPen(Qt.NoPen)
            if frame == "phone":                                # вырез под камеру
                p.setBrush(QColor("#000000"))
                p.drawEllipse(QRectF(body.center().x() - 6, body.top() + 12, 12, 12))
            else:                                               # кнопки листания читалки
                p.setBrush(QColor("#3a3a3f"))
                p.drawRoundedRect(QRectF(body.center().x() - 30, body.bottom() - 42, 60, 22), 6, 6)
        self.pages.paint(p, screen, self.number)
        p.end()


class PreviewDialog(Sheet):
    """Окно предпросмотра: вкладки устройств, ◀ страница ▶."""

    def __init__(self, parent, title, text, device="book"):
        super().__init__(parent, f"Как увидит читатель · {title}")
        self.setMinimumSize(560, 760)
        self.title, self.text = title, text
        row = QHBoxLayout()
        self.group = QButtonGroup(self)
        self.buttons = {}
        for key, spec in DEVICES.items():
            button = QPushButton(spec[0])
            button.setCheckable(True)
            button.setProperty("noIcon", True)
            button.setAutoDefault(False)
            button.setStyleSheet(f"QPushButton:checked {{ background: {C.IMPORTANT}; color: {C.on_color(C.IMPORTANT)}; }}")
            button.clicked.connect(lambda _c=False, k=key: self.set_device(k))
            self.group.addButton(button)
            self.buttons[key] = button
            row.addWidget(button)
        row.addStretch()
        self.content.addLayout(row)
        self.view = DeviceView()
        self.content.addWidget(self.view, 1)
        nav = QHBoxLayout()
        self.back = QPushButton("◀")
        self.back.clicked.connect(lambda: self.turn(-1))
        self.forward = QPushButton("▶")
        self.forward.clicked.connect(lambda: self.turn(1))
        self.counter = QLabel("")
        self.counter.setAlignment(Qt.AlignCenter)
        self.counter.setObjectName("Status")
        close = QPushButton("Закрыть")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        for button in (self.back, self.forward):
            button.setAutoDefault(False)
        nav.addWidget(self.back)
        nav.addWidget(self.counter, 1)
        nav.addWidget(self.forward)
        nav.addWidget(close)
        self.content.addLayout(nav)
        self.pages = {}
        self.set_device(device)

    def set_device(self, key):
        self.device = key
        self.buttons[key].setChecked(True)
        if key not in self.pages:
            self.pages[key] = Pages(key, self.title, self.text)
        self.number = 0
        self._show()

    def turn(self, step):
        self.number = max(0, min(self.pages[self.device].count() - 1, self.number + step))
        self._show()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Right, Qt.Key_PageDown, Qt.Key_Space):
            self.turn(1)
        elif event.key() in (Qt.Key_Left, Qt.Key_PageUp):
            self.turn(-1)
        else:
            super().keyPressEvent(event)

    def _show(self):
        pages = self.pages[self.device]
        total = pages.count()
        self.view.show_page(pages, self.number)
        self.counter.setText(f"страница {self.number + 1} из {total}")
        self.back.setEnabled(self.number > 0)
        self.forward.setEnabled(self.number < total - 1)
