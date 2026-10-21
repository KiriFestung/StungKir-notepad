# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Дедлайн книги: темп, полоска «книга», строка в статистике."""
import unittest
from datetime import date

from stungkir import deadline as D
from stungkir import storage as S
from stungkir.tests.helpers import WindowCase


class PaceTest(unittest.TestCase):
    def test_pace(self):
        today = date(2026, 10, 15)
        self.assertEqual(S.deadline_pace(10_000, 40_000, date(2026, 10, 24), today), (30_000, 10, 3000))
        self.assertEqual(S.deadline_pace(50_000, 40_000, date(2026, 10, 24), today), (0, 10, 0))
        self.assertEqual(S.deadline_pace(1_000, 40_000, date(2026, 10, 1), today), (39_000, 0, None))
        self.assertEqual(S.deadline_pace(0, 1000, today, today), (1000, 1, 1000))       # сегодня - последний день

    def test_text(self):
        today = date(2026, 10, 15)
        self.assertIn("нужно 3000 слов в день",
                      D.pace_text("Роман", 10_000, {"words": 40_000, "date": "2026-10-24"}, today))
        self.assertIn("готово", D.pace_text("Роман", 40_000, {"words": 40_000, "date": "2026-10-24"}, today))
        self.assertIn("прошёл", D.pace_text("Роман", 0, {"words": 40_000, "date": "2026-10-01"}, today))


class DeadlineWindowTest(WindowCase):
    def test_deadline_bar_and_stats(self):
        one = self.chapter("Роман", "Глава 1", "раз два три четыре")
        self.chapter("Роман", "Глава 2", "пять шесть")
        w = self.window()
        w.open_path(one)

        class Pick:
            removed = False

            def __init__(self, parent, categories, current, deadlines, words_of):
                self.words_of = words_of
                self.current = current

            def exec(self):
                return True

            def chosen(self):
                return "Роман", {"words": 12, "date": date.today().isoformat()}
        self.patch("DeadlineDialog", Pick)
        w.show_deadline()
        self.assertEqual(S.load_deadlines(), {"Роман": {"words": 12, "date": date.today().isoformat()}})
        self.assertEqual(w.book_words(one.parent), 6)
        w.editor.setPlainText("раз два три четыре пять шесть")       # открытая глава считается как в окне
        w.count_words()
        self.assertEqual(w.book_words(one.parent), 8)
        item = w.goal_strip.items["book"]
        self.assertTrue(item["shown"])
        self.assertIn("8 из 12", w.goal_strip.toolTip())
        self.assertTrue(any("«Роман»" in line for line in w.deadline_lines()))
