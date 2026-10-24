# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ласка с объёмом: без белой бахромы по краю (на тёмной теме она светилась), фиолетовое тело
освещено сверху слева и темнеет к краю и к животу, кремовое - еле заметно. Сам рисунок не меняется.
python3 packaging/anim/polish.py - из packaging/art-src/weasel.png в stungkir/art/weasel.png.
Кадры бега и прыжка (weasel.py) проходят через то же самое."""

import sys
from pathlib import Path

import numpy as np
from PIL import Image


def _blur(x, sigma):
    h, w = x.shape
    pad = 4 * int(sigma + 4)
    big = np.zeros((h + 2 * pad, w + 2 * pad))
    big[pad:pad + h, pad:pad + w] = x
    fy, fx = np.fft.fftfreq(big.shape[0])[:, None], np.fft.fftfreq(big.shape[1])[None, :]
    out = np.real(np.fft.ifft2(np.fft.fft2(big) * np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))))
    return out[pad:pad + h, pad:pad + w]


def polish(image, scale=1.0):
    """image - PIL RGBA; scale - во сколько раз рисунок меньше исходных 480 точек (тени - того же размера)."""
    a = np.asarray(image.convert("RGBA")).astype(float)
    rgb, alpha = a[..., :3], a[..., 3] / 255
    halo = (rgb[..., 0] > 238) & (rgb[..., 1] > 238) & (rgb[..., 2] > 222)
    alpha = np.where(halo, 0, alpha)
    violet = (rgb[..., 2] > rgb[..., 0] + 20) & (alpha > 0.5)
    cream = (rgb[..., 0] > 235) & (rgb[..., 2] > 180) & (rgb[..., 2] < 225) & (alpha > 0.5)
    fill = (violet | cream).astype(float)
    gy, gx = np.gradient(_blur(fill, 7 * scale))
    lit = (gx * 0.6 + gy * 0.8) * 14 * scale                        # свет сверху слева
    rim = 1 - np.clip(_blur(fill, 3.5 * scale), 0, 1)               # к краю - темнее
    shade = 1 + np.where(violet, np.clip(lit, -0.16, 0.16) - 0.14 * rim, np.clip(lit, -0.05, 0.05))
    rows = np.arange(rgb.shape[0])[:, None] / rgb.shape[0]
    shade -= np.where(violet, 0.10 * (rows - 0.4), 0)               # к животу темнее
    mask = violet | cream
    rgb = rgb.copy()
    rgb[mask] = np.clip(rgb[mask] * shade[mask, None], 0, 255)
    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    source = sys.argv[1] if len(sys.argv) > 1 else root / "packaging" / "art-src" / "weasel.png"
    target = sys.argv[2] if len(sys.argv) > 2 else root / "stungkir" / "art" / "weasel.png"
    polish(Image.open(source)).save(target, optimize=True)
