# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Чтение вслух (F5): с места курсора, по предложению, читаемое подсвечено.
На слух ловятся корявые фразы, повторы и пропущенные слова, которых глаз уже не видит."""

import re
import sys

from PySide6.QtCore import QLocale
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from ..core import config as C
from .rhythm import sentences
from ..core.textutil import MARKER_RE, plain_markup, position_map
from ..core.i18n import tr

RATES = {"Медленно": -0.3, "Обычно": 0.0, "Быстрее": 0.25, "Быстро": 0.5}


def speakable(sentence):
    """Что отдать голосу: без *разметки* и [пометок], тире реплики - паузой."""
    text = MARKER_RE.sub("", plain_markup(sentence))
    text = re.sub(r"^\s*[—–-]\s*", "", text)
    text = re.sub(r",?\s[—–-]\s", ", ", text)
    text = re.sub(r"\s+([.,!?…;:])", r"\1", " ".join(text.split()))
    return text


def missing_voice_hint():
    if sys.platform.startswith("win"):
        return ("Нет русского голоса. В Windows: Параметры → Время и язык → Речь → Добавить голоса → "
                "Русский, потом перезапусти StungKir.")
    return ("Нет русского голоса. Поставь его так: sudo apt install speech-dispatcher "
            "speech-dispatcher-rhvoice rhvoice rhvoice-russian - и перезапусти StungKir.")


class SpeechMixin:
    """Чтение вслух. Часть главного окна."""

    SPEECH_ENGINE = None          # в тестах - "mock"

    def _speech(self):
        if getattr(self, "_tts", None) is not None:
            return self._tts
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
        except ImportError:
            return None
        engine = self.SPEECH_ENGINE
        tts = QTextToSpeech(engine, self) if engine else QTextToSpeech(self)
        if tts.state() == QTextToSpeech.State.Error:
            return None
        russian = [loc for loc in tts.availableLocales() if loc.language() == QLocale.Russian]
        if russian:
            tts.setLocale(russian[0])
        elif engine is None:
            return None                         # голос есть, но не русский - читать им нельзя
        tts.stateChanged.connect(self._speech_state)
        self._tts = tts
        return tts

    def toggle_reading(self):
        if getattr(self, "_reading", None):
            self.stop_reading()
        else:
            self.start_reading()

    def start_reading(self):
        if self.view is not None:
            self.toast.show_message(tr("Вслух читается глава, а не таблица, доска или хронология"))
            return
        tts = self._speech()
        if tts is None:
            from ..ui.dialogs import show_warning
            show_warning(self, tr("Чтение вслух"), missing_voice_hint())
            return
        tts.setRate(RATES.get(self.settings.value("speech_rate", "Обычно"), 0.0))
        wanted = self.settings.value("speech_voice", "") or ""
        if wanted:                                          # свой голос из настроек, если он ещё стоит
            for voice in tts.availableVoices():
                if voice.name() == wanted:
                    tts.setVoice(voice)
                    break
        cursor = self.editor.textCursor()
        line, column = cursor.blockNumber(), cursor.positionInBlock()
        queue = [s for s in sentences(self.editor.toPlainText()) if (s[0], s[2]) > (line, column)]
        queue = [self._sentence_cursor(s) for s in queue if speakable(s[4])]
        queue = [c for c in queue if c is not None]
        if not queue:
            self.toast.show_message(tr("Дальше курсора читать нечего: поставь курсор выше"))
            return
        self._reading = queue
        self._typed_at = 0.0
        self.toast.show_message(tr("Читаю вслух - можно править дальше. F5 - остановить"), 2600)
        self._speak_next()

    def _sentence_cursor(self, sentence):
        """Предложение - [начало, конец] в документе. Когда текст выше или внутри правят, границы
        сдвигаются следом (_shift_reading), поэтому читать можно и одновременно писать (вычитка на слух)."""
        number, start, end = sentence[0], sentence[1], sentence[2]
        block = self.editor.document().findBlockByNumber(number)
        if not block.isValid():
            return None
        to_qt = position_map(block.text())
        return [block.position() + to_qt(start), block.position() + to_qt(min(end, len(block.text())))]

    def _shift_reading(self, pos, removed, added):
        delta = added - removed
        for span in (getattr(self, "_reading", None) or []) + ([self._current_span] if getattr(
                self, "_current_span", None) else []):
            s, e = span
            span[0] = s if pos >= s else (s + delta if pos + removed <= s else pos)
            span[1] = e if pos >= e else (e + delta if pos + removed <= e else pos + added)

    def _selection(self, span):
        cursor = QTextCursor(self.editor.document())
        size = self.editor.document().characterCount() - 1
        cursor.setPosition(max(0, min(span[0], size)))
        cursor.setPosition(max(0, min(span[1], size)), QTextCursor.KeepAnchor)
        return cursor

    def _speak_next(self):
        if not getattr(self, "_watching_edits", False):
            self.editor.document().contentsChange.connect(self._shift_reading)
            self._watching_edits = True
        while getattr(self, "_reading", None):
            span = self._reading.pop(0)
            sentence = self._selection(span)
            text = speakable(sentence.selectedText().replace("\u2029", " "))
            if text:                                  # предложение стёрли, пока читалось прежнее - дальше
                self._current_span = span
                self._current_sentence = sentence
                self._highlight_sentence(sentence)
                self._tts.say(text)
                return
        self.stop_reading()

    def _speech_state(self, state):
        from PySide6.QtTextToSpeech import QTextToSpeech
        if state == QTextToSpeech.State.Ready and getattr(self, "_current_sentence", None) is not None:
            self._current_sentence = None
            if getattr(self, "_reading", None):
                self._speak_next()
            else:
                self.stop_reading()
        elif state == QTextToSpeech.State.Error:
            self.toast.show_message(tr("Голос перестал читать: ") + self._tts.errorString(), 3500)
            self.stop_reading()

    def stop_reading(self):
        self._reading = None
        self._current_sentence = None
        self._current_span = None
        if getattr(self, "_tts", None) is not None:
            self._tts.stop()
        self.editor.setExtraSelections([])

    def note_typing_for_speech(self):
        """Пока пишешь, голос не дёргает прокрутку."""
        import time
        self._typed_at = time.monotonic()

    def _highlight_sentence(self, cursor):
        """Подсветить читаемое. Курсор того, кто пишет, НЕ трогается (раньше голос переставлял его
        на читаемое предложение - и всё, что набиралось, улетало туда, а стрелки «не слушались»).
        Глава сама прокручивается за голосом, только если ты сейчас не печатаешь."""
        import time
        selection = QTextEdit.ExtraSelection()
        selection.cursor = QTextCursor(cursor)
        selection.format = QTextCharFormat()
        selection.format.setBackground(QColor(C.FOUND))
        self.editor.setExtraSelections([selection])
        if time.monotonic() - getattr(self, "_typed_at", 0.0) < 4.0:
            return
        spot = QTextCursor(cursor)
        spot.clearSelection()
        rect = self.editor.cursorRect(spot)
        view = self.editor.viewport().rect()
        if rect.top() < view.top() + 20 or rect.bottom() > view.bottom() - 20:
            bar = self.editor.verticalScrollBar()
            bar.setValue(bar.value() + rect.center().y() - view.height() // 3)
