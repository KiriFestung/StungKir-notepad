# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Звуки кубиков и монетки, рулетки, антистресса и печатной машинки. Сами звуки синтезированы
(packaging/sounds/make_sounds.py).

Играет их отдельная маленькая программа системы (pw-play, paplay или aplay; на Windows - winsound),
а не сам блокнот: если со звуком в системе что-то не так, падает она, а не окно с текстом.
Нет ни одной - блокнот просто молчит."""

import array
import os
import random
import shutil
import sys
import wave
from pathlib import Path

from PySide6.QtCore import QProcess

from . import config as C

FOLDER = Path(__file__).resolve().parent / "sounds"
VOLUMES = {"Без звука": 0.0, "Тихо": 0.3, "Обычно": 0.6, "Громко": 0.95}
DEFAULT_VOLUME = "Обычно"
HITS = ["die_hit_1", "die_hit_2", "die_hit_3", "die_hit_4"]
# имя без номера - каждый раз случайный из нескольких похожих, чтобы стук не был одинаковым
VARIANTS = {"die_hit": HITS, "bone_hit": ["bone_hit_1", "bone_hit_2", "bone_hit_3"],
            "oak_hit": ["oak_hit_1", "oak_hit_2", "oak_hit_3"]}
PLAYERS = ("pw-play", "paplay", "aplay")


def cache_folder():
    return C.cache_dir() / "sounds"


def scaled(name, level):
    """Файл звука нужной громкости (громкость «запекается» в файл: так умеет любой проигрыватель)."""
    step = max(1, min(10, round(level * 10)))
    target = cache_folder() / f"{name}-{step}.wav"
    if target.is_file():
        return target
    source = FOLDER / f"{name}.wav"
    try:
        with wave.open(str(source), "rb") as w:
            params = w.getparams()
            samples = array.array("h", w.readframes(w.getnframes()))
        if sys.byteorder == "big":
            samples.byteswap()
        factor = step / 10
        samples = array.array("h", (int(s * factor) for s in samples))
        if sys.byteorder == "big":
            samples.byteswap()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        with wave.open(str(temporary), "wb") as w:
            w.setparams(params)
            w.writeframes(samples.tobytes())
        os.replace(temporary, target)
    except (OSError, wave.Error, EOFError):
        return None
    return target


class Sounds:
    """play("die_hit", сила 0..1)."""

    def __init__(self, parent=None, volume=DEFAULT_VOLUME):
        self.volume = VOLUMES.get(volume, VOLUMES[DEFAULT_VOLUME])
        self.played = []                                         # что звучало - для проверок
        self.quiet = bool(os.environ.get("STUNGKIR_TEST_HOME"))  # проверки не шумят
        self._player = None

    def set_volume(self, name):
        self.volume = VOLUMES.get(name, VOLUMES[DEFAULT_VOLUME])

    def player(self):
        if self._player is None:
            if sys.platform.startswith("win"):
                self._player = "winsound"
            else:
                self._player = next((p for p in PLAYERS if shutil.which(p)), "")
        return self._player

    def play(self, name, strength=1.0, volume=None):
        """volume - своя громкость (у машинки она отдельная от кубиков), иначе общая."""
        if name in VARIANTS:
            name = random.choice(VARIANTS[name])
        level = max(0.0, min(1.0, (self.volume if volume is None else volume) * strength))
        self.played.append((name, round(level, 2)))
        if level <= 0.04 or self.quiet or not self.player():
            return
        path = scaled(name, level)
        if path is None:
            return
        if self._player == "winsound":
            try:
                import winsound
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            except (ImportError, RuntimeError):
                pass
            return
        args = [str(path)] if self._player != "aplay" else ["-q", str(path)]
        QProcess.startDetached(self._player, args)
