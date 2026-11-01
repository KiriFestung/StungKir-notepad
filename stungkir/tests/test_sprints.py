# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Спринты (таймер, дошедший до конца, - в историю) и график прогресса в статистике."""
from datetime import date, datetime

from stungkir.text import sprints as SP
from stungkir.ui import chart as CH
from stungkir.tests.helpers import Sandbox, WindowCase, wait


class GrowthTest(Sandbox):
    def test_growth_adds_up(self):
        today = date(2026, 11, 1)
        stats = {"2026-10-30": 100, "2026-10-31": -40, "2026-11-01": 250, "2026-01-01": 9999}
        points = CH.growth(stats, today, days=3)
        self.assertEqual([total for _day, total in points], [100, 100, 350])    # минус в рост не идёт
        self.assertEqual(points[-1][0], today)

    def test_pace_and_forecast(self):
        today = date(2026, 11, 1)
        stats = {date(2026, 10, d).isoformat(): 300 for d in range(3, 32)} | {"2026-11-01": 300}
        self.assertEqual(round(CH.pace(stats, today)), 300)
        self.assertIn("9 000 слов", CH.forecast(stats, today))                    # 300 в день × 30, по разрядам
        self.assertIn("мало данных", CH.forecast({}, today))


class SprintStoreTest(Sandbox):
    def test_record_and_best(self):
        self.assertEqual(SP.load_sprints(), [])
        first, record = SP.record_sprint(10, 200, datetime(2026, 11, 1, 10, 0))
        self.assertFalse(record)                                    # первому не с чем сравнивать
        _second, record = SP.record_sprint(10, 400, datetime(2026, 11, 1, 11, 0))
        self.assertTrue(record)
        _third, record = SP.record_sprint(2, 300)                   # короткий рывок - не рекорд
        self.assertFalse(record)
        self.assertEqual(len(SP.load_sprints()), 3)
        self.assertEqual(SP.best_sprint(SP.load_sprints())["words"], 400)
        self.assertEqual(first["when"], "2026-11-01T10:00")
        self.assertEqual(SP.record_sprint(0, 50), (None, False))    # ноль минут - не спринт

    def test_broken_file_is_empty(self):
        SP.sprints_path().parent.mkdir(parents=True, exist_ok=True)
        SP.sprints_path().write_text('[{"when": "x"}, "мусор", {"when": "2026", "minutes": 5, "words": 9}]',
                                     encoding="utf-8", newline="\n")
        self.assertEqual(SP.load_sprints(), [{"when": "2026", "minutes": 5, "words": 9}])
        SP.sprints_path().write_text("не json", encoding="utf-8", newline="\n")
        self.assertEqual(SP.load_sprints(), [])

    def test_result_text(self):
        self.assertEqual(SP.sprint_result(25, 500, True),
                         "Время вышло. За 25 мин: +500 слов (20,0 в минуту). Рекорд скорости!")
        self.assertEqual(SP.sprint_result(10, 0, False), "Время вышло. За 10 мин: +0 слов")


class SprintWindowTest(WindowCase):
    def test_finished_timer_becomes_sprint(self):
        path = self.chapter("Книга", "Глава", "Текст")
        w = self.window()
        w.open_path(path)
        w.timer_minutes.setValue(15)
        w.timer_close.setChecked(False)
        w.toggle_timer()
        w.editor.insertPlainText("раз два три четыре пять ")
        w.timer_deadline = w.session.elapsed()                       # время вышло
        w._tick()
        wait(0.1)
        [entry] = SP.load_sprints()
        self.assertEqual((entry["minutes"], entry["words"]), (15, 5))
        self.assertIn("За 15 мин", w.toast.text())

    def test_sprints_window_and_growth_page(self):
        from stungkir.ui import dialogs, windows
        SP.record_sprint(25, 500)
        w = self.window()
        shown = []
        original = dialogs.Sheet.exec
        self.addCleanup(setattr, dialogs.Sheet, "exec", original)
        dialogs.Sheet.exec = lambda dialog: shown.append(dialog) or 0
        w.show_sprints()
        self.assertEqual(shown[-1].table.rowCount(), 1)
        w.show_stats()
        stats = shown[-1]
        self.assertIsInstance(stats, windows.StatsDialog)
        self.assertEqual(stats.charts.count(), 3)                    # 30 дней, год, рост
        stats.period.button(2).click()
        self.assertIsInstance(stats.charts.currentWidget().findChild(CH.GrowthChart), CH.GrowthChart)
