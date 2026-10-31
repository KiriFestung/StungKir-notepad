# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Работа с текстом без окон: слова, падежи, разметка, таблицы, сравнение версий."""

import csv
import difflib
import functools
import html
import io
import re

from . import config as C


# служебные слова, которые повторяются нормально и не подсвечиваются
STOP_WORDS = set("""
это этот эта эти этого этой этому этим этом того тому тоже также только когда тогда потом
теперь сейчас здесь опять снова перед после через между около против было были была будет
будут есть быть него нему ними своей свой свою свои своих своим себя себе тебя тебе
меня даже если чтобы чтоб очень может можно нужно надо который которая которое
которые которых которым какой какая какое какие сказал сказала сказали ответил ответила
спросил спросила хотя пока ведь вдруг потому почему зачем куда откуда всех всем всего всё
все весь вся она они оно неё ней нами вами ваши наши наша ваша наш ваш просто
""".split())


WORD_RE = re.compile(r"\w+(?:[-'’]\w+)*")
CYR_WORD = re.compile(r"[А-Яа-яЁё́]+(?:-[А-Яа-яЁё́]+)*")
CYR_PART = re.compile(r"[А-Яа-яЁё́]+")
MARKER_RE = re.compile(r"\[[^\[\]\n]{0,120}\]")
# пометка, которую стоит показать в списке «Пометки»: пустые [] и [ ] не в счёт
MARKER_FILLED_RE = re.compile(r"\[[^\S\n]*[^\s\[\]][^\[\]\n]{0,119}\]")
# знаки препинания; дефис внутри слова («кто-то») не трогаем
PUNCT_RE = re.compile(r"[.,!?;:…«»„“”\"'’()—–]|(?<!\w)-|-(?!\w)")
# **жирный** и *курсив*: в файле остаются звёздочки, на экране - настоящее начертание
EMPH_RE = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*|(?<![*\w])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![*\w])")


# ---------------- мелкие помощники ----------------
def plural(n, one, few, many):
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def words_label(n):
    return f"{n} {plural(n, 'слово', 'слова', 'слов')}"


def signed(n):
    return f"+{n}" if n >= 0 else f"−{abs(n)}"


def utf16_len(text):
    """Длина строки так, как её считает Qt."""
    return len(text.encode("utf-16-le")) // 2


def py_index(text, qt_position):
    """Обратное к position_map: позиция Qt -> индекс в строке Python."""
    if utf16_len(text) == len(text):
        return max(0, min(qt_position, len(text)))
    qt = 0
    for i, ch in enumerate(text):
        if qt >= qt_position:
            return i
        qt += 2 if ord(ch) > 0xFFFF else 1
    return len(text)


def position_map(text):
    """Переводит позицию в строке Python в позицию Qt (они расходятся только на эмодзи)."""
    if utf16_len(text) == len(text):
        return lambda i: i
    offsets = [0]
    for ch in text:
        offsets.append(offsets[-1] + (2 if ord(ch) > 0xFFFF else 1))
    return offsets.__getitem__


def has_foreign(text):
    """Есть ли в тексте буквы, которые не относятся к кириллице."""
    return any(ch.isalpha() and not "Ѐ" <= ch <= "ӿ" for ch in text)


@functools.lru_cache(maxsize=65536)
def stem(word):
    """Грубая основа слова, чтобы «туман» и «тумана» считались повтором."""
    return word if len(word) <= 4 else word[:max(4, len(word) - 2)]


PARAGRAPH_GAP_RE = re.compile(r"(?<=[.!?…»\"'”)\]>/*:])[ \t ]{3,}(?=\S)")
SPACES_RE = re.compile(r"(?<=\S)[ \t ]{2,}(?=\S)")
# все виды переноса, которые присылают другие программы: Windows, старый Mac, Word (Shift+Enter - \v),
# разрыв страницы, «следующая строка» и юникодные разделители строки и абзаца
LINE_BREAKS_RE = re.compile("\r\n|[\r\v\f\x85  ]")
_PAIRS = {"«": "»", "<": ">", "{": "}", "(": ")", "[": "]", "„": "“", "“": "”", "‘": "’"}
_CLOSERS = set(_PAIRS.values())
_SYMMETRIC = set("'\"/")           # одна и та же кавычка открывает и закрывает реплику
_ENDS = set(".!?…")


