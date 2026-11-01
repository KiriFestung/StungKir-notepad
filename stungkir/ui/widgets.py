# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Мелкие виджеты: полоски целей, ласка в колесе, кубики, панели, всплывающие сообщения."""

import math
import random
from pathlib import Path
from PySide6.QtCore import (
    QEasingCurve, QElapsedTimer, QEvent, QParallelAnimationGroup, QPauseAnimation, QPoint,
    QPointF, QPropertyAnimation, QRectF, QSequentialAnimationGroup, QSize, Qt, QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QGraphicsOpacityEffect, QLabel, QLineEdit, QPushButton, QTextEdit,
    QTreeWidget, QWidget,
)

from ..core import config as C
from ..core.textutil import has_foreign
from ..core.i18n import tr


class GoalStrip(QWidget):
    """Полоски под текстом: цель на день, цель главы и дедлайн книги.
    Вид (style): «bright» - сочные цвета темы, «rainbow» - радуга, «calm» - приглушённые, как раньше."""

    BAR = 170
    HEIGHT = 6
    CAPTIONS = {"day": "день", "chapter": "глава", "book": "книга"}
    ORDER = ("day", "chapter", "book")
    STYLES = {"bright": "Яркие, в цветах темы", "rainbow": "Радуга", "calm": "Спокойные"}

    def __init__(self):
        super().__init__()
        self.setFixedHeight(20)
        self.style_name = "bright"
        self.align = "center"
        self.items = {}
        for name in self.ORDER:
            anim = QVariantAnimation(self)
            anim.setDuration(600)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            item = {"value": 0.0, "done": False, "shown": False, "anim": anim}
            anim.valueChanged.connect(lambda v, it=item: self._step(it, v))
            self.items[name] = item

    def set_align(self, align):
        self.align = align if align in ("left", "right") else "center"
        self.update()

    def set_style(self, name):
        self.style_name = name if name in self.STYLES else "bright"
        self.update()

    def _step(self, item, value):
        item["value"] = float(value)
        self.update()

    def set(self, name, value, done, shown):
        item = self.items[name]
        value = max(0.0, min(1.0, value))
        item["done"], item["shown"] = done, shown
        if abs(value - item["value"]) < 0.001:
            self.update()
            return
        item["anim"].stop()
        item["anim"].setStartValue(float(item["value"]))
        item["anim"].setEndValue(float(value))
        item["anim"].start()

    def any_shown(self):
        return any(item["shown"] for item in self.items.values())

    def color(self, name, done=False):
        """Цвет полоски (и цифры под текстом) в нынешнем виде."""
        if self.style_name == "calm":
            if name == "day":
                return QColor(C.TEXT) if done else C.mix(C.TEXT, C.BG, 0.3)
            if name == "book":
                return QColor(C.LORE) if done else C.mix(C.LORE, C.TEXT, 0.35)
            return QColor(C.DIALOGUE) if done else C.mix(C.DIALOGUE, C.BG, 0.3)
        return QColor({"day": C.BAR_DAY, "chapter": C.BAR_CHAPTER, "book": C.BAR_BOOK}[name])

    @staticmethod
    def _hue_gap(a, b):
        return C.hue_gap(a, b)

    def _fill(self, name, rect, done):
        if self.style_name != "rainbow":
            return self.color(name, done)
        gradient = QLinearGradient(rect.left(), 0, rect.right(), 0)             # радуга на всю длину:
        colors = C.rainbow()                                                    # чем больше написано,
        for i, color in enumerate(colors):                                      # тем больше цветов видно
            gradient.setColorAt(i / (len(colors) - 1), color)
        return gradient

    def paintEvent(self, _event):
        shown = [(n, self.items[n]) for n in self.ORDER if self.items[n]["shown"]]
        if not shown:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont(C.FONT_FAMILY, 8)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        gap = 32
        captions = [tr(self.CAPTIONS[n]) + (" ✓" if item["done"] else "") for n, item in shown]
        text_width = sum(metrics.horizontalAdvance(c) + 8 for c in captions) + gap * (len(shown) - 1)
        bar_len = max(40.0, min(float(self.BAR), (self.width() - 24 - text_width) / len(shown)))  # узкое окно
        widths = [metrics.horizontalAdvance(c) + 8 + bar_len for c in captions]
        total = sum(widths) + gap * (len(shown) - 1)
        x = {"left": 16.0, "right": self.width() - total - 16.0}.get(self.align, (self.width() - total) / 2)
        top = 7
        for (name, item), caption, width in zip(shown, captions, widths):
            done_color = self.color(name, True) if self.style_name != "rainbow" else C.rainbow()[3]
            painter.setPen(done_color if item["done"] and self.style_name != "calm" else QColor(C.DIM))
            painter.drawText(int(x), top + self.HEIGHT, caption)
            bar_x = x + metrics.horizontalAdvance(caption) + 8
            painter.setPen(Qt.NoPen)
            bar_painter = getattr(self, "bar_painter", None)        # праздник: полоска заполняется снегом
            if bar_painter is not None:
                bar_painter(painter, QRectF(bar_x, top, bar_len, self.HEIGHT), item["value"], item["done"])
                x += width + gap
                continue
            # дорожка заметна на любом фоне, заполнение - ярче, чтобы не сливалось
            painter.setBrush(C.mix(C.DIM, C.BG, 0.55))
            painter.drawRoundedRect(QRectF(bar_x, top, bar_len, self.HEIGHT), 3, 3)
            if item["value"] > 0:
                rect = QRectF(bar_x, top, max(float(self.HEIGHT), bar_len * item["value"]), self.HEIGHT)
                painter.setBrush(self._fill(name, QRectF(bar_x, top, bar_len, self.HEIGHT), item["done"]))
                painter.drawRoundedRect(rect, 3, 3)
            x += width + gap


