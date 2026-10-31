# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Пробковая доска: свободное место карточек, нитки, переключение с колонками, сохранение."""
import json

from PySide6.QtCore import QPointF

from stungkir.core import config as C
from stungkir.core import storage as S
from stungkir.tests.helpers import WindowCase
from stungkir.tests.test_board import FakeCard

DATA = {"columns": [
    {"title": "Завязка", "cards": [{"title": "Туман", "text": "Лодки не будет"}, {"title": "Посол"}]},
    {"title": "Развязка", "cards": [{"title": "Мост", "color": "purple"}]}]}


class CorkboardTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.w = self.window()
        self.path = C.ROOT / "Книга" / "План.board"
        self.path.parent.mkdir()
        self.path.write_text(json.dumps(DATA, ensure_ascii=False), encoding="utf-8", newline="\n")
        self.w.open_path(self.path)
        self.board = self.w.board_view
        self.patch("CardDialog", FakeCard)

    def saved(self):
        return json.loads(S.read_text(self.path))

    def by_title(self):
        return {item.card["title"]: item for item in self.board.free.items_by_id.values()}

    def test_free_mode_places_cards_and_saves_everything(self):
        self.board.set_mode("free")
        items = self.by_title()
        self.assertEqual(set(items), {"Туман", "Посол", "Мост"})
        self.assertLess(items["Туман"].pos().x(), items["Мост"].pos().x())        # колонки - столбиками
        items["Мост"].setPos(900, 40)
        self.board.free.start_link(items["Туман"])
        self.board.free.finish_link(items["Мост"])
        self.board.free.start_link(items["Мост"])
        self.board.free.finish_link(items["Туман"])                                   # та же нитка - не дублируется
        self.w.save()
        data = self.saved()
        self.assertEqual(data["mode"], "free")
        self.assertEqual(len(data["links"]), 1)
        most = data["columns"][1]["cards"][0]
        self.assertEqual((most["x"], most["y"]), (900, 40))
        self.assertFalse(self.w.is_modified())

    def test_reopen_and_switch_back_keeps_columns(self):
        self.board.set_mode("free")
        self.by_title()["Посол"].setPos(500, 300)
        self.w.save()
        self.w.path = None
        self.w.open_path(self.path)
        board = self.w.board_view
        self.assertEqual(board.mode, "free")
        self.assertEqual(self.by_title()["Посол"].pos(), QPointF(500, 300))
        board.set_mode("columns")
        self.assertEqual([c["title"] for c in board.columns[0].cards()], ["Туман", "Посол"])
        self.assertEqual(board.columns[0].cards()[1]["x"], 500)               # место на пробке помнится

    def test_new_and_deleted_card_on_cork(self):
        self.board.set_mode("free")
        self.board.new_free_card(QPointF(700, 500))
        self.assertIn("Встреча", self.by_title())
        self.assertEqual(self.board.columns[0].cards()[-1]["title"], "Встреча")
        items = self.by_title()
        self.board.free.start_link(items["Встреча"])
        self.board.free.finish_link(items["Туман"])
        self.board._free_delete(items["Встреча"])
        self.assertNotIn("Встреча", [c["title"] for c in self.board.columns[0].cards()])
        self.assertEqual(self.board.free.links, [])                            # нитка ушла вместе с карточкой

    def test_find_on_cork_selects_card(self):
        self.board.set_mode("free")
        self.board.reset_find()
        self.assertEqual(self.board.find("мост"), (1, 1))
        self.assertTrue(self.by_title()["Мост"].isSelected())

    def test_old_boards_stay_in_old_format(self):
        self.board.columns[0].list.item(0)                                     # просто открыли и сохранили
        self.w.save()
        self.assertNotIn("mode", self.saved())
