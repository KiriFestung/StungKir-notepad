# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Монетка-пряник (Рождество): круглое печенье с волнистым краем, тесто с порами и румяным краем,
рисунок - белой глазурью с бликом и тенью. Стороны: ёлка (с сахарными бусинами) и снежинка.
python3 packaging/seasons/gingerbread.py [папка] - пишет coin-heads.png (ёлка) и coin-tails.png (снежинка)
в stungkir/art/seasons/xmas."""

import math
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402
from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen,  # noqa: E402
                           QRadialGradient)

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stungkir" / "art" / "seasons" / "xmas"
S = 512
C = S / 2
ICING = QColor("#fbf6ec")


def layer():
    image = QImage(S, S, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    return image, p


def to_pil(image):
    image = image.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombuffer("RGBA", (S, S), bytes(image.constBits()), "raw", "RGBA", 0, 1).copy()


def cookie_path(radius=246, waves=26, depth=6):
    path = QPainterPath()
    for k in range(361):
        a = math.radians(k)
        r = radius + depth * math.cos(a * waves)
        point = QPointF(C + r * math.cos(a), C + r * math.sin(a))
        path.moveTo(point) if k == 0 else path.lineTo(point)
    path.closeSubpath()
    return path


def dough():
    """Тесто: светлее в середине, румяный край, поры и мука - шумом."""
    image, p = layer()
    grad = QRadialGradient(QPointF(C - 40, C - 50), 300)
    grad.setColorAt(0, QColor("#c98848"))
    grad.setColorAt(0.65, QColor("#a86630"))
    grad.setColorAt(0.9, QColor("#7d4519"))
    grad.setColorAt(1, QColor("#5e3110"))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawPath(cookie_path())
    p.end()
    pil = to_pil(image)
    a = np.asarray(pil).astype(float)
    rng = np.random.default_rng(12)
    grain = np.asarray(Image.fromarray((rng.random((S, S)) * 255).astype("uint8")).filter(
        ImageFilter.GaussianBlur(1.2))).astype(float) / 255 - 0.5
    pores = rng.random((S, S)) > 0.9965
    a[..., :3] *= (1 + grain[..., None] * 0.35)
    a[..., :3][pores] *= 0.55
    yy, xx = np.mgrid[0:S, 0:S]
    rim = np.clip((np.hypot(xx - C, yy - C) - 222) / 24, 0, 1)            # бортик чуть выпуклый: блик сверху слева
    light = np.clip(((C - xx) + (C - yy)) / (2 * C), -1, 1)
    a[..., :3] *= (1 + rim[..., None] * light[..., None] * 0.25)
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"), "RGBA")


def icing(draw):
    """Глазурь: тень (размыта), белая линия, блик. draw(painter, width) - рисует узор."""
    shadow, p = layer()
    p.translate(3, 4)
    draw(p, QColor(70, 30, 8, 150), 14)
    p.end()
    shadow = to_pil(shadow).filter(ImageFilter.GaussianBlur(3))
    body, p = layer()
    draw(p, ICING, 12)
    p.end()
    shine, p = layer()
    p.translate(-1.6, -1.8)
    draw(p, QColor(255, 255, 255, 230), 4)
    p.end()
    shine = to_pil(shine)
    body = to_pil(body)
    keep = np.asarray(body)[..., 3:4] / 255.0                             # блик - только на глазури
    sa = np.asarray(shine).astype(float)
    sa[..., 3:4] *= keep
    shine = Image.fromarray(sa.astype("uint8"), "RGBA")
    return shadow, body, shine


def stroke(p, color, width, path):
    p.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)


def dot(p, color, width, point, r):
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawEllipse(point, r + (width - 9) * 0.5, r + (width - 9) * 0.5)


def border(p, color, width):
    """Кайма: волна глазурью по краю и точки."""
    path = QPainterPath()
    for k in range(361):
        a = math.radians(k)
        r = 222 + 6 * math.sin(a * 24)
        point = QPointF(C + r * math.cos(a), C + r * math.sin(a))
        path.moveTo(point) if k == 0 else path.lineTo(point)
    stroke(p, color, width * 0.8, path)
    for k in range(24):
        a = math.radians(k * 15 + 7.5)
        dot(p, color, width, QPointF(C + 202 * math.cos(a), C + 202 * math.sin(a)), 4.5)


def tree(p, color, width):
    top, base, half = 112, 352, 112
    path = QPainterPath(QPointF(C, top))
    pts_right, pts_left = [], []
    for i in range(3):
        y1 = top + (base - top) * (i + 1) / 3
        w = half * (i + 1) / 3
        pts_right += [(C + w, y1), (C + w * 0.42, y1 - 6)] if i < 2 else [(C + w, y1)]
        pts_left += [(C - w, y1), (C - w * 0.42, y1 - 6)] if i < 2 else [(C - w, y1)]
    for x, y in pts_right:
        path.lineTo(x, y)
    for x, y in reversed(pts_left):
        path.lineTo(x, y)
    path.closeSubpath()
    stroke(p, color, width, path)
    for i, y in enumerate((178, 248, 318)):                    # гирлянда - волнами
        w = half * (i + 1) / 3 * 0.8
        garland = QPainterPath(QPointF(C - w, y - 14))
        garland.quadTo(QPointF(C, y + 14), QPointF(C + w, y - 22))
        stroke(p, color, width * 0.75, garland)
    trunk = QPainterPath(QPointF(C - 16, base))
    trunk.lineTo(C - 16, base + 34)
    trunk.lineTo(C + 16, base + 34)
    trunk.lineTo(C + 16, base)
    stroke(p, color, width, trunk)
    star = QPainterPath()
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        r = 30 if k % 2 == 0 else 13
        point = QPointF(C + r * math.cos(a), top - 14 + r * math.sin(a))
        star.moveTo(point) if k == 0 else star.lineTo(point)
    star.closeSubpath()
    p.setPen(QPen(color, width * 0.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(color)
    p.drawPath(star)


def snowflake(p, color, width):
    for k in range(6):
        a = math.radians(k * 60 - 90)
        d = QPointF(math.cos(a), math.sin(a))
        n = QPointF(-d.y(), d.x())
        center = QPointF(C, C)
        arm = QPainterPath(center + d * 26)
        arm.lineTo(center + d * 160)
        stroke(p, color, width, arm)
        for t, length in ((0.45, 46), (0.72, 32)):
            root = center + d * (160 * t)
            for side in (-1, 1):
                twig = QPainterPath(root)
                twig.lineTo(root + d * (length * 0.75) + n * (side * length * 0.75))
                stroke(p, color, width * 0.8, twig)
        dot(p, color, width, center + d * 176, 8)
        between = math.radians(k * 60 - 60)
        dot(p, color, width, QPointF(C + 112 * math.cos(between), C + 112 * math.sin(between)), 4)
    hexagon = QPainterPath()
    for k in range(7):
        a = math.radians(k * 60 - 90)
        point = QPointF(C + 24 * math.cos(a), C + 24 * math.sin(a))
        hexagon.moveTo(point) if k == 0 else hexagon.lineTo(point)
    stroke(p, color, width * 0.8, hexagon)


def beads(image, points):
    """Сахарные бусины: красные и золотые, круглые с бликом."""
    q = QImage(image.tobytes(), S, S, QImage.Format_RGBA8888).copy()
    p = QPainter(q)
    p.setRenderHint(QPainter.Antialiasing)
    for i, (x, y) in enumerate(points):
        base = QColor("#d8302c") if i % 2 == 0 else QColor("#e8b33a")
        grad = QRadialGradient(QPointF(x - 3, y - 3), 11)
        grad.setColorAt(0, base.lighter(160))
        grad.setColorAt(0.5, base)
        grad.setColorAt(1, base.darker(170))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(60, 25, 5, 120))
        p.drawEllipse(QPointF(x + 2, y + 3), 8, 8)
        p.setBrush(grad)
        p.drawEllipse(QPointF(x, y), 8, 8)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(QPointF(x - 3, y - 3), 2.2, 2.2)
    p.end()
    return to_pil(q)


def side(draw, bead_points=()):
    out = dough()
    for part in (icing(border), icing(draw)):
        for piece in part:
            out = Image.alpha_composite(out, piece)
    if bead_points:
        out = beads(out, bead_points)
    return out


def main():
    QGuiApplication.instance() or QGuiApplication([])
    OUT.mkdir(parents=True, exist_ok=True)
    side(tree, [(C - 112, 352), (C + 112, 352), (C - 75, 271), (C + 75, 271), (C - 37, 191), (C + 37, 191),
                (C - 20, 230), (C + 34, 300), (C - 44, 316)]).save(OUT / "coin-heads.png")
    side(snowflake).save(OUT / "coin-tails.png")


if __name__ == "__main__":
    main()
