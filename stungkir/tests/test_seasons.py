# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Праздники: даты, цвета, огоньки гирлянды, комната под текстом, снежная полоска, окно настроек."""
import unittest
from datetime import date

from stungkir.core import config as C
from stungkir.core import seasons
from stungkir.tests.helpers import Sandbox, WindowCase, app, wait


class DatesTest(unittest.TestCase):
    def test_christmas_crosses_new_year(self):
        start, end = seasons.SEASONS["xmas"]["from"], seasons.SEASONS["xmas"]["to"]
        for day, inside in ((date(2026, 12, 14), False), (date(2026, 12, 15), True), (date(2026, 12, 31), True),
                            (date(2027, 1, 1), True), (date(2027, 1, 14), True), (date(2027, 1, 15), False),
                            (date(2027, 7, 1), False)):
            self.assertEqual(seasons.in_range(day, start, end), inside, day)

    def test_choice(self):
        winter, summer = date(2026, 12, 20), date(2026, 7, 1)
        self.assertEqual(seasons.active({}, winter), "xmas")                      # по умолчанию - по датам
        self.assertIsNone(seasons.active({}, summer))
        self.assertIsNone(seasons.active({"season": "off"}, winter))
        self.assertEqual(seasons.active({"season": "xmas"}, summer), "xmas")      # «всегда»
        self.assertIsNone(seasons.active({"season": "что-то"}, summer))           # мусор - как по умолчанию

    def test_options_survive_garbage(self):
        bad = {"season_room": "да", "season_garland": 5, "season_garland_colors": None,
               "season_custom_colors": ["красный", 7, "#123456"]}
        self.assertTrue(seasons.option(bad, "season_room"))
        self.assertEqual(seasons.option(bad, "season_garland"), "twinkle")
        self.assertEqual(seasons.option(bad, "season_custom_colors"), ["#123456"])
        self.assertEqual(seasons.garland_colors({"season_garland_colors": "custom", "season_custom_colors": []}),
                         seasons.DEFAULTS["season_custom_colors"])

    def test_bulb_levels(self):
        for mode in seasons.GARLAND_MODES:
            levels = [seasons.bulb_level(mode, i, 30, t / 10) for i in range(30) for t in range(40)]
            self.assertTrue(all(0.0 <= v <= 1.0 for v in levels), mode)
            if mode == "steady":
                self.assertEqual(set(levels), {1.0})
            else:
                self.assertGreater(max(levels) - min(levels), 0.2, mode)       # видно, что огоньки живут
        self.assertEqual(seasons.bulb_level("random", 3, 30, 1.5), seasons.bulb_level("random", 3, 30, 1.5))

    def test_palette_replaces_theme_only_in_season(self):
        winter = __import__("datetime").datetime(2026, 12, 20, 12)
        colors = C.current_palette({"theme": "Мох"}, winter)
        self.assertEqual(colors["BG"], seasons.SEASONS["xmas"]["palette"]["BG"])
        self.assertTrue(all(k in colors for k in C.COLOR_KEYS))
        own = C.current_palette({"theme": "Мох", "season_colors": False}, winter)
        self.assertEqual(own["BG"], C.THEMES["Мох"]["BG"])
        summer = C.current_palette({"theme": "Мох"})                        # в проверках «сегодня» - лето
        self.assertEqual(summer["BG"], C.THEMES["Мох"]["BG"])


class ArtTest(Sandbox):
    def test_art_is_there_and_draws(self):
        app()
        from stungkir.fun.season_scene import Art
        art = Art("xmas")
        for name in ("tree", "presents", "snowman", "lantern", "fireplace", "chair", "wreath"):
            self.assertTrue(art.renderers[name].isValid(), name)
            pix = art.pixmap(name, 120)
            self.assertFalse(pix.isNull(), name)
            image = pix.toImage()
            painted = sum(image.pixelColor(x, y).alpha() > 0 for x in range(0, image.width(), 4)
                          for y in range(0, image.height(), 4))
            self.assertGreater(painted, 20, name)                                 # что-то нарисовано
        self.assertTrue(art.spec["tree"]["lights"])
        self.assertEqual(len(art.spec["fireplace"]["fire"]), 4)

    def test_room_layout_fits_window(self):
        app()
        from PySide6.QtCore import QRectF, QSize
        from stungkir.fun.season_scene import Art, Room
        room = Room(Art("xmas"), {})
        wide = room.layout(QSize(1600, 900))
        for key in ("fireplace", "tree", "snowman", "lantern", "chair_left", "chair_right"):
            self.assertIn(key, wide)
            self.assertTrue(QRectF(0, 0, 1600, 900).intersects(wide[key]), key)
        self.assertLess(wide["tree"].right(), wide["fireplace"].left())
        self.assertLess(wide["fireplace"].right(), wide["lantern"].left())
        narrow = room.layout(QSize(600, 500))
        self.assertIn("fireplace", narrow)
        self.assertNotIn("lantern", narrow)                  # в узком окне лишнее убирается


