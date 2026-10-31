# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Поле текста: подсветка, орфография, печатная машинка, заметки на полях."""

import html
import json
import re
from contextlib import contextmanager
from pathlib import Path
from PySide6.QtCore import (
    QAbstractAnimation, QEasingCurve, QEvent, QObject, QPoint, QPointF, QPropertyAnimation,
    QRectF, QSizeF, Qt, QVariantAnimation,
)
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QKeySequence, QPainter, QPen, QSyntaxHighlighter,
    QTextBlockFormat, QTextCharFormat, QTextCursor,
)
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QToolTip, QVBoxLayout, QWidget,
)

from ..core import config as C
from ..ui.style import rounded_menu
from ..core.textutil import (CYR_PART, CYR_WORD, EMPH_RE, MARKER_RE, PUNCT_RE, STOP_WORDS, WORD_RE, Crutches,
    anchor_notes, clean_pasted, has_foreign, is_board, is_table, is_timeline, name_key, parse_table, position_map,
    stem, word_root)
from ..core.storage import LockedFile, read_text


HEADING_LINE_RE = re.compile(r"^(\s*#{1,3}\s+)\S")


# ---------------- орфография ----------------
DICTIONARY_DIRS = [Path(__file__).resolve().parents[1] / "dictionaries", Path("/usr/share/hunspell"),
                   Path("/usr/share/myspell/dicts"), Path("/app/share/hunspell")]


class Speller:
    """Русская проверка орфографии. Обычно через системный Hunspell (pyenchant + hunspell-ru);
    если его нет (Windows, Flatpak) - встроенным словарём через spylls."""

    def __init__(self, personal):
        self.dict = None          # enchant
        self.spylls = None        # запасной вариант
        self.personal_path = personal
        self.personal = set()
        self.cache = {}
        self.version = 0
        try:
            personal.parent.mkdir(parents=True, exist_ok=True)
            personal.touch(exist_ok=True)
        except OSError:
            pass
        try:
            import enchant
            for lang in ("ru_RU", "ru"):
                if enchant.dict_exists(lang):
                    self.dict = enchant.DictWithPWL(lang, str(personal))
                    break
        except Exception:
            self.dict = None
        if self.dict is None:
            self._load_spylls()
        self._load_personal()

    def _load_personal(self):
        """Свои слова читаем сами, при любом словаре: у некоторых сборок enchant личный список
        с русскими буквами не срабатывает, и добавленное слово так и оставалось красным."""
        try:
            self.personal = {w.strip() for w in self.personal_path.read_text(encoding="utf-8").split("\n")
                             if w.strip()}
        except (OSError, UnicodeDecodeError):
            self.personal = set()

    _spylls_cache = {}    # словарь грузится около секунды - один раз на запуск

    def _load_spylls(self):
        try:
            from spylls.hunspell import Dictionary
        except ImportError:
            return
        if "ru" in Speller._spylls_cache:
            self.spylls = Speller._spylls_cache["ru"]
        for folder in ([] if self.spylls is not None else DICTIONARY_DIRS):
            if (folder / "ru_RU.dic").is_file() and (folder / "ru_RU.aff").is_file():
                try:
                    self.spylls = Dictionary.from_files(str(folder / "ru_RU"))
                    Speller._spylls_cache["ru"] = self.spylls
                except Exception:
                    self.spylls = None
                    continue
                break

    @property
    def available(self):
        return self.dict is not None or self.spylls is not None

    def _check(self, word):
        if word in self.personal or word.lower() in self.personal:   # «Фух» в начале фразы = «фух»
            return True
        if self.dict is not None:
            try:
                return self.dict.check(word)
            except Exception:
                return True
        return self.spylls.lookup(word)

    def common(self, word):
        """Есть ли слово в самом словаре, без личных добавлений."""
        word = word.replace("\u0301", "")
        if self.dict is not None:
            import enchant
            return enchant.Dict.check(self.dict, word)
        if self.spylls is not None:
            return self.spylls.lookup(word)
        return False

    def ok(self, word):
        word = word.replace("\u0301", "")
        if not self.available or len(word) < 2:
            return True
        if word not in self.cache:
            good = self._check(word)
            if not good and ("ё" in word or "Ё" in word):
                good = self._check(word.replace("ё", "е").replace("Ё", "Е"))
            self.cache[word] = good
        return self.cache[word]

    def suggest(self, word):
        """Варианты исправления. Запоминаются: раньше одно и то же слово то получало варианты,
        то «Нет вариантов» - смотря, что успел ответить словарь."""
        word = word.replace("\u0301", "")
        found = self.__dict__.setdefault("_suggested", {}).get(word)
        if found is not None:
            return found
        found = []
        try:
            if self.dict is not None:
                found = self.dict.suggest(word)
                if not found and word[:1].isupper():
                    found = [s[:1].upper() + s[1:] for s in self.dict.suggest(word.lower())]
            elif self.spylls is not None:
                for s in self.spylls.suggest(word):
                    found.append(s)
                    if len(found) >= 8:
                        break
        except Exception:
            found = []
        found = [s for s in dict.fromkeys(found) if not has_foreign(s) and s != word]
        self._suggested[word] = found
        return found

    def add(self, word, as_name=False):
        """В свой словарь. Слово с большой буквы (начало фразы) кладётся маленькими - тогда оно
        подходит и в середине фразы, и в начале; «ВОТ», «КиРа» и имена (as_name) - как есть."""
        word = word.replace("\u0301", "").strip()
        if not word:
            return
        title = word[:1].isupper() and word[1:] == word[1:].lower()
        stored = word.lower() if title and not as_name else word
        if stored in self.personal:
            return
        self.personal.add(stored)
        written = False
        if self.dict is not None:
            try:
                self.dict.add(stored)            # enchant сам дописывает в тот же файл
                written = True
            except Exception:
                written = False
        if not written:
            try:
                with open(self.personal_path, "a", encoding="utf-8") as handle:
                    handle.write(stored + "\n")
            except OSError:
                pass
        self.cache.clear()
        self.__dict__.pop("_suggested", None)
        self.version += 1         # подсветка абзацев считается заново


