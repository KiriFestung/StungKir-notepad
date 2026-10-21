// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.logic

/**
 * Крошечный JSON: служебные файлы блокнота простые (список строк, «день -> слов»),
 * а встроенный в Android org.json не работает в обычных проверках на компьютере.
 */
object Json {
    fun parse(text: String): Any? {
        val parser = Parser(text)
        val value = parser.value()
        parser.skipSpace()
        if (!parser.done()) throw IllegalArgumentException("лишнее в конце JSON")
        return value
    }

    fun stringList(text: String?): List<String> = try {
        (parse(text ?: "") as? List<*>)?.filterIsInstance<String>() ?: emptyList()
    } catch (e: IllegalArgumentException) {
        emptyList()
    }

    fun intMap(text: String?): Map<String, Int> = try {
        val raw = parse(text ?: "") as? Map<*, *> ?: emptyMap<String, Any>()
        raw.entries.mapNotNull { (k, v) ->
            val key = k as? String ?: return@mapNotNull null
            val number = (v as? Number)?.toInt() ?: return@mapNotNull null
            key to number
        }.toMap()
    } catch (e: IllegalArgumentException) {
        emptyMap()
    }

    fun quote(value: String): String {
        val out = StringBuilder("\"")
        for (ch in value) {
            when (ch) {
                '"' -> out.append("\\\"")
                '\\' -> out.append("\\\\")
                '\n' -> out.append("\\n")
                '\r' -> out.append("\\r")
                '\t' -> out.append("\\t")
                else -> if (ch < ' ') out.append(String.format("\\u%04x", ch.code)) else out.append(ch)
            }
        }
        return out.append('"').toString()
    }

    fun ofList(values: List<String>): String = values.joinToString(", ", "[", "]") { quote(it) }

    fun ofIntMap(values: Map<String, Int>): String =
        values.toSortedMap().entries.joinToString(", ", "{", "}") { "${quote(it.key)}: ${it.value}" }

    private class Parser(val s: String) {
        var i = 0
        fun done() = i >= s.length
        fun skipSpace() {
            while (i < s.length && s[i].isWhitespace()) i++
        }

        fun value(): Any? {
            skipSpace()
            if (done()) throw IllegalArgumentException("пустой JSON")
            return when (val c = s[i]) {
                '{' -> obj()
                '[' -> arr()
                '"' -> str()
                't' -> word("true", true)
                'f' -> word("false", false)
                'n' -> word("null", null)
                else -> if (c == '-' || c.isDigit()) num() else throw IllegalArgumentException("непонятный JSON")
            }
        }

        private fun word(w: String, v: Any?): Any? {
            if (!s.startsWith(w, i)) throw IllegalArgumentException("непонятный JSON")
            i += w.length
            return v
        }

        private fun num(): Number {
            val start = i
            while (i < s.length && (s[i].isDigit() || s[i] in "+-.eE")) i++
            val text = s.substring(start, i)
            return text.toLongOrNull() ?: text.toDoubleOrNull() ?: throw IllegalArgumentException("не число")
        }

        private fun str(): String {
            i++
            val out = StringBuilder()
            while (i < s.length) {
                val c = s[i++]
                when (c) {
                    '"' -> return out.toString()
                    '\\' -> {
                        if (i >= s.length) break
                        when (val e = s[i++]) {
                            'n' -> out.append('\n')
                            'r' -> out.append('\r')
                            't' -> out.append('\t')
                            'b' -> out.append('\b')
                            'f' -> out.append('\u000c')
                            'u' -> {
                                if (i + 4 > s.length) throw IllegalArgumentException("обрыв \\u")
                                out.append(s.substring(i, i + 4).toInt(16).toChar())
                                i += 4
                            }
                            else -> out.append(e)
                        }
                    }
                    else -> out.append(c)
                }
            }
            throw IllegalArgumentException("строка не закрыта")
        }

        private fun arr(): List<Any?> {
            i++
            val out = mutableListOf<Any?>()
            skipSpace()
            if (i < s.length && s[i] == ']') {
                i++
                return out
            }
            while (true) {
                out.add(value())
                skipSpace()
                if (done()) throw IllegalArgumentException("список не закрыт")
                when (s[i++]) {
                    ',' -> continue
                    ']' -> return out
                    else -> throw IllegalArgumentException("ждал , или ]")
                }
            }
        }

        private fun obj(): Map<String, Any?> {
            i++
            val out = LinkedHashMap<String, Any?>()
            skipSpace()
            if (i < s.length && s[i] == '}') {
                i++
                return out
            }
            while (true) {
                skipSpace()
                if (done() || s[i] != '"') throw IllegalArgumentException("ждал ключ")
                val key = str()
                skipSpace()
                if (done() || s[i++] != ':') throw IllegalArgumentException("ждал :")
                out[key] = value()
                skipSpace()
                if (done()) throw IllegalArgumentException("объект не закрыт")
                when (s[i++]) {
                    ',' -> continue
                    '}' -> return out
                    else -> throw IllegalArgumentException("ждал , или }")
                }
            }
        }
    }
}
