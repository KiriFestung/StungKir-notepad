// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.logic

import java.io.File
import java.nio.ByteBuffer
import java.nio.charset.CharacterCodingException
import java.nio.charset.Charset
import java.nio.charset.CodingErrorAction
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

/**
 * Папка с текстами - та же, что у блокнота на компьютере (её возит Syncthing).
 * Раскладка совпадает до файла: категории - папки, главы - .txt, порядок - .order,
 * служебное - в .stungkir (версии, персонажи, статистика). Телефон пишет свою статистику
 * в .stungkir/stats-phone.json, чтобы синхронизация не затирала числа компьютера.
 */
class Book(val root: File) {
    val service = File(root, ".stungkir")

    enum class Kind { CHAPTER, CONFLICT, DESKTOP_ONLY, OTHER }

    companion object {
        const val ORDER_FILE = ".order"
        const val MAX_VERSIONS = 50
        val MAGIC: ByteArray = "STUNGKIR-ENC1\n".toByteArray()
        val VERSION_STAMP: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd_HH-mm-ss_SSSSSS")
        private val CHAPTER_SUFFIXES = setOf("txt", "md", "text", "")
        private val DESKTOP_SUFFIXES = setOf("csv", "board", "timeline")
        private val CONFLICT_PATTERNS = listOf(
            Regex("^(.+?)\\.sync-conflict-\\d{8}-\\d{6}-[A-Za-z0-9]+(\\.[^.]+)?$"),               // Syncthing
            Regex("^(.+?) \\((?:[^()]*'s )?conflicted copy[^()]*\\)(\\.[^.]+)?$", RegexOption.IGNORE_CASE),
            Regex("^(.+?) \\([^()]*конфликт[^()]*\\)(\\.[^.]+)?$", RegexOption.IGNORE_CASE),
            Regex("^(.+?)_conf\\(\\d+\\)(\\.[^.]+)?$"),
        )

        /** Для копии-конфликта от синхронизации - имя главы, с которой она разошлась; иначе null. */
        fun conflictOriginal(name: String): String? {
            for (pattern in CONFLICT_PATTERNS) {
                val m = pattern.matchEntire(name) ?: continue
                return m.groupValues[1] + m.groupValues[2]
            }
            return null
        }

        fun kind(file: File): Kind {
            val ext = file.extension.lowercase()
            return when {
                conflictOriginal(file.name) != null && ext in CHAPTER_SUFFIXES -> Kind.CONFLICT
                ext in CHAPTER_SUFFIXES -> Kind.CHAPTER
                ext in DESKTOP_SUFFIXES -> Kind.DESKTOP_ONLY
                else -> Kind.OTHER
            }
        }
    }

    // ---------------- категории и главы ----------------
    fun categories(): List<File> =
        ordered(root.listFiles()?.filter { it.isDirectory && !it.name.startsWith(".") } ?: emptyList(), root)

    fun files(category: File): List<File> =
        ordered(category.listFiles()?.filter { it.isFile && !it.name.startsWith(".") } ?: emptyList(), category)

    fun loadOrder(folder: File): List<String> = try {
        Json.stringList(File(folder, ORDER_FILE).readText())
    } catch (e: java.io.IOException) {
        emptyList()
    }

    fun ordered(items: List<File>, folder: File): List<File> {
        val rank = loadOrder(folder).withIndex().associate { it.value to it.index }
        return items.sortedWith(compareBy<File>({ rank[it.name] ?: rank.size }, { it.name.lowercase() }))
    }

    /** Новое - в конец того порядка, что сейчас на экране (как на компьютере). */
    fun appendToOrder(folder: File, name: String) {
        val shown = ordered(folder.listFiles()?.filter { !it.name.startsWith(".") && it.name != name } ?: emptyList(), folder)
        writeAtomic(File(folder, ORDER_FILE), Json.ofList(shown.map { it.name } + name).toByteArray())
    }

    /** Есть ли рядом то же имя в другом регистре («Глава» и «глава»): на Windows и телефоне это один файл. */
    private fun clash(file: File): Boolean =
        file.exists() || (file.parentFile?.listFiles()?.any { it.name.equals(file.name, ignoreCase = true) } ?: false)

