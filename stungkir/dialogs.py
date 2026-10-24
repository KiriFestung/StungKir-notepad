# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Окна-карточки: вопросы, пароль, заметка на полях, горячие клавиши."""

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QVBoxLayout,
)

from . import config as C
from .storage import LockBroken, lock_path
from .style import translucency_ok


# ---------------- окна в стиле программы ----------------
class Sheet(QDialog):
    """Скруглённое тёмное окно без системной рамки. Таскается мышкой за любое пустое место."""

    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self.setObjectName("Sheet")
        self.setWindowTitle(title or C.APP_NAME)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        outer = QVBoxLayout(self)
        self._sheet_card = QFrame()
        self._sheet_card.setObjectName("DialogCard")
        self.flat = not translucency_ok()
        if self.flat:
            # без композитора прозрачная тень рисуется чёрной рамкой: тогда просто прямоугольник
            outer.setContentsMargins(0, 0, 0, 0)
            self._sheet_card.setProperty("flat", True)
        else:
            self.setAttribute(Qt.WA_TranslucentBackground)
            outer.setContentsMargins(18, 14, 18, 22)
            shadow = QGraphicsDropShadowEffect(self._sheet_card)
            shadow.setBlurRadius(28)
            shadow.setOffset(0, 6)
            shadow.setColor(QColor(0, 0, 0, 150))
            self._sheet_card.setGraphicsEffect(shadow)
        outer.addWidget(self._sheet_card)
        inner = QVBoxLayout(self._sheet_card)
        inner.setContentsMargins(20, 12, 14, 18)
        inner.setSpacing(10)
        head = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setObjectName("DialogTitle")
        head.addWidget(self.title_label, 1)
        close = QPushButton("✕")
        close.setObjectName("DialogClose")
        close.setCursor(Qt.PointingHandCursor)
        close.setAutoDefault(False)
        close.clicked.connect(self.reject)
        head.addWidget(close)
        inner.addLayout(head)
        self.content = QVBoxLayout()
        self.content.setContentsMargins(0, 0, 6, 0)
        self.content.setSpacing(10)
        inner.addLayout(self.content, 1)
        self._drag = None

    def exec(self):
        """После закрытия окно удаляется, как только программа вернётся к обычной работе:
        результат читается сразу после exec, а копить старые окна незачем (их пришлось бы
        перекрашивать при каждой смене темы)."""
        result = super().exec()
        QTimer.singleShot(0, self.deleteLater)
        return result

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _event):
        self._drag = None

    def showEvent(self, event):
        super().showEvent(event)
        from .icons import decorate
        decorate(self)                             # значки кнопкам по надписям
        anchor = self.parentWidget().window() if self.parentWidget() else None
        area = anchor.frameGeometry() if anchor else QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        layout = self.layout()
        if layout is not None and layout.hasHeightForWidth():
            # длинный текст с переносами: высота по настоящей ширине, иначе строки обрезаются
            need = layout.totalHeightForWidth(self.width())
            if need > self.height():
                self.resize(self.width(), min(need, int(area.height() * 0.95)))
        self.move(area.center() - self.rect().center())
        self.setWindowOpacity(0.0)
        self._appear = QPropertyAnimation(self, b"windowOpacity", self)
        self._appear.setDuration(150)
        self._appear.setStartValue(0.0)
        self._appear.setEndValue(1.0)
        self._appear.start()


class AskDialog(Sheet):
    """Вопрос с кнопками и, если нужно, полем для ответа."""

    def __init__(self, parent, title, text, buttons, field=None):
        super().__init__(parent, title)
        self.setMinimumWidth(460)
        self.result_key = None
        if text:
            label = QLabel(text)
            label.setWordWrap(True)
            self.content.addWidget(label)
        self.field = None
        if field:
            kind = field[0]
            if kind == "text":
                self.field = QLineEdit(field[1])
                self.field.selectAll()
            elif kind == "int":
                self.field = QSpinBox()
                self.field.setRange(field[2], field[3])
                self.field.setSingleStep(field[4])
                self.field.setValue(field[1])
            else:
                self.field = QComboBox()
                self.field.addItems(field[1])
                self.field.setCurrentIndex(field[2])
            self.content.addWidget(self.field)
        row = QHBoxLayout()
        row.addStretch()
        focus = None
        for key, label, is_default in buttons:
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setAutoDefault(is_default)
            if is_default:
                button.setDefault(True)
                button.setObjectName("Primary")
                focus = button
            button.clicked.connect(lambda _c=False, k=key: self._choose(k))
            row.addWidget(button)
        self.content.addLayout(row)
        (self.field or focus or self).setFocus()

    def _choose(self, key):
        self.result_key = key
        self.accept()


