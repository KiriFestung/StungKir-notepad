# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Доска сюжета, таблицы, пометки, календарь письма, часы, настройки без перезапуска."""
import json
import unittest
from datetime import date, timedelta

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from stungkir import config as C
from stungkir import storage as S
from stungkir import textutil as T
from stungkir.tests.helpers import WindowCase, wait

BLANK = {"columns": [{"title": t, "cards": []} for t in C.BOARD_COLUMNS]}


class FakeCard:
    """Окно карточки, в котором уже всё заполнили и нажали «Готово»."""
    deleted = False

    def __init__(self, *_a, **_k):
        pass

    def exec(self):
        return True

    def card_data(self):
        return {"title": "Встреча", "text": "Они видятся впервые", "color": "purple", "chapter": ""}


class BoardTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.w = self.window()
        self.path = C.ROOT / "Книга" / "План.board"
        self.path.parent.mkdir()
        self.path.write_text(json.dumps(BLANK), encoding="utf-8", newline="\n")
        self.w.open_path(self.path)
        self.board = self.w.board_view
        from stungkir import board
        self.patch("CardDialog", FakeCard)
        self.assertTrue(board)

    def saved(self):
        return json.loads(S.read_text(self.path))

    def test_new_card_is_saved_by_itself(self):
        self.board.new_card(self.board.columns[2])
        self.assertTrue(self.w.is_modified())
        wait(C.AUTOSAVE_PAUSE_MS / 1000 + 0.5)
        self.assertEqual(self.saved()["columns"][2]["cards"][0]["title"], "Встреча")
        self.assertFalse(self.w.is_modified())

    def test_double_click_on_empty_place_makes_card(self):
        column = self.board.columns[0]
        QTest.mouseDClick(column.list.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(60, 200))
        self.assertEqual([c["title"] for c in column.cards()], ["Встреча"])

    def test_double_click_on_header_renames(self):
        self.patch("ask_text", lambda *a, **k: ("Начало", True))
        column = self.board.columns[0]
        QTest.mouseDClick(column.header, Qt.LeftButton, Qt.NoModifier, QPoint(20, 8))
        self.assertEqual(column.title.text(), "Начало")

    def test_dragging_column_moves_it(self):
        wait(0.1)
        first = self.board.columns[0]
        self.board._dragged = first
        last = self.board.columns[-1]
        self.board.column_dragged_to(QPoint(last.geometry().right() + 5, 20))   # за последнюю
        self.board._dragged = None
        self.assertIs(self.board.columns[-1], first)
        self.assertEqual(self.board.row.indexOf(first), len(self.board.columns) - 1)
        titles = [c["title"] for c in self.board.data()["columns"]]
        self.assertEqual(titles, C.BOARD_COLUMNS[1:] + C.BOARD_COLUMNS[:1])

    def test_column_follows_theme(self):
        from PySide6.QtWidgets import QApplication
        self.assertNotIn("#1b201c", QApplication.instance().styleSheet())

    def test_markers_and_search_look_at_cards_not_file_format(self):
        self.board.new_card(self.board.columns[0])
        self.w.save()
        self.chapter("Книга", "Глава", "Текст [проверить дату] и пустые [] [ ].")
        self.w.show_markers()
        found = [self.w.global_results.item(i).text() for i in range(self.w.global_results.count())]
        self.assertEqual(len(found), 1, found)
        self.assertIn("[проверить дату]", found[0])
        self.w.overlay_mode = "search"
        self.w.global_edit.setText("cards")
        self.w.run_global_search()
        self.assertEqual(self.w.global_results.count(), 0)
        self.w.global_edit.setText("впервые")
        self.w.run_global_search()
        self.assertEqual(self.w.global_results.count(), 1)


class SearchableTextTest(unittest.TestCase):
    def test_board_and_table(self):
        from pathlib import Path
        board = json.dumps({"columns": [{"title": "Завязка", "cards": [{"title": "Сцена", "text": "[ок]"}]}]})
        self.assertEqual(T.searchable_text(Path("a.board"), board), "Завязка\nСцена\n[ок]")
        self.assertEqual(T.searchable_text(Path("a.board"), "не json"), "")
        self.assertEqual(T.searchable_text(Path("a.csv"), "Имя,Роль\nКира,героиня\n"),
                         "Имя  ·  Роль\nКира  ·  героиня")
        self.assertEqual(T.searchable_text(Path("a.txt"), "[]"), "[]")
        self.assertEqual(T.MARKER_FILLED_RE.findall("[] [ ] [x] [ y ]"), ["[x]", "[ y ]"])


class TableAutosaveTest(WindowCase):
    def test_table_saves_by_itself(self):
        w = self.window()
        path = C.ROOT / "Книга" / "Герои.csv"
        path.parent.mkdir()
        path.write_text("Имя,Роль\nКира,\n", encoding="utf-8", newline="\n")
        w.open_path(path)
        w.table_view.table.item(0, 1).setText("героиня")
        self.assertTrue(w.is_modified())
        wait(C.AUTOSAVE_PAUSE_MS / 1000 + 0.5)
        self.assertIn("героиня", S.read_text(path))


