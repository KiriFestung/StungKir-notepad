# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Внешний вид: новые темы, вложенные шрифты, фактура под текстом, «без отвлечений»."""
import unittest

from stungkir import config as C
from stungkir.tests.helpers import WindowCase, app, wait


class ThemesTest(unittest.TestCase):
    def test_new_themes_present(self):
        for name in ("Полночь", "Чернила", "Пергамент", "Графит", "Высокий контраст"):
            self.assertIn(name, C.THEMES)
        from PySide6.QtGui import QColor
        self.assertGreater(QColor(C.THEMES["Пергамент"]["BG"]).lightness(), 128)      # светлая
        self.assertLess(QColor(C.THEMES["Полночь"]["BG"]).lightness(), 40)           # тёмная


class FontsTest(unittest.TestCase):
    def test_bundled_fonts_have_cyrillic(self):
        app()
        from PySide6.QtGui import QFontDatabase
        from stungkir.app import load_bundled_fonts
        load_bundled_fonts()
        for family in ("Literata", "PT Serif"):
            self.assertIn(family, QFontDatabase.families())
            self.assertIn(QFontDatabase.WritingSystem.Cyrillic, QFontDatabase.writingSystems(family))
            self.assertTrue(QFontDatabase.isSmoothlyScalable(family, "Regular") or
                            QFontDatabase.isSmoothlyScalable(family))

    def test_windows_draws_letters_like_linux(self):
        """На Windows - движок FreeType (мягкие буквы, как на Linux); заданный вручную QT_QPA_PLATFORM не трогается."""
        import os
        from unittest import mock
        from stungkir.app import windows_font_engine
        with mock.patch("sys.platform", "win32"), mock.patch.dict(os.environ, clear=False):
            os.environ.pop("QT_QPA_PLATFORM", None)
            windows_font_engine()
            self.assertEqual(os.environ["QT_QPA_PLATFORM"], "windows:fontengine=freetype")
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            windows_font_engine()
            self.assertEqual(os.environ["QT_QPA_PLATFORM"], "offscreen")
        with mock.patch("sys.platform", "linux"), mock.patch.dict(os.environ, clear=False):
            os.environ.pop("QT_QPA_PLATFORM", None)
            windows_font_engine()
            self.assertNotIn("QT_QPA_PLATFORM", os.environ)


class LookWindowTest(WindowCase):
    def test_texture_applies_and_is_remembered(self):
        from PySide6.QtWidgets import QApplication
        w = self.window()
        self.addCleanup(setattr, C, "TEXTURE", "none")
        w.set_texture("linen")
        self.assertIn("texture-linen", QApplication.instance().styleSheet())
        self.assertEqual(w.settings.value("texture"), "linen")
        w.set_texture("none")
        self.assertNotIn("texture-", QApplication.instance().styleSheet())
        for kind in ("paper-book", "paper-rough", "paper-old"):          # настоящая бумага - плиткой
            w.set_texture(kind)
            self.assertIn(f"paper/{kind.split('-')[1]}-overlay.png", QApplication.instance().styleSheet())
        w.editor.grab()
        w.set_texture("none")

    def test_zen_hides_everything_but_text_and_comes_back(self):
        w = self.window()
        w.goal = 500
        w.update_status()
        w.set_zen(True)
        self.assertFalse(w.status.isVisible())
        self.assertFalse(w.goal_strip.isVisible())
        self.assertFalse(w.corner_clock.isVisible())
        self.assertFalse(w.left.hint.isVisible())
        w.update_status()                                     # обновление строки не возвращает её
        self.assertFalse(w.goal_strip.isVisible())
        w.check_hover()
        self.assertFalse(w.left.opened)
        w.set_zen(False)
        self.assertTrue(w.status.isVisible())
        self.assertTrue(w.corner_clock.isVisible())
        self.assertTrue(w.left.hint.isVisible())

    def test_more_menu_with_theme_list(self):
        w = self.window()
        menu = w.build_more_menu()
        titles = []

        def walk(m):
            for action in m.actions():
                titles.append(action.text())
                if action.menu():
                    walk(action.menu())
        walk(menu)
        self.assertIn("Полночь", titles)
        self.assertIn("Бумага книжная", titles)
        self.assertTrue(any(t.startswith("Без отвлечений") for t in titles))
        wait(0.01)


