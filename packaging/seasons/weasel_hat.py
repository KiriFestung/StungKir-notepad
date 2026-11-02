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


SCALE = 1.18          # шапка чуть крупнее «настоящей»: в колесе ласка маленькая, а шапку должно быть видно


def hat(p, point, flap=0.0, scale=SCALE):
    """Колпак по точкам рисунка: point(x, y) - где точка (x, y) рисунка ласки оказалась в кадре.
    Опушка обхватывает голову дугой и закрывает ухо, колпак поднимается над макушкой и свисает назад,
    к шее (помпон ниже макушки - край кадра его не режет); flap - на сколько качнулся помпон."""
    raw = point

    def point(x, y):                                        # увеличиваем вокруг макушки
        return raw(410 + (x - 410) * scale, 18 + (y - 18) * scale)
    red = QLinearGradient(point(440, 20), point(350, 30))
    red.setColorAt(0, QColor("#e8473e"))
    red.setColorAt(0.6, QColor("#b8262a"))
    red.setColorAt(1, QColor("#8a1717"))
    pen = QPen(W.OCHRE, W.LINE)
    pen.setJoinStyle(Qt.RoundJoin)
    tail = QPainterPath(point(404, -11))                    # свисающий хвост колпака - сзади, под макушкой
    tail.cubicTo(point(378, -16), point(350, -2 + flap * 0.4), point(344, 26 + flap))
    tail.cubicTo(point(356, 22 + flap), point(372, 2), point(396, 2))
    tail.closeSubpath()
    crown = QPainterPath(point(370, 32))                    # сам колпак над головой
    crown.cubicTo(point(372, -2), point(396, -16), point(414, -13))
    crown.cubicTo(point(432, -10), point(448, 6), point(450, 28))
    crown.closeSubpath()
    p.setPen(pen)
    p.setBrush(red)
    p.drawPath(tail)
    p.drawPath(crown)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 55))                         # складка: хвост уходит за колпак
    fold = QPainterPath(point(398, -14))
    fold.cubicTo(point(386, -12), point(378, -2), point(376, 8))
    fold.cubicTo(point(386, 0), point(394, -6), point(404, -8))
    p.drawPath(fold)
    shine = QPainterPath(point(420, -8))                   # блик на ткани
    shine.cubicTo(point(434, -8), point(442, 4), point(444, 18))
    p.setPen(QPen(QColor(255, 200, 190, 130), 3.2, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawPath(shine)
    rim = QPainterPath(point(364, 36))                      # опушка - дугой по голове, через ухо
    rim.cubicTo(point(382, 14), point(428, 10), point(452, 30))
    for width, color in ((17, W.OCHRE), (13, FUR)):
        p.setPen(QPen(color, width * scale, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(rim)
    p.setPen(QPen(QColor(196, 210, 228), 3.4, Qt.SolidLine, Qt.RoundCap))   # тень в мехе снизу
    p.drawPath(rim.translated(0, 3.2 * scale))
    for k in range(7):                                       # ворс опушки
        t = (k + 0.5) / 7
        spot = rim.pointAtPercent(t)
        p.setPen(QPen(QColor(205, 218, 234), 1.6, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(spot + QPointF(-2, -3), spot + QPointF(1, 1))
    tip = point(344, 30 + flap)
    p.setPen(QPen(W.OCHRE, W.LINE))
    p.setBrush(FUR)
    p.drawEllipse(tip, 11 * scale, 11 * scale)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(200, 214, 230))
    p.drawEllipse(tip + QPointF(3, 4) * scale, 6 * scale, 5 * scale)
    p.setBrush(FUR)
    p.drawEllipse(tip + QPointF(-2, -2) * scale, 7 * scale, 7 * scale)


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

    def save(pair, path, drop=0):
        """Кадр после чистки каймы + слой шапки; drop - опустить всё на столько точек (прыжок пониже)."""
        frame, layer = pair
        frame.save(str(path))
        clean = polish(Image.open(path), 2 / 3)
        layer.save(str(path))
        done = Image.alpha_composite(clean, Image.open(path).convert("RGBA"))
        if drop:
            moved = Image.new("RGBA", done.size, (0, 0, 0, 0))
            moved.paste(done, (0, drop))
            done = moved
        done.save(path, optimize=True)

    def run_hat(p, bend, i):                                    # на бегу помпон подпрыгивает
        hat(p, bent(bend), 6 * math.sin(2 * math.pi * i / W.RUN_FRAMES))

    def cheer_hat(p, bend, i):                                  # в прыжке помпон отстаёт и потом догоняет
        t = i / (W.CHEER_FRAMES - 1)
        hat(p, bent(bend), 9 * math.sin(math.pi * t))
    for i, pair in enumerate(W.run_frames(body, run_hat)):
        save(pair, run_dir / f"weasel-run_{i:02d}.png")
    for i, pair in enumerate(W.cheer_frames(body, cheer_hat)):          # на пике голова у края кадра - чуть ниже
        drop = round(16 * math.sin(math.pi * i / (W.CHEER_FRAMES - 1)))
        save(pair, cheer_dir / f"weasel-cheer_{i:02d}.png", drop)
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
