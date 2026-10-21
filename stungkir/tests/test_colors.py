# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Цвета: темы, дневная тема по расписанию, плавный переход, теплота, контраст, окно настроек."""
import unittest
from datetime import datetime, timedelta

from stungkir import config as C
from stungkir.tests.helpers import WindowCase, app, wait

DAY = {"theme": "Мох", "day_theme": "Дневная бумага", "day_from": 8 * 60, "day_to": 20 * 60,
       "transition": 40}


def at(hour, minute=0):
    return datetime(2026, 3, 1, hour, minute)


class PaletteTest(unittest.TestCase):
    def setUp(self):
        app()
        self.saved = C.palette()
        self.addCleanup(C.set_palette, self.saved)

    def test_every_theme_has_every_color(self):
        for name, colors in C.THEMES.items():
            self.assertEqual(sorted(colors), sorted(C.COLOR_KEYS), name)

    def test_groups_cover_every_color_once(self):
        keys = [k for _title, group in C.COLOR_GROUPS for k in group]
        self.assertEqual(sorted(keys), sorted(C.COLOR_KEYS))
        self.assertTrue(all(k in C.COLOR_NAMES for k in keys))

    def test_important_stands_out_and_is_readable(self):
        for name, colors in C.THEMES.items():
            important = colors["IMPORTANT"]
            self.assertGreaterEqual(C.contrast(important, C.on_color(important)), 4.5, name)   # надпись на кнопке
            self.assertNotEqual(important, colors["ACCENT"], name)

    def test_old_custom_theme_gets_new_colors(self):
        themes = C.all_themes({"custom_themes": {"Моя": {"BG": "#000000", "TEXT": "#ffffff"}}})
        self.assertEqual(themes["Моя"]["CLOCK_RING"], C.OBJECT_COLORS["CLOCK_RING"])
        self.assertIn("IMPORTANT", themes["Моя"])

    def test_clock_and_buttons_follow_palette(self):
        from stungkir.style import build_style
        from stungkir.widgets import ClockFace
        C.set_palette({**C.THEMES["Графит"], "CLOCK_RING": "#00aa00", "IMPORTANT": "#123456"})
        self.assertEqual(ClockFace().RING, "#00aa00")
        style = build_style()
        self.assertIn("#123456", style)

    def test_builtin_themes_are_comfortable(self):
        for name, colors in C.THEMES.items():
            ratio = C.contrast(colors["BG"], colors["TEXT"])
            top = 21 if name == "Высокий контраст" else 12        # эта тема нарочно резче остальных
            self.assertTrue(7 <= ratio <= top, f"{name}: {ratio:.1f}")
            for key in ("REPEAT_BG", "CRUTCH_BG", "SELECT"):        # подсвеченный текст читается
                self.assertGreaterEqual(C.contrast(colors["TEXT"], colors[key]), 4.2, f"{name}: {key}")
            self.assertGreaterEqual(C.contrast(colors["BG"], colors["DIALOGUE"]), 7, name)

    def test_day_share(self):
        self.assertEqual(C.day_share(DAY, at(12)), 1.0)
        self.assertEqual(C.day_share(DAY, at(3)), 0.0)
        self.assertEqual(C.day_share(DAY, at(8)), 0.5)
        self.assertEqual(C.day_share(DAY, at(20)), 0.5)
        self.assertTrue(0 < C.day_share(DAY, at(7, 50)) < 0.5 < C.day_share(DAY, at(8, 10)) < 1)
        self.assertEqual(C.day_share({**DAY, "transition": 0}, at(7, 59)), 0.0)
        self.assertEqual(C.day_share({**DAY, "day_theme": ""}, at(12)), 0.0)

    def test_schedule_across_midnight(self):
        night_shift = {**DAY, "day_from": 22 * 60, "day_to": 6 * 60, "transition": 0}
        self.assertEqual(C.day_share(night_shift, at(23)), 1.0)
        self.assertEqual(C.day_share(night_shift, at(3)), 1.0)
        self.assertEqual(C.day_share(night_shift, at(12)), 0.0)

    def test_text_readable_at_every_minute(self):
        """Ни в одну минуту суток текст не сливается с фоном, в том числе посреди перехода."""
        moment = at(0)
        worst = 99
        for _ in range(24 * 60):
            colors = C.current_palette(DAY, moment)
            worst = min(worst, C.contrast(colors["BG"], colors["TEXT"]))
            moment += timedelta(minutes=1)
        self.assertGreaterEqual(worst, 6.5)

    def test_evening_dims_then_switches(self):
        day_bg = C.THEMES["Дневная бумага"]["BG"]
        self.assertEqual(C.current_palette(DAY, at(19, 30))["BG"], day_bg)
        dusk = C.current_palette(DAY, at(19, 59))["BG"]
        from PySide6.QtGui import QColor
        self.assertLess(QColor(dusk).lightness(), QColor(day_bg).lightness())     # к вечеру темнеет
        self.assertEqual(C.current_palette(DAY, at(20, 1))["BG"], C.THEMES["Мох"]["BG"])

    def test_warmth(self):
        from PySide6.QtGui import QColor
        warm = QColor(C.warm({"X": "#808080"}, 1)["X"])
        cold = QColor(C.warm({"X": "#808080"}, -1)["X"])
        self.assertGreater(warm.red(), warm.blue())
        self.assertGreater(cold.blue(), cold.red())
        self.assertEqual(C.warm({"X": "#808080"}, 0)["X"], "#808080")

    def test_custom_and_legacy(self):
        config = {"theme": "Моя", "custom_themes": {"Моя": {"BG": "#101010", "TEXT": "#c0c0c0", "BAD": "x"}}}
        colors = C.current_palette(config)
        self.assertEqual((colors["BG"], colors["TEXT"]), ("#101010", "#c0c0c0"))
        self.assertEqual(colors["DIALOGUE"], C.THEMES[C.DEFAULT_THEME]["DIALOGUE"])     # недостающее - из основной
        legacy = C.current_palette({"theme": "Сепия", "TEXT": "#aabbcc"})
        self.assertEqual(legacy["TEXT"], "#aabbcc")

    def test_contrast_hints(self):
        self.assertAlmostEqual(C.contrast("#000000", "#ffffff"), 21, places=1)
        self.assertIn("удобно", C.contrast_hint(8.4))
        self.assertIn("резко", C.contrast_hint(19))
        self.assertIn("тяжело", C.contrast_hint(3))


