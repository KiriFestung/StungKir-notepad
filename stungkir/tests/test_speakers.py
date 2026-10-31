# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Кто говорит: разбор реплик, длинные цепочки, непонятные «сказала она», реплики персонажей."""
import unittest

from stungkir.text.speakers import NARRATOR, ReplyStatsDialog, Speakers, reply_stats, segments
from stungkir.tests.helpers import WindowCase

TALK = """Кира подошла к окну.
— Холодно, — сказала она.
— Закрой, — ответил Кев.
— Не хочу.
— Почему?
— Просто.
— Ну и ладно.
* * *
Ния и Кира сидели у огня.
— Пойдём, — сказала она.
— Я — человек, — сказал я.
— Лодки не будет, — сказала Ния. — Не сегодня.
— Тише, — Кев оглянулся на дверь."""


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.s = Speakers(["Кира", "Ния", "Кев"])

    def test_segments(self):
        line = "— Лодки не будет, — сказала Ния. — Не сегодня."
        self.assertEqual([(line[a:b], speech) for a, b, speech in segments(line)],
                         [("Лодки не будет,", True), ("сказала Ния.", False), ("Не сегодня.", True)])
        line = "— Я — человек."                              # тире внутри речи - не слова автора
        self.assertEqual([(line[a:b], speech) for a, b, speech in segments(line)], [("Я — человек.", True)])

    def test_who_speaks(self):
        found = [(r.line, r.speaker, r.how) for r in self.s.chapter(TALK)]
        self.assertEqual(found[:3], [(1, "Кира", "pronoun"), (2, "Кев", "name"), (3, "Кира", "turn")])
        self.assertEqual(found[-4:], [(9, "Кира", "pronoun"), (10, NARRATOR, "pronoun"), (11, "Ния", "name"),
                                      (12, "Кев", "name")])

    def test_forms_of_names_and_gender_learning(self):
        s = Speakers(["Лис"])
        replies = s.chapter("— Да, — сказала Лис.\nДождь.\n— Нет, — ответила она.")
        self.assertEqual([r.speaker for r in replies], ["Лис", "Лис"])    # «Лис» - она, раз «сказала Лис»

    def test_problems(self):
        problems = self.s.problems(TALK)
        labels = [p[4] for p in problems]
        self.assertEqual(problems[0][:2], (3, 6))
        self.assertIn("4 реплики подряд", labels[0])
        self.assertIn("Кев и Кира", labels[0])
        self.assertIn("«она» - Кира или Ния?", labels)
        self.assertEqual(self.s.problems("— Да, — сказал Кев.\n— Нет, — сказала Кира."), [])

    def test_stats(self):
        stats = reply_stats(self.s, [("гл1", TALK)])
        self.assertEqual(stats["Кира"]["replies"], 4)
        self.assertEqual(stats["Ния"]["words"], 5)                      # «Лодки не будет» + «Не сегодня»
        self.assertEqual(stats["Кев"]["how"], {"name": 2, "turn": 2})
        self.assertNotIn(None, stats)


class SpeakersWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        from stungkir.core import storage as S
        S.save_names(["Кира", "Ния", "Кев"])
        self.one = self.chapter("Книга", "Глава 1", TALK)
        self.two = self.chapter("Книга", "Глава 2", "— Ещё раз, — сказала Ния.")
        self.w = self.window()
        self.w.names = ["Кира", "Ния", "Кев"]
        self.w.open_path(self.two)

    def test_check_lists_places_and_opens_them(self):
        self.w.show_speaker_check()
        self.assertEqual(self.w.global_results.count(), 2)
        self.assertIn("2 места", self.w.global_count.text())
        item = self.w.global_results.item(0)
        self.assertIn("4 реплики подряд", item.text())
        self.w._open_global_result(item)
        self.assertEqual(self.w.path, self.one)
        selected = self.w.editor.textCursor().selectedText()
        self.assertTrue(selected.startswith("Не хочу.") and selected.endswith("Ну и ладно."), selected)

    def test_stats_dialog(self):
        texts = self.w.crutch_texts()
        dialog = ReplyStatsDialog(self.w, self.w.speaker_finder(), texts, self.w.path)
        names = [dialog.table.item(r, 0).text() for r in range(dialog.table.rowCount())]
        self.assertEqual(names[0], "Кира")
        self.assertIn("Ния", names)
        ния = names.index("Ния")
        self.assertEqual(dialog.table.item(ния, 1).text(), "2")             # по реплике в каждой главе
        dialog.table.selectRow(ния)
        self.assertEqual(dialog.per_chapter.rowCount(), 2)
        dialog.scope.setCurrentIndex(dialog.scope.findText("Только глава «Глава 2»"))
        self.assertEqual(dialog.table.rowCount(), 1)


class ShortDashTest(unittest.TestCase):
    def test_short_dash_before_author_words(self):
        """Кто пишет длинное тире только в начале реплики, а дальше короткое, - тоже понят."""
        s = Speakers(["Кира", "Кев"])
        found = [(r.speaker, r.how) for r in s.chapter("— Холодно, - сказала Кира.\n— Закрой, - ответил Кев. - Сейчас.")]
        self.assertEqual(found, [("Кира", "name"), ("Кев", "name")])
        line = "— Я - человек."
        self.assertEqual(len(segments(line)), 1)
