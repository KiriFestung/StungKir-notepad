// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.ui

import android.os.Environment
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import page.codeberg.kirifestung.stungkir.BuildConfig
import page.codeberg.kirifestung.stungkir.logic.Book
import java.io.File
import java.time.LocalDate

// ---------------- версии главы ----------------
@Composable
fun VersionsScreen(state: AppState, file: File) {
    val book = state.book ?: return
    val c = MaterialTheme.colorScheme
    val context = LocalContext.current
    var shown by remember { mutableStateOf<File?>(null) }
    val versions by produceState(initialValue = emptyList<File>(), file, state.version) {
        value = withContext(Dispatchers.IO) { book.versions(file) }
    }
    Column(Modifier.fillMaxSize()) {
        Bar("Версии", subtitle = file.nameWithoutExtension, onBack = { state.back() })
        if (versions.isEmpty()) {
            Text("Версий пока нет. Они появляются сами, пока пишешь (не чаще раза в 10 минут), и при выходе из главы.",
                color = c.onSurfaceVariant, modifier = Modifier.padding(20.dp))
        }
        LazyColumn(Modifier.fillMaxSize()) {
            items(versions, key = { it.absolutePath }) { v ->
                Row(Modifier.fillMaxWidth().clickable { shown = v }.padding(horizontal = 16.dp, vertical = 14.dp)) {
                    Text(book.versionLabel(v), color = c.onBackground, fontSize = 16.sp, modifier = Modifier.weight(1f))
                }
            }
        }
    }
    val v = shown
    if (v != null) {
        val text = remember(v) {
            when (val r = try { book.read(v) } catch (e: Exception) { null }) {
                is Book.Read.Text -> r.text
                is Book.Read.Locked -> null
                null -> null
            }
        }
        AlertDialog(
            onDismissRequest = { shown = null },
            title = { Text(book.versionLabel(v)) },
            text = {
                Column(Modifier.heightIn(max = 420.dp).verticalScroll(rememberScrollState())) {
                    Text(text ?: "Версия под паролем - посмотри её на компьютере.", fontSize = 15.sp)
                }
            },
            confirmButton = {
                if (text != null) {
                    TextButton(onClick = {
                        try {
                            val now = book.read(file)
                            if (now is Book.Read.Text) book.snapshot(file, now.text)
                            book.write(file, text)
                            toast(context, "Глава вернулась к версии ${book.versionLabel(v)}. То, что было, тоже лежит в версиях")
                            shown = null
                            state.version++
                            state.back()
                        } catch (e: Exception) {
                            toast(context, "Не получилось: ${e.message}")
                        }
                    }) { Text("Вернуть эту") }
                }
            },
            dismissButton = { TextButton(onClick = { shown = null }) { Text("Закрыть") } },
        )
    }
}

// ---------------- конфликт синхронизации ----------------
@Composable
fun ConflictScreen(state: AppState, file: File) {
    val book = state.book ?: return
    val c = MaterialTheme.colorScheme
    val context = LocalContext.current
    val original = Book.conflictOriginal(file.name)?.let { File(file.parentFile, it) }
    val (mine, theirs) = remember(file) {
        fun text(f: File?) = try {
            (f?.let { book.read(it) } as? Book.Read.Text)?.text
        } catch (e: Exception) {
            null
        }
        text(original) to text(file)
    }
    var tab by remember { mutableStateOf(1) }
    Column(Modifier.fillMaxSize()) {
        Bar("Две версии главы", subtitle = original?.nameWithoutExtension, onBack = { state.back() })
        Text(
            "Глава поменялась сразу на двух устройствах, и Syncthing сохранил вторую версию отдельным файлом. " +
                "Выбери, какую оставить. Вторая не пропадёт - она ляжет в «Версии» главы.",
            color = c.onSurfaceVariant, fontSize = 14.sp, modifier = Modifier.padding(16.dp),
        )
        Row(Modifier.padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Chip("Глава сейчас", tab == 0) { tab = 0 }
            Chip("Вторая версия", tab == 1) { tab = 1 }
        }
        Box(Modifier.weight(1f).fillMaxWidth().padding(16.dp).verticalScroll(rememberScrollState())) {
            Text((if (tab == 0) mine else theirs) ?: "(не читается)", color = c.onBackground, fontSize = 15.sp)
        }
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = {
                try {
                    book.dropConflict(file)
                    toast(context, "Оставлена глава как есть")
                    state.version++
                    state.back()
                } catch (e: Exception) {
                    toast(context, "Не получилось: ${e.message}")
                }
            }, modifier = Modifier.weight(1f)) { Text("Оставить главу") }
            Button(onClick = {
                try {
                    book.keepConflict(file)
                    toast(context, "Глава заменена второй версией")
                    state.version++
                    state.back()
                } catch (e: Exception) {
                    toast(context, "Не получилось: ${e.message}")
                }
            }, modifier = Modifier.weight(1f)) { Text("Взять вторую") }
        }
    }
}

