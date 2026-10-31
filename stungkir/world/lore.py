# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Справочник мира: термины, их формы в тексте, подсказки и поиск разного написания."""

import html
import json
import re

from ..core import config as C
from ..core.textutil import CYR_PART, MARKER_RE, levenshtein, markup_html, name_key, parse_table, plural
from ..core.storage import report_problem, write_atomic


# окончания, с которыми слово считается формой термина: «Давнь», «Давня», «Давнем»
LORE_ENDINGS = frozenset("""
а я у ю е и ы о ь й ой ей ом ем ам ям ами ями ах ях ов ев ью ий ый ая яя ое ее ые ие
ого его ому ему ым им ых их ую юю ыми ими ия ию ии
""".split()) | {""}
LORE_ALIASES_RE = re.compile(r"^\s*(?:также|ещё|еще|другие имена|синонимы)\s*:\s*(.+)$", re.IGNORECASE)
LORE_ALIAS_COLUMNS = {"также", "другие имена", "синонимы"}
# «Родилась: 1203» в заметке - год рождения в летоисчислении книги; по нему считается возраст в главе
BIRTH_RE = re.compile(r"^\s*(?:родил(?:ся|ась|ось|ись)|год рождения|рождение)\s*:?\s*(-?\d+(?:[.,]\d+)?)",
                      re.IGNORECASE)
LORE_NOTE_LIMIT = 420
LORE_GAP_RE = re.compile(r"[\s\-]+")
# слово термина: буквы любого алфавита и цифры («Сектор-7», «X-17»), ударение внутри слова
LORE_WORD = re.compile(r"(?:[^\W_]|\u0301)+")
LORE_SKIP_BEFORE = " \t«„\"'(—–-"