# ---------------- виджеты ----------------
class ProseHighlighter(QSyntaxHighlighter):
    """Реплики, пометки, повторы, ошибки и затемнение абзацев в режиме фокуса."""

    def __init__(self, document, speller):
        super().__init__(document)
        self.speller = speller
        self.focus = False
        self.current = 0
        self.name_rules = []   # имена персонажей: их повтор - это нормально
        self.punctuation = True
        self.lore = None       # термины мира
        self.crutches = Crutches([])   # мои штампы
        self.lore_underline = True
        self.checks = True     # повторы и орфография; в панели «рядом» выключены
        self.paused = False    # пока True - абзацы не раскрашиваются (открытие большой главы)
        self.refresh_colors()

    def refresh_colors(self):
        """Цвета и форматы, которые нужны в каждом абзаце, считаются один раз - и заново при смене темы.
        Раньше каждый повтор заново смешивал цвета - на главе в 200 тысяч слов это были секунды."""
        self.dialogue = QColor(C.DIALOGUE)
        self.text_dim = C.mix(C.TEXT, C.BG, C.FOCUS_DIM)
        self.dialogue_dim = C.mix(C.DIALOGUE, C.BG, C.FOCUS_DIM)
        self.heading_color = C.toward_contrast(C.TEXT, 0.15)
        self.stars_color = C.mix(C.BORDER, C.TEXT, 0.3)
        self.text_color = QColor(C.TEXT)

        def overlay(**kw):
            fmt = QTextCharFormat()
            if "fg" in kw:
                fmt.setForeground(QColor(kw["fg"]))
            if "bg" in kw:
                fmt.setBackground(QColor(kw["bg"]))
            if "under" in kw:
                style, color = kw["under"]
                fmt.setUnderlineStyle(style)
                fmt.setUnderlineColor(QColor(color))
            if kw.get("italic"):
                fmt.setFontItalic(True)
            return fmt

        under = QTextCharFormat.SingleUnderline
        self.overlays = {
            "lore": overlay(under=(QTextCharFormat.DotLine, C.LORE)),
            "punct": overlay(fg=C.PUNCT),
            "stars": overlay(fg=self.stars_color),
            "italic": overlay(italic=True),
            "marker": overlay(fg=C.MARKER, bg=C.MARKER_BG),
            # подложка и черта того же цвета, но ярче: повтор видно и там, где подложка почти сливается с фоном
            "repeat": overlay(bg=C.REPEAT_BG, under=(under, C.toward_contrast(C.REPEAT_BG, 0.45))),
            "crutch": overlay(bg=C.CRUTCH_BG, under=(under, C.toward_contrast(C.CRUTCH_BG, 0.45))),
            "spell": overlay(fg=C.SPELL),
        }
        self._bold_colors = {}

    def highlightBlock(self, text):
        if self.paused:
            return               # глава ещё загружается: покрасим один раз, когда всё на месте
        to_qt = position_map(text)
        is_dialogue = text.lstrip().startswith(C.DIALOGUE_MARKS)
        dim = self.focus and self.currentBlock().blockNumber() != self.current
        if is_dialogue or dim:
            base = QTextCharFormat()
            if is_dialogue:
                base.setForeground(self.dialogue_dim if dim else self.dialogue)
            else:
                base.setForeground(self.text_dim)
            self.setFormat(0, to_qt(len(text)), base)
        heading = HEADING_LINE_RE.match(text)
        if heading:
            # «# Пролог» - заголовок внутри главы: крупнее и плотнее, решётки приглушены
            fmt = QTextCharFormat()
            fmt.setFontWeight(QFont.Black)
            size = self.document().defaultFont().pointSizeF()
            if size > 0:
                fmt.setFontPointSize(size + 3)
            fmt.setForeground(self.text_dim if dim else self.heading_color)
            self.setFormat(0, to_qt(len(text)), fmt)
            marks = QTextCharFormat(fmt)
            marks.setForeground(self.stars_color)
            self.setFormat(0, to_qt(heading.end(1)), marks)
            return
        emph, rest = self._ops(text)
        overlays, fmt_at, put, bold = self.overlays, self.format, self.setFormat, self._bold
        for begin, length, kind in emph:
            fmt = fmt_at(begin)
            if kind == "bold":
                bold(fmt)
            else:
                fmt.merge(overlays[kind])
            put(begin, length, fmt)
        if dim:
            return   # в приглушённых абзацах больше ничего не подсвечиваем, чтобы не отвлекало
        for begin, length, kind in rest:
            fmt = fmt_at(begin)
            fmt.merge(overlays[kind])
            put(begin, length, fmt)

    def _context(self):
        """Всё, от чего зависит разметка абзаца, кроме цветов: имена, термины, штампы, словарь, настройки."""
        lore = self.lore
        return (lore, lore.signature if lore is not None else None, self.crutches, self.name_rules,
                self.punctuation, self.lore_underline, self.checks, getattr(self.speller, "version", 0),
                C.REPEAT_MIN_LEN, C.REPEAT_WINDOW)

    def _ops(self, text):
        """Что и где покрасить в абзаце: [(начало, длина, вид)]. Запоминается по тексту абзаца,
        поэтому смена темы и повторное открытие главы не считают всё заново."""
        context = self._context()
        if context != self.__dict__.get("_ops_context"):
            self._ops_context, self._ops_cache = context, {}
        cache = self._ops_cache
        found = cache.get(text)
        if found is None:
            if len(cache) > 60000:
                cache.clear()
            found = cache[text] = self._compute_ops(text)
        return found

    def _compute_ops(self, text):
        to_qt = position_map(text)
        emph, rest = [], []

        def add(target, start, end, kind):
            begin = to_qt(start)
            target.append((begin, to_qt(end) - begin, kind))

        if "*" in text:
            for m in EMPH_RE.finditer(text):
                bold = m.group(1) is not None
                inner_start, inner_end = (m.start(1), m.end(1)) if bold else (m.start(2), m.end(2))
                add(emph, m.start(), inner_start, "stars")
                add(emph, inner_end, m.end(), "stars")
                add(emph, inner_start, inner_end, "bold" if bold else "italic")

        if self.punctuation:
            for m in PUNCT_RE.finditer(text):
                add(rest, m.start(), m.end(), "punct")
        markers = [(m.start(), m.end()) for m in MARKER_RE.finditer(text)] if "[" in text else []
        for start, end in markers:
            add(rest, start, end, "marker")

        def in_marker(position):
            return any(s <= position < e for s, e in markers)

        # термины мира: тонкое подчёркивание; они не считаются повтором и ошибкой
        lore_spans = self.lore.spans(text) if self.lore is not None else []
        if self.lore_underline:
            for start, end, _term in lore_spans:
                add(rest, start, end, "lore")

        def in_lore(position):
            return any(s <= position < e for s, e, _t in lore_spans)

        if not self.checks:
            return emph, rest
        tokens = list(CYR_WORD.finditer(text))
        if markers:
            tokens = [m for m in tokens if not in_marker(m.start())]
        plain = [m for m in tokens if not in_lore(m.start())] if lore_spans else tokens
        for m in self._repeats(plain):
            add(rest, m.start(), m.end(), "repeat")
        for start, end, _entry in self.crutches.spans(text):      # мои штампы - поверх повторов
            if not in_marker(start):
                add(rest, start, end, "crutch")
        if self.speller.available:
            ok = self.speller.ok
            for m in tokens:
                word = m.group()
                if "-" not in word:   # обычное слово - без разбора на части
                    if not ok(word) and not (lore_spans and in_lore(m.start())):
                        add(rest, m.start(), m.end(), "spell")
                    continue
                for part in CYR_PART.finditer(word):
                    if not ok(part.group()) and not in_lore(m.start() + part.start()):
                        add(rest, m.start() + part.start(), m.start() + part.end(), "spell")
        return emph, rest

    def set_names(self, names):
        self.name_rules = [(stem(name_key(n)), len(name_key(n)) + 3) for n in names]
        self._name_cache = {}

    def _is_name(self, word):
        cache = self.__dict__.setdefault("_name_cache", {})
        found = cache.get(word)
        if found is None:
            found = cache[word] = any(word.startswith(base) and len(word) <= limit
                                      for base, limit in self.name_rules)
        return found

    def _repeats(self, tokens):
        keys = []
        minimum, stops = C.REPEAT_MIN_LEN, STOP_WORDS
        for m in tokens:
            word = name_key(m.group())
            usable = len(word) >= minimum and word not in stops and not self._is_name(word)
            keys.append(word_root(word) if usable else None)
        marked = set()
        window = C.REPEAT_WINDOW
        last = {}
        for i, key in enumerate(keys):
            if key is None:
                continue
            seen = last.get(key)
            if seen is not None:
                while seen and i - seen[0] > window:   # дальше окна - уже не повтор; без этого
                    seen.pop(0)                        # строка в 50 тысяч одинаковых слов считалась минутами
                for j in seen:
                    marked.update((i, j))
                seen.append(i)
            else:
                last[key] = [i]
        return [tokens[i] for i in sorted(marked)]

    def _bold(self, fmt):
        base = fmt.foreground().color() if fmt.foreground().style() != Qt.NoBrush else self.text_color
        key = base.rgba()
        color = self._bold_colors.get(key)
        if color is None:
            color = self._bold_colors[key] = C.toward_contrast(base, 0.22)
        fmt.setFontWeight(QFont.Black)
        fmt.setForeground(color)