@Composable
private fun Chip(label: String, selected: Boolean, onClick: () -> Unit) {
    val c = MaterialTheme.colorScheme
    Box(
        Modifier.clip(RoundedCornerShape(16.dp)).background(if (selected) c.primary else c.surface)
            .clickable(onClick = onClick).padding(horizontal = 14.dp, vertical = 8.dp),
    ) { Text(label, color = if (selected) c.onPrimary else c.onSurface, fontSize = 14.sp) }
}

// ---------------- статистика ----------------
@Composable
fun StatsScreen(state: AppState) {
    val c = MaterialTheme.colorScheme
    val stats = remember(state.version, state.typedToday) { state.liveStats() }
    val today = LocalDate.now()
    val streak = remember(stats) { state.streak() }
    val phone = remember(state.version) { state.book?.phoneStats() ?: emptyMap() }
    val goal = state.prefs.goal
    val last = (13 downTo 0).map { today.minusDays(it.toLong()) }
    val values = last.map { stats[it.toString()] ?: 0 }
    val top = maxOf(goal, values.maxOrNull() ?: 0, 1)
    val week = values.takeLast(7).sum()
    val month = (0 until 30).sumOf { stats[today.minusDays(it.toLong()).toString()] ?: 0 }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        Bar("Статистика", onBack = { state.back() })
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Сегодня ${words(state.typedToday)}", color = c.onBackground, fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
            Text("из них на телефоне ${words(maxOf(0, state.counter?.words ?: 0))}", color = c.onSurfaceVariant, fontSize = 14.sp)
            if (goal > 0) GoalBar(state.typedToday / goal.toFloat(), Modifier.fillMaxWidth().padding(vertical = 6.dp))
            Text(if (streak > 0) "Серия: ${days(streak)} подряд" else "Серии пока нет - день засчитывается от 250 слов",
                color = c.primary, fontSize = 16.sp)
            Text("За неделю ${words(week)}, за 30 дней ${words(month)}", color = c.onBackground, fontSize = 15.sp)
            Spacer(Modifier.height(16.dp))
            Text("Последние две недели", color = c.onSurfaceVariant, fontSize = 13.sp)
            Row(Modifier.fillMaxWidth().height(140.dp), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                last.forEachIndexed { i, day ->
                    val v = values[i]
                    val wrote = v >= 250
                    Box(Modifier.weight(1f).fillMaxHeight(), contentAlignment = Alignment.BottomCenter) {
                        Box(
                            Modifier.fillMaxWidth().fillMaxHeight((v / top.toFloat()).coerceIn(0.02f, 1f))
                                .clip(RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp))
                                .background(if (day == today) c.primary else if (wrote) c.secondary else c.outline),
                        )
                    }
                }
            }
            Row(Modifier.fillMaxWidth()) {
                Text(last.first().let { "%02d.%02d".format(it.dayOfMonth, it.monthValue) }, color = c.onSurfaceVariant, fontSize = 11.sp, modifier = Modifier.weight(1f))
                Text("сегодня", color = c.onSurfaceVariant, fontSize = 11.sp)
            }
            Spacer(Modifier.height(16.dp))
            Text("Слова с телефона пишутся в .stungkir/stats-phone.json и складываются с компьютерными: " +
                "блокнот на компьютере тоже видит их в серии и в «сегодня».",
                color = c.onSurfaceVariant, fontSize = 12.sp)
            if (phone.isEmpty()) Text("На телефоне пока ничего не написано.", color = c.onSurfaceVariant, fontSize = 12.sp)
        }
    }
}

