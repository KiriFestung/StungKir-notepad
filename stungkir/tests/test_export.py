# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Сборка книги: EPUB по стандарту, Word с мусорными символами, PDF, сбой без порчи прежней книги."""
import unittest
import xml.etree.ElementTree as ET
import zipfile

from stungkir import config as C
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


class PicturesTest(WindowCase):
    """Картинка в тексте: «[картинка: файл]» - в книге картинка, без файла - строки нет, пометкой не считается."""

    def _picture(self, folder, name="карта.png"):
        from PySide6.QtGui import QColor, QImage
        image = QImage(300, 200, QImage.Format_RGB32)
        image.fill(QColor("#2a2696"))
        folder.mkdir(parents=True, exist_ok=True)
        image.save(str(folder / name))
        return folder / name

    def test_paragraphs_and_all_formats(self):
        app()
        folder = C.ROOT / "Книга"
        self._picture(folder / "картинки")
        text = "До.\n[картинка: карта.png]\n[картинка: нет-такой.png]\n[пометка]\nПосле."
        self.assertEqual(E.marker_lines(text), ["[пометка]"])           # картинка - не пометка
        paragraphs = E.book_paragraphs(text, True, folder=folder)
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(E.image_of(paragraphs[1]), folder / "картинки" / "карта.png")
        self.assertEqual(E.book_paragraphs(text, True), ["До.", "После."])   # без папки - просто без картинки
        chapters = [("Глава", paragraphs)]
        E.export_epub(self.tmp / "b.epub", "Книга", "Кира", chapters, OPTIONS)
        with zipfile.ZipFile(self.tmp / "b.epub") as book:
            self.assertIn("OEBPS/img-001.png", book.namelist())
            self.assertIn('media-type="image/png"', book.read("OEBPS/content.opf").decode())
            self.assertIn('<img src="img-001.png"', book.read("OEBPS/chapter-001.xhtml").decode())
            for name in book.namelist():
                if name.endswith((".xhtml", ".opf")):
                    ET.fromstring(book.read(name))
        E.export_fb2(self.tmp / "b.fb2", "Книга", "Кира", chapters, OPTIONS)
        fb2 = (self.tmp / "b.fb2").read_text(encoding="utf-8")
        ET.fromstring(fb2)
        self.assertIn('<image l:href="#img1.png"/>', fb2)
        self.assertIn('<binary id="img1.png"', fb2)
        E.export_txt(self.tmp / "b.txt", "Книга", "", chapters, OPTIONS)
        self.assertNotIn("img", (self.tmp / "b.txt").read_text(encoding="utf-8"))
        E.export_pdf(self.tmp / "b.pdf", "Книга", "Кира", chapters, OPTIONS)
        self.assertGreater((self.tmp / "b.pdf").stat().st_size, 2000)
        if E.docx_available():
            E.export_docx(self.tmp / "b.docx", "Книга", "Кира", chapters, OPTIONS)
            with zipfile.ZipFile(self.tmp / "b.docx") as doc:
                self.assertTrue(any(n.startswith("word/media/") for n in doc.namelist()))

    def test_insert_from_window_and_preview(self):
        from stungkir import dialogs
        w = self.window()
        path = self.chapter("Книга", "Глава", "Первый абзац.")
        w.open_path(path)
        outside = self._picture(self.tmp / "где-то", "рисунок.png")
        cursor = w.editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        w.editor.setTextCursor(cursor)
        self.assertEqual(w.insert_picture(outside), "рисунок.png")
        self.assertTrue((path.parent / "картинки" / "рисунок.png").exists())     # скопирована к главе
        self.assertIn("\n[картинка: рисунок.png]", w.editor.toPlainText())
        self.assertIsNone(w.insert_picture(self.tmp / "нет.txt"))
        self.addCleanup(setattr, dialogs.Sheet, "exec", dialogs.Sheet.exec)
        dialogs.Sheet.exec = lambda dialog: 0
        dialog = w.show_preview()
        self.assertIn("<img", dialog.pages["book"].document.toHtml())
        dialog.view.grab()


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
