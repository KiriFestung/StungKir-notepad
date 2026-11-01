# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Антистресс (F12): пупырка, мячик, спиннер, песок с граблями, тумблеры, блинчики и блоки. Отдельное окошко -
на экране ничего не занимает: открылось по клавише, помял, закрыл и пишешь дальше."""

import math
import random
import time

from PySide6.QtCore import QEasingCurve, QElapsedTimer, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QWidget

from ..core import config as C
from ..ui.dialogs import Sheet
from ..core.i18n import tr

COLUMNS, ROWS = 9, 6
def _body():
    """Цвет «тела» игрушек - из темы (у основной - индиго)."""
    return C.toy_colors()["body"]


def _glow():
    """Цвет огонька - из темы (у основной - охра)."""
    return C.toy_colors()["glow"]


class BubbleWrap(QWidget):
    """Лист пупырки: щёлкни по пузырьку - лопнет. Можно вести мышью с зажатой кнопкой - лопаются подряд."""

    def __init__(self, on_pop=None):
        super().__init__()
        self.on_pop = on_pop
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.PointingHandCursor)
        self.popped_total = 0
        self.clock = time.monotonic
        self.popping = {}                       # пузырь -> когда лопнул (пока играет «лоп»)
        self.pop_timer = QTimer(self, timerType=Qt.PreciseTimer)
        self.pop_timer.setInterval(33)
        self.pop_timer.timeout.connect(self._pop_tick)
        self.refill()

    POP_FPS = 30

    def refill(self):
        self.popped = set()
        self.popping = {}
        cells = [(c, r) for c in range(COLUMNS) for r in range(ROWS)]
        self.wobble = {key: random.uniform(-0.06, 0.06) for key in cells}
        # какой из трёх рисунков у пузырька - случайно у каждого (раньше выбор зависел только
        # от столбца, и в ряду картинки шли одним и тем же узором)
        self.kind = {key: random.randrange(3) for key in cells}
        self.update()

    def cell(self):
        return min(self.width() / COLUMNS, self.height() / ROWS)

    def _origin(self):
        size = self.cell()
        return QPointF((self.width() - size * COLUMNS) / 2, (self.height() - size * ROWS) / 2)

    def bubble_at(self, point):
        size = self.cell()
        origin = self._origin()
        col = int((point.x() - origin.x()) // size)
        row = int((point.y() - origin.y()) // size)
        if not (0 <= col < COLUMNS and 0 <= row < ROWS):
            return None
        center = origin + QPointF((col + 0.5) * size, (row + 0.5) * size)
        if (point - center).manhattanLength() > size * 0.55:
            return None
        return col, row

    def pop(self, key):
        if key is None or key in self.popped:
            return False
        self.popped.add(key)
        self.popping[key] = self.clock()
        if not self.pop_timer.isActive():
            self.pop_timer.start()
        self.popped_total += 1
        if self.on_pop:
            self.on_pop()
        self.update()
        return True

    def pop_frame(self, key):
        """Кадр «лопа» у этого пузыря (0..5) или None - уже лопнул совсем."""
        start = self.popping.get(key)
        if start is None:
            return None
        index = int((self.clock() - start) * self.POP_FPS)
        return index if index < 6 else None

    def _pop_tick(self):
        self.popping = {key: start for key, start in self.popping.items() if self.pop_frame(key) is not None}
        if not self.popping:
            self.pop_timer.stop()
        self.update()

    def all_popped(self):
        return len(self.popped) == COLUMNS * ROWS

    def mousePressEvent(self, event):
        self.pop(self.bubble_at(event.position()))

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.pop(self.bubble_at(event.position()))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        size = self.cell()
        origin = self._origin()
        sheet = QRectF(origin.x() - 6, origin.y() - 6, size * COLUMNS + 12, size * ROWS + 12)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(200, 225, 255, 28))                      # сама плёнка
        p.drawRoundedRect(sheet, 10, 10)
        from .artwork import scaled
        ratio = self.devicePixelRatioF()
        whole = [scaled(f"bubble-{k}", size * 0.86, ratio) for k in range(3)]
        popped = [scaled(f"bubble-popped-{k}", size * 0.86, ratio) for k in range(3)]
        if not any(picture.isNull() for picture in whole + popped):
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            for col in range(COLUMNS):
                for row in range(ROWS):
                    center = origin + QPointF((col + 0.5) * size, (row + 0.5) * size)
                    k = self.kind[(col, row)]
                    picture = popped[k] if (col, row) in self.popped else whole[k]
                    frame = self.pop_frame((col, row))
                    if frame is not None:                          # лопается прямо сейчас
                        moving = scaled(f"anim/bubble-pop/bubble-{k}-pop_{frame:02d}", size * 0.86, ratio)
                        picture = picture if moving.isNull() else moving
                    side = size * (0.86 + self.wobble[(col, row)] * 0.4)
                    p.save()
                    p.translate(center)
                    p.rotate(self.wobble[(col, row)] * 900)       # пузырьки чуть по-разному повёрнуты
                    p.drawPixmap(QRectF(-side / 2, -side / 2, side, side), picture, QRectF(picture.rect()))
                    p.restore()
            p.end()
            return
        for col in range(COLUMNS):
            for row in range(ROWS):
                center = origin + QPointF((col + 0.5) * size, (row + 0.5) * size)
                radius = size * (0.38 + self.wobble[(col, row)] * 0.3)
                if (col, row) in self.popped:
                    # лопнувший: плоский, мятый, с трещинкой
                    p.setBrush(QColor(200, 225, 255, 18))
                    p.setPen(QPen(QColor(220, 235, 255, 60), 1))
                    p.drawEllipse(center, radius * 0.9, radius * 0.75)
                    crack = QPainterPath(center + QPointF(-radius * 0.5, -radius * 0.1))
                    crack.lineTo(center + QPointF(-radius * 0.1, radius * 0.15))
                    crack.lineTo(center + QPointF(radius * 0.2, -radius * 0.2))
                    crack.lineTo(center + QPointF(radius * 0.5, radius * 0.05))
                    p.setBrush(Qt.NoBrush)
                    p.drawPath(crack)
                    continue
                gloss = QRadialGradient(center - QPointF(radius * 0.35, radius * 0.4), radius * 1.3)
                gloss.setColorAt(0.0, QColor(255, 255, 255, 190))
                gloss.setColorAt(0.25, QColor(220, 238, 255, 90))
                gloss.setColorAt(1.0, QColor(170, 200, 240, 40))
                p.setBrush(gloss)
                p.setPen(QPen(QColor(230, 242, 255, 110), 1.2))
                p.drawEllipse(center, radius, radius)
        p.end()


class SquishBall(QWidget):
    """Мячик-антистресс. Зажми и держи - сминается тем сильнее, чем дольше держишь; отпусти - пружинит.
    Схвати и потащи - мячик в руке; брось - летит, отскакивает от стенок и пола, сплющивается
    от удара и стучит."""

    GRAVITY = 2600.0          # точек в секунду за секунду
    BOUNCE = 0.72             # сколько скорости остаётся после отскока
    DRAG_START = 8            # на сколько точек сдвинуть мышь, чтобы это был не «сжать», а «схватить»
    DUST_SPEED = 1100         # с какой скорости удар о пол поднимает пыль

    def __init__(self, on_bounce=None):
        super().__init__()
        self.on_bounce = on_bounce
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.OpenHandCursor)
        from .artwork import Effects
        self.dust = Effects(self)              # пыльное колечко от сильного удара о пол
        self.squeeze = 0.0                     # 0 - круглый, 1 - сплющен до предела
        self.squash_axis = 1                   # 1 - сплющен сверху вниз (пол), 0 - с боков (стенка)
        self.press_point = QPointF()
        self.held = QElapsedTimer()
        self.grow = QTimer(self, interval=16, timerType=Qt.PreciseTimer)
        self.grow.timeout.connect(self._grow)
        self.spring = QVariantAnimation(self)
        self.spring.setDuration(900)
        self.spring.setEasingCurve(QEasingCurve.OutElastic)
        self.spring.valueChanged.connect(self._set)
        self.squeezes = 0
        self.bounces = 0
        self.pos = None                        # центр мячика; None - лежит на месте по умолчанию
        self.velocity = QPointF()
        self.angle = 0.0
        self.dragging = False
        self.grab_offset = QPointF()
        self.trail = []                        # последние точки мыши - из них скорость броска
        self.clock = QElapsedTimer()
        self.physics = QTimer(self, interval=16, timerType=Qt.PreciseTimer)
        self.physics.timeout.connect(self._step)

    # ---- размеры ----
    def radius(self):
        return min(self.width(), self.height()) * 0.2

    def floor(self):
        return self.height() - 18

    def center(self):
        if self.pos is None:
            return QPointF(self.width() / 2, self.floor() - self.radius())
        return self.pos

    def _set(self, value):
        self.squeeze = float(value)
        self.update()

    def _grow(self):
        self.squeeze = min(1.0, self.held.elapsed() / 600)
        self.update()

    def _on_ball(self, point):
        c, r = self.center(), self.radius()
        return (point.x() - c.x()) ** 2 + (point.y() - c.y()) ** 2 <= (r * 1.15) ** 2

    # ---- мышь ----
    def mousePressEvent(self, event):
        self.spring.stop()
        self.squash_axis = 1
        self.press_point = event.position()
        self.press_start = event.position()
        self.on_ball = self._on_ball(event.position())
        self.dragging = False
        self.held.start()
        self.grow.start()
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not event.buttons() & Qt.LeftButton:
            return
        point = event.position()
        self.press_point = point
        if not self.dragging and self.on_ball and \
                (point - self.press_start).manhattanLength() > self.DRAG_START:
            self.dragging = True                     # схватили: сжатие отменяется, мячик в руке
            self.grow.stop()
            self.squeeze = 0.0
            self.physics.stop()
            self.grab_offset = self.center() - self.press_start
            self.trail = []
            self.clock.start()
        if self.dragging:
            self.pos = self._clamp(point + self.grab_offset)
            self.trail.append((self.clock.elapsed(), QPointF(self.pos)))
            self.trail = self.trail[-6:]
        self.update()

    def mouseReleaseEvent(self, _event):
        self.grow.stop()
        self.setCursor(Qt.OpenHandCursor)
        if self.dragging:
            self.dragging = False
            self.throw(self._throw_speed())
            return
        if self.squeeze > 0.05:
            self.squeezes += 1
        self._spring_back(900)

    def _throw_speed(self):
        if len(self.trail) < 2:
            return QPointF()
        (t0, p0), (t1, p1) = self.trail[0], self.trail[-1]
        seconds = max(0.016, (t1 - t0) / 1000)
        speed = (p1 - p0) / seconds
        limit = 4000.0
        length = math.hypot(speed.x(), speed.y())
        return speed * (limit / length) if length > limit else speed

    def throw(self, velocity):
        """Бросок с заданной скоростью (точек в секунду)."""
        if self.pos is None:
            self.pos = self.center()
        self.velocity = QPointF(velocity)
        self.clock.start()
        self.physics.start()

    def _clamp(self, point):
        r = self.radius()
        return QPointF(min(max(point.x(), r), self.width() - r), min(max(point.y(), r), self.floor() - r))

    def _spring_back(self, ms):
        self.spring.stop()
        self.spring.setDuration(ms)
        self.spring.setStartValue(self.squeeze)
        self.spring.setEndValue(0.0)
        self.spring.start()

    def _hit(self, speed, axis):
        if speed < 90:
            return
        self.bounces += 1
        self.squash_axis = axis
        self.squeeze = min(0.55, speed / 3200)
        self._spring_back(380)
        if self.on_bounce:
            self.on_bounce(min(1.0, speed / 2200))

    def _step(self):
        dt = min(0.04, max(0.001, self.clock.restart() / 1000)) if self.clock.isValid() else 0.016
        r = self.radius()
        x, y = self.pos.x(), self.pos.y()
        vx, vy = self.velocity.x(), self.velocity.y() + self.GRAVITY * dt
        x += vx * dt
        y += vy * dt
        if x < r or x > self.width() - r:
            x = r if x < r else self.width() - r
            self._hit(abs(vx), 0)
            vx = -vx * self.BOUNCE
        if y < r:
            y = r
            self._hit(abs(vy), 1)
            vy = -vy * self.BOUNCE
        bottom = self.floor() - r
        on_floor = False
        if y >= bottom:
            y = bottom
            if vy > 0:
                if vy > self.DUST_SPEED:
                    self.dust.play("anim/ball/ball-dust", x, self.floor() + 3, r * 3.4, anchor="bottom",
                                   opacity=min(1.0, vy / 2600))
                self._hit(vy, 1)
                vy = -vy * self.BOUNCE
            if abs(vy) < 60:
                vy, on_floor = 0.0, True
        if on_floor:
            vx *= 0.94 ** (dt * 60)                 # катится и тормозит о стол
        self.angle += math.degrees(vx * dt / max(r, 1))
        self.pos, self.velocity = QPointF(x, y), QPointF(vx, vy)
        if on_floor and abs(vx) < 8:
            self.velocity = QPointF()
            self.physics.stop()
        self.update()

    def resizeEvent(self, event):
        if self.pos is not None:
            self.pos = self._clamp(self.pos)
        super().resizeEvent(event)

    # ---- рисование ----
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        radius = self.radius()
        center = self.center()
        s = self.squeeze                       # пружина может «перелететь» в минус - мячик вытягивается
        squash, stretch = 1 - 0.38 * s, 1 + 0.32 * s
        rx, ry = (radius * stretch, radius * squash) if self.squash_axis == 1 else (radius * squash, radius * stretch)
        height = max(0.0, self.floor() - (center.y() + radius))
        shadow_scale = max(0.25, 1 - height / max(1.0, self.height()))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, int(80 * shadow_scale)))
        p.drawEllipse(QPointF(center.x(), self.floor() + 2), rx * 0.9 * shadow_scale, radius * 0.12 * shadow_scale)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        self.dust.paint(p)
        if self.squash_axis == 1:                    # сплющивается к тому, обо что ударился
            body_center = QPointF(center.x(), center.y() + (radius - ry))
        else:
            side = -1 if center.x() < self.width() / 2 else 1
            body_center = QPointF(center.x() + side * (radius - rx), center.y())
        from .artwork import scaled
        picture = scaled("ball", 2 * radius, self.devicePixelRatioF())
        if not picture.isNull():                 # нарисованный мячик (индиго, охристый блик) мнётся целиком
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.save()
            p.translate(body_center)
            p.scale(rx / radius, ry / radius)
            p.rotate(self.angle)
            p.drawPixmap(QRectF(-radius, -radius, 2 * radius, 2 * radius), picture, QRectF(picture.rect()))
            p.restore()
        else:
            color = QColor(C.IMPORTANT)
            fill = QRadialGradient(body_center - QPointF(rx * 0.35, ry * 0.45), max(rx, ry) * 1.4)
            fill.setColorAt(0, color.lighter(165))
            fill.setColorAt(0.5, color)
            fill.setColorAt(1, color.darker(170))
            p.setBrush(fill)
            p.drawEllipse(body_center, rx, ry)
        inside = ((self.press_point.x() - body_center.x()) / max(rx, 1)) ** 2 + \
            ((self.press_point.y() - body_center.y()) / max(ry, 1)) ** 2 < 0.8
        if s > 0.05 and self.grow.isActive() and inside:   # вмятина от пальца - только на самом мячике
            dent = QRadialGradient(self.press_point, radius * 0.35)
            dent.setColorAt(0, QColor(0, 0, 0, int(90 * s)))
            dent.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(dent)
            p.drawEllipse(self.press_point, radius * 0.35, radius * 0.35)
        p.end()


class Spinner(QWidget):
    """Спиннер: возьми мышью и толкни - крутится долго, плавно тормозит и тихо шуршит.
    Схватил на ходу - остановил: пока держишь, он идёт ровно за рукой."""

    FRICTION = 22.0            # градусов в секунду за секунду - сухое трение подшипника
    DRAG = 0.018               # и сопротивление воздуха: доля скорости в секунду
    MAX_SPEED = 3200.0         # градусов в секунду (около 530 оборотов в минуту)

    def __init__(self, on_whirr=None):
        super().__init__()
        self.on_whirr = on_whirr
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.OpenHandCursor)
        self.angle = 0.0
        self.speed = 0.0                       # градусов в секунду
        self.top_rpm = 0
        self.last = None                       # держат: (угол руки, когда)
        self.samples = []                      # последние положения руки: (секунды, угол без скачков)
        self.clock = QElapsedTimer()
        self.hand = QElapsedTimer()
        self.since_sound = 0.0
        self.timer = QTimer(self, interval=16, timerType=Qt.PreciseTimer)
        self.timer.timeout.connect(self._step)

    def rpm(self):
        return abs(self.speed) / 6

    def _polar(self, point):
        c = QPointF(self.width() / 2, self.height() / 2)
        return math.degrees(math.atan2(point.y() - c.y(), point.x() - c.x()))

    def mousePressEvent(self, event):
        self.hand.start()
        self.last = self._polar(event.position())
        self.samples = [(0.0, self.angle)]
        self.speed = 0.0                                   # схватил - остановил
        self.setCursor(Qt.ClosedHandCursor)
        self.update()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self.last is None:
            return
        now = self._polar(event.position())
        delta = (now - self.last + 180) % 360 - 180
        self.last = now
        self.angle += delta                                # спиннер идёт ровно за рукой
        t = self.hand.elapsed() / 1000
        self.samples.append((t, self.samples[-1][1] + delta))
        self.samples = [sample for sample in self.samples if t - sample[0] <= 0.12]
        self.update()

    def mouseReleaseEvent(self, _event):
        if self.last is None:
            return
        self.last = None
        self.setCursor(Qt.OpenHandCursor)
        t = self.hand.elapsed() / 1000
        recent = [sample for sample in self.samples if t - sample[0] <= 0.12]
        if len(recent) >= 2 and recent[-1][0] - recent[0][0] > 0.005 and t - recent[-1][0] < 0.08:
            # скорость - по последней десятой секунды движения руки (резкий рывок в конце не обманет)
            speed = (recent[-1][1] - recent[0][1]) / (recent[-1][0] - recent[0][0])
            self.flick(speed)

    def flick(self, speed):
        self.speed = max(-self.MAX_SPEED, min(self.MAX_SPEED, speed))
        self.spin()

    def spin(self):
        self.top_rpm = max(self.top_rpm, int(self.rpm()))
        if not self.timer.isActive():
            self.clock.start()
            self.timer.start()

    def _step(self):
        dt = min(0.05, self.clock.restart() / 1000) if self.clock.isValid() else 0.016
        if self.last is not None:                          # держат рукой - не крутим сами
            return
        sign = 1 if self.speed > 0 else -1
        slow = (self.FRICTION + abs(self.speed) * self.DRAG) * dt
        self.speed = sign * max(0.0, abs(self.speed) - slow)
        self.angle = (self.angle + self.speed * dt) % 360
        self.since_sound += dt
        if self.on_whirr and self.rpm() > 40 and self.since_sound > 0.45:
            self.since_sound = 0.0
            self.on_whirr(min(1.0, self.rpm() / 450))
        if self.speed == 0.0:
            self.timer.stop()
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        size = min(self.width(), self.height()) * 0.36
        p.translate(c)
        blur = min(1.0, self.rpm() / 400)
        for ghost in range(3 if blur > 0.3 else 1):       # быстро - лёгкий смаз
            p.save()
            p.rotate(self.angle - ghost * self.speed * 0.006)
            p.setOpacity(1.0 if ghost == 0 else 0.25 * blur)
            body = QPainterPath()
            for k in range(3):
                a = math.radians(k * 120 - 90)
                lobe = QPointF(math.cos(a), math.sin(a)) * size * 0.62
                body.addEllipse(lobe, size * 0.36, size * 0.36)
            body.addEllipse(QPointF(), size * 0.5, size * 0.5)
            body = body.simplified()
            p.setPen(QPen(_glow(), 2.4))
            p.setBrush(_body())
            p.drawPath(body)
            for k in range(3):
                a = math.radians(k * 120 - 90)
                lobe = QPointF(math.cos(a), math.sin(a)) * size * 0.62
                p.setBrush(_body().darker(220))
                p.setPen(QPen(_glow(), 2))
                p.drawEllipse(lobe, size * 0.22, size * 0.22)
                p.setBrush(_glow().lighter(115))
                p.setPen(Qt.NoPen)
                p.drawEllipse(lobe, size * 0.08, size * 0.08)
            p.restore()
        p.setOpacity(1.0)
        p.setBrush(_glow())
        p.setPen(QPen(_body().darker(130), 2))
        p.drawEllipse(QPointF(), size * 0.17, size * 0.17)          # центр под пальцем не крутится
        p.end()


class ZenSand(QWidget):
    """Сад камней: веди мышью с зажатой кнопкой - грабли оставляют ровные бороздки, камни они
    обходят (поднимаются над ними). Вокруг камней - круги, как в настоящем саду. «Разровнять» - чисто."""

    TINES = 5
    SAND, SAND_DARK, SAND_LIGHT = QColor("#d8c59b"), QColor("#a88d5e"), QColor("#f6ead0")

    def __init__(self, on_rake=None):
        super().__init__()
        self.on_rake = on_rake
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(self._rake_cursor())
        self.lines = []                 # готовые бороздки: списки точек в долях ширины и высоты
        self.current = []               # бороздка, которую ведут сейчас
        self.stones = []
        self.strokes = 0
        self.base = QImage()
        self._sound_clock = QElapsedTimer()
        self.smooth()

    # ---------------- состояние ----------------
    def smooth(self):
        """Разровнять: новые камни (2-3, не впритык друг к другу) и круги вокруг них."""
        self.lines, self.current, self.strokes = [], [], 0
        stones = []
        for _ in range(60):
            if len(stones) >= random.randint(2, 3):
                break
            x, y, r = random.uniform(0.18, 0.82), random.uniform(0.25, 0.75), random.uniform(0.05, 0.075)
            if all(math.hypot(x - a, (y - b) * 0.75) > 0.22 for a, b, _r in stones):
                stones.append((x, y, r))
        self.stones = stones
        self.stone_kinds = random.sample(range(1, 5), len(stones))   # какой из четырёх рисунков
        self.base = QImage()
        self.update()

    @staticmethod
    def _rake_cursor():
        """Курсор - маленькие грабли (art/rake), остриё - середина ряда зубьев; без картинки - крестик."""
        from PySide6.QtGui import QCursor
        from .artwork import pixmap
        picture = pixmap("rake")
        if picture.isNull():
            return QCursor(Qt.CrossCursor)
        small = picture.scaledToWidth(44, Qt.SmoothTransformation)
        return QCursor(small, 22, int(small.height() * 112 / 128))

    def _side(self):
        return max(1.0, min(self.width(), self.height()))

    def _gap(self):
        return max(6.0, self._side() * 0.024)

    def _px(self, point):
        return QPointF(point[0] * self.width(), point[1] * self.height())

    # ---------------- мышь ----------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.current = [self._norm(event.position())]
            self._sound_clock.restart()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or not self.current:
            return
        point = event.position()
        last = self._px(self.current[-1])
        step = math.hypot(point.x() - last.x(), point.y() - last.y())
        if step < 4:
            return
        self.current.append(self._norm(point))
        if self.on_rake and self._sound_clock.elapsed() > 170:
            self._sound_clock.restart()
            self.on_rake(min(1.0, 0.35 + step / 40))
        self.update()

    def mouseReleaseEvent(self, _event):
        self.finish_stroke()

    def finish_stroke(self):
        if len(self.current) >= 2:
            self.lines.append(self.current)
            self.strokes += 1
            if not self.base.isNull():
                p = QPainter(self.base)
                p.setRenderHint(QPainter.Antialiasing)
                self._groove(p, [self._px(q) for q in self.current])
                p.end()
        self.current = []
        self.update()

    def rake(self, a, b):
        """Провести грабли по прямой от a к b (для проверок и подсказки)."""
        self.current = [self._norm(a), self._norm(b)]
        self.finish_stroke()

    def _norm(self, point):
        return (point.x() / max(1, self.width()), point.y() / max(1, self.height()))

    # ---------------- рисование ----------------
    def _tine_paths(self, points):
        """Пять параллельных линий зубьев; где зуб над камнем - линия прерывается."""
        if len(points) < 2:
            return []
        gap, side = self._gap(), self._side()
        stones = [(self._px((x, y)), r * side * 1.12 + gap * 0.5) for x, y, r in self.stones]
        normals = []
        for i in range(len(points)):
            a, b = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
            dx, dy = b.x() - a.x(), b.y() - a.y()
            length = math.hypot(dx, dy) or 1.0
            normals.append(QPointF(-dy / length, dx / length))
        paths = []
        for k in range(self.TINES):
            off = (k - (self.TINES - 1) / 2) * gap
            run = []
            for point, normal in zip(points, normals):
                q = point + normal * off
                if any(math.hypot(q.x() - c.x(), (q.y() - c.y()) * 1.35) < radius for c, radius in stones):
                    if len(run) > 1:
                        paths.append(run)
                    run = []
                else:
                    run.append(q)
            if len(run) > 1:
                paths.append(run)
        return paths

    @staticmethod
    def _curve(run):
        path = QPainterPath(run[0])
        for a, b in zip(run[1:], run[2:]):
            path.quadTo(a, (a + b) / 2)
        path.lineTo(run[-1])
        return path

    def _groove(self, p, points):
        """Бороздка: тень с одной стороны, светлый гребень с другой - свет слева сверху."""
        gap = self._gap()
        curves = [self._curve(run) for run in self._tine_paths(points)]
        if not curves:
            return
        shade = QColor(self.SAND_DARK)
        shade.setAlpha(150)
        light = QColor(self.SAND_LIGHT)
        light.setAlpha(170)
        bottom = QColor(self.SAND_DARK.darker(115))
        bottom.setAlpha(110)
        for color, width, shift in ((light, gap * 0.34, QPointF(-gap * 0.16, -gap * 0.2)),
                                    (shade, gap * 0.36, QPointF(gap * 0.1, gap * 0.13)),
                                    (bottom, gap * 0.16, QPointF(gap * 0.04, gap * 0.05))):
            p.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            for curve in curves:
                p.drawPath(curve.translated(shift))

    def _ring_points(self, stone, radius):
        x, y, _r = stone
        center = self._px((x, y))
        return [center + QPointF(math.cos(a) * radius, math.sin(a) * radius / 1.35)
                for a in (i * 2 * math.pi / 72 for i in range(73))]

    def _render_base(self):
        """Песок, круги у камней и готовые бороздки - в одну картинку (перерисовка только при изменениях)."""
        self.base = QImage(self.size(), QImage.Format_ARGB32_Premultiplied)
        self.base.fill(Qt.transparent)
        p = QPainter(self.base)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        sand = QRadialGradient(rect.center() - QPointF(rect.width() * 0.15, rect.height() * 0.2), rect.width() * 0.8)
        sand.setColorAt(0, self.SAND.lighter(106))
        sand.setColorAt(1, self.SAND.darker(108))
        clip = QPainterPath()
        clip.addRoundedRect(rect, 12, 12)
        p.setClipPath(clip)
        p.fillRect(rect, sand)
        rnd = random.Random(7)                                  # песчинки - один и тот же узор
        p.setPen(Qt.NoPen)
        for _ in range(int(rect.width() * rect.height() / 90)):
            tone = rnd.choice((QColor(120, 95, 55, 55), QColor(255, 245, 220, 70), QColor(90, 80, 70, 40)))
            p.setBrush(tone)
            size = rnd.uniform(0.5, 1.3)
            p.drawEllipse(QPointF(rnd.uniform(rect.left(), rect.right()), rnd.uniform(rect.top(), rect.bottom())),
                          size, size)
        gap, side = self._gap(), self._side()
        for stone in self.stones:
            for ring in range(3):
                radius = stone[2] * side * 1.12 + gap * (3.2 + ring * self.TINES * 1.15)
                self._groove(p, self._ring_points(stone, radius))
        for line in self.lines:
            self._groove(p, [self._px(q) for q in line])
        p.end()

    def resizeEvent(self, event):
        self.base = QImage()
        super().resizeEvent(event)

    def paintEvent(self, _event):
        if self.base.isNull() or self.base.size() != self.size():
            self._render_base()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawImage(0, 0, self.base)
        if len(self.current) >= 2:
            self._groove(p, [self._px(q) for q in self.current])
        side = self._side()
        from PySide6.QtGui import QPixmap
        from .artwork import scaled
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        for index, (x, y, r) in enumerate(self.stones):
            center = self._px((x, y))
            rx, ry = r * side * 1.12, r * side * 0.82
            shadow = QRadialGradient(center + QPointF(rx * 0.25, ry * 0.55), rx * 1.4)
            shadow.setColorAt(0, QColor(60, 45, 20, 120))
            shadow.setColorAt(1, QColor(60, 45, 20, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(shadow)
            p.drawEllipse(center + QPointF(rx * 0.25, ry * 0.55), rx * 1.4, ry * 1.2)
            kinds = getattr(self, "stone_kinds", [])
            picture = scaled(f"stone-{kinds[index]}", rx * 2.8, self.devicePixelRatioF()) \
                if index < len(kinds) else QPixmap()
            if not picture.isNull():                    # нарисованный камень, тень под ним - наша
                height = rx * 2.8 * picture.height() / picture.width()
                p.drawPixmap(QRectF(center.x() - rx * 1.4, center.y() - height / 2, rx * 2.8, height),
                             picture, QRectF(picture.rect()))
                continue
            stone = QRadialGradient(center - QPointF(rx * 0.35, ry * 0.45), rx * 1.5)
            stone.setColorAt(0, QColor("#9a97a3"))
            stone.setColorAt(0.55, QColor("#5d5a68"))
            stone.setColorAt(1, QColor("#2c2a36"))
            p.setBrush(stone)
            p.drawEllipse(center, rx, ry)
            p.setBrush(QColor(255, 255, 255, 40))                        # блик
            p.drawEllipse(center - QPointF(rx * 0.35, ry * 0.42), rx * 0.32, ry * 0.18)
        p.end()


class StoneSkip(QWidget):
    """Блинчики: камень по воде. Зажми мышь у берега, оттяни вниз (сила) и вбок (куда), отпусти.
    Колесо мыши - угол броска: чем площе, тем больше отскоков, но слишком низко - сразу «бульк».
    Вид из-за спины: озеро уходит к горизонту, на воде остаются круги."""

    GRAVITY = 9.8
    CAMERA_BACK, CAMERA_HEIGHT, HAND = 3.0, 1.7, 1.1
    MAX_SPEED = 30.0

    def __init__(self, on_sound=None, on_result=None):
        super().__init__()
        self.on_sound = on_sound
        self.on_result = on_result
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.OpenHandCursor)
        self.angle = 12.0                       # градусы над водой
        self.stone = None                       # [x вбок, высота, дальность, vx, vy, vz] в метрах
        self.skips = 0
        self.distance = 0.0
        self.best = 0
        self.best_distance = 0.0
        self.ripples = []                       # (вбок, дальность, время рождения)
        self.drops = []                         # брызги: [x, y, z, vx, vy, vz, время]
        self.splashes = []                      # нарисованные брызги: (вбок, дальность, время, имя)
        self.pull = None                        # (откуда тянем, где сейчас)
        self.t = 0.0
        self.clock = QElapsedTimer()
        self.clock.start()
        self._last = 0.0
        self.timer = QTimer(self, interval=16, timerType=Qt.PreciseTimer)
        self.timer.timeout.connect(self._frame)

    # ---- перевод метров в точки экрана: вид из-за спины ----
    def _horizon(self):
        return self.height() * 0.36

    def project(self, lateral, height, ahead):
        z = ahead + self.CAMERA_BACK
        f = self.height() * 0.95
        return QPointF(self.width() / 2 + f * lateral / z, self._horizon() + f * (self.CAMERA_HEIGHT - height) / z), f / z

    # ---- бросок ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.stone is None:
            self.pull = (event.position(), event.position())
            self.setCursor(Qt.ClosedHandCursor)
            self.update()

    def mouseMoveEvent(self, event):
        if self.pull is not None:
            self.pull = (self.pull[0], event.position())
            self.update()

    def mouseReleaseEvent(self, _event):
        if self.pull is None:
            return
        start, end = self.pull
        self.pull = None
        self.setCursor(Qt.OpenHandCursor)
        dy = end.y() - start.y()                      # тянем вниз - бросок вперёд
        dx = start.x() - end.x()                      # оттянул влево - полетит правее
        if dy < 8:
            self.update()
            return
        power = min(1.0, math.hypot(dx, dy) / (self.height() * 0.45))
        self.throw(power, math.degrees(math.atan2(dx, dy)) * 0.5)

    def wheelEvent(self, event):
        step = 1.0 if event.angleDelta().y() > 0 else -1.0
        self.angle = max(0.0, min(45.0, self.angle + step))
        self.update()

    def throw(self, power, aim=0.0, angle=None):
        """Бросить: power 0..1 - сила, aim - градусы вбок, angle - над водой (по умолчанию свой)."""
        angle = self.angle if angle is None else angle
        speed = 4 + power * (self.MAX_SPEED - 4)
        up = math.radians(angle)
        side = math.radians(max(-25.0, min(25.0, aim)))
        flat = speed * math.cos(up)
        self.stone = [0.0, self.HAND, 0.4, flat * math.sin(side), speed * math.sin(up), flat * math.cos(side)]
        self.skips, self.distance = 0, 0.0
        self._last = self.clock.elapsed() / 1000
        self.timer.start()

    def _step(self, dt):
        s = self.stone
        s[4] -= self.GRAVITY * dt
        s[0] += s[3] * dt
        s[1] += s[4] * dt
        s[2] += s[5] * dt
        if s[1] > 0:
            return
        s[1] = 0.0
        forward = math.hypot(s[3], s[5])
        steep = -s[4] / max(forward, 0.01)            # насколько отвесно вошёл в воду
        self.ripples.append((s[0], s[2], self.t))
        if random.random() < self.skip_chance(steep, forward):
            # отскок; каждый шлепок съедает скорость, и камень чуть уводит в сторону
            self.skips += 1
            s[4] = -s[4] * 0.55 + random.uniform(-0.1, 0.2)
            s[3] = s[3] * 0.86 + random.uniform(-0.25, 0.25)
            s[5] *= 0.86
            self._splash(s[0], s[2], "skip-splash")
            self._sound("water_skip", min(1.0, 0.35 + forward / 25))
            return
        self._sound("water_plunk", min(1.0, 0.4 + forward / 30))
        if not self._splash(s[0], s[2], "skip-plunk"):
            for _ in range(14):                         # брызги (если нет нарисованного «булька»)
                self.drops.append([s[0], 0.0, s[2], random.uniform(-1.2, 1.2), random.uniform(1.5, 3.8),
                                   random.uniform(-1.0, 1.0), self.t])
        self.distance = s[2]
        self.stone = None
        new_record = self.skips > self.best or (self.skips == self.best and self.distance > self.best_distance)
        if self.skips > self.best:
            self.best = self.skips
        self.best_distance = max(self.best_distance, self.distance)
        if self.on_result:
            self.on_result(self.skips, self.distance, new_record and self.skips > 0)

    SPLASH_FPS = 30
    SPLASH_SIZE = {"skip-splash": 1.8, "skip-plunk": 2.2}      # ширина в метрах (нарочно крупнее, как камень)

    def _splash(self, lateral, ahead, name):
        """Нарисованные брызги в точке шлепка; False - кадров нет."""
        from .artwork import frame_count
        if not frame_count(f"anim/lake/{name}"):
            return False
        self.splashes.append((lateral, ahead, self.t, name))
        return True

    def _splash_frame(self, splash):
        from .artwork import frame_count
        index = int((self.t - splash[2]) * self.SPLASH_FPS)
        return index if index < frame_count(f"anim/lake/{splash[3]}") else None

    @staticmethod
    def skip_chance(steep, forward):
        """Отскочит ли: лучше всего вход под 6-18 градусов; слишком отвесно - бульк, слишком плоско -
        камень цепляет воду краем. Медленный камень тонет."""
        if forward < 3.0 or steep > 0.5:
            return 0.0
        if steep < 0.1:
            base = 0.6 + 3.5 * steep
        elif steep <= 0.32:
            base = 0.95
        else:
            base = 0.95 * (0.5 - steep) / 0.18
        return base * min(1.0, (forward - 3.0) / 6.0)

    def _sound(self, name, strength):
        if self.on_sound:
            self.on_sound(name, strength)

    def finish(self):
        """Долететь сразу (для проверок): шаги физики без экрана."""
        while self.stone is not None:
            self.t += 1 / 120
            self._step(1 / 120)
        self.timer.stop()

    def _frame(self):
        now = self.clock.elapsed() / 1000
        dt = min(0.05, max(0.0, now - self._last))
        self._last = now
        for _ in range(4):
            self.t += dt / 4
            if self.stone is not None:
                self._step(dt / 4)
        for drop in self.drops:
            drop[4] -= self.GRAVITY * dt
            drop[0] += drop[3] * dt
            drop[1] += drop[4] * dt
            drop[2] += drop[5] * dt
        self.drops = [d for d in self.drops if d[1] > -0.05]
        self.ripples = [r for r in self.ripples if self.t - r[2] < 3.0]
        self.splashes = [x for x in self.splashes if self._splash_frame(x) is not None]
        if self.stone is None and not self.drops and not self.ripples and not self.splashes:
            self.timer.stop()
        self.update()

    # ---- рисование ----
    def _shore(self, width):
        """Дальний берег (art/lake-shore) в цветах темы: картинку красим в оттенок «тела» темы.
        Готовая картинка запоминается до смены размера или темы."""
        from .artwork import scaled
        ratio = self.devicePixelRatioF()
        body = C.toy_colors()["body"]
        key = (int(width), round(ratio, 2), body.name())
        cached = getattr(self, "_shore_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        source = scaled("lake-shore", width, ratio)
        if source.isNull():
            result = source
        else:
            # яркость - нарисованная (свет и тени остаются), оттенок - как у неба и воды
            picture = source.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
            result = self._tint(picture, C.mix(body, "#ffffff", 0.1))
            result.setDevicePixelRatio(ratio)
        self._shore_cache = (key, result)
        return result

    @staticmethod
    def _tint(image, color):
        """Картинка в оттенке color: яркость каждой точки умножается на цвет, прозрачность та же."""
        from PySide6.QtGui import QPixmap
        gray = image.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_ARGB32_Premultiplied)
        q = QPainter(gray)                            # картинка тёмная: яркость вдвое, иначе берег - сажа
        q.setCompositionMode(QPainter.CompositionMode_Plus)
        q.drawImage(0, 0, gray.copy())
        q.end()
        tinted = QImage(gray.size(), QImage.Format_ARGB32_Premultiplied)
        tinted.fill(color)
        q = QPainter(tinted)
        q.setCompositionMode(QPainter.CompositionMode_Multiply)
        q.drawImage(0, 0, gray)
        q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        q.drawImage(0, 0, image)                      # прозрачность - как у картинки
        q.end()
        return QPixmap.fromImage(tinted)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h, horizon = self.width(), self.height(), self._horizon()
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 12, 12)
        p.setClipPath(clip)
        colors = C.toy_colors()                         # небо и вода - в цветах темы
        body, light, base = colors["body"], colors["glow"], colors["bg"]
        sky = QLinearGradient(0, 0, 0, horizon)
        sky.setColorAt(0, C.mix(base, "#000000", 0.1) if colors["dark"] else C.mix(body, "#ffffff", 0.5))
        sky.setColorAt(0.65, C.mix(body, base, 0.2))
        sky.setColorAt(1, C.mix(light, "#c98a4a", 0.4))
        p.fillRect(QRectF(0, 0, w, horizon + 1), sky)
        sun = QPointF(w * 0.68, horizon - h * 0.02)
        glow = QRadialGradient(sun, h * 0.28)
        glow.setColorAt(0, QColor(255, 210, 140, 200))
        glow.setColorAt(1, QColor(255, 210, 140, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(sun, h * 0.28, h * 0.28)
        p.setBrush(QColor("#ffe1a8"))
        p.drawEllipse(sun, h * 0.035, h * 0.035)
        # дальний берег: холмы и ели
        rnd = random.Random(5)
        shore_picture = self._shore(w)
        if not shore_picture.isNull():
            ratio = shore_picture.devicePixelRatio()
            shore_h = shore_picture.height() / ratio
            p.drawPixmap(QRectF(0, horizon + 1 - shore_h, w, shore_h), shore_picture, QRectF(shore_picture.rect()))
        hills = QPainterPath(QPointF(0, horizon))
        for k in range(13):
            hills.lineTo(QPointF(w * k / 12, horizon - h * rnd.uniform(0.02, 0.06)))
        hills.lineTo(QPointF(w, horizon))
        p.setBrush(C.mix(body, "#000000", 0.6))
        if shore_picture.isNull():
            p.drawPath(hills)
        for _ in range(40):
            x = rnd.uniform(0, w)
            top = horizon - h * rnd.uniform(0.04, 0.09)
            tree = QPainterPath(QPointF(x, top))
            tree.lineTo(QPointF(x - h * 0.012, horizon))
            tree.lineTo(QPointF(x + h * 0.012, horizon))
            if shore_picture.isNull():
                p.drawPath(tree)
        # вода
        water = QLinearGradient(0, horizon, 0, h)
        water.setColorAt(0, C.mix(light, body, 0.5))
        water.setColorAt(0.08, C.mix(body, base, 0.25))
        water.setColorAt(1, C.mix(base, "#000000", 0.35 if colors["dark"] else 0.15))
        p.fillRect(QRectF(0, horizon, w, h - horizon), water)
        p.setBrush(QColor(255, 210, 150, 60))                  # дорожка солнца
        for k in range(28):
            y = horizon + (h - horizon) * (k / 28) ** 1.6
            half = w * 0.01 + w * 0.05 * (k / 28)
            wobble = math.sin(self.t * 2 + k) * half * 0.3
            p.drawRect(QRectF(sun.x() - half + wobble, y, half * 2 * rnd.uniform(0.3, 1.0), 1.5 + k * 0.08))
        p.setPen(QPen(QColor(255, 255, 255, 16), 1))           # мелкая рябь
        for k in range(1, 40):
            ahead = 60 / k
            point, _scale = self.project(0, 0, ahead)
            shift = math.sin(self.t * 1.3 + k * 0.7) * 20
            p.drawLine(QPointF(shift, point.y()), QPointF(w + shift, point.y()))
        # круги на воде
        for lateral, ahead, born in self.ripples:
            age = self.t - born
            center, scale = self.project(lateral, 0, ahead)
            radius = (0.5 + age * 2.4) * scale
            alpha = int(170 * max(0.0, 1 - age / 3))
            p.setPen(QPen(QColor(220, 225, 255, alpha), max(1.0, scale * 0.05)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(center, radius, radius * 0.28)
            p.drawEllipse(center, radius * 0.6, radius * 0.6 * 0.28)
        # нарисованные брызги и «бульк»: дальние меньше
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        from .artwork import scaled
        for splash in self.splashes:
            index = self._splash_frame(splash)
            if index is None:
                continue
            point, scale = self.project(splash[0], 0, splash[1])
            width = max(8.0, scale * self.SPLASH_SIZE[splash[3]])
            picture = scaled(f"anim/lake/{splash[3]}_{index:02d}", width, self.devicePixelRatioF())
            if picture.isNull():
                continue
            height = width * picture.height() / picture.width()
            p.drawPixmap(QRectF(point.x() - width / 2, point.y() + scale * 0.03 - height, width, height),
                         picture, QRectF(picture.rect()))
        # брызги
        p.setPen(Qt.NoPen)
        for x, y, z, *_rest in self.drops:
            point, scale = self.project(x, max(0.0, y), z)
            p.setBrush(QColor(220, 230, 255, 200))
            p.drawEllipse(point, max(1.0, scale * 0.04), max(1.0, scale * 0.04))
        # камень и его тень на воде
        if self.stone is not None:
            x, y, z = self.stone[0], self.stone[1], self.stone[2]
            shadow, scale = self.project(x, 0, z)
            p.setBrush(QColor(0, 0, 0, 70))
            p.drawEllipse(shadow, max(3.0, scale * 0.2), max(1.0, scale * 0.05))
            point, scale = self.project(x, y, z)
            rx, ry = max(3.0, scale * 0.17), max(1.8, scale * 0.08)        # камень нарочно крупнее - чтобы видно
            picture = scaled("skip-stone", rx * 2.3, self.devicePixelRatioF())
            if not picture.isNull():                    # нарисованный блинчик, крутится в полёте
                p.save()
                p.translate(point)
                p.rotate(math.sin(self.t * 9) * 8)
                height = rx * 2.3 * picture.height() / picture.width()
                p.drawPixmap(QRectF(-rx * 1.15, -height / 2, rx * 2.3, height), picture, QRectF(picture.rect()))
                p.restore()
            else:
                stone = QRadialGradient(point - QPointF(rx * 0.35, ry * 0.4), rx * 1.4)
                stone.setColorAt(0, QColor("#d9d6e4"))
                stone.setColorAt(1, QColor("#4a4858"))
                p.setBrush(stone)
                p.drawEllipse(point, rx, ry)
        # ближний берег и рука с камнем
        shore = QPainterPath(QPointF(0, h))
        shore.lineTo(QPointF(0, h * 0.9))
        shore.cubicTo(QPointF(w * 0.3, h * 0.86), QPointF(w * 0.7, h * 0.93), QPointF(w, h * 0.88))
        shore.lineTo(QPointF(w, h))
        p.setBrush(C.mix(base, "#000000", 0.3) if colors["dark"] else C.mix(body, "#000000", 0.35))
        p.drawPath(shore)
        p.setBrush(QColor(110, 100, 130, 90))
        for _ in range(60):
            p.drawEllipse(QPointF(rnd.uniform(0, w), rnd.uniform(h * 0.92, h)), rnd.uniform(1, 3), rnd.uniform(0.8, 2))
        if self.pull is not None:
            start, end = self.pull
            power = min(1.0, math.hypot(end.x() - start.x(), end.y() - start.y()) / (h * 0.45))
            p.setPen(QPen(QColor(232, 169, 58, 200), 3, Qt.DashLine, Qt.RoundCap))
            p.drawLine(start, end)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(232, 169, 58, 230))
            bar = QRectF(16, h - 26, (w - 32) * power, 8)
            p.drawRoundedRect(bar, 4, 4)
        # угол броска - дуга в углу
        corner = QPointF(w - 70, h - 30)
        p.setPen(QPen(QColor(255, 255, 255, 60), 2))
        p.drawLine(corner, corner + QPointF(50, 0))
        p.setPen(QPen(QColor(232, 169, 58, 220), 3, Qt.SolidLine, Qt.RoundCap))
        up = math.radians(self.angle)
        p.drawLine(corner, corner + QPointF(50 * math.cos(up), -50 * math.sin(up)))
        p.setPen(QColor(230, 230, 245))
        p.drawText(QRectF(corner.x() - 60, corner.y() - 24, 56, 20), Qt.AlignRight | Qt.AlignVCenter,
                   f"{self.angle:.0f}°")
        p.end()


# ---------------- головоломка «Свет на пульте» ----------------
# Щелчок переключает тумблер и соседей по узору; цель - зажечь все лампочки. Задачи делаются из
# собранного пульта случайными щелчками (номер уровня - зерно), поэтому каждая решаема, а уровней
# сколько угодно. Решение - те же щелчки: каждый можно отменить повтором, порядок не важен.
PUZZLES = {
    # ключ: (название, столбцы, строки, узор соседей, сколько щелчков на запутывание (от, до))
    "easy": ("Лёгкая", 3, 3, ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)), (2, 3)),
    "medium": ("Средняя", 4, 4, ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)), (4, 6)),
    "hard": ("Трудная", 5, 5, ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)), (7, 10)),
    "tricky": ("Хитрая", 5, 4, ((0, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)), (5, 8)),
}


def puzzle_flip(state, col, row, pattern):
    """Щёлкнуть (col, row): переключить его и соседей по узору (за краем - ничего)."""
    rows, cols = len(state), len(state[0])
    for dx, dy in pattern:
        x, y = col + dx, row + dy
        if 0 <= x < cols and 0 <= y < rows:
            state[y][x] = not state[y][x]


def make_puzzle(kind, level):
    """(состояние, решение) уровня: решение - множество тумблеров, которые надо щёлкнуть."""
    _title, cols, rows, pattern, (low, high) = PUZZLES[kind]
    rnd = random.Random(f"{kind}-{level}")
    cells = [(x, y) for y in range(rows) for x in range(cols)]
    for _ in range(50):
        presses = set(rnd.sample(cells, rnd.randint(low, high)))
        state = [[True] * cols for _ in range(rows)]
        for x, y in presses:
            puzzle_flip(state, x, y, pattern)
        if not all(all(r) for r in state):
            return state, presses
    return state, presses


class Toggles(QWidget):
    """Пульт тумблеров: щёлк вверх, щёлк вниз, лампочка горит. Под крышкой справа внизу -
    красный «Не трогать»: откинь крышку и щёлкни - пульт устроит переполох огоньками."""

    COLS, ROWS_ = 5, 3
    LABELS = ("Муза", "Кофе", "Тишина", "Сюжет", "Диалоги",
              "Злодей", "Дедлайн", "Котик", "Ночь", "Музыка",
              "Чай", "Редактор", "Свет", "Сон", "НЕ ТРОГАТЬ")
    SPECIAL = (4, 2)

    def __init__(self, on_sound=None, on_change=None):
        super().__init__()
        self.on_sound = on_sound
        self.on_change = on_change              # ход в головоломке, решено, новый уровень
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.PointingHandCursor)
        self.cols, self.rows = self.COLS, self.ROWS_
        self.state = [[False] * self.COLS for _ in range(self.ROWS_)]
        self.flips = 0
        self.puzzle = None                      # None - просто щёлкать; иначе ключ из PUZZLES
        self.level = 1
        self.moves = 0
        self.solution = set()
        self.hint = None
        self.solved = False
        self.anim = {}
        self.guard_open = False
        self.guard_t = 0.0
        self.party = 0.0
        from .artwork import Effects
        self.effects = Effects(self)            # звёздная вспышка над решённым пультом
        self._party = QVariantAnimation(self)
        self._party.setDuration(2400)
        self._party.setStartValue(0.0)
        self._party.setEndValue(1.0)
        self._party.valueChanged.connect(lambda v: (setattr(self, "party", float(v)), self.update()))
        self._party.finished.connect(lambda: (setattr(self, "party", 0.0), self.update()))

    def cell_rect(self, col, row):
        inner = QRectF(self.rect()).adjusted(14, 14, -14, -14)
        w, h = inner.width() / self.cols, inner.height() / self.rows
        if self.puzzle is not None:                       # головоломка - квадратные клетки по центру
            side = min(w, h)
            left = inner.left() + (inner.width() - side * self.cols) / 2
            top = inner.top() + (inner.height() - side * self.rows) / 2
            return QRectF(left + col * side, top + row * side, side, side)
        return QRectF(inner.left() + col * w, inner.top() + row * h, w, h)

    # ---- головоломка ----
    def start_puzzle(self, kind, level):
        """kind None - просто щёлкать (пульт с надписями); иначе уровень головоломки."""
        self.puzzle, self.level, self.moves, self.hint, self.solved = kind, level, 0, None, False
        self.anim = {}
        self._party.stop()
        self.party = 0.0
        if kind is None:
            self.cols, self.rows = self.COLS, self.ROWS_
            self.state = [[False] * self.cols for _ in range(self.rows)]
            self.solution = set()
        else:
            _title, self.cols, self.rows, _pattern, _r = PUZZLES[kind]
            self.state, self.solution = make_puzzle(kind, level)
        self.guard_open, self.guard_t = False, 0.0
        self._changed()
        self.update()

    def show_hint(self):
        if self.puzzle is not None and self.solution and not self.solved:
            self.hint = sorted(self.solution)[0]
            self.update()

    def _changed(self):
        if self.on_change:
            self.on_change()

    def _sound(self, name):
        if self.on_sound:
            self.on_sound(name)

    def _animate(self, key, start, end, duration, setter):
        animation = QVariantAnimation(self)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.OutBack)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.valueChanged.connect(lambda v: (setter(float(v)), self.update()))
        animation.start(QVariantAnimation.DeleteWhenStopped)

    def toggle(self, col, row):
        if self.puzzle is not None:
            return self._puzzle_click(col, row)
        if (col, row) == self.SPECIAL and not self.guard_open:
            self.guard_open = True
            self._sound("guard_open")
            self._animate("guard", 0.0, 1.0, 220, lambda v: setattr(self, "guard_t", v))
            return
        on = not self.state[row][col]
        self.state[row][col] = on
        self.flips += 1
        self._animate((col, row), 0.0 if on else 1.0, 1.0 if on else 0.0, 150,
                      lambda v, k=(col, row): self.anim.__setitem__(k, v))
        self._sound("toggle_up" if on else "toggle_down")
        if (col, row) == self.SPECIAL and on:
            self._party.stop()
            self._party.start()
        elif (col, row) == self.SPECIAL:                       # выключили - крышка захлопнулась
            self.guard_open = False
            self._animate("guard", 1.0, 0.0, 180, lambda v: setattr(self, "guard_t", v))
        self.update()

    def _puzzle_click(self, col, row):
        if self.solved:
            return
        before = [r[:] for r in self.state]
        puzzle_flip(self.state, col, row, PUZZLES[self.puzzle][3])
        self.solution ^= {(col, row)}
        self.moves += 1
        self.flips += 1
        self.hint = None
        for y in range(self.rows):
            for x in range(self.cols):
                if before[y][x] != self.state[y][x]:
                    on = self.state[y][x]
                    self._animate((x, y), 0.0 if on else 1.0, 1.0 if on else 0.0, 150,
                                  lambda v, k=(x, y): self.anim.__setitem__(k, v))
        self._sound("toggle_up" if self.state[row][col] else "toggle_down")
        if all(all(r) for r in self.state):
            self.solved = True
            self._party.stop()
            self._party.start()
            self.effects.play("anim/toggle/puzzle-solved", self.width() / 2, self.height() / 2,
                              min(self.width(), self.height()) * 1.1)
            self._sound("chime")
        self._changed()
        self.update()

    def mousePressEvent(self, event):
        for row in range(self.rows):
            for col in range(self.cols):
                if self.cell_rect(col, row).contains(event.position()):
                    self.toggle(col, row)
                    return

    def _lit(self, col, row):
        """Горит ли лампочка: включён тумблер или пульт сейчас «гуляет» волной."""
        if self.party > 0:
            wave = (self.party * 9 - (col + row) * 0.45) % 1.0
            return wave < 0.45
        return self.state[row][col]

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        panel = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        metal = QRadialGradient(panel.topLeft() + QPointF(panel.width() * 0.3, panel.height() * 0.2), panel.width())
        body = _body()
        metal.setColorAt(0, C.mix(body, "#9aa0b8", 0.3))
        metal.setColorAt(1, C.mix(body, "#000000", 0.5))
        p.setPen(QPen(QColor("#0e0f22"), 1.5))
        p.setBrush(metal)
        p.drawRoundedRect(panel, 12, 12)
        rnd = random.Random(3)                                   # шлифовка металла
        for _ in range(int(panel.height() / 2.2)):
            y = rnd.uniform(panel.top() + 4, panel.bottom() - 4)
            p.setPen(QPen(QColor(255, 255, 255, rnd.randint(4, 12)), 1))
            p.drawLine(QPointF(panel.left() + 6, y), QPointF(panel.right() - 6, y))
        for corner in (panel.topLeft() + QPointF(10, 10), panel.topRight() + QPointF(-10, 10),
                       panel.bottomLeft() + QPointF(10, -10), panel.bottomRight() + QPointF(-10, -10)):
            screw = QRadialGradient(corner - QPointF(1.5, 1.5), 5)
            screw.setColorAt(0, QColor("#d9dbe6"))
            screw.setColorAt(1, QColor("#5a5d75"))
            p.setPen(Qt.NoPen)
            p.setBrush(screw)
            p.drawEllipse(corner, 4.2, 4.2)
            p.setPen(QPen(QColor("#33354d"), 1.2))
            p.drawLine(corner - QPointF(2.6, 0), corner + QPointF(2.6, 0))
        font = p.font()
        for row in range(self.rows):
            for col in range(self.cols):
                self._paint_switch(p, col, row, font)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        self.effects.paint(p)
        p.end()

    def _paint_switch(self, p, col, row, font):
        rect = self.cell_rect(col, row)
        c = rect.center()
        unit = min(rect.width(), rect.height())
        if self.puzzle is not None:
            return self._paint_puzzle_switch(p, col, row, rect, unit)
        special = (col, row) == self.SPECIAL
        label = self.LABELS[row * self.COLS + col]
        # табличка с надписью
        plate = QRectF(0, 0, min(rect.width() * 0.86, unit * 1.25), unit * 0.17)
        plate.moveCenter(QPointF(c.x(), rect.top() + unit * 0.13))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#8a1f1f") if special else QColor("#e9e2cf"))
        p.drawRoundedRect(plate, 3, 3)
        f = QFont(font)
        f.setPixelSize(max(8, int(unit * 0.105)))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#fff2d8") if special else QColor("#2a2680"))
        p.drawText(plate, Qt.AlignCenter, label)
        # лампочка
        lit = self._lit(col, row)
        pivot = QPointF(c.x(), rect.top() + unit * 0.64)
        lamp = QPointF(c.x() + min(rect.width() * 0.3, unit * 0.42), pivot.y() - unit * 0.12)
        lamp_r = unit * 0.07
        color = QColor("#ff5a4a") if special else _glow().lighter(120)
        if lit:
            glow = QRadialGradient(lamp, lamp_r * 3.2)
            glow.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 150))
            glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            p.setBrush(glow)
            p.drawEllipse(lamp, lamp_r * 3.2, lamp_r * 3.2)
        bulb = QRadialGradient(lamp - QPointF(lamp_r * 0.3, lamp_r * 0.3), lamp_r * 1.3)
        bulb.setColorAt(0, color.lighter(150) if lit else QColor("#4b4766"))
        bulb.setColorAt(1, color.darker(110) if lit else QColor("#1d1b30"))
        p.setPen(QPen(QColor("#0e0f22"), 1))
        p.setBrush(bulb)
        p.drawEllipse(lamp, lamp_r, lamp_r)
        # гайка и рычаг: вверх - вкл, вниз - выкл
        on = self.state[row][col]
        t = self.anim.get((col, row), 1.0 if on else 0.0)
        self._paint_lever(p, pivot, unit, t, special)
        # защитная крышка «не трогать»: красная, откидывается вверх
        if special:
            cover = QRectF(0, 0, unit * 0.42, unit * 0.5)
            cover.moveCenter(pivot)
            lift = self.guard_t
            if lift < 0.98:
                shown = QRectF(cover)
                shown.setTop(cover.bottom() - cover.height() * (1 - lift))
                glass = QColor(200, 40, 35, 200)
                p.setPen(QPen(QColor("#5a0f0c"), 1.5))
                p.setBrush(glass)
                p.drawRoundedRect(shown, 5, 5)
                p.setPen(QPen(QColor(255, 255, 255, 60), 2))
                p.drawLine(shown.topLeft() + QPointF(5, 5), shown.bottomLeft() + QPointF(5, -5))
            if lift > 0.02:                                              # откинутая - узкая полоска сверху
                up = QRectF(cover.left(), cover.top() - cover.height() * 0.22 * lift, cover.width(),
                            cover.height() * 0.2 * lift)
                p.setPen(QPen(QColor("#5a0f0c"), 1.2))
                p.setBrush(QColor(200, 40, 35, 220))
                p.drawRoundedRect(up, 3, 3)


    def _paint_puzzle_switch(self, p, col, row, rect, unit):
        """Клетка головоломки - клавиша с подсветкой: горит охрой, погасшая - тёмное стекло."""
        on = self.state[row][col]
        t = self.anim.get((col, row), 1.0 if on else 0.0)
        if self.party > 0:
            t = 1.0 if self._lit(col, row) else 0.35
        t = max(0.0, min(1.0, t))
        key = rect.adjusted(rect.width() * 0.1, rect.height() * 0.1, -rect.width() * 0.1, -rect.height() * 0.1)
        radius = key.width() * 0.16
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))                                   # тень клавиши
        p.drawRoundedRect(key.translated(2, 4), radius, radius)
        if t > 0.05:
            glow = QRadialGradient(key.center(), key.width() * 0.9)
            light = _glow()
            glow.setColorAt(0, QColor(light.red(), light.green(), light.blue(), int(110 * t)))
            glow.setColorAt(1, QColor(light.red(), light.green(), light.blue(), 0))
            p.setBrush(glow)
            p.drawEllipse(key.center(), key.width() * 0.9, key.height() * 0.9)
        body, light = _body(), _glow()
        off_top, off_bottom = C.mix(body, "#ffffff", 0.12), C.mix(body, "#000000", 0.55)
        on_top, on_bottom = C.mix(light, "#ffffff", 0.45), C.mix(light, "#000000", 0.08)
        face = QLinearGradient(key.topLeft(), key.bottomLeft())
        face.setColorAt(0, C.mix(off_top, on_top, t))
        face.setColorAt(1, C.mix(off_bottom, on_bottom, t))
        p.setPen(QPen(QColor("#0b0b1c"), 1.5))
        p.setBrush(face)
        p.drawRoundedRect(key, radius, radius)
        p.setPen(Qt.NoPen)                                                # блик сверху
        p.setBrush(QColor(255, 255, 255, int(30 + 50 * t)))
        shine = QRectF(key.left() + key.width() * 0.12, key.top() + key.height() * 0.07,
                       key.width() * 0.76, key.height() * 0.22)
        p.drawRoundedRect(shine, shine.height() / 2, shine.height() / 2)
        if self.hint == (col, row):                                      # подсказка - пунктир вокруг
            p.setPen(QPen(QColor(255, 240, 200, 220), max(2.0, unit * 0.03), Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(key.adjusted(-6, -6, 6, 6), radius + 4, radius + 4)

    def _paint_lever(self, p, pivot, unit, t, special=False):
        """Гайка и рычаг тумблера: t=1 - вверх (вкл), 0 - вниз. Обычные - нарисованные
        (art/toggle-up, toggle-down: гайка на (64, 120) из 128×192), красный - свой."""
        if not special:
            from .artwork import scaled
            width = unit * 0.545
            picture = scaled("toggle-up" if t >= 0.5 else "toggle-down", width, p.device().devicePixelRatioF())
            if not picture.isNull():
                height = width * 1.5
                p.save()
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                p.drawPixmap(QRectF(pivot.x() - width / 2, pivot.y() - height * 120 / 192, width, height),
                             picture, QRectF(picture.rect()))
                p.restore()
                return
        nut = QPainterPath()
        nut_r = unit * 0.13
        for k in range(6):
            angle = math.pi / 6 + k * math.pi / 3
            q = pivot + QPointF(math.cos(angle) * nut_r, math.sin(angle) * nut_r)
            nut.moveTo(q) if k == 0 else nut.lineTo(q)
        nut.closeSubpath()
        steel = QRadialGradient(pivot - QPointF(nut_r * 0.4, nut_r * 0.5), nut_r * 1.6)
        steel.setColorAt(0, QColor("#eef0f6"))
        steel.setColorAt(1, QColor("#6b6f86"))
        p.setPen(QPen(QColor("#22243a"), 1))
        p.setBrush(steel)
        p.drawPath(nut)
        p.setBrush(QColor("#2a2c40"))
        p.drawEllipse(pivot, nut_r * 0.45, nut_r * 0.45)
        reach = unit * 0.25 * (2 * t - 1)
        tip = pivot + QPointF(0, -reach)
        p.setPen(QPen(QColor(0, 0, 0, 70), unit * 0.08, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(pivot + QPointF(2, 3), tip + QPointF(3, 4))
        p.setPen(QPen(QColor("#d7d9e3"), unit * 0.07, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(pivot, tip)
        knob = QRadialGradient(tip - QPointF(unit * 0.02, unit * 0.025), unit * 0.07)
        knob.setColorAt(0, QColor("#ffffff"))
        knob.setColorAt(1, QColor("#b02a22") if special else QColor("#8d90a6"))
        p.setPen(QPen(QColor("#2a2c40"), 1))
        p.setBrush(knob)
        p.drawEllipse(tip, unit * 0.055, unit * 0.055)


# ---------------- «Блоки»: падающие фигуры из четырёх клеток ----------------
SHAPES = {           # фигура: клетки в положении «как появилась» (x, y), y вниз
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "T": ((1, 0), (0, 1), (1, 1), (2, 1)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
    "J": ((0, 0), (0, 1), (1, 1), (2, 1)),
    "L": ((2, 0), (0, 1), (1, 1), (2, 1)),
}
LINE_SCORE = {1: 100, 2: 300, 3: 500, 4: 800}


class BlocksGame:
    """Логика «Блоков» без рисования: стакан 10×20, фигура, следующая, очки, линии, уровень.
    Фигуры выпадают «мешком» (все семь по разу, потом заново) - без долгих засух на палку."""

    COLS, ROWS = 10, 20

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.grid = [[None] * self.COLS for _ in range(self.ROWS)]
        self.bag = []
        self.score = self.lines = 0
        self.over = False
        self.next = self._take()
        self._spawn()

    @property
    def level(self):
        return 1 + self.lines // 10

    def interval(self):
        """Сколько мс между шагами вниз: с уровнем быстрее, но без безумия - это антистресс."""
        return max(110, 720 - (self.level - 1) * 60)

    def _take(self):
        if not self.bag:
            self.bag = list(SHAPES)
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def _spawn(self):
        self.kind, self.next = self.next, self._take()
        self.cells = list(SHAPES[self.kind])
        self.x, self.y = 3, 0
        if not self._fits(self.cells, self.x, self.y):
            self.over = True

    def blocks(self, cells=None, x=None, y=None):
        cells = self.cells if cells is None else cells
        x = self.x if x is None else x
        y = self.y if y is None else y
        return [(x + cx, y + cy) for cx, cy in cells]

    def _fits(self, cells, x, y):
        for bx, by in self.blocks(cells, x, y):
            if not (0 <= bx < self.COLS and by < self.ROWS) or (by >= 0 and self.grid[by][bx] is not None):
                return False
        return True

    def move(self, dx):
        if not self.over and self._fits(self.cells, self.x + dx, self.y):
            self.x += dx
            return True
        return False

    def rotate(self):
        """Поворот по часовой; упёрлась в стену или кучу - пробуем сдвинуть на клетку-две."""
        if self.over or self.kind == "O":
            return False
        size = 4 if self.kind == "I" else 3
        turned = [(size - 1 - cy, cx) for cx, cy in self.cells]
        for dx in (0, -1, 1, -2, 2):
            if self._fits(turned, self.x + dx, self.y):
                self.cells, self.x = turned, self.x + dx
                return True
        return False

    def ghost_y(self):
        y = self.y
        while self._fits(self.cells, self.x, y + 1):
            y += 1
        return y

    def step(self):
        """Шаг вниз. -> сколько линий убрано (если фигура легла), иначе None."""
        if self.over:
            return None
        if self._fits(self.cells, self.x, self.y + 1):
            self.y += 1
            return None
        return self._lock()

    def drop(self):
        """Сразу вниз (пробел). -> сколько линий убрано."""
        if self.over:
            return 0
        fall = self.ghost_y() - self.y
        self.y += fall
        self.score += 2 * fall
        return self._lock()

    def _lock(self):
        for bx, by in self.blocks():
            if by < 0:
                self.over = True
                return 0
            self.grid[by][bx] = self.kind
        full = [row for row in range(self.ROWS) if all(self.grid[row])]
        for row in full:
            del self.grid[row]
            self.grid.insert(0, [None] * self.COLS)
        if full:
            self.lines += len(full)
            self.score += LINE_SCORE[len(full)] * self.level
        self._spawn()
        return len(full)


class Blocks(QWidget):
    """«Блоки»: ← → двигать, ↑ повернуть, ↓ быстрее, пробел - сразу вниз, P - пауза.
    Фигуры - мягкие объёмные кубики в цветах темы; рядом - следующая фигура и счёт."""

    def __init__(self, on_sound=None, on_change=None):
        super().__init__()
        self.on_sound = on_sound
        self.on_change = on_change
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setFocusPolicy(Qt.StrongFocus)
        self.game = BlocksGame()
        self.best = 0
        self.paused = True                      # стартует, когда окно с игрой открыли и нажали клавишу
        self.flash = {}                         # убранные линии вспыхивают
        self.timer = QTimer(self, timerType=Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)

    def start(self):
        if self.game.over:
            self.game.reset()
        self.paused = False
        self.timer.start(self.game.interval())
        self._changed()

    def pause(self, on=True):
        self.paused = on
        if on:
            self.timer.stop()
        else:
            self.timer.start(self.game.interval())
        self._changed()

    def hideEvent(self, event):                 # ушли на другую вкладку - пауза
        if not self.paused:
            self.pause(True)
        super().hideEvent(event)

    def _changed(self):
        self.best = max(self.best, self.game.score)
        if self.on_change:
            self.on_change()
        self.update()

    def _landed(self, lines):
        if lines:
            if self.on_sound:
                self.on_sound("pop", min(1.0, 0.5 + 0.15 * lines))
        elif self.on_sound:
            self.on_sound("toggle_down", 0.35)
        if self.game.over:
            self.timer.stop()
            self.paused = True
        else:
            self.timer.setInterval(self.game.interval())
        self._changed()

    def _tick(self):
        lines = self.game.step()
        if lines is not None:
            self._landed(lines)
        else:
            self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_P, Qt.Key_Escape) and not self.game.over:
            if key == Qt.Key_Escape and self.paused:
                super().keyPressEvent(event)
                return
            self.pause(not self.paused)
            return
        if self.paused:
            if key in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                self.start()
            else:
                super().keyPressEvent(event)
            return
        if key == Qt.Key_Left:
            self.game.move(-1)
        elif key == Qt.Key_Right:
            self.game.move(1)
        elif key in (Qt.Key_Up, Qt.Key_X):
            if self.game.rotate() and self.on_sound:
                self.on_sound("toggle_up", 0.25)
        elif key == Qt.Key_Down:
            lines = self.game.step()
            self.game.score += 1
            if lines is not None:
                self._landed(lines)
        elif key == Qt.Key_Space:
            self._landed(self.game.drop())
        else:
            super().keyPressEvent(event)
            return
        self.update()

    def mousePressEvent(self, _event):
        self.setFocus()
        if self.paused:
            self.start()

    # ---- рисование ----
    def _palette(self):
        colors = C.toy_colors()
        body, glow = colors["body"], colors["glow"]
        tones = {"I": C.mix(glow, "#ffffff", 0.2), "O": glow, "T": body.lighter(150), "S": C.mix(body, glow, 0.5),
                 "Z": C.mix(glow, "#c0392b", 0.45), "J": body.lighter(115), "L": C.mix(glow, body, 0.25)}
        return colors, tones

    def _block(self, p, rect, color, ghost=False):
        color = QColor(color)
        if ghost:
            p.setPen(QPen(C.mix(color, "#ffffff", 0.2), 1.2, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)
            return
        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill.setColorAt(0, color.lighter(135))
        fill.setColorAt(1, color.darker(130))
        p.setPen(QPen(color.darker(170), 1))
        p.setBrush(fill)
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 60))
        p.drawRoundedRect(QRectF(rect.x() + 3, rect.y() + 3, rect.width() * 0.5, rect.height() * 0.22), 2, 2)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        colors, tones = self._palette()
        g = self.game
        cell = min((self.height() - 20) / g.ROWS, (self.width() - 40) / (g.COLS + 7))
        well = QRectF((self.width() - cell * (g.COLS + 6)) / 2, (self.height() - cell * g.ROWS) / 2,
                      cell * g.COLS, cell * g.ROWS)
        p.setPen(QPen(C.mix(colors["body"], "#ffffff", 0.25), 1.5))
        p.setBrush(C.mix(colors["bg"], "#000000", 0.25))
        p.drawRoundedRect(well.adjusted(-6, -6, 6, 6), 10, 10)
        p.setPen(QPen(QColor(255, 255, 255, 12), 1))
        for col in range(1, g.COLS):
            p.drawLine(QPointF(well.x() + col * cell, well.top()), QPointF(well.x() + col * cell, well.bottom()))
        for row in range(g.ROWS):
            for col in range(g.COLS):
                if g.grid[row][col]:
                    self._block(p, QRectF(well.x() + col * cell, well.y() + row * cell, cell, cell),
                                tones[g.grid[row][col]])
        if not g.over:
            ghost = g.ghost_y()
            for bx, by in g.blocks(y=ghost):
                if by >= 0:
                    self._block(p, QRectF(well.x() + bx * cell, well.y() + by * cell, cell, cell), tones[g.kind], True)
            for bx, by in g.blocks():
                if by >= 0:
                    self._block(p, QRectF(well.x() + bx * cell, well.y() + by * cell, cell, cell), tones[g.kind])
        side = QRectF(well.right() + cell * 1.2, well.top(), cell * 4.8, well.height())
        font = QFont(p.font())
        font.setPixelSize(max(11, int(cell * 0.55)))
        font.setBold(True)
        p.setFont(font)
        p.setPen(C.mix(colors["glow"], "#ffffff", 0.1))
        p.drawText(QRectF(side.x(), side.y(), side.width(), cell), Qt.AlignLeft | Qt.AlignVCenter, "Дальше")
        small = cell * 0.8
        for cx, cy in SHAPES[g.next]:
            self._block(p, QRectF(side.x() + cx * small, side.y() + cell * 1.3 + cy * small, small, small), tones[g.next])
        lines = [("Очки", g.score), ("Линии", g.lines), ("Уровень", g.level), ("Рекорд", self.best)]
        for i, (label, value) in enumerate(lines):
            top = side.y() + cell * (4.4 + i * 2.1)
            font.setBold(False)
            p.setFont(font)
            p.setPen(QColor(C.TEXT))
            p.drawText(QRectF(side.x(), top, side.width(), cell), Qt.AlignLeft | Qt.AlignVCenter, label)
            font.setBold(True)
            p.setFont(font)
            p.setPen(C.mix(colors["glow"], "#ffffff", 0.1))
            p.drawText(QRectF(side.x(), top + cell * 0.8, side.width(), cell), Qt.AlignLeft | Qt.AlignVCenter,
                       f"{value:,}".replace(",", " "))
        if self.paused or g.over:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 140))
            p.drawRoundedRect(well, 8, 8)
            p.setPen(QColor("#ffffff"))
            text = (f"Конец: {g.score} очков\nПробел - ещё раз" if g.over else
                    "Пауза\nПробел или щелчок - играть" if g.score or g.lines else
                    "Щёлкни или нажми пробел\n← → ↑ ↓ и пробел")
            p.drawText(well, Qt.AlignCenter, text)
        p.end()


PAGES = ("Пупырка", "Мячик", "Спиннер", "Песок", "Тумблеры", "Блинчики", "Блоки")
HINTS = {
    1: "Зажми мячик и подержи - сожмётся. Схвати и брось - отскочит",
    2: "Раскрути спиннер мышью",
    3: "Веди мышью с зажатой кнопкой - грабли оставят бороздки",
    4: "Щёлк. А красный - под крышкой: откинь и попробуй",
    5: "Зажми мышь, оттяни вниз и отпусти. Колесо - угол: чем площе, тем больше блинчиков",
    6: "← → двигать, ↑ повернуть, ↓ быстрее, пробел - сразу вниз, P - пауза",
}


class StressDialog(Sheet):
    def __init__(self, parent=None):
        super().__init__(parent, tr("Антистресс"))
        sounds = getattr(parent, "sounds", None)
        self._play = sounds.play if sounds is not None else (lambda *_a: None)
        tabs = QHBoxLayout()
        self.group = QButtonGroup(self)
        self.pages = QStackedWidget()
        self.wrap = BubbleWrap(on_pop=self._popped)
        self.ball = SquishBall(on_bounce=lambda strength: self._play("ball_bounce", strength))
        self.spinner = Spinner(on_whirr=lambda strength: self._play("spinner", strength))
        self.sand = ZenSand(on_rake=lambda strength: self._play("sand_rake", strength))
        self.toggles = Toggles(on_sound=lambda name: self._play(name, 0.8), on_change=self._update_count)
        toggles_page = self._toggles_page()
        self.skip = StoneSkip(on_sound=lambda name, strength: self._play(name, strength), on_result=self._skipped)
        self.skip.best = int(self.settings.value("skip_best", 0) or 0)
        self.skip.best_distance = float(self.settings.value("skip_best_distance", 0) or 0)
        self.blocks = Blocks(on_sound=lambda name, strength: self._play(name, strength), on_change=self._blocks_changed)
        self.blocks.best = int(self.settings.value("blocks_best", 0) or 0)
        for index, (title, page) in enumerate(zip(PAGES, (self.wrap, self.ball, self.spinner, self.sand,
                                                          toggles_page, self.skip, self.blocks))):
            button = QPushButton(tr(title))
            button.setCheckable(True)
            button.setAutoDefault(False)                 # иначе первая вкладка выглядит нажатой всегда
            button.setProperty("noIcon", True)
            button.setStyleSheet(f"QPushButton:checked {{ background: {C.IMPORTANT}; "
                                 f"color: {C.on_color(C.IMPORTANT)}; }}")
            button.clicked.connect(lambda _c=False, i=index: self._show_page(i))
            self.group.addButton(button)
            tabs.addWidget(button)
            self.pages.addWidget(page)
            if index == 0:
                button.setChecked(True)
        tabs.addStretch()
        self.content.addLayout(tabs)
        self.content.addWidget(self.pages, 1)
        row = QHBoxLayout()
        self.count = QLabel("")
        self.count.setObjectName("Status")
        row.addWidget(self.count, 1)
        self.refill = refill = QPushButton(tr("Новый лист"))
        refill.clicked.connect(self._refill)
        close = QPushButton(tr("Закрыть"))
        close.setProperty("minor", True)
        close.clicked.connect(self.accept)
        row.addWidget(refill)
        row.addWidget(close)
        self.content.addLayout(row)
        self._update_count()

    def _toggles_page(self):
        """Тумблеры: сверху - режим (просто щёлкать или головоломка), подсказка, заново, дальше."""
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QComboBox, QVBoxLayout
        self.settings = QSettings(C.APP_ID, C.APP_ID)
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.toggle_mode = QComboBox()
        self.toggle_mode.addItem("Просто щёлкать", "")
        for key, (title, cols, rows, _pattern, _range) in PUZZLES.items():
            self.toggle_mode.addItem(f"Головоломка: {title.lower()} ({cols}×{rows})", key)
        bar.addWidget(self.toggle_mode)
        bar.addStretch()
        self.hint_button = QPushButton(tr("Подсказка"))
        self.restart_button = QPushButton(tr("Заново"))
        self.next_button = QPushButton(tr("Дальше"))
        for button, action in ((self.hint_button, self.toggles.show_hint), (self.restart_button, self._restart_level),
                               (self.next_button, self._next_level)):
            button.setAutoDefault(False)
            button.clicked.connect(action)
            bar.addWidget(button)
        column.addLayout(bar)
        column.addWidget(self.toggles, 1)
        self.toggle_mode.currentIndexChanged.connect(lambda _i: self._start_toggles())
        saved = self.settings.value("toggles_mode", "") or ""
        self.toggle_mode.setCurrentIndex(max(0, self.toggle_mode.findData(saved)))
        self._start_toggles()
        return page

    def _skipped(self, skips, distance, record):
        self.settings.setValue("skip_best", self.skip.best)
        self.settings.setValue("skip_best_distance", round(self.skip.best_distance, 1))
        if skips == 0:
            text = f"Бульк на {distance:.0f} м - сразу ко дну. Площе!"
        else:
            text = f"Блинчиков: {skips}, улетел на {distance:.0f} м"
        if record:
            text += " - новый рекорд!"
        else:
            text += f" · рекорд {self.skip.best}"
        self.count.setText(text)

    def _toggle_level(self, kind):
        return max(1, int(self.settings.value(f"toggles_level_{kind}", 1) or 1))

    def _start_toggles(self):
        kind = self.toggle_mode.currentData() or None
        self.settings.setValue("toggles_mode", kind or "")
        self.toggles.start_puzzle(kind, self._toggle_level(kind) if kind else 1)
        self._update_toggle_buttons()

    def _restart_level(self):
        self.toggles.start_puzzle(self.toggles.puzzle, self.toggles.level)
        self._update_toggle_buttons()

    def _next_level(self):
        kind = self.toggles.puzzle
        if kind is None:
            return
        level = self.toggles.level + 1
        self.settings.setValue(f"toggles_level_{kind}", level)
        self.toggles.start_puzzle(kind, level)
        self._update_toggle_buttons()

    def _update_toggle_buttons(self):
        puzzle = self.toggles.puzzle is not None
        for button in (self.hint_button, self.restart_button, self.next_button):
            button.setVisible(puzzle)
        self.next_button.setEnabled(puzzle and self.toggles.solved)
        self.hint_button.setEnabled(puzzle and not self.toggles.solved)

    def _blocks_changed(self):
        if self.blocks.best > int(self.settings.value("blocks_best", 0) or 0):
            self.settings.setValue("blocks_best", self.blocks.best)

    def _show_page(self, index):
        self.pages.setCurrentIndex(index)
        if self.pages.widget(index) is self.blocks:
            self.blocks.setFocus()
        self.group.buttons()[index].setChecked(True)
        self.refill.setVisible(index in (0, 3))
        self.refill.setText(tr("Разровнять") if index == 3 else tr("Новый лист"))
        self._update_count()

    def _popped(self):
        self._play("pop")
        self._update_count()
        if self.wrap.all_popped():
            QTimer.singleShot(700, self, self._refill)          # лист кончился - новый сам

    def _refill(self):
        if self.pages.currentIndex() == 3:
            self.sand.smooth()
        else:
            self.wrap.refill()
        self._update_count()

    def _update_count(self):
        if not hasattr(self, "count"):
            return                                       # окно ещё собирается
        index = self.pages.currentIndex()
        if index == 4 and self.toggles.puzzle is not None:
            t = self.toggles
            title = PUZZLES[t.puzzle][0]
            if t.solved:
                self.count.setText(tr("{title}, уровень {level}: решено за {moves}! Жми «Дальше»").format(title=title, level=t.level, moves=t.moves))
            else:
                self.count.setText(tr("{title}, уровень {level} · ходов {moves} · зажги все клавиши. Клавиша "
                                      "переключает и соседей").format(title=title, level=t.level, moves=t.moves))
            self._update_toggle_buttons()
            return
        if index:
            self.count.setText(HINTS[index])
            return
        total = self.wrap.popped_total
        self.count.setText(tr("Лопнуто: {total}").format(total=total) if total else tr("Щёлкай по пузырькам или веди мышью с зажатой кнопкой"))