def visible_blocks(editor, limit=400):
    """Абзацы, которые сейчас видны в поле."""
    top = editor.cursorForPosition(QPoint(0, 0)).block()
    bottom = editor.cursorForPosition(QPoint(0, editor.viewport().height())).block()
    blocks = []
    block = top
    while block.isValid() and len(blocks) < limit:
        blocks.append(block)
        if block == bottom:
            break
        block = block.next()
    return blocks


class Rehighlighter(QObject):
    """Перекраска всей главы. Qt после каждого перекрашенного абзаца заново раскладывает все абзацы
    ниже него - на главе в 200 тысяч слов это полминуты. Поэтому большая глава красится при
    выключенной вёрстке, а потом вёрстка включается один раз и место на экране возвращается."""

    MANY_BLOCKS = 200

    def __init__(self, highlighter, editor, busy=None):
        super().__init__(editor)
        self.highlighter, self.editor = highlighter, editor
        self.busy = busy or (lambda _flag: None)

    pending = False         # всё красится сразу; оставлено для совместимости проверок

    def finish(self):
        pass

    def run(self, blocks=None):
        """blocks=None - вся глава; иначе только эти абзацы."""
        h = self.highlighter
        h.paused = False
        self.busy(True)
        try:
            if blocks is not None:
                for block in blocks:
                    if block.isValid():
                        h.rehighlightBlock(block)
            elif h.document().blockCount() <= self.MANY_BLOCKS or h.document().pageSize().isNull():
                h.rehighlight()
            else:
                self._run_detached()
        finally:
            self.busy(False)

    def _run_detached(self):
        with self.detached():
            self.highlighter.rehighlight()

    @contextmanager
    def detached(self, keep_place=True):
        """На время блока выключает вёрстку текста (большие правки идут в разы быстрее),
        потом включает её один раз и возвращает экран на то же место."""
        doc, editor = self.highlighter.document(), self.editor
        size = doc.pageSize()
        if size.isNull():
            yield                           # уже выключена - снаружи
            return
        bar = editor.verticalScrollBar()
        value = bar.value()
        shown = visible_blocks(editor) if keep_place else []
        doc.setPageSize(QSizeF(0, 0))       # без размера страницы Qt не раскладывает текст
        try:
            yield
        finally:
            doc.setPageSize(size)           # вёрстка заново - по частям, как при открытии
            if shown and shown[-1].isValid():
                # разложить текст до того места, где стоял экран, и вернуть прокрутку туда же
                doc.documentLayout().blockBoundingRect(shown[-1])
                bar.setRange(0, max(bar.maximum(), value))
                bar.setValue(value)


