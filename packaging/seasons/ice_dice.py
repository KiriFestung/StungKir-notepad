# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ледяные кубики для кнопок: берём кубики автора из кости (stungkir/art/dice/bone/d*.png) и перекрашиваем
в лёд. Свет и тени - те же (яркость кости ложится на голубую шкалу), цифры - тёмно-синие, сверху иней
у краёв, пузырьки внутри и тонкая трещинка. Форма и цифры остаются рисунком автора.
python3 packaging/seasons/ice_dice.py [папка art]"""

import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
ART = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stungkir" / "art"
DARK, MID, LIGHT = np.array((22, 70, 110)), np.array((104, 180, 226)), np.array((232, 248, 255))
INK = np.array((16, 58, 104))


def ice(image, seed):
    rgba = np.asarray(image.convert("RGBA")).astype(float)
    rgb, alpha = rgba[..., :3], rgba[..., 3]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ink = (b - r > 35) & (alpha > 0)                          # цифры и лунки у кости - индиго
    light = (0.3 * r + 0.59 * g + 0.11 * b) / 255.0
    light = np.clip((light - 0.3) / 0.66, 0, 1)[..., None]
    low = DARK + (MID - DARK) * np.clip(light * 1.6, 0, 1)
    body = np.where(light < 0.62, low, MID + (LIGHT - MID) * np.clip((light - 0.62) / 0.38, 0, 1))
    out = np.where(ink[..., None], INK + (rgb - rgb.mean(axis=-1, keepdims=True)) * 0.15, body)
    shadow = (alpha > 0) & (light[..., 0] < 0.05) & ~ink        # тень под кубиком - мягче, голубоватая
    out[shadow] = (18, 40, 60)
    result = Image.fromarray(np.dstack([np.clip(out, 0, 255), alpha]).astype("uint8"), "RGBA")
    solid = Image.fromarray(((alpha > 200) & ~shadow).astype("uint8") * 255, "L")
    rng = random.Random(seed)
    w, h = result.size
    frost = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(frost)
    edge = np.asarray(solid.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(9))) > 0
    ys, xs = np.nonzero(edge & (np.asarray(solid) > 0))
    for _ in range(int(len(xs) * 0.05)):                       # иней: мелкая крупа у рёбер
        i = rng.randrange(len(xs))
        draw.point((int(xs[i]), int(ys[i])), fill=rng.randint(120, 230))
    inside = np.argwhere(np.asarray(solid.filter(ImageFilter.MinFilter(15))) > 0)
    for _ in range(9 if len(inside) else 0):                    # пузырьки внутри
        y, x = inside[rng.randrange(len(inside))]
        rad = rng.uniform(1.0, 2.6)
        draw.ellipse((x - rad, y - rad, x + rad, y + rad), outline=150)
    if len(inside):                                             # трещинка: ломаная с ответвлением
        y, x = inside[rng.randrange(len(inside))]
        points = [(x, y)]
        for _ in range(5):
            x, y = x + rng.uniform(-9, 9), y + rng.uniform(4, 10)
            points.append((x, y))
        draw.line(points, fill=110, width=1)
        bx, by = points[2]
        draw.line([(bx, by), (bx + rng.uniform(6, 12), by + rng.uniform(-6, 2))], fill=90, width=1)
    frost = Image.fromarray((np.asarray(frost) * (np.asarray(solid) > 0)).astype("uint8"), "L")
    white = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    white.putalpha(frost.filter(ImageFilter.GaussianBlur(0.4)))
    return Image.alpha_composite(result, white)


def main():
    out = ART / "dice" / "ice"
    out.mkdir(parents=True, exist_ok=True)
    for n, path in enumerate(sorted((ART / "dice" / "bone").glob("d*.png"))):
        ice(Image.open(path), n).save(out / path.name)


if __name__ == "__main__":
    main()