// ---------------- настройки ----------------
@Composable
fun SettingsScreen(state: AppState) {
    val c = MaterialTheme.colorScheme
    val prefs = state.prefs
    var goalText by remember { mutableStateOf(prefs.goal.toString()) }
    var size by remember { mutableStateOf(prefs.fontSize.toFloat()) }
    var spacing by remember { mutableStateOf(prefs.lineSpacing) }
    var font by remember { mutableStateOf(prefs.font) }
    var punct by remember { mutableStateOf(prefs.punctuation) }
    var repeats by remember { mutableStateOf(prefs.repeats) }
    var awake by remember { mutableStateOf(prefs.keepScreenOn) }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        Bar("Настройки", onBack = { state.back() })
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Section("Цель на день")
            OutlinedTextField(
                value = goalText,
                onValueChange = { t ->
                    goalText = t.filter { it.isDigit() }.take(6)
                    prefs.goal = goalText.toIntOrNull() ?: 0
                    state.version++
                },
                singleLine = true, label = { Text("слов (0 - без цели)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            )

            Section("Текст")
            Text("Размер: ${size.toInt()}", color = c.onBackground)
            Slider(value = size, onValueChange = { size = it; prefs.fontSize = it.toInt(); state.version++ }, valueRange = 12f..30f, steps = 17)
            Text("Межстрочный: ${"%.2f".format(spacing)}", color = c.onBackground)
            Slider(value = spacing, onValueChange = { spacing = it; prefs.lineSpacing = it; state.version++ }, valueRange = 1.0f..2.0f)
            for (name in Prefs.FONTS) {
                Row(Modifier.fillMaxWidth().clickable { font = name; prefs.font = name; state.version++ }, verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(selected = font == name, onClick = { font = name; prefs.font = name; state.version++ })
                    Text(name, color = c.onBackground)
                }
            }
            Toggle("Подсвечивать знаки препинания", punct) { punct = it; prefs.punctuation = it; state.version++ }
            Toggle("Подсвечивать повторы слов рядом", repeats) { repeats = it; prefs.repeats = it; state.version++ }
            Toggle("Не гасить экран в главе", awake) { awake = it; prefs.keepScreenOn = it; state.version++ }

            Section("Тема")
            for (p in Themes.ALL) {
                Row(
                    Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).clickable { state.palette = p; prefs.theme = p.name }
                        .background(if (state.palette.name == p.name) c.surface else c.background).padding(10.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(Modifier.size(34.dp).clip(RoundedCornerShape(8.dp)).background(color(p.bg)).border(1.dp, color(p.border), RoundedCornerShape(8.dp)),
                        contentAlignment = Alignment.Center) {
                        Text("Аа", color = color(p.text), fontSize = 13.sp)
                    }
                    Spacer(Modifier.width(8.dp))
                    Box(Modifier.size(14.dp).clip(RoundedCornerShape(7.dp)).background(color(p.dialogue)))
                    Spacer(Modifier.width(4.dp))
                    Box(Modifier.size(14.dp).clip(RoundedCornerShape(7.dp)).background(color(p.important)))
                    Spacer(Modifier.width(12.dp))
                    Text(p.name, color = c.onBackground, fontSize = 16.sp)
                }
            }

            Section("Папка")
            Text(state.book?.root?.absolutePath ?: "не выбрана", color = c.onSurfaceVariant, fontSize = 13.sp)
            OutlinedButton(onClick = { state.open(Screen.Folder) }) { Text("Выбрать другую папку") }

            Section("О программе")
            Text("StungKir для Android ${BuildConfig.VERSION_NAME}. Писательский блокнот KiriFesTung, лицензия GNU GPL 3. " +
                "Ничего не отправляет в интернет: тексты лежат в папке, а между устройствами их возит Syncthing.",
                color = c.onSurfaceVariant, fontSize = 13.sp)
        }
    }
}

@Composable
private fun Section(title: String) {
    Spacer(Modifier.height(8.dp))
    Text(title, color = MaterialTheme.colorScheme.primary, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
    HorizontalDivider(color = MaterialTheme.colorScheme.outline)
}

@Composable
private fun Toggle(label: String, value: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().clickable { onChange(!value) }.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = MaterialTheme.colorScheme.onBackground, modifier = Modifier.weight(1f))
        Switch(checked = value, onCheckedChange = onChange)
    }
}

// ---------------- папка с текстами ----------------
/** Где обычно лежит папка, которую возит Syncthing. Ищем папку StungKir или папку со служебной .stungkir. */
fun findFolders(): List<File> {
    val home = Environment.getExternalStorageDirectory()
    val found = LinkedHashSet<File>()
    fun looks(f: File) = f.isDirectory && (File(f, ".stungkir").isDirectory || File(f, ".order").isFile && f.name.equals("StungKir", true))
    fun scan(dir: File, depth: Int) {
        val children = dir.listFiles()?.filter { it.isDirectory } ?: return
        for (child in children) {
            if (child.name.equals("Android", true) && depth == 0) continue
            if (looks(child) || child.name.equals("StungKir", ignoreCase = true)) found.add(child)
            if (depth < 2 && !child.name.startsWith(".")) scan(child, depth + 1)
        }
    }
    try {
        scan(home, 0)
    } catch (e: Exception) {
        // нет доступа - вернём, что успели
    }
    return found.sortedByDescending { looks(it) }
}

