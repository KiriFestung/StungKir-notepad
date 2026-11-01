# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Кто говорит. Блокнот разбирает реплики («— …, — сказала Кира.»), находит длинные цепочки
реплик, где читатель может потерять, чья очередь, и непонятные «сказала она», когда рядом две героини.
И считает, сколько реплик и слов у каждого персонажа - по книге и по главам."""

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
)

from ..core import config as C
from ..ui.dialogs import Sheet
from ..world.lore import Lore, LoreTerm
from ..core.textutil import MARKER_RE, WORD_RE, name_key, plain_markup, plural
from ..core.i18n import tr

DASHES = ("—", "–")
RUN = 4                       # столько реплик подряд без «кто говорит» - уже повод проверить
# стык реплики и слов автора: «…, — сказала», «…? — спросил», «… — Кира отвернулась»
# тире между репликой и словами автора бывает и коротким: «— Да, - сказала Кира.»
JOINT = re.compile(r"(?<=[,.!?…»\"”])\s+[—–-]\s+")
PAST = re.compile(r"[а-яё]+(?:л|ла|ло|ли|лся|лась|лось|лись)$")
SCENE_BREAK = re.compile(r"^\s*(?:#|[*~•\s]+$)")
NARRATOR = "Я (рассказчик)"
UNKNOWN = None

HOW = {"name": "по имени", "pronoun": "по местоимению", "beat": "по действию рядом", "turn": "по очерёдности"}


def name_finder(names, terms=()):
    """Функция строка -> [(начало, конец, имя)] со всеми формами имён: Кира, Киры, Кире…"""
    lore = Lore(None)
    known = {name_key(n) for n in names}
    lore.build([LoreTerm(n) for n in names] + [t for t in terms if name_key(t.name) not in known])
    characters = set(names)

    def find(text):
        return [(s, e, term.name, term.name in characters) for s, e, term in lore.spans(text)]
    return find


def segments(line):
    """Реплика по кусочкам: [(начало, конец, это ли речь)]. Первая часть - речь, дальше через тире
    чередуются слова автора и снова речь."""
    body = len(line) - len(line.lstrip())
    body += 1                                           # само тире
    while body < len(line) and line[body] == " ":
        body += 1
    parts, start, speech = [], body, True
    for m in JOINT.finditer(line, body):
        parts.append((start, m.start(), speech))
        start, speech = m.end(), not speech
    parts.append((start, len(line.rstrip()), speech))
    return [p for p in parts if p[1] > p[0]]


def _gender_of_verb(text):
    for word in re.findall(r"[а-яё]+", text.lower()):
        if PAST.fullmatch(word):
            if word.endswith(("ла", "лась")):
                return "f"
            if word.endswith(("л", "лся")):
                return "m"
    return None


class Reply:
    __slots__ = ("line", "start", "end", "speaker", "how", "words", "ambiguous")

    def __init__(self, line, start, end, words):
        self.line, self.start, self.end, self.words = line, start, end, words
        self.speaker, self.how, self.ambiguous = UNKNOWN, None, ()


class Speakers:
    """Разбор глав. genders учится по ходу: «сказала Кира» - значит, Кира - она."""

    def __init__(self, names, terms=()):
        self.find = name_finder(names, terms)
        self.names = list(names)
        self.votes = {}

    def gender(self, name):
        if name == NARRATOR:
            return None
        f, m = self.votes.get(name, (0, 0))
        if f != m:
            return "f" if f > m else "m"
        return "f" if name_key(name)[-1:] in ("а", "я") else "m"     # Кира, Ния - она; Кев - он

    def _vote(self, name, gender):
        f, m = self.votes.get(name, (0, 0))
        self.votes[name] = (f + (gender == "f"), m + (gender == "m"))

    def chapter(self, text):
        """[Reply] по порядку."""
        replies, recent = [], []          # recent - кто упоминался недавно, последний - в конце
        beat = None                       # единственное имя в абзаце прямо перед репликой
        exchange = []                     # реплики текущего разговора (без рассказа между ними)
        for number, line in enumerate(text.split("\n")):
            stripped = line.strip()
            if not stripped:
                continue
            if SCENE_BREAK.match(line):
                recent, beat, exchange = [], None, []
                continue
            if not stripped.startswith(DASHES):
                found = [n for _s, _e, n, person in self.find(MARKER_RE.sub("", line)) if person]
                recent += found
                beat = found[0] if len(set(found)) == 1 else None
                exchange = []
                continue
            parts = segments(line)
            speech = [line[s:e] for s, e, is_speech in parts if is_speech]
            words = sum(len(WORD_RE.findall(MARKER_RE.sub("", plain_markup(t)))) for t in speech)
            reply = Reply(number, parts[0][0] if parts else 0, len(line.rstrip()), words)
            for s, e, is_speech in parts:
                if is_speech:
                    continue
                author = line[s:e]
                names = [(a, n, person) for a, _b, n, person in self.find(author)]
                people = [n for _a, n, person in names if person]
                if reply.speaker is UNKNOWN and (people or names):
                    reply.speaker = people[0] if people else names[0][1]
                    reply.how = "name"
                    verb = _gender_of_verb(author)
                    if verb:
                        self._vote(reply.speaker, verb)
                elif reply.speaker is UNKNOWN:
                    lower = f" {author.lower()} "
                    pronoun = "f" if re.search(r"\bона\b", lower) else "m" if re.search(r"\bон\b", lower) else None
                    if pronoun is None and re.search(r"\bя\b", lower):
                        reply.speaker, reply.how = NARRATOR, "pronoun"
                    elif pronoun:
                        window = []
                        for name in reversed(recent[-12:]):
                            if name not in window and self.gender(name) == pronoun:
                                window.append(name)
                        if window:
                            reply.speaker, reply.how = window[0], "pronoun"
                            if len(window) > 1:
                                reply.ambiguous = tuple(window[:2])
                recent += people
            if reply.speaker is UNKNOWN and beat:
                reply.speaker, reply.how = beat, "beat"
            if reply.speaker is UNKNOWN and len(exchange) >= 2:
                a, b = exchange[-2].speaker, exchange[-1].speaker
                if a and b and a != b:
                    reply.speaker, reply.how = a, "turn"        # разговор двоих: по очереди
            if reply.speaker not in (UNKNOWN, NARRATOR):
                recent.append(reply.speaker)
            beat = None
            exchange.append(reply)
            replies.append(reply)
        return replies

    def problems(self, text, run=RUN):
        """[(первая строка, последняя строка, начало, конец, что не так)]."""
        replies = self.chapter(text)
        out = []
        streak = []

        def close():
            if len(streak) >= run:
                who = sorted({r.speaker for r in streak if r.speaker})
                between = f" (похоже, {' и '.join(who)})" if 0 < len(who) <= 2 else ""
                out.append((streak[0].line, streak[-1].line, streak[0].start, streak[-1].end,
                            f"{len(streak)} {plural(len(streak), 'реплика', 'реплики', 'реплик')} подряд "
                            f"без «кто говорит»{between}"))
        lines = text.split("\n")
        previous = None
        for reply in replies:
            unclear = reply.how in (None, "turn")
            # цепочка - реплики одна за другой, между ними только пустые строки
            follows = previous is not None and all(not line.strip() for line in lines[previous.line + 1:reply.line])
            if not unclear or not follows:
                close()
                streak = []
            if unclear:
                streak.append(reply)
            if reply.ambiguous:
                a, b = reply.ambiguous
                pronoun = "она" if self.gender(a) == "f" else "он"
                out.append((reply.line, reply.line, reply.start, reply.end,
                            f"«{pronoun}» - {a} или {b}?"))
            previous = reply
        close()
        out.sort()
        return out


def reply_stats(speakers, texts):
    """{персонаж: {"replies": n, "words": n, "chapters": {путь: (реплик, слов)}, "how": {способ: n}}}.
    Реплики, где говорящего не понять, - под ключом None."""
    stats = {}
    for path, text in texts:
        for reply in speakers.chapter(text):
            entry = stats.setdefault(reply.speaker, {"replies": 0, "words": 0, "chapters": {}, "how": {}})
            entry["replies"] += 1
            entry["words"] += reply.words
            n, w = entry["chapters"].get(path, (0, 0))
            entry["chapters"][path] = (n + 1, w + reply.words)
            entry["how"][reply.how] = entry["how"].get(reply.how, 0) + 1
    return stats


class ReplyStatsDialog(Sheet):
    """Сколько говорит каждый: реплики и слова, по всей книге или по одной главе; ниже - по главам."""

    def __init__(self, parent, speakers, texts, current=None):
        super().__init__(parent, tr("Реплики персонажей"))
        self.setMinimumSize(760, 620)
        self.speakers, self.texts = speakers, texts
        row = QHBoxLayout()
        self.scope = QComboBox()
        books = []
        for path, _t in texts:
            if path.parent.name not in books:
                books.append(path.parent.name)
        for book in books:
            self.scope.addItem(f"Книга «{book}»", ("book", book))
        if current is not None and any(p == current for p, _t in texts):
            self.scope.addItem(f"Только глава «{current.stem}»", ("chapter", current))
        if current is not None:
            index = self.scope.findData(("book", current.parent.name))
            self.scope.setCurrentIndex(max(0, index))
        self.scope.currentIndexChanged.connect(self.fill)
        row.addWidget(self.scope, 1)
        self.content.addLayout(row)
        hint = QLabel(tr("Кто говорит - по «сказала Кира», по «сказал он» (кто упоминался последним), по действию "
                      "в абзаце перед репликой и по очерёдности в разговоре двоих. Выбери персонажа - ниже будет "
                      "видно, сколько он говорит в каждой главе."))
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr(name) for name in ["Персонаж", "Реплик", "Слов", "Доля реплик"]])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._chapters)
        self.content.addWidget(self.table, 3)
        self.per_chapter = QTableWidget(0, 3)
        self.per_chapter.setHorizontalHeaderLabels([tr(name) for name in ["Глава", "Реплик", "Слов"]])
        self.per_chapter.verticalHeader().setVisible(False)
        self.per_chapter.setEditTriggers(QTableWidget.NoEditTriggers)
        self.content.addWidget(self.per_chapter, 2)
        self.summary = QLabel("")
        self.summary.setObjectName("Status")
        self.summary.setWordWrap(True)
        self.content.addWidget(self.summary)
        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton(tr("Закрыть"))
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        self.content.addLayout(buttons)
        for table in (self.table, self.per_chapter):
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.fill()

    def chosen_texts(self):
        kind, value = self.scope.currentData()
        if kind == "chapter":
            return [(p, t) for p, t in self.texts if p == value]
        return [(p, t) for p, t in self.texts if p.parent.name == value]

    def fill(self, *_):
        self.stats = reply_stats(self.speakers, self.chosen_texts())
        people = sorted((k for k in self.stats if k is not None), key=lambda k: -self.stats[k]["replies"])
        if None in self.stats:
            people.append(None)
        total = sum(s["replies"] for s in self.stats.values()) or 1
        self.rows = people
        self.table.setRowCount(len(people))
        strong = QColor(C.IMPORTANT)
        for r, name in enumerate(people):
            entry = self.stats[name]
            title = QTableWidgetItem(name if name is not None else "Не понять, кто")
            if name is None:
                title.setForeground(QColor(C.DIM))
            guessed = entry["how"].get("turn", 0)
            if guessed:
                title.setToolTip(tr("Из них {guessed} - угадано по очерёдности в разговоре").format(guessed=guessed))
            self.table.setItem(r, 0, title)
            for c, value in ((1, entry["replies"]), (2, entry["words"])):
                cell = QTableWidgetItem(f"{value:,}".replace(",", " "))
                cell.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, cell)
            share = entry["replies"] / total
            bar = QTableWidgetItem(f"{round(share * 100)}%  " + "▮" * max(1, round(share * 24)))
            bar.setForeground(strong if name is not None else QColor(C.DIM))
            self.table.setItem(r, 3, bar)
        replies = sum(s["replies"] for s in self.stats.values())
        unknown = self.stats.get(None, {}).get("replies", 0)
        self.summary.setText(tr("Всего {replies} {n}").format(replies=replies, n=plural(replies, 'реплика', 'реплики', 'реплик'))
                             + (tr(", у {unknown} не понять, кто говорит - их можно найти через «Кто говорит: "
                                   "проверить реплики»").format(unknown=unknown) if unknown else ""))
        if people:
            self.table.selectRow(0)
        else:
            self.per_chapter.setRowCount(0)

    def _chapters(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        name = self.rows[rows[0].row()]
        chapters = self.stats[name]["chapters"]
        order = [p for p, _t in self.chosen_texts() if p in chapters]
        self.per_chapter.setRowCount(len(order))
        for r, path in enumerate(order):
            n, w = chapters[path]
            self.per_chapter.setItem(r, 0, QTableWidgetItem(path.stem))
            for c, value in ((1, n), (2, w)):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignCenter)
                self.per_chapter.setItem(r, c, cell)


class SpeakersMixin:
    """«Кто говорит» и реплики персонажей. Часть главного окна."""

    def speaker_finder(self):
        self.rebuild_lore()
        terms = list(self.lore.terms) if self.lore is not None else []
        return Speakers(self.names, terms)

    def show_speaker_check(self):
        """Список мест по всем главам: длинные цепочки реплик и непонятные «сказала она». Клик - к месту."""
        if not self.names:
            self.toast.show_message(tr("Сначала добавь персонажей: «Персонажи» слева или правый клик по имени"), 3500)
        speakers = self.speaker_finder()
        texts = self.crutch_texts()
        for _path, text in texts:                         # сначала узнать, кто он, кто она
            speakers.chapter(text)
        self._open_overlay("speakers")
        self.global_results.setFocus()

        def finder(text):
            starts = [0]
            for line in text.split("\n"):
                starts.append(starts[-1] + len(line) + 1)
            for first, last, start, end, label in speakers.problems(text):
                yield starts[first] + start, starts[last] + end, label
        self._fill_results(finder, only={p for p, _t in texts})

    def show_reply_stats(self):
        speakers = self.speaker_finder()
        texts = self.crutch_texts()
        for _path, text in texts:
            speakers.chapter(text)
        if not texts:
            self.toast.show_message(tr("Пока нет глав"))
            return
        ReplyStatsDialog(self, speakers, texts, self.path if self.view is None else None).exec()
