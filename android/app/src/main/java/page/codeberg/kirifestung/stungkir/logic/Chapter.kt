// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.logic

import java.io.File

/**
 * Открытая глава: когда сохранять, когда делать версию, что делать, если файл поменял кто-то другой
 * (Syncthing привёз правку с компьютера). Сохранение может идти в фоне, правки - в главном потоке.
 */
class ChapterSession(val book: Book, val file: File, private val now: () -> Long = { System.currentTimeMillis() }) {
    companion object {
        const val SAVE_PAUSE_MS = 1500L
        const val VERSION_EVERY_MS = 600_000L      // как на компьютере: версия не чаще раза в 10 минут
    }

    sealed class External {
        object None : External()
        data class Reload(val text: String) : External()
        object Kept : External()
    }

    @Volatile var saved: String = ""
        private set
    @Volatile private var stamp = 0L
    @Volatile private var edits = 0
    @Volatile private var savedEdits = 0
    @Volatile private var lastEdit = 0L
    private var lastVersion = 0L
    private var openVersioned = false

    val dirty get() = edits != savedEdits

    fun open(): Book.Read {
        val read = book.read(file)
        if (read is Book.Read.Text) {
            saved = read.text
            stamp = file.lastModified()
        }
        return read
    }

    fun edited() {
        edits++
        lastEdit = now()
    }

    fun edits() = edits

    fun dueSave() = dirty && now() - lastEdit >= SAVE_PAUSE_MS

    /** Записать текст. seen - номер правки, до которой текст снят: правки после него ещё не записаны. */
    @Synchronized
    fun save(text: String, seen: Int, version: Boolean = false) {
        if (!openVersioned) {
            // как было до этого раза - в версии: любую сессию на телефоне можно откатить
            book.snapshot(file, saved)
            openVersioned = true
            lastVersion = now()
        }
        if (text != saved || !file.exists()) {
            book.write(file, text)
            saved = text
            stamp = file.lastModified()
        }
        savedEdits = maxOf(savedEdits, seen)
        if (version || now() - lastVersion >= VERSION_EVERY_MS) {
            book.snapshot(file, text)
            lastVersion = now()
        }
    }

    /** Файл поменялся снаружи? Наши несохранённые правки важнее, а чужой текст уходит в версии. */
    @Synchronized
    fun checkExternal(current: String): External {
        val modified = file.lastModified()
        if (modified == 0L || modified == stamp) return External.None
        val read = try {
            book.read(file)
        } catch (e: java.io.IOException) {
            return External.None
        }
        stamp = modified
        if (read !is Book.Read.Text || read.text == saved) return External.None
        if (!dirty && current == saved) {
            book.snapshot(file, saved)
            saved = read.text
            return External.Reload(read.text)
        }
        book.snapshot(file, read.text)
        edits++                      // наш текст надо записать поверх
        lastEdit = 0
        return External.Kept
    }
}
