# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Английский текст: реплики в кавычках, орфография, «кто говорит», имена с 's. Русский текст - как был."""
import unittest

from stungkir.core import textutil as T
from stungkir.tests.helpers import WindowCase, wait


class QuotedDialogueTest(unittest.TestCase):
    def spans(self, text):
        return [text[a:b] for a, b in T.quoted_spans(text)]

    def test_quote_styles(self):
        self.assertEqual(self.spans("“No,” Kira said. “Not today.”"), ["“No,”", "“Not today.”"])
        self.assertEqual(self.spans('"Run!" he shouted.'), ['"Run!"'])
        self.assertEqual(self.spans("‘I don’t know,’ she said."), ["‘I don’t know,’"])   # британские
        self.assertEqual(self.spans("“It goes on"), ["“It goes on"])                 # реплика на несколько абзацев

    def test_not_dialogue(self):
        self.assertEqual(self.spans('He is 5" tall'), [])                             # дюймы
        self.assertEqual(self.spans("It's Kev's boat"), [])                           # апострофы
        self.assertEqual(self.spans('— Нет, - сказала она. "Цитата"'), [])            # русский - по-старому
        self.assertEqual(self.spans("Она прочла «Тервену»."), [])


class QuotedHighlightTest(WindowCase):
    def color_at(self, w, block, position):
        """Цвет букв в позиции: последний слой подсветки, где цвет задан."""
        from PySide6.QtGui import QTextFormat
        color = None
        for item in w.editor.document().findBlockByNumber(block).layout().formats():
            if item.start <= position < item.start + item.length and item.format.hasProperty(QTextFormat.ForegroundBrush):
                color = item.format.foreground().color().name()
        return color

    def test_only_quotes_are_dialogue(self):
        path = self.chapter("Book", "Chapter", "“No,” Kira said. “Not today.”\n— Нет, - сказала она.")
        w = self.window()
        w.open_path(path)
        wait(0.2)
        dialogue = w.highlighter.dialogue.name()
        self.assertEqual(self.color_at(w, 0, 1), dialogue)                    # «No»
        self.assertNotEqual(self.color_at(w, 0, 8), dialogue)                 # «Kira said»
        self.assertEqual(self.color_at(w, 1, 8), dialogue)                    # русская реплика - вся строка


class EnglishSpellingTest(WindowCase):
    def setUp(self):
        super().setUp()
        from stungkir.core import i18n
        from stungkir.tests.helpers import speller_available
        speller_available()                                     # словари из packaging/ - и английские тоже
        self.addCleanup(i18n.set_language, i18n.LANG)
        self.i18n = i18n

    def speller(self):
        import tempfile
        from pathlib import Path
        from stungkir.text.editor import Speller
        return Speller(Path(tempfile.mkdtemp()) / "pwl.txt")

    def test_us_and_uk(self):
        speller = self.speller()
        self.i18n.set_language("en")
        self.assertTrue(speller.ok_english("color"))
        self.assertFalse(speller.ok_english("recieve"))
        self.assertTrue(speller.ok_english("don’t"))                     # фигурный апостроф
        self.assertIn("receive", speller.suggest_english("recieve"))
        self.i18n.set_language("en-GB")
        self.assertTrue(speller.ok_english("colour"))
        self.assertTrue(speller.ok_english("The"))                        # с большой буквы в начале фразы

    def test_possessive_of_known_word(self):
        speller = self.speller()
        speller.add("Tervena", as_name=True)
        self.assertTrue(speller.ok_english("Tervena's"))
        self.assertTrue(speller.ok_english("Tervena’s"))

    def test_highlight_only_english_paragraphs(self):
        path = self.chapter("Book", "Chapter", "She did not recieve the letter.\nВ Давни звонил iPhonne.")
        w = self.window()
        w.open_path(path)
        wait(0.3)
        spell = w.highlighter._ops("She did not recieve the letter.")[1]
        self.assertIn("spell", [kind for _b, _l, kind in spell])
        line = "В Давни звонил iPhonne."
        latin = line.index("iPhonne")
        russian = w.highlighter._ops(line)[1]
        self.assertFalse([1 for begin, length, kind in russian if kind == "spell" and begin <= latin < begin + length])
        # латиница в русском абзаце - как раньше, не проверяется


