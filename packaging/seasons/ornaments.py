# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Пупырка из ёлочных шариков (Рождество): три шарика - красный с белым зигзагом, золотой в горошек,
синий со снежинкой; у каждого золотой колпачок с петелькой и стеклянный блик. Лопнул - осколки разлетаются,
сыплются золотые блёстки, на плёнке остаются колпачок, пара осколков и блёстки.
python3 packaging/seasons/ornaments.py [папка art] - пишет seasons/xmas/ornament-*.png и anim/ornament-pop/*."""

import math
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen,  # noqa: E402
                           QPolygonF, QRadialGradient)

ROOT = Path(__file__).resolve().parents[2]
ART = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stungkir" / "art"
S = 128                    # картинка 128×128 (на экране ~45 точек - хватает и для экранов с увеличением)
C = QPointF(S / 2, S / 2 + 8)
R = 44
KINDS = [("#e0382f", "#ff9a8a", "#6e0e0e"), ("#e2a92c", "#fff0a8", "#7a4f06"), ("#2f6fd6", "#a8d0ff", "#0f2a66")]
FRAMES = 6


def canvas():
    image = QImage(S, S, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    return image, p


def cap(p, center, angle=0.0, scale=1.0):
    p.save()
    p.translate(center)
    p.rotate(angle)
    p.scale(scale, scale)
    gold = QLinearGradient(-9, 0, 9, 0)
    gold.setColorAt(0, QColor("#8a5a10"))
    gold.setColorAt(0.4, QColor("#f7d886"))
    gold.setColorAt(1, QColor("#9a6a18"))
    p.setPen(QPen(QColor("#d8b45a"), 1.6))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(0, -15), 4.5, 5)                              # петелька
    p.setPen(QPen(QColor("#6a4410"), 0.8))
    p.setBrush(gold)
    p.drawRoundedRect(QRectF(-9, -11, 18, 11), 2, 2)
    for x in (-5, -1.5, 2, 5.5):                                         # рубчики
        p.drawLine(QPointF(x, -10), QPointF(x, -1))
    p.restore()


def pattern(p, kind):
    """Узор шарика: зигзаг, горошек или снежинка - белым, по форме шара."""
    white = QColor(255, 255, 255, 215)
    if kind == 0:
        zig = QPainterPath(QPointF(C.x() - R, C.y() + 2))
        for i in range(1, 11):
            zig.lineTo(C.x() - R + i * 2 * R / 10, C.y() + (-7 if i % 2 else 7) + 2)
        p.setPen(QPen(white, 4.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(zig)
        p.setPen(QPen(white, 2))
        for dy in (-12, 16):
            band = QPainterPath(QPointF(C.x() - R * 0.92, C.y() + dy))
            band.quadTo(QPointF(C.x(), C.y() + dy + 6), QPointF(C.x() + R * 0.92, C.y() + dy))
            p.drawPath(band)
    elif kind == 1:
        p.setPen(Qt.NoPen)
        p.setBrush(white)
        for row, dy in enumerate((-20, -4, 12, 26)):
            for k in range(-3, 4):
                x = C.x() + k * 12 + (6 if row % 2 else 0)
                y = C.y() + dy
                if math.hypot(x - C.x(), y - C.y()) < R - 6:
                    p.drawEllipse(QPointF(x, y), 2.6, 2.6)
    else:
        p.setPen(QPen(white, 2.6, Qt.SolidLine, Qt.RoundCap))
        for k in range(6):
            a = math.radians(k * 60 + 90)
            d = QPointF(math.cos(a), math.sin(a))
            n = QPointF(-d.y(), d.x())
            p.drawLine(C, C + d * 22)
            for t in (0.5, 0.78):
                root = C + d * (22 * t)
                p.drawLine(root, root + d * 5 + n * 5)
                p.drawLine(root, root + d * 5 - n * 5)


def ball(p, kind, scale=1.0, crack=0.0):
    base, light, dark = (QColor(c) for c in KINDS[kind])
    p.save()
    p.translate(C)
    p.scale(scale, scale)
    p.translate(-C)
    shadow = QRadialGradient(C + QPointF(4, R + 4), R)
    shadow.setColorAt(0, QColor(0, 0, 0, 90))
    shadow.setColorAt(1, QColor(0, 0, 0, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(shadow)
    p.drawEllipse(C + QPointF(4, R - 2), R * 0.9, 7)
    body = QRadialGradient(C + QPointF(-R * 0.35, -R * 0.4), R * 1.4)
    body.setColorAt(0, light)
    body.setColorAt(0.35, base)
    body.setColorAt(1, dark)
    p.setBrush(body)
    p.drawEllipse(C, R, R)
    pattern(p, kind)
    rim = QRadialGradient(C, R)                                          # стекло: край темнее, блик-окно
    rim.setColorAt(0.75, QColor(0, 0, 0, 0))
    rim.setColorAt(1, QColor(0, 0, 0, 70))
    p.setBrush(rim)
    p.drawEllipse(C, R, R)
    p.setBrush(QColor(255, 255, 255, 190))
    p.drawEllipse(C + QPointF(-R * 0.38, -R * 0.42), R * 0.2, R * 0.13)
    p.setBrush(QColor(255, 255, 255, 110))
    p.drawEllipse(C + QPointF(-R * 0.15, -R * 0.55), R * 0.07, R * 0.05)
    arc = QPainterPath()
    arc.arcMoveTo(QRectF(C.x() - R * 0.82, C.y() - R * 0.82, R * 1.64, R * 1.64), 200)
    arc.arcTo(QRectF(C.x() - R * 0.82, C.y() - R * 0.82, R * 1.64, R * 1.64), 200, 60)
    p.setPen(QPen(QColor(255, 255, 255, 70), 2.2, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawPath(arc)
    if crack > 0:                                                         # трещины перед тем, как лопнуть
        rng = random.Random(kind)
        p.setPen(QPen(QColor(255, 255, 255, int(220 * crack)), 1.4))
        for _ in range(5):
            a = rng.uniform(0, math.tau)
            path = QPainterPath(C + QPointF(-6, -4))
            for step in range(1, 4):
                path.lineTo(C + QPointF(math.cos(a + rng.uniform(-0.4, 0.4)), math.sin(a + rng.uniform(-0.4, 0.4)))
                            * (R * 0.33 * step * crack))
            p.drawPath(path)
    p.restore()
    cap(p, C + QPointF(0, -R * scale + 2))


def shard_shapes(kind):
    """Осколки: треугольники-кусочки шара с направлением разлёта."""
    rng = random.Random(40 + kind)
    shards = []
    for k in range(9):
        a = k / 9 * math.tau + rng.uniform(-0.2, 0.2)
        size = rng.uniform(7, 13)
        points = [QPointF(math.cos(a + d) * size * rng.uniform(0.6, 1.0), math.sin(a + d) * size * rng.uniform(0.6, 1.0))
                  for d in (0, 2.1, 4.2)]
        shards.append((a, rng.uniform(0.75, 1.0), rng.uniform(-180, 180), points))
    return shards


def shard(p, kind, center, points, angle, alpha):
    base, light, dark = (QColor(c) for c in KINDS[kind])
    p.save()
    p.translate(center)
    p.rotate(angle)
    grad = QLinearGradient(-8, -8, 8, 8)
    grad.setColorAt(0, light)
    grad.setColorAt(0.5, base)
    grad.setColorAt(1, dark)
    p.setOpacity(alpha)
    p.setPen(QPen(QColor(255, 255, 255, 120), 0.8))
    p.setBrush(grad)
    p.drawPolygon(QPolygonF(points))
    p.restore()


def glitter(p, rng, count, spread, alpha, center=None):
    center = center or C
    for _ in range(count):
        a, r = rng.uniform(0, math.tau), spread * math.sqrt(rng.random())
        point = center + QPointF(math.cos(a) * r, math.sin(a) * r * 0.75)
        color = QColor(rng.choice(["#fff3b0", "#f2c94c", "#ffffff", "#ffd27a"]))
        color.setAlphaF(alpha * rng.uniform(0.5, 1))
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        if rng.random() < 0.25:                                           # блёстка-звёздочка
            s = rng.uniform(2, 3.4)
            p.drawPolygon(QPolygonF([point + QPointF(0, -s), point + QPointF(s * 0.3, -s * 0.3), point + QPointF(s, 0),
                                     point + QPointF(s * 0.3, s * 0.3), point + QPointF(0, s), point + QPointF(-s * 0.3, s * 0.3),
                                     point + QPointF(-s, 0), point + QPointF(-s * 0.3, -s * 0.3)]))
        else:
            p.drawEllipse(point, 1.1, 1.1)


def popped(p, kind):
    """Что осталось: колпачок на боку, два-три осколка, блёстки."""
    rng = random.Random(70 + kind)
    glitter(p, rng, 26, R * 0.95, 0.85, C + QPointF(0, 8))
    shards = shard_shapes(kind)
    for a, _reach, spin, points in shards[:3]:
        shard(p, kind, C + QPointF(math.cos(a) * R * 0.55, math.sin(a) * R * 0.4 + 10), points, spin, 0.95)
    cap(p, C + QPointF(-4, 2), 70, 0.95)


def pop_frame(p, kind, frame):
    t = frame / (FRAMES - 1)
    if frame == 0:                                                        # вздрогнул, пошли трещины
        ball(p, kind, 1.06, 0.7)
        return
    rng = random.Random(90 + kind * 10 + frame)
    for a, reach, spin, points in shard_shapes(kind):                     # осколки летят и падают
        dist = R * (0.25 + 1.0 * reach * t)
        center = C + QPointF(math.cos(a) * dist, math.sin(a) * dist * 0.8 + 14 * t * t)
        shard(p, kind, center, points, spin * t, 1.0 - 0.55 * t)
    glitter(p, rng, int(18 + 30 * t), R * (0.4 + 0.8 * t), 1.0 - 0.3 * t, C + QPointF(0, 10 * t))
    cap(p, C + QPointF(-4 * t, -R + 2 + (R) * t), 70 * t, 1.0 - 0.05 * t)
    if frame <= 2:                                                       # вспышка
        flash = QRadialGradient(C, R * (0.8 + 0.6 * t))
        flash.setColorAt(0, QColor(255, 250, 220, int(200 * (1 - t))))
        flash.setColorAt(1, QColor(255, 250, 220, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(flash)
        p.drawEllipse(C, R * 1.4, R * 1.4)


def main():
    QGuiApplication.instance() or QGuiApplication([])
    flat = ART / "seasons" / "xmas"
    anim = ART / "anim" / "ornament-pop"
    flat.mkdir(parents=True, exist_ok=True)
    anim.mkdir(parents=True, exist_ok=True)
    for kind in range(3):
        image, p = canvas()
        ball(p, kind)
        p.end()
        image.save(str(flat / f"ornament-{kind}.png"))
        image, p = canvas()
        popped(p, kind)
        p.end()
        image.save(str(flat / f"ornament-popped-{kind}.png"))
        for frame in range(FRAMES):
            image, p = canvas()
            pop_frame(p, kind, frame)
            p.end()
            image.save(str(anim / f"ornament-{kind}-pop_{frame:02d}.png"))


if __name__ == "__main__":
    main()
