# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Сукно стола для бросков: бесшовная плитка 512x512 в оттенках серого - волокна, ворс и лёгкая неровность
валяния. Программа перекрашивает её в цвет темы (яркость точки относительно средней).
Запуск: python3 packaging/textures/felt.py stungkir/art/texture-felt.png 0.10"""
import sys
import numpy as np
from PIL import Image

N = 512
rng = np.random.default_rng(7)


def periodic_noise(scale, power=2.0):
    """Бесшовный шум: белый шум, отфильтрованный в частотах (по кругу - края сходятся сами)."""
    f = np.fft.fftfreq(N)
    fx, fy = np.meshgrid(f, f)
    radius = np.sqrt(fx ** 2 + fy ** 2)
    radius[0, 0] = 1
    spectrum = np.fft.fft2(rng.standard_normal((N, N))) / (radius * scale) ** power * np.exp(-(radius * scale) ** 2)
    out = np.real(np.fft.ifft2(spectrum))
    return (out - out.mean()) / out.std()


def blur(a, sigma):
    f = np.fft.fftfreq(N)
    fx, fy = np.meshgrid(f, f)
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))))


# волокна: короткие изогнутые штрихи, чуть больше вдоль одного направления (ворс)
fibers = np.zeros((N, N))
count, samples = 90000, 14
x0, y0 = rng.uniform(0, N, count), rng.uniform(0, N, count)
angle = rng.normal(0.35, 0.9, count)
length = rng.uniform(4, 18, count)
bend = rng.normal(0, 0.06, count)
bright = rng.choice([-1.0, 1.0], count, p=[0.45, 0.55]) * rng.uniform(0.4, 1.0, count)
t = np.linspace(-0.5, 0.5, samples)
a = angle[:, None] + bend[:, None] * t[None, :] * length[:, None]
xs = (x0[:, None] + np.cos(a) * t[None, :] * length[:, None]) % N
ys = (y0[:, None] + np.sin(a) * t[None, :] * length[:, None]) % N
np.add.at(fibers, (ys.astype(int).ravel(), xs.astype(int).ravel()), np.repeat(bright, samples))
fibers = blur(fibers, 0.6)
fibers = (fibers - fibers.mean()) / fibers.std()

grain = blur(rng.standard_normal((N, N)), 0.5)
grain = (grain - grain.mean()) / grain.std()
mottle = periodic_noise(18, 1.0)           # валяние: мягкие пятна в пару сантиметров
cloud = periodic_noise(4, 1.0)             # совсем крупная неровность, еле заметная

relief = 0.66 * fibers + 0.24 * grain + 0.28 * mottle + 0.14 * cloud
relief = relief / relief.std()
contrast = float(sys.argv[2]) if len(sys.argv) > 2 else 0.12     # разброс яркости относительно среднего
img = 128 * (1 + contrast * relief)
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "L").save(sys.argv[1], optimize=True)
print("mean", round(img.mean(), 1), "stdev", round(img.std(), 1))