class WindowSeasonTest(WindowCase):
    def season(self, **options):
        from stungkir.ui.windows import load_config_raw
        config = load_config_raw()
        config.update(options)
        C.save_config(config)

    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, C, "SEASON_ROOM", False)
        self.addCleanup(setattr, C, "SEASON", None)

    def test_room_turns_on_and_off(self):
        self.season(season="xmas")
        w = self.window()
        w.update_palette()
        self.assertEqual(C.SEASON, "xmas")
        self.assertIs(w.editor.scene, w.season)
        self.assertIsNotNone(w.season.overlay)
        self.assertEqual(C.BG, seasons.SEASONS["xmas"]["palette"]["BG"])
        wait(0.3)
        for _ in range(5):                                      # кадры идут без ошибок
            w.season.tick(force=True)
        image = w.grab().toImage()
        self.assertFalse(image.isNull())
        self.assertTrue(w.backdrop_layer.isVisible())
        self.season(season="off")
        w.update_palette()
        self.assertIsNone(C.SEASON)
        self.assertIsNone(w.editor.scene)
        self.assertIsNone(w.season.overlay)
        self.assertFalse(w.season.timer.isActive())
        self.assertIsNone(w.goal_strip.bar_painter)

    def test_only_colors_without_room(self):
        self.season(season="xmas", season_room=False)
        w = self.window()
        w.update_palette()
        self.assertEqual(C.SEASON, "xmas")
        self.assertIsNone(w.editor.scene)                       # комнаты нет - поле как обычно
        self.assertFalse(C.SEASON_ROOM)

    def test_still_picture_without_motion(self):
        self.season(season="xmas", season_motion=False)
        w = self.window()
        w.update_palette()
        self.assertFalse(w.season.timer.isActive())
        self.assertEqual(w.season.mode, "steady")

    def test_overlay_snow_calms_down_while_typing(self):
        self.season(season="xmas")
        w = self.window()
        w.update_palette()
        overlay = w.season.overlay
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.keyClicks(w.editor, "snow")
        for _ in range(30):
            w.season._last -= 0.05                               # время идёт без ожидания
            w.season.tick(force=True)
        self.assertLess(overlay.snow_alpha, 0.5)
        self.assertTrue(overlay.testAttribute(Qt.WA_TransparentForMouseEvents))

    def test_snow_bar_draws(self):
        self.season(season="xmas")
        w = self.window()
        w.update_palette()
        strip = w.goal_strip
        strip.items["day"]["anim"].stop()
        strip.items["day"].update(value=0.6, shown=True, done=True)
        self.assertFalse(strip.grab().isNull())

    def test_settings_dialog(self):
        from stungkir.fun.season_settings import SeasonDialog
        w = self.window()
        dialog = SeasonDialog(w)
        dialog.choice.setCurrentIndex(dialog.choice.findData("xmas"))
        self.assertEqual(C.SEASON, "xmas")
        dialog.palette.setCurrentIndex(dialog.palette.findData("custom"))
        self.assertTrue(dialog.swatches[0].isVisibleTo(dialog))
        dialog.mode.setCurrentIndex(dialog.mode.findData("chase"))
        self.assertEqual(w.season.mode, "chase")
        dialog.boxes["season_room"].setChecked(False)
        self.assertIsNone(w.editor.scene)
        dialog.choice.setCurrentIndex(dialog.choice.findData("off"))
        self.assertIsNone(C.SEASON)
        self.assertFalse(dialog.mode.isEnabled())
        dialog.close()
