# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Снимки окон: python -m stungkir --screens <папка>. На GitHub это запускается на настоящем Windows -
видно, как блокнот выглядит там, без компьютера с Windows. Всё во временной папке, у пользователя
ничего не трогается. Окошко не открылось - в report.txt записано почему, остальные снимки всё равно делаются."""

import sys
import traceback
import unittest
from pathlib import Path

from stungkir.core import config as C
from stungkir.tests.helpers import WindowCase, wait

OUT = Path("screens")
REPORT = []


class Screens(WindowCase):
    def shot(self, widget, name):
        widget.grab().save(str(OUT / f"{name}.png"))
        REPORT.append(f"ok   {name}")

    def step(self, name, action):
        try:
            action()
        except Exception:                    # одно окно не вышло - остальные снимки нужнее, чем остановка
            REPORT.append(f"FAIL {name}\n{traceback.format_exc()}")

    def test_screens(self):
        from stungkir.ui import dialogs
        from stungkir.books.sample import create_sample
        create_sample()
        from stungkir.app import load_bundled_fonts
        load_bundled_fonts()                     # шрифты программы - как у человека, а не только системные
        from datetime import date, timedelta
        from stungkir.core.storage import save_stats
        today = date.today()                     # пробная статистика за год - на диск: окно читает её оттуда
        save_stats({(today - timedelta(days=n)).isoformat(): (n * 37) % 1400 for n in range(0, 365, 2)})
        w = self.window()
        w.resize(1280, 800)
        w.choose_theme(C.DEFAULT_THEME)          # основная тема, как у человека (в проверках - своя)
        w.open_path(next(C.ROOT.rglob("Глава 1.txt")))          # первая глава пробной книги
        wait(0.5)
        number = iter(range(1, 100))

        def name(text):
            return f"{next(number):02d}-{text}"

        self.step("главное окно", lambda: self.shot(w, name("главное-окно")))

        def panels():
            w.left.set_open(True)
            wait(0.6)
            self.shot(w, name("левая-панель"))
            w.left.set_open(False)
            wait(0.4)
        self.step("левая панель", panels)

        def lines():
            w.toggle_line_numbers()
            wait(0.3)
            self.shot(w, name("номера-строк"))
            w.toggle_line_numbers()
        self.step("номера строк", lines)

        # окошки: вместо ожидания ответа - показать, снять и закрыть
        original = dialogs.Sheet.exec

        def snap(label):
            def fake(dialog):
                dialog.show()
                wait(0.8)
                self.shot(dialog, name(label))
                dialog.reject()
                return 0
            return fake
        self.addCleanup(setattr, dialogs.Sheet, "exec", original)
        for label, method in (("план-книги", "show_plan"), ("кубики", "show_random"), ("антистресс", "show_antistress"),
                              ("как-увидит-читатель", "show_preview"), ("настройки", "show_settings"),
                              ("горячие-клавиши", "show_hotkeys"), ("статистика", "show_stats"),
                              ("кто-в-какой-главе", "show_presence")):
            dialogs.Sheet.exec = snap(label)
            self.step(label, getattr(w, method))

        def year(dialog):                        # статистика за год клеточками - на пробных днях
            dialog.show()
            dialog.resize(1000, 600)
            dialog.period.button(1).click()
            wait(0.8)
            self.shot(dialog, name("статистика-год"))
            dialog.reject()
            return 0

        def stats_year():
            dialogs.Sheet.exec = year
            w.show_stats()
        self.step("статистика за год", stats_year)
        dialogs.Sheet.exec = original

        def day():
            w.choose_theme(C.DAY_THEME)
            wait(0.6)
            self.shot(w, name("дневная-тема"))
        self.step("дневная тема", day)


def main(out):
    global OUT
    OUT = Path(out)
    OUT.mkdir(parents=True, exist_ok=True)
    result = unittest.TextTestRunner(stream=open(OUT / "unittest.txt", "w", encoding="utf-8")).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Screens))
    shots = sorted(p.name for p in OUT.glob("*.png"))
    REPORT.append(f"снимков: {len(shots)}; {sys.platform}; Qt: {__import__('PySide6').__version__}")
    (OUT / "report.txt").write_text("\n".join(REPORT) + "\n", encoding="utf-8", newline="\n")
    return 0 if result.wasSuccessful() and shots else 1
