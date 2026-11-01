# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Праздник на экране. Под текстом - комната (Room): стена, деревянный пол, камин с живым огнём, кресла-качалки,
ёлка с подарками и огоньками, снеговик на сугробе, фонарь и тихий снег. Поверх (Overlay) - гирлянда по верху
окна, хвойный венок вокруг часов и редкий снег, который затихает, пока печатаешь. SeasonLook включает и
выключает всё это по настройкам (core/seasons.py). Неподвижное рисуется один раз в картинку, на каждом кадре -
только то, что движется, и только его кусочки экрана: окно не грузит компьютер."""

import json
import math
import random
import time
from pathlib import Path

from PySide6.QtCore import QObject, QEvent, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient, QRegion)
from PySide6.QtWidgets import QWidget

from ..core import config as C
from ..core import seasons

ART = Path(__file__).resolve().parents[1] / "art" / "seasons"
FRAME_MS = 50              # 20 кадров в секунду, пока окно впереди (огоньки - через кадр)
IDLE_MS = 160              # окно позади других - медленнее, чтобы не тратить батарею


def _noise(t, seed):
    """Плавная «случайность» из трёх синусов: огонь и ореол дрожат живо, но без рывков."""
    return (math.sin(t * 2.1 + seed) * 0.5 + math.sin(t * 5.3 + seed * 1.7) * 0.3
            + math.sin(t * 11.7 + seed * 2.9) * 0.2)


class Art:
    """SVG праздника и scene.json (где огоньки, где огонь). Картинки - в кэше под нужный размер."""

    def __init__(self, name):
        from PySide6.QtSvg import QSvgRenderer
        folder = ART / name
        self.spec = json.loads((folder / "scene.json").read_text(encoding="utf-8"))
        self.renderers = {p.stem: QSvgRenderer(str(p)) for p in folder.glob("*.svg")}
        self.images = {p.stem: QImage(str(p)) for p in folder.glob("*.png")}      # ласка - рисунок автора
        self._cache = {}

    def width_for(self, name, height):
        if name in self.images:
            image = self.images[name]
            return height * image.width() / max(1, image.height())
        w, h = self.spec["window" if name.startswith("window") else name]["size"]   # обе половины окна - одна рамка
        return height * w / h

    def pixmap(self, name, height, ratio=1.0, mirror=False, width=None):
        key = (name, int(height), ratio, mirror, None if width is None else int(width))
        if key not in self._cache:
            width = self.width_for(name, height) if width is None else width
            size = QSize(max(1, round(width * ratio)), max(1, round(height * ratio)))
            pix = QPixmap(size)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            if name in self.images:
                painter.drawImage(QRectF(0, 0, size.width(), size.height()), self.images[name])
            else:
                self.renderers[name].render(painter, QRectF(0, 0, size.width(), size.height()))
            painter.end()
            if mirror:                     # зеркалим готовую картинку: узоры SVG (плед) при зеркальном пере рисуются плохо
                image = pix.toImage()                   # Qt 6.9+: flipped, раньше - mirrored
                image = image.flipped(Qt.Horizontal) if hasattr(image, "flipped") else image.mirrored(True, False)
                pix = QPixmap.fromImage(image)
            pix.setDevicePixelRatio(ratio)
            if len(self._cache) > 40:
                self._cache.clear()
            self._cache[key] = pix
        return self._cache[key]


class Snow:
    """Снежинки на прямоугольнике: падают, покачиваются, внизу появляются снова сверху."""

    def __init__(self, count, radius, speed, seed):
        self.rng = random.Random(seed)
        self.count, self.radius, self.speed = count, radius, speed
        self.flakes = []
        self.size = QSize(0, 0)

    def resize(self, size):
        if size == self.size:
            return
        self.size = size
        rng = self.rng
        self.flakes = [[rng.uniform(0, size.width()), rng.uniform(0, size.height()), rng.uniform(*self.radius),
                        rng.uniform(*self.speed), rng.uniform(0, 6.28), rng.uniform(0.35, 0.9)]
                       for _ in range(self.count)]

    def step(self, dt, t):
        dirty = []
        height = self.size.height()
        for flake in self.flakes:
            x, y, r = flake[0], flake[1], flake[2]
            old = QRect(int(x - r - 1), int(y - r - 1), int(2 * r + 3), int(2 * r + 3))
            flake[1] += flake[3] * dt * (0.6 + r / 3)
            flake[0] += math.sin(t * 0.9 + flake[4]) * 12 * dt
            if flake[1] - r > height:
                flake[1] = -r
                flake[0] = self.rng.uniform(0, self.size.width())
            new = QRect(int(flake[0] - r - 1), int(flake[1] - r - 1), int(2 * r + 3), int(2 * r + 3))
            dirty.append(old.united(new))
        return dirty

    def paint(self, painter, alpha=1.0, region=None):
        painter.setPen(Qt.NoPen)
        for x, y, r, _speed, _phase, a in self.flakes:
            if region is not None and not region.intersects(QRect(int(x - r), int(y - r), int(2 * r + 2), int(2 * r + 2))):
                continue                         # рисуем только то, что попало в перерисовку
            color = QColor(255, 255, 255)
            color.setAlphaF(max(0.0, min(1.0, a * alpha)))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), r, r)


_SPRITES = {}


def paint_bulb(painter, center, color, level, radius):
    """Огонёк: свечение вокруг и яркая сердцевина. level 0..1 - насколько горит. Готовые картинки огоньков
    лежат в кэше (12 ступеней яркости): рисовать градиент на каждом кадре дорого."""
    ratio = max(1.0, painter.device().devicePixelRatioF()) if painter.device() is not None else 1.0
    step = round(max(0.0, min(1.0, level)) * 12)
    key = (QColor(color).name(), step, round(radius * 4), ratio)
    sprite = _SPRITES.get(key)
    if sprite is None:
        size = radius * 7
        sprite = QPixmap(max(1, round(size * ratio)), max(1, round(size * ratio)))
        sprite.setDevicePixelRatio(ratio)
        sprite.fill(Qt.transparent)
        p = QPainter(sprite)
        p.setRenderHint(QPainter.Antialiasing)
        _draw_bulb(p, QPointF(size / 2, size / 2), color, step / 12, radius)
        p.end()
        if len(_SPRITES) > 600:
            _SPRITES.clear()
        _SPRITES[key] = sprite
    half = radius * 3.5
    painter.drawPixmap(QPointF(center.x() - half, center.y() - half), sprite)


def _draw_bulb(painter, center, color, level, radius):
    glow = QRadialGradient(center, radius * 3.4)
    c = QColor(color)
    c.setAlphaF(0.62 * level)
    glow.setColorAt(0, c)
    c.setAlphaF(0.0)
    glow.setColorAt(1, c)
    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(center, radius * 3.4, radius * 3.4)
    core = QColor(color).lighter(100 + int(70 * level))
    if level < 0.5:
        core = C.mix(color, "#2a2a2a", 0.55 - level)
    painter.setBrush(core)
    painter.drawEllipse(center, radius, radius * 1.35)


class Room:
    """Комната под текстом. Всё в координатах центральной части окна (canvas)."""

    FIRE_OPACITY = 0.62          # камин стоит под текстом: приглушён, чтобы буквы читались
    CHAIR_OPACITY = 0.78

    def __init__(self, art, config):
        self.art = art
        self.config = config
        self.size = QSize(0, 0)
        self.ratio = 1.0
        self.items = {}
        self.static = None
        self.snow = Snow(42, (0.9, 2.2), (22, 46), 11) if seasons.option(config, "season_snow_under") else None
        self.outside = Snow(18, (0.7, 1.7), (14, 30), 31)          # снег за окном - идёт всегда
        self.sparks = []
        self.rng = random.Random(5)
        self.t = 0.0
        self.levels = {}
        self._lights = None
        self.chair_t = 0.0
        from .snowman import Yard
        self.yard = Yard()                                  # снеговик за окном
        self.yard_dirty = True

    # ---- где что стоит ----
    def layout(self, size):
        w, h = size.width(), size.height()
        floor_h = max(34, min(84, h * 0.085))
        floor_top = h - floor_h
        items = {"floor_top": floor_top}
        fh = max(120, min(300, h * 0.32))
        fw = self.art.width_for("fireplace", fh)
        items["fireplace"] = QRectF((w - fw) / 2, floor_top + floor_h * 0.25 - fh, fw, fh)
        th = max(150, min(420, h * 0.44))
        tree = QRectF(8, floor_top + floor_h * 0.35 - th, self.art.width_for("tree", th), th)
        items["tree"] = tree
        ph = th * 0.24
        items["presents"] = QRectF(tree.left() + tree.width() * 0.06, floor_top + floor_h * 0.55 - ph,
                                   self.art.width_for("presents", ph), ph)
        wh = max(180, min(380, h * 0.42))                     # окно на стене справа, за ним - улица
        ww = self.art.width_for("window-back", wh)
        items["window"] = QRectF(w - ww - 6, max(40.0, floor_top - h * 0.14 - wh), ww, wh)
        ch = fh * 0.56
        cw = self.art.width_for("chair", ch)
        fire = items["fireplace"]
        # кресла стоят перед камином, заходя на его края; друг на друга вещи не налезают
        left = QRectF(fire.left() - cw * 0.45, floor_top + floor_h * 0.45 - ch, cw, ch)
        right = QRectF(fire.right() - cw * 0.55, left.top(), cw, ch)
        if left.left() > tree.right() + 6:
            items["chair_left"] = left
        if right.right() < items["window"].left() - 6:
            items["chair_right"] = right
        # ласка с ковриком - в промежутке между ёлкой и креслом (или камином), сколько влезет
        gap_right = items["chair_left"].left() if "chair_left" in items else fire.left()
        rug_w = min(th * 0.5, gap_right - tree.right() - 10)
        if rug_w >= 90:
            rug_h = min(rug_w * 92 / 320, floor_h * 0.9)
            center = (tree.right() + gap_right) / 2
            items["rug"] = QRectF(center - rug_w / 2, h - rug_h - floor_h * 0.08, rug_w, rug_h)
            sleep_w = rug_w * 0.88
            sleep_h = sleep_w / max(0.1, self.art.width_for("weasel-sleep", 1.0))
            items["weasel"] = QRectF(center - sleep_w / 2, items["rug"].center().y() + rug_h * 0.2 - sleep_h,
                                     sleep_w, sleep_h)
        if w < 700:                              # узкое окно: только ёлка и камин
            for key in ("window", "rug", "weasel", "chair_left", "chair_right"):
                items.pop(key, None)
        return items

    def resize(self, size, ratio):
        if size == self.size and ratio == self.ratio and self.static is not None:
            return
        self.size, self.ratio = size, ratio
        self.items = self.layout(size)
        self._lights = None
        if self.snow:
            self.snow.resize(size)
        if "window" in self.items:
            self.outside.resize(self.glass().size().toSize())
        self.static = self._render_static()

    # ---- неподвижное: один раз в картинку ----
    def _render_static(self):
        w, h = self.size.width(), self.size.height()
        pix = QPixmap(max(1, round(w * self.ratio)), max(1, round(h * self.ratio)))
        pix.setDevicePixelRatio(self.ratio)
        pix.fill(QColor(C.BG))
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        items = self.items
        floor_top = items["floor_top"]
        stripe = QColor(C.TEXT)                                  # обои: еле заметные полосы
        stripe.setAlphaF(0.016)
        for x in range(0, w, 46):
            p.fillRect(QRectF(x, 0, 18, floor_top), stripe)
        fire = items["fireplace"]
        glow = QRadialGradient(QPointF(fire.center().x(), fire.bottom() - fire.height() * 0.2), fire.width() * 1.1)
        glow.setColorAt(0, QColor(255, 140, 50, 70))
        glow.setColorAt(1, QColor(255, 140, 50, 0))
        p.fillRect(QRectF(0, 0, w, h), glow)
        self._paint_floor(p, w, h, floor_top)
        if "window" in items:
            self._paint_window(p)
        p.setOpacity(self.FIRE_OPACITY)
        p.drawPixmap(fire.topLeft(), self.art.pixmap("fireplace", fire.height(), self.ratio))
        p.setOpacity(1.0)
        for name in ("tree", "presents"):
            rect = items[name]
            p.drawPixmap(rect.topLeft(), self.art.pixmap(name, rect.height(), self.ratio))
        if "rug" in items:
            rect = items["rug"]
            p.drawPixmap(rect.topLeft(), self.art.pixmap("rug", rect.height(), self.ratio, width=rect.width()))
        p.end()
        return pix

    def _window_k(self):
        return self.items["window"].height() / self.art.spec["window"]["size"][1]

    def glass(self):
        """Стекло окна в координатах комнаты."""
        win, k = self.items["window"], self._window_k()
        x0, y0, x1, y1 = self.art.spec["window"]["glass"]
        return QRectF(win.left() + x0 * k, win.top() + y0 * k, (x1 - x0) * k, (y1 - y0) * k)

    def _outside(self, name):
        """Где за окном стоят снеговик и фонарь: прямоугольник в координатах комнаты."""
        win, k = self.items["window"], self._window_k()
        x, bottom, height = self.art.spec["window"][name]
        h = height * k
        w = self.art.width_for(name, h)
        return QRectF(win.left() + x * k - w / 2, win.top() + bottom * k - h, w, h)

    def _paint_window(self, p):
        win = self.items["window"]
        p.drawPixmap(win.topLeft(), self.art.pixmap("window-back", win.height(), self.ratio))
        p.save()
        p.setClipRect(self.glass())
        rect = self._outside("lantern")                    # снеговика за окном лепишь сам (fun/snowman.py)
        p.drawPixmap(rect.topLeft(), self.art.pixmap("lantern", rect.height(), self.ratio))
        p.restore()                                        # рама - отдельным слоем поверх снеговика и снега

    def _paint_floor(self, p, w, h, top):
        rng = random.Random(9)
        wood = QLinearGradient(0, top, 0, h)
        wood.setColorAt(0, QColor("#5a3a24"))
        wood.setColorAt(0.5, QColor("#3e2716"))
        wood.setColorAt(1, QColor("#1f130a"))
        p.fillRect(QRectF(0, top, w, h - top), wood)
        rows = 4
        y = top
        for row in range(rows):                                 # доски: ниже - шире (перспектива)
            height = (h - top) * (0.16 + row * 0.06) / (0.16 * rows + 0.06 * 6)
            x = -rng.uniform(0, 160)
            while x < w:
                length = rng.uniform(140, 260)
                shade = QColor(0, 0, 0) if rng.random() < 0.5 else QColor(255, 220, 180)
                shade.setAlphaF(rng.uniform(0.02, 0.07))
                p.fillRect(QRectF(x, y, length, height), shade)
                p.setPen(QPen(QColor(0, 0, 0, 90), 1))
                p.drawLine(QPointF(x, y), QPointF(x, y + height))
                grain = QColor(0, 0, 0, 28)
                p.setPen(QPen(grain, 0.8))
                for _ in range(2):
                    gy = y + rng.uniform(0.2, 0.8) * height
                    p.drawLine(QPointF(x + 6, gy), QPointF(x + length - 6, gy + rng.uniform(-1, 1)))
                x += length
            p.setPen(QPen(QColor(0, 0, 0, 110), 1))
            p.drawLine(QPointF(0, y), QPointF(w, y))
            y += height
        p.fillRect(QRectF(0, top - 6, w, 6), QColor("#2a1a10"))         # плинтус
        p.fillRect(QRectF(0, top - 6, w, 1.2), QColor(255, 220, 180, 40))
        fire = self.items["fireplace"]
        shine = QRadialGradient(QPointF(fire.center().x(), top + 4), fire.width() * 0.8)
        shine.setColorAt(0, QColor(255, 150, 60, 60))
        shine.setColorAt(1, QColor(255, 150, 60, 0))
        p.fillRect(QRectF(0, top, w, h - top), shine)

    # ---- движение ----
    def _fire_geometry(self):
        rect = self.items["fireplace"]
        k = rect.height() / self.art.spec["fireplace"]["size"][1]
        cx, base, width, height = self.art.spec["fireplace"]["fire"]
        return QPointF(rect.left() + cx * k, rect.top() + base * k), width * k, height * k

    def fire_rect(self):
        base, width, height = self._fire_geometry()
        return QRectF(base.x() - width * 0.75, base.y() - height * 1.25, width * 1.5, height * 1.35)

    def _chair_transform(self, name, t):
        rect = self.items[name]
        px, py = self.art.spec["chair"]["pivot"]
        k = rect.height() / self.art.spec["chair"]["size"][1]
        mirror = name == "chair_right"
        pivot = QPointF(rect.left() + (rect.width() - px * k if mirror else px * k), rect.top() + py * k)
        phase = 0.0 if name == "chair_left" else 2.1
        angle = 2.4 * math.sin(t * 2 * math.pi / 4.6 + phase)
        return pivot, angle, mirror

    def light_points(self):
        """Огоньки ёлки в координатах окна: [(точка, радиус)] - считаются один раз на размер окна."""
        if self._lights is None:
            self._lights = []
            if "tree" in self.items:
                rect = self.items["tree"]
                k = rect.height() / self.art.spec["tree"]["size"][1]
                self._lights = [(QPointF(rect.left() + x * k, rect.top() + y * k), max(1.4, 2.6 * k))
                                for x, y in self.art.spec["tree"]["lights"]]
        return self._lights

    def lantern_glass(self):
        """Стекло фонаря за окном и радиус его ореола."""
        if "window" not in self.items:
            return None, 0
        rect = self._outside("lantern")
        k = rect.height() / self.art.spec["lantern"]["size"][1]
        gx, gy = self.art.spec["lantern"]["glass"]
        return QPointF(rect.left() + gx * k, rect.top() + gy * k), 70 * k

    def weasel_rect(self):
        rect = self.items["weasel"]
        return rect.adjusted(-4, -rect.height() * 0.7, rect.width() * 0.15, 4)     # с местом для «Zzz»

    def _paint_weasel(self, painter, t):
        rect = self.items["weasel"]
        breath = 1 + 0.025 * math.sin(t * 2 * math.pi / 3.4)              # дышит: бока чуть поднимаются
        painter.save()
        painter.translate(rect.center().x(), rect.bottom())
        painter.scale(1.0, breath)
        painter.translate(-rect.center().x(), -rect.bottom())
        painter.drawPixmap(rect.topLeft(), self.art.pixmap("weasel-sleep", rect.height(), self.ratio))
        painter.restore()
        head = QPointF(rect.left() + rect.width() * 0.86, rect.top() + rect.height() * 0.12)
        font = QFont(C.FONT_FAMILY)
        font.setBold(True)
        for k in range(3):                                              # «Z z z» всплывают и тают
            phase = (t / 2.6 + k / 3) % 1.0
            font.setPixelSize(int(9 + 9 * phase))
            painter.setFont(font)
            color = QColor("#e8eef8")
            color.setAlphaF(math.sin(math.pi * phase) * 0.85)
            painter.setPen(color)
            painter.drawText(head + QPointF(phase * 22, -phase * rect.height() * 0.6), "z")

    def tick(self, t, dt, colors, mode, lights=True):
        """Сдвинуть время. Возвращает кусочки окна, которые надо перерисовать. lights=False - огоньки
        и ореол фонаря в этот кадр не трогать (они меняются медленно, им хватает каждого второго кадра)."""
        self.t = t
        dirty = [self.fire_rect().toAlignedRect()]
        if lights:                                # кресла качаются медленно - им хватает 10 кадров в секунду
            self.chair_t = t
            for name in ("chair_left", "chair_right"):
                if name in self.items:
                    dirty.append(self.items[name].adjusted(-14, -14, 14, 6).toAlignedRect())
            if "weasel" in self.items:
                dirty.append(self.weasel_rect().toAlignedRect())
        for i, (point, radius) in enumerate(self.light_points() if lights else []):
            level = seasons.bulb_level(mode, i, 99, t)
            if abs(level - self.levels.get(i, -1)) > 0.04:
                self.levels[i] = level
                r = radius * 3.6
                dirty.append(QRectF(point.x() - r, point.y() - r, 2 * r, 2 * r).toAlignedRect())
        center, radius = self.lantern_glass()
        if center is not None and lights:
            dirty.append(QRectF(center.x() - radius, center.y() - radius, 2 * radius, 2 * radius).toAlignedRect())
        base, width, height = self._fire_geometry()            # искры: вылетают из огня и гаснут
        if self.rng.random() < dt * 5:
            self.sparks.append([base.x() + self.rng.uniform(-width * 0.3, width * 0.3), base.y() - height * 0.3,
                                self.rng.uniform(-8, 8), self.rng.uniform(-38, -22), 1.0])
        for spark in self.sparks:
            spark[0] += spark[2] * dt
            spark[1] += spark[3] * dt
            spark[4] -= dt * 0.9
        self.sparks = [s for s in self.sparks if s[4] > 0]
        if self.snow:
            dirty += self.snow.step(dt, t)
        if "window" in self.items:
            corner = self.glass().topLeft().toPoint()
            dirty += [rect.translated(corner) for rect in self.outside.step(dt, t)]
            if self.yard.busy() or self.yard_dirty:          # едет машина или слепился новый кусок
                self.yard_dirty = False
                dirty.append(self.glass().toAlignedRect())
        return dirty

    def paint(self, painter, widget, canvas, colors, mode, region=None):
        """Нарисовать свою часть комнаты на widget (поле текста, края, строка внизу). region - что именно
        перерисовать (в координатах widget): движущееся рисуется, только если попало в него."""
        ratio = max(1.0, widget.devicePixelRatioF())
        self.resize(canvas.size(), ratio)
        offset = widget.mapTo(canvas, QPoint(0, 0)) if widget is not canvas else QPoint(0, 0)
        region = QRegion(widget.rect()) if region is None or region.isEmpty() else region
        region = region.translated(offset)
        painter.save()
        painter.translate(-offset)
        painter.setRenderHint(QPainter.Antialiasing)
        clip = QRectF(region.boundingRect())

        def hit(rect):
            return region.intersects(rect.toAlignedRect())
        painter.drawPixmap(clip, self.static, QRectF(clip.left() * ratio, clip.top() * ratio,
                                                     clip.width() * ratio, clip.height() * ratio))
        t = self.t
        if hit(self.fire_rect()):
            self._paint_fire(painter, t)
        for name in ("chair_left", "chair_right"):
            if name in self.items and hit(self.items[name].adjusted(-14, -14, 14, 6)):
                pivot, angle, mirror = self._chair_transform(name, self.chair_t)
                rect = self.items[name]
                painter.save()
                painter.translate(pivot)
                painter.rotate(angle)
                painter.translate(-pivot)
                painter.setOpacity(self.CHAIR_OPACITY)
                painter.drawPixmap(rect.topLeft(), self.art.pixmap("chair", rect.height(), ratio, mirror))
                painter.restore()
        for i, (point, radius) in enumerate(self.light_points()):
            if hit(QRectF(point.x() - radius * 3.5, point.y() - radius * 3.5, radius * 7, radius * 7)):
                paint_bulb(painter, point, colors[i % len(colors)], seasons.bulb_level(mode, i, 99, t), radius)
        if "weasel" in self.items and hit(self.weasel_rect()):
            self._paint_weasel(painter, self.chair_t)
        if "window" in self.items and hit(self.glass()):          # за окном: ореол фонаря и снег
            glass = self.glass()
            painter.save()
            painter.setClipRect(glass, Qt.IntersectClip)
            center, radius = self.lantern_glass()
            halo = QRadialGradient(center, radius)
            a = 0.34 + 0.07 * _noise(t, 4.0)
            halo.setColorAt(0, QColor(255, 180, 80, int(255 * a)))
            halo.setColorAt(1, QColor(255, 180, 80, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(halo)
            painter.drawEllipse(center, radius, radius)
            spot = self._outside("snowman")
            self.yard.paint(painter, QPointF(spot.center().x(), spot.bottom()), spot.height(), glass.width(), t)
            painter.translate(glass.topLeft())
            self.outside.paint(painter, 0.9)
            painter.restore()
            win = self.items["window"]
            painter.drawPixmap(win.topLeft(), self.art.pixmap("window-front", win.height(), ratio))
        if self.snow:
            self.snow.paint(painter, 0.75, region)
        painter.restore()

    def _paint_fire(self, painter, t):
        base, width, height = self._fire_geometry()
        painter.save()
        painter.setPen(Qt.NoPen)
        glow = QRadialGradient(QPointF(base.x(), base.y() - height * 0.2), width * 0.9)
        glow.setColorAt(0, QColor(255, 150, 50, int(110 + 30 * _noise(t, 1.0))))
        glow.setColorAt(1, QColor(255, 120, 40, 0))
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(base.x(), base.y() - height * 0.2), width * 0.9, height * 0.8)
        for layer, (scale, colors, alpha) in enumerate(
                ((1.0, ("#ff4a12", "#ff8a2a", "#ffc14d"), 0.9), (0.62, ("#ff9a2e", "#ffd66b", "#fff3c0"), 0.95))):
            count = 7 if layer == 0 else 5
            for j in range(count):
                rel = j / (count - 1) - 0.5
                x = base.x() + rel * width * 0.78 * scale
                half = width * 0.12 * (1 - abs(rel) * 0.6)
                tall = height * scale * (0.5 + 0.5 * (1 - abs(rel) * 1.5)) * (0.82 + 0.18 * _noise(t * 1.3, j + layer * 7))
                sway = (math.sin(t * 3.1 + j * 1.7) * 0.6 + math.sin(t * 7.3 + j * 2.3) * 0.25) * half
                path = QPainterPath(QPointF(x - half, base.y()))
                path.cubicTo(QPointF(x - half, base.y() - tall * 0.45), QPointF(x + sway * 0.3 - half * 0.45,
                             base.y() - tall * 0.72), QPointF(x + sway, base.y() - tall))
                path.cubicTo(QPointF(x + sway * 0.3 + half * 0.45, base.y() - tall * 0.72),
                             QPointF(x + half, base.y() - tall * 0.45), QPointF(x + half, base.y()))
                path.closeSubpath()
                grad = QLinearGradient(0, base.y(), 0, base.y() - tall)
                for stop, color in zip((0.0, 0.45, 0.8), colors):
                    c = QColor(color)
                    c.setAlphaF(alpha)
                    grad.setColorAt(stop, c)
                tip = QColor(colors[-1])
                tip.setAlphaF(0.0)
                grad.setColorAt(1.0, tip)
                painter.setBrush(grad)
                painter.drawPath(path)
        for x, y, _vx, _vy, life in self.sparks:
            c = QColor(255, 190, 90)
            c.setAlphaF(max(0.0, life))
            painter.setBrush(c)
            painter.drawEllipse(QPointF(x, y), 1.4, 1.4)
        painter.restore()


class Overlay(QWidget):
    """Поверх текста: гирлянда по верху, венок вокруг часов, редкий снег. Мышь проходит насквозь."""

    def __init__(self, parent, look):
        super().__init__(parent)
        self.look = look
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.snow = None
        self.snow_alpha = 1.0
        self.levels = {}
        self.setGeometry(parent.rect())
        parent.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.parent() and event.type() == QEvent.Resize:
            self.setGeometry(self.parent().rect())
            if self.snow:
                self.snow.resize(self.size())
        return False

    def set_snow(self, on):
        self.snow = Snow(22, (1.6, 3.4), (34, 70), 23) if on else None
        if self.snow:
            self.snow.resize(self.size())

    def _wire(self):
        """Провод гирлянды волнами и патроны - одной картинкой на ширину окна."""
        ratio = max(1.0, self.devicePixelRatioF())
        key = (self.width(), ratio, C.BG)
        if getattr(self, "_wire_key", None) != key:
            pix = QPixmap(max(1, round(self.width() * ratio)), round(50 * ratio))
            pix.setDevicePixelRatio(ratio)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            span, top = 150.0, 3.0
            wire = QPainterPath(QPointF(0, top))
            for i in range(int(self.width() / span) + 2):
                wire.quadTo(QPointF(i * span + span / 2, top + 30), QPointF(i * span + span, top))
            p.setPen(QPen(C.mix("#3a4a3c", C.BG, 0.2), 2))
            p.drawPath(wire)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#2b332c"))
            for point in self.garland_points():
                p.drawRect(QRectF(point.x() - 2, point.y() - 8, 4, 4))
            p.end()
            self._wire_pix, self._wire_key = pix, key
        return self._wire_pix

    def garland_points(self):
        span, top = 150.0, 3.0
        points = []
        for i in range(int(self.width() / span) + 2):
            for k in (0.2, 0.5, 0.8):
                points.append(QPointF(i * span + span * k, top + 60 * (1 - k) * k + 8))
        return points

    def wreath_rect(self):
        clock = self.look.clock()
        if clock is None:
            return None
        geo = QRect(clock.mapTo(self.parent(), QPoint(0, 0)), clock.size())
        d = geo.width() * 1.42
        k = self.look.art.spec["wreath"]
        cx, cy = k["center"]
        w, h = k["size"]
        scale = d / w
        return QRectF(geo.center().x() - cx * scale, geo.center().y() - cy * scale, w * scale, h * scale)

    def wreath_points(self):
        rect = self.wreath_rect()
        if rect is None:
            return []
        spec = self.look.art.spec["wreath"]
        k = rect.width() / spec["size"][0]
        return [QPointF(rect.left() + x * k, rect.top() + y * k) for x, y in spec["lights"]]

    def tick(self, t, dt, mode, typing, lights=True):
        dirty = []
        target = 0.12 if typing else 1.0
        self.snow_alpha += (target - self.snow_alpha) * min(1.0, dt * 3)
        garland = self.garland_points()
        for n, point in enumerate(garland + self.wreath_points() if lights else []):
            level = seasons.bulb_level(mode, n, 99, t)
            if abs(level - self.levels.get(n, -1)) > 0.04:
                self.levels[n] = level
                half = 17 if n < len(garland) else 9
                dirty.append(QRect(int(point.x() - half), int(point.y() - half), 2 * half, 2 * half))
        if self.snow:
            dirty += self.snow.step(dt, t)
        if dirty:
            region = QRegion()
            for rect in dirty:
                region += rect
            self.update(region)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors, mode, t = self.look.colors, self.look.mode, self.look.t
        region = event.region()
        clip = QRectF(event.rect())
        if self.snow:
            self.snow.paint(painter, self.snow_alpha, region)
        wire = self._wire()
        if region.intersects(QRect(0, 0, self.width(), 50)):
            painter.drawPixmap(0, 0, wire)
        for n, point in enumerate(self.garland_points()):
            if not region.intersects(QRect(int(point.x() - 17), int(point.y() - 17), 34, 34)):
                continue
            paint_bulb(painter, point, colors[n % len(colors)], seasons.bulb_level(mode, n, 99, t), 4.6)
        rect = self.wreath_rect()
        if rect is not None and clip.intersects(rect):
            ratio = max(1.0, self.devicePixelRatioF())
            painter.drawPixmap(rect.topLeft(), self.look.art.pixmap("wreath", rect.height(), ratio))
            base = len(self.garland_points())
            for n, point in enumerate(self.wreath_points()):
                paint_bulb(painter, point, colors[n % len(colors)],
                           seasons.bulb_level(mode, base + n, 99, t), 2.4)
        painter.end()


def paint_snow_bar(painter, track, value, done):
    """Полоска цели в праздник: заполняется снегом - комковатый верх, голубая тень, искры, снежок на краю."""
    painter.save()
    painter.setPen(Qt.NoPen)
    groove = C.mix(C.DIM, C.BG, 0.6)
    painter.setBrush(groove)
    painter.drawRoundedRect(track, 3, 3)
    length = max(track.height(), track.width() * max(0.0, min(1.0, value)))
    if value > 0:
        fill = QRectF(track.left(), track.top(), length, track.height())
        path = QPainterPath(QPointF(fill.left(), fill.bottom()))
        path.lineTo(fill.left(), fill.top() + 1)
        x, n = fill.left(), 0
        while x < fill.right():
            step = min(6.0, fill.right() - x)
            bump = 1.2 + 1.6 * seasons._hash(n)
            path.quadTo(QPointF(x + step / 2, fill.top() - bump), QPointF(x + step, fill.top() + 0.5))
            x += step
            n += 1
        path.lineTo(fill.right(), fill.bottom())
        path.closeSubpath()
        grad = QLinearGradient(0, fill.top() - 3, 0, fill.bottom())
        grad.setColorAt(0, QColor("#ffffff"))
        grad.setColorAt(0.6, QColor("#e7eff9"))
        grad.setColorAt(1, QColor("#a9c0db"))
        painter.setBrush(grad)
        painter.drawPath(path)
        for i in range(int(length / 9)):                         # искорки на снегу
            sx = fill.left() + 4 + i * 9 + 3 * seasons._hash(i + 40)
            sy = fill.top() + fill.height() * seasons._hash(i + 80) * 0.7
            painter.setBrush(QColor(255, 255, 255, 230) if i % 2 else QColor(170, 210, 255, 220))
            painter.drawEllipse(QPointF(sx, sy), 0.8, 0.8)
        end = QPointF(fill.right() - 1, fill.center().y() - 0.5)
        ball = QRadialGradient(QPointF(end.x() - 1.2, end.y() - 1.2), track.height() * 0.9)
        ball.setColorAt(0, QColor("#ffffff"))
        ball.setColorAt(1, QColor("#b8cce4"))
        painter.setBrush(ball)
        painter.drawEllipse(end, track.height() * 0.75, track.height() * 0.75)
        if done:                                                # цель есть - снежинка на краю
            painter.setPen(QPen(QColor(C.IMPORTANT), 1.2))
            star = QPointF(fill.right() + 9, fill.center().y())
            for k in range(3):
                a = math.radians(90 + k * 60)
                d = QPointF(math.cos(a) * 4.5, math.sin(a) * 4.5)
                painter.drawLine(star - d, star + d)
    painter.restore()


class SeasonLook(QObject):
    """Праздник в окне: включает комнату, верхний слой, снежную полоску и сдвигает часы под венок."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.key = None
        self.art = None
        self.room = None
        self.overlay = None
        self.colors = list(seasons.PALETTES["multi"])
        self.mode = "twinkle"
        self.t = 0.0
        self._last = time.monotonic()
        self._typed = 0.0
        self.timer = QTimer(self, interval=FRAME_MS)
        self.timer.timeout.connect(self.tick)
        window.editor.installEventFilter(self)
        self.refresh()

    # ---- что включено ----
    def clock(self):
        clock = getattr(self.window, "corner_clock", None)
        return clock if clock is not None and clock.isVisible() else None

    def refresh(self):
        """Сверить с настройками и датой. Возвращает True, если что-то поменялось."""
        from ..ui.windows import load_config_raw
        config = load_config_raw()
        key = seasons.active(config)
        state = (key, seasons.option(config, "season_room"), seasons.option(config, "season_snow_under"),
                 seasons.option(config, "season_snow_over"), seasons.option(config, "season_motion"))
        self.colors = seasons.garland_colors(config)
        self.mode = seasons.option(config, "season_garland")
        if not seasons.option(config, "season_motion"):
            self.mode = "steady"
        if state == getattr(self, "_state", None):
            if self.overlay:
                self.overlay.update()
            return False
        self._state = state
        C.SEASON = key
        from .dice import use_season_coin
        use_season_coin(key == "xmas")                     # монетка-пряник: ёлка и снежинка
        window = self.window
        room_on = bool(key) and state[1]
        room_changed = room_on != C.SEASON_ROOM
        if key and (self.art is None or self.key != key):
            self.art = Art(seasons.SEASONS[key]["art"])
        self.key = key
        self.room = Room(self.art, config) if room_on else None
        window.editor.scene = self if room_on else None
        C.SEASON_ROOM = room_on
        if key:
            if self.overlay is None:
                self.overlay = Overlay(window.centralWidget(), self)
            self.overlay.set_snow(state[3])
            self.overlay.show()
            self.overlay.stackUnder(window.corner_clock)
        elif self.overlay is not None:
            self.overlay.deleteLater()
            self.overlay = None
        window.goal_strip.bar_painter = paint_snow_bar if key else None
        window.clock_spot = self.clock_spot if room_on else None
        window.clock_pad = 16 if key else 0
        if room_changed:                  # фон поля: прозрачный под комнату или обычный
            window.apply_palette(window._palette_now or C.palette())
        window.apply_backdrop()
        window.place_overlays()
        window.goal_strip.update()
        if key and state[4]:
            self._last = time.monotonic()
            self.timer.start()
        else:
            self.timer.stop()
        self.tick(force=True)
        return True

    def clock_spot(self):
        """Куда повесить часы в венке: на стену над окном, по его середине. Не влезает - None (угол как обычно)."""
        if self.room is None:
            return None
        canvas = self.window.centralWidget()
        self.room.resize(canvas.size(), max(1.0, canvas.devicePixelRatioF()))
        win = self.room.items.get("window")
        clock = self.window.corner_clock
        if win is None:
            return None
        size = clock.width()
        center_y = win.top() - size * 0.82                  # бант венка - чуть выше карниза
        if center_y - size * 0.75 < 44:                     # сверху гирлянда: места нет
            return None
        return QPoint(round(win.center().x() - size / 2), round(center_y - clock.height() / 2))

    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress:
            self._typed = time.monotonic()
        return False

    # ---- кадр ----
    def tick(self, force=False):
        window = self.window
        if not force and (window.isMinimized() or not window.isVisible()):
            return
        now = time.monotonic()
        dt = min(0.1, now - self._last)
        self._last = now
        self.t += dt
        if self.timer.isActive():
            self.timer.setInterval(FRAME_MS if window.isActiveWindow() else IDLE_MS)
        typing = now - self._typed < 1.4
        self._frame = getattr(self, "_frame", 0) + 1
        lights = force or self._frame % 2 == 0
        if self.room is not None:
            canvas = window.centralWidget()
            self.room.resize(canvas.size(), max(1.0, canvas.devicePixelRatioF()))
            if force or now - getattr(self, "_words_at", 0.0) > 1.0:      # снеговик за окном - раз в секунду
                self._words_at = now
                self.feed_yard()
            dirty = self.room.tick(self.t, dt, self.colors, self.mode, lights)
            self._invalidate(dirty)
        if self.overlay is not None:
            self.overlay.tick(self.t, dt, self.mode, typing, lights)

    def feed_yard(self):
        """Слова за сегодня - снеговику за окном: растёт, а на 300% цели его кто-нибудь сносит."""
        window = self.window
        if self.room is None or not hasattr(window, "today_words"):
            return
        try:
            written = window.today_words()
        except (AttributeError, TypeError):
            return
        from datetime import date
        day = (seasons.FIXED_TODAY or date.today()).isoformat()
        if self.room.yard.update(written, getattr(window, "goal", C.DAILY_GOAL), day, self.t):
            self.room.yard_dirty = True

    def _invalidate(self, rects):
        canvas = self.window.centralWidget()
        region = QRegion()
        for rect in rects:
            region += rect
        layer = getattr(self.window, "backdrop_layer", None)
        if layer is not None:
            layer.update(region)
        editor = self.window.editor
        for widget in (editor.viewport(), getattr(editor, "margin_widget", None)):
            if widget is not None and widget.isVisible():
                widget.update(region.translated(-widget.mapTo(canvas, QPoint(0, 0))))

    def paint(self, painter, widget, canvas, region=None):
        if self.room is not None:
            self.room.paint(painter, widget, canvas, self.colors, self.mode, region)
