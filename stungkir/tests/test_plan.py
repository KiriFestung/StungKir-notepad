# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""План книги: статусы глав, «о чём», точки слева, порядок перетаскиванием, переезд при переименовании."""

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView

from stungkir import config as C
from stungkir import storage as S
from stungkir.plan import STATUS_ROLE, PlanDialog, plan_summary
from stungkir.tests.helpers import Sandbox, WindowCase, wait


class PlanStorageTest(Sandbox):
    def test_round_trip_and_damage(self):
        S.save_plan({"Книга/Глава 1.txt": {"status": "done", "about": "Кира у реки"}, "Пусто": {}})
        self.assertEqual(S.load_plan(), {"Книга/Глава 1.txt": {"status": "done", "about": "Кира у реки"}})
        C.service_path(C.PLAN_FILE).write_text('{"a": 5, "b": {"status": 3, "about": "  "}}', encoding="utf-8",
                                               newline="\n")
        self.assertEqual(S.load_plan(), {})                      # мусор пропускается, а не роняет программу

    def test_summary(self):
        rows = [(C.ROOT / "К" / "1.txt", 1200), (C.ROOT / "К" / "2.txt", 800), (C.ROOT / "К" / "3.txt", 0)]
        plan = {"К/1.txt": {"status": "done"}, "К/2.txt": {"status": "edit"}}
        key = lambda p: p.relative_to(C.ROOT).as_posix()       # noqa: E731
        self.assertEqual(plan_summary(rows, plan, key), "Готово 1 из 3 глав · в правке 1 · 2 000 слов")


class PlanWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.first = self.chapter("Книга", "Глава 1", "Тервена спала. Давнь ждал.")
        self.second = self.chapter("Книга", "Глава 2", "Кев ушёл.")
        self.third = self.chapter("Книга", "Глава 3", "Лосс вернулся домой к Нии.")
        self.w = self.window()

    def child(self, path):
        for i in range(self.w.tree.topLevelItemCount()):
            folder = self.w.tree.topLevelItem(i)
            for j in range(folder.childCount()):
                if self.w.item_path(folder.child(j)) == path:
                    return folder.child(j)
        return None

    def test_status_dot_and_about_in_tree(self):
        self.w.plan_set(self.first, "status", "draft")
        self.patch("ask_text", lambda *a, **k: ("Тервена   засыпает\nу огня", True))
        self.w.edit_chapter_about(self.first)
        item = self.child(self.first)
        self.assertEqual(item.data(0, STATUS_ROLE), "draft")
        self.assertEqual(item.toolTip(0), "Черновик · Тервена засыпает у огня")
        saved = json.loads(C.service_path(C.PLAN_FILE).read_text(encoding="utf-8"))
        self.assertEqual(saved, {"Книга/Глава 1.txt": {"about": "Тервена засыпает у огня", "status": "draft"}})
        self.w.refresh_tree()                                     # после перерисовки точка на месте
        self.assertEqual(self.child(self.first).data(0, STATUS_ROLE), "draft")
        self.w.plan_set(self.first, "status", None)
        self.assertEqual(self.child(self.first).data(0, STATUS_ROLE), "")

    def test_rename_keeps_plan(self):
        self.w.plan_set(self.second, "status", "done")
        self.patch("ask_text", lambda *a, **k: ("Глава вторая", True))
        self.w.rename(self.second)
        moved = self.second.with_name("Глава вторая.txt")
        self.assertTrue(moved.exists())
        self.assertEqual(self.w.chapter_plan(moved), {"status": "done"})
        self.assertEqual(S.load_plan(), {"Книга/Глава вторая.txt": {"status": "done"}})

    def test_plan_dialog(self):
        self.w.plan_set(self.third, "status", "edit")
        dialog = PlanDialog(self.w, self.w.plan_chapters(), self.w.plan, self.w._position_key,
                            lambda: S.save_plan(self.w.plan), lambda folder, names: S.save_order(folder, names))
        self.assertIn("Готово 0 из 3 глав · в правке 1", dialog.summary.text())
        top = dialog.tree.topLevelItem(0)
        self.assertEqual([top.child(i).text(0) for i in range(3)], ["Глава 1", "Глава 2", "Глава 3"])
        self.assertEqual(top.child(0).text(2), "4")              # слова главы
        self.assertEqual(top.child(2).text(1), "Правка")
        menu = dialog.status_menu(top.child(0))                   # как щелчок по статусу: меню и выбор
        next(a for a in menu.actions() if a.text() == "Готово").trigger()
        self.assertEqual(S.load_plan()["Книга/Глава 1.txt"], {"status": "done"})
        self.assertEqual(dialog.tree.topLevelItem(0).child(0).text(1), "Готово")
        menu = dialog.status_menu(dialog.tree.topLevelItem(0).child(0))
        self.assertTrue(next(a for a in menu.actions() if a.text() == "Готово").isChecked())
        top = dialog.tree.topLevelItem(0)
        top.child(1).setText(PlanDialog.ABOUT, "  Кев   уходит ")  # «о чём» прямо в таблице
        self.assertEqual(S.load_plan()["Книга/Глава 2.txt"], {"about": "Кев уходит"})
        # перетащить третью главу выше первой: порядок меняется на диске
        dialog._moved(top.child(2), top.child(0), QAbstractItemView.AboveItem)
        self.assertEqual(S.load_order(C.ROOT / "Книга"), ["Глава 3.txt", "Глава 1.txt", "Глава 2.txt"])
        top = dialog.tree.topLevelItem(0)
        self.assertEqual([top.child(i).text(0) for i in range(3)], ["Глава 3", "Глава 1", "Глава 2"])
        dialog._moved(top.child(0), top, QAbstractItemView.OnItem)    # брошена на категорию - в конец
        self.assertEqual(S.load_order(C.ROOT / "Книга"), ["Глава 1.txt", "Глава 2.txt", "Глава 3.txt"])
        self.assertFalse(dialog.grab().isNull())
        dialog._double_clicked(dialog.tree.topLevelItem(0).child(1), PlanDialog.NAME)
        self.assertEqual(dialog.open_target, self.second)

    def test_show_plan_opens_chapter_and_hotkey(self):
        self.assertEqual(self.w.shortcuts["plan"].key().toString(), "Ctrl+P")
        from stungkir import dialogs

        def pick_second(dialog):
            dialog.open_target = self.second
            return 1
        original = dialogs.Sheet.exec
        dialogs.Sheet.exec = pick_second
        self.addCleanup(setattr, dialogs.Sheet, "exec", original)
        self.w.show_plan()
        wait()
        self.assertEqual(self.w.path, self.second)

    def test_lore_and_boards_not_in_plan(self):
        self.chapter("Мир", "Тервена", "Город у моря.")
        self.w.lore_cfg["categories"].append("Мир")
        board = C.ROOT / "Книга" / "Сюжет.board"
        board.write_text('{"columns": []}', encoding="utf-8", newline="\n")
        names = [(f.name, [p.name for p, _w in rows]) for f, rows in self.w.plan_chapters()]
        self.assertEqual(names, [("Книга", ["Глава 1.txt", "Глава 2.txt", "Глава 3.txt"])])
        self.assertEqual(self.child(self.first).flags() & Qt.ItemIsDropEnabled, Qt.ItemFlag(0))
