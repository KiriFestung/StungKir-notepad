# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""«Обезьяна»: робот-дурак, который добрался до мышки.

В отличие от первого робота окошки у неё не закрываются сами: она заходит в каждое, жмёт там
что попало, пишет в поля ерунду (иногда одну и ту же во все - так совпадают пароли), крутит
списки и ползунки и уходит то через «Готово», то через крестик. Ещё она щёлкает правой
кнопкой где придётся и выбирает случайный пункт меню, жмёт горячие клавиши, таскает карточки
по пробковой доске, бросает главы в другие категории и колонки куда попало.

Проверки те же: никаких ошибок, на экране то, что на диске, мусора в папке нет, окна не
зависают. Длинный прогон:  MONKEY_STEPS=3000 MONKEY_SEED=9 python3 -m unittest stungkir.tests.test_monkey"""

import faulthandler
import os
import random
import sys
import traceback
from collections import Counter

from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import (
    QColor, QContextMenuEvent, QDesktopServices, QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent,
    QShortcut,
)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton, QAbstractItemView, QAbstractSlider, QAbstractSpinBox, QApplication, QColorDialog, QComboBox,
    QCheckBox, QDialog, QFileDialog, QLineEdit, QPushButton, QMenu, QPlainTextEdit, QSpinBox, QTabBar, QTextEdit,
    QToolButton, QWidget,
)

from stungkir import config as C
from stungkir import dialogs
from stungkir import storage as S
from stungkir.tests.helpers import WindowCase, wait
from stungkir.tests.test_fuzz import TEXTS, WEIRD_NAMES, Robot

REAL_ASK_QUESTION = dialogs.ask_question       # настоящий, пока тесты ничего не подменили
PASSWORDS = ["", "1", "пароль", "Кира", "очень длинный пароль с пробелами", "😀"]
KEYS = [Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Delete, Qt.Key_Backspace,
        Qt.Key_Up, Qt.Key_Down, Qt.Key_PageDown, Qt.Key_Home, Qt.Key_End, Qt.Key_Space] + \
       [getattr(Qt, f"Key_F{n}") for n in range(1, 13)] + [Qt.Key_Z, Qt.Key_S, Qt.Key_F, Qt.Key_H, Qt.Key_B, Qt.Key_I,
                                                           Qt.Key_N, Qt.Key_W, Qt.Key_Plus, Qt.Key_Minus, Qt.Key_0]
MODIFIERS = [Qt.NoModifier, Qt.ControlModifier, Qt.ControlModifier | Qt.ShiftModifier, Qt.AltModifier, Qt.ShiftModifier]


def drag_event(kind, pos, mime):
    """Событие перетаскивания. В новых Qt точка - QPointF, в старых (6.8) - только QPoint."""
    try:
        return kind(QPointF(pos), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    except TypeError:
        return kind(QPointF(pos).toPoint(), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)


def own_context_menu(widget):
    """Своё меню по правой кнопке, написанное в программе (стандартные меню Qt ждали бы настоящую мышь)."""
    if widget.contextMenuPolicy() == Qt.CustomContextMenu:
        return True
    for cls in type(widget).__mro__:
        if cls.__module__.startswith("stungkir") and "contextMenuEvent" in vars(cls):
            return True
    return False


def safe_button(button):
    """Кнопка без выпадающего меню: такие Qt открывает своим циклом, который ждёт настоящую мышь."""
    if isinstance(button, QToolButton) and button.menu() is not None:
        return False
    return not (hasattr(button, "menu") and callable(button.menu) and button.menu() is not None)


class Monkey:
    """Подменяет все окошки, меню, перетаскивания и выбор файлов: решения принимает случай."""

    def __init__(self, rng, tmp):
        self.rng, self.tmp = rng, tmp
        self.depth = 0
        self.cooperative = False
        self.password = "пароль"
        self.menu_depth = 0
        self.seen = Counter()                    # в какие окошки заходила
        self.clicked = Counter()                 # какие кнопки жала
        self.fixtures = self._fixtures()

    def _fixtures(self):
        folder = self.tmp / "чужие файлы"
        folder.mkdir()
        files = {"рассказ.txt": "Первая строка.\n\n— Реплика, - сказала Мира.\n".encode("utf-8"),
                 "cp1251.txt": "Старый файл в другой кодировке".encode("cp1251"),
                 "пустой.txt": b"", "сломанный.docx": b"PK\x03\x04 broken", "фото.jpg": b"\xff\xd8\xff\0\0",
                 "текст.rtf": rb"{\rtf1\ansi Hello \par World}", "огромный.md": ("# Глава\n" + "слово " * 20000).encode()}
        for name, data in files.items():
            (folder / name).write_bytes(data)
        (self.tmp / "пустая.scriv").mkdir()
        return folder

    # ---- окошки программы ----
    def fill(self, widget, password=None):
        rng = self.rng
        if isinstance(widget, QLineEdit):
            if not widget.isReadOnly():
                widget.setText(password if password is not None else rng.choice(WEIRD_NAMES + PASSWORDS))
                if rng.random() < 0.2:
                    QTest.keyClick(widget, Qt.Key_Return)
        elif isinstance(widget, (QPlainTextEdit, QTextEdit)):
            if not widget.isReadOnly():
                widget.setPlainText(rng.choice(TEXTS + WEIRD_NAMES))
        elif isinstance(widget, QSpinBox):
            widget.setValue(rng.choice([widget.minimum(), widget.maximum(), rng.randint(widget.minimum(),
                                                                                         widget.maximum())]))
        elif isinstance(widget, QAbstractSpinBox):
            QTest.keyClick(widget, rng.choice([Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp]))
        elif isinstance(widget, QComboBox):
            if widget.count():
                widget.setCurrentIndex(rng.randrange(widget.count()))
            if widget.isEditable() and rng.random() < 0.3:
                widget.setEditText(rng.choice(WEIRD_NAMES))
        elif isinstance(widget, QAbstractSlider):
            widget.setValue(rng.randint(widget.minimum(), widget.maximum()))
        elif isinstance(widget, QTabBar):
            if widget.count():
                widget.setCurrentIndex(rng.randrange(widget.count()))
        elif isinstance(widget, QAbstractButton):
            if safe_button(widget):
                self.clicked[widget.text() or type(widget).__name__] += 1
                widget.click()
        elif isinstance(widget, QAbstractItemView):
            model = widget.model()
            if model is not None and model.rowCount():
                index = model.index(rng.randrange(model.rowCount()), 0)
                widget.setCurrentIndex(index)
                if rng.random() < 0.4:
                    rect = widget.visualRect(index)
                    QTest.mouseDClick(widget.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())
        else:                                    # нарисованное самой программой: кубики, колесо, часы
            if widget.width() > 0 and widget.height() > 0:
                QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier,
                                 QPoint(rng.randrange(widget.width()), rng.randrange(widget.height())))

    def sheet_exec(self, dialog):
        """Вместо Sheet.exec: окошко открыто, обезьяна в нём хозяйничает и как-нибудь уходит."""
        name = type(dialog).__name__
        self.seen[name] += 1
        if self.depth >= 2:                      # окошко из окошка из окошка - хватит
            QTimer.singleShot(0, dialog, dialog.deleteLater)
            return 0
        self.depth += 1
        try:
            dialog.show()
            QApplication.processEvents()
            if self.cooperative:                 # послушный режим: заполнить как надо и нажать главную кнопку
                return self.cooperate(dialog)
            same = self.rng.choice(PASSWORDS) if self.rng.random() < 0.5 else None
            for _ in range(self.rng.randint(0, 9)):
                if not dialog.isVisible():
                    break
                widgets = [w for w in dialog.findChildren(QWidget)
                           if w.isVisible() and w.isEnabled() and w.objectName() != "qt_scrollarea_viewport"]
                if not widgets:
                    break
                widget = self.rng.choice(widgets)
                if os.environ.get("FUZZ_TRACE"):
                    print(f"     [{name}] {type(widget).__name__} {getattr(widget, 'text', lambda: '')()!r:.40}",
                          flush=True)
                self.fill(widget, same if isinstance(widget, QLineEdit) else None)
                QApplication.processEvents()
            if dialog.isVisible():
                way = self.rng.randint(0, 4)
                if way == 0:
                    QTest.keyClick(dialog, Qt.Key_Escape)
                elif way == 1:
                    QTest.keyClick(dialog, Qt.Key_Return)
                elif way == 2:
                    dialog.accept()
                else:
                    dialog.reject()
            if dialog.isVisible():               # не отпустило (неверный пароль и т.п.) - крестик
                dialog.reject()
            return QDialog.result(dialog)
        finally:
            self.depth -= 1
            dialog.hide()
            QTimer.singleShot(0, dialog, dialog.deleteLater)

    def cooperate(self, dialog):
        for field in dialog.findChildren(QLineEdit):
            if field.isVisible() and not field.isReadOnly():
                field.setText(self.password)
        for box in dialog.findChildren(QCheckBox):
            if box.isVisible() and not box.isChecked():
                box.click()
        primary = [b for b in dialog.findChildren(QPushButton) if b.objectName() == "Primary" and b.isVisible()]
        if primary:
            primary[0].click()
        if dialog.isVisible():
            dialog.accept()
        if dialog.isVisible():
            dialog.reject()
        return QDialog.result(dialog)

    # ---- меню ----
    def leaves(self, menu, out):
        menu.aboutToShow.emit()
        for action in menu.actions():
            if action.isSeparator() or not action.isEnabled() or not action.isVisible():
                continue
            if action.menu() is not None:
                self.leaves(action.menu(), out)
            else:
                out.append(action)
        return out

    def watch_popups(self):
        """Меню Qt открывает своим циклом и ждёт настоящую мышь. Поэтому обезьяна каждые
        несколько миллисекунд смотрит, не открылось ли меню, и выбирает в нём пункт сама."""
        self.popup_timer = QTimer()
        self.popup_timer.setInterval(5)
        self.popup_timer.timeout.connect(self.handle_popup)
        self.popup_timer.start()

    def handle_popup(self):
        popup = QApplication.activePopupWidget()
        if popup is None:
            return
        actions = []
        if isinstance(popup, QMenu) and self.menu_depth < 2 and self.rng.random() > 0.1:
            actions = self.leaves(popup, [])
        while QApplication.activePopupWidget() is not None:      # закрыть меню (и подменю)
            QApplication.activePopupWidget().close()
        if not actions:
            return                               # передумала и щёлкнула мимо
        action = self.rng.choice(actions)
        from shiboken6 import isValid
        if not isValid(action):
            return                               # меню, закрываясь, само убрало свои пункты (PySide 6.8)
        self.clicked["меню: " + action.text()] += 1
        if os.environ.get("FUZZ_TRACE"):
            print("     меню:", action.text(), flush=True)
        self.menu_depth += 1
        try:
            action.trigger()
        finally:
            self.menu_depth -= 1

    # ---- перетаскивание за заголовок и т.п. (QDrag) ----
    def drag_exec(self, drag, *_args, **_kwargs):
        source = drag.source()
        window = source.window() if isinstance(source, QWidget) else None
        mime = drag.mimeData() or QMimeData()
        target, local = None, QPointF()
        if window is not None:
            for kind in [QEvent.DragEnter] + [QEvent.DragMove] * self.rng.randint(1, 5):
                pos = QPoint(self.rng.randrange(max(1, window.width())), self.rng.randrange(max(1, window.height())))
                target = window.childAt(pos) or window
                local = QPointF(target.mapFrom(window, pos))
                event_class = QDragEnterEvent if kind == QEvent.DragEnter else QDragMoveEvent
                # прямо в виджет, мимо QApplication::notify: без настоящего QDrag Qt 6.12 иногда падал
                # в своём разборе перетаскивания (у человека мышью такого не бывает); наш код при этом
                # получает те же события
                target.event(drag_event(event_class, local, mime))
        if target is not None and self.rng.random() < 0.6:
            target.event(QDropEvent(local, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier))
            return Qt.MoveAction
        return Qt.IgnoreAction

    # ---- выбор файлов и цвета ----
    def save_name(self, *_args, **_kwargs):
        choice = self.rng.choice(["", self.tmp / "книга.docx", self.tmp / "книга.pdf", self.tmp / "книга",
                                  self.tmp / "нет такой папки" / "книга.txt", C.ROOT / "Черновики" / "книга.txt",
                                  self.tmp / "книга.fb2", self.tmp / "книга.html", self.tmp / "книга.md"])
        return str(choice), ""

    def open_names(self, *_args, **_kwargs):
        files = sorted(self.fixtures.iterdir())
        return [str(p) for p in self.rng.sample(files, self.rng.randint(0, len(files)))], ""

    def folder(self, *_args, **_kwargs):
        return str(self.rng.choice(["", self.tmp / "пустая.scriv", C.ROOT, self.fixtures, self.tmp / "копии",
                                    "/", self.tmp / "нет такой папки"]))

    def color(self, *_args, **_kwargs):
        return QColor(self.rng.choice(["#ff00ff", "#000000", "#ffffff", "not a color", "#123"]))


class MonkeyRobot(Robot):
    def __init__(self, case, w, rng, monkey):
        super().__init__(case, w, rng)
        self.monkey = monkey

    def alive(self):
        if not self.w.isVisible():               # обезьяна закрыла окно (Ctrl+Q, крестик) - открываем снова
            self.restart_closed()
            return False
        return True

    def restart_closed(self):
        from stungkir.window import Notepad
        self.w.deleteLater()
        QApplication.processEvents()
        self.w = Notepad()
        self.w.resize(1200, 800)
        self.w.show()
        self.w.hover_timer.stop()
        self.case.windows.append(self.w)

    def visible(self, kind):
        return [w for w in self.w.findChildren(kind) if w.isVisible() and w.isEnabled()]

    # ---- новые действия ----
    def poke_menu(self):
        self.w.build_more_menu().exec(QPoint(0, 0))

    def press_button(self):
        buttons = [b for b in self.visible(QAbstractButton) if safe_button(b)]
        if buttons:
            button = self.rng.choice(buttons)
            self.monkey.clicked[button.text() or button.toolTip()[:30] or type(button).__name__] += 1
            button.click()

    def right_click(self):
        widgets = [w for w in self.visible(QWidget) if own_context_menu(w)]
        if not widgets:
            return
        widget = self.rng.choice(widgets)
        target = widget.viewport() if isinstance(widget, QAbstractItemView) else widget
        pos = QPoint(self.rng.randrange(max(1, target.width())), self.rng.randrange(max(1, target.height())))
        if isinstance(widget, QAbstractItemView) and widget.model() is not None and widget.model().rowCount() \
                and self.rng.random() < 0.7:
            index = widget.model().index(self.rng.randrange(widget.model().rowCount()), 0)
            pos = widget.visualRect(index).center()
        if widget.contextMenuPolicy() == Qt.CustomContextMenu:
            widget.customContextMenuRequested.emit(pos)
        else:
            QApplication.sendEvent(target, QContextMenuEvent(QContextMenuEvent.Mouse, pos, target.mapToGlobal(pos)))

    def hotkey(self):
        if self.rng.random() < 0.3:
            shortcuts = [s for s in self.w.findChildren(QShortcut) if s.isEnabled()]
            if shortcuts:
                self.rng.choice(shortcuts).activated.emit()
                return
        target = QApplication.focusWidget() or self.w
        if target.window() is not self.w:
            target = self.w
        QTest.keyClick(target, self.rng.choice(KEYS), self.rng.choice(MODIFIERS))

    def mouse_on_board(self):
        """Пробковая доска: взять карточку и утащить, растянуть рамку, двойной щелчок по пустому."""
        view = self.w.view
        if view is None or not hasattr(view, "free"):
            return
        if view.mode != "free" or self.rng.random() < 0.1:
            view.set_mode("free")
        board = view.free
        port = board.viewport()
        items = list(board.items_by_id.values())
        if items and self.rng.random() < 0.7:
            start = board.mapFromScene(self.rng.choice(items).sceneBoundingRect().center())
        else:
            start = QPoint(self.rng.randrange(max(1, port.width())), self.rng.randrange(max(1, port.height())))
        if self.rng.random() < 0.2:
            QTest.mouseDClick(port, Qt.LeftButton, Qt.NoModifier, start)
            return
        modifiers = Qt.ShiftModifier if self.rng.random() < 0.15 else Qt.NoModifier
        point = QPointF(start)

        def send(kind, at, buttons):
            QApplication.sendEvent(port, QMouseEvent(kind, at, port.mapToGlobal(at), Qt.LeftButton, buttons,
                                                     modifiers))
        send(QEvent.MouseButtonPress, point, Qt.LeftButton)
        for _ in range(self.rng.randint(1, 8)):
            point = QPointF(point.x() + self.rng.uniform(-400, 400), point.y() + self.rng.uniform(-400, 400))
            send(QEvent.MouseMove, point, Qt.LeftButton)
        send(QEvent.MouseButtonRelease, point, Qt.NoButton)
        if self.rng.random() < 0.2:
            board.fit()

    def drop_in_tree(self):
        """Бросить главу или категорию куда попало в дереве: на себя, в другую категорию, между."""
        tree = self.w.tree
        items = []

        def walk(item):
            for i in range(item.childCount()):
                items.append(item.child(i))
                walk(item.child(i))
        walk(tree.invisibleRootItem())
        if len(items) < 2:
            return
        source, target = self.rng.choice(items), self.rng.choice(items)
        tree.setCurrentItem(source)
        if self.rng.random() < 0.5:
            rect = tree.visualItemRect(target)
            pos = QPointF(rect.center().x(), rect.top() + self.rng.choice([1, rect.height() // 2, rect.height() - 1]))
            mime = tree.model().mimeData([tree.currentIndex()])
            # обработчики дерева - напрямую: поддельное перетаскивание через QApplication::notify без
            # настоящего QDrag однажды роняло сам Qt (в нём нет «текущей цели» перетаскивания);
            # у человека мышью такого не бывает, а проверить нужно наш код, а не Qt
            enter, move = drag_event(QDragEnterEvent, pos, mime), drag_event(QDragMoveEvent, pos, mime)
            tree.dragEnterEvent(enter)
            tree.dragMoveEvent(move)
            if move.isAccepted() or self.rng.random() < 0.5:
                tree.dropEvent(QDropEvent(pos, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier))
        else:
            from pathlib import Path
            where = self.rng.choice(list(QAbstractItemView.DropIndicatorPosition))
            self.w.on_drop(Path(source.data(0, Qt.UserRole)), Path(target.data(0, Qt.UserRole)), where)

    def password_games(self):
        """Пароль всерьёз: поставить, сменить, новый код, снять - с правильными ответами,
        чтобы дальше обезьяна бесилась уже с зашифрованными главами."""
        if not S.crypto_available():
            return
        monkey = self.monkey
        monkey.cooperative = True
        try:
            if not S.lock_path().exists():
                monkey.password = self.rng.choice(["пароль", "Кира Мира", "😀 ё"])
                self.w.set_password()
            else:
                choice = self.rng.randint(0, 3)
                if choice == 0:
                    self.w.remove_password()
                elif choice == 1:
                    self.w.new_recovery_code()
                else:
                    self.w.change_password()      # оба окна получают один пароль - он и остаётся
        finally:
            monkey.cooperative = False
            if os.environ.get("FUZZ_TRACE"):
                encrypted = sum(S.is_encrypted(p) for p in S.content_files())
                print("     пароль стоит:", S.lock_path().exists(), "зашифровано файлов:", encrypted, flush=True)

    def drag_column(self):
        view = self.w.view
        if view is None or not getattr(view, "columns", None):
            return
        view.set_mode("columns")
        view.drag_column(self.rng.choice(view.columns))

    def click_tree(self):
        tree = self.w.tree
        model = tree.model()
        if not model.rowCount():
            return
        index = model.index(self.rng.randrange(model.rowCount()), 0)
        if self.rng.random() < 0.5 and model.rowCount(index):
            index = model.index(self.rng.randrange(model.rowCount(index)), 0, index)
        rect = tree.visualRect(index)
        click = QTest.mouseDClick if self.rng.random() < 0.3 else QTest.mouseClick
        click(tree.viewport(), Qt.LeftButton, Qt.NoModifier, rect.center())

    ACTIONS = [("restart", 1), ("type_text", 6), ("select_and_kill", 2), ("undo_redo", 2), ("new_things", 3),
               ("open_something", 3), ("save_things", 2), ("look_and_modes", 1), ("toys", 1),
               ("board_games", 2), ("outside_world", 1), ("misc", 4),
               ("poke_menu", 6), ("press_button", 5), ("right_click", 5), ("hotkey", 5), ("mouse_on_board", 4),
               ("drop_in_tree", 3), ("drag_column", 1), ("click_tree", 3), ("password_games", 1)]

    def run(self, steps):
        names = [n for n, weight in self.ACTIONS for _ in range(weight)]
        for number in range(steps):
            if not self.alive():
                continue
            name = self.rng.choice(names)
            self.log.append(name)
            if os.environ.get("FUZZ_TRACE"):
                print(number, name, self.w.path.name if self.w.path else None, flush=True)
            try:
                getattr(self, name)()
                QApplication.processEvents()
            except Exception:                    # noqa: BLE001 - обезьяна ищет именно это
                self.problems.append(f"шаг {number} «{name}»: " + traceback.format_exc(limit=8))
            while QApplication.activePopupWidget() is not None:  # раскрытый список и т.п. - как Esc
                QApplication.activePopupWidget().close()
            if self.w.isVisible():
                self.check()
            if self.problems:
                return number
        return steps


class MonkeyTest(WindowCase):
    def test_monkey(self):
        self._run(int(os.environ.get("MONKEY_SEED", "1")), int(os.environ.get("MONKEY_STEPS", "200")))

    def test_monkey_other_seed(self):
        self._run(int(os.environ.get("MONKEY_SEED", "1")) + 500, int(os.environ.get("MONKEY_STEPS", "200")))

    def _swap(self, owner, name, value):
        self.addCleanup(setattr, owner, name, getattr(owner, name))
        setattr(owner, name, value)

    def _run(self, seed, steps):
        rng = random.Random(seed)
        monkey = Monkey(rng, self.tmp)
        self._swap(dialogs.Sheet, "exec", lambda dialog: monkey.sheet_exec(dialog))
        monkey.watch_popups()
        self.addCleanup(monkey.popup_timer.stop)
        self._swap(QDrag, "exec", lambda drag, *a, **k: monkey.drag_exec(drag))
        self._swap(QFileDialog, "getSaveFileName", staticmethod(monkey.save_name))
        self._swap(QFileDialog, "getOpenFileNames", staticmethod(monkey.open_names))
        self._swap(QFileDialog, "getOpenFileName",
                   staticmethod(lambda *a, **k: ((monkey.open_names()[0][:1] or [""])[0], "")))
        self._swap(QFileDialog, "getExistingDirectory", staticmethod(monkey.folder))
        self._swap(QColorDialog, "getColor", staticmethod(monkey.color))
        launched = []
        self._swap(QDesktopServices, "openUrl", staticmethod(lambda url: launched.append(url) or True))
        from PySide6.QtCore import QProcess
        self._swap(QProcess, "startDetached", staticmethod(lambda *a, **k: launched.append(a) or True))
        self._swap(QApplication, "quit", staticmethod(lambda: None))
        self.answer = None                        # вопросы - настоящие окошки, отвечает обезьяна
        self.patch("ask_question", REAL_ASK_QUESTION)
        errors = []
        old_hook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: errors.append("".join(traceback.format_exception(kind, value, tb)))
        self.addCleanup(setattr, sys, "excepthook", old_hook)
        self.addCleanup(setattr, C, "DATA_DIR", C.DATA_DIR)
        C.DATA_DIR = self.tmp / f"data{seed}"
        self.addCleanup(setattr, C, "BACKUP_DIR", C.BACKUP_DIR)
        faulthandler.dump_traceback_later(int(os.environ.get("MONKEY_TIMEOUT", "900")), exit=True)
        self.addCleanup(faulthandler.cancel_dump_traceback_later)
        w = self.window()
        self.windows = [w]
        robot = MonkeyRobot(self, w, rng, monkey)
        done = robot.run(steps)
        wait(0.05)
        for other in self.windows:
            try:
                other.set_modified(False)
                other.close()
            except RuntimeError:
                pass
        if os.environ.get("FUZZ_TRACE"):
            print("окошки:", dict(monkey.seen), "\nкнопок нажато:", sum(monkey.clicked.values()), flush=True)
        problems = robot.problems + errors
        self.assertEqual(problems, [], f"seed={seed}, шагов {done}, последние: {robot.log[-12:]}\n"
                         + "\n".join(problems[:3]))
        self.assertGreater(len(monkey.seen), 5, "обезьяна почти не заходила в окошки")