class Editor(QTextEdit):
    """Поле текста: колонка по центру, плавная прокрутка, печатная машинка,
    запрет латиницы и подсказки орфографии по правому клику."""

    def __init__(self):
        super().__init__()
        self.setObjectName("Editor")
        self.setAcceptRichText(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCursorWidth(2)
        self.document().setDocumentMargin(36)
        self.zoom_callback = None
        self.paste_callback = None        # (сколько слов прибавила вставка) - в «за день» они не идут
        self.key_callback = None          # (событие клавиши) - звук печатной машинки
        self.foreign_callback = None
        self.dictionary_changed = None
        self.speller = None
        self.track_name_callback = None
        self.lore_tip = None      # позиция мыши -> текст подсказки о термине или None
        self.lore_open = None     # позиция мыши -> открыл ли заметку о термине
        self.note_callback = None  # абзац -> заметка на полях
        self.crutch_callback = None   # слово или оборот -> в мои штампы
        self.margin_widget = None     # заметки на полях справа
        self.line_widget = None       # номера строк слева
        self.forward_only = False
        self.forward_callback = None
        self.only_russian = C.ONLY_RUSSIAN
        self.typewriter = False
        self._extra_bottom = 0
        self._base_max = 0
        self._extending = False
        self._target = 0
        self._anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.verticalScrollBar().rangeChanged.connect(self._on_range)
        # печатная машинка: пока текста мало, строку к середине поднимает отступ сверху,
        # а когда текста много - прокрутка
        self._lift = 0
        self._lift_anim = QVariantAnimation(self)
        self._lift_anim.setDuration(220)
        self._lift_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._lift_anim.valueChanged.connect(lambda v: self._set_lift(int(v)))

    # ---- только русский ----
    def _reject(self):
        if self.foreign_callback:
            self.foreign_callback()

    def _forward_reject(self):
        if self.forward_callback:
            self.forward_callback()

    # ---- стёрли много за раз: окно узнаёт и подстраховывает ----
    ERASE_CHARS = 600

    # ---- своя картинка под текстом ----
    def set_backdrop(self, path=None, dim=0.6):
        """Картинка под текстом, притемнённая цветом фона темы (dim 0..1 - насколько сильно),
        чтобы буквы читались. Картинка стоит на месте, текст прокручивается поверх. None - убрать."""
        from PySide6.QtGui import QPixmap
        self.backdrop = QPixmap(str(path)) if path else None
        if self.backdrop is not None and self.backdrop.isNull():
            self.backdrop = None
        self.backdrop_dim = max(0.0, min(0.95, float(dim)))
        self._backdrop_scaled = None
        if not getattr(self, "_backdrop_hooked", False):
            self.verticalScrollBar().valueChanged.connect(lambda _v: self.backdrop and self.viewport().update())
            self._backdrop_hooked = True
        self.viewport().update()
        margin = getattr(self, "margin_widget", None)
        if margin is not None:
            margin.update()
        return self.backdrop is not None

    def backdrop_canvas(self):
        """Где лежит картинка целиком: всё окно (под полем, полями заметок, краями и строкой внизу)."""
        window = self.window()
        central = window.centralWidget() if hasattr(window, "centralWidget") else None
        return central if central is not None else self

    def paint_backdrop(self, painter, widget):
        """Нарисовать свою картинку на widget: картинка растянута на всё окно, каждый кусок
        рисует свою часть - получается одна картинка без стыков. Масштаб - в настоящих точках
        экрана (на экранах с увеличением картинка не мылится)."""
        backdrop = getattr(self, "backdrop", None)
        if backdrop is None:
            return
        canvas = self.backdrop_canvas()
        size = canvas.size()
        ratio = max(1.0, widget.devicePixelRatioF())
        cached = getattr(self, "_backdrop_scaled", None)
        if cached is None or cached[0] != (size, ratio):
            scaled = backdrop.scaled(size * ratio, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            scaled.setDevicePixelRatio(ratio)
            cached = self._backdrop_scaled = ((size, ratio), scaled)
        scaled = cached[1]
        width, height = scaled.width() / ratio, scaled.height() / ratio
        offset = widget.mapTo(canvas, QPoint(0, 0)) if widget is not canvas else QPoint(0, 0)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(QPointF((size.width() - width) / 2 - offset.x(), (size.height() - height) / 2 - offset.y()),
                           scaled)
        veil = QColor(C.BG)
        veil.setAlphaF(self.backdrop_dim)
        painter.fillRect(widget.rect(), veil)

    def paintEvent(self, event):
        if getattr(self, "backdrop", None) is not None:
            painter = QPainter(self.viewport())
            self.paint_backdrop(painter, self.viewport())
            painter.end()
        super().paintEvent(event)

    def _watch_erase(self, run):
        cursor = self.textCursor()
        callback = getattr(self, "big_erase_callback", None)
        if callback is None or cursor.selectionEnd() - cursor.selectionStart() < self.ERASE_CHARS:
            return run()
        before = self.toPlainText()
        result = run()
        callback(before)
        return result

    def cut(self):
        self._watch_erase(super().cut)

    def keyPressEvent(self, event):
        erasing = (event.key() in (Qt.Key_Backspace, Qt.Key_Delete) or event.matches(QKeySequence.Cut)
                   or bool(event.text()))
        if erasing and not self.forward_only and self.textCursor().hasSelection():
            return self._watch_erase(lambda: self._key_press(event))
        return self._key_press(event)

    def _key_press(self, event):
        if self.forward_only:
            erases = (event.key() in (Qt.Key_Backspace, Qt.Key_Delete)
                      or event.matches(QKeySequence.Cut) or event.matches(QKeySequence.Undo)
                      or event.matches(QKeySequence.Redo))
            if erases:
                self._forward_reject()
                event.accept()
                return
            if event.text() and self.textCursor().hasSelection():
                # набор поверх выделения стёр бы его, поэтому просто пишем после
                cursor = self.textCursor()
                cursor.setPosition(cursor.selectionEnd())
                self.setTextCursor(cursor)
        mods = event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)
        if self.only_russian and not mods and has_foreign(event.text()):
            self._reject()
            event.accept()
            return
        super().keyPressEvent(event)
        if self.key_callback and not mods and not self.isReadOnly():
            self.key_callback(event)

    def insertFromMimeData(self, source):
        if self.only_russian and source.hasText() and has_foreign(source.text()):
            self._reject()
            return
        if self.forward_only and self.textCursor().hasSelection():
            cursor = self.textCursor()
            cursor.setPosition(cursor.selectionEnd())
            self.setTextCursor(cursor)
        if source.hasText():
            from PySide6.QtCore import QMimeData
            from PySide6.QtGui import QTextDocument
            html_text = None
            if source.hasHtml():
                document = QTextDocument()
                document.setHtml(source.html())
                html_text = document.toPlainText()
            cleaned = QMimeData()
            cleaned.setText(clean_pasted(source.text(), html_text))
            source = cleaned
        before = len(WORD_RE.findall(self.toPlainText())) if self.paste_callback else 0
        self._watch_erase(lambda: super(Editor, self).insertFromMimeData(source))
        if self.paste_callback:
            self.paste_callback(len(WORD_RE.findall(self.toPlainText())) - before)

    def dropEvent(self, event):
        if self.forward_only:
            event.setDropAction(Qt.CopyAction)   # перетаскивание не вырезает текст
        super().dropEvent(event)

    def inputMethodEvent(self, event):
        if self.only_russian and has_foreign(event.commitString()):
            self._reject()
            event.accept()
            return
        super().inputMethodEvent(event)

    # ---- термины мира: подсказка при наведении, Ctrl+клик открывает заметку ----
    def viewportEvent(self, event):
        if event.type() == QEvent.ToolTip and self.lore_tip:
            tip = self.lore_tip(event.pos())
            if tip:
                QToolTip.showText(event.globalPos(), tip, self.viewport())
            else:
                QToolTip.hideText()
            return True
        return super().viewportEvent(event)

    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier
                and self.lore_open and self.lore_open(event.position().toPoint())):
            event.accept()
            return
        super().mousePressEvent(event)

    # ---- правый клик: варианты исправления ----
    def contextMenuEvent(self, event):
        menu = rounded_menu(self)
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText()
        if (self.speller and self.speller.available and CYR_PART.fullmatch(word or "")
                and not self.speller.ok(word) and not self.forward_only):
            suggestions = self.speller.suggest(word)[:6]
            for suggestion in suggestions:
                action = menu.addAction(suggestion, lambda s=suggestion, c=cursor: c.insertText(s))
                action.setProperty("noIcon", True)        # вариант слова - без значка
            if not suggestions:
                menu.addAction("Нет вариантов").setEnabled(False)
            menu.addAction(f"Добавить «{word}» в словарь", lambda: self._add_word(word))
            menu.addSeparator()
        if self.track_name_callback and CYR_PART.fullmatch(word or "") and word[:1].isupper():
            menu.addAction(f"Считать «{word}» персонажем", lambda: self.track_name_callback(word))
            menu.addSeparator()
        if self.crutch_callback:
            selected = self.textCursor().selectedText().strip()
            phrase = selected if selected and len(selected) <= 40 and "\u2029" not in selected else word
            if phrase and WORD_RE.search(phrase):
                menu.addAction(f"В мои штампы: «{phrase}»", lambda p=phrase: self.crutch_callback(p))
                menu.addSeparator()
        if self.note_callback:
            block = cursor.block()
            menu.addAction("Заметка на полях   Ctrl+M", lambda: self.note_callback(block))
            menu.addSeparator()
        undo = menu.addAction("Отменить", self.undo)
        undo.setEnabled(self.document().isUndoAvailable() and not self.forward_only)
        redo = menu.addAction("Вернуть", self.redo)
        redo.setEnabled(self.document().isRedoAvailable() and not self.forward_only)
        menu.addSeparator()
        has_selection = self.textCursor().hasSelection()
        menu.addAction("Вырезать", self.cut).setEnabled(has_selection and not self.forward_only)
        menu.addAction("Копировать", self.copy).setEnabled(has_selection)
        menu.addAction("Вставить", self.paste).setEnabled(self.canPaste())
        menu.addSeparator()
        menu.addAction("Выделить всё", self.selectAll)
        menu.exec(event.globalPos())

    def _add_word(self, word):
        self.speller.add(word)
        if self.dictionary_changed:
            self.dictionary_changed()

    # ---- запас прокрутки снизу, чтобы последняя строка могла встать в середину ----
    def _on_range(self, _minimum, maximum):
        if self._extending:
            return
        self._base_max = maximum
        if self._extra_bottom:
            self._set_max(maximum + self._extra_bottom)

    def _set_max(self, value):
        self._extending = True
        self.verticalScrollBar().setMaximum(value)
        self._extending = False

    def _update_extra(self):
        extra = int(self.viewport().height() * (1 - C.TYPEWRITER_POS)) if self.typewriter else 0
        if extra != self._extra_bottom:
            self._extra_bottom = extra
            self._set_max(self._base_max + extra)

    def set_typewriter(self, on):
        self.typewriter = on
        self._update_extra()
        if on:
            self.center_cursor()
        else:
            self._animate_lift(0)

    def _side(self):
        return max(40, (self.width() - C.COLUMN_WIDTH) // 2)

    def _set_lift(self, value):
        value = max(0, value)
        self._lift = value
        if self.viewportMargins().top() != value:
            side = self._side()
            self.setViewportMargins(side, value, side, 0)
            self.place_side_widgets()

    def _animate_lift(self, value):
        self._lift_anim.stop()
        if value == self._lift:
            return
        self._lift_anim.setStartValue(self._lift)
        self._lift_anim.setEndValue(int(value))
        self._lift_anim.start()

    def scroll_smooth(self, value, duration=260):
        bar = self.verticalScrollBar()
        value = max(bar.minimum(), min(bar.maximum(), value))
        self._target = value
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setStartValue(bar.value())
        self._anim.setEndValue(value)
        self._anim.start()

    def center_cursor(self):
        """Строка с курсором - на высоте TYPEWRITER_POS. В начале главы, где прокручивать некуда,
        текст опускается отступом сверху, поэтому машинку видно сразу, а не только в длинной главе."""
        bar = self.verticalScrollBar()
        want = int(self.height() * C.TYPEWRITER_POS)
        delta = self._lift + self.cursorRect().center().y() - want
        if abs(delta) <= 1:
            return
        offset = bar.value() - self._lift + delta      # сдвиг текста вверх; меньше нуля - отступ
        lift = min(max(0, -offset), want)
        scroll = max(0, offset)
        self._animate_lift(lift)
        if scroll != bar.value():
            self.scroll_smooth(scroll, 180)

    def stop_scroll(self):
        self._anim.stop()
        self._target = self.verticalScrollBar().value()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if self.zoom_callback and event.angleDelta().y():
                self.zoom_callback(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        # тачпад и так присылает плавные пиксельные сдвиги
        if not event.pixelDelta().isNull() or event.angleDelta().y() == 0:
            super().wheelEvent(event)
            return
        bar = self.verticalScrollBar()
        running = self._anim.state() == QAbstractAnimation.State.Running
        base = self._target if running else bar.value()
        self.scroll_smooth(base - event.angleDelta().y())
        event.accept()

    def resizeEvent(self, event):
        # поля ставим до раскладки текста: иначе строки раскладываются по старой ширине
        # и уходят за правый край колонки
        self._margins()
        super().resizeEvent(event)
        self._update_extra()
        self.place_side_widgets()

    def _margins(self):
        side = self._side()
        if self.viewportMargins().left() != side or self.viewportMargins().top() != self._lift:
            self.setViewportMargins(side, self._lift, side, 0)

    def place_side_widgets(self):
        for widget in (self.margin_widget, self.line_widget):
            if widget is not None:
                widget.place()

    def apply_column(self):
        """Новая ширина колонки из настроек - сразу, без перезапуска."""
        self._margins()
        self._update_extra()
        self.place_side_widgets()


class NotesMargin(QWidget):
    """Заметки на полях: карточки справа от абзацев. В книгу и счёт слов не попадают.
    Каждая заметка держится за курсор в начале абзаца, поэтому едет вместе с текстом."""

    WIDE = 120        # с такой ширины поля видно текст заметки, уже - только значок
    CARD = 240
    LINES = 3

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.notes = []            # [[QTextCursor, текст]]
        self.shown = True
        self.open_callback = None  # номер заметки -> редактировать
        self.add_callback = None   # абзац -> новая заметка
        self._cards = []
        self.setMouseTracking(True)
        doc = editor.document()
        editor.verticalScrollBar().valueChanged.connect(self.update)
        editor.verticalScrollBar().rangeChanged.connect(lambda *_: self.place())
        doc.contentsChanged.connect(self.update)
        doc.documentLayout().update.connect(self.update)

    def place(self):
        viewport = self.editor.viewport().geometry()
        bar = self.editor.verticalScrollBar()
        holder = bar.parentWidget()   # полоса прокрутки лежит в своём контейнере у края окна
        if bar.isVisible() and holder is not None and holder is not self.editor:
            right = holder.geometry().left()
        else:
            right = self.editor.width()
        self.setGeometry(viewport.right() + 1, viewport.top(),
                         max(0, right - viewport.right() - 1), viewport.height())
        self.raise_()
        self.update()

    # ---- данные ----
    def clear(self):
        self.notes = []
        self.update()

    def block_of(self, index):
        return self.editor.document().findBlock(self.notes[index][0].position())

    def index_for(self, block):
        for i in range(len(self.notes)):
            if self.block_of(i).blockNumber() == block.blockNumber():
                return i
        return None

    def add(self, block, text):
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(block.position())
        self.notes.append([cursor, text])
        self.update()

    def data(self):
        """Заметки для сохранения: текст абзаца как якорь и его номер."""
        out = []
        for i, (_cursor, text) in enumerate(self.notes):
            block = self.block_of(i)
            previous, following = block.previous(), block.next()
            out.append({"anchor": block.text(), "index": block.blockNumber(), "text": text,
                        "before": previous.text() if previous.isValid() else "",
                        "after": following.text() if following.isValid() else ""})
        out.sort(key=lambda n: n["index"])
        return out

    def load(self, data):
        self.notes = []
        doc = self.editor.document()
        paragraphs = [doc.findBlockByNumber(i).text() for i in range(doc.blockCount())]
        items = [n for n in data if isinstance(n, dict) and isinstance(n.get("text"), str) and n["text"].strip()]
        for note, number in zip(items, anchor_notes(paragraphs, items)):
            self.add(doc.findBlockByNumber(number), note["text"])
        self.update()

    # ---- рисование ----
    def _font(self):
        font = QFont(self.editor.font())
        font.setPointSizeF(max(8.0, font.pointSizeF() * 0.72))
        font.setWeight(QFont.Normal)
        return font

    def _elide(self, metrics, text, width):
        limit = metrics.height() * self.LINES
        flags = int(Qt.TextWordWrap)
        if metrics.boundingRect(0, 0, width, 100000, flags, text).height() <= limit:
            return text
        low, high = 0, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if metrics.boundingRect(0, 0, width, 100000, flags, text[:middle].rstrip() + "…").height() <= limit:
                low = middle
            else:
                high = middle - 1
        return text[:low].rstrip() + "…"

    def paintEvent(self, _event):
        self._cards = []
        if getattr(self.editor, "backdrop", None) is not None:      # своя картинка - и под заметками
            backdrop_painter = QPainter(self)
            self.editor.paint_backdrop(backdrop_painter, self)
            backdrop_painter.end()
        if not self.notes or not self.shown:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = self._font()
        painter.setFont(font)
        metrics = QFontMetrics(font)
        layout = self.editor.document().documentLayout()
        offset = self.editor.verticalScrollBar().value()
        wide = self.width() >= self.WIDE
        order = sorted(range(len(self.notes)), key=lambda i: self.notes[i][0].position())
        bottom = -10 ** 6
        text_color = C.mix(C.TEXT, C.BG, 0.3)
        for i in order:
            block = self.block_of(i)
            if not block.isValid():
                continue
            top = layout.blockBoundingRect(block).top() - offset
            if wide:
                width = min(self.width() - 26, self.CARD)
                shown = self._elide(metrics, self.notes[i][1], width - 20)
                height = metrics.boundingRect(0, 0, width - 20, 100000, int(Qt.TextWordWrap), shown).height() + 16
                rect = QRectF(14, max(top + 4, bottom + 6), width, height)
            else:
                rect = QRectF((self.width() - 14) / 2, max(top + 8, bottom + 4), 14, 14)
            bottom = rect.bottom()
            if rect.bottom() < 0 or rect.top() > self.height():
                continue
            self._cards.append((rect, i))
            painter.setPen(QPen(QColor(C.BORDER), 1))
            painter.setBrush(QColor(C.PANEL))
            if wide:
                painter.drawRoundedRect(rect, 10, 10)
                painter.setPen(text_color)
                painter.drawText(rect.adjusted(10, 8, -10, -8), int(Qt.TextWordWrap), shown)
            else:
                painter.setBrush(QColor(C.DIM))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(rect.adjusted(3, 3, -3, -3))

    # ---- мышь ----
    def _card_at(self, pos):
        for rect, i in self._cards:
            if rect.adjusted(-3, -3, 3, 3).contains(QPointF(pos)):
                return i
        return None

    def mouseMoveEvent(self, event):
        i = self._card_at(event.position())
        self.setCursor(Qt.PointingHandCursor if i is not None else Qt.ArrowCursor)
        if i is not None:
            text = html.escape(self.notes[i][1]).replace("\n", "<br>")
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"<table width='300'><tr><td>{text}</td></tr></table>", self)
        else:
            QToolTip.hideText()

    def mousePressEvent(self, event):
        i = self._card_at(event.position())
        if event.button() == Qt.LeftButton and i is not None and self.open_callback:
            self.open_callback(i)
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._card_at(event.position()) is not None or not self.add_callback:
            return
        y = int(event.position().y())
        cursor = self.editor.cursorForPosition(QPoint(10, y))
        self.add_callback(cursor.block())

    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)


