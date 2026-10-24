# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Все копии иконки - из stungkir/art/app-icon.png: ICO для Windows, SVG для Flatpak, значки Android
(передний слой, обычный и круглый со светлым фоном, заставка). Ласка встаёт ровно туда же, где была:
место и размер берутся из нынешних файлов. Однотонный значок Android (силуэт) не трогается.
python3 packaging/icons.py"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RES = ROOT / "android" / "app" / "src" / "main" / "res"
CREAM = (243, 236, 219)              # фон значка (icon_bg)


def solid_box(image, threshold=128):
    return image.getchannel("A").point(lambda v: 255 if v > threshold else 0).getbbox()


def placed(icon, box, size):
    """Иконка на прозрачном холсте size, ласка - в рамке box (по плотной части)."""
    src = solid_box(icon)
    scale = (box[3] - box[1]) / (src[3] - src[1])
    small = icon.resize((round(icon.width * scale), round(icon.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(small, (round(box[0] - src[0] * scale), round(box[1] - src[1] * scale)))
    return canvas


def relaunch(path, icon):
    """Обычный и круглый значок: старую ласку закрашиваем фоном, сверху - новую на её место."""
    old = Image.open(path).convert("RGBA")
    a = np.asarray(old).astype(float)
    bright, dull = a[..., :3].max(-1), a[..., :3].min(-1)
    differs = ((bright - dull) / np.maximum(bright, 1) > 0.4) & (a[..., 3] == 255)   # ласка яркая, фон и край блёклые
    mask = Image.fromarray((differs * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    box = Image.fromarray((differs * 255).astype(np.uint8)).getbbox()
    clean = old.copy()
    clean.paste(Image.new("RGBA", old.size, CREAM + (255,)), (0, 0), mask)
    clean.putalpha(old.getchannel("A"))
    clean.alpha_composite(placed(icon, box, old.size))
    clean.save(path, optimize=True)


def main():
    icon = Image.open(ROOT / "stungkir" / "art" / "app-icon.png").convert("RGBA")
    icon.save(ROOT / "packaging" / "windows" / "stungkir.ico",
              sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    from stungkir.icons import ICON_SVG
    (ROOT / "packaging" / "flatpak" / "page.codeberg.kirifestung.StungKir.svg").write_text(
        ICON_SVG, encoding="utf-8", newline="\n")
    for folder in sorted(RES.glob("mipmap-*dpi")):
        fore = folder / "ic_launcher_foreground.png"
        old = Image.open(fore).convert("RGBA")
        placed(icon, solid_box(old), old.size).save(fore, optimize=True)
        for name in ("ic_launcher.png", "ic_launcher_round.png"):
            relaunch(folder / name, icon)
    splash = RES / "drawable-nodpi" / "splash_icon.png"
    old = Image.open(splash).convert("RGBA")
    placed(icon, solid_box(old), old.size).save(splash, optimize=True)


if __name__ == "__main__":
    main()
