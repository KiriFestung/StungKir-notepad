# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Своя корзина: удалить, вернуть, удалить насовсем, само чистится через 30 дней."""
import json
from datetime import datetime, timedelta

from PySide6.QtWidgets import QMessageBox

from stungkir import config as C
from stungkir import storage as S
from stungkir import trash as T
from stungkir.tests.helpers import Sandbox, WindowCase


class TrashStoreTest(Sandbox):
    def test_move_restore_and_name_clash(self):
        path = self.chapter("Книга", "Глава 1", "Текст")
        S.snapshot(path, "Старая версия")
        entry = T.move_to_trash(path)
        self.assertFalse(path.exists())
        [(found, item, origin, _when)] = T.trash_entries()
        self.assertEqual((found, item.name, origin), (entry, "Глава 1.txt", "Книга/Глава 1.txt"))
        self.assertTrue(S.versions_dir(path).exists())                   # история никуда не делась
        self.assertEqual(T.restore(entry), path)
        self.assertEqual(path.read_text(encoding="utf-8"), "Текст")
        self.assertEqual(T.trash_entries(), [])
        entry = T.move_to_trash(path)
        self.chapter("Книга", "Глава 1", "Новая с тем же именем")
        back = T.restore(entry)
        self.assertEqual(back.name, "Глава 1 (из корзины).txt")

    def test_chapter_trashed_on_phone_comes_back(self):
        """Телефон кладёт главу в корзину так же (Book.moveToTrash): компьютер её видит и возвращает."""
        path = self.chapter("Тервена", "Глава 1", "Кев ушёл.")
        S.snapshot(path, "До удаления")
        entry = C.service_path(".trash") / "20261029-090500-a1b2c3"
        entry.mkdir(parents=True)
        (entry / T.META).write_text('{"from": "Тервена/Глава 1.txt", "when": "2026-10-29T09:05:00", "kind": "file"}',
                                    encoding="utf-8", newline="\n")
        path.replace(entry / path.name)
        [(found, item, origin, when)] = T.trash_entries()
        self.assertEqual((found, item.name, origin, when), (entry, "Глава 1.txt", "Тервена/Глава 1.txt",
                                                            datetime(2026, 10, 29, 9, 5)))
        self.assertEqual(T.restore(entry), path)
        self.assertEqual(path.read_text(encoding="utf-8"), "Кев ушёл.")
        self.assertTrue(S.versions_dir(path).exists())

    def test_folder_and_purge(self):
        self.chapter("Черновики", "Набросок", "…")
        T.move_to_trash(self.tmp / "StungKir" / "Черновики")
        [(entry, item, _o, _w)] = T.trash_entries()
        self.assertTrue(item.is_dir())
        self.assertEqual(T.purge_old(), 0)
        meta = json.loads((entry / T.META).read_text(encoding="utf-8"))
        meta["when"] = (datetime.now() - timedelta(days=31)).isoformat()
        (entry / T.META).write_text(json.dumps(meta), encoding="utf-8", newline="\n")
        self.assertEqual(T.purge_old(), 1)
        self.assertEqual(T.trash_entries(), [])

    def test_trash_is_encrypted_with_everything(self):
        path = self.chapter("Книга", "Тайна", "секрет")
        T.move_to_trash(path)
        names = [p.name for p in S.content_files()]
        self.assertIn("Тайна.txt", names)
        self.assertNotIn("meta.json", names)


class TrashWindowTest(WindowCase):
    def test_delete_goes_to_trash_and_comes_back(self):
        path = self.chapter("Книга", "Глава", "Текст главы")
        w = self.window()
        w.open_path(path)
        w.editor.insertPlainText("Правка. ")
        self.answer = QMessageBox.Yes
        w.delete(path)
        self.assertFalse(path.exists())
        self.assertIsNone(w.path)
        self.assertIn("в корзине", w.toast.text())
        dialog = T.TrashDialog(w, w._restored)
        self.assertEqual(dialog.listing.count(), 1)
        dialog._restore()
        self.assertEqual(path.read_text(encoding="utf-8"), "Правка. Текст главы")   # с последней правкой
        self.assertEqual(w.path, path)


class SampleTest(WindowCase):
    def test_sample_appears_and_goes_to_trash(self):
        from stungkir import sample
        w = self.window()
        w.add_sample()
        self.assertFalse(sample.is_fresh())
        self.assertTrue(sample.has_sample())
        self.assertEqual(w.path.name, "Прочитай меня.txt")
        self.assertIn("Тервена", [t.name for t in w.lore.terms])            # справочник мира работает сразу
        board = C.ROOT / sample.BOOK / "План.board"
        w.open_path(board)
        self.assertEqual(w.board_view.mode, "free")
        self.assertEqual(len(w.board_view.free.links), 3)
        self.answer = QMessageBox.Yes
        w.drop_sample()
        self.assertFalse(sample.has_sample())
        self.assertFalse((C.ROOT / sample.BOOK).exists() or (C.ROOT / sample.WORLD).exists())
        self.assertEqual(len(T.trash_entries()), 2)
        self.assertNotIn(sample.WORLD, w.lore_cfg["categories"])