class ClockFace(QWidget):
    """Часы в углу: индиговый циферблат с охристым ободком и рисками, часовая стрелка - охристый
    наконечник, минутная - тонкая светлая игла (как на рисунках). Выделяются в любой теме.
    Цвета меняются в «Цвета и темы» → «Часы». Мышь проходит насквозь."""

    @property
    def FACE(self):
        return C.CLOCK_FACE

    @property
    def RING(self):
        return C.CLOCK_RING

    @property
    def HOUR(self):
        return C.CLOCK_HANDS

    @property
    def MINUTE(self):
        return C.CLOCK_MINUTE

    @property
    def MARK(self):
        return C.CLOCK_RING

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(116, 116)
        self.now = None

    def text(self):
        return self.now.strftime("%H:%M") if self.now else ""

    def set_time(self, now):
        if self.now is None or (now.hour, now.minute) != (self.now.hour, self.now.minute):
            self.now = now
            self.update()

    @staticmethod
    def text_spot(hours, minutes):
        """Где писать цифры: внизу, если там нет стрелок, иначе вверху, иначе сбоку - там, где
        дальше всего от обеих стрелок (раньше цифры всегда были внизу, и в 00:27 минутная
        стрелка ложилась прямо на них)."""
        hands = (hours / 12 * 360, minutes / 60 * 360)

        def clearance(spot):
            return min(abs((spot - h + 180) % 360 - 180) for h in hands)
        for spot in (180, 0):
            if clearance(spot) >= 40:
                return spot
        return max((180, 0, 90, 270), key=clearance)

    def text_rect(self, center, radius, hours, minutes):
        spot = self.text_spot(hours, minutes)
        angle = math.radians(spot)
        distance = radius * (0.42 if spot in (0, 180) else 0.36)     # сбоку ближе: там длинные риски
        x = center.x() + math.sin(angle) * distance
        y = center.y() - math.cos(angle) * distance
        return QRectF(x - 20, y - 8, 40, 16)

    def paintEvent(self, _event):
        if self.now is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = self.width() / 2 - 5
        painter.setPen(QPen(QColor(0, 0, 0, 90), 6))                 # мягкая тень по краю
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center + QPointF(0, 1.5), radius, radius)
        painter.setPen(QPen(QColor(self.RING), 4.2))
        painter.setBrush(QColor(self.FACE))
        painter.drawEllipse(center, radius, radius)
        for minute in range(60):                                      # риски: часовые - бруски, минутные - штрихи
            angle = math.radians(minute * 6)
            sin, cos = math.sin(angle), math.cos(angle)
            big = minute % 15 == 0
            hour = minute % 5 == 0
            inner = radius - (14 if big else 10.5 if hour else 7.5)
            painter.setPen(QPen(QColor(self.MARK), 3.0 if big else 2.4 if hour else 1.1, Qt.SolidLine, Qt.FlatCap))
            painter.drawLine(QPointF(center.x() + sin * inner, center.y() - cos * inner),
                             QPointF(center.x() + sin * (radius - 4.5), center.y() - cos * (radius - 4.5)))
        font = QFont(C.FONT_FAMILY, 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(self.MINUTE))
        minutes = self.now.minute + self.now.second / 60
        hours = (self.now.hour % 12) + minutes / 60
        painter.drawText(self.text_rect(center, radius, hours, minutes), Qt.AlignCenter, self.text())

        def hand(value, full, shape, color, edge):
            painter.save()
            painter.translate(center)
            painter.rotate(value / full * 360)
            painter.setPen(QPen(QColor(edge), 1.0) if edge else Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in shape]))
            painter.restore()
        # часовая: широкий наконечник с перехватом, как на рисунке; минутная: тонкая длинная игла
        hl, ml = radius * 0.52, radius * 0.80
        hand(hours, 12, [(0, -hl), (4.6, -hl * 0.55), (3.0, -hl * 0.40), (3.4, -hl * 0.22), (1.6, hl * 0.14),
                         (-1.6, hl * 0.14), (-3.4, -hl * 0.22), (-3.0, -hl * 0.40), (-4.6, -hl * 0.55)],
             self.HOUR, self.FACE)
        hand(minutes, 60, [(0, -ml), (1.5, -ml * 0.6), (1.9, ml * 0.12), (-1.9, ml * 0.12), (-1.5, -ml * 0.6)],
             self.MINUTE, None)
        painter.setPen(QPen(QColor(self.FACE), 1.5))
        painter.setBrush(QColor(self.RING))
        painter.drawEllipse(center, 4.2, 4.2)


