# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Значки кнопок и иконка программы."""

from pathlib import Path

from PySide6.QtGui import QColor, QIcon, QPixmap

from ..core import config as C


# Значки кнопок: простые линии, цвет подставляется из темы
ICONS = {
    "create": '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v8M8 12h8"/>',
    "save": '<path d="M5 4h11l3 3v13H5z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    "marker": '<path d="M7 4h10v16l-5-4-5 4z"/>',
    "people": '<circle cx="12" cy="8" r="3.6"/><path d="M5 20c1.3-3.6 4-5.5 7-5.5s5.7 1.9 7 5.5"/>',
    "versions": '<circle cx="12" cy="12" r="8"/><path d="M12 8v4.3l3 1.9"/>',
    "book": '<path d="M3 5.5c3-1 6-1 9 1 3-2 6-2 9-1v13c-3-1-6-1-9 1-3-2-6-2-9-1z"/><path d="M12 6.5v13"/>',
    "focus": '<path d="M2.5 12s3.6-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.6 6.5-9.5 6.5S2.5 12 2.5 12z"/>'
             '<circle cx="12" cy="12" r="2.8"/>',
    "typewriter": '<path d="M4 7.5h16M4 12h16M4 16.5h10"/>',
    "forward": '<path d="M5 12h13M13 6.5l5.5 5.5-5.5 5.5"/>',
    "more": '<circle cx="5.5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18.5" cy="12" r="1.2"/>',
    # для остальных кнопок и пунктов меню - подбираются по надписи, см. icon_for_text
    "close": '<path d="M7 7l10 10M17 7L7 17"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "trash": '<path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13M10 11v5.5M14 11v5.5"/>',
    "open": '<path d="M3.5 7V5h6l2 2h9v3"/><path d="M3.5 7v12h15l2.5-9H6.5L3.5 19"/>',
    "replace": '<path d="M4 9h12l-3-3M20 15H8l3 3"/>',
    "dice": '<rect x="4.5" y="4.5" width="15" height="15" rx="3.5"/><circle cx="9" cy="9" r=".9"/>'
            '<circle cx="15" cy="15" r=".9"/><circle cx="12" cy="12" r=".9"/>',
    "coin": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="5"/><path d="M12 9.5v5"/>',
    "shuffle": '<path d="M3.5 7h3.5c4.5 0 5.5 10 10 10h3.5M17.5 14l3 3-3 3"/><path d="M3.5 17h3.5c1.6 0 2.6-1.2 3.5-3'
               'M13.5 10c.9-1.8 1.9-3 3.5-3h3.5M17.5 4l3 3-3 3"/>',
    "flag": '<path d="M6.5 20.5V4M6.5 4.5h11l-2.5 4 2.5 4h-11"/>',
    "drum": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="7.3" r="1.7"/><circle cx="16.1" cy="9.7" r="1.7"/>'
            '<circle cx="16.1" cy="14.3" r="1.7"/><circle cx="12" cy="16.7" r="1.7"/><circle cx="7.9" cy="14.3" r="1.7"/>'
            '<circle cx="7.9" cy="9.7" r="1.7"/>',
    "play": '<path d="M8 5.5v13l10.5-6.5z"/>',
    "stop": '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8'
                'M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8"/>',
    "palette": '<path d="M12 3.5a8.5 8.5 0 1 0 0 17c1.4 0 1.9-1 1.4-2.1-.6-1.3.2-2.4 1.6-2.4H17a3.5 3.5 0 0 0 3.5-3.5'
               'C20.5 7.3 16.7 3.5 12 3.5z"/><circle cx="8" cy="11" r=".9"/><circle cx="11" cy="7.5" r=".9"/>'
               '<circle cx="15.5" cy="8.5" r=".9"/>',
    "export": '<path d="M12 15V4M7.5 8.5L12 4l4.5 4.5M5 14v6h14v-6"/>',
    "import": '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 14v6h14v-6"/>',
    "copy": '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V5.5a1 1 0 0 0-1-1h-9a1 1 0 0 0-1 1v9'
            'a1 1 0 0 0 1 1h3"/>',
    "edit": '<path d="M4.5 19.5l1-4.5L16 4.5l3.5 3.5L9 18.5zM13.5 7l3.5 3.5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "chart": '<path d="M4.5 19.5h15M7.5 16v-5M12 16V7M16.5 16v-8"/>',
    "wave": '<path d="M3 12h2.5l2-5 3 10 3-13 3 11 2-3H21"/>',
    "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/>',
    "calendar": '<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    "speaker": '<path d="M4.5 9.5h3.5l5-4v13l-5-4H4.5z"/><path d="M16.5 9a4.5 4.5 0 0 1 0 6M19 6.5a8 8 0 0 1 0 11"/>',
    "speech": '<path d="M4.5 6.5h15v9h-8l-4.5 3.5v-3.5H4.5z"/><path d="M8.5 10.5h7"/>',
    "stamp": '<path d="M9.5 4.5h5l-1 7h-3z"/><path d="M5 15.5h14v2.5H5zM6.5 20h11"/><path d="M10.5 11.5l-1 4M13.5 11.5l1 4"/>',
    "undo": '<path d="M8.5 7.5L4.5 11.5l4 4"/><path d="M4.5 11.5H15a4.5 4.5 0 0 1 0 9h-2.5"/>',
    "lock": '<rect x="5.5" y="10.5" width="13" height="9.5" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>',
    "unlock": '<rect x="5.5" y="10.5" width="13" height="9.5" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 6.8-1.2"/>',
    "key": '<circle cx="8" cy="15" r="3.5"/><path d="M10.5 12.5L19 4M15.5 7.5l2.5 2.5M17.5 5.5l2 2"/>',
    "shield": '<path d="M12 3.5l7 2.5v5.5c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z"/>',
    "template": '<rect x="4.5" y="4.5" width="15" height="15" rx="2"/><path d="M4.5 9.5h15M9.5 9.5v10"/>',
    "timeline": '<path d="M4 12h16"/><circle cx="7" cy="12" r="1.8"/><circle cx="13" cy="12" r="1.8"/>'
                '<circle cx="18" cy="12" r="1.8"/><path d="M7 10V6M13 14v4"/>',
    "board": '<rect x="4" y="4.5" width="4.5" height="15" rx="1.2"/><rect x="9.8" y="4.5" width="4.5" height="10" rx="1.2"/>'
             '<rect x="15.5" y="4.5" width="4.5" height="12.5" rx="1.2"/>',
    "table": '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M4 10h16M4 14.5h16M10 10v9"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.2"/>',
    "keyboard": '<rect x="3" y="6.5" width="18" height="11" rx="2"/><path d="M6.5 10h1M10 10h1M13.5 10h1M17 10h.5M8 14h8"/>',
    "zen": '<path d="M12 4.5c3 3 3 7 0 9-3-2-3-6 0-9z"/><path d="M4 14c3 0 5.5 1 8 4 2.5-3 5-4 8-4"/>',
    "fullscreen": '<path d="M4.5 9V4.5H9M15 4.5h4.5V9M19.5 15v4.5H15M9 19.5H4.5V15"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2"/>',
    "texture": '<rect x="4.5" y="4.5" width="15" height="15" rx="2"/><path d="M4.5 11l6.5-6.5M4.5 17.5l13-13'
               'M10 19.5l9.5-9.5"/>',
    "font": '<path d="M5 19.5L11 4.5h2l6 15M7.5 14h9"/>',
    "split": '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M12 5v14"/>',
    "note": '<path d="M5 4.5h14v10l-5 5H5z"/><path d="M14 19.5v-5h5M8.5 9h7M8.5 12.5h4"/>',
    "camera": '<path d="M4 8h3.5l1.5-2.5h6L16.5 8H20v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    "moon": '<path d="M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "list": '<path d="M9 7h11M9 12h11M9 17h11"/><circle cx="5" cy="7" r=".9"/><circle cx="5" cy="12" r=".9"/>'
            '<circle cx="5" cy="17" r=".9"/>',
    "up": '<path d="M12 19V5M6.5 10.5L12 5l5.5 5.5"/>',
    "down": '<path d="M12 5v14M6.5 13.5L12 19l5.5-5.5"/>',
}

