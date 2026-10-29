// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.ui

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

fun color(argb: Long) = Color(argb)

/** Надпись поверх цвета: белая или почти чёрная - что читается лучше. */
fun onColor(argb: Long): Color {
    val r = ((argb shr 16) and 0xFF) / 255.0
    val g = ((argb shr 8) and 0xFF) / 255.0
    val b = (argb and 0xFF) / 255.0
    val light = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return if (light > 0.5) Color(0xFF141414) else Color.White
}

@Composable
fun StungTheme(p: Palette, content: @Composable () -> Unit) {
    val scheme = if (p.light) {
        lightColorScheme(
            primary = color(p.important), onPrimary = onColor(p.important),
            secondary = color(p.dialogue), onSecondary = onColor(p.dialogue),
            background = color(p.bg), onBackground = color(p.text),
            surface = color(p.panel), onSurface = color(p.text),
            surfaceVariant = color(p.hover), onSurfaceVariant = color(p.dim),
            surfaceContainer = color(p.panel), surfaceContainerHigh = color(p.hover),
            surfaceContainerHighest = color(p.hover), surfaceContainerLow = color(p.panel),
            outline = color(p.border), outlineVariant = color(p.border),
        )
    } else {
        darkColorScheme(
            primary = color(p.important), onPrimary = onColor(p.important),
            secondary = color(p.dialogue), onSecondary = onColor(p.dialogue),
            background = color(p.bg), onBackground = color(p.text),
            surface = color(p.panel), onSurface = color(p.text),
            surfaceVariant = color(p.hover), onSurfaceVariant = color(p.dim),
            surfaceContainer = color(p.panel), surfaceContainerHigh = color(p.hover),
            surfaceContainerHighest = color(p.hover), surfaceContainerLow = color(p.panel),
            outline = color(p.border), outlineVariant = color(p.border),
        )
    }
    MaterialTheme(colorScheme = scheme, content = content)
}

/** Верхняя строка экрана: назад, заголовок с подписью, кнопки справа. */
@Composable
fun Bar(
    title: String,
    subtitle: String? = null,
    onBack: (() -> Unit)? = null,
    actions: @Composable () -> Unit = {},
) {
    val c = MaterialTheme.colorScheme
    Row(
        Modifier.fillMaxWidth().background(c.surface).height(56.dp).padding(horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (onBack != null) {
            IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, contentDescription = "Назад", tint = c.onSurface) }
        } else {
            Box(Modifier.width(12.dp))
        }
        Column(Modifier.weight(1f)) {
            Text(title, color = c.onSurface, fontSize = 18.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            if (subtitle != null) Text(subtitle, color = c.onSurfaceVariant, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        actions()
    }
}

/** Полоска прогресса цели. */
@Composable
fun GoalBar(fraction: Float, modifier: Modifier = Modifier) {
    val c = MaterialTheme.colorScheme
    Box(modifier.height(6.dp).clip(RoundedCornerShape(3.dp)).background(c.outline)) {
        Box(Modifier.fillMaxHeight().fillMaxWidth(fraction.coerceIn(0f, 1f)).background(c.primary))
    }
}

fun toast(context: android.content.Context, text: String) = Toast.makeText(context, text, Toast.LENGTH_LONG).show()

/** «1 слово», «2 слова», «5 слов». */
fun words(n: Int): String {
    val a = kotlin.math.abs(n)
    val word = when {
        a % 100 in 11..14 -> "слов"
        a % 10 == 1 -> "слово"
        a % 10 in 2..4 -> "слова"
        else -> "слов"
    }
    return "$n $word"
}

fun days(n: Int): String {
    val a = kotlin.math.abs(n)
    val word = when {
        a % 100 in 11..14 -> "дней"
        a % 10 == 1 -> "день"
        a % 10 in 2..4 -> "дня"
        else -> "дней"
    }
    return "$n $word"
}

/** Спросить перед удалением главы: она уходит в корзину, вернуть можно на компьютере. */
@Composable
fun TrashDialog(name: String, onDismiss: () -> Unit, onConfirm: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Удалить главу?") },
        text = { Text("«$name» уйдёт в корзину. На компьютере она 30 дней лежит в корзине («Ещё» → «Файлы и импорт» → «Корзина»), оттуда её можно вернуть вместе с версиями.") },
        confirmButton = { TextButton(onClick = onConfirm) { Text("В корзину") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } },
    )
}

/** Глава - в корзину; «Продолжить» на главном экране о ней забывает. true - получилось. */
fun trashChapter(state: AppState, file: java.io.File, context: android.content.Context): Boolean {
    val book = state.book ?: return false
    return try {
        book.moveToTrash(file)
        if (state.prefs.lastChapter == file.absolutePath) state.prefs.lastChapter = null
        state.version++
        toast(context, "«${file.nameWithoutExtension}» в корзине")
        true
    } catch (e: Exception) {
        toast(context, "Не получилось удалить: ${e.message}")
        false
    }
}
