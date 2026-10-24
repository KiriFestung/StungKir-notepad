# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Огонёк серии: живое пламя по ступеням (каждые 10 дней подряд - выше и наряднее).
Охристый огонь из нескольких языков, индиго-капля внутри, кремовое пятно под число. Языки тянутся,
качаются и перехлёстываются; 12 кадров идут по кругу без рывка (всё движение - целые периоды).
python3 packaging/anim/flame.py [папка art] - перезаписывает anim/flame/flame-<ступень>_NN.png."""

import math
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QLinearGradient, QPainter,  # noqa: E402
                           QPainterPath, QPen, QRadialGradient)

SIZE = 192
SS = 2
FRAMES = 12
BOTTOM = 246 / 256                     # низ пламени - доля высоты кадра (так ставит программа)
SPOT = 158 / 256                       # середина пятна под число
GOLD_TOP, GOLD_BOTTOM = QColor(255, 222, 128), QColor(214, 140, 40)
INDIGO_TOP, INDIGO_BOTTOM = QColor(84, 76, 200), QColor(30, 24, 110)
CREAM = QColor(255, 244, 214)
EDGE = QColor(186, 112, 28)            # тонкий тёмный край огня


def wave(t, speed, phase):
    """Колебание, которое за кадры 0..12 делает целое число оборотов - цикл без шва."""
    return math.sin(2 * math.pi * (speed * t + phase))


def tongue(base_x, base_y, half, height, lean, curl=0.25):
    """Язык пламени: широкое основание, бока выгибаются наружу и сходятся к тонкому кончику с изгибом."""
    tip = QPointF(base_x + lean * height, base_y - height)
    path = QPainterPath(QPointF(base_x - half, base_y))
    path.cubicTo(QPointF(base_x - half * 1.25, base_y - height * 0.38),
                 QPointF(tip.x() - half * (0.55 + curl), base_y - height * 0.72), tip)
    path.cubicTo(QPointF(tip.x() + half * (0.45 - curl * 0.5), base_y - height * 0.66),
                 QPointF(base_x + half * 1.25, base_y - height * 0.36), QPointF(base_x + half, base_y))
    path.closeSubpath()
    return path


def spot_radius(stage, t=0.0):
    return SIZE * (0.15 + 0.008 * stage) * (1 + 0.025 * wave(t, 2, 0.1))


def flame(stage, t):
    """Форма огня и капли в момент t (0..1) для ступени stage. Всё строится вокруг пятна под число:
    капля его обнимает, огонь обнимает каплю, языки растут вверх с каждой ступенью."""
    s = SIZE
    cx, spot = s / 2, s * SPOT
    r = spot_radius(stage)
    bottom = s * BOTTOM
    rng = random.Random(stage * 31 + 7)
    drop_r = r * 1.3
    rx = drop_r + s * (0.07 + 0.016 * stage)
    ry = min(rx, (bottom - spot) * 0.98)                              # круглый низ, кверху - языки
    outer = QPainterPath()
    outer.addEllipse(QPointF(cx, bottom - ry), rx, ry)
    tongues = [(0.0, 1.0, 0.62)]                                     # (сдвиг, высота, ширина) - главный
    if stage >= 1:
        tongues += [(-0.45, 0.62, 0.4), (0.47, 0.58, 0.38)]
    if stage >= 2:
        tongues += [(-0.75, 0.46, 0.3), (0.77, 0.44, 0.29)]
    if stage >= 4:
        tongues += [(-0.22, 0.82, 0.34), (0.26, 0.8, 0.32)]
    if stage >= 5:
        tongues += [(-0.9, 0.36, 0.22), (0.92, 0.34, 0.22), (0.06, 0.9, 0.28)]
    top = s * (0.25 - 0.034 * stage)                                  # куда тянется главный язык
    height = (spot - top) / 1.13                                      # с запасом на колыхание - не за край
    for shift, tall, wide in tongues:
        speed = rng.choice((1, 2, 3))
        phase = rng.random()
        h = height * tall * (1 + 0.09 * wave(t, speed, phase) + 0.04 * wave(t, speed + 2, phase * 1.7)) + drop_r * 0.4
        lean = 0.1 * wave(t, rng.choice((1, 2)), rng.random()) + shift * 0.2
        outer = outer.united(tongue(cx + shift * rx, spot, rx * wide, h, lean))
    inner = QPainterPath()
    inner.addEllipse(QPointF(cx, spot), drop_r, drop_r)
    inner_h = drop_r * 0.4 + height * 0.62 * (1 + 0.06 * wave(t, 2, 0.3))
    inner = inner.united(tongue(cx, spot, drop_r * 0.98, inner_h, 0.07 * wave(t, 1, 0.6), curl=0.1))
    return outer.simplified(), inner.simplified(), bottom - top


def sparks(p, stage, t):
    """Искры летят вверх и гаснут; у каждой свой круг, все круги - целые."""
    if stage < 3:
        return
    rng = random.Random(stage)
    for _k in range(4 + 3 * stage):
        x = SIZE / 2 + rng.uniform(-0.38, 0.38) * SIZE
        start = rng.random()
        life = (t + start) % 1.0
        y = SIZE * (0.6 - 0.55 * life)
        size = rng.uniform(1.6, 3.2) * (1 - life * 0.6)
        alpha = int(230 * math.sin(math.pi * life))
        x += 6 * math.sin(2 * math.pi * (life + start))
        color = QColor(255, 226, 140, alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        star = QPainterPath(QPointF(x, y - size * 2))
        for corner in ((x + size * 0.5, y - size * 0.5), (x + size * 2, y), (x + size * 0.5, y + size * 0.5),
                       (x, y + size * 2), (x - size * 0.5, y + size * 0.5), (x - size * 2, y),
                       (x - size * 0.5, y - size * 0.5)):
            star.lineTo(QPointF(*corner))
        star.closeSubpath()
        p.drawPath(star)


def render(stage, index):
    t = index / FRAMES
    image = QImage(SIZE * SS, SIZE * SS, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(SS, SS)
    outer, inner, height = flame(stage, t)
    bottom = SIZE * BOTTOM
    glow = QRadialGradient(QPointF(SIZE / 2, bottom - height * 0.5), SIZE * 0.48)    # тёплый ореол, внутри кадра
    glow.setColorAt(0, QColor(255, 200, 90, 60 + 10 * stage))
    glow.setColorAt(1, QColor(255, 200, 90, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(glow)
    p.drawEllipse(QPointF(SIZE / 2, bottom - height * 0.5), SIZE * 0.48, SIZE * 0.48)
    gold = QLinearGradient(0, bottom - height, 0, bottom)
    gold.setColorAt(0, GOLD_TOP)
    gold.setColorAt(1, GOLD_BOTTOM)
    p.setBrush(gold)
    p.setPen(QPen(EDGE, 1.6))
    p.drawPath(outer)
    p.setPen(Qt.NoPen)
    deep = QLinearGradient(0, bottom - height * 0.8, 0, bottom)
    deep.setColorAt(0, INDIGO_TOP)
    deep.setColorAt(1, INDIGO_BOTTOM)
    p.setBrush(deep)
    p.drawPath(inner)
    spot = QPointF(SIZE / 2, SIZE * SPOT)
    radius = spot_radius(stage, t)
    light = QRadialGradient(spot, radius * 1.35)
    light.setColorAt(0, CREAM)
    light.setColorAt(0.72, CREAM)
    light.setColorAt(1, QColor(255, 244, 214, 0))
    p.setBrush(light)
    p.drawEllipse(spot, radius * 1.35, radius * 1.35)
    sparks(p, stage, t)
    p.end()
    return image.scaled(SIZE, SIZE, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def main(art):
    app = QGuiApplication.instance() or QGuiApplication([])
    folder = Path(art) / "anim" / "flame"
    for stage in range(6):
        for index in range(FRAMES):
            render(stage, index).save(str(folder / f"flame-{stage}_{index:02d}.png"))
    del app


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "stungkir" / "art")
