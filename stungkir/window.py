# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: интерфейс, панели, режимы, кубики."""

import json
import random
import sys
from datetime import date, datetime
from pathlib import Path
from PySide6.QtCore import (
    QElapsedTimer, QEvent, QFileSystemWatcher, QPoint, QProcess, QSettings, Qt, QTimer,
)
from PySide6.QtGui import QColor, QCursor, QFont, QKeySequence, QShortcut, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMainWindow, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

from . import config as C
from . import storage as S
from .icons import decorate, make_icon
from .style import TEXTURES, apply_theme, fade
from .textutil import (
    WORD_RE, is_prose,
)
from .storage import (
    MAIN_FILE, backup_path, files_in, load_goals, load_marks, load_names, load_plan, load_stats, make_backup,
)
from .lore import Lore, load_lore_config
from .dialogs import HotkeysDialog, show_error, show_warning
from .windows import SettingsDialog, load_config_raw
from .dice import RandomDialog
from .sounds import DEFAULT_VOLUME, Sounds
from .widgets import ClockFace, EmptyHint, GoalPop, GoalStrip, NightVeil, PicturePop, SlidePanel, StreakPop, Toast
from .editor import Editor, LineNumbers, NotesMargin, ProseHighlighter, Rehighlighter, SidePane, Speller, visible_blocks
from .table import TableView
from .board import BoardView
from .files import FilesMixin
from .search import SearchMixin
from .world import WorldMixin
from .progress import ProgressMixin
from .security import SecurityMixin
from .project import ProjectMixin
from .crutches import CrutchesMixin
from .replace import ReplaceMixin
from .presence import PresenceMixin
from .deadline import DeadlineMixin
from .plan import PlanMixin
from .publish import PublishMixin
from .templates import TemplatesMixin
from .rhythm import RhythmMixin
from .timeline import TimelineView
from .conflicts import ConflictsMixin
from .markup import MarkupMixin
from .panels import PanelsMixin
from .sample import SampleMixin
from .safety import SafetyMixin, clear_journal
from .trash import purge_old as purge_trash
from .speakers import SpeakersMixin
from .speech import SpeechMixin


