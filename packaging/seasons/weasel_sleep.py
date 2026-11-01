# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ласка спит на коврике у камина (Рождество): тот же рисунок автора (packaging/art-src/weasel.png), лапы срезаны
и дорисованы поджатыми, голова опущена на передние лапы, хвост лежит на полу, глаз закрыт, на голове - шапка.
Дыхание и «Zzz» рисует программа. python3 packaging/seasons/weasel_sleep.py [папка]"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "anim"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath,  # noqa: E402
                           QPen, QRadialGradient)

import weasel as W  # noqa: E402  (packaging/anim/weasel.py: срез лап и цвета рисунка)

ROOT = HERE.parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stungkir" / "art" / "seasons" / "xmas"
WIDTH, HEIGHT = 520, 280
SS = 2
GROUND = 250                                    # где пол (в точках рисунка)
LIFT = 52                                       # насколько опущено всё тело (лежит)


def drop(x):
    """На сколько опустить столбик рисунка x: тело лежит, хвост на полу, голова на лапах."""
    if x < W.HIP:
        return LIFT + (W.HIP - x) * 0.2            # круп и хвост ложатся на пол
    if x > W.SHOULDER:
        return LIFT + (x - W.SHOULDER) * 0.42      # голова клонится к передним лапам
    return LIFT


def point(x, y):
    return QPointF(x + 10, y + drop(x))


def clean(image):
    """Белая кайма по краю рисунка (он лежал на белом) на тёмной комнате видна точками - убираем её.
    Кремовое брюхо (синий канал ~207) не трогаем: убираем только почти белое."""
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            if c.alpha() and c.red() > 228 and c.green() > 228 and c.blue() > 228:
                image.setPixelColor(x, y, QColor(0, 0, 0, 0))
    return image


def paw(p, center, rx, ry, fill):
    shape = QPainterPath()
    shape.addEllipse(center, rx, ry)
    p.setPen(QPen(W.OCHRE, W.LINE * 1.6))
    p.setBrush(fill)
    p.drawPath(shape)
    p.setPen(Qt.NoPen)
    p.setBrush(W.CREAM)
    p.save()
    p.setClipPath(shape)
    p.drawEllipse(center + QPointF(rx * 0.55, ry * 0.25), rx * 0.6, ry * 0.8)
    p.restore()


def main():
    QGuiApplication.instance() or QGuiApplication([])
    sprite = QImage(str(ROOT / "packaging" / "art-src" / "weasel.png"))
    body = clean(W.body_image(sprite))
    image = QImage(WIDTH * SS, HEIGHT * SS, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(SS, SS)
    shadow = QRadialGradient(QPointF(270, GROUND), 230)
    shadow.setColorAt(0, QColor(0, 0, 0, 90))
    shadow.setColorAt(1, QColor(0, 0, 0, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(shadow)
    p.drawEllipse(QPointF(270, GROUND), 240, 16)
    # лапы - раньше тела: тело ложится на них сверху, видны только кончики
    paw(p, QPointF(250, GROUND - 16), 40, 14, W.FAR)                 # дальняя задняя - в тени
    paw(p, QPointF(212, GROUND - 10), 44, 13, W.BODY)                # ближняя задняя поджата
    paw(p, QPointF(470, GROUND - 40), 32, 10, W.FAR)                 # передние вытянуты, морда на них
    paw(p, QPointF(456, GROUND - 32), 34, 10, W.BODY)
    for x in range(body.width()):                                    # тело полосками, каждая на свою высоту
        target = point(x, 0)
        p.drawImage(QRectF(target.x(), target.y(), 1.6, body.height()), body, QRectF(x, 0, 1, body.height()))
    belly = QPainterPath(point(150, W.cut(150)))
    for x in range(152, 372, 2):
        belly.lineTo(point(x, W.cut(x)))
    p.setPen(QPen(W.OCHRE, W.LINE * 1.2, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawPath(belly)
    # закрытый глаз - дужка вниз
    eye = point(442, 48)
    p.setPen(QPen(QColor(40, 26, 70), 3.2, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(QRectF(eye.x() - 9, eye.y() - 6, 18, 12), 200 * 16, 140 * 16)
    # шапка: красный колпак назад к спине, белая опушка, помпон
    a, b = point(380, 14), point(456, 22)
    hat = QPainterPath(a)
    hat.cubicTo(a + QPointF(-4, -38), point(350, -34), point(330, -14))
    hat.cubicTo(point(352, -22), a + QPointF(40, -30), b)
    hat.closeSubpath()
    red = QLinearGradient(a, point(330, -14))
    red.setColorAt(0, QColor("#e3423a"))
    red.setColorAt(1, QColor("#9c1a1a"))
    p.setPen(QPen(W.OCHRE, W.LINE))
    p.setBrush(red)
    p.drawPath(hat)
    rim = QPainterPath(a + QPointF(-4, 4))
    rim.cubicTo(a + QPointF(20, -8), b + QPointF(-20, -10), b + QPointF(4, 2))
    pen = QPen(QColor("#f4f7fb"), 15, Qt.SolidLine, Qt.RoundCap)
    p.setPen(QPen(W.OCHRE, 19, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(rim)
    p.setPen(pen)
    p.drawPath(rim)
    pom = point(328, -12)
    p.setPen(QPen(W.OCHRE, W.LINE))
    p.setBrush(QColor("#f4f7fb"))
    p.drawEllipse(pom, 13, 13)
    p.end()
    OUT.mkdir(parents=True, exist_ok=True)
    small = image.scaled(WIDTH * 2 // 3 * 2, HEIGHT * 2 // 3 * 2, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    small.save(str(OUT / "weasel-sleep.png"))      # вдвое крупнее показа: чётко и на экранах с увеличением


if __name__ == "__main__":
    main()