# надпись кнопки или пункта меню -> значок. Первое совпадение по началу слов
TEXT_ICONS = [
    ("снять пароль", "unlock"), ("поставить пароль", "lock"), ("сменить пароль", "key"), ("новый код", "key"),
    ("войти по коду", "key"), ("пароль", "lock"), ("код восстановления", "key"),
    ("сохранить как шаблон", "template"), ("сохранить", "save"), ("отменить", "undo"), ("отмена", "close"), ("закрыть", "close"),
    ("готово", "check"), ("применить", "check"), ("понятно", "check"), ("ок", "check"), ("да", "check"),
    ("войти", "unlock"),
    ("удалить", "trash"), ("убрать", "trash"), ("стереть", "trash"), ("очистить", "trash"),
    ("открыть", "open"), ("найти и заменить", "replace"), ("заменить", "replace"), ("найти", "search"),
    ("поиск", "search"), ("бросить", "dice"), ("подбросить", "coin"), ("монета", "coin"), ("рандомайзеры", "drum"), ("случайное", "shuffle"),
    ("старт", "play"), ("стоп", "stop"), ("настройки", "settings"), ("настроить цвета", "palette"),
    ("цвета", "palette"), ("вид, тема", "palette"), ("темы", "palette"), ("собрать книгу", "book"),
    ("экспорт", "export"), ("импорт", "import"), ("скопировать", "copy"), ("копировать", "copy"),
    ("переименовать", "edit"), ("изменить", "edit"), ("правка", "edit"), ("добавить", "plus"),
    ("новая точка", "flag"), ("новая", "plus"), ("новое", "plus"), ("новый", "plus"), ("создать", "create"),
    ("статистика", "chart"), ("ритм", "wave"), ("цель", "target"), ("цели", "target"), ("дедлайн", "calendar"),
    ("календарь", "calendar"), ("читать вслух", "speaker"), ("кто говорит", "speech"), ("реплики", "speech"),
    ("кто в какой", "people"), ("персонаж", "people"), ("проверить написание", "check"),
    ("мои штампы", "stamp"), ("найти мои штампы", "stamp"), ("версии", "versions"), ("версия", "versions"),
    ("вернуть", "undo"), ("откатить", "undo"), ("сбросить", "undo"), ("восстановить", "undo"),
    ("точки возврата", "flag"), ("вернуться к точке", "undo"), ("снимок", "camera"), ("снимки", "camera"), ("резервн", "shield"), ("пароль и копии", "shield"),
    ("справочник", "book"), ("шаблон", "template"), ("хронолог", "timeline"), ("доск", "board"),
    ("таблиц", "table"), ("пометки", "marker"), ("режим фокуса", "focus"), ("печатная машинка", "typewriter"),
    ("только вперёд", "forward"), ("о программе", "info"), ("горячие клавиши", "keyboard"),
    ("без отвлечений", "zen"), ("во весь экран", "fullscreen"), ("часы", "clock"), ("фон под текстом", "texture"),
    ("шрифт", "font"), ("рядом", "split"), ("заметк", "note"), ("ночной", "moon"), ("тёплый", "moon"),
    ("связать", "link"), ("главу", "book"), ("главы", "book"), ("список", "list"), ("ещё", "more"),
]


