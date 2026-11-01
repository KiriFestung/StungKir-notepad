# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Как глава будет выглядеть у читателя: книга (карманная, A5, большая, A4), телефон, планшет,
электронная читалка - каждый в нескольких размерах. Текст вёрстается настоящими размерами
(миллиметры страницы, кегль, поля). Два режима: страницами (листать, с перелистыванием и
шелестом по желанию) и лентой, как в веб-новелле: листаешь вниз, и следующая глава
подгружается сама. У книги - выбор бумаги с фактурой."""

import html

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSizeF, Qt, QVariantAnimation
from PySide6.QtGui import (
    QAbstractTextDocumentLayout, QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPalette, QPen,
    QPixmap, QTextDocument, QTransform,
)
from PySide6.QtWidgets import QButtonGroup, QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from ..core import config as C
from ..ui.dialogs import Sheet
from .export import book_paragraphs, heading_of, image_of, is_scene_break
from ..core.textutil import markup_runs
from ..core.i18n import tr

MM = 96 / 25.4                       # экранных точек в миллиметре (вёрстка в «настоящем» размере)

# вид: (название, рамка, [(размер, подпись, ширина мм, высота мм, поля мм (верх, право, низ, лево), кегль)])
KINDS = {
    "book": ("Книга", "book", [
        ("pocket", "Карманная 110×170", 110, 170, (13, 11, 16, 13), 9.5),
        ("a5", "Обычная A5", 148, 210, (17, 15, 20, 18), 10.5),
        ("large", "Большая 170×240", 170, 240, (20, 18, 24, 21), 11.0),
        ("a4", "A4", 210, 297, (25, 22, 28, 25), 12.0)]),
    "phone": ("Телефон", "phone", [
        ("small", "Маленький 5,4\"", 57, 124, (5, 4, 5, 4), 9.0),
        ("normal", "Обычный 6,1\"", 64, 139, (6, 5, 6, 5), 9.5),
        ("large", "Большой 6,7\"", 71, 154, (6, 5, 6, 5), 10.0)]),
    "tablet": ("Планшет", "tablet", [
        ("small", "Планшет 8\"", 116, 174, (10, 10, 10, 10), 10.5),
        ("large", "Планшет 11\"", 160, 229, (14, 14, 14, 14), 11.5)]),
    "reader": ("Читалка", "reader", [
        ("6", "Читалка 6\"", 90, 122, (7, 7, 8, 7), 9.5),
        ("7", "Читалка 7\"", 107, 143, (8, 8, 9, 8), 10.0),
        ("10", "Читалка 10\"", 157, 209, (12, 12, 13, 12), 11.0)]),
}
# шрифт, межстрочный %, отступ абзаца em, выравнивание, бумага по умолчанию, чернила
STYLE = {
    "book": ("Literata", 135, 1.5, "justify", "book", "#1d1a16"),
    "phone": ("DejaVu Sans", 150, 1.2, "left", "screen", "#202124"),
    "tablet": ("Literata", 145, 1.3, "left", "screen", "#202124"),
    "reader": ("Literata", 140, 1.3, "justify", "eink", "#222222"),
}
DEFAULT_SIZE = {"book": "a5", "phone": "normal", "tablet": "small", "reader": "6"}
# бумага: (подпись, цвет, фактура art/paper/<…> или "", сила фактуры)
PAPERS = {
    "book": ("Книжная", "#f6efdf", "paper/book", 1.0),
    "white": ("Белая плотная", "#fbfaf6", "paper/rough", 0.8),
    "old": ("Старая", "#efe2c4", "paper/old", 1.0),
    "screen": ("Экран", "#ffffff", "", 0.0),
    "eink": ("Электронные чернила", "#ecebe5", "paper/book", 0.45),
}
BOOK_PAPERS = ("book", "white", "old")
DEVICES = {kind: spec for kind, spec in KINDS.items()}          # старое имя (вкладки устройств)


def chapter_html(title, text, folder=None, width=None):
    """Глава в HTML для вёрстки: заголовок, абзацы с отступом, разрывы сцен, курсив и жирный,
    картинки из строк «[картинка: файл]» (если файл рядом с главой). width - ширина полосы."""
    out = [f"<h2>{html.escape(title)}</h2>"] if title else []
    first = True
    for paragraph in book_paragraphs(text, strip_markers=True, folder=folder):
        picture = image_of(paragraph)
        if picture:
            from PySide6.QtGui import QImageReader
            natural = QImageReader(str(picture)).size().width()
            shown = min(width or natural, natural) if natural > 0 else (width or 300)
            out.append(f'<p class="scene"><img src="{html.escape(picture.as_posix())}" width="{int(shown)}"></p>')
            first = True
            continue
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


def size_spec(kind, size):
    sizes = KINDS[kind][2]
    return next((s for s in sizes if s[0] == size), next(s for s in sizes if s[0] == DEFAULT_SIZE[kind]))


def paint_paper(painter, rect, paper_key, scale=1.0):
    """Лист бумаги: цвет и бесшовная фактура (art/paper) поверх в режиме «умножение»."""
    _title, color, texture, strength = PAPERS[paper_key]
    painter.fillRect(rect, QColor(color))
    if not texture or strength <= 0:
        return
    from ..fun.artwork import pixmap
    tile = pixmap(texture)
    if tile.isNull():
        return
    painter.save()
    painter.setCompositionMode(QPainter.CompositionMode_Multiply)
    painter.setOpacity(strength)
    brush = QBrush(tile)
    brush.setTransform(QTransform.fromScale(0.55 / scale, 0.55 / scale))      # плитка ≈ 15 см
    painter.fillRect(rect, brush)
    painter.restore()


class Layout:
    """Общее у страниц и ленты: размер экрана или листа, поля, шрифт, документ."""

    def __init__(self, kind, size, paper=None):
        self.kind = kind
        _key, self.size_title, width, height, margins, point = size_spec(kind, size)
        self.size = _key
        family, spacing, indent, align, default_paper, self.ink = STYLE[kind]
        self.paper_key = paper if (paper in BOOK_PAPERS and kind == "book") else default_paper
        self.paper = PAPERS[self.paper_key][1]
        self.frame = KINDS[kind][1]
        self.name = self.size_title
        top, right, bottom, left = margins
        self.page = QSizeF(width * MM, height * MM)
        self.margins = (top * MM, right * MM, bottom * MM, left * MM)
        self.inner = QSizeF(self.page.width() - (left + right) * MM, self.page.height() - (top + bottom) * MM)
        self.font = QFont(family)
        self.font.setPointSizeF(point)
        self.style = (
            f"p {{ margin: 0; text-indent: {indent * point * 1.33:.1f}px; line-height: {spacing}%; "
            f"text-align: {align}; }}"
            "p.first { text-indent: 0px; }"
            "p.scene { text-indent: 0px; text-align: center; margin: 8px 0; }"
            f"h2 {{ text-align: center; font-size: {point + 4:g}pt; margin: 18px 0 14px; }}"
            f"h3 {{ text-align: center; font-size: {point + 2:g}pt; margin: 12px 0 8px; }}")

    def _document(self, markup):
        document = QTextDocument()
        document.setDefaultFont(self.font)
        document.setDocumentMargin(0)
        document.setDefaultStyleSheet(self.style)
        document.setHtml(markup)
        return document

    def _context(self):
        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette.setColor(QPalette.Text, QColor(self.ink))
        return context

    def _scaled(self, painter, rect):
        """Перенести рисование в мм-координаты листа, вписанного в rect. -> масштаб."""
        scale = min(rect.width() / self.page.width(), rect.height() / self.page.height())
        painter.translate(rect.x() + (rect.width() - self.page.width() * scale) / 2,
                          rect.y() + (rect.height() - self.page.height() * scale) / 2)
        painter.scale(scale, scale)
        return scale


class Pages(Layout):
    """Глава, свёрстанная по страницам: сколько их и как нарисовать любую."""

    def __init__(self, kind, title, text, size=None, paper=None, folder=None):
        super().__init__(kind, size or DEFAULT_SIZE[kind], paper)
        self.document = self._document(chapter_html(title, text, folder, self.inner.width()))
        self.document.setPageSize(self.inner)

    def count(self):
        return max(1, self.document.pageCount())

    def paint(self, painter, rect, number):
        """Страница number (с нуля) в прямоугольник rect, с масштабом по нему."""
        painter.save()
        scale = self._scaled(painter, rect)
        paint_paper(painter, QRectF(0, 0, self.page.width(), self.page.height()), self.paper_key, scale)
        top, _right, bottom, left = self.margins
        painter.translate(left, top - number * self.inner.height())
        context = self._context()
        context.clip = QRectF(0, number * self.inner.height(), self.inner.width(), self.inner.height() - 1)
        painter.setClipRect(context.clip)
        self.document.documentLayout().draw(painter, context)
        painter.restore()
        painter.save()
        small = QFont(self.font)
        small.setPointSizeF(7)
        painter.setFont(small)
        painter.setPen(QColor(self.ink).lighter(250))
        footer = QRectF(rect.x(), rect.y() + (rect.height() + self.page.height() * scale) / 2 - bottom * scale * 0.8,
                        rect.width(), bottom * scale * 0.6)
        painter.drawText(footer, Qt.AlignCenter, str(number + 1))
        painter.restore()


class Ribbon(Layout):
    """Лента, как в веб-новелле: главы одна за другой без страниц, листается вниз.
    more() дописывает следующую главу, когда до конца остаётся немного."""

    def __init__(self, kind, title, text, size=None, following=(), folder=None):
        super().__init__(kind, size or DEFAULT_SIZE[kind])
        self.folder = folder
        self.parts = [(title, text)]
        self.following = list(following)           # [(название, функция -> текст)] - читаются по мере листания
        self.document = self._document("")
        self.document.setTextWidth(self.inner.width())
        self._rebuild()

    def _rebuild(self):
        markup = []
        for i, (title, text) in enumerate(self.parts):
            if i:
                markup.append('<p class="scene">⁂</p>')
            markup.append(chapter_html(title, text, self.folder, self.inner.width()))
        if not self.following:
            markup.append('<p class="scene">- конец -</p>')
        self.document.setHtml("".join(markup))
        self.document.setTextWidth(self.inner.width())

    def height(self):
        return self.document.size().height() + self.margins[0] + self.margins[2]

    def max_offset(self):
        return max(0.0, self.height() - self.page.height())

    def more(self):
        """Дописать следующую главу. False - глав больше нет."""
        while self.following:
            title, read = self.following.pop(0)
            try:
                text = read()
            except Exception:                         # noqa: BLE001 - не прочиталась - листаем дальше
                continue
            self.parts.append((title, text))
            self._rebuild()
            return True
        self._rebuild()
        return False

    def chapter_at(self, offset):
        """Номер главы (с единицы), которую сейчас видно."""
        block = self.document.documentLayout().hitTest(QPointF(10, offset + self.page.height() / 3), Qt.FuzzyHit)
        text = self.document.toPlainText()[:max(0, block)]
        return 1 + text.count("⁂")

    def paint(self, painter, rect, offset):
        painter.save()
        scale = self._scaled(painter, rect)
        paint_paper(painter, QRectF(0, 0, self.page.width(), self.page.height()), self.paper_key, scale)
        top, _right, _bottom, left = self.margins
        painter.setClipRect(QRectF(0, 0, self.page.width(), self.page.height()))
        painter.translate(left, top - offset)
        context = self._context()
        context.clip = QRectF(0, offset - top, self.inner.width(), self.page.height())
        self.document.documentLayout().draw(painter, context)
        painter.restore()


class DeviceView(QWidget):
    """Страница в рамке устройства: книга с тенью, телефон и планшет в корпусе, читалка с полями.
    Страницы перелистываются (анимация загиба), лента прокручивается колесом и перетаскиванием."""

    FLIP_MS = 420

    def __init__(self):
        super().__init__()
        self.setMinimumSize(420, 520)
        self.pages, self.number = None, 0
        self.offset = 0.0
        self.on_scrolled = None
        self.flip = None                          # (старая страница, новая, вперёд ли)
        self.flip_t = 0.0
        self.flip_anim = QVariantAnimation(self)
        self.flip_anim.setStartValue(0.0)
        self.flip_anim.setEndValue(1.0)
        self.flip_anim.setDuration(self.FLIP_MS)
        self.flip_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.flip_anim.valueChanged.connect(self._flip_step)
        self.flip_anim.finished.connect(self._flip_done)
        self._drag = None

    # ---- что показывать ----
    def show_page(self, pages, number, animate=0):
        """animate: 1 - листаем вперёд, -1 - назад, 0 - сразу."""
        old = self.number if self.pages is pages else None
        self.pages, self.number = pages, number
        if animate and old is not None and old != number and isinstance(pages, Pages):
            self.flip = (old, number, animate > 0)
            self.flip_anim.stop()
            self.flip_anim.start()
        else:
            self.flip_anim.stop()
            self.flip = None
        self.update()

    def show_ribbon(self, ribbon, offset=0.0):
        self.flip_anim.stop()
        self.flip = None
        self.pages, self.offset = ribbon, offset
        self.update()

    def _flip_step(self, value):
        self.flip_t = float(value)
        self.update()

    def _flip_done(self):
        self.flip = None
        self.update()

    def finish_flip(self):
        if self.flip_anim.state() == QVariantAnimation.Running:
            self.flip_anim.setCurrentTime(self.FLIP_MS)

    # ---- лента: колесо и перетаскивание ----
    def scroll_by(self, delta):
        if not isinstance(self.pages, Ribbon):
            return
        screen = self._screen_rect()
        scale = screen.height() / self.pages.page.height()
        self.offset = max(0.0, min(self.pages.max_offset(), self.offset + delta / max(scale, 1e-3)))
        if self.pages.max_offset() - self.offset < self.pages.page.height() * 1.5 and self.pages.following:
            self.pages.more()                     # близко к концу - подгрузить следующую главу
        if self.on_scrolled:
            self.on_scrolled()
        self.update()

    def wheelEvent(self, event):
        if isinstance(self.pages, Ribbon):
            self.scroll_by(-event.angleDelta().y() * 0.6)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        self._drag = event.position().y()

    def mouseMoveEvent(self, event):
        if self._drag is not None and isinstance(self.pages, Ribbon):
            self.scroll_by(self._drag - event.position().y())
            self._drag = event.position().y()

    def mouseReleaseEvent(self, _event):
        self._drag = None

    # ---- рисование ----
    def _frame_insets(self):
        return {"book": (0, 0, 0, 0), "phone": (12, 34, 12, 30), "tablet": (22, 22, 22, 22),
                "reader": (24, 24, 24, 58)}[self.pages.frame]

    def _body_and_screen(self):
        area = QRectF(self.rect()).adjusted(16, 10, -16, -10)
        left, top, right, bottom = self._frame_insets()
        ratio = self.pages.page.width() / self.pages.page.height()
        height = area.height() - top - bottom
        width = height * ratio
        if width > area.width() - left - right:
            width = area.width() - left - right
            height = width / ratio
        x = area.center().x() - (width + left + right) / 2
        y = area.center().y() - (height + top + bottom) / 2
        return QRectF(x, y, width + left + right, height + top + bottom), QRectF(x + left, y + top, width, height)

    def _screen_rect(self):
        return self._body_and_screen()[1]

    def _page_pixmap(self, number, screen):
        ratio = self.devicePixelRatioF()
        picture = QPixmap(int(screen.width() * ratio) + 1, int(screen.height() * ratio) + 1)
        picture.setDevicePixelRatio(ratio)
        picture.fill(Qt.transparent)
        q = QPainter(picture)
        q.setRenderHint(QPainter.Antialiasing)
        q.setRenderHint(QPainter.TextAntialiasing)
        self.pages.paint(q, QRectF(0, 0, screen.width(), screen.height()), number)
        q.end()
        return picture

    def _paint_flip(self, p, screen):
        """Загиб страницы: линия сгиба едет справа налево (вперёд) или обратно (назад)."""
        old, new, forward = self.flip
        t = self.flip_t if forward else 1 - self.flip_t
        under, over = (new, old) if forward else (old, new)
        w = screen.width()
        fold = w * (1 - t)                        # где сейчас сгиб (от левого края листа)
        p.save()
        p.translate(screen.topLeft())
        p.drawPixmap(QPointF(0, 0), self._page_pixmap(under, screen))
        shade = QLinearGradient(fold, 0, fold + w * 0.12, 0)          # тень на следующей странице у сгиба
        shade.setColorAt(0, QColor(0, 0, 0, int(110 * (1 - abs(0.5 - t) * 1.2))))
        shade.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(QRectF(fold, 0, w * 0.12, screen.height()), shade)
        p.save()
        p.setClipRect(QRectF(0, 0, fold, screen.height()))
        p.drawPixmap(QPointF(0, 0), self._page_pixmap(over, screen))
        p.restore()
        flap = min(w - fold, fold)                # оборот перелистываемой страницы - слева от сгиба
        if flap > 1:
            drop = QLinearGradient(fold - flap - w * 0.05, 0, fold - flap, 0)    # тень от загиба на лист
            drop.setColorAt(0, QColor(0, 0, 0, 0))
            drop.setColorAt(1, QColor(0, 0, 0, 70))
            p.fillRect(QRectF(max(0.0, fold - flap - w * 0.05), 0, min(w * 0.05, fold - flap), screen.height()),
                       drop)
            back = QColor(self.pages.paper).darker(104)
            gloss = QLinearGradient(fold - flap, 0, fold, 0)
            gloss.setColorAt(0, back.darker(112))
            gloss.setColorAt(0.7, back)
            gloss.setColorAt(1, back.lighter(104))
            path = QPainterPath()
            curve = screen.height() * 0.012 * (1 - abs(0.5 - t) * 2)
            path.moveTo(fold, 0)
            path.lineTo(fold - flap, -curve)
            path.lineTo(fold - flap, screen.height() + curve)
            path.lineTo(fold, screen.height())
            path.closeSubpath()
            p.setPen(QPen(QColor(0, 0, 0, 40), 1))
            p.setBrush(gloss)
            p.drawPath(path)
        p.restore()

    def paintEvent(self, _event):
        if self.pages is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        body, screen = self._body_and_screen()
        frame = self.pages.frame
        if frame == "book":                                     # лист с мягкой тенью
            for k in range(6, 0, -1):
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, 10))
                p.drawRoundedRect(body.adjusted(-k, -k + 3, k, k + 3), 3, 3)
        else:
            radius = body.width() * {"phone": 0.12, "tablet": 0.05, "reader": 0.04}[frame]
            case = QPainterPath()
            case.addRoundedRect(body, radius, radius)
            p.setPen(QPen(QColor("#0b0b0e"), 2))
            p.setBrush(QColor("#4a4a4f") if frame == "reader" else QColor("#1b1b20"))
            p.drawPath(case)
            p.setPen(Qt.NoPen)
            if frame in ("phone", "tablet"):                    # камера
                p.setBrush(QColor("#000000"))
                p.drawEllipse(QRectF(body.center().x() - 5, body.top() + (12 if frame == "phone" else 8), 10, 10))
            else:                                               # кнопки листания читалки
                p.setBrush(QColor("#3a3a3f"))
                p.drawRoundedRect(QRectF(body.center().x() - 30, body.bottom() - 42, 60, 22), 6, 6)
        if isinstance(self.pages, Ribbon):
            self.pages.paint(p, screen, self.offset)
            share = self.offset / self.pages.max_offset() if self.pages.max_offset() else 0
            bar = QRectF(screen.right() - 4, screen.top() + 6 + (screen.height() - 52) * share, 3, 40)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 60))
            p.drawRoundedRect(bar, 1.5, 1.5)
        elif self.flip is not None:
            self._paint_flip(p, screen)
        else:
            self.pages.paint(p, screen, self.number)
        p.end()


class PreviewDialog(Sheet):
    """Окно предпросмотра: вид (книга, телефон, планшет, читалка), размер, режим, бумага;
    ◀ страница ▶ или лента."""

    def __init__(self, parent, title, text, device="book", following=(), folder=None):
        super().__init__(parent, tr("Как увидит читатель · {title}").format(title=title))
        self.folder = folder
        self.setMinimumSize(640, 760)
        self.title, self.text = title, text
        self.following = list(following)
        self.settings = getattr(parent, "settings", None)
        self.sounds = getattr(parent, "sounds", None)
        row = QHBoxLayout()
        self.group = QButtonGroup(self)
        self.buttons = {}
        for key, (name, _frame, _sizes) in KINDS.items():
            button = QPushButton(tr(name))
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
        row = QHBoxLayout()                       # второй ряд: размер, как листать, бумага
        self.size_box = QComboBox()
        self.size_box.currentIndexChanged.connect(self._size_changed)
        row.addWidget(self.size_box)
        self.mode_box = QComboBox()
        self.mode_box.addItem(tr("Страницами"), "pages")
        self.mode_box.addItem(tr("Лентой, как веб-новелла"), "ribbon")
        self.mode_box.currentIndexChanged.connect(lambda _i: self._show(reset=True))
        row.addWidget(self.mode_box)
        self.paper_box = QComboBox()
        for key in BOOK_PAPERS:
            self.paper_box.addItem(tr(PAPERS[key][0]), key)
        self.paper_box.setToolTip(tr("Бумага книги"))
        self.paper_box.currentIndexChanged.connect(self._paper_changed)
        row.addWidget(self.paper_box)
        row.addStretch()
        self.content.addLayout(row)
        self.view = DeviceView()
        self.view.on_scrolled = self._update_counter
        self.content.addWidget(self.view, 1)
        nav = QHBoxLayout()
        self.back = QPushButton("◀")
        self.back.clicked.connect(lambda: self.turn(-1))
        self.forward = QPushButton("▶")
        self.forward.clicked.connect(lambda: self.turn(1))
        self.counter = QLabel("")
        self.counter.setAlignment(Qt.AlignCenter)
        self.counter.setObjectName("Status")
        self.sound_box = QCheckBox(tr("Шелест страниц"))
        self.sound_box.setChecked(self._setting("preview_sound", "false") == "true")
        self.sound_box.toggled.connect(lambda on: self._remember("preview_sound", "true" if on else "false"))
        close = QPushButton(tr("Закрыть"))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        for button in (self.back, self.forward):
            button.setAutoDefault(False)
        nav.addWidget(self.back)
        nav.addWidget(self.counter, 1)
        nav.addWidget(self.forward)
        nav.addWidget(self.sound_box)
        nav.addWidget(close)
        self.content.addLayout(nav)
        self.pages = {}                 # (вид, размер, бумага) -> Pages; по виду - последний (для проверок)
        self.sizes = {}
        paper = self._setting("preview_paper", "book")
        self.paper_box.setCurrentIndex(max(0, self.paper_box.findData(paper)))
        self.mode_box.setCurrentIndex(max(0, self.mode_box.findData(self._setting("preview_mode", "pages"))))
        self.set_device(device)

    # ---- настройки ----
    def _setting(self, key, default):
        return self.settings.value(key, default) if self.settings is not None else default

    def _remember(self, key, value):
        if self.settings is not None:
            self.settings.setValue(key, value)

    def showEvent(self, event):
        """Окно - побольше: почти весь экран, чтобы страница была видна как есть."""
        super().showEvent(event)
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is not None and not getattr(self, "_sized", False):
            self._sized = True
            self.resize(max(self.minimumWidth(), int(screen.width() * 0.7)),
                        max(self.minimumHeight(), int(screen.height() * 0.9)))
            self.move(screen.center().x() - self.width() // 2, screen.center().y() - self.height() // 2)

    # ---- вид, размер, режим ----
    @property
    def mode(self):
        return self.mode_box.currentData() or "pages"

    def set_device(self, key):
        self.device = key if key in KINDS else "book"
        self.buttons[self.device].setChecked(True)
        self.size_box.blockSignals(True)
        self.size_box.clear()
        for size, label, *_rest in KINDS[self.device][2]:
            self.size_box.addItem(tr(label), size)
        chosen = self.sizes.get(self.device) or self._setting(f"preview_size_{self.device}", DEFAULT_SIZE[self.device])
        self.size_box.setCurrentIndex(max(0, self.size_box.findData(chosen)))
        self.size_box.blockSignals(False)
        self.paper_box.setVisible(self.device == "book")
        self._show(reset=True)

    def _size_changed(self, _index):
        size = self.size_box.currentData()
        if size:
            self.sizes[self.device] = size
            self._remember(f"preview_size_{self.device}", size)
            self._show(reset=True)

    def _paper_changed(self, _index):
        self._remember("preview_paper", self.paper_box.currentData())
        if hasattr(self, "device"):
            self._show(reset=False)

    def _layout(self):
        size = self.size_box.currentData() or DEFAULT_SIZE[self.device]
        paper = self.paper_box.currentData() if self.device == "book" else None
        key = (self.device, size, paper)
        if key not in self._cache():
            self._cache()[key] = Pages(self.device, self.title, self.text, size, paper, self.folder)
        pages = self._cache()[key]
        self.pages[self.device] = pages
        return pages

    def _cache(self):
        if not hasattr(self, "_layouts"):
            self._layouts = {}
        return self._layouts

    def _show(self, reset=False):
        if not hasattr(self, "device"):
            return
        self._remember("preview_mode", self.mode)
        if self.mode == "ribbon":
            size = self.size_box.currentData() or DEFAULT_SIZE[self.device]
            if reset or not isinstance(self.view.pages, Ribbon) or self.view.pages.kind != self.device \
                    or self.view.pages.size != size:
                ribbon = Ribbon(self.device, self.title, self.text, size, self.following, self.folder)
                self.view.show_ribbon(ribbon, 0.0)
            self._update_counter()
            return
        pages = self._layout()
        if reset:
            self.number = 0
        self.number = min(getattr(self, "number", 0), pages.count() - 1)
        self.view.show_page(pages, self.number)
        self._update_counter()

    def turn(self, step):
        if self.mode == "ribbon":
            screen = self.view._screen_rect()
            self.view.scroll_by(step * screen.height() * 0.85)
            return
        pages = self.pages[self.device]
        number = max(0, min(pages.count() - 1, self.number + step))
        if number == self.number:
            return
        direction = 1 if number > self.number else -1
        self.number = number
        self.view.finish_flip()
        self.view.show_page(pages, number, animate=direction if abs(step) == 1 else 0)
        if self.sound_box.isChecked() and self.sounds is not None:
            self.sounds.play("page_turn", 0.8)
        self._update_counter()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Right, Qt.Key_PageDown, Qt.Key_Space, Qt.Key_Down):
            self.turn(1)
        elif event.key() in (Qt.Key_Left, Qt.Key_PageUp, Qt.Key_Up):
            self.turn(-1)
        else:
            super().keyPressEvent(event)

    def _update_counter(self):
        if self.mode == "ribbon" and isinstance(self.view.pages, Ribbon):
            ribbon = self.view.pages
            total = len(ribbon.parts) + len(ribbon.following)
            share = self.view.offset / ribbon.max_offset() if ribbon.max_offset() else 1.0
            self.counter.setText(tr("глава {n} из {total} · {n2}%").format(n=ribbon.chapter_at(self.view.offset), total=total, n2=round(share * 100)))
            self.counter.setToolTip(tr("Листай вниз колесом или перетаскиванием - следующая глава подгрузится сама"))
            self.back.setEnabled(self.view.offset > 0)
            self.forward.setEnabled(self.view.offset < ribbon.max_offset())
            return
        pages = self.pages[self.device]
        total = pages.count()
        self.counter.setText(tr("страница {n} из {total}").format(n=self.number + 1, total=total))
        self.back.setEnabled(self.number > 0)
        self.forward.setEnabled(self.number < total - 1)
