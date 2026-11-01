# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Чужие файлы в папках, конфликты синхронизации, отмена замены во всех главах."""
from pathlib import Path

from stungkir.core import config as C
from stungkir.core import conflicts as K
from stungkir.core import storage as S
from stungkir.tests.helpers import Sandbox, WindowCase

PNG = b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR" + b"\0" * 40


class FileKindsTest(Sandbox):
    def test_text_or_not(self):
        folder = C.ROOT / "Книга"
        folder.mkdir()
        (folder / "фото.png").write_bytes(PNG)
        (folder / "без расширения").write_bytes(b"\0\x01\x02 binary")
        (folder / "заметка").write_text("Обычный текст", encoding="utf-8", newline="\n")
        (folder / "старое.txt").write_bytes("Текст в 1251".encode("cp1251"))
        self.assertFalse(S.is_text_file(folder / "фото.png"))
        self.assertFalse(S.is_text_file(folder / "без расширения"))
        self.assertTrue(S.is_text_file(folder / "заметка"))
        self.assertEqual([p.name for p in S.files_in(folder)], ["заметка", "старое.txt"])
        self.assertEqual(len(S.files_in(folder, everything=True)), 4)

    def test_conflict_names(self):
        cases = {
            "Глава 3.sync-conflict-20261015-101010-ABCDEFG.txt": "Глава 3.txt",
            "Глава 3 (conflicted copy 2026-10-15 101010).txt": "Глава 3.txt",
            "Глава 3 (Kirill's conflicted copy 2026-10-15).txt": "Глава 3.txt",
            "Глава 3 (конфликтующая копия Kirill 2026-10-15).txt": "Глава 3.txt",
        }
        for name, original in cases.items():
            self.assertEqual(S.conflict_original(Path("/x") / name), Path("/x") / original, name)
        self.assertIsNone(S.conflict_original(Path("/x/Глава 3 (2).txt")))

    def test_resolve(self):
        mine = self.chapter("Книга", "Глава", "Моя версия")
        copy = mine.with_name("Глава.sync-conflict-20261015-101010-ABC.txt")
        copy.write_text("Их версия", encoding="utf-8", newline="\n")
        self.assertEqual(S.files_in(mine.parent), [mine])           # копия не попадает в книгу и поиск
        trashed = []
        K.resolve(copy, mine, "theirs", to_trash=lambda p: (trashed.append(p), p.unlink()))
        self.assertEqual(mine.read_text(encoding="utf-8"), "Их версия")
        self.assertEqual(trashed, [copy])
        self.assertTrue(any(f.read_text(encoding="utf-8") == "Моя версия" for f in S.versions_dir(mine).glob("*.txt")))
        copy.write_text("Третья", encoding="utf-8", newline="\n")
        both = K.resolve(copy, mine, "both")
        self.assertEqual(both.name, "Глава (вторая версия).txt")
        self.assertEqual(mine.read_text(encoding="utf-8"), "Их версия")


class GuardsWindowTest(WindowCase):
    def test_not_text_is_shown_but_not_opened(self):
        folder = C.ROOT / "Книга"
        folder.mkdir()
        (folder / "обложка.png").write_bytes(PNG)
        w = self.window()
        w.refresh_tree()
        labels = [w.tree.topLevelItem(0).child(i).text(0).strip() for i in range(w.tree.topLevelItem(0).childCount())]
        self.assertIn("⊘ обложка.png", labels)
        self.assertFalse(w.open_path(folder / "обложка.png"))
        self.assertIn("не текст", w.toast.text())

    def test_conflict_dialog_flow(self):
        mine = self.chapter("Книга", "Глава", "Моя версия")
        copy = mine.with_name("Глава (conflicted copy 2026-10-15).txt")
        copy.write_text("Их версия", encoding="utf-8", newline="\n")
        w = self.window()
        w.announce_conflicts()
        self.assertIn("Конфликт синхронизации", w.toast.text())
        self.patch("ConflictDialog", type("Fake", (), {
            "__init__": lambda self, *a: setattr(self, "choice", "mine") or setattr(self, "mine", None)
            or setattr(self, "theirs", None), "exec": lambda self: True}))
        w.open_path(copy)
        self.assertFalse(copy.exists())
        self.assertEqual(w.path, mine)
        from stungkir.core.trash import trash_entries
        self.assertEqual(len(trash_entries()), 1)                 # копия - в корзине, не пропала

    def test_conflict_copy_vanished_before_click(self):
        """Нашёл робот: пока висело «нажми сюда - разобрать», синхронизация убрала копию сама."""
        mine = self.chapter("Книга", "Глава", "Моя версия")
        copy = mine.with_name("Глава (conflicted copy 2026-10-15).txt")
        copy.write_text("Их версия", encoding="utf-8", newline="\n")
        w = self.window()
        w.announce_conflicts()
        copy.unlink()
        w.open_conflict(copy, mine)                               # раньше - FileNotFoundError
        self.assertIn("уже нет", w.toast.text())
        self.assertEqual(mine.read_text(encoding="utf-8"), "Моя версия")

    def test_undo_replace_everywhere(self):
        one = self.chapter("Книга", "Глава 1", "Кира пришла.")
        two = self.chapter("Книга", "Глава 2", "Кира ушла.")
        w = self.window()
        w.remember_replace([(one, "Кира пришла.", "Мира пришла."), (two, "Кира ушла.", "Мира ушла.")])
        S.save_text(one, "Мира пришла.")
        S.save_text(two, "Мира ушла. И вернулась.")               # эту главу уже правили после замены
        w.undo_replace()
        self.assertEqual(one.read_text(encoding="utf-8"), "Кира пришла.")
        self.assertEqual(two.read_text(encoding="utf-8"), "Мира ушла. И вернулась.")
        self.assertIn("Глава 2", w.toast.text())
        w.undo_replace()
        self.assertIn("Нечего отменять", w.toast.text())


class NamesTest(Sandbox):
    def test_bad_names(self):
        for name in ("con", "NUL.txt", "Com1", "имя\nс переводом", "таб\tуляция", "​невидимка",
                     "‮перевёрнутое", "a/b", ".скрытая", "Глава.", "ы" * 300):
            self.assertIsNotNone(S.bad_name_reason(name), repr(name))
        for name in ("Глава 1", "Ёжик", "😀 эмодзи", "Глава 1.5", "Сон о con"):
            self.assertIsNone(S.bad_name_reason(name), repr(name))

    def test_case_clash(self):
        path = self.chapter("Книга", "Глава", "Текст")
        self.assertEqual(S.name_clash(path.with_name("глава.txt")), path)
        self.assertIsNone(S.name_clash(path.with_name("глава.txt"), source=path))   # сам себя - можно


class RenameKeepsTypeTest(WindowCase):
    def test_chapter_stays_chapter(self):
        path = self.chapter("Книга", "Глава", "Текст главы")
        w = self.window()
        self.patch("ask_text", lambda *a, **k: ("План.board", True))
        w.rename(path)
        renamed = path.with_name("План.board.txt")
        self.assertEqual(renamed.read_text(encoding="utf-8"), "Текст главы")   # не превратилась в доску
