# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Большие главы: каждый абзац красится один раз, смена темы не пересчитывает разметку,
экран остаётся на месте, а ускорения не меняют того, что подсвечивается."""
import random
import unittest

from stungkir.core import config as C
from stungkir.tests.helpers import WindowCase, wait
from stungkir.core.textutil import Crutches, WORD_RE, _crutch_word_ok, name_key, crutch_base, CRUTCH_GAP


def big_text(paragraphs=600):
    random.seed(7)
    words = "туман река берег лодка утро вечер дорога ветер окно дверь огонь камень".split()
    lines = []
    for i in range(paragraphs):
        body = " ".join(random.choice(words) for _ in range(14)).capitalize() + "."
        lines.append(("— " + body + " — сказала Кира.") if i % 4 == 0 else body)
    return "\n".join(lines)


def backgrounds(block):
    return {f.format.background().color().name() for f in block.layout().formats()
            if f.format.background().style()}


class BigChapterTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.path = self.chapter("Книга", "Большая", big_text())
        self.w = self.window()
        self.calls = []
        original = self.w.highlighter._compute_ops
        self.w.highlighter._compute_ops = lambda text: (self.calls.append(text), original(text))[1]

    def test_open_highlights_every_paragraph_once(self):
        self.w.open_path(self.path)
        doc = self.w.editor.document()
        self.assertEqual(len(self.calls), doc.blockCount())          # не дважды, как было
        last = doc.lastBlock()
        self.assertIn(C.REPEAT_BG, backgrounds(doc.firstBlock()) | backgrounds(last))
        self.assertFalse(doc.pageSize().isNull())                    # вёрстка включена обратно
        self.assertFalse(doc.isModified())

    def test_theme_change_reuses_marks_and_keeps_place(self):
        self.w.open_path(self.path)
        doc = self.w.editor.document()
        cursor = self.w.editor.textCursor()
        cursor.setPosition(doc.characterCount() // 2)
        self.w.editor.setTextCursor(cursor)
        self.w.editor.ensureCursorVisible()
        wait(0.1)
        place = self.w.editor.verticalScrollBar().value()
        self.assertGreater(place, 0)
        self.calls.clear()
        theme = "Сирень" if C.palette() != C.THEMES["Сирень"] else "Сепия"
        self.w.apply_palette(C.THEMES[theme])
        wait(0.1)
        self.assertEqual(self.calls, [])                              # цвета новые, разметка та же
        self.assertEqual(self.w.editor.verticalScrollBar().value(), place)
        repeat = C.THEMES[theme]["REPEAT_BG"]
        self.assertTrue(any(repeat in backgrounds(b) for b in (doc.findBlockByNumber(n) for n in range(0, 600, 50))))

    def test_marks_recount_when_names_or_crutches_change(self):
        self.w.open_path(self.path)
        self.calls.clear()
        self.w.highlighter.crutches = Crutches(["туман"])
        self.w._rehighlight()
        self.assertEqual(len(self.calls), self.w.editor.document().blockCount())
        self.assertTrue(any(C.CRUTCH_BG in backgrounds(b) for b in (self.w.editor.document().findBlockByNumber(n)
                                                                     for n in range(0, 600, 25))))

    def test_typing_still_highlights_new_text(self):
        self.w.open_path(self.path)
        cursor = self.w.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.w.editor.setTextCursor(cursor)
        self.w.editor.insertPlainText("\nОкно и окно")
        wait(0.05)
        self.assertIn(C.REPEAT_BG, backgrounds(self.w.editor.document().lastBlock()))


class CrutchIndexTest(unittest.TestCase):
    def brute(self, entries, line):
        """Прежний поиск: каждый штамп с каждого слова."""
        items = [(e.strip(), [(name_key(w), crutch_base(w)) for w in WORD_RE.findall(e)]) for e in entries]
        tokens = list(WORD_RE.finditer(line))
        found = []
        for i in range(len(tokens)):
            for entry, words in items:
                if i + len(words) > len(tokens):
                    continue
                if all(_crutch_word_ok(tokens[i + k].group(), *words[k]) and
                       (not k or CRUTCH_GAP.fullmatch(line[tokens[i + k - 1].end():tokens[i + k].start()]))
                       for k in range(len(words))):
                    found.append((tokens[i].start(), tokens[i + len(words) - 1].end(), entry))
        found.sort(key=lambda s: (s[0], -(s[1] - s[0])))
        result, last = [], -1
        for start, end, entry in found:
            if start >= last:
                result.append((start, end, entry))
                last = end
        return result

    def test_index_finds_the_same(self):
        entries = ["вдруг", "вздохнул", "почувствовал, как", "и", "он", "Ёжик", "кивнул головой"]
        lines = ["Вдруг он вздохнула и почувствовала, как ёжик кивнули головой.",
                 "Он вздохнули. И вдруг — почувствовал как. Ежики", "", "вздохнувший кивнул  головой"]
        crutches = Crutches(entries)
        for line in lines:
            self.assertEqual(crutches.spans(line), self.brute(entries, line), line)