def _glued_cuts(text):
    """Где резать слипшийся текст: после конца фразы или закрытой реплики, когда сразу, без пробела,
    начинается новая реплика или фраза с заглавной - и только на «верхнем уровне», когда все кавычки
    и скобки закрыты (иначе «блин?!!"'Ну» резалось бы внутри реплики). Перед концом фразы - минимум
    две строчные буквы: инициалы «А.С.Пушкин» не режутся. Апостроф и косая черта между буквами
    («don't», «и/или») - не кавычки."""
    cuts, stack = [], []
    n = len(text)
    for i, ch in enumerate(text):
        if ch == "\n":
            stack.clear()
            continue
        before = text[i - 1] if i else " "
        after = text[i + 1] if i + 1 < n else " "
        if ch in _SYMMETRIC:
            if before.isalpha() and after.isalpha():
                continue                                    # апостроф или «и/или»
            if ch in stack:
                del stack[len(stack) - 1 - stack[::-1].index(ch):]
            else:
                stack.append(ch)
        elif ch in _PAIRS:
            stack.append(_PAIRS[ch])
        elif ch in _CLOSERS and ch in stack:
            del stack[len(stack) - 1 - stack[::-1].index(ch):]
        if stack or i + 1 >= n or not (ch in _ENDS or ch in _CLOSERS or ch in _SYMMETRIC):
            continue
        nxt = text[i + 1]
        if nxt.isspace():
            continue
        starts = nxt.isupper() and nxt.isalpha()
        if nxt in _PAIRS or nxt in _SYMMETRIC:
            j = i + 1
            while j < n and (text[j] in _PAIRS or text[j] in _SYMMETRIC):
                j += 1
            starts = j < n and (text[j].isalpha() or text[j] in ".…")
        if not starts:
            continue
        k = i                                               # назад через знаки и кавычки - к последней букве
        while k >= 0 and (text[k] in _ENDS or text[k] in _CLOSERS or text[k] in _SYMMETRIC):
            k -= 1
        if k >= 1 and text[k].isalpha() and text[k].islower() and text[k - 1].isalpha() and text[k - 1].islower():
            cuts.append(i + 1)
    return cuts


def unglue(text):
    """Разрезать слипшийся текст на абзацы: «отрубил'.«ня Загрузка» -> «отрубил'.» и «ня Загрузка».
    Делается, только если текст правда слипся: таких мест три и больше (или два, а переносов нет вовсе).
    Одна случайная опечатка «пошёл.Потом» в обычном тексте абзац не режет."""
    cuts = _glued_cuts(text)
    if len(cuts) < 3 and not (len(cuts) == 2 and "\n" not in text):
        return text
    parts, last = [], 0
    for cut in cuts:
        parts.append(text[last:cut])
        last = cut
    parts.append(text[last:])
    return "\n".join(parts)


