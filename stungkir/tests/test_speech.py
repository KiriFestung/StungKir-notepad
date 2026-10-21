# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Чтение вслух: что отдаётся голосу, очередь с места курсора, подсветка, остановка."""
import time
import unittest

from stungkir import speech as SP
from stungkir.tests.helpers import WindowCase, wait


class SpeakableTest(unittest.TestCase):
    def test_cleanup(self):
        self.assertEqual(SP.speakable("— Лодки *не* будет, — сказала она [проверить]."),
                         "Лодки не будет, сказала она.")
        self.assertEqual(SP.speakable("**Жирно** и  просто"), "Жирно и просто")


class ReadingTest(WindowCase):
    def setUp(self):
        super().setUp()
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
        except ImportError:
            self.skipTest("нет модуля QtTextToSpeech")
        if "mock" not in QTextToSpeech.availableEngines():
            self.skipTest("нет тестового голоса")
        self.w = self.window()
        self.w.SPEECH_ENGINE = "mock"
        self.w.editor.setPlainText("Первое. Второе предложение.\nТретье!")

    def test_reads_from_cursor_and_highlights(self):
        cursor = self.w.editor.textCursor()
        cursor.setPosition(8)                                        # перед «Второе»
        self.w.editor.setTextCursor(cursor)
        spoken = []
        real = self.w._highlight_sentence

        def remember(sentence):
            real(sentence)
            selections = self.w.editor.extraSelections()
            spoken.append(selections[0].cursor.selectedText() if selections else "")
        self.w._highlight_sentence = remember
        self.w.start_reading()
        end = time.time() + 5
        while self.w._reading is not None and time.time() < end:
            wait(0.05)
        self.assertIsNone(self.w._reading)                           # дочитал до конца
        self.assertEqual(spoken, ["Второе предложение.", "Третье!"])
        self.assertEqual(self.w.editor.extraSelections(), [])
        self.assertEqual(self.w.editor.textCursor().position(), 8)   # курсор пишущего остался на месте

    def test_can_write_while_reading(self):
        """Голос читает, а ты правишь: набранное остаётся там, где курсор, а голос читает уже новый текст."""
        self.w.editor.moveCursor(self.w.editor.textCursor().MoveOperation.Start)
        said = []
        self.w.start_reading()
        tts = self.w._tts
        real_say = tts.say
        tts.say = lambda text: (said.append(text), real_say(text))
        cursor = self.w.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.w.editor.setTextCursor(cursor)
        self.w.editor.insertPlainText(" Дописал")
        cursor = self.w.editor.document().find("Третье")
        cursor.insertText("Четвёртое")                      # правка в ещё не прочитанном предложении
        end = time.time() + 5
        while self.w._reading is not None and time.time() < end:
            wait(0.05)
        self.assertTrue(self.w.editor.toPlainText().endswith("Четвёртое! Дописал"))
        self.assertIn("Четвёртое!", said)

    def test_stop(self):
        self.w.editor.moveCursor(self.w.editor.textCursor().MoveOperation.Start)
        self.w.toggle_reading()
        self.assertTrue(self.w._reading is not None)
        self.w.toggle_reading()
        self.assertIsNone(self.w._reading)
        self.assertEqual(self.w.editor.extraSelections(), [])

    def test_no_voice_explains(self):
        self.w.SPEECH_ENGINE = None
        self.w._tts = None
        self.w._speech = lambda: None
        self.w.start_reading()
        self.assertIn("русского голоса", self.messages[-1][1])

    def test_choose_voice(self):
        from stungkir.windows import SettingsDialog
        dialog = SettingsDialog(self.w, {}, 500)
        self.assertGreaterEqual(dialog.voice.count(), 1)
        if dialog.voice.count() > 1:
            dialog.voice.setCurrentIndex(1)
            name = dialog.voice.currentData()
            dialog.values()
            self.assertEqual(self.w.settings.value("speech_voice"), name)
            self.w.editor.moveCursor(self.w.editor.textCursor().MoveOperation.Start)
            self.w.start_reading()
            self.assertEqual(self.w._tts.voice().name(), name)
            self.w.stop_reading()
