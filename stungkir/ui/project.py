# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: импорт из Word и Scrivener, снимки всего проекта."""

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..core import config as C
from .dialogs import ask_choice, ask_question, ask_text, show_error, show_warning
from ..books.importers import (TABLE_READERS, ScrivenerError, read_document, read_scrivener, safe_name,
    scrivener_plan, split_chapters)
from ..world.lore import load_lore_config
from ..core.snapshots import SnapshotError, delete_snapshot, make_snapshot, restore_snapshot
from ..core.storage import (append_to_order, load_goals, load_names, load_order, load_plan, notes_path, os_message,
    save_text, unique_path)
from ..core.textutil import plural
from ..core.i18n import tr


class ProjectMixin:
    """Импорт из Word и Scrivener, снимки проекта. Часть главного окна."""

    # ---------------- Word ----------------
    def import_docx(self, source, category):
        return self.import_document(source, category)

    def import_tables(self, source, category):
        """Таблица Excel или Calc: каждый непустой лист - своя таблица блокнота. Возвращает число файлов."""
        from ..core.textutil import table_to_text
        sheets = [(name, rows) for name, rows in TABLE_READERS[source.suffix.lower()](source) if rows]
        made = 0
        for name, rows in sheets:
            title = safe_name(source.stem if len(sheets) == 1 else f"{source.stem} - {name}")
            header, body = rows[0], rows[1:]
            header = [cell or f"Столбец {i + 1}" for i, cell in enumerate(header)]
            target = unique_path(category / f"{title}.csv")
            save_text(target, table_to_text(header, body))
            append_to_order(category, target.name)
            made += 1
        return made

    def import_document(self, source, category):
        """Кладёт документ (Word, ODT, RTF, FB2, EPUB, HTML) в категорию: одним файлом или главами.
        Возвращает число новых файлов."""
        paragraphs = read_document(source)
        chapters = split_chapters(paragraphs, safe_name(source.stem))
        choice = "one"
        if len(chapters) > 1:
            names = ", ".join(f"«{name}»" for name, _ in chapters[:3])
            more = f" и ещё {len(chapters) - 3}" if len(chapters) > 3 else ""
            choice = ask_choice(
                self, tr("Импорт"),
                tr("В «{name}» {n} {n2}: {names}{more}.\n\nРазрезать на главы или положить одним файлом?").format(name=source.name, n=len(chapters), n2=plural(len(chapters), 'глава', 'главы', 'глав'), names=names, more=more),
                [("one", "Одним файлом"), ("split", f"Разрезать на {len(chapters)} "
                                                    f"{plural(len(chapters), 'главу', 'главы', 'глав')}")])
            if choice is None:
                return 0
        if choice == "split":
            items = [(safe_name(name), lines) for name, lines in chapters]
        else:
            items = [(safe_name(source.stem), [text for text, _level in paragraphs if text.strip()])]
        for name, lines in items:
            target = unique_path(category / f"{name}.txt")
            save_text(target, "\n".join(lines))
            append_to_order(category, target.name)
        return len(items)

    # ---------------- Scrivener ----------------
    def import_scrivener(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка проекта Scrivener (.scriv)", str(Path.home()))
        if not folder:
            return
        try:
            name, items = read_scrivener(folder)
        except ScrivenerError as error:
            show_warning(self, tr("Импорт из Scrivener"), tr("Не получилось: {error}.").format(error=error))
            return
        plan, skipped = scrivener_plan(name, items)
        if not plan:
            show_warning(self, tr("Импорт из Scrivener"), tr("В проекте не нашлось текстов."))
            return
        lines = "\n".join(f"• {category}: {len(chapters)} {plural(len(chapters), 'глава', 'главы', 'глав')}"
                          for category, chapters in plan)
        answer = ask_choice(self, tr("Импорт из Scrivener"),
                            tr("Из «{name}» будут созданы категории:\n{lines}\n\nСцены внутри папки станут "
                               "одной главой через «* * *», синопсисы и заметки - заметками на полях. Сам "
                               "проект Scrivener не меняется.").format(name=name, lines=lines),
                            [("cancel", "Отмена"), ("go", "Импортировать")])
        if answer != "go":
            return
        created, files, errors = [], 0, []
        for category, chapters in plan:
            target_folder = unique_path(C.ROOT / category)
            try:
                target_folder.mkdir(parents=True)
            except OSError as error:
                errors.append(f"{category} - {os_message(error)}")
                continue
            if load_order(C.ROOT):
                append_to_order(C.ROOT, target_folder.name)
            created.append(target_folder.name)
            for title, text_lines, notes in chapters:
                target = unique_path(target_folder / f"{title}.txt")
                try:
                    save_text(target, "\n".join(text_lines))
                    append_to_order(target_folder, target.name)
                    files += 1
                    if notes:
                        self._save_imported_notes(target, text_lines, notes)
                except OSError as error:
                    errors.append(f"{title} - {os_message(error)}")
        self.refresh_tree()
        message = (f"Готово: {files} {plural(files, 'глава', 'главы', 'глав')} в "
                   f"{len(created)} {plural(len(created), 'категории', 'категориях', 'категориях')}.")
        if skipped:
            message += (f"\n\nПропущено {skipped} {plural(skipped, 'файл', 'файла', 'файлов')} "
                        "не-текстов (PDF, картинки, веб-страницы): их можно открыть прямо из папки проекта.")
        if errors:
            message += "\n\nНе получилось:\n" + "\n".join("• " + e for e in errors)
        show_warning(self, tr("Импорт из Scrivener"), message)

    def _save_imported_notes(self, target, lines, notes):
        data = []
        for index, text in notes:
            data.append({"anchor": lines[index] if index < len(lines) else "", "index": index, "text": text,
                         "before": lines[index - 1] if 0 < index <= len(lines) else "",
                         "after": lines[index + 1] if index + 1 < len(lines) else ""})
        file = notes_path(target)
        file.parent.mkdir(parents=True, exist_ok=True)
        save_text(file, json.dumps(data, ensure_ascii=False, indent=1))

    # ---------------- снимки проекта ----------------
    def show_snapshots(self):
        from .windows import SnapshotsDialog
        SnapshotsDialog(self).exec()

    def take_snapshot(self):
        title, ok = ask_text(self, tr("Точка возврата"), tr("Как назвать точку? Например: «перед правкой второй части»."),
                             text=f"Точка {datetime.now():%d.%m.%Y %H:%M}")
        if not ok:
            return None
        if not self.save_everything():
            show_warning(self, tr("Точка возврата"), tr("Не получилось сохранить главу, точка не поставлена."))
            return None
        try:
            path = make_snapshot(title.strip() or "Точка")
        except SnapshotError as error:
            show_error(self, tr("Точка возврата"), tr("Точка не поставлена: {error}").format(error=error))
            return None
        self.toast.show_message(tr("Точка возврата поставлена"))
        return path

    def restore_snapshot(self, path, info):
        when = info.get("created", "")[:16].replace("T", " ")
        if ask_question(self, tr("Вернуться к точке"),
                        tr("Вернуть всю книгу к точке «{n}» ({when})?\n\nНынешнее состояние сначала "
                           "сохранится отдельной точкой, так что это можно отменить. История версий глав и "
                           "статистика останутся как есть.").format(n=info.get('title', ''), when=when)) != QMessageBox.Yes:
            return False
        if not self.save_everything():
            show_warning(self, tr("Вернуть книгу"), tr("Не получилось сохранить текущую главу, ничего не менял."))
            return False
        try:
            make_snapshot(f"Перед возвратом к «{info.get('title', '')}»")
            restore_snapshot(path)
        except SnapshotError as error:
            show_error(self, tr("Вернуть книгу"), tr("Книга не возвращена, всё осталось как было: {error}").format(error=error))
            return False
        self._reload_project()
        self.toast.show_message(tr("Книга возвращена к точке"), 3500)
        return True

    def delete_snapshot(self, path, info):
        if ask_question(self, tr("Удалить точку возврата"),
                        tr("Удалить точку «{n}»? Её не вернуть.").format(n=info.get('title', ''))) != QMessageBox.Yes:
            return False
        delete_snapshot(path)
        return True

    def _reload_project(self):
        """После возврата к снимку перечитывает всё, что лежит в папке книги."""
        self.names = load_names()
        self.highlighter.set_names(self.names)
        self.lore_cfg = load_lore_config()
        self.chapter_goals = load_goals()
        self.plan = load_plan()
        current = self.path
        self.path = None
        self.set_modified(False)
        self.load_text("")
        self.refresh_tree()
        if current is not None and current.is_file():
            self.open_path(current)
        self.update_title()
        self.refresh_side()

    def recode_snapshots(self, old_crypto, new_crypto):
        """Вызывается при установке и снятии пароля."""
        from ..core.snapshots import recode_snapshots
        failed = recode_snapshots(old_crypto, new_crypto)
        if failed:
            self._report("Точки возврата",
                         "Эти точки не получилось перешифровать, они остались как были:",
                         failed)

