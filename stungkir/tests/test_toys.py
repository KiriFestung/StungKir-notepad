# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Рулетка, антистресс, огонёк серии, места часов и строки, свои цвета полосок."""
import random
import unittest
from datetime import date, timedelta

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest

from stungkir import config as C
from stungkir.tests.helpers import WindowCase, app, wait


class RouletteLogicTest(unittest.TestCase):
    def test_one_bullet_in_six_and_chance_grows(self):
        from stungkir.roulette import CHAMBERS, Roulette
        for seed in range(40):
            r = Roulette(random.Random(seed))
            r.spin()
            chances = []
            for _ in range(CHAMBERS):
                chances.append(r.chance())
                if r.pull() == "live":
                    break
            else:
                self.fail("шесть щелчков без «баха» - патрона нет")
            self.assertEqual(chances, [(1, n) for n in range(CHAMBERS, CHAMBERS - len(chances), -1)])

    def test_loads(self):
        from stungkir.roulette import CHAMBERS, LOADS, Roulette
        self.assertEqual([key for key, *_ in LOADS], ["1", "2", "3", "4", "5", "6"])   # «6 и холостой» убран
        for key, _title, live in LOADS:
            r = Roulette(random.Random(3), load=key)
            self.assertEqual(r.chambers.count("live"), live, key)
            self.assertEqual(len(r.chambers), CHAMBERS)
        full = Roulette(random.Random(1), load="6")
        self.assertEqual(full.chance_text(), "вызов будет точно")
        self.assertTrue(all(full.pull() == "live" for _ in range(10)))
        self.assertEqual(Roulette(load="ерунда").load, "1")

    def test_hundred_challenges_by_level(self):
        from stungkir.roulette import CHALLENGES, LEVEL_CHALLENGES, LEVELS, Roulette, level_pool
        self.assertEqual(len(CHALLENGES), 100)
        self.assertEqual(len(set(CHALLENGES)), 100)
        self.assertEqual(len(LEVELS), 6)
        self.assertEqual(set(level_pool(5)), set(LEVEL_CHALLENGES[5][1] + LEVEL_CHALLENGES[4][1]))
        self.assertEqual(set(level_pool(1)), set(LEVEL_CHALLENGES[1][1]))
        r = Roulette(random.Random(4))
        self.assertTrue(all(r.challenge(level=5) in level_pool(5) for _ in range(50)))
        self.assertEqual({r.challenge(["своё"], True, 3) for _ in range(10)}, {"своё"})

    def test_challenges_own_and_builtin(self):
        from stungkir.roulette import CHALLENGES, Roulette, own_list
        self.assertGreaterEqual(len(set(CHALLENGES)), 15)
        for text in CHALLENGES:
            self.assertNotIn("—", text)                 # внутри текста - короткое тире
        r = Roulette(random.Random(1))
        self.assertIn(r.challenge(), CHALLENGES)
        self.assertEqual({r.challenge(["своё"], only_own=True) for _ in range(20)}, {"своё"})
        mixed = {r.challenge(["своё"]) for _ in range(300)}
        self.assertIn("своё", mixed)
        self.assertGreater(len(mixed), 5)
        self.assertIn(r.challenge([], only_own=True), CHALLENGES)   # своих нет - встроенные
        self.assertEqual(own_list(" раз \n\n два\n  "), ["раз", "два"])


