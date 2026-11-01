# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Язык интерфейса: перевод с запасом на русский, выбор при первом запуске, переключатель в «Настройках»."""
import json
import re

from PySide6.QtCore import QSettings

from stungkir.core import config as C
from stungkir.core import i18n
from stungkir.core.lang_en import EN
from stungkir.tests.helpers import Sandbox, WindowCase, app


class TranslateTest(Sandbox):
    def setUp(self):
        super().setUp()
        self.addCleanup(i18n.set_language, i18n.LANG)

    def test_russian_is_the_source_and_the_fallback(self):
        i18n.set_language("ru")
        self.assertEqual(i18n.tr("Язык"), "Язык")
        i18n.set_language("en")
        self.assertEqual(i18n.tr("Язык"), "Language")
        self.assertEqual(i18n.tr("Такой надписи в словаре нет"), "Такой надписи в словаре нет")
        self.assertEqual(i18n.tr("Язык", "ru"), "Язык")             # явный язык важнее текущего
        i18n.set_language("en-GB")
        self.assertEqual(i18n.tr("Цвет"), "Colour")                       # британское написание
        self.assertEqual(i18n.tr("Цвет", "en"), "Color")
        self.assertEqual(i18n.british("Pick a color, neighbors"), "Pick a colour, neighbours")
        self.assertEqual(i18n.tr("Такой надписи в словаре нет"), "Такой надписи в словаре нет")
        i18n.set_language("klingon")
        self.assertEqual(i18n.LANG, "ru")

    def test_dictionary_is_clean(self):
        for source, english in EN.items():
            self.assertTrue(english.strip(), source)
            # без русских букв - кроме примеров русского текста в «…» и [ … ]
            self.assertNotRegex(re.sub(r"«[^»]*»|\[[^\]]*\]", "", english), "[а-яё]", source)
            self.assertEqual(sorted(re.findall(r"\{[^{}]*\}", source)), sorted(re.findall(r"\{[^{}]*\}", english)),
                             source)                                          # подстановки те же


class FirstRunTest(Sandbox):
    def setUp(self):
        super().setUp()
        app()
        self.settings = QSettings(C.APP_ID, C.APP_ID)
        self.settings.clear()
        self.addCleanup(self.settings.clear)
        self.addCleanup(i18n.set_language, i18n.LANG)
        self.asked = []

    def ask(self, answer):
        def fake():
            self.asked.append(answer)
            return answer
        return fake

    def saved(self):
        return json.loads(self.settings.value("config", "") or "{}").get("LANGUAGE")

    def test_fresh_start_asks_once(self):
        from stungkir.app import choose_language_once
        self.assertEqual(choose_language_once(self.ask("en")), "en")
        self.assertEqual((self.asked, self.saved(), i18n.LANG), (["en"], "en", "en"))
        self.assertEqual(choose_language_once(self.ask("ru")), "en")       # второй раз не спрашивает
        self.assertEqual(self.asked, ["en"])

    def test_closed_window_means_russian(self):
        from stungkir.app import choose_language_once
        self.assertEqual(choose_language_once(self.ask(None)), "ru")
        self.assertEqual(self.saved(), "ru")

    def test_someone_already_writing_is_not_asked(self):
        from stungkir.app import choose_language_once
        self.chapter("Книга", "Глава 1", "Текст")
        self.assertEqual(choose_language_once(self.ask("en")), "ru")
        self.assertEqual((self.asked, self.saved()), ([], "ru"))

    def test_windows_installer_already_asked(self):
        from stungkir.app import choose_language_once
        self.settings.setValue("installer_language", "en")
        self.assertEqual(choose_language_once(self.ask("ru")), "en")
        self.assertEqual((self.asked, self.saved()), ([], "en"))

    def test_settings_keep_the_rest_of_the_config(self):
        from stungkir.app import choose_language_once
        self.settings.setValue("config", json.dumps({"FONT_SIZE": 19}))
        choose_language_once(self.ask("en"))
        self.assertEqual(json.loads(self.settings.value("config")), {"FONT_SIZE": 19, "LANGUAGE": "en"})

    def test_language_window(self):
        from stungkir.ui.dialogs import LanguageDialog
        dialog = LanguageDialog()
        self.assertEqual(dialog.code, "ru")
        dialog.buttons["en"].click()
        self.assertEqual(dialog.code, "en")


class SettingsLanguageTest(WindowCase):
    def test_switch_waits_for_restart(self):
        from stungkir.ui import windows
        self.addCleanup(i18n.set_language, i18n.LANG)
        w = self.window()

        def choose_english(dialog):
            dialog.language.setCurrentIndex(dialog.language.findData("en"))
            return 1
        original = windows.SettingsDialog.exec
        self.addCleanup(setattr, windows.SettingsDialog, "exec", original)
        windows.SettingsDialog.exec = choose_english
        w.show_settings()
        self.assertEqual(json.loads(QSettings(C.APP_ID, C.APP_ID).value("config"))["LANGUAGE"], "en")
        self.assertEqual(i18n.LANG, "ru")                                  # на ходу не меняется
        self.assertEqual(w.toast.text(), "The language will change after a restart")
