# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: файлы, категории, открытие, сохранение, сборка книги, версии."""

import json
import os
from pathlib import Path
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QIcon, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import QAbstractItemView, QApplication, QFileDialog, QMessageBox, QTreeWidgetItem

from . import config as C
from .style import fade, rounded_menu
from .textutil import WORD_RE, is_board, is_prose, is_table, is_timeline, table_to_text, words_label
from .trash import DAYS as TRASH_DAYS, TrashDialog, move_to_trash, restore as restore_from_trash
from .conflicts import NOT_TEXT_HINT
from .storage import bad_name_reason, conflict_original, is_text_file, keep_raw_copy, name_clash
from .storage import (
    LockedFile, append_to_order, files_in, list_versions, load_order, log_error,
    move_notes, move_tree, move_versions, ordered, os_message, read_text,
    read_text_info, rename_in_order, report_problem, save_order, save_text,
    next_chapter_name, snapshot, unique_path,
)
from .lore import save_lore_config
from .export import (
    book_paragraphs, docx_available, export_docx, export_epub, export_fb2, export_pdf, export_txt, marker_lines,
)
from .dialogs import ask_choice, ask_item, ask_question, ask_text, show_error, show_warning
from .windows import CompileDialog, VersionsDialog


def _valid_json(text):
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


