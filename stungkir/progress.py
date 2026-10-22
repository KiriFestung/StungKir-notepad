# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: счёт слов, цели, статистика, таймер."""

import html
import json
from datetime import date, datetime
from PySide6.QtCore import QTimer

from . import config as C
from .textutil import plural, signed, words_label
from .storage import load_stats, save_goals, save_marks, save_stats, streaks
from .dialogs import ask_int
from .windows import StatsDialog


class ProgressMixin:
    """Счёт слов, цели, статистика, таймер. Часть главного окна."""

    # ---------------- слова, цель, статистика ----------------
    def count_words(self):
        self.words = self.word_count()
        self.update_status()
        self.check_goal()

    def today_words(self):
        """Сколько за сегодня написано руками: всё, что прибавилось во всех главах, минус вставленное."""
        return (self.today_base + self.session_net + self.words - self.file_base_words
                - getattr(self, "pasted_today", 0))

    def note_pasted(self, words):
        """Вставили текст из буфера: эти слова не «написаны сегодня»."""
        if words > 0:
            self.pasted_today = getattr(self, "pasted_today", 0) + words

    def check_new_day(self):
        """Окно открыто за полночь: вчерашнее - во вчера, сегодня считается с нуля (раньше всё,
        написанное после полуночи, приписывалось вчерашнему дню)."""
        day = date.today().isoformat()
        if day == self.today:
            return False
        self.words = self.word_count()
        self.store_stats()
        self.today = day
        self.today_base = load_stats(own_only=True).get(day, 0)
        self.session_net = 0
        self.file_base_words = self.words
        self.pasted_today = 0
        return True

    def shown_number(self, name, value):
        """Цифры в строке внизу не прыгают, а быстро добегают до нового значения."""
        shown = self.__dict__.setdefault("_shown_numbers", {})
        current = shown.get(name)
        if current is None or not self.isVisible() or abs(value - current) > 5000:
            shown[name] = value
            return value
        if current != value:
            step = max(1, round(abs(value - current) * 0.35))
            current = current + step if value > current else current - step
            shown[name] = current
            timer = self.__dict__.get("_number_timer")
            if timer is None:
                timer = self._number_timer = QTimer(self, interval=30, singleShot=True)
                timer.timeout.connect(self.update_status)
            timer.start()
        return current

    def update_status(self):
        seconds = self.session.elapsed() // 1000
        h, rest = divmod(seconds, 3600)
        m, s = divmod(rest, 60)
        strip = self.goal_strip
        colored = strip.style_name != "calm"

        def number(text, name):
            """Цифра в цвет своей полоски: глава, день, серия видны с первого взгляда."""
            if not colored:
                return html.escape(text)
            color = C.rainbow()[{"chapter": 4, "day": 0, "streak": 1}[name]] \
                if strip.style_name == "rainbow" else (C.vivid(C.IMPORTANT) if name == "streak"
                                                       else strip.color(name))
            return f"<span style='color:{color.name()}'>{html.escape(text)}</span>"

        parts = []                             # (простой текст, текст с цветом)
        if self.timer_deadline is not None:
            left = max(0, (self.timer_deadline - self.session.elapsed()) // 1000)
            text = f"таймер {left // 60}:{left % 60:02}"
            parts.append((text, text))
        chapter = self.chapter_goal()
        words_now = self.shown_number("chapter", self.words)
        if chapter:
            tail = f" из {chapter} {plural(chapter, 'слова', 'слов', 'слов')}"
            parts.append((f"{self.words}{tail}", number(str(words_now), "chapter") + html.escape(tail)))
        else:
            label = words_label(self.words)
            count, _, rest = label.partition(" ")
            rest = words_label(words_now).partition(" ")[2]
            parts.append((label, number(str(words_now), "chapter") + " " + html.escape(rest)))
        today = self.today_words()
        tail = f" из {self.goal}" if self.goal else ""
        if today >= 0:
            day_now = self.shown_number("day", today)
            parts.append((f"за день {signed(today)}{tail}", "за день " + number(signed(day_now), "day") + tail))
        else:
            # стирать - тоже работа, но в минус день не уходит: сколько сократил, видно отдельно
            cut = f", сокращено на {-today}"
            parts.append((f"за день 0{tail}{cut}", "за день " + number("0", "day") + tail + cut))
        today = max(0, today)
        streak = self.current_streak()
        self._celebrate_streak(streak)
        if streak >= 2 and self.screen_shown("streak"):
            tail = f" {plural(streak, 'день', 'дня', 'дней')} подряд"
            parts.append((f"{streak}{tail}", number(str(streak), "streak") + tail))
        if self.screen_shown("session"):
            text = f"сессия {h}:{m:02}:{s:02}"
            parts.append((text, text))
        modes = self.active_modes()
        if modes:
            text = "◉ " + ", ".join(modes)
            parts.insert(0, (text, html.escape(text)))
        self.status_plain = "   ·   ".join(p for p, _ in parts)
        self.status.setText("&nbsp;&nbsp;&nbsp;·&nbsp;&nbsp;&nbsp;".join(r for _, r in parts))
        pasted = getattr(self, "pasted_today", 0)
        self.status.setToolTip("Первое число - слов в открытой главе. «За день» - сколько написано сегодня "
                               "во всех главах вместе, поэтому при переходе в другую главу не обнуляется. "
                               "Вставленное из буфера в «за день» не идёт"
                               + (f" (сегодня вставлено {words_label(pasted)})." if pasted else "."))
        self.goal_strip.set("day", today / self.goal if self.goal else 0,
                            bool(self.goal) and today >= self.goal, bool(self.goal))
        self.goal_strip.set("chapter", self.words / chapter if chapter else 0,
                            bool(chapter) and self.words >= chapter, bool(chapter))
        if hasattr(self, "deadlines"):
            self.update_book_strip()
        self.goal_strip.setVisible(self.goal_strip.any_shown() and not getattr(self, "zen", False)
                                   and self.screen_shown("goals"))

    def _celebrate_streak(self, streak):
        """Серия выросла прямо сейчас (не при запуске) - огонёк с числом над строкой внизу."""
        seen = getattr(self, "_streak_seen", None)
        self._streak_seen = streak
        if seen is None or streak <= seen or getattr(self, "zen", False) or not self.screen_shown("streak"):
            return
        label = "День засчитан!" if streak == 1 else f"{streak} {plural(streak, 'день', 'дня', 'дней')} подряд!"
        if hasattr(self, "streak_pop"):
            from .widgets import streak_line
            self.place_overlays()
            self.streak_pop.play(streak, label, streak_line(streak, self.settings.value("streak_voice", "cheer")))

    def check_goal(self):
        chapter = self.chapter_goal()
        if chapter and self.words >= chapter and self.file_base_words < chapter:
            key = self._position_key(self.path)
            if key not in self._chapter_toasted:
                self._chapter_toasted.add(key)
                self.fox_wheel.celebrate()
                self._goal_burst("chapter")
                self.toast.show_message(f"Цель главы выполнена: {words_label(self.words)}", 3000)
                return
        if not self.goal or self.today_words() < self.goal:
            return
        if self.settings.value("goal_done") != self.today:
            self.settings.setValue("goal_done", self.today)
            self.fox_wheel.celebrate()
            self._goal_burst("day")
            self.toast.show_message(f"Цель на сегодня выполнена: {words_label(self.today_words())}", 3000)

    def _goal_burst(self, kind):
        """Звёздочки и конфетти над строкой (если окно их умеет и кадры на месте)."""
        pop = getattr(self, "goal_pop", None)
        if pop is not None:
            self.place_overlays()
            pop.play(kind)

    def chapter_goal(self):
        return self.chapter_goals.get(self._position_key(self.path), 0) if self.path else 0

    def set_chapter_goal(self, path=None):
        path = path or self.path
        if path is None:
            self.toast.show_message("Сначала открой главу")
            return
        key = self._position_key(path)
        value, ok = ask_int(
            self, "Цель главы", f"Сколько слов должно быть в «{path.stem}» (0 - без цели):",
            self.chapter_goals.get(key, C.CHAPTER_GOAL), 0, 1_000_000, 100)
        if not ok:
            return
        if value:
            self.chapter_goals[key] = value
        else:
            self.chapter_goals.pop(key, None)
        save_goals(self.chapter_goals)
        self.update_status()

    def _move_keys(self, old, new):
        """После переименования или переноса цели и позиции едут вместе с файлом."""
        old_key, new_key = self._position_key(old), self._position_key(new)
        for store in (self.chapter_goals, self.positions):
            for key in list(store):
                if key == old_key or key.startswith(old_key + "/"):
                    store[new_key + key[len(old_key):]] = store.pop(key)
        save_goals(self.chapter_goals)
        self.settings.setValue("positions", json.dumps(self.positions, ensure_ascii=False))

    def store_stats(self):
        own = load_stats(own_only=True)
        own[self.today] = max(0, self.today_words())
        save_stats(own)
        self.stats = load_stats()                      # и с тем, что написано на телефоне
        self._elsewhere = None

    def set_streak_voice(self, voice):
        self.settings.setValue("streak_voice", voice)
        from .widgets import STREAK_VOICES, streak_line
        line = streak_line(3, voice)
        self.toast.show_message(f"Огонёк серии: {STREAK_VOICES[voice].lower()}" + (f" - «{line}»" if line else ""))

    def set_goal(self):
        value, ok = ask_int(self, "Цель на день", "Сколько слов в день (0 - без цели):",
                                        self.goal, 0, 100000, 50)
        if ok:
            self.goal = value
            self.settings.setValue("daily_goal", value)
            self.update_status()

    def show_stats(self):
        self.count_words()
        self.store_stats()
        StatsDialog(self, self.stats, self.goal, self.day_marks, self.set_day_marks,
                    extra=self.deadline_lines()).exec()

    def set_day_marks(self, marks):
        self.day_marks = marks
        save_marks(marks)
        self.update_status()

    def current_streak(self):
        """Серия с учётом сегодняшних слов, ещё не записанных в статистику."""
        stats = dict(self.stats)
        elsewhere = getattr(self, "_elsewhere", None)
        if elsewhere is None or elsewhere[0] != self.today:   # сколько сегодня написано на других устройствах
            own = load_stats(own_only=True).get(self.today, 0)
            elsewhere = self._elsewhere = (self.today, max(0, self.stats.get(self.today, 0) - own))
        stats[self.today] = elsewhere[1] + max(0, self.today_words())
        return streaks(stats, self.day_marks, date.fromisoformat(self.today))[0]

    # ---------------- таймер ----------------
    def _timer_label(self, text):
        from .icons import decorate_button
        self.timer_button.setText(text)
        decorate_button(self.timer_button)       # ▶ или ■

    def toggle_timer(self):
        if self.timer_deadline is not None:
            self.timer_deadline = None
            self._timer_label("Старт")
            self.fox_wheel.set_running(False)
            self.fox_wheel.set_left(None)
            self.toast.show_message("Таймер остановлен")
            self.update_status()
            return
        self.count_words()
        minutes = self.timer_minutes.value()
        self.timer_deadline = self.session.elapsed() + minutes * 60_000
        self.timer_total = minutes * 60_000
        self.fox_wheel.set_left(1.0)
        self.timer_words_start = self.today_words()
        self.timer_warned = minutes <= 1
        self._timer_label("Стоп")
        self.fox_wheel.set_running(True)
        end = "потом сохраню и закрою" if self.timer_close.isChecked() else "потом скажу"
        self.toast.show_message(f"Таймер на {minutes} мин: {end}")
        self.update_status()
        self.editor.setFocus()

    # ---------------- перерыв для глаз ----------------
    EYE_TEXTS = ["{m} минут за текстом. Посмотри вдаль секунд двадцать - глазам нужен отдых",
                 "Моргни пару раз и посмотри в окно - глаза скажут спасибо",
                 "Пора встать: пройдись, потянись, попей воды. Текст подождёт"]

    def _eye_break_tick(self):
        """Считает время за текстом: идёт, пока окно активно и ты что-то пишешь; если отошёл
        минут на пять - отдых засчитан, счёт заново. Каждые N минут (настройки) - мягкое напоминание."""
        import time
        minutes = int(self.settings.value("eye_break", 20) or 0)
        if not minutes:
            return False
        idle = time.monotonic() - getattr(self, "_last_typed", 0.0)
        if self.isActiveWindow() and idle < 120:
            self._screen_time = getattr(self, "_screen_time", 0) + 1
        elif idle > 300:
            self._screen_time = 0
        if getattr(self, "_screen_time", 0) < minutes * 60:
            return False
        self._screen_time = 0
        self._breaks = getattr(self, "_breaks", 0) + 1
        text = self.EYE_TEXTS[2] if self._breaks % 3 == 0 else self.EYE_TEXTS[(self._breaks - 1) % 2]
        self.sounds.play("chime", 0.8)
        self.toast.show_message(text.format(m=minutes), 9000)
        if hasattr(self, "picture_pop"):                 # ласка смотрит вдаль
            self.picture_pop.play("eye-break", 9000)
        return True

    def _tick(self):
        if datetime.now().second == 0:
            self.update_night()
            self.check_new_day()
            self.stats = load_stats()                  # раз в минуту - что пришло с телефона
            self._elsewhere = None
        self._eye_break_tick()
        if self.timer_deadline is not None:
            left = self.timer_deadline - self.session.elapsed()
            if left <= 0:
                self.finish_timer()
                return
            self.fox_wheel.set_left(left / max(1, getattr(self, "timer_total", left)))
            if not self.timer_warned and left <= 60_000:
                self.timer_warned = True
                self.toast.show_message("Осталась минута", 2000)
        self.update_status()

    def finish_timer(self):
        self.count_words()
        written = self.today_words() - self.timer_words_start
        self.timer_deadline = None
        self._timer_label("Старт")
        self.fox_wheel.set_running(False)
        self.fox_wheel.set_left(None)
        self.update_status()
        saved = self.save_everything()
        self.store_stats()
        result = f"Время вышло. За это время {signed(written)} {plural(written, 'слово', 'слова', 'слов')}"
        if self.timer_close.isChecked() and saved:
            self.toast.show_message(result + ". Всё сохранено, закрываю…", 3000)
            QTimer.singleShot(3600, self, self.close)
        else:
            self.toast.show_message(result, 4000)
