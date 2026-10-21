// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import page.codeberg.kirifestung.stungkir.logic.Book
import page.codeberg.kirifestung.stungkir.logic.TextRules
import java.io.File

/** Сегодня, цель, серия - карточка сверху на главном экране. */
@Composable
fun TodayCard(state: AppState) {
    val c = MaterialTheme.colorScheme
    val goal = state.prefs.goal
    val today = state.typedToday
    val streak = remember(state.version, today) { state.streak() }
    Column(
        Modifier.fillMaxWidth().padding(12.dp).clip(RoundedCornerShape(12.dp)).background(c.surface)
            .clickable { state.open(Screen.Stats) }.padding(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Сегодня ${words(today)}", color = c.onSurface, fontSize = 17.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
            if (streak > 0) Text("серия ${days(streak)}", color = c.primary, fontSize = 14.sp)
        }
        if (goal > 0) {
            Spacer(Modifier.height(8.dp))
            GoalBar(today / goal.toFloat(), Modifier.fillMaxWidth())
            Spacer(Modifier.height(4.dp))
            val left = goal - today
            Text(
                if (left > 0) "до цели $left из $goal" else "цель $goal выполнена",
                color = c.onSurfaceVariant, fontSize = 12.sp,
            )
        }
    }
}

@Composable
fun NameDialog(title: String, initial: String, confirm: String, onDismiss: () -> Unit, onDone: (String) -> String?) {
    var name by remember { mutableStateOf(initial) }
    var error by remember { mutableStateOf<String?>(null) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            OutlinedTextField(
                value = name, onValueChange = { name = it; error = null }, singleLine = true,
                isError = error != null, supportingText = { error?.let { Text(it) } },
            )
        },
        confirmButton = {
            TextButton(onClick = {
                error = TextRules.badName(name) ?: onDone(name.trim())
            }) { Text(confirm) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } },
    )
}

@Composable
fun MainMenu(state: AppState) {
    var open by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { open = true }) { Icon(Icons.Filled.MoreVert, contentDescription = "Ещё", tint = MaterialTheme.colorScheme.onSurface) }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            DropdownMenuItem(text = { Text("Статистика") }, onClick = { open = false; state.open(Screen.Stats) })
            DropdownMenuItem(text = { Text("Настройки") }, onClick = { open = false; state.open(Screen.Settings) })
            DropdownMenuItem(text = { Text("Папка с текстами") }, onClick = { open = false; state.open(Screen.Folder) })
        }
    }
}

@Composable
fun LibraryScreen(state: AppState) {
    val book = state.book ?: return
    val c = MaterialTheme.colorScheme
    var adding by remember { mutableStateOf(false) }
    val categories by produceState(initialValue = emptyList<Pair<File, Int>>(), state.version) {
        value = withContext(Dispatchers.IO) {
            book.categories().map { folder -> folder to book.files(folder).count { Book.kind(it) == Book.Kind.CHAPTER } }
        }
    }
    // раз в минуту - свежие числа с компьютера (Syncthing мог привезти)
    LaunchedEffect(Unit) {
        while (true) {
            delay(60_000)
            state.reloadStats()
        }
    }
    Column(Modifier.fillMaxSize()) {
        Bar("StungKir", subtitle = book.root.name, actions = { MainMenu(state) })
        Box(Modifier.weight(1f)) {
            LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 96.dp)) {
                item { TodayCard(state) }
                state.prefs.lastChapter?.let { path ->
                    val file = File(path)
                    if (file.isFile && file.absolutePath.startsWith(book.root.absolutePath)) {
                        item {
                            Row(
                                Modifier.fillMaxWidth().clickable { state.open(Screen.Editor(file)) }.padding(horizontal = 16.dp, vertical = 10.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text("Продолжить: ", color = c.onSurfaceVariant, fontSize = 14.sp)
                                Text("${file.parentFile?.name} / ${file.nameWithoutExtension}", color = c.primary, fontSize = 15.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            }
                        }
                    }
                }
                if (categories.isEmpty()) {
                    item {
                        Text(
                            "Здесь пока пусто. Если на компьютере уже есть книги - проверь, что Syncthing закончил синхронизацию папки. Или создай категорию кнопкой «+».",
                            color = c.onSurfaceVariant, modifier = Modifier.padding(20.dp),
                        )
                    }
                }
                items(categories, key = { it.first.absolutePath }) { (folder, count) ->
                    Row(
                        Modifier.fillMaxWidth().clickable { state.open(Screen.Category(folder)) }.padding(horizontal = 16.dp, vertical = 14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.size(10.dp).clip(RoundedCornerShape(5.dp)).background(c.primary))
                        Spacer(Modifier.width(14.dp))
                        Text(folder.name, color = c.onBackground, fontSize = 17.sp, modifier = Modifier.weight(1f), maxLines = 2, overflow = TextOverflow.Ellipsis)
                        Text(count.toString(), color = c.onSurfaceVariant, fontSize = 14.sp)
                    }
                }
            }
            FloatingActionButton(
                onClick = { adding = true }, containerColor = c.primary, contentColor = c.onPrimary,
                modifier = Modifier.align(Alignment.BottomEnd).padding(20.dp),
            ) { Icon(Icons.Filled.Add, contentDescription = "Новая категория") }
        }
    }
    if (adding) {
        NameDialog("Новая категория", "", "Создать", onDismiss = { adding = false }) { name ->
            try {
                val folder = book.createCategory(name)
                adding = false
                state.version++
                state.open(Screen.Category(folder))
                null
            } catch (e: Exception) {
                e.message ?: "Не получилось"
            }
        }
    }
}

