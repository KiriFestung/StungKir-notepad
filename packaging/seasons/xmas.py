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
    body = '<rect x="136" y="345" width="28" height="60" rx="4" fill="url(#trunk)"/>'
    tiers = [(170, 360, 135, 6), (115, 285, 110, 5), (65, 212, 86, 4), (22, 142, 60, 3)]
    lights = []
    for n, (top, base, half, lobes) in enumerate(tiers):
        body += f'<path d="{tier_path(top + 7, base + 8, half + 2, lobes)}" fill="url(#needle-dark)"/>'
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
    for i, (y0, half) in enumerate([(315, 110), (245, 88), (178, 64), (110, 40)]):   # нитки гирлянды
        x0, x1, sag = 150 - half, 150 + half, 26
        body += (f'<path d="M{x0},{y0 - 12} Q150,{y0 - 12 + 2 * sag} {x1},{y0 - 12}" stroke="#1b3322" '
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
    SCENE["tree"] = {"size": [300, 405], "lights": lights, "star": [150, 22]}
    return svg(300, 405, defs, body)


# ---------- подарки ----------
def box(x, y, w, h, d, base, ribbon, rng):
    """Коробка в 2.5D: перед, верх (светлее), бок (темнее), лента крестом и бант."""
    def shade(color, k):
        c = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{max(0, min(255, int(v * k))):02x}" for v in c)
    dx, dy = d * 0.7, -d * 0.45
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{base}"/>'
    out += f'<rect x="{x}" y="{y + h * 0.6}" width="{w}" height="{h * 0.4}" fill="#000" fill-opacity="0.12"/>'
    out += f'<path d="M{x + w},{y} l{dx},{dy} l0,{h} l{-dx},{-dy} Z" fill="{shade(base, 0.62)}"/>'
    out += f'<path d="M{x},{y} l{dx},{dy} l{w},0 l{-dx},{-dy} Z" fill="{shade(base, 1.25)}"/>'
    rx = x + w / 2 - 4
    out += f'<rect x="{rx}" y="{y}" width="8" height="{h}" fill="{ribbon}"/>'
    out += f'<rect x="{rx}" y="{y}" width="8" height="{h}" fill="#000" fill-opacity="0.08"/>'
    out += f'<path d="M{rx},{y} l{dx},{dy} l8,0 l{-dx},{-dy} Z" fill="{shade(ribbon, 1.15)}"/>'
    out += f'<path d="M{x + w},{y + h / 2 - 4} l{dx},{dy} l0,8 l{-dx},{-dy} Z" fill="{shade(ribbon, 0.7)}"/>'
    bx, by = x + w / 2 + dx / 2, y + dy / 2
    for side in (-1, 1):
        out += (f'<path d="M{bx},{by} Q{bx + side * 16},{by - 18} {bx + side * 20},{by - 4} '
                f'Q{bx + side * 12},{by + 2} {bx},{by} Z" fill="{ribbon}"/>')
        out += (f'<path d="M{bx},{by} Q{bx + side * 12},{by - 10} {bx + side * 15},{by - 4}" stroke="#fff" '
                f'stroke-opacity="0.35" stroke-width="1.5" fill="none"/>')
    out += f'<circle cx="{bx}" cy="{by}" r="4" fill="{shade(ribbon, 0.85)}"/>'
    _ = rng
    return out


def presents(rng):
    defs = rad("floor-ao", [(0, "#000000", 0.45), (1, "#000000", 0)])
    body = '<ellipse cx="135" cy="112" rx="132" ry="12" fill="url(#floor-ao)"/>'
    body += box(150, 42, 62, 66, 26, "#2d8a4e", "#d9363e", rng)
    body += box(14, 52, 70, 56, 24, "#c62f35", "#f1c24b", rng)
    body += box(200, 70, 48, 40, 18, "#f1c24b", "#c62f35", rng)
    body += box(80, 74, 58, 36, 20, "#3567c4", "#e8eef6", rng)
    SCENE["presents"] = {"size": [270, 120]}
    return svg(270, 120, defs, body)


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
    body += '<rect x="10" y="68" width="400" height="6" fill="#000" fill-opacity="0.35"/>'
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
    SCENE["fireplace"] = {"size": [420, 302], "fire": [210, 274, 120, 130], "mouth": [120, 132, 300, 292]}
    return svg(420, 302, defs, body)


# ---------- кресло-качалка ----------
def chair(rng):
    defs = lin("wood", [(0, "#9a6a42", 1), (0.5, "#6e4426", 1), (1, "#422815", 1)], x2=1, y2=1)
    defs += lin("wood-top", [(0, "#b8875a", 1), (1, "#7a4c2c", 1)])
    defs += lin("cushion", [(0, "#c8443c", 1), (1, "#8a1f1f", 1)])
    body = ""
    rocker = "M8,214 Q100,236 192,206"
    body += f'<path d="{rocker}" stroke="#2e1c0f" stroke-width="9" fill="none" stroke-linecap="round"/>'
    body += f'<path d="{rocker}" stroke="url(#wood)" stroke-width="7" fill="none" stroke-linecap="round"/>'
    for x0, x1 in ((52, 56), (150, 146)):                                   # ножки
        body += f'<path d="M{x0},{220} L{x1},130" stroke="url(#wood)" stroke-width="8" stroke-linecap="round"/>'
    body += '<path d="M40,124 L166,124 L172,136 L46,136 Z" fill="url(#wood-top)"/>'          # сиденье
    body += '<path d="M46,136 L172,136 L170,146 L48,146 Z" fill="#4a2c17"/>'
    for x0, x1 in ((48, 20), (64, 38)):                                      # спинка
        body += f'<path d="M{x0},128 L{x1},20" stroke="url(#wood)" stroke-width="8" stroke-linecap="round"/>'
    for t in (0.25, 0.45, 0.65):
        y = 128 - 108 * t
        body += (f'<path d="M{48 - 28 * t:.1f},{y:.1f} L{64 - 26 * t:.1f},{y:.1f}" stroke="#5a371e" '
                 f'stroke-width="3"/>')
    body += '<path d="M14,22 Q30,6 46,18" stroke="url(#wood)" stroke-width="9" fill="none" stroke-linecap="round"/>'
    body += '<path d="M36,80 Q100,72 168,86" stroke="url(#wood)" stroke-width="8" fill="none" stroke-linecap="round"/>'
    body += '<path d="M160,86 L158,126" stroke="url(#wood)" stroke-width="6" stroke-linecap="round"/>'
    body += '<path d="M50,114 Q100,104 160,114 L162,126 L48,126 Z" fill="url(#cushion)"/>'   # подушка
    # плед на спинке: клетка в повёрнутом прямоугольнике, бахрома снизу
    plaid = '<rect x="0" y="0" width="44" height="88" rx="4" fill="#1f5a36"/>'
    for i in range(1, 4):
        plaid += f'<rect x="{i * 11 - 2}" y="0" width="4" height="88" fill="#b8312b" fill-opacity="0.85"/>'
    for i in range(1, 8):
        plaid += f'<rect x="0" y="{i * 11 - 2}" width="44" height="4" fill="#b8312b" fill-opacity="0.85"/>'
        plaid += f'<rect x="0" y="{i * 11 + 3}" width="44" height="1" fill="#f1c24b" fill-opacity="0.6"/>'
    plaid += '<rect x="0" y="0" width="12" height="88" fill="#000" fill-opacity="0.18"/>'
    for i in range(8):
        plaid += f'<path d="M{3 + i * 5.5},88 l0,7" stroke="#b8312b" stroke-width="2" stroke-linecap="round"/>'
    body += f'<g transform="translate(30,26) rotate(-14)">{plaid}</g>'
    _ = rng
    SCENE["chair"] = {"size": [200, 236], "pivot": [100, 224]}
    return svg(200, 236, defs, body)


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


def main():
    rng = random.Random(3)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in (("tree", tree(rng)), ("presents", presents(rng)), ("snowman", snowman()),
                       ("lantern", lantern()), ("fireplace", fireplace(rng)), ("chair", chair(rng)),
                       ("wreath", wreath(rng))):
        (OUT / f"{name}.svg").write_text(text, encoding="utf-8", newline="\n")
    (OUT / "scene.json").write_text(json.dumps(SCENE, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