_reverse = None


def as_russian(clean):
    """Надпись на другом языке -> русская: значки и «тихие» кнопки узнаются по русским словам.
    Не нашлась - как есть."""
    global _reverse
    from ..core import i18n
    if i18n.LANG == i18n.DEFAULT or not clean:
        return clean
    if _reverse is None:
        from ..core.lang_en import EN
        pairs = {}
        for russian, english in EN.items():
            for variant in (english, i18n.british(english)):
                key = variant.replace("&", "").strip().lower().lstrip("+−-✕… ").strip().rstrip("…. ")
                if len(key) >= 2:
                    pairs.setdefault(key, russian.strip().lower().lstrip("+−-✕… ").strip())
        _reverse = sorted(pairs.items(), key=lambda kv: -len(kv[0]))
    for english, russian in _reverse:
        if clean == english or (len(english) > 3 and clean.startswith(english + " ")):
            return russian + clean[len(english):]
    return clean


def icon_for_text(text):
    """Значок по надписи: «Сохранить» - дискета, «Отмена» - крестик. Не узнал - None."""
    clean = as_russian(text.replace("&", "").strip().lower().lstrip("+−-✕… ").strip().rstrip("…. "))
    if not clean:
        return None
    for key, name in TEXT_ICONS:
        if len(key) <= 2:
            if clean == key:
                return name
        elif clean.startswith(key) or f" {key}" in f" {clean}":
            return name
    return None


_made = {}


DRAWN = Path(__file__).resolve().parents[1] / "art" / "icons"