class RouletteDialogTest(WindowCase):
    def _dialog(self):
        from stungkir.dice import RandomDialog
        results = []
        settings = QSettings(C.APP_ID, C.APP_ID)
        dialog = RandomDialog(None, ["Кира"], [], settings, results.append)
        dialog.set_mode("roulette")
        dialog.show()
        return dialog, results, settings

    def test_spin_pull_until_bang(self):
        dialog, results, _settings = self._dialog()
        self.assertTrue(dialog.revolver.isVisible())
        dialog.spin()
        dialog.pull()                                    # пока крутится - только доводит барабан
        self.assertFalse(results)
        for _ in range(6):
            dialog.pull()
            dialog.revolver.finish()
            if results:
                break
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].startswith("Рулетка: "))
        self.assertTrue(dialog.revolver.revealed)
        self.assertIn("live", dialog.revolver.shown)
        dialog.revolver.grab()
        dialog.pull()                                    # после «баха» - сперва прокрутка
        self.assertFalse(dialog.revolver.revealed)
        self.assertEqual(len(results), 1)
        dialog.close()

    def test_drum_is_loaded_before_spin(self):
        dialog, _results, _settings = self._dialog()
        heard = []
        dialog._sound = lambda name, strength=1.0: heard.append(name)
        dialog.load_box.setCurrentIndex(dialog.load_box.findData("3"))
        dialog.spin()
        self.assertIsNotNone(dialog.revolver.loading)          # сначала зарядка
        for value in (0.1, 0.4, 0.7, 0.95):
            dialog.revolver._load_step(value)
            dialog.revolver.grab()
        dialog.revolver.finish()                               # зарядка кончилась - пошла прокрутка
        self.assertEqual(heard.count("round_in"), 3)
        self.assertIn("drum_spin", heard)
        self.assertIsNone(dialog.revolver.loading)
        dialog.revolver.finish()
        dialog.spin()                                          # без перезарядки - сразу крутится
        self.assertIsNone(dialog.revolver.loading)
        dialog.close()

    def test_level_and_own_challenges(self):
        from stungkir.roulette import level_pool
        dialog, results, settings = self._dialog()
        dialog.load_box.setCurrentIndex(dialog.load_box.findData("6"))
        self.assertEqual(settings.value("roulette_load"), "6")
        dialog.level_box.setCurrentIndex(dialog.level_box.findData(5))
        self.assertEqual(int(settings.value("roulette_level")), 5)
        dialog.revolver.finish()
        dialog.pull()                                    # полный барабан - сразу бах
        self.assertIn(results[-1].removeprefix("Рулетка: "), level_pool(5))
        settings.setValue("roulette_own", "Мой вызов")
        settings.setValue("roulette_only_own", "true")
        dialog.pull()                                    # после «баха» - прокрутка
        dialog.revolver.finish()
        dialog.pull()
        self.assertEqual(results[-1], "Рулетка: Мой вызов")
        dialog.close()

