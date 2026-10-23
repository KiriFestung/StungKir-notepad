# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Сохранение, кодировки, версии, заметки, резервные копии, переезд старой папки."""
import shutil
import zipfile
from datetime import date, timedelta

from stungkir import config as C
from stungkir import storage as S
from stungkir.tests.helpers import Sandbox


class SavingTest(Sandbox):
    def test_atomic_write_leaves_no_temp_files(self):
        path = self.chapter("Книга", "Глава", "")
        S.save_text(path, "Новый текст главы.")
        self.assertEqual(S.read_text(path), "Новый текст главы.")
        self.assertEqual(sorted(p.name for p in path.parent.iterdir()), ["Глава.txt"])

    def test_failed_write_keeps_old_text(self):
        path = self.chapter("Книга", "Глава", "Старый текст.")
        real = S.os.replace

        def broken(*_a, **_k):
            raise OSError(28, "No space left on device")
        S.os.replace = broken
        try:
            with self.assertRaises(OSError):
                S.save_text(path, "Новый текст, который не влез.")
        finally:
            S.os.replace = real
        self.assertEqual(S.read_text(path), "Старый текст.")
        self.assertEqual([p.name for p in path.parent.iterdir()], ["Глава.txt"])


class EncodingTest(Sandbox):
    TEXT = "Привет, мир! Ёжик в тумане шёл домой."

    def test_old_encodings_are_recognised(self):
        for data, name in ((self.TEXT.encode("utf-8"), "UTF-8"), (self.TEXT.encode("cp1251"), None),
                           (self.TEXT.encode("koi8-r"), None), (self.TEXT.encode("utf-16"), "UTF-16"),
                           (self.TEXT.encode("utf-16-le"), "UTF-16"),
                           (b"\xef\xbb\xbf" + self.TEXT.encode("utf-8"), "UTF-8")):
            text, encoding, lossy = S.decode_text(data)
            self.assertEqual(text, self.TEXT, encoding)
            self.assertFalse(lossy)
            if name:
                self.assertEqual(encoding, name)

    def test_word_control_characters_do_not_break_utf8(self):
        text = "Первая\x0b строка.\n\n— Реплика\x0c!"
        decoded, encoding, _ = S.decode_text(text.encode("utf-8"))
        self.assertEqual((decoded, encoding), (text, "UTF-8"))


class VersionsTest(Sandbox):
    def test_snapshot_skips_identical_text(self):
        path = self.chapter("Книга", "Глава", "")
        S.snapshot(path, "раз")
        S.snapshot(path, "раз")
        S.snapshot(path, "раз два")
        versions = S.list_versions(path)
        self.assertEqual(len(versions), 2)
        self.assertEqual(S.read_text(versions[0]), "раз два")   # новые сверху

    def test_category_named_like_root_does_not_share_history(self):
        root_file = C.ROOT / "Глава.txt"
        category_file = C.ROOT / C.ROOT.name / "Глава.txt"
        self.assertNotEqual(S.versions_dir(root_file), S.versions_dir(category_file))
        self.assertEqual(S.versions_dir(C.ROOT / "Книга" / "Глава.txt"),
                         C.service_path(".versions") / "Книга" / "Глава.txt")


class NotesStorageTest(Sandbox):
    def test_notes_move_with_chapter(self):
        old, new = C.ROOT / "Книга" / "Глава.txt", C.ROOT / "Роман" / "Первая.txt"
        S.notes_path(old).parent.mkdir(parents=True)
        S.notes_path(old).write_text("[]", encoding="utf-8", newline="\n")
        self.assertTrue(S.move_notes(old, new))
        self.assertTrue(S.notes_path(new).exists())
        self.assertFalse(S.notes_path(old).exists())

    def test_notes_are_part_of_content_for_encryption(self):
        self.chapter("Книга", "Глава", "текст")
        note = S.notes_path(C.ROOT / "Книга" / "Глава.txt")
        note.parent.mkdir(parents=True)
        note.write_text("[]", encoding="utf-8", newline="\n")
        self.assertIn(note, S.content_files())


class BackupTest(Sandbox):
    def test_backup_contains_texts_and_keeps_limited_number(self):
        self.chapter("Книга", "Глава", "Текст в архиве.")
        C.BACKUP_DIR.mkdir()
        for days in range(1, C.BACKUP_KEEP + 5):
            S.backup_path(date.today() - timedelta(days=days)).write_bytes(b"old")
        self.assertTrue(S.make_backup())
        archives = sorted(C.BACKUP_DIR.glob("*.zip"))
        self.assertEqual(len(archives), C.BACKUP_KEEP)
        with zipfile.ZipFile(S.backup_path()) as archive:
            names = archive.namelist()
            inside = next(n for n in names if n.endswith("Глава.txt"))
            self.assertEqual(archive.read(inside).decode("utf-8"), "Текст в архиве.")
        self.assertFalse(list(C.BACKUP_DIR.glob("*.part")))