def _drawn_icon(name, color):
    """Нарисованный значок (art/icons/<имя>.png - линия на прозрачном, толщина как у остальных):
    перекрашивается в цвет темы по прозрачности. Нет файла - None, берётся значок из линий ниже."""
    path = DRAWN / f"{name}.png"
    if not path.is_file():
        return None
    from PySide6.QtGui import QImage, QPainter
    mask = QImage(str(path))
    if mask.isNull():
        return None
    image = QImage(mask.size(), QImage.Format_ARGB32_Premultiplied)
    image.fill(QColor(color))
    p = QPainter(image)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    p.drawImage(0, 0, mask)
    p.end()
    return QIcon(QPixmap.fromImage(image))


def make_icon(name, color=None):
    key = (name, QColor(color or C.TEXT).name())
    if key in _made:
        return _made[key]
    drawn = _drawn_icon(name, color or C.TEXT)
    if drawn is not None:
        _made[key] = drawn
        return drawn
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color or C.TEXT}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
           f'{ICONS[name]}</svg>')
    # рисуем крупно (96 точек): значок чёткий и на экранах с увеличением, и рядом с нарисованными
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    image = QImage(96, 96, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(p)
    p.end()
    icon = _made[key] = QIcon(QPixmap.fromImage(image))
    return icon


MINOR_TEXTS = ("отмена", "закрыть", "стереть историю", "пропустить", "не сейчас", "позже", "сбросить")


def decorate_button(button):
    """Значок кнопке по её надписи, цветом надписи. Свой значок у кнопки не трогается.
    «Отмена», «Закрыть» и подобные (если это не главная кнопка окна) - неважные: тише остальных."""
    clean = as_russian(button.text().replace("&", "").strip().lower().rstrip("…. "))
    minor = (clean in MINOR_TEXTS and button.objectName() != "Primary" and not button.isDefault()
             and not button.property("noIcon"))
    if bool(button.property("minor")) != minor:
        button.setProperty("minor", minor)
        button.style().unpolish(button)          # стиль кнопки зависит от этого свойства
        button.style().polish(button)
    own = button.property("autoIcon") or ""
    if (not own and not button.icon().isNull()) or button.property("noIcon"):
        return
    name = icon_for_text(button.text())
    if name is None:
        if own:
            button.setIcon(QIcon())
            button.setProperty("autoIcon", "")
        return
    if button.objectName() == "Primary" or button.isDefault():
        color = C.on_color(C.IMPORTANT)
    elif button.property("minor"):
        color = C.MINOR
    else:
        color = C.TEXT
    button.setIcon(make_icon(name, color))
    button.setProperty("autoIcon", name)


def decorate(widget):
    """Значки всем кнопкам внутри окна (и перекраска при смене темы)."""
    from PySide6.QtWidgets import QPushButton
    for button in widget.findChildren(QPushButton):
        decorate_button(button)


def decorate_menu(menu):
    """Значки пунктам меню. Пункты с галочкой не трогаем: галочка важнее значка."""
    for action in menu.actions():
        if action.isSeparator() or action.isCheckable() or action.property("noIcon"):
            continue
        own = action.property("autoIcon") or ""
        if not own and not action.icon().isNull():
            continue
        name = icon_for_text(action.text())
        if name:
            action.setIcon(make_icon(name, C.TEXT))
            action.setProperty("autoIcon", name)


# запасная иконка, если картинки ласки нет: индиговый круг с охристой «S» (старая лиса удалена)
FALLBACK_ICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
                     '<circle cx="128" cy="128" r="116" fill="#2e2a6e" stroke="#d4a02e" stroke-width="12"/>'
                     '<path d="M168 82c-12-14-58-18-64 8s56 26 54 56-58 30-70 12" fill="none" stroke="#d4a02e" '
                     'stroke-width="22" stroke-linecap="round"/></svg>\n')

APP_ICON_PNG = Path(__file__).resolve().parents[1] / "art" / "app-icon.png"


def _app_icon_svg():
    """Иконка программы - ласка (art/app-icon.png), завёрнутая в SVG: ярлыки Linux берут SVG.
    Нет картинки - запасная из линий."""
    try:
        import base64
        data = base64.b64encode(APP_ICON_PNG.read_bytes()).decode("ascii")
    except OSError:
        return FALLBACK_ICON_SVG
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            'viewBox="0 0 256 256" width="256" height="256">'
            f'<image width="256" height="256" xlink:href="data:image/png;base64,{data}"/></svg>\n')


ICON_SVG = _app_icon_svg()
