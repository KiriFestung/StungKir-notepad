# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""«Слепи снеговика»: ступени от дневной цели, снос на 300%, снеговик сезона, вкладка и двор за окном."""
import unittest
from datetime import date

from stungkir.core import config as C
from stungkir.fun import snowman as S
from stungkir.tests.helpers import Sandbox, WindowCase, app, wait


class CountTest(unittest.TestCase):
    def test_progress_by_goal(self):
        self.assertEqual(S.progress(0, 500), (0, 0.0))
        self.assertEqual(S.progress(250, 500), (0, 50.0))
        self.assertEqual(S.progress(1500, 500), (1, 0.0))              # 300% - снесли, лепится второй
        self.assertEqual(S.progress(1750, 500), (1, 50.0))
        self.assertEqual(S.progress(100, 0)[0], 0)                     # без цели - цель по умолчанию

    def test_next_stage(self):
        self.assertEqual(S.next_stage(0, 0, 500), ("снежный ком", 50))
        self.assertEqual(S.next_stage(100, 500, 500), ("шарф", 100))
        self.assertEqual(S.next_stage(50, 1750, 500), ("средний шар", 50))   # второй снеговик

    def test_items_grow_with_percent(self):
        self.assertEqual(S.items_for(90), set())
        self.assertEqual(S.items_for(130), {"face", "arms", "scarf"})
        self.assertIn("bird", S.items_for(260))

    def test_vehicle_is_stable(self):
        self.assertIn(S.vehicle("2026-12-20", 1), S.VEHICLES)
        self.assertEqual(S.vehicle("2026-12-20", 1), S.vehicle("2026-12-20", 1))
        self.assertEqual({S.vehicle(f"2026-12-{d}", 1) for d in range(15, 31)}, set(S.VEHICLES))   # все бывают

    def test_season_words_cross_new_year(self):
        stats = {"2026-12-14": 900, "2026-12-15": 1000, "2026-12-31": 500, "2027-01-02": 250, "2027-01-20": 999}
        self.assertEqual(S.season_bounds(date(2027, 1, 3)), (date(2026, 12, 15), date(2027, 1, 14)))
        self.assertEqual(S.season_words(stats, date(2027, 1, 3)), 1750)
        self.assertEqual(S.season_words(stats, date(2027, 1, 2), live_today=400), 1900)    # сегодня - живые слова
        self.assertEqual(S.season_items(2500), S.SEASON_ITEMS[:2])
        self.assertEqual(len(S.season_items(10 ** 6)), len(S.SEASON_ITEMS))
        self.assertTrue(set(S.SEASON_KEYS) == set(S.SEASON_ITEMS))


class YardTest(Sandbox):
    def test_knocked_at_300_percent(self):
        yard = S.Yard()
        yard.update(400, 500, "2026-12-20", 0.0)
        self.assertFalse(yard.busy())
        yard.update(1510, 500, "2026-12-20", 1.0)                      # перешли 300% - кто-то едет
        self.assertTrue(yard.busy())
        self.assertEqual(yard.done, 1)
        app()
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QImage, QPainter
        image = QImage(300, 200, QImage.Format_ARGB32)
        for now in (1.0, 2.0, 3.0, 4.5):                                # едет, сносит, уезжает
            p = QPainter(image)
            yard.paint(p, QPointF(150, 180), 120, 300, now)
            p.end()
        self.assertFalse(yard.busy())

    def test_no_knock_when_opened_late_in_the_day(self):
        yard = S.Yard()
        yard.update(2000, 500, "2026-12-20", 0.0)                     # открыли программу, уже написано много
        self.assertFalse(yard.busy())
        self.assertEqual(yard.done, 1)

    def test_every_stage_and_vehicle_paints(self):
        app()
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QImage, QPainter
        image = QImage(400, 300, QImage.Format_ARGB32)
        p = QPainter(image)
        for percent in (0, 5, 25, 45, 70, 90, 110, 160, 220, 280):
            S.paint_snowman(p, QPointF(200, 280), 200, percent)
        S.paint_snowman(p, QPointF(200, 280), 200, S.FULL, set(S.SEASON_KEYS.values()))
        S.paint_pile(p, QPointF(200, 280), 200)
        for kind in S.VEHICLES:
            S.paint_vehicle(p, kind, QPointF(200, 280), 100, 0.3)
        p.end()

    def test_winter_is_remembered(self):
        S.remember(date(2026, 12, 20), 3200, 2)
        S.remember(date(2026, 12, 20), 3300, 1)                        # снесённые за день не уменьшаются
        winter = S.load_winters()["2026-2027"]
        self.assertEqual(winter["words"], 3300)
        self.assertEqual(winter["items"], 3)
        self.assertEqual(winter["days"]["2026-12-20"], 2)


class WindowSnowmanTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, C, "SEASON_ROOM", False)
        self.addCleanup(setattr, C, "SEASON", None)
        from stungkir.fun.dice import use_season_coin
        self.addCleanup(use_season_coin, False)

    def test_yard_follows_words_and_tab_shows(self):
        from stungkir.ui.windows import load_config_raw
        config = load_config_raw()
        config["season"] = "xmas"
        C.save_config(config)
        w = self.window()
        w.update_palette()
        w.goal = 100
        w.today_base = 70                                              # 70% цели - уже есть голова
        w.season.tick(force=True)
        self.assertGreaterEqual(w.season.room.yard.percent, 60)
        w.today_base = 320                                             # 320% - снеговика снесли
        w.season.tick(force=True)
        self.assertEqual(w.season.room.yard.done, 1)
        self.assertTrue(w.season.room.yard.busy())
        self.assertFalse(w.grab().isNull())
        from stungkir.fun.antistress import StressDialog
        dialog = StressDialog(w)
        self.assertIsNotNone(getattr(dialog, "snowman", None))
        dialog._show_page(dialog.pages.indexOf(dialog.snowman))
        wait(0.1)
        self.assertIn("320%", dialog.snowman.text)
        self.assertFalse(dialog.snowman.grab().isNull())
        dialog.close()

    def test_no_snowman_tab_outside_season(self):
        from stungkir.fun.antistress import StressDialog
        w = self.window()
        dialog = StressDialog(w)
        self.assertIsNone(getattr(dialog, "snowman", None))
        dialog.close()
