# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно целиком: сохранение и версии, заметки на полях, справочник мира."""
import json

from stungkir import config as C
from stungkir import storage as S
from stungkir.tests.helpers import WindowCase, speller_available, wait


class ChapterTest(WindowCase):
    def test_save_writes_file_and_version(self):
        path = self.chapter("Книга", "Глава", "Начало.")
        w = self.window()
        w.open_path(path)
        w.editor.moveCursor(w.editor.textCursor().MoveOperation.End)
        w.editor.insertPlainText(" Продолжение.")
        self.assertTrue(w.is_modified())
        w.save()
        self.assertEqual(path.read_text(encoding="utf-8"), "Начало. Продолжение.")
        self.assertFalse(w.is_modified())
        self.assertEqual(S.read_text(S.list_versions(path)[0]), "Начало. Продолжение.")

    def test_versions_dialog_shows_changes(self):
        path = self.chapter("Книга", "Глава", "Раз.")
        w = self.window()
        w.open_path(path)
        w.save()
        w.editor.setPlainText("Раз.\nДва три.")
        w.save()
        from stungkir.windows import VersionsDialog
        dialog = VersionsDialog(w, path, S.list_versions(path), w.editor.font(), w.current_text())
        dialog.mode.setCurrentIndex(1)
        dialog._show(0)
        self.assertIn("+2 слова", dialog.summary.text())


class NotesTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.paragraphs = ["Утро было серым.", "Ольга вышла к реке.", "Лодки не было.", "Вечер."]
        self.path = self.chapter("Книга", "Глава", "\n".join(self.paragraphs))
        self.other = self.chapter("Книга", "Другая", "Другая глава.")
        self.answers = []
        test = self

        class FakeNote:
            def __init__(self, *a, **k):
                self.action, self._text = test.answers.pop(0)

            def exec(self):
                return self.action is not None

            def text(self):
                return self._text
        self.patch("NoteDialog", FakeNote)
        self.w = self.window()
        self.w.open_path(self.path)

    def notes(self):
        return [(n["anchor"], n["text"]) for n in self.w.notes_margin.data()]

    def add(self, number, text):
        self.answers.append(("save", text))
        self.w.note_for_block(self.w.editor.document().findBlockByNumber(number))

    def test_note_is_saved_beside_chapter_and_survives_edits(self):
        self.add(1, "Какая река?")
        stored = json.loads(S.notes_path(self.path).read_text(encoding="utf-8"))
        self.assertEqual(stored[0]["text"], "Какая река?")
        cursor = self.w.editor.textCursor()
        cursor.setPosition(0)
        cursor.insertText("Новый первый абзац.\n")
        self.w.save()
        self.w.open_path(self.other)
        self.w.open_path(self.path)
        self.assertEqual(self.notes(), [("Ольга вышла к реке.", "Какая река?")])

    def test_note_does_not_go_into_text_or_word_count(self):
        words = self.w.word_count()
        self.add(2, "Добавить лодку позже")
        self.assertEqual(self.w.word_count(), words)
        self.assertNotIn("лодку позже", self.w.current_text())

    def test_note_moves_with_rename(self):
        self.add(0, "Заметка")
        self.patch("ask_text", lambda *a, **k: ("Первая", True))
        self.w.rename(self.path)
        new = self.path.with_name("Первая.txt")
        self.assertTrue(S.notes_path(new).exists())
        self.assertEqual(self.notes(), [("Утро было серым.", "Заметка")])

    def test_delete_note(self):
        self.add(0, "Заметка")
        self.answers.append(("delete", ""))
        self.w.edit_note(0)
        self.assertEqual(self.notes(), [])
        self.assertFalse(S.notes_path(self.path).exists())

    def test_broken_notes_file_is_kept_aside(self):
        self.w.open_path(self.other)
        S.notes_path(self.path).parent.mkdir(parents=True, exist_ok=True)
        S.notes_path(self.path).write_text("{сломано", encoding="utf-8", newline="\n")
        self.w.open_path(self.path)
        self.assertEqual(self.notes(), [])
        self.assertTrue(S.notes_path(self.path).with_name("Глава.txt.json.broken").exists())


class LoreWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        world = C.ROOT / "Мир"
        world.mkdir()
        (world / "Тервена.txt").write_text("Также: Тервенская республика\nПрибрежное государство.", encoding="utf-8", newline="\n")
        (world / "_Общее.txt").write_text("Не термин.", encoding="utf-8", newline="\n")
        self.chapter_path = self.chapter("Книга", "Глава", "Она вспомнила Тервену.\nВ Тервенне шёл дождь.")
        self.w = self.window()
        self.w.toggle_lore_category(world)
        self.w.open_path(self.chapter_path)

    def test_terms_from_reference_category(self):
        self.assertEqual(sorted(t.name for t in self.w.lore.terms), ["Тервена"])
        self.assertEqual(json.loads(C.service_path(".lore.json").read_text(encoding="utf-8"))["categories"], ["Мир"])

    def test_hover_shows_note(self):
        doc = self.w.editor.document()
        block = doc.firstBlock()
        cursor = self.w.editor.textCursor()
        cursor.setPosition(block.position() + block.text().index("Тервену") + 2)
        point = self.w.editor.cursorRect(cursor).center()
        tip = self.w._lore_tip(point)
        self.assertIn("Прибрежное государство.", tip)

    def test_spelling_check_lists_variant(self):
        if not speller_available():
            self.skipTest("нет словаря hunspell-ru")
        self.w.check_term_spelling()
        wait()
        self.assertEqual(self.w.variant_terms, {"Тервенне": "Тервена"})
        self.assertEqual(self.w.global_results.count(), 1)

    def test_renaming_category_keeps_it_a_reference(self):
        self.patch("ask_text", lambda *a, **k: ("Справочник", True))
        self.w.rename(C.ROOT / "Мир")
        self.assertEqual(self.w.lore_cfg["categories"], ["Справочник"])
        self.assertEqual(len(self.w.lore.terms), 1)


class AutosaveTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(setattr, C, "AUTOSAVE_PAUSE_MS", C.AUTOSAVE_PAUSE_MS)
        C.AUTOSAVE_PAUSE_MS = 200
        self.path = self.chapter("Книга", "Глава", "Начало.")
        self.w = self.window()
        self.w.autosave_timer.setInterval(C.AUTOSAVE_PAUSE_MS)
        self.w.open_path(self.path)

    def type(self, text):
        cursor = self.w.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.w.editor.setTextCursor(cursor)
        self.w.editor.insertPlainText(text)

    def test_saves_after_pause_quietly(self):
        self.type(" Дальше.")
        self.assertTrue(self.w.is_modified())
        wait(0.5)
        self.assertEqual(S.read_text(self.path), "Начало. Дальше.")
        self.assertFalse(self.w.is_modified())
        self.assertNotEqual(self.w.toast.text(), "Сохранено")       # без сообщения на листе

    def test_versions_not_on_every_autosave(self):
        self.w.save()                                                 # ручное - всегда версия
        before = len(S.list_versions(self.path))
        for word in (" раз", " два", " три"):
            self.type(word)
            wait(0.4)
        self.assertEqual(S.read_text(self.path), "Начало. раз два три")
        self.assertEqual(len(S.list_versions(self.path)), before)    # автосохранения не плодят версии

    def test_saves_during_long_typing(self):
        self.addCleanup(setattr, C, "AUTOSAVE_MAX_S", C.AUTOSAVE_MAX_S)
        C.AUTOSAVE_MAX_S = 0.3
        self.w.autosave_timer.setInterval(10_000)                    # паузы нет
        self.type(" а")
        wait(0.4)
        self.type(" б")
        self.assertEqual(S.read_text(self.path), "Начало. а б")

    def test_new_text_lands_in_drafts(self):
        self.w.path = None
        self.w.load_text("")
        self.type("Новый текст без файла.")
        wait(0.5)
        drafts = C.ROOT / "Черновики"
        self.assertEqual([f.name for f in S.files_in(drafts)], ["Глава 1.txt"])

    def test_can_be_turned_off(self):
        self.addCleanup(setattr, C, "AUTOSAVE", C.AUTOSAVE)
        C.AUTOSAVE = False
        self.type(" Не сохранять.")
        wait(0.5)
        self.assertEqual(S.read_text(self.path), "Начало.")
        self.assertTrue(self.w.is_modified())

    def test_failure_does_not_spam_dialogs(self):
        def broken(*a, **k):
            raise OSError(28, "No space left on device")
        self.patch("save_text", broken)
        self.type(" x")
        wait(0.5)
        self.assertEqual(self.messages, [])                          # без окон с ошибкой каждые 3 секунды
        self.assertIn("Автосохранение не удалось", self.w.toast.text())


class HotkeysTest(WindowCase):
    def test_change_hotkey_and_conflicts(self):
        import json
        from PySide6.QtGui import QKeySequence
        from stungkir import dialogs
        from stungkir.dialogs import HotkeysDialog, hotkey_problems
        w = self.window()
        self.assertEqual(w.shortcuts["antistress"].key().toString(), "F12")
        self.assertTrue(hotkey_problems({"save": "Ctrl+S", "new": "Ctrl+S"}))       # одна на два дела
        self.assertTrue(hotkey_problems({"save": "Alt+F4"}))                         # системная
        self.assertEqual(hotkey_problems(dict(dialogs.DEFAULT_KEYS)), [])
        dialog = HotkeysDialog(w, w.hotkeys())
        dialog.edits["antistress"].setKeySequence(QKeySequence("Ctrl+Shift+A"))
        dialog.edits["save"].setKeySequence(QKeySequence("Ctrl+N"))
        self.assertFalse(dialog.ok.isEnabled())                                      # Ctrl+N уже занята
        dialog.edits["save"].setKeySequence(QKeySequence("Ctrl+S"))
        self.assertTrue(dialog.ok.isEnabled())
        values = dialog.values()
        original = dialogs.Sheet.exec
        HotkeysDialog.exec = lambda d: (d.edits["antistress"].setKeySequence(QKeySequence("Ctrl+Shift+A")), 1)[1]
        self.addCleanup(lambda: delattr(HotkeysDialog, "exec"))
        w.show_hotkeys()
        self.assertEqual(json.loads(w.settings.value("hotkeys")), {"antistress": "Ctrl+Shift+A"})
        self.assertEqual(w.shortcuts["antistress"].key().toString(), "Ctrl+Shift+A")
        self.assertIn("Ctrl+Shift+A", w.hk("antistress"))
        self.assertEqual(values["antistress"], "Ctrl+Shift+A")
        dialog.reset()
        self.assertEqual(dialog.values()["antistress"], "F12")
        self.assertIs(original, dialogs.Sheet.exec)
