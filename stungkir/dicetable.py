# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Стол для бросков в «Рандомайзерах»: кубик вылетает с края, катится и отскакивает от бортов,
кувыркается и ложится выпавшим числом вверх; монетка подлетает, крутится и падает на стол.

Кубики трёх материалов - кость, металл, дуб: у каждого свой цвет, рисунок на гранях
(прожилки кости, шлифовка металла, волокна дуба) и свой стук о стол.

Честность: число выбирается заранее обычным случайным выбором (как у всех бросков блокнота),
а потом подбирается такой бросок - откуда вылетел, как закручен, - после которого кубик сам
ложится этим числом вверх. Надпись на грани не переписывается на глазах."""

import math
import random

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QBrush,
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient, QTransform,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import config as C
from .dice import (
    COIN_EDGE, COIN_SIDES, IDENTITY, Die3D, _apply, _cross, _dot, _mul, _norm, _sub, axis_angle, d100_parts,
    d100_value, form, labels, rotation, shape,
)

# материал: (основа, тёмная, светлая, цвет чисел, звук удара, звук «докатился»)
MATERIALS = {
    "bone": ("Кость", "#e9e2cf", "#8a7f62", "#fbf8ee", "#2a2680", "bone_hit", "bone_settle"),
    "metal": ("Металл", "#9aa0ad", "#2f343c", "#dfe3ec", "#2a2680", "die_hit", "die_settle"),
    "oak": ("Дуб", "#9c6a3a", "#4a2e14", "#c99560", "#24130a", "oak_hit", "oak_settle"),
    # смола цвета индиго с золотыми цифрами - как классические кости для настолок и как тема блокнота
    "resin": ("Индиго", "#2a2696", "#07073a", "#5652d8", "#e8a93a", "bone_hit", "bone_settle"),
}
FELT, FELT_DARK, RIM = QColor("#23265a"), QColor("#13153a"), QColor("#6b4524")
STEP = 1 / 60                        # шаг расчёта: один и тот же и в подборе броска, и на экране
GRAVITY = 2200.0
SETTLE = 0.36                        # секунды: укладка выпавшей гранью вверх
TRIES = 220


class TableBody:
    """Кость или монетка на столе: где она, как летит и крутится, что на гранях."""

    def __init__(self, kind, faces, material, radius):
        self.kind, self.labels, self.material, self.radius = kind, list(faces), material, radius
        self.matrix = rotation((1, 0.6, 0.2), 0.75)
        self.x = self.y = self.z = 0.0
        self.vx = self.vy = self.vz = 0.0
        self.w = (0.0, 0.0, 0.0)                 # угловая скорость: ось * обороты
        self.t = 0.0
        self.landings = 0
        self.settle_from = self.settle_turn = None
        self.settle_t = 0.0
        self.front = None
        self.target = None
        self.done = False

    def state(self):
        return (self.x, self.y, self.z, self.vx, self.vy, self.vz, self.w, [r[:] for r in self.matrix], self.t,
                self.landings)

    def restore(self, state):
        (self.x, self.y, self.z, self.vx, self.vy, self.vz, self.w, matrix, self.t, self.landings) = state
        self.matrix = [r[:] for r in matrix]


class DiceTable(QWidget):
    """Стол. throw(sides, result, material) и toss(side) - бросить; finish() - сразу в конец (проверки)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(520, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.bodies = []
        self.mode = None                          # "dice" или "coin"
        self.sides = 20
        self.result = None
        self.on_done = None
        self.on_sound = None                      # (имя, сила)
        self.relabeled = 0
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._frame)

    def sizeHint(self):
        return QSize(640, 290)

    @property
    def rolling(self):
        return self.timer.isActive()

    # ---------------- броски ----------------
    def throw(self, sides, result, material="bone", on_done=None):
        self.mode, self.sides, self.result, self.on_done = "dice", sides, result, on_done
        material = material if material in MATERIALS else "bone"
        if sides == 100:
            tens = [f"{n:02d}" for n in range(0, 100, 10)]
            units = [str(n) for n in range(10)]
            self.bodies = [TableBody(10, tens, material, 38), TableBody(10, units, material, 38)]
            targets = d100_parts(result)
        else:
            self.bodies = [TableBody(form(sides), labels(sides), material, 46)]
            targets = [str(result)]
        lanes = [0.38, 0.66] if len(self.bodies) == 2 else [random.uniform(0.35, 0.65)]
        for body, target, lane in zip(self.bodies, targets, lanes):
            body.target = target
            body.labels = self._shuffled(body.labels)
            self._aim(body, lambda b, lane=lane: self._launch_die(b, lane))
        self._sound(MATERIALS[material][5], 0.5)
        self.timer.start()
        self.update()

    def toss(self, side, on_done=None):
        self.mode, self.sides, self.result, self.on_done = "coin", "coin", side, on_done
        body = TableBody("coin", list(COIN_SIDES), "coin", 46)
        body.target = side
        self.bodies = [body]
        self._aim(body, self._launch_coin)
        self._sound("coin_flick", 1.0)
        self.timer.start()
        self.update()

    @staticmethod
    def _shuffled(names):
        names = list(names)
        random.shuffle(names)                     # где какое число - у каждого броска по-своему
        return names

    def _launch_die(self, body, lane):
        w, h = max(self.width(), 520), max(self.height(), 250)
        body.matrix = rotation(_norm((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))),
                               random.uniform(0, 6.28))
        body.x, body.y, body.z = -body.radius, h * lane, random.uniform(60, 110)
        speed = random.uniform(620, 900)
        angle = random.uniform(-0.35, 0.35)
        body.vx, body.vy, body.vz = speed * math.cos(angle), speed * math.sin(angle), random.uniform(50, 200)
        axis = _norm((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.5, 0.5)))
        spin = random.uniform(14, 22)
        body.w = tuple(a * spin for a in axis)
        body.t, body.landings = 0.0, 0
        body.width, body.height = w, h

    def _launch_coin(self, body):
        w, h = max(self.width(), 520), max(self.height(), 250)
        body.matrix = _mul(rotation((1, 0, 0), random.choice((0.0, math.pi))), rotation((0, 0, 1),
                                                                                         random.uniform(-0.4, 0.4)))
        body.x, body.y, body.z = w / 2 + random.uniform(-40, 40), h * 0.6, 0.0
        body.vx, body.vy = random.uniform(-60, 60), random.uniform(-40, 10)
        body.vz = random.uniform(820, 980)                         # вверх, к зрителю
        flip = random.uniform(24, 34)
        body.w = (flip, random.uniform(-1.5, 1.5), 0.0)
        body.t, body.landings = 0.0, 0
        body.width, body.height = w, h

    def _aim(self, body, launch):
        """Подобрать бросок, после которого вверх сама ляжет нужная грань."""
        if body.target == COIN_EDGE:
            launch(body)
            return
        if body.target not in body.labels:
            body.labels[0] = body.target
        want = body.labels.index(body.target)
        for _ in range(TRIES):
            launch(body)
            start = body.state()
            self._fly(body, sound=False)
            face = self._nearest_face(body)
            body.restore(start)
            if face == want:
                return
        # не нашлось: меняем надписи сейчас, пока кость ещё за краем стола и её не видно
        launch(body)
        start = body.state()
        self._fly(body, sound=False)
        face = self._nearest_face(body)
        body.restore(start)
        body.labels[want], body.labels[face] = body.labels[face], body.labels[want]

    def _fly(self, body, sound):
        """Прогнать полёт до укладки (для подбора броска)."""
        for _ in range(60 * 8):
            if self._step(body, sound):
                return

    # ---------------- физика ----------------
    def _step(self, body, sound=True):
        """Один шаг полёта. True - пора укладываться."""
        dt = STEP
        body.t += dt
        coin = body.kind == "coin"
        w, h, r = body.width, body.height, body.radius
        body.vz -= (GRAVITY * (0.9 if coin else 1.0)) * dt
        body.z += body.vz * dt
        if body.z <= 0:
            body.z = 0.0
            if body.vz < -70:
                body.landings += 1
                if sound:
                    strength = min(1.0, -body.vz / (900 if coin else 700))
                    name = "coin_land" if coin else MATERIALS[body.material][5]
                    self._sound(name, strength if not coin or body.landings == 1 else strength * 0.4)
                body.vz = -body.vz * (0.3 if coin else 0.42)
                if coin:                                           # монетка от стола теряет вращение
                    body.w = tuple(c * 0.45 for c in body.w)
            else:
                body.vz = 0.0
        body.x += body.vx * dt
        body.y += body.vy * dt
        # борт: деревянная рамка (10 точек) плюс сама кость - в перспективе углы выходят за radius
        edge = 12 + r * (1.0 if coin else 1.3)
        for axis, low, high in (("x", edge, w - edge), ("y", edge, h - edge)):
            value, speed = getattr(body, axis), getattr(body, "v" + axis)
            if (value < low and speed < 0) or (value > high and speed > 0):
                setattr(body, axis, low if value < low else high)
                setattr(body, "v" + axis, -speed * 0.55)
                body.w = (body.w[1], -body.w[0], body.w[2])            # удар о борт закручивает иначе
                if sound and not coin:
                    self._sound(MATERIALS[body.material][5], min(1.0, abs(speed) / 900) * 0.7)
        if body.z == 0 and body.vz == 0:
            decay = math.exp(-(2.6 if coin else 1.7) * dt)
            body.vx *= decay
            body.vy *= decay
            if not coin:                                           # катится: ось вращения - поперёк хода
                roll = (body.vy / r, -body.vx / r, body.w[2] * 0.9)
                k = min(1.0, 7 * dt)
                body.w = tuple(a + (b - a) * k for a, b in zip(body.w, roll))
            else:
                body.w = tuple(c * math.exp(-4 * dt) for c in body.w)
        else:
            body.w = tuple(c * math.exp(-0.15 * dt) for c in body.w)
        size = math.sqrt(_dot(body.w, body.w))
        if size > 1e-6:
            body.matrix = _mul(rotation(tuple(c / size for c in body.w), size * dt), body.matrix)
        speed = math.hypot(body.vx, body.vy)
        if coin:
            return body.landings >= 2 and body.z == 0 and body.vz == 0
        return body.t > 0.9 and body.z == 0 and body.vz == 0 and speed < 60

    def _nearest_face(self, body):
        points, faces = shape(body.kind)
        best, best_dot = 0, -2.0
        for i, face in enumerate(faces[:len(body.labels)]):
            normal = Die3D._normal(points, face, body.matrix)
            if normal[2] > best_dot:
                best, best_dot = i, normal[2]
        return best

    def _begin_settle(self, body):
        points, faces = shape(body.kind)
        body.settle_from = [row[:] for row in body.matrix]
        if body.target == COIN_EDGE:
            body.front = None
            target = _mul(Die3D.REST_TILT, rotation((0, 1, 0), math.pi / 2 - 0.25))
        else:
            best = self._nearest_face(body)
            if body.labels[best] != body.target:                  # не должно случаться
                other = body.labels.index(body.target)
                body.labels[other], body.labels[best] = body.labels[best], body.target
                self.relabeled += 1
            body.front = best
            normal = Die3D._normal(points, faces[best], body.matrix)
            align_axis = _cross(normal, (0, 0, 1))
            align = rotation(align_axis, math.acos(max(-1.0, min(1.0, normal[2])))) \
                if _dot(align_axis, align_axis) > 1e-9 else IDENTITY
            aligned = _mul(align, body.matrix)
            up = _apply(aligned, Die3D._up(points, faces[best]))
            # цифрой к зрителю и чуть наклонён, чтобы был виден объём
            target = _mul(Die3D.REST_TILT, _mul(rotation((0, 0, 1), math.atan2(up[0], up[1])), aligned))
        current_t = [list(r) for r in zip(*body.matrix)]
        body.settle_turn = axis_angle(_mul(target, current_t))
        body.settle_t = 0.0

    def _frame(self):
        active = False
        for body in self.bodies:
            if body.done:
                continue
            active = True
            if body.settle_from is None:
                if self._step(body):
                    self._begin_settle(body)
                continue
            body.settle_t += STEP
            k = min(1.0, body.settle_t / SETTLE)
            eased = 1 - (1 - k) ** 3
            axis, angle = body.settle_turn
            body.matrix = _mul(rotation(axis, angle * eased), body.settle_from)
            decay = math.exp(-5 * STEP)
            body.vx *= decay
            body.vy *= decay
            body.x += body.vx * STEP
            body.y += body.vy * STEP
            if k >= 1.0:
                body.done = True
        if not active:
            self.timer.stop()
            if self.mode == "dice":
                self._sound(MATERIALS[self.bodies[0].material][6], 0.45)
            if self.on_done:
                self.on_done(self.result)
        self.update()

    def finish(self):
        while self.timer.isActive():
            self._frame()

    def front_label(self):
        if self.mode == "coin":
            body = self.bodies[0]
            return COIN_EDGE if body.target == COIN_EDGE and body.done else (
                body.labels[body.front] if body.front is not None else None)
        if self.sides == 100 and len(self.bodies) == 2:
            parts = [b.labels[b.front] if b.front is not None else None for b in self.bodies]
            return None if None in parts else str(d100_value(*parts))
        body = self.bodies[0] if self.bodies else None
        return body.labels[body.front] if body is not None and body.front is not None else None

    def _sound(self, name, strength):
        if self.on_sound:
            self.on_sound(name, strength)

    # ---------------- рисование ----------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        self._paint_table(p)
        sx = self.width() / max(1.0, self.bodies[0].width) if self.bodies and hasattr(self.bodies[0], "width") else 1
        sy = self.height() / max(1.0, self.bodies[0].height) if self.bodies and hasattr(self.bodies[0], "height") else 1
        for body in sorted(self.bodies, key=lambda b: b.y):
            if not hasattr(body, "width"):
                continue
            x, y = body.x * sx, body.y * sy
            lift = body.z
            scale = 1 + lift / (420 if body.kind == "coin" else 900)
            radius = body.radius * scale
            # тень на сукне: дальше и бледнее, когда кость в воздухе
            shadow = QRadialGradient(QPointF(x + lift * 0.18, y + radius * 0.55), radius * (1.1 + lift / 600))
            shadow.setColorAt(0, QColor(0, 0, 0, int(120 * max(0.25, 1 - lift / 500))))
            shadow.setColorAt(1, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(shadow)
            p.drawEllipse(QPointF(x + lift * 0.18, y + radius * 0.55), radius * 1.15, radius * 0.5)
            self._paint_body(p, body, x, y - lift * 0.45, radius)
        p.end()

    def _paint_table(self, p):
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        wood = QLinearGradient(rect.topLeft(), rect.bottomRight())
        wood.setColorAt(0, RIM.lighter(125))
        wood.setColorAt(1, RIM.darker(130))
        p.setBrush(wood)
        p.drawRoundedRect(rect, 14, 14)
        felt_rect = rect.adjusted(10, 10, -10, -10)
        cloth = self._cloth()
        if not cloth.isNull():                     # сукно - нарисованное, цветом темы, края чуть темнее
            p.setBrush(QBrush(cloth))
            p.drawRoundedRect(felt_rect, 9, 9)
            felt = QRadialGradient(felt_rect.center(), max(felt_rect.width(), felt_rect.height()) * 0.7)
            felt.setColorAt(0, QColor(0, 0, 0, 0))
            edge = C.mix(self._felt_color(), "#000000", 0.65)
            felt.setColorAt(1, QColor(edge.red(), edge.green(), edge.blue(), 190))
        else:
            felt = QRadialGradient(felt_rect.center(), max(felt_rect.width(), felt_rect.height()) * 0.7)
            felt.setColorAt(0, FELT.lighter(118))
            felt.setColorAt(1, FELT_DARK)
        p.setBrush(felt)
        p.drawRoundedRect(felt_rect, 9, 9)
        if not cloth.isNull():
            return
        rnd = random.Random(11)                        # ворс сукна - один и тот же узор
        p.setBrush(QColor(255, 255, 255, 10))
        for _ in range(int(felt_rect.width() * felt_rect.height() / 260)):
            p.drawEllipse(QPointF(rnd.uniform(felt_rect.left(), felt_rect.right()),
                                  rnd.uniform(felt_rect.top(), felt_rect.bottom())), 0.8, 0.8)

    @staticmethod
    def _felt_color():
        colors = C.toy_colors()
        if colors["dark"]:
            return C.mix(colors["body"], colors["bg"], 0.2)
        return C.mix(colors["body"], "#3a4a3a", 0.35)            # на светлой теме - приглушённое сукно

    def _cloth(self):
        """Плитка сукна цвета темы: рисунок ворса из art/texture-felt.png, перекрашенный
        (яркость каждой точки сохраняется, цвет - от темы). Считается один раз на цвет."""
        from PySide6.QtGui import QImage, QPixmap
        from .artwork import scaled
        ratio = self.devicePixelRatioF()
        felt = self._felt_color()
        key = (felt.name(), round(ratio, 2))
        cache = self.__dict__.setdefault("_cloth_cache", {})
        if key in cache:
            return cache[key]
        source = scaled("texture-felt", 256, ratio)
        if source.isNull():
            cache[key] = source
            return source
        gray = source.toImage().convertToFormat(QImage.Format_Grayscale8)
        width, height = gray.width(), gray.height()
        stride = gray.bytesPerLine()
        data = bytes(gray.constBits())[:stride * height]
        values = [data[y * stride + x] for y in range(height) for x in range(width)]
        mean = max(1.0, sum(values) / len(values))
        r, g, b = felt.red(), felt.green(), felt.blue()
        out = bytearray(width * height * 4)
        for i, v in enumerate(values):
            k = v / mean
            out[i * 4] = min(255, int(b * k))
            out[i * 4 + 1] = min(255, int(g * k))
            out[i * 4 + 2] = min(255, int(r * k))
            out[i * 4 + 3] = 255
        image = QImage(bytes(out), width, height, width * 4, QImage.Format_ARGB32).copy()
        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(ratio)
        cache[key] = pixmap
        return pixmap

    def _paint_body(self, p, body, cx, cy, radius):
        points, faces = shape(body.kind)
        world = [_apply(body.matrix, v) for v in points]
        distance = 6.0

        def project(v):
            k = distance / (distance - v[2])
            return QPointF(cx + v[0] * radius * k, cy - v[1] * radius * k)

        light = _norm((-0.45, 0.6, 0.9))
        coin = body.kind == "coin"
        if coin:
            base, dark, bright, ink = "#c8962e", "#5a3f10", "#f3d58a", "#2e2a6e"
        else:
            _title, base, dark, bright, ink, _hit, _settle = MATERIALS[body.material]
        dark, bright, base = QColor(dark), QColor(bright), QColor(base)
        drawn = []
        for i, face in enumerate(faces):
            corners = [world[j] for j in face]
            middle = tuple(sum(v[k] for v in corners) / len(corners) for k in range(3))
            normal = _norm(_cross(_sub(corners[1], corners[0]), _sub(corners[2], corners[0])))
            if _dot(normal, middle) < 0:
                normal = (-normal[0], -normal[1], -normal[2])
            facing = _dot(normal, _norm(_sub((0, 0, distance), middle)))
            if facing > 0:
                drawn.append((middle[2], i, face, normal, facing, middle))
        drawn.sort()
        for _z, i, face, normal, facing, middle in drawn:
            lit = max(0.0, _dot(normal, light))
            polygon = QPolygonF([project(world[j]) for j in face])
            if coin and i >= 2:                                    # ребро монетки - бронза с насечкой
                color = C.mix("#3a2a10", "#a8791f", (0.15 + 0.75 * lit) * (1.0 if i % 2 else 0.72))
                p.setPen(QPen(QColor("#2a1d0a"), 0.8))
            else:
                color = C.mix(C.mix(dark, base, min(1.0, 0.25 + lit)), bright, max(0.0, lit - 0.55) * 1.6)
                if body.material == "metal":                       # блик металла - резкий
                    color = C.mix(color, "#ffffff", 0.45 * lit ** 30)
                elif body.material == "resin":                     # смола блестит, как лак
                    color = C.mix(color, "#cfd2ff", 0.55 * lit ** 18)
                p.setPen(QPen(C.mix(dark, "#000000", 0.35), 1.3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(color)
            p.drawPolygon(polygon)
            if facing < 0.12:
                continue
            transform, size = self._face_transform(body, points, face, middle, project)
            if not coin:
                self._paint_grain(p, body, polygon, transform, i, facing)
            if i < len(body.labels) and facing >= 0.28:
                self._paint_label(p, body, transform, size, body.labels[i], QColor(ink), facing)

    def _face_transform(self, body, points, face, middle, project):
        up_body = Die3D._up(points, face)
        center_body = Die3D._center(points, face)
        normal_body = _norm(_cross(_sub(points[face[1]], points[face[0]]), _sub(points[face[2]], points[face[0]])))
        if _dot(normal_body, center_body) < 0:
            normal_body = (-normal_body[0], -normal_body[1], -normal_body[2])
        right_body = _cross(up_body, normal_body)
        origin = project(middle)
        right = project(_apply(body.matrix, tuple(c + r * 0.01 for c, r in zip(center_body, right_body))))
        up = project(_apply(body.matrix, tuple(c + u * 0.01 for c, u in zip(center_body, up_body))))
        transform = QTransform(right.x() - origin.x(), right.y() - origin.y(),
                               origin.x() - up.x(), origin.y() - up.y(), origin.x(), origin.y())
        inner = min(math.dist(center_body, points[j]) for j in face) * (0.72 if len(face) > 3 else 0.55)
        if body.kind == 10:
            inner *= 0.95
        return transform, inner * 100

    def _paint_grain(self, p, body, polygon, transform, index, facing):
        """Рисунок материала на грани: волокна дуба, прожилки кости, шлифовка металла."""
        clip = QPainterPath()
        clip.addPolygon(polygon)
        p.save()
        p.setClipPath(clip)
        p.setTransform(transform, True)
        p.setBrush(Qt.NoBrush)
        rnd = random.Random(index * 31 + 7)
        alpha = min(1.0, (facing - 0.12) / 0.3)
        if body.material == "oak":
            for k in range(-6, 7):
                path = QPainterPath(QPointF(-140, k * 17))
                wobble = rnd.uniform(3, 9)
                for x in range(-120, 141, 20):
                    path.lineTo(QPointF(x, k * 17 + math.sin(x / 23 + k) * wobble))
                p.setPen(QPen(QColor(50, 25, 8, int(70 * alpha)), rnd.uniform(1.5, 3.5)))
                p.drawPath(path)
            p.setPen(QPen(QColor(40, 20, 6, int(90 * alpha)), 2))
            p.drawEllipse(QPointF(rnd.uniform(-50, 50), rnd.uniform(-40, 40)), 9, 5)      # сучок
        elif body.material == "bone":
            for _ in range(5):
                path = QPainterPath(QPointF(rnd.uniform(-120, -60), rnd.uniform(-90, 90)))
                path.cubicTo(QPointF(rnd.uniform(-40, 0), rnd.uniform(-90, 90)),
                             QPointF(rnd.uniform(0, 40), rnd.uniform(-90, 90)),
                             QPointF(rnd.uniform(60, 120), rnd.uniform(-90, 90)))
                p.setPen(QPen(QColor(120, 95, 60, int(55 * alpha)), rnd.uniform(1.0, 2.2)))
                p.drawPath(path)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(110, 85, 55, int(70 * alpha)))
            for _ in range(14):
                p.drawEllipse(QPointF(rnd.uniform(-100, 100), rnd.uniform(-100, 100)), 1.6, 1.6)
        elif body.material == "resin":
            # внутри смолы - светлые разводы и блёстки, как у литых костей
            for _ in range(3):
                path = QPainterPath(QPointF(rnd.uniform(-130, -70), rnd.uniform(-80, 80)))
                path.cubicTo(QPointF(rnd.uniform(-50, 10), rnd.uniform(-110, 110)),
                             QPointF(rnd.uniform(-10, 50), rnd.uniform(-110, 110)),
                             QPointF(rnd.uniform(70, 130), rnd.uniform(-80, 80)))
                p.setPen(QPen(QColor(130, 135, 255, int(38 * alpha)), rnd.uniform(6, 14), Qt.SolidLine, Qt.RoundCap))
                p.drawPath(path)
            p.setPen(Qt.NoPen)
            for _ in range(22):
                p.setBrush(QColor(255, 225, 160, int(rnd.uniform(60, 150) * alpha)))
                p.drawEllipse(QPointF(rnd.uniform(-100, 100), rnd.uniform(-100, 100)), 1.1, 1.1)
        else:
            for k in range(-30, 31):
                p.setPen(QPen(QColor(255, 255, 255, int(rnd.uniform(8, 26) * alpha)), 0.8))
                p.drawLine(QPointF(-140, k * 4.5), QPointF(140, k * 4.5 + rnd.uniform(-1, 1)))
        p.restore()

    def _paint_label(self, p, body, transform, inner, text, ink, facing):
        size = inner * (0.95 if len(text) < 3 else 0.62 if len(text) < 4 else 0.42)
        p.save()
        p.setTransform(transform, True)
        alpha = min(1.0, (facing - 0.28) / 0.3)
        if body.kind == "coin":
            from .artwork import pixmap
            picture = pixmap(COIN_SIDES.get(text, ""))
            if not picture.isNull():
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                p.setOpacity(alpha)
                p.drawPixmap(QRectF(-86, -86, 172, 172), picture, QRectF(picture.rect()))
            p.restore()
            return
        font = QFont(C.FONT_FAMILY)
        font.setPixelSize(max(6, int(size)))
        font.setWeight(QFont.Black)
        p.setFont(font)
        box = QRectF(-150, -size * 0.75, 300, size * 1.5)
        if body.material == "resin":                       # золото в углублении: тёмная тень сверху
            p.setPen(QColor(0, 0, 0, int(150 * alpha)))
            p.drawText(box.translated(0, -size * 0.04), Qt.AlignCenter, text)
        if body.material == "metal":                       # гравировка: светлый край снизу
            edge = QColor(255, 255, 255, int(120 * alpha))
            p.setPen(edge)
            p.drawText(box.translated(0, size * 0.05), Qt.AlignCenter, text)
        color = QColor(ink)
        color.setAlphaF(alpha)
        p.setPen(color)
        p.drawText(box, Qt.AlignCenter, text)
        if text in ("6", "9"):
            p.setPen(QPen(color, max(1.0, size * 0.08), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(-size * 0.22, size * 0.5), QPointF(size * 0.22, size * 0.5))
        p.restore()
