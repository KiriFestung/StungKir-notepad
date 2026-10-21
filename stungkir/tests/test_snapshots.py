# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Снимки всего проекта: сделать, вернуть, откат при сбое, пароль."""
import unittest
import zipfile

from stungkir import config as C
from stungkir import snapshots as P
from stungkir import storage as S
from stungkir.tests.helpers import Sandbox, WindowCase, crypto_available, wait


class SnapshotCase(Sandbox):
    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, C, "SNAPSHOT_DIR", C.SNAPSHOT_DIR)
        C.SNAPSHOT_DIR = self.tmp / "snapshots"
        self.first = self.chapter("Книга", "Глава 1", "Первый вариант.")
        C.service_path(".names.json").parent.mkdir(parents=True, exist_ok=True)
        C.service_path(".names.json").write_text('["Ольга"]', encoding="utf-8", newline="\n")
        (C.ROOT / ".stfolder").mkdir()                       # отметка Syncthing
        S.snapshot(self.first, "Первый вариант.")


class SnapshotTest(SnapshotCase):
    def test_make_and_list(self):
        path = P.make_snapshot("Перед правкой")
        [(listed, info)] = P.list_snapshots()
        self.assertEqual(listed, path)
        self.assertEqual((info["title"], info["chapters"], info["words"]), ("Перед правкой", 1, 2))
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
        self.assertIn("Книга/Глава 1.txt", names)
        self.assertFalse(any(n.startswith((".versions", ".stfolder")) for n in names))

    def test_restore_brings_back_book_but_keeps_history(self):
        path = P.make_snapshot("Старое")
        S.save_text(self.first, "Переписано.")
        S.snapshot(self.first, "Переписано.")
        self.chapter("Новое", "Лишняя", "Появилась после снимка.")
        C.service_path(".names.json").write_text('["Ольга", "Пётр"]', encoding="utf-8", newline="\n")
        P.restore_snapshot(path)
        self.assertEqual(S.read_text(self.first), "Первый вариант.")
        self.assertFalse((C.ROOT / "Новое").exists())
        self.assertEqual(C.service_path(".names.json").read_text(encoding="utf-8"), '["Ольга"]')
        self.assertEqual(len(S.list_versions(self.first)), 2)   # история версий не откатилась
        self.assertTrue((C.ROOT / ".stfolder").is_dir())        # Syncthing не потеряет папку
        self.assertEqual([p.name for p in C.ROOT.parent.iterdir() if p.name.startswith(".")], [])

    def test_archive_keeps_old_names_and_old_points_restore_into_service_folder(self):
        path = P.make_snapshot("Новая")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
        self.assertIn(".names.json", names)                    # внутри точки - прежние имена
        self.assertFalse(any(n.startswith(C.SERVICE_DIR) for n in names))
        old = self.tmp / "старая.zip"                           # точка из прошлой версии: всё прямо в StungKir
        with zipfile.ZipFile(path) as source, zipfile.ZipFile(old, "w") as target:
            for name in source.namelist():
                target.writestr(name, source.read(name))
        S.save_text(self.first, "Переписано.")
        C.service_path(".names.json").write_text('["Пётр"]', encoding="utf-8", newline="\n")
        P.restore_snapshot(old)
        self.assertEqual(S.read_text(self.first), "Первый вариант.")
        self.assertEqual(C.service_path(".names.json").read_text(encoding="utf-8"), '["Ольга"]')
        self.assertFalse((C.ROOT / ".names.json").exists())
        self.assertEqual(len(S.list_versions(self.first)), 1)     # версии (служебные, но не в точке) на месте

    def test_failed_restore_changes_nothing(self):
        path = P.make_snapshot("Старое")
        S.save_text(self.first, "Переписано.")
        real = P.os.replace
        calls = {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] == 3:
                raise OSError(28, "No space left on device")
            return real(src, dst)
        P.os.replace = flaky
        try:
            with self.assertRaises(P.SnapshotError):
                P.restore_snapshot(path)
        finally:
            P.os.replace = real
        self.assertEqual(S.read_text(self.first), "Переписано.")
        self.assertEqual(C.service_path(".names.json").read_text(encoding="utf-8"), '["Ольга"]')
        self.assertEqual([p.name for p in C.ROOT.parent.iterdir() if p.name.startswith(".")], [])

    def test_broken_snapshot_is_refused(self):
        path = P.make_snapshot("Старое")
        path.write_bytes(path.read_bytes()[:100])
        with self.assertRaises(P.SnapshotError):
            P.restore_snapshot(path)
        self.assertEqual(S.read_text(self.first), "Первый вариант.")

    def test_archive_with_foreign_paths_is_not_unpacked_outside(self):
        path = P.make_snapshot("Старое")
        for leftover in (self.tmp.parent / "вне.txt", self.tmp / "вне.txt"):
            self.addCleanup(leftover.unlink, missing_ok=True)
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("../../вне.txt", "плохо")
        P.restore_snapshot(path)
        self.assertFalse((self.tmp.parent / "вне.txt").exists())
        self.assertFalse((self.tmp / "вне.txt").exists())


