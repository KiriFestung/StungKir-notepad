# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Оформление: таблица стилей Qt, палитра, скруглённые меню, плавное появление."""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QGraphicsOpacityEffect, QMenu

from ..core import config as C


TEXTURES = {"none": "ровный", "paper": "бумага лёгкая", "paper-book": "бумага книжная",
            "paper-rough": "бумага плотная", "paper-old": "бумага старая", "linen": "лён",
            "picture": "своя картинка"}


def texture_tile(kind):
    """Полупрозрачная плитка фактуры: светлые и тёмные крапинки поверх цвета фона.
    Не зависит от темы - ложится на любой фон, поэтому делается один раз и кешируется."""
    import random
    from pathlib import Path
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QImage, QPainter, QPen
    if kind in ("paper-book", "paper-rough", "paper-old"):     # настоящая фактура (art/paper, бесшовная)
        drawn = Path(__file__).resolve().parents[1] / "art" / "paper" / f"{kind.split('-')[1]}-overlay.png"
        return drawn if drawn.is_file() else None
    if kind not in ("paper", "linen"):
        return None
    drawn = Path(__file__).resolve().parents[1] / "art" / f"texture-{kind}.png"
    if drawn.is_file():                    # плитка из настоящей бумаги или льна (прозрачная, ложится на любой фон)
        return drawn
    folder = C.cache_dir()
    path = folder / f"texture-{kind}-2.png"
    if path.exists():
        return path
    size = 192
    rng = random.Random(7 if kind == "paper" else 11)
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    strength = 15 if kind == "paper" else 17
    if kind == "paper":
        coarse = [[rng.uniform(-1, 1) for _ in range(size // 8 + 1)] for _ in range(size // 8 + 1)]
    else:
        rows = [rng.uniform(-1, 1) for _ in range(size)]
        cols = [rng.uniform(-1, 1) for _ in range(size)]
    for y in range(size):
        for x in range(size):
            if kind == "paper":
                value = 0.6 * rng.uniform(-1, 1) + 0.4 * coarse[y // 8][x // 8]
            else:
                value = 0.45 * rows[y] + 0.35 * cols[x] + 0.2 * rng.uniform(-1, 1)
            alpha = int(abs(value) * strength)
            if alpha:
                image.setPixelColor(x, y, QColor(255, 255, 255, alpha) if value > 0 else QColor(0, 0, 0, alpha))
    if kind == "paper":                    # редкие волокна
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        for _ in range(26):
            x, y = rng.uniform(0, size), rng.uniform(0, size)
            dx, dy = rng.uniform(-14, 14), rng.uniform(-5, 5)
            light = rng.random() < 0.5
            painter.setPen(QPen(QColor(255, 255, 255, 14) if light else QColor(0, 0, 0, 14), 0.8))
            painter.drawLine(QPointF(x, y), QPointF(x + dx, y + dy))
        painter.end()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        image.save(str(path))
    except OSError:
        return None
    return path


def check_icon(color, shape="check"):
    """Картинка галочки (или стрелки списка, shape="arrow") нужного цвета: стили Qt умеют
    ставить её только из файла."""
    import tempfile
    from pathlib import Path
    color = QColor(color).name()
    folder = C.cache_dir()
    path = folder / f"{shape}-{color[1:]}.svg"
    if not path.exists():
        line = "M3.5 8.5l3 3 6-7" if shape == "check" else "M4 6.5l4 4 4-4"
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
               f'<path d="{line}" fill="none" stroke="{color}" stroke-width="2.2" '
               f'stroke-linecap="round" stroke-linejoin="round"/></svg>')
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path.write_text(svg, encoding="utf-8")
        except OSError:
            path = Path(tempfile.gettempdir()) / f"stungkir-{shape}-{color[1:]}.svg"
            path.write_text(svg, encoding="utf-8")
    return path.as_posix()


def _texture_rule():
    if C.TEXTURE == "picture" or getattr(C, "SEASON_ROOM", False):   # своя картинка или праздничная комната
        # рисуются самим полем (Editor.paintEvent)
        return "QTextEdit#Editor { background: transparent; }"
    tile = texture_tile(C.TEXTURE)
    if tile is None:
        return ""
    url = str(tile).replace("\\", "/")
    return (f"QTextEdit#Editor {{ background-color: {C.BG}; background-image: url({url}); "
            f"background-repeat: repeat-xy; background-attachment: fixed; }}")


def build_style():
    return f"""
QWidget {{ color: {C.TEXT}; }}
QDialog, QMessageBox {{ background: {C.PANEL}; }}
QToolTip {{ background: {C.PANEL}; color: {C.TEXT}; border: 1px solid {C.mix(C.BORDER, C.TEXT, 0.25).name()};
    padding: 7px 10px; }}

QPushButton {{ background: {C.HOVER}; border: 1px solid transparent; border-radius: 10px; padding: 8px 18px; }}
QPushButton:hover {{ background: {C.ACCENT}; }}
QPushButton:pressed {{ background: {C.SELECT}; padding-top: 9px; padding-bottom: 7px; }}
QPushButton:disabled {{ color: {C.DIM}; background: {C.PANEL}; border: 1px solid {C.BORDER}; }}
QPushButton:default {{ background: {C.IMPORTANT}; color: {C.on_color(C.IMPORTANT)};
    border: 1px solid {C.toward_contrast(C.IMPORTANT, 0.25).name()}; }}
QPushButton:default:hover {{ background: {C.toward_contrast(C.IMPORTANT, 0.16).name()}; }}
QPushButton:default:disabled {{ color: {C.DIM}; background: {C.PANEL}; border: 1px solid {C.BORDER}; }}
QPushButton[minor="true"] {{ background: transparent; color: {C.MINOR}; border: 1px solid {C.rgba(C.MINOR, 60)}; }}
QPushButton[minor="true"]:hover {{ background: {C.HOVER}; color: {C.TEXT}; }}
#Panel QPushButton[minor="true"] {{ border: none; }}

#Panel {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {C.mix(C.PANEL, C.TEXT, 0.035).name()},
    stop:1 {C.PANEL}); border: 1px solid {C.mix(C.BORDER, C.TEXT, 0.08).name()};
    border-top-color: {C.mix(C.BORDER, C.TEXT, 0.22).name()}; border-radius: 16px; }}
#Panel QPushButton {{ background: transparent; border: none; text-align: left; padding: 8px 14px;
    border-radius: 10px; }}
#Panel QPushButton:hover {{ background: {C.HOVER}; }}
#Panel QPushButton[soft="true"]:hover {{ background: transparent; }}
#Panel QPushButton:pressed {{ background: {C.ACCENT}; }}
#Panel QPushButton:checked {{ background: {C.mix(C.IMPORTANT, C.PANEL, 0.78).name()}; border-left: 3px solid {C.IMPORTANT};
    border-top-left-radius: 4px; border-bottom-left-radius: 4px; }}
#Grid QPushButton {{ background: {C.HOVER}; text-align: center; padding: 8px 0; border-radius: 9px; }}
#Grid QPushButton:hover {{ background: {C.ACCENT}; }}
#Panel #Solid {{ background: {C.HOVER}; text-align: center; }}
#Panel #Solid:hover {{ background: {C.ACCENT}; }}
#DiceResult {{ background: {C.BG}; border-radius: 14px; }}

#Panel QTreeWidget, #Panel QListWidget, #Overlay QListWidget {{
    background: transparent; border: none; outline: 0; }}
QDialog QListWidget {{ background: {C.BG}; border: none; border-radius: 12px; outline: 0; padding: 4px; }}
QTreeView {{ show-decoration-selected: 0; }}
QTreeWidget::item, QListWidget::item {{ padding: 5px 6px; border-radius: 8px; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {C.HOVER}; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: {C.SELECT}; color: {C.TEXT}; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTimeEdit {{
    background: {C.mix(C.PANEL, C.BG, 0.55).name()}; border: 1px solid {C.mix(C.BORDER, C.PANEL, 0.2).name()};
    border-radius: 10px; padding: 7px 12px; selection-background-color: {C.SELECT};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QTimeEdit:hover {{
    border-color: {C.mix(C.BORDER, C.TEXT, 0.25).name()}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus {{
    border: 1px solid {C.mix(C.ACCENT, C.TEXT, 0.4).name()}; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 0; border: none; }}
QComboBox {{ padding-right: 30px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 28px;
    border: none; background: transparent; }}
QComboBox::down-arrow {{ image: url({check_icon(C.mix(C.TEXT, C.PANEL, 0.35), "arrow")}); width: 12px; height: 12px; }}
QComboBox::down-arrow:on {{ top: 1px; }}
QComboBox QAbstractItemView {{
    background: {C.PANEL}; border: 1px solid {C.BORDER}; outline: 0;
    selection-background-color: {C.SELECT};
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 6px;
    border: 1px solid {C.mix(C.BORDER, C.TEXT, 0.2).name()}; background: {C.BG}; }}
QCheckBox::indicator:hover {{ border-color: {C.mix(C.ACCENT, C.TEXT, 0.4).name()}; }}
QCheckBox::indicator:checked {{ border-color: {C.IMPORTANT}; background: {C.IMPORTANT};
    image: url({check_icon(C.on_color(C.IMPORTANT))}); }}

#SearchBar {{ background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 18px; }}
#SearchBar QLineEdit {{ background: transparent; border: none; padding: 4px 6px; }}
#SearchBar QPushButton {{ background: transparent; border-radius: 12px; padding: 6px 10px; }}
#SearchBar QPushButton:hover {{ background: {C.HOVER}; }}
#Overlay {{ background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 18px; }}

QTextEdit {{ border: none; background: {C.BG}; selection-background-color: {C.SELECT};
    selection-color: {C.TEXT}; }}
{_texture_rule()}
QDialog QTextEdit {{ border-radius: 12px; }}
#SidePane {{ background: {C.BG}; border-left: 1px solid {C.BORDER}; }}
#SidePane QTextEdit {{ background: {C.BG}; color: {C.TEXT}; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {C.HOVER}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 6px 2px; }}
QScrollBar::handle:vertical {{ background: {C.SCROLL}; border-radius: 3px; min-height: 48px; }}
QScrollBar::handle:vertical:hover {{ background: {C.ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px 6px; }}
QScrollBar::handle:horizontal {{ background: {C.SCROLL}; border-radius: 3px; min-width: 40px; }}
QScrollBar::handle:horizontal:hover {{ background: {C.ACCENT}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

QMenu {{ background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px; padding: 6px; }}
QMenu[flat="true"] {{ border-radius: 0px; }}
QMenu::item {{ padding: 8px 22px 8px 16px; border-radius: 8px; margin: 1px 0; }}
QMenu::item:selected {{ background: {C.SELECT}; }}
QMenu::item:disabled {{ color: {C.DIM}; }}
QMenu::separator {{ height: 1px; background: {C.BORDER}; margin: 4px 10px; }}

QTableWidget {{ background: {C.BG}; border: none; gridline-color: {C.BORDER};
    selection-background-color: {C.SELECT}; selection-color: {C.TEXT}; outline: 0; }}
QTableWidget::item {{ padding: 6px 8px; }}
QHeaderView {{ background: {C.BG}; }}
QHeaderView::section {{ background: {C.PANEL}; color: {C.DIM}; border: none;
    border-right: 1px solid {C.BORDER}; border-bottom: 1px solid {C.BORDER}; padding: 8px 10px; }}
QTableCornerButton::section {{ background: {C.PANEL}; border: none; }}
#TableBar QPushButton {{ background: transparent; padding: 6px 12px; }}
#TableBar QPushButton:hover {{ background: {C.HOVER}; }}
#Board {{ background: {C.BG}; }}
#Column {{ background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 14px; }}
#Column QListWidget {{ background: transparent; border: none; outline: 0; }}
#Column QListWidget::item {{ background: transparent; padding: 0; }}
#Column QListWidget::item:hover, #Column QListWidget::item:selected {{ background: transparent; }}
#Column QPushButton {{ background: transparent; padding: 4px 10px; }}
#Column QPushButton:hover {{ background: {C.HOVER}; }}
#Swatch {{ border-radius: 12px; min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
    padding: 0; border: 2px solid transparent; }}
#Swatch:checked {{ border: 2px solid {C.TEXT}; }}
QDialog#Sheet {{ background: transparent; }}
#DialogCard {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {C.mix(C.PANEL, C.TEXT, 0.035).name()},
    stop:1 {C.PANEL}); border: 1px solid {C.mix(C.BORDER, C.TEXT, 0.08).name()};
    border-top-color: {C.mix(C.BORDER, C.TEXT, 0.22).name()}; border-radius: 16px; }}
#DialogCard[flat="true"] {{ border-radius: 0px; }}
#DialogTitle {{ font-size: 12pt; padding: 2px 2px; }}
#DialogClose {{ background: transparent; padding: 2px 9px; border-radius: 8px; }}
#DialogClose:hover {{ background: {C.HOVER}; }}
#Primary {{ background: {C.IMPORTANT}; color: {C.on_color(C.IMPORTANT)}; }}
#Primary:hover {{ background: {C.toward_contrast(C.IMPORTANT, 0.16).name()}; }}
#Panel #Primary {{ background: {C.IMPORTANT}; color: {C.on_color(C.IMPORTANT)}; text-align: center; }}
#Panel #Primary:hover {{ background: {C.toward_contrast(C.IMPORTANT, 0.16).name()}; }}
#ColorButton {{ border: 1px solid {C.BORDER}; border-radius: 8px; padding: 8px 6px; }}
#Section {{ color: {C.DIM}; padding-top: 6px; }}
#Status {{ color: {C.DIM}; }}
#PanelScroll, #PanelInner {{ background: transparent; border: none; }}
QPushButton#Link {{ background: transparent; color: {C.DIM}; text-decoration: underline; padding: 4px 2px; }}
QPushButton#Link:hover {{ color: {C.TEXT}; }}
#Code {{ background: {C.BG}; color: {C.TEXT}; border: 1px solid {C.BORDER}; border-radius: 10px; padding: 14px; }}
#Title {{ color: {C.DIM}; padding: 8px 14px 3px 14px; font-size: 8pt; }}
#Error {{ color: {C.CRIT_LOW}; }}
#Toast {{ background: transparent; border: none; padding: 9px 22px 13px 32px; font-size: 10pt; }}
#Hint {{ background: {C.HINT}; border-radius: 2px; }}
"""


_TRANSLUCENT = {"value": None, "at": 0.0}


def _x11_compositor():
    """Работает ли в X11 композитор (тот, кто рисует прозрачность и тени). Без него всё
    прозрачное вокруг окна выходит чёрным."""
    import ctypes
    import ctypes.util
    try:
        x11 = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XDefaultScreen.argtypes = [ctypes.c_void_p]
        x11.XInternAtom.restype = ctypes.c_ulong
        x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x11.XGetSelectionOwner.restype = ctypes.c_ulong
        x11.XGetSelectionOwner.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        display = x11.XOpenDisplay(None)
        if not display:
            return False
        try:
            atom = x11.XInternAtom(display, f"_NET_WM_CM_S{x11.XDefaultScreen(display)}".encode(), 0)
            return x11.XGetSelectionOwner(display, atom) != 0
        finally:
            x11.XCloseDisplay(display)
    except (OSError, AttributeError):
        return False


def translucency_ok():
    """Можно ли рисовать окна с прозрачными краями (скругления, мягкая тень).
    Нет - окна и меню рисуются простыми прямоугольниками, без чёрной каймы."""
    import time
    if C.FLAT_WINDOWS:
        return False
    from PySide6.QtGui import QGuiApplication
    platform = QGuiApplication.platformName()
    if platform in ("wayland", "windows", "cocoa", "offscreen"):
        return True
    if platform != "xcb":
        return False
    now = time.monotonic()
    if _TRANSLUCENT["value"] is None or now - _TRANSLUCENT["at"] > 30:
        _TRANSLUCENT.update(value=_x11_compositor(), at=now)
    return _TRANSLUCENT["value"]


def frameless_menu(menu):
    """Скруглённое меню без системной рамки, если прозрачность работает. Пунктам - значки по надписи."""
    from .icons import decorate_menu
    menu.aboutToShow.connect(lambda m=menu: decorate_menu(m))
    if translucency_ok():
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
    else:
        menu.setProperty("flat", True)
    return menu


def rounded_menu(parent):
    return frameless_menu(QMenu(parent))


def fade(widget, start, end, duration, on_done=None):
    """Плавно меняет прозрачность виджета. Возвращает анимацию."""
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    old = getattr(widget, "_fade_anim", None)
    if old is not None:
        old.stop()
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(effect.opacity() if start is None else start)
    anim.setEndValue(end)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    if on_done:
        anim.finished.connect(on_done)
    widget._fade_anim = anim
    anim.start()
    return anim


def apply_theme(app):
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in [
        (QPalette.Window, C.BG), (QPalette.WindowText, C.TEXT), (QPalette.Base, C.BG),
        (QPalette.AlternateBase, C.PANEL), (QPalette.Text, C.TEXT), (QPalette.Button, C.PANEL),
        (QPalette.ButtonText, C.TEXT), (QPalette.Highlight, C.SELECT),
        (QPalette.HighlightedText, C.TEXT), (QPalette.ToolTipBase, C.PANEL),
        (QPalette.ToolTipText, C.TEXT), (QPalette.PlaceholderText, C.DIM),
    ]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    ui_font = QFont(C.FONT_FAMILY, 11)
    ui_font.setBold(True)
    app.setFont(ui_font)
    app.setStyleSheet(build_style())
