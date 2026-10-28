# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Нарисованная графика из папки art/: ласка в колесе таймера, стороны монетки.
Картинки нарисованы для StungKir (индиго и охра) и лежат в пакете как PNG с прозрачностью.
Нет файла - вернётся пустая картинка, и то место просто рисуется без неё."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

FOLDER = Path(__file__).resolve().parent / "art"
_cache = {}


def pixmap(name):
    """Картинка как есть (один раз загружается с диска)."""
    if name not in _cache:
        _cache[name] = QPixmap(str(FOLDER / f"{name}.png"))
    return _cache[name]


def scaled(name, width, ratio=1.0):
    """Та же картинка, уменьшенная до ширины width (в точках экрана) заранее и плавно:
    уменьшать большую картинку на каждом кадре анимации было бы и медленно, и мыльно."""
    width = max(1, int(round(width)))
    key = (name, width, round(ratio, 2))
    if key not in _cache:
        source = pixmap(name)
        if source.isNull():
            _cache[key] = source
        else:
            result = source.scaledToWidth(int(width * ratio), Qt.SmoothTransformation)
            result.setDevicePixelRatio(ratio)
            _cache[key] = result
    return _cache[key]


def frame_count(name):
    """Сколько кадров у анимации name (файлы name_00.png, name_01.png ...); 0 - кадров нет."""
    key = ("frames", name)
    if key not in _cache:
        folder, stem = (FOLDER / name).parent, Path(name).name
        count = 0
        while (folder / f"{stem}_{count:02d}.png").exists():
            count += 1
        _cache[key] = count
    return _cache[key]


class Effects:
    """Короткие нарисованные вспышки поверх игрушки (лопнул пузырь, пыль от удара, брызги):
    play() запускает кадры name_NN в точке, paint() рисует живые в paintEvent хозяина.
    Пока что-то играет, хозяин сам перерисовывается; доиграло - таймер стоит."""

    FPS = 30

    def __init__(self, widget, clock=None):
        import time
        from PySide6.QtCore import QTimer
        self.widget = widget
        self.clock = clock or time.monotonic
        self.live = []
        self.timer = QTimer(widget, timerType=Qt.PreciseTimer)
        self.timer.setInterval(1000 // self.FPS)
        self.timer.timeout.connect(self._tick)

    def play(self, name, x, y, width, anchor="center", fps=None, opacity=1.0):
        """x, y - точка привязки: середина кадра (anchor="center") или середина его низа ("bottom").
        False - кадров нет (тогда хозяин обходится без вспышки)."""
        count = frame_count(name)
        if not count or width <= 1:
            return False
        self.live.append({"name": name, "x": float(x), "y": float(y), "width": float(width),
                          "anchor": anchor, "count": count, "fps": fps or self.FPS,
                          "opacity": opacity, "start": self.clock()})
        if not self.timer.isActive():
            self.timer.start()
        return True

    def frame(self, effect):
        """Номер кадра сейчас; None - уже доиграло."""
        index = int((self.clock() - effect["start"]) * effect["fps"])
        return index if index < effect["count"] else None

    @property
    def busy(self):
        return any(self.frame(effect) is not None for effect in self.live)

    def clear(self):
        self.live.clear()
        self.timer.stop()

    def _tick(self):
        from PySide6.QtWidgets import QWidget
        self.live = [effect for effect in self.live if self.frame(effect) is not None]
        if not self.live:
            self.timer.stop()
        QWidget.update(self.widget)

    def paint(self, painter):
        from PySide6.QtCore import QRectF
        ratio = self.widget.devicePixelRatioF()
        for effect in self.live:
            index = self.frame(effect)
            if index is None:
                continue
            picture = scaled(f"{effect['name']}_{index:02d}", effect["width"], ratio)
            if picture.isNull():
                continue
            width = effect["width"]
            height = width * picture.height() / max(1, picture.width())
            top = effect["y"] - (height if effect["anchor"] == "bottom" else height / 2)
            painter.save()
            painter.setOpacity(painter.opacity() * effect["opacity"])
            painter.drawPixmap(QRectF(effect["x"] - width / 2, top, width, height), picture,
                               QRectF(picture.rect()))
            painter.restore()
