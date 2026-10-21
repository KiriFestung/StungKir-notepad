// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
// Цвета тем - те же, что на компьютере (stungkir/config.py THEMES). Файл собран из них скриптом.
package page.codeberg.kirifestung.stungkir.ui

data class Palette(
    val name: String, val bg: Long, val text: Long, val dialogue: Long, val punct: Long, val repeatBg: Long,
    val marker: Long, val markerBg: Long, val dim: Long, val panel: Long, val border: Long, val hover: Long,
    val accent: Long, val select: Long, val important: Long, val light: Boolean,
)

object Themes {
    val ALL = listOf(
        Palette("Индиго и охра", 0xFF121429, 0xFFC6CBE9, 0xFFE2B65A, 0xFFF5EFE0, 0xFF3D3274,
            0xFFF0A08F, 0xFF3A2228, 0xFF6A6F9C, 0xFF181B37, 0xFF282C55, 0xFF212549,
            0xFF2E2A6E, 0xFF2C3268, 0xFFD4A02E, false),
        Palette("Мох", 0xFF171B18, 0xFF93BF9C, 0xFFD2B47C, 0xFFE6EDE4, 0xFF403670,
            0xFFE3A08F, 0xFF3A2723, 0xFF5A7360, 0xFF1F2420, 0xFF2A322C, 0xFF273029,
            0xFF355A41, 0xFF2B4535, 0xFF7C3AED, false),
        Palette("Сирень", 0xFF16141B, 0xFFB9A6E8, 0xFFE0B77C, 0xFFEFEAF8, 0xFF2F4A5C,
            0xFFE3A08F, 0xFF3A2629, 0xFF6E6488, 0xFF1E1B25, 0xFF2D2838, 0xFF29243A,
            0xFF4C3A7A, 0xFF3A2F5C, 0xFFE11D48, false),
        Palette("Сепия", 0xFF1B1814, 0xFFD4C4A4, 0xFFE3A86F, 0xFFF3ECE0, 0xFF453C78,
            0xFFE3A08F, 0xFF3A2723, 0xFF7D7058, 0xFF23201A, 0xFF332D24, 0xFF2C2720,
            0xFF5A4A33, 0xFF43382A, 0xFFC2410C, false),
        Palette("Дневная бумага", 0xFFF3ECDB, 0xFF3B342B, 0xFF70400F, 0xFF35587A, 0xFFD3BDF0,
            0xFF9A3F25, 0xFFF1CFC1, 0xFF857A68, 0xFFE3D5B8, 0xFFB9A67C, 0xFFD9C9A6,
            0xFFC2A878, 0xFFD8C69C, 0xFF7C3AED, true),
        Palette("Полночь", 0xFF120F1A, 0xFFC3B4EF, 0xFFF2A7B8, 0xFFF4F0FF, 0xFF3D2F6E,
            0xFFF0A08F, 0xFF3F1F2A, 0xFF75689A, 0xFF1A1526, 0xFF2C2442, 0xFF251D3A,
            0xFF5B2FB3, 0xFF3A2A6A, 0xFFE11D48, false),
        Palette("Чернила", 0xFF0F1520, 0xFFB8C7DC, 0xFFE6C07B, 0xFFEEF3FA, 0xFF3B3570,
            0xFFE3A08F, 0xFF3A2626, 0xFF5F7189, 0xFF151D2B, 0xFF22304A, 0xFF1D2840,
            0xFF2E4A78, 0xFF24395E, 0xFF2563EB, false),
        Palette("Пергамент", 0xFFEFE4CC, 0xFF3D3326, 0xFF6A320D, 0xFF2F5A7A, 0xFFD6C2EE,
            0xFF93361C, 0xFFECC6B4, 0xFF84755B, 0xFFE2D2B0, 0xFFB5A079, 0xFFD8C49C,
            0xFFB89A62, 0xFFD3BD8C, 0xFF9A3412, true),
        Palette("Графит", 0xFF1C1C1E, 0xFFC8C8C8, 0xFFD9B98A, 0xFFF2F2F2, 0xFF3E3A5E,
            0xFFE3A08F, 0xFF3B2A28, 0xFF707074, 0xFF242426, 0xFF333336, 0xFF2C2C2F,
            0xFF48484E, 0xFF3A3A40, 0xFF7C3AED, false),
        Palette("Высокий контраст", 0xFF0A0A0A, 0xFFF0F0F0, 0xFFFFD27A, 0xFFFFFFFF, 0xFF4B3C9A,
            0xFFFFB199, 0xFF4A2016, 0xFFA0A0A0, 0xFF141414, 0xFF5A5A5A, 0xFF262626,
            0xFF5A5A5A, 0xFF3A3A6A, 0xFFFFD400, false),
    )
    const val DEFAULT = "Индиго и охра"
    fun byName(name: String?): Palette = ALL.firstOrNull { it.name == name } ?: ALL.first { it.name == DEFAULT }
}