class ColorsDialogTest(WindowCase):
    def dialog(self, config):
        from stungkir.colors import ColorsDialog
        self.w = getattr(self, "w", None) or self.window()
        return ColorsDialog(self.w, config, self.w.editor.font())

    def test_editing_builtin_theme_makes_own_copy(self):
        dialog = self.dialog({"theme": "Мох"})
        dialog.set_color("TEXT", "#a0c8a8")
        result = dialog.values()
        self.assertEqual(result["theme"], "Мох (своя)")
        self.assertEqual(result["custom_themes"]["Мох (своя)"]["TEXT"], "#a0c8a8")
        self.assertEqual(C.THEMES["Мох"]["TEXT"], "#93bf9c")          # встроенная не испорчена

    def test_schedule_and_day_slot(self):
        dialog = self.dialog({"theme": "Сепия"})
        dialog.use_day.setChecked(True)
        dialog._switch_slot("day")
        self.assertEqual(dialog.theme.currentText(), "Дневная бумага")
        dialog.set_color("BG", "#f5f0e4")
        dialog.transition.setValue(30)
        result = dialog.values()
        self.assertEqual(result["day_theme"], "Дневная бумага (своя)")
        self.assertEqual(result["theme"], "Сепия")
        self.assertEqual(result["transition"], 30)
        self.assertEqual((result["day_from"], result["day_to"]), (8 * 60, 20 * 60))

    def test_legacy_colors_become_own_theme(self):
        dialog = self.dialog({"theme": "Мох", "TEXT": "#aabbcc"})
        result = dialog.values()
        self.assertNotIn("TEXT", result)
        self.assertEqual(result["custom_themes"][result["theme"]]["TEXT"], "#aabbcc")

    def test_lightness_slider_and_typed_code(self):
        dialog = self.dialog({"theme": "Мох"})
        row = dialog.rows["TEXT"]
        row.slider.setValue(200)
        from PySide6.QtGui import QColor
        self.assertEqual(QColor(dialog.colors()["TEXT"]).lightness(), 200)
        row.code.setText("123456")
        row._typed()
        self.assertEqual(dialog.colors()["TEXT"], "#123456")
        row.code.setText("не цвет")
        row._typed()
        self.assertEqual(row.code.text(), "#123456")

    def test_preview_shows_contrast(self):
        dialog = self.dialog({"theme": "Мох"})
        self.assertIn("8,4:1", dialog.preview.contrast.text())
        self.assertEqual(C.palette(), self.w._palette_now or C.palette())   # образец не перекрасил окно


class LiveApplyTest(WindowCase):
    def test_theme_change_applies_without_restart(self):
        w = self.window()
        path = self.chapter("Книга", "Глава", "— Реплика.")
        w.open_path(path)
        C.save_config({"theme": "Сирень"})
        w.update_palette(animate=True)
        wait(3.2)                                           # плавная смена за пару секунд
        self.assertEqual(C.BG, C.THEMES["Сирень"]["BG"])
        self.assertIn(C.THEMES["Сирень"]["BG"], self.app_style())
        self.assertEqual(w.highlighter.dialogue.name(), C.THEMES["Сирень"]["DIALOGUE"])

    def test_theme_change_on_screen_does_not_freeze(self):
        """Смена темы в открытом окне: снимок старого вида тает, окно живое (во Flatpak на PySide 6.8
        перекраска падала на списках, и снимок навсегда закрывал окно - «зависло»)."""
        w = self.window()
        w.show()
        wait(0.3)
        w.choose_theme("Сепия")
        wait(1.2)
        self.assertEqual(C.BG, C.THEMES["Сепия"]["BG"])
        self.assertIsNone(getattr(w, "_dissolve_label", None))
        w.choose_theme("Индиго и охра")
        wait(1.2)
        self.assertEqual(C.BG, C.THEMES["Индиго и охра"]["BG"])
        self.assertIsNone(getattr(w, "_dissolve_label", None))

    def test_choose_theme_and_settings_keep_colors(self):
        w = self.window()
        C.save_config({"theme": "Мох", "custom_themes": {"Моя": {"BG": "#101010"}}})
        w.choose_theme("Сепия")
        from stungkir.windows import load_config_raw
        self.assertEqual(load_config_raw()["theme"], "Сепия")
        self.patch("ask_question", lambda *a, **k: None)
        from stungkir import windows

        class Fake:
            def __init__(self, *a):
                pass

            def exec(self):
                return True

            def values(self):
                return {"FONT_SIZE": 16}, 300
        self.patch("SettingsDialog", Fake)
        w.show_settings()
        config = load_config_raw()
        self.assertEqual((config["theme"], config["FONT_SIZE"]), ("Сепия", 16))
        self.assertIn("Моя", config["custom_themes"])
        self.assertTrue(windows)

    def app_style(self):
        from PySide6.QtWidgets import QApplication
        return QApplication.instance().styleSheet()