class EnglishSpeakersTest(unittest.TestCase):
    TEXT = """Kira stood at the window.
“There will be no boat,” Kira said. “Not today.”
“Why not?” Kev asked.
“Because of the fog,” she said.
He shrugged. “Then we wait.”
“We wait.”
“Until spring?”
“Until spring.”
“I hate waiting,” I said."""

    def test_who_speaks(self):
        from stungkir.text.speakers import NARRATOR, Speakers
        replies = Speakers(["Kira", "Kev"]).chapter(self.TEXT)
        self.assertEqual([(r.speaker, r.how) for r in replies],
                         [("Kira", "name"), ("Kev", "name"), ("Kira", "pronoun"), ("Kev", "pronoun"),
                          ("Kira", "turn"), ("Kev", "turn"), ("Kira", "turn"), (NARRATOR, "pronoun")])
        self.assertEqual(replies[0].words, 7)                  # слова автора («Kira said») - не в счёт

    def test_long_run_and_unclear_pronoun(self):
        from stungkir.text.speakers import Speakers
        text = "Kira and Mira came in.\n" + "\n".join(f"“Line {n}.”" for n in range(5)) + "\n“Go,” she said."
        problems = Speakers(["Kira", "Mira"]).problems(text)
        self.assertTrue(any("подряд" in label for *_rest, label in problems))
        self.assertTrue(any("Kira" in label and "Mira" in label for *_rest, label in problems))

    def test_russian_unchanged(self):
        from stungkir.text.speakers import Speakers
        replies = Speakers(["Кира", "Кев"]).chapter("— Нет, - сказала Кира.\n— Почему? - спросил Кев.")
        self.assertEqual([(r.speaker, r.how) for r in replies], [("Кира", "name"), ("Кев", "name")])


class EnglishNamesTest(WindowCase):
    def test_possessive_and_no_false_match(self):
        from stungkir.world.lore import Lore, LoreTerm
        lore = Lore(None)
        lore.build([LoreTerm("Tervena"), LoreTerm("Kev")])
        found = lambda text: [text[s:e] for s, e, _t in lore.spans(text)]   # noqa: E731
        self.assertEqual(found("Tervena’s capital"), ["Tervena"])
        self.assertEqual(found("Kev's boat"), ["Kev"])
        self.assertEqual(found("Kevin came"), [])                          # Kevin - не Kev

    def test_latin_character_names(self):
        w = self.window()
        w.track_name("Kira")
        self.assertIn("Kira", w.names)
        w.track_name("Kiра")                                                # латиница с кириллицей
        self.assertNotIn("Kiра", w.names)
        self.assertIn("вперемешку", w.toast.text())


class EnglishRepeatsAndCrutchesTest(WindowCase):
    def test_roots(self):
        cases = {"looked": "look", "looks": "look", "looking": "look", "sighed": "sigh", "sighing": "sigh",
                 "stories": "story", "stopped": "stop", "hoping": "hop", "hope": "hop", "boxes": "box",
                 "Kira’s": "kira", "glass": "glass", "status": "status"}
        self.assertEqual({w: T.english_root(w) for w in cases}, cases)

    def test_crutch_forms(self):
        crutches = T.Crutches(["sighed", "felt that", "вздохнул"])
        found = lambda text: [text[s:e] for s, e, _e in crutches.spans(text)]   # noqa: E731
        self.assertEqual(found("He sighs. Sighing, she left; they sighed."), ["sighs", "Sighing", "sighed"])
        self.assertEqual(found("She felt that it was wrong."), ["felt that"])
        self.assertEqual(found("Она вздохнула."), ["вздохнула"])                 # русский - как был

    def test_repeats_in_english_paragraph(self):
        path = self.chapter("Book", "Chapter", "x")
        w = self.window()
        w.open_path(path)
        line = "The river was grey and the river was cold, and that was that."
        repeats = [line[b:b + n] for b, n, kind in w.highlighter._ops(line)[1] if kind == "repeat"]
        self.assertEqual(repeats, ["river", "river"])                           # «that» - служебное
        line = "She looked at him. He looks away."
        repeats = [line[b:b + n] for b, n, kind in w.highlighter._ops(line)[1] if kind == "repeat"]
        self.assertEqual(repeats, ["looked", "looks"])                         # формы одного слова