BUTTON_LABELS = {QMessageBox.Save: "Сохранить", QMessageBox.Discard: "Не сохранять",
                 QMessageBox.Cancel: "Отмена", QMessageBox.Yes: "Да", QMessageBox.No: "Нет"}
BUTTON_ORDER = [QMessageBox.Discard, QMessageBox.No, QMessageBox.Cancel, QMessageBox.Yes, QMessageBox.Save]


def ask_question(parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No, default=None):
    present = [b for b in BUTTON_ORDER if buttons & b]
    if default is None:
        default = QMessageBox.Save if QMessageBox.Save in present else (
            QMessageBox.Yes if QMessageBox.Yes in present else present[-1])
    dialog = AskDialog(parent, title, text, [(b, BUTTON_LABELS[b], b == default) for b in present])
    dialog.exec()
    if dialog.result_key is None:   # закрыли крестиком или Esc
        for fallback in (QMessageBox.Cancel, QMessageBox.No):
            if fallback in present:
                return fallback
        return present[0]
    return dialog.result_key


def show_warning(parent, title, text):
    AskDialog(parent, title, text, [("ok", "Понятно", True)]).exec()


show_error = show_warning


def ask_choice(parent, title, text, choices):
    """choices: [(ключ, надпись)], последний - основной. Возвращает ключ или None."""
    buttons = [(key, label, i == len(choices) - 1) for i, (key, label) in enumerate(choices)]
    dialog = AskDialog(parent, title, text, buttons)
    dialog.exec()
    return dialog.result_key


def _ask_field(parent, title, label, field):
    dialog = AskDialog(parent, title, label, [("cancel", "Отмена", False), ("ok", "Готово", True)], field)
    dialog.exec()
    return dialog, dialog.result_key == "ok"


def ask_text(parent, title, label, text=""):
    dialog, ok = _ask_field(parent, title, label, ("text", text))
    return dialog.field.text(), ok


def ask_int(parent, title, label, value=0, minimum=0, maximum=100, step=1):
    dialog, ok = _ask_field(parent, title, label, ("int", value, minimum, maximum, step))
    return dialog.field.value(), ok


def ask_item(parent, title, label, items, current=0, editable=False):
    dialog, ok = _ask_field(parent, title, label, ("item", list(items), current))
    return dialog.field.currentText(), ok


class NoteDialog(Sheet):
    """Окно одной заметки на полях."""

    def __init__(self, parent, text="", existing=False, paragraph=""):
        super().__init__(parent, "Заметка на полях")
        self.setMinimumWidth(460)
        self.action = None
        if paragraph.strip():
            quote = paragraph.strip()
            quote = quote if len(quote) <= 90 else quote[:90].rstrip() + "…"
            label = QLabel(f"К абзацу: {quote}")
            label.setObjectName("Status")
            label.setWordWrap(True)
            self.content.addWidget(label)
        self.field = QPlainTextEdit(text)
        self.field.setPlaceholderText("Мысль, вопрос к себе, что проверить… В книгу не попадает.")
        self.field.setMinimumHeight(130)
        self.content.addWidget(self.field)
        row = QHBoxLayout()
        if existing:
            remove = QPushButton("Удалить")
            remove.setAutoDefault(False)
            remove.clicked.connect(lambda: self._finish("delete"))
            row.addWidget(remove)
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Готово")
        ok.clicked.connect(lambda: self._finish("save"))
        row.addWidget(cancel)
        row.addWidget(ok)
        self.content.addLayout(row)
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(lambda: self._finish("save"))
        self.field.setFocus()
        cursor = self.field.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.field.setTextCursor(cursor)

    def text(self):
        return self.field.toPlainText().strip()

    def _finish(self, action):
        self.action = action
        self.accept()


