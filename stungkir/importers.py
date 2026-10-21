# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Импорт чужих форматов: Word (.docx), LibreOffice (.odt), RTF, FB2, EPUB, HTML, таблицы Excel (.xlsx)
и Calc (.ods), проекты Scrivener (.scriv).
Здесь нет окон: функции возвращают главы и заметки, а кладёт их на диск главное окно."""

import codecs
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .textutil import clean_control

# заголовок главы в тексте без стилей Word: «Глава 3», «ГЛАВА ПЕРВАЯ. Туман», «Пролог»
CHAPTER_LINE_RE = re.compile(r"^\s*(глава|часть|пролог|эпилог|интерлюдия|chapter|prologue|epilogue)\b",
                             re.IGNORECASE)
CHAPTER_LINE_MAX = 80
# символы, которые не любят телефоны и флешки (Android, FAT), заменяем на тире
BAD_NAME_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
NAME_LIMIT = 80


def safe_name(text, fallback="Без названия"):
    """Название главы или категории, которое можно сделать именем файла."""
    name = BAD_NAME_RE.sub("-", clean_control(text)).strip(" .-")
    name = re.sub(r"\s+", " ", name)
    if len(name) > NAME_LIMIT:
        cut = name.rfind(" ", 0, NAME_LIMIT)
        name = name[:cut if cut > NAME_LIMIT // 2 else NAME_LIMIT].rstrip(" .,-")
    return name or fallback


def runs_to_markup(runs):
    """[(кусок, жирный, курсив)] -> строка с *курсивом* и **жирным**.
    Соседние куски с одинаковым начертанием склеиваются, пробелы остаются снаружи звёздочек."""
    merged = []
    for text, bold, italic in runs:
        if not text:
            continue
        if merged and (merged[-1][1], merged[-1][2]) == (bold, italic):
            merged[-1][0] += text
        else:
            merged.append([text, bold, italic])
    out = []
    for text, bold, italic in merged:
        core = text.strip()
        if not core or not (bold or italic):
            out.append(text)
            continue
        left = text[:len(text) - len(text.lstrip())]
        right = text[len(text.rstrip()):]
        mark = "**" if bold else "*"
        if bold and italic:
            core = f"*{core}*"
        out.append(f"{left}{mark}{core}{mark}{right}")
    return "".join(out)


def split_chapters(paragraphs, fallback):
    """[(текст, уровень заголовка)] -> [(название, [абзацы])].
    Режем по заголовкам самого верхнего уровня, а если стилей заголовков нет - по строкам «Глава …».
    Текст до первого заголовка становится главой с названием fallback."""
    levels = [level for _text, level in paragraphs if level]
    top = min(levels) if levels else None
    chapters, name, body = [], None, []

    def flush():
        if name is not None or any(line.strip() for line in body):
            chapters.append((name or fallback, [line for line in body if line.strip()]))

    for text, level in paragraphs:
        plain = re.sub(r"\*+", "", text).strip()
        if top is not None:
            starts = level == top
        else:
            starts = bool(CHAPTER_LINE_RE.match(plain)) and len(plain) <= CHAPTER_LINE_MAX
        if starts and plain:
            flush()
            name, body = plain, []
        elif level and plain:
            body.append(plain)          # заголовок пониже - просто строка текста
        else:
            body.append(text)
    flush()
    return chapters


# ---------------- Word ----------------
def _heading_level(paragraph):
    style = paragraph.style
    while style is not None:
        name = (style.name or "").lower()
        m = re.match(r"(heading|заголовок)\s*(\d)", name)
        if m:
            return int(m.group(2))
        if name in ("title", "название"):
            return 0
        style = style.base_style
    level = paragraph._p.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}outlineLvl")
    if level is not None:
        value = level.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
        if value is not None and value.isdigit() and int(value) < 9:
            return int(value) + 1
    return 0


def _run_flag(run, attribute):
    value = getattr(run, attribute)
    if value is None and run.style is not None:
        value = getattr(run.style.font, attribute)
    return bool(value)


def docx_paragraphs(path):
    """Абзацы файла Word -> [(текст с разметкой, уровень заголовка или 0)]."""
    import docx
    document = docx.Document(str(path))
    out = []
    for paragraph in document.paragraphs:
        runs = []
        items = paragraph.iter_inner_content() if hasattr(paragraph, "iter_inner_content") else paragraph.runs
        for item in items:
            for run in getattr(item, "runs", [item]):
                runs.append((run.text, _run_flag(run, "bold"), _run_flag(run, "italic")))
        level = _heading_level(paragraph)
        text = clean_control(runs_to_markup(runs))
        if level:
            text = re.sub(r"\*+", "", text)
        # мягкий перенос строки внутри абзаца (стихи, письма) - отдельная строка
        for line in text.split("\n"):
            out.append((line.rstrip(), level if line.strip() else 0))
    return out


# ---------------- RTF ----------------
RTF_SKIP = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "header", "footer", "headerl", "headerr",
            "headerf", "footerl", "footerr", "footerf", "listtable", "listoverridetable", "rsidtbl",
            "generator", "xmlnstbl", "themedata", "colorschememapping", "latentstyles", "datastore",
            "mmathPr", "fldinst", "object", "footnote", "annotation", "expandedcolortbl", "filetbl",
            "revtbl", "pgdsctbl", "nonshppict", "shp", "bkmkstart", "bkmkend", "atnid", "atnauthor"}
RTF_SYMBOLS = {"emdash": "—", "endash": "–", "lquote": "‘", "rquote": "’", "ldblquote": "“",
               "rdblquote": "”", "bullet": "•", "tab": "\t", "~": "\u00a0", "_": "-", "-": ""}
RTF_TOKEN_RE = re.compile(rb"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|([^\\{}\r\n]+)|[\r\n]+",
                          re.S)


def rtf_to_lines(data):
    """RTF -> строки-абзацы с *курсивом* и **жирным**. Понимает русский и в \\uNNNN,
    и в \\'hh с кодовой страницей документа (Scrivener на Mac и Windows пишет по-разному)."""
    if isinstance(data, str):
        data = data.encode("latin-1", "replace")
    codepage = "cp1252"
    stack = []
    state = {"bold": False, "italic": False, "skip": False, "uc": 1}
    pending_bytes = bytearray()
    lines, runs = [], []
    skip_chars = 0
    star = False        # после \* весь блок - служебный

    def emit(text):
        nonlocal skip_chars
        if state["skip"] or not text:
            return
        if skip_chars:
            drop = min(skip_chars, len(text))
            text = text[drop:]
            skip_chars -= drop
            if not text:
                return
        runs.append((text, state["bold"], state["italic"]))

    def flush_bytes():
        if pending_bytes:
            try:
                text = bytes(pending_bytes).decode(codepage, "replace")
            except LookupError:
                text = bytes(pending_bytes).decode("cp1252", "replace")
            pending_bytes.clear()
            emit(text)

    def end_paragraph():
        flush_bytes()
        lines.append(runs_to_markup(runs))
        runs.clear()

    for m in RTF_TOKEN_RE.finditer(data):
        word, number, hexbyte, symbol, brace, text = m.groups()
        if hexbyte is not None:
            if skip_chars:
                skip_chars -= 1
                continue
            pending_bytes.append(int(hexbyte, 16))
            continue
        flush_bytes()
        if brace == b"{":
            stack.append(dict(state))
            star = False
        elif brace == b"}":
            if stack:
                state = stack.pop()
            skip_chars = 0
        elif word is not None:
            word = word.decode("ascii")
            if star or word in RTF_SKIP:
                state["skip"] = True
                star = False
                continue
            value = int(number) if number is not None else None
            if word in ("par", "line", "sect", "page") and not state["skip"]:
                end_paragraph()
            elif word == "b":
                state["bold"] = value != 0
            elif word == "i":
                state["italic"] = value != 0
            elif word == "plain":
                state["bold"] = state["italic"] = False
            elif word == "ansicpg" and value:
                codepage = f"cp{value}"
                try:
                    codecs.lookup(codepage)
                except LookupError:
                    codepage = "cp1252"
            elif word == "uc" and value is not None:
                state["uc"] = value
            elif word == "u" and value is not None:
                emit(chr(value + 65536 if value < 0 else value))
                skip_chars = state["uc"]
            elif word in RTF_SYMBOLS:
                emit(RTF_SYMBOLS[word])
        elif symbol is not None:
            ch = symbol.decode("latin-1")
            if ch == "*":
                star = True
            elif ch in "\\{}":
                emit(ch)
            elif ch in RTF_SYMBOLS:
                emit(RTF_SYMBOLS[ch])
            elif ch in "\r\n" and not state["skip"]:
                end_paragraph()       # «\» в конце строки = \par
        elif text is not None:
            if skip_chars:
                drop = min(skip_chars, len(text))
                text = text[drop:]
                skip_chars -= drop
            emit(text.decode(codepage, "replace") if text else "")
    end_paragraph()
    while lines and not lines[-1].strip():
        lines.pop()
    return [clean_control(line) for line in lines]


