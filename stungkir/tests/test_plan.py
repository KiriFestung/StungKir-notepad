# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""План книги: статусы глав, «о чём», точки слева, порядок перетаскиванием, переезд при переименовании."""

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView

from stungkir import config as C
from stungkir import storage as S
from stungkir.lore import birth_year, lore_tooltip
from stungkir.plan import STATUS_ROLE, PlanDialog, parse_year, plan_summary
from stungkir.tests.helpers import Sandbox, WindowCase, wait


class PlanStorageTest(Sandbox):
    def test_round_trip_and_damage(self):
        full = {"status": "done", "about": "Кира у реки", "pov": "Кира", "year": "1203", "skip": "yes"}
        S.save_plan({"Книга/Глава 1.txt": full, "Пусто": {}})
        self.assertEqual(S.load_plan(), {"Книга/Глава 1.txt": full})      # все поля переживают перезапуск
        C.service_path(C.PLAN_FILE).write_text('{"a": 5, "b": {"status": 3, "about": "  "}}', encoding="utf-8",
                                               newline="\n")
        self.assertEqual(S.load_plan(), {})                      # мусор пропускается, а не роняет программу

    def test_birth_and_year(self):
        self.assertEqual(birth_year("Мельничиха.\nРодилась: 1203\nТакже: Кира"), 1203)
        self.assertEqual(birth_year("год рождения - нет\nГод рождения: -40"), -40)
        self.assertIsNone(birth_year("Родилась весной, у реки."))
        self.assertEqual(parse_year(" 1203,5 "), 1203.5)
        self.assertIsNone(parse_year("весной"))

    def test_summary(self):
        rows = [(C.ROOT / "К" / "1.txt", 1200), (C.ROOT / "К" / "2.txt", 800), (C.ROOT / "К" / "3.txt", 0)]
        plan = {"К/1.txt": {"status": "done"}, "К/2.txt": {"status": "edit"}}
        key = lambda p: p.relative_to(C.ROOT).as_posix()       # noqa: E731
        self.assertEqual(plan_summary(rows, plan, key), "Готово 1 из 3 глав · в правке 1 · 2 000 слов")
        plan["К/2.txt"]["skip"] = "yes"                        # «не в книгу» - не в счёт
        self.assertEqual(plan_summary(rows, plan, key), "Готово 1 из 2 глав · 1 200 слов · не в книгу 1")


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
        self.assertEqual(top.child(0).text(PlanDialog.WORDS), "4")     # слова главы
        self.assertEqual(top.child(2).text(PlanDialog.STATUS), "Правка")
        menu = dialog.status_menu(top.child(0))                   # как щелчок по статусу: меню и выбор
        next(a for a in menu.actions() if a.text() == "Готово").trigger()
        self.assertEqual(S.load_plan()["Книга/Глава 1.txt"], {"status": "done"})
        self.assertEqual(dialog.tree.topLevelItem(0).child(0).text(PlanDialog.STATUS), "Готово")
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

    def test_pov_year_and_age(self):
        self.chapter("Мир", "Кира", "Мельничиха.\nРодилась: 1200")
        self.w.toggle_lore_category(C.ROOT / "Мир")
        self.w.rebuild_lore()
        timeline = C.ROOT / "Книга" / "Хроника.timeline"
        timeline.write_text(json.dumps({"events": [{"year": 1210, "title": "Буря", "chapter": "Книга/Глава 2.txt"},
                                                   {"year": 1215, "title": "Ещё", "chapter": "Книга/Глава 2.txt"}]},
                                       ensure_ascii=False), encoding="utf-8", newline="\n")
        self.assertEqual(self.w.story_year(self.second), 1210)          # самое раннее событие главы
        self.assertIsNone(self.w.story_year(self.first))                # года нет - возраста нет
        self.w.plan_set(self.second, "year", "1217")                    # свой год сильнее хронологии
        self.assertEqual(self.w.story_year(self.second), 1217)
        self.assertIn("Кира", self.w.plan_people())
        # возраст - в подсказке к имени в тексте открытой главы
        self.w.open_path(self.second)
        term = next(t for t in self.w.lore.terms if t.name == "Кира")
        self.w.lore_term_at = lambda pos: term
        self.assertIn("В этой главе: 17 лет", self.w._lore_tip(None))
        self.w.open_path(self.first)
        self.assertNotIn("В этой главе", self.w._lore_tip(None))
        self.assertIn("до рождения ещё 3 года", lore_tooltip(term, True, -2.5))
        # в плане: чей взгляд с возрастом, год из хронологии бледным
        self.w.plan.pop("Книга/Глава 2.txt")
        dialog = PlanDialog(self.w, self.w.plan_chapters(), self.w.plan, self.w._position_key,
                            lambda: S.save_plan(self.w.plan), lambda f, n: None, self.w.plan_people(),
                            self.w.timeline_years(), {"Кира": 1200})
        row = dialog.tree.topLevelItem(0).child(1)
        self.assertEqual(row.text(PlanDialog.YEAR), "1210")
        next(a for a in dialog.pov_menu(row).actions() if a.text() == "Кира").trigger()
        self.assertEqual(S.load_plan()["Книга/Глава 2.txt"], {"pov": "Кира"})
        row = dialog.tree.topLevelItem(0).child(1)
        self.assertEqual(row.text(PlanDialog.POV), "Кира (10 лет)")
        row.setText(PlanDialog.YEAR, "весной")                        # не число - не сохраняется
        wait()
        self.assertNotIn("year", S.load_plan()["Книга/Глава 2.txt"])
        dialog.tree.topLevelItem(0).child(1).setText(PlanDialog.YEAR, "1220")
        wait()
        self.assertEqual(S.load_plan()["Книга/Глава 2.txt"], {"pov": "Кира", "year": "1220"})
        self.assertEqual(dialog.tree.topLevelItem(0).child(1).text(PlanDialog.POV), "Кира (20 лет)")
        self.patch("ask_text", lambda *a, **k: ("  Мира ", True))
        next(a for a in dialog.pov_menu(dialog.tree.topLevelItem(0).child(0)).actions()
             if a.text() == "Другое имя…").trigger()
        self.assertEqual(S.load_plan()["Книга/Глава 1.txt"], {"pov": "Мира"})

    def test_not_in_book(self):
        from stungkir.windows import CompileDialog
        self.w.plan_set(self.second, "skip", "yes")
        self.assertEqual(self.child(self.second).foreground(0).color().name(), C.DIM.lower())
        self.assertIn("не в книгу", self.child(self.second).toolTip(0))
        dialog = CompileDialog(self.w, self.w.categories(), C.ROOT / "Книга", "", self.w.skipped_chapters())
        states = {dialog.chapters.item(i).text(): dialog.chapters.item(i).checkState() for i in range(3)}
        self.assertEqual(states, {"Глава 1": Qt.Checked, "Глава 2": Qt.Unchecked, "Глава 3": Qt.Checked})
        self.assertEqual([p.name for p in dialog.options()["chapters"]], ["Глава 1.txt", "Глава 3.txt"])
        plan = PlanDialog(self.w, self.w.plan_chapters(), self.w.plan, self.w._position_key,
                          lambda: S.save_plan(self.w.plan), lambda f, n: None)
        menu = plan.status_menu(plan.tree.topLevelItem(0).child(1))
        skip = next(a for a in menu.actions() if a.text() == "Не в книгу")
        self.assertTrue(skip.isChecked())
        skip.trigger()                                                  # снять флажок из плана
        self.assertNotIn("Книга/Глава 2.txt", S.load_plan())