class IconsAndImportanceTest(WindowCase):
    def test_buttons_get_icons_by_text(self):
        from PySide6.QtWidgets import QPushButton, QWidget
        from stungkir.icons import decorate, icon_for_text
        self.assertEqual(icon_for_text("Сохранить"), "save")
        self.assertEqual(icon_for_text("Отмена"), "close")
        self.assertIsNone(icon_for_text("d20"))
        holder = QWidget()
        save, cancel, plain, skip = (QPushButton(t, holder) for t in ("Сохранить", "Отмена", "d20", "Удалить"))
        save.setDefault(True)
        skip.setProperty("noIcon", True)
        decorate(holder)
        self.assertEqual(save.property("autoIcon"), "save")
        self.assertFalse(save.icon().isNull())
        self.assertTrue(plain.icon().isNull())
        self.assertTrue(skip.icon().isNull())
        self.assertTrue(cancel.property("minor"))                 # «Отмена» - неважное
        self.assertFalse(bool(save.property("minor")))

    def test_menu_icons_leave_checkmarks_alone(self):
        from stungkir.icons import decorate_menu
        from stungkir.style import rounded_menu
        w = self.window()
        menu = rounded_menu(w)
        plain = menu.addAction("Статистика")
        toggle = menu.addAction("Часы в углу")
        toggle.setCheckable(True)
        decorate_menu(menu)
        self.assertFalse(plain.icon().isNull())
        self.assertTrue(toggle.icon().isNull())

    def test_every_theme_has_minor_and_old_custom_follows_dim(self):
        self.assertTrue(all("MINOR" in colors for colors in C.THEMES.values()))
        themes = C.all_themes({"custom_themes": {"Моя": {"DIM": "#123456"}}})
        self.assertEqual(themes["Моя"]["MINOR"], "#123456")

    def test_timer_rim_and_coin(self):
        w = self.window()
        w.timer_minutes.setValue(10)
        w.toggle_timer()
        self.assertEqual(w.fox_wheel.left, 1.0)
        self.assertEqual(w.timer_button.property("autoIcon"), "stop")
        w.toggle_timer()
        self.assertIsNone(w.fox_wheel.left)
        self.assertEqual(w.timer_button.property("autoIcon"), "play")


class ScreenItemsTest(WindowCase):
    """Вид → На экране: каждое убирается отдельно, запоминается, «Убрать всё» оставляет только текст."""

    def test_each_item_hides_and_is_remembered(self):
        w = self.window()
        w.goal = 500
        w.update_status()
        w.toggle_screen("goals")
        self.assertFalse(w.goal_strip.isVisible())
        w.toggle_screen("session")
        self.assertNotIn("сессия", w.status_plain)
        w.toggle_screen("tabs")
        self.assertFalse(w.left.hint.isVisible())
        w.toggle_screen("status")
        self.assertFalse(w.status.isVisible())
        self.assertTrue(w.corner_clock.isVisible())             # остальное на месте
        w.set_zen(True)
        w.set_zen(False)                                        # F10 туда-обратно не возвращает убранное
        self.assertFalse(w.status.isVisible())
        self.assertFalse(w.goal_strip.isVisible())
        w2 = self.window()                                      # и после перезапуска
        self.assertFalse(w2.status.isVisible())
        self.assertFalse(w2.left.hint.isVisible())

    def test_hide_all_and_back(self):
        w = self.window()
        w.goal = 500
        w.update_status()
        w.set_screen_all(False)
        for widget in (w.status, w.goal_strip, w.corner_clock, w.left.hint):
            self.assertFalse(widget.isVisible())
        self.assertFalse(w.notes_margin.shown)
        self.assertFalse(w.left.quiet)                          # панели у краёв по-прежнему выезжают
        w.set_screen_all(True)
        for widget in (w.status, w.goal_strip, w.corner_clock, w.left.hint):
            self.assertTrue(widget.isVisible())
        self.assertTrue(w.notes_margin.shown)
        self.assertIn("сессия", w.status_plain)

    def test_menu_has_screen_items(self):
        w = self.window()
        labels = []

        def walk(menu):
            for action in menu.actions():
                labels.append(action.text())
                if action.menu():
                    walk(action.menu())
        walk(w.build_more_menu())
        for _key, label in w.SCREEN_ITEMS:
            self.assertIn(label, labels)
        self.assertIn("Радуга", labels)
        self.assertIn("Убрать всё - только текст", labels)


