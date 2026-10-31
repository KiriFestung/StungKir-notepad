# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Кто в какой главе: счёт упоминаний по главам, пропажи, переход к месту."""
import unittest

from stungkir.world import presence as P
from stungkir.tests.helpers import WindowCase


class GapTest(unittest.TestCase):
    def test_longest_gap(self):
        self.assertEqual(P.longest_gap([1, 0, 0, 0, 2, 0, 1]), 3)
        self.assertEqual(P.longest_gap([0, 3, 0]), 0)            # одно упоминание - не пропажа
        self.assertEqual(P.longest_gap([]), 0)


class PresenceWindowTest(WindowCase):
    def test_matrix_and_click(self):
        world = self.tmp / "StungKir" / "Мир"
        world.mkdir()
        (world / "Тервена.txt").write_text("Прибрежное государство.", encoding="utf-8", newline="\n")
        self.chapter("Книга", "Глава 1", "Кира пришла в Тервену.")
        self.chapter("Книга", "Глава 2", "Тихо.")
        self.chapter("Книга", "Глава 3", "Строка.\nКиры нет, но о Тервене говорят. Тервена далеко.")
        w = self.window()
        w.lore_cfg["categories"].append("Мир")
        w.track_name("Кира")
        w.rebuild_lore()
        texts = w.crutch_texts()
        counts, first = P.presence(w.lore, texts)
        self.assertEqual(counts["Кира"], [1, 0, 1])
        self.assertEqual(counts["Тервена"], [1, 0, 2])
        opened = []
        dialog = P.PresenceDialog(w, w.lore, texts, lambda path, n, s: opened.append((path.stem, n, s)))
        self.assertEqual(dialog.table.rowCount(), 2)
        dialog.kind.setCurrentIndex(1)                            # только персонажи
        self.assertEqual([t.name for t in dialog.terms], ["Кира"])
        dialog._clicked(0, 2)
        self.assertEqual(opened, [("Глава 3", 1, 0)])
        w._open_line_place(texts[2][0], 1, 0)
        self.assertTrue(w.editor.textCursor().block().text().startswith("Киры"))
