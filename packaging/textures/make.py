# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Фактуры фона и бумаги - рисуются программой, бесшовные (шум считается по кругу, края сходятся сами).
python3 packaging/textures/make.py [папка art] - перезаписывает:
  texture-linen.png, texture-paper.png        - полупрозрачные плитки фона под текстом (на любую тему);
  paper/<book|rough|old>.png                   - серая бумага для «Как увидит читатель» (умножается на цвет);
  paper/<book|rough|old>-overlay.png           - она же полупрозрачной плиткой для фона под текстом.
Сукно стола для бросков - felt.py рядом."""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

SEED = 21


def grid(n):
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    return fx, fy


def noise(rng, n, scale, power=1.0):
    """Бесшовный шум: пятна размером около scale точек."""
    fx, fy = grid(n)
    radius = np.sqrt(fx ** 2 + fy ** 2)
    radius[0, 0] = 1
    spectrum = np.fft.fft2(rng.standard_normal((n, n))) / (radius * scale) ** power * np.exp(-(radius * scale) ** 2)
    return norm(np.real(np.fft.ifft2(spectrum)))


def blur(a, sigma):
    fx, fy = grid(a.shape[0])
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))))


def norm(a):
    return (a - a.mean()) / (a.std() or 1)


def fibers(rng, n, count, length, width, straight=0.012):
    """Волокна бумаги: длинные тонкие изогнутые нити в случайных направлениях (по кругу через края)."""
    out = np.zeros((n, n))
    samples = int(max(length) * 1.5)
    x0, y0 = rng.uniform(0, n, count), rng.uniform(0, n, count)
    angle = rng.uniform(0, np.pi, count)
    size = rng.uniform(*length, count)
    bend = rng.normal(0, straight, count)
    sign = rng.choice([-1.0, 1.0], count, p=[0.4, 0.6]) * rng.uniform(0.3, 1.0, count)
    t = np.linspace(-0.5, 0.5, samples)
    a = angle[:, None] + bend[:, None] * t[None, :] * size[:, None]
    xs = (x0[:, None] + np.cos(a) * t[None, :] * size[:, None]) % n
    ys = (y0[:, None] + np.sin(a) * t[None, :] * size[:, None]) % n
    np.add.at(out, (ys.astype(int).ravel(), xs.astype(int).ravel()), np.repeat(sign, samples))
    return norm(blur(out, width))


def shade(height, light=(-1.0, -1.0)):
    """Рельеф, освещённый слева сверху: бугорки светлеют с одной стороны и темнеют с другой."""
    gy, gx = np.gradient(height)
    return norm(-(gx * light[0] + gy * light[1]))


def streaks(rng, n, along, across):
    """Шум, вытянутый в одну сторону: вдоль нити меняется медленно, поперёк - быстро (по кругу, без швов)."""
    fx, fy = grid(n)
    spectrum = np.fft.fft2(rng.standard_normal((n, n)))
    spectrum *= np.exp(-2 * np.pi ** 2 * ((fx * along) ** 2 + (fy * across) ** 2))
    return norm(np.real(np.fft.ifft2(spectrum)))


def weave(rng, n, threads):
    """Лён: тонкие нити основы (вдоль) и утка (поперёк), у каждой свои утолщения и тон - как у настоящей
    ткани, а не клеточка. Переплетение - лёгкая шашечка, чтобы нити ныряли друг под друга."""
    period = n / threads
    y, x = np.mgrid[0:n, 0:n].astype(float)
    weft = np.cos(2 * np.pi * y / period) * (1 + 0.6 * streaks(rng, n, 40, 0.8))          # уток - поперёк
    warp = np.cos(2 * np.pi * x / period) * (1 + 0.6 * np.rot90(streaks(rng, n, 40, 0.8)))  # основа - вдоль
    tone_rows = streaks(rng, n, 120, 3)                     # нити светлее и темнее целиком
    tone_cols = np.rot90(streaks(rng, n, 120, 3))
    under = np.cos(np.pi * x / period) * np.cos(np.pi * y / period)          # шашечка переплетения
    cloth = 0.5 * weft + 0.5 * warp + 0.35 * tone_rows + 0.35 * tone_cols + 0.25 * under
    return norm(blur(cloth, 0.6))


def overlay(relief, strength, light_share=0.5):
    """Полупрозрачная плитка: светлые и тёмные точки с силой |рельеф|, ложится на любой фон."""
    alpha = np.clip(np.abs(relief) * strength, 0, 255)
    light = relief > np.quantile(relief, 1 - light_share)
    rgba = np.zeros(relief.shape + (4,), np.uint8)
    rgba[..., :3] = np.where(light[..., None], 255, 0)
    rgba[..., 3] = alpha.astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def gray(relief, mean, spread):
    return Image.fromarray(np.clip(mean + relief * spread, 0, 255).astype(np.uint8), "L")


def paper(rng, n, kind):
    """Рельеф бумаги: волокна, облачка массы (неравномерность), для плотной - зерно, для старой - пятнышки."""
    flocks = noise(rng, n, 10, 1.2)                          # облачка массы
    fine = fibers(rng, n, n * 10, (14, 50), 0.6)           # тонкие волокна
    grain = norm(blur(rng.standard_normal((n, n)), 0.7))   # мелкая зернистость
    relief = 0.55 * flocks + 0.28 * fine + 0.3 * grain
    if kind == "rough":                                     # «холодное прессование»: бугорки, освещённые сбоку
        tooth = noise(rng, n, 5, 1.2)            # бугорки в несколько точек
        relief = 0.8 * shade(tooth) + 0.15 * fine + 0.2 * flocks
    if kind == "old":                                       # пожелтевшие края пятен и мелкие точки времени
        stains = noise(rng, n, 160, 1.4)         # большие мягкие пятна
        spots = np.zeros((n, n))
        for _ in range(26):
            x, y, r = rng.uniform(0, n), rng.uniform(0, n), rng.uniform(3, 11)
            yy, xx = np.ogrid[0:n, 0:n]
            dx, dy = np.minimum(abs(xx - x), n - abs(xx - x)), np.minimum(abs(yy - y), n - abs(yy - y))
            spots -= np.exp(-(dx ** 2 + dy ** 2) / (2 * r * r)) * rng.uniform(0.5, 1.2)
        relief = 0.65 * relief + 0.45 * stains + 0.12 * norm(spots + 0.001 * rng.standard_normal((n, n)))
    return norm(relief)


def main(art):
    art = Path(art)
    rng = np.random.default_rng(SEED)
    linen = weave(rng, 512, 64)
    overlay(linen, 5.5).save(art / "texture-linen.png", optimize=True)
    light_paper = norm(0.4 * fibers(rng, 512, 4000, (12, 44), 0.6) + 0.6 * noise(rng, 512, 8, 1.2))
    overlay(light_paper, 5.0, 0.6).save(art / "texture-paper.png", optimize=True)
    for kind, mean, spread, strength in (("book", 242, 4.0, 9.0), ("rough", 236, 7.5, 9.0), ("old", 232, 6.5, 12.0)):
        relief = paper(rng, 1024, kind)
        gray(relief, mean, spread).save(art / "paper" / f"{kind}.png", optimize=True)
        overlay(relief, strength, 0.4).save(art / "paper" / f"{kind}-overlay.png", optimize=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "stungkir" / "art")
