// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.logic

/**
 * Правила текста - те же, что в блокноте на компьютере (stungkir/textutil.py):
 * счёт слов, повторы слов рядом, подсветка реплик, пометок, курсива, починка вставки.
 */
object TextRules {
    /** Слово - как \w+(?:[-'’]\w+)* в блокноте на компьютере. */
    val WORD = Regex("[\\p{L}\\p{N}_]+(?:[-'’][\\p{L}\\p{N}_]+)*")
    private val CYR_WORD = Regex("[А-Яа-яЁё́]+(?:-[А-Яа-яЁё́]+)*")
    val MARKER = Regex("\\[[^\\[\\]\\n]{0,120}\\]")
    /** **жирный** или *курсив* - как EMPH_RE на компьютере. */
    private val EMPH = Regex("\\*\\*(?=\\S)(.+?)(?<=\\S)\\*\\*|(?<![*\\p{L}\\p{N}_])\\*(?=\\S)([^*\\n]+?)(?<=\\S)\\*(?![*\\p{L}\\p{N}_])")
    private val PUNCT = Regex("[.,!?;:…«»„“”\"'’()—–]|(?<![\\p{L}\\p{N}_])-|-(?![\\p{L}\\p{N}_])")
    private val HEADING_LINE = Regex("^(\\s*#{1,3}\\s+)\\S")
    const val REPEAT_WINDOW = 15
    const val REPEAT_MIN_LEN = 4
    const val STREAK_WORDS = 250

    fun countWords(text: CharSequence): Int = WORD.findAll(text).count()

    val STOP_WORDS: Set<String> = """
        это этот эта эти этого этой этому этим этом того тому тоже также только когда тогда потом
        теперь сейчас здесь опять снова перед после через между около против было были была будет
        будут есть быть него нему ними своей свой свою свои своих своим себя себе тебя тебе
        меня даже если чтобы чтоб очень может можно нужно надо который которая которое
        которые которых которым какой какая какое какие сказал сказала сказали ответил ответила
        спросил спросила хотя пока ведь вдруг потому почему зачем куда откуда всех всем всего всё
        все весь вся она они оно неё ней нами вами ваши наши наша ваша наш ваш просто
    """.trim().split(Regex("\\s+")).toSet()

    private val ROOT_ENDINGS: List<String> = """
        ившись ывшись ешься ется ются ится атся ятся ешь ете ите
        ами ями ого его ому ему ыми ими ией ость ости остью иях ием ией
        ой ей ий ый ая яя ое ее ые ие ую юю ом ем ам ям ах ях ов ев ью ия ья ье ьи ию ьё
        ет ют ут ит ат ят им ть ться тся сь ся
        а я о е ё ы и у ю ь й
    """.trim().split(Regex("\\s+")).distinct().sortedByDescending { it.length }

    fun nameKey(word: String): String = word.replace("́", "").lowercase().replace('ё', 'е')

    /** Основа слова для повторов: «туман» и «тумана» - одно, «голоса» и «голове» - разное. */
    fun wordRoot(source: String): String {
        var word = source
        if ((word.endsWith("ся") || word.endsWith("сь")) && word.length >= 7) word = word.dropLast(2)
        for (ending in ROOT_ENDINGS) {
            if (word.endsWith(ending) && word.length - ending.length >= 3) return word.dropLast(ending.length)
        }
        return word
    }

    /** Имена персонажей: их повтор - не ошибка («Кира… Кира»). */
    class Names(names: Collection<String>) {
        private val rules = names.map { nameKey(it) }.filter { it.isNotBlank() }.map { key ->
            (if (key.length <= 4) key else key.substring(0, maxOf(4, key.length - 2))) to key.length + 3
        }

        fun isName(word: String): Boolean = rules.any { (base, limit) -> word.startsWith(base) && word.length <= limit }
    }

    enum class Kind { DIALOGUE, PUNCT, MARKER, ITALIC, BOLD, STARS, HEADING, SCENE, REPEAT }

    data class Span(val start: Int, val end: Int, val kind: Kind)

    private fun isDialogue(line: String): Boolean {
        val t = line.trimStart()
        return t.startsWith("—") || t.startsWith("–")
    }

    private fun isScene(line: String): Boolean {
        val t = line.trim()
        return t.isNotEmpty() && t.all { it == '*' || it == '~' || it == '•' || it == ' ' }
    }

