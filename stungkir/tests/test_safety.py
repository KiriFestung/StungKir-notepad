# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Защита текста: запасной файл, аварийное сохранение, страховка от стирания, один запуск."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from stungkir.core import config as C
from stungkir.core import safety
from stungkir.core import storage as S
from stungkir.tests.helpers import Sandbox, WindowCase, app, wait

LONG = "\n".join("Туман стелился над рекой, и лодка ждала у берега до самого утра." for _ in range(40))


class SafetyStoreTest(Sandbox):
    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, C, "DATA_DIR", C.DATA_DIR)
        C.DATA_DIR = self.tmp / "data"

    def test_journal_roundtrip(self):
        safety.write_journal(None, "Набранное")
        self.assertEqual(safety.read_journal()["text"], "Набранное")
        safety.clear_journal()
        self.assertIsNone(safety.read_journal())

    def test_session_marker(self):
        self.assertFalse(safety.crashed_last_time())
        safety.mark_session(True)
        self.assertTrue(safety.crashed_last_time())          # не закрылись - значит, упали
        safety.mark_session(False)
        self.assertFalse(safety.crashed_last_time())

    def test_single_instance(self):
        app()
        first = safety.single_instance()
        self.assertIsNotNone(first)
        self.assertIsNone(safety.single_instance())          # второй запуск не проходит
        first.unlock()
        again = safety.single_instance()
        self.assertIsNotNone(again)
        again.unlock()


class SafetyWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, C, "DATA_DIR", C.DATA_DIR)
        C.DATA_DIR = self.tmp / "data"
        self.path = self.chapter("Книга", "Глава", "Было на диске.")
        self.w = self.window()
        self.w.open_path(self.path)

    def test_journal_follows_unsaved_text(self):
        self.w.editor.insertPlainText("Новое. ")
        self.w.write_journal()
        self.assertIn("Новое.", safety.read_journal()["text"])
        self.w.save()
        self.assertIsNone(safety.read_journal())             # сохранено - запасной файл не нужен

    def test_recovery_after_crash(self):
        safety.write_journal(self.path, "Было на диске. И дописано перед сбоем.")
        other = self.w
        asked = []
        self.assertTrue(other.offer_recovery(lambda text: asked.append(text) or True))
        self.assertIn("«Глава»", asked[0])
        self.assertEqual(other.editor.toPlainText(), "Было на диске. И дописано перед сбоем.")
        self.assertTrue(other.is_modified())
        self.assertEqual(self.path.read_text(encoding="utf-8"), "Было на диске.")   # сам не перезаписал
        self.assertTrue(S.versions_dir(self.path).exists())

    def test_recovery_warns_when_disk_is_newer(self):
        import os
        import time
        safety.write_journal(self.path, "Набрано до сбоя.")
        self.path.write_text("Потом поменяли на телефоне.", encoding="utf-8", newline="\n")
        later = time.time() + 120                           # глава на диске - новее запасного файла
        os.utime(self.path, (later, later))
        asked = []
        self.assertTrue(self.w.offer_recovery(lambda text: asked.append(text) or True))
        self.assertIn("новее запасного файла", asked[0])
        self.assertEqual(self.path.read_text(encoding="utf-8"), "Потом поменяли на телефоне.")   # не тронута
        versions = S.list_versions(self.path)
        self.assertIn("Потом поменяли на телефоне.", S.read_text(versions[0]))           # и есть в версиях

    def test_recovery_declined_or_needless(self):
        safety.write_journal(self.path, "Другой текст")
        self.assertFalse(self.w.offer_recovery(lambda text: False))
        self.assertIsNone(safety.read_journal())
        safety.write_journal(self.path, "Было на диске.")        # то же, что на диске - и спрашивать нечего
        self.assertFalse(self.w.offer_recovery(lambda text: self.fail("не должен спрашивать")))

    def test_crash_guard_saves_and_keeps_working(self):
        self.addCleanup(setattr, sys, "excepthook", sys.excepthook)
        guard = safety.install_crash_guard(lambda: self.w)
        self.w.editor.insertPlainText("Важное. ")
        try:
            raise ValueError("проверка")
        except ValueError:
            guard(*sys.exc_info())
        self.assertIn("Важное.", self.path.read_text(encoding="utf-8"))
        self.assertIn("ValueError: проверка", C.ERROR_LOG.read_text(encoding="utf-8"))
        self.assertIn("пошло не так", self.w.toast.text())

    def test_big_erase_can_be_undone(self):
        self.w.editor.setPlainText(LONG)
        self.w.save()
        self.w.editor.selectAll()
        QTest.keyClick(self.w.editor, Qt.Key_Delete)
        self.assertEqual(self.w.editor.toPlainText(), "")
        self.assertIn("Стёрто", self.w.toast.text())
        self.assertTrue(any(LONG == f.read_text(encoding="utf-8") for f in S.versions_dir(self.path).glob("*.txt")))
        self.w.undo_big_erase()
        self.assertEqual(self.w.editor.toPlainText(), LONG)

    def test_small_erase_is_quiet(self):
        self.w.editor.setPlainText(LONG)
        cursor = self.w.editor.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(5, cursor.MoveMode.KeepAnchor)
        self.w.editor.setTextCursor(cursor)
        self.w.toast.hide()
        QTest.keyClick(self.w.editor, Qt.Key_Delete)
        wait(0.02)
        self.assertIsNone(self.w.last_erase)
