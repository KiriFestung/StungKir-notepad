# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Правка текста кнопками: курсив и жирный переключаются, ударение, «ё»; машинка; окошки; пауза пароля."""
import time
import unittest

from stungkir.core import config as C
from stungkir.core import storage as S
from stungkir.core import textutil as T
from stungkir.tests.helpers import Sandbox, WindowCase, app, crypto_available, wait


class MarkupToggleTest(unittest.TestCase):
    def check(self, line, start, end, mark, expected):
        self.assertEqual(T.toggle_markup(line, start, end, mark), expected, (line, start, end, mark))

    def test_selection_wraps_and_unwraps(self):
        self.check("слово", 0, 5, "*", ("*слово*", 1, 6))
        self.check("*слово*", 1, 6, "*", ("слово", 0, 5))
        self.check("*слово*", 0, 7, "*", ("слово", 0, 5))            # выделили вместе со звёздочками
        self.check("**слово**", 2, 7, "**", ("слово", 0, 5))
        self.check("**слово**", 2, 7, "*", ("***слово***", 3, 8))      # курсив поверх жирного
        self.check("***слово***", 3, 8, "*", ("**слово**", 2, 7))
        self.check(" слово ", 0, 7, "**", (" **слово** ", 3, 8))       # пробелы по краям не берём

    def test_pressing_again_does_not_pile_up(self):
        line, a, b = "слово", 0, 5
        for _ in range(5):
            line, a, b = T.toggle_markup(line, a, b, "**")
        self.assertEqual(line, "**слово**")

    def test_without_selection(self):
        self.check("а  б", 2, 2, "*", ("а ** б", 3, 3))                # начать курсив
        self.check("а ** б", 3, 3, "*", ("а  б", 2, 2))                # передумал
        self.check("*текст*", 6, 6, "*", ("*текст*", 7, 7))            # закончить курсив
        self.check("**текст**", 7, 7, "**", ("**текст**", 9, 9))
        self.check("одно слово", 6, 6, "*", ("одно *слово*", 7, 7))    # внутри слова - слово
        self.check("одно *слово*", 8, 8, "*", ("одно слово", 7, 7))
        self.check("[]", 1, 1, "[]", ("", 0, 0))
        self.check("[пометка]", 8, 8, "[]", ("[пометка]", 9, 9))

    def test_stress(self):
        self.assertEqual(T.toggle_stress("вода", 2), ("во́да", 3))
        self.assertEqual(T.toggle_stress("во́да", 3), ("вода", 2))       # ещё раз - убрал
        self.assertEqual(T.toggle_stress("во́да", 5), ("вода́", 5))  # одно ударение на слово
        self.assertIsNone(T.toggle_stress("вод", 3))                           # после согласной - нет
        self.assertIsNone(T.toggle_stress("", 0))

    def test_yo(self):
        self.assertEqual(T.smart_yo("Он ушёл. ", 9, 9), "Ё")
        self.assertEqual(T.smart_yo("— ", 2, 2), "Ё")
        self.assertEqual(T.smart_yo("", 0, 0), "Ё")
        self.assertEqual(T.smart_yo("он ", 3, 3), "ё")
        self.assertEqual(T.smart_yo("все", 2, 3), "ё")                         # выделенную «е» - в «ё»


class EditorButtonsTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.w = self.window()
        self.w.editor.setPlainText("Первое слово тут.\nВторая строка.")

    def select(self, start, end):
        cursor = self.w.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
        self.w.editor.setTextCursor(cursor)

    def test_italic_button_toggles_and_undo_is_one_step(self):
        self.select(7, 12)
        self.w.insert_symbol("*|*")
        self.assertEqual(self.w.editor.toPlainText().split("\n")[0], "Первое *слово* тут.")
        self.assertEqual(self.w.editor.textCursor().selectedText(), "слово")
        self.w.insert_symbol("*|*")
        self.assertEqual(self.w.editor.toPlainText().split("\n")[0], "Первое слово тут.")
        self.w.insert_symbol("*|*")
        self.w.editor.undo()
        self.assertEqual(self.w.editor.toPlainText().split("\n")[0], "Первое слово тут.")

    def test_bold_over_two_lines(self):
        self.select(0, len(self.w.editor.toPlainText()))
        self.w.insert_symbol("**|**")
        self.assertEqual(self.w.editor.toPlainText(), "**Первое слово тут.**\n**Вторая строка.**")
        self.select(0, len(self.w.editor.toPlainText()))
        self.w.insert_symbol("**|**")
        self.assertEqual(self.w.editor.toPlainText(), "Первое слово тут.\nВторая строка.")

    def test_stress_and_yo_buttons(self):
        self.select(2, 2)                                     # после «е» в «Первое»
        self.w.insert_symbol(T.STRESS)
        self.assertTrue(self.w.editor.toPlainText().startswith("Пе́рвое"))
        self.w.insert_symbol(T.STRESS)
        self.assertTrue(self.w.editor.toPlainText().startswith("Первое"))
        self.select(1, 1)                                     # после «П» - согласная
        self.w.insert_symbol(T.STRESS)
        self.assertTrue(self.w.editor.toPlainText().startswith("Первое"))
        self.select(0, 0)
        self.w.insert_symbol("ё")
        self.assertTrue(self.w.editor.toPlainText().startswith("ЁПервое"))

    def test_symbol_panel_has_no_apostrophe_and_one_yo(self):
        labels = [label for label, _value, _tip in C.SYMBOLS]
        self.assertNotIn("’", labels)
        self.assertNotIn("Ё", labels)
        self.assertEqual(len(labels) % 4, 0)                  # ровная сетка по 4