class LineNumbers(QWidget):
    """Номера строк слева от текста, как в обычном блокноте. Строка - это абзац (строка файла):
    номер стоит у первой строчки абзаца и не прыгает, когда меняется ширина окна или шрифт."""

    GAP = 28    # от номеров до текста: подальше, чтобы не липли к буквам
    PAD = 8     # поля полосы по бокам от номера

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.shown = False
        self.quiet = False      # «без отвлечений»: спрятаны, но не выключены
        self.setAttribute(Qt.WA_TransparentForMouseEvents)     # щелчок у начала строки - в текст
        doc = editor.document()
        editor.verticalScrollBar().valueChanged.connect(self.update)
        editor.cursorPositionChanged.connect(self.update)
        doc.blockCountChanged.connect(lambda _n: self.place())
        doc.documentLayout().documentSizeChanged.connect(lambda _s: self.place())
        doc.documentLayout().update.connect(self.update)
        self.hide()

    def set_shown(self, on):
        self.shown = on
        self.place()

    def set_quiet(self, on):
        self.quiet = on
        self.place()

    def _font(self):
        font = QFont(self.editor.font())
        font.setPointSizeF(max(8.0, font.pointSizeF() * 0.72))
        font.setWeight(QFont.Normal)
        return font

    def place(self):
        if not self.shown or self.quiet:
            self.hide()
            return
        digits = max(2, len(str(self.editor.document().blockCount())))
        width = QFontMetrics(self._font()).horizontalAdvance("0" * digits) + 2 * self.PAD
        viewport = self.editor.viewport().geometry()
        right = viewport.left() + int(self.editor.document().documentMargin()) - self.GAP
        left = max(0, right - width)
        self.setGeometry(left, viewport.top(), max(0, right - left), viewport.height())
        self.show()
        self.raise_()
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)      # без фона: только номера, под ними видно то же, что под текстом
        font = self._font()
        painter.setFont(font)
        metrics = QFontMetrics(font)
        layout = self.editor.document().documentLayout()
        offset = self.editor.verticalScrollBar().value()
        current = self.editor.textCursor().blockNumber()
        dim, bright = QColor(C.DIM), QColor(C.mix(C.TEXT, C.BG, 0.15))
        right = self.width() - self.PAD
        for block in visible_blocks(self.editor):
            if not block.isVisible():
                continue
            top = layout.blockBoundingRect(block).top() - offset
            lines = block.layout()
            if lines is not None and lines.lineCount():
                first = lines.lineAt(0)
                baseline = top + first.y() + first.ascent()      # на одной линии с первой строчкой
            else:
                baseline = top + metrics.ascent()
            text = str(block.blockNumber() + 1)
            painter.setPen(bright if block.blockNumber() == current else dim)
            painter.drawText(QPointF(right - metrics.horizontalAdvance(text), baseline), text)


