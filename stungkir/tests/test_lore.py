# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Справочник мира: формы терминов в тексте, подсказки, разное написание."""
import time
import unittest

from stungkir.world import lore as L
from stungkir.text.editor import Speller
from stungkir.tests.helpers import Sandbox, app, speller_available


class LoreCase(Sandbox):
    NAMES = ["Тервена", "Давнь", "Серое Жерло", "Кев", "Ния", "Сектор-7", "X-17", "Ольга"]

    def setUp(self):
        super().setUp()
        app()
        self.lore = L.Lore(Speller(self.tmp / "pwl.txt"))
        self.lore.build([L.LoreTerm(n) for n in self.NAMES])

    def found(self, text):
        return [(text[a:b], term.name) for a, b, term in self.lore.spans(text)]


class FormsTest(LoreCase):
    def test_cases_are_recognised(self):
        self.assertEqual(self.found("Она вспомнила Тервену, Давнь и Серое Жерло."),
                         [("Тервену", "Тервена"), ("Давнь", "Давнь"), ("Серое Жерло", "Серое Жерло")])
        self.assertEqual(self.found("Говорил с Ольгой о Серого Жерла."),
                         [("Ольгой", "Ольга"), ("Серого Жерла", "Серое Жерло")])

    def test_short_terms_on_vowel(self):
        self.assertEqual(self.found("Видел Нии и Нию, говорил с Нией."),
                         [("Нии", "Ния"), ("Нию", "Ния"), ("Нией", "Ния")])
        self.assertEqual(self.found("Посол Кева прибыл."), [("Кева", "Кев")])

    def test_latin_and_digits(self):
        self.assertEqual(self.found("Сектор-7, сектор-7 и Сектор-8. Отряд X-17, но не X-171."),
                         [("Сектор-7", "Сектор-7"), ("сектор-7", "Сектор-7"), ("X-17", "X-17")])

    @unittest.skipUnless(speller_available(), "нет словаря hunspell-ru")
    def test_ordinary_words_are_not_terms(self):
        self.assertEqual(self.found("Давно дома. Ни звука! Давн."), [])
        self.assertEqual(self.found("Давно Давня."), [("Давня", "Давнь")])

    def test_long_paragraph_is_fast(self):
        paragraph = "Тервена и Давнь у Кева, а Ния молчала над Серым Жерлом. " * 300
        start = time.time()
        spans = self.lore.spans(paragraph)
        self.assertEqual(len(spans), 1500)
        self.assertLess(time.time() - start, 0.5)


class VariantsTest(LoreCase):
    @unittest.skipUnless(speller_available(), "нет словаря hunspell-ru")
    def test_misspelled_names_are_found(self):
        texts = ["В Тервенне шёл дождь. Даввнь молчал. Тервенна далеко.",
                 "Давно пусто. Тервену видно. Ольгу ждали."]
        self.assertEqual(self.lore.variants(texts),
                         {"Тервенна": "Тервена", "Тервенне": "Тервена", "Даввнь": "Давнь"})
        self.assertEqual(self.lore.variants(texts, ignore=["Даввнь"]),
                         {"Тервенна": "Тервена", "Тервенне": "Тервена"})


class NotesTest(LoreCase):
    def test_note_and_aliases_from_file(self):
        note, aliases = L.lore_note("Также: Тервенская республика, Юг\nПрибрежное государство.\n"
                                    "[проверить]\nСтолица - *Лосс*.")
        self.assertEqual(aliases, ["Тервенская республика", "Юг"])
        self.assertEqual(note, "Прибрежное государство.\n\nСтолица - *Лосс*.")

    def test_table_rows_become_terms(self):
        terms = L.lore_terms_from_table("Название,Также,Описание\nЛунит,лун-камень,Светится\n,,\n",
                                        "Мир · Ресурсы", None)
        self.assertEqual([(t.name, t.aliases, t.note) for t in terms],
                         [("Лунит", ["лун-камень"], "Описание: Светится")])

    def test_tooltip_escapes_html(self):
        term = L.LoreTerm("Тервена", "Столица <Лосс> & *порт*", source="Мир", path=self.tmp / "x.txt")
        tip = L.lore_tooltip(term, True)
        self.assertIn("&lt;Лосс&gt; &amp; <i>порт</i>", tip)
        self.assertIn("Ctrl+клик", tip)