    /** Что и где покрасить. Считается по строкам (абзацам), как на компьютере. */
    fun spans(text: String, names: Names = Names(emptyList())): List<Span> {
        val out = ArrayList<Span>()
        var start = 0
        while (start <= text.length) {
            var end = text.indexOf('\n', start)
            if (end < 0) end = text.length
            val line = text.substring(start, end)
            lineSpans(line, start, names, out)
            start = end + 1
        }
        return out
    }

    private fun lineSpans(line: String, offset: Int, names: Names, out: MutableList<Span>) {
        if (line.isBlank()) return
        val heading = HEADING_LINE.find(line)
        if (heading != null) {
            // «# Пролог» - заголовок внутри главы, решётки приглушены
            out.add(Span(offset, offset + line.length, Kind.HEADING))
            out.add(Span(offset, offset + heading.groups[1]!!.range.last + 1, Kind.STARS))
            return
        }
        if (isScene(line)) {
            out.add(Span(offset, offset + line.length, Kind.SCENE))
            return
        }
        if (isDialogue(line)) out.add(Span(offset, offset + line.length, Kind.DIALOGUE))
        if ('*' in line) {
            for (m in EMPH.findAll(line)) {
                val bold = m.groups[1] != null
                val inner = (if (bold) m.groups[1] else m.groups[2])!!.range
                out.add(Span(offset + m.range.first, offset + inner.first, Kind.STARS))
                out.add(Span(offset + inner.last + 1, offset + m.range.last + 1, Kind.STARS))
                out.add(Span(offset + inner.first, offset + inner.last + 1, if (bold) Kind.BOLD else Kind.ITALIC))
            }
        }
        for (m in PUNCT.findAll(line)) out.add(Span(offset + m.range.first, offset + m.range.last + 1, Kind.PUNCT))
        val markers = if ('[' in line) MARKER.findAll(line).map { it.range }.toList() else emptyList()
        for (m in markers) out.add(Span(offset + m.first, offset + m.last + 1, Kind.MARKER))
        for (r in repeats(line, names, markers)) out.add(Span(offset + r.first, offset + r.last + 1, Kind.REPEAT))
    }

    /** Разметка одного абзаца с отсчётом от его начала. Для редактора: красит только изменённые абзацы. */
    fun lineSpans(line: String, names: Names = Names(emptyList())): List<Span> =
        ArrayList<Span>().also { lineSpans(line, 0, names, it) }

    /** Сколько слов прибавилось/убавилось правкой: считаются только изменённые места, а не вся глава. */
    fun wordDelta(old: CharSequence, new: CharSequence): Int {
        var prefix = 0
        val limit = minOf(old.length, new.length)
        while (prefix < limit && old[prefix] == new[prefix]) prefix++
        var suffix = 0
        while (suffix < limit - prefix && old[old.length - 1 - suffix] == new[new.length - 1 - suffix]) suffix++
        // до границ слов, чтобы «кот» -> «котик» было 0, а не +1
        fun isWordChar(c: Char) = c.isLetterOrDigit() || c == '_' || c == '-' || c == '\'' || c == '’' || c == '\u0301'
        while (prefix > 0 && (isWordChar(old[prefix - 1]))) prefix--
        while (suffix > 0 && isWordChar(old[old.length - suffix])) suffix--
        return countWords(new.subSequence(prefix, new.length - suffix)) - countWords(old.subSequence(prefix, old.length - suffix))
    }

    /** Повторы одного слова рядом (в пределах REPEAT_WINDOW слов). Внутри [пометок] не ищутся. */
    fun repeats(line: String, names: Names = Names(emptyList()), skip: List<IntRange> = emptyList()): List<IntRange> {
        val tokens = CYR_WORD.findAll(line).filter { m -> skip.none { m.range.first in it } }.toList()
        val keys = tokens.map { m ->
            val word = nameKey(m.value)
            if (word.length >= REPEAT_MIN_LEN && word !in STOP_WORDS && !names.isName(word)) wordRoot(word) else null
        }
        val marked = sortedSetOf<Int>()
        val last = HashMap<String, ArrayDeque<Int>>()
        keys.forEachIndexed { i, key ->
            if (key == null) return@forEachIndexed
            val seen = last.getOrPut(key) { ArrayDeque() }
            while (seen.isNotEmpty() && i - seen.first() > REPEAT_WINDOW) seen.removeFirst()
            if (seen.isNotEmpty()) {
                marked.add(i)
                marked.addAll(seen)
            }
            seen.addLast(i)
        }
        return marked.map { tokens[it].range }
    }

