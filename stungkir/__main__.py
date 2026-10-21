# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Запуск: python3 -m stungkir (или напрямую этим файлом)."""
import sys
from pathlib import Path

if __package__ in (None, ""):
    # запущен как файл: добавляем папку над пакетом, чтобы работали импорты пакета
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stungkir.app import main
else:
    from .app import main

sys.exit(main())