class AntistressTest(WindowCase):
    def test_bubbles_pop_once_and_sheet_refills(self):
        from stungkir.antistress import COLUMNS, ROWS, StressDialog
        dialog = StressDialog(None)
        dialog.resize(700, 520)
        dialog.show()
        wait(0.05)
        wrap = dialog.wrap
        size, origin = wrap.cell(), wrap._origin()
        point = QPoint(int(origin.x() + size / 2), int(origin.y() + size / 2))
        QTest.mouseClick(wrap, Qt.LeftButton, Qt.NoModifier, point)
        QTest.mouseClick(wrap, Qt.LeftButton, Qt.NoModifier, point)       # второй раз тот же не лопается
        self.assertEqual(wrap.popped_total, 1)
        QTest.mouseClick(wrap, Qt.LeftButton, Qt.NoModifier, QPoint(1, 1))  # мимо листа
        self.assertEqual(wrap.popped_total, 1)
        for col in range(COLUMNS):
            for row in range(ROWS):
                wrap.pop((col, row))
        self.assertTrue(wrap.all_popped())
        for _ in range(60):                              # лист кончился - новый сам (под нагрузкой - чуть позже)
            wait(0.05)
            if not wrap.popped:
                break
        self.assertFalse(wrap.popped)
        self.assertEqual(wrap.popped_total, COLUMNS * ROWS)
        dialog.close()

    def test_ball_squeezes_and_springs_back(self):
        from stungkir.antistress import StressDialog
        dialog = StressDialog(None)
        dialog.show()
        dialog._show_page(1)
        ball = dialog.ball
        center = QPoint(ball.width() // 2, ball.height() // 2)
        QTest.mousePress(ball, Qt.LeftButton, Qt.NoModifier, center)
        wait(0.3)
        self.assertGreater(ball.squeeze, 0.2)
        ball.grab()
        QTest.mouseRelease(ball, Qt.LeftButton, Qt.NoModifier, center)
        for _ in range(60):                              # под нагрузкой анимация может запаздывать
            wait(0.05)
            if ball.spring.state() != ball.spring.State.Running:
                break
        self.assertAlmostEqual(ball.squeeze, 0.0, places=2)
        self.assertEqual(ball.squeezes, 1)
        self.assertFalse(dialog.refill.isVisible())
        dialog.close()

    def test_sand_rake_goes_around_stones(self):
        from PySide6.QtCore import QPointF
        from stungkir.antistress import StressDialog
        heard = []
        dialog = StressDialog(None)
        dialog.resize(760, 560)
        dialog.show()
        dialog._show_page(3)
        sand = dialog.sand
        sand.on_rake = heard.append
        wait(0.05)
        self.assertIn(len(sand.stones), (2, 3))
        x, y, _r = sand.stones[0]
        w, h = sand.width(), sand.height()
        a, b = QPointF(0.02 * w, y * h), QPointF(0.98 * w, y * h)          # прямо через камень
        runs = sand._tine_paths([a + (b - a) * (k / 60) for k in range(61)])
        self.assertGreater(len(runs), sand.TINES)                          # зубья над камнем прервались
        QTest.mousePress(sand, Qt.LeftButton, Qt.NoModifier, QPoint(20, 20))
        for k in range(1, 12):
            QTest.mouseMove(sand, QPoint(20 + k * 25, 20 + k * 6))
            wait(0.02)
        QTest.mouseRelease(sand, Qt.LeftButton, Qt.NoModifier, QPoint(300, 86))
        self.assertEqual(sand.strokes, 1)
        sand.grab()
        dialog._refill()                                                   # «Разровнять»
        self.assertEqual((sand.strokes, sand.lines), (0, []))
        dialog.close()

    def test_toggles_click_and_guarded_switch(self):
        from stungkir.antistress import StressDialog, Toggles
        heard = []
        dialog = StressDialog(None)
        dialog.show()
        dialog._show_page(4)
        panel = dialog.toggles
        panel.on_sound = heard.append
        panel.toggle(0, 0)
        panel.toggle(0, 0)
        self.assertEqual(heard, ["toggle_up", "toggle_down"])
        col, row = Toggles.SPECIAL
        panel.toggle(col, row)                                   # сначала откидывается крышка
        self.assertFalse(panel.state[row][col])
        self.assertTrue(panel.guard_open)
        panel.toggle(col, row)
        self.assertTrue(panel.state[row][col])
        self.assertEqual(heard[-2:], ["guard_open", "toggle_up"])
        wait(0.3)
        self.assertGreater(panel.party, 0)                      # огоньки гуляют
        panel.grab()
        dialog.close()

    def test_toggle_puzzles_are_solvable_and_levels_go_on(self):
        from stungkir.antistress import PUZZLES, StressDialog, make_puzzle, puzzle_flip
        for kind, (_t, cols, rows, pattern, _r) in PUZZLES.items():
            for level in (1, 2, 17, 250):
                state, solution = make_puzzle(kind, level)
                self.assertEqual((len(state), len(state[0])), (rows, cols))
                self.assertFalse(all(all(r) for r in state))               # не решена с порога
                self.assertEqual(make_puzzle(kind, level), (state, solution))   # уровень всегда тот же
                for x, y in solution:
                    puzzle_flip(state, x, y, pattern)
                self.assertTrue(all(all(r) for r in state), f"{kind} {level}")
        dialog = StressDialog(None)
        dialog.show()
        dialog._show_page(4)
        dialog.toggle_mode.setCurrentIndex(dialog.toggle_mode.findData("medium"))
        panel = dialog.toggles
        self.assertEqual((panel.cols, panel.rows, panel.level), (4, 4, 1))
        self.assertFalse(dialog.next_button.isEnabled())
        panel.show_hint()
        self.assertIn(panel.hint, panel.solution)
        wrong = next((x, y) for y in range(4) for x in range(4) if (x, y) not in panel.solution)
        panel.toggle(*wrong)                                               # лишний ход - и его надо отменить
        self.assertIn(wrong, panel.solution)
        for cell in sorted(panel.solution):
            panel.toggle(*cell)
        self.assertTrue(panel.solved)
        self.assertIn("решено", dialog.count.text())
        self.assertTrue(dialog.next_button.isEnabled())
        panel.grab()
        dialog._next_level()
        self.assertEqual(panel.level, 2)
        self.assertFalse(panel.solved)
        again = StressDialog(None)                                         # уровень и режим запомнились
        self.assertEqual((again.toggles.puzzle, again.toggles.level), ("medium", 2))
        again.toggle_mode.setCurrentIndex(0)                               # просто щёлкать
        self.assertEqual((again.toggles.cols, again.toggles.rows), (5, 3))
        dialog.close()
        again.close()

    def test_stone_skipping(self):
        import random
        from stungkir.antistress import StoneSkip, StressDialog
        self.assertEqual(StoneSkip.skip_chance(0.9, 20), 0.0)              # отвесно - бульк
        self.assertEqual(StoneSkip.skip_chance(0.2, 2), 0.0)               # медленно - бульк
        self.assertGreater(StoneSkip.skip_chance(0.2, 20), 0.9)
        heard = []
        dialog = StressDialog(None)
        dialog.resize(860, 600)
        dialog.show()
        dialog._show_page(5)
        skip = dialog.skip
        skip.on_sound = lambda name, strength: heard.append(name)
        random.seed(2)
        skip.throw(1.0, 0, 40)                                             # круто вверх - ни одного блинчика
        skip.finish()
        self.assertEqual(skip.skips, 0)
        self.assertEqual(heard[-1], "water_plunk")
        best = []
        for seed in range(6):
            random.seed(seed)
            skip.throw(0.9, 0, 10)
            skip.finish()
            best.append(skip.skips)
        self.assertGreater(max(best), 2)
        self.assertIn("water_skip", heard)
        self.assertEqual(skip.best, max(best))
        self.assertIn("Блинчиков", dialog.count.text())
        self.assertEqual(int(dialog.settings.value("skip_best")), max(best))
        # бросок мышью: зажал, оттянул вниз, отпустил
        start = QPoint(skip.width() // 2, skip.height() // 2)
        QTest.mousePress(skip, Qt.LeftButton, Qt.NoModifier, start)
        QTest.mouseMove(skip, start + QPoint(-30, 160))
        QTest.mouseRelease(skip, Qt.LeftButton, Qt.NoModifier, start + QPoint(-30, 160))
        self.assertIsNotNone(skip.stone)
        skip.grab()
        skip.finish()
        dialog.close()

    def test_spinner_follows_hand_and_spins_long(self):
        import math
        from stungkir.antistress import StressDialog
        dialog = StressDialog(None)
        dialog.resize(760, 520)
        dialog.show()
        dialog._show_page(2)
        spinner = dialog.spinner
        wait(0.05)
        c = QPoint(spinner.width() // 2, spinner.height() // 2)
        r = min(spinner.width(), spinner.height()) // 3

        def at(deg):
            a = math.radians(deg)
            return c + QPoint(int(r * math.cos(a)), int(r * math.sin(a)))
        QTest.mousePress(spinner, Qt.LeftButton, Qt.NoModifier, at(0))
        start = spinner.angle
        for k in range(1, 9):                                    # тянем по кругу по часовой
            QTest.mouseMove(spinner, at(k * 20))
            wait(0.015)
        self.assertAlmostEqual((spinner.angle - start) % 360, 160, delta=6)   # шёл ровно за рукой
        self.assertEqual(spinner.speed, 0.0)                     # пока держат - сам не крутится
        QTest.mouseRelease(spinner, Qt.LeftButton, Qt.NoModifier, at(160))
        self.assertGreater(spinner.speed, 300)                   # толкнули по часовой
        spinner.flick(1800)
        wait(1.0)
        self.assertGreater(spinner.speed, 1300)                  # тормозит плавно, а не сразу
        QTest.mousePress(spinner, Qt.LeftButton, Qt.NoModifier, at(0))
        self.assertEqual(spinner.speed, 0.0)                     # схватил - остановил
        QTest.mouseRelease(spinner, Qt.LeftButton, Qt.NoModifier, at(0))
        dialog.close()

    def test_f12_opens_it(self):
        w = self.window()
        seen = []
        from stungkir import dialogs
        original = dialogs.Sheet.exec
        dialogs.Sheet.exec = lambda dialog: seen.append(type(dialog).__name__) or 0
        self.addCleanup(setattr, dialogs.Sheet, "exec", original)
        QTest.keyClick(w.editor, Qt.Key_F12)
        self.assertEqual(seen, ["StressDialog"])


class StreakPopTest(WindowCase):
    def _window_with_streak(self):
        w = self.window()
        for days in range(1, 4):
            w.stats[(date.today() - timedelta(days=days)).isoformat()] = 400
        w._streak_seen = None
        w.today_base = 0
        w.update_status()
        return w

    def test_pops_when_day_counts_not_at_start(self):
        w = self._window_with_streak()
        self.assertFalse(w.streak_pop.isVisible())       # при запуске - тихо
        w.today_base = 300                               # набрал 250+ слов - день засчитан
        w.update_status()
        self.assertTrue(w.streak_pop.isVisible())
        self.assertIn("4 дня подряд", w.streak_pop.label)
        for t in (0.05, 0.2, 0.5, 0.9):
            w.streak_pop.t = t
            w.streak_pop.grab()
        w.update_status()                                # та же серия - второй раз не выпрыгивает
        w.streak_pop.hide()
        w.update_status()
        self.assertFalse(w.streak_pop.isVisible())

    def test_flame_grows_and_talks(self):
        from stungkir.widgets import STREAK_LINES, StreakPop, streak_line
        self.assertEqual([StreakPop.stage(n) for n in (1, 9, 10, 25, 49, 50, 300)], [0, 0, 1, 2, 4, 5, 5])
        self.assertIn(streak_line(4, "cheer"), STREAK_LINES["cheer"])
        self.assertIn(streak_line(4, "roast"), STREAK_LINES["roast"])
        self.assertEqual(streak_line(4, "quiet"), "")
        self.assertNotEqual(streak_line(20, "cheer"), streak_line(21, "cheer"))
        w = self._window_with_streak()
        w.set_streak_voice("roast")
        w.today_base = 300
        w.update_status()
        self.assertIn(w.streak_pop.line, STREAK_LINES["roast"])
        pop = w.streak_pop
        for count in (4, 12, 23, 37, 45, 60):                     # каждая ступень рисуется
            pop.play(count, "x", streak_line(count, "cheer"))
            for t in (0.1, 0.5, 0.9):
                pop.t = t
                pop.grab()

    def test_quiet_when_streak_hidden(self):
        w = self._window_with_streak()
        w.set_screen_shown("streak", False)
        w.today_base = 300
        w.update_status()
        self.assertFalse(w.streak_pop.isVisible())


class PlacesTest(WindowCase):
    def test_bar_on_top_left_and_clock_bottom(self):
        w = self.window()
        w.goal = 500
        w.update_status()
        layout = w.main_layout
        self.assertGreater(layout.indexOf(w.status), layout.indexOf(w.split))
        w.set_place("bar", "top")
        self.assertLess(layout.indexOf(w.status), layout.indexOf(w.split))
        self.assertLess(layout.indexOf(w.goal_strip), layout.indexOf(w.split))
        w.set_place("align", "left")
        self.assertTrue(w.status.alignment() & Qt.AlignLeft)
        self.assertEqual(w.goal_strip.align, "left")
        w.set_place("clock", "bl")
        wait(0.05)
        central = w.centralWidget()
        self.assertLess(w.corner_clock.x(), central.width() / 2)
        self.assertGreater(w.corner_clock.y(), central.height() / 2)
        w.set_place("clock", "что-то не то")             # испорченная настройка - угол по умолчанию
        self.assertEqual(w.place("clock"), "tr")
        w2 = self.window()                               # запомнилось
        self.assertLess(w2.main_layout.indexOf(w2.status), w2.main_layout.indexOf(w2.split))


class BarColorsTest(WindowCase):
    def test_own_bar_colors_are_used_and_previewed(self):
        app()
        palette = dict(C.palette())
        palette["BAR_DAY"] = "#00ff00"
        C.set_palette(palette)
        from stungkir.widgets import GoalStrip
        self.assertEqual(GoalStrip().color("day").name(), "#00ff00")
        for name, theme in C.THEMES.items():
            for key in C.BAR_KEYS:
                self.assertIn(key, theme, name)
        custom = C.all_themes({"custom_themes": {"Моя": {"BG": "#ffffff", "TEXT": "#000000"}}})["Моя"]
        for key in C.BAR_KEYS:                           # своя тема без цветов полосок - подобраны
            self.assertGreaterEqual(C.contrast(custom[key], "#ffffff"), 2.9)
        from PySide6.QtGui import QFont
        from stungkir.colors import ColorsDialog
        dialog = ColorsDialog(None, {}, QFont("DejaVu Sans", 12))
        dialog.preview.strip.grab()
        self.assertEqual(dialog.preview.strip.colors["BAR_BOOK"], dialog.colors()["BAR_BOOK"])


class ArtworkTest(WindowCase):
    def test_pictures_are_bundled(self):
        from stungkir import artwork
        for name in ("weasel", "coin-heads", "coin-tails", "drum", "round-live", "round-blank", "round-spent",
                     "ball", "cork", "pin-indigo", "pin-ochre", "about", "empty", "bubble-0", "bubble-popped-0"):
            picture = artwork.pixmap(name)
            self.assertFalse(picture.isNull(), name)
            if name != "cork":                                       # пробка - сплошная плитка
                self.assertTrue(picture.hasAlphaChannel(), f"{name}: нет прозрачности")
        self.assertTrue(artwork.pixmap("нет такой").isNull())       # нет файла - пусто, без падения
        small = artwork.scaled("weasel", 60, 2.0)
        self.assertEqual(small.width(), 120)

    def test_wheel_rungs_are_visible(self):
        """Перекладины колеса должны быть охристыми, а не залиты серединой (была такая ошибка)."""
        from PySide6.QtGui import QColor
        from stungkir.widgets import FoxWheel
        wheel = FoxWheel()
        wheel.setFixedHeight(220)
        wheel.resize(300, 220)
        wheel.angle = 0
        image = wheel.grab().toImage()
        r, cx, cy = wheel._geometry()
        band = max(4.0, r * 0.16)
        color = image.pixelColor(int(cx + r - band / 2), int(cy))
        self.assertLess(C.hue_gap(color, QColor(C.FOX_2)), 0.05, color.name())
        wheel.set_running(True)
        wheel.celebrate()
        for _ in range(5):
            wheel._frame()
            wheel.grab()

    def test_coin_sides_are_pictures(self):
        from stungkir.dice import COIN_SIDES, Die3D
        self.assertEqual(set(COIN_SIDES), {"Ворон", "Ласка"})
        for side in COIN_SIDES:
            die = Die3D(150)
            die.resize(170, 150)
            die.roll("coin", side)
            die.finish()
            die.grab()


class DrawnLookTest(WindowCase):
    def test_drawn_icons_follow_theme_color(self):
        from stungkir import icons
        self.assertTrue((icons.DRAWN / "check.png").is_file())
        for color in ("#ff0000", "#00ff00"):
            image = icons.make_icon("check", color).pixmap(48, 48).toImage()
            seen = {image.pixelColor(x, y).name() for x in range(48) for y in range(48)
                    if image.pixelColor(x, y).alpha() > 250}
            self.assertEqual(seen, {color})
        self.assertFalse(icons.make_icon("calendar", "#ffffff").isNull())     # линейный (SVG) тоже есть

    def test_empty_page_picture(self):
        w = self.window()
        self.assertTrue(w.empty_hint.isVisible())                 # пустая страница - картинка
        self.assertEqual(w.empty_hint.geometry(), w.editor.viewport().rect())
        w.empty_hint.grab()
        w.editor.insertPlainText("Т")
        self.assertFalse(w.empty_hint.isVisible())               # первая буква - картинка ушла
        w.editor.selectAll()
        w.editor.textCursor().removeSelectedText()
        self.assertTrue(w.empty_hint.isVisible())
        w.set_zen(True)
        self.assertFalse(w.empty_hint.isVisible())

    def test_about_has_header_and_full_text(self):
        from stungkir import dialogs
        w = self.window()
        seen = {}

        def look(dialog):
            dialog.show()
            labels = [child for child in dialog.findChildren(dialogs.QLabel) if child.pixmap() and
                      not child.pixmap().isNull()]
            seen["header"] = bool(labels)
            text = [child for child in dialog.findChildren(dialogs.QLabel) if "Лицензия" in child.text()][0]
            seen["fits"] = text.height() >= text.heightForWidth(text.width()) - 2
            return 0
        original = dialogs.Sheet.exec
        dialogs.Sheet.exec = look
        self.addCleanup(setattr, dialogs.Sheet, "exec", original)
        w.show_about()
        self.assertEqual(seen, {"header": True, "fits": True})

    def test_corkboard_and_bubbles_paint(self):
        from stungkir.antistress import StressDialog
        from stungkir.corkboard import cork_tile
        self.assertFalse(cork_tile().isNull())
        dialog = StressDialog(None)
        dialog.show()
        dialog.wrap.pop((0, 0))
        dialog.wrap.grab()
        dialog.ball.grab()
        dialog.close()


class CompareWithVersionTest(WindowCase):
    def test_old_version_beside_text(self):
        import time
        from stungkir import storage as S
        from stungkir.textutil import old_side_html
        html, summary = old_side_html("Раз два три.\n\nКонец.", "Раз два.\n\nСередина.\n\nКонец.")
        self.assertIn("три", html)
        self.assertIn("чего теперь нет: 1 слово", summary)
        self.assertEqual(old_side_html("А", "А")[1], "Совпадает с нынешним текстом")

        path = self.chapter("Книга", "Глава 1", "Старый текст главы.")
        S.snapshot(path, "Старый текст главы.")
        time.sleep(1.05)
        w = self.window()
        w.open_path(path)
        w.editor.selectAll()
        w.editor.insertPlainText("Новый текст главы.")
        w.compare_with_version()
        self.assertTrue(w.side.isVisible())
        self.assertTrue(w.side.showing_version)
        self.assertEqual(w.split.indexOf(w.side), 0)                  # слева от текста
        self.assertIn("Старый", w.side.view.toPlainText())
        self.assertIn("2 из 2", w.side.note.text())          # свежая версия совпадает с текстом - взята прошлая
        w.editor.insertPlainText(" Ещё.")                              # пишем дальше - сравнение обновляется
        w.side_compare_timer.timeout.emit()
        w.save()                                                      # сохранение не выкидывает из сравнения
        self.assertTrue(w.side.showing_version)
        w.flip_side()
        self.assertEqual(w.split.indexOf(w.side), 1)
        other = self.chapter("Книга", "Глава 2", "Другая.")
        w.open_path(other)                                            # другая глава - версия чужая, панель закрыта
        self.assertFalse(w.side.isVisible())
        w.open_beside(path)                                           # обычная панель рядом - как раньше
        self.assertFalse(w.side.showing_version)
        self.assertIn("Новый", w.side.view.toPlainText())

    def test_no_versions_no_crash(self):
        w = self.window()
        w.compare_with_version()                                      # ничего не открыто
        path = self.chapter("Книга", "Пустая", "")
        w.open_path(path)
        w.compare_with_version()
        self.assertFalse(w.side.isVisible())


class TypewriterAndBreaksTest(WindowCase):
    def test_typing_sound_only_when_on(self):
        import time
        w = self.window()
        w.sounds.played.clear()
        QTest.keyClick(w.editor, Qt.Key_A)
        self.assertEqual(w.sounds.played, [])                 # по умолчанию тихо
        w.set_typing_sound("Тихо")
        for key in (Qt.Key_A, Qt.Key_Space, Qt.Key_Return):
            w._typed_sound_at = 0.0
            QTest.keyClick(w.editor, key)
        names = [n for n, _l in w.sounds.played]
        self.assertTrue(names[0].startswith("type_"))
        self.assertEqual(names[1:], ["type_space", "type_return"])
        w._typed_sound_at = time.monotonic()
        QTest.keyClick(w.editor, Qt.Key_B)                    # зажатая клавиша - не очередь
        self.assertEqual(len(w.sounds.played), 3)

    def test_eye_break_reminds_after_minutes_of_writing(self):
        import time
        w = self.window()
        w.settings.setValue("eye_break", 1)
        w.isActiveWindow = lambda: True
        w._last_typed = time.monotonic()
        fired = [w._eye_break_tick() for _ in range(60)]
        self.assertEqual(fired.count(True), 1)
        self.assertTrue(fired[-1])
        self.assertIn("chime", [n for n, _l in w.sounds.played])
        w._last_typed = time.monotonic() - 400                # отошёл от компьютера - отдых засчитан
        w._screen_time = 50
        w._eye_break_tick()
        self.assertEqual(w._screen_time, 0)
        w.settings.setValue("eye_break", 0)
        self.assertFalse(any(w._eye_break_tick() for _ in range(200)))


class ThemeNamesTest(unittest.TestCase):
    def test_default_and_old_names(self):
        self.assertEqual(C.DEFAULT_THEME, "Индиго и охра")
        self.assertEqual(C.theme_colors({}, "Зелёная")["BG"], C.THEMES["Мох"]["BG"])     # старое имя - не слетает
        self.assertEqual(C.theme_colors({}, "Лиса")["BG"], C.THEMES["Сирень"]["BG"])
        self.assertEqual(C.THEMES["Индиго и охра"]["IMPORTANT"], "#d4a02e")
