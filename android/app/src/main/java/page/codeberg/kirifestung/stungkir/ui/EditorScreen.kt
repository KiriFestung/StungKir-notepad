// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import page.codeberg.kirifestung.stungkir.logic.Book
import page.codeberg.kirifestung.stungkir.logic.ChapterSession
import page.codeberg.kirifestung.stungkir.logic.TextRules
import java.io.File

@Composable
fun EditorScreen(state: AppState, file: File) {
    val book = state.book ?: return
    val context = LocalContext.current
    val c = MaterialTheme.colorScheme
    val prefs = state.prefs
    val session = remember(file) { ChapterSession(book, file) }
    val opened = remember(file) {
        try {
            if (!file.exists()) book.write(file, "")
            session.open()
        } catch (e: Exception) {
            null
        }
    }
    if (opened !is Book.Read.Text) {
        Column(Modifier.fillMaxSize()) {
            Bar(file.nameWithoutExtension, onBack = { state.back() })
            Text(
                if (opened is Book.Read.Locked) "Глава под паролем. Пароль на телефоне будет позже - пока открой её на компьютере."
                else "Главу не получилось прочитать. Проверь, что у приложения есть доступ к файлам.",
                color = c.onSurfaceVariant, modifier = Modifier.padding(20.dp),
            )
        }
        return
    }

    var chapterWords by remember(file) { mutableIntStateOf(TextRules.countWords(opened.text)) }
    var canUndo by remember { mutableStateOf(false) }
    var canRedo by remember { mutableStateOf(false) }
    var menu by remember { mutableStateOf(false) }

    val editor = remember(file) {
        ProseEditText(context).apply {
            names = TextRules.Names(try { book.names() } catch (e: Exception) { emptyList() })
            val pad = (18 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad / 2, pad, pad * 3)
            load(opened.text, prefs.cursor(file.absolutePath).let { if (it < 0) opened.text.length else it })
        }
    }

    fun flush(version: Boolean = false) {
        try {
            session.save(editor.text.toString(), session.edits(), version)
        } catch (e: Exception) {
            toast(context, "Не сохранилось: ${e.message}. Текст пока на экране - попробуй ещё раз.")
        }
        prefs.saveCursor(file.absolutePath, editor.selectionStart)
        state.counter?.save()
    }

    // вид: тема, шрифт, разметка
    editor.showPunctuation = prefs.punctuation
    editor.showRepeats = prefs.repeats
    editor.keepScreenOn = prefs.keepScreenOn
    LaunchedEffect(state.palette, state.version) {
        editor.applyLook(state.palette, prefs.font, prefs.fontSize, prefs.lineSpacing)
    }

    DisposableEffect(file) {
        prefs.lastChapter = file.absolutePath
        editor.onEdited = { typed, pasted ->
            session.edited()
            chapterWords = maxOf(0, chapterWords + typed + pasted)
            if (typed != 0) state.typed(typed)
        }
        editor.onUndoState = {
            canUndo = editor.undoStack.canUndo
            canRedo = editor.undoStack.canRedo
        }
        state.pauseHooks[file] = { flush(version = true) }
        onDispose {
            state.pauseHooks.remove(file)
            flush(version = true)
            editor.onEdited = null
            editor.onUndoState = null
        }
    }

    // автосохранение после паузы и проверка: не привёз ли Syncthing новый текст
    LaunchedEffect(file) {
        var ticks = 0
        while (true) {
            delay(500)
            ticks++
            if (session.dueSave()) {
                val text = editor.text.toString()
                val seen = session.edits()
                try {
                    withContext(Dispatchers.IO) { session.save(text, seen) }
                    state.counter?.save()
                } catch (e: Exception) {
                    toast(context, "Не сохранилось: ${e.message}")
                }
            }
            if (ticks % 6 == 0) {
                val current = editor.text.toString()
                when (val r = withContext(Dispatchers.IO) { session.checkExternal(current) }) {
                    is ChapterSession.External.Reload -> {
                        editor.replaceAll(r.text)
                        chapterWords = TextRules.countWords(r.text)
                        toast(context, "Глава обновилась - пришла с другого устройства")
                    }
                    ChapterSession.External.Kept ->
                        toast(context, "С другого устройства пришла другая версия главы. Оставлен твой текст, а пришедший - в «Версиях»")
                    ChapterSession.External.None -> {}
                }
            }
        }
    }

    Column(Modifier.fillMaxSize().background(color(state.palette.bg))) {
        val goal = prefs.goal
        val today = state.typedToday
        Bar(
            file.nameWithoutExtension,
            subtitle = "${words(chapterWords)} · сегодня $today" + (if (goal > 0) " из $goal" else ""),
            onBack = { state.back() },
            actions = {
                Box {
                    IconButton(onClick = { menu = true }) { Icon(Icons.Filled.MoreVert, contentDescription = "Ещё", tint = c.onSurface) }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        DropdownMenuItem(text = { Text("Версии главы") }, onClick = { menu = false; state.open(Screen.Versions(file)) })
                        DropdownMenuItem(text = { Text("Сохранить версию сейчас") }, onClick = {
                            menu = false
                            flush(version = true)
                            toast(context, "Версия сохранена")
                        })
                        DropdownMenuItem(text = { Text("Статистика") }, onClick = { menu = false; state.open(Screen.Stats) })
                        DropdownMenuItem(text = { Text("Настройки") }, onClick = { menu = false; state.open(Screen.Settings) })
                    }
                }
            },
        )
        if (goal > 0) GoalBar(today / goal.toFloat(), Modifier.fillMaxWidth())
        AndroidView(factory = { editor }, modifier = Modifier.weight(1f).fillMaxWidth())
        SymbolRow(editor, canUndo, canRedo)
    }
}

/** Кнопки над клавиатурой: то, чего на телефонной клавиатуре нет или до чего далеко. */
@Composable
private fun SymbolRow(editor: ProseEditText, canUndo: Boolean, canRedo: Boolean) {
    val c = MaterialTheme.colorScheme
    Row(
        Modifier.fillMaxWidth().background(c.surface).horizontalScroll(rememberScrollState()).height(46.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Key("↶", enabled = canUndo) { editor.undo() }
        Key("↷", enabled = canRedo) { editor.redo() }
        Key("—") { editor.insertDash() }
        Key("«»") { editor.insertAround("«", "»") }
        Key("…") { editor.insertAround("…") }
        Key("*к*", italic = true) { editor.insertAround("*", "*") }
        Key("**ж**", bold = true) { editor.insertAround("**", "**") }
        Key("[ ]") { editor.insertAround("[", "]") }
        Key("#") { editor.insertAround("# ") }
        Key("* * *") { editor.insertAround("\n* * *\n") }
        Key("„“") { editor.insertAround("„", "“") }
    }
}

@Composable
private fun Key(label: String, enabled: Boolean = true, italic: Boolean = false, bold: Boolean = false, onClick: () -> Unit) {
    val c = MaterialTheme.colorScheme
    Box(
        Modifier.widthIn(min = 46.dp).height(46.dp).clickable(enabled = enabled, onClick = onClick).padding(horizontal = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            label,
            color = if (enabled) c.onSurface else c.onSurfaceVariant.copy(alpha = 0.5f),
            fontSize = 18.sp,
            fontWeight = if (bold) FontWeight.Bold else FontWeight.Normal,
            fontStyle = if (italic) androidx.compose.ui.text.font.FontStyle.Italic else androidx.compose.ui.text.font.FontStyle.Normal,
        )
    }
}