def load_lore_config():
    empty = {"categories": [], "ignore": []}
    try:
        data = json.loads((C.service_path(C.LORE_FILE)).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("внутри не словарь")
    except FileNotFoundError:
        return empty
    except (OSError, ValueError) as error:
        report_problem("Файл справочника мира повреждён", error)
        return empty
    return {"categories": [c for c in data.get("categories", []) if isinstance(c, str)],
            "ignore": [w for w in data.get("ignore", []) if isinstance(w, str)]}


def save_lore_config(config):
    try:
        write_atomic(C.service_path(C.LORE_FILE), json.dumps(config, ensure_ascii=False).encode("utf-8"))
    except OSError as error:
        report_problem("Не сохранились настройки справочника мира", error)


def lore_stem(norm):
    """Основа термина без окончания: «ильвена» -> «ильвен», «околь» -> «окол»."""
    shortest = 2 if len(norm) == 3 else 3   # «ния» -> «ни», чтобы узнавались «Нии», «Нию», «Нией»
    for size in (3, 2, 1):
        if len(norm) - size >= shortest and norm[-size:] in LORE_ENDINGS:
            return norm[:-size]
    return norm


def lore_splits(norm):
    """Варианты «основа + окончание» для слова из текста."""
    for size in range(0, 4):
        if len(norm) - size < 1:
            break
        tail = norm[len(norm) - size:]
        if tail in LORE_ENDINGS:
            yield norm[:len(norm) - size], tail


def split_aliases(text):
    return [a.strip() for a in re.split(r"[,;]", text) if a.strip()]


def birth_year(text):
    """Год рождения из строки «Родился: 1203» (или «Год рождения: -40»); нет такой строки - None."""
    for line in text.replace("\r\n", "\n").split("\n"):
        found = BIRTH_RE.match(line)
        if found:
            return float(found.group(1).replace(",", "."))
    return None


def age_label(age):
    """Сколько лет герою в главе: «17 лет» или «до рождения ещё 3 года»."""
    import math
    years = math.floor(age)
    if years < 0:
        later = -years
        return f"до рождения ещё {later} {plural(later, 'год', 'года', 'лет')}"
    return f"{years} {plural(years, 'год', 'года', 'лет')}"


def lore_note(text):
    """Текст из справочника -> (короткая заметка, другие имена из строки «Также: …»)."""
    aliases, lines = [], []
    for line in text.replace("\r\n", "\n").split("\n"):
        found = LORE_ALIASES_RE.match(line)
        if found:
            aliases += split_aliases(found.group(1))
        else:
            lines.append(MARKER_RE.sub("", line).rstrip())
    note = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    if len(note) > LORE_NOTE_LIMIT:
        cut = note.rfind(" ", 0, LORE_NOTE_LIMIT)
        note = note[:cut if cut > LORE_NOTE_LIMIT // 2 else LORE_NOTE_LIMIT].rstrip(" ,;:-—") + "…"
    return note, aliases


class LoreTerm:
    """Термин мира: имя, другие имена, короткая заметка и откуда она."""

    def __init__(self, name, note="", path=None, source="", aliases=(), born=None):
        self.name = name
        self.note = note
        self.path = path
        self.source = source
        self.born = born        # год рождения из заметки или None
        self.aliases = [a for a in aliases if name_key(a) != name_key(name)]


def lore_terms_from_table(text, source, path):
    """Таблица в справочнике: каждая строка - термин, первая колонка - его имя."""
    header, rows = parse_table(text)
    terms = []
    for row in rows:
        name = row[0].strip() if row else ""
        if not name:
            continue
        aliases, lines = [], []
        for title, value in zip(header[1:], row[1:]):
            title, value = title.strip(), value.strip()
            if not value:
                continue
            if title.lower() in LORE_ALIAS_COLUMNS:
                aliases += split_aliases(value)
            else:
                lines.append(f"{title}: {value}" if title else value)
        note, _ = lore_note("\n".join(lines))
        terms.append(LoreTerm(name, note, path, source, aliases))
    return terms


def lore_tooltip(term, has_reference, age=None):
    head = f"<b>{html.escape(term.name)}</b>"
    if term.source:
        head += f"&nbsp;&nbsp;<span style='color:{C.DIM}'>{html.escape(term.source)}</span>"
    parts = [head]
    if term.note:
        parts.append("<br>".join(markup_html(line) for line in term.note.split("\n")))
    if age is not None:
        parts.append(f"<i>В этой главе: {html.escape(age_label(age))}</i>")
    if term.path is None:
        where = ("создай в справочнике файл с этим именем" if has_reference else
                 "сделай категорию справочником (правый клик по ней) и создай там файл с этим именем")
        parts.append(f"<span style='color:{C.DIM}'>Персонаж. Заметки пока нет: {where}.</span>")
    else:
        parts.append(f"<span style='color:{C.DIM}'>Ctrl+клик - открыть</span>")
    body = "<br>".join(parts)
    if len(term.note) + len(term.name) > 50 or term.path is None:
        return f"<table width='340'><tr><td>{body}</td></tr></table>"
    return body


class Lore:
    """Термины мира: где они в тексте, что о них написано и где их написали иначе."""

    def __init__(self, speller=None):
        self.speller = speller
        self.terms = []
        self.index = {}    # основа первого слова -> [(правила слов, придуманное ли слово, термин)]
        self.stems = {}    # основа любого слова термина -> (термин, нужна ли заглавная)
        self.signature = None
        self._common_cache = {}

    def _common(self, word):
        """Есть ли слово в обычном словаре (личный словарь не в счёт)."""
        speller = self.speller
        if not speller or not speller.available:
            return False
        if word not in self._common_cache:
            try:
                self._common_cache[word] = speller.common(word)
            except Exception:
                self._common_cache[word] = speller.ok(word)
        return self._common_cache[word]

    def build(self, terms):
        """Возвращает True, если что-то поменялось и текст надо перекрасить."""
        signature = tuple((t.name, t.note, str(t.path), t.source, tuple(t.aliases)) for t in terms)
        if signature == self.signature:
            return False
        self.signature = signature
        self.terms = terms
        self.index, self.stems = {}, {}
        self._candidates = {}   # слово -> термины, которые с него могут начинаться
        for term in terms:
            for phrase in [term.name] + term.aliases:
                words = LORE_WORD.findall(phrase)
                if not words:
                    continue
                single = len(words) == 1
                common = single and CYR_PART.fullmatch(words[0]) and self._common(words[0])
                rules = []
                for w in words:
                    norm = name_key(w)
                    if CYR_PART.fullmatch(w):
                        rules.append((lore_stem(norm), norm, bool(common) and w[:1].isupper()))
                    else:
                        rules.append((norm, norm, False))   # латиница и цифры: только как написано
                invented = single and not common and bool(CYR_PART.fullmatch(words[0]))
                self.index.setdefault(rules[0][0], []).append((rules, invented, term))
                for (stem_, _norm, need_cap), w in zip(rules, words):
                    if CYR_PART.fullmatch(w):
                        self.stems.setdefault(stem_, (term, need_cap))
        return True

    def _word_ok(self, surface, rule, invented, sentence_start):
        stem_, full, need_cap = rule
        norm = name_key(surface)
        if stem_ == full:
            if not (norm.startswith(stem_) and norm[len(stem_):] in LORE_ENDINGS
                    and (CYR_PART.fullmatch(surface) or norm == full)):
                return False
        elif not (norm.startswith(stem_) and len(norm) > len(stem_) and norm[len(stem_):] in LORE_ENDINGS):
            return False   # одна голая основа («Давн», «Ни») - это не форма термина
        if need_cap and not surface[:1].isupper():
            return False
        # «Давно» в начале фразы - обычное слово, а не форма «Давнь»
        if (invented and norm != full and (sentence_start or not surface[:1].isupper())
                and self._common(surface.lower())):
            return False
        return True

    def spans(self, text):
        """[(начало, конец, термин)] - где в строке встречаются термины."""
        if not self.index:
            return []
        tokens = list(LORE_WORD.finditer(text))
        found, i = [], 0
        while i < len(tokens):
            candidates = self._starting_with(name_key(tokens[i].group()))
            if not candidates:
                i += 1
                continue
            j = tokens[i].start() - 1
            while j >= 0 and text[j] in LORE_SKIP_BEFORE:
                j -= 1
            sentence_start = j < 0 or text[j] in ".!?…"
            best = None
            for rules, invented, term in candidates:
                n = len(rules)
                if i + n > len(tokens):
                    continue
                if any(not LORE_GAP_RE.fullmatch(text[tokens[j].end():tokens[j + 1].start()])
                       for j in range(i, i + n - 1)):
                    continue
                if all(self._word_ok(tokens[i + k].group(), rules[k], invented, sentence_start and k == 0)
                       for k in range(n)):
                    best = (n, term)
                    break
            if best:
                n, term = best
                found.append((tokens[i].start(), tokens[i + n - 1].end(), term))
                i += n
            else:
                i += 1
        return found

    def _starting_with(self, norm):
        cache = self.__dict__.setdefault("_candidates", {})
        found = cache.get(norm)
        if found is None:
            found = []
            for head, _tail in lore_splits(norm):
                found += self.index.get(head, [])
            found.sort(key=lambda entry: -len(entry[0]))
            cache[norm] = found
        return found

    def _is_form(self, norm):
        return any(head in self.stems for head, _tail in lore_splits(norm))

    def variants(self, texts, ignore=()):
        """Слова, очень похожие на термин, но написанные иначе: {как написано: имя термина}."""
        stems = {s: v for s, v in self.stems.items() if len(s) >= 4}
        if not stems:
            return {}
        nearby = {}
        for s in stems:
            for v in {s} | {s[:i] + s[i + 1:] for i in range(len(s))}:
                nearby.setdefault(v, set()).add(s)
        ignore = {name_key(w) for w in ignore}
        surfaces = set()
        for text in texts:
            surfaces.update(CYR_PART.findall(text))
        speller = self.speller if self.speller and self.speller.available else None
        result = {}
        for surface in sorted(surfaces):
            norm = name_key(surface)
            if len(norm) < 4 or norm in ignore or self._is_form(norm):
                continue
            best = None
            for head, _tail in lore_splits(norm):
                if len(head) < 3:
                    continue
                pool = set()
                for v in {head} | {head[:i] + head[i + 1:] for i in range(len(head))}:
                    pool |= nearby.get(v, set())
                for s in pool:
                    term, need_cap = stems[s]
                    if need_cap and not surface[:1].isupper():
                        continue
                    distance = levenshtein(head, s)
                    if 0 < distance <= (1 if len(s) < 7 else 2) and (best is None or distance < best[0]):
                        best = (distance, term)
            # настоящее слово из словаря («давно» рядом с «Давнь») - не опечатка
            if best and not (speller and speller.ok(surface)):
                result[surface] = best[1].name
        return result