    fun createCategory(name: String): File {
        val folder = File(root, name.trim())
        require(!clash(folder)) { "Такая категория уже есть" }
        if (!folder.mkdirs()) throw java.io.IOException("Не получилось создать папку")
        appendToOrder(root, folder.name)
        return folder
    }

    fun createChapter(category: File, name: String): File {
        val clean = name.trim()
        val file = File(category, if (clean.endsWith(".txt") || clean.endsWith(".md")) clean else "$clean.txt")
        require(!clash(file)) { "Такая глава уже есть" }
        writeAtomic(file, ByteArray(0))
        appendToOrder(category, file.name)
        return file
    }

    fun nextChapterName(category: File): String =
        TextRules.nextChapterName(category.listFiles()?.map { it.nameWithoutExtension } ?: emptyList())

    /** Оставить копию-конфликт: её текст становится главой, прежний текст главы уходит в версии. */
    fun keepConflict(conflict: File): File {
        val original = File(conflict.parentFile, conflictOriginal(conflict.name) ?: return conflict)
        if (original.exists()) {
            val old = read(original)
            if (old is Read.Text) snapshot(original, old.text)
        }
        val chosen = read(conflict)
        require(chosen is Read.Text) { "Копия зашифрована - разбери её на компьютере" }
        snapshot(original, chosen.text)
        write(original, chosen.text)
        conflict.delete()
        return original
    }

    /** Выбросить копию-конфликт, текст при этом остаётся в версиях главы. */
    fun dropConflict(conflict: File) {
        val original = File(conflict.parentFile, conflictOriginal(conflict.name) ?: return)
        val text = read(conflict)
        if (text is Read.Text) snapshot(original, text.text)
        conflict.delete()
    }

    /**
     * Глава - в корзину, так же, как на компьютере: .stungkir/trash/<время>-<случайное>/глава.txt и meta.json
     * (откуда и когда). Синхронизация привезёт её на компьютер - там она 30 дней лежит в «Корзине»
     * и возвращается одной кнопкой. Версии главы остаются: вернулась глава - вернулась и история.
     */
    fun moveToTrash(file: File, now: LocalDateTime = LocalDateTime.now()): File {
        val stamp = now.format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"))
        val tail = (1..6).map { "0123456789abcdef"[kotlin.random.Random.nextInt(16)] }.joinToString("")
        val entry = File(File(service, "trash"), "$stamp-$tail")
        if (!entry.mkdirs()) throw java.io.IOException("Не получилось создать папку в корзине")
        val from = file.relativeTo(root).invariantSeparatorsPath
        val whenText = now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss"))
        File(entry, "meta.json").writeText(
            "{\"from\": ${Json.quote(from)}, \"when\": \"$whenText\", \"kind\": \"file\"}", Charsets.UTF_8,
        )
        if (!file.renameTo(File(entry, file.name))) {
            entry.deleteRecursively()
            throw java.io.IOException("Не получилось перенести главу в корзину")
        }
        return entry
    }

    // ---------------- чтение и запись ----------------
    sealed class Read {
        data class Text(val text: String) : Read()
        object Locked : Read()
    }

    fun read(file: File): Read {
        val bytes = file.readBytes()
        if (bytes.size >= MAGIC.size && bytes.copyOfRange(0, MAGIC.size).contentEquals(MAGIC)) return Read.Locked
        return Read.Text(decode(bytes))
    }