# ---------------- главное окно ----------------
class Notepad(FilesMixin, SearchMixin, WorldMixin, ProgressMixin, SecurityMixin, ProjectMixin, CrutchesMixin,
              ReplaceMixin, PresenceMixin, DeadlineMixin, PlanMixin, PublishMixin, TemplatesMixin, RhythmMixin, SpeechMixin,
              SpeakersMixin, SafetyMixin, ConflictsMixin, SampleMixin, PanelsMixin, MarkupMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.zen = False           # «без отвлечений»
        C.ROOT.mkdir(parents=True, exist_ok=True)
        from .storage import tidy_root
        tidy_root()                    # служебное из прошлых версий - в .stungkir (если ещё не переехало)
        if not any(p.is_dir() and not p.name.startswith(".") for p in C.ROOT.iterdir()):
            (C.ROOT / "Черновики").mkdir()

        self.settings = QSettings(C.APP_ID, C.APP_ID)
        self.sounds = Sounds(self, self.settings.value("dice_sound", DEFAULT_VOLUME))
        self.path = None
        self.font_size = int(self.settings.value("font_size", C.FONT_SIZE))
        self.goal = int(self.settings.value("daily_goal", C.DAILY_GOAL))
        self.session = QElapsedTimer()
        self.session.start()
        self.words = 0
        self._rehighlighting = False
        self._own_stamp = None
        self._tree_signature = None
        self.speller = Speller(C.service_path(".dictionary.txt"))
        try:
            self.positions = json.loads(self.settings.value("positions", "{}"))
        except ValueError:
            self.positions = {}
        self.chapter_goals = load_goals()
        self.plan = load_plan()
        self._chapter_toasted = set()
        self.names = load_names()
        self.night_mode = self.settings.value("night_mode", "off")   # вечерние цвета теперь в «Цвета и темы»

        # слова за сегодня: сколько уже было за день + сколько добавлено сейчас
        self.today = date.today().isoformat()
        self.stats = load_stats()                      # все устройства вместе (телефон пишет свой файл)
        self.day_marks = load_marks()
        self.today_base = load_stats(own_only=True).get(self.today, 0)
        self.session_net = 0
        self.file_base_words = 0
        self.pasted_today = 0                 # слова, вставленные из буфера: в «написано за день» не идут

        # таймер
        self.timer_deadline = None
        self.timer_words_start = 0
        self.timer_warned = False

        self.setMinimumSize(640, 480)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.main_layout = layout

        self.editor = Editor()
        self.empty_hint = EmptyHint(self.editor.viewport())
        self.editor.zoom_callback = self.zoom
        self.view = None          # None - глава, иначе таблица или доска
        self.board_view = BoardView(self._view_changed,
                                    lambda: self.toast.show_message(
                                        "Латиница выключена: переключи раскладку на русскую"),
                                    lambda text: self.toast.show_message(text),
                                    self.chapter_keys, self.open_chapter_key)
        self.table_view = TableView(self._view_changed,         # таблицы тоже сохраняются сами
                                    lambda: self.toast.show_message(
                                        "Латиница выключена: переключи раскладку на русскую"),
                                    lambda text: self.toast.show_message(text))
        self.table_view.table.itemChanged.connect(lambda _i: self.count_timer.start())
        self.timeline_view = TimelineView(self._view_changed,
                                          lambda: self.toast.show_message(
                                              "Латиница выключена: переключи раскладку на русскую"),
                                          lambda text: self.toast.show_message(text),
                                          self.chapter_keys, self.open_chapter_key)
        self.editor.speller = self.speller
        self.editor.foreign_callback = lambda: self.toast.show_message(
            "Латиница выключена: переключи раскладку на русскую")
        self.editor.dictionary_changed = lambda: self._rehighlight()
        self.editor.track_name_callback = self.name_from_text
        self.editor.lore_tip = self._lore_tip
        self.editor.lore_open = self._lore_open
        self.notes_margin = NotesMargin(self.editor)
        self.notes_margin.open_callback = self.edit_note
        self.notes_margin.add_callback = self.note_for_block
        self.notes_margin.shown = self.settings.value("margin_notes", "true") == "true"
        self.editor.margin_widget = self.notes_margin
        self.line_numbers = LineNumbers(self.editor)
        self.editor.line_widget = self.line_numbers
        self.line_numbers.set_shown(self.settings.value("line_numbers", "false") == "true")
        self.editor.note_callback = self.note_for_block
        self.editor.forward_callback = lambda: self.toast.show_message(
            "Режим «только вперёд»: стирать нельзя, пиши дальше")
        self.pages = QStackedWidget()
        self.pages.addWidget(self.editor)
        self.pages.addWidget(self.table_view)
        self.pages.addWidget(self.board_view)
        self.pages.addWidget(self.timeline_view)
        # справа от текста может стоять панель «рядом»: глава, справочник, таблица
        self.side = SidePane(self.open_from_side, self.close_side)
        self.side.side_button.clicked.connect(self.flip_side)
        self.side_compare_timer = QTimer(self, singleShot=True, interval=1200)   # сравнение - после паузы
        self.side_compare_timer.timeout.connect(lambda: self.side.refresh_version(keep_place=True))
        self.split = QSplitter(Qt.Horizontal)
        self.split.splitterMoved.connect(lambda *_a: self.place_overlays())   # часы - вслед за панелью «рядом»
        self.split.setChildrenCollapsible(False)
        self.split.setHandleWidth(6)
        # самая широкая страница (доска с колонками) иначе не даёт панели рядом стать шире узкой полоски
        self.pages.setMinimumWidth(320)
        self.side.setMinimumWidth(240)
        self.split.addWidget(self.pages)
        self.split.addWidget(self.side)
        self.split.setStretchFactor(0, 3)
        self.split.setStretchFactor(1, 2)
        self.side.hide()
        layout.addWidget(self.split, 1)
        self.highlighter = ProseHighlighter(self.editor.document(), self.speller)
        self.rehighlighter = Rehighlighter(self.highlighter, self.editor, self._set_rehighlighting)
        self.highlighter.set_names(self.names)
        self.highlighter.punctuation = self.settings.value("punctuation", "true") == "true"
        self.lore_cfg = load_lore_config()
        self.lore = Lore(self.speller)
        self.highlighter.lore = self.lore
        self.side.highlighter.lore = self.lore
        self.highlighter.lore_underline = self.settings.value("lore_underline", "true") == "true"
        self.side.highlighter.lore_underline = self.highlighter.lore_underline
        self.variant_terms = {}
        self.crutch_entries = []
        self.init_deadlines()

        self.goal_strip = GoalStrip()
        self.goal_strip.set_style(self.settings.value("goal_style", "bright"))
        layout.addWidget(self.goal_strip)
        self.status = QLabel()
        self.status.setObjectName("Status")
        self.status.setTextFormat(Qt.RichText)    # цифры - в цвет своих полосок
        self.status_plain = ""
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setContentsMargins(0, 0, 0, 10)
        layout.addWidget(self.status)

        self.search_bar = self._build_search_bar(central)
        self.global_search = self._build_global_search(central)
        self.characters = self._build_characters(central)
        # часы в правом верхнем углу (под панелями): время с системой, бледно, мышь сквозь них проходит
        self.corner_clock = ClockFace(central)
        self.corner_clock.setVisible(self.screen_shown("clock"))
        self.clock_timer = QTimer(self, interval=1000)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start()
        self.update_clock()
        self.history = []                        # выпавшее в «Рандомайзерах» (новое - первым)
        self.left = SlidePanel(central, "left", C.LEFT_WIDTH)
        self._build_left(self.left)
        self.toast = Toast(central)
        self.streak_pop = StreakPop(central)
        self.goal_pop = GoalPop(central)
        self.picture_pop = PicturePop(central)
        central.installEventFilter(self)
        S._problem_hook = lambda text: self.toast.show_message(text, 3500)
        for text in S._pending_problems:
            QTimer.singleShot(1200, self, lambda t=text: self.toast.show_message(t, 3500))
        S._pending_problems.clear()
        self.veil = NightVeil(self)
        self.veil.setGeometry(self.rect())
        self.veil.raise_()

        # следим за файлами: если глава поменялась на другом устройстве, подхватываем
        self.watcher = QFileSystemWatcher(self)
        self.file_check_timer = QTimer(self, singleShot=True, interval=400)
        self.file_check_timer.timeout.connect(self.check_external)
        self.tree_timer = QTimer(self, singleShot=True, interval=700)
        self.tree_timer.timeout.connect(self._tree_maybe_changed)
        self.watcher.fileChanged.connect(lambda _p: self.file_check_timer.start())
        self.watcher.directoryChanged.connect(lambda _p: self.tree_timer.start())

        self.apply_font()
        doc = self.editor.document()
        doc.modificationChanged.connect(self.update_title)
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.paste_callback = self.note_pasted
        self.editor.key_callback = self.typing_sound
        self.editor.cursorPositionChanged.connect(self._on_cursor_moved)

        self.count_timer = QTimer(self, singleShot=True, interval=900)
        self.autosave_timer = QTimer(self, singleShot=True, interval=C.AUTOSAVE_PAUSE_MS)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_age = QElapsedTimer()
        self.count_timer.timeout.connect(self.count_words)
        self.status_idle = QTimer(self, singleShot=True, interval=C.STATUS_IDLE_MS)
        self.status_idle.timeout.connect(lambda: fade(self.status, None, 1.0, 600))
        self.global_timer = QTimer(self, singleShot=True, interval=250)
        self.global_timer.timeout.connect(self.run_global_search)
        self.clock = QTimer(self, interval=1000)
        self.clock.timeout.connect(self._tick)
        self.clock.start()
        self.hover_timer = QTimer(self, interval=40)
        self.hover_timer.timeout.connect(self.check_hover)
        self.hover_timer.start()

        # горячие клавиши: что делает каждая (сами клавиши - свои из настроек или стандартные, см. KEY_ACTIONS)
        self.key_callbacks = {
            "save": self.save, "new": self.new_file, "find": self.show_search,
            "find_all": self.show_global_search, "replace": self.show_replace_all, "copy_all": self.copy_all,
            "forward": lambda: self.set_forward_only(not self.editor.forward_only),
            "italic": lambda: self.insert_symbol("*|*"), "bold": lambda: self.insert_symbol("**|**"),
            "marker": lambda: self.insert_symbol("[|]"),
            "focus": lambda: self.set_focus_mode(not self.highlighter.focus),
            "typewriter": lambda: self.set_typewriter(not self.editor.typewriter),
            "read": self.toggle_reading, "zen": lambda: self.set_zen(not self.zen),
            "fullscreen": self.toggle_fullscreen, "help": lambda: self.show_hotkeys(),
            "settings": lambda: self.show_settings(), "dash": lambda: self.insert_symbol("—"),
            "ellipsis": lambda: self.insert_symbol("…"), "quotes": lambda: self.insert_symbol("«|»"),
            "zoom_in": lambda: self.zoom(1), "zoom_out": lambda: self.zoom(-1),
            "note": lambda: self.note_for_block(self.editor.textCursor().block()),
            "side": lambda: self.toggle_side(), "antistress": lambda: self.show_antistress(),
            "compare": lambda: self.compare_with_version(), "preview": lambda: self.show_preview(),
            "lines": lambda: self.toggle_line_numbers(), "plan": lambda: self.show_plan(),
        }
        self.shortcuts = {}
        self.apply_hotkeys()
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(lambda: self.zoom(1))   # «+» без Shift

        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1100, 740)

        self.load_text("")
        last = self.settings.value("last_file")
        if last and Path(last).is_file():
            self.open_path(Path(last))
        self.refresh_tree()
        self.set_focus_mode(self.settings.value("focus_mode", "false") == "true", quiet=True)
        self.set_typewriter(self.settings.value("typewriter", "false") == "true", quiet=True)
        self.update_night(instant=True)
        # цвета по времени суток: дневная тема, вечернее потемнение, плавная смена на ночную
        self._palette_now = None
        self.palette_timer = QTimer(self, interval=30_000)
        self.palette_timer.timeout.connect(self.update_palette)
        self.palette_timer.start()
        beside = self.settings.value("side_file", "")
        if self.settings.value("side_open", "false") == "true" and beside and Path(beside).is_file():
            self.open_beside(Path(beside))
        self.init_crutches()
        self.init_safety()
        purge_trash()                         # что пролежало в корзине дольше 30 дней
        texture = self.settings.value("texture", "none")
        if texture == "picture" and not self.backdrop_file().is_file():
            texture = "none"                      # картинку удалили - ровный фон
        if texture != C.TEXTURE and texture in TEXTURES:
            C.TEXTURE = texture
            apply_theme(QApplication.instance())
        self.apply_backdrop()
        self.update_title()
        self.update_empty_hint()
        self.apply_places()                # где стоят часы, полоски и строка
        self.apply_screen()                # что видно на экране: часы, полоски, строка, язычки
        decorate(self)                     # значки кнопкам по надписям: «Старт», «Стереть историю»…
        self.editor.setFocus()

        QTimer.singleShot(400, self, self.finish_encryption)
        QTimer.singleShot(1500, self, self.announce_conflicts)
        if self.settings.value("intro_seen", "false") != "true":
            QTimer.singleShot(1200, self, self.show_intro)
        if not backup_path().exists():
            QTimer.singleShot(2000, make_backup)
        QTimer.singleShot(2600, self, self.weekly_backup)
        if not self.speller.available:
            QTimer.singleShot(900, self, lambda: self.toast.show_message(
                "Проверка орфографии выключена: нет русского словаря", 3000))

    # ---------------- панели и окно ----------------
    def eventFilter(self, obj, event):
        if obj is self.centralWidget() and event.type() == QEvent.Resize:
            self.left.place()
            self.place_overlays()
        return super().eventFilter(obj, event)

    def update_clock(self):
        self.corner_clock.set_time(datetime.now())

    def set_zen(self, on):
        """«Без отвлечений» (F10): только текст. Прячутся часы, строка внизу, полоска цели,
        заметки на полях и язычки панелей; панели у краёв не выезжают. F10 - всё обратно."""
        self.zen = on
        self.update_empty_hint()
        for panel in (self.left,):
            panel.set_quiet(on)
        self.apply_screen()
        self.notes_margin.setVisible(not on)
        self.line_numbers.set_quiet(on)
        if on:
            self.toast.show_message("Без отвлечений. F10 - вернуть всё", 2600)
        self.editor.setFocus()

    def set_texture(self, kind):
        """Фон под текстом: ровный, бумага, лён или своя картинка. Фактура едва заметна и ложится
        на цвет любой темы; картинка притемняется цветом фона, чтобы буквы читались."""
        if kind == "picture" and not self.backdrop_file().is_file():
            self.choose_backdrop()
            return
        C.TEXTURE = kind if kind in TEXTURES else "none"
        self.settings.setValue("texture", C.TEXTURE)
        self.apply_palette(self._palette_now or C.palette())
        self.apply_backdrop()

    BACKDROP_DIMS = {35: "чуть", 55: "средне", 70: "сильно", 82: "очень сильно"}

    @staticmethod
    def backdrop_file():
        found = sorted(C.DATA_DIR.glob("фон-под-текстом.*"))
        return found[0] if found else C.DATA_DIR / "фон-под-текстом.png"

    def apply_backdrop(self):
        dim = int(self.settings.value("backdrop_dim", 55) or 55)
        shown = self.editor.set_backdrop(self.backdrop_file() if C.TEXTURE == "picture" else None, dim / 100)
        layer = getattr(self, "backdrop_layer", None)
        if shown and layer is None:
            from .editor import BackdropLayer
            layer = self.backdrop_layer = BackdropLayer(self.centralWidget(), self.editor)
        if layer is not None:
            layer.setVisible(shown)
            layer.lower()
            layer.update()

    def choose_backdrop(self, path=None):
        """Своя картинка под текстом: копия кладётся к настройкам (сам файл можно потом удалить)."""
        import shutil
        from PySide6.QtGui import QImage
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Картинка под текстом", str(Path.home()),
                                                  "Картинки (*.jpg *.jpeg *.png *.webp *.bmp)")
            if not path:
                return False
        path = Path(path)
        image = QImage(str(path))
        if image.isNull():
            show_warning(self, "Картинка под текстом", "Эту картинку не получилось открыть. "
                                                       "Подойдут JPG, PNG, WebP, BMP.")
            return False
        try:
            C.DATA_DIR.mkdir(parents=True, exist_ok=True)
            for old in C.DATA_DIR.glob("фон-под-текстом.*"):
                old.unlink()
            shutil.copyfile(path, C.DATA_DIR / f"фон-под-текстом{path.suffix.lower()}")
        except OSError as error:
            show_error(self, "Картинка под текстом", f"Не получилось сохранить картинку: {error}")
            return False
        self.set_texture("picture")
        need = self.backdrop_need()
        if image.width() < need[0] * 0.8 or image.height() < need[1] * 0.8:
            show_warning(self, "Картинка под текстом",
                         f"Картинка маленькая: {image.width()}×{image.height()}, а окно на твоём экране - "
                         f"{need[0]}×{need[1]} точек. Её придётся растянуть, и она будет мыльной.\n\n"
                         f"Для чёткой картинки нужна от {need[0]}×{need[1]} и больше. Блокнот хранит её "
                         f"без пережатия и рисует в настоящих точках экрана - качество теряется только "
                         f"при растягивании.")
        else:
            self.toast.show_message("Картинка под текстом. Насколько её притемнить - «Фон под текстом → Затемнение»")
        return True

    def backdrop_need(self):
        """Сколько настоящих точек экрана занимает окно развёрнутым: такой должна быть картинка."""
        screen = self.screen() or QApplication.primaryScreen()
        ratio = screen.devicePixelRatio() if screen else 1.0
        size = screen.availableGeometry().size() if screen else self.size()
        return int(size.width() * ratio), int(size.height() * ratio)

    def set_backdrop_dim(self, percent):
        self.settings.setValue("backdrop_dim", percent)
        self.apply_backdrop()

    # ---------------- что видно на экране ----------------
    # каждое можно убрать отдельно: кому-то нужны часы и полоски, а кому-то - только текст
    SCREEN_ITEMS = (("clock", "Часы в углу"), ("goals", "Полоски целей"), ("status", "Строка внизу"),
                    ("session", "Время сессии в строке"), ("streak", "Дни подряд в строке"),
                    ("tabs", "Язычки панелей у краёв"))

    @staticmethod
    def _screen_key(key):
        return "clock" if key == "clock" else f"screen_{key}"     # часы - под прежним ключом

    def screen_shown(self, key):
        return self.settings.value(self._screen_key(key), "true") == "true"

    def set_screen_shown(self, key, shown):
        self.settings.setValue(self._screen_key(key), "true" if shown else "false")
        self.apply_screen()

    def toggle_screen(self, key):
        self.set_screen_shown(key, not self.screen_shown(key))

    def set_screen_all(self, shown):
        """«Убрать всё» / «Вернуть всё»: остаётся только текст, но не в режиме F10 - панели
        у краёв выезжают как обычно, просто ничего лишнего не видно."""
        for key, _label in self.SCREEN_ITEMS:
            self.settings.setValue(self._screen_key(key), "true" if shown else "false")
        if self.notes_margin.shown != shown:
            self.toggle_margin_notes()
        if not shown and self.line_numbers.shown:      # номера сами не возвращаются: их включают нарочно
            self.toggle_line_numbers()
        self.apply_screen()
        self.toast.show_message("Всё вернулось на экран" if shown else
                                "На экране только текст. Вернуть: Вид → На экране → Вернуть всё", 3500)

    PLACES = {"clock": (("tr", "Справа сверху"), ("tl", "Слева сверху"), ("br", "Справа снизу"),
                        ("bl", "Слева снизу")),
              "bar": (("bottom", "Снизу"), ("top", "Сверху")),
              "align": (("center", "По центру"), ("left", "Слева"), ("right", "Справа"))}

    def place(self, what):
        value = self.settings.value(f"place_{what}", self.PLACES[what][0][0])
        return value if value in dict(self.PLACES[what]) else self.PLACES[what][0][0]

    def set_place(self, what, value):
        self.settings.setValue(f"place_{what}", value)
        self.apply_places()

    def apply_places(self):
        """Где стоят часы, полоски и строка: строка с полосками - сверху или снизу текста,
        по центру или у края; часы - в любом углу."""
        layout = self.main_layout
        for widget in (self.goal_strip, self.status):
            layout.removeWidget(widget)
        top = self.place("bar") == "top"
        if top:
            layout.insertWidget(0, self.status)
            layout.insertWidget(1, self.goal_strip)
            self.status.setContentsMargins(16, 10, 16, 0)
        else:
            layout.addWidget(self.goal_strip)
            layout.addWidget(self.status)
            self.status.setContentsMargins(16, 0, 16, 10)
        align = self.place("align")
        self.status.setAlignment({"left": Qt.AlignLeft, "right": Qt.AlignRight}.get(align, Qt.AlignHCenter)
                                 | Qt.AlignVCenter)
        self.goal_strip.set_align(align)
        self.place_overlays()

    def apply_screen(self):
        zen = getattr(self, "zen", False)
        self.corner_clock.setVisible(not zen and self.screen_shown("clock"))
        self.status.setVisible(not zen and self.screen_shown("status"))
        for panel in (self.left,):
            panel.set_tabs(self.screen_shown("tabs"))
        self.update_status()                     # и полоски, и части строки внизу
        self.place_overlays()                    # часы прячутся, если их угол занят панелью «рядом»
        self.place_overlays()                    # часы в нижнем углу встают над строкой или ниже

    def set_goal_style(self, name):
        self.settings.setValue("goal_style", name)
        self.goal_strip.set_style(name)
        self.update_status()

    def toggle_clock(self):
        self.toggle_screen("clock")

    def place_overlays(self):
        central = self.centralWidget()
        if hasattr(self, "corner_clock"):
            corner = self.place("clock")
            x = 18 if corner.endswith("l") else central.width() - self.corner_clock.width() - 18
            side = getattr(self, "side", None)
            covered = False
            if side is not None and side.isVisible():
                # панель «рядом» в том же углу: часы закрыли бы и её, и край текста - прячем, пока она открыта
                left = side.mapTo(central, QPoint(0, 0)).x()
                side_on_left = left < central.width() / 2
                covered = corner.endswith("l") == side_on_left
            zen = getattr(self, "zen", False)
            self.corner_clock.setVisible(not covered and not zen and self.screen_shown("clock"))
            y = 12
            if corner.startswith("b"):
                y = central.height() - self.corner_clock.height() - 12
                if self.place("bar") == "bottom" and self.status.isVisible():
                    y -= self.status.height() + self.goal_strip.height()     # не наезжать на строку
            elif self.place("bar") == "top" and self.status.isVisible():
                y += self.status.height() + self.goal_strip.height()
            self.corner_clock.move(x, max(0, y))
        self.search_bar.move((central.width() - self.search_bar.width()) // 2, C.MARGIN)
        if hasattr(self, "streak_pop"):              # огонёк серии - рядом со строкой (снизу или сверху)
            align = self.place("align")
            x = {"left": 24, "right": central.width() - self.streak_pop.width() - 24}.get(
                align, (central.width() - self.streak_pop.width()) // 2)
            y = central.height() - self.streak_pop.height() - 56 if self.place("bar") == "bottom" else 64
            self.streak_pop.move(x, y)
            pop = self.goal_pop                      # праздник цели - из той же точки над строкой
            y = central.height() - pop.height() - 40 if self.place("bar") == "bottom" else 40
            pop.move(x + (self.streak_pop.width() - pop.width()) // 2, y)
        for box in (self.global_search, getattr(self, "characters", None)):
            if box is None:
                continue
            box.setFixedHeight(min(460, central.height() - 4 * C.MARGIN))
            box.move((central.width() - box.width()) // 2, (central.height() - box.height()) // 2)

    def check_hover(self):
        if (self.zen or not self.isActiveWindow() or QApplication.activePopupWidget()
                or QApplication.activeModalWidget()):
            return
        central = self.centralWidget()
        pos = central.mapFromGlobal(QCursor.pos())
        inside_y = 0 <= pos.y() <= central.height()
        reach = 30
        if not self.left.opened and inside_y and 0 <= pos.x() <= C.EDGE:
            self.left.set_open(True)
        elif self.left.opened and (pos.x() > C.MARGIN + self.left.width() + reach or not inside_y):
            self.left.set_open(False)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def apply_font(self):
        font = QFont(C.FONT_FAMILY, self.font_size)
        font.setWeight(C.FONT_WEIGHT)
        if font == self.editor.font() and getattr(self, "_font_set", False):
            return         # тот же шрифт: не пересчитываем вёрстку всей главы (на большой это секунды)
        self._font_set = True
        self.editor.setFont(font)
        self.editor.setTabStopDistance(self.editor.fontMetrics().horizontalAdvance(" ") * 4)
        if hasattr(self, "side"):
            self.side.set_font(font)

    def zoom(self, step):
        self.font_size = max(10, min(32, self.font_size + step))
        self.apply_font()

    # ---- текущий файл: глава, таблица или доска ----
    @property
    def table_mode(self):
        """Открыта не глава, а таблица или доска."""
        return self.view is not None

    def current_text(self):
        return self.view.text() if self.view else self.editor.toPlainText()

    def word_count(self):
        source = self.view.words_text() if self.view else self.editor.toPlainText()
        return len(WORD_RE.findall(source))

    def is_modified(self):
        return self.view.modified if self.view else self.editor.document().isModified()

    def set_modified(self, value):
        if self.view:
            self.view.set_modified(value)
        else:
            self.editor.document().setModified(value)

    def _view_changed(self):
        self.update_title()
        if hasattr(self, "count_timer"):
            self.count_timer.start()
        if hasattr(self, "autosave_timer"):
            self.schedule_autosave()          # таблицы и доски тоже сохраняются сами

    def load_view(self, view, text):
        self.words = self.word_count()
        self.session_net += self.words - self.file_base_words
        self.view = view
        view.load(text)
        self.pages.setCurrentWidget(view)
        self.update_empty_hint()
        self.words = self.file_base_words = self.word_count()
        self.count_words()
        self.update_status()

    def load_table(self, text):
        self.load_view(self.table_view, text)

    def chapter_keys(self):
        keys = []
        for category in self.categories():
            for f in files_in(category):
                if is_prose(f):
                    keys.append(self._position_key(f))
        return keys

    def open_chapter_key(self, key):
        path = C.ROOT / key
        if path.exists():
            self.open_path(path)
        else:
            self.toast.show_message("Такой главы больше нет")

    def update_title(self, *_):
        name = self.path.stem if self.path else "Без названия"
        mark = "● " if self.is_modified() else ""
        self.setWindowTitle(f"{mark}{name} · {C.APP_NAME}")

    MARKUP = {"*|*": "*", "**|**": "**", "[|]": "[]"}

    def update_empty_hint(self):
        """Картинка на пустой странице - только когда текста нет совсем и открыта глава, а не доска."""
        hint = self.empty_hint
        empty = self.view is None and self.editor.document().isEmpty() and not getattr(self, "zen", False)
        if empty:
            hint.lines = (("Чистый лист.", f"«{self.path.stem}» пока пустая - начни печатать.") if self.path else
                          ("Чистый лист.", "Начни печатать здесь - или создай главу слева, у края окна."))
            hint.place()
            hint.update()
        hint.setVisible(empty)

    def _on_text_changed(self):
        self.update_empty_hint()
        if self.side.showing_version and self.side.isVisible():
            self.side_compare_timer.start()
        if self._rehighlighting:
            return
        import time
        self._last_typed = time.monotonic()
        if getattr(self, "_reading", None):
            self.note_typing_for_speech()
        if not self.count_timer.isActive():
            self.count_timer.start()      # пока печатаешь, счёт обновляется примерно раз в секунду
        self.schedule_autosave()
        if self.search_bar.isVisible():
            self.update_matches()
        if self.timer_deadline is not None:
            self.fox_wheel.speed_up()
        # пока пишешь, статус почти пропадает, чтобы не отвлекать
        if self.editor.hasFocus():
            fade(self.status, None, 0.55, 300)    # приглушён, но цель видна
            self.status_idle.start()

    def _rehighlight(self, blocks=None):
        """blocks=None - вся глава (большая - порциями, начиная с экрана); иначе только эти абзацы."""
        self.rehighlighter.run(blocks)

    def _set_rehighlighting(self, flag):
        self._rehighlighting = flag

    def _focus_block(self):
        """Абзац, который светится в режиме фокуса: на пустой строке - последний непустой выше."""
        block = self.editor.textCursor().block()
        probe = block
        while probe.isValid() and not probe.text().strip():
            probe = probe.previous()
        if not probe.isValid():
            probe = block
            while probe.isValid() and not probe.text().strip():
                probe = probe.next()
        return (probe if probe.isValid() else block).blockNumber()

    def _on_cursor_moved(self):
        number = self._focus_block()
        if number != self.highlighter.current:
            old = self.highlighter.current
            self.highlighter.current = number
            if self.highlighter.focus:
                doc = self.editor.document()
                self._rehighlight([doc.findBlockByNumber(old), doc.findBlockByNumber(number)])
        if self.editor.typewriter and QApplication.mouseButtons() == Qt.NoButton:
            QTimer.singleShot(0, self.editor, self.editor.center_cursor)

    def set_focus_mode(self, on, quiet=False):
        changed = on != self.highlighter.focus
        self.highlighter.focus = on
        self.highlighter.current = self._focus_block()
        self.focus_button.setChecked(on)
        self._rehighlight()
        self._mode_changed("Режим фокуса включён" if on else "Режим фокуса выключен", changed and not quiet)

    def set_typewriter(self, on, quiet=False):
        changed = on != self.editor.typewriter
        self.editor.set_typewriter(on)
        self.typewriter_button.setChecked(on)
        self._mode_changed("Печатная машинка: строка, где пишешь, всегда посередине экрана" if on
                           else "Печатная машинка выключена",
                           changed and not quiet)

    def set_forward_only(self, on):
        self.editor.forward_only = on
        self.forward_button.setChecked(on)
        self.toast.show_message("Только вперёд: стирать нельзя" if on else "Стирать снова можно")
        self.update_status()

    def _mode_changed(self, message, announce):
        if announce and hasattr(self, "toast"):
            self.toast.show_message(message)
        if hasattr(self, "status"):
            self.update_status()

    def active_modes(self):
        """Включённые режимы - коротко, для строки внизу."""
        modes = []
        if self.highlighter.focus:
            modes.append("фокус")
        if self.editor.typewriter:
            modes.append("машинка")
        if self.editor.forward_only:
            modes.append("только вперёд")
        return modes

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "veil"):
            self.veil.setGeometry(self.rect())
            self.veil.raise_()

    def is_night(self):
        if self.night_mode == "on":
            return True
        if self.night_mode == "off":
            return False
        hour = datetime.now().hour
        if C.NIGHT_FROM > C.NIGHT_TO:
            return hour >= C.NIGHT_FROM or hour < C.NIGHT_TO
        return C.NIGHT_FROM <= hour < C.NIGHT_TO

    def update_night(self, instant=False):
        self.veil.set_level(1.0 if self.is_night() else 0.0, instant)
        self.veil.raise_()

    def toggle_punctuation(self):
        self.highlighter.punctuation = not self.highlighter.punctuation
        self.settings.setValue("punctuation", "true" if self.highlighter.punctuation else "false")
        self._rehighlight()

    def show_preview(self, device="book"):
        """Как глава будет выглядеть у читателя: книга A5, телефон, читалка."""
        if self.view is not None:
            self.toast.show_message("Предпросмотр - для главы, а не таблицы, доски или хронологии")
            return None
        from .preview import PreviewDialog
        title = self.path.stem if self.path else "Без названия"
        following = []                           # для ленты: следующие главы той же категории
        if self.path is not None:
            try:
                chapters = [f for f in S.files_in(self.path.parent) if f.suffix.lower() in (".txt", ".md", "")]
                after = chapters[chapters.index(self.path) + 1:] if self.path in chapters else []
                following = [(f.stem, lambda f=f: S.read_text(f)) for f in after]
            except OSError:
                following = []
        dialog = PreviewDialog(self, title, self.editor.toPlainText(), device, following,
                               self.path.parent if self.path else None)
        dialog.exec()
        return dialog

    def show_antistress(self):
        from .antistress import StressDialog
        StressDialog(self).exec()
        self.editor.setFocus()

    def hotkeys(self):
        from .dialogs import hotkey_map
        return hotkey_map(self.settings.value("hotkeys", ""))

    def hk(self, code):
        """Клавиши действия для подписи в меню: «   F12» или пусто, если клавишу убрали."""
        keys = self.hotkeys().get(code, "")
        return f"   {QKeySequence(keys).toString(QKeySequence.NativeText)}" if keys else ""

    def apply_hotkeys(self):
        keys = self.hotkeys()
        for code, callback in self.key_callbacks.items():
            shortcut = self.shortcuts.get(code)
            if shortcut is None:
                shortcut = self.shortcuts[code] = QShortcut(self)
                shortcut.activated.connect(callback)
            shortcut.setKey(QKeySequence(keys.get(code, "")))
        from .icons import decorate_button
        for name, label, code in (("focus_button", "Режим фокуса", "focus"),
                                  ("typewriter_button", "Печатная машинка", "typewriter"),
                                  ("forward_button", "Только вперёд", "forward")):
            button = getattr(self, name, None)
            if button is not None and button.text() != label + self.hk(code):
                button.setText(label + self.hk(code))
                decorate_button(button)

    def show_hotkeys(self):
        import json
        from .dialogs import DEFAULT_KEYS
        dialog = HotkeysDialog(self, self.hotkeys())
        if not dialog.exec():
            return
        own = {code: value for code, value in dialog.values().items() if value != DEFAULT_KEYS[code]}
        self.settings.setValue("hotkeys", json.dumps(own, ensure_ascii=False))
        self.apply_hotkeys()
        self.toast.show_message("Горячие клавиши сохранены" if own else "Горячие клавиши - как были")

    def show_settings(self):
        dialog = SettingsDialog(self, load_config_raw(), self.goal)
        if not dialog.exec():
            return
        changes, goal = dialog.values()
        config = load_config_raw()      # темы и цвета живут в отдельном окне, их не трогаем
        config.update(changes)
        C.save_config(config)
        self.goal = goal
        self.settings.setValue("daily_goal", goal)
        if config.get("FONT_SIZE"):
            self.font_size = config["FONT_SIZE"]
        self.apply_settings(config)
        self.toast.show_message("Настройки применены")
        QTimer.singleShot(800, self, self.weekly_backup)          # новая папка недельной копии - сразу

    def apply_settings(self, config):
        """Настройки сразу, без перезапуска: шрифт, ширина колонки, интервал, латиница, сохранение."""
        old_line = C.LINE_HEIGHT
        C.apply_config(config)
        self.apply_palette(self._palette_now or C.palette())     # шрифт интерфейса и текста
        self.editor.only_russian = C.ONLY_RUSSIAN
        self.editor.apply_column()
        self.sounds.set_volume(self.settings.value("dice_sound", DEFAULT_VOLUME))
        if C.LINE_HEIGHT != old_line:
            doc = self.editor.document()
            modified = doc.isModified()
            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.Document)
            block = QTextBlockFormat()
            block.setLineHeight(C.LINE_HEIGHT, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            cursor.mergeBlockFormat(block)
            doc.setModified(modified)                          # интервал - не правка текста
        if not C.AUTOSAVE:
            self.autosave_timer.stop()
        self.update_night()
        self.update_status()

    # ---------------- цвета ----------------
    def show_colors(self):
        from .colors import ColorsDialog
        dialog = ColorsDialog(self, load_config_raw(), self.editor.font())
        if not dialog.exec():
            return
        C.save_config(dialog.values())
        self.update_palette(animate=True)

    def choose_theme(self, name):
        config = load_config_raw()
        config["theme"] = name
        C.save_config(config)
        self.update_palette(animate=True)

    def update_palette(self, animate=False):
        """Сверяет цвета с темой и временем суток. Смена темы - растворением старого вида поверх
        нового (без промежуточных мутных цветов), мелкие шаги вечернего потемнения - сразу."""
        target = C.current_palette(load_config_raw())
        current = self._palette_now or C.palette()
        jump = max(max(abs(a - b) for a, b in zip(QColor(current[k]).getRgb()[:3], QColor(target[k]).getRgb()[:3]))
                   for k in C.COLOR_KEYS)
        if jump < 4:
            return
        if jump > 40 and (animate or self.isVisible()) and self.isVisible():
            self._dissolve(lambda: self.apply_palette(target))
        else:
            self.apply_palette(target)

    def _dissolve(self, change):
        """Снимок окна кладётся сверху, под ним всё меняется сразу, а снимок плавно тает."""
        old = getattr(self, "_dissolve_label", None)
        if old is not None:
            old.deleteLater()
        shot = QLabel(self)
        shot.setPixmap(self.grab())
        shot.setGeometry(self.rect())
        shot.show()
        shot.raise_()
        self._dissolve_label = shot

        def done():
            shot.deleteLater()
            if getattr(self, "_dissolve_label", None) is shot:
                self._dissolve_label = None
        try:
            change()
        finally:
            # что бы ни случилось при перекраске - снимок старого вида обязан растаять, иначе окно
            # выглядит зависшим
            self.veil.raise_()
            shot.raise_()
            fade(shot, 1.0, 0.0, 650, done)

    def apply_palette(self, colors, full=True):
        """Перекрашивает окно без перезапуска."""
        C.set_palette(colors)
        self._palette_now = dict(colors)
        apply_theme(QApplication.instance())
        self.apply_font()      # смена оформления сбрасывает шрифт текста на шрифт интерфейса
        for highlighter in (self.highlighter, self.side.highlighter):
            highlighter.refresh_colors()
        if full:
            self._rehighlight()
            self.side.rehighlight()
        else:
            self._rehighlight(self._visible_blocks())   # в анимации - только то, что на экране
        for button, icon in getattr(self, "_icon_buttons", []):
            button.setIcon(make_icon(icon))
        decorate(self)                                   # значки по надписям - цветом новой темы
        self.board_view.refresh_colors()                 # пробка темнеет и светлеет вместе с темой
        for widget in self.findChildren(QWidget):
            # QWidget.update явно: у списков и таблиц в PySide 6.8 widget.update() - это update(index),
            # и без аргумента он падал, оставляя снимок старой темы поверх окна («зависло»)
            QWidget.update(widget)

    def _visible_blocks(self):
        return visible_blocks(self.editor)

    def restart(self):
        if self.close():
            if getattr(sys, "frozen", False):        # готовая сборка: перезапускаем сам .exe
                QProcess.startDetached(sys.executable, sys.argv[1:])
            else:
                QProcess.startDetached(sys.executable, [str(MAIN_FILE)] + sys.argv[1:])
            QApplication.quit()

    def set_night_mode(self, mode):
        self.night_mode = mode
        self.settings.setValue("night_mode", mode)
        self.update_night()

    def fade_in_editor(self):
        def done():
            self.editor.setGraphicsEffect(None)
            self.editor._fade_anim = None
        fade(self.editor, 0.0, 1.0, 260, done)

    def closeEvent(self, event):
        if not self.maybe_save():
            event.ignore()
            return
        self.keep_left_text()
        self.journal_timer.stop()
        clear_journal()                          # закрылись сами: запасной файл не нужен
        self._closed = True                      # закрытое окно больше ничего не пишет на диск
        for timer in (self.autosave_timer, self.journal_timer, self.count_timer, self.palette_timer):
            timer.stop()
        try:
            self.watcher.fileChanged.disconnect()
            self.watcher.directoryChanged.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.count_words()
        self.store_stats()
        self.remember_position()
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("font_size", self.font_size)
        self.settings.setValue("last_file", str(self.path) if self.path else "")
        self.settings.setValue("focus_mode", "true" if self.highlighter.focus else "false")
        self.settings.setValue("typewriter", "true" if self.editor.typewriter else "false")
        self.settings.setValue("timer_minutes", self.timer_minutes.value())
        self.settings.setValue("timer_close", "true" if self.timer_close.isChecked() else "false")
        make_backup()
        self.weekly_backup()
        event.accept()

    # ---------------- где остановился ----------------
    def _position_key(self, path):
        try:
            return path.relative_to(C.ROOT).as_posix()
        except ValueError:
            return str(path)

    def remember_position(self):
        if self.path is not None and not self.table_mode:
            self.positions[self._position_key(self.path)] = self.editor.textCursor().position()
            self.settings.setValue("positions", json.dumps(self.positions, ensure_ascii=False))

    def restore_position(self):
        position = self.positions.get(self._position_key(self.path)) if self.path else None
        if not position:
            return
        cursor = self.editor.textCursor()
        cursor.setPosition(min(int(position), self.editor.document().characterCount() - 1))
        self.editor.setTextCursor(cursor)
        QTimer.singleShot(0, self.editor, self.editor.center_cursor)

    # ---------------- звук печатной машинки ----------------
    def typing_volume(self):
        from .sounds import VOLUMES
        return VOLUMES.get(self.settings.value("typing_sound", "Без звука"), 0.0)

    def weekly_backup(self):
        """Копия раз в неделю в свою папку (Настройки → «Копия раз в неделю»)."""
        from .storage import weekly_copy
        done = weekly_copy(self.settings.value("weekly_dir", ""), self.settings.value("weekly_last", ""))
        if done:
            self.settings.setValue("weekly_last", done)
            if not getattr(self, "_closed", False):
                self.toast.show_message("Недельная копия книги сделана", 2500)
        return done

    def set_eye_break(self, minutes):
        self.settings.setValue("eye_break", minutes)
        self._screen_time = 0
        self.toast.show_message(f"Напомню отдохнуть глазам через {minutes} минут за текстом" if minutes
                                else "Напоминание о перерыве выключено")

    def set_typing_sound(self, name):
        self.settings.setValue("typing_sound", name)
        self.toast.show_message("Звук машинки выключен" if name == "Без звука" else f"Звук машинки: {name.lower()}")

    def typing_sound(self, event):
        """Каждая клавиша - удар литеры, пробел - глуше, Enter - звоночек каретки."""
        import time
        volume = self.typing_volume()
        if not volume:
            return
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            name = "type_return"
        elif key == Qt.Key_Space:
            name = "type_space"
        elif key in (Qt.Key_Backspace, Qt.Key_Delete) or (event.text() and event.text().isprintable()):
            name = random.choice(("type_1", "type_2", "type_3"))
        else:
            return
        now = time.monotonic()
        if now - getattr(self, "_typed_sound_at", 0.0) < 0.028:      # зажатая клавиша - не очередь выстрелов
            return
        self._typed_sound_at = now
        self.sounds.play(name, random.uniform(0.75, 1.0), volume)

    def add_to_history(self, text):
        """Всё выпавшее в «Рандомайзерах» - сверху списка истории (живёт, пока открыт блокнот)."""
        self.history.insert(0, text)
        del self.history[200:]

    def show_random(self):
        terms = list(self.lore.terms) if self.lore is not None else []
        RandomDialog(self, self.names, terms, self.settings, self.add_to_history, self.open_lore_term,
                     history=self.history).exec()
