# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""График прогресса («Рост» в окне статистики): сколько всего написано день за днём - линией,
а пунктир - где был бы, если бы каждый день выполнял цель. Под графиком - прогноз: в том же темпе
через месяц и через год будет ещё столько-то. Только рисует и считает, ничего не пишет на диск."""

from datetime import timedelta

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..core import config as C
from ..core.i18n import tr
from ..core.textutil import plural

DAYS = 90            # сколько дней показывает график
PACE_DAYS = 30       # по скольким последним дням считается темп для прогноза


def words(n):
    """«159 383 слова»: большое число - с пробелами по разрядам."""
    return f"{n:,}".replace(",", " ") + " " + plural(n, "слово", "слова", "слов")


def _written(stats, day):
    try:
        return max(0, int(stats.get(day.isoformat(), 0) or 0))
    except (TypeError, ValueError):
        return 0


def growth(stats, today, days=DAYS):
    """[(день, написано с начала окна)] - накопленная сумма за последние days дней, сегодня последним."""
    total, points = 0, []
    for n in range(days - 1, -1, -1):
        day = today - timedelta(days=n)
        total += _written(stats, day)
        points.append((day, total))
    return points


def pace(stats, today, days=PACE_DAYS):
    """Слов в день в среднем за последние days дней - с днями без текста, как оно и было."""
    return sum(_written(stats, today - timedelta(days=n)) for n in range(days)) / days


def forecast(stats, today):
    """Строка под графиком: темп и что будет в том же темпе."""
    per_day = pace(stats, today)
    if per_day < 1:
        return tr("Для прогноза пока мало данных: попиши несколько дней - здесь появится, к чему ты идёшь.")
    return tr("Темп за {days} дней: {n} в день. Так через месяц будет ещё {month}, через год - {year}.").format(
        days=PACE_DAYS, n=words(round(per_day)), month=words(round(per_day * 30)), year=words(round(per_day * 365)))


class GrowthChart(QWidget):
    """Линия накопленных слов и пунктир цели (цель на день × дни)."""

    def __init__(self, stats, goal, today, days=DAYS):
        super().__init__()
        self.points = growth(stats, today, days)
        self.goal = goal
        self.setMinimumHeight(240)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        left, right, top, bottom = 10, 14, 26, 26
        width = self.width() - left - right
        height = self.height() - top - bottom
        values = [total for _day, total in self.points]
        target = self.goal * len(values) if self.goal else 0
        top_value = max(values + [target, 1])
        step = width / max(1, len(values) - 1)

        def at(i, value):
            return QPointF(left + i * step, top + height - height * value / top_value)

        small = QFont(C.FONT_FAMILY, 9)
        small.setBold(True)
        painter.setFont(small)
        if self.goal:                                        # где был бы, если писать цель каждый день
            pen = QPen(QColor(C.DIM))
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(at(0, self.goal), at(len(values) - 1, target))
            painter.drawText(left, top - 8, tr("пунктир - цель {goal} в день").format(goal=self.goal))
        line = QPainterPath(at(0, values[0]))
        for i, value in enumerate(values[1:], 1):
            line.lineTo(at(i, value))
        area = QPainterPath(line)                            # под линией - лёгкая заливка
        area.lineTo(at(len(values) - 1, 0))
        area.lineTo(at(0, 0))
        area.closeSubpath()
        fill = QColor(C.IMPORTANT)                           # золото темы: на тёмном и на светлом видно
        fill.setAlpha(40)
        painter.fillPath(area, fill)
        painter.setPen(QPen(QColor(C.IMPORTANT), 2.5))
        painter.drawPath(line)
        end = at(len(values) - 1, values[-1])
        painter.setBrush(QColor(C.IMPORTANT))
        painter.drawEllipse(end, 4, 4)
        painter.setPen(QColor(C.TEXT))
        label = words(values[-1])
        metrics = painter.fontMetrics()
        painter.drawText(QRectF(end.x() - metrics.horizontalAdvance(label) - 8, end.y() - 22,
                                metrics.horizontalAdvance(label) + 4, 16), Qt.AlignRight, label)
        painter.setPen(QColor(C.DIM))
        for i, (day, _total) in enumerate(self.points):
            if i % 15 == 0 or i == len(self.points) - 1:
                text = day.strftime("%d.%m")
                x = min(int(left + i * step), self.width() - right - metrics.horizontalAdvance(text))
                painter.drawText(x, self.height() - 6, text)