def clean_pasted(text, html_text=None):
    """Текст из буфера, приведённый в порядок. Другие программы при копировании портят абзацы:
    перенос превращается в три пробела, в непонятный символ или пропадает совсем - и абзацы слипаются.
    Все виды переносов - обычный перенос; три и больше пробела после конца фразы - новый абзац;
    слипшиеся реплики разрезаются (unglue); длинные пробелы - один; пробелы в конце строк - прочь.
    Если у буфера есть та же вставка с разметкой абзацев (HTML) и абзацев в ней больше - берётся она."""
    text = LINE_BREAKS_RE.sub("\n", text)
    if html_text:
        html_text = LINE_BREAKS_RE.sub("\n", html_text)
        words, html_words = len(WORD_RE.findall(text)), len(WORD_RE.findall(html_text))
        if html_text.count("\n") > text.count("\n") and abs(words - html_words) <= max(2, words // 50):
            text = html_text
    text = PARAGRAPH_GAP_RE.sub("\n", text)
    text = unglue(text)
    text = SPACES_RE.sub(" ", text)
    text = re.sub(r"[ \t ]+\n", "\n", text)
    return re.sub(r"[ \t ]{2,}$", "", text)      # один пробел в конце оставляем: его копируют нарочно


ROOT_ENDINGS = sorted(set("""
ившись ывшись ешься ется ются ится атся ятся ешь ете ите
ами ями ого его ому ему ыми ими ией ость ости остью иях ием ией
ой ей ий ый ая яя ое ее ые ие ую юю ом ем ам ям ах ях ов ев ью ия ья ье ьи ию ьё
ет ют ут ит ат ят им ть ться тся сь ся
а я о е ё ы и у ю ь й
""".split()), key=len, reverse=True)


@functools.lru_cache(maxsize=65536)
def word_root(word):
    """Основа для поиска повторов: отрезается падежное или глагольное окончание целиком,
    поэтому «туман» и «тумана» - повтор, а «голоса» и «голове» - нет (раньше резались
    просто две последние буквы, и у обоих оставалось «голо»)."""
    if word.endswith(("ся", "сь")) and len(word) >= 7:      # «смотрелась» -> «смотрела» -> «смотрел»
        word = word[:-2]
    for ending in ROOT_ENDINGS:
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[:-len(ending)]
    return word


def anchor_notes(paragraphs, notes):
    """К какому абзацу теперь относится каждая заметка. Абзац ищется по своему тексту
    (точному или похожему) и по соседям сверху и снизу; заметка никогда не теряется."""
    def ratio(a, b):
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0
        return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()

    def context(i, note):
        # сосед, совпавший точно, весит вдвое больше просто похожего
        before = paragraphs[i - 1] if i > 0 else ""
        after = paragraphs[i + 1] if i + 1 < len(paragraphs) else ""
        score = 0.0
        for stored, current in ((note.get("before", ""), before), (note.get("after", ""), after)):
            if isinstance(stored, str):
                score += 1.0 if stored == current else 0.5 * ratio(stored, current)
        return score

    result = []
    for note in notes:
        anchor = note.get("anchor", "") if isinstance(note.get("anchor"), str) else ""
        index = note.get("index", 0) if isinstance(note.get("index"), int) else 0
        candidates = []
        for i, p in enumerate(paragraphs):
            if not anchor.strip() or not p.strip():
                continue
            if p == anchor:
                candidates.append((i, 1.0))
                continue
            matcher = difflib.SequenceMatcher(None, anchor, p, autojunk=False)
            if matcher.real_quick_ratio() < 0.6 or matcher.quick_ratio() < 0.6:
                continue
            score = matcher.ratio()
            if score >= 0.6:
                candidates.append((i, score))
        if candidates:
            best = max(candidates, key=lambda c: 2 * c[1] + context(c[0], note) - abs(c[0] - index) * 0.0005)
            result.append(best[0])
        else:
            result.append(max(0, min(index, len(paragraphs) - 1)))
    return result


@functools.lru_cache(maxsize=131072)
def name_key(word):
    return word.replace("\u0301", "").lower().replace("ё", "е")


def levenshtein(a, b):
    if a == b:
        return 0
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def markup_html(text):
    out = []
    for piece, bold, italic in markup_runs(text):
        piece = html.escape(piece)
        if italic:
            piece = f"<i>{piece}</i>"
        if bold:
            piece = f"<b>{piece}</b>"
        out.append(piece)
    return "".join(out)


def parse_table(text):
    """Текст CSV -> (заголовки, строки)."""
    text = text.replace("\r\n", "\n")
    if not text.strip():
        return list(C.TABLE_COLUMNS), [[""] * len(C.TABLE_COLUMNS) for _ in range(C.TABLE_ROWS)]
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    header = rows[0] if rows else list(C.TABLE_COLUMNS)
    width = max([len(header)] + [len(r) for r in rows[1:]]) or 1
    header = header + [""] * (width - len(header))
    body = [r + [""] * (width - len(r)) for r in rows[1:]]
    return header, body


def table_to_text(header, rows):
    while rows and not any(cell.strip() for cell in rows[-1]):
        rows = rows[:-1]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def is_table(path):
    return path is not None and path.suffix.lower() == ".csv"


def is_board(path):
    return path is not None and path.suffix.lower() == ".board"


def is_timeline(path):
    return path is not None and path.suffix.lower() == ".timeline"


def is_prose(path):
    """Обычный текстовый файл - глава или заметка, а не таблица, доска или хронология."""
    return not (is_table(path) or is_board(path) or is_timeline(path))


def searchable_text(path, text):
    """То, что видит человек, а не формат файла: у доски - колонки и карточки,
    у таблицы - ячейки. Иначе поиск и «Пометки» находят служебное `"cards": []`."""
    if is_board(path):
        import json
        try:
            data = json.loads(text) if text.strip() else {}
        except ValueError:
            return ""
        lines = []
        for column in data.get("columns", []) if isinstance(data, dict) else []:
            lines.append(str(column.get("title", "")))
            for card in column.get("cards", []):
                lines += [str(card.get("title", "")), str(card.get("text", ""))]
        return "\n".join(line for line in lines if line)
    if is_timeline(path):
        import json
        try:
            data = json.loads(text) if text.strip() else {}
        except ValueError:
            return ""
        lines = []
        for event in data.get("events", []) if isinstance(data, dict) else []:
            lines += [str(event.get(k, "")) for k in ("when", "title", "text") if event.get(k)]
        return "\n".join(lines)
    if is_table(path):
        header, rows = parse_table(text)
        return "\n".join("  ·  ".join(c for c in row if c.strip()) for row in [header] + rows
                         if any(c.strip() for c in row))
    return text


def markup_runs(text):
    """Строка с *курсивом* и **жирным** -> [(кусок, жирный, курсив)]."""
    runs, position = [], 0
    for m in EMPH_RE.finditer(text):
        if m.start() > position:
            runs.append((text[position:m.start()], False, False))
        if m.group(1) is not None:
            runs.append((m.group(1), True, False))
        else:
            runs.append((m.group(2), False, True))
        position = m.end()
    runs.append((text[position:], False, False))
    return [r for r in runs if r[0]]


def plain_markup(text):
    return "".join(piece for piece, _, _ in markup_runs(text))


CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_control(text):
    """Убирает невидимые служебные символы (например \\x0b из Word): docx их не принимает."""
    return CONTROL_RE.sub("", text)


DIFF_TOKEN_RE = re.compile(r"\n|[^\S\n]+|[^\s]+")
DIFF_CONTEXT = 1   # сколько неизменённых абзацев показывать вокруг правки


SIDE_TOKEN_RE = re.compile(r"\w+|\s+|[^\w\s]")     # слово, пробелы, знак - каждый отдельно


def old_side_html(old, new):
    """Старая версия целиком для панели рядом: что из неё ушло или поменялось - подсвечено,
    где в нынешнем тексте появилось новое - тонкая отметка. -> (html, сводка)."""
    gone_style = f"background:{C.rgba(C.SPELL, 60)}; color:{C.TEXT}"
    old_pars = old.replace("\r\n", "\n").split("\n")
    new_pars = new.replace("\r\n", "\n").split("\n")
    matcher = difflib.SequenceMatcher(None, old_pars, new_pars, autojunk=False)
    out, gone_words, came_words = [], 0, 0

    def para(text, style=""):
        return f"<p style='margin: 0 0 10px 0; {style}'>{text or '&nbsp;'}</p>"
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out += [para(html.escape(t)) for t in old_pars[i1:i2]]
            continue
        if tag == "insert":
            came = sum(len(WORD_RE.findall(t)) for t in new_pars[j1:j2])
            came_words += came
            out.append(para(f"＋ здесь теперь новый текст: {came} {plural(came, 'слово', 'слова', 'слов')}",
                            f"color:{C.DIM}; font-size: small"))
            continue
        before = SIDE_TOKEN_RE.findall("\n".join(old_pars[i1:i2]))
        after = SIDE_TOKEN_RE.findall("\n".join(new_pars[j1:j2]))
        pieces = []
        for wtag, a1, a2, b1, b2 in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
            text = "".join(before[a1:a2])
            came_words += len(WORD_RE.findall("".join(after[b1:b2])))
            if wtag == "equal" or not text.strip():
                pieces.append(html.escape(text))
                continue
            gone_words += len(WORD_RE.findall(text))
            pieces.append("\n".join(f"<span style='{gone_style}'>{html.escape(line)}</span>" if line else ""
                                    for line in text.split("\n")))
        out += [para(t) for t in "".join(pieces).split("\n")]
    if old == new:
        return "".join(out), "Совпадает с нынешним текстом"
    summary = (f"подсвечено то, чего теперь нет: {gone_words} {plural(gone_words, 'слово', 'слова', 'слов')}"
               f"   ·   с тех пор дописано {came_words}")
    return "".join(out), summary


def diff_html(old, new):
    """Что поменялось между двумя текстами -> (html, короткая сводка).
    Абзацы сравниваются целиком, а изменённые - по словам."""
    added_color, removed_color = C.TEXT, C.SPELL
    added_bg = C.rgba(C.TEXT, 45)
    old_pars = old.replace("\r\n", "\n").split("\n")
    new_pars = new.replace("\r\n", "\n").split("\n")
    matcher = difflib.SequenceMatcher(None, old_pars, new_pars, autojunk=False)
    added = removed = changed = 0
    out = []

    def para(text, style=""):
        return f"<p style='margin: 0 0 10px 0; {style}'>{text or '&nbsp;'}</p>"

    def wrap(text, style):
        # перенос абзаца остаётся снаружи: каждая строка оборачивается отдельно
        return "\n".join(f"<span style='{style}'>{html.escape(line)}</span>" if line else ""
                         for line in text.split("\n"))

    def ins(text):
        return wrap(text, f"color:{added_color}; background:{added_bg}")

    def rem(text):
        return wrap(text, f"color:{removed_color}; text-decoration: line-through")

    opcodes = matcher.get_opcodes()
    for index, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag == "equal":
            block = new_pars[j1:j2]
            keep_head = DIFF_CONTEXT if index > 0 else 0
            keep_tail = DIFF_CONTEXT if index < len(opcodes) - 1 else 0
            if len(block) > keep_head + keep_tail + 1:
                for text in block[:keep_head]:
                    out.append(para(html.escape(text), f"color:{C.DIM}"))
                hidden = len(block) - keep_head - keep_tail
                out.append(para(f"· · ·   {hidden} {plural(hidden, 'абзац', 'абзаца', 'абзацев')} без изменений",
                                f"color:{C.DIM}; text-align: center"))
                for text in block[len(block) - keep_tail:]:
                    out.append(para(html.escape(text), f"color:{C.DIM}"))
            else:
                for text in block:
                    out.append(para(html.escape(text), f"color:{C.DIM}"))
            continue
        changed += max(i2 - i1, j2 - j1)
        before = DIFF_TOKEN_RE.findall("\n".join(old_pars[i1:i2]))
        after = DIFF_TOKEN_RE.findall("\n".join(new_pars[j1:j2]))
        words = difflib.SequenceMatcher(None, before, after, autojunk=False)
        pieces = []
        for wtag, a1, a2, b1, b2 in words.get_opcodes():
            if wtag == "equal":
                pieces.append(html.escape("".join(after[b1:b2])))
                continue
            gone, came = "".join(before[a1:a2]), "".join(after[b1:b2])
            removed += len(WORD_RE.findall(gone))
            added += len(WORD_RE.findall(came))
            if gone.strip():
                pieces.append(rem(gone))
            if came.strip():
                pieces.append(ins(came))
            elif came:
                pieces.append(html.escape(came))
        joined = "".join(pieces)
        for text in joined.split("\n"):
            out.append(para(text))
    if not added and not removed and old == new:
        return para("Изменений нет", f"color:{C.DIM}"), "Изменений нет"
    summary = (f"+{added} {plural(added, 'слово', 'слова', 'слов')}   "
               f"−{removed} {plural(removed, 'слово', 'слова', 'слов')}")
    summary += f"   ·   {changed} {plural(changed, 'абзац затронут', 'абзаца затронуто', 'абзацев затронуто')}"
    return "".join(out), summary


# ---- кнопки и клавиши разметки: включают и выключают, а не копят звёздочки ----
STRESS = "́"
VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯaeiouyAEIOUY")


def _pair(mark):
    return ("[", "]") if mark == "[]" else (mark, mark)


def _star_runs(line, start, end):
    left = 0
    while start - left - 1 >= 0 and line[start - left - 1] == "*":
        left += 1
    right = 0
    while end + right < len(line) and line[end + right] == "*":
        right += 1
    return left, right


def markup_wrapped(line, start, end, mark):
    """Обёрнут ли кусок строки этой разметкой."""
    return _wrapped(line, start, end, mark)


def _wrapped(line, start, end, mark):
    if mark == "[]":
        return start > 0 and line[start - 1] == "[" and end < len(line) and line[end] == "]"
    left, right = _star_runs(line, start, end)
    if mark == "*":
        return left in (1, 3) and right in (1, 3)
    return left >= 2 and right >= 2


def _unwrap(line, start, end, mark):
    n = 1 if mark == "[]" else len(mark)
    return line[:start - n] + line[start:end] + line[end + n:], start - n, end - n


def _wrap(line, start, end, mark):
    opening, closing = _pair(mark)
    return line[:start] + opening + line[start:end] + closing + line[end:], start + len(opening), end + len(opening)


def _inside(prefix, mark):
    """Открыта ли разметка к этому месту строки (нечётное число открывающих)."""
    if mark == "[]":
        return prefix.rfind("[") > prefix.rfind("]")
    runs = [len(run) for run in re.findall(r"\*+", prefix)]
    count = sum(n % 2 for n in runs) if mark == "*" else sum(n // 2 for n in runs)
    return count % 2 == 1


def markup_range(line, start, end, mark):
    """Выделение без пробелов по краям и без самих знаков разметки, если их выделили вместе со словом."""
    while start < end and line[start].isspace():
        start += 1
    while end > start and line[end - 1].isspace():
        end -= 1
    if end - start > 2 and mark == "[]" and line[start] == "[" and line[end - 1] == "]":
        start, end = start + 1, end - 1
    elif mark != "[]":
        lead = len(line[start:end]) - len(line[start:end].lstrip("*"))
        tail = len(line[start:end]) - len(line[start:end].rstrip("*"))
        k = min(lead, tail)
        if k and end - start > 2 * k:
            start, end = start + k, end - k
    return start, end


def toggle_markup(line, start, end, mark, action=None):
    """Курсив «*», жирный «**» или пометка «[]» для куска строки.
    Выделено - обернуть или снять, если уже обёрнуто. Без выделения: внутри пустой пары - убрать её,
    перед закрывающим знаком - выйти за него, внутри слова - обернуть слово, иначе - поставить пару
    и курсор внутрь. Возвращает (новая строка, начало, конец) - куда поставить выделение."""
    if start != end:
        start, end = markup_range(line, start, end, mark)
        if start != end:
            has = _wrapped(line, start, end, mark)
            if action == "remove" or (action is None and has):
                return _unwrap(line, start, end, mark) if has else (line, start, end)
            return _wrap(line, start, end, mark)
    p = start
    if _wrapped(line, p, p, mark):                                       # «*|*» - передумал
        new, p, _ = _unwrap(line, p, p, mark)
        return new, p, p
    _opening, closing = _pair(mark)
    if line.startswith(closing, p) and _inside(line[:p], mark):          # «*текст|*» - выйти
        return line, p + len(closing), p + len(closing)
    for word in WORD_RE.finditer(line):
        if word.start() < p < word.end():                                # внутри слова - само слово
            a, b = word.start(), word.end()
            if _wrapped(line, a, b, mark):
                new, a2, _ = _unwrap(line, a, b, mark)
                return new, p - (a - a2), p - (a - a2)
            new, a2, _ = _wrap(line, a, b, mark)
            return new, p + (a2 - a), p + (a2 - a)
        if word.start() > p:
            break
    new, a, _ = _wrap(line, p, p, mark)
    return new, a, a


def toggle_stress(line, pos):
    """Ударение после гласной перед курсором. Нажал ещё раз - убрал. В слове одно ударение:
    новое заменяет старое. Возвращает (строка, позиция) или None, если перед курсором не гласная."""
    if pos > 0 and line[pos - 1] == STRESS:
        return line[:pos - 1] + line[pos:], pos - 1
    if pos < len(line) and line[pos] == STRESS:
        return line[:pos] + line[pos + 1:], pos
    if pos == 0 or line[pos - 1] not in VOWELS:
        return None
    a = pos
    while a > 0 and (line[a - 1].isalpha() or line[a - 1] == STRESS):
        a -= 1
    b = pos
    while b < len(line) and (line[b].isalpha() or line[b] == STRESS):
        b += 1
    before, after = line[a:pos].replace(STRESS, ""), line[pos:b].replace(STRESS, "")
    return line[:a] + before + STRESS + after + line[b:], a + len(before) + 1


def smart_yo(line, start, end):
    """«ё» или «Ё»: в начале предложения - заглавная; выделенная «е» меняется на «ё»."""
    selected = line[start:end]
    if selected in ("е", "Е"):
        return "ё" if selected == "е" else "Ё"
    before = line[:start].rstrip()
    capital = not before or before[-1] in ".!?…" or before in ("—", "–", "-")
    return "Ё" if capital else "ё"


# ---- мои штампы: слова-костыли автора, с формами слова ----
CRUTCH_ENDINGS = set("""
а я о е и ы у ю ь й ой ей ий ый ая яя ое ее ие ые ого его ому ему ым им ом ем ую юю ах ях ам ям ами ями
ов ев ою ею ешь ет ете ут ют ит ите ат ят ишь л ла ло ли ся сь ась ось ись лся лась лось лись ть ться
ешься ется ются ится ятся
""".split()) | {""}


def crutch_base(word):
    """Основа штампа, к которой прибавляются окончания: «вздохнул» -> «вздохну» (+л, +ла, +ли).
    Короткие слова (до 4 букв) - только точное совпадение."""
    word = name_key(word)
    if len(word) <= 4:
        return None
    for size in range(min(4, len(word) - 4), 0, -1):
        if word[-size:] in CRUTCH_ENDINGS:
            return word[:-size]
    return word


def _crutch_word_ok(token, word, base):
    token = name_key(token)
    if token == word:
        return True
    return base is not None and token.startswith(base) and token[len(base):] in CRUTCH_ENDINGS


CRUTCH_GAP = re.compile(r"[^\S\n]*[,;:—–-]?[^\S\n]*")


class Crutches:
    """Список штампов: «вдруг», «вздохнул», «почувствовал, как». Ищет их в строке с формами слова."""

    def __init__(self, entries):
        self.entries = []
        self.by_start = {}     # первые три буквы первого слова -> штампы: в строке проверяются только они
        for entry in entries:
            words = [m.group() for m in WORD_RE.finditer(entry)]
            if words:
                item = (entry.strip(), [(name_key(w), crutch_base(w)) for w in words])
                self.entries.append(item)
                self.by_start.setdefault(item[1][0][0][:3], []).append(item)

    def __bool__(self):
        return bool(self.entries)

    def spans(self, line):
        """[(начало, конец, штамп)] в строке; длинные штампы важнее коротких, без наложений."""
        if not self.entries:
            return []
        tokens = list(WORD_RE.finditer(line))
        keys = [name_key(t.group()) for t in tokens]
        found = []
        for i in range(len(tokens)):
            for entry, words in self.by_start.get(keys[i][:3], ()):
                if i + len(words) > len(tokens):
                    continue
                ok = True
                for k, (word, base) in enumerate(words):
                    if not _crutch_word_ok(keys[i + k], word, base):
                        ok = False
                        break
                    if k and not CRUTCH_GAP.fullmatch(line[tokens[i + k - 1].end():tokens[i + k].start()]):
                        ok = False
                        break
                if ok:
                    found.append((tokens[i].start(), tokens[i + len(words) - 1].end(), entry))
        found.sort(key=lambda s: (s[0], -(s[1] - s[0])))
        result, last = [], -1
        for start, end, entry in found:
            if start >= last:
                result.append((start, end, entry))
                last = end
        return result

    def count(self, text):
        """{штамп: сколько раз} по всему тексту."""
        counts = {}
        for line in text.split("\n"):
            for _start, _end, entry in self.spans(line):
                counts[entry] = counts.get(entry, 0) + 1
        return counts


def _sentence_start(before):
    stripped = before.rstrip(" \t«\"„(")
    return not stripped or stripped[-1] in ".!?…" or stripped in ("—", "–", "-")


def delete_span(line, start, end):
    """Вырезает штамп из строки так, чтобы не остались двойные пробелы, «, ,» и строчная буква
    в начале предложения. Возвращает (строка, позиция курсора)."""
    capital = line[start:end][:1].isupper()
    at_start = _sentence_start(line[:start])
    before, after = line[:start], line[end:]
    # «Он, однако, пришёл» -> «Он пришёл»; «Однако, он» -> «Он»
    if after.lstrip(" ").startswith(","):
        stripped_before = before.rstrip(" ")
        if stripped_before.endswith(","):
            before = stripped_before[:-1]
            after = after.lstrip(" ")[1:]
        elif at_start:
            after = after.lstrip(" ")[1:]
    if before.endswith(" ") and (after.startswith(" ") or after[:1] in (".", ",", "!", "?", "…", ";", ":") or not after):
        before = before.rstrip(" ")
        if after[:1] not in (".", ",", "!", "?", "…", ";", ":") and after:
            before += " "
            after = after.lstrip(" ")
    elif not before.strip():
        after = after.lstrip(" ")
    if at_start and capital and after[:1].islower():
        after = after[0].upper() + after[1:]
    return before + after, len(before)


def replace_span(line, start, end, replacement):
    """Заменяет штамп словом, сохраняя заглавную букву. Пустая замена - удаление."""
    if not replacement.strip():
        return delete_span(line, start, end)
    replacement = replacement.strip()
    if line[start:end][:1].isupper():
        replacement = replacement[0].upper() + replacement[1:]
    return line[:start] + replacement + line[end:], start + len(replacement)
