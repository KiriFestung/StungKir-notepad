// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.logic

import java.time.LocalDate

/**
 * Слова за день, написанные на телефоне. Вставленное (из буфера) не считается - как на компьютере.
 * Число может уходить в минус, пока правишь (вырезал абзац - потом дописал), а в файл пишется не меньше нуля.
 */
class DayCounter(private val book: Book, private val clock: () -> LocalDate = { LocalDate.now() }) {
    var day: LocalDate = clock()
        private set
    var words: Int = book.phoneStats()[day.toString()] ?: 0
        private set
    private var dirty = false

    /** Полночь прошла - сохранить старый день и начать новый. true - день сменился. */
    fun rollover(): Boolean {
        val now = clock()
        if (now == day) return false
        save()
        day = now
        words = book.phoneStats()[day.toString()] ?: 0
        return true
    }

    fun add(delta: Int) {
        if (delta == 0) return
        rollover()
        words += delta
        dirty = true
    }

    fun save() {
        if (!dirty) return
        book.savePhoneDay(day, words)
        dirty = false
    }

    /** Сегодня со всех устройств: файл телефона подменяется живым числом. */
    fun todayAll(stats: Map<String, Int>): Int {
        val key = day.toString()
        val saved = book.phoneStats()[key] ?: 0
        return maxOf(0, (stats[key] ?: 0) - saved + maxOf(0, words))
    }
}

/**
 * Отмена и повтор правок. Набор подряд склеивается в одну правку (до пробела после слова,
 * паузы или перехода в другое место), как в редакторе на компьютере.
 */
class UndoStack(private val limit: Int = 300, private val clock: () -> Long = { System.currentTimeMillis() }) {
    data class Edit(val start: Int, val removed: String, val inserted: String, var time: Long)

    private val undo = ArrayList<Edit>()
    private val redo = ArrayList<Edit>()
    private var sealed = true

    val canUndo get() = undo.isNotEmpty()
    val canRedo get() = redo.isNotEmpty()

    fun clear() {
        undo.clear()
        redo.clear()
        sealed = true
    }

    /** Следующая правка не склеится с прошлой (вставка, кнопка, перемещение курсора). */
    fun seal() {
        sealed = true
    }

    fun record(start: Int, removed: String, inserted: String) {
        if (removed == inserted) return
        redo.clear()
        val now = clock()
        val last = undo.lastOrNull()
        if (!sealed && last != null && now - last.time < 2000) {
            val lastEnd = last.start + last.inserted.length
            val wordBreak = last.inserted.isNotEmpty() && last.inserted.last().isWhitespace() &&
                inserted.isNotEmpty() && !inserted.first().isWhitespace()
            // клавиатура телефона набирает слово, заменяя его целиком: «к» -> «ко» -> «кот»
            val composing = removed.isNotEmpty() && inserted.isNotEmpty() && start + removed.length == lastEnd &&
                start >= last.start && last.inserted.endsWith(removed) && !wordBreak
            if (composing) {
                undo[undo.size - 1] = last.copy(inserted = last.inserted.dropLast(removed.length) + inserted, time = now)
                return
            }
            val typing = removed.isEmpty() && last.removed.isEmpty() && start == lastEnd && !wordBreak
            val erasing = inserted.isEmpty() && last.inserted.isEmpty() && start + removed.length == last.start
            if (typing) {
                undo[undo.size - 1] = last.copy(inserted = last.inserted + inserted, time = now)
                return
            }
            if (erasing) {
                undo[undo.size - 1] = last.copy(start = start, removed = removed + last.removed, time = now)
                return
            }
        }
        undo.add(Edit(start, removed, inserted, now))
        if (undo.size > limit) undo.removeAt(0)
        sealed = inserted.length > 1 || removed.length > 1 && inserted.isNotEmpty()
    }

    /** Правка, которую надо применить к тексту, чтобы отменить последнюю: (начало, что заменить, на что). */
    fun undo(): Edit? {
        val edit = undo.removeLastOrNull() ?: return null
        redo.add(edit)
        sealed = true
        return Edit(edit.start, edit.inserted, edit.removed, edit.time)
    }

    fun redo(): Edit? {
        val edit = redo.removeLastOrNull() ?: return null
        undo.add(edit)
        sealed = true
        return edit
    }
}

/** Применить правку к тексту (для проверок и для отмены). */
fun applyEdit(text: String, edit: UndoStack.Edit): String {
    require(text.regionMatches(edit.start, edit.removed, 0, edit.removed.length)) { "Текст не совпал с отменой" }
    return text.substring(0, edit.start) + edit.inserted + text.substring(edit.start + edit.removed.length)
}
