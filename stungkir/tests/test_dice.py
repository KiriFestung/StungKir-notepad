# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Объёмные кубики и «Случайное»: число, монетка, список, персонаж или термин."""
import random
import unittest

from stungkir.dice import Die3D, RandomDialog, list_items, pick_number, shape
from stungkir.tests.helpers import WindowCase, app


class ShapesTest(unittest.TestCase):
    def test_solids_have_right_faces(self):
        for kind, faces, corners in ((4, 4, 3), (6, 6, 4), (8, 8, 3), (10, 10, 4), (12, 12, 5), (20, 20, 3)):
            _points, found = shape(kind)
            self.assertEqual(len(found), faces, kind)
            self.assertEqual({len(f) for f in found}, {corners}, kind)

    def test_die_lands_on_result(self):
        app()
        random.seed(5)
        for sides in (4, 6, 8, 10, 12, 20, 100):
            for result in (1, sides // 2 or 1, sides):
                die = Die3D()
                die.resize(200, 150)
                got = []
                die.roll(sides, result, got.append)
                self.assertTrue(die.rolling)
                die.finish()
                self.assertEqual(got, [result])
                self.assertEqual(die.front_label(), str(result))
                self.assertEqual(die.relabeled, 0, (sides, result))   # число не перекрашивалось на глазах
                if sides != 100:                                  # числа на гранях не повторяются
                    self.assertEqual(sorted(die.labels), sorted(map(str, range(1, sides + 1))))
                die.grab()                                        # и нарисовать получается

    def test_coin(self):
        app()
        die = Die3D()
        die.roll("coin", "Ласка")
        die.finish()
        self.assertEqual(die.front_label(), "Ласка")
        self.assertIsNone(die.highlight)
        die.roll("coin", "Ребро")                          # встала на ребро
        die.finish()
        self.assertEqual(die.front_label(), "Ребро")
        die.resize(160, 140)
        die.grab()

    def test_number_never_changes_on_the_face(self):
        """То, что видно на грани в момент приземления, и есть результат: грань не перекрашивается."""
        app()
        random.seed(11)
        die = Die3D()
        die.resize(200, 150)
        for _ in range(40):
            sides = random.choice((4, 6, 8, 10, 12, 20, 100))
            result = random.randint(1, sides)
            before = [list(b.labels) for b in die.bodies]
            die.roll(sides, result)
            die.finish()
            self.assertEqual(die.front_label(), str(result))
            if [list(b.labels) for b in die.bodies] != before and len(before) == len(die.bodies) and \
                    sides != 100 and sorted(before[0]) == sorted(die.labels):
                self.fail(f"надписи граней переставлены: d{sides}")
        self.assertEqual(die.relabeled, 0)

    def test_d100_is_two_dice(self):
        from stungkir.dice import d100_parts, d100_value
        app()
        self.assertEqual(d100_parts(100), ("00", "0"))
        self.assertEqual(d100_parts(7), ("00", "7"))
        self.assertEqual(d100_parts(70), ("70", "0"))
        self.assertEqual(sorted(d100_value(*d100_parts(n)) for n in range(1, 101)), list(range(1, 101)))
        die = Die3D()
        die.resize(220, 150)
        die.roll(100, 37)
        die.finish()
        self.assertEqual(len(die.bodies), 2)
        self.assertEqual(sorted(die.bodies[0].labels), [f"{n:02d}" for n in range(0, 100, 10)])
        self.assertEqual(sorted(die.bodies[1].labels), [str(n) for n in range(10)])
        self.assertEqual(die.front_label(), "37")
        die.grab()

    def test_fair(self):
        """Честность: монетка поровну и ребро около 1%, числа и рулетка - без перекоса."""
        from stungkir.dice import toss_coin
        from stungkir.roulette import CHAMBERS, Roulette
        rng = random.Random(2026)
        n = 200_000
        counts = {}
        for _ in range(n):
            side = toss_coin(rng)
            counts[side] = counts.get(side, 0) + 1
        self.assertAlmostEqual(counts["Ребро"] / n, 0.01, delta=0.002)
        self.assertAlmostEqual(counts["Ворон"] / n, 0.495, delta=0.006)
        self.assertAlmostEqual(counts["Ласка"] / n, 0.495, delta=0.006)
        for sides in (4, 6, 20, 100):
            got = [0] * sides
            for _ in range(sides * 2000):
                got[pick_number(1, sides, rng) - 1] += 1
            expected = 2000
            chi = sum((g - expected) ** 2 / expected for g in got)
            self.assertLess(chi, sides * 2 + 40, sides)       # хи-квадрат: перекоса нет
        r = Roulette(rng)
        spots = [0] * CHAMBERS
        for _ in range(60_000):
            spots[r.spin()] += 1
        self.assertLess(max(spots) - min(spots), 600)

    def test_helpers(self):
        self.assertEqual(list_items(" дождь\n\nтуман \n"), ["дождь", "туман"])
        for _ in range(50):
            self.assertTrue(3 <= pick_number(7, 3) <= 7)


class RandomWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.w = self.window()

    def dialog(self, names=("Кира", "Ния"), terms=()):
        self.entries = []
        return RandomDialog(self.w, list(names), list(terms), self.w.settings, self.entries.append)

    def test_panel_die_rolls_into_history(self):
        self.w.roll(20)
        self.w.dice_value.finish()
        self.assertEqual(self.w.history.count(), 1)
        self.assertRegex(self.w.history.item(0).text(), r"^d20:\s+\d+$")

    def test_number(self):
        d = self.dialog()
        self.assertEqual(d.windowTitle(), "Рандомайзеры")
        d.set_mode("number")
        d.low.setValue(9)
        d.high.setValue(5)
        d.draw()
        d.draw()                                          # пока перебирает - второй раз не бросить
        d.shuffle.finish()
        self.assertEqual(len(self.entries), 1)
        self.assertRegex(self.entries[-1], r"^Число 5–9: [5-9]$")
        self.assertEqual(int(d.settings.value("random_high")), 5)

    def test_dice_pictures_follow_material(self):
        from stungkir import config as C
        from stungkir.artwork import pixmap
        from stungkir.dicetable import MATERIALS
        for material in MATERIALS:
            for sides in C.DICE:
                self.assertFalse(pixmap(f"dice/{material}/d{sides}").isNull(), f"{material} d{sides}")
        d = self.dialog()
        d.set_mode("dice")
        before = d.dice_group.buttons()[0].icon().cacheKey()
        d.material_group.button(list(MATERIALS).index("resin")).click()
        self.assertEqual(d.material.currentData(), "resin")
        self.assertTrue(d.material_group.button(list(MATERIALS).index("resin")).isChecked())
        self.assertNotEqual(d.dice_group.buttons()[0].icon().cacheKey(), before)
        d.material.setCurrentIndex(d.material.findData("oak"))
        self.assertTrue(d.material_group.button(list(MATERIALS).index("oak")).isChecked())

    def test_dice_and_coin_on_the_table(self):
        d = self.dialog()
        d.show()
        d.set_mode("dice")
        self.assertTrue(d.table.isVisible())
        for sides, material in ((20, "bone"), (6, "metal"), (100, "oak")):
            next(b for b in d.dice_group.buttons() if b.property("sides") == sides).setChecked(True)
            d.material.setCurrentIndex(d.material.findData(material))
            d.draw()
            d.draw()                                         # катится - второй раз не бросить
            d.table.grab()
            d.table.finish()
            title = d.material.currentText().lower()
            self.assertRegex(self.entries[-1], rf"^d{sides} \({title}\): \d+$")
            self.assertEqual(d.table.front_label(), self.entries[-1].rsplit(" ", 1)[1])
            self.assertEqual(d.shuffle.text(), self.entries[-1].rsplit(" ", 1)[1])
        self.assertEqual(len(self.entries), 3)
        self.assertEqual(d.table.relabeled, 0)
        self.assertEqual(d.settings.value("dice_material"), "oak")
        d.set_mode("coin")
        d.draw()
        d.table.finish()
        self.assertRegex(self.entries[-1], r"^Монетка: (ворон|ласка|на ребро)")
        d.set_mode("list")
        self.assertFalse(d.table.isVisible())

    def test_table_lands_every_number_honestly(self):
        from stungkir.dicetable import DiceTable
        app()
        random.seed(3)
        table = DiceTable()
        table.resize(640, 290)
        heard = []
        table.on_sound = lambda name, strength: heard.append(name)
        for _ in range(30):
            sides = random.choice((4, 6, 8, 10, 12, 20, 100))
            result = random.randint(1, sides)
            table.throw(sides, result, random.choice(("bone", "metal", "oak")))
            table.finish()
            self.assertEqual(table.front_label(), str(result))
        for side in ("Ворон", "Ласка", "Ребро"):
            table.toss(side)
            table.finish()
            self.assertEqual(table.front_label(), side)
        self.assertEqual(table.relabeled, 0)                  # грань ни разу не перекрашивалась
        self.assertTrue({"coin_flick", "coin_land"} <= set(heard))
        self.assertTrue({"bone_hit", "oak_hit", "die_hit"} & set(heard))

    def test_panel_waits_until_die_lands(self):
        self.w.roll(20)
        self.w.roll(6)                                    # кубик ещё катится - не считается
        self.w.flip_coin()
        self.w.dice_value.finish()
        self.assertEqual(self.w.history.count(), 1)
        self.assertTrue(self.w.history.item(0).text().startswith("d20:"))
        self.w.flip_coin()
        self.w.dice_value.finish()
        self.assertRegex(self.w.history.item(0).text(), r"^Монетка: (ворон|ласка|на ребро)")

    def test_list_without_repeats(self):
        d = self.dialog()
        d.set_mode("list")
        d.list_edit.setPlainText("дождь\nтуман\nясно")
        d.cross_out.setChecked(True)
        seen = []
        for _ in range(3):
            d.draw()
            d.shuffle.finish()
            seen.append(self.entries[-1].removeprefix("Из списка: "))
        self.assertEqual(sorted(seen), ["дождь", "туман", "ясно"])
        self.assertEqual(d.list_edit.toPlainText().strip(), "")
        d.draw()
        self.assertIn("Список пуст", d.note.text())

    def test_character_or_term(self):
        from stungkir.lore import LoreTerm
        d = self.dialog(terms=[LoreTerm("Тервена"), LoreTerm("Кира")])      # «Кира» - и персонаж, и термин: один раз
        d.set_mode("cast")
        self.assertEqual(sorted(t for t, _ in d._pool()), ["Кира", "Ния", "Тервена"])
        d.draw()
        d.shuffle.finish()
        self.assertRegex(self.entries[-1], r"^(Персонаж|Термин): (Кира|Ния|Тервена)$")
        empty = self.dialog(names=())
        empty.set_mode("cast")
        empty.draw()
        self.assertIn("не из чего", empty.note.text())


class SoundTest(unittest.TestCase):
    def test_die_knocks_in_time_with_bounces(self):
        app()
        heard = []
        die = Die3D()
        die.on_sound = lambda name, strength: heard.append((name, strength))
        die.roll(20, 7)
        die.finish()
        self.assertEqual([n for n, _s in heard], ["die_hit", "die_hit", "die_hit", "die_settle"])
        strengths = [s for _n, s in heard[:3]]
        self.assertEqual(strengths, sorted(strengths, reverse=True))           # каждый отскок тише

    def test_coin_rings(self):
        app()
        heard = []
        die = Die3D()
        die.on_sound = lambda name, strength: heard.append(name)
        die.roll("coin", "Орёл")
        die.finish()
        self.assertEqual(heard, ["coin_flick", "coin_land", "coin_land"])

    def test_volume_is_baked_into_file(self):
        import os
        import tempfile
        import wave
        from array import array
        from stungkir import sounds
        folder = tempfile.mkdtemp()
        old = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = folder
        try:
            def peak(path):
                with wave.open(str(path)) as w:
                    return max(abs(x) for x in array("h", w.readframes(w.getnframes())))
            full = peak(sounds.FOLDER / "die_hit_1.wav")
            quiet = sounds.scaled("die_hit_1", 0.3)
            self.assertTrue(str(quiet).startswith(folder))
            self.assertAlmostEqual(peak(quiet) / full, 0.3, delta=0.01)
        finally:
            if old is None:
                os.environ.pop("XDG_CACHE_HOME")
            else:
                os.environ["XDG_CACHE_HOME"] = old

    def test_settings_volume_and_silence(self):
        from stungkir.sounds import Sounds
        s = Sounds(volume="Тихо")
        s.play("coin_flick", 1.0)
        s.set_volume("Без звука")
        s.play("die_hit", 1.0)
        self.assertEqual(s.played[0], ("coin_flick", 0.3))
        self.assertEqual(s.played[1][1], 0.0)
