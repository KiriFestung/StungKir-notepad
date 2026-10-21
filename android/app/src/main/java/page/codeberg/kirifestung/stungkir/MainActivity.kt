// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.core.view.WindowCompat
import page.codeberg.kirifestung.stungkir.ui.AccessScreen
import page.codeberg.kirifestung.stungkir.ui.AppState
import page.codeberg.kirifestung.stungkir.ui.CategoryScreen
import page.codeberg.kirifestung.stungkir.ui.ConflictScreen
import page.codeberg.kirifestung.stungkir.ui.EditorScreen
import page.codeberg.kirifestung.stungkir.ui.FolderScreen
import page.codeberg.kirifestung.stungkir.ui.LibraryScreen
import page.codeberg.kirifestung.stungkir.ui.Prefs
import page.codeberg.kirifestung.stungkir.ui.Screen
import page.codeberg.kirifestung.stungkir.ui.SettingsScreen
import page.codeberg.kirifestung.stungkir.ui.StatsScreen
import page.codeberg.kirifestung.stungkir.ui.StungTheme
import page.codeberg.kirifestung.stungkir.ui.VersionsScreen
import page.codeberg.kirifestung.stungkir.ui.color

class MainActivity : ComponentActivity() {
    private val access = mutableStateOf(false)
    private lateinit var state: AppState

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        access.value = hasAccess()
        state = AppState(Prefs(this))
        setContent {
            val p = state.palette
            val view = window.decorView
            SideEffect {
                val controller = WindowCompat.getInsetsController(window, view)
                controller.isAppearanceLightStatusBars = p.light
                controller.isAppearanceLightNavigationBars = p.light
            }
            StungTheme(p) {
                Box(Modifier.fillMaxSize().background(color(p.bg)).systemBarsPadding().imePadding()) {
                    App()
                }
            }
        }
    }

    @androidx.compose.runtime.Composable
    private fun App() {
        if (!access.value) {
            AccessScreen(onAsk = ::askAccess)
            return
        }
        val book = state.book
        if (book == null || !book.root.isDirectory) {
            FolderScreen(state, canGoBack = false)
            return
        }
        val screen = state.screen
        BackHandler(enabled = state.stack.size > 1) { state.back() }
        when (screen) {
            Screen.Library -> LibraryScreen(state)
            is Screen.Category -> CategoryScreen(state, screen.folder)
            is Screen.Editor -> EditorScreen(state, screen.file)
            is Screen.Versions -> VersionsScreen(state, screen.file)
            is Screen.Conflict -> ConflictScreen(state, screen.file)
            Screen.Stats -> StatsScreen(state)
            Screen.Settings -> SettingsScreen(state)
            Screen.Folder -> FolderScreen(state, canGoBack = true)
        }
    }

    override fun onResume() {
        super.onResume()
        access.value = hasAccess()
        if (::state.isInitialized) {
            if (access.value) state.restore()
            state.reloadStats()
        }
    }

    override fun onPause() {
        if (::state.isInitialized) state.pause()
        super.onPause()
    }

    private fun hasAccess(): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Environment.isExternalStorageManager()
        } else {
            checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED
        }

    private fun askAccess() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                startActivity(Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName")))
            } catch (e: Exception) {
                startActivity(Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION))
            }
        } else {
            requestPermissions(arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE, Manifest.permission.WRITE_EXTERNAL_STORAGE), 1)
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        access.value = hasAccess()
    }
}
