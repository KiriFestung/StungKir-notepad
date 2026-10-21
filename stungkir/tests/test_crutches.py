# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Мои штампы: формы слова, обороты, вырезание без следов, замена по всем главам с версиями."""
import unittest

from stungkir import config as C
from stungkir import storage as S
from stungkir import textutil as T
from stungkir.tests.helpers import WindowCase, wait


class MatchTest(unittest.TestCase):
    def found(self, entries, line):
        return [line[a:b] for a, b, _e in T.Crutches(entries).spans(line)]

    def test_forms_and_phrases(self):
        line = "Вдруг она вздохнула. Он почувствовал, как внезапный холод. Они вздохнули."
        self.assertEqual(self.found(["вдруг", "вздохнул", "почувствовал, как", "внезапно"], line),
                         ["Вдруг", "вздохнула", "почувствовал, как", "внезапный", "вздохнули"])

    def test_no_false_friends(self):
        self.assertEqual(self.found(["вздохнул"], "Вздох был тяжёлым, вздохов много."), [])
        self.assertEqual(self.found(["как"], "Какой как-нибудь как."), ["как"])          # короткие - точно
        self.assertEqual(self.found(["почувствовал, как"], "Он почувствовал. Как же."), [])  # через точку - нет

    def test_long_phrase_wins(self):
        spans = T.Crutches(["как", "почувствовал, как"]).spans("Он почувствовал, как холод.")
        self.assertEqual([e for _a, _b, e in spans], ["почувствовал, как"])

    def test_counts(self):
        counts = T.Crutches(["вдруг", "однако"]).count("Вдруг.\nОднако вдруг, вдруг.")
        self.assertEqual(counts, {"вдруг": 3, "однако": 1})


class CleanupTest(unittest.TestCase):
    def cut(self, line, word):
        i = line.index(word)
        return T.delete_span(line, i, i + len(word))[0]

    def test_delete_leaves_clean_sentence(self):
        self.assertEqual(self.cut("Вдруг он ушёл.", "Вдруг"), "Он ушёл.")
        self.assertEqual(self.cut("Он вдруг ушёл.", "вдруг"), "Он ушёл.")
        self.assertEqual(self.cut("Он ушёл вдруг.", "вдруг"), "Он ушёл.")
        self.assertEqual(self.cut("Он, однако, пришёл.", "однако"), "Он пришёл.")
        self.assertEqual(self.cut("Однако, он пришёл.", "Однако"), "Он пришёл.")
        self.assertEqual(self.cut("— Вдруг ушёл? — спросил он.", "Вдруг"), "— Ушёл? — спросил он.")

    def test_replace_keeps_capital(self):
        self.assertEqual(T.replace_span("Вдруг он ушёл.", 0, 5, "неожиданно")[0], "Неожиданно он ушёл.")
        self.assertEqual(T.replace_span("Он вдруг ушёл.", 3, 8, "резко")[0], "Он резко ушёл.")

    def test_parse_entries(self):
        from stungkir.crutches import parse_entries
        self.assertEqual(parse_entries("вдруг\n\n Вдруг \nвнезапно,\n---\nпочувствовал, как"),
                         ["вдруг", "внезапно", "почувствовал, как"])


class CrutchWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.one = self.chapter("Книга", "Глава 1", "Вдруг он ушёл. Она вздохнула.")
        self.two = self.chapter("Книга", "Глава 2", "Он вдруг вернулся, вдруг.")
        self.w = self.window()
        self.w.open_path(self.one)

    def test_add_from_text_highlights_and_saves(self):
        self.w.add_crutch("вдруг")
        self.assertEqual(S.load_crutches(), ["вдруг"])
        block = self.w.editor.document().firstBlock()
        formats = block.layout().formats()
        self.assertTrue(any(f.format.background().color().name() == C.CRUTCH_BG for f in formats))
        self.w.add_crutch("Вдруг")                                  # второй раз не добавляется
        self.assertEqual(S.load_crutches(), ["вдруг"])

    def test_places_and_delete_one(self):
        self.w.add_crutch("вдруг")
        self.w.show_crutch_places()
        self.assertEqual(self.w.global_results.count(), 3)
        self.assertIn("вдруг 3", self.w.global_count.text())
        item = self.w.global_results.item(0)                        # «Вдруг он ушёл.» в первой главе
        self.w._edit_place(item, "")
        self.assertTrue(self.w.editor.toPlainText().startswith("Он ушёл."))
        self.assertEqual(self.w.global_results.count(), 2)

    def test_replace_everywhere_only_checked_and_versions_kept(self):
        from stungkir import crutches as module
        self.w.add_crutch("вдруг")

        class Pick:
            def __init__(self, parent, entry, places, key_of):
                self.places = places
                self.replacement = type("F", (), {"text": lambda _s: "резко"})()

            def exec(self):
                return True

            def chosen(self):
                return self.places[1:]                              # первое место оставили
        self.patch("ReplaceAllDialog", Pick)
        self.w.replace_crutch_everywhere("вдруг")
        wait(0.2)
        self.assertEqual(S.read_text(self.one), "Вдруг он ушёл. Она вздохнула.")
        self.assertEqual(S.read_text(self.two), "Он резко вернулся, резко.")
        self.assertEqual(S.read_text(S.list_versions(self.two)[0]), "Он вдруг вернулся, вдруг.")
        self.assertTrue(module)

    def test_dialog_counts_by_chapter(self):
        from stungkir.crutches import CrutchesDialog
        dialog = CrutchesDialog(self.w, ["вдруг"], self.w.crutch_texts(), self.w._position_key)
        self.assertEqual(dialog.table.item(0, 0).text(), "Книга · Глава 2")   # больше всех
        self.assertEqual(dialog.table.item(0, 2).text(), "2")
        dialog.edit.setPlainText("вдруг\nвздохнул")
        dialog.recount()
        self.assertIn("вздохнул 1", dialog.totals.text())