class FoxWheel(QWidget):
    """Ласка бежит в колесе, пока идёт таймер. Ласка - нарисованная картинка (art/weasel.png),
    бег - кодом: она пружинит, подпрыгивает в такт и чуть качается, а колесо под ней крутится
    с той же скоростью. Колесо и стойка нарисованы кодом в стиле картинки: индиго с охристыми
    перекладинами, цвета - «Колесо» в «Цвета и темы». Класс зовётся FoxWheel со времён лисы."""

    STRIDE = 14.0            # рад/с - частота шага на обычной скорости

    def __init__(self):
        super().__init__()
        self.setFixedHeight(120)
        self.setToolTip(tr("Пока идёт таймер, ласка бежит"))
        self.running = False
        self.phase = 0.0
        self.angle = 0.0
        self.idle = 0.0          # время для дыхания, хвоста и моргания
        self.boost = 0.0         # ускорение от быстрого набора
        self.speed = 0.0         # плавно разгоняется и тормозит, а не дёргается
        self.jump = None         # сколько секунд идёт прыжок радости
        self.left = None         # сколько осталось таймера, от 1 до 0 - яркая часть обода
        self.sparks = []         # [x, y, vx, vy, жизнь]
        self.clock = QElapsedTimer()
        self.clock.start()
        self.frames = QTimer(self, interval=40, timerType=Qt.PreciseTimer)
        self.frames.timeout.connect(self._frame)
        self.frames.start()

    def set_left(self, share):
        """Сколько осталось таймера (1 - только начали, 0 - вышло, None - таймер не идёт)."""
        self.left = share
        self.update()

    def _move_sparks(self, dt):
        r, cx, cy = self._geometry()
        s = r / 58
        if self.speed > 0.3:
            rate = 1.5 + max(0.0, self.speed - 1.0) * 26          # быстрый набор - больше искр
            if random.random() < rate * dt:
                x = cx - 16 * s + random.uniform(-3, 3) * s
                y = cy + r - 11 * s
                self.sparks.append([x, y, -random.uniform(20, 45) * s * self.speed,
                                    -random.uniform(25, 55) * s, 1.0])
        for spark in self.sparks:
            spark[0] += spark[2] * dt
            spark[1] += spark[3] * dt
            spark[3] += 120 * s * dt                                # падают вниз
            spark[4] -= dt * 1.6
        self.sparks = [sp for sp in self.sparks if sp[4] > 0]

    def set_running(self, on):
        self.running = on
        self.frames.setInterval(16 if on else 40)
        self.update()

    def speed_up(self):
        self.boost = min(self.boost + 0.35, 2.5)

    def celebrate(self):
        self.jump = 0.0
        self.frames.setInterval(16)

    def _frame(self):
        dt = min(self.clock.restart() / 1000, 0.05)
        self.idle += dt
        self.boost *= math.exp(-dt * 1.5)
        target = (1 + self.boost) if self.running else 0.0
        self.speed += (target - self.speed) * min(1.0, dt * 4)          # разгон и торможение
        if self.speed > 0.01:
            self.phase += dt * self.STRIDE * self.speed
            r = self._geometry()[0]
            scale = r / 58
            # лапа проходит около 22 единиц за шаг: колесо уходит назад с той же скоростью
            ground = 22 * scale * self.STRIDE * self.speed / (2 * math.pi)
            self.angle += math.degrees(ground / max(1.0, r - 7)) * dt
        self._move_sparks(dt)
        if self.jump is not None:
            self.jump += dt
            if self.jump > 1.2:
                self.jump = None
                self.frames.setInterval(16 if self.running else 40)
        if not self.visibleRegion().isEmpty():
            self.update()

    RUN_FRAMES, CHEER_FRAMES = 12, 12

    def _drawn_frame(self, wide, ratio):
        """Нарисованный кадр ласки (art/anim/weasel-run, weasel-cheer) или None, если кадров нет.
        Стоит - weasel-stand; бежит прыжками - кадр по фазе шага; радуется - кадры прыжка за 0,6 с."""
        from ..fun.artwork import scaled

        def picture_of(folder, name):                    # в Рождество - кадры в шапке, если они есть
            if C.SEASON == "xmas":
                festive = scaled(f"anim/{folder}-xmas/{name}", wide, ratio)
                if not festive.isNull():
                    return festive
            return scaled(f"anim/{folder}/{name}", wide, ratio)
        if self.jump is not None and self.jump < 0.6:
            frame = min(self.CHEER_FRAMES - 1, int(self.jump / 0.6 * self.CHEER_FRAMES))
            picture = picture_of("weasel-cheer", f"weasel-cheer_{frame:02d}")
            if not picture.isNull():
                return picture, True
        if self.speed > 0.05:
            frame = int(self.phase / (2 * math.pi) * self.RUN_FRAMES) % self.RUN_FRAMES
            picture = picture_of("weasel-run", f"weasel-run_{frame:02d}")
        else:
            picture = picture_of("weasel-run", "weasel-stand")
        return (picture, False) if not picture.isNull() else None

    def _geometry(self):
        """(радиус колеса, центр x, центр y): снизу оставлено место под стойку."""
        r = self.height() / 2 - 8
        return r, self.width() / 2, self.height() / 2 - 4

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r, cx, cy = self._geometry()
        center = QPointF(cx, cy)
        main, second = QColor(C.FOX), QColor(C.FOX_2)
        outline = QPen(second, max(1.2, r / 34))
        outline.setJoinStyle(Qt.RoundJoin)

        # стойка: два столбика и основание - стоят на месте, колесо крутится между ними
        post = r + 3
        p.setPen(outline)
        p.setBrush(main)
        for side in (-1, 1):
            p.drawRoundedRect(QRectF(cx + side * post - 3.2, cy - r * 0.18, 6.4, r * 1.18 + 7), 2, 2)
        p.drawRoundedRect(QRectF(cx - post - 8, cy + r + 3, 2 * post + 16, 5), 2, 2)
        for side in (-1, 1):
            p.drawRoundedRect(QRectF(cx + side * (post + 2) - 4, cy + r + 7.5, 8, 3.2), 1.2, 1.2)

        # середина колеса - тёмное индиго, чтобы ласку было видно и на светлой теме
        inside = QColor(C.mix(main, "#000000", 0.35))
        inside.setAlpha(225)
        p.setPen(Qt.NoPen)
        p.setBrush(inside)
        p.drawEllipse(center, r - 2, r - 2)

        band = max(4.0, r * 0.16)                       # ширина обода с перекладинами
        p.save()
        p.translate(cx, cy)
        p.rotate(self.angle)
        for i in range(6):                              # спицы: охристый контур, индиго внутри
            a = math.radians(i * 60)
            tip = QPointF(math.cos(a) * (r - band), math.sin(a) * (r - band))
            p.setPen(QPen(second, max(3.2, r * 0.075), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(0, 0), tip)
            p.setPen(QPen(main, max(1.6, r * 0.042), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(0, 0), tip)
        ring = QPainterPath()
        ring.addEllipse(QPointF(0, 0), r, r)
        ring.addEllipse(QPointF(0, 0), r - band, r - band)
        p.setPen(Qt.NoPen)
        p.setBrush(main)
        p.drawPath(ring)
        p.setPen(QPen(second, max(1.4, band * 0.32), Qt.SolidLine, Qt.FlatCap))
        for i in range(30):                             # перекладины поперёк обода
            a = math.radians(i * 12)
            ca, sa = math.cos(a), math.sin(a)
            p.drawLine(QPointF(ca * (r - band + 1.3), sa * (r - band + 1.3)), QPointF(ca * (r - 1.3), sa * (r - 1.3)))
        p.setPen(outline)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), r - band, r - band)
        p.restore()

        # наружный контур: тусклый - прошедшее время, яркий - сколько таймера осталось
        box = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        width = max(2.0, r / 18)
        p.setBrush(Qt.NoBrush)                       # иначе обвод зальёт колесо цветом середины
        p.setPen(QPen(C.mix(second, "#000000", 0.55), width))
        p.drawEllipse(center, r, r)
        left = 1.0 if self.left is None else max(0.0, min(1.0, self.left))
        if left > 0:
            p.setPen(QPen(second, width, Qt.SolidLine, Qt.FlatCap if left < 1 else Qt.RoundCap))
            if left >= 1:
                p.drawEllipse(center, r, r)
            else:
                p.drawArc(box, 90 * 16, -int(left * 360 * 16))               # от двенадцати по часовой
        p.setPen(outline)                                                     # ось
        p.setBrush(main)
        p.drawEllipse(center, 4.6, 4.6)
        p.setPen(Qt.NoPen)
        p.setBrush(second)
        p.drawEllipse(center, 2.0, 2.0)

        # ласка: бежит на месте внизу колеса
        s = r / 58
        run = min(1.0, self.speed)
        t = self.phase
        breathe = math.sin(self.idle * 2.0) * 0.6 * (1 - run)
        bob = -abs(math.sin(t)) * 3.0 * run + breathe
        hop = 0.0
        if self.jump is not None:
            if self.jump < 0.6:
                hop = -math.sin(math.pi * self.jump / 0.6) * 18
            elif self.jump < 0.9:
                hop = -math.sin(math.pi * (self.jump - 0.6) / 0.3) * 5
        ox, oy = cx, cy + r - band - 1.5 * s
        lifted = min(1.0, -(bob + hop) / 18) if (bob + hop) < 0 else 0.0
        floor = QRadialGradient(QPointF(ox, oy + 1.2 * s), 30 * s)
        floor.setColorAt(0, QColor(0, 0, 0, int(110 * (1 - 0.6 * lifted))))
        floor.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(floor)
        p.drawEllipse(QPointF(ox, oy + 1.2 * s), 30 * s * (1 - 0.3 * lifted), 4 * s)    # тень
        from ..fun.artwork import scaled
        wide = 1.5 * r                                                         # ласка почти во всё колесо
        ratio = self.devicePixelRatioF()
        drawn = self._drawn_frame(wide, ratio)
        if drawn is not None:
            # нарисованные кадры: бег (цикл из 10 кадров в такт шагу) и прыжок радости
            sprite, cheer = drawn
            tall = wide * sprite.height() / sprite.width()
            p.save()
            p.translate(ox, oy + (0 if cheer else breathe * s))
            p.drawPixmap(QRectF(-wide / 2, -tall, wide, tall), sprite, QRectF(sprite.rect()))
            p.restore()
            sprite = QPixmap()
        else:
            sprite = scaled("weasel", wide, ratio)
        if not sprite.isNull():
            tall = wide * sprite.height() / sprite.width()
            stride = math.sin(2 * t) * run                                    # шаг: тянется и сжимается
            p.save()
            p.translate(ox, oy + (bob + hop) * s)
            p.rotate(math.degrees(0.05 * math.sin(t + 0.6) * run) - (6 if hop < -4 else 0))
            p.scale(1 + 0.045 * stride, 1 - 0.06 * stride + 0.012 * breathe)
            p.drawPixmap(QRectF(-wide / 2, -tall, wide, tall), sprite, QRectF(sprite.rect()))
            p.restore()

        # искры из-под лап, когда печатаешь быстро - внутри колеса
        p.save()
        inner = QPainterPath()
        inner.addEllipse(center, r - band, r - band)
        p.setClipPath(inner)
        for x, y, _vx, _vy, life in self.sparks:
            spark = QColor(second if life > 0.5 else C.mix(second, "#ffffff", 0.5))
            spark.setAlpha(int(255 * min(1.0, life * 2)))
            p.setPen(Qt.NoPen)
            p.setBrush(spark)
            k = 2.4 * s * (0.6 + life)
            p.drawPolygon(QPolygonF([QPointF(x, y - k), QPointF(x + k * 0.5, y), QPointF(x, y + k),
                                     QPointF(x - k * 0.5, y)]))
        p.restore()

        # искры, когда выполнена цель
        if self.jump is not None:
            alpha = max(0, int(255 * (1 - self.jump / 1.2)))
            spark = QColor(second)
            spark.setAlpha(alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(spark)
            for i in range(7):
                a = self.jump * 2.5 + i * (2 * math.pi / 7)
                d = (20 + self.jump * 14) * s
                x, y = ox + math.cos(a) * d, oy - 24 * s + math.sin(a) * d * 0.7
                k = 3.0 * s
                p.drawPolygon(QPolygonF([QPointF(x, y - k), QPointF(x + k * 0.3, y - k * 0.3),
                                         QPointF(x + k, y), QPointF(x + k * 0.3, y + k * 0.3),
                                         QPointF(x, y + k), QPointF(x - k * 0.3, y + k * 0.3),
                                         QPointF(x - k, y), QPointF(x - k * 0.3, y - k * 0.3)]))


class NightVeil(QWidget):
    """Вечером делает цвета теплее и чуть тусклее, накладываясь поверх окна."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.level = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(2500)
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.valueChanged.connect(self._step)

    def _step(self, value):
        self.level = float(value)
        self.update()

    def set_level(self, target, instant=False):
        if instant:
            self.anim.stop()
            self._step(target)
            return
        if abs(target - self.level) < 0.001:
            return
        self.anim.stop()
        self.anim.setStartValue(self.level)
        self.anim.setEndValue(float(target))
        self.anim.start()

    def paintEvent(self, _event):
        if self.level <= 0.001:
            return
        k = self.level * C.NIGHT_STRENGTH
        p = QPainter(self)
        # умножение: чёрное остаётся чёрным, а синий и зелёный уходят - цвета теплеют
        p.setCompositionMode(QPainter.CompositionMode_Multiply)
        dim = 1 - 0.12 * k
        p.fillRect(self.rect(), QColor(int(255 * dim), int(255 * (1 - 0.16 * k) * dim),
                                       int(255 * (1 - 0.42 * k) * dim)))


class RussianLineEdit(QLineEdit):
    def __init__(self, on_foreign):
        super().__init__()
        self.on_foreign = on_foreign
        self.textEdited.connect(self._clean)

    def _clean(self, text):
        if C.ONLY_RUSSIAN and has_foreign(text):
            self.setText("".join(ch for ch in text if not (ch.isalpha() and has_foreign(ch))))
            self.on_foreign()


class RussianTextEdit(QTextEdit):
    def __init__(self, on_foreign):
        super().__init__()
        self.setAcceptRichText(False)
        self.on_foreign = on_foreign

    def keyPressEvent(self, event):
        mods = event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)
        if C.ONLY_RUSSIAN and not mods and has_foreign(event.text()):
            self.on_foreign()
            return
        super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        if C.ONLY_RUSSIAN and source.hasText() and has_foreign(source.text()):
            self.on_foreign()
            return
        super().insertFromMimeData(source)


class FileTree(QTreeWidget):
    """Дерево категорий: перетаскивание файлов и категорий мышкой."""

    def __init__(self, on_drop):
        super().__init__()
        self.on_drop = on_drop
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setIconSize(QSize(22, 28))           # обложка категории - заметным значком
        self.setDropIndicatorShown(True)

    def dropEvent(self, event):
        source = self.currentItem()
        target = self.itemAt(event.position().toPoint())
        where = self.dropIndicatorPosition()
        # перемещение делаем сами, на диске, а дерево потом перерисуется
        event.setDropAction(Qt.IgnoreAction)
        event.accept()
        if source and target and source is not target:
            src = Path(source.data(0, Qt.UserRole))
            dst = Path(target.data(0, Qt.UserRole))
            QTimer.singleShot(0, self, lambda: self.on_drop(src, dst, where))


class SoftButton(QPushButton):
    """Кнопка панели, у которой подсветка под мышкой плавно проявляется и гаснет, а не мигает."""

    def __init__(self, text=""):
        super().__init__(text)
        self.setProperty("soft", True)
        self.glow = 0.0
        self.fade = QVariantAnimation(self)
        self.fade.setDuration(140)
        self.fade.setEasingCurve(QEasingCurve.OutCubic)
        self.fade.valueChanged.connect(self._glow)

    def _glow(self, value):
        self.glow = float(value)
        self.update()

    def _to(self, target):
        self.fade.stop()
        self.fade.setStartValue(self.glow)
        self.fade.setEndValue(target)
        self.fade.setDuration(140 if target else 260)              # гаснет чуть медленнее
        self.fade.start()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._to(1.0)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._to(0.0)

    def paintEvent(self, event):
        if self.glow > 0.01 and not self.isChecked():
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            color = QColor(C.HOVER)
            color.setAlphaF(self.glow)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(self.rect()), 10, 10)
            p.end()
        super().paintEvent(event)


class PanelShadow(QWidget):
    """Мягкая тень под выезжающей панелью: рисуется отдельно, чтобы панель с бегущей лисой
    не перерисовывалась целиком через эффект тени на каждом кадре."""

    SPREAD = 16

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def follow(self, panel):
        g = panel.geometry()
        self.setGeometry(g.adjusted(-self.SPREAD, -self.SPREAD + 4, self.SPREAD, self.SPREAD + 4))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        dark = 0.85 if C.is_light() else 1.0
        inner = QRectF(self.rect()).adjusted(self.SPREAD, self.SPREAD, -self.SPREAD, -self.SPREAD)
        for i in range(self.SPREAD, 0, -2):                 # слои всё прозрачнее к краю
            p.setBrush(QColor(0, 0, 0, int(dark * 7 * (1 - i / (self.SPREAD + 2)) ** 1.5 * 3)))
            p.drawRoundedRect(inner.adjusted(-i, -i, i, i), 16 + i, 16 + i)


class SlidePanel(QFrame):
    """Скруглённая панель, которая выезжает из-за края окна, с мягкой тенью."""

    def __init__(self, parent, side, width):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.side = side
        self.opened = False
        self.quiet = False         # «без отвлечений»: язычок у края не показывается
        self.setFixedWidth(width)
        self.anim = QPropertyAnimation(self, b"pos", self)
        self.anim.setDuration(240)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        # еле заметный язычок у края: подсказывает, что здесь есть панель
        self.hint = QFrame(parent)
        self.hint.setObjectName("Hint")
        self.hint.setFixedSize(4, 56)
        self.hint.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.tabs = True                        # язычок у края можно убрать (Вид → На экране)
        self.anim.finished.connect(self._show_hint)
        self.shadow = PanelShadow(parent)
        self.anim.valueChanged.connect(lambda _v: self.shadow.follow(self))

    def moveEvent(self, event):
        super().moveEvent(event)
        self.shadow.follow(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.shadow.follow(self)

    def _x(self, opened):
        parent_width = self.parentWidget().width()
        if self.side == "left":
            return C.MARGIN if opened else -self.width() - C.MARGIN
        return parent_width - self.width() - C.MARGIN if opened else parent_width + C.MARGIN

    def place(self):
        parent = self.parentWidget()
        self.setFixedHeight(max(120, parent.height() - 2 * C.MARGIN))
        self.anim.stop()
        self.move(self._x(self.opened), C.MARGIN)
        hint_x = 3 if self.side == "left" else parent.width() - 7
        self.hint.move(hint_x, (parent.height() - self.hint.height()) // 2)
        self._show_hint()

    def _show_hint(self):
        self.hint.setVisible(not self.opened and not self.quiet and self.tabs)

    def set_tabs(self, shown):
        self.tabs = shown
        self._show_hint()

    def set_quiet(self, quiet):
        self.quiet = quiet
        if quiet:
            self.set_open(False)
        self._show_hint()

    def set_open(self, value):
        if value == self.opened:
            return
        self.opened = value
        if value:
            self.hint.hide()
        self.shadow.raise_()
        self.raise_()
        self.anim.stop()
        # выезжает быстро и мягко тормозит, уезжает чуть быстрее - так панель не «висит» в воздухе
        self.anim.setDuration(280 if value else 200)
        self.anim.setEasingCurve(QEasingCurve.OutQuint if value else QEasingCurve.InCubic)
        self.anim.setStartValue(self.pos())
        self.anim.setEndValue(QPoint(self._x(value), C.MARGIN))
        self.anim.start()


class Toast(QLabel):
    """Короткое всплывающее сообщение, которое плавно гаснет."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        fade_in = QPropertyAnimation(self.effect, b"opacity", self)
        fade_in.setDuration(180)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_out = QPropertyAnimation(self.effect, b"opacity", self)
        fade_out.setDuration(450)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        self.pause = QPauseAnimation(1400, self)
        self.slide = QPropertyAnimation(self, b"pos", self)
        self.slide.setDuration(260)
        self.slide.setEasingCurve(QEasingCurve.OutCubic)
        appear = QParallelAnimationGroup(self)
        appear.addAnimation(fade_in)
        appear.addAnimation(self.slide)
        self.group = QSequentialAnimationGroup(self)
        self.group.addAnimation(appear)
        self.group.addAnimation(self.pause)
        self.group.addAnimation(fade_out)
        self.group.finished.connect(self.hide)
        self.hide()

    def paintEvent(self, event):
        """Плашка: мягкая тень, скруглённый фон и точка цвета «Важное» слева."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        body = QRectF(self.rect()).adjusted(6, 4, -6, -8)
        p.setPen(Qt.NoPen)
        for i in range(6, 0, -1):
            p.setBrush(QColor(0, 0, 0, 10 + 4 * (6 - i)))
            p.drawRoundedRect(body.adjusted(-i * 0.6, -i * 0.4, i * 0.6, i), body.height() / 2 + i, body.height() / 2 + i)
        fill = QLinearGradient(body.topLeft(), body.bottomLeft())
        fill.setColorAt(0, C.mix(C.PANEL, C.TEXT, 0.06))
        fill.setColorAt(1, QColor(C.PANEL))
        p.setBrush(fill)
        p.setPen(QPen(C.mix(C.BORDER, C.TEXT, 0.15), 1))
        p.drawRoundedRect(body, body.height() / 2, body.height() / 2)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C.IMPORTANT))
        p.drawEllipse(QPointF(body.left() + 15, body.center().y()), 3.2, 3.2)
        p.end()
        super().paintEvent(event)

    def mousePressEvent(self, event):
        action, self._action = getattr(self, "_action", None), None
        if action is not None:
            self.group.stop()
            self.hide()
            action()
        super().mousePressEvent(event)

    def show_message(self, text, ms=1400, action=None):
        """action - что сделать по щелчку по плашке (например, «вернуть»)."""
        self._action = action
        self.setCursor(Qt.PointingHandCursor if action else Qt.ArrowCursor)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, action is None)
        if self.isVisible() and self.text() == text:
            return
        self.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        # чуть выше строки состояния, а не посреди листа
        end = QPoint((parent.width() - self.width()) // 2, parent.height() - self.height() - 34)
        self.group.stop()
        self.slide.setStartValue(end + QPoint(0, 14))
        self.slide.setEndValue(end)
        self.move(end + QPoint(0, 14))
        self.raise_()
        self.show()
        self.pause.setDuration(ms)
        self.group.start()


STREAK_LINES = {
    "cheer": ["Так держать!", "Огонь растёт - и книга тоже", "Ещё день - и глава ближе",
              "Ты в ритме. Не сбавляй", "Книги пишутся вот так - день за днём", "Красиво идёшь",
              "Слово за словом - и вот уже серия", "Завтра огонь ждёт тебя снова"],
    "roast": ["Ну надо же, опять пришёл", "Не зазнавайся, это всего лишь слова",
              "Пиши давай, огонь сам себя не кормит", "Вау. Буквы. Поздравляю",
              "Только попробуй завтра пропустить", "Огонь растёт быстрее твоего сюжета",
              "Неплохо. Для начала", "Ладно, сегодня без нытья - засчитано"],
}
STREAK_MILESTONE = {"cheer": "Огонь вырос! Так держать",
                    "roast": "Ладно. Признаю. Уважаю"}
STREAK_VOICES = {"cheer": "Подбадривает", "roast": "Подкалывает", "quiet": "Молчит"}


def streak_line(count, voice):
    """Что говорит огонёк. Каждые 10 дней огонь подрастает - и говорит про это."""
    if voice not in STREAK_LINES:
        return ""
    if count and count % 10 == 0:
        return STREAK_MILESTONE[voice]
    lines = STREAK_LINES[voice]
    return lines[(count * 7 + 3) % len(lines)]


class PicturePop(QWidget):
    """Картинка над всплывающей плашкой (например, ласка «дай глазам отдохнуть»): мягко
    появляется, стоит, пока видна плашка, и тает. Мышь проходит насквозь."""

    SIDE = 170

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(self.SIDE, self.SIDE)
        self.side = self.SIDE
        self.name, self.opacity = None, 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.valueChanged.connect(self._step)
        self.anim.finished.connect(self.hide)
        self.hide()

    def play(self, name, ms=9000, width=SIDE):
        """False - картинки нет."""
        from ..fun.artwork import pixmap
        source = pixmap(name)
        if source.isNull():
            return False
        self.name, self.side = name, width
        self.setFixedSize(width, int(width * source.height() / source.width()) + 2)
        parent = self.parentWidget()
        self.move((parent.width() - self.width()) // 2, max(0, parent.height() - self.height() - 96))
        self.anim.stop()
        self.anim.setDuration(max(1200, ms + 650))
        self.opacity = 0.0
        self.show()
        self.raise_()
        self.anim.start()
        return True

    def _step(self, value):
        total = self.anim.duration()
        ms = float(value) * total
        self.opacity = min(1.0, ms / 300, max(0.0, (total - ms) / 600))
        self.update()

    def paintEvent(self, _event):
        if not self.name:
            return
        from ..fun.artwork import scaled
        picture = scaled(self.name, self.side, self.devicePixelRatioF())
        if picture.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setOpacity(self.opacity)
        height = self.side * picture.height() / picture.width()
        p.drawPixmap(QRectF(0, self.height() - height, self.side, height), picture, QRectF(picture.rect()))
        p.end()


class EmptyPicture(QWidget):
    """Картинка «пусто» посреди списка (поиск ничего не нашёл, корзина пуста, пометок нет):
    show_picture(имя) - показать, hide() - убрать. Мышь проходит насквозь."""

    def __init__(self, view):
        super().__init__(view.viewport())
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.name = None
        view.viewport().installEventFilter(self)
        self.hide()

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() == QEvent.Resize:
            self.setGeometry(obj.rect())
        return False

    def show_picture(self, name):
        from ..fun.artwork import pixmap
        if pixmap(name).isNull():
            self.hide()
            return False
        self.name = name
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.update()
        return True

    def paintEvent(self, _event):
        from ..fun.artwork import scaled
        if not self.name:
            return
        width = min(320.0, self.width() * 0.75)
        picture = scaled(self.name, width, self.devicePixelRatioF())
        if picture.isNull():
            return
        height = width * picture.height() / picture.width()
        if height > self.height() * 0.8:                 # список низкий - картинку меньше
            width *= self.height() * 0.8 / height
            height = self.height() * 0.8
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setOpacity(0.9)
        top = max(28.0, (self.height() - height) / 2)
        p.drawPixmap(QRectF((self.width() - width) / 2, top, width, height), picture, QRectF(picture.rect()))
        p.end()


class GoalPop(QWidget):
    """Выполнена цель дня или главы: над строкой внизу из одной точки вылетают звёздочки
    и конфетти (нарисованные кадры art/anim/goal), меньше секунды. Мышь проходит насквозь."""

    SIZES = {"day": 300, "chapter": 220}

    def __init__(self, parent):
        super().__init__(parent)
        from ..fun.artwork import Effects
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(320, 300)
        self.effects = Effects(self)
        self.effects.timer.timeout.connect(self._maybe_hide)
        self.hide()

    def play(self, kind="day"):
        """False - кадров нет, праздник обходится надписью."""
        self.effects.clear()
        width = self.SIZES.get(kind, 300)
        if not self.effects.play(f"anim/goal/goal-{kind}", self.width() / 2, self.height() - 4, width,
                                 anchor="bottom"):
            return False
        self.show()
        self.raise_()
        return True

    def _maybe_hide(self):
        if not self.effects.busy:
            self.hide()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        self.effects.paint(p)
        p.end()


class StreakPop(QWidget):
    """Новый засчитанный день серии: огонёк с числом выпрыгивает над строкой внизу,
    чуть подрагивает и тает. Каждые 10 дней подряд огонь подрастает и становится наряднее
    (сердцевина, боковые языки, искры, корона); может подбодрить или подколоть фразой.
    Мышь проходит насквозь, печатать не мешает."""

    DURATION = 3200

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setFixedSize(360, 220)
        self.count, self.label, self.line, self.t = 0, "", "", 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(self.DURATION)
        self.anim.valueChanged.connect(self._step)
        self.anim.finished.connect(self.hide)
        self.hide()

    @staticmethod
    def stage(count):
        """0..5: каждые 10 дней подряд - ступень выше."""
        return max(0, min(5, count // 10))

    def play(self, count, label, line=""):
        self.count, self.label, self.line = count, label, line
        self.anim.stop()
        self.t = 0.0
        self.show()
        self.raise_()
        self.anim.start()

    def _step(self, value):
        self.t = float(value)
        self.update()

    def _state(self):
        """(масштаб, прозрачность, сдвиг вверх) в момент t: выпрыгнул, осел, постоял, растаял."""
        t = self.t
        if t < 0.14:
            k = t / 0.14
            back = 1 + 2.4 * (k - 1) ** 3 + 1.4 * (k - 1) ** 2       # перелёт за 1 и обратно
            return 0.4 + 0.75 * back, min(1.0, k * 2), 0.0
        if t < 0.24:
            k = (t - 0.14) / 0.1
            return 1.15 - 0.15 * k, 1.0, 0.0
        if t < 0.78:
            return 1.0, 1.0, 0.0
        k = (t - 0.78) / 0.22
        return 1.0 - 0.08 * k, 1.0 - k, 22 * k

    BASE_Y = 116                     # где середина огонька по высоте окошка
    FLAME_FPS = 24

    def _paint_drawn(self, scale, opacity, rise, stage):
        """Нарисованное пламя (art/anim/flame/flame-<ступень>_NN): горит циклом, число - в светлом
        пятне посередине, подписи - под ним. False - кадров нет, рисуем по-старому."""
        from ..fun.artwork import scaled
        size = 150.0                                     # ступени уже нарисованы разного размера
        frame = int(self.t * self.DURATION / 1000 * self.FLAME_FPS) % 12
        picture = scaled(f"anim/flame/flame-{stage}_{frame:02d}", size * 1.15, self.devicePixelRatioF())
        if picture.isNull():
            return False
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setOpacity(max(0.0, opacity))
        p.translate(self.width() / 2, self.BASE_Y - rise)
        p.scale(scale, scale)
        bottom = 40.0                                     # низ пламени (в кадре он на 96% высоты)
        top = bottom - size * 246 / 256
        p.drawPixmap(QRectF(-size / 2, top, size, size), picture, QRectF(picture.rect()))
        font = QFont(C.FONT_FAMILY, 14 + stage)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#2a2680"))                       # тёмное число на светлом пятне
        spot = top + size * 158 / 256
        p.drawText(QRectF(-40, spot - 20, 80, 40), Qt.AlignCenter, str(self.count))
        font.setPointSize(11)
        p.setFont(font)
        p.setPen(QColor("#d4a02e") if not C.is_light() else QColor("#2e2a6e"))
        p.drawText(QRectF(-170, bottom + 4, 340, 24), Qt.AlignCenter, self.label)
        if self.line:
            font.setPointSize(10)
            font.setBold(False)
            font.setItalic(True)
            p.setFont(font)
            p.setPen(QColor(C.TEXT))
            p.drawText(QRectF(-175, bottom + 26, 350, 22), Qt.AlignCenter, self.line)
        p.end()
        return True

    @staticmethod
    def _drop(height, width, flicker=0.0, lean=0.0):
        """Язык пламени: капля острием вверх. lean - наклон кончика вбок."""
        path = QPainterPath()
        tip = QPointF(lean * height * 0.35, -height * (1 + flicker))
        path.moveTo(tip)
        path.cubicTo(width * 0.45 + lean * 6, -height * 0.48, width * 0.65, -height * 0.09, width * 0.57, height * 0.26)
        path.cubicTo(width * 0.48, height * 0.65, -width * 0.48, height * 0.65, -width * 0.57, height * 0.26)
        path.cubicTo(-width * 0.65, -height * 0.09, -width * 0.45 + lean * 6, -height * 0.48, tip.x(), tip.y())
        return path

    def paintEvent(self, _event):
        if not self.count:
            return
        import math
        scale, opacity, rise = self._state()
        stage = self.stage(self.count)
        grow = 1 + 0.11 * stage
        if self._paint_drawn(scale, opacity, rise, stage):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(max(0.0, opacity))
        p.translate(self.width() / 2, self.BASE_Y - rise)
        p.scale(scale * grow, scale * grow)
        t = self.t
        flicker = math.sin(t * 40) * 0.04                              # язычок пламени дышит
        ochre, gold, indigo = QColor("#d4a02e"), QColor("#f6d27a"), QColor("#2e2a6e")
        glow = QColor(ochre)
        glow.setAlpha(50 + 6 * stage)
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(0, 0), 40, 42)
        if stage >= 4:                                                 # жар: дрожащий ореол над огнём
            heat = QColor(gold)
            heat.setAlpha(int(30 + 14 * math.sin(t * 25)))
            p.setBrush(heat)
            p.drawEllipse(QPointF(0, -26), 26, 30)
        if stage >= 2:                                                 # боковые языки за основным
            for side in (-1, 1):
                p.save()
                p.translate(side * 20, 8)
                p.rotate(side * 16)
                tongue = self._drop(30, 30, math.sin(t * 33 + side) * 0.06, side * 0.3)
                fill = QLinearGradient(0, 18, 0, -30)
                fill.setColorAt(0.0, QColor("#3b3590"))
                fill.setColorAt(0.7, ochre)
                fill.setColorAt(1.0, gold)
                p.setPen(QPen(ochre, 1.6))
                p.setBrush(fill)
                p.drawPath(tongue)
                p.restore()
        # основной огонёк: индиго внизу (там число) переходит в охру и светлое золото к кончику
        path = self._drop(46, 52, flicker)
        fill = QLinearGradient(0, 30, 0, -46)
        fill.setColorAt(0.0, indigo)
        fill.setColorAt(0.42, QColor("#3b3590"))
        fill.setColorAt(0.62, ochre)
        fill.setColorAt(1.0, gold)
        p.setPen(QPen(ochre, 2.2))
        p.setBrush(fill)
        p.drawPath(path)
        if stage >= 5:                                                 # корона: три языка поверх
            for side, lean in ((-1, -0.5), (0, 0.0), (1, 0.5)):
                p.save()
                p.translate(side * 9, -40 + abs(side) * 6)
                tongue = self._drop(16, 10, math.sin(t * 50 + side * 2) * 0.1, lean)
                p.setPen(Qt.NoPen)
                p.setBrush(gold)
                p.drawPath(tongue)
                p.restore()
        if stage >= 1:                                                 # светлая сердцевина над числом
            p.save()
            p.translate(0, -12)
            core = self._drop(22, 18, -flicker * 1.5)
            p.setPen(Qt.NoPen)
            core_fill = QLinearGradient(0, 10, 0, -22)
            core_fill.setColorAt(0.0, QColor(246, 210, 122, 0))
            core_fill.setColorAt(1.0, QColor("#fff3c9"))
            p.setBrush(core_fill)
            p.drawPath(core)
            p.restore()
        if stage >= 3:                                                 # искры летят вверх
            p.setPen(Qt.NoPen)
            rnd = random.Random(self.count)
            for k in range(4 + stage * 2):
                phase = (t * (1.4 + rnd.random()) + rnd.random()) % 1.0
                x = rnd.uniform(-30, 30) + math.sin(phase * 6 + k) * 6
                y = -30 - phase * 70
                spark = QColor(gold)
                spark.setAlphaF(max(0.0, 1 - phase))
                p.setBrush(spark)
                p.drawEllipse(QPointF(x, y), 2.2 - phase, 2.2 - phase)
        p.resetTransform()
        p.setOpacity(max(0.0, opacity))
        p.translate(self.width() / 2, self.BASE_Y - rise)
        p.scale(scale, scale)
        font = QFont(C.FONT_FAMILY, 15 + stage)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(-30, -8 * grow, 60, 30), Qt.AlignCenter, str(self.count))
        font.setPointSize(11)
        p.setFont(font)
        p.setPen(QColor("#d4a02e") if not C.is_light() else QColor("#2e2a6e"))
        top = 34 * grow
        p.drawText(QRectF(-170, top, 340, 24), Qt.AlignCenter, self.label)
        if self.line:
            font.setPointSize(10)
            font.setBold(False)
            font.setItalic(True)
            p.setFont(font)
            p.setPen(QColor(C.TEXT))
            p.drawText(QRectF(-175, top + 22, 350, 22), Qt.AlignCenter, self.line)
        p.end()


class EmptyHint(QWidget):
    """Пустая страница: ласка и ворон и подсказка, с чего начать. Стоит поверх пустого текста,
    мышь и клавиатура проходят насквозь; исчезает с первой буквой."""

    def __init__(self, viewport):
        super().__init__(viewport)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lines = ("Чистый лист.", "Начни печатать здесь - или создай главу слева, у края окна.")
        viewport.installEventFilter(self)            # страница меняет размер - картинка встаёт по центру
        self.hide()

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() == QEvent.Resize:
            self.place()
        return False

    def place(self):
        parent = self.parentWidget()
        self.setGeometry(parent.rect())

    def paintEvent(self, _event):
        from ..fun.artwork import scaled
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        # размер страницы - по самой странице: её поля (колонка текста) меняются без события Resize
        area = self.parentWidget().rect()
        if self.geometry() != area:
            QTimer.singleShot(0, self, self.place)
        width, height = area.width(), area.height()
        wide = min(360.0, width * 0.5)
        picture = scaled("empty", wide, self.devicePixelRatioF())
        tall = 0.0 if picture.isNull() else wide * picture.height() / picture.width()
        top = max(10.0, height * 0.42 - tall / 2 - 30)
        if not picture.isNull():
            p.setOpacity(0.9)
            p.drawPixmap(QRectF((width - wide) / 2, top, wide, tall), picture, QRectF(picture.rect()))
            p.setOpacity(1.0)
        font = QFont(C.FONT_FAMILY, 13)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(C.TEXT))
        y = top + tall + 16
        p.drawText(QRectF(0, y, width, 26), Qt.AlignHCenter | Qt.AlignVCenter, self.lines[0])
        p.setFont(QFont(C.FONT_FAMILY, 10))
        p.setPen(QColor(C.DIM))
        p.drawText(QRectF(20, y + 28, width - 40, 40), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                   self.lines[1])