    /** UTF-8 (с BOM или без); не вышло - старая кодировка Windows (cp1251), как на компьютере. */
    fun decode(bytes: ByteArray): String {
        val data = if (bytes.size >= 3 && bytes[0] == 0xEF.toByte() && bytes[1] == 0xBB.toByte() && bytes[2] == 0xBF.toByte())
            bytes.copyOfRange(3, bytes.size) else bytes
        val text = try {
            Charsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(data)).toString()
        } catch (e: CharacterCodingException) {
            String(data, Charset.forName("windows-1251"))
        }
        return text.replace("\r\n", "\n").replace('\r', '\n')
    }

    /** Сначала во временный файл рядом, потом подмена: оборвалось - остался прежний файл, а не пустой. */
    fun writeAtomic(file: File, data: ByteArray) {
        file.parentFile?.mkdirs()
        val temp = File(file.parentFile, ".${file.name}.tmp")
        temp.outputStream().use { stream ->
            stream.write(data)
            stream.fd.sync()
        }
        if (!temp.renameTo(file)) {
            temp.delete()
            throw java.io.IOException("Не получилось записать ${file.name}")
        }
    }

    fun write(file: File, text: String) = writeAtomic(file, text.toByteArray(Charsets.UTF_8))

    // ---------------- версии (как «Версии файла» на компьютере) ----------------
    fun versionsDir(file: File): File {
        val relative = file.relativeToOrNull(root)?.path ?: "${file.parentFile?.name}/${file.name}"
        return File(File(service, "versions"), relative)
    }

    fun versions(file: File): List<File> =
        versionsDir(file).listFiles()?.filter { it.isFile && it.name.endsWith(".txt") }?.sortedByDescending { it.name } ?: emptyList()

    /** Копия текста в версии - если он отличается от последней. Старше 50-й - прочь. */
    fun snapshot(file: File, text: String, now: LocalDateTime = LocalDateTime.now()): Boolean {
        val folder = versionsDir(file)
        val existing = versions(file)
        val latest = existing.firstOrNull()
        if (latest != null) {
            val previous = read(latest)
            if (previous is Read.Text && previous.text == text) return false
        }
        var target = File(folder, now.format(VERSION_STAMP) + ".txt")
        var n = 2
        while (target.exists()) target = File(folder, now.format(VERSION_STAMP) + " ($n).txt").also { n++ }
        write(target, text)
        versions(file).drop(MAX_VERSIONS).forEach { it.delete() }
        return true
    }

    fun versionLabel(version: File): String = try {
        val stamp = LocalDateTime.parse(version.nameWithoutExtension.take(26), VERSION_STAMP)
        stamp.format(DateTimeFormatter.ofPattern("dd.MM.yyyy   HH:mm:ss"))
    } catch (e: Exception) {
        version.nameWithoutExtension
    }

    // ---------------- персонажи и статистика ----------------
    fun names(): List<String> = try {
        Json.stringList(File(service, "names.json").readText())
    } catch (e: java.io.IOException) {
        emptyList()
    }

    private fun readMap(file: File): Map<String, Int> = try {
        Json.intMap(file.readText())
    } catch (e: java.io.IOException) {
        emptyMap()
    }

    val phoneStatsFile get() = File(service, "stats-phone.json")

    fun phoneStats(): Map<String, Int> = readMap(phoneStatsFile)

    fun savePhoneDay(day: LocalDate, words: Int) {
        val stats = phoneStats().toMutableMap()
        stats[day.toString()] = maxOf(0, words)
        writeAtomic(phoneStatsFile, Json.ofIntMap(stats).toByteArray())
    }

    /** Слова по дням со всех устройств: компьютер (stats.json) и телефоны (stats-*.json). */
    fun allStats(): Map<String, Int> {
        val total = HashMap(readMap(File(service, "stats.json")))
        service.listFiles()?.filter { it.name.startsWith("stats-") && it.name.endsWith(".json") }?.forEach { file ->
            for ((day, words) in readMap(file)) total[day] = (total[day] ?: 0) + maxOf(0, words)
        }
        return total
    }

    fun markedDays(): Set<String> = try {
        Json.stringList(File(service, "days.json").readText()).toSet()
    } catch (e: java.io.IOException) {
        emptySet()
    }

    /** Дней подряд: день засчитан от 250 слов или отмечен вручную. Сегодня ещё не засчитано - серия не рвётся. */
    fun streak(stats: Map<String, Int>, today: LocalDate, marks: Set<String> = markedDays()): Int {
        fun wrote(day: LocalDate) = day.toString() in marks || (stats[day.toString()] ?: 0) >= TextRules.STREAK_WORDS
        var day = if (wrote(today)) today else today.minusDays(1)
        var count = 0
        while (wrote(day)) {
            count++
            day = day.minusDays(1)
        }
        return count
    }
}