class TypewriterTest(WindowCase):
    def test_short_text_line_goes_to_middle(self):
        w = self.window()
        w.editor.setPlainText("Короткая строка.")
        w.editor.setFocus()
        before = w.editor.viewport().mapTo(w.editor, w.editor.cursorRect().center()).y()
        w.set_typewriter(True)
        wait(0.5)
        after = w.editor.viewport().mapTo(w.editor, w.editor.cursorRect().center()).y()
        self.assertGreater(after - before, 100)               # строка заметно опустилась
        self.assertAlmostEqual(after, w.editor.height() * C.TYPEWRITER_POS, delta=12)
        self.assertFalse(w.is_modified())                     # отступ - не правка текста
        w.set_typewriter(False)
        wait(0.5)
        self.assertEqual(w.editor.viewportMargins().top(), 0)


class FlatWindowsTest(WindowCase):
    def test_flat_sheet_has_no_transparent_border(self):
        from stungkir.ui.dialogs import Sheet
        self.addCleanup(setattr, C, "FLAT_WINDOWS", C.FLAT_WINDOWS)
        C.FLAT_WINDOWS = True
        sheet = Sheet(None, "Проба")
        self.assertTrue(sheet.flat)
        from PySide6.QtCore import Qt
        self.assertFalse(sheet.testAttribute(Qt.WA_TranslucentBackground))
        self.assertEqual(sheet.layout().contentsMargins().left(), 0)
        C.FLAT_WINDOWS = False
        self.assertFalse(Sheet(None, "Проба").flat)           # в тестах (offscreen) прозрачность есть


@unittest.skipUnless(crypto_available(), "нет библиотеки cryptography")
class PasswordBackoffTest(Sandbox):
    def setUp(self):
        super().setUp()
        app()
        from PySide6.QtCore import QSettings
        settings = QSettings(C.APP_ID, C.APP_ID)
        settings.remove("password_failures")
        settings.remove("password_wait_until")
        self.addCleanup(settings.remove, "password_failures")
        self.addCleanup(settings.remove, "password_wait_until")
        from stungkir.tests.test_password import write_lock
        write_lock("секрет")

    def test_delay_grows(self):
        from stungkir.ui.dialogs import password_delay
        self.assertEqual([password_delay(n) for n in range(1, 10)], [0, 0, 2, 4, 8, 16, 32, 60, 60])

    def test_wrong_passwords_slow_down_and_survive_restart(self):
        from stungkir.ui.dialogs import PasswordDialog
        dialog = PasswordDialog(None, "Вход", "Пароль", check=S.unlock)
        for _ in range(3):
            dialog.first.setText("не тот")
            dialog.accept()
        self.assertFalse(dialog.ok_button.isEnabled())
        self.assertIn("через", dialog.error.text())
        dialog.first.setText("секрет")                        # даже верный пароль - только после паузы
        dialog.accept()
        self.assertIsNone(dialog.password)
        again = PasswordDialog(None, "Вход", "Пароль", check=S.unlock)   # закрыл и открыл снова
        self.assertFalse(again.ok_button.isEnabled())
        time.sleep(2.1)
        again._countdown()
        self.assertTrue(again.ok_button.isEnabled())
        again.first.setText("секрет")
        again.accept()
        self.assertEqual(again.password, "секрет")
        self.assertEqual(PasswordDialog._state()[1], 0)       # после верного счёт сброшен


