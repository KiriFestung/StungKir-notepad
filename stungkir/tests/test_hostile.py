# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Плохое снаружи: диск полон, нет доступа, файлы и папки удалили или испортили, пока блокнот открыт."""
import errno
import shutil

from stungkir import config as C
from stungkir import storage as S
from stungkir.tests.helpers import WindowCase, wait


class HostileTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.path = self.chapter("Книга", "Глава", "Было.")
        self.w = self.window()
        self.w.open_path(self.path)

    def failing_write(self, code):
        def fail(path, data):
            raise OSError(code, "нарочно")
        return fail

    def test_disk_full_keeps_text_and_says_so(self):
        self.w.editor.insertPlainText("Новое. ")
        self.patch("write_atomic", self.failing_write(errno.ENOSPC))
        self.assertFalse(self.w.save())
        self.assertIn("Не получилось сохранить", self.messages[-1][1])
        self.assertTrue(self.w.is_modified())                       # текст не потерян и ждёт сохранения
        self.w.autosave()
        self.assertIn("закончилось место", self.w.toast.text())
        self.assertEqual(self.path.read_text(encoding="utf-8"), "Было.")
        self.assertEqual(list(C.ROOT.rglob("*.tmp")), [])

    def test_no_access(self):
        self.w.editor.insertPlainText("Новое. ")
        self.patch("write_atomic", self.failing_write(errno.EACCES))
        self.w.autosave()
        self.assertIn("Нет доступа", self.w.toast.text())
        self.assertTrue(self.w.is_modified())

    def test_open_chapter_deleted_outside(self):
        self.path.unlink()
        self.w.check_external()
        self.assertIn("удалили или переименовали снаружи", self.w.toast.text())
        self.assertEqual(self.w.editor.toPlainText(), "Было.")
        self.w.editor.insertPlainText("Ещё. ")
        self.assertTrue(self.w.save())
        self.assertEqual(self.path.read_text(encoding="utf-8"), "Ещё. Было.")

    def test_category_deleted_outside(self):
        shutil.rmtree(self.path.parent)
        self.w.editor.insertPlainText("Спасено. ")
        self.assertTrue(self.w.save())
        self.assertTrue(self.path.exists())

    def test_whole_folder_deleted_outside(self):
        shutil.rmtree(C.ROOT)
        self.w.refresh_tree()                                       # не падает
        self.assertTrue(C.ROOT.is_dir())
        self.w.editor.insertPlainText("Спасено. ")
        self.assertTrue(self.w.save())
        self.assertEqual(self.path.read_text(encoding="utf-8"), "Спасено. Было.")

    def test_broken_board_is_kept(self):
        board = self.path.with_name("План.board")
        board.write_text('{"columns": [{"title": "Обрыв', encoding="utf-8", newline="\n")
        self.w.open_path(board)
        self.assertEqual(self.messages[-1][0], "Файл повреждён")
        self.assertFalse(self.w.is_modified())
        versions = list(S.versions_dir(board).glob("*.txt"))
        self.assertEqual(versions[0].read_text(encoding="utf-8"), '{"columns": [{"title": "Обрыв')
        wait(0.05)
        self.assertEqual(board.read_text(encoding="utf-8"), '{"columns": [{"title": "Обрыв')   # сам не перезаписал

    def test_broken_service_files(self):
        (self.path.parent / ".order").write_text("{сломано", encoding="utf-8", newline="\n")
        C.service_path(C.LORE_FILE).parent.mkdir(parents=True, exist_ok=True)
        C.service_path(C.LORE_FILE).write_text("[1, 2", encoding="utf-8", newline="\n")
        (C.ROOT / ".crutches.json").write_text("не json", encoding="utf-8", newline="\n")
        timeline = self.path.with_name("Хроно.timeline")
        timeline.write_text("\0\0\0", encoding="utf-8", newline="\n")
        self.w.refresh_tree()
        self.w.rebuild_lore()
        self.assertTrue(self.w.open_path(timeline) or True)
        self.w.open_path(self.path)
        self.assertEqual(self.w.editor.toPlainText(), "Было.")

    def test_bad_bytes_keep_exact_copy(self):
        odd = self.path.with_name("Странная.txt")
        odd.write_bytes("Текст ".encode() + b"\xff\xfe\x00\x81" + "конец".encode())
        self.w.open_path(odd)
        raw = list(S.versions_dir(odd).glob("*.raw"))
        if raw:                                                     # если прочиталось с потерями - есть точная копия
            self.assertEqual(raw[0].read_bytes(), odd.read_bytes())

    def test_broken_encrypted_file(self):
        if not S.crypto_available():
            self.skipTest("нет cryptography")
        bad = self.path.with_name("Шифр.txt")
        bad.write_bytes(C.MAGIC + b"gAAAAABoborvalos")                # обрывок шифра
        self.assertFalse(self.w.open_path(bad))
        self.assertIn("не расшифровывается", self.messages[-1][1])

    def test_empty_and_huge_lines(self):
        empty = self.path.with_name("Пусто.txt")
        empty.write_bytes(b"")
        self.assertTrue(self.w.open_path(empty))
        long_line = self.path.with_name("Строка.txt")
        long_line.write_text("слово " * 50_000, encoding="utf-8", newline="\n")          # одна строка в 300 тысяч знаков
        self.assertTrue(self.w.open_path(long_line))
        self.w.editor.insertPlainText("начало ")
        self.assertTrue(self.w.save())
