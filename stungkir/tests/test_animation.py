# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Нарисованные анимации и картинки: кадры на месте (и в готовой сборке), играют и кончаются,
игрушки и праздники их показывают, а без кадров всё рисуется по-старому."""
import random
import unittest

from PySide6.QtCore import QPointF, QSettings

from stungkir import config as C
from stungkir.tests.helpers import WindowCase, app, wait

# имя анимации -> сколько кадров должно быть
FRAMES = {
    "anim/weasel-run/weasel-run": 10, "anim/weasel-cheer/weasel-cheer": 12,
    **{f"anim/flame/flame-{k}": 12 for k in range(6)},
    "anim/goal/goal-day": 24, "anim/goal/goal-chapter": 12,
    "anim/table/felt-dust": 8, "anim/table/crit-high": 16, "anim/table/crit-low": 16,
    "anim/coin/coin-edge-shine": 12, "anim/roulette/drum-glint": 8,
    **{f"anim/bubble-pop/bubble-{k}-pop": 6 for k in range(3)},
    "anim/ball/ball-dust": 8, "anim/lake/skip-splash": 8, "anim/lake/skip-plunk": 12,
    "anim/toggle/puzzle-solved": 12, "anim/bang/bang": 16, "anim/dust/dust": 8,
}
PICTURES = ("lake-shore", "skip-stone", "stone-1", "stone-2", "stone-3", "stone-4", "rake", "toggle-up",
            "toggle-down", "empty-search", "empty-trash", "empty-versions", "empty-notes", "eye-break",
            "about-day", "drum-bone", "drum-metal", "drum-oak", "drum-indigo")


class Clock:
    """Часы для проверок: время идёт, только когда скажешь."""

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class FramesTest(unittest.TestCase):
    def setUp(self):
        app()

    def test_all_frames_and_pictures_are_bundled(self):
        from stungkir.artwork import frame_count, pixmap
        for name, count in FRAMES.items():
            self.assertEqual(frame_count(name), count, name)
            first = pixmap(f"{name}_00")
            self.assertTrue(first.hasAlphaChannel(), name)
        for name in PICTURES:
            self.assertFalse(pixmap(name).isNull(), name)
        self.assertEqual(frame_count("anim/нет/такой"), 0)

    def test_effects_play_once_and_stop(self):
        from PySide6.QtWidgets import QWidget
        from stungkir.artwork import Effects
        host = QWidget()
        host.resize(200, 200)
        clock = Clock()
        effects = Effects(host, clock)
        self.assertFalse(effects.play("anim/нет/такой", 10, 10, 50))
        self.assertTrue(effects.play("anim/ball/ball-dust", 100, 150, 120, anchor="bottom"))
        self.assertTrue(effects.timer.isActive())
        self.assertEqual(effects.frame(effects.live[0]), 0)
        clock.now += 0.11
        self.assertEqual(effects.frame(effects.live[0]), 3)
        host.grab()                                       # рисуется посреди
        clock.now += 1.0
        self.assertFalse(effects.busy)
        effects._tick()
        self.assertEqual(effects.live, [])
        self.assertFalse(effects.timer.isActive())


class OverlaysTest(WindowCase):
    def test_streak_flame_is_drawn_from_frames(self):
        w = self.window()
        pop = w.streak_pop
        drawn = []
        original = pop._paint_drawn
        pop._paint_drawn = lambda *a: drawn.append(original(*a)) or drawn[-1]
        for count in (3, 15, 55):
            pop.play(count, "x дней подряд!", "Так держать!")
            for t in (0.1, 0.5):
                pop.t = t
                pop.grab()
        self.assertTrue(drawn and all(drawn))
        pop.hide()

    def test_goal_burst_when_day_goal_done(self):
        w = self.window()
        w.goal = 10
        w.today_base = 50
        w.settings.remove("goal_done")
        w.check_goal()
        self.assertTrue(w.goal_pop.isVisible())
        clock = Clock()
        effects = w.goal_pop.effects
        effects.clock = clock
        effects.live[0]["start"] = clock.now
        clock.now += 0.4
        w.goal_pop.grab()
        clock.now += 2
        effects._tick()
        w.goal_pop._maybe_hide()
        self.assertFalse(w.goal_pop.isVisible())
        self.assertTrue(w.goal_pop.play("chapter"))
        self.assertFalse(w.goal_pop.play("нет такого"))

    def test_eye_break_shows_weasel_and_versions_empty_picture(self):
        import time
        w = self.window()
        w.settings.setValue("eye_break", 1)
        w.isActiveWindow = lambda: True
        w._last_typed = time.monotonic()
        w._screen_time = 10_000
        self.assertTrue(w._eye_break_tick())
        self.assertTrue(w.picture_pop.isVisible())
        self.assertEqual(w.picture_pop.name, "eye-break")
        w.picture_pop.grab()
        w.picture_pop.hide()
        w.open_path(self.chapter("Книга", "Глава", "Текст главы."))
        w.compare_with_version()
        if w.picture_pop.isVisible():                     # версий нет - песочные часы
            self.assertEqual(w.picture_pop.name, "empty-versions")

    def test_empty_search_and_notes_pictures(self):
        w = self.window()
        self.chapter("Книга", "Глава", "Обычный текст.")
        w.show_global_search()
        w.global_edit.setText("щщщщ")
        w.run_global_search()
        self.assertTrue(w.global_empty.isVisible())
        self.assertEqual(w.global_empty.name, "empty-search")
        w.global_empty.grab()
        w.global_edit.setText("текст")
        w.run_global_search()
        self.assertFalse(w.global_empty.isVisible())
        w.hide_global_search()

    def test_empty_trash_picture(self):
        from stungkir.trash import TrashDialog
        w = self.window()
        dialog = TrashDialog(w, lambda *a: None)
        dialog.show()
        wait(0.05)
        self.assertTrue(dialog.empty_picture.isVisible())
        dialog.grab()
        dialog.close()


class ToyAnimationsTest(WindowCase):
    def test_bubble_pops_through_frames(self):
        from stungkir.antistress import BubbleWrap
        wrap = BubbleWrap()
        wrap.resize(500, 340)
        clock = Clock()
        wrap.clock = clock
        wrap.pop((2, 2))
        self.assertEqual(wrap.pop_frame((2, 2)), 0)
        clock.now += 0.11
        self.assertEqual(wrap.pop_frame((2, 2)), 3)
        wrap.grab()
        clock.now += 1
        self.assertIsNone(wrap.pop_frame((2, 2)))
        wrap._pop_tick()
        self.assertFalse(wrap.pop_timer.isActive())
        wrap.grab()

    def test_ball_raises_dust_on_hard_floor_hit(self):
        from stungkir.antistress import SquishBall
        ball = SquishBall()
        ball.resize(500, 340)
        ball.show()
        wait(0.05)
        r = ball.radius()
        ball.pos = QPointF(250, ball.floor() - r - 1)
        ball.velocity = QPointF(0, 2400)
        ball.clock.invalidate()
        ball._step()
        self.assertEqual(len(ball.dust.live), 1)
        ball.grab()
        ball.pos = QPointF(250, ball.floor() - r - 1)
        ball.velocity = QPointF(0, 400)                       # тихий удар - без пыли
        ball._step()
        self.assertEqual(len(ball.dust.live), 1)

    def test_lake_has_drawn_splashes_stone_and_shore(self):
        from stungkir.antistress import StoneSkip
        lake = StoneSkip()
        lake.resize(700, 420)
        random.seed(3)
        lake.throw(0.85, 0, 12)
        names = set()
        for _ in range(4000):
            lake.t += 1 / 120
            lake._step(1 / 120)
            names |= {s[3] for s in lake.splashes}
            if lake.stone is None:
                break
        self.assertIn("skip-plunk", names)
        self.assertEqual(lake.drops, [])                      # нарисованный «бульк» вместо капель
        lake.grab()
        shore = lake._shore(700)
        self.assertFalse(shore.isNull())
        self.assertIs(lake._shore(700), shore)                # запомнен
        C.set_palette(dict(C.palette(), ACCENT="#2a8a3a"))    # другая тема - берег перекрашен
        self.assertIsNot(lake._shore(700), shore)

    def test_sand_stones_and_rake_cursor(self):
        from stungkir.antistress import ZenSand
        sand = ZenSand()
        sand.resize(600, 400)
        self.assertEqual(len(sand.stone_kinds), len(sand.stones))
        self.assertTrue(set(sand.stone_kinds) <= {1, 2, 3, 4})
        self.assertFalse(sand.cursor().pixmap().isNull())      # курсор - грабли
        sand.grab()

    def test_puzzle_solved_burst_and_drawn_levers(self):
        from stungkir.antistress import Toggles
        toggles = Toggles()
        toggles.resize(700, 400)
        toggles.grab()                                        # просто щёлкать: нарисованные тумблеры
        toggles.start_puzzle("easy", 1)
        for col, row in sorted(toggles.solution):
            toggles.toggle(col, row)
        self.assertTrue(toggles.solved)
        self.assertEqual(len(toggles.effects.live), 1)
        toggles.grab()

    def test_table_dust_and_crits(self):
        from stungkir.dice import COIN_EDGE
        from stungkir.dicetable import DiceTable
        table = DiceTable()
        table.resize(640, 290)
        table.throw(20, 20, "resin")
        table.finish()
        self.assertEqual(table.finale_kind(), "crit-high")
        names = [e["name"] for e in table.under.live]
        self.assertIn("anim/table/crit-high", names)
        self.assertIn("anim/table/felt-dust", names)
        table.grab()
        table.throw(20, 1, "bone")
        table.finish()
        self.assertEqual(table.finale_kind(), "crit-low")
        self.assertIn("anim/table/crit-low", [e["name"] for e in table.over.live])
        table.throw(20, 7, "oak")
        table.finish()
        self.assertIsNone(table.finale_kind())
        table.toss(COIN_EDGE)
        table.finish()
        self.assertEqual(table.finale_kind(), "edge")
        self.assertIn("anim/coin/coin-edge-shine", [e["name"] for e in table.over.live])
        table.grab()

    def test_drum_follows_dice_material_and_glints_after_loading(self):
        from stungkir.dice import RandomDialog
        settings = QSettings(C.APP_ID, C.APP_ID)
        dialog = RandomDialog(None, ["Кира"], [], settings, lambda *a: None)
        dialog.show()
        index = dialog.material.findData("oak")
        dialog.material.setCurrentIndex(index)
        self.assertEqual(dialog.revolver.material, "oak")
        dialog.revolver.load(["live", "empty", "empty", "empty", "empty", "empty"])
        dialog.revolver.finish_load()
        self.assertEqual(dialog.revolver.effect[0], "glint")
        dialog.revolver.grab()
        dialog.close()