class FilesMixin:
    """Файлы, категории, открытие, сохранение, сборка книги, версии. Часть главного окна."""

    # ---------------- изменения с другого устройства ----------------
    def _stamp(self, path):
        try:
            info = path.stat()
            return info.st_mtime_ns, info.st_size
        except OSError:
            return None

    def remember_own_write(self):
        if self.path is not None:
            self._own_stamp = self._stamp(self.path)

    def watch_current(self):
        files = self.watcher.files()
        if files:
            self.watcher.removePaths(files)
        if self.path is not None and self.path.exists():
            self.watcher.addPath(str(self.path))

    def watch_dirs(self):
        dirs = self.watcher.directories()
        if dirs:
            self.watcher.removePaths(dirs)
        self.watcher.addPaths([str(C.ROOT)] + [str(c) for c in self.categories()])

    def _signature(self):
        return tuple((c.name, tuple(f.name for f in files_in(c))) for c in self.categories())

    def _tree_maybe_changed(self):
        if self._signature() != self._tree_signature:
            self.refresh_tree()
        else:
            self.rebuild_lore()   # например, Syncthing обновил файл справочника
            self.refresh_side()

    def check_external(self):
        if self.path is None or getattr(self, "_closed", False):
            return
        if not self.path.exists():
            if getattr(self, "_gone_told", None) != self.path:
                self._gone_told = self.path
                self.toast.show_message(f"«{self.path.stem}» удалили или переименовали снаружи. Текст остался "
                                        "здесь - сохранишь, и глава появится снова", 5000)
            return
        self.watch_current()   # после замены файла его надо отслеживать заново
        stamp = self._stamp(self.path)
        if stamp == self._own_stamp:
            return
        self._own_stamp = stamp
        try:
            text = read_text(self.path)
        except (OSError, LockedFile):
            return
        if text == self.current_text():
            return
        if self.is_modified():
            choice = ask_choice(self, "Глава изменилась",
                                f"«{self.path.stem}» изменили на другом устройстве.\n"
                                "Твои несохранённые правки останутся в версиях.",
                                [("keep", "Оставить мою"), ("take", "Взять новую")])
            if choice != "take":
                # своя версия остаётся и сразу ложится на диск, а пришедшая - в «Версии файла»:
                # иначе после Ctrl+Z глава выглядела бы сохранённой, хотя на диске другой текст
                snapshot(self.path, text)
                snapshot(self.path, self.current_text())
                try:
                    self.save(auto=True)
                except OSError as error:
                    log_error("Своя версия не записалась", error)
                    self.toast.show_message(f"Не записалось: {os_message(error)}. Сохрани вручную", 4000)
                return
        # то, что было на экране, - в версии (если ещё не там): автосохранённое версий не делает
        snapshot(self.path, self.current_text())
        if self.view:
            self.load_view(self.view, text)
            self.toast.show_message(f"{self.view.kind()} обновилась с другого устройства", 2500)
            return
        position = self.editor.textCursor().position()
        notes = self.notes_margin.data()
        self.load_text(text)
        self.notes_margin.load(notes)
        cursor = self.editor.textCursor()
        cursor.setPosition(min(position, self.editor.document().characterCount() - 1))
        self.editor.setTextCursor(cursor)
        self.toast.show_message("Глава обновилась с другого устройства", 2500)

    def save_everything(self):
        """Сохраняет без вопросов. Безымянный текст кладёт в «Черновики»."""
        if not self.is_modified():
            return True
        if self.path is not None:
            return self.save()
        text = self.editor.toPlainText()
        if not text.strip():
            self.editor.document().setModified(False)
            return True
        folder = C.ROOT / "Черновики"
        folder.mkdir(exist_ok=True)
        path = unique_path(folder / f"{next_chapter_name(folder)}.txt")
        try:
            save_text(path, text)
        except OSError:
            return False
        append_to_order(folder, path.name)
        snapshot(path, text)
        self.path = path
        self.remember_own_write()
        self.editor.document().setModified(False)
        self.update_title()
        self.refresh_tree()
        return True

    # ---------------- файлы ----------------
    def categories(self):
        if not C.ROOT.is_dir():
            # папку с текстами удалили или отключили диск - не падаем, а заводим заново
            try:
                C.ROOT.mkdir(parents=True, exist_ok=True)
            except OSError:
                return []
        return ordered([p for p in C.ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")],
                       C.ROOT)

    def _update_arrow(self, item):
        if item.parent() is None:
            arrow = "▾" if item.isExpanded() else "▸"
            name = Path(item.data(0, Qt.UserRole)).name
            mark = "   ✦" if name in self.lore_cfg["categories"] else ""
            item.setText(0, f"{arrow}  {name}{mark}")

    def _cover_icon(self, item, folder):
        """Обложка категории - маленьким значком слева от названия."""
        from .covers import cover_pixmap, has_cover
        if not has_cover(folder):
            item.setIcon(0, QIcon())
            return
        picture = cover_pixmap(folder)
        if picture.isNull():
            return
        thumb = picture.scaled(36, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        item.setIcon(0, QIcon(thumb))
        item.setToolTip(0, f"«{folder.name}» - у категории есть обложка. Правый клик → «Обложка…»")

    def make_world_kit(self, category=None):
        """Пустые таблицы и карточки для мира в категории (по умолчанию - спросить, в какую)."""
        from .worldkit import WorldKitDialog, create_kit
        category = category or self.ask_category()
        if not category:
            return []
        is_lore = category.name in self.lore_cfg["categories"]
        dialog = WorldKitDialog(self, category.name, is_lore)
        if not dialog.exec() or not dialog.chosen():
            return []
        made = create_kit(category, dialog.chosen())
        if dialog.lore.isChecked() and not is_lore:
            self.toggle_lore_category(category)
        self.refresh_tree()
        self.toast.show_message(f"Создано в «{category.name}»: {len(made)}")
        return made

    def show_cover(self, folder):
        from .windows import CoverDialog
        CoverDialog(self, folder).exec()
        self.refresh_tree()

    def refresh_tree(self):
        expanded = {Path(self.tree.topLevelItem(i).data(0, Qt.UserRole)).name
                    for i in range(self.tree.topLevelItemCount())
                    if self.tree.topLevelItem(i).isExpanded()}
        first_run = self.tree.topLevelItemCount() == 0
        self.tree.clear()
        current = None
        for folder in self.categories():
            item = QTreeWidgetItem([folder.name])
            item.setData(0, Qt.UserRole, str(folder))
            self._cover_icon(item, folder)
            self.tree.addTopLevelItem(item)
            self._update_arrow(item)
            for f in files_in(folder, everything=True):
                original = conflict_original(f)
                if not is_text_file(f):
                    child = QTreeWidgetItem(["      ⊘ " + f.name])            # картинка, Word, программа
                    child.setData(0, Qt.UserRole, str(f))
                    child.setForeground(0, QColor(C.DIM))
                    child.setToolTip(0, "Не текст - блокнот его не открывает. " + NOT_TEXT_HINT)
                    child.setFlags(child.flags() & ~Qt.ItemIsDropEnabled)
                    item.addChild(child)
                    continue
                if original is not None:
                    child = QTreeWidgetItem([f"      ⚠ {original.stem} - конфликт"])
                    child.setData(0, Qt.UserRole, str(f))
                    child.setForeground(0, QColor(C.SPELL))
                    child.setToolTip(0, "Копия от программы синхронизации: глава поменялась на двух устройствах. "
                                        "Открой - покажу разницу и дам выбрать")
                    child.setFlags(child.flags() & ~Qt.ItemIsDropEnabled)
                    item.addChild(child)
                    continue
                if is_table(f):
                    label = f"▦ {f.stem}"
                elif is_board(f):
                    label = f"▤ {f.stem}"
                elif is_timeline(f):
                    label = f"◷ {f.stem}"
                else:
                    label = f.stem if f.suffix == ".txt" else f.name
                child = QTreeWidgetItem(["      " + label])
                child.setData(0, Qt.UserRole, str(f))
                # на файл ничего нельзя бросить, только выше или ниже него
                child.setFlags(child.flags() & ~Qt.ItemIsDropEnabled)
                item.addChild(child)
                if self.path and f == self.path:
                    current = child
            item.setExpanded(first_run or folder.name in expanded
                             or (self.path is not None and self.path.parent == folder))
        if current:
            self.tree.setCurrentItem(current)
        self._tree_signature = self._signature()
        self.watch_dirs()
        self.watch_current()
        self.rebuild_lore()
        self.mark_tree_status()
        self.check_conflicts(quiet=first_run)        # новые конфликты - плашкой; при запуске - чуть позже

    def select_in_tree(self):
        for i in range(self.tree.topLevelItemCount()):
            folder = self.tree.topLevelItem(i)
            for j in range(folder.childCount()):
                child = folder.child(j)
                if self.path is not None and Path(child.data(0, Qt.UserRole)) == self.path:
                    folder.setExpanded(True)
                    self.tree.setCurrentItem(child)
                    return

    def item_path(self, item):
        return Path(item.data(0, Qt.UserRole)) if item else None

    def selected_category(self):
        path = self.item_path(self.tree.currentItem())
        if path:
            return path if path.is_dir() else path.parent
        return self.path.parent if self.path else None

    def ask_category(self):
        category = self.selected_category()
        if category and category.is_dir():
            return category
        cats = self.categories()
        if not cats:
            return self.new_category()
        if len(cats) == 1:
            return cats[0]
        name, ok = ask_item(self, "Категория", "Куда положить:",
                                        [c.name for c in cats], 0, False)
        return C.ROOT / name if ok else None

    def ask_name(self, title, label, default=""):
        name, ok = ask_text(self, title, label, text=default)
        name = name.strip()
        if not ok or not name:
            return None
        reason = bad_name_reason(name)
        if reason:
            show_warning(self, title, reason)
            return None
        return name

    def new_category(self):
        name = self.ask_name("Новая категория", "Название категории:")
        if not name:
            return None
        folder = C.ROOT / name
        if name_clash(folder):
            show_warning(self, "Новая категория", f"Такая категория уже есть: «{name_clash(folder).name}».")
            return None
        try:
            folder.mkdir()
        except OSError as error:
            show_error(self, "Новая категория", f"Категория не создана. {os_message(error)}")
            return None
        if load_order(C.ROOT):
            append_to_order(C.ROOT, name)
        self.refresh_tree()
        return folder

    def new_file(self, content=None):
        """Новый пустой файл. С content - сохранить текущий текст как новый файл."""
        if content is None and not self.maybe_save():
            return False
        category = self.ask_category()
        if not category:
            return False
        lore = content is None and category.name in self.lore_cfg["categories"]
        name = self.ask_name("Новый файл", f"Название файла в «{category.name}»:",
                             "" if lore else next_chapter_name(category))
        if not name:
            return False
        if lore:                                   # карточка справочника: можно начать с шаблона
            content = self.choose_template()
            if content is None:
                return False
            fresh = True
        else:
            fresh = content is None
        # «Глава 1.5» или «План.board» - всё равно глава: тип файла не меняется от точки в названии
        path = category / (name if Path(name).suffix.lower() in (".txt", ".md") else name + ".txt")
        if name_clash(path):
            show_warning(self, "Новый файл", f"Файл с таким названием уже есть: «{name_clash(path).name}».")
            return False
        try:
            save_text(path, content or "")
        except OSError as error:
            show_error(self, "Новый файл", f"Файл не создан. {os_message(error)}")
            return False
        append_to_order(category, path.name)
        if fresh:
            self.remember_position()
            self.load_text(content or "")
            self.fade_in_editor()
        else:
            snapshot(path, content)
        self.path = path
        self.remember_own_write()
        self.editor.document().setModified(False)
        self.update_title()
        self.refresh_tree()
        self.editor.setFocus()
        return True

    def new_table(self):
        if not self.maybe_save():
            return False
        category = self.ask_category()
        if not category:
            return False
        name = self.ask_name("Новая таблица", f"Название таблицы в «{category.name}»:")
        if not name:
            return False
        path = category / (name + ".csv")
        if name_clash(path):
            show_warning(self, "Новая таблица", "Файл с таким названием уже есть.")
            return False
        empty = [[""] * len(C.TABLE_COLUMNS) for _ in range(C.TABLE_ROWS)]
        header_only = table_to_text(list(C.TABLE_COLUMNS), [])
        try:
            save_text(path, header_only)
        except OSError as error:
            show_error(self, "Новая таблица", f"Не получилось создать:\n{error}")
            return False
        append_to_order(category, path.name)
        self.refresh_tree()
        self.open_path(path)
        self.table_view._loading = True
        self.table_view.table.setRowCount(len(empty))
        self.table_view._loading = False
        self.table_view.set_modified(False)
        return True

    def new_board(self):
        if not self.maybe_save():
            return False
        category = self.ask_category()
        if not category:
            return False
        name = self.ask_name("Новая доска", f"Название доски в «{category.name}»:")
        if not name:
            return False
        path = category / (name + ".board")
        if name_clash(path):
            show_warning(self, "Новая доска", "Файл с таким названием уже есть.")
            return False
        blank = {"columns": [{"title": t, "cards": []} for t in C.BOARD_COLUMNS]}
        try:
            save_text(path, json.dumps(blank, ensure_ascii=False, indent=1) + "\n")
        except OSError as error:
            show_error(self, "Новая доска", f"Не получилось создать:\n{error}")
            return False
        append_to_order(category, path.name)
        self.refresh_tree()
        self.open_path(path)
        return True

    def new_timeline(self):
        if not self.maybe_save():
            return False
        category = self.ask_category()
        if not category:
            return False
        name = self.ask_name("Новая хронология", f"Название хронологии в «{category.name}»:", "Хронология")
        if not name:
            return False
        path = category / (name + ".timeline")
        if name_clash(path):
            show_warning(self, "Новая хронология", "Файл с таким названием уже есть.")
            return False
        try:
            save_text(path, json.dumps({"events": []}, ensure_ascii=False, indent=1) + "\n")
        except OSError as error:
            show_error(self, "Новая хронология", f"Не получилось создать:\n{error}")
            return False
        append_to_order(category, path.name)
        self.refresh_tree()
        self.open_path(path)
        return True

    def show_create_menu(self):
        menu = rounded_menu(self)
        menu.addAction("Главу" + self.hk("new"), self.new_file)
        menu.addAction("Таблицу", self.new_table)
        menu.addAction("Доску сюжета", self.new_board)
        menu.addAction("Хронологию", self.new_timeline)
        menu.addSeparator()
        menu.addAction("Категорию", self.new_category)
        menu.exec(self.create_button.mapToGlobal(QPoint(self.create_button.width(), 0)))

    def compile_book(self):
        if not self.save_everything():
            return
        current = self.path.parent if self.path else None
        dialog = CompileDialog(self, self.categories(), current,
                               self.settings.value("author", ""), self.skipped_chapters())
        if not dialog.exec():
            return
        options = dialog.options()
        self.settings.setValue("author", options["author"])
        if options["format"] == "docx" and not docx_available():
            show_warning(self, "Собрать книгу", "Для Word нужна библиотека python-docx.\n"
                                "Запусти install.sh ещё раз, он её поставит.")
            return
        extension = options["format"]
        filters = {"pdf": "PDF (*.pdf)", "docx": "Word (*.docx)", "epub": "Электронная книга (*.epub)",
                   "fb2": "FictionBook (*.fb2)", "txt": "Текст (*.txt)"}
        default = Path.home() / f"{options['title']}.{extension}"
        target, _ = QFileDialog.getSaveFileName(self, "Сохранить книгу", str(default),
                                                filters[options["format"]])
        if not target:
            return
        target = Path(target)
        if target.suffix.lower() != "." + extension:
            target = target.with_name(target.name + "." + extension)
        texts, skipped, folders = [], [], {}
        for path in options["chapters"]:
            try:
                texts.append((path.stem, self.current_text() if path == self.path else read_text(path)))
                folders[len(texts) - 1] = path.parent          # там ищутся картинки из текста
            except (OSError, LockedFile) as error:
                skipped.append(path)
                log_error(f"Глава не попала в книгу: {path}", error)
        # строки целиком в [скобках] - это пометки, при сборке они вырезаются; если это на самом
        # деле заголовки («[ПРОЛОГ]»), они бы молча пропали из книги
        as_headings = False
        if options["strip_markers"]:
            found = [(name, line) for name, text in texts for line in marker_lines(text)]
            if found:
                shown = "\n".join(f"• {line}   ({name})" for name, line in found[:8])
                more = f"\n…и ещё {len(found) - 8}" if len(found) > 8 else ""
                choice = ask_choice(
                    self, "Собрать книгу",
                    "Эти строки целиком в квадратных скобках. Скобки - это пометки для себя, "
                    f"при сборке они вырезаются:\n\n{shown}{more}\n\nЕсли это заголовки, их можно "
                    "сделать заголовками. В тексте заголовок пишется так: «# Пролог».",
                    [("cancel", "Отмена"), ("cut", "Вырезать"), ("heading", "Сделать заголовками")])
                if choice in (None, "cancel"):
                    return
                as_headings = choice == "heading"
        chapters = [(name, book_paragraphs(text, options["strip_markers"], as_headings, folders.get(i)))
                    for i, (name, text) in enumerate(texts)]
        if options.get("category") and options.get("use_cover", True):
            from .covers import cover_bytes
            options["cover"] = cover_bytes(Path(options["category"]))   # своя картинка категории - обложкой
        # собираем во временный файл: если сборка сорвётся, прежняя книга останется целой
        temp = target.with_name(f".{target.name}.part")
        try:
            {"pdf": export_pdf, "docx": export_docx, "epub": export_epub, "fb2": export_fb2,
             "txt": export_txt}[options["format"]](
                temp, options["title"], options["author"], chapters, options)
            if not temp.exists() or temp.stat().st_size == 0:
                raise OSError("файл книги получился пустым")
            with open(temp, "rb+") as handle:
                os.fsync(handle.fileno())
            os.replace(temp, target)
        except Exception as error:
            temp.unlink(missing_ok=True)
            log_error("Книга не собрана", error)
            kept = " Прежний файл книги не тронут." if target.exists() else ""
            show_error(self, "Собрать книгу", f"Книга не собрана: {error}.{kept}")
            return
        words = sum(len(WORD_RE.findall(p)) for _, paragraphs in chapters for p in paragraphs)
        self.toast.show_message(f"Книга собрана: {target.name}, {words_label(words)}", 3500)
        if skipped:
            self._report("Книга собрана не полностью", "Эти главы не прочитались и в книгу не попали:",
                         skipped)

    def import_files(self):
        category = self.ask_category()
        if not category:
            return
        from .importers import DOCUMENT_READERS, TABLE_READERS
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Добавить файлы", str(Path.home()),
            "Тексты, книги и таблицы (*.txt *.md *.csv *.docx *.odt *.rtf *.fb2 *.epub *.html *.htm *.xlsx *.ods);;"
            "Все файлы (*)")
        added, skipped, odd = 0, [], []
        kinds = {".docx": "файл Word", ".odt": "файл LibreOffice", ".rtf": "RTF", ".fb2": "FB2", ".epub": "EPUB",
                 ".html": "веб-страница", ".htm": "веб-страница", ".xhtml": "веб-страница",
                 ".xlsx": "таблица Excel", ".ods": "таблица Calc"}
        for source in paths:
            source = Path(source)
            suffix = source.suffix.lower()
            if suffix in DOCUMENT_READERS or suffix in TABLE_READERS:
                try:
                    added += (self.import_tables if suffix in TABLE_READERS else self.import_document)(source, category)
                except ImportError:
                    skipped.append(f"{source.name} - для Word нужна python-docx, запусти install.sh ещё раз")
                except Exception as error:   # битый или не тот файл: сообщаем и идём дальше
                    log_error(f"Не получилось импортировать {source}", error)
                    skipped.append(f"{source.name} - не читается как {kinds.get(suffix, 'документ')} ({error})")
                continue
            if suffix == ".pdf":
                skipped.append(f"{source.name} - PDF не открывается: в нём нет абзацев, только буквы на "
                               "страницах. Открой его в читалке, скопируй текст и вставь - вставка сама "
                               "починит абзацы")
                continue
            target = unique_path(category / source.name)
            try:
                text, encoding, lossy = read_text_info(source)
                save_text(target, text)
            except LockedFile:
                skipped.append(f"{source.name} - зашифрован другим паролем")
                continue
            except OSError as error:
                skipped.append(f"{source.name} - {os_message(error)}")
                continue
            if lossy or encoding != "UTF-8":
                odd.append(f"{source.name} - {encoding}" + (", есть нераспознанные символы" if lossy else ""))
            append_to_order(category, target.name)
            added += 1
        if paths:
            self.refresh_tree()
            self.toast.show_message(f"Добавлено: {added}")
        if skipped or odd:
            parts = []
            if skipped:
                parts.append("Не добавлены:\n" + "\n".join("• " + x for x in skipped))
            if odd:
                parts.append("Переведены в UTF-8, проверь текст:\n" + "\n".join("• " + x for x in odd))
            show_warning(self, "Добавить файлы", "\n\n".join(parts))

    def on_item_clicked(self, item, _column=0):
        path = self.item_path(item)
        if path.is_dir():
            item.setExpanded(not item.isExpanded())
        else:
            self.open_path(path)

    def on_drop(self, src, dst, where):
        above = where == QAbstractItemView.DropIndicatorPosition.AboveItem
        if not src.exists():
            return
        if src.is_dir():
            # категории: только меняем порядок
            if dst.is_file():
                dst = dst.parent
            names = [c.name for c in self.categories() if c != src]
            index = names.index(dst.name) + (0 if above else 1) if dst.name in names else len(names)
            names.insert(index, src.name)
            save_order(C.ROOT, names)
            self.refresh_tree()
            return
        folder = dst if dst.is_dir() else dst.parent
        new = src
        if folder != src.parent:
            new = unique_path(folder / src.name)
            try:
                src.rename(new)
            except OSError as error:
                show_warning(self, "Перемещение", f"Не получилось переместить:\n{error}")
                return
            if not move_versions(src, new):
                report_problem(f"Версии «{src.stem}» остались под старым путём")
            if not move_notes(src, new):
                report_problem(f"Заметки на полях «{src.stem}» остались под старым путём")
            self._move_keys(src, new)
            save_order(src.parent, [n for n in load_order(src.parent) if n != src.name])
            if self.path == src:
                self.path = new
                self.update_title()
            if self.side.path == src:
                self.side.path = new
                self.settings.setValue("side_file", str(new))
        names = [f.name for f in files_in(folder) if f != new]
        if dst.is_file() and dst.name in names:
            index = names.index(dst.name) + (0 if above else 1)
        else:
            index = len(names)
        names.insert(index, new.name)
        save_order(folder, names)
        self.refresh_tree()

    def load_text(self, text):
        if getattr(self, "_reading", None) is not None:
            self.stop_reading()                 # голос читал прошлую главу - в новой ему нечего делать
        # запоминаем, сколько слов дописано в прошлом файле, до того как его заменить
        self.words = self.word_count()
        self.session_net += self.words - self.file_base_words
        self.view = None
        self.pages.setCurrentWidget(self.editor)
        self.editor.stop_scroll()
        self.highlighter.current = 0
        self.notes_margin.clear()
        with self.rehighlighter.detached(keep_place=False):   # большая глава: вёрстка один раз, в конце
            self.highlighter.paused = True    # иначе глава красится дважды целиком, а это секунды на большой
            self.editor.setPlainText(text)
            doc = self.editor.document()
            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.Document)
            block = QTextBlockFormat()
            block.setLineHeight(C.LINE_HEIGHT, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            cursor.mergeBlockFormat(block)
            doc.clearUndoRedoStacks()
            doc.setModified(False)
            self._rehighlight()
        self.editor.moveCursor(QTextCursor.Start)
        # база новой главы - до пересчёта: иначе на миг все её слова считались «написанными сегодня»,
        # серия дней росла, и огонёк выскакивал при каждом запуске и каждом переходе в главу
        self.words = self.file_base_words = self.word_count()
        self.count_words()
        self.update_status()

    def open_path(self, path):
        if path == self.path:
            return True
        if path.is_file() and not is_text_file(path):
            self.refuse_not_text(path)
            return False
        original = conflict_original(path)
        if original is not None and path.is_file():
            self.open_conflict(path, original)
            return False
        if not self.maybe_save():
            self.refresh_tree()
            return False
        self.keep_left_text()
        try:
            text, encoding, lossy = read_text_info(path)
        except LockedFile:
            show_warning(self, "Открыть", "Этот файл не расшифровывается: он зашифрован другим паролем "
                                          "или повреждён (например, оборвалась синхронизация). Предыдущие "
                                          "версии - в «Версиях файла», копии - в резервных копиях.")
            return False
        except OSError as error:
            show_error(self, "Открыть", f"Не получилось открыть файл:\n{os_message(error)}")
            return False
        broken = (is_board(path) or is_timeline(path)) and text.strip() and not _valid_json(text)
        if broken:
            snapshot(path, text)                  # испорченный файл - копией в версии, прежде чем что-то делать
        if lossy:
            keep_raw_copy(path)                   # байты как были: при сохранении нераспознанное станет �
        self.remember_position()
        if is_table(path):
            self.load_view(self.table_view, text)
        elif is_board(path):
            self.load_view(self.board_view, text)
        elif is_timeline(path):
            self.load_view(self.timeline_view, text)
        else:
            self.load_text(text)
        self.path = path
        self._own_stamp = self._stamp(path)
        self.update_empty_hint()
        if self.side.isVisible() and self.side.showing_version and self.side.path != path:
            self.close_side()                                      # версии другой главы здесь не к месту
        self.load_notes()
        self.watch_current()
        self.update_title()
        self.select_in_tree()
        if broken:
            show_warning(self, "Файл повреждён", f"«{path.stem}» не читается - похоже, файл испорчен "
                         "(оборвалась запись или синхронизация). Он открыт пустым, а то, что в нём было, "
                         "сохранено в «Версиях файла». Если ничего не менять, файл останется как есть.")
        if lossy:
            show_warning(self, "Кодировка", f"Часть символов в «{path.stem}» не распознана, "
                         "они показаны знаком �. Если сохранить, они так и останутся, но точная копия "
                         f"файла сохранена в {C.service_path('.versions')}. Лучше сначала проверь текст.")
        elif encoding not in ("UTF-8",):
            self.toast.show_message(f"Файл был в кодировке {encoding}: при сохранении станет UTF-8", 4000)
        if self.view:
            view = self.view
            fade(view, 0.0, 1.0, 260, lambda: view.setGraphicsEffect(None))
            view.focus_widget().setFocus()
        else:
            self.restore_position()
            self.fade_in_editor()
            self.editor.setFocus()
        return True

    def keep_left_text(self):
        """Текст главы, из которой уходишь, ложится в «Версии файла», если его там ещё нет.
        Автосохранение делает версии редко, и без этого программа синхронизации, вернув на диск
        старый файл с другого устройства, стёрла бы последние правки насовсем."""
        if self.path is None or not self.path.is_file():
            return
        if not self.is_modified():
            # на экране - то, что считаем записанным; если файл уже успели подменить снаружи,
            # а наблюдатель ещё не сказал, этот текст иначе пропал бы вместе с окном
            snapshot(self.path, self.current_text())
        try:
            snapshot(self.path, read_text(self.path))
        except (OSError, LockedFile):
            pass

    def _foreign_on_disk(self, text):
        """Перед записью: если файл с прошлого чтения поменял кто-то другой (наблюдатель ещё не
        успел сказать), его текст сначала уходит в версии, чтобы запись поверх ничего не стёрла."""
        if not self.path.is_file() or self._stamp(self.path) == getattr(self, "_own_stamp", None):
            return False
        try:
            theirs = read_text(self.path)
        except (OSError, LockedFile):
            return False
        if theirs == text:
            return False
        snapshot(self.path, theirs)
        return True

    def save(self, auto=False):
        """Ctrl+S и кнопка. auto=True - тихое автосохранение: без сообщения, а версия главы
        делается не чаще раза в 10 минут, чтобы история не забивалась мелкими шагами."""
        if self.path is None:
            return self.new_file(content=self.editor.toPlainText())
        text = self.current_text()
        foreign = self._foreign_on_disk(text)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)   # категорию удалили снаружи - заведём снова
            save_text(self.path, text)
        except OSError as error:
            if auto:
                raise
            show_error(self, "Сохранить", f"Не получилось сохранить:\n{error}")
            return False
        self.remember_own_write()
        self.watch_current()
        versions = self.__dict__.setdefault("_version_times", {})
        now = self.session.elapsed() / 1000
        if not auto or now - versions.get(self.path, -1e9) >= C.AUTOSAVE_VERSION_S:
            snapshot(self.path, text)
            versions[self.path] = now
        self.save_notes()
        self.refresh_side(self.path)
        self.set_modified(False)
        self.journal_saved()
        if self.path.parent.name in self.lore_cfg["categories"]:
            self.rebuild_lore()
        self.count_words()
        self.store_stats()
        if foreign:
            self.toast.show_message("Глава успела измениться на другом устройстве. Записана твоя версия, "
                                    "а та - в «Версиях файла»", 5000)
        elif not auto:
            self.toast.show_message("Сохранено")
        return True

    # ---------------- автосохранение ----------------
    def schedule_autosave(self):
        """Вызывается при каждом изменении текста."""
        if not C.AUTOSAVE:
            return
        if not self.autosave_age.isValid():
            self.autosave_age.start()
        if self.autosave_age.elapsed() >= C.AUTOSAVE_MAX_S * 1000:
            self.autosave()                      # печатаешь без пауз - сохраняем по дороге
        else:
            self.autosave_timer.start()

    def autosave(self):
        self.autosave_timer.stop()
        self.autosave_age.invalidate()
        if not C.AUTOSAVE or not self.is_modified() or getattr(self, "_closed", False):
            return
        try:
            if self.path is None:
                if self.editor.toPlainText().strip():
                    self.save_everything()       # новый текст сам ляжет в «Черновики» как «Глава N»
                return
            self.save(auto=True)
        except OSError as error:
            log_error("Автосохранение не удалось", error)
            self.toast.show_message(f"Автосохранение не удалось: {os_message(error)}. Сохрани вручную", 4000)

    def maybe_save(self):
        if not self.is_modified():
            return True
        if C.AUTOSAVE:
            # автосохранение включено - при переходе в другую главу, категорию и при закрытии окна
            # просто сохраняем, без вопроса (раньше вопрос то был, то нет: смотря, успело ли
            # автосохранение сработать за 3 секунды после последней буквы)
            self.autosave()
            if not self.is_modified():
                return True
        answer = ask_question(
            self, "Несохранённый текст", "Сохранить изменения?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save()
        return answer == QMessageBox.Discard

    def copy_all(self):
        if self.view:
            text, message = self.view.copy_text()
            QApplication.clipboard().setText(text)
            self.toast.show_message(message)
            return
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.toast.show_message("Весь текст скопирован")

    def show_versions(self, path=None):
        if self.editor.forward_only:
            self.toast.show_message("В режиме «только вперёд» версии не возвращаются")
            return
        path = path or self.path
        if path is None:
            self.toast.show_message("Сначала открой файл")
            return
        versions = list_versions(path)
        if not versions:
            self.toast.show_message("Версий пока нет: они появляются при сохранении", 3000)
            if hasattr(self, "picture_pop"):
                self.picture_pop.play("empty-versions", 3000, width=260)
            return
        if not self.open_path(path):
            return
        if not self.maybe_save():
            return
        versions = list_versions(path)
        dialog = VersionsDialog(self, path, versions, self.editor.font(), self.current_text())
        accepted = dialog.exec() and dialog.chosen is not None
        if dialog.beside_index is not None and dialog.beside_index in versions:
            self.compare_with_version(versions.index(dialog.beside_index))
            return
        if accepted and self.view:
            self.view.load(dialog.chosen)
            self.view.set_modified(True)
            self.toast.show_message("Версия возвращена. Сохрани, если всё так")
        elif accepted:
            # одним действием, чтобы Ctrl+Z вернул всё обратно
            notes = self.notes_margin.data()
            cursor = self.editor.textCursor()
            cursor.beginEditBlock()
            cursor.select(QTextCursor.Document)
            cursor.insertText(dialog.chosen)
            cursor.endEditBlock()
            self.notes_margin.load(notes)
            self.editor.moveCursor(QTextCursor.Start)
            self.toast.show_message("Версия возвращена. Сохрани, если всё так")

    def tree_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        path = self.item_path(item)
        menu = rounded_menu(self)
        if path.is_dir():
            self.tree.setCurrentItem(item)
            menu.addAction("Новый файл здесь", self.new_file)
            menu.addAction("Новая таблица здесь", self.new_table)
            menu.addAction("Новая доска здесь", self.new_board)
            menu.addAction("Новая хронология здесь", self.new_timeline)
            menu.addSeparator()
            is_lore = path.name in self.lore_cfg["categories"]
            menu.addAction("Больше не справочник мира" if is_lore else "Сделать справочником мира",
                           lambda: self.toggle_lore_category(path))
            menu.addAction("Обложка…", lambda: self.show_cover(path))
            menu.addAction("Заготовки для мира…", lambda: self.make_world_kit(path))
            menu.addSeparator()
        else:
            menu.addAction("Открыть рядом" + self.hk("side"), lambda: self.open_beside(path))
            menu.addAction("Версии…", lambda: self.show_versions(path))
            menu.addAction("Цель главы…", lambda: self.set_chapter_goal(path))
            if is_prose(path) and path.parent.name not in self.lore_cfg["categories"]:
                menu.addSeparator()
                self.plan_menu(menu, path)
                menu.addSeparator()
            if path.parent.name in self.lore_cfg["categories"] and path.suffix == ".txt":
                menu.addAction("Сохранить как шаблон…", lambda: self.save_as_template(path))
        menu.addAction("Переименовать", lambda: self.rename(path))
        menu.addAction("Удалить в корзину", lambda: self.delete(path))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _affects_current(self, path):
        return self.path is not None and (self.path == path or path in self.path.parents)

    def show_trash(self):
        TrashDialog(self, self._restored).exec()

    def _restored(self, target):
        self.refresh_tree()
        self.toast.show_message(f"Вернулось: «{target.stem if target.is_file() else target.name}»")
        if target.is_file():
            self.open_path(target)

    def rename(self, path):
        default = path.stem if path.suffix in (".txt", ".csv", ".board") else path.name
        name = self.ask_name("Переименовать", "Новое название:", default)
        if not name:
            return
        if path.is_file() and Path(name).suffix.lower() != path.suffix.lower():
            name += path.suffix                  # тип файла не меняется: глава останется главой, доска - доской
        target = path.with_name(name)
        if target == path:
            return
        try:
            if name_clash(target, source=path):
                show_warning(self, "Переименовать", "Такое название уже занято.")
                return
            path.rename(target)
        except OSError as error:
            show_error(self, "Переименовать", f"Не переименовано. {os_message(error)}")
            return
        self._move_keys(path, target)
        if target.is_dir():
            moved = move_tree(C.service_path(".versions") / path.name, C.service_path(".versions") / target.name)
            if not move_tree(C.service_path(".notes") / path.name, C.service_path(".notes") / target.name):
                report_problem(f"Заметки на полях категории «{path.name}» остались под старым именем")
            rename_in_order(C.ROOT, path.name, target.name)
            from .covers import move_cover
            move_cover(path, target)
            if path.name in self.lore_cfg["categories"]:
                categories = self.lore_cfg["categories"]
                categories[categories.index(path.name)] = target.name
                save_lore_config(self.lore_cfg)
        else:
            moved = move_versions(path, target)
            if not move_notes(path, target):
                report_problem(f"Заметки на полях «{path.stem}» остались под старым именем")
            rename_in_order(path.parent, path.name, target.name)
        if not moved:
            show_warning(self, "История версий",
                         f"Переименовано, но старые версии не переехали и лежат под прежним именем "
                         f"в папке {C.service_path('.versions')}. Подробности в {C.ERROR_LOG}.")
        if self._affects_current(path):
            self.path = target if self.path == path else target / self.path.relative_to(path)
            self.update_title()
        side = self.side.path
        if side is not None and (side == path or path in side.parents):
            self.side.path = target if side == path else target / side.relative_to(path)
            self.settings.setValue("side_file", str(self.side.path))
            self.refresh_side()
        self.refresh_tree()

    def delete(self, path):
        what = "категорию со всеми файлами" if path.is_dir() else "файл"
        answer = ask_question(self, "Удалить", f"Отправить {what} «{path.name}» в корзину?\n"
                                               f"Там он пролежит {TRASH_DAYS} дней, и его можно вернуть.")
        if answer != QMessageBox.Yes:
            return
        if self._affects_current(path) and self.is_modified():
            self.save()                         # в корзину - с последними правками
        try:
            entry = move_to_trash(path)
        except OSError as error:
            show_warning(self, "Удалить", f"Не получилось отправить в корзину: {os_message(error)}")
            return
        self.toast.show_message(f"«{path.stem if path.is_file() else path.name}» в корзине. Нажми сюда - вернуть",
                                5000, action=lambda e=entry: self._restored(restore_from_trash(e)))
        if self._affects_current(path):
            self.path = None
            self.load_text("")
            self.update_title()
        self.refresh_side()
        self.refresh_tree()