private data class Entry(val file: File, val kind: Book.Kind, val words: Int?, val locked: Boolean)

@Composable
fun CategoryScreen(state: AppState, folder: File) {
    val book = state.book ?: return
    val c = MaterialTheme.colorScheme
    val context = LocalContext.current
    var adding by remember { mutableStateOf(false) }
    val entries by produceState(initialValue = emptyList<Entry>(), folder, state.version) {
        value = withContext(Dispatchers.IO) {
            book.files(folder).map { file ->
                val kind = Book.kind(file)
                if (kind == Book.Kind.CHAPTER || kind == Book.Kind.CONFLICT) {
                    when (val read = try { book.read(file) } catch (e: Exception) { null }) {
                        is Book.Read.Text -> Entry(file, kind, TextRules.countWords(read.text), false)
                        is Book.Read.Locked -> Entry(file, kind, null, true)
                        null -> Entry(file, kind, null, false)
                    }
                } else {
                    Entry(file, kind, null, false)
                }
            }.filter { it.kind != Book.Kind.OTHER }
        }
    }
    val total = entries.filter { it.kind == Book.Kind.CHAPTER }.sumOf { it.words ?: 0 }
    Column(Modifier.fillMaxSize()) {
        Bar(folder.name, subtitle = words(total), onBack = { state.back() })
        Box(Modifier.weight(1f)) {
            LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 96.dp)) {
                if (entries.isEmpty()) {
                    item { Text("Глав пока нет. Новая - кнопкой «+».", color = c.onSurfaceVariant, modifier = Modifier.padding(20.dp)) }
                }
                items(entries, key = { it.file.absolutePath }) { e ->
                    Row(
                        Modifier.fillMaxWidth().clickable {
                            when {
                                e.kind == Book.Kind.CONFLICT -> state.open(Screen.Conflict(e.file))
                                e.kind == Book.Kind.DESKTOP_ONLY -> toast(context, "Таблицы, доски и ленты времени пока открываются только на компьютере")
                                e.locked -> toast(context, "Глава под паролем. Пароль на телефоне будет позже - пока открой её на компьютере")
                                else -> state.open(Screen.Editor(e.file))
                            }
                        }.padding(horizontal = 16.dp, vertical = 13.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        when {
                            e.kind == Book.Kind.CONFLICT -> Icon(Icons.Filled.Warning, contentDescription = "Конфликт", tint = c.primary, modifier = Modifier.size(20.dp))
                            e.locked -> Icon(Icons.Filled.Lock, contentDescription = "Под паролем", tint = c.onSurfaceVariant, modifier = Modifier.size(20.dp))
                        }
                        Column(Modifier.weight(1f)) {
                            val dim = e.kind == Book.Kind.DESKTOP_ONLY || e.locked
                            Text(
                                if (e.kind == Book.Kind.CHAPTER) e.file.nameWithoutExtension else e.file.name,
                                color = if (dim) c.onSurfaceVariant else c.onBackground, fontSize = 16.sp,
                                maxLines = 2, overflow = TextOverflow.Ellipsis,
                            )
                            if (e.kind == Book.Kind.CONFLICT) {
                                Text("две версии разошлись при синхронизации - разобрать", color = c.primary, fontSize = 12.sp)
                            }
                        }
                        e.words?.let { Text(it.toString(), color = c.onSurfaceVariant, fontSize = 13.sp) }
                    }
                }
            }
            FloatingActionButton(
                onClick = { adding = true }, containerColor = c.primary, contentColor = c.onPrimary,
                modifier = Modifier.align(Alignment.BottomEnd).padding(20.dp),
            ) { Icon(Icons.Filled.Add, contentDescription = "Новая глава") }
        }
    }
    if (adding) {
        NameDialog("Новая глава", remember(folder) { book.nextChapterName(folder) }, "Создать", onDismiss = { adding = false }) { name ->
            try {
                val file = book.createChapter(folder, name)
                adding = false
                state.version++
                state.open(Screen.Editor(file))
                null
            } catch (e: Exception) {
                e.message ?: "Не получилось"
            }
        }
    }
}