class _NoSpeller:
    available = False

    def ok(self, _word):
        return True


class SidePane(QFrame):
    """Панель рядом с текстом: другая глава, справочник, таблица или доска - только для чтения.
    Править можно в основном окне: кнопка «Открыть здесь» меняет их местами."""

    def __init__(self, open_callback, close_callback):
        super().__init__()
        self.setObjectName("SidePane")
        self.path = None
        layout = QVBoxLayout(self)
        # справа отступ побольше: у самого края окна выезжает правая панель
        layout.setContentsMargins(14, 10, 18, 6)
        layout.setSpacing(4)
        head = QHBoxLayout()
        self.title = QLabel("")
        self.title.setObjectName("Title")
        self.title.setWordWrap(True)
        self.title.setMinimumWidth(40)
        head.addWidget(self.title, 1)
        self.swap = QPushButton("⇄")
        self.swap.setCursor(Qt.PointingHandCursor)
        self.swap.setToolTip("Поменять местами: этот файл - в основное окно, чтобы править")
        self.swap.clicked.connect(lambda: self.path and open_callback(self.path))
        close = QPushButton("✕")
        close.setCursor(Qt.PointingHandCursor)
        close.setToolTip("Закрыть панель   F4")
        for button in (self.swap, close):
            button.setStyleSheet("background: transparent; padding: 4px 10px;")
        close.clicked.connect(close_callback)
        # листать версии: старее / новее (видны, только когда в панели версия)
        self.older = QPushButton("◀")
        self.older.setToolTip("Версия постарше")
        self.newer = QPushButton("▶")
        self.newer.setToolTip("Версия поновее")
        self.side_button = QPushButton("⇆")
        self.side_button.setToolTip("Перенести панель на другую сторону от текста")
        for button in (self.older, self.newer, self.side_button):
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("background: transparent; padding: 4px 8px;")
            button.setProperty("noIcon", True)
        self.older.clicked.connect(lambda: self.step_version(1))
        self.newer.clicked.connect(lambda: self.step_version(-1))
        head.addWidget(self.older)
        head.addWidget(self.newer)
        head.addWidget(self.side_button)
        head.addWidget(self.swap)
        head.addWidget(close)
        layout.addLayout(head)
        self.note = QLabel("")
        self.note.setObjectName("Status")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.versions = []           # версии главы, от новых к старым (когда в панели версия)
        self.version_index = -1
        self.current_text = None     # функция: нынешний текст главы - с ним и сравниваем
        self.on_version_changed = None
        self._show_version_controls(False)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        self.view.setFrameShape(QFrame.NoFrame)
        self.view.document().setDocumentMargin(16)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.view, 1)
        self.highlighter = ProseHighlighter(self.view.document(), _NoSpeller())
        self.highlighter.checks = False
        self.rehighlighter = Rehighlighter(self.highlighter, self.view)

    def set_font(self, font):
        small = QFont(font)
        small.setPointSizeF(max(9.0, font.pointSizeF() * 0.9))
        self.view.setFont(small)

    def _show_version_controls(self, on):
        for widget in (self.older, self.newer, self.note):
            widget.setVisible(on)
        self.swap.setVisible(not on)

    @property
    def showing_version(self):
        return 0 <= self.version_index < len(self.versions)

    def show_version(self, chapter, versions, index, current_text):
        """Старая версия главы - рядом с нынешним текстом: только чтение, ушедшее подсвечено."""
        self.path = chapter
        self.versions, self.version_index, self.current_text = list(versions), index, current_text
        self._show_version_controls(True)
        self.refresh_version(keep_place=False)

    def step_version(self, delta):
        target = self.version_index + delta
        if 0 <= target < len(self.versions):
            self.version_index = target
            self.refresh_version(keep_place=True)
            if self.on_version_changed:
                self.on_version_changed()

    def refresh_version(self, keep_place=True):
        """Перерисовать сравнение (нынешний текст мог измениться, пока пишешь)."""
        if not self.showing_version:
            return
        from ..core.storage import version_label
        from ..core.textutil import old_side_html
        version = self.versions[self.version_index]
        position = self.view.verticalScrollBar().value() if keep_place else 0
        self.title.setText(f"{self.path.stem} · версия от {version_label(version)}")
        try:
            old = read_text(version)
        except (OSError, LockedFile) as error:
            self.view.setPlainText(f"Не открывается: {error}")
            return
        body, summary = old_side_html(old, self.current_text() if self.current_text else old)
        self.highlighter.paused = True                        # подсветка прозы здесь мешала бы отличиям
        self.view.setHtml(body)
        self.note.setText(f"{self.version_index + 1} из {len(self.versions)}   ·   {summary}")
        self.older.setEnabled(self.version_index + 1 < len(self.versions))
        self.newer.setEnabled(self.version_index > 0)
        self.view.verticalScrollBar().setValue(position)

    def show_path(self, path):
        """Показывает файл. Если это тот же файл, место прокрутки сохраняется."""
        self.versions, self.version_index = [], -1
        self._show_version_controls(False)
        self.highlighter.paused = False
        same = path == self.path
        position = self.view.verticalScrollBar().value() if same else 0
        self.path = path
        self.title.setText(f"{path.parent.name} · {path.stem}")
        try:
            text = read_text(path)
        except (OSError, LockedFile) as error:
            self.view.setPlainText(f"Не открывается: {error}")
            return
        self.highlighter.paused = True       # большая глава красится после, порциями
        if is_table(path):
            header, rows = parse_table(text)
            cells = "".join(f"<th align='left'>{html.escape(h)}</th>" for h in header)
            body = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in row) + "</tr>"
                           for row in rows if any(c.strip() for c in row))
            self.view.setHtml(f"<table cellspacing='0' cellpadding='6' width='100%'><tr>{cells}</tr>{body}</table>")
        elif is_board(path):
            try:
                data = json.loads(text) if text.strip() else {}
                columns = data.get("columns", []) if isinstance(data, dict) else []
            except ValueError:
                columns = []
            parts = []
            for column in columns:
                parts.append(f"<h3>{html.escape(column.get('title', ''))}</h3>")
                for card in column.get("cards", []):
                    parts.append(f"<p><b>{html.escape(card.get('title', ''))}</b><br>"
                                 f"{html.escape(card.get('text', '')).replace(chr(10), '<br>')}</p>")
            self.view.setHtml("".join(parts) or "Доска пустая")
        elif is_timeline(path):
            from ..world.timeline import load_events, sort_events, year_label
            parts = []
            for event in sort_events(load_events(text)):
                when = html.escape(event.get("when") or year_label(float(event.get("year", 0))))
                parts.append(f"<p><b>{when}</b> - {html.escape(event.get('title', ''))}<br>"
                             f"{html.escape(event.get('text', '')).replace(chr(10), '<br>')}</p>")
            self.view.setHtml("".join(parts) or "Хронология пустая")
        else:
            self.view.setPlainText(text)
            cursor = QTextCursor(self.view.document())
            cursor.select(QTextCursor.Document)
            block = QTextBlockFormat()
            block.setLineHeight(C.LINE_HEIGHT, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            block.setBottomMargin(4)
            cursor.mergeBlockFormat(block)
        self.view.verticalScrollBar().setValue(position)
        self.rehighlighter.run()

    def rehighlight(self):
        self.rehighlighter.run()


class BackdropLayer(QWidget):
    """Своя картинка под всем окном: лежит в самом низу центральной части окна, тянется за ней
    и рисует ту же картинку, что поле текста, - края окна и строка внизу тоже с картинкой."""

    def __init__(self, parent, editor):
        super().__init__(parent)
        self.editor = editor
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.lower()

    def eventFilter(self, watched, event):
        if watched is self.parent() and event.type() == QEvent.Resize:
            self.setGeometry(self.parent().rect())
            self.lower()
        return False

    def paintEvent(self, _event):
        painter = QPainter(self)
        self.editor.paint_backdrop(painter, self)
        painter.end()
