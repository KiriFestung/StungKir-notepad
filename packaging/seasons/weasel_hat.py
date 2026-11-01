# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ласка-таймер в новогодней шапке: те же кадры бега и прыжка (packaging/anim/weasel.py из рисунка автора),
поверх - красный колпак с белой опушкой и помпоном. Шапка сидит на голове при любом изгибе тела и
на бегу машет помпоном. Шапка - отдельным слоем поверх готового кадра: чистка белой каймы её не трогает.
python3 packaging/seasons/weasel_hat.py [папка art] - пишет anim/weasel-run-xmas, anim/weasel-cheer-xmas."""

import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "anim"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen  # noqa: E402

import weasel as W  # noqa: E402

FUR = QColor("#f4f7fb")


SCALE = 1.35          # шапка чуть крупнее «настоящей»: в колесе ласка маленькая, а шапку должно быть видно


def hat(p, point, flap=0.0):
    """Колпак по точкам рисунка: point(x, y) - где точка (x, y) рисунка ласки оказалась в кадре."""
    raw = point

    def point(x, y):                                        # увеличиваем вокруг макушки, опушка - на лбу
        return raw(418 + (x - 418) * SCALE, 24 + (y - 24) * SCALE)
    a, b = point(380, 14), point(456, 22)
    tip = point(328, -14 + flap)
    shape = QPainterPath(a)
    shape.cubicTo(a + QPointF(-4, -38) * SCALE, point(350, -34 + flap * 0.5), tip)
    shape.cubicTo(point(352, -22 + flap * 0.5), a + QPointF(40, -30) * SCALE, b)
    shape.closeSubpath()
    red = QLinearGradient(a, tip)
    red.setColorAt(0, QColor("#e3423a"))
    red.setColorAt(1, QColor("#9c1a1a"))
    p.setPen(QPen(W.OCHRE, W.LINE))
    p.setBrush(red)
    p.drawPath(shape)
    shine = QPainterPath(a + QPointF(8, -10))                  # блик на ткани
    shine.cubicTo(a + QPointF(6, -26), point(356, -26 + flap * 0.5), point(342, -16 + flap * 0.7))
    p.setPen(QPen(QColor(255, 190, 180, 120), 3, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawPath(shine)
    rim = QPainterPath(a + QPointF(-4, 4) * SCALE)
    rim.cubicTo(a + QPointF(20, -8) * SCALE, b + QPointF(-20, -10) * SCALE, b + QPointF(4, 2) * SCALE)
    p.setPen(QPen(W.OCHRE, 19 * SCALE, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(rim)
    p.setPen(QPen(FUR, 15 * SCALE, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(rim)
    p.setPen(QPen(QColor(200, 214, 230), 4, Qt.SolidLine, Qt.RoundCap))   # тень в мехе снизу
    p.drawPath(rim.translated(0, 4))
    p.setPen(QPen(W.OCHRE, W.LINE))
    p.setBrush(FUR)
    p.drawEllipse(tip, 13 * SCALE, 13 * SCALE)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(200, 214, 230))
    p.drawEllipse(tip + QPointF(3, 4) * SCALE, 7 * SCALE, 6 * SCALE)
    p.setBrush(FUR)
    p.drawEllipse(tip + QPointF(-2, -2) * SCALE, 8 * SCALE, 8 * SCALE)


def bent(bend):
    return lambda x, y: bend.point(x, W.TOP + y)


def main(art):
    from PIL import Image
    from polish import polish
    app = QGuiApplication.instance() or QGuiApplication([])
    art = Path(art)
    sprite = QImage(str(HERE.parents[0] / "art-src" / "weasel.png"))
    body = W.body_image(sprite)
    run_dir, cheer_dir = art / "anim" / "weasel-run-xmas", art / "anim" / "weasel-cheer-xmas"
    for folder in (run_dir, cheer_dir):
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.png"):
            old.unlink()

    def save(pair, path):
        frame, layer = pair
        frame.save(str(path))
        clean = polish(Image.open(path), 2 / 3)
        layer.save(str(path))
        Image.alpha_composite(clean, Image.open(path).convert("RGBA")).save(path, optimize=True)

    def run_hat(p, bend, i):                                    # на бегу помпон подпрыгивает
        hat(p, bent(bend), 7 * math.sin(2 * math.pi * i / W.RUN_FRAMES))

    def cheer_hat(p, bend, i):                                  # в прыжке шапку сдувает назад и вниз
        t = i / (W.CHEER_FRAMES - 1)
        hat(p, bent(bend), 10 * math.sin(math.pi * t))
    for i, pair in enumerate(W.run_frames(body, run_hat)):
        save(pair, run_dir / f"weasel-run_{i:02d}.png")
    for i, pair in enumerate(W.cheer_frames(body, cheer_hat)):
        save(pair, cheer_dir / f"weasel-cheer_{i:02d}.png")
    # стоит - сам рисунок, шапка по тем же точкам рисунка
    stand = W.stand_frame(sprite)
    layer = QImage(W.W * W.SS, W.H * W.SS, QImage.Format_ARGB32_Premultiplied)
    layer.fill(Qt.transparent)
    p = QPainter(layer)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(W.SS, W.SS)
    hat(p, lambda x, y: QPointF(x, W.GROUND - 254 + y))
    p.end()
    save((stand, W.shrink(layer, W.H)), run_dir / "weasel-stand.png")
    del app


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "stungkir" / "art")
