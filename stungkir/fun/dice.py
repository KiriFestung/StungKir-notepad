# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Объёмные кубики d4-d100 и монетка: кувыркаются, замедляются и ложатся выпавшей гранью к тебе.
И «Рандомайзеры»: число от-до, строка из своего списка, персонаж или термин мира, рулетка."""

import math
import random
from functools import lru_cache
from itertools import combinations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF, QRadialGradient, QTransform
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSizePolicy, QSpinBox,
    QStackedWidget,
    QToolButton, QVBoxLayout, QWidget,
)

from ..core import config as C
from ..ui.dialogs import Sheet
from ..core.i18n import tr

PHI = (1 + 5 ** 0.5) / 2


# ---------------- немного трёхмерной математики ----------------
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    length = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / length, a[1] / length, a[2] / length)


def _apply(m, v):
    return (m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2])


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rotation(axis, angle):
    """Поворот на угол вокруг оси (формула Родрига)."""
    x, y, z = _norm(axis)
    c, s, t = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return [[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
            [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c]]


def axis_angle(m):
    """Обратное к rotation: (ось, угол) для матрицы поворота."""
    cos = max(-1.0, min(1.0, (m[0][0] + m[1][1] + m[2][2] - 1) / 2))
    angle = math.acos(cos)
    if angle < 1e-6:
        return (0.0, 0.0, 1.0), 0.0
    axis = (m[2][1] - m[1][2], m[0][2] - m[2][0], m[1][0] - m[0][1])
    if math.sqrt(_dot(axis, axis)) < 1e-6:          # разворот на 180°: ось - из диагонали
        axis = (math.sqrt(max(0.0, (m[0][0] + 1) / 2)), math.sqrt(max(0.0, (m[1][1] + 1) / 2)),
                math.sqrt(max(0.0, (m[2][2] + 1) / 2)))
        if m[0][1] < 0:
            axis = (axis[0], -axis[1], axis[2])
        if m[0][2] < 0:
            axis = (axis[0], axis[1], -axis[2])
    return _norm(axis), angle


IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


# ---------------- формы ----------------
def _hull_faces(points):
    """Грани выпуклого многогранника по его вершинам: каждая - список номеров вершин по кругу."""
    faces, seen = [], set()
    center = tuple(sum(p[i] for p in points) / len(points) for i in range(3))
    for a, b, c in combinations(range(len(points)), 3):
        normal = _cross(_sub(points[b], points[a]), _sub(points[c], points[a]))
        if _dot(normal, normal) < 1e-9:
            continue
        normal = _norm(normal)
        if _dot(normal, _sub(points[a], center)) < 0:
            normal = (-normal[0], -normal[1], -normal[2])
        offset = _dot(normal, points[a])
        sides = [_dot(normal, p) - offset for p in points]
        if max(sides) > 1e-6:
            continue                                   # плоскость режет тело - не грань
        on = frozenset(i for i, d in enumerate(sides) if abs(d) < 1e-6)
        if on in seen:
            continue
        seen.add(on)
        middle = tuple(sum(points[i][k] for i in on) / len(on) for k in range(3))
        u = _norm(_sub(points[next(iter(sorted(on)))], middle))
        v = _cross(normal, u)
        ordered = sorted(on, key=lambda i: math.atan2(_dot(_sub(points[i], middle), v),
                                                     _dot(_sub(points[i], middle), u)))
        faces.append(ordered)
    return faces


def _scaled(points):
    radius = max(math.sqrt(_dot(p, p)) for p in points)
    return [tuple(x / radius for x in p) for p in points]


@lru_cache(maxsize=None)
def shape(kind):
    """(вершины, грани) - тело с радиусом 1. kind: 4, 6, 8, 10, 12, 20 или "coin"."""
    if kind == "coin":
        n, half = 28, 0.11
        points = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n), z)
                  for z in (half, -half) for i in range(n)]
        faces = [list(range(n)), list(range(2 * n - 1, n - 1, -1))]
        faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
        # монетка смотрит на зрителя ребром вниз: ось - вдоль z, это и есть «плашмя»
        return points, faces
    if kind == 4:
        points = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    elif kind == 6:
        points = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    elif kind == 8:
        points = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    elif kind == 10:
        a = 0.1
        h = a * (1 + math.cos(math.pi / 5)) / (1 - math.cos(math.pi / 5))   # чтобы грани-«воздушные змеи» были плоскими
        points = [(0, 0, h), (0, 0, -h)]
        points += [(math.cos(math.pi * i / 5), math.sin(math.pi * i / 5), a if i % 2 == 0 else -a) for i in range(10)]
    elif kind == 12:
        points = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                points += [(0, s1 / PHI, s2 * PHI), (s1 / PHI, s2 * PHI, 0), (s1 * PHI, 0, s2 / PHI)]
    elif kind == 20:
        points = []
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                points += [(0, s1, s2 * PHI), (s1, s2 * PHI, 0), (s1 * PHI, 0, s2)]
    else:
        raise ValueError(kind)
    points = _scaled(points)
    return points, _hull_faces(points)


COIN_SIDES = {"Ворон": "coin-heads", "Ласка": "coin-tails"}    # рисунки сторон монетки (art/)
COIN_EDGE = "Ребро"
# Настоящие цифры из опытов:
# - на ребро монетка встаёт примерно раз из 6000 бросков (Murray, Teare, Physical Review E, 1993 -
#   расчёт и опыты с американской монетой в 5 центов);
# - падает той же стороной, какой лежала вверх перед броском, в 50,8% бросков (Bartoš и др., 2023 -
#   350 757 бросков руками 48 человек): рука подбрасывает монетку чуть «с покачиванием».
EDGE_CHANCE = 1 / 6000
SAME_SIDE = 0.508


def toss_coin(rng=random, up=None):
    """Ворон или Ласка, как в жизни: сторона, что лежала сверху (up), выпадает чуть чаще -
    50,8 на 49,2; без up - поровну. И изредка, раз из 6000, - ребро."""
    if rng.random() < EDGE_CHANCE:
        return COIN_EDGE
    if up not in COIN_SIDES:
        return rng.choice(list(COIN_SIDES))
    other = next(side for side in COIN_SIDES if side != up)
    return up if rng.random() < SAME_SIDE else other


def labels(sides):
    if sides == 100:
        return [f"{n}" for n in range(10, 101, 10)]
    if sides == "coin":
        return list(COIN_SIDES)
    return [str(n) for n in range(1, sides + 1)]


def form(sides):
    return "coin" if sides == "coin" else (10 if sides == 100 else sides)


def d100_parts(result):
    """d100 - две кости d10: десятки (00-90) и единицы (0-9). 100 - это «00» и «0»."""
    result = int(result) % 100
    return f"{result // 10 * 10:02d}", str(result % 10)


def d100_value(tens, units):
    value = int(tens) + int(units)
    return 100 if value == 0 else value


class _Body:
    """Одна кость (или монетка) на столе: форма, надписи граней, как повёрнута и куда крутится."""

    def __init__(self, kind, faces, dx=0.0, scale=1.0, matrix=None):
        self.kind, self.labels, self.dx, self.scale = kind, list(faces), dx, scale
        self.matrix = matrix or rotation((1, 0.6, 0.2), 0.75)
        self.spin_axis, self.spin = (1, 0, 0), 0.0
        self.settle_from = self.settle_turn = None
        self.front = None
        self.target = None                        # что должно оказаться сверху


# ---------------- кубик на экране ----------------
class Die3D(QWidget):
    """Объёмный кубик. roll(sides, result) - бросок: кувыркается, подпрыгивает, замедляется
    и поворачивается выпавшей гранью к тебе. Цвета - «Кубик» и «Числа на кубике» из палитры.

    Число на грани не перекрашивается на глазах: ещё до броска подбирается такое вращение,
    после которого к тебе само повернётся нужное число (раньше в конце броска на ближайшую грань
    просто «переписывалось» выпавшее - и было видно, как 7 превращается в 15).
    d100 - две кости d10: десятки и единицы, как в настольных играх."""

    TUMBLE, SETTLE = 0.85, 0.42         # секунды: кувырок и укладка
    REST_TILT = _mul(rotation((0, 1, 0), -0.17), rotation((1, 0, 0), -0.27))
    FRAME_MS = 16
    TRIES = 160                         # сколько вращений перебрать, чтобы нужная грань пришла сама

    def __init__(self, height=150, parent=None):
        super().__init__(parent)
        # в невысоком окне кубик сжимается (рисуется по размеру), а не наезжает на кнопки под ним
        self.setMinimumHeight(min(height, 64))
        self.setMaximumHeight(height)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self._preferred = height
        self.sides = 20
        self.result = None
        self.highlight = None            # цвет ореола на максимуме или единице
        self.bodies = [_Body(20, labels(20))]
        self.lift = 0.0
        self.t = 0.0
        self.on_done = None
        self.on_sound = None             # (имя звука, сила 0..1): удары о стол
        self.crits = True
        self.relabeled = 0               # сколько раз пришлось переписать грань (должно быть 0)
        self._bounces = 0
        self.timer = QTimer(self, timerType=Qt.PreciseTimer)
        self.timer.setInterval(self.FRAME_MS)
        self.timer.timeout.connect(self._frame)

    # ---- совместимость: одна кость ----
    @property
    def labels(self):
        return self.bodies[0].labels

    @property
    def matrix(self):
        return self.bodies[0].matrix

    def sizeHint(self):
        return QSize(self._preferred, self._preferred)

    @property
    def rolling(self):
        return self.timer.isActive()

    # ---- бросок ----
    def _layout(self, sides):
        """Какие кости на столе для этого броска. Повороты прежних костей сохраняются."""
        old = self.bodies
        if sides == 100:
            tens = [f"{n:02d}" for n in range(0, 100, 10)]
            units = [str(n) for n in range(10)]
            if len(old) == 2 and old[0].kind == 10:      # те же кости - надписи не трогаем
                return old
            return [_Body(10, tens, -0.72, 0.64, old[0].matrix),
                    _Body(10, units, 0.72, 0.64, rotation((0.3, 1, 0.5), 2.1))]
        kind = form(sides)
        keep = old[0] if len(old) == 1 and old[0].kind == kind and sides != 100 else None
        if keep is not None:
            keep.labels = labels(sides) if sorted(keep.labels) != sorted(labels(sides)) else keep.labels
            return [keep]
        return [_Body(kind, labels(sides), 0.0, 1.0, old[0].matrix)]

    def roll(self, sides, result, on_done=None, crits=True):
        self.crits = crits and sides != "coin"
        self.sides = sides
        self.result = result
        self.highlight = None
        self.on_done = on_done
        self.t = 0.0
        self._bounces = 0
        self.bodies = self._layout(sides)
        targets = list(d100_parts(result)) if sides == 100 else [result if sides == "coin" else str(result)]
        for body, target in zip(self.bodies, targets):
            body.target = target
            body.settle_from = None
            self._aim(body)
        self._sound("coin_flick" if sides == "coin" else "die_hit", 1.0)     # щелчок по монетке / удар о стол
        self.timer.start()
        self.update()

    def _random_spin(self, body):
        if body.kind == "coin":                   # монетку подбрасывают через ребро
            return _norm((1, random.uniform(-0.15, 0.15), 0)), random.uniform(22, 28)
        return (_norm((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-0.4, 0.4))),
                random.uniform(15, 20))

    def _tumble(self, matrix, axis, spin):
        """Где окажется кость к концу кувырка - тот же расчёт, что и в _frame, кадр в кадр."""
        t, step = 0.0, self.FRAME_MS / 1000
        while True:
            t += step
            if t >= self.TUMBLE:
                return matrix
            k = t / self.TUMBLE
            speed = spin * math.exp(-2.6 * k)
            drift = rotation(_norm((axis[0] + 0.3 * math.sin(7 * k), axis[1], axis[2] + 0.3 * math.cos(5 * k))),
                             speed * step)
            matrix = _mul(drift, matrix)

    def _nearest_face(self, body, matrix):
        points, faces = shape(body.kind)
        best, best_dot = 0, -2.0
        for i, face in enumerate(faces[:len(body.labels)]):
            normal = self._normal(points, face, matrix)
            if normal[2] > best_dot:
                best, best_dot = i, normal[2]
        return best

    def _aim(self, body):
        """Подобрать вращение, после которого к зрителю сама придёт грань с нужным числом."""
        if body.target == COIN_EDGE:
            body.spin_axis, body.spin = self._random_spin(body)
            return
        if body.target not in body.labels:
            body.labels[0] = body.target
        want = body.labels.index(body.target)
        for _ in range(self.TRIES):
            axis, spin = self._random_spin(body)
            if self._nearest_face(body, self._tumble(body.matrix, axis, spin)) == want:
                body.spin_axis, body.spin = axis, spin
                return
        # не нашлось (так бывает редко): поменять надписи сейчас, пока кость только сорвалась с места
        axis, spin = self._random_spin(body)
        body.spin_axis, body.spin = axis, spin
        best = self._nearest_face(body, self._tumble(body.matrix, axis, spin))
        body.labels[want], body.labels[best] = body.labels[best], body.labels[want]

    def finish(self):
        """Сразу в конец броска (для проверок): те же кадры, только без ожидания."""
        while self.timer.isActive():
            self._frame()

    def _frame(self, step=None):
        step = step if step is not None else self.FRAME_MS / 1000
        self.t += step
        if self.t < self.TUMBLE:
            k = self.t / self.TUMBLE
            for body in self.bodies:
                axis = body.spin_axis
                speed = body.spin * math.exp(-2.6 * k)
                drift = rotation(_norm((axis[0] + 0.3 * math.sin(7 * k), axis[1], axis[2] + 0.3 * math.cos(5 * k))),
                                 speed * step)
                body.matrix = _mul(drift, body.matrix)
            self.lift = abs(math.sin(math.pi * 2.5 * k)) * (1 - k) ** 1.6       # отскоки всё ниже
            contacts = int(2.5 * k)                                            # коснулся стола: k = 0,4 и 0,8
            if contacts > self._bounces:
                self._bounces = contacts
                strength = (0.75, 0.45)[min(contacts, 2) - 1]
                self._sound("coin_land" if self.sides == "coin" else "die_hit",
                            strength if self.sides != "coin" or contacts == 1 else 0.3)
        else:
            k = min(1.0, (self.t - self.TUMBLE) / self.SETTLE)
            eased = 1 - (1 - k) ** 3
            for body in self.bodies:
                if body.settle_from is None:
                    self._begin_settle(body)
                axis, angle = body.settle_turn
                body.matrix = _mul(rotation(axis, angle * eased), body.settle_from)
            self.lift = 0.0
            if k >= 1.0:
                self.timer.stop()
                if self.sides != "coin":
                    self._sound("die_settle", 0.5)              # докатился и встал
                if self.crits and self.result == self.sides:
                    self.highlight = QColor(C.CRIT_HIGH)          # выпал максимум
                elif self.crits and self.result == 1:
                    self.highlight = QColor(C.CRIT_LOW)           # выпала единица
                if self.on_done:
                    self.on_done(self.result)
        self.update()

    def _sound(self, name, strength):
        if self.on_sound:
            self.on_sound(name, strength)

    def _begin_settle(self, body):
        """Ближайшая к зрителю грань плавно встаёт к нему лицом, цифрой вверх."""
        points, faces = shape(body.kind)
        body.settle_from = [row[:] for row in body.matrix]
        if body.target == COIN_EDGE:
            # монетка на ребре: стоит торчком, видно обод и чуть-чуть одну сторону
            body.front = None
            target = _mul(self.REST_TILT, rotation((0, 1, 0), math.pi / 2 - 0.22))
        else:
            best = self._nearest_face(body, body.matrix)
            if body.labels[best] != body.target:                  # не должно случаться - но результат важнее
                other = body.labels.index(body.target)
                body.labels[other], body.labels[best] = body.labels[best], body.target
                self.relabeled += 1
            body.front = best
            normal = self._normal(points, faces[best], body.matrix)
            align_axis = _cross(normal, (0, 0, 1))
            align = rotation(align_axis, math.acos(max(-1.0, min(1.0, normal[2])))) \
                if _dot(align_axis, align_axis) > 1e-9 else IDENTITY
            aligned = _mul(align, body.matrix)
            up = _apply(aligned, self._up(points, faces[best]))
            upright = rotation((0, 0, 1), math.atan2(up[0], up[1]))
            # чуть наклонён, чтобы был виден объём, а не плоская картинка
            target = _mul(self.REST_TILT, _mul(upright, aligned))
        # поворот от текущего положения к нужному - одним движением
        current_t = [list(r) for r in zip(*body.matrix)]
        body.settle_turn = axis_angle(_mul(target, current_t))

    @staticmethod
    def _normal(points, face, matrix):
        a, b, c = (_apply(matrix, points[i]) for i in face[:3])
        normal = _norm(_cross(_sub(b, a), _sub(c, a)))
        middle = tuple(sum(_apply(matrix, points[i])[k] for i in face) / len(face) for k in range(3))
        if _dot(normal, middle) < 0:
            normal = (-normal[0], -normal[1], -normal[2])
        return normal

    @staticmethod
    def _center(points, face):
        return tuple(sum(points[i][k] for i in face) / len(face) for k in range(3))

    @classmethod
    def _up(cls, points, face):
        """Куда смотрит верх надписи на грани (в координатах тела)."""
        middle = cls._center(points, face)
        if len(face) == 4 and len(points) == 12:     # d10: верх цифры - к острому концу «змея»
            far = max(face, key=lambda i: math.dist(points[i], middle))
            return _norm(_sub(points[far], middle))
        if len(face) == 4:                           # квадрат: цифра стоит ровно, а не ромбом
            edge = tuple((points[face[0]][k] + points[face[1]][k]) / 2 for k in range(3))
            return _norm(_sub(edge, middle))
        return _norm(_sub(points[face[0]], middle))

    def front_label(self):
        """Что видно сверху после броска. d100 - число из двух костей."""
        if self.sides == 100 and len(self.bodies) == 2:
            tens, units = (b.labels[b.front] if b.front is not None else None for b in self.bodies)
            return None if tens is None or units is None else str(d100_value(tens, units))
        body = self.bodies[0]
        if body.target == COIN_EDGE and body.settle_from is not None:
            return COIN_EDGE
        return body.labels[body.front] if body.front is not None else None

    # ---- рисование ----
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        radius = min(w, h) * (0.34 if self.sides == "coin" else 0.36)
        if len(self.bodies) == 2:                     # две кости рядом: вписать по ширине
            radius = min(radius / 0.64, w / (2 * (0.72 + 0.64)) * 0.95)
        base_y = h / 2 + radius * 0.06 - self.lift * h * 0.16
        floor = h / 2 + radius * 1.02
        if self.highlight is not None:
            glow = QRadialGradient(QPointF(w / 2, base_y), radius * 1.55)
            color = QColor(self.highlight)
            color.setAlpha(110)
            glow.setColorAt(0.45, color)
            color.setAlpha(0)
            glow.setColorAt(1, color)
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(QPointF(w / 2, base_y), radius * 1.55, radius * 1.55)
        for body in self.bodies:
            r = radius * body.scale
            cx = w / 2 + body.dx * radius
            cy = base_y + (radius - r) * 0.9                # маленькие кости стоят на том же столе
            self._paint_body(p, body, cx, cy, r, floor)

    def _paint_body(self, p, body, cx, cy, radius, floor):
        # тень на «столе»: меньше и бледнее, когда кубик в воздухе
        shadow = QRadialGradient(QPointF(cx, floor), radius * (1.0 - 0.35 * self.lift))
        shadow.setColorAt(0, QColor(0, 0, 0, int(95 * (1 - 0.6 * self.lift))))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(QPointF(cx, floor), radius * 1.05, radius * 0.22)

        points, faces = shape(body.kind)
        world = [_apply(body.matrix, v) for v in points]
        distance = 5.5

        def project(v):
            k = distance / (distance - v[2])
            return QPointF(cx + v[0] * radius * k, cy - v[1] * radius * k)

        light = _norm((-0.45, 0.6, 0.9))
        coin = body.kind == "coin"
        # монетка - охристая (её стороны - рисунки: ворон и ласка), кубики - в цвет «Кубика»
        color_body = QColor("#c8962e") if coin else QColor(C.DICE_BODY)
        dark, bright = C.mix(color_body, "#000000", 0.55), C.mix(color_body, "#ffffff", 0.32)
        edge = C.mix(color_body, "#000000", 0.62)
        # ребро монетки - тёмная бронза с насечкой (через одну грань светлее), а не та же охра
        rim_dark, rim_bright = QColor("#3a2a10"), QColor("#a8791f")
        ink = QColor(C.DICE_TEXT)
        drawn = []
        for i, face in enumerate(faces):
            corners = [world[j] for j in face]
            middle = tuple(sum(v[k] for v in corners) / len(corners) for k in range(3))
            normal = _norm(_cross(_sub(corners[1], corners[0]), _sub(corners[2], corners[0])))
            if _dot(normal, middle) < 0:
                normal = (-normal[0], -normal[1], -normal[2])
            view = _norm(_sub((0, 0, distance), middle))
            facing = _dot(normal, view)
            if facing <= 0:
                continue
            drawn.append((middle[2], i, face, normal, facing, middle))
        drawn.sort()
        for _z, i, face, normal, facing, middle in drawn:
            lit = max(0.0, _dot(normal, light))
            if coin and i >= 2:
                color = C.mix(rim_dark, rim_bright, (0.15 + 0.75 * lit) * (1.0 if i % 2 else 0.72))
                p.setPen(QPen(C.mix(rim_dark, "#000000", 0.3), 0.8))
            else:
                color = C.mix(dark, bright, 0.18 + 0.82 * lit)
                p.setPen(QPen(edge, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(color)
            p.drawPolygon(QPolygonF([project(world[j]) for j in face]))
            if coin and i < 2:                       # ободок по краю стороны монетки
                ring = [project(_apply(body.matrix, (x * 0.9, y * 0.9, z))) for x, y, z in
                        (points[j] for j in face)]
                p.setPen(QPen(QColor(90, 60, 15, 150), max(1.0, radius * 0.025)))
                p.setBrush(Qt.NoBrush)
                p.drawPolygon(QPolygonF(ring))
            if i >= len(body.labels) or facing < 0.28:
                continue
            self._label(p, body, points, face, middle, project, ink, facing, i)

    def _label(self, p, body, points, face, middle, project, ink, facing, index):
        """Надпись лежит на грани: рисуется в плоскости грани и вместе с ней поворачивается."""
        text = body.labels[index]
        up_body = self._up(points, face)
        center_body = self._center(points, face)
        normal_body = _norm(_cross(_sub(points[face[1]], points[face[0]]), _sub(points[face[2]], points[face[0]])))
        if _dot(normal_body, center_body) < 0:
            normal_body = (-normal_body[0], -normal_body[1], -normal_body[2])
        right_body = _cross(up_body, normal_body)
        # 1 единица надписи = 0.01 радиуса тела; оси надписи - «вправо» и «вниз» по грани
        origin = project(middle)
        right = project(_apply(body.matrix, tuple(c + r * 0.01 for c, r in zip(center_body, right_body))))
        up = project(_apply(body.matrix, tuple(c + u * 0.01 for c, u in zip(center_body, up_body))))
        transform = QTransform(right.x() - origin.x(), right.y() - origin.y(),
                               origin.x() - up.x(), origin.y() - up.y(), origin.x(), origin.y())
        # размер надписи - от вписанного круга грани
        inner = min(math.dist(center_body, points[j]) for j in face) * (0.72 if len(face) > 3 else 0.55)
        if body.kind == 10:
            inner *= 0.95
        size = inner * 100 * (0.95 if len(text) < 3 else 0.62 if len(text) < 4 else 0.42)
        p.save()
        p.setTransform(transform, True)
        if body.kind == "coin":                                  # сторона монетки - рисунок, а не надпись
            from .artwork import pixmap
            picture = pixmap(COIN_SIDES.get(text, ""))
            if not picture.isNull():
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                p.setOpacity(min(1.0, (facing - 0.28) / 0.3))
                p.drawPixmap(QRectF(-86, -86, 172, 172), picture, QRectF(picture.rect()))
                p.restore()
                return
        font = QFont(C.FONT_FAMILY)
        font.setPixelSize(max(6, int(size)))
        font.setWeight(QFont.Black)
        p.setFont(font)
        color = QColor(ink)
        color.setAlphaF(min(1.0, (facing - 0.28) / 0.3))
        p.setPen(color)
        box = QRectF(-150, -size * 0.75, 300, size * 1.5)
        p.drawText(box, Qt.AlignCenter, text)
        if text in ("6", "9"):                                   # черта под 6 и 9, чтобы не путались
            p.setPen(QPen(color, max(1.0, size * 0.08), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(-size * 0.22, size * 0.5), QPointF(size * 0.22, size * 0.5))
        p.restore()


# ---------------- «Рандомайзеры» ----------------
# здесь кубики и монетка - большие, на столе, с материалом; быстрые - по-прежнему на правой панели
MODES = [("dice", "Кубики"), ("coin", "Монетка"), ("number", "Число"), ("list", "Из списка"),
         ("cast", "Персонаж"), ("roulette", "Рулетка")]


def pick_number(low, high, rng=random):
    low, high = min(low, high), max(low, high)
    return rng.randint(low, high)


def list_items(text):
    return [line.strip() for line in text.split("\n") if line.strip()]


class Shuffle(QLabel):
    """Крупная надпись, которая перебирает варианты, замедляясь, и останавливается на выпавшем."""

    def __init__(self):
        super().__init__("")
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumHeight(64)
        font = self.font()
        font.setPointSize(22)
        font.setWeight(QFont.Black)
        self.setFont(font)
        self.timer = QTimer(self, timerType=Qt.PreciseTimer)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._step)
        self.options, self.final, self.steps, self.on_done = [], "", 0, None

    @property
    def rolling(self):
        return self.timer.isActive()

    def run(self, options, final, on_done=None):
        self.options, self.final, self.on_done = list(options), final, on_done
        self.steps = 0
        self._step()

    def finish(self):
        if self.timer.isActive():
            self.timer.stop()
            self.steps = 99
            self._step()

    def _step(self):
        self.steps += 1
        if self.steps >= 14 or len(self.options) < 2:
            self.setStyleSheet(f"color: {C.IMPORTANT};")
            self.setText(self.final)
            if self.on_done:
                self.on_done(self.final)
            return
        self.setStyleSheet(f"color: {C.DIM};")
        self.setText(random.choice(self.options))
        self.timer.start(int(30 + self.steps ** 2 * 2.2))         # всё медленнее, как барабан


def dice_icon(material, sides):
    """Картинка кубика (art/dice/<материал>/d<грани>.png) для кнопок; нет файла - пустой значок."""
    from PySide6.QtGui import QIcon
    from .artwork import pixmap
    picture = pixmap(f"dice/{material}/d{sides}")
    return QIcon(picture) if not picture.isNull() else QIcon()


class RandomDialog(Sheet):
    """Рандомайзеры: кубики и монетка на столе, число от-до, строка из списка, персонаж или термин мира,
    рулетка. Всё выпавшее попадает и в историю бросков."""

    def __init__(self, parent, names, terms, settings, on_result, open_term=None, history=None):
        super().__init__(parent, tr("Рандомайзеры"))
        self.history = history if history is not None else []      # список окна: новое - первым
        self.setMinimumWidth(820)                      # шесть вкладок в ряд
        self.names, self.terms, self.settings = list(names), list(terms), settings
        self.on_result, self.open_term = on_result, open_term
        self.picked_term = None
        tabs = QHBoxLayout()
        self.group = QButtonGroup(self)
        self.tab_buttons = {}
        for key, title in MODES:
            button = QPushButton(title)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(f"QPushButton:checked {{ background: {C.IMPORTANT}; "
                                 f"color: {C.on_color(C.IMPORTANT)}; }}")
            button.clicked.connect(lambda _c=False, k=key: self.set_mode(k))
            button.setProperty("noIcon", True)             # вкладки - без значков, ровным рядом
            self.group.addButton(button)
            self.tab_buttons[key] = button
            tabs.addWidget(button)
        self.content.addLayout(tabs)

        self.pages = QStackedWidget()
        self.content.addWidget(self.pages)
        # кубики на столе
        from .dicetable import MATERIALS, DiceTable
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        tile = (f"QToolButton {{ border-radius: 10px; padding: 4px 6px; background: transparent; }}"
                f"QToolButton:hover {{ background: {C.HOVER}; }}"
                f"QToolButton:checked {{ background: {C.SELECT}; }}")
        row = QHBoxLayout()
        row.setSpacing(4)
        self.dice_group = QButtonGroup(self)
        chosen = int(settings.value("table_dice", 20) or 20)
        for sides in C.DICE:
            button = QToolButton()
            button.setText(f"d{sides}")
            button.setCheckable(True)
            button.setProperty("noIcon", True)
            button.setProperty("sides", sides)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(54, 54))
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(tile)
            button.setChecked(sides == chosen)
            self.dice_group.addButton(button)
            row.addWidget(button)
        row.addStretch()
        column.addLayout(row)
        # из чего: плитки с кубиком d20 каждого материала (список - внутри, для истории и настроек)
        row = QHBoxLayout()
        row.setSpacing(4)
        row.addWidget(QLabel(tr("Из чего:")))
        self.material = QComboBox()
        for key, (title, *_rest) in MATERIALS.items():
            self.material.addItem(title, key)
        self.material.setCurrentIndex(max(0, self.material.findData(settings.value("dice_material", "bone"))))
        self.material.hide()
        self.material_group = QButtonGroup(self)
        for index, (key, (title, *_rest)) in enumerate(MATERIALS.items()):
            button = QToolButton()
            button.setText(title)
            button.setIcon(dice_icon(key, 20))
            button.setIconSize(QSize(30, 30))
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setCheckable(True)
            button.setProperty("noIcon", True)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(tile)
            button.setChecked(index == self.material.currentIndex())
            button.clicked.connect(lambda _c=False, i=index: self.material.setCurrentIndex(i))
            self.material_group.addButton(button, index)
            row.addWidget(button)
        self.material.currentIndexChanged.connect(self._material_changed)
        row.addStretch()
        column.addLayout(row)
        self._dice_icons()
        self.pages.addWidget(page)
        # монетка на столе
        self.coin_up = settings.value("coin_up", "Ворон") or "Ворон"     # как монетка лежит перед броском
        coin = self.coin_note = QLabel("")
        coin.setObjectName("Status")
        coin.setWordWrap(True)
        self.pages.addWidget(coin)
        self._coin_text()
        # число
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(tr("от")))
        self.low = QSpinBox()
        self.high = QSpinBox()
        for box, value in ((self.low, int(settings.value("random_low", 1))),
                           (self.high, int(settings.value("random_high", 100)))):
            box.setRange(-1_000_000, 1_000_000)
            box.setValue(value)
            box.setAlignment(Qt.AlignCenter)
        row.addWidget(self.low, 1)
        row.addWidget(QLabel(tr("до")))
        row.addWidget(self.high, 1)
        self.pages.addWidget(page)
        # список
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        self.list_edit = QPlainTextEdit()
        self.list_edit.setPlaceholderText(tr("Каждый вариант - с новой строки.\nНапример: дождь\nтуман\nясно"))
        self.list_edit.setPlainText(settings.value("random_list", "") or "")
        self.list_edit.setFixedHeight(120)
        column.addWidget(self.list_edit)
        self.cross_out = QCheckBox(tr("Вычёркивать выпавшее (без повторов)"))
        column.addWidget(self.cross_out)
        self.pages.addWidget(page)
        # персонаж или термин
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        self.cast_group = QButtonGroup(self)
        self.cast_buttons = {}
        for key, title in (("names", tr("Персонаж ({n})").format(n=len(self.names))), ("terms", tr("Термин мира ({n})").format(n=len(self.terms))),
                           ("any", tr("Любой"))):
            box = QPushButton(title)
            box.setCheckable(True)
            box.setStyleSheet(f"QPushButton:checked {{ background: {C.SELECT}; }}")
            self.cast_group.addButton(box)
            self.cast_buttons[key] = box
            row.addWidget(box)
        self.cast_buttons["any"].setChecked(True)
        row.addStretch()
        self.pages.addWidget(page)
        # рулетка
        from .roulette import LEVELS, LOADS, Revolver, Roulette
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        info = QLabel(tr("Крутани барабан и жми «Спуск»: щёлк - пронесло, бах - писательский вызов. "
                      "Без прокрутки шанс с каждым щелчком растёт."))
        info.setObjectName("Status")
        info.setWordWrap(True)
        column.addWidget(info)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Заряжено:")))
        self.load_box = QComboBox()
        for key, title, _live in LOADS:
            self.load_box.addItem(title, key)
        load = settings.value("roulette_load", "1") or "1"
        self.load_box.setCurrentIndex(max(0, self.load_box.findData(load)))
        self.load_box.currentIndexChanged.connect(self._load_changed)
        row.addWidget(self.load_box, 1)
        row.addWidget(QLabel(tr("Вызовы:")))
        self.level_box = QComboBox()
        for key, title in LEVELS:
            self.level_box.addItem(title, key)
        level = int(settings.value("roulette_level", 0) or 0)
        self.level_box.setCurrentIndex(max(0, self.level_box.findData(level)))
        self.level_box.setToolTip(tr("Насколько жёсткие вызовы выпадают: от безобидных до адища"))
        self.level_box.currentIndexChanged.connect(
            lambda: self.settings.setValue("roulette_level", self.level_box.currentData()))
        row.addWidget(self.level_box, 1)
        column.addLayout(row)
        row = QHBoxLayout()                              # кнопки - вторым рядом, чтобы ничего не обрезалось
        own = QPushButton(tr("Свои вызовы…"))
        own.clicked.connect(self.edit_own)
        row.addWidget(own)
        row.addStretch()
        self.spin_button = QPushButton(tr("Крутануть барабан"))
        self.spin_button.clicked.connect(self.spin)
        row.addWidget(self.spin_button)
        column.addLayout(row)
        self.pages.addWidget(page)

        self.roulette = Roulette(load=self.load_box.currentData())
        self.revolver = Revolver()
        self.needs_load = True                           # первая прокрутка - с зарядкой
        self.revolver.on_round = lambda last: self._sound("round_in", 0.9 if last else 0.6)
        self.revolver.turn_to(self.roulette.current, duration=1)
        self.content.addWidget(self.revolver)

        self.table = DiceTable()
        sounds = getattr(parent, "sounds", None)
        if sounds is not None:
            self.table.on_sound = sounds.play
        self.content.addWidget(self.table, 1)
        self.shuffle = Shuffle()
        self.content.addWidget(self.shuffle)
        self.note = QLabel("")
        self.note.setObjectName("Status")
        self.note.setAlignment(Qt.AlignCenter)
        self.note.setWordWrap(True)
        self.content.addWidget(self.note)

        buttons = QHBoxLayout()
        self.history_button = QPushButton(tr("История"))
        self.history_button.setToolTip(tr("Что выпадало, пока открыт блокнот"))
        self.history_button.clicked.connect(self.show_history)
        buttons.addWidget(self.history_button)
        self.open_button = QPushButton(tr("Открыть статью"))
        self.open_button.setVisible(False)
        self.open_button.clicked.connect(self._open_term)
        buttons.addWidget(self.open_button)
        buttons.addStretch()
        close = QPushButton(tr("Закрыть"))
        close.clicked.connect(self.accept)
        self.go = QPushButton(tr("Бросить"))
        self.go.setObjectName("Primary")
        self.go.setDefault(True)
        self.go.clicked.connect(self.draw)
        buttons.addWidget(close)
        buttons.addWidget(self.go)
        self.content.addLayout(buttons)
        self.set_mode(settings.value("random_mode", "dice") or "dice")

    def _coin_text(self):
        self.coin_note.setText(
            tr("Сейчас сверху - {n}. Как в жизни: монетка чуть чаще падает той стороной, что лежала сверху "
               "(50,8 на 49,2 - опыт на 350 757 бросках), а на ребро встаёт примерно раз из 6000. Подлетит, "
               "покрутится и упадёт на стол.").format(n=self.coin_up.lower()))

    def _coin_landed(self, side):
        if side in COIN_SIDES:                    # подняли - и она лежит той же стороной вверх
            self.coin_up = side
            self.settings.setValue("coin_up", side)
            self._coin_text()
        self._done_big("Монетка: на ребро! Такое бывает раз из 6000" if side == COIN_EDGE
                       else f"Монетка: {side.lower()}", tr("На ребро!") if side == COIN_EDGE else side)

    def _material_changed(self, index):
        button = self.material_group.button(index)
        if button is not None:
            button.setChecked(True)
        self._dice_icons()

    def _dice_icons(self):
        """На кнопках d4…d100 - кубики того материала, что выбран."""
        material = self.material.currentData() or "bone"
        for button in self.dice_group.buttons():
            button.setIcon(dice_icon(material, int(button.property("sides"))))


    def set_mode(self, mode):
        keys = [k for k, _t in MODES]
        if mode not in keys:
            mode = "dice"
        self.mode = mode
        self.tab_buttons[mode].setChecked(True)
        self.pages.setCurrentIndex(keys.index(mode))
        for i in range(self.pages.count()):            # высота - по открытой вкладке, без пустоты
            policy = QSizePolicy.Preferred if i == self.pages.currentIndex() else QSizePolicy.Ignored
            self.pages.widget(i).setSizePolicy(QSizePolicy.Preferred, policy)
        self.pages.adjustSize()
        self.revolver.setVisible(mode == "roulette")
        self.table.setVisible(mode in ("dice", "coin"))
        self.shuffle.setText("")
        self.note.setText("")
        self.open_button.setVisible(False)
        self.go.setText({"dice": "Бросить", "coin": "Подбросить", "number": "Бросить",
                         "roulette": "Спуск"}.get(mode, "Выбрать"))
        QTimer.singleShot(0, self, self.adjustSize)     # окно по размеру вкладки

    # ---- бросок ----
    def draw(self):
        if self.shuffle.rolling or self.table.rolling:     # пока не выпало - заново не бросить
            return
        self.settings.setValue("random_mode", self.mode)
        self.open_button.setVisible(False)
        self.picked_term = None
        if self.mode == "number":
            low, high = sorted((self.low.value(), self.high.value()))
            self.settings.setValue("random_low", self.low.value())
            self.settings.setValue("random_high", self.high.value())
            value = pick_number(low, high)
            self.note.setText("")
            span = range(low, high + 1) if high - low < 400 else [pick_number(low, high) for _ in range(40)]
            self.shuffle.run([str(n) for n in span], str(value),
                             lambda v: self._done(f"Число {low}–{high}: {v}"))
        elif self.mode == "roulette":
            self.pull()
        elif self.mode == "dice":
            button = self.dice_group.checkedButton()
            sides = int(button.property("sides")) if button is not None else 20
            material = self.material.currentData()
            self.settings.setValue("table_dice", sides)
            self.settings.setValue("dice_material", material)
            value = random.randint(1, sides)
            self.shuffle.setText("")
            self.note.setText("")
            title = self.material.currentText().lower()
            self.table.throw(sides, value, material, lambda v: self._done_big(f"d{sides} ({title}): {v}", str(v)))
        elif self.mode == "coin":
            side = toss_coin(up=self.coin_up)
            self.shuffle.setText("")
            self.note.setText("")
            self.table.toss(side, lambda v: self._coin_landed(v))
        elif self.mode == "list":
            self.settings.setValue("random_list", self.list_edit.toPlainText())
            items = list_items(self.list_edit.toPlainText())
            if not items:
                self.note.setText(tr("Список пуст: впиши варианты, каждый с новой строки"))
                return
            choice = random.choice(items)
            if self.cross_out.isChecked():
                lines = self.list_edit.toPlainText().split("\n")
                lines.remove(next(line for line in lines if line.strip() == choice))
                self.list_edit.setPlainText("\n".join(lines))
                self.settings.setValue("random_list", self.list_edit.toPlainText())
            left = len(items) - 1 if self.cross_out.isChecked() else None
            self.shuffle.run(items, choice, lambda v: self._done(
                f"Из списка: {v}", "" if left is None else tr("Осталось вариантов: {left}").format(left=left)))
        else:
            pool = self._pool()
            if not pool:
                self.note.setText(tr("Пока не из чего выбирать: добавь персонажей или справочник мира"))
                return
            title, term = random.choice(pool)
            self.picked_term = term
            kind = "Термин" if term is not None else "Персонаж"
            self.shuffle.run([t for t, _ in pool], title, lambda v: self._done(f"{kind}: {v}"))

    # ---- рулетка ----
    def _sound(self, name, strength=1.0):
        sounds = getattr(self.parent(), "sounds", None)
        if sounds is not None:
            sounds.play(name, strength)

    def _load_changed(self):
        key = self.load_box.currentData()
        self.settings.setValue("roulette_load", key)
        self.roulette.set_load(key)
        self.needs_load = True
        self.revolver.hide_all()
        self.revolver.turn_to(self.roulette.current, duration=200)
        self.shuffle.setText("")
        self.note.setText(tr("Заряжено: {n}. Крутани барабан").format(n=self.load_box.currentText()))

    def edit_own(self):
        from .roulette import OwnChallengesDialog
        dialog = OwnChallengesDialog(self, self.settings.value("roulette_own", "") or "",
                                     self.settings.value("roulette_only_own", "false") == "true")
        if dialog.exec():
            self.settings.setValue("roulette_own", dialog.text())
            self.settings.setValue("roulette_only_own", "true" if dialog.only_own() else "false")
            self.note.setText(dialog.summary())

    def _challenge(self):
        from .roulette import own_list
        return self.roulette.challenge(own_list(self.settings.value("roulette_own", "")),
                                       self.settings.value("roulette_only_own", "false") == "true",
                                       self.level_box.currentData())

    PULL_PAUSE_MS = 450           # между щелчками спуска - не чаще (иначе можно «строчить» без конца)

    def _paused(self):
        clock = getattr(self, "_pull_clock", None)
        return clock is not None and clock.elapsed() < self.PULL_PAUSE_MS

    def _roulette_ready(self):
        """Можно ли сейчас жать: барабан не крутится, не заряжается, «бах» отгремел, пауза прошла."""
        bang = self.revolver.effect is not None and self.revolver.effect[0] == "bang"
        if self.revolver.busy or bang or self.revolver.flash_anim.state() == QVariantAnimation.Running:
            return False
        return not self._paused()

    def _roulette_touched(self):
        from PySide6.QtCore import QElapsedTimer
        self._pull_clock = QElapsedTimer()
        self._pull_clock.start()

    def spin(self):
        if self.revolver.loading is not None or self._paused():
            return                                       # заряжается или только что жали
        if self.revolver.busy:
            self.revolver.finish()
        self._roulette_touched()
        if self.needs_load:                              # барабан только что перезаряжен - сначала зарядка
            self.needs_load = False
            self.shuffle.setText("")
            self.note.setText(tr("Заряжаю…"))
            self.revolver.load(self.roulette.chambers, on_done=self.spin)
            return
        self.revolver.hide_all()
        self.roulette.spin()
        self._sound("drum_spin")
        self.shuffle.setText("")
        self.note.setText(tr("Барабан крутится…"))
        self.revolver.turn_to(self.roulette.current, turns=3, duration=1300,
                              on_done=lambda: self.note.setText(tr("Жми «Спуск»: {n}").format(n=self.roulette.chance_text())))

    def pull(self):
        if not self._roulette_ready():
            return
        self._roulette_touched()
        if self.revolver.revealed:                       # после «баха» барабан перезаряжен - сперва прокрутка
            self.spin()
            return
        result = self.roulette.pull()
        if result == "live":
            self._sound("bang")
            self.revolver.boom(self.roulette.chambers)
            challenge = self._challenge()
            self.shuffle.setStyleSheet(f"color: {C.IMPORTANT};")
            self.shuffle.setText(challenge)
            self.note.setText(tr("Бах! Вот твой вызов. Барабан перезаряжен - крутани заново"))
            self.roulette.reload()
            self.needs_load = True
            self._result(f"Рулетка: {challenge}")
            QTimer.singleShot(0, self, self.adjustSize)      # вызов в две строки - окно подрастает
            return
        self._sound("trigger_click")
        self.revolver.puff()
        self.shuffle.setText("")
        self.note.setText(tr("Щёлк. Пронесло. Дальше: {n}").format(n=self.roulette.chance_text()))
        self.revolver.turn_to(self.roulette.current, duration=260)

    def _pool(self):
        which = next(k for k, b in self.cast_buttons.items() if b.isChecked())
        pool = []
        if which in ("names", "any"):
            pool += [(name, None) for name in self.names]
        if which in ("terms", "any"):
            known = {n.lower() for n in self.names}
            pool += [(t.name, t) for t in self.terms if t.name.lower() not in known]
        return pool

    def _result(self, entry):
        """Выпавшее - в историю и наружу (окну)."""
        before = len(self.history)
        if self.on_result is not None:
            self.on_result(entry)                       # окно само кладёт в свою историю
        if len(self.history) == before:
            self.history.insert(0, entry)

    def show_history(self):
        from ..ui.style import rounded_menu
        menu = rounded_menu(self)
        if not self.history:
            menu.addAction(tr("Пока ничего не выпадало")).setEnabled(False)
        for entry in self.history[:30]:
            menu.addAction(entry).setEnabled(False)
        if self.history:
            menu.addSeparator()
            menu.addAction(tr("Стереть историю"), self.history.clear)
        menu.exec(self.history_button.mapToGlobal(self.history_button.rect().topLeft()))

    def _done(self, entry, note=""):
        self.note.setText(note)
        self.open_button.setVisible(self.picked_term is not None and self.open_term is not None
                                    and getattr(self.picked_term, "path", None) is not None)
        self._result(entry)

    def _done_big(self, entry, shown):
        """Кубик или монетка легли: что выпало - крупно под столом."""
        self.shuffle.setStyleSheet(f"color: {C.IMPORTANT};")
        self.shuffle.setText(shown)
        self._done(entry)

    def _open_term(self):
        if self.picked_term is not None and self.open_term:
            self.accept()
            self.open_term(self.picked_term)
