# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Запуск программы."""

import os
import sys
from pathlib import Path
from PySide6.QtGui import QFontDatabase, QIcon, QPixmap
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from .core import config as C
from .ui.icons import ICON_SVG
from .ui.style import apply_theme
from .core.storage import (log_error, crypto_available, install_launcher, lock_path, lock_problem, lock_version,
    migrate_old_root, unlock)
from .ui.dialogs import PasswordDialog, ask_question, show_error, show_warning
from .books.sample import create_sample, is_fresh
from .core.safety import (clean_temp_files, crashed_last_time, enable_fault_log, install_crash_guard, mark_session,
    single_instance)
from .ui.window import Notepad


def load_bundled_fonts():
    """Шрифты для текста, которые едут с программой: Literata и PT Serif (OFL), а в сборке
    для Windows ещё и DejaVu (на Linux он уже в системе)."""
    folder = Path(__file__).resolve().parent / "fonts"
    if folder.is_dir():
        for font in sorted(folder.glob("*.ttf")):
            QFontDatabase.addApplicationFont(str(font))


def windows_font_engine():
    """На Windows буквы рисует тот же FreeType, что и на Linux: мягче, без цветной каймы ClearType -
    иначе шрифт выглядит резче и «плывёт». Если QT_QPA_PLATFORM задан вручную - не трогаем."""
    if sys.platform == "win32" and not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "windows:fontengine=freetype"


def main():
    windows_font_engine()
    if "--test" in sys.argv:
        from .tests.run import main as run_tests
        return run_tests("-v" in sys.argv)
    if "--screens" in sys.argv:                # снимки окон для проверки вида (на GitHub - на Windows)
        from .tests.screens import main as screens
        index = sys.argv.index("--screens")
        return screens(sys.argv[index + 1] if len(sys.argv) > index + 1 else "screens")
    if "--install-only" in sys.argv:
        install_launcher()
        return 0
    migration_error = migrate_old_root()
    C.load_config()
    app = QApplication(sys.argv)
    enable_fault_log()
    instance = single_instance()
    if instance is None:
        apply_theme(app)
        show_warning(None, C.APP_NAME, "StungKir уже открыт.\n\nДва окна на одни и те же главы затирали бы "
                     "правки друг друга, поэтому второе не открывается. Окно может быть свёрнуто "
                     "или на другом рабочем столе.")
        return 0
    crashed = crashed_last_time()
    app.setApplicationName(C.APP_ID)
    app.setApplicationDisplayName(C.APP_NAME)
    app.setDesktopFileName(os.environ.get("FLATPAK_ID") or C.APP_ID)
    load_bundled_fonts()
    icon = install_launcher()
    from .ui.icons import APP_ICON_PNG
    if APP_ICON_PNG.is_file():
        app.setWindowIcon(QIcon(str(APP_ICON_PNG)))   # ласка: картинка в пакете, чёткая в любом размере
    elif icon:
        app.setWindowIcon(QIcon(str(icon)))      # прямо файл: по имени система может отдать старую
    else:
        pixmap = QPixmap()
        pixmap.loadFromData(ICON_SVG.encode("utf-8"), "SVG")
        app.setWindowIcon(QIcon(pixmap))
    apply_theme(app)
    if migration_error is not None:
        show_error(None, C.APP_NAME, f"Не всё перенеслось из «{C.OLD_ROOT}» в «{C.ROOT}». Старая папка "
                   f"осталась на месте, ничего не удалено.\n\n{migration_error}")
    if C.ROOT.is_dir():
        from .core.storage import tidy_root
        tidy_root()                     # служебные файлы прошлых версий - в одну скрытую папку .stungkir
    if lock_path().exists() and lock_problem() is not None:
        show_error(None, C.APP_NAME, f"Файл ключа {lock_path()} повреждён, без него зашифрованные тексты "
                   "не открыть.\n\nВозьми файл ключа из последней резервной копии (архив в "
                   f"{C.BACKUP_DIR}: внутри StungKir/.stungkir/lock.json, в старых копиях - StungKir/.lock.json) "
                   "и положи его на место.\n\n"
                   f"Подробности: {lock_problem()}")
        return 1
    if lock_path().exists():
        if not crypto_available():
            show_error(None, C.APP_NAME, "Тексты зашифрованы, а библиотеки cryptography нет.\n"
                                 "Запусти install.sh ещё раз.")
            return 1
        from .ui.security import offer_recovery_code, recover_with_code
        dialog = PasswordDialog(None, C.APP_NAME, "Введи пароль, чтобы открыть тексты.", check=unlock,
                                recover=recover_with_code)
        if not dialog.exec():
            return 0
        if not dialog.recovered and lock_version() == 1:
            offer_recovery_code(None, dialog.password)      # пароль из прошлой версии - даём код
    from PySide6.QtCore import QSettings
    settings = QSettings(C.APP_ID, C.APP_ID)
    if is_fresh() and settings.value("sample_offered", "false") != "true":
        # самый первый запуск: пример-проект, чтобы было что потрогать (только один раз)
        settings.setValue("sample_offered", "true")
        try:
            readme = create_sample()
            settings.setValue("last_file", str(readme))
        except OSError as error:
            log_error("Пример не создался", error)
    clean_temp_files()                        # обрывки записи после сбоя
    mark_session(True)                        # пропадёт при нормальном закрытии
    window = Notepad()
    window.show()
    install_crash_guard(lambda: window)
    if crashed:
        log_error("Прошлый запуск закрылся аварийно")

    def recover():
        def ask(text):
            return ask_question(window, "Восстановление", text, QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.Yes) == QMessageBox.Yes
        if not window.offer_recovery(ask) and crashed:
            window.toast.show_message("Прошлый раз блокнот закрылся аварийно, но всё было сохранено", 4000)
    QTimer.singleShot(600, window, recover)
    code = app.exec()
    mark_session(False)                       # закрылись сами, а не упали
    instance.unlock()
    return code


def run():
    """Точка входа для pipx и сборок: код возврата - системе."""
    sys.exit(main())