@unittest.skipUnless(crypto_available(), "нет библиотеки cryptography")
class SnapshotPasswordTest(SnapshotCase):
    def test_recode_on_password_change(self):
        from stungkir.tests.test_password import write_lock
        path = P.make_snapshot("Открытый")
        crypto = write_lock("секрет")
        with self.assertRaises(P.SnapshotError):         # снимок без пароля, а пароль уже стоит
            P.restore_snapshot(path)
        self.assertEqual(P.recode_snapshots(None, crypto), [])
        with zipfile.ZipFile(path) as archive:
            data = archive.read("Книга/Глава 1.txt")
        self.assertTrue(data.startswith(C.MAGIC))
        self.assertNotIn("Первый".encode(), data)
        S.CRYPTO = crypto
        S.save_text(self.first, "Переписано.")
        P.restore_snapshot(path)
        self.assertEqual(S.read_text(self.first), "Первый вариант.")


class SnapshotWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QMessageBox
        self.addCleanup(setattr, C, "SNAPSHOT_DIR", C.SNAPSHOT_DIR)
        C.SNAPSHOT_DIR = self.tmp / "snapshots"
        self.first = self.chapter("Книга", "Глава 1", "Первый вариант.")
        self.w = self.window()
        self.w.open_path(self.first)
        self.patch("ask_text", lambda *a, **k: ("Перед правкой", True))
        self.answer = QMessageBox.Yes

    def test_take_and_restore_from_window(self):
        path = self.w.take_snapshot()
        cursor = self.w.editor.textCursor()
        cursor.select(cursor.SelectionType.Document)
        cursor.insertText("Совсем другой текст, не сохранён.")      # как будто набрал сам
        self.assertTrue(self.w.is_modified())
        info = dict(P.list_snapshots())[path]
        self.assertTrue(self.w.restore_snapshot(path, info))
        wait()
        self.assertEqual(self.w.editor.toPlainText(), "Первый вариант.")
        self.assertFalse(self.w.is_modified())
        titles = [i["title"] for _p, i in P.list_snapshots()]
        self.assertIn("Перед возвратом к «Перед правкой»", titles)   # отменить возврат можно
        undo = next(p for p, i in P.list_snapshots() if i["title"].startswith("Перед возвратом"))
        P.restore_snapshot(undo)
        self.assertEqual(S.read_text(self.first), "Совсем другой текст, не сохранён.")

    def test_dialog_lists_snapshots(self):
        from stungkir.windows import SnapshotsDialog
        self.w.take_snapshot()
        dialog = SnapshotsDialog(self.w)
        self.assertEqual(len(dialog.items), 1)
        self.assertIn("Перед правкой", dialog.list.item(0).text())