# горячие клавиши, которые можно поменять: (код, клавиши по умолчанию, что делает)
KEY_ACTIONS = [
    ("save", "Ctrl+S", "сохранить"), ("new", "Ctrl+N", "новая глава"), ("find", "Ctrl+F", "поиск в главе"),
    ("find_all", "Ctrl+Shift+F", "поиск по всем файлам"), ("replace", "Ctrl+H", "найти и заменить во всех главах"),
    ("copy_all", "Ctrl+Shift+C", "копировать всё"), ("italic", "Ctrl+I", "курсив"), ("bold", "Ctrl+B", "жирный"),
    ("dash", "Alt+-", "тире «—»"), ("ellipsis", "Alt+.", "многоточие"), ("quotes", "Alt+9", "кавычки «»"),
    ("forward", "F6", "только вперёд"), ("marker", "F7", "пометка [ ]"), ("focus", "F8", "режим фокуса"),
    ("typewriter", "F9", "печатная машинка"), ("zen", "F10", "без отвлечений: только текст"),
    ("fullscreen", "F11", "во весь экран"), ("zoom_in", "Ctrl+=", "шрифт крупнее"), ("zoom_out", "Ctrl+-", "шрифт мельче"),
    ("settings", "Ctrl+,", "настройки"), ("note", "Ctrl+M", "заметка на полях к абзацу (или двойной клик по полю)"),
    ("lines", "Ctrl+L", "номера строк слева от текста"),
    ("plan", "Ctrl+P", "план книги: статусы глав, о чём они и сколько слов"),
    ("side", "F4", "панель рядом: глава или справочник для чтения"),
    ("read", "F5", "читать главу вслух с места курсора - можно править, пока читает"),
    ("antistress", "F12", "антистресс: пупырка, мячик, спиннер, песок, тумблеры"),
    ("compare", "Ctrl+Shift+V", "сравнить с прошлой версией - рядом с текстом"),
    ("preview", "Ctrl+Shift+P", "как увидит читатель: книга A5, телефон, читалка"),
    ("help", "F1", "горячие клавиши"),
]
# не клавиши, а приёмы - их не поменять
KEY_TRICKS = [("# в начале строки", "заголовок внутри главы: «# Пролог»"),
              ("Ctrl+колесо", "размер шрифта"), ("Ctrl+клик по имени", "открыть заметку из справочника мира")]
# то, что забирает себе система: такие клавиши блокноту не достанутся
SYSTEM_KEYS = {"Alt+Tab", "Alt+F4", "Ctrl+Alt+Del", "Ctrl+Alt+Delete", "Meta+L", "Meta+D", "Meta+E", "Meta+Tab",
               "Ctrl+Alt+T", "Ctrl+Esc", "Alt+Space", "Print"}
DEFAULT_KEYS = {code: keys for code, keys, _what in KEY_ACTIONS}


def hotkey_map(saved):
    """{код: клавиши}: свои поверх стандартных (saved - JSON из настроек или словарь)."""
    import json
    keys = dict(DEFAULT_KEYS)
    try:
        own = json.loads(saved) if isinstance(saved, str) and saved else (saved or {})
    except ValueError:
        own = {}
    for code, value in (own.items() if isinstance(own, dict) else []):
        if code in keys and isinstance(value, str):
            keys[code] = value
    return keys


def hotkey_problems(keys):
    """Что не так со списком клавиш: одна клавиша на два дела, системная клавиша. [] - всё хорошо."""
    names = {code: what for code, _default, what in KEY_ACTIONS}
    problems, seen = [], {}
    for code, value in keys.items():
        if not value:
            continue
        normal = QKeySequence(value).toString()
        if normal in SYSTEM_KEYS:
            problems.append(f"{normal} забирает себе система - для «{names[code]}» выбери другую")
        if normal in seen:
            problems.append(f"{normal} - и «{names[seen[normal]]}», и «{names[code]}»")
        seen[normal] = code
    return problems


