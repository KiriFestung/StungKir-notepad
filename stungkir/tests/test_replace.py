# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Найти и заменить во всех главах: формы имён, целое слово, регистр, версии до замены."""
import unittest
from pathlib import Path

from stungkir import storage as S
from stungkir import replace as R
from stungkir.tests.helpers import WindowCase, app, speller_available, wait

TEXT = "Кира пришла. Киры не было. С Кирой. Кирилл и кира."


class ReplaceLogicTest(unittest.TestCase):
    def test_transfer_form(self):
        self.assertEqual([R.transfer_form("Кира", "Мира", f) for f in ("Кира", "Киры", "Кирой", "КИРЕ", "киру")],
                         ["Мира", "Миры", "Мирой", "МИРЕ", "миру"])
        self.assertEqual(R.transfer_form("Тёмное Озеро", "Серое Жерло", "Тёмного Озера"), "Серого Жерла")

    def test_plain_whole_and_case(self):
        texts = [(Path("К/Г.txt"), TEXT)]
        self.assertEqual([p[4] for p in R.find_places(texts, "кира", whole=True)], ["Кира", "кира"])
        self.assertEqual([p[4] for p in R.find_places(texts, "Кир")], ["Кир", "Кир", "Кир", "Кир", "кир"])
        self.assertEqual([p[4] for p in R.find_places(texts, "кира", case=True, whole=True)], ["кира"])
        places = R.find_places(texts, "кира", whole=True)
        self.assertEqual(R.apply_places(TEXT, places, "кира", "мира", False)[0],
                         "Мира пришла. Киры не было. С Кирой. Кирилл и мира.")

    @unittest.skipUnless(speller_available(), "нет словаря hunspell-ru")
    def test_all_forms(self):
        app()
        from stungkir.editor import Speller
        import tempfile
        speller = Speller(Path(tempfile.mkdtemp()) / "p.txt")
        places = R.find_places([(Path("К/Г.txt"), TEXT)], "Кира", forms=True, speller=speller)
        self.assertEqual([p[4] for p in places], ["Кира", "Киры", "Кирой", "кира"])
        self.assertEqual(R.apply_places(TEXT, places, "Кира", "Мира", True)[0],
                         "Мира пришла. Миры не было. С Мирой. Кирилл и мира.")

    def test_delete_and_changed_text_skipped(self):
        places = R.find_places([(Path("a"), "Он вдруг ушёл.")], "вдруг", whole=True)
        self.assertEqual(R.apply_places("Он вдруг ушёл.", places, "вдруг", "", False)[0], "Он ушёл.")
        self.assertEqual(R.apply_places("Совсем другой текст.", places, "вдруг", "", False),
                         ("Совсем другой текст.", 0))


class ReplaceWindowTest(WindowCase):
    def test_replace_everywhere_keeps_versions(self):
        one = self.chapter("Книга", "Глава 1", "Кира пришла.")
        two = self.chapter("Мир", "Кира", "Также: Кирочка\nСестра Киры.")
        w = self.window()
        w.open_path(one)

        class Pick:
            def __init__(self, parent, query, texts, speller):
                self.places = R.find_places(texts, "Кира", whole=True)

            def exec(self):
                return True

            def settings(self):
                return "Кира", "Мира", False, True, False

            def chosen(self):
                return self.places
        self.patch("ReplaceDialog", Pick)
        w.show_replace_all()
        wait(0.2)
        self.assertEqual(S.read_text(one), "Мира пришла.")
        self.assertEqual(w.editor.toPlainText(), "Мира пришла.")          # открытая глава перечитана
        self.assertEqual(S.read_text(S.list_versions(one)[0]), "Кира пришла.")
        self.assertEqual(S.read_text(two), "Также: Кирочка\nСестра Киры.")  # «Киры» без «все падежи» не тронуты