class GoalColorsTest(WindowCase):
    def test_bars_are_bright_and_distinct_in_every_theme(self):
        from stungkir.widgets import GoalStrip
        strip = GoalStrip()
        for theme in C.THEMES:
            C.set_palette(C.THEMES[theme])
            colors = [strip.color(n) for n in strip.ORDER]
            for name, color in zip(strip.ORDER, colors):
                self.assertGreaterEqual(C.contrast(color, C.BG), 2.9, f"{theme}: {name} сливается с фоном")
            for i in range(3):
                for j in range(i + 1, 3):
                    self.assertGreaterEqual(GoalStrip._hue_gap(colors[i], colors[j]), 0.08,
                                            f"{theme}: полоски {strip.ORDER[i]} и {strip.ORDER[j]} одного цвета")
            for color in C.rainbow():
                self.assertGreaterEqual(C.contrast(color, C.BG), 1.85, f"{theme}: радуга не видна")

    def test_all_styles_paint(self):
        w = self.window()
        w.goal = 100
        w.today_base = 150                                      # цель дня выполнена - галочка
        for style in ("bright", "rainbow", "calm", "что-то странное"):
            w.set_goal_style(style)
            w.update_status()
            w.goal_strip.grab()
            w.status.grab()
        self.assertEqual(w.goal_strip.style_name, "bright")     # неизвестный вид - яркий
        self.assertIn("за день", w.status_plain)
        self.assertNotIn("<span", w.status_plain)