# ---------------- Scrivener ----------------
class ScrivenerError(Exception):
    """Папка не похожа на проект Scrivener или он повреждён."""


SCENE_BREAK = "* * *"


class ScrivenerItem:
    def __init__(self, kind, title, ident):
        self.kind, self.title, self.ident = kind, title, ident
        self.children = []
        self.lines, self.synopsis, self.notes = [], "", ""


def _read_rtf(path):
    try:
        return rtf_to_lines(path.read_bytes()) if path.is_file() else []
    except OSError:
        return []


def _read_plain(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip() if path.is_file() else ""
    except OSError:
        return ""


def read_scrivener(folder):
    """Папка .scriv -> (название проекта, [корневые элементы ScrivenerItem]).
    Поддерживает Scrivener 3 (Files/Data/<UUID>/content.rtf) и 2 / Windows 1 (Files/Docs/<ID>.rtf)."""
    folder = Path(folder)
    projects = sorted(folder.glob("*.scrivx"))
    if not projects:
        raise ScrivenerError("в папке нет файла .scrivx - это не проект Scrivener")
    try:
        root = ET.parse(projects[0]).getroot()
    except (ET.ParseError, OSError) as error:
        raise ScrivenerError(f"файл {projects[0].name} не читается: {error}") from error
    binder = root.find("Binder")
    if binder is None:
        raise ScrivenerError("в проекте нет списка документов (Binder)")

    def load(element):
        ident = element.get("UUID") or element.get("ID") or ""
        item = ScrivenerItem(element.get("Type", "Text"), (element.findtext("Title") or "").strip(), ident)
        data = folder / "Files" / "Data" / ident
        if data.is_dir():
            item.lines = _read_rtf(data / "content.rtf")
            item.synopsis = _read_plain(data / "synopsis.txt")
            item.notes = "\n".join(_read_rtf(data / "notes.rtf")).strip()
        else:
            docs = folder / "Files" / "Docs"
            item.lines = _read_rtf(docs / f"{ident}.rtf")
            item.synopsis = _read_plain(docs / f"{ident}_synopsis.txt")
            item.notes = "\n".join(_read_rtf(docs / f"{ident}_notes.rtf")).strip()
        children = element.find("Children")
        if children is not None:
            item.children = [load(child) for child in children.findall("BinderItem")]
        return item

    name = projects[0].stem
    return name, [load(element) for element in binder.findall("BinderItem")]


def flatten_item(item):
    """Папка Scrivener со всеми вложенными сценами -> (строки, заметки к строкам).
    Сцены разделяются «* * *», синопсис и заметки сцены становятся заметкой на полях к её первой строке."""
    lines, notes = [], []
    text = [line for line in item.lines if line.strip()]
    note = "\n\n".join(x for x in (item.synopsis, item.notes) if x)
    if note:
        notes.append((0, (f"{item.title}: " if item.title else "") + note))
    lines.extend(text)
    for child in item.children:
        if child.kind in ("Text", "Folder"):
            child_lines, child_notes = flatten_item(child)
            if child_lines and lines:
                lines.append(SCENE_BREAK)
            offset = len(lines)
            notes += [(offset + i, text) for i, text in child_notes]
            lines += child_lines
    # заметку к пустому месту в конце вешаем на последнюю строку
    notes = [(min(i, max(0, len(lines) - 1)), text) for i, text in notes]
    return lines, notes


def scrivener_plan(name, items):
    """Что создать: [(категория, [(глава, строки, заметки)]), …] и сколько файлов пропущено.
    Рукопись (Draft) -> категория с названием проекта, каждая верхняя папка или текст - глава.
    Материалы и свои папки -> отдельные категории, корзина пропускается."""
    plan, skipped = [], 0

    def chapters_of(children):
        nonlocal skipped
        chapters = []
        for child in children:
            if child.kind not in ("Text", "Folder"):
                skipped += 1 + sum(1 for _ in _walk(child))
                continue
            lines, notes = flatten_item(child)
            if lines or child.kind == "Text":
                chapters.append((safe_name(child.title, "Глава"), lines, notes))
            skipped += sum(1 for c in _walk(child) if c.kind not in ("Text", "Folder"))
        return chapters

    for item in items:
        if item.kind == "TrashFolder":
            continue
        if item.kind == "DraftFolder":
            category = safe_name(name, "Рукопись")
        elif item.kind == "ResearchFolder":
            category = safe_name(f"{name} · материалы", "Материалы")
        elif item.kind == "Folder":
            category = safe_name(item.title, "Папка")
        else:
            plan.append((safe_name(name, "Рукопись"), chapters_of([item])))
            continue
        chapters = chapters_of(item.children)
        if chapters:
            plan.append((category, chapters))
    # одинаковые категории (тексты в корне и рукопись) объединяем
    merged = {}
    for category, chapters in plan:
        merged.setdefault(category, []).extend(chapters)
    return list(merged.items()), skipped


def _walk(item):
    for child in item.children:
        yield child
        yield from _walk(child)


# ---------------- HTML, EPUB, FB2, ODT, Markdown ----------------
# все читатели возвращают то же, что docx_paragraphs: [(текст с *курсивом* и **жирным**, уровень заголовка)]
from html.parser import HTMLParser                                     # noqa: E402

BLOCK_TAGS = {"p", "div", "li", "blockquote", "pre", "dd", "dt", "tr", "section", "article"}
HEAD_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


class _HtmlText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.runs = [], []
        self.bold = self.italic = self.skip = 0
        self.level = 0

    def _flush(self):
        text = clean_control(runs_to_markup(self.runs)).strip()
        if self.level:
            text = re.sub(r"\*+", "", text)
        for line in text.split("\n"):
            if line.strip():
                self.out.append((line.strip(), self.level))
        self.runs = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "title"):
            self.skip += 1
        elif tag in ("b", "strong"):
            self.bold += 1
        elif tag in ("i", "em", "cite"):
            self.italic += 1
        elif tag == "br":
            self.runs.append(("\n", False, False))
        elif tag in BLOCK_TAGS or tag in HEAD_TAGS:
            self._flush()
            self.level = HEAD_TAGS.get(tag, 0)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "title"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("b", "strong"):
            self.bold = max(0, self.bold - 1)
        elif tag in ("i", "em", "cite"):
            self.italic = max(0, self.italic - 1)
        elif tag in BLOCK_TAGS or tag in HEAD_TAGS:
            self._flush()
            self.level = 0

    def handle_data(self, data):
        if self.skip:
            return
        data = re.sub(r"\s+", " ", data)
        if data.strip() or self.runs:
            self.runs.append((data, bool(self.bold), bool(self.italic)))

    def result(self):
        self._flush()
        return self.out