class MigrationTest(Sandbox):
    def setUp(self):
        super().setUp()
        shutil.rmtree(C.ROOT)
        (C.OLD_ROOT / "Кат").mkdir(parents=True)
        (C.OLD_ROOT / "Кат" / "a.txt").write_text("текст", encoding="utf-8", newline="\n")
        (C.OLD_ROOT / "Кат" / ".order").write_text('["a.txt"]', encoding="utf-8", newline="\n")    # признак старой папки StungKir
        # переименовать нельзя (как будто другой диск) - придётся копировать
        self.real_rename = S.Path.rename

        def no_rename(path, target):
            if path == C.OLD_ROOT and S.Path(target) == C.ROOT:
                raise OSError(18, "Invalid cross-device link")
            return self.real_rename(path, target)
        S.Path.rename = no_rename
        self.addCleanup(setattr, S.Path, "rename", self.real_rename)

    def test_interrupted_copy_leaves_no_half_folder(self):
        real_copy = S.shutil.copytree

        def broken_copy(src, dst, *a, **k):
            real_copy(src, dst, *a, **k)
            raise shutil.Error("диск кончился")
        S.shutil.copytree = broken_copy
        try:
            error = S.migrate_old_root()
        finally:
            S.shutil.copytree = real_copy
        self.assertIsNotNone(error)
        self.assertFalse(C.ROOT.exists())
        self.assertEqual(sorted(p.name for p in C.ROOT.parent.iterdir() if p.name.startswith(".")), [])
        self.assertTrue((C.OLD_ROOT / "Кат" / "a.txt").exists())

    def test_copy_then_old_folder_is_marked(self):
        self.assertIsNone(S.migrate_old_root())
        self.assertEqual((C.ROOT / "Кат" / "a.txt").read_text(encoding="utf-8"), "текст")
        self.assertFalse(C.OLD_ROOT.exists())
        self.assertTrue(C.OLD_ROOT.with_name(C.OLD_ROOT.name + " (перенесено в StungKir)").exists())

    def test_someone_elses_notebook_folder_is_left_alone(self):
        (C.OLD_ROOT / "Кат" / ".order").unlink()
        self.assertIsNone(S.migrate_old_root())
        self.assertTrue((C.OLD_ROOT / "Кат" / "a.txt").exists())
        self.assertFalse(C.ROOT.exists())


class LauncherTest(Sandbox):
    def test_new_icon_gets_new_name_and_old_one_goes(self):
        import hashlib
        from stungkir.icons import ICON_SVG
        icons = S.Path.home() / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"
        icons.mkdir(parents=True, exist_ok=True)
        (icons / "stungkir.svg").write_text("<svg>старая лиса</svg>", encoding="utf-8", newline="\n")
        real = S.packaged
        S.packaged = lambda: False
        self.addCleanup(setattr, S, "packaged", real)
        icon = S.install_launcher()
        self.assertEqual(icon.name, f"stungkir-{hashlib.sha1(ICON_SVG.encode('utf-8')).hexdigest()[:8]}.svg")
        self.assertEqual(icon.read_text(encoding="utf-8"), ICON_SVG)
        self.assertFalse((icons / "stungkir.svg").exists())
        desktop = (S.Path.home() / ".local" / "share" / "applications" / "stungkir.desktop").read_text(encoding="utf-8")
        self.assertIn(f"Icon={icon}\n", desktop)


class WeeklyCopyTest(Sandbox):
    def test_once_a_week_into_own_folder(self):
        import tempfile
        from datetime import date, timedelta
        from pathlib import Path
        self.chapter("Книга", "Глава", "Текст главы.")
        folder = Path(tempfile.mkdtemp())
        day = date(2026, 10, 21)
        self.assertIsNone(S.weekly_copy("", None, day))                          # папка не задана
        self.assertIsNone(S.weekly_copy(folder / "нет флешки", None, day))       # флешку вынули
        self.assertEqual(S.weekly_copy(folder, None, day), "2026-10-21")
        self.assertEqual(len(list(folder.glob("*.zip"))), 1)
        self.assertIsNone(S.weekly_copy(folder, "2026-10-21", day + timedelta(days=3)))   # неделя не прошла
        for week in range(1, 12):
            S.weekly_copy(folder, None, day + timedelta(days=7 * week))
        self.assertEqual(len(list(folder.glob("*.zip"))), S.WEEKLY_KEEP)          # старые убираются