class StreakTest(unittest.TestCase):
    TODAY = date(2026, 10, 14)

    def day(self, n):
        return (self.TODAY - timedelta(days=n)).isoformat()

    def test_words_and_marks(self):
        stats = {self.day(1): 300, self.day(2): 249, self.day(3): 1000}
        marks = {self.day(2)}
        self.assertTrue(S.wrote_on(self.TODAY - timedelta(days=1), stats, marks))
        self.assertTrue(S.wrote_on(self.TODAY - timedelta(days=2), stats, marks))   # отмечен вручную
        self.assertFalse(S.wrote_on(self.TODAY - timedelta(days=2), stats, set()))   # 249 - мало
        self.assertEqual(S.streaks(stats, marks, self.TODAY), (3, 3))     # сегодня ещё не рвёт
        self.assertEqual(S.streaks(stats, set(), self.TODAY), (1, 1))

    def test_record_is_kept_after_break(self):
        stats = {self.day(n): 400 for n in (10, 11, 12, 13)} | {self.day(0): 260}
        self.assertEqual(S.streaks(stats, set(), self.TODAY), (1, 4))
        self.assertEqual(S.streaks({}, set(), self.TODAY), (0, 0))


class CalendarTest(WindowCase):
    def test_click_marks_day_and_streak_shows(self):
        w = self.window()
        yesterday = date.today() - timedelta(days=1)
        w.stats[(yesterday - timedelta(days=1)).isoformat()] = 500
        from stungkir.windows import StatsDialog
        dialog = StatsDialog(w, w.stats, w.goal, w.day_marks, w.set_day_marks)
        if yesterday.month != date.today().month:
            dialog._shift(-1)
        dialog.calendar.on_toggle(yesterday)
        self.assertIn(yesterday.isoformat(), S.load_marks())
        self.assertIn("Дней подряд: 2", dialog.streak.text())
        w.update_status()
        self.assertIn("2 дня подряд", w.status_plain)
        dialog.calendar.on_toggle(yesterday)
        self.assertNotIn(yesterday.isoformat(), S.load_marks())
        dialog.grab()                                          # рисуется без ошибок


class ClockAndSettingsTest(WindowCase):
    def test_clock_and_toggle(self):
        from datetime import datetime
        w = self.window()
        self.assertEqual(w.corner_clock.text(), datetime.now().strftime("%H:%M"))
        w.corner_clock.grab()                                  # циферблат рисуется без ошибок
        self.assertTrue(w.corner_clock.isVisible())
        w.toggle_clock()
        self.assertFalse(w.corner_clock.isVisible())
        self.assertEqual(w.settings.value("clock"), "false")

    def test_column_width_applies_without_restart(self):
        w = self.window()
        self.addCleanup(setattr, C, "COLUMN_WIDTH", C.COLUMN_WIDTH)
        before = w.editor.viewportMargins().left()

        class Fake:
            def __init__(self, *a):
                pass

            def exec(self):
                return True

            def values(self):
                return {"COLUMN_WIDTH": C.COLUMN_WIDTH - 200}, 0
        self.patch("SettingsDialog", Fake)
        w.show_settings()
        self.assertEqual(w.editor.viewportMargins().left(), before + 100)
        self.assertEqual(self.messages, [])                   # без вопроса о перезапуске


class RealCardDialogTest(WindowCase):
    """Настоящее окно карточки, без подмены: раньше «Готово» молча падало, и карточка не появлялась."""

    def test_card_dialog_returns_what_was_typed(self):
        from stungkir.board import CardDialog
        dialog = CardDialog(None, {}, ["Книга/Глава.txt"], lambda: None, existing=False)
        dialog.title.setText("Встреча")
        dialog.text.setPlainText("Они видятся впервые")
        dialog.swatches[2].setChecked(True)
        dialog.chapter.setCurrentIndex(1)
        self.assertEqual(dialog.card_data(), {"title": "Встреча", "text": "Они видятся впервые",
                                              "color": C.CARD_COLORS[2][0], "chapter": "Книга/Глава.txt"})

    def test_no_window_hides_sheet_parts(self):
        """Ни одно окно-карточка не называет свои функции так же, как детали самой карточки."""
        import inspect
        from PySide6.QtWidgets import QDialog
        from stungkir import dialogs
        from stungkir.tests.helpers import MODULES
        sheet = dialogs.Sheet(None, "проба")
        parts = {name for name in vars(sheet) if not hasattr(QDialog, name)}    # content, flat, …
        self.assertIn("content", parts)
        for module in MODULES:
            for _name, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, dialogs.Sheet) and cls is not dialogs.Sheet:
                    clash = parts & set(vars(cls))
                    self.assertFalse(clash, f"{cls.__name__}: {clash}")