@Composable
fun FolderScreen(state: AppState, canGoBack: Boolean) {
    val c = MaterialTheme.colorScheme
    val home = remember { Environment.getExternalStorageDirectory() }
    var browsing by remember { mutableStateOf<File?>(null) }
    val found by produceState(initialValue = emptyList<File>()) { value = withContext(Dispatchers.IO) { findFolders() } }
    var creating by remember { mutableStateOf(false) }

    val dir = browsing
    if (dir != null) {
        val children = remember(dir) { dir.listFiles()?.filter { it.isDirectory && !it.name.startsWith(".") }?.sortedBy { it.name.lowercase() } ?: emptyList() }
        Column(Modifier.fillMaxSize()) {
            Bar(dir.name.ifEmpty { "Память телефона" }, subtitle = dir.absolutePath, onBack = {
                browsing = if (dir == home) null else dir.parentFile
            })
            Button(onClick = { state.useFolder(dir) }, modifier = Modifier.fillMaxWidth().padding(12.dp)) { Text("Выбрать эту папку") }
            LazyColumn(Modifier.fillMaxSize()) {
                items(children, key = { it.absolutePath }) { child ->
                    Text(child.name, color = c.onBackground, fontSize = 16.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.fillMaxWidth().clickable { browsing = child }.padding(horizontal = 16.dp, vertical = 14.dp))
                }
            }
        }
        return
    }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
        val goBack: (() -> Unit)? = if (canGoBack) fun() { state.back() } else null
        Bar("Папка с текстами", onBack = goBack)
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(
                "Выбери папку StungKir, которую Syncthing синхронизирует с компьютером. " +
                    "Приложение работает прямо с файлами в ней: что напишешь тут - появится на компьютере, и наоборот.",
                color = c.onBackground, fontSize = 15.sp,
            )
            if (found.isNotEmpty()) {
                Text("Нашлось:", color = c.onSurfaceVariant, fontSize = 13.sp)
                for (f in found) {
                    Column(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(c.surface)
                            .clickable { state.useFolder(f) }.padding(14.dp),
                    ) {
                        Text(f.name, color = c.onSurface, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                        Text(f.absolutePath, color = c.onSurfaceVariant, fontSize = 12.sp)
                    }
                }
            } else {
                Text("Готовой папки не нашлось. Если Syncthing ещё не настроен - сначала добавь в нём папку StungKir с компьютера.",
                    color = c.onSurfaceVariant, fontSize = 13.sp)
            }
            OutlinedButton(onClick = { browsing = home }, modifier = Modifier.fillMaxWidth()) { Text("Найти папку вручную") }
            OutlinedButton(onClick = { creating = true }, modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.outlinedButtonColors()) { Text("Создать новую папку StungKir") }
        }
    }
    if (creating) {
        AlertDialog(
            onDismissRequest = { creating = false },
            title = { Text("Новая папка") },
            text = { Text("Создать ${File(home, "StungKir").absolutePath}? Потом её можно добавить в Syncthing.") },
            confirmButton = {
                TextButton(onClick = {
                    val f = File(home, "StungKir")
                    f.mkdirs()
                    creating = false
                    if (f.isDirectory) state.useFolder(f)
                }) { Text("Создать") }
            },
            dismissButton = { TextButton(onClick = { creating = false }) { Text("Отмена") } },
        )
    }
}

// ---------------- доступ к файлам ----------------
@Composable
fun AccessScreen(onAsk: () -> Unit) {
    val c = MaterialTheme.colorScheme
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Нужен доступ к файлам", color = c.onBackground, fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(12.dp))
        Text(
            "StungKir пишет прямо в папку, которую синхронизирует Syncthing - как блокнот на компьютере. " +
                "Для этого Android просит разрешить «Доступ ко всем файлам». Приложение ничего не отправляет в интернет " +
                "и трогает только выбранную папку с текстами.",
            color = c.onBackground, fontSize = 15.sp,
        )
        Spacer(Modifier.height(20.dp))
        Button(onClick = onAsk, modifier = Modifier.fillMaxWidth()) { Text("Разрешить") }
        Spacer(Modifier.height(8.dp))
        Text("Откроются настройки: включи переключатель у StungKir и вернись назад.", color = c.onSurfaceVariant, fontSize = 13.sp)
    }
}
