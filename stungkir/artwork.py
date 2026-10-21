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
