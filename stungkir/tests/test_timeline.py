# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Хронология: порядок по году, правка событий, поиск, место среди файлов."""
import json
import unittest
from pathlib import Path

from stungkir.core import config as C
from stungkir.core import storage as S
from stungkir.core import textutil as T
from stungkir.world import timeline as TL
from stungkir.tests.helpers import WindowCase, wait

EVENTS = [{"when": "Весна 312 г.", "year": 312, "title": "Падение Лосса", "text": "Город сдан."},
          {"when": "Древность", "year": -40, "title": "Основание", "text": ""},
          {"when": "Осень 312 г.", "year": 312.5, "title": "Мир", "text": ""}]


class TimelineLogicTest(unittest.TestCase):
    def test_order_and_text(self):
        self.assertEqual([e["title"] for e in TL.sort_events(EVENTS)], ["Основание", "Падение Лосса", "Мир"])
        self.assertEqual(TL.timeline_text(EVENTS).split("\n")[:3],
                         ["Древность - Основание", "Весна 312 г. - Падение Лосса", "Город сдан."])
        self.assertEqual(TL.load_events("не json"), [])
        self.assertEqual(TL.year_label(312.5), "312,5")

    def test_types(self):
        self.assertTrue(T.is_timeline(Path("а.timeline")))
        self.assertFalse(T.is_prose(Path("а.timeline")))
        self.assertTrue(T.is_prose(Path("а.txt")))
        text = json.dumps({"events": EVENTS}, ensure_ascii=False)
        self.assertIn("Падение Лосса", T.searchable_text(Path("а.timeline"), text))


class FakeEvent:
    deleted = False
    data = {"when": "Зима 313 г.", "year": 313, "title": "Коронация", "text": "", "color": "purple", "chapter": ""}

    def __init__(self, *a, **k):
        pass

    def exec(self):
        return True

    def event_data(self):
        return dict(self.data)


class TimelineWindowTest(WindowCase):
    def test_create_open_add_edit_save(self):
        w = self.window()
        (C.ROOT / "Мир").mkdir()
        w.ask_category = lambda: C.ROOT / "Мир"
        w.ask_name = lambda *a: "Летопись"
        self.assertTrue(w.new_timeline())
        path = C.ROOT / "Мир" / "Летопись.timeline"
        self.assertIs(w.view, w.timeline_view)
        view = w.timeline_view
        view._fill(EVENTS)
        self.patch("EventDialog", FakeEvent)
        view.new_event()
        self.assertEqual([e["title"] for e in view.events()], ["Основание", "Падение Лосса", "Мир", "Коронация"])
        FakeEvent.data = {**FakeEvent.data, "year": -100, "title": "Первые люди"}
        view.edit_event(view.list.item(3))                         # правка переставляет по году
        self.assertEqual(view.events()[0]["title"], "Первые люди")
        w.save()
        saved = json.loads(S.read_text(path))
        self.assertEqual(len(saved["events"]), 4)
        self.assertEqual(view.find("лосс"), (1, 1))
        self.assertIn("◷ Летопись", [w.tree.topLevelItem(0).child(i).text(0).strip()
                                     for i in range(w.tree.topLevelItem(0).childCount())])
        wait(0.01)
