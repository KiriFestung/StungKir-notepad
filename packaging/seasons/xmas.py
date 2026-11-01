# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Рождество в 2.5D: ёлка, подарки, снеговик на сугробе, фонарь, камин, кресла-качалки и хвойный венок
для часов. Всё - SVG: программа рисует их чётко на любом экране. Объём - градиентами, бликами и тенями
(без фильтров - Qt SVG их не умеет). Огонь, огоньки гирлянд, снег и качание кресел программа рисует сама
(fun/season_scene.py) - здесь только неподвижное, а где что зажигать, лежит в scene.json.
Запуск: python3 packaging/seasons/xmas.py [папка]  (по умолчанию stungkir/art/seasons/xmas)"""

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stungkir" / "art" / "seasons" / "xmas"
SCENE = {}


def svg(w, h, defs, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<defs>{defs}</defs>{body}</svg>')


def lin(id_, stops, x1=0, y1=0, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<linearGradient id="{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>'


def rad(id_, stops, cx=0.5, cy=0.5, r=0.5):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<radialGradient id="{id_}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>'


BALLS = {"red": ("#ff8a80", "#d32f2f", "#6f0e0e"), "gold": ("#fff1a8", "#e0a526", "#7a4f06"),
         "blue": ("#9cc8ff", "#2f6fd6", "#102a60"), "white": ("#ffffff", "#dfe8f2", "#8ea3ba"),
         "green": ("#a8f0b4", "#2e9a4a", "#0f4220")}


def ball_defs():
    return "".join(rad(f"ball-{n}", [(0, a, 1), (0.45, b, 1), (1, c, 1)], cx=0.38, cy=0.34, r=0.72)
                   for n, (a, b, c) in BALLS.items())


def ball(x, y, r, color, cap=True):
    out = ""
    if cap:
        out += (f'<rect x="{x - r * 0.3:.1f}" y="{y - r - 3:.1f}" width="{r * 0.6:.1f}" height="4" rx="1" '
                f'fill="#c9a24a"/>')
    return out + (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="url(#ball-{color})"/>'
                  f'<ellipse cx="{x - r * 0.35:.1f}" cy="{y - r * 0.4:.1f}" rx="{r * 0.24:.1f}" '
                  f'ry="{r * 0.15:.1f}" fill="#ffffff" fill-opacity="0.8"/>')


def star(cx, cy, r1, r2, fill):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r1 if k % 2 == 0 else r2
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return (f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="#a8740c" stroke-width="1.2" '
            f'stroke-linejoin="round"/>')


# ---------- ёлка ----------
def tier_path(top, base, half, lobes, cx=150):
    left, right = cx - half, cx + half
    d = f"M{cx},{top} Q{cx + half * 0.35},{(top + base) / 2} {right},{base} "
    step = (right - left) / lobes
    for i in range(lobes):
        x1 = right - step * (i + 1)
        mid = right - step * (i + 0.5)
        d += f"Q{mid:.1f},{base + 16:.1f} {x1:.1f},{base - 2 if i < lobes - 1 else base:.1f} "
    return d + f"Q{cx - half * 0.35},{(top + base) / 2} {cx},{top} Z"


def frosting(base, half, lobes, cx=150, lift=6):
    left, right = cx - half, cx + half
    step = (right - left) / lobes
    d = f"M{right - 4},{base - lift} "
    for i in range(lobes):
        x1 = right - step * (i + 1)
        mid = right - step * (i + 0.5)
        d += f"Q{mid:.1f},{base + 12 - lift:.1f} {x1 + 2:.1f},{base - lift:.1f} "
    return d


def tree(rng):
    defs = ball_defs()
    defs += lin("needle", [(0, "#5cb36b", 1), (0.45, "#2e7a43", 1), (1, "#123d22", 1)], x2=1, y2=0.15)
    defs += lin("needle-dark", [(0, "#1d5a33", 1), (1, "#0a2414", 1)], x2=1, y2=0)
    defs += lin("round", [(0, "#000000", 0), (0.55, "#000000", 0.05), (1, "#000000", 0.35)])
    defs += lin("trunk", [(0, "#8a5a35", 1), (0.6, "#5c3a20", 1), (1, "#2e1c0f", 1)], x2=1, y2=0)
    defs += rad("star-glow", [(0, "#ffe9a0", 0.85), (0.4, "#ffcf5a", 0.35), (1, "#ffcf5a", 0)])
    defs += lin("star-fill", [(0, "#fff6c4", 1), (0.5, "#ffd34d", 1), (1, "#e09a12", 1)], x2=0.6, y2=1)
    defs += lin("snow", [(0, "#ffffff", 1), (1, "#dbe7f4", 1)])
    defs += '<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4"/></filter>'
    body = '<ellipse cx="150" cy="402" rx="110" ry="8" fill="#000" fill-opacity="0.5" filter="url(#soft)"/>'
    body += '<rect x="136" y="345" width="28" height="60" rx="4" fill="url(#trunk)"/>'
    tiers = [(170, 360, 135, 6), (115, 285, 110, 5), (65, 212, 86, 4), (22, 142, 60, 3)]
    lights = []
    for n, (top, base, half, lobes) in enumerate(tiers):
        body += (f'<path d="{tier_path(top + 7, base + 10, half + 2, lobes)}" fill="#000" fill-opacity="0.45" '
                 f'filter="url(#soft)"/>')                                   # мягкая тень яруса на нижний
        body += f'<path d="{tier_path(top + 4, base + 5, half + 1, lobes)}" fill="url(#needle-dark)"/>'
        body += f'<path d="{tier_path(top, base, half, lobes)}" fill="url(#needle)"/>'
        body += f'<path d="{tier_path(top, base, half, lobes)}" fill="url(#round)"/>'      # объём: низ темнее
        for _ in range(int(half / 3.5)):                                     # штрихи хвои
            y = rng.uniform(top + (base - top) * 0.3, base - 4)
            span = half * (y - top) / (base - top) * 0.88
            x = 150 + rng.uniform(-span, span)
            light = x < 150
            body += (f'<path d="M{x:.1f},{y:.1f} l{rng.uniform(-6, 6):.1f},{rng.uniform(5, 10):.1f}" '
                     f'stroke="{rng.choice(["#6cc27a", "#4fa35f"] if light else ["#1f5f35", "#174a2a"])}" '
                     f'stroke-width="1.7" stroke-linecap="round" stroke-opacity="0.75"/>')
        body += (f'<path d="{frosting(base + 3, half, lobes)}" fill="none" stroke="#9fb4cc" stroke-width="7" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
        body += (f'<path d="{frosting(base, half, lobes)}" fill="none" stroke="url(#snow)" stroke-width="7" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
        step = 2 * half / lobes
        for i in range(lobes):                                               # комья снега на концах лап
            x = 150 + half - step * (i + 0.5) + rng.uniform(-6, 6)
            body += (f'<ellipse cx="{x:.1f}" cy="{base - 3:.1f}" rx="{rng.uniform(5, 8):.1f}" ry="3.6" '
                     f'fill="#ffffff"/>')
        _ = n
    def width_at(y):
        """Полуширина ёлки на высоте y - по самому широкому ярусу там (лапы с зубцами чуть уже)."""
        return max((half * (y - top) / (base - top) for top, base, half, _ in tiers if top <= y <= base), default=0)
    for y0 in (315, 245, 178, 110):                                   # нитки гирлянды - не шире веток
        sag = 26
        y = y0 - 12
        half = 0.86 * min(width_at(y), width_at(y + sag))
        x0, x1 = 150 - half, 150 + half
        body += (f'<path d="M{x0:.1f},{y} Q150,{y + 2 * sag} {x1:.1f},{y}" stroke="#1b3322" '
                 f'stroke-width="1.1" fill="none"/>')
        n = int(half / 11)
        for t in range(1, n):
            lights.append([round(x0 + (x1 - x0) * t / n, 1), round(y0 - 12 + 4 * sag * (t / n) * (1 - t / n), 1)])
    for x, y, r, c in [(110, 335, 9, "red"), (190, 330, 9, "gold"), (150, 300, 8, "blue"), (88, 290, 7, "gold"),
                       (210, 285, 7, "red"), (128, 258, 8, "red"), (176, 250, 7, "blue"), (150, 210, 7, "gold"),
                       (112, 205, 6, "blue"), (186, 200, 6, "red"), (138, 150, 6, "red"), (166, 160, 6, "gold"),
                       (150, 100, 5, "blue"), (70, 345, 7, "white"), (230, 342, 7, "blue")]:
        body += ball(x, y, r, c)
    body += '<circle cx="150" cy="22" r="40" fill="url(#star-glow)"/>' + star(150, 22, 20, 8.5, "url(#star-fill)")
    top, side = 24, 12                           # поля: свечение звезды и края лап не обрезаются краем картинки
    SCENE["tree"] = {"size": [300 + 2 * side, 405 + top], "star": [150 + side, 22 + top],
                     "lights": [[x + side, y + top] for x, y in lights]}
    return svg(300 + 2 * side, 405 + top, defs, f'<g transform="translate({side},{top})">{body}</g>')


# ---------- подарки ----------
def shade(color, k):
    c = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{max(0, min(255, int(v * k))):02x}" for v in c)


def paper_defs(name, base, mark, kind):
    """Обёрточная бумага узором: горошек, полоски или звёздочки (pattern Qt SVG умеет)."""
    if kind == "dots":
        inner = f'<rect width="12" height="12" fill="{base}"/><circle cx="3" cy="3" r="1.6" fill="{mark}"/>' \
                f'<circle cx="9" cy="9" r="1.6" fill="{mark}"/>'
        size = 12
    elif kind == "stripes":
        inner = f'<rect width="10" height="10" fill="{base}"/><path d="M-2,8 L8,-2 M3,13 L13,3" stroke="{mark}" ' \
                f'stroke-width="2.4"/>'
        size = 10
    else:
        inner = f'<rect width="16" height="16" fill="{base}"/>' + star(8, 8, 3.4, 1.4, mark).replace(
            'stroke="#a8740c" stroke-width="1.2"', 'stroke="none"')
        size = 16
    return (f'<pattern id="{name}" width="{size}" height="{size}" patternUnits="userSpaceOnUse">{inner}</pattern>')


def box(x, y, w, h, d, paper, base, ribbon):
    """Коробка в 2.5D: перед, верх, бок. Лента крестом идёт по всем трём граням, бант - в середине крышки."""
    dx, dy = d * 0.62, -d * 0.42
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{paper})"/>'                     # перед
    out += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#face-shade)"/>'
    out += f'<path d="M{x + w},{y} l{dx},{dy} l0,{h} l{-dx},{-dy} Z" fill="url(#{paper})"/>'          # бок
    out += f'<path d="M{x + w},{y} l{dx},{dy} l0,{h} l{-dx},{-dy} Z" fill="#000" fill-opacity="0.32"/>'
    out += f'<path d="M{x},{y} l{dx},{dy} l{w},0 l{-dx},{-dy} Z" fill="url(#{paper})"/>'               # крышка
    out += f'<path d="M{x},{y} l{dx},{dy} l{w},0 l{-dx},{-dy} Z" fill="#fff" fill-opacity="0.16"/>'
    band = max(5.0, w * 0.13)
    cx = x + w / 2
    out += f'<rect x="{cx - band / 2}" y="{y}" width="{band}" height="{h}" fill="{ribbon}"/>'           # лента спереди
    out += f'<rect x="{cx - band / 2}" y="{y}" width="{band}" height="{h}" fill="url(#face-shade)"/>'
    out += (f'<path d="M{cx - band / 2},{y} l{dx},{dy} l{band},0 l{-dx},{-dy} Z" fill="{shade(ribbon, 1.12)}"/>')
    mid = 0.5                                                                    # поперечная - по середине глубины
    px, py = x + dx * mid, y + dy * mid
    out += (f'<path d="M{px},{py - band * 0.3} l{w},0 l0,{band * 0.6} l{-w},0 Z" fill="{shade(ribbon, 1.05)}"/>')
    sx = x + w + dx * mid
    out += (f'<path d="M{sx - band * 0.31},{y + dy * mid - band * 0.2} l{band * 0.62},{-band * 0.42} '
            f'l0,{h} l{-band * 0.62},{band * 0.42} Z" fill="{shade(ribbon, 0.7)}"/>')
    bx, by = cx + dx * mid, y + dy * mid
    for side in (-1, 1):                                                         # бант: две петли и хвостики
        out += (f'<path d="M{bx},{by} C{bx + side * 6},{by - 20} {bx + side * 24},{by - 16} {bx + side * 20},{by - 4} '
                f'C{bx + side * 16},{by + 3} {bx + side * 6},{by + 2} {bx},{by} Z" fill="{ribbon}"/>')
        out += (f'<path d="M{bx},{by} C{bx + side * 8},{by - 14} {bx + side * 18},{by - 12} {bx + side * 17},{by - 5}" '
                f'stroke="{shade(ribbon, 0.6)}" stroke-width="1.2" fill="none"/>')
        out += (f'<path d="M{bx},{by + 1} L{bx + side * 8},{by + 14} L{bx + side * 12},{by + 11} Z" '
                f'fill="{shade(ribbon, 0.85)}"/>')
    out += f'<ellipse cx="{bx}" cy="{by}" rx="4.4" ry="3.6" fill="{shade(ribbon, 0.9)}"/>'
    out += f'<ellipse cx="{bx - 1.2}" cy="{by - 1.2}" rx="1.6" ry="1.2" fill="#fff" fill-opacity="0.5"/>'
    return out


def presents(rng):
    defs = '<filter id="soft" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="5"/></filter>'
    defs += lin("face-shade", [(0, "#ffffff", 0.10), (0.5, "#000000", 0), (1, "#000000", 0.22)])
    defs += paper_defs("p-green", "#2d8a4e", "#e9f3ea", "dots")
    defs += paper_defs("p-red", "#c62f35", "#f6d27a", "stars")
    defs += paper_defs("p-gold", "#e8b13a", "#fff2c4", "stripes")
    defs += paper_defs("p-blue", "#3567c4", "#dce8fb", "dots")
    body = '<ellipse cx="140" cy="114" rx="130" ry="9" fill="#000" fill-opacity="0.5" filter="url(#soft)"/>'
    body += box(150, 44, 62, 66, 26, "p-green", "#2d8a4e", "#d9363e")
    body += box(16, 54, 70, 56, 24, "p-red", "#c62f35", "#f1c24b")
    body += box(204, 72, 46, 38, 18, "p-gold", "#e8b13a", "#c62f35")
    body += box(82, 76, 58, 34, 20, "p-blue", "#3567c4", "#e8eef6")
    _ = rng
    SCENE["presents"] = {"size": [280, 126]}
    return svg(280, 126, defs, body)


# ---------- снеговик ----------
def snowman():
    defs = rad("snowball", [(0, "#ffffff", 1), (0.55, "#eef3fa", 1), (0.85, "#cbd8e8", 1), (1, "#a9bcd2", 1)],
               cx=0.4, cy=0.35, r=0.65)
    defs += rad("contact", [(0, "#5d7594", 0.55), (1, "#5d7594", 0)])
    defs += lin("drift", [(0, "#ffffff", 1), (0.6, "#e6eef8", 1), (1, "#b4c6dc", 1)])
    defs += lin("knit", [(0, "#e8453c", 1), (1, "#9e1b1b", 1)], x2=1, y2=1)
    defs += lin("carrot", [(0, "#ffb04a", 1), (1, "#e2650f", 1)], x2=1, y2=0)
    defs += lin("stick", [(0, "#7a4d2a", 1), (1, "#4b2e17", 1)])
    body = ('<path d="M6,318 Q12,286 48,284 Q70,268 100,276 Q132,266 156,284 Q192,286 196,318 Z" '
            'fill="url(#drift)"/>')
    body += ('<path d="M62,148 L18,112 M30,122 L20,104 M38,128 L28,136" stroke="url(#stick)" stroke-width="4" '
             'stroke-linecap="round" fill="none"/>')
    body += ('<path d="M138,148 L184,118 M170,127 L182,108 M160,134 L174,140" stroke="url(#stick)" '
             'stroke-width="4" stroke-linecap="round" fill="none"/>')
    body += '<ellipse cx="100" cy="290" rx="60" ry="10" fill="url(#contact)"/>'
    body += '<circle cx="100" cy="236" r="58" fill="url(#snowball)"/>'
    body += '<ellipse cx="100" cy="186" rx="40" ry="10" fill="url(#contact)"/>'
    body += '<circle cx="100" cy="150" r="43" fill="url(#snowball)"/>'
    body += '<ellipse cx="100" cy="114" rx="30" ry="8" fill="url(#contact)"/>'
    body += '<circle cx="100" cy="86" r="31" fill="url(#snowball)"/>'
    for y in (138, 158, 178, 222, 248):
        body += (f'<circle cx="100" cy="{y}" r="4.2" fill="#1b1b22"/>'
                 f'<circle cx="98.6" cy="{y - 1.4}" r="1.2" fill="#666"/>')
    body += '<path d="M66,112 Q100,128 134,112 L136,124 Q100,142 64,124 Z" fill="url(#knit)"/>'
    body += '<path d="M118,122 L124,170 L140,166 L132,118 Z" fill="url(#knit)"/>'
    for y in (140, 150, 160):
        body += (f'<path d="M{122 + (y - 140) * 0.12:.1f},{y} L{135 + (y - 140) * 0.1:.1f},{y - 2}" '
                 f'stroke="#fff" stroke-width="3" stroke-opacity="0.85"/>')
    body += ('<path d="M124,170 l-2,6 M129,169 l0,7 M134,168 l2,6 M139,167 l3,5" stroke="#c22b25" '
             'stroke-width="2" stroke-linecap="round"/>')
    for x in (89, 111):
        body += f'<circle cx="{x}" cy="80" r="4" fill="#1b1b22"/><circle cx="{x - 1.3}" cy="78.6" r="1.3" fill="#fff"/>'
    body += '<path d="M100,88 L128,93 L100,95 Z" fill="url(#carrot)"/>'
    for k in range(5):
        a = math.radians(30 + k * 30)
        body += f'<circle cx="{100 + 13 * math.cos(a):.1f}" cy="{96 + 6 * math.sin(a):.1f}" r="1.9" fill="#1b1b22"/>'
    body += '<ellipse cx="86" cy="90" rx="5" ry="3" fill="#ff9aa2" fill-opacity="0.45"/>'
    body += '<ellipse cx="114" cy="90" rx="5" ry="3" fill="#ff9aa2" fill-opacity="0.45"/>'
    body += '<path d="M70,70 Q72,30 104,32 Q126,36 132,64 Z" fill="url(#knit)"/>'
    for x in range(80, 124, 7):
        body += (f'<path d="M{x},64 Q{x + 2},54 {x + 4},46" stroke="#b72420" stroke-width="1.5" fill="none" '
                 f'stroke-opacity="0.6"/>')
    body += '<rect x="66" y="62" width="70" height="12" rx="6" fill="#f4f7fb"/>'
    body += '<rect x="66" y="69" width="70" height="5" rx="2.5" fill="#cfdbe8"/>'
    body += '<circle cx="106" cy="30" r="10" fill="url(#snowball)"/>'
    SCENE["snowman"] = {"size": [200, 320]}
    return svg(200, 320, defs, body)


# ---------- фонарь ----------
def lantern():
    defs = lin("iron", [(0, "#14161b", 1), (0.35, "#4a515e", 1), (0.6, "#23272f", 1), (1, "#0d0e12", 1)], x2=1, y2=0)
    defs += rad("glass", [(0, "#fff8d6", 1), (0.45, "#ffc96a", 1), (1, "#e2832a", 1)], cy=0.6)
    defs += lin("snow", [(0, "#ffffff", 1), (1, "#d3e1f0", 1)])
    defs += rad("floor-ao", [(0, "#000000", 0.5), (1, "#000000", 0)])
    body = '<ellipse cx="60" cy="412" rx="40" ry="7" fill="url(#floor-ao)"/>'
    body += '<path d="M40,412 L44,386 L76,386 L80,412 Z" fill="url(#iron)"/>'
    body += '<rect x="46" y="370" width="28" height="18" rx="3" fill="url(#iron)"/>'
    body += '<rect x="54" y="150" width="12" height="222" fill="url(#iron)"/>'
    body += '<rect x="50" y="250" width="20" height="8" rx="3" fill="url(#iron)"/>'
    body += '<path d="M44,150 L76,150 L70,140 L50,140 Z" fill="url(#iron)"/>'
    body += '<path d="M36,72 L84,72 L76,140 L44,140 Z" fill="url(#glass)"/>'
    body += '<path d="M60,72 L60,140 M36,72 L44,140 M84,72 L76,140" stroke="#1a1d23" stroke-width="3"/>'
    body += '<path d="M33,72 L87,72" stroke="#1a1d23" stroke-width="5" stroke-linecap="round"/>'
    body += '<path d="M30,72 L60,44 L90,72 Z" fill="url(#iron)"/>'
    body += '<path d="M28,70 Q34,52 50,50 Q60,40 72,50 Q88,52 92,70 Q60,62 28,70 Z" fill="url(#snow)"/>'
    body += '<circle cx="60" cy="38" r="5" fill="url(#iron)"/>'
    SCENE["lantern"] = {"size": [120, 420], "glass": [60, 106]}
    return svg(120, 420, defs, body)


# ---------- камин ----------
def fireplace(rng):
    defs = lin("mantel", [(0, "#9a6a42", 1), (0.25, "#7a4c2c", 1), (1, "#3f2614", 1)])
    defs += rad("firebox", [(0, "#4a1607", 1), (0.6, "#220a04", 1), (1, "#0e0503", 1)], cy=0.9, r=0.8)
    defs += lin("log", [(0, "#7a4a2a", 1), (1, "#3b2312", 1)])
    defs += lin("hearth", [(0, "#77706a", 1), (1, "#3f3a36", 1)])
    defs += lin("sock", [(0, "#e3423a", 1), (1, "#9c1a1a", 1)], x2=1, y2=1)
    defs += lin("candle", [(0, "#fff9ec", 1), (1, "#d8cbb2", 1)], x2=1, y2=0)
    defs += rad("candle-glow", [(0, "#ffd27a", 0.8), (1, "#ffd27a", 0)])
    defs += '<filter id="soft" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>'
    defs += ball_defs()
    body = '<rect x="30" y="70" width="360" height="222" fill="#3c2018"/>'           # раствор
    for row in range(12):
        y = 70 + row * 19
        shift = 0 if row % 2 else 22
        for col in range(-1, 10):
            x = 30 + shift + col * 44
            if x > 390 or x + 42 < 30:
                continue
            x0, x1 = max(30, x), min(390, x + 42)
            shade = rng.choice(["#8e3b2c", "#7d3226", "#9a4532", "#6f2c22", "#a14d37"])
            body += f'<rect x="{x0 + 1}" y="{y + 1}" width="{x1 - x0 - 2}" height="16" rx="2" fill="{shade}"/>'
            body += f'<rect x="{x0 + 2}" y="{y + 1.5}" width="{x1 - x0 - 4}" height="3" rx="1.5" fill="#fff" fill-opacity="0.13"/>'
            body += f'<rect x="{x0 + 1}" y="{y + 13}" width="{x1 - x0 - 2}" height="4" rx="2" fill="#000" fill-opacity="0.22"/>'
    body += '<rect x="30" y="70" width="18" height="222" fill="#000" fill-opacity="0.18"/>'
    body += '<rect x="372" y="70" width="18" height="222" fill="#000" fill-opacity="0.28"/>'
    body += '<path d="M110,292 L110,170 Q110,120 210,120 Q310,120 310,170 L310,292 Z" fill="#2b140e"/>'
    body += '<path d="M120,292 L120,174 Q120,132 210,132 Q300,132 300,174 L300,292 Z" fill="url(#firebox)"/>'
    body += ('<rect x="140" y="268" width="140" height="16" rx="8" fill="url(#log)" transform="rotate(-6 210 276)"/>'
             '<rect x="140" y="268" width="140" height="16" rx="8" fill="url(#log)" transform="rotate(7 210 276)"/>'
             '<ellipse cx="146" cy="272" rx="5" ry="7" fill="#c98a52"/><ellipse cx="274" cy="270" rx="5" ry="7" '
             'fill="#c98a52"/>')
    body += '<rect x="0" y="290" width="420" height="12" rx="3" fill="url(#hearth)"/>'        # плита перед топкой
    body += '<rect x="0" y="290" width="420" height="2" fill="#fff" fill-opacity="0.18"/>'
    body += '<rect x="10" y="48" width="400" height="24" rx="4" fill="url(#mantel)"/>'
    body += ('<rect x="14" y="70" width="392" height="10" fill="#000" fill-opacity="0.6" filter="url(#soft)"/>'
             '<rect x="10" y="50" width="400" height="3" rx="1.5" fill="#e8c49a" fill-opacity="0.35"/>')
    for x in range(14, 410, 8):
        y = 74 + 6 * math.sin(x / 22)
        for _ in range(3):
            body += (f'<path d="M{x:.0f},{y:.1f} l{rng.uniform(-9, 9):.1f},{rng.uniform(-4, 10):.1f}" '
                     f'stroke="{rng.choice(["#2f7a42", "#1d5a33", "#3f9152", "#5cb36b"])}" stroke-width="2.4" '
                     f'stroke-linecap="round"/>')
    for x in range(30, 400, 46):
        y = 76 + 6 * math.sin(x / 22)
        body += "".join(f'<circle cx="{x + dx}" cy="{y + dy}" r="3.2" fill="url(#ball-red)"/>'
                        for dx, dy in ((0, 0), (5, 3), (-4, 4)))
    for x in (78, 342):
        body += (f'<path d="M{x - 14},82 L{x + 14},82 L{x + 14},132 Q{x + 14},146 {x},146 L{x - 22},146 '
                 f'Q{x - 32},146 {x - 32},136 Q{x - 32},126 {x - 14},126 Z" fill="url(#sock)"/>')
        body += f'<rect x="{x - 17}" y="78" width="34" height="13" rx="5" fill="#f4f7fb"/>'
        body += f'<rect x="{x - 17}" y="86" width="34" height="5" rx="2" fill="#cfdbe8"/>'
    for x in (40, 380):
        body += f'<circle cx="{x}" cy="6" r="16" fill="url(#candle-glow)"/>'
        body += f'<rect x="{x - 6}" y="12" width="12" height="36" rx="2" fill="url(#candle)"/>'
        body += f'<path d="M{x},0 Q{x + 5},8 {x},12 Q{x - 5},8 {x},0 Z" fill="#ffcf5a"/>'
    top = 22                                     # поле сверху: свечение свечей не обрезается
    SCENE["fireplace"] = {"size": [420, 302 + top], "fire": [210, 274 + top, 120, 130],
                          "mouth": [120, 132 + top, 300, 292 + top]}
    return svg(420, 302 + top, defs, f'<g transform="translate(0,{top})">{body}</g>')


# ---------- кресло-качалка ----------
def chair(rng):
    """Кресло боком, смотрит вправо: полозья, точёные ножки, сиденье с подушкой, спинка с балясинами,
    подлокотник и плед в клетку, переброшенный через спинку. Дерево - градиентами вдоль деталей,
    мягкие тени - размытием."""
    defs = '<filter id="soft" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3"/></filter>'
    defs += '<filter id="softer" x="-40%" y="-80%" width="180%" height="260%"><feGaussianBlur stdDeviation="6"/></filter>'
    defs += lin("wood-v", [(0, "#b98a5c", 1), (0.35, "#8a5a35", 1), (0.7, "#6a4122", 1), (1, "#43281a", 1)], x2=1, y2=0)
    defs += lin("wood-h", [(0, "#c49568", 1), (0.4, "#8f5e38", 1), (1, "#4e3019", 1)])
    defs += lin("seat-top", [(0, "#c99a6c", 1), (1, "#946039", 1)])
    defs += rad("cushion", [(0, "#d9584f", 1), (0.6, "#b23a33", 1), (1, "#7d1f1f", 1)], cx=0.45, cy=0.35, r=0.7)
    defs += ('<pattern id="plaid" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(-8)">'
             '<rect width="18" height="18" fill="#1f5a36"/>'
             '<rect x="6" width="6" height="18" fill="#b8312b" fill-opacity="0.85"/>'
             '<rect y="6" width="18" height="6" fill="#b8312b" fill-opacity="0.75"/>'
             '<rect x="14" width="1.2" height="18" fill="#f1c24b" fill-opacity="0.8"/>'
             '<rect y="14" width="18" height="1.2" fill="#f1c24b" fill-opacity="0.8"/></pattern>')
    defs += lin("fold", [(0, "#000", 0.35), (0.3, "#000", 0), (0.6, "#fff", 0.08), (1, "#000", 0.3)], x2=1, y2=0)
    body = '<ellipse cx="104" cy="230" rx="96" ry="7" fill="#000" fill-opacity="0.55" filter="url(#softer)"/>'
    # полоз: тёмная подложка, дерево, блик сверху
    rocker = "M6,212 Q100,240 196,204"
    body += f'<path d="{rocker}" stroke="#2a180c" stroke-width="12" fill="none" stroke-linecap="round"/>'
    body += f'<path d="{rocker}" stroke="url(#wood-h)" stroke-width="9" fill="none" stroke-linecap="round"/>'
    body += '<path d="M10,210 Q100,236 192,203" stroke="#e2b98a" stroke-opacity="0.45" stroke-width="1.6" fill="none"/>'

    def leg(x_top, x_bottom, top, bottom, width):
        out = (f'<path d="M{x_top - width / 2},{top} L{x_top + width / 2},{top} L{x_bottom + width * 0.35},{bottom} '
               f'L{x_bottom - width * 0.35},{bottom} Z" fill="url(#wood-v)"/>')
        for t in (0.3, 0.62):                                                     # точёные пояски
            y = top + (bottom - top) * t
            x = x_top + (x_bottom - x_top) * t
            out += f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{width * 0.62:.1f}" ry="2.6" fill="url(#wood-v)"/>'
            out += f'<ellipse cx="{x - 1:.1f}" cy="{y - 0.8:.1f}" rx="{width * 0.4:.1f}" ry="0.9" fill="#e2b98a" fill-opacity="0.5"/>'
        return out
    body += leg(58, 52, 136, 222, 9) + leg(150, 154, 136, 216, 9)
    body += '<path d="M54,186 L152,182" stroke="url(#wood-h)" stroke-width="5" stroke-linecap="round"/>'   # перекладина
    # спинка: два изогнутых столба, балясины, верхняя планка
    body += '<path d="M44,134 C40,100 30,60 20,22" stroke="#2a180c" stroke-width="11" fill="none" stroke-linecap="round"/>'
    body += '<path d="M44,134 C40,100 30,60 20,22" stroke="url(#wood-v)" stroke-width="8" fill="none" stroke-linecap="round"/>'
    for x0, x1 in ((48, 26), (54, 33), (60, 40), (66, 47)):
        body += f'<path d="M{x0},128 L{x1},34" stroke="url(#wood-v)" stroke-width="4" stroke-linecap="round"/>'
        body += f'<ellipse cx="{(x0 + x1) / 2:.1f}" cy="81" rx="3.4" ry="5" fill="url(#wood-v)"/>'
    body += '<path d="M64,134 C62,100 54,62 46,24" stroke="#2a180c" stroke-width="10" fill="none" stroke-linecap="round"/>'
    body += '<path d="M64,134 C62,100 54,62 46,24" stroke="url(#wood-v)" stroke-width="7" fill="none" stroke-linecap="round"/>'
    body += '<path d="M12,26 C24,8 44,8 54,22" stroke="#2a180c" stroke-width="13" fill="none" stroke-linecap="round"/>'
    body += '<path d="M12,26 C24,8 44,8 54,22" stroke="url(#wood-h)" stroke-width="10" fill="none" stroke-linecap="round"/>'
    body += '<path d="M16,22 C27,10 42,10 50,19" stroke="#e8c49a" stroke-opacity="0.55" stroke-width="2" fill="none"/>'
    # сиденье: верх, торец, тень под ним
    body += '<path d="M42,124 L166,124 L174,136 L48,136 Z" fill="url(#seat-top)"/>'
    body += '<path d="M48,136 L174,136 L172,146 L50,146 Z" fill="#5c3820"/>'
    body += '<path d="M50,146 L172,146 L170,152 L54,152 Z" fill="#000" fill-opacity="0.45" filter="url(#soft)"/>'
    # подушка с пуговками
    body += '<path d="M50,124 C52,108 76,104 106,104 C138,104 162,106 166,118 C168,124 160,128 108,128 C70,128 50,128 50,124 Z" fill="url(#cushion)"/>'
    body += '<path d="M56,112 C80,106 136,106 160,113" stroke="#f3b1a6" stroke-opacity="0.45" stroke-width="1.4" fill="none"/>'
    for x in (84, 110, 136):
        body += f'<circle cx="{x}" cy="116" r="2.2" fill="#6e1717"/><circle cx="{x - 0.6}" cy="115.4" r="0.8" fill="#f3b1a6"/>'
    # подлокотник
    body += '<path d="M40,82 C80,72 130,76 170,86" stroke="#2a180c" stroke-width="10" fill="none" stroke-linecap="round"/>'
    body += '<path d="M40,82 C80,72 130,76 170,86" stroke="url(#wood-h)" stroke-width="7" fill="none" stroke-linecap="round"/>'
    body += '<path d="M44,79 C84,70 130,73 166,82" stroke="#e8c49a" stroke-opacity="0.5" stroke-width="1.4" fill="none"/>'
    body += leg(160, 158, 88, 124, 6)
    # плед: перекинут через верх спинки, свисает спереди складками
    plaid = ("M8,30 C18,14 46,12 58,26 C64,48 70,84 74,118 C66,124 58,121 52,126 C44,121 36,124 28,118 "
             "C22,92 14,58 8,30 Z")
    body += f'<path d="{plaid}" fill="#000" fill-opacity="0.45" filter="url(#soft)" transform="translate(4,4)"/>'
    body += f'<path d="{plaid}" fill="url(#plaid)"/>'
    body += f'<path d="{plaid}" fill="url(#fold)"/>'
    for x0 in (26, 40, 54):                                                       # складки
        body += f'<path d="M{x0 - 6},30 C{x0 - 2},64 {x0 + 2},96 {x0 + 4},120" stroke="#000" stroke-opacity="0.22" stroke-width="2.2" fill="none"/>'
    for k in range(10):                                                           # бахрома
        x = 29 + k * 4.6
        y = 119 + (2 if k % 2 else 0)
        body += f'<path d="M{x:.1f},{y} l0.6,7" stroke="#c9b48a" stroke-width="1.6" stroke-linecap="round"/>'
    _ = rng
    SCENE["chair"] = {"size": [200, 240], "pivot": [100, 224]}
    return svg(200, 240, defs, body)


# ---------- венок для часов ----------
def wreath(rng):
    defs = ball_defs()
    defs += lin("bow", [(0, "#ef4a40", 1), (1, "#a01c1c", 1)], x2=1, y2=1)
    defs += rad("shade", [(0, "#000", 0), (0.7, "#000", 0), (0.8, "#000", 0.35), (0.9, "#000", 0), (1, "#000", 0)])
    body = '<circle cx="150" cy="150" r="140" fill="url(#shade)"/>'
    cx = cy = 150
    for layer, colors in ((0, ["#123d22", "#174a2a", "#1d5a33"]), (1, ["#2f7a42", "#3f9152", "#1d5a33"]),
                          (2, ["#4fa35f", "#6cc27a", "#3f9152"])):
        for _ in range(420):
            a = rng.uniform(0, math.tau)
            r = rng.gauss(118 - layer * 2, 8 - layer * 2)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a) - layer * 1.5
            t = a + math.pi / 2 + rng.uniform(-0.9, 0.9)
            ln = rng.uniform(9, 16)
            body += (f'<path d="M{x:.1f},{y:.1f} l{ln * math.cos(t):.1f},{ln * math.sin(t):.1f}" '
                     f'stroke="{rng.choice(colors)}" stroke-width="{2.8 - layer * 0.4:.1f}" stroke-linecap="round"/>')
    for k in range(10):
        a = k / 10 * math.tau + 0.3
        x, y = cx + 120 * math.cos(a), cy + 120 * math.sin(a)
        for dx, dy in ((0, 0), (6, 3), (-3, 6)):
            body += ball(x + dx, y + dy, 4.6, "red", cap=False)
    lights = [[round(cx + 110 * math.cos(k / 14 * math.tau), 1), round(cy + 110 * math.sin(k / 14 * math.tau), 1)]
              for k in range(14)]
    body += ('<path d="M150,262 Q118,236 104,256 Q100,276 150,266 Q200,276 196,256 Q182,236 150,262 Z" '
             'fill="url(#bow)"/>'
             '<path d="M146,266 L128,298 L140,294 L146,304 L150,268 Z M154,266 L172,298 L160,294 L154,304 L150,268 Z" '
             'fill="url(#bow)"/><circle cx="150" cy="264" r="7" fill="#c9302a"/>')
    SCENE["wreath"] = {"size": [300, 310], "lights": lights, "center": [150, 150], "inner": 98}
    return svg(300, 310, defs, body)


# ---------- окно: за стеклом ночь, снег, фонарь и снеговик ----------
# одна система координат на обе половины: стекло 60..240 × 50..280, рама вокруг, шторы по бокам
GLASS = (60, 50, 240, 280)


def window_back(rng):
    """Что за стеклом: ночное небо, звёзды, луна, дальний лес и сугробы. Фонарь, снеговик и падающий
    снег программа кладёт сверху (между этим и рамой)."""
    x0, y0, x1, y1 = GLASS
    defs = lin("sky", [(0, "#081226", 1), (0.6, "#16284d", 1), (1, "#2c3f68", 1)])
    defs += rad("moon-glow", [(0, "#fff6d8", 0.55), (0.5, "#cfe0ff", 0.12), (1, "#cfe0ff", 0)])
    defs += lin("drift", [(0, "#eef4fb", 1), (1, "#a9bcd6", 1)])
    defs += lin("far", [(0, "#c3d1e6", 1), (1, "#8fa3c2", 1)])
    body = f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#sky)"/>'
    for _ in range(26):
        x, y = rng.uniform(x0 + 4, x1 - 4), rng.uniform(y0 + 4, y0 + 120)
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(0.5, 1.3):.1f}" fill="#fff" fill-opacity="{rng.uniform(0.4, 0.9):.2f}"/>'
    body += '<circle cx="96" cy="88" r="34" fill="url(#moon-glow)"/><circle cx="96" cy="88" r="13" fill="#fdf3d2"/>'
    body += '<circle cx="91" cy="84" r="3" fill="#e9dcb4" fill-opacity="0.6"/><circle cx="100" cy="93" r="2" fill="#e9dcb4" fill-opacity="0.6"/>'
    body += f'<path d="M{x0},{y1 - 70} Q110,{y1 - 92} 160,{y1 - 78} Q205,{y1 - 66} {x1},{y1 - 84} L{x1},{y1} L{x0},{y1} Z" fill="url(#far)"/>'
    for x, h in ((70, 34), (84, 26), (196, 30), (212, 40), (228, 28)):                # дальний ельник
        base = y1 - 74
        body += f'<path d="M{x},{base - h} L{x + h * 0.38:.1f},{base} L{x - h * 0.38:.1f},{base} Z" fill="#203553"/>'
        body += f'<path d="M{x},{base - h} L{x + h * 0.2:.1f},{base - h * 0.45:.1f} L{x - h * 0.2:.1f},{base - h * 0.45:.1f} Z" fill="#dfe8f4" fill-opacity="0.7"/>'
    body += '<rect x="166" y="196" width="26" height="18" fill="#2a3550"/><path d="M162,197 L179,184 L196,197 Z" fill="#dfe8f4"/>'
    body += '<rect x="172" y="202" width="7" height="7" fill="#ffcf6b"/>'                       # дальний домик, окошко горит
    body += f'<path d="M{x0},{y1 - 34} Q100,{y1 - 52} 150,{y1 - 38} Q200,{y1 - 26} {x1},{y1 - 44} L{x1},{y1} L{x0},{y1} Z" fill="url(#drift)"/>'
    SCENE["window"] = {"size": [328, 360], "glass": [x0 + 14, y0, x1 + 14, y1],         # +14: поля под карниз
                       "snowman": [104 + 14, y1 - 30, 88], "lantern": [206 + 14, y1 - 30, 150]}
    return svg(328, 360, defs, f'<g transform="translate(14,0)">{body}</g>')


def window_front(rng):
    """Рама, переплёт, снег в нижних углах стёкол, иней, подоконник и шторы - поверх того, что за окном."""
    x0, y0, x1, y1 = GLASS
    defs = lin("frame", [(0, "#f3ead8", 1), (1, "#cbbfa6", 1)], x2=1, y2=1)
    defs += lin("frame-dark", [(0, "#a8987a", 1), (1, "#7f7059", 1)])
    defs += lin("curtain", [(0, "#5a0f14", 1), (0.25, "#9e2027", 1), (0.5, "#6e141a", 1), (0.75, "#a8262d", 1),
                            (1, "#4a0c10", 1)], x2=1, y2=0)
    defs += lin("rod", [(0, "#f2cf73", 1), (1, "#a8740c", 1)])
    defs += lin("velvet", [(0, "#4a0c10", 1), (0.3, "#9e2027", 1), (0.7, "#7a161c", 1), (1, "#a8262d", 1)], x2=1, y2=0)
    defs += lin("velvet-v", [(0, "#000", 0.25), (0.15, "#000", 0), (0.8, "#000", 0.05), (1, "#000", 0.35)])
    defs += '<filter id="soft" x="-30%" y="-10%" width="160%" height="120%"><feGaussianBlur stdDeviation="5"/></filter>'
    defs += rad("frost", [(0, "#ffffff", 0.55), (1, "#ffffff", 0)])
    defs += lin("snow", [(0, "#ffffff", 1), (1, "#d3e1f0", 1)])
    body = ""
    for cx, cy in ((x0 + 6, y0 + 6), (x1 - 6, y0 + 6), (x0 + 6, y1 - 6), (x1 - 6, y1 - 6)):   # иней по углам стекла
        body += f'<circle cx="{cx}" cy="{cy}" r="24" fill="url(#frost)"/>'
    mid = (x0 + x1) / 2
    for left, right in ((x0, mid - 4), (mid + 4, x1)):                          # снег в нижних углах стёкол
        body += (f'<path d="M{left},{y1} L{left},{y1 - 14} Q{left + 16},{y1 - 8} {left + 34},{y1 - 3} '
                 f'L{right - 34},{y1 - 3} Q{right - 16},{y1 - 9} {right},{y1 - 16} L{right},{y1} Z" fill="url(#snow)"/>')
    body += (f'<rect x="{x0 - 10}" y="{y0 - 6}" width="{x1 - x0 + 26}" height="{y1 - y0 + 36}" fill="#000" '
             f'fill-opacity="0.45" filter="url(#soft)"/>')                    # тень рамы на стене
    # рама: внешняя коробка, переплёт крестом
    body += (f'<path d="M{x0 - 12},{y0 - 12} L{x1 + 12},{y0 - 12} L{x1 + 12},{y1 + 10} L{x0 - 12},{y1 + 10} Z '
             f'M{x0},{y0} L{x0},{y1} L{x1},{y1} L{x1},{y0} Z" fill="url(#frame)" fill-rule="evenodd"/>')
    body += f'<rect x="{mid - 4}" y="{y0}" width="8" height="{y1 - y0}" fill="url(#frame)"/>'
    body += f'<rect x="{x0}" y="{(y0 + y1) / 2 - 4}" width="{x1 - x0}" height="8" fill="url(#frame)"/>'
    body += f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="3" fill="#000" fill-opacity="0.25"/>'
    body += f'<rect x="{x0}" y="{y0}" width="3" height="{y1 - y0}" fill="#000" fill-opacity="0.2"/>'
    body += f'<rect x="{x0 - 26}" y="{y1 + 8}" width="{x1 - x0 + 52}" height="14" rx="3" fill="url(#frame)"/>'   # подоконник
    body += f'<rect x="{x0 - 26}" y="{y1 + 20}" width="{x1 - x0 + 52}" height="5" fill="url(#frame-dark)"/>'
    # шторы: присобраны на кольцах, подхвачены шнуром с кистью, ниже подхвата расходятся и мягко
    # закругляются у подола; складки - узкими полосами света и тени, тени от штор - размытием
    left = ("M0,20 C30,20 62,20 90,22 C86,80 64,150 40,198 C52,238 66,290 70,336 "
            "C58,350 40,354 22,350 C12,348 4,344 0,340 Z")
    folds = ""
    for k, x in enumerate((14, 30, 46, 62, 78)):
        pinch = 12 + k * 6
        foot = 6 + k * 15
        folds += (f'<path d="M{x},22 C{x - 2},90 {pinch + 8},160 {pinch},198 C{pinch + 6},250 {foot + 6},300 {foot},344" '
                  f'stroke="#000" stroke-opacity="0.28" stroke-width="3.2" fill="none" stroke-linecap="round"/>')
        folds += (f'<path d="M{x + 5},22 C{x + 3},90 {pinch + 13},160 {pinch + 4},198 C{pinch + 10},250 {foot + 11},300 '
                  f'{foot + 6},344" stroke="#ff8b8b" stroke-opacity="0.16" stroke-width="2" fill="none" '
                  f'stroke-linecap="round"/>')
    rings = "".join(f'<circle cx="{x}" cy="17" r="3.2" fill="none" stroke="url(#rod)" stroke-width="1.8"/>'
                    for x in range(6, 92, 12))
    tie = ('<path d="M4,192 C18,186 36,190 46,198 C36,206 18,208 4,204 Z" fill="url(#rod)"/>'
           '<path d="M8,196 C20,192 34,194 42,198" stroke="#fff3c4" stroke-opacity="0.6" stroke-width="1.2" fill="none"/>'
           '<path d="M10,204 C8,214 6,226 8,236" stroke="url(#rod)" stroke-width="2" fill="none"/>'
           '<path d="M3,236 L13,236 L15,256 L1,256 Z" fill="url(#rod)"/>'
           '<path d="M2,256 l0,6 M5,256 l0,7 M8,256 l0,7 M11,256 l0,7 M14,256 l0,6" stroke="#c9952c" stroke-width="1.2"/>')
    curtain = (f'<path d="{left}" fill="#000" fill-opacity="0.5" filter="url(#soft)" transform="translate(6,4)"/>'
               f'<path d="{left}" fill="url(#velvet)"/><path d="{left}" fill="url(#velvet-v)"/>{folds}'
               f'<path d="M22,350 C40,354 58,350 70,336" stroke="#ff8b8b" stroke-opacity="0.25" stroke-width="1.6" '
               f'fill="none"/>{tie}{rings}')
    body += curtain + f'<g transform="translate(300,0) scale(-1,1)">{curtain}</g>'
    body += '<rect x="0" y="11" width="300" height="8" rx="4" fill="url(#rod)"/>'
    body += '<rect x="2" y="12" width="296" height="2" rx="1" fill="#fff3c4" fill-opacity="0.6"/>'
    for x in (2, 298):
        body += f'<circle cx="{x}" cy="15" r="7.5" fill="url(#rod)"/><circle cx="{x - 2}" cy="13" r="2.4" fill="#fff3c4" fill-opacity="0.7"/>'
    return svg(328, 360, defs, f'<g transform="translate(14,0)">{body}</g>')


# ---------- коврик у камина ----------
def rug(rng):
    defs = rad("rug", [(0, "#a8333a", 1), (0.7, "#8a242b", 1), (1, "#5e161b", 1)], cy=0.4, r=0.6)
    defs += rad("rug-in", [(0, "#2f6b45", 1), (1, "#1d4a2e", 1)], cy=0.4, r=0.6)
    body = '<ellipse cx="160" cy="52" rx="158" ry="36" fill="#000" fill-opacity="0.3"/>'
    for k in range(0, 360, 4):                                                  # бахрома
        a = math.radians(k)
        x, y = 160 + 150 * math.cos(a), 46 + 32 * math.sin(a)
        body += (f'<path d="M{x:.1f},{y:.1f} l{6 * math.cos(a):.1f},{3 * math.sin(a):.1f}" stroke="#e8d3a6" '
                 f'stroke-width="1.6" stroke-linecap="round"/>')
    body += '<ellipse cx="160" cy="46" rx="150" ry="32" fill="url(#rug)"/>'
    body += '<ellipse cx="160" cy="46" rx="128" ry="25" fill="none" stroke="#e8c169" stroke-width="3" stroke-dasharray="7 5"/>'
    body += '<ellipse cx="160" cy="46" rx="104" ry="19" fill="url(#rug-in)"/>'
    body += '<ellipse cx="160" cy="46" rx="80" ry="13" fill="none" stroke="#e8c169" stroke-width="2"/>'
    body += '<ellipse cx="160" cy="40" rx="140" ry="22" fill="#fff" fill-opacity="0.05"/>'
    _ = rng
    SCENE["rug"] = {"size": [320, 92]}
    return svg(320, 92, defs, body)


def main():
    rng = random.Random(3)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in (("tree", tree(rng)), ("presents", presents(rng)), ("snowman", snowman()),
                       ("lantern", lantern()), ("fireplace", fireplace(rng)), ("chair", chair(rng)),
                       ("wreath", wreath(rng)), ("window-back", window_back(rng)),
                       ("window-front", window_front(rng)), ("rug", rug(rng))):
        (OUT / f"{name}.svg").write_text(text, encoding="utf-8", newline="\n")
    (OUT / "scene.json").write_text(json.dumps(SCENE, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
