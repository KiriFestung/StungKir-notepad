# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Обложка категории: своя картинка у книги. Видна значком в списке слева, крупно - в окошке
«Обложка…» (правый клик по категории) и становится обложкой при сборке книги в PDF и EPUB.

Картинка хранится в служебной папке (.stungkir/covers/<категория>.cover) текстом base64 -
поэтому с паролем она шифруется тем же замком, что и главы, попадает в точки возврата и копии
и никогда не лежит на диске открытой картинкой."""

import base64

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage, QPixmap

from . import config as C
from .storage import LockedFile, read_text, save_text, shred

MAX_SIDE = 1100                       # больше для обложки не нужно, а файл маленький
PREFIX = "data:image/jpeg;base64,"
_cache = {}


def cover_path(category):
    return C.service_path(".covers") / f"{category.name}.cover"


def has_cover(category):
    return cover_path(category).is_file()


def save_cover(category, image_file):
    """Поставить обложку из картинки (jpg, png, webp…). False - картинка не читается."""
    image = QImage(str(image_file))
    if image.isNull():
        return False
    if max(image.width(), image.height()) > MAX_SIDE:
        image = image.scaled(MAX_SIDE, MAX_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.convertToFormat(QImage.Format_RGB32).save(buffer, "JPEG", 88)
    buffer.close()
    path = cover_path(category)
    path.parent.mkdir(parents=True, exist_ok=True)
    save_text(path, PREFIX + base64.b64encode(bytes(data)).decode("ascii"))
    _cache.pop(str(path), None)
    return True


def cover_bytes(category):
    """JPEG обложки или None (нет обложки, файл испорчен, не тот пароль)."""
    path = cover_path(category)
    if not path.is_file():
        return None
    try:
        text = read_text(path).strip()
        return base64.b64decode(text.removeprefix(PREFIX), validate=True)
    except (OSError, LockedFile, ValueError):
        return None


def cover_pixmap(category):
    """Картинка обложки (запоминается, пока файл не поменялся)."""
    path = cover_path(category)
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return QPixmap()
    found = _cache.get(str(path))
    if found and found[0] == stamp:
        return found[1]
    data = cover_bytes(category)
    pixmap = QPixmap()
    if data:
        pixmap.loadFromData(data, "JPEG")
    _cache[str(path)] = (stamp, pixmap)
    return pixmap


def remove_cover(category):
    path = cover_path(category)
    if path.is_file() and not shred(path):
        path.unlink(missing_ok=True)
    _cache.pop(str(path), None)


def move_cover(old, new):
    """Категорию переименовали - обложка едет следом."""
    source, target = cover_path(old), cover_path(new)
    if source.is_file() and not target.exists():
        source.replace(target)
        _cache.pop(str(source), None)
