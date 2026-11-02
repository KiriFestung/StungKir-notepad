# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""«Слепи снеговика» (Рождество). Дневной снеговик растёт за окном комнаты от дневной цели: 10% - ком,
40/60/80% - шары, 100% - лицо и морковка, 120% - шарф, 150% - ведро, 200% - метла и пуговицы, 250% -
снегирь на руке. На 300% он готов - и его сносит то машина, то снегоуборщик, то дети на санках: остаётся
сугроб с ведром, и лепится следующий («снеговиков за день»). Утром - пустой двор.
Снеговик сезона растёт за все слова с 15 декабря по 14 января: каждые 1000 слов - новая вещь.
Итог каждой зимы лежит в StungKir/.stungkir/snowmen.json. Здесь - расчёты, рисование и вкладка «Антистресса»."""

import json
import math
import random
from datetime import date, timedelta

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from ..core import config as C
from ..core import seasons
from ..core.i18n import tr
from ..core.textutil import plural

FULL = 300                              # процентов цели на одного снеговика
STAGES = [(10, "снежный ком"), (40, "нижний шар"), (60, "средний шар"), (80, "голова"), (100, "лицо и морковка"),
          (120, "шарф"), (150, "шапка-ведро"), (200, "метла и пуговицы"), (250, "снегирь на руке"), (300, "готов!")]
VEHICLES = ("car", "plow", "sled")
SEASON_STEP = 1000                      # слов на одну вещь снеговика сезона
SEASON_ITEMS = ["пуговицы", "руки-веточки", "лицо и морковка", "шарф", "варежки", "шапка-ведро", "метла",
                "снегирь", "фонарик", "гирлянда", "ёлочка рядом", "звезда на ведре"]
FILE = "snowmen.json"


# ---------- расчёты ----------
def progress(written, goal):
    """(сколько снеговиков уже снесено сегодня, проценты нынешнего: 0..300)."""
    goal = goal if goal and goal > 0 else C.DAILY_GOAL or 500
    percent = max(0.0, written) / goal * 100
    done = int(percent // FULL)
    return done, percent - done * FULL


def next_stage(percent, written, goal):
    """(что будет дальше, сколько слов до него) или None."""
    goal = goal if goal and goal > 0 else C.DAILY_GOAL or 500
    base = written - percent * goal / 100
    for need, name in STAGES:
        if percent < need:
            return name, max(1, math.ceil(base + need * goal / 100 - written))
    return None


def vehicle(day, index):
    """Кто снесёт снеговика: то машина, то снегоуборщик, то санки - одинаково при каждом запуске."""
    return VEHICLES[random.Random(f"{day}-{index}").randrange(len(VEHICLES))]


def season_bounds(today):
    """(начало, конец) нынешней зимы: 15 декабря - 14 января."""
    year = today.year if today.month == 12 else today.year - 1
    return date(year, 12, 15), date(year + 1, 1, 14)


def season_words(stats, today, live_today=None):
    start, end = season_bounds(today)
    total, day = 0, start
    while day <= min(end, today):
        key = day.isoformat()
        total += live_today if (day == today and live_today is not None) else max(0, int(stats.get(key, 0) or 0))
        day += timedelta(days=1)
    return total


def season_items(words):
    return SEASON_ITEMS[:min(len(SEASON_ITEMS), int(words // SEASON_STEP))]


def season_key(today):
    start, _end = season_bounds(today)
    return f"{start.year}-{start.year + 1}"


def load_winters():
    try:
        data = json.loads((C.ROOT / C.SERVICE_DIR / FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def remember(today, words, snowmen_today):
    """Записать итог зимы: слова сезона и сколько снеговиков снесли за каждый день."""
    from ..core.storage import write_atomic
    winters = load_winters()
    key = season_key(today)
    winter = winters.get(key) if isinstance(winters.get(key), dict) else {}
    days = winter.get("days") if isinstance(winter.get("days"), dict) else {}
    if winter.get("words") == words and days.get(today.isoformat(), 0) >= snowmen_today:
        return
    days[today.isoformat()] = max(days.get(today.isoformat(), 0), snowmen_today)
    winters[key] = {"words": words, "items": len(season_items(words)), "days": days}
    try:
        path = C.ROOT / C.SERVICE_DIR / FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(path, json.dumps(winters, ensure_ascii=False, indent=1).encode("utf-8"))
    except OSError:
        pass


def items_for(percent):
    """Что уже есть у дневного снеговика."""
    have = set()
    for need, key in ((100, "face"), (100, "arms"), (120, "scarf"), (150, "bucket"), (200, "broom"),
                      (200, "buttons"), (250, "bird")):
        if percent >= need:
            have.add(key)
    return have


SEASON_KEYS = {"пуговицы": "buttons", "руки-веточки": "arms", "лицо и морковка": "face", "шарф": "scarf",
               "варежки": "mittens", "шапка-ведро": "bucket", "метла": "broom", "снегирь": "bird",
               "фонарик": "lantern", "гирлянда": "garland", "ёлочка рядом": "fir", "звезда на ведре": "star"}


# ---------- рисование ----------
def _snowball(p, center, radius):
    grad = QRadialGradient(center + QPointF(-radius * 0.35, -radius * 0.4), radius * 1.3)
    grad.setColorAt(0, QColor("#ffffff"))
    grad.setColorAt(0.6, QColor("#e8eff8"))
    grad.setColorAt(1, QColor("#a9bcd4"))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawEllipse(center, radius, radius)


def paint_snowman(p, ground, height, percent=FULL, items=None):
    """Снеговик стоит серединой низа на ground; height - рост готового. percent - докуда слеплен,
    items - что на нём (по умолчанию - по проценту)."""
    items = items_for(percent) if items is None else items
    r1, r2, r3 = height * 0.24, height * 0.17, height * 0.12
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    shadow = QRadialGradient(ground, r1 * 1.4)
    shadow.setColorAt(0, QColor(40, 60, 90, 90))
    shadow.setColorAt(1, QColor(40, 60, 90, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(shadow)
    p.drawEllipse(ground, r1 * 1.4, r1 * 0.35)
    if percent < 10:
        p.restore()
        return
    if percent < 40:                                            # ком катится и растёт
        k = (percent - 10) / 30
        r = r1 * (0.3 + 0.7 * k)
        _snowball(p, ground + QPointF(-r1 * (1 - k), -r), r)
        p.restore()
        return
    low = ground + QPointF(0, -r1 * 0.95)
    shoulder = low + QPointF(0, -r1 - r2 * 0.6)
    hands = [shoulder + QPointF(side * r2 * 2.2, -r2 * 0.5) for side in (-1, 1)]
    if "fir" in items:
        _fir(p, ground + QPointF(r1 * 2.2, 0), height * 0.7)
    if "broom" in items and percent >= 60:                       # метла - в правой руке, метёлкой в снег
        _broom(p, QPointF(hands[1].x() + r2 * 0.4, ground.y()), hands[1] + QPointF(-r2 * 0.1, -r2 * 0.7), height)
    if "arms" in items:
        _arms(p, shoulder, r2, "mittens" in items)
    _snowball(p, low, r1)
    if percent >= 40:
        k = min(1.0, (percent - 40) / 20)
        mid = low + QPointF(0, -r1 * 0.85 - r2 * k)
        if k > 0:
            _snowball(p, mid, r2 * (0.3 + 0.7 * k))
        if percent >= 60:
            kh = min(1.0, (percent - 60) / 20)
            head = mid + QPointF(0, -r2 * 0.85 - r3 * kh)
            if kh > 0:
                _snowball(p, head, r3 * (0.3 + 0.7 * kh))
            if "buttons" in items:
                for dy in (-0.45, 0.0, 0.45):
                    p.setBrush(QColor("#1e1e26"))
                    p.drawEllipse(mid + QPointF(0, dy * r2), r2 * 0.09, r2 * 0.09)
            if "scarf" in items:
                _scarf(p, mid + QPointF(0, -r2 * 0.78), r2)
            if "face" in items:
                _face(p, head, r3)
            if "bucket" in items:                                # ведро сидит на макушке
                _bucket(p, head + QPointF(r3 * 0.1, -r3 * 1.05), r3 * 1.15, "star" in items)
            if "bird" in items:                                  # снегирь сидит на левой руке
                _bird(p, hands[0] + QPointF(r2 * 0.15, -r3 * 0.45), r3 * 0.55)
            if "lantern" in items:
                _lantern(p, ground + QPointF(-r1 * 1.9, 0), height * 0.42)
            if "garland" in items:
                _garland(p, mid, r2)
    p.restore()


def _face(p, head, r):
    p.setBrush(QColor("#1b1b22"))
    for dx in (-0.35, 0.35):
        p.drawEllipse(head + QPointF(dx * r, -0.15 * r), r * 0.11, r * 0.11)
    for k in range(5):
        a = math.radians(30 + k * 30)
        p.drawEllipse(head + QPointF(0.5 * r * math.cos(a), 0.2 * r + 0.22 * r * math.sin(a)), r * 0.06, r * 0.06)
    nose = QPainterPath(head + QPointF(0, -0.02 * r))
    nose.lineTo(head + QPointF(0.95 * r, 0.12 * r))
    nose.lineTo(head + QPointF(0, 0.16 * r))
    nose.closeSubpath()
    grad = QLinearGradient(head, head + QPointF(r, 0))
    grad.setColorAt(0, QColor("#ffb04a"))
    grad.setColorAt(1, QColor("#e2650f"))
    p.setBrush(grad)
    p.drawPath(nose)


def _scarf(p, neck, r):
    red = QColor("#c8302a")
    p.setBrush(red)
    p.drawRoundedRect(QRectF(neck.x() - r * 0.85, neck.y() - r * 0.16, r * 1.7, r * 0.32), r * 0.14, r * 0.14)
    tail = QPainterPath(neck + QPointF(r * 0.35, r * 0.05))
    tail.lineTo(neck + QPointF(r * 0.62, r * 0.85))
    tail.lineTo(neck + QPointF(r * 0.95, r * 0.75))
    tail.lineTo(neck + QPointF(r * 0.62, r * 0.0))
    tail.closeSubpath()
    p.drawPath(tail)
    p.setPen(QPen(QColor(255, 255, 255, 190), max(1.0, r * 0.06)))
    for k in range(4):
        x = neck.x() - r * 0.6 + k * r * 0.4
        p.drawLine(QPointF(x, neck.y() - r * 0.15), QPointF(x, neck.y() + r * 0.15))
    p.setPen(Qt.NoPen)


def _bucket(p, top, r, star):
    w, h = r * 1.4, r * 0.9
    shape = QPainterPath(top + QPointF(-w * 0.5, h * 0.5))
    shape.lineTo(top + QPointF(-w * 0.36, -h * 0.5))
    shape.lineTo(top + QPointF(w * 0.36, -h * 0.5))
    shape.lineTo(top + QPointF(w * 0.5, h * 0.5))
    shape.closeSubpath()
    grad = QLinearGradient(top + QPointF(-w / 2, 0), top + QPointF(w / 2, 0))
    grad.setColorAt(0, QColor("#4f7fb8"))
    grad.setColorAt(0.4, QColor("#8fb8e8"))
    grad.setColorAt(1, QColor("#2f5488"))
    p.setBrush(grad)
    p.drawPath(shape)
    p.setBrush(QColor("#2a4a78"))
    p.drawRoundedRect(QRectF(top.x() - w * 0.55, top.y() + h * 0.4, w * 1.1, h * 0.18), 2, 2)
    if star:
        p.setBrush(QColor("#ffd34d"))
        c = top + QPointF(0, -h * 0.75)
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = r * 0.35 if k % 2 == 0 else r * 0.15
            pts.append(c + QPointF(rr * math.cos(a), rr * math.sin(a)))
        path = QPainterPath(pts[0])
        for point in pts[1:]:
            path.lineTo(point)
        path.closeSubpath()
        p.drawPath(path)


def _arms(p, root, r, mittens):
    p.setPen(QPen(QColor("#5a3418"), max(1.5, r * 0.09), Qt.SolidLine, Qt.RoundCap))
    for side in (-1, 1):
        hand = root + QPointF(side * r * 2.2, -r * 0.5)
        p.drawLine(root + QPointF(side * r * 0.6, 0), hand)
        p.drawLine(hand + QPointF(-side * r * 0.4, r * 0.14), hand + QPointF(-side * r * 0.2, -r * 0.35))
        if mittens:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#2e7d4f"))
            p.drawEllipse(hand, r * 0.22, r * 0.18)
            p.setPen(QPen(QColor("#5a3418"), max(1.5, r * 0.09), Qt.SolidLine, Qt.RoundCap))
    p.setPen(Qt.NoPen)


def _broom(p, foot, top, height):
    """Метла: метёлка стоит на снегу (foot), черенок - до руки (top)."""
    neck = foot + QPointF((top.x() - foot.x()) * 0.18, -height * 0.13)
    p.setPen(QPen(QColor("#7a4d2a"), max(1.5, height * 0.025), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(neck, top)
    p.setPen(Qt.NoPen)
    straw = QPainterPath(foot + QPointF(-height * 0.07, 0))
    straw.lineTo(foot + QPointF(height * 0.08, 0))
    straw.lineTo(neck + QPointF(height * 0.015, 0))
    straw.lineTo(neck + QPointF(-height * 0.015, 0))
    straw.closeSubpath()
    p.setBrush(QColor("#d8b45a"))
    p.drawPath(straw)
    p.setPen(QPen(QColor("#a8843a"), max(1.0, height * 0.008)))
    for k in (-0.04, 0.0, 0.04):
        p.drawLine(neck, foot + QPointF(height * k, 0))
    p.setPen(QPen(QColor("#b0303a"), max(1.2, height * 0.012)))
    p.drawLine(neck + QPointF(-height * 0.02, height * 0.02), neck + QPointF(height * 0.02, height * 0.02))
    p.setPen(Qt.NoPen)


def _bird(p, at, r):
    p.setBrush(QColor("#2a2a33"))                                        # снегирь: чёрная шапочка, красная грудь
    p.drawEllipse(at, r * 1.1, r * 0.9)
    p.setBrush(QColor("#e2453a"))
    p.drawEllipse(at + QPointF(r * 0.15, r * 0.25), r * 0.75, r * 0.6)
    p.setBrush(QColor("#2a2a33"))
    p.drawEllipse(at + QPointF(r * 0.6, -r * 0.55), r * 0.5, r * 0.45)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(at + QPointF(r * 0.75, -r * 0.62), r * 0.1, r * 0.1)


def _lantern(p, foot, height):
    p.setPen(QPen(QColor("#1d2026"), max(1.5, height * 0.04)))
    p.drawLine(foot, foot + QPointF(0, -height * 0.8))
    p.setPen(Qt.NoPen)
    glow = QRadialGradient(foot + QPointF(0, -height * 0.88), height * 0.4)
    glow.setColorAt(0, QColor(255, 200, 100, 140))
    glow.setColorAt(1, QColor(255, 200, 100, 0))
    p.setBrush(glow)
    p.drawEllipse(foot + QPointF(0, -height * 0.88), height * 0.4, height * 0.4)
    p.setBrush(QColor("#ffcf6b"))
    p.drawRect(QRectF(foot.x() - height * 0.07, foot.y() - height * 0.98, height * 0.14, height * 0.18))


def _garland(p, mid, r):
    colors = ["#ff4d4d", "#ffcf4d", "#4dd27a", "#5aa8ff"]
    for k in range(7):
        t = k / 6
        point = mid + QPointF(-r * 0.9 + 1.8 * r * t, -r * 0.2 + r * 0.35 * math.sin(math.pi * t))
        p.setBrush(QColor(colors[k % 4]))
        p.drawEllipse(point, r * 0.08, r * 0.08)


def _fir(p, foot, height):
    p.setBrush(QColor("#2e7a43"))
    for k in range(3):
        y = foot.y() - height * (0.25 + 0.25 * k)
        w = height * (0.32 - 0.08 * k)
        path = QPainterPath(QPointF(foot.x(), y - height * 0.32))
        path.lineTo(foot.x() + w, y)
        path.lineTo(foot.x() - w, y)
        path.closeSubpath()
        p.drawPath(path)
    p.setBrush(QColor("#5c3a20"))
    p.drawRect(QRectF(foot.x() - height * 0.04, foot.y() - height * 0.25, height * 0.08, height * 0.25))


def paint_pile(p, ground, height):
    """Что осталось после машины: сугроб, ведро набок, морковка торчит."""
    r = height * 0.24
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    mound = QPainterPath(ground + QPointF(-r * 1.5, 0))
    mound.cubicTo(ground + QPointF(-r * 1.2, -r * 0.9), ground + QPointF(r * 0.9, -r * 1.1), ground + QPointF(r * 1.5, 0))
    mound.closeSubpath()
    grad = QLinearGradient(ground + QPointF(0, -r), ground)
    grad.setColorAt(0, QColor("#ffffff"))
    grad.setColorAt(1, QColor("#b8c9de"))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawPath(mound)
    p.translate(ground + QPointF(r * 0.4, -r * 0.75))
    p.rotate(-35)
    _bucket(p, QPointF(0, 0), height * 0.12, False)
    p.rotate(35)
    p.setBrush(QColor("#ee7a1c"))
    nose = QPainterPath(QPointF(-r * 0.9, r * 0.2))
    nose.lineTo(QPointF(-r * 0.4, -r * 0.1))
    nose.lineTo(QPointF(-r * 0.45, r * 0.15))
    nose.closeSubpath()
    p.drawPath(nose)
    p.restore()


def paint_vehicle(p, kind, front, height, t):
    """Кто едет: машина (фары), снегоуборщик (мигалка, отвал), санки (двое детей). front - нос, по земле."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    h = height
    x, y = front.x(), front.y()
    if kind == "car":
        beam = QLinearGradient(QPointF(x, y), QPointF(x + h * 1.3, y))
        beam.setColorAt(0, QColor(255, 240, 180, 120))
        beam.setColorAt(1, QColor(255, 240, 180, 0))
        p.setBrush(beam)
        cone = QPainterPath(QPointF(x, y - h * 0.32))
        cone.lineTo(x + h * 1.3, y - h * 0.6)
        cone.lineTo(x + h * 1.3, y)
        cone.lineTo(x, y - h * 0.22)
        p.drawPath(cone)
        p.setBrush(QColor("#7d1f22"))
        p.drawRoundedRect(QRectF(x - h * 1.5, y - h * 0.45, h * 1.5, h * 0.3), h * 0.08, h * 0.08)
        p.drawRoundedRect(QRectF(x - h * 1.15, y - h * 0.68, h * 0.8, h * 0.28), h * 0.1, h * 0.1)
        p.setBrush(QColor("#a8c8e8"))
        p.drawRect(QRectF(x - h * 1.05, y - h * 0.63, h * 0.3, h * 0.18))
        p.drawRect(QRectF(x - h * 0.7, y - h * 0.63, h * 0.28, h * 0.18))
        p.setBrush(QColor("#fff2b0"))
        p.drawEllipse(QPointF(x - h * 0.04, y - h * 0.32), h * 0.05, h * 0.05)
        wheels = (x - h * 1.2, x - h * 0.35)
    elif kind == "plow":
        blink = 1.0 if int(t * 6) % 2 else 0.25
        glow = QRadialGradient(QPointF(x - h * 0.7, y - h * 0.95), h * 0.35)
        glow.setColorAt(0, QColor(255, 160, 40, int(200 * blink)))
        glow.setColorAt(1, QColor(255, 160, 40, 0))
        p.setBrush(glow)
        p.drawEllipse(QPointF(x - h * 0.7, y - h * 0.95), h * 0.35, h * 0.35)
        p.setBrush(QColor("#e8892c"))
        p.drawRoundedRect(QRectF(x - h * 1.6, y - h * 0.5, h * 1.35, h * 0.36), h * 0.05, h * 0.05)
        p.drawRoundedRect(QRectF(x - h * 0.95, y - h * 0.85, h * 0.55, h * 0.4), h * 0.06, h * 0.06)
        p.setBrush(QColor("#a8c8e8"))
        p.drawRect(QRectF(x - h * 0.85, y - h * 0.78, h * 0.35, h * 0.2))
        p.setBrush(QColor("#9aa3ad"))
        blade = QPainterPath(QPointF(x - h * 0.25, y - h * 0.45))
        blade.lineTo(x + h * 0.05, y - h * 0.5)
        blade.lineTo(x + h * 0.12, y)
        blade.lineTo(x - h * 0.25, y - h * 0.08)
        blade.closeSubpath()
        p.drawPath(blade)
        p.setBrush(QColor(255, 160, 40, int(255 * blink)))
        p.drawEllipse(QPointF(x - h * 0.7, y - h * 0.9), h * 0.06, h * 0.05)
        wheels = (x - h * 1.35, x - h * 0.55)
    else:                                                                # санки: двое в шапках, шарф развевается
        p.setBrush(QColor("#9a6a3a"))
        p.drawRoundedRect(QRectF(x - h * 1.2, y - h * 0.24, h * 1.15, h * 0.1), h * 0.04, h * 0.04)
        p.setPen(QPen(QColor("#6a4a2a"), max(1.2, h * 0.04), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(x - h * 1.25, y - h * 0.04), QPointF(x - h * 0.05, y - h * 0.04))
        p.drawArc(QRectF(x - h * 0.16, y - h * 0.26, h * 0.22, h * 0.24), -90 * 16, 180 * 16)
        p.setPen(Qt.NoPen)
        for k, (coat, hat) in enumerate((("#3567c4", "#d8302c"), ("#2e8a4e", "#e8b13a"))):
            cx = x - h * (0.95 - 0.45 * k)
            p.setBrush(QColor(coat))
            p.drawRoundedRect(QRectF(cx - h * 0.14, y - h * 0.58, h * 0.28, h * 0.36), h * 0.1, h * 0.1)
            p.setBrush(QColor("#f1c9a0"))
            p.drawEllipse(QPointF(cx, y - h * 0.68), h * 0.11, h * 0.11)
            p.setBrush(QColor(hat))
            p.drawChord(QRectF(cx - h * 0.12, y - h * 0.82, h * 0.24, h * 0.2), 0, 180 * 16)
            p.drawEllipse(QPointF(cx, y - h * 0.84), h * 0.04, h * 0.04)
        p.setBrush(QColor("#d8302c"))
        wave = QPainterPath(QPointF(x - h * 0.95, y - h * 0.55))
        wave.cubicTo(QPointF(x - h * 1.15, y - h * (0.6 + 0.05 * math.sin(t * 12))),
                     QPointF(x - h * 1.3, y - h * 0.5), QPointF(x - h * 1.4, y - h * (0.55 + 0.06 * math.sin(t * 15))))
        wave.lineTo(x - h * 1.38, y - h * 0.48)
        wave.cubicTo(QPointF(x - h * 1.25, y - h * 0.46), QPointF(x - h * 1.1, y - h * 0.52), QPointF(x - h * 0.95, y - h * 0.5))
        p.drawPath(wave)
        wheels = ()
    p.setBrush(QColor("#15161a"))
    for wx in wheels:
        p.drawEllipse(QPointF(wx, y - h * 0.1), h * 0.12, h * 0.12)
    p.restore()


class Yard:
    """Двор за окном: какой снеговик сейчас, сколько снесено, и сцена «кто-то едет» (3 секунды)."""

    KNOCK = 3.2

    def __init__(self):
        self.percent = 0.0
        self.done = 0
        self.knock = None                      # (кто, когда началось)
        self.puffs = []

    def update(self, written, goal, day, now):
        """Новые слова. Возвращает True, если что-то поменялось (надо перерисовать)."""
        done, percent = progress(written, goal)
        changed = abs(percent - self.percent) > 0.4 or done != self.done
        if done > self.done and self.knock is None and self.percent > 0:
            self.knock = (vehicle(day, done), now)
        self.done, self.percent = done, percent
        return changed

    def busy(self):
        return self.knock is not None

    def paint(self, p, ground, height, width, now):
        """Нарисовать снеговика (или сугроб) и, если едет, - машину; ground - где стоит снеговик."""
        if self.knock is None:
            if self.done and self.percent < 10:
                paint_pile(p, ground + QPointF(-height * 0.6, 0), height * 0.7)     # след прошлого снеговика
            paint_snowman(p, ground, height, self.percent)
            return
        kind, start = self.knock
        t = (now - start) / self.KNOCK
        if t >= 1:
            self.knock = None
            self.paint(p, ground, height, width, now)
            return
        front_x = ground.x() - width * 0.6 + width * 1.4 * t
        hit = front_x >= ground.x() - height * 0.2
        if hit:
            paint_pile(p, ground, height)
            if not self.puffs:
                rng = random.Random(int(start * 1000))
                self.puffs = [(rng.uniform(-1, 1), rng.uniform(-1, -0.2), rng.uniform(0.6, 1.4)) for _ in range(14)]
            age = max(0.0, front_x - (ground.x() - height * 0.2)) / (width * 0.4)
            p.save()
            p.setPen(Qt.NoPen)
            for dx, dy, s in self.puffs:
                c = QColor(255, 255, 255)
                c.setAlphaF(max(0.0, 0.9 - age))
                p.setBrush(c)
                p.drawEllipse(ground + QPointF(dx * height * 0.5 * (0.3 + age), dy * height * 0.5 * (0.3 + age)),
                              height * 0.04 * s, height * 0.04 * s)
            p.restore()
        else:
            self.puffs = []
            paint_snowman(p, ground, height, FULL)
        paint_vehicle(p, kind, QPointF(front_x, ground.y()), height * 0.55, now)


# ---------- вкладка «Снеговик» в «Антистрессе» ----------
class SnowmanView(QWidget):
    """Слева - снеговик дня (во весь рост, со двором), справа - снеговик сезона и его вещи."""

    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.yard = Yard()
        self.setMinimumSize(560, 330)
        self.clock = QTimer(self, interval=40)
        self.clock.timeout.connect(self._tick)
        self.t = 0.0
        self.refresh()

    def numbers(self):
        window = self.window
        written = window.today_words() if window is not None and hasattr(window, "today_words") else 0
        goal = getattr(window, "goal", C.DAILY_GOAL)
        stats = dict(getattr(window, "stats", {}) or {})
        return written, goal, stats

    def refresh(self):
        written, goal, stats = self.numbers()
        today = seasons.FIXED_TODAY or date.today()
        self.yard.update(written, goal, today.isoformat(), self.t)
        self.season = season_words(stats, today, written)
        self.text = self._describe(written, goal)
        if self.yard.busy():
            self.clock.start()
        remember(today, self.season, self.yard.done)
        self.update()

    def _describe(self, written, goal):
        lines = [tr("Сегодня: {n} - {p}% цели.").format(n=f"{written} " + plural(written, "слово", "слова", "слов"),
                                                       p=int(self.yard.done * FULL + self.yard.percent))]
        stage = next_stage(self.yard.percent, written, goal)
        if stage:
            lines.append(tr("Дальше - {what}: ещё {n}.").format(
                what=tr(stage[0]), n=f"{stage[1]} " + plural(stage[1], "слово", "слова", "слов")))
        if self.yard.done:
            lines.append(tr("Снеговиков за день: {n}").format(n=self.yard.done))
        return "\n".join(lines)

    def _tick(self):
        self.t += 0.04
        if not self.yard.busy():
            self.clock.stop()
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor("#0b1730"))
        sky.setColorAt(1, QColor("#2c3f68"))
        p.fillRect(self.rect(), sky)
        rng = random.Random(3)
        p.setPen(Qt.NoPen)
        for _ in range(40):
            c = QColor(255, 255, 255, rng.randint(80, 200))
            p.setBrush(c)
            p.drawEllipse(QPointF(rng.uniform(0, w), rng.uniform(0, h * 0.55)), 1.1, 1.1)
        ground_y = h * 0.8
        snow = QPainterPath(QPointF(0, ground_y))
        snow.cubicTo(QPointF(w * 0.3, ground_y - 14), QPointF(w * 0.6, ground_y + 10), QPointF(w, ground_y - 8))
        snow.lineTo(w, h)
        snow.lineTo(0, h)
        snow.closeSubpath()
        drift = QLinearGradient(0, ground_y - 14, 0, h)
        drift.setColorAt(0, QColor("#eef4fb"))
        drift.setColorAt(1, QColor("#a9bcd6"))
        p.setBrush(drift)
        p.drawPath(snow)
        self.yard.paint(p, QPointF(w * 0.28, ground_y + 4), h * 0.6, w * 0.56, self.t)
        items = {SEASON_KEYS[name] for name in season_items(self.season)}
        paint_snowman(p, QPointF(w * 0.74, ground_y + 6), h * 0.68, FULL if items else 40, items)
        font = QFont(C.FONT_FAMILY, 9)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#e8eef8"))
        p.drawText(QRectF(12, 10, w * 0.5 - 16, h * 0.3), Qt.TextWordWrap, self.text)
        got = len(items)
        season = tr("Снеговик сезона: {n}, вещей {got} из {all}.").format(
            n=f"{self.season} " + plural(self.season, "слово", "слова", "слов"), got=got, all=len(SEASON_ITEMS))
        if got < len(SEASON_ITEMS):
            need = SEASON_STEP * (got + 1) - self.season
            season += "\n" + tr("Следующая - {what}: ещё {n}.").format(
                what=tr(SEASON_ITEMS[got]), n=f"{need} " + plural(need, "слово", "слова", "слов"))
        p.drawText(QRectF(w * 0.52, 10, w * 0.48 - 12, h * 0.3), Qt.TextWordWrap, season)
        p.end()
