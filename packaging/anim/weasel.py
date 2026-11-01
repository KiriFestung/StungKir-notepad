# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Кадры ласки из её же рисунка (packaging/art-src/weasel.png): лапы у рисунка срезаются, тело гнётся
(спина дугой - вытянулась в струну), морда, уши и хвост - те же. Лапы дорисовываются в том же стиле
и двигаются по-настоящему: бег прыжками, как у живых ласок, и прыжок радости.
python3 packaging/anim/weasel.py [папка art] - перезаписывает anim/weasel-run/*, anim/weasel-cheer/*."""

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QPainter, QPainterPath,  # noqa: E402
                           QPainterPathStroker, QPen, QTransform)

BODY = QColor(72, 51, 120)
FAR = QColor(57, 40, 97)                # дальние лапы - в тени
CREAM = QColor(251, 236, 207)
OCHRE = QColor(214, 162, 52)
LINE = 4.0
W, H = 480, 300                         # холст кадра в точках рисунка (рисунок 480×257 стоит внизу)
TOP = H - 257                           # сдвиг рисунка вниз на холсте
GROUND = H - 5
HIP, SHOULDER = 150.0, 322.0            # где у рисунка бедро и плечо (по x)
RUN_FRAMES, CHEER_FRAMES = 12, 12
SS = 2                                  # рисуем вдвое крупнее и уменьшаем - края мягче


def cut(x):
    """Линия живота: ниже неё у рисунка лапы, их срезаем (хвост слева не трогаем)."""
    points = ((0, 400), (46, 400), (47, 186), (58, 176), (110, 172), (200, 168), (240, 179), (276, 185),
              (340, 192), (372, 160), (402, 108), (480, 108))
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / max(1e-6, x1 - x0)
    return 400


def body_image(sprite):
    """Рисунок без лап: ниже линии живота - прозрачно."""
    image = sprite.convertToFormat(QImage.Format_ARGB32)
    for x in range(image.width()):
        for y in range(max(0, int(cut(x + 0.5)) + 1), image.height()):
            image.setPixelColor(x, y, QColor(0, 0, 0, 0))
    return image


class Bend:
    """Изгиб тела: chord - бедро-плечо по прямой, arch - на сколько спина выгнута вверх.
    Круп с хвостом и грудь с головой наклоняются вслед за дугой, а не просто сдвигаются."""

    def __init__(self, chord, arch):
        self.span = SHOULDER - HIP
        self.k = chord / self.span
        self.arch = arch

    def x(self, x):
        if x <= HIP:
            return x
        if x <= SHOULDER:
            return HIP + (x - HIP) * self.k
        return HIP + self.span * self.k + (x - SHOULDER)

    def dy(self, x):
        slope = self.arch * math.pi / self.span
        if x <= HIP:
            return slope * (HIP - x) * 0.55                       # круп и хвост опускаются
        if x <= SHOULDER:
            return -self.arch * math.sin(math.pi * (x - HIP) / self.span)
        return slope * (x - SHOULDER) * 0.25                      # голова чуть клюёт вниз

    def point(self, x, y):
        return QPointF(self.x(x), y + self.dy(x))


def limb(root, angle, length, upper, lower, bend):
    """Лапа на двух косточках, сгиб в сторону bend. Возвращает (форма, кончик)."""
    paw = root + QPointF(math.sin(angle), math.cos(angle)) * length
    d = paw - root
    reach = max(abs(upper - lower) + 1, min(upper + lower - 0.5, math.hypot(d.x(), d.y())))
    cos_a = (upper * upper + reach * reach - lower * lower) / (2 * upper * reach)
    a = math.acos(max(-1.0, min(1.0, cos_a)))
    base = math.atan2(d.y(), d.x())
    joint = root + QPointF(math.cos(base + bend * a), math.sin(base + bend * a)) * upper
    tip = root + QPointF(math.cos(base), math.sin(base)) * reach
    shape = QPainterPath()
    for start, end, width in ((root, joint, 40), (joint, tip, 24)):
        bone = QPainterPath(start)
        bone.lineTo(end)
        stroker = QPainterPathStroker()
        stroker.setWidth(width)
        stroker.setCapStyle(Qt.RoundCap)
        shape = shape.united(stroker.createStroke(bone))
    foot = QPainterPath()
    foot.addEllipse(tip + QPointF(9, 2), 18, 10)
    return shape.united(foot).simplified(), tip


def build(chord, arch, tilt, hind, front):
    """Геометрия кадра: изгиб, поворот тела (tilt, + нос вверх) и четыре лапы.
    hind/front - ((угол, длина) ближней, (угол, длина) дальней); угол от вертикали, + вперёд."""
    bend = Bend(chord, arch)
    middle = (bend.x(HIP) + bend.x(SHOULDER)) / 2
    turn = QTransform()
    turn.translate(W / 2 - 6, TOP + 150)
    turn.rotateRadians(-tilt)
    turn.translate(-middle, -TOP - 150)
    legs = {}
    for index, side, shift in ((1, "far", QPointF(-14, -6)), (0, "near", QPointF(0, 0))):
        angle, length = hind[index]
        root = bend.point(HIP - 10, TOP + 150) + shift
        legs[(side, "hind")] = limb(root, angle - tilt, 100 * length, 50, 54, -1)
        angle, length = front[index]
        root = bend.point(SHOULDER - 10, TOP + 158) + shift
        legs[(side, "front")] = limb(root, angle - tilt, 96 * length, 46, 52, 1)
    return bend, turn, legs


def paws(turn, legs, keys):
    return [turn.map(legs[key][1]).y() for key in keys]


def canvas(turn, lift, height):
    """Холст кадра и кисть с теми же сдвигами и поворотом, что у тела."""
    image = QImage(W * SS, height * SS, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(SS, SS)
    p.translate(0, lift + height - H)
    p.setTransform(turn, True)
    return image, p


def shrink(image, height):
    return image.scaled(W * 2 // 3, height * 2 // 3, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def render(body, bend, turn, legs, lift, height=H, overlay=None):
    """Кадр: дальние лапы, тело (изогнутое полосками по 1 точке), контур живота, ближние лапы.
    overlay(painter, bend) - что дорисовать поверх (шапка к празднику): отдельным слоем, его отдают вторым,
    чтобы чистка белой каймы (polish.py) не тронула белое у этой дорисовки."""
    image, p = canvas(turn, lift, height)
    pen = QPen(OCHRE, LINE * 2)
    pen.setJoinStyle(Qt.RoundJoin)

    def draw_leg(key, fill):
        shape, tip = legs[key]
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(shape)
        p.setPen(Qt.NoPen)
        p.setBrush(fill)
        p.drawPath(shape)
        p.save()
        p.setClipPath(shape, Qt.IntersectClip)
        p.setBrush(CREAM if fill == BODY else CREAM.darker(115))
        p.drawEllipse(tip + QPointF(10, 6), 24, 12)
        p.restore()

    xs = [x * 2.0 for x in range(30, 202)]
    belly = QPainterPath(bend.point(xs[0], TOP + cut(xs[0])))
    for x in xs[1:]:
        belly.lineTo(bend.point(x, TOP + cut(x)))
    under = QPainterPath(belly)                                  # всё ниже живота - место ближних лап
    under.lineTo(bend.point(xs[-1], 900))
    under.lineTo(bend.point(xs[0], 900))
    under.closeSubpath()

    draw_leg(("far", "hind"), FAR)
    draw_leg(("far", "front"), FAR)
    p.setPen(QPen(OCHRE, LINE * 1.2, Qt.SolidLine, Qt.RoundCap))     # контур по срезу живота
    p.setBrush(Qt.NoBrush)
    p.drawPath(belly)
    for x in range(body.width()):                                  # тело полосками: каждая на свою высоту
        target = bend.point(x, TOP)
        width = max(1.0, bend.x(x + 1) - bend.x(x))
        p.drawImage(QRectF(target.x(), target.y(), width + 0.6, body.height()), body,
                    QRectF(x, 0, 1, body.height()))
    p.save()
    p.setClipPath(under.translated(0, -2), Qt.IntersectClip)
    draw_leg(("near", "hind"), BODY)
    draw_leg(("near", "front"), BODY)
    p.restore()
    p.end()
    if overlay is None:
        return shrink(image, height)
    layer, q = canvas(turn, lift, height)
    overlay(q, bend)
    q.end()
    return shrink(image, height), shrink(layer, height)


def gallop(t):
    """Бег прыжками, t от 0 до 1: 0 - собралась (спина дугой, задние лапы у передних), 0.5 - летит вытянувшись."""
    a = math.cos(2 * math.pi * t)
    arch = 6 + 22 * max(0.0, a) - 3 * max(0.0, -a)
    chord = 154 - 20 * a
    tilt = 0.1 * math.sin(2 * math.pi * t)
    lag = 0.06                                                    # дальняя пара чуть позже - живее

    def hind_on(s):
        return s % 1 < 0.32 or s % 1 > 0.96

    def front_on(s):
        return 0.62 < s % 1 < 0.98

    def hind(s):
        c = math.cos(2 * math.pi * s)
        return 0.85 * c - 0.1, 1.0 if hind_on(s) else 0.72 + 0.2 * max(0.0, -c)

    def front(s):
        c = math.cos(2 * math.pi * s)
        return -0.8 * c + 0.1, 1.0 if front_on(s) else 0.7 + 0.28 * max(0.0, -c)
    bend, turn, legs = build(chord, arch, tilt, (hind(t), hind(t - lag)), (front(t), front(t - lag)))
    stance = [key for key, on in ((("near", "hind"), hind_on(t)), (("far", "hind"), hind_on(t - lag)),
                                  (("near", "front"), front_on(t)), (("far", "front"), front_on(t - lag))) if on]
    return bend, turn, legs, stance


def run_frames(body, overlay=None):
    shapes = [gallop(i / RUN_FRAMES) for i in range(RUN_FRAMES)]
    known = [GROUND - max(paws(turn, legs, stance)) if stance else None for _b, turn, legs, stance in shapes]
    images = []
    for i, (bend, turn, legs, _stance) in enumerate(shapes):
        lift = known[i]
        if lift is None:                                          # полёт: выше соседних опор
            before = next(known[(i - k) % RUN_FRAMES] for k in range(1, RUN_FRAMES) if known[(i - k) % RUN_FRAMES] is not None)
            after = next(known[(i + k) % RUN_FRAMES] for k in range(1, RUN_FRAMES) if known[(i + k) % RUN_FRAMES] is not None)
            lift = (before + after) / 2 - 16
        images.append(render(body, bend, turn, legs, lift, overlay=overlay and (lambda q, b, i=i: overlay(q, b, i))))
    return images


def stand_frame(sprite):
    """Стоит - сам рисунок без изменений, на том же холсте, что и бег."""
    image = QImage(W * 2 // 3, H * 2 // 3, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(2 / 3, 2 / 3)
    p.drawImage(QRectF(0, GROUND - 254, 480, 257), sprite)
    p.end()
    return image


def cheer_frames(body, overlay=None):
    """Прыжок радости: присела, свечой вверх носом к небу, приземлилась."""
    images = []
    for i in range(CHEER_FRAMES):
        t = i / (CHEER_FRAMES - 1)
        crouch = max(0.0, 1 - t / 0.2) if t < 0.2 else max(0.0, (t - 0.84) / 0.16)
        air = math.sin(math.pi * min(1.0, max(0.0, (t - 0.16) / 0.7)))
        tilt = 0.32 * air - (0.12 * air if t > 0.55 else 0)
        bend, turn, legs = build(176 - 26 * crouch, 4 + 20 * crouch - 8 * air, tilt,
                                 ((0.45 * crouch - 0.6 * air, 1 - 0.25 * crouch), (0.4 * crouch - 0.65 * air, 1 - 0.25 * crouch)),
                                 ((0.9 * air - 0.15 * crouch, 1 - 0.3 * air), (1.1 * air, 1 - 0.32 * air)))
        lowest = max(paws(turn, legs, list(legs)))
        images.append(render(body, bend, turn, legs, GROUND - lowest - 80 * air, 400,   # выше - есть куда прыгать
                             overlay=overlay and (lambda q, b, i=i: overlay(q, b, i))))
    return images


def main(art):
    """Кадры - из исходного плоского рисунка (packaging/art-src/weasel.png), потом объём (polish.py)."""
    from PIL import Image
    from polish import polish
    app = QGuiApplication.instance() or QGuiApplication([])
    art = Path(art)
    sprite = QImage(str(Path(__file__).resolve().parents[1] / "art-src" / "weasel.png"))
    body = body_image(sprite)
    run_dir, cheer_dir = art / "anim" / "weasel-run", art / "anim" / "weasel-cheer"
    for old in list(run_dir.glob("weasel-*.png")) + list(cheer_dir.glob("weasel-cheer_*.png")):
        old.unlink()

    def save(image, path):
        image.save(str(path))
        polish(Image.open(path), 2 / 3).save(path, optimize=True)
    for i, image in enumerate(run_frames(body)):
        save(image, run_dir / f"weasel-run_{i:02d}.png")
    save(stand_frame(sprite), run_dir / "weasel-stand.png")
    for i, image in enumerate(cheer_frames(body)):
        save(image, cheer_dir / f"weasel-cheer_{i:02d}.png")
    del app


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "stungkir" / "art")
