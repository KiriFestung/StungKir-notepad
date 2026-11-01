# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Запуск всех автотестов: python3 -m stungkir --test
Тесты работают во временных папках и не трогают тексты, настройки и копии пользователя."""
import os
import sys
import unittest
from pathlib import Path


MODULES = ["test_board", "test_plan", "test_publish", "test_colors", "test_corkboard", "test_crutches", "test_deadline", "test_animation", "test_dice", "test_editing", "test_export", "test_fuzz", "test_guards", "test_hostile", "test_import", "test_language", "test_layout", "test_look", "test_lore", "test_monkey", "test_password", "test_presence", "test_replace", "test_rhythm", "test_safety",
           "test_snapshots", "test_speakers", "test_speech", "test_speed", "test_storage", "test_templates", "test_timeline", "test_toys", "test_trash", "test_text", "test_two_devices", "test_window"]


REPORT = Path(os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp") / "stungkir-test-report.txt"


def main(verbose=False):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # у оконной сборки для Windows нет консоли: отчёт пишется в файл (его читает скрипт сборки)
    if sys.stdout is None or sys.stderr is None:
        report = open(REPORT, "w", encoding="utf-8")
        sys.stdout = sys.stderr = report
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parent.parent))
    import importlib
    importlib.import_module("stungkir.tests.helpers")   # подменяет дом до создания окон
    # в готовой сборке (Windows) файлов тестов на диске нет, поэтому список модулей явный
    suite = unittest.defaultTestLoader.loadTestsFromNames([f"stungkir.tests.{name}" for name in MODULES])
    result = unittest.TextTestRunner(verbosity=2 if verbose else 1).run(suite)
    skipped = len(result.skipped)
    if result.wasSuccessful():
        print(f"\nВсё в порядке: проверок {result.testsRun}" + (f", пропущено {skipped}" if skipped else ""))
        return 0
    print(f"\nЕсть проблемы: ошибок {len(result.errors)}, не прошло {len(result.failures)}")
    return 1


if __name__ == "__main__":
    sys.exit(main("-v" in sys.argv))