class TidyRootTest(Sandbox):
    def test_old_service_files_move_into_one_hidden_folder(self):
        import json
        chapter = self.chapter("Книга", "Глава", "Текст.")
        (C.ROOT / ".stats.json").write_text('{"2026-10-01": 300}', encoding="utf-8", newline="\n")
        (C.ROOT / ".names.json").write_text('["Кира"]', encoding="utf-8", newline="\n")
        old_versions = C.ROOT / ".versions" / "Книга" / "Глава.txt"
        old_versions.mkdir(parents=True)
        (old_versions / "2026-10-01_10-00-00_000000.txt").write_text("Старое.", encoding="utf-8", newline="\n")
        (C.ROOT / ".dictionary.txt").write_text("фух\n", encoding="utf-8", newline="\n")
        before = sorted(p.read_bytes() for p in C.ROOT.rglob("*") if p.is_file() and C.SERVICE_DIR not in p.parts)
        moved = S.tidy_root()
        self.assertEqual(set(moved), {".stats.json", ".names.json", ".versions", ".dictionary.txt"})
        self.assertEqual(sorted(p.name for p in C.ROOT.iterdir()), [".stungkir", "Книга"])  # рядом - только книги
        after = sorted(p.read_bytes() for p in C.ROOT.rglob("*") if p.is_file())
        for data in before:
            self.assertIn(data, after)                       # ни один файл не потерялся
        self.assertEqual(S.load_stats(), {"2026-10-01": 300})
        self.assertEqual(len(S.list_versions(chapter)), 1)
        self.assertTrue(S.backup_path().exists())            # копия до переезда
        self.assertEqual(S.tidy_root(), [])                  # второй раз - нечего делать
        # синхронизация принесла старый файл ещё раз: ничего не затирается
        C.service_path(".stats.json").write_text('{"2026-10-02": 500}', encoding="utf-8", newline="\n")
        (C.ROOT / ".stats.json").write_text('{"2026-10-01": 300}', encoding="utf-8", newline="\n")
        import os
        os.utime(C.ROOT / ".stats.json", (1, 1))
        S.tidy_root()
        self.assertEqual(json.loads(C.service_path(".stats.json").read_text(encoding="utf-8")), {"2026-10-02": 500})
        aside = list((C.ROOT / C.SERVICE_DIR / "переезд").rglob(".stats.json"))
        self.assertEqual(len(aside), 1)
        self.assertFalse((C.ROOT / ".stats.json").exists())


class PhoneStatsTest(Sandbox):
    def test_each_device_has_own_file_and_they_add_up(self):
        S.save_stats({"2026-10-20": 300})
        phone = C.ROOT / C.SERVICE_DIR / "stats-phone.json"
        phone.write_text('{"2026-10-20": 120, "2026-10-21": 50}', encoding="utf-8", newline="\n")
        self.assertEqual(S.load_stats(own_only=True), {"2026-10-20": 300})
        self.assertEqual(S.load_stats(), {"2026-10-20": 420, "2026-10-21": 50})
        phone.write_text("испорчен", encoding="utf-8", newline="\n")
        self.assertEqual(S.load_stats(), {"2026-10-20": 300})


class PortableTest(Sandbox):
    """Переносная версия: portable.txt рядом с .exe - всё хранится рядом с программой."""

    def test_marker_next_to_exe(self):
        import sys
        from unittest import mock
        folder = self.tmp / "флешка" / "StungKir"
        folder.mkdir(parents=True)
        exe = folder / "StungKir.exe"
        exe.write_bytes(b"")
        with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "executable", str(exe)):
            self.assertIsNone(C._portable_dir())
            (folder / C.PORTABLE_MARK).write_text("переносная", encoding="utf-8")
            self.assertEqual(C._portable_dir(), folder.resolve())
        # без сборки (запуск из исходников) метка не действует
        self.assertIsNone(C._portable_dir())


class NamesTest(Sandbox):
    def test_unique_path_ignores_letter_case(self):
        """«Глава» и «глава» на Windows и телефоне - один файл: новое имя не должно с ним совпасть."""
        folder = C.ROOT / "Книга"
        folder.mkdir()
        (folder / "Глава.txt").write_text("раз", encoding="utf-8", newline="\n")
        self.assertEqual(S.unique_path(folder / "глава.txt").name, "глава (2).txt")
        self.assertEqual(S.unique_path(folder / "Глава.txt").name, "Глава (2).txt")
        (folder / "ГЛАВА (2).txt").write_text("два", encoding="utf-8", newline="\n")
        self.assertEqual(S.unique_path(folder / "глава.txt").name, "глава (3).txt")
        self.assertEqual(S.unique_path(folder / "Другая.txt").name, "Другая.txt")

    def test_content_files_without_root(self):
        """Папку с книгами удалили или диск отключился - список пуст, без падения."""
        shutil.rmtree(C.ROOT)
        self.assertEqual([p for p in S.content_files() if C.ROOT in p.parents], [])
