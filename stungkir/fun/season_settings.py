# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Окно «Праздники»: включить по датам, всегда или выключить; что показывать (цвета, комнату, снег под текстом
и поверх, движение) и как горит гирлянда - режим и цвета, в том числе свои. Всё меняется сразу, без кнопки
«Применить»: настройка ложится в общие настройки, окно перерисовывается."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QColorDialog, QComboBox, QHBoxLayout, QLabel, QPushButton

from ..core import seasons
from ..core.i18n import tr
from ..ui.dialogs import Sheet


class SeasonDialog(Sheet):
    def __init__(self, window):
        super().__init__(window, tr("Праздники"))
        self.window = window
        self.setMinimumWidth(460)
        config = self._config()
        intro = QLabel(tr("Рождество: с 15 декабря по 14 января - ёлка, камин, кресла-качалки, гирлянда, "
                          "венок на часах и снег. Полоска цели заполняется снегом."))
        intro.setWordWrap(True)
        self.content.addWidget(intro)
        self.choice = QComboBox()
        for key, label in seasons.CHOICES.items():
            self.choice.addItem(tr(label), key)
        self.choice.setCurrentIndex(max(0, self.choice.findData(seasons.option(config, "season"))))
        self.choice.currentIndexChanged.connect(lambda _i: self.save("season", self.choice.currentData()))
        self.content.addWidget(self.choice)
        self.boxes = {}
        for key, label in (("season_colors", "Праздничные цвета"),
                           ("season_room", "Комната под текстом: ёлка, камин, кресла, фонарь"),
                           ("season_snow_under", "Снег под текстом"),
                           ("season_snow_over", "Снег поверх текста (затихает, пока печатаешь)"),
                           ("season_motion", "Движение: огонь, снег, огоньки, кресла")):
            box = QCheckBox(tr(label))
            box.setChecked(seasons.option(config, key))
            box.toggled.connect(lambda on, k=key: self.save(k, on))
            self.content.addWidget(box)
            self.boxes[key] = box
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Гирлянда:")))
        self.mode = QComboBox()
        for key, label in seasons.GARLAND_MODES.items():
            self.mode.addItem(tr(label), key)
        self.mode.setCurrentIndex(max(0, self.mode.findData(seasons.option(config, "season_garland"))))
        self.mode.currentIndexChanged.connect(lambda _i: self.save("season_garland", self.mode.currentData()))
        row.addWidget(self.mode, 1)
        self.palette = QComboBox()
        for key, label in seasons.GARLAND_COLORS.items():
            self.palette.addItem(tr(label), key)
        self.palette.setCurrentIndex(max(0, self.palette.findData(seasons.option(config, "season_garland_colors"))))
        self.palette.currentIndexChanged.connect(self._palette_changed)
        row.addWidget(self.palette, 1)
        self.content.addLayout(row)
        self.custom_row = QHBoxLayout()
        self.custom_row.addWidget(QLabel(tr("Свои цвета:")))
        self.swatches = []
        for i in range(5):
            button = QPushButton()
            button.setFixedSize(30, 24)
            button.clicked.connect(lambda _c=False, n=i: self.pick(n))
            self.custom_row.addWidget(button)
            self.swatches.append(button)
        self.custom_row.addStretch()
        self.content.addLayout(self.custom_row)
        self._paint_swatches(config)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close = QPushButton(tr("Закрыть"))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        close_row.addWidget(close)
        self.content.addLayout(close_row)
        self._update_enabled()

    @staticmethod
    def _config():
        from ..ui.windows import load_config_raw
        return load_config_raw()

    def save(self, key, value):
        from ..core import config as C
        config = self._config()
        config[key] = value
        C.save_config(config)
        self._update_enabled()
        self.window.update_palette(animate=True)     # праздник включился/выключился - цвета и комната

    def _palette_changed(self, _i):
        self.save("season_garland_colors", self.palette.currentData())
        self._paint_swatches(self._config())

    def _paint_swatches(self, config):
        colors = seasons.option(config, "season_custom_colors")
        custom = seasons.option(config, "season_garland_colors") == "custom"
        for i, button in enumerate(self.swatches):
            color = colors[i] if i < len(colors) else None
            button.setStyleSheet(f"background: {color}; border-radius: 4px;" if color else "border-radius: 4px;")
            button.setText("" if color else "+")
            button.setVisible(custom)
        self.custom_row.itemAt(0).widget().setVisible(custom)

    def pick(self, index):
        config = self._config()
        colors = seasons.option(config, "season_custom_colors")
        start = QColor(colors[index]) if index < len(colors) else QColor("#ffffff")
        color = QColorDialog.getColor(start, self, tr("Цвет огонька"), QColorDialog.DontUseNativeDialog)
        if not color.isValid():
            return
        colors = colors[:index] + [color.name()] + colors[index + 1:] if index < len(colors) else colors + [color.name()]
        self.save("season_custom_colors", colors)
        self._paint_swatches(self._config())

    def _update_enabled(self):
        on = self.choice.currentData() != "off"
        for widget in list(self.boxes.values()) + [self.mode, self.palette] + self.swatches:
            widget.setEnabled(on)