    // ---------------- починка вставки (как clean_pasted на компьютере) ----------------
    private val LINE_BREAKS = Regex("\r\n|[\r\u000b\u000c\u0085  ]")
    private val PARAGRAPH_GAP = Regex("(?<=[.!?…»\"'”)\\]>/*:])[ \t ]{3,}(?=\\S)")
    private val SPACES = Regex("(?<=\\S)[ \t ]{2,}(?=\\S)")
    private val PAIRS = mapOf('«' to '»', '<' to '>', '{' to '}', '(' to ')', '[' to ']', '„' to '“', '“' to '”', '‘' to '’')
    private val CLOSERS = PAIRS.values.toSet()
    private val SYMMETRIC = setOf('\'', '"', '/')
    private val ENDS = setOf('.', '!', '?', '…')

    /** Где резать слипшийся текст: после конца фразы или закрытой реплики, когда без пробела
     *  начинается новая реплика или фраза с заглавной, и все кавычки уже закрыты. */
    fun gluedCuts(text: String): List<Int> {
        val cuts = ArrayList<Int>()
        val stack = ArrayList<Char>()
        val n = text.length
        for (i in 0 until n) {
            val ch = text[i]
            if (ch == '\n') {
                stack.clear()
                continue
            }
            val before = if (i > 0) text[i - 1] else ' '
            val after = if (i + 1 < n) text[i + 1] else ' '
            if (ch in SYMMETRIC) {
                if (before.isLetter() && after.isLetter()) continue
                val at = stack.lastIndexOf(ch)
                if (at >= 0) while (stack.size > at) stack.removeAt(stack.size - 1) else stack.add(ch)
            } else if (ch in PAIRS) {
                stack.add(PAIRS.getValue(ch))
            } else if (ch in CLOSERS) {
                val at = stack.lastIndexOf(ch)
                if (at >= 0) while (stack.size > at) stack.removeAt(stack.size - 1)
            }
            if (stack.isNotEmpty() || i + 1 >= n || !(ch in ENDS || ch in CLOSERS || ch in SYMMETRIC)) continue
            val next = text[i + 1]
            if (next.isWhitespace()) continue
            var starts = next.isUpperCase() && next.isLetter()
            if (next in PAIRS || next in SYMMETRIC) {
                var j = i + 1
                while (j < n && (text[j] in PAIRS || text[j] in SYMMETRIC)) j++
                starts = j < n && (text[j].isLetter() || text[j] == '.' || text[j] == '…')
            }
            if (!starts) continue
            var k = i
            while (k >= 0 && (text[k] in ENDS || text[k] in CLOSERS || text[k] in SYMMETRIC)) k--
            if (k >= 1 && text[k].isLetter() && text[k].isLowerCase() && text[k - 1].isLetter() && text[k - 1].isLowerCase()) {
                cuts.add(i + 1)
            }
        }
        return cuts
    }

    fun unglue(text: String): String {
        val cuts = gluedCuts(text)
        if (cuts.size < 3 && !(cuts.size == 2 && '\n' !in text)) return text
        val out = StringBuilder()
        var last = 0
        for (cut in cuts) {
            out.append(text, last, cut).append('\n')
            last = cut
        }
        return out.append(text, last, text.length).toString()
    }

    /** Текст из буфера: переносы любого вида - обычные, три пробела после фразы - абзац, слипшееся - разрезать. */
    fun cleanPasted(source: String): String {
        var text = LINE_BREAKS.replace(source, "\n")
        text = PARAGRAPH_GAP.replace(text, "\n")
        text = unglue(text)
        text = SPACES.replace(text, " ")
        text = Regex("[ \t ]+\n").replace(text, "\n")
        return Regex("[ \t ]{2,}$").replace(text, "")
    }

    /** «Глава N» - следующий номер после самого большого. */
    fun nextChapterName(existing: Collection<String>): String {
        val numbers = existing.mapNotNull { Regex("Глава (\\d+)").matchEntire(it)?.groupValues?.get(1)?.toIntOrNull() }
        return "Глава ${(numbers.maxOrNull() ?: 0) + 1}"
    }

    /** Почему название не годится для файла (на компьютере, Windows и телефоне). null - годится. */
    fun badName(name: String): String? {
        val clean = name.trim()
        return when {
            clean.isEmpty() -> "Пустое название"
            clean.startsWith(".") -> "Название не может начинаться с точки"
            clean.endsWith(".") || clean.endsWith(" ") -> "Название не может кончаться точкой или пробелом"
            clean.any { it in "/\\:*?\"<>|" || it < ' ' } -> "Нельзя знаки / \\ : * ? \" < > |"
            clean.toByteArray().size > 200 -> "Слишком длинное название"
            else -> null
        }
    }
}
