// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import page.codeberg.kirifestung.stungkir.logic.Book
import page.codeberg.kirifestung.stungkir.logic.DayCounter
import java.io.File
import java.time.LocalDate

sealed interface Screen {
    object Library : Screen
    data class Category(val folder: File) : Screen
    data class Editor(val file: File) : Screen
    data class Versions(val file: File) : Screen
    data class Conflict(val file: File) : Screen
    object Stats : Screen
    object Settings : Screen
    object Folder : Screen
}

/** Всё, что живёт, пока открыто приложение: папка, экраны, тема, счётчик слов за день. */
class AppState(val prefs: Prefs) {
    var palette by mutableStateOf(Themes.byName(prefs.theme))
    var book by mutableStateOf<Book?>(null)
        private set
    var counter: DayCounter? = null
        private set
    val stack = mutableStateListOf<Screen>(Screen.Library)

    /** Растёт, когда что-то поменялось на диске или в настройках - экраны перечитывают. */
    var version by mutableIntStateOf(0)
    var stats by mutableStateOf<Map<String, Int>>(emptyMap())
        private set
    var typedToday by mutableIntStateOf(0)
        private set

    /** Что сделать, когда приложение уходит в фон (сохранить главу). */
    val pauseHooks = LinkedHashMap<Any, () -> Unit>()

    init {
        prefs.folder?.let { path -> File(path).takeIf { it.isDirectory }?.let { useFolder(it) } }
    }

    /** Доступ к файлам дали только что - папка из настроек теперь читается. */
    fun restore() {
        if (book != null) return
        prefs.folder?.let { path -> File(path).takeIf { it.isDirectory }?.let { useFolder(it) } }
    }

    fun useFolder(folder: File) {
        counter?.save()
        val b = Book(folder)
        book = b
        counter = DayCounter(b)
        prefs.folder = folder.absolutePath
        stack.clear()
        stack.add(Screen.Library)
        reloadStats()
    }

    fun reloadStats() {
        val b = book ?: return
        stats = try {
            b.allStats()
        } catch (e: Exception) {
            emptyMap()
        }
        typedToday = counter?.let { it.todayAll(stats) } ?: 0
        version++
    }

    fun typed(words: Int) {
        val c = counter ?: return
        val dayChanged = c.rollover()
        c.add(words)
        if (dayChanged) reloadStats() else typedToday = c.todayAll(stats)
    }

    /** Статистика вместе с живым числом сегодняшнего дня. */
    fun liveStats(): Map<String, Int> {
        val c = counter ?: return stats
        return stats + (c.day.toString() to c.todayAll(stats))
    }

    fun streak(): Int = book?.let { b ->
        try {
            b.streak(liveStats(), LocalDate.now())
        } catch (e: Exception) {
            0
        }
    } ?: 0

    val screen: Screen get() = stack.last()

    fun open(screen: Screen) {
        stack.add(screen)
    }

    /** Назад; false - уже на первом экране. */
    fun back(): Boolean {
        if (stack.size <= 1) return false
        stack.removeAt(stack.size - 1)
        return true
    }

    fun pause() {
        for (hook in pauseHooks.values.toList()) hook()
        counter?.save()
    }
}
