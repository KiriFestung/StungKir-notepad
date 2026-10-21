# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ритм главы: предложения, сводка, переход к предложению."""
import unittest

from stungkir import rhythm as R
from stungkir.tests.helpers import WindowCase

TEXT = ("# Пролог\nУтро было серым. Туман стелился над рекой! — Лодки не будет, — сказала она… Да?\n"
        "* * *\nКоротко [пометка] тут.\nБез точки в конце")


class SentencesTest(unittest.TestCase):
    def test_split(self):
        found = R.sentences(TEXT)
        self.assertEqual([s[4] for s in found], ["Утро было серым.", "Туман стелился над рекой!",
                                                 "— Лодки не будет, — сказала она…", "Да?",
                                                 "Коротко [пометка] тут.", "Без точки в конце"])
        self.assertEqual([s[3] for s in found], [3, 4, 5, 1, 2, 4])     # пометка не считается

    def test_summary(self):
        self.assertIn("6 предложений", R.summary(R.sentences(TEXT)))
        self.assertIn("в среднем 3,2", R.summary(R.sentences(TEXT)))
        self.assertIn("нет предложений", R.summary([]))


class RhythmWindowTest(WindowCase):
    def test_pick_selects_sentence(self):
        w = self.window()
        w.editor.setPlainText(TEXT)
        items = R.sentences(TEXT)
        dialog = R.RhythmDialog(w, "Глава", items, w._select_sentence)
        dialog.grab()                                              # рисуется без ошибок
        w._select_sentence(items[2])
        self.assertEqual(w.editor.textCursor().selectedText(), "— Лодки не будет, — сказала она…")
