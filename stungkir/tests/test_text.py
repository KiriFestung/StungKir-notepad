# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Работа с текстом: разметка, таблицы, сравнение версий, привязка заметок к абзацам."""
import unittest

from stungkir import textutil as T
from stungkir.export import book_paragraphs
from stungkir.tests.helpers import app


class MarkupTest(unittest.TestCase):
    def test_plural(self):
        self.assertEqual([T.plural(n, "слово", "слова", "слов") for n in (1, 2, 5, 11, 21, 104)],
                         ["слово", "слова", "слов", "слов", "слово", "слова"])

    def test_bold_and_italic(self):
        self.assertEqual(T.markup_runs("Это *курсив* и **жирный**."),
                         [("Это ", False, False), ("курсив", False, True), (" и ", False, False),
                          ("жирный", True, False), (".", False, False)])

    def test_book_paragraphs_clean_markers_and_control_chars(self):
        self.assertEqual(book_paragraphs("Первый [пометка] абзац\x0b.\n\n  Второй   абзац.  ", True),
                         ["Первый абзац.", "Второй абзац."])

    def test_table_round_trip(self):
        header, rows = T.parse_table("Имя,Описание\nОльга,\"Рыжая, смелая\"\n")
        self.assertEqual(header, ["Имя", "Описание"])
        self.assertEqual(rows, [["Ольга", "Рыжая, смелая"]])
        self.assertEqual(T.parse_table(T.table_to_text(header, rows)), (header, rows))


class DiffTest(unittest.TestCase):
    def setUp(self):
        app()

    def test_summary_counts_words(self):
        old = "Туман над рекой.\nЛодка шла медленно.\nКонец."
        new = "Туман густел над рекой.\nКонец.\nНовый абзац здесь."
        html, summary = T.diff_html(old, new)
        self.assertIn("+4 слова", summary)       # «густел» и «Новый абзац здесь»
        self.assertIn("−3 слова", summary)       # «Лодка шла медленно»
        self.assertIn("3 абзаца затронуто", summary)   # правка, удаление, новый
        self.assertIn("line-through", html)

    def test_no_changes(self):
        self.assertEqual(T.diff_html("Раз.\nДва.", "Раз.\nДва.")[1], "Изменений нет")

    def test_long_unchanged_parts_are_folded(self):
        old = "\n".join(f"Абзац {i}." for i in range(30))
        new = old.replace("Абзац 15.", "Абзац пятнадцать.")
        html, _ = T.diff_html(old, new)
        self.assertIn("без изменений", html)
        self.assertNotIn("Абзац 3.", html)


class AnchorNotesTest(unittest.TestCase):
    def note(self, paragraphs, i, **extra):
        return {"anchor": paragraphs[i], "index": i, "before": paragraphs[i - 1] if i else "",
                "after": paragraphs[i + 1] if i + 1 < len(paragraphs) else "", **extra}

    def test_moves_with_inserted_paragraphs(self):
        text = ["Утро было серым.", "Ольга вышла к реке.", "Лодки не было.", "Вечер."]
        note = self.note(text, 1)
        self.assertEqual(T.anchor_notes(["Новое начало.", "Ещё строка."] + text, [note]), [3])

    def test_edited_paragraph_among_similar_ones(self):
        text = [f"Абзац {i}: туман стелился над рекой." for i in range(10)]
        note = self.note(text, 4)
        edited = list(text)
        edited.insert(0, "Вставка сверху.")
        edited[5] = edited[5].replace("туман", "густой туман")
        self.assertEqual(T.anchor_notes(edited, [note]), [5])

    def test_deleted_paragraph_keeps_note_nearby(self):
        text = ["Раз два три.", "Совсем другой абзац про лису.", "Конец главы."]
        note = self.note(text, 1)
        self.assertEqual(T.anchor_notes(["Раз два три.", "Конец главы."], [note]), [1])


class TestListTest(unittest.TestCase):
    @unittest.skipIf(getattr(__import__("sys"), "frozen", False), "в готовой сборке файлов тестов нет")
    def test_runner_knows_every_test_file(self):
        from pathlib import Path
        from stungkir.tests.run import MODULES
        here = Path(__file__).resolve().parent
        self.assertEqual(sorted(p.stem for p in here.glob("test_*.py")), sorted(MODULES))


class PersonalDictionaryTest(unittest.TestCase):
    def test_added_words_count_everywhere(self):
        import tempfile
        from pathlib import Path
        from stungkir.editor import Speller
        from stungkir.tests.helpers import speller_available
        if not speller_available():
            self.skipTest("нет словаря hunspell-ru")
        path = Path(tempfile.mkdtemp()) / "pwl.txt"
        speller = Speller(path)
        for word in ("Винто", "Фух", "Хахаха"):
            self.assertFalse(speller.ok(word), word)
            speller.add(word)
            self.assertTrue(speller.ok(word), word)
            self.assertTrue(speller.ok(word.lower()), word)       # и в середине фразы
        speller.add("Тервена", as_name=True)
        self.assertTrue(speller.ok("Тервена"))
        again = Speller(path)                                      # после перезапуска - тоже
        self.assertTrue(all(again.ok(w) for w in ("Винто", "фух", "Хахаха", "Тервена")))
        self.assertEqual(again.suggest("малако"), again.suggest("малако"))   # варианты не скачут


class PasteRepairTest(unittest.TestCase):
    def test_all_kinds_of_line_breaks(self):
        for sep in ("\r\n", "\r", "\v", "\f", "\x85", " ", " "):
            self.assertEqual(T.clean_pasted(f"Раз.{sep}Два."), "Раз.\nДва.", repr(sep))

    def test_glued_replies_are_cut_where_one_ends_and_next_begins(self):
        glued = ("Внутри было сухо.   'Так, малая, я уже отрубил'.«ня Загрузка ня».   "
                 "\"У меня вопрос, блин?!!\"'Ну хз, а сколько?'\"Процентов нисколько!\"/ня Ждите, ня/."
                 "<Ого, злая ты. А почему?>\"Ладно\".Веки моргнули.")
        self.assertEqual(T.clean_pasted(glued).split("\n"), [
            "Внутри было сухо.", "'Так, малая, я уже отрубил'.", "«ня Загрузка ня».",
            "\"У меня вопрос, блин?!!\"", "'Ну хз, а сколько?'", "\"Процентов нисколько!\"", "/ня Ждите, ня/.",
            "<Ого, злая ты. А почему?>", "\"Ладно\".", "Веки моргнули."])

    def test_ordinary_text_is_not_cut(self):
        for text in ("Это А.С.Пушкин. Он пошёл.Потом вернулся.", "don't stop и/или.Дальше",
                     "Он сказал: «Нет». И ушёл."):
            self.assertEqual(T.clean_pasted(text), text)

    def test_html_paragraphs_win_when_plain_text_lost_them(self):
        self.assertEqual(T.clean_pasted("Первый абзац. Второй абзац.", "Первый абзац.\nВторой абзац."),
                         "Первый абзац.\nВторой абзац.")
