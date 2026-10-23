# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Защита от потери текста:
- ошибка внутри программы не закрывает окно: всё сохраняется, ошибка пишется в журнал;
- набранное каждые несколько секунд пишется в запасной файл - после сбоя его можно вернуть;
- если за раз стёрто много текста, остаётся версия «до» и кнопка «вернуть»;
- второй запуск не открывает второе окно на те же файлы."""

import faulthandler
import json
import sys
import traceback
from datetime import datetime

from PySide6.QtCore import QLockFile, QTimer

from . import config as C
from .storage import LockedFile, log_error, read_text, save_text, snapshot
from .textutil import WORD_RE, plural

ERASE_WORDS = 150            # стёрто за раз больше - это повод подстраховать
JOURNAL_SECONDS = 5


def recovery_dir():
    return C.DATA_DIR / "recovery"


def journal_path():
    return recovery_dir() / "journal"


def session_marker():
    return C.DATA_DIR / "session.open"


# ---------------- обрывки записи ----------------
def clean_temp_files(older_than=120):
    """Временные «.имя.tmp», оставшиеся от записи, которую оборвал сбой. Сам файл при этом цел:
    запись атомарная, подмена происходит в самом конце. Возвращает, сколько убрано."""
    import time
    removed = 0
    now = time.time()
    try:
        candidates = list(C.ROOT.rglob(".*.tmp"))
    except OSError:
        return 0
    for path in candidates:
        try:
            if path.is_file() and now - path.stat().st_mtime > older_than:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


# ---------------- один запуск ----------------
def single_instance():
    """Замок «блокнот уже открыт». None - если уже открыт другим окном."""
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(C.DATA_DIR / "running.lock"))
    lock.setStaleLockTime(0)              # замок от упавшего запуска Qt снимет сам (процесса уже нет)
    if not lock.tryLock(300):
        return None
    return lock


# ---------------- аварийный выход ----------------
def crashed_last_time():
    """Прошлый запуск закрылся не сам (свет, сбой системы, падение)."""
    return session_marker().exists()


def mark_session(open_now):
    try:
        if open_now:
            session_marker().parent.mkdir(parents=True, exist_ok=True)
            session_marker().write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
        else:
            session_marker().unlink(missing_ok=True)
    except OSError:
        pass


_fault_file = None


def enable_fault_log():
    """Если упадёт сама Qt или Python, в журнал попадёт, где именно."""
    global _fault_file
    try:
        C.DATA_DIR.mkdir(parents=True, exist_ok=True)
        _fault_file = open(C.DATA_DIR / "crash.log", "a", encoding="utf-8")
        faulthandler.enable(_fault_file)
    except (OSError, RuntimeError):
        _fault_file = None


def install_crash_guard(window_getter):
    """Любая необработанная ошибка: сохранить всё, записать в журнал, сказать - и работать дальше."""
    state = {"busy": False, "shown": 0}

    def guard(kind, value, tb):
        if issubclass(kind, KeyboardInterrupt):
            sys.__excepthook__(kind, value, tb)
            return
        log_error("Внутренняя ошибка:\n" + "".join(traceback.format_exception(kind, value, tb)))
        if state["busy"]:
            return                               # ошибка в самом спасении - не зацикливаемся
        state["busy"] = True
        try:
            window = window_getter()
            saved = False
            if window is not None:
                try:
                    window.write_journal(force=True)
                    saved = window.save_everything()
                except Exception as error:      # noqa: BLE001 - спасаем, что можно
                    log_error("Аварийное сохранение не удалось", error)
                if state["shown"] < 3:          # не засыпать сообщениями, если ошибка повторяется
                    state["shown"] += 1
                    note = "текст сохранён" if saved else "набранное в запасном файле"
                    window.toast.show_message(f"Что-то пошло не так внутри блокнота - {note}. "
                                              f"Подробности в {C.ERROR_LOG.name}", 5000)
        finally:
            state["busy"] = False

    sys.excepthook = guard
    return guard


# ---------------- запасной файл набранного ----------------
def write_journal(path, text):
    """Набранное в главе, которое ещё не сохранено. Шифруется, если стоит пароль."""
    data = json.dumps({"path": str(path) if path else "", "time": datetime.now().isoformat(timespec="seconds"),
                       "text": text}, ensure_ascii=False)
    recovery_dir().mkdir(parents=True, exist_ok=True)
    save_text(journal_path(), data)


def read_journal():
    """{"path", "time", "text"} или None."""
    try:
        data = json.loads(read_text(journal_path()))
    except (OSError, LockedFile, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        return None
    return data


def clear_journal():
    try:
        journal_path().unlink(missing_ok=True)
    except OSError:
        pass


def word_count(text):
    return len(WORD_RE.findall(text))


class SafetyMixin:
    """Запасной файл, аварийное сохранение, страховка от стирания. Часть главного окна."""

    def init_safety(self):
        self._journal_text = None
        self.journal_timer = QTimer(self, interval=JOURNAL_SECONDS * 1000)
        self.journal_timer.timeout.connect(self.write_journal)
        self.journal_timer.start()
        self.editor.big_erase_callback = self._big_erase
        self.last_erase = None

    def write_journal(self, force=False):
        """Каждые несколько секунд: если глава не сохранена - пишем её в запасной файл."""
        if getattr(self, "_closed", False):
            return
        if self.view is not None or not self.is_modified():
            if self._journal_text is not None:
                clear_journal()
                self._journal_text = None
            return
        text = self.editor.toPlainText()
        if not force and text == self._journal_text:
            return
        try:
            write_journal(self.path, text)
            self._journal_text = text
        except OSError as error:
            log_error("Запасной файл не записался", error)

    def journal_saved(self):
        """Глава сохранена - запасной файл больше не нужен."""
        if getattr(self, "_journal_text", None) is not None or journal_path().exists():
            clear_journal()
            self._journal_text = None

    def offer_recovery(self, ask):
        """После сбоя: вернуть набранное, что не успело сохраниться. ask(текст) -> True/False."""
        data = read_journal()
        if data is None:
            return False
        from pathlib import Path
        path = Path(data["path"]) if data["path"] else None
        text = data["text"]
        on_disk = None
        if path is not None:
            try:
                on_disk = read_text(path)
            except (OSError, LockedFile):
                on_disk = None
        if on_disk is not None and on_disk == text or not text.strip():
            clear_journal()
            return False
        name = f"«{path.stem}»" if path else "новый текст без названия"
        when = data.get("time", "")[:16].replace("T", " в ")
        words = word_count(text)
        newer = ""
        if on_disk is not None:                    # главу могли поменять после сбоя - например, на телефоне
            from datetime import datetime
            try:
                changed = datetime.fromtimestamp(path.stat().st_mtime)
                if changed > datetime.fromisoformat(data.get("time", "")):
                    newer = (f"\n\nОсторожно: глава на диске новее запасного файла - её меняли "
                             f"{changed:%d.%m в %H:%M} (может, на телефоне). Если вернуть, в главе будет "
                             "старый набранный текст, а новый - только в «Версиях файла».")
            except (OSError, ValueError):
                newer = ""
        if not ask(f"Прошлый раз блокнот закрылся, не успев сохранить {name} ({when}).\n\n"
                   f"В запасном файле {words} {plural(words, 'слово', 'слова', 'слов')}. Вернуть их?\n\n"
                   "Сейчас ничего не перезапишется: текст откроется в главе, а сохранишь ты сам. "
                   "То, что было на диске, останется в «Версиях файла»." + newer):
            clear_journal()
            return False
        if path is not None and path.is_file():
            if on_disk is not None:
                snapshot(path, on_disk)
            if not self.open_path(path):
                return False
        else:
            self.path = None
            self.load_text("")
            self.update_title()
        cursor = self.editor.textCursor()
        cursor.select(cursor.SelectionType.Document)
        cursor.insertText(text)                     # одной правкой: Ctrl+Z вернёт то, что было на диске
        self.set_modified(True)
        self.toast.show_message("Набранное вернулось. Сохрани, если всё на месте", 4000)
        return True

    # ---- стёрли много за раз ----
    def _big_erase(self, before):
        after = self.editor.toPlainText()
        lost = word_count(before) - word_count(after)
        if lost < ERASE_WORDS:
            return
        if self.path is not None:
            snapshot(self.path, before)             # версия «до» - даже если плашку не заметят
        self.last_erase = before
        self.toast.show_message(f"Стёрто {lost} {plural(lost, 'слово', 'слова', 'слов')}. Нажми сюда - вернуть",
                                7000, action=self.undo_big_erase)

    def undo_big_erase(self):
        if self.last_erase is None:
            return
        cursor = self.editor.textCursor()
        cursor.select(cursor.SelectionType.Document)
        cursor.insertText(self.last_erase)
        self.last_erase = None
        self.toast.show_message("Вернул")

