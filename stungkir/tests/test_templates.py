# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Шаблоны карточек справочника: встроенные, свои из готовой карточки, выбор при создании."""
import unittest

from stungkir.core import config as C
from stungkir.core import storage as S
from stungkir.world import templates as T
from stungkir.tests.helpers import WindowCase


class SkeletonTest(unittest.TestCase):
    def test_values_are_removed(self):
        text = "Также: Кирочка\nКто: лучница\nВозраст: 19\nПросто строка без раздела.\n# Связи\nСестра: Ния"
        self.assertEqual(T.skeleton(text), "Кто: \nВозраст: \n# Связи\nСестра: \n")
        self.assertEqual(T.skeleton("без разделов"), "")


class TemplateWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        (C.ROOT / "Мир").mkdir()
        self.w = self.window()
        self.w.lore_cfg["categories"].append("Мир")

    def test_new_card_in_lore_category_starts_from_template(self):
        self.w.ask_category = lambda: C.ROOT / "Мир"
        self.w.ask_name = lambda *a: "Кира"
        self.w.choose_template = lambda: T.BUILTIN["Персонаж"]
        self.assertTrue(self.w.new_file())
        self.assertEqual(S.read_text(C.ROOT / "Мир" / "Кира.txt"), T.BUILTIN["Персонаж"])
        self.assertEqual(self.w.editor.toPlainText(), T.BUILTIN["Персонаж"])
        self.w.choose_template = lambda: None                    # передумал - файла нет
        self.w.ask_name = lambda *a: "Ния"
        self.assertFalse(self.w.new_file())
        self.assertFalse((C.ROOT / "Мир" / "Ния.txt").exists())

    def test_save_own_template_and_see_it_in_dialog(self):
        card = C.ROOT / "Мир" / "Тервена.txt"
        card.write_text("Строй: республика\nСтолица: Лосс\n", encoding="utf-8", newline="\n")
        self.patch("ask_text", lambda *a, **k: ("Моё государство", True))
        self.w.save_as_template(card)
        self.assertEqual(T.user_templates(), {"Моё государство": "Строй: \nСтолица: \n"})
        dialog = T.TemplateDialog(self.w)
        dialog.list.setCurrentRow(dialog.list.count() - 1)
        self.assertEqual(dialog.text(), "Строй: \nСтолица: \n")
        self.assertTrue(dialog.delete.isVisibleTo(dialog))
