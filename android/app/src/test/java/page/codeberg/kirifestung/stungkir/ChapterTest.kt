package page.codeberg.kirifestung.stungkir

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import page.codeberg.kirifestung.stungkir.logic.Book
import page.codeberg.kirifestung.stungkir.logic.ChapterSession
import java.nio.file.Files

class ChapterTest {
    @Test fun savesKeepsVersionsAndReloads() {
        val book = Book(Files.createTempDirectory("stungkir").toFile())
        val cat = book.createCategory("Книга")
        val file = book.createChapter(cat, "Глава 1")
        book.write(file, "было")
        var now = 1_000_000L
        val s = ChapterSession(book, file) { now }
        assertEquals(Book.Read.Text("было"), s.open())
        s.edited()
        assertFalse(s.dueSave())
        now += 2000
        assertTrue(s.dueSave())
        s.save("стало", s.edits())
        assertFalse(s.dirty)
        assertEquals("стало", file.readText())
        assertEquals(listOf("было"), book.versions(file).map { it.readText() })

        // правка во время сохранения не теряется
        s.edited()
        val seen = s.edits()
        s.edited()
        s.save("стало ещё", seen)
        assertTrue(s.dirty)
        s.save("стало ещё и ещё", s.edits())

        // Syncthing привёз текст с компьютера, на телефоне правок нет - показать его
        file.writeText("с компьютера")
        file.setLastModified(file.lastModified() + 5000)
        val r = s.checkExternal("стало ещё и ещё")
        assertEquals(ChapterSession.External.Reload("с компьютера"), r)
        assertEquals(ChapterSession.External.None, s.checkExternal("с компьютера"))

        // оба правили: наш остаётся, чужой - в версиях
        s.edited()
        file.writeText("опять с компьютера")
        file.setLastModified(file.lastModified() + 10000)
        assertEquals(ChapterSession.External.Kept, s.checkExternal("наш"))
        assertTrue(book.versions(file).any { it.readText() == "опять с компьютера" })
        assertTrue(s.dirty)
        s.save("наш", s.edits())
        assertEquals("наш", file.readText())

        now += ChapterSession.VERSION_EVERY_MS
        s.edited()
        s.save("через десять минут", s.edits())
        assertEquals("через десять минут", book.versions(file).first().readText())
    }
}
