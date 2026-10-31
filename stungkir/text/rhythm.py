# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ритм главы: длина каждого предложения по порядку. Только показывает - ничего не правит."""

import re
import statistics

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QToolTip, QWidget

from ..core import config as C
from ..ui.dialogs import Sheet
from ..core.textutil import MARKER_RE, WORD_RE, plain_markup, plural, position_map

SHORT, LONG = 6, 25          # до 6 слов - короткое, от 25 - длинное
SENTENCE_END = re.compile(r"[.!?…]+[»\"”)]*(?=\s|$)")


def sentences(text):
    """[(номер строки, начало, конец, слов, текст)] - предложения главы по порядку.
    Заголовки «# …», разрывы сцен и пометки [ ] не в счёт."""
    out = []
    for number, line in enumerate(text.split("\n")):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or set(stripped) <= set("*~• "):
            continue
        start = len(line) - len(line.lstrip())
        pieces = [(m.end()) for m in SENTENCE_END.finditer(line)]
        if not pieces or pieces[-1] < len(line.rstrip()):
            pieces.append(len(line.rstrip()))
        for end in pieces:
            chunk = line[start:end]
            words = len(WORD_RE.findall(MARKER_RE.sub("", plain_markup(chunk))))
            if words:
                out.append((number, start, end, words, chunk.strip()))
            start = end
            while start < len(line) and line[start] == " ":
                start += 1
    return out


def summary(items):
    if not items:
        return "В главе пока нет предложений."
    lengths = [s[3] for s in items]
    short = sum(1 for n in lengths if n <= SHORT)
    long = sum(1 for n in lengths if n >= LONG)
    longest = max(lengths)
    mean = f"{statistics.mean(lengths):.1f}".replace(".", ",")
    median = f"{statistics.median(lengths):g}".replace(".", ",")
    return (f"{len(items)} {plural(len(items), 'предложение', 'предложения', 'предложений')} · в среднем "
            f"{mean} слова · обычно {median} · "
            f"коротких (до {SHORT}) {round(100 * short / len(items))}% · длинных (от {LONG}) "
            f"{round(100 * long / len(items))}% · самое длинное - {longest} {plural(longest, 'слово', 'слова', 'слов')}")


class RhythmChart(QWidget):
    """Столбик на предложение: высота - число слов. Наведи - видно предложение, клик - перейти к нему."""

    STEP = 9

    def __init__(self, items, on_pick):
        super().__init__()
        self.items, self.on_pick = items, on_pick
        self.setMouseTracking(True)
        self.setMinimumHeight(260)
        self.setMinimumWidth(max(600, len(items) * self.STEP + 60))
        self._hover = None

    def _index(self, x):
        i = int((x - 40) // self.STEP)
        return i if 0 <= i < len(self.items) else None

    def mouseMoveEvent(self, event):
        i = self._index(event.position().x())
        if i != self._hover:
            self._hover = i
            self.update()
        if i is not None:
            n, text = self.items[i][3], self.items[i][4]
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"{n} {plural(n, 'слово', 'слова', 'слов')}: {text[:220]}", self)

    def leaveEvent(self, _event):
        self._hover = None
        self.update()

    def mousePressEvent(self, event):
        i = self._index(event.position().x())
        if i is not None and event.button() == Qt.LeftButton:
            self.on_pick(self.items[i])

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        top, bottom, left = 16, 22, 40
        height = self.height() - top - bottom
        peak = max([s[3] for s in self.items] + [LONG + 5])
        small = QFont(C.FONT_FAMILY, 8)
        painter.setFont(small)
        painter.setPen(QPen(QColor(C.BORDER), 1, Qt.DashLine))
        for level in (SHORT, LONG):
            y = top + height - height * level / peak
            painter.drawLine(left, int(y), self.width(), int(y))
            painter.setPen(QColor(C.DIM))
            painter.drawText(QRectF(0, y - 8, left - 6, 16), Qt.AlignRight | Qt.AlignVCenter, str(level))
            painter.setPen(QPen(QColor(C.BORDER), 1, Qt.DashLine))
        if self.items:
            mean = statistics.mean(s[3] for s in self.items)
            y = top + height - height * mean / peak
            painter.setPen(QPen(QColor(C.PUNCT), 1.2))
            painter.drawLine(left, int(y), self.width(), int(y))
        painter.setPen(Qt.NoPen)
        for i, item in enumerate(self.items):
            n = item[3]
            if n <= SHORT:
                color = QColor(C.DIALOGUE)
            elif n >= LONG:
                color = QColor(C.SPELL)
            else:
                color = C.mix(C.TEXT, C.BG, 0.25)
            if i == self._hover:
                color = QColor(C.PUNCT)
            bar = height * n / peak
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(left + i * self.STEP, top + height - bar, self.STEP - 3, max(bar, 2)), 2, 2)


class RhythmDialog(Sheet):
    def __init__(self, parent, title, items, on_pick):
        super().__init__(parent, f"Ритм главы · {title}")
        self.setMinimumSize(900, 560)
        self.on_pick = on_pick
        info = QLabel(summary(items))
        info.setWordWrap(True)
        self.content.addWidget(info)
        legend = QLabel(f"Каждый столбик - предложение по порядку. Жёлтые - короткие (до {SHORT} слов), "
                        f"красные - длинные (от {LONG}), линия - средняя длина. Наведи - видно предложение, "
                        "клик - перейти к нему.")
        legend.setObjectName("Status")
        legend.setWordWrap(True)
        self.content.addWidget(legend)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(RhythmChart(items, self._pick))
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setMinimumHeight(300)
        self.content.addWidget(scroll, 1)
        row = QHBoxLayout()
        row.addStretch()
        close = QPushButton("Закрыть")
        close.setDefault(True)
        close.clicked.connect(self.accept)
        row.addWidget(close)
        self.content.addLayout(row)

    def _pick(self, item):
        self.accept()
        self.on_pick(item)


class RhythmMixin:
    """Ритм главы. Часть главного окна."""

    def show_rhythm(self):
        if self.view is not None:
            self.toast.show_message("Ритм считается для главы, а не для таблицы или доски")
            return
        items = sentences(self.editor.toPlainText())
        title = self.path.stem if self.path else "без названия"
        RhythmDialog(self, title, items, self._select_sentence).exec()

    def _select_sentence(self, item):
        number, start, end = item[0], item[1], item[2]
        block = self.editor.document().findBlockByNumber(number)
        if not block.isValid():
            return
        to_qt = position_map(block.text())
        cursor = QTextCursor(block)
        cursor.setPosition(block.position() + to_qt(start))
        cursor.setPosition(block.position() + to_qt(min(end, len(block.text()))), QTextCursor.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.editor.setFocus()
