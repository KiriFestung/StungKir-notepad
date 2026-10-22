# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""«Робот-дурак»: тысячи случайных глупых действий подряд - странные имена, удаление открытого,
правки снаружи, пароли, темы, кубики, доска... После каждого шага: ошибок нет, сохранённое
совпадает с тем, что на экране, мусорных файлов нет.

Обычный прогон - короткий. Длинный:  FUZZ_STEPS=5000 FUZZ_SEED=7 python3 -m unittest stungkir.tests.test_fuzz"""

import os
import random
import sys
import traceback

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from stungkir import config as C
from stungkir import dialogs
from stungkir import storage as S
from stungkir.tests.helpers import WindowCase, wait

WEIRD_NAMES = [
    "", " ", "   ", ".", "..", "...", "/", "\\", "a/b", "con", "CON", "nul", "Com1", "LPT9", "aux.txt",
    "Глава", "глава", "ГЛАВА", "Глава 1", "Глава 1.txt", "Глава.", "Глава ", " Глава", ".скрытая", "-",
    "😀 эмодзи", "имя\nс переводом", "таб\tуляция", "очень " * 60, "ы" * 300, "Ёжик", "ё", "?", "*", "\"кавычки\"",
    "<>", "|", "%s %n", "${HOME}", "~", "Новая категория", "Черновики", "План.board", "x" * 120, "Пример · Мир",
    "​невидимка", "‮перевёрнутое", "a\x00b", "COM¹", "con.txt", "Глава 1 (из корзины)", "Mixed Латиница",
]
TEXTS = [
    "", "а", "Туман над рекой. ", "— Реплика, - сказала Кира.\n", "\n\n\n", "Latin text in Russian book. ",
    "😀🦊🎲", "*курсив* **жирный** [пометка] ", "# Заголовок\n", "\t\t", "слово " * 400, "x" * 5000,
    "́́", "\r\n\r\n", "Ё" * 50, "<html><b>не html</b></html>", "\\n \\t %s", "  ",
]


class Robot:
    def __init__(self, case, w, rng):
        self.case, self.w, self.rng = case, w, rng
        self.log = []
        self.problems = []

    # ---- что под рукой ----
    def files(self, everything=True):
        out = []
        for folder in [p for p in C.ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")]:
            out += S.files_in(folder, everything=everything)
        return out

    def folders(self):
        return [p for p in C.ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")]

    def any_path(self):
        choices = self.files() + self.folders()
        return self.rng.choice(choices) if choices else None

    # ---- действия ----
    def type_text(self):
        if self.w.view is not None:
            return
        cursor = self.w.editor.textCursor()
        cursor.setPosition(self.rng.randint(0, max(0, self.w.editor.document().characterCount() - 1)))
        self.w.editor.setTextCursor(cursor)
        text = self.rng.choice(TEXTS)
        if self.rng.random() < 0.5:
            self.w.editor.insertPlainText(text)
        else:
            for ch in text[:40]:                   # как с клавиатуры, по букве
                key = Qt.Key_Return if ch == "\n" else Qt.Key_unknown
                for kind in (QEvent.KeyPress, QEvent.KeyRelease):
                    QApplication.sendEvent(self.w.editor, QKeyEvent(kind, key, Qt.NoModifier, ch))

    def select_and_kill(self):
        if self.w.view is not None:
            return
        doc_len = self.w.editor.document().characterCount() - 1
        cursor = self.w.editor.textCursor()
        if self.rng.random() < 0.4:
            self.w.editor.selectAll()
        else:
            a, b = sorted(self.rng.randint(0, max(0, doc_len)) for _ in range(2))
            cursor.setPosition(a)
            cursor.setPosition(b, cursor.MoveMode.KeepAnchor)
            self.w.editor.setTextCursor(cursor)
        key = self.rng.choice([Qt.Key_Delete, Qt.Key_Backspace, Qt.Key_A, Qt.Key_Space])
        QTest.keyClick(self.w.editor, key)
        if self.rng.random() < 0.3:
            if getattr(self.w.toast, "_action", None) and self.w.toast.isVisible():
                QTest.mouseClick(self.w.toast, Qt.LeftButton)          # «нажми сюда - вернуть»

    def undo_redo(self):
        for _ in range(self.rng.randint(1, 25)):
            (self.w.editor.undo if self.rng.random() < 0.7 else self.w.editor.redo)()

    def new_things(self):
        self.rng.choice([self.w.new_file, self.w.new_category, self.w.new_board, self.w.new_table,
                         self.w.new_timeline])()

    def rename_something(self):
        path = self.any_path()
        if path is not None:
            self.w.rename(path)

    def delete_something(self):
        path = self.any_path()
        if path is not None:
            self.w.delete(path)

    def open_something(self):
        path = self.any_path()
        if path is not None and path.is_file():
            self.w.open_path(path)

    def save_things(self):
        self.rng.choice([self.w.save, self.w.save_everything, self.w.autosave, lambda: self.w.write_journal(force=True)])()

    def look_and_modes(self):
        choice = self.rng.randint(0, 8)
        if choice == 0:
            self.w.apply_palette(C.THEMES[self.rng.choice(list(C.THEMES))])
        elif choice == 1:
            self.w.set_focus_mode(self.rng.random() < 0.5)
        elif choice == 2:
            self.w.set_typewriter(self.rng.random() < 0.5)
        elif choice == 3:
            self.w.set_forward_only(self.rng.random() < 0.5)
        elif choice == 4:
            self.w.set_zen(self.rng.random() < 0.5)
        elif choice == 5:
            self.w.zoom(self.rng.choice([-30, -1, 1, 30]))
        elif choice == 6:
            self.w.toggle_punctuation()
        elif choice == 7:
            self.w.set_night_mode(self.rng.choice(["auto", "on", "off"]))
        else:
            self.w.insert_symbol(self.rng.choice(["—", "«»", "…", "́", "ё", "[ ]", "**", "*"]))

    def toys(self):
        choice = self.rng.randint(0, 2)
        if choice == 0:
            self.w.toggle_timer()
        elif choice == 1:
            self.w.add_to_history(f"d20: {self.rng.randint(1, 20)}")
        else:
            self.w.history.clear()

    def board_games(self):
        view = self.w.view
        if view is None or not hasattr(view, "free"):
            return
        choice = self.rng.randint(0, 4)
        if choice == 0:
            view.set_mode(self.rng.choice(["free", "columns"]))
        elif choice == 1 and view.mode == "free":
            view.new_free_card(QPointF(self.rng.uniform(-500, 2000), self.rng.uniform(-500, 2000)))
        elif choice == 2 and view.columns:
            view.new_card(self.rng.choice(view.columns))
        elif choice == 3 and view.mode == "free" and view.free.items_by_id:
            item = self.rng.choice(list(view.free.items_by_id.values()))
            self.rng.choice([lambda: view._free_delete(item), lambda: view.free.start_link(item),
                             lambda: view.free.finish_link(item), lambda: view.free.remove_links(item),
                             lambda: item.setPos(self.rng.uniform(-3000, 3000), self.rng.uniform(-3000, 3000))])()
        elif choice == 4 and view.columns:
            view.remove_column(self.rng.choice(view.columns))

    def outside_world(self):
        """Кто-то снаружи (синхронизация, файловый менеджер) трогает файлы."""
        files = [f for f in self.files() if f.is_file()]
        choice = self.rng.randint(0, 5)
        if choice == 0 and files:
            S.save_text(self.rng.choice(files), self.rng.choice(TEXTS))
        elif choice == 1 and files:
            self.rng.choice(files).unlink()
        elif choice == 2 and files:
            f = self.rng.choice(files)
            try:
                f.rename(f.with_name("переименовано снаружи " + str(self.rng.randint(0, 99)) + f.suffix))
            except OSError:
                pass
        elif choice == 3 and files:
            f = self.rng.choice(files)
            f.with_name(f.stem + ".sync-conflict-20261015-101010-ABC" + f.suffix).write_text("чужая версия",
                                                                                         encoding="utf-8", newline="\n")
        elif choice == 4 and self.folders():
            (self.rng.choice(self.folders()) / "фото.jpg").write_bytes(b"\xff\xd8\xff\0\0junk")
        else:
            (self.rng.choice(self.folders()) / ".order").write_text("{сломано", encoding="utf-8", newline="\n") \
                if self.folders() else None
        self.w.check_external()
        self.w.refresh_tree()

    def misc(self):
        action = self.rng.choice([
            self.w.show_speaker_check, self.w.show_reply_stats, self.w.show_markers, self.w.show_presence,
            self.w.show_rhythm, self.w.show_trash, self.w.show_random, self.w.undo_replace,
            self.w.undo_big_erase, self.w.check_conflicts, self.w.hide_global_search, self.w.toggle_side,
            self.w.show_stats, lambda: self.w.offer_recovery(lambda _t: self.rng.random() < 0.5),
            self.w.add_sample, self.w.drop_sample, self.w.copy_all, self.w.rebuild_lore,
            lambda: self.w.track_name(self.rng.choice(WEIRD_NAMES)),
            lambda: self.w.add_crutch(self.rng.choice(WEIRD_NAMES + TEXTS)),
            lambda: self.w.edit_note(self.rng.randrange(len(self.w.notes_margin.notes)))
            if self.w.notes_margin.notes else None,
            self.w.set_goal, self.w.set_chapter_goal,
            lambda: self.w.toggle_lore_category(self.rng.choice(self.folders())) if self.folders() else None,
            lambda: self.w.open_beside(self.any_path()),
            self.w.close_side, self.w.check_term_spelling, self.w.show_versions,
            lambda: self.w.note_for_block(self.w.editor.document().findBlockByNumber(
                self.rng.randint(0, self.w.editor.document().blockCount()))),
            lambda: self.w.toggle_markup(self.rng.choice(["*", "**", "[]"])), self.w.toggle_stress,
        ])
        if os.environ.get("FUZZ_TRACE"):
            print("   misc:", getattr(action, "__name__", action), "path:", self.w.path, flush=True)
        action()

    def restart(self):
        """Закрыть блокнот (на вопрос «сохранить?» отвечаем как попало) и открыть заново."""
        if os.environ.get("FUZZ_TRACE"):
            for f in self.files():
                print("     ", f.relative_to(C.ROOT), f.stat().st_size if f.exists() else "-", flush=True)
        from stungkir.window import Notepad
        before = {f: S.read_text(f) for f in self.files(everything=False) if f.is_file() and S.is_text_file(f)
                  and f.suffix == ".txt"}
        unsaved = self.w.path if self.w.is_modified() else None
        self.w.close()
        if self.w.isVisible():                     # «Отмена» на вопросе - окно осталось
            return
        self.w.deleteLater()
        QApplication.processEvents()
        if os.environ.get("FUZZ_TRACE"):
            print("     closed; last_file =", self.w.settings.value("last_file"), flush=True)
            for f in self.files():
                print("     ", f.relative_to(C.ROOT), f.stat().st_size if f.exists() else "-", flush=True)
        self.w = Notepad()
        self.w.resize(1200, 800)
        self.w.show()
        self.w.hover_timer.stop()
        self.case.windows.append(self.w)
        QApplication.processEvents()
        for f, text in before.items():             # всё, что было на диске, на месте
            if f != unsaved and f.exists() and S.read_text(f) != text:
                self.problems.append(f"после перезапуска изменилась глава {f.name!r}")

    ACTIONS = [("restart", 1), ("type_text", 9), ("select_and_kill", 4), ("undo_redo", 3), ("new_things", 4),
               ("rename_something", 3), ("delete_something", 2), ("open_something", 6), ("save_things", 4),
               ("look_and_modes", 3), ("toys", 2), ("board_games", 3), ("outside_world", 2), ("misc", 3)]

    # ---- проверки после каждого шага ----
    def check(self):
        w = self.w
        stray = [p for p in C.ROOT.rglob("*.tmp")]
        if stray:
            self.problems.append(f"остались временные файлы: {stray[:3]}")
        if w.path is not None and w.view is None and not w.is_modified() and w.path.exists():
            try:
                disk = S.read_text(w.path)
            except (OSError, S.LockedFile) as error:
                self.problems.append(f"не читается открытая глава: {error}")
                return
            screen = w.editor.toPlainText()

            def lines(text):                      # переводы строк Qt показывает одинаково, это не потеря
                for sep in ("\r\n", "\r", "\u2028", "\u2029"):
                    text = text.replace(sep, "\n")
                return text
            if lines(disk) != lines(screen):
                self.problems.append(f"на экране не то, что на диске: {w.path.name!r} "
                                     f"(диск {len(disk)} знаков {disk[:60]!r}, экран {len(screen)} {screen[:60]!r})")

    def run(self, steps):
        names = [n for n, weight in self.ACTIONS for _ in range(weight)]
        for number in range(steps):
            name = self.rng.choice(names)
            self.log.append(name)
            if os.environ.get("FUZZ_TRACE"):
                state = ""
                if self.w.path is not None and self.w.view is None:
                    state = f" [{self.w.path.name} mod={self.w.is_modified()} {self.w.editor.toPlainText()[:30]!r}]"
                print(number, name, state, flush=True)
            try:
                getattr(self, name)()
                QApplication.processEvents()
            except Exception:                       # noqa: BLE001 - робот ищет именно это
                self.problems.append(f"шаг {number} «{name}»: " + traceback.format_exc(limit=6))
            self.check()
            if self.problems:
                return number
        return steps


class FakeCard:
    deleted = False

    def __init__(self, *_a, **_k):
        pass

    def exec(self):
        return True

    def card_data(self):
        return {"title": "Робот", "text": "был здесь", "color": "purple", "chapter": ""}


def fake_note(rng):
    class FakeNote:
        def __init__(self, *_a, **_k):
            self.action = rng.choice(["save", "save", "delete", None])

        def exec(self):
            return True

        def text(self):
            return rng.choice(TEXTS)
    return FakeNote


class FuzzTest(WindowCase):
    def test_robot(self):
        self._run(int(os.environ.get("FUZZ_SEED", "1")), int(os.environ.get("FUZZ_STEPS", "250")))

    def test_robot_other_seed(self):
        self._run(int(os.environ.get("FUZZ_SEED", "1")) + 1000, int(os.environ.get("FUZZ_STEPS", "250")))

    def _run(self, seed, steps):
        rng = random.Random(seed)
        answers = [QMessageBox.Yes, QMessageBox.No, QMessageBox.Save, QMessageBox.Discard, QMessageBox.Cancel]
        self.patch("ask_text", lambda *a, **k: (rng.choice(WEIRD_NAMES), rng.random() < 0.9))
        self.patch("ask_question", lambda *a, **k: rng.choice(answers))
        self.patch("ask_item", lambda parent, title, label, items, *a, **k: (rng.choice(items) if items else "",
                                                                           rng.random() < 0.9))
        self.patch("ask_int", lambda *a, **k: (rng.choice([0, 1, 250, 10 ** 6]), rng.random() < 0.9))
        self.patch("CardDialog", FakeCard)
        self.patch("NoteDialog", fake_note(rng))
        original_exec = dialogs.Sheet.exec
        dialogs.Sheet.exec = lambda self: 0               # остальные окна сразу закрываются «Отменой»
        self.addCleanup(setattr, dialogs.Sheet, "exec", original_exec)
        errors = []
        old_hook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: errors.append("".join(traceback.format_exception(kind, value, tb)))
        self.addCleanup(setattr, sys, "excepthook", old_hook)
        self.addCleanup(setattr, C, "DATA_DIR", C.DATA_DIR)
        C.DATA_DIR = self.tmp / f"data{seed}"
        if os.environ.get("FUZZ_TRACE"):
            original_write = S.write_atomic

            def spy(path, data):
                if path.exists() and path.stat().st_size and not data.strip():
                    print("     !!! пустая запись в", path.name, "".join(traceback.format_stack(limit=9)), flush=True)
                return original_write(path, data)
            self.patch("write_atomic", spy)
        w = self.window()
        self.windows = []
        robot = Robot(self, w, rng)
        done = robot.run(steps)
        wait(0.05)
        for other in self.windows:                 # окна после «перезапусков»
            try:
                other.set_modified(False)
                other.close()
            except RuntimeError:
                pass
        problems = robot.problems + errors
        self.assertEqual(problems, [], f"seed={seed}, шагов {done}, последние: {robot.log[-12:]}\n"
                         + "\n".join(problems[:3]))