class HotkeysDialog(Sheet):
    """Горячие клавиши: посмотреть и поменять. Щёлкни по клавишам и нажми новое сочетание."""

    def __init__(self, parent, keys=None):
        from PySide6.QtWidgets import QKeySequenceEdit, QScrollArea, QWidget
        super().__init__(parent, "Горячие клавиши")
        self.setMinimumSize(620, 560)
        self.keys = dict(keys or DEFAULT_KEYS)
        hint = QLabel("Щёлкни по клавишам и нажми новое сочетание. Пустое - без клавиши.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(4)
        self.edits = {}
        for row, (code, _default, what) in enumerate(KEY_ACTIONS):
            edit = QKeySequenceEdit(QKeySequence(self.keys.get(code, "")))
            edit.setMaximumSequenceLength(1)
            edit.setFixedWidth(170)
            edit.keySequenceChanged.connect(self._check)
            self.edits[code] = edit
            grid.addWidget(edit, row, 0)
            grid.addWidget(QLabel(what), row, 1)
        for row, (keys_text, what) in enumerate(KEY_TRICKS, len(KEY_ACTIONS)):
            key = QLabel(keys_text)
            key.setObjectName("Section")
            grid.addWidget(key, row, 0)
            grid.addWidget(QLabel(what), row, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(holder)
        self.content.addWidget(scroll, 1)
        tip = QLabel("Подвести мышь к левому краю окна - файлы, к правому - знаки, таймер и кубики.")
        tip.setObjectName("Status")
        tip.setWordWrap(True)
        self.content.addWidget(tip)
        self.problem = QLabel("")
        self.problem.setWordWrap(True)
        self.problem.setStyleSheet(f"color: {C.SPELL};")
        self.content.addWidget(self.problem)
        row = QHBoxLayout()
        reset = QPushButton("Вернуть как было")
        reset.clicked.connect(self.reset)
        row.addWidget(reset)
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        self.ok = QPushButton("Сохранить")
        self.ok.setObjectName("Primary")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(self.ok)
        self.content.addLayout(row)

    def values(self):
        return {code: edit.keySequence().toString() for code, edit in self.edits.items()}

    def _check(self, *_args):
        problems = hotkey_problems(self.values())
        self.problem.setText("\n".join(problems))
        self.ok.setEnabled(not problems)
        return problems

    def reset(self):
        for code, edit in self.edits.items():
            edit.setKeySequence(QKeySequence(DEFAULT_KEYS[code]))
        self._check()

    def accept(self):
        if self._check():
            return
        super().accept()


def password_delay(failures):
    """Сколько секунд ждать после стольких неверных паролей подряд: три попытки сразу,
    дальше 2, 4, 8… секунд, но не больше минуты."""
    return 0 if failures < 3 else min(60, 2 ** (failures - 2))


class PasswordDialog(Sheet):
    """Ввод пароля: для входа (check) или новый пароль с повтором (confirm).
    Неверные пароли подряд запоминаются (и между запусками): перебирать их руками становится долго."""

    def __init__(self, parent, title, text, confirm=False, check=None, recover=None):
        super().__init__(parent, title)
        self.setMinimumWidth(420)
        self.confirm = confirm
        self.check = check
        self.recover = recover        # окно -> вошли ли по коду восстановления
        self.recovered = False
        self.password = None
        layout = self.content
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.first = QLineEdit()
        self.first.setEchoMode(QLineEdit.Password)
        self.first.setPlaceholderText("Пароль")
        layout.addWidget(self.first)
        self.second = QLineEdit()
        self.second.setEchoMode(QLineEdit.Password)
        self.second.setPlaceholderText("Ещё раз")
        self.second.setVisible(confirm)
        layout.addWidget(self.second)
        self.error = QLabel("")
        self.error.setObjectName("Error")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Готово")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        self.ok_button = ok
        self.forgot = QPushButton("Забыл пароль? Войти по коду")
        self.forgot.setObjectName("Link")
        self.forgot.setAutoDefault(False)
        self.forgot.clicked.connect(self._recover)
        self.forgot.setVisible(False)
        layout.insertWidget(layout.indexOf(self.error) + 1, self.forgot, 0, Qt.AlignLeft)
        row.addWidget(cancel)
        row.addWidget(ok)
        layout.addLayout(row)
        self.first.setFocus()
        self.tick = QTimer(self, interval=250)
        self.tick.timeout.connect(self._countdown)
        if self.check and not self.confirm:
            self._countdown()

    # ---- неверные пароли: растущая пауза ----
    @staticmethod
    def _state():
        from PySide6.QtCore import QSettings
        settings = QSettings(C.APP_ID, C.APP_ID)
        try:
            failures = int(settings.value("password_failures", 0))
            until = float(settings.value("password_wait_until", 0))
        except (TypeError, ValueError):
            failures, until = 0, 0.0
        return settings, failures, until

    def _wait_left(self):
        import time
        _settings, _failures, until = self._state()
        left = until - time.time()
        return 0 if left <= 0 or left > 120 else int(left + 0.999)   # часы перевели - не держим вечно

    def _show_forgot(self):
        """Вход по коду восстановления: ссылка видна сразу, если окно его поддерживает."""
        if self.recover is not None and not self.forgot.isVisibleTo(self):
            self.forgot.setVisible(True)
            self.adjustSize()

    def _recover(self):
        if self.recover(self):
            self.recovered = True
            self._succeeded()
            super().accept()

    def _countdown(self):
        self._show_forgot()
        left = self._wait_left()
        self.first.setEnabled(not left)
        self.ok_button.setEnabled(not left)
        if left:
            wrapped = self.error.text().startswith("Неверный пароль. Следующая")
            self.error.setText(f"Неверный пароль. Следующая попытка через {left} с")
            if not wrapped:
                self.adjustSize()
            if not self.tick.isActive():
                self.tick.start()
        else:
            self.tick.stop()
            if self.error.text().startswith("Неверный пароль. Следующая"):
                self.error.setText("Неверный пароль")
            self.first.setFocus()

    def _failed(self):
        import time
        settings, failures, _until = self._state()
        failures += 1
        settings.setValue("password_failures", failures)
        settings.setValue("password_wait_until", time.time() + password_delay(failures))
        settings.sync()
        self._countdown()

    def _succeeded(self):
        settings, _failures, _until = self._state()
        settings.remove("password_failures")
        settings.remove("password_wait_until")

    def accept(self):
        password = self.first.text()
        if not password:
            self.error.setText("Введи пароль")
            return
        if self.confirm and len(password) < 6:
            self.error.setText("Нужно хотя бы 6 символов")
            return
        if self.confirm and password != self.second.text():
            self.error.setText("Пароли не совпадают")
            return
        if self.check and self._wait_left():
            self._countdown()
            return
        try:
            accepted = self.check(password) if self.check else True
        except LockBroken:
            self.error.setText(f"Файл ключа повреждён ({lock_path().name}). Возьми его из резервной копии.")
            return
        if not accepted:
            self.error.setText("Неверный пароль")
            self.first.clear()
            if self.check:
                self._failed()
            return
        if self.check:
            self._succeeded()
        self.password = password
        super().accept()


class RecoveryCodeDialog(Sheet):
    """Показывает код восстановления один раз. Дальше - только с галочкой «записал»."""

    def __init__(self, parent, code, intro=""):
        super().__init__(parent, "Код восстановления")
        self.setMinimumWidth(520)
        text = QLabel((intro + "\n\n" if intro else "") +
                      "Если забудешь пароль, этим кодом можно будет войти и поставить новый. "
                      "Запиши его на бумагу или в менеджер паролей - больше он нигде не покажется. "
                      "Не храни его в папке StungKir: кто найдёт код, тот откроет тексты.")
        text.setWordWrap(True)
        self.content.addWidget(text)
        shown = QLabel(code)
        shown.setObjectName("Code")
        shown.setAlignment(Qt.AlignCenter)
        shown.setTextInteractionFlags(Qt.TextSelectableByMouse)
        font = shown.font()
        font.setFamily("DejaVu Sans Mono")
        font.setPointSize(18)
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 2)
        shown.setFont(font)
        self.content.addWidget(shown)
        self.written = QCheckBox("Я записал код")
        self.content.addWidget(self.written)
        row = QHBoxLayout()
        copy = QPushButton("Скопировать")
        copy.setAutoDefault(False)
        copy.clicked.connect(lambda: QApplication.clipboard().setText(code))
        row.addWidget(copy)
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        self.ok = QPushButton("Готово")
        self.ok.setDefault(True)
        self.ok.setEnabled(False)
        self.ok.clicked.connect(self.accept)
        self.written.toggled.connect(self.ok.setEnabled)
        row.addWidget(cancel)
        row.addWidget(self.ok)
        self.content.addLayout(row)


class CodeEntryDialog(Sheet):
    """Ввод кода восстановления. check(code) -> подошёл ли."""

    def __init__(self, parent, check):
        super().__init__(parent, "Вход по коду")
        self.setMinimumWidth(520)
        self.check = check
        label = QLabel("Введи код восстановления, который блокнот показал, когда ставили пароль. "
                       "Дефисы и регистр не важны.")
        label.setWordWrap(True)
        self.content.addWidget(label)
        self.field = QLineEdit()
        self.field.setPlaceholderText("XXXX-XXXX-XXXX-XXXX-XXXX")
        self.content.addWidget(self.field)
        self.error = QLabel("")
        self.error.setObjectName("Error")
        self.error.setWordWrap(True)
        self.content.addWidget(self.error)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Войти")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        self.content.addLayout(row)
        self.field.setFocus()

    def accept(self):
        try:
            accepted = self.check(self.field.text())
        except LockBroken:
            self.error.setText(f"Файл ключа повреждён ({lock_path().name}). Возьми его из резервной копии.")
            return
        if not accepted:
            self.error.setText("Код не подходит. Проверь, нет ли опечатки.")
            self.adjustSize()
            return
        super().accept()
