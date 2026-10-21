# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Сборка книги: EPUB по стандарту, Word с мусорными символами, PDF, сбой без порчи прежней книги."""
import unittest
import xml.etree.ElementTree as ET
import zipfile

from stungkir import export as E
from stungkir.tests.helpers import Sandbox, WindowCase, app

CHAPTERS = [("Глава 1 <туман> & «ночь»", E.book_paragraphs("Абзац с *курсивом* и **жирным**.\n— Реплика\x0b!", True)),
            ("Пустая", []), ("Глава 3", ["Последний абзац."])]
OPTIONS = {"headings": True, "new_page": True, "strip_markers": True}


class EpubTest(Sandbox):
    def test_structure(self):
        target = self.tmp / "book.epub"
        E.export_epub(target, "Туманная книга", "Мира Лосс", CHAPTERS, OPTIONS)
        with zipfile.ZipFile(target) as book:
            first = book.infolist()[0]
            self.assertEqual(first.filename, "mimetype")
            self.assertEqual(first.compress_type, zipfile.ZIP_STORED)
            self.assertEqual(book.read("mimetype"), b"application/epub+zip")
            for name in book.namelist():
                if name.endswith((".xhtml", ".opf", ".ncx", ".xml")):
                    ET.fromstring(book.read(name))          # каждый файл - правильный XML
            opf = book.read("OEBPS/content.opf").decode()
            self.assertIn("<dc:title>Туманная книга</dc:title>", opf)
            self.assertIn("<dc:creator>Мира Лосс</dc:creator>", opf)
            nav = book.read("OEBPS/nav.xhtml").decode()
            self.assertEqual(nav.count("<li>"), 3)
            chapter = book.read("OEBPS/chapter-001.xhtml").decode()
            self.assertIn("<em>курсивом</em>", chapter)
            self.assertIn("&lt;туман&gt; &amp;", chapter)
            self.assertNotIn("\x0b", chapter)


class OtherFormatsTest(Sandbox):
    def test_txt(self):
        target = self.tmp / "book.txt"
        E.export_txt(target, "Книга", "", CHAPTERS, OPTIONS)
        text = target.read_text(encoding="utf-8")
        self.assertIn("Абзац с курсивом и жирным.", text)

    def test_pdf(self):
        app()
        target = self.tmp / "book.pdf"
        E.export_pdf(target, "Книга", "Автор", CHAPTERS, OPTIONS)
        self.assertTrue(target.read_bytes().startswith(b"%PDF"))

    @unittest.skipUnless(E.docx_available(), "нет python-docx")
    def test_docx_with_control_characters(self):
        target = self.tmp / "book.docx"
        E.export_docx(target, "Книга\x0b", "Автор", CHAPTERS, OPTIONS)
        import docx
        text = "\n".join(p.text for p in docx.Document(str(target)).paragraphs)
        self.assertIn("Реплика!", text)


class CompileTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.first = self.chapter("Книга", "Глава 1", "Первая глава.")
        self.second = self.chapter("Книга", "Глава 2", "Вторая глава.")
        self.out = self.tmp / "out"
        self.out.mkdir()
        from PySide6.QtWidgets import QFileDialog
        self.patch("QFileDialog", type("FakeFiles", (), {
            "getSaveFileName": staticmethod(lambda *a, **k: (str(self.out / "Книга"), "")),
            "getOpenFileNames": QFileDialog.getOpenFileNames}))
        self.format = "epub"
        test = self

        class FakeCompile:
            def __init__(self, *a):
                pass

            def exec(self):
                return True

            def options(self):
                return {"title": "Книга", "author": "", "chapters": [test.first, test.second],
                        "format": test.format, **OPTIONS}
        self.patch("CompileDialog", FakeCompile)
        self.w = self.window()

    def test_build_epub_from_window(self):
        self.w.compile_book()
        with zipfile.ZipFile(self.out / "Книга.epub") as book:
            self.assertIn("Вторая глава.", book.read("OEBPS/chapter-002.xhtml").decode())

    def test_failed_build_keeps_previous_book(self):
        self.w.compile_book()
        before = (self.out / "Книга.epub").read_bytes()

        def broken(target, *a):
            target.write_bytes(b"half")
            raise E.ChapterError("глава «Глава 2»: сломалось")
        self.patch("export_epub", broken)
        self.w.compile_book()
        self.assertEqual((self.out / "Книга.epub").read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["Книга.epub"])
        self.assertIn("Глава 2", self.messages[-1][1])
        self.assertIn("Прежний файл книги не тронут", self.messages[-1][1])
