# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Антистресс (F12): пупырка, мячик, спиннер, песок с граблями и тумблеры. Отдельное окошко -
на экране ничего не занимает: открылось по клавише, помял, закрыл и пишешь дальше."""

import math
import random

from PySide6.QtCore import QEasingCurve, QElapsedTimer, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QWidget

from . import config as C
from .dialogs import Sheet

COLUMNS, ROWS = 9, 6
INDIGO, OCHRE = QColor("#2e2a6e"), QColor("#d4a02e")


class BubbleWrap(QWidget):
    """Лист пупырки: щёлкни по пузырьку - лопнет. Можно вести мышью с зажатой кнопкой - лопаются подряд."""

    def __init__(self, on_pop=None):
        super().__init__()
        self.on_pop = on_pop
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.PointingHandCursor)
        self.popped_total = 0
        self.refill()

    def refill(self):
        self.popped = set()
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
        self.popped_total += 1
        if self.on_pop:
            self.on_pop()
        self.update()
        return True

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

    def __init__(self, on_bounce=None):
        super().__init__()
        self.on_bounce = on_bounce
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.OpenHandCursor)
        self.squeeze = 0.0                     # 0 - круглый, 1 - сплющен до предела
        self.squash_axis = 1                   # 1 - сплющен сверху вниз (пол), 0 - с боков (стенка)
        self.press_point = QPointF()
        self.held = QElapsedTimer()
        self.grow = QTimer(self, interval=16)
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
        self.physics = QTimer(self, interval=16)
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
    """Спиннер: раскрути мышью - крутится долго и тихо шуршит, понемногу тормозя."""

    FRICTION = 0.35            # на сколько оборотов в секунду замедляется за секунду (плюс сопротивление)

    def __init__(self, on_whirr=None):
        super().__init__()
        self.on_whirr = on_whirr
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.OpenHandCursor)
        self.angle = 0.0
        self.speed = 0.0                       # градусов в секунду
        self.top_rpm = 0
        self.last = None
        self.clock = QElapsedTimer()
        self.since_sound = 0.0
        self.timer = QTimer(self, interval=16)
        self.timer.timeout.connect(self._step)

    def rpm(self):
        return abs(self.speed) / 6

    def _polar(self, point):
        c = QPointF(self.width() / 2, self.height() / 2)
        return math.degrees(math.atan2(point.y() - c.y(), point.x() - c.x()))

    def mousePressEvent(self, event):
        self.last = (self._polar(event.position()), QElapsedTimer())
        self.last[1].start()
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self.last is None:
            return
        angle, clock = self.last
        now = self._polar(event.position())
        delta = (now - angle + 180) % 360 - 180
        seconds = max(0.008, clock.restart() / 1000)
        push = delta / seconds
        self.speed = max(-4000.0, min(4000.0, self.speed * 0.6 + push * 0.6))
        self.angle += delta
        self.last = (now, clock)
        self.spin()

    def mouseReleaseEvent(self, _event):
        self.last = None
        self.setCursor(Qt.OpenHandCursor)

    def flick(self, speed):
        self.speed = speed
        self.spin()

    def spin(self):
        self.top_rpm = max(self.top_rpm, int(self.rpm()))
        if not self.timer.isActive():
            self.clock.start()
            self.timer.start()

    def _step(self):
        dt = min(0.05, self.clock.restart() / 1000) if self.clock.isValid() else 0.016
        sign = 1 if self.speed > 0 else -1
        slow = (self.FRICTION * 360 + abs(self.speed) * 0.05) * dt
        self.speed = sign * max(0.0, abs(self.speed) - slow)
        self.angle = (self.angle + self.speed * dt) % 360
        self.since_sound += dt
        if self.on_whirr and self.rpm() > 60 and self.since_sound > 0.45:
            self.since_sound = 0.0
            self.on_whirr(min(1.0, self.rpm() / 500))
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
            p.setPen(QPen(OCHRE, 2.4))
            p.setBrush(INDIGO)
            p.drawPath(body)
            for k in range(3):
                a = math.radians(k * 120 - 90)
                lobe = QPointF(math.cos(a), math.sin(a)) * size * 0.62
                p.setBrush(QColor("#1b1840"))
                p.setPen(QPen(OCHRE, 2))
                p.drawEllipse(lobe, size * 0.22, size * 0.22)
                p.setBrush(OCHRE.lighter(115))
                p.setPen(Qt.NoPen)
                p.drawEllipse(lobe, size * 0.08, size * 0.08)
            p.restore()
        p.setOpacity(1.0)
        p.setBrush(OCHRE)
        p.setPen(QPen(INDIGO.darker(130), 2))
        p.drawEllipse(QPointF(), size * 0.17, size * 0.17)          # центр под пальцем не крутится
        p.end()


class ZenSand(QWidget):
    """Песок с граблями: веди мышью с зажатой кнопкой - остаются бороздки. «Разровнять» - чисто."""

    TINES = 5

    def __init__(self):
        super().__init__()
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.CrossCursor)
        self.image = QImage()
        self.last = None
        self.strokes = 0
        self.stones = []

    def smooth(self):
        self.image = QImage()
        self.stones = [(random.uniform(0.15, 0.85), random.uniform(0.2, 0.8), random.uniform(0.05, 0.08))
                       for _ in range(random.randint(2, 3))]
        self.strokes = 0
        self.update()

    def _ensure(self):
        if self.image.size() != self.size() or self.image.isNull():
            old = self.image
            self.image = QImage(self.size(), QImage.Format_ARGB32_Premultiplied)
            self.image.fill(Qt.transparent)
            if not old.isNull():
                p = QPainter(self.image)
                p.drawImage(0, 0, old)
                p.end()
            if not self.stones:
                self.smooth()
                self._ensure()

    def mousePressEvent(self, event):
        self.last = event.position()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self.last is None:
            return
        point = event.position()
        if (point - self.last).manhattanLength() < 3:
            return
        self.rake(self.last, point)
        self.last = point

    def mouseReleaseEvent(self, _event):
        if self.last is not None:
            self.strokes += 1
        self.last = None

    def rake(self, a, b):
        """Протащить грабли от a к b: зубья стоят поперёк движения."""
        self._ensure()
        dx, dy = b.x() - a.x(), b.y() - a.y()
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        gap = max(6.0, min(self.width(), self.height()) * 0.022)
        p = QPainter(self.image)
        p.setRenderHint(QPainter.Antialiasing)
        for k in range(self.TINES):
            off = (k - (self.TINES - 1) / 2) * gap
            shift = QPointF(nx * off, ny * off)
            p.setPen(QPen(QColor(90, 70, 40, 70), gap * 0.42, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(a + shift, b + shift)                     # бороздка
            p.setPen(QPen(QColor(255, 248, 225, 60), gap * 0.18, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(a + shift + QPointF(-1, -1.5), b + shift + QPointF(-1, -1.5))   # светлый край
        p.end()
        self.update()

    def paintEvent(self, _event):
        self._ensure()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#d9c79f"))
        p.drawRoundedRect(rect, 12, 12)
        rnd = random.Random(7)                                  # зерно - один и тот же узор песчинок
        p.setBrush(QColor(140, 115, 70, 40))
        for _ in range(500):
            p.drawEllipse(QPointF(rnd.uniform(rect.left(), rect.right()), rnd.uniform(rect.top(), rect.bottom())),
                          0.9, 0.9)
        p.drawImage(0, 0, self.image)
        side = min(self.width(), self.height())
        for x, y, r in self.stones:
            center = QPointF(x * self.width(), y * self.height())
            p.setBrush(QColor(0, 0, 0, 50))
            p.drawEllipse(center + QPointF(3, 5), r * side * 1.1, r * side * 0.8)
            stone = QRadialGradient(center - QPointF(r * side * 0.3, r * side * 0.3), r * side * 1.4)
            stone.setColorAt(0, QColor("#8a8794"))
            stone.setColorAt(1, QColor("#3d3b49"))
            p.setBrush(stone)
            p.drawEllipse(center, r * side * 1.1, r * side * 0.8)
        p.end()


class Toggles(QWidget):
    """Доска тумблеров: щёлк туда, щёлк обратно. Просто ради щелчка."""

    COLS, ROWS_ = 5, 3

    def __init__(self, on_click=None):
        super().__init__()
        self.on_click = on_click
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.PointingHandCursor)
        self.state = [[False] * self.COLS for _ in range(self.ROWS_)]
        self.flips = 0
        self.anim = {}

    def cell_rect(self, col, row):
        w, h = self.width() / self.COLS, self.height() / self.ROWS_
        return QRectF(col * w, row * h, w, h)

    def toggle(self, col, row):
        self.state[row][col] = not self.state[row][col]
        self.flips += 1
        animation = QVariantAnimation(self)
        animation.setDuration(140)
        animation.setEasingCurve(QEasingCurve.OutBack)
        start = 0.0 if self.state[row][col] else 1.0
        animation.setStartValue(start)
        animation.setEndValue(1.0 - start)
        animation.valueChanged.connect(lambda v, k=(col, row): (self.anim.__setitem__(k, float(v)), self.update()))
        animation.start(QVariantAnimation.DeleteWhenStopped)
        if self.on_click:
            self.on_click(self.state[row][col])
        self.update()

    def mousePressEvent(self, event):
        col = int(event.position().x() // (self.width() / self.COLS))
        row = int(event.position().y() // (self.height() / self.ROWS_))
        if 0 <= col < self.COLS and 0 <= row < self.ROWS_:
            self.toggle(col, row)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for row in range(self.ROWS_):
            for col in range(self.COLS):
                rect = self.cell_rect(col, row)
                c = rect.center()
                plate = QRectF(0, 0, rect.width() * 0.42, rect.height() * 0.72)
                plate.moveCenter(c)
                p.setPen(QPen(OCHRE.darker(140), 1.5))
                p.setBrush(INDIGO)
                p.drawRoundedRect(plate, 8, 8)
                on = self.state[row][col]
                t = self.anim.get((col, row), 1.0 if on else 0.0)   # 0 - вниз (выкл), 1 - вверх (вкл)
                lamp = QPointF(c.x(), plate.top() + plate.height() * 0.14)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#f6d27a") if on else QColor("#4a4370"))
                p.drawEllipse(lamp, plate.width() * 0.1, plate.width() * 0.1)
                pivot = QPointF(c.x(), c.y() + plate.height() * 0.12)
                tip = pivot + QPointF(0, -plate.height() * 0.24 * (2 * t - 1))
                p.setPen(QPen(QColor("#c9c4d8"), plate.width() * 0.16, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(pivot, tip)
                p.setPen(QPen(INDIGO.darker(150), 1.5))
                p.setBrush(OCHRE)
                p.drawEllipse(tip, plate.width() * 0.14, plate.width() * 0.14)
                p.setBrush(QColor("#1b1840"))
                p.drawEllipse(pivot, plate.width() * 0.12, plate.width() * 0.12)
        p.end()


PAGES = ("Пупырка", "Мячик", "Спиннер", "Песок", "Тумблеры")
HINTS = {
    1: "Зажми мячик и подержи - сожмётся. Схвати и брось - отскочит",
    2: "Раскрути спиннер мышью",
    3: "Веди мышью с зажатой кнопкой - грабли оставят бороздки",
    4: "Щёлк",
}


class StressDialog(Sheet):
    def __init__(self, parent=None):
        super().__init__(parent, "Антистресс")
        sounds = getattr(parent, "sounds", None)
        self._play = sounds.play if sounds is not None else (lambda *_a: None)
        tabs = QHBoxLayout()
        self.group = QButtonGroup(self)
        self.pages = QStackedWidget()
        self.wrap = BubbleWrap(on_pop=self._popped)
        self.ball = SquishBall(on_bounce=lambda strength: self._play("ball_bounce", strength))
        self.spinner = Spinner(on_whirr=lambda strength: self._play("spinner", strength))
        self.sand = ZenSand()
        self.toggles = Toggles(on_click=lambda on: self._play("type_space" if on else "type_1", 0.6))
        for index, (title, page) in enumerate(zip(PAGES, (self.wrap, self.ball, self.spinner, self.sand,
                                                          self.toggles))):
            button = QPushButton(title)
            button.setCheckable(True)
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
        self.refill = refill = QPushButton("Новый лист")
        refill.clicked.connect(self._refill)
        close = QPushButton("Закрыть")
        close.setProperty("minor", True)
        close.clicked.connect(self.accept)
        row.addWidget(refill)
        row.addWidget(close)
        self.content.addLayout(row)
        self._update_count()

    def _show_page(self, index):
        self.pages.setCurrentIndex(index)
        self.group.buttons()[index].setChecked(True)
        self.refill.setVisible(index in (0, 3))
        self.refill.setText("Разровнять" if index == 3 else "Новый лист")
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
        index = self.pages.currentIndex()
        if index:
            self.count.setText(HINTS[index])
            return
        total = self.wrap.popped_total
        self.count.setText(f"Лопнуто: {total}" if total else "Щёлкай по пузырькам или веди мышью с зажатой кнопкой")
