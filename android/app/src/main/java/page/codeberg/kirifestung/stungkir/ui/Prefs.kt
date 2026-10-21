// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.ui

import android.content.Context

/** Настройки телефона. Они свои, не общие с компьютером: у телефона другой экран и другая жизнь. */
class Prefs(context: Context) {
    private val store = context.getSharedPreferences("stungkir", Context.MODE_PRIVATE)

    var folder: String?
        get() = store.getString("folder", null)
        set(value) = store.edit().putString("folder", value).apply()
    var goal: Int
        get() = store.getInt("goal", 500)
        set(value) = store.edit().putInt("goal", value).apply()
    var fontSize: Int
        get() = store.getInt("font_size", 18)
        set(value) = store.edit().putInt("font_size", value).apply()
    var font: String
        get() = store.getString("font", "Literata") ?: "Literata"
        set(value) = store.edit().putString("font", value).apply()
    var theme: String
        get() = store.getString("theme", Themes.DEFAULT) ?: Themes.DEFAULT
        set(value) = store.edit().putString("theme", value).apply()
    var punctuation: Boolean
        get() = store.getBoolean("punctuation", true)
        set(value) = store.edit().putBoolean("punctuation", value).apply()
    var repeats: Boolean
        get() = store.getBoolean("repeats", true)
        set(value) = store.edit().putBoolean("repeats", value).apply()
    var keepScreenOn: Boolean
        get() = store.getBoolean("keep_screen_on", true)
        set(value) = store.edit().putBoolean("keep_screen_on", value).apply()
    var lineSpacing: Float
        get() = store.getFloat("line_spacing", 1.35f)
        set(value) = store.edit().putFloat("line_spacing", value).apply()

    /** Где остановился в главе: курсор возвращается туда же. */
    fun cursor(path: String): Int = store.getInt("cursor:$path", -1)
    fun saveCursor(path: String, at: Int) = store.edit().putInt("cursor:$path", at).apply()
    var lastChapter: String?
        get() = store.getString("last_chapter", null)
        set(value) = store.edit().putString("last_chapter", value).apply()

    companion object {
        val FONTS = listOf("Literata", "PT Serif", "Системный с засечками", "Системный без засечек")
    }
}
