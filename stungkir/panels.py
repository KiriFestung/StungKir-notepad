# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: построение панелей, меню «Ещё», поиска."""

from PySide6.QtCore import (
    QPoint, QSize,
    Qt, QTimer,
)
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QVBoxLayout, QWidget,
)

from . import config as C
from .icons import make_icon
from .style import TEXTURES, frameless_menu, rounded_menu
from .storage import (
    lock_path,
)
from .windows import load_config_raw
from .dice import Die3D
from .widgets import FileTree, FoxWheel, GoalStrip, SoftButton
from .sample import has_sample



class PanelsMixin:
    """Левая и правая панели, меню «Ещё», строки поиска. Часть главного окна."""

    # ---------------- построение интерфейса ----------------
    def _button(self, text, callback, layout, tip="", icon=None):
        button = SoftButton(text)                       # подсветка под мышкой - плавно
        if icon:
            if not hasattr(self, "_icon_buttons"):
                self._icon_buttons = []
            self._icon_buttons.append((button, icon))
            button.setIcon(make_icon(icon))
            button.setIconSize(QSize(16, 16))
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda checked=False: callback())
        if tip:
            button.setToolTip(tip)
        layout.addWidget(button)
        return button

    def _title(self, text, layout):
        title = QLabel(text.upper())                   # заголовки разделов: мелко, заглавными, вразрядку
        title.setObjectName("Title")
        spaced = title.font()
        spaced.setLetterSpacing(QFont.AbsoluteSpacing, 1.4)
        title.setFont(spaced)
        layout.addWidget(title)

    @staticmethod
    def _scrolling(panel):
        """Содержимое панели - в прокрутке: в невысоком окне кнопки не наезжают друг на друга,
        а панель прокручивается колесом. В обычном окне прокрутки не видно."""
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("PanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("PanelInner")
        scroll.setWidget(inner)
        scroll.viewport().setAutoFillBackground(False)
        outer.addWidget(scroll)
        return inner

    def _build_left(self, panel):
        layout = QVBoxLayout(self._scrolling(panel))
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(1)
        self.create_button = self._button("Создать  ▸", self.show_create_menu, layout,
                                          "Главу, таблицу, доску или категорию", "create")
        for text, callback, tip, icon in [
            ("Сохранить", self.save, "Ctrl+S", "save"),
            ("Поиск по всем файлам", self.show_global_search, "Ctrl+Shift+F", "search"),
            ("Пометки", self.show_markers, "Всё, что в [скобках], по всем главам", "marker"),
            ("Персонажи", self.show_characters, "Сколько раз встречается каждое имя", "people"),
            ("Версии файла", self.show_versions, "Прошлые сохранения этой главы", "versions"),
            ("Сравнить с версией", lambda: self.compare_with_version(), "Прошлая версия рядом с текстом, "
             "ушедшее подсвечено" + self.hk("compare"), "split"),
            ("Собрать книгу", self.compile_book, "В PDF, Word, EPUB или один текстовый файл", "book"),
        ]:
            self._button(text, callback, layout, tip, icon)
        layout.addSpacing(6)
        self.focus_button = self._button("Режим фокуса" + self.hk("focus"),
                                         lambda: self.set_focus_mode(not self.highlighter.focus),
                                         layout, "Яркий только абзац, где пишешь", "focus")
        self.typewriter_button = self._button("Печатная машинка" + self.hk("typewriter"),
                                              lambda: self.set_typewriter(not self.editor.typewriter),
                                              layout, "Строка всегда по центру экрана", "typewriter")
        self.forward_button = self._button("Только вперёд" + self.hk("forward"),
                                           lambda: self.set_forward_only(not self.editor.forward_only),
                                           layout, "Нельзя стирать: только писать дальше", "forward")
        for button in (self.focus_button, self.typewriter_button, self.forward_button):
            button.setCheckable(True)
        self.more_button = self._button("Ещё  ▸", self.show_more_menu, layout,
                                        "Настройки, статистика, цели, пароль…", "more")
        layout.addSpacing(6)
        self._title("Категории", layout)
        self.tree = FileTree(self.on_drop)
        self.tree.setHeaderHidden(True)
        # стрелки рисуем сами, чтобы выделение было одной скруглённой плашкой
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setAnimated(True)
        self.tree.itemExpanded.connect(self._update_arrow)
        self.tree.itemCollapsed.connect(self._update_arrow)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.tree_menu)
        layout.addWidget(self.tree, 1)

    def _submenu(self, menu, title):
        sub = frameless_menu(menu.addMenu(title))
        return sub

    @staticmethod
    def _toggle(menu, label, callback, checked):
        action = menu.addAction(label, callback)
        action.setCheckable(True)
        action.setChecked(checked)
        return action

    def build_more_menu(self):
        """«Ещё» по разделам: каждый раздел - подменю, чтобы всё влезало и в маленькое окно."""
        menu = rounded_menu(self)
        files = self._submenu(menu, "Файлы и импорт")
        files.addAction("Добавить файлы (текст, Word, книги, таблицы)…", self.import_files)
        files.addAction("Импорт из Scrivener…", self.import_scrivener)
        files.addAction("Заготовки для мира…", lambda: self.make_world_kit())
        files.addAction("Точки возврата…", self.show_snapshots)
        files.addAction("Корзина…", self.show_trash)
        if has_sample():
            files.addAction("Убрать пример", self.drop_sample)
        else:
            files.addAction("Добавить пример-проект", self.add_sample)
        files.addSeparator()
        files.addAction("Поиск в главе" + self.hk("find"), self.show_search)
        files.addAction("Найти и заменить во всех главах…" + self.hk("replace"), self.show_replace_all)
        undo = files.addAction("Отменить последнюю замену во всех главах", self.undo_replace)
        undo.setEnabled(bool(getattr(self, "last_replace", None)))
        files.addAction("Копировать всё" + self.hk("copy_all"), self.copy_all)

        look = self._submenu(menu, "Вид, тема и цвета")
        config = load_config_raw()
        current = C.theme_name(config.get("theme")) or C.DEFAULT_THEME
        themes = self._submenu(look, f"Тема: {current}")       # тем много - отдельным списком
        for name in C.all_themes(config):
            self._toggle(themes, name, lambda _c=False, n=name: self.choose_theme(n), name == current)
        if config.get("day_theme"):
            look.addAction(f"Днём: {config['day_theme']}").setEnabled(False)
        look.addAction("Настроить цвета и дневную тему…", self.show_colors)
        look.addSeparator()
        self._toggle(look, "Выделять знаки препинания", self.toggle_punctuation, self.highlighter.punctuation)
        self._toggle(look, "Подчёркивать имена и термины мира", self.toggle_lore_underline,
                     self.highlighter.lore_underline)
        screen = self._submenu(look, "На экране")       # что показывать вокруг текста
        for key, label in self.SCREEN_ITEMS:
            self._toggle(screen, label, lambda _c=False, k=key: self.toggle_screen(k), self.screen_shown(key))
        self._toggle(screen, "Заметки на полях", self.toggle_margin_notes, self.notes_margin.shown)
        screen.addSeparator()
        for what, title in (("clock", "Часы"), ("bar", "Полоски и строка"), ("align", "Полоски и строка")):
            current = dict(self.PLACES[what])[self.place(what)]
            places = self._submenu(screen, f"{title}: {current.lower()}")
            for value, label in self.PLACES[what]:
                self._toggle(places, label, lambda _c=False, w=what, v=value: self.set_place(w, v),
                             self.place(what) == value)
        screen.addSeparator()
        screen.addAction("Убрать всё - только текст", lambda: self.set_screen_all(False))
        screen.addAction("Вернуть всё", lambda: self.set_screen_all(True))
        bars = self._submenu(look, f"Полоски цели: {GoalStrip.STYLES[self.goal_strip.style_name].lower()}")
        for name, label in GoalStrip.STYLES.items():
            self._toggle(bars, label, lambda _c=False, n=name: self.set_goal_style(n),
                         self.goal_strip.style_name == name)
        self._toggle(look, "Без отвлечений" + self.hk("zen"), lambda: self.set_zen(not self.zen), self.zen)
        texture = self._submenu(look, f"Фон под текстом: {TEXTURES.get(C.TEXTURE, 'ровный')}")
        for kind, label in TEXTURES.items():
            self._toggle(texture, label.capitalize(), lambda _c=False, k=kind: self.set_texture(k), C.TEXTURE == kind)
        texture.addAction("Выбрать свою картинку…", lambda: self.choose_backdrop())
        if C.TEXTURE == "picture":
            dim = int(self.settings.value("backdrop_dim", 55) or 55)
            dims = self._submenu(texture, f"Затемнение картинки: {self.BACKDROP_DIMS.get(dim, dim)}")
            for value, label in self.BACKDROP_DIMS.items():
                self._toggle(dims, label.capitalize(), lambda _c=False, v=value: self.set_backdrop_dim(v), dim == value)
        look.addAction(("Закрыть панель рядом" if self.side.isVisible() else "Панель рядом") + self.hk("side"),
                       self.toggle_side)
        look.addAction("Во весь экран" + self.hk("fullscreen"), self.toggle_fullscreen)
        from .sounds import VOLUMES
        typing = self.settings.value("typing_sound", "Без звука")
        sound = self._submenu(look, "Звук печатной машинки: " + ("выключен" if typing == "Без звука" else typing.lower()))
        for name in VOLUMES:
            self._toggle(sound, name, lambda _c=False, n=name: self.set_typing_sound(n), typing == name)
        eye = int(self.settings.value("eye_break", 20) or 0)
        breaks = self._submenu(look, "Перерыв для глаз: " + (f"раз в {eye} мин" if eye else "выключен"))
        for minutes, label in ((20, "Каждые 20 минут"), (30, "Каждые 30 минут"), (45, "Каждые 45 минут"),
                               (60, "Каждый час"), (0, "Выключен")):
            self._toggle(breaks, label, lambda _c=False, m=minutes: self.set_eye_break(m), eye == minutes)
        night = self._submenu(look, "Тёплый фильтр вечером")
        for mode, label in (("auto", f"Авто, с {C.NIGHT_FROM}:00 до {C.NIGHT_TO}:00"),
                            ("on", "Всегда"), ("off", "Выключен")):
            self._toggle(night, label, lambda _c=False, m=mode: self.set_night_mode(m), self.night_mode == mode)

        goals = self._submenu(menu, "Цели и статистика")
        goals.addAction("Статистика", self.show_stats)
        goal = f" (сейчас {self.goal})" if self.goal else " (выключена)"
        goals.addAction("Цель на день" + goal + "…", self.set_goal)
        chapter = self.chapter_goal()
        goals.addAction("Цель этой главы" + (f" (сейчас {chapter})" if chapter else "") + "…",
                        self.set_chapter_goal)
        goals.addAction("Дедлайн книги…", self.show_deadline)
        from .widgets import STREAK_VOICES
        voice = self.settings.value("streak_voice", "cheer")
        talk = self._submenu(goals, f"Огонёк серии: {STREAK_VOICES.get(voice, 'подбадривает').lower()}")
        for key, label in STREAK_VOICES.items():
            self._toggle(talk, label, lambda _c=False, k=key: self.set_streak_voice(k), voice == key)
        goals.addAction("Кто в какой главе", self.show_presence)
        goals.addAction("Ритм главы", self.show_rhythm)
        goals.addAction("Реплики персонажей", self.show_reply_stats)
        goals.addAction("Кто говорит: проверить реплики", self.show_speaker_check)
        goals.addAction("Читать вслух" + self.hk("read"), self.toggle_reading)
        goals.addAction("Проверить написание имён", self.check_term_spelling)
        goals.addAction("Мои штампы…", self.show_crutches)
        goals.addAction("Найти мои штампы во всех главах", self.show_crutch_places)

        safety = self._submenu(menu, "Пароль и копии")
        if lock_path().exists():
            safety.addAction("Сменить пароль…", self.change_password)
            safety.addAction("Новый код восстановления…", self.new_recovery_code)
            safety.addAction("Снять пароль…", self.remove_password)
        else:
            safety.addAction("Поставить пароль…", self.set_password)
        safety.addAction("Точки возврата…", self.show_snapshots)

        menu.addSeparator()
        menu.addAction("Настройки…" + self.hk("settings"), self.show_settings)
        menu.addAction("Горячие клавиши - посмотреть и поменять…" + self.hk("help"), self.show_hotkeys)
        menu.addAction("Как увидит читатель (книга, телефон, читалка)" + self.hk("preview"), lambda: self.show_preview())
        menu.addAction("Антистресс" + self.hk("antistress"), self.show_antistress)
        menu.addAction("О программе", self.show_about)
        return menu

    def show_intro(self):
        """Первый запуск: показываем, что у краёв окна спрятаны панели."""
        self.settings.setValue("intro_seen", "true")
        self.hover_timer.stop()
        steps = [
            (0, lambda: (self.left.set_open(True),
                         self.toast.show_message("Слева: файлы, меню и режимы. Подведи мышь к левому краю", 2600))),
            (3000, lambda: (self.left.set_open(False), self.right.set_open(True),
                            self.toast.show_message("Справа: знаки, таймер и кубики. Подведи мышь к правому краю",
                                                    2600))),
            (6000, lambda: (self.right.set_open(False), self.hover_timer.start())),
        ]
        for delay, step in steps:
            QTimer.singleShot(delay, self, step)     # с окном-хозяином: закрыли окно - шаги отменятся

    def show_about(self):
        from . import AUTHORS, BUILD, LICENSE, __version__
        from .dialogs import AskDialog
        dialog = AskDialog(self, "О программе",
                  f"{C.APP_NAME} {__version__} (сборка {BUILD})\nПисательский блокнот.\n\nАвторы: {AUTHORS}\nCopyright © 2026 KiriFesTung\n"
                  f"Лицензия: {LICENSE} - программу можно свободно использовать, менять и раздавать, "
                  "а изменённые версии тоже должны оставаться открытыми.\n\n"
                  f"Тексты: {C.ROOT}\nРезервные копии: {C.BACKUP_DIR}\nЖурнал ошибок: {C.ERROR_LOG}",
                  [("ok", "Понятно", True)])
        from PySide6.QtWidgets import QLabel
        from .artwork import scaled
        picture = scaled("about", 520, self.devicePixelRatioF())
        if not picture.isNull():                    # шапка: ласка и ворон
            header = QLabel()
            header.setPixmap(picture)
            header.setFixedSize(picture.deviceIndependentSize().toSize())
            dialog.content.insertWidget(0, header, 0, Qt.AlignHCenter)
            dialog.setMinimumWidth(header.width() + 60)
        dialog.exec()

    def show_more_menu(self):
        self.build_more_menu().exec(self.more_button.mapToGlobal(QPoint(self.more_button.width(), 0)))

    def _grid(self, layout):
        holder = QWidget()
        holder.setObjectName("Grid")
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(5)
        layout.addWidget(holder)
        return grid

    def _build_right(self, panel):
        layout = QVBoxLayout(self._scrolling(panel))
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(5)

        self._title("Знаки", layout)
        grid = self._grid(layout)
        for i, (label, value, tip) in enumerate(C.SYMBOLS):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            if tip:
                button.setToolTip(tip)
            button.clicked.connect(lambda checked=False, v=value: self.insert_symbol(v))
            grid.addWidget(button, i // 4, i % 4)

        layout.addSpacing(4)
        self._title("Таймер", layout)
        self.fox_wheel = FoxWheel()
        layout.addWidget(self.fox_wheel)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.timer_minutes = QSpinBox()
        self.timer_minutes.setRange(1, 600)
        self.timer_minutes.setSuffix(" мин")
        self.timer_minutes.setAlignment(Qt.AlignCenter)
        self.timer_minutes.setValue(int(self.settings.value("timer_minutes", C.TIMER_MINUTES)))
        row.addWidget(self.timer_minutes, 1)
        self.timer_button = QPushButton("Старт")
        self.timer_button.setObjectName("Primary")          # главное действие панели - цветом «Важное»
        self.timer_button.setCursor(Qt.PointingHandCursor)
        self.timer_button.clicked.connect(self.toggle_timer)
        row.addWidget(self.timer_button, 1)
        layout.addLayout(row)
        self.timer_close = QCheckBox("Сохранить и выйти")
        self.timer_close.setToolTip("Когда время выйдет, StungKir всё сохранит и закроется сам")
        self.timer_close.setChecked(self.settings.value("timer_close", "true") == "true")
        layout.addWidget(self.timer_close)

        layout.addSpacing(4)
        self._title("Кубики", layout)
        grid = self._grid(layout)
        for i, sides in enumerate(C.DICE):
            button = QPushButton(f"d{sides}")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, s=sides: self.roll(s))
            grid.addWidget(button, i // 4, i % 4)
        coin = QPushButton("")
        coin.setIcon(make_icon("coin"))
        coin.setIconSize(QSize(18, 18))
        self._icon_buttons = getattr(self, "_icon_buttons", []) + [(coin, "coin")]
        coin.setCursor(Qt.PointingHandCursor)
        coin.setToolTip("Ворон или ласка - поровну, и один раз из ста монетка встаёт на ребро")
        coin.clicked.connect(lambda checked=False: self.flip_coin())
        grid.addWidget(coin, len(C.DICE) // 4, len(C.DICE) % 4)
        self.dice_value = Die3D(132)
        self.dice_value.on_sound = self.sounds.play
        self.dice_value.setToolTip("Кубик ложится выпавшей гранью к тебе")
        layout.addWidget(self.dice_value)
        self._button("Рандомайзеры…", self.show_random, layout,
                     "Число от и до, вариант из своего списка, персонаж или термин мира, рулетка с вызовами")
        self.history = QListWidget()
        self.history.setMinimumHeight(64)               # хотя бы пара последних бросков видна всегда
        # история берёт только оставшееся место: сначала кубик в полный размер, потом она
        self.history.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        layout.addWidget(self.history, 1)
        self._button("Стереть историю", self.history.clear, layout)

    def _build_search_bar(self, parent):
        bar = QFrame(parent)
        bar.setObjectName("SearchBar")
        bar.setFixedSize(520, 46)
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 4, 6, 4)
        row.setSpacing(2)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Поиск…")
        self.find_edit.textChanged.connect(self._on_find_text)
        self.find_edit.returnPressed.connect(self.find_next)
        row.addWidget(self.find_edit, 1)
        self.find_count = QLabel("")
        self.find_count.setObjectName("Status")
        self.find_count.setMinimumWidth(70)
        self.find_count.setAlignment(Qt.AlignCenter)
        row.addWidget(self.find_count)
        for text, callback in [("↑", self.find_prev), ("↓", self.find_next), ("✕", self.hide_search)]:
            self._button(text, callback, row)
        back = QShortcut(QKeySequence("Shift+Return"), self.find_edit)
        back.setContext(Qt.WidgetShortcut)
        back.activated.connect(self.find_prev)
        close = QShortcut(QKeySequence(Qt.Key_Escape), bar)
        close.setContext(Qt.WidgetWithChildrenShortcut)
        close.activated.connect(self.hide_search)
        bar.hide()
        return bar

    def _build_global_search(self, parent):
        box = QFrame(parent)
        box.setObjectName("Overlay")
        box.setFixedSize(640, 460)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        top = QHBoxLayout()
        self.global_title = QLabel("Поиск по всем файлам")
        self.global_title.setObjectName("Title")
        top.addWidget(self.global_title)
        top.addStretch()
        close_button = QPushButton("✕")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setStyleSheet("background: transparent; padding: 4px 10px;")
        close_button.clicked.connect(self.hide_global_search)
        top.addWidget(close_button)
        layout.addLayout(top)
        self.global_edit = QLineEdit()
        self.global_edit.setPlaceholderText("Слово или фраза…")
        self.global_edit.textChanged.connect(lambda: self.global_timer.start())
        self.global_edit.returnPressed.connect(self.run_global_search)
        search_row = QHBoxLayout()
        search_row.addWidget(self.global_edit, 1)
        self.replace_button = QPushButton("Заменить…")
        self.replace_button.setToolTip("Найти и заменить во всех главах" + self.hk("replace"))
        self.replace_button.clicked.connect(self.show_replace_all)
        search_row.addWidget(self.replace_button)
        layout.addLayout(search_row)
        self.global_count = QLabel("")
        self.global_count.setObjectName("Status")
        self.global_count.setWordWrap(True)
        layout.addWidget(self.global_count)
        self.global_results = QListWidget()
        self.global_results.setWordWrap(True)
        self.global_results.itemClicked.connect(self._open_global_result)
        self.global_results.itemActivated.connect(self._open_global_result)
        self.global_results.setContextMenuPolicy(Qt.CustomContextMenu)
        self.global_results.customContextMenuRequested.connect(self._results_menu)
        layout.addWidget(self.global_results, 1)
        close = QShortcut(QKeySequence(Qt.Key_Escape), box)
        close.setContext(Qt.WidgetWithChildrenShortcut)
        close.activated.connect(self.hide_global_search)
        self.overlay_mode = "search"
        box.hide()
        return box
