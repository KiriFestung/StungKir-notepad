# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Пример-проект для первого запуска: маленькая книга с главами, справочником мира, доской и хронологией.
Видно, что умеет блокнот, и всё это убирается одной кнопкой («Ещё → Файлы и импорт → Убрать пример»)."""

import json

from ..core import config as C
from ..world.lore import load_lore_config, save_lore_config
from ..core.storage import save_order, save_text
from ..core import i18n
from ..core.i18n import tr

BOOK = "Пример · Туман над рекой"
WORLD = "Пример · Мир"
MARK = ".sample.json"

README = """# Прочитай меня
Это учебная книжка. Здесь всё можно трогать: править, двигать, удалять. Когда надоест - «Ещё → Файлы и импорт → Убрать пример», и она уйдёт в корзину.
Подведи мышь к левому краю окна - там главы, поиск, режимы и меню «Ещё». У правого края - знаки, таймер с лаской и кубики.
Реплика начинается с тире и подсвечивается своим цветом:
— Вот так, - сказала Тервена.
Наведи мышь на Тервену, Давнь или Кев: это термины из справочника «Пример · Мир», у каждого есть описание. Ctrl+клик откроет его сбоку.
[для себя - в книгу не попадёт] Так выглядят квадратные скобки. Список всех таких мест по главам - кнопка «Пометки» слева.
*Курсив* и **жирный** - звёздочками; в собранной книге звёздочек не будет.
Повтор повтор слова рядом подчёркивается, ашибка - красным.
Открой «План» - это доска сюжета на пробке: карточки, булавки и нитки. Переключатель «Колонки» сверху раскладывает их стопками.
«Хронология» - события мира по годам своего летоисчисления.
F8 - режим фокуса, F9 - печатная машинка, F10 - без отвлечений, F1 - все клавиши.
"""

CHAPTER_1 = """# Глава 1
Утро было серым. Тервена стояла у окна и смотрела, как туман ложится на реку и прячет дальний берег.
— Лодки не будет, - сказала она. - Не сегодня.
Хозяин постоялого двора пожал плечами и вернулся к очагу. В Давни уже звонили колокола [проверить, сколько их], и *никто* не ждал **гостей** с юга.
— А если туман уйдёт к полудню?
— Не уйдёт. Он здесь до весны.
Она надела плащ, проверила нож у пояса и вышла на мокрые доски причала.
"""

CHAPTER_2 = """# Глава 2
Посол Кева пришёл вечером. Он долго молчал, грел руки у огня и смотрел на карту, словно мог передвинуть горы взглядом.
— Перевал закроют через неделю, - сказал он наконец.
— Тогда пойдём через неделю и один день, - ответила Тервена.
Посол усмехнулся, но спорить не стал.
* * *
Ночью пошёл снег.
"""

WORLD_NOTES = {
    "Тервена": "Также: Тервенская республика\nПрибрежное государство на юге. Столица - *Лосс*. Живёт торговлей солью и рыбой.",
    "Давнь": "Горная страна двенадцати кланов. Колокола звонят, когда закрывается перевал.",
    "Кев": "Маленькое княжество в предгорьях. Его послы осторожны и редко говорят первыми.",
}

PLAN = {
    "mode": "free",
    "columns": [
        {"title": "Завязка", "cards": [
            {"id": "s1", "title": "Туман над рекой", "text": "Лодки не будет. Тервена решает идти сама.",
             "color": "purple", "chapter": f"{BOOK}/Глава 1.txt", "x": 60, "y": 60},
            {"id": "s2", "title": "Посол Кева", "text": "Предупреждает о перевале.", "color": "amber",
             "chapter": f"{BOOK}/Глава 2.txt", "x": 360, "y": 40}]},
        {"title": "Развитие", "cards": [
            {"id": "s3", "title": "Перевал", "text": "Снег, кланы Давни, чужие следы.", "color": "green", "x": 660, "y": 80},
            {"id": "s4", "title": "Кто знал заранее?", "text": "Кто-то в совете знал о тумане.", "color": "coral",
             "x": 330, "y": 260}]},
        {"title": "Развязка", "cards": [
            {"id": "s5", "title": "Последний мост", "text": "Всё решится на реке.", "color": "purple", "x": 640, "y": 300}]},
    ],
    "links": [["s1", "s4"], ["s2", "s4"], ["s4", "s5"]],
}

TIMELINE = {"events": [
    {"when": "312 г. Второй эры", "year": 312, "title": "Основан Лосс", "text": "Рыбаки строят первый причал.", "color": "none"},
    {"when": "Зима 590 г.", "year": 590, "title": "Перевал закрыт на год", "text": "Давнь и Тервена не торгуют.",
     "color": "coral"},
    {"when": "Осень 614 г.", "year": 614, "title": "Туман над рекой", "text": "Начало книги.", "color": "purple",
     "chapter": f"{BOOK}/Глава 1.txt"},
]}


def has_sample():
    return (C.service_path(MARK)).exists()


def _content():
    """Пример на языке интерфейса: (книга, мир, [(файл, текст)], заметки мира)."""
    if i18n.LANG != i18n.DEFAULT:
        from . import sample_en as E
        files = [(E.README_NAME, E.README), (E.CHAPTER_1_NAME, E.CHAPTER_1), (E.CHAPTER_2_NAME, E.CHAPTER_2),
                 (E.BOARD_NAME, json.dumps(E.PLAN, ensure_ascii=False, indent=1) + "\n"),
                 (E.TIMELINE_NAME, json.dumps(E.TIMELINE, ensure_ascii=False, indent=1) + "\n")]
        return E.BOOK, E.WORLD, files, E.WORLD_NOTES
    files = [("Прочитай меня.txt", README), ("Глава 1.txt", CHAPTER_1), ("Глава 2.txt", CHAPTER_2),
             ("План.board", json.dumps(PLAN, ensure_ascii=False, indent=1) + "\n"),
             ("Хронология.timeline", json.dumps(TIMELINE, ensure_ascii=False, indent=1) + "\n")]
    return BOOK, WORLD, files, WORLD_NOTES


def create_sample():
    """Кладёт пример в папку с текстами. Возвращает путь к «Прочитай меня»."""
    book_name, world_name, files, notes = _content()
    book, world = C.ROOT / book_name, C.ROOT / world_name
    book.mkdir(parents=True, exist_ok=True)
    world.mkdir(parents=True, exist_ok=True)
    for name, text in files:
        if not (book / name).exists():
            save_text(book / name, text)
    save_order(book, [name for name, _t in files])
    for name, note in notes.items():
        if not (world / f"{name}.txt").exists():
            save_text(world / f"{name}.txt", note)
    config = load_lore_config()
    if world_name not in config["categories"]:
        config["categories"].append(world_name)
        save_lore_config(config)
    (C.service_path(MARK)).write_text(json.dumps({"folders": [book_name, world_name]}, ensure_ascii=False),
                                      encoding="utf-8")
    return book / files[0][0]


def sample_folders():
    try:
        names = json.loads((C.service_path(MARK)).read_text(encoding="utf-8")).get("folders", [])
    except (OSError, ValueError):
        names = [BOOK, WORLD]
    return [C.ROOT / n for n in names if (C.ROOT / n).is_dir()]


def remove_sample(to_trash):
    """Пример - в корзину (вдруг там уже что-то своё дописано)."""
    folders = sample_folders()
    for folder in folders:
        to_trash(folder)
    from .sample_en import WORLD as WORLD_EN
    config = load_lore_config()
    gone = [name for name in config["categories"] if name in (WORLD, WORLD_EN) or name in [f.name for f in folders]]
    if gone:
        config["categories"] = [name for name in config["categories"] if name not in gone]
        save_lore_config(config)
    (C.service_path(MARK)).unlink(missing_ok=True)


def is_fresh():
    """В папке с текстами ещё ничего нет - значит, первый запуск."""
    if not C.ROOT.is_dir():
        return True
    return not any(p.is_dir() and not p.name.startswith(".") for p in C.ROOT.iterdir())


class SampleMixin:
    """Пример-проект. Часть главного окна."""

    def add_sample(self):
        readme = create_sample()
        self.lore_cfg = load_lore_config()          # «Пример · Мир» - справочник
        self.rebuild_lore()
        self.refresh_tree()
        self.open_path(readme)
        self.toast.show_message(tr("Пример добавлен. Убрать - «Ещё → Файлы и импорт → Убрать пример»"), 4000)

    def drop_sample(self):
        from PySide6.QtWidgets import QMessageBox
        from ..ui.dialogs import ask_question
        from ..core.trash import move_to_trash
        answer = ask_question(self, tr("Убрать пример"), tr("Убрать пример в корзину? Оттуда его можно вернуть 30 дней."))
        if answer != QMessageBox.Yes:
            return
        if self.path is not None and any(f in self.path.parents for f in sample_folders()):
            if self.is_modified():
                self.save()
            self.path = None
            self.load_text("")
            self.update_title()
        remove_sample(move_to_trash)
        self.lore_cfg = load_lore_config()
        self.rebuild_lore()
        self.refresh_tree()
        self.toast.show_message(tr("Пример в корзине. Чистый лист!"))
