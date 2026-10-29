package page.codeberg.kirifestung.stungkir

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import page.codeberg.kirifestung.stungkir.logic.Book
import page.codeberg.kirifestung.stungkir.logic.Json
import java.io.File
import java.nio.file.Files
import java.time.LocalDate
import java.time.LocalDateTime

class BookTest {
    private fun book(): Book = Book(Files.createTempDirectory("stungkir").toFile())

    @Test fun namesDifferingOnlyInCaseClash() {
        val b = book()
        val cat = b.createCategory("Книга")
        b.createChapter(cat, "Глава")
        val chapter = runCatching { b.createChapter(cat, "глава") }
        assertTrue(chapter.isFailure)                 // на телефоне и Windows это тот же файл
        assertTrue(runCatching { b.createCategory("КНИГА") }.isFailure)
        assertEquals("Другая.txt", b.createChapter(cat, "Другая").name)
    }

    @Test fun keepsDesktopOrder() {
        val b = book()
        for (name in listOf("Аа", "Бб", "Вв")) File(b.root, name).mkdirs()
        File(b.root, ".stungkir").mkdirs()
        File(b.root, ".order").writeText(Json.ofList(listOf("Вв", "Аа")))
        assertEquals(listOf("Вв", "Аа", "Бб"), b.categories().map { it.name })
        val c = b.createCategory("Гг")
        assertEquals("Гг", b.categories().last().name)
        val ch = b.createChapter(c, "Глава 1")
        assertEquals("Глава 1.txt", ch.name)
        assertEquals("Глава 2", b.nextChapterName(c))
        assertEquals(listOf("Глава 1.txt"), Json.stringList(File(c, ".order").readText()))
    }

    @Test fun readsOldEncodingAndLocked() {
        val b = book()
        val f = File(b.root, "a.txt")
        f.writeBytes("Привет\r\nмир".toByteArray(charset("windows-1251")))
        assertEquals(Book.Read.Text("Привет\nмир"), b.read(f))
        f.writeBytes(byteArrayOf(0xEF.toByte(), 0xBB.toByte(), 0xBF.toByte()) + "Тест".toByteArray())
        assertEquals(Book.Read.Text("Тест"), b.read(f))
        f.writeBytes(Book.MAGIC + "gAAAA".toByteArray())
        assertEquals(Book.Read.Locked, b.read(f))
    }

    @Test fun versionsLikeDesktop() {
        val b = book()
        val cat = b.createCategory("Книга")
        val ch = b.createChapter(cat, "Глава 1")
        val t = LocalDateTime.of(2026, 10, 21, 12, 0, 0)
        assertTrue(b.snapshot(ch, "один", t))
        assertFalse(b.snapshot(ch, "один", t.plusSeconds(1)))
        assertTrue(b.snapshot(ch, "два", t.plusSeconds(2)))
        val v = b.versions(ch)
        assertEquals(2, v.size)
        assertEquals("2026-10-21_12-00-02_000000.txt", v[0].name)
        assertEquals(File(b.root, ".stungkir/versions/Книга/Глава 1.txt"), v[0].parentFile)
        assertEquals("21.10.2026   12:00:02", b.versionLabel(v[0]))
        for (i in 0 until 60) b.snapshot(ch, "текст $i", t.plusMinutes(i.toLong() + 1))
        assertEquals(Book.MAX_VERSIONS, b.versions(ch).size)
    }

    @Test fun phoneStatsAddToDesktop() {
        val b = book()
        File(b.root, ".stungkir").mkdirs()
        File(b.root, ".stungkir/stats.json").writeText("{\"2026-10-20\": 200, \"2026-10-19\": 300}")
        b.savePhoneDay(LocalDate.of(2026, 10, 20), 100)
        val all = b.allStats()
        assertEquals(300, all["2026-10-20"])
        assertEquals(300, all["2026-10-19"])
        assertEquals(mapOf("2026-10-20" to 100), b.phoneStats())
        // сегодня ещё не дописано - серия держится на вчерашних днях
        assertEquals(2, b.streak(all, LocalDate.of(2026, 10, 21), emptySet()))
        assertEquals(3, b.streak(all, LocalDate.of(2026, 10, 21), setOf("2026-10-18")))
    }

    @Test fun atomicWriteLeavesNoTemp() {
        val b = book()
        val f = File(b.root, "x.txt")
        b.write(f, "абв")
        assertEquals("абв", f.readText())
        assertEquals(listOf("x.txt"), b.root.list()!!.toList())
    }
}

class ConflictTest {
    @Test fun recognisesConflicts() {
        assertEquals("Глава 1.txt", Book.conflictOriginal("Глава 1.sync-conflict-20261021-120000-ABCDEF7.txt"))
        assertEquals("Глава 1.txt", Book.conflictOriginal("Глава 1 (Kira's conflicted copy 2026-10-21).txt"))
        assertEquals(null, Book.conflictOriginal("Глава 1.txt"))
        assertEquals(Book.Kind.CONFLICT, Book.kind(File("Глава 1.sync-conflict-20261021-120000-ABCDEF7.txt")))
        assertEquals(Book.Kind.DESKTOP_ONLY, Book.kind(File("План.board")))
        assertEquals(Book.Kind.OTHER, Book.kind(File("карта.png")))
    }

    @Test fun keepAndDropConflicts() {
        val b = Book(Files.createTempDirectory("stungkir").toFile())
        val cat = b.createCategory("Книга")
        val ch = b.createChapter(cat, "Глава 1")
        b.write(ch, "с компьютера")
        val conflict = File(cat, "Глава 1.sync-conflict-20261021-120000-ABCDEF7.txt")
        b.write(conflict, "с телефона")
        assertEquals(ch, b.keepConflict(conflict))
        assertEquals("с телефона", ch.readText())
        assertFalse(conflict.exists())
        assertTrue(b.versions(ch).any { it.readText() == "с компьютера" })
        b.write(conflict, "лишнее")
        b.dropConflict(conflict)
        assertFalse(conflict.exists())
        assertEquals("с телефона", ch.readText())
        assertTrue(b.versions(ch).any { it.readText() == "лишнее" })
    }

    @Test fun chapterGoesToTrashLikeOnDesktop() {
        val b = book()
        val cat = b.createCategory("Тервена")
        val ch = b.createChapter(cat, "Глава 1")
        ch.writeText("Кев ушёл.")
        val entry = b.moveToTrash(ch, LocalDateTime.of(2026, 10, 29, 9, 5, 0))
        assertFalse(ch.exists())
        assertEquals(File(b.root, ".stungkir/trash"), entry.parentFile)
        assertTrue(entry.name.matches(Regex("20261029-090500-[0-9a-f]{6}")))
        assertEquals("Кев ушёл.", File(entry, "Глава 1.txt").readText())
        val meta = Json.parse(File(entry, "meta.json").readText()) as Map<*, *>
        assertEquals("Тервена/Глава 1.txt", meta["from"])
        assertEquals("2026-10-29T09:05:00", meta["when"])                  // секунды всегда, как у компьютера
        assertEquals("file", meta["kind"])
    }
}
