package page.codeberg.kirifestung.stungkir

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import page.codeberg.kirifestung.stungkir.logic.Book
import page.codeberg.kirifestung.stungkir.logic.DayCounter
import page.codeberg.kirifestung.stungkir.logic.UndoStack
import page.codeberg.kirifestung.stungkir.logic.applyEdit
import java.io.File
import java.nio.file.Files
import java.time.LocalDate

class SessionTest {
    @Test fun dayCounterSavesAndRolls() {
        val book = Book(Files.createTempDirectory("stungkir").toFile())
        var today = LocalDate.of(2026, 10, 21)
        val counter = DayCounter(book) { today }
        counter.add(120)
        counter.add(-20)
        counter.save()
        assertEquals(mapOf("2026-10-21" to 100), book.phoneStats())
        File(book.root, ".stungkir/stats.json").writeText("{\"2026-10-21\": 400}")
        counter.add(5)
        assertEquals(505, counter.todayAll(book.allStats()))
        today = today.plusDays(1)
        counter.add(7)
        assertEquals(105, book.phoneStats()["2026-10-21"])
        assertEquals(7, counter.words)
        counter.add(-50)
        counter.save()
        assertEquals(0, book.phoneStats()["2026-10-22"])
        // новый запуск продолжает с сохранённого
        assertEquals(105, DayCounter(book) { LocalDate.of(2026, 10, 21) }.words)
    }

    @Test fun undoMergesTyping() {
        var now = 0L
        val stack = UndoStack(clock = { now })
        var text = ""
        fun type(at: Int, s: String) {
            stack.record(at, "", s)
            text = text.substring(0, at) + s + text.substring(at)
            now += 100
        }
        stack.seal()
        "Кот спит".forEachIndexed { i, c -> type(i, c.toString()) }
        assertEquals("Кот спит", text)
        var e = stack.undo()!!
        text = applyEdit(text, e)
        assertEquals("Кот ", text)
        e = stack.undo()!!
        text = applyEdit(text, e)
        assertEquals("", text)
        assertFalse(stack.canUndo)
        text = applyEdit(text, stack.redo()!!)
        text = applyEdit(text, stack.redo()!!)
        assertEquals("Кот спит", text)
        // пауза - новая правка
        now += 5000
        type(8, ".")
        text = applyEdit(text, stack.undo()!!)
        assertEquals("Кот спит", text)
        assertTrue(stack.canRedo)
        // стирание назад склеивается
        stack.seal()
        for (i in 7 downTo 4) {
            stack.record(i, text.substring(i, i + 1), "")
            text = text.removeRange(i, i + 1)
            now += 100
        }
        assertEquals("Кот ", text)
        assertFalse(stack.canRedo)
        text = applyEdit(text, stack.undo()!!)
        assertEquals("Кот спит", text)
    }

    @Test fun undoMergesKeyboardComposing() {
        var now = 0L
        val stack = UndoStack(clock = { now })
        var text = "Начало "
        fun edit(at: Int, removed: String, inserted: String) {
            stack.record(at, removed, inserted)
            text = text.substring(0, at) + inserted + text.substring(at + removed.length)
            now += 80
        }
        stack.seal()
        edit(7, "", "к")
        edit(7, "к", "ко")
        edit(7, "ко", "кот")
        edit(10, "", " ")
        edit(11, "", "с")
        edit(11, "с", "сп")
        assertEquals("Начало кот сп", text)
        text = applyEdit(text, stack.undo()!!)
        assertEquals("Начало кот ", text)
        text = applyEdit(text, stack.undo()!!)
        assertEquals("Начало ", text)
    }
}
