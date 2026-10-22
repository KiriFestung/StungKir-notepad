# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Фактуры бумаги - синтез, без чужих фото. Запуск из корня проекта:
    python3 packaging/paper/make_paper.py
Пишет stungkir/art/paper/*.png: серые бесшовные плитки 1024×1024 (белое = чистая бумага).
Программа кладёт их поверх цвета бумаги в режиме «умножение», поэтому одна плитка годится
для любой бумаги. Бесшовность - от синтеза в частотах (шум по кругу повторяется сам)."""

from pathlib import Path

import numpy as np
from PIL import Image

SIZE = 1024
OUT = Path(__file__).resolve().parents[2] / "stungkir" / "art" / "paper"


def periodic_noise(rng, power, aniso=(1.0, 1.0), angle=0.0):
    """Бесшовный шум со спектром 1/f^power; aniso и angle вытягивают его (волокна)."""
    fy = np.fft.fftfreq(SIZE)[:, None]
    fx = np.fft.fftfreq(SIZE)[None, :]
    c, s = np.cos(angle), np.sin(angle)
    u, v = (fx * c + fy * s) * aniso[0], (-fx * s + fy * c) * aniso[1]
    f = np.sqrt(u * u + v * v)
    f[0, 0] = 1
    spectrum = (rng.standard_normal((SIZE, SIZE)) + 1j * rng.standard_normal((SIZE, SIZE))) / f ** power
    spectrum[0, 0] = 0
    out = np.real(np.fft.ifft2(spectrum))
    return out / (np.abs(out).std() + 1e-9)


def band(rng, low, high, aniso=(1.0, 1.0), angle=0.0):
    """Шум только в полосе частот (в периодах на плитку): облака, зерно, волокна."""
    fy = np.fft.fftfreq(SIZE)[:, None] * SIZE
    fx = np.fft.fftfreq(SIZE)[None, :] * SIZE
    c, s = np.cos(angle), np.sin(angle)
    u, v = (fx * c + fy * s) * aniso[0], (-fx * s + fy * c) * aniso[1]
    f = np.sqrt(u * u + v * v)
    mask = np.exp(-((np.log(f + 1e-9) - np.log(np.sqrt(low * high))) ** 2) / (2 * (np.log(high / low) / 2.5) ** 2))
    spectrum = (rng.standard_normal((SIZE, SIZE)) + 1j * rng.standard_normal((SIZE, SIZE))) * mask
    spectrum[0, 0] = 0
    out = np.real(np.fft.ifft2(spectrum))
    return out / (out.std() + 1e-9)


def fibers(rng, count, length, width):
    """Отдельные волокна - тонкие изогнутые линии, переходящие через край плитки по кругу."""
    canvas = np.zeros((SIZE, SIZE))
    for _ in range(count):
        x, y = rng.uniform(0, SIZE, 2)
        angle = rng.uniform(0, np.pi)
        bend = rng.uniform(-0.02, 0.02)
        strength = rng.uniform(0.3, 1.0)
        steps = int(length * rng.uniform(0.4, 1.0))
        for _step in range(steps):
            xi, yi = int(x) % SIZE, int(y) % SIZE
            canvas[yi, xi] += strength
            if width > 1:
                canvas[(yi + 1) % SIZE, xi] += strength * 0.5
            x += np.cos(angle)
            y += np.sin(angle)
            angle += bend
    # мягко размыть по кругу
    k = np.fft.fft2(canvas)
    fy = np.fft.fftfreq(SIZE)[:, None]
    fx = np.fft.fftfreq(SIZE)[None, :]
    k *= np.exp(-(fx * fx + fy * fy) * (SIZE * 0.6) ** 2 / 2)
    out = np.real(np.fft.ifft2(k))
    return out / (out.max() + 1e-9)


def save(name, shade):
    """shade: 0 - чистая бумага, больше - темнее. В PNG: 255 - белое."""
    image = np.clip(255 - shade, 0, 255).astype(np.uint8)
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image, "L").save(OUT / name, optimize=True)
    # и прозрачная накладка для фона под текстом: тёмное - чёрным, светлое - белым, ложится на любую тему
    deviation = shade - shade.mean()
    dark = np.clip(deviation * 1.15 + 3, 0, 26)
    light = np.clip(-deviation * 1.0 - 1, 0, 16)
    rgba = np.zeros((SIZE, SIZE, 4), np.uint8)
    rgba[..., :3] = np.where((light > dark)[..., None], 255, 0)
    rgba[..., 3] = np.maximum(dark, light).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(OUT / name.replace(".png", "-overlay.png"), optimize=True)
    print(name, "среднее", round(float(image.mean()), 1), "разброс", round(float(image.std()), 2))


def main():
    rng = np.random.default_rng(20261022)
    clouds = band(rng, 2, 10)                              # облачность (неровная плотность массы)
    grain = band(rng, 120, 400)                            # мелкое зерно
    tooth = band(rng, 40, 120, aniso=(1.0, 2.2), angle=0.3)   # «зуб» бумаги, чуть вытянутый
    fib = fibers(rng, 260, 90, 1)
    # «Книжная»: гладкая, тёплая, едва заметная
    save("book.png", 6 + 2.2 * clouds + 1.6 * tooth + 2.0 * grain + 10 * fib)
    # «Акварельная»/плотная: заметный зуб и облака
    save("rough.png", 10 + 4.0 * clouds + 4.0 * tooth + 3.0 * grain + 14 * fib)
    # «Старая»: пятна и неровный тон
    stains = np.clip(band(rng, 2, 8), 0, None) ** 1.3
    save("old.png", 10 + 3.0 * clouds + 2.0 * tooth + 2.5 * grain + 3.5 * stains + 18 * fib)


if __name__ == "__main__":
    main()
