package page.codeberg.kirifestung.stungkir

import org.junit.Assert.assertEquals
import org.junit.Test
import page.codeberg.kirifestung.stungkir.logic.Json

class JsonTest {
    @Test fun roundTripsLists() {
        val names = listOf("Глава 1.txt", "кавычки \"и\" \\слэш", "таб\tи\nперенос")
        assertEquals(names, Json.stringList(Json.ofList(names)))
    }

    @Test fun readsDesktopFiles() {
        assertEquals(listOf("Тервена", "Кев"), Json.stringList("[\"\\u0422\\u0435\\u0440\\u0432\\u0435\\u043d\\u0430\", \"Кев\"]"))
        assertEquals(mapOf("2026-10-20" to 300, "2026-10-21" to 12), Json.intMap("{\"2026-10-20\": 300, \"2026-10-21\": 12.0}"))
    }

    @Test fun badJsonGivesEmpty() {
        assertEquals(emptyList<String>(), Json.stringList("{испорчено"))
        assertEquals(emptyMap<String, Int>(), Json.intMap("[1,2"))
    }
}
