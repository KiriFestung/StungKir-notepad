# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Пробка для доски: прессованная крошка - гранулы разного размера и тона, тёмные щели между ними,
поры внутри. Бесшовная: ячейки считаются по кругу.
python3 packaging/textures/cork.py [куда.png]"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make import blur, noise, norm  # noqa: E402

SEED = 5
BASE = np.array([166, 122, 80], float)       # светлая пробка


def granules(rng, n, cell, warp):
    """Ячейки на дрожащей сетке (у каждой свой «вес» - крошки разного размера), сетка искривлена шумом -
    края рваные, а не прямые. Номер ближайшей, расстояние до неё и до второй (щель - где почти равны)."""
    k = n // cell
    jitter = rng.uniform(0.1, 0.9, (k, k, 2))
    weight = rng.uniform(-0.35, 0.35, (k, k)) * cell
    y, x = np.mgrid[0:n, 0:n].astype(float)
    y, x = (y + warp * noise(rng, n, 6, 1.0)) % n, (x + warp * noise(rng, n, 6, 1.0)) % n
    gy, gx = (y // cell).astype(int), (x // cell).astype(int)
    first = np.full((n, n), np.inf)
    second = np.full((n, n), np.inf)
    owner = np.zeros((n, n), int)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cy, cx = (gy + dy) % k, (gx + dx) % k
            sy = (gy + dy + jitter[cy, cx, 0]) * cell
            sx = (gx + dx + jitter[cy, cx, 1]) * cell
            d = np.hypot(y - sy, x - sx) - weight[cy, cx]
            closer = d < first
            second = np.where(closer, first, np.minimum(second, d))
            owner = np.where(closer, cy * k + cx, owner)
            first = np.minimum(first, d)
    return owner, first, second


def cork(n=512):
    rng = np.random.default_rng(SEED)
    owner, first, second = granules(rng, n, 10, 2.5)
    count = owner.max() + 1
    tone = rng.normal(0, 1, count)
    tone[rng.random(count) < 0.12] -= 3.0                                  # подгоревшие тёмные крошки
    warm = rng.normal(0, 1, count)[owner]                                 # и у каждой чуть свой оттенок
    tone = tone[owner]
    edge = np.clip((second - first) / 3.0, 0, 1)                          # 0 - край крошки, 1 - середина
    broken = noise(rng, n, 4, 1.0) > 0.35                                 # щели не сплошные, а провалами
    gap = np.where(broken, edge, 1.0)
    pores = norm(blur(rng.standard_normal((n, n)), 0.7))                   # поры
    cloud = noise(rng, n, 90, 1.2)                                         # пресс неровный: пятна светлее-темнее
    light = 1 + 0.08 * tone + 0.015 * cloud + 0.05 * pores + 0.04 * (edge - 0.5)
    light *= 0.68 + 0.32 * gap ** 0.7
    rgb = BASE[None, None, :] * blur(light, 0.5)[..., None]
    rgb[..., 0] += 5 * warm
    rgb[..., 2] -= 4 * warm
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "stungkir" / "art" / "cork.png"
    cork().save(out, optimize=True)