class PasteAndDayCountTest(WindowCase):
    def test_paste_is_cleaned_and_not_counted_as_written(self):
        from PySide6.QtCore import QMimeData
        w = self.window()
        path = self.chapter("Книга", "Глава", "Было.")
        w.open_path(path)
        w.editor.moveCursor(w.editor.textCursor().MoveOperation.End)
        data = QMimeData()
        data.setText(" Раз два.   Три четыре  пять.   ")
        w.editor.insertFromMimeData(data)
        self.assertEqual(w.editor.toPlainText(), "Было. Раз два.\nТри четыре пять.")
        w.count_words()
        self.assertEqual(w.pasted_today, 5)
        self.assertEqual(w.today_words(), 0)              # вставленное - не «написано»
        w.editor.insertPlainText(" Сам написал")
        w.count_words()
        self.assertEqual(w.today_words(), 2)

    def test_day_never_goes_below_zero(self):
        w = self.window()
        path = self.chapter("Книга", "Глава", "Раз два три четыре пять.")
        w.open_path(path)
        w.editor.selectAll()
        w.editor.textCursor().removeSelectedText()
        w.count_words()
        self.assertEqual(w.today_words(), -5)
        self.assertIn("за день 0", w.status_plain)
        self.assertIn("сокращено на 5", w.status_plain)
        self.assertNotIn("-5", w.status_plain)

    def test_opening_a_chapter_is_not_writing(self):
        """Открыл главу - это не «написал её за сегодня»: серия не растёт и огонёк не выскакивает."""
        w = self.window()
        path = self.chapter("Книга", "Глава", "слово " * 300)
        seen = []
        w.streak_pop.play = lambda *a: seen.append(a)
        w.update_status()
        w.open_path(path)
        self.assertEqual(w.today_words(), 0)
        self.assertEqual(seen, [])

    def test_midnight_starts_a_new_day(self):
        from datetime import date, timedelta
        from stungkir.ui import progress
        w = self.window()
        path = self.chapter("Книга", "Глава", "Начало.")
        w.open_path(path)
        w.editor.moveCursor(w.editor.textCursor().MoveOperation.End)
        w.editor.insertPlainText(" Ещё три слова")
        w.count_words()
        self.assertEqual(w.today_words(), 3)
        old_day = w.today

        class Tomorrow(date):
            @classmethod
            def today(cls):
                return date.fromisoformat(old_day) + timedelta(days=1)
        self.addCleanup(setattr, progress, "date", progress.date)
        progress.date = Tomorrow
        self.assertTrue(w.check_new_day())
        self.assertEqual(w.stats[old_day], 3)                  # вчерашнее осталось вчера
        self.assertEqual(w.today_words(), 0)
        w.editor.insertPlainText(" и дальше")
        w.count_words()
        self.assertEqual(w.today_words(), 2)


class SwitchSavesQuietlyTest(WindowCase):
    def test_switching_and_closing_save_without_asking(self):
        asked = []
        self.patch("ask_question", lambda *a, **k: asked.append(a) or self.answer)
        w = self.window()
        one = self.chapter("Книга", "Первая", "Раз.")
        two = self.chapter("Книга", "Вторая", "Два.")
        w.open_path(one)
        w.editor.moveCursor(w.editor.textCursor().MoveOperation.End)
        w.editor.insertPlainText(" Дописал")
        self.assertTrue(w.open_path(two))                # сразу, до автосохранения
        self.assertEqual(asked, [])
        self.assertEqual(one.read_text(encoding="utf-8"), "Раз. Дописал")
        w.editor.insertPlainText("Новое. ")
        w.close()
        self.assertEqual(asked, [])
        self.assertEqual(two.read_text(encoding="utf-8"), "Новое. Два.")


class PhoneWordsTest(WindowCase):
    def test_phone_words_count_for_today_but_are_not_rewritten(self):
        import json
        from stungkir.core import storage as S2
        w = self.window()
        phone = C.ROOT / C.SERVICE_DIR / "stats-phone.json"
        phone.parent.mkdir(parents=True, exist_ok=True)
        phone.write_text(json.dumps({w.today: 200}), encoding="utf-8", newline="\n")
        w.stats = S2.load_stats()
        w._elsewhere = None
        path = self.chapter("Книга", "Глава", "Начало.")
        w.open_path(path)
        w.editor.moveCursor(w.editor.textCursor().MoveOperation.End)
        w.editor.insertPlainText(" ещё " * 60)
        w.count_words()
        self.assertEqual(w.today_words(), 60)                    # своё - только своё
        w.store_stats()
        self.assertEqual(S2.load_stats(own_only=True)[w.today], 60)
        self.assertEqual(w.stats[w.today], 260)                    # а вместе - с телефоном
        self.assertEqual(json.loads(phone.read_text(encoding="utf-8"))[w.today], 200)   # файл телефона не тронут
        self.assertGreaterEqual(w.current_streak(), 1)             # 260 >= 250: день засчитан
