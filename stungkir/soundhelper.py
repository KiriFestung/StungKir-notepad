# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Отдельная маленькая программа, которая играет звуки через Qt - когда в системе нет pw-play,
paplay и aplay (так во Flatpak). Блокнот запускает её один раз и пишет ей пути к .wav по строке.
Отдельно - нарочно: если звук в системе сломан и Qt падает, падает она, а не окно с текстом.
Закрылся блокнот (кончился ввод) - выходит и она. Ничего из блокнота не импортирует."""

import sys

VOICES = 4


def main():
    from PySide6.QtCore import QCoreApplication, QSocketNotifier, QUrl
    from PySide6.QtMultimedia import QSoundEffect

    app = QCoreApplication(sys.argv[:1])
    effects = {}
    buffer = bytearray()

    def play(path):
        voices = effects.setdefault(path, [])
        effect = next((e for e in voices if not e.isPlaying()), None)
        if effect is None and len(voices) < VOICES:
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(path))
            effect.setVolume(1.0)
            voices.append(effect)
        if effect is None:
            effect = voices[0]
            effect.stop()
        effect.play()

    def ready():
        import os
        try:
            chunk = os.read(sys.stdin.fileno(), 4096)
        except OSError:
            chunk = b""
        if not chunk:
            app.quit()
            return
        buffer.extend(chunk)
        while b"\n" in buffer:
            line, _, rest = bytes(buffer).partition(b"\n")
            buffer[:] = rest
            path = line.decode("utf-8", "replace").strip()
            if path:
                play(path)

    notifier = QSocketNotifier(sys.stdin.fileno(), QSocketNotifier.Read)
    notifier.activated.connect(ready)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
