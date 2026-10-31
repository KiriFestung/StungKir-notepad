# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Общее для тестов: временная папка вместо ~/StungKir, подмены окон-вопросов, одно приложение Qt."""
import importlib
import os
import pkgutil
import shutil
import tempfile
import time
import unittest
from pathlib import Path

# тесты не должны трогать настройки, корзину и ярлыки пользователя: свой временный дом
if not os.environ.get("STUNGKIR_TEST_HOME"):
    import atexit
    _home = tempfile.mkdtemp(prefix="stungkir-home-")
    os.environ.update(STUNGKIR_TEST_HOME=_home, HOME=_home, XDG_CONFIG_HOME=f"{_home}/.config",
                      XDG_DATA_HOME=f"{_home}/.local/share", XDG_CACHE_HOME=f"{_home}/.cache")
    atexit.register(shutil.rmtree, _home, ignore_errors=True)

import stungkir  # noqa: E402
from stungkir.core import config as C  # noqa: E402
from stungkir.core import storage as S  # noqa: E402

# все модули пакета, со всех папок (core, ui, …): patch() подменяет имя в каждом, где оно есть
MODULES = [importlib.import_module(m.name) for m in pkgutil.walk_packages(stungkir.__path__, "stungkir.")
           if m.name != "stungkir.__main__" and not m.name.startswith("stungkir.tests")]
_APP = None


def app():
    """Одно QApplication на все тесты, без окна на экране."""
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from stungkir.ui.style import apply_theme
    _APP = QApplication.instance() or QApplication([])
    apply_theme(_APP)
    return _APP


def wait(seconds=0.05):
    end = time.time() + seconds
    while time.time() < end:
        _APP.processEvents()


def speller_available():
    from stungkir.text import editor
    from stungkir.text.editor import Speller
    source = Path(__file__).resolve().parents[2] / "packaging" / "dictionaries"
    if source.is_dir() and source not in editor.DICTIONARY_DIRS:   # из исходников: словарь лежит в packaging
        editor.DICTIONARY_DIRS.append(source)
    return Speller(Path(tempfile.mkdtemp()) / "pwl.txt").available


def crypto_available():
    return S.crypto_available()


class Sandbox(unittest.TestCase):
    """Каждый тест работает в своей временной папке и ничего не трогает у пользователя."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="stungkir-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        for name, value in (("ROOT", self.tmp / "StungKir"), ("OLD_ROOT", self.tmp / "Блокнот"),
                            ("BACKUP_DIR", self.tmp / "backups"), ("ERROR_LOG", self.tmp / "errors.log")):
            self.addCleanup(setattr, C, name, getattr(C, name))
            setattr(C, name, value)
        C.ROOT.mkdir()
        self.addCleanup(C.set_palette, C.palette())      # тесты цветов не должны перекрашивать другие
        self.addCleanup(setattr, S, "CRYPTO", S.CRYPTO)
        S.CRYPTO = None
        self.addCleanup(setattr, S, "_problem_hook", S._problem_hook)
        self.problems = []
        S._problem_hook = self.problems.append

    def patch(self, name, value):
        """Подменяет функцию или класс во всех модулях пакета, где он используется."""
        hit = False
        for module in MODULES:
            if name in vars(module):
                self.addCleanup(setattr, module, name, vars(module)[name])
                setattr(module, name, value)
                hit = True
        if not hit:
            raise AttributeError(name)

    def chapter(self, category, name, text):
        folder = C.ROOT / category
        folder.mkdir(exist_ok=True)
        path = folder / f"{name}.txt"
        path.write_text(text, encoding="utf-8", newline="\n")
        return path


class WindowCase(Sandbox):
    """Тест с главным окном. Вопросы и предупреждения не показываются, а записываются."""

    def setUp(self):
        super().setUp()
        app()
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QMessageBox
        settings = QSettings(C.APP_ID, C.APP_ID)
        settings.clear()                           # позиции, последний файл и прочее от прошлых тестов
        settings.setValue("intro_seen", "true")    # знакомство с панелями в тестах не нужно
        self.messages = []
        self.patch("show_warning", lambda parent, title, text: self.messages.append((title, text)))
        self.patch("show_error", lambda parent, title, text: self.messages.append((title, text)))
        self.answer = QMessageBox.Discard
        self.patch("ask_question", lambda *a, **k: self.answer)

    def window(self):
        from stungkir.ui.window import Notepad
        w = Notepad()
        w.resize(1300, 800)
        w.show()
        w.hover_timer.stop()
        wait(0.1)

        def close():
            from PySide6.QtCore import QCoreApplication, QEvent
            from PySide6.QtWidgets import QApplication
            try:
                w.set_modified(False)
                w.close()
            except RuntimeError:                   # окно уже закрыл и удалил сам тест («перезапуск»)
                pass
            # окна и окошки теста удаляем совсем, иначе следующие тесты перекрашивают и их
            for widget in QApplication.topLevelWidgets():
                widget.close()
                widget.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            wait(0.02)
        self.addCleanup(close)
        return w