def html_paragraphs(text):
    parser = _HtmlText()
    parser.feed(text)
    parser.close()
    return parser.result()


def _decode(data):
    for encoding in ("utf-8", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def html_file_paragraphs(path):
    return html_paragraphs(_decode(Path(path).read_bytes()))


def epub_paragraphs(path):
    """EPUB: главы по порядку чтения (spine), каждая - со своими заголовками."""
    import posixpath
    import zipfile
    with zipfile.ZipFile(path) as book:
        container = ET.fromstring(book.read("META-INF/container.xml"))
        rootfile = next(e.get("full-path") for e in container.iter() if e.tag.endswith("rootfile"))
        opf = ET.fromstring(book.read(rootfile))
        base = posixpath.dirname(rootfile)
        items = {e.get("id"): e.get("href") for e in opf.iter() if e.tag.endswith("}item")}
        order = [e.get("idref") for e in opf.iter() if e.tag.endswith("}itemref")]
        out = []
        for idref in order:
            href = items.get(idref)
            if not href or not href.lower().endswith((".xhtml", ".html", ".htm")):
                continue
            name = posixpath.normpath(posixpath.join(base, href.split("#")[0]))
            try:
                out += html_paragraphs(_decode(book.read(name)))
            except KeyError:
                continue
    return out


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _fb2_runs(element, bold=False, italic=False):
    runs = [(element.text or "", bold, italic)]
    for child in element:
        tag = _local(child.tag)
        runs += _fb2_runs(child, bold or tag == "strong", italic or tag == "emphasis")
        runs.append((child.tail or "", bold, italic))
    return runs


def fb2_paragraphs(path):
    """FB2: разделы (section) - главы, их заголовки - заголовки; стихи и эпиграфы - строками текста."""
    root = ET.fromstring(Path(path).read_bytes())
    out = []

    def walk(element, depth):
        for child in element:
            tag = _local(child.tag)
            if tag == "section":
                walk(child, depth + 1)
            elif tag == "title":
                title = " ".join(clean_control("".join(t for t, _b, _i in _fb2_runs(p))).strip()
                                 for p in child if _local(p.tag) == "p")
                if title.strip():
                    out.append((title.strip(), max(1, depth)))
            elif tag in ("p", "v", "subtitle", "text-author"):
                text = clean_control(runs_to_markup(_fb2_runs(child))).strip()
                if text:
                    out.append((text, 0))
            elif tag == "empty-line":
                out.append(("", 0))
            elif tag in ("poem", "stanza", "epigraph", "cite"):
                walk(child, depth)
    for body in root:
        if _local(body.tag) == "body" and body.get("name") not in ("notes", "comments"):
            walk(body, 0)
    return out


ODT_NS = {"text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
          "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
          "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
          "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
          "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0"}


def _q(prefix, name):
    return f"{{{ODT_NS[prefix]}}}{name}"


def _odt_styles(root):
    """Имя стиля -> (жирный, курсив) из автоматических стилей документа."""
    found = {}
    for style in root.iter(_q("style", "style")):
        props = style.find(_q("style", "text-properties"))
        if props is not None:
            found[style.get(_q("style", "name"))] = (props.get(_q("fo", "font-weight")) == "bold",
                                                     props.get(_q("fo", "font-style")) == "italic")
    return found


def _odt_runs(element, styles, bold=False, italic=False):
    flags = styles.get(element.get(_q("text", "style-name")), (False, False))
    bold, italic = bold or flags[0], italic or flags[1]
    runs = [(element.text or "", bold, italic)]
    for child in element:
        tag = _local(child.tag)
        if tag == "s":
            runs.append((" " * int(child.get(_q("text", "c"), "1")), bold, italic))
        elif tag == "tab":
            runs.append(("\t", bold, italic))
        elif tag == "line-break":
            runs.append(("\n", bold, italic))
        elif tag not in ("note", "annotation"):
            runs += _odt_runs(child, styles, bold, italic)
        runs.append((child.tail or "", bold, italic))
    return runs


def odt_paragraphs(path):
    """LibreOffice Writer (.odt): абзацы и заголовки с уровнями, курсив и жирный."""
    import zipfile
    with zipfile.ZipFile(path) as document:
        root = ET.fromstring(document.read("content.xml"))
    styles = _odt_styles(root)
    out = []
    for element in root.iter():
        tag = _local(element.tag)
        if tag not in ("p", "h") or not element.tag.startswith(f"{{{ODT_NS['text']}}}"):
            continue
        level = int(element.get(_q("text", "outline-level"), "1")) if tag == "h" else 0
        text = clean_control(runs_to_markup(_odt_runs(element, styles)))
        if level:
            text = re.sub(r"\*+", "", text)
        for line in text.split("\n"):
            out.append((line.rstrip(), level if line.strip() else 0))
    return out


def rtf_paragraphs(path):
    return [(line, 0) for line in rtf_to_lines(Path(path).read_bytes())]


DOCUMENT_READERS = {".docx": "docx_paragraphs", ".odt": odt_paragraphs, ".rtf": rtf_paragraphs,
                    ".fb2": fb2_paragraphs, ".epub": epub_paragraphs, ".html": html_file_paragraphs,
                    ".htm": html_file_paragraphs, ".xhtml": html_file_paragraphs}


def read_document(path):
    """Книга или документ чужого формата -> абзацы с уровнями заголовков."""
    reader = DOCUMENT_READERS[Path(path).suffix.lower()]
    if reader == "docx_paragraphs":
        reader = docx_paragraphs
    return reader(path)


# ---------------- таблицы: Excel и LibreOffice Calc ----------------
SHEET_LIMIT = 2000                     # строк и столбцов: пустые «до конца листа» не тащим


def _trim(rows):
    rows = [[cell.strip() for cell in row] for row in rows]
    while rows and not any(rows[-1]):
        rows.pop()
    width = max((max((i + 1 for i, c in enumerate(row) if c), default=0) for row in rows), default=0)
    return [(row + [""] * width)[:width] for row in rows]


def xlsx_tables(path):
    """Excel (.xlsx) -> [(название листа, строки)]. Формулы - их последнее значение."""
    import zipfile
    main = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    with zipfile.ZipFile(path) as book:
        names = book.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            for item in ET.fromstring(book.read("xl/sharedStrings.xml")).iter(f"{main}si"):
                shared.append("".join(t.text or "" for t in item.iter(f"{main}t")))
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        tables = []
        for sheet in workbook.iter(f"{main}sheet"):
            target = targets.get(sheet.get(f"{rel}id"), "")
            member = "xl/" + target.lstrip("/").removeprefix("xl/")
            if member not in names:
                continue
            rows = {}
            for row in ET.fromstring(book.read(member)).iter(f"{main}row"):
                for cell in row.iter(f"{main}c"):
                    ref = cell.get("r", "")
                    letters = "".join(ch for ch in ref if ch.isalpha())
                    column = 0
                    for ch in letters:
                        column = column * 26 + (ord(ch.upper()) - 64)
                    number = int("".join(ch for ch in ref if ch.isdigit()) or 0)
                    if not (0 < column <= SHEET_LIMIT and 0 < number <= SHEET_LIMIT):
                        continue
                    kind, value = cell.get("t"), cell.find(f"{main}v")
                    if kind == "s" and value is not None:
                        text = shared[int(value.text)] if value.text and int(value.text) < len(shared) else ""
                    elif kind == "inlineStr":
                        text = "".join(t.text or "" for t in cell.iter(f"{main}t"))
                    else:
                        text = value.text if value is not None and value.text else ""
                        if text.endswith(".0") and text[:-2].lstrip("-").isdigit():
                            text = text[:-2]
                    rows.setdefault(number, {})[column] = clean_control(text)
            grid = [[rows.get(r, {}).get(c, "") for c in range(1, max((max(v) for v in rows.values()), default=0) + 1)]
                    for r in range(1, max(rows, default=0) + 1)]
            tables.append((sheet.get("name") or "Лист", _trim(grid)))
    return tables


def ods_tables(path):
    """LibreOffice Calc (.ods) -> [(название листа, строки)]."""
    import zipfile
    with zipfile.ZipFile(path) as book:
        root = ET.fromstring(book.read("content.xml"))
    tables = []
    for table in root.iter(_q("table", "table")):
        grid = []
        for row in table.iter(_q("table", "table-row")):
            repeat_rows = min(int(row.get(_q("table", "number-rows-repeated"), "1")), SHEET_LIMIT)
            cells = []
            for cell in row:
                if _local(cell.tag) not in ("table-cell", "covered-table-cell"):
                    continue
                text = "\n".join("".join(t for t, _b, _i in _odt_runs(p, {})) for p in cell
                                 if _local(p.tag) == "p")
                repeat = min(int(cell.get(_q("table", "number-columns-repeated"), "1")), SHEET_LIMIT)
                cells += [clean_control(text)] * repeat
                if len(cells) >= SHEET_LIMIT:
                    break
            grid += [cells[:SHEET_LIMIT]] * (repeat_rows if any(c.strip() for c in cells) else min(repeat_rows, 1))
            if len(grid) >= SHEET_LIMIT:
                break
        tables.append((table.get(_q("table", "name")) or "Лист", _trim(grid)))
    return tables


TABLE_READERS = {".xlsx": xlsx_tables, ".ods": ods_tables}
