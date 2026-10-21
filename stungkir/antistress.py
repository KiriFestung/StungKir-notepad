# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Антистресс (F12): пупырка, мячик, спиннер, песок с граблями и тумблеры. Отдельное окошко -
на экране ничего не занимает: открылось по клавише, помял, закрыл и пишешь дальше."""

import math
import random

from PySide6.QtCore import QEasingCurve, QElapsedTimer, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QRadialGradient
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
    """Сад камней: веди мышью с зажатой кнопкой - грабли оставляют ровные бороздки, камни они
    обходят (поднимаются над ними). Вокруг камней - круги, как в настоящем саду. «Разровнять» - чисто."""

    TINES = 5
    SAND, SAND_DARK, SAND_LIGHT = QColor("#d8c59b"), QColor("#a88d5e"), QColor("#f6ead0")

    def __init__(self, on_rake=None):
        super().__init__()
        self.on_rake = on_rake
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.CrossCursor)
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
        self.base = QImage()
        self.update()

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
        for x, y, r in self.stones:
            center = self._px((x, y))
            rx, ry = r * side * 1.12, r * side * 0.82
            shadow = QRadialGradient(center + QPointF(rx * 0.25, ry * 0.55), rx * 1.4)
            shadow.setColorAt(0, QColor(60, 45, 20, 120))
            shadow.setColorAt(1, QColor(60, 45, 20, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(shadow)
            p.drawEllipse(center + QPointF(rx * 0.25, ry * 0.55), rx * 1.4, ry * 1.2)
            stone = QRadialGradient(center - QPointF(rx * 0.35, ry * 0.45), rx * 1.5)
            stone.setColorAt(0, QColor("#9a97a3"))
            stone.setColorAt(0.55, QColor("#5d5a68"))
            stone.setColorAt(1, QColor("#2c2a36"))
            p.setBrush(stone)
            p.drawEllipse(center, rx, ry)
            p.setBrush(QColor(255, 255, 255, 40))                        # блик
            p.drawEllipse(center - QPointF(rx * 0.35, ry * 0.42), rx * 0.32, ry * 0.18)
        p.end()


class Toggles(QWidget):
    """Пульт тумблеров: щёлк вверх, щёлк вниз, лампочка горит. Под крышкой справа внизу -
    красный «Не трогать»: откинь крышку и щёлкни - пульт устроит переполох огоньками."""

    COLS, ROWS_ = 5, 3
    LABELS = ("Муза", "Кофе", "Тишина", "Сюжет", "Диалоги",
              "Злодей", "Дедлайн", "Котик", "Ночь", "Музыка",
              "Чай", "Редактор", "Свет", "Сон", "НЕ ТРОГАТЬ")
    SPECIAL = (4, 2)

    def __init__(self, on_sound=None):
        super().__init__()
        self.on_sound = on_sound
        self.setMinimumSize(COLUMNS * 52, ROWS * 52)
        self.setCursor(Qt.PointingHandCursor)
        self.state = [[False] * self.COLS for _ in range(self.ROWS_)]
        self.flips = 0
        self.anim = {}
        self.guard_open = False
        self.guard_t = 0.0
        self.party = 0.0
        self._party = QVariantAnimation(self)
        self._party.setDuration(2400)
        self._party.setStartValue(0.0)
        self._party.setEndValue(1.0)
        self._party.valueChanged.connect(lambda v: (setattr(self, "party", float(v)), self.update()))
        self._party.finished.connect(lambda: (setattr(self, "party", 0.0), self.update()))

    def cell_rect(self, col, row):
        inner = QRectF(self.rect()).adjusted(14, 14, -14, -14)
        w, h = inner.width() / self.COLS, inner.height() / self.ROWS_
        return QRectF(inner.left() + col * w, inner.top() + row * h, w, h)

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

    def mousePressEvent(self, event):
        for row in range(self.ROWS_):
            for col in range(self.COLS):
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
        metal.setColorAt(0, QColor("#3b3f63"))
        metal.setColorAt(1, QColor("#1b1d36"))
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
        for row in range(self.ROWS_):
            for col in range(self.COLS):
                self._paint_switch(p, col, row, font)
        p.end()

    def _paint_switch(self, p, col, row, font):
        rect = self.cell_rect(col, row)
        c = rect.center()
        unit = min(rect.width(), rect.height())
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
        color = QColor("#ff5a4a") if special else OCHRE.lighter(120)
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
        # гайка с основанием
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
        # рычаг: вверх - вкл, вниз - выкл; посередине хода он смотрит на нас и кажется короче
        on = self.state[row][col]
        t = self.anim.get((col, row), 1.0 if on else 0.0)
        reach = unit * 0.25 * (2 * t - 1)
        tip = pivot + QPointF(0, -reach)
        lever = QPen(QColor("#d7d9e3"), unit * 0.07, Qt.SolidLine, Qt.RoundCap)
        p.setPen(QPen(QColor(0, 0, 0, 70), unit * 0.08, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(pivot + QPointF(2, 3), tip + QPointF(3, 4))                 # тень рычага
        p.setPen(lever)
        p.drawLine(pivot, tip)
        knob = QRadialGradient(tip - QPointF(unit * 0.02, unit * 0.025), unit * 0.07)
        knob.setColorAt(0, QColor("#ffffff"))
        knob.setColorAt(1, QColor("#8d90a6") if not special else QColor("#b02a22"))
        p.setPen(QPen(QColor("#2a2c40"), 1))
        p.setBrush(knob)
        p.drawEllipse(tip, unit * 0.055, unit * 0.055)
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


PAGES = ("Пупырка", "Мячик", "Спиннер", "Песок", "Тумблеры")
HINTS = {
    1: "Зажми мячик и подержи - сожмётся. Схвати и брось - отскочит",
    2: "Раскрути спиннер мышью",
    3: "Веди мышью с зажатой кнопкой - грабли оставят бороздки",
    4: "Щёлк. А красный - под крышкой: откинь и попробуй",
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
        self.sand = ZenSand(on_rake=lambda strength: self._play("sand_rake", strength))
        self.toggles = Toggles(on_sound=lambda name: self._play(name, 0.8))
        for index, (title, page) in enumerate(zip(PAGES, (self.wrap, self.ball, self.spinner, self.sand,
                                                          self.toggles))):
            button = QPushButton(title)
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
