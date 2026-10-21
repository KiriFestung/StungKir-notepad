package page.codeberg.kirifestung.stungkir

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import page.codeberg.kirifestung.stungkir.logic.TextRules
import page.codeberg.kirifestung.stungkir.logic.TextRules.Kind

class TextRulesTest {
    @Test fun countsWordsLikeDesktop() {
        assertEquals(5, TextRules.countWords("Кто-то пришёл, 12 раз; don’t"))
        assertEquals(0, TextRules.countWords("  — … «» "))
    }

    @Test fun rootsDropEndings() {
        assertEquals("смотрел", TextRules.wordRoot("смотрела"))
        assertEquals("смотрел", TextRules.wordRoot("смотрелась"))
        assertEquals("дорог", TextRules.wordRoot("дорогами"))
    }

    @Test fun pasteKeepsParagraphs() {
        assertEquals("Он вошёл.\nОна молчала.— Привет, — сказал он.\nПотом ушёл.",
            TextRules.cleanPasted("Он вошёл.Она молчала.— Привет, — сказал он.Потом ушёл."))
        assertEquals("Первая строка.\nВторая.\nТретья.", TextRules.cleanPasted("Первая строка.\r\nВторая. Третья."))
        // одиночную склейку не трогаем: это может быть «т.Е.» или сокращение
        assertEquals("Сказал т.Е. так", TextRules.cleanPasted("Сказал т.Е. так"))
    }

    @Test fun highlightsDialogueMarkersAndScenes() {
        val text = "— Привет, — сказала Кира.\nОбычная строка [проверить дату] и *курсив*.\n***\n# Глава"
        val kinds = TextRules.spans(text).map { it.kind }.toSet()
        assertTrue(Kind.DIALOGUE in kinds)
        assertTrue(Kind.MARKER in kinds)
        assertTrue(Kind.ITALIC in kinds)
        assertTrue(Kind.SCENE in kinds || Kind.STARS in kinds)
        assertTrue(Kind.HEADING in kinds)
        val marker = TextRules.spans(text).first { it.kind == Kind.MARKER }
        assertEquals("[проверить дату]", text.substring(marker.start, marker.end))
    }

    @Test fun repeatsSkipNamesAndShortWords() {
        val line = "Дорога шла вдаль, дорогами шли люди, и дорога кончилась."
        val found = TextRules.repeats(line).map { line.substring(it) }
        assertTrue(found.isNotEmpty())
        assertTrue(found.all { it.lowercase().startsWith("дорог") })
        val names = TextRules.Names(listOf("Мира"))
        val withName = "Мира пришла, Мира ушла, Миры нет."
        assertTrue(TextRules.repeats(withName, names).isEmpty())
    }

    @Test fun chapterNamesAndBadNames() {
        assertEquals("Глава 4", TextRules.nextChapterName(listOf("Глава 1", "Глава 3", "Пролог")))
        assertEquals("Глава 1", TextRules.nextChapterName(emptyList()))
        assertNull(TextRules.badName("Глава 2"))
        assertTrue(TextRules.badName("a/b") != null)
        assertTrue(TextRules.badName(".скрытая") != null)
        assertTrue(TextRules.badName("   ") != null)
    }

    @Test fun wordDeltaMatchesFullCount() {
        val random = java.util.Random(7)
        val pieces = listOf("кот", " ", "ик", "-то", "\n", "— ", "слово ", ",", "«а»", "12", "‘", "е́")
        var text = "Начало текста. Кот спит."
        repeat(3000) {
            val sb = StringBuilder(text)
            val at = if (sb.isEmpty()) 0 else random.nextInt(sb.length + 1)
            if (random.nextInt(3) == 0 && sb.isNotEmpty()) {
                val from = random.nextInt(sb.length)
                sb.delete(from, minOf(sb.length, from + 1 + random.nextInt(6)))
            } else {
                sb.insert(at, pieces[random.nextInt(pieces.size)])
            }
            val next = sb.toString()
            assertEquals("$text -> $next", TextRules.countWords(next) - TextRules.countWords(text), TextRules.wordDelta(text, next))
            text = next
        }
        assertEquals(0, TextRules.wordDelta("кот спит", "котик спит"))
        assertEquals(1, TextRules.wordDelta("кот спит", "кот не спит"))
    }

    @Test fun headingsAndPunctuation() {
        val spans = TextRules.lineSpans("## Пролог")
        assertTrue(spans.any { it.kind == Kind.HEADING && it.start == 0 && it.end == 9 })
        assertTrue(spans.any { it.kind == Kind.STARS && it.start == 0 && it.end == 3 })
        val p = TextRules.lineSpans("Да, нет.")
        assertEquals(2, p.count { it.kind == Kind.PUNCT })
        val b = TextRules.lineSpans("это **жирно** и *косо*")
        assertEquals("жирно", "это **жирно** и *косо*".substring(b.first { it.kind == Kind.BOLD }.start, b.first { it.kind == Kind.BOLD }.end))
        assertEquals(4, b.count { it.kind == Kind.STARS })
    }

    @Test fun unicodeWordsLikeDesktop() {
        // дефис внутри слова - не знак препинания; звёздочка вплотную к слову - не курсив
        assertTrue(TextRules.lineSpans("Кто-то").none { it.kind == Kind.PUNCT })
        assertEquals(1, TextRules.lineSpans("Да - нет").count { it.kind == Kind.PUNCT })
        assertTrue(TextRules.lineSpans("слово*не*курсив").none { it.kind == Kind.ITALIC })
    }
}
