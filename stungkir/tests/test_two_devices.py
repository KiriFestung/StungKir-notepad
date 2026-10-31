# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Два устройства правят одни и те же главы через общую папку (Dropbox, Syncthing, Nextcloud).

Каждое «устройство» - отдельное окно блокнота над одной папкой. Они печатают в главы метки,
которые нигде больше не встречаются, сохраняют, закрываются, отвечают на «глава изменилась»
как попало, а программа синхронизации то кладёт рядом копию-конфликт, то возвращает старую
версию файла. Правило одно: ни одна метка, хоть раз побывавшая на экране или на диске, не
пропадает - она в главе, в «Версиях файла», в корзине или во второй версии главы.

Длинный прогон:  DUO_STEPS=3000 DUO_SEED=5 python3 -m unittest stungkir.tests.test_two_devices"""

import os
import random
import traceback

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QMessageBox

from stungkir.core import config as C
from stungkir.core import conflicts
from stungkir.ui import dialogs
from stungkir.core import storage as S
from stungkir.tests.helpers import WindowCase, wait

CHAPTERS = ["Глава 1", "Глава 2", "Глава 3"]


class Duo:
    def __init__(self, case, rng):
        self.case, self.rng = case, rng
        self.devices = [case.window(), case.window()]
        self.markers = set()                     # всё, что когда-либо побывало на экране или на диске
        self.outside = set()                     # дописано телефоном: блокнот этих меток мог и не видеть
        self.seen = set()                        # метки, которые хоть раз были в окне блокнота
        self.counter = 0
        self.history = {}                        # глава -> прежние тексты на диске (для «старой версии»)
        self.problems = []

    # ---- что под рукой ----
    def chapters(self):
        folder = C.ROOT / "Книга"
        return [p for p in S.files_in(folder) if p.suffix == ".txt"] if folder.is_dir() else []

    def device(self):
        return self.rng.choice(self.devices)

    def new_marker(self):
        self.counter += 1
        marker = f"МЕТКА{self.counter:05d}Ж"
        self.markers.add(marker)
        return marker

    def remember_disk(self, path):
        try:
            self.history.setdefault(path, []).append(S.read_text(path))
        except (OSError, S.LockedFile):
            pass

    # ---- действия ----
    def open_chapter(self):
        chapters = self.chapters()
        if chapters:
            self.device().open_path(self.rng.choice(chapters))

    def type_marker(self):
        w = self.device()
        if w.path is None or w.view is not None:
            return
        cursor = w.editor.textCursor()
        cursor.movePosition(QTextCursor.End if self.rng.random() < 0.7 else QTextCursor.Start)
        w.editor.setTextCursor(cursor)
        marker = self.new_marker()
        if os.environ.get("DUO_TRACE"):
            print("   печатает", self.devices.index(w), marker, flush=True)
        w.editor.insertPlainText(f" {marker} ")

    def save(self):
        w = self.device()
        if w.path is not None:
            self.remember_disk(w.path)
        self.rng.choice([w.save, w.autosave, w.save_everything, lambda: w.save(auto=True)])()

    def notice(self):
        """Наблюдатель за файлами сработал (у настоящего - через долю секунды, а может и позже)."""
        self.device().check_external()

    def restart(self):
        index = self.rng.randrange(2)
        old = self.devices[index]
        if os.environ.get("DUO_TRACE"):
            print("   перезапуск", index, flush=True)
        if old.path is not None:
            self.remember_disk(old.path)
        old.close()
        if old.isVisible():
            return
        old.deleteLater()
        QApplication.processEvents()
        self.devices[index] = self.case.window()

    def sync_conflict(self):
        """Синхронизация не стала перезаписывать главу, а положила рядом вторую версию."""
        chapters = self.chapters()
        if not chapters:
            return
        original = self.rng.choice(chapters)
        try:
            base = S.read_text(original)
        except (OSError, S.LockedFile):
            return
        copy = original.with_name(f"{original.stem}.sync-conflict-2026101{self.counter % 10}-"
                                  f"{self.counter:06d}-{self.rng.choice(['PHONE7X', 'ДРУГОЙ'])}{original.suffix}")
        S.save_text(copy, base + f" {self.new_marker()} ")
        w = self.device()
        w.refresh_tree()
        if self.rng.random() < 0.6:
            w.open_conflict(copy, original)

    def stale_version(self):
        """Устройство долго было без сети и, вернувшись, затёрло главу своим старым текстом."""
        chapters = [p for p in self.chapters() if self.history.get(p)]
        if not chapters:
            return
        path = self.rng.choice(chapters)
        self.remember_disk(path)
        old = self.rng.choice(self.history[path])
        if os.environ.get("DUO_TRACE"):
            print("   старая версия", path.name, repr(old[-50:]), flush=True)
        S.save_text(path, old)
        for w in self.devices:
            if self.rng.random() < 0.8:
                w.check_external()

    def other_device_writes(self):
        """Третье устройство (телефон) дописало главу, пока окна не смотрят."""
        chapters = self.chapters()
        if not chapters:
            return
        path = self.rng.choice(chapters)
        self.remember_disk(path)
        try:
            text = S.read_text(path)
        except (OSError, S.LockedFile):
            return
        marker = self.new_marker()
        self.outside.add(marker)
        if os.environ.get("DUO_TRACE"):
            print("   телефон дописал", path.name, marker, flush=True)
        S.save_text(path, text + f" {marker} ")

    ACTIONS = [("open_chapter", 4), ("type_marker", 10), ("save", 6), ("notice", 4), ("restart", 1),
               ("sync_conflict", 1), ("stale_version", 2), ("other_device_writes", 3)]

    # ---- проверка ----
    def everywhere(self):
        """Весь текст, который ещё можно найти: файлы в папке (с версиями и корзиной) и открытые окна."""
        found = []
        for path in C.ROOT.rglob("*"):
            if path.is_file():
                try:
                    found.append(S.read_text(path))
                except (OSError, S.LockedFile, UnicodeDecodeError):
                    pass
        for w in self.devices:
            found.append(w.editor.toPlainText())
        return "\n".join(found)

    def check(self, step, name):
        text = self.everywhere()
        on_screen = "\n".join(w.editor.toPlainText() for w in self.devices)
        self.seen |= {m for m in self.markers if m in on_screen}
        # телефон дописал, а другая программа затёрла раньше, чем глава хоть раз открылась, -
        # блокнот этого текста не видел и сберечь не мог
        lost = sorted(m for m in self.markers if m not in text and not (m in self.outside and m not in self.seen))
        if lost:
            self.problems.append(f"шаг {step} «{name}»: пропали метки {lost[:5]} (всего {len(lost)})")
        stray = list(C.ROOT.rglob("*.tmp"))
        if stray:
            self.problems.append(f"шаг {step}: остались временные файлы {stray[:3]}")

    def run(self, steps):
        names = [n for n, weight in self.ACTIONS for _ in range(weight)]
        log = []
        for step in range(steps):
            name = self.rng.choice(names)
            log.append(name)
            if os.environ.get("DUO_TRACE"):
                print(step, name, [(w.path.name if w.path else None, w.is_modified()) for w in self.devices],
                      flush=True)
            try:
                getattr(self, name)()
                QApplication.processEvents()
            except Exception:                    # noqa: BLE001 - ищем именно это
                self.problems.append(f"шаг {step} «{name}»: " + traceback.format_exc(limit=6))
            self.check(step, name)
            if self.problems:
                return log
        return log


class TwoDevicesTest(WindowCase):
    def test_nothing_lost(self):
        seed = int(os.environ.get("DUO_SEED", "3"))
        for offset in range(2):
            with self.subTest(seed=seed + offset):
                self._run(seed + offset, int(os.environ.get("DUO_STEPS", "250")))

    def _run(self, seed, steps):
        rng = random.Random(seed)
        for path in list(C.ROOT.iterdir()):
            S.shutil.rmtree(path) if path.is_dir() else path.unlink()
        self.addCleanup(setattr, C, "MAX_VERSIONS", C.MAX_VERSIONS)
        C.MAX_VERSIONS = 10 ** 6                 # старые версии удаляются по сроку - это не потеря
        self.addCleanup(setattr, C, "DATA_DIR", C.DATA_DIR)
        C.DATA_DIR = self.tmp / f"data{seed}"
        for number, name in enumerate(CHAPTERS):
            self.chapter("Книга", name, f"Начало главы {number + 1}.")
        self.answer = QMessageBox.Save           # «сохранить?» - всегда да: сброс своего текста - не потеря
        def choose(*_a, **_k):
            choice = rng.choice(["keep", "take", None])
            if os.environ.get("DUO_TRACE"):
                print("   «глава изменилась» ->", choice, flush=True)
            return choice
        self.patch("ask_choice", choose)
        self.patch("ask_text", lambda *a, **k: (f"Новая {rng.randint(0, 9)}", True))
        unexpected = []

        def no_window(dialog):                   # любое другое окошко - ошибка теста, а не вечное ожидание
            unexpected.append(type(dialog).__name__)
            dialog.deleteLater()
            return 0
        original_exec = dialogs.Sheet.exec
        dialogs.Sheet.exec = no_window
        self.addCleanup(setattr, dialogs.Sheet, "exec", original_exec)

        class Conflict(conflicts.ConflictDialog):
            def exec(self):
                self.choice = rng.choice(["mine", "theirs", "both", None])
                self.deleteLater()
                return self.choice is not None
        self.patch("ConflictDialog", Conflict)
        duo = Duo(self, rng)
        for w in duo.devices:
            w.hover_timer.stop()
        log = duo.run(steps)
        wait(0.02)
        for w in duo.devices:
            w.set_modified(False)
            w.close()
        self.assertEqual(unexpected, [], "неожиданные окошки")
        self.assertEqual(duo.problems, [],f"seed={seed}, последние шаги: {log[-12:]}\n" + "\n".join(duo.problems[:3]))


class SyncCasesTest(WindowCase):
    """Те же беды по одной, чтобы было видно, что именно сломалось."""

    def test_save_does_not_bury_change_from_other_device(self):
        path = self.chapter("Книга", "Глава 1", "Начало.")
        w = self.window()
        w.open_path(path)
        S.save_text(path, "Начало. Дописано на телефоне.")        # наблюдатель ещё не успел сказать
        w.editor.moveCursor(QTextCursor.End)
        w.editor.insertPlainText(" Дописано здесь.")
        w.save(auto=True)
        self.assertEqual(S.read_text(path), "Начало. Дописано здесь.")
        versions = [S.read_text(v) for v in S.list_versions(path)]
        self.assertIn("Начало. Дописано на телефоне.", versions)

    def test_leaving_chapter_keeps_autosaved_text_in_versions(self):
        first = self.chapter("Книга", "Глава 1", "Начало.")
        second = self.chapter("Книга", "Глава 2", "Другое.")
        w = self.window()
        w.open_path(first)
        w.editor.moveCursor(QTextCursor.End)
        w.editor.insertPlainText(" Новое.")
        w.save(auto=True)
        w.editor.insertPlainText(" Ещё.")
        w.save(auto=True)                                        # вторая за 10 минут - без версии
        w.open_path(second)
        self.assertEqual(S.read_text(S.list_versions(first)[0]), "Начало. Новое. Ещё.")

    def test_reload_from_outside_keeps_screen_text(self):
        path = self.chapter("Книга", "Глава 1", "Начало.")
        w = self.window()
        w.open_path(path)
        w.editor.moveCursor(QTextCursor.End)
        w.editor.insertPlainText(" Моё.")
        w.save(auto=True)
        w.save(auto=True)
        S.save_text(path, "Старый текст с другого устройства.")
        w.check_external()
        self.assertEqual(w.editor.toPlainText(), "Старый текст с другого устройства.")
        self.assertIn("Начало. Моё.", [S.read_text(v) for v in S.list_versions(path)])

    def test_backup_folder_must_be_safe(self):
        self.assertIsNone(C.backup_dir_problem(""))
        self.assertIsNone(C.backup_dir_problem(str(self.tmp / "копии")))
        self.assertIn("полный путь", C.backup_dir_problem("копии"))
        self.assertIn("сами себя", C.backup_dir_problem(str(C.ROOT / "копии")))
        self.assertIn("сами себя", C.backup_dir_problem(str(C.ROOT)))
        (self.tmp / "файл").write_text("x", encoding="utf-8", newline="\n")
        self.assertIn("файл", C.backup_dir_problem(str(self.tmp / "файл")))
        before = C.BACKUP_DIR
        C.apply_config({"BACKUP_DIR": "копии"})                  # старый конфиг с плохим путём не применяется
        self.assertEqual(C.BACKUP_DIR, before)