class CoverAndBackdropTest(WindowCase):
    def _picture(self, color="#3b3590", size=(300, 400)):
        from PySide6.QtGui import QImage, QColor
        image = QImage(*size, QImage.Format_RGB32)
        image.fill(QColor(color))
        path = self.tmp / f"картинка-{color[1:]}.png"
        image.save(str(path))
        return path

    def test_category_cover_everywhere(self):
        import zipfile
        from stungkir import covers
        from stungkir.windows import CoverDialog
        w = self.window()
        chapter = self.chapter("Книга", "Глава", "Текст главы.")
        w.refresh_tree()
        folder = chapter.parent
        dialog = CoverDialog(w, folder)
        self.assertFalse(dialog.choose_file(self.tmp / "нет.png"))
        self.assertTrue(dialog.choose_file(self._picture()))
        self.assertTrue(covers.has_cover(folder))
        self.assertTrue(covers.cover_path(folder).read_text(encoding="utf-8").startswith(covers.PREFIX))   # текстом, не картинкой
        w.refresh_tree()
        self.assertFalse(w.tree.topLevelItem(0).icon(0).isNull())          # значок в списке слева
        data = covers.cover_bytes(folder)
        self.assertTrue(data.startswith(b"\xff\xd8"))                        # JPEG
        from stungkir.export import export_epub, export_pdf
        options = {"headings": True, "new_page": True, "layout": {}, "cover": data}
        epub = self.tmp / "книга.epub"
        export_epub(epub, "Книга", "Автор", [("Глава", ["Текст."])], options)
        with zipfile.ZipFile(epub) as book:
            self.assertIn("OEBPS/cover.jpg", book.namelist())
            self.assertIn("cover-image", book.read("OEBPS/content.opf").decode())
        pdf = self.tmp / "книга.pdf"
        export_pdf(pdf, "Книга", "Автор", [("Глава", ["Текст."])], options)
        self.assertGreater(pdf.stat().st_size, len(data) // 3)
        from stungkir import storage as S
        self.assertIn(covers.cover_path(folder), S.content_files())          # с паролем шифруется
        dialog._remove()
        self.assertFalse(covers.has_cover(folder))

    def test_cover_moves_with_renamed_category(self):
        from stungkir import covers
        w = self.window()
        chapter = self.chapter("Книга", "Глава", "Текст.")
        covers.save_cover(chapter.parent, self._picture())
        self.answer_text = "Роман"
        self.patch("ask_text", lambda *a, **k: ("Роман", True))
        w.rename(chapter.parent)
        from stungkir import config as C
        self.assertTrue(covers.has_cover(C.ROOT / "Роман"))

    def test_own_picture_under_text(self):
        from stungkir import config as C
        w = self.window()
        w.resize(900, 600)
        w.show()
        warned = []
        self.patch("show_warning", lambda *a, **k: warned.append(a[-1]))
        w.backdrop_need = lambda: (1920, 1080)
        self.assertTrue(w.choose_backdrop(self._picture("#d4a02e", (800, 500))))
        self.assertEqual(C.TEXTURE, "picture")
        self.assertTrue(warned and "800×500" in warned[0])                 # маленькая - предупредили
        w.backdrop_need = lambda: (700, 400)
        warned.clear()
        self.assertTrue(w.choose_backdrop(self._picture("#d4a02e", (800, 500))))
        self.assertEqual(warned, [])
        # картинка - под всем окном, и у левого края тоже
        central = w.centralWidget().grab().toImage()
        edge = central.pixelColor(3, central.height() // 2)
        self.assertGreater(edge.red(), edge.blue())
        self.assertIsNotNone(w.editor.backdrop)
        w.set_backdrop_dim(82)
        self.assertAlmostEqual(w.editor.backdrop_dim, 0.82)
        shot = w.editor.viewport().grab().toImage()
        middle = shot.pixelColor(shot.width() // 2, shot.height() - 5)
        self.assertNotEqual(middle.name(), "#d4a02e")                       # притемнена цветом фона
        self.assertGreater(middle.red(), C.mix(C.BG, C.BG, 0).red())        # но видна
        w.set_texture("none")
        self.assertIsNone(w.editor.backdrop)
        w.set_texture("picture")                                           # картинка уже есть - без вопросов
        self.assertIsNotNone(w.editor.backdrop)
        self.assertFalse(w.choose_backdrop(self.tmp / "нет.png"))


class ReaderPreviewTest(WindowCase):
    def test_book_phone_and_reader(self):
        from stungkir import dialogs
        w = self.window()
        path = self.chapter("Книга", "Глава 1", "\n".join(f"Абзац номер {i}, *с курсивом*, длинный - чтобы "
                                                          "строк хватило на несколько страниц." for i in range(80))
                            + "\n* * *\n# Конец\nПоследний.")
        self.chapter("Книга", "Вторая", "Вторая глава.\n" * 20)
        from stungkir import storage
        storage.save_order(path.parent, ["Глава 1.txt", "Вторая.txt"])
        w.open_path(path)
        self.patch_exec = dialogs.Sheet.exec
        dialogs.Sheet.exec = lambda dialog: 0
        self.addCleanup(setattr, dialogs.Sheet, "exec", self.patch_exec)
        dialog = w.show_preview()
        counts = {}
        for device in ("book", "phone", "reader"):
            dialog.set_device(device)
            counts[device] = dialog.pages[device].count()
            dialog.view.resize(420, 560)
            dialog.view.grab()
            dialog.turn(1)
            self.assertEqual(dialog.number, 1)
            dialog.turn(-5)
            self.assertEqual(dialog.number, 0)
            self.assertIn(f"из {counts[device]}", dialog.counter.text())
        self.assertGreater(counts["phone"], counts["book"])          # на телефоне страниц больше
        self.assertGreater(counts["book"], 1)
        dialog.set_device("book")                                   # размеры книги и бумага
        dialog.size_box.setCurrentIndex(dialog.size_box.findData("a4"))
        a4 = dialog.pages["book"].count()
        dialog.size_box.setCurrentIndex(dialog.size_box.findData("pocket"))
        self.assertGreater(dialog.pages["book"].count(), a4)        # в карманной страниц больше
        dialog.paper_box.setCurrentIndex(dialog.paper_box.findData("old"))
        self.assertEqual(dialog.pages["book"].paper_key, "old")
        dialog.turn(1)                                              # перелистывание - с загибом
        self.assertIsNotNone(dialog.view.flip)
        dialog.view.flip_t = 0.5
        dialog.view.grab()
        dialog.view.finish_flip()
        self.assertIsNone(dialog.view.flip)
        dialog.set_device("tablet")
        dialog.view.grab()
        dialog.set_device("phone")                                  # лентой: главы подряд
        dialog.mode_box.setCurrentIndex(dialog.mode_box.findData("ribbon"))
        ribbon = dialog.view.pages
        self.assertEqual(len(ribbon.parts), 1)
        for _ in range(400):
            dialog.view.scroll_by(500)
            if len(ribbon.parts) == 2:
                break
        self.assertEqual(len(ribbon.parts), 2)                      # следующая глава подгрузилась сама
        self.assertEqual(ribbon.parts[1][0], "Вторая")
        dialog.view.grab()
        self.assertIn("из 2", dialog.counter.text())
        from stungkir.preview import chapter_html
        markup = chapter_html("Глава", "Раз *курсив*.\n* * *\n# Конец\n[пометка для себя]Текст.")
        self.assertIn("<i>курсив</i>", markup)
        self.assertIn('class="scene"', markup)
        self.assertIn("<h3>Конец</h3>", markup)
        self.assertNotIn("пометка", markup)
