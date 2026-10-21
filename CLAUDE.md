# Заметки для Claude (как работать с этим проектом)

StungKir - писательский блокнот KiriFesTung: PySide6 (Linux, Windows) + приложение для Android (Kotlin, Compose, папка `android/`). GPL-3.0-or-later, Claude указан в AUTHORS.md.

## Правила
- Отвечать по-русски, просто и прямо.
- Длинное тире «—» только в начале реплики (строки); внутри текста - короткое «-». Касается и текстов интерфейса, и документации.
- Никаких имён из мира автора в программе, примерах и тестах. Только нейтральные: Тервена, Давнь, Кев, Лосс, Ния, Кира, Мира.
- Шрифт текста по умолчанию - обычной насыщенности.
- Не писать в репозиторий личные данные автора (почту, настоящее имя, адрес).

## Проверки
- Вся программа: `QT_QPA_PLATFORM=offscreen python3 -m stungkir --test` (больше 330 проверок). Новый модуль проверок - добавить в `stungkir/tests/run.py` (MODULES).
- Обязательно и на PySide 6.8 (на нём Flatpak): `pip install "PySide6==6.8.2.1"` в отдельном venv и тот же запуск. На 6.8 у списков `widget.update()` - это `update(index)`, нужен `QWidget.update(widget)`.
- Роботы: `MONKEY_STEPS=2500 MONKEY_SEED=N python3 -m unittest stungkir.tests.test_monkey`, `FUZZ_STEPS/FUZZ_SEED` для test_fuzz.
- Android, логика без Android SDK: `android/app/src/main/java/.../logic/*.kt` и проверки в `android/app/src/test`. Полная сборка - только в GitHub Actions (`.github/workflows/android.yml`).
- Тексты в проверках писать с `encoding="utf-8", newline="\n"` (иначе на Windows cp1252 и `\r\n`).
- `ruff check stungkir` должен быть чистым.

## Сборки (GitHub Actions)
- `check.yml`: проверки на Linux (PySide 6.8 и новый), на Windows - сборка, проверка готовой сборки, установщик и переносная версия; кладёт их в релиз `windows-latest`.
- `android.yml`: проверки и APK, релиз `android-latest`. Подпись: `android/app/stungkir-release.keystore`, пароль - секрет `ANDROID_KEYSTORE_PASSWORD` (есть только у автора). Без секрета APK в релиз не выкладывается.
- `build.yml`: Flatpak (KDE 6.8), сам при изменениях программы и по кнопке; релиз `linux-latest`.
- Журналы Actions из сессии Claude не скачиваются: ошибки шагов выводятся заметками (`::error::`), их видно через API check-runs/annotations.
- `packaging/windows/build-windows.ps1` - в UTF-8 с BOM (иначе PowerShell 5 ломает русский текст).

## Устройство (коротко)
- Тексты: `~/StungKir/<категория>/<глава>.txt`, порядок - `.order` (JSON-список), служебное - `~/StungKir/.stungkir/` (версии `versions/<категория>/<файл>/<время>.txt`, до 50; `stats.json` компьютера, `stats-phone.json` телефона - складываются; `days.json`, `names.json`).
- Зашифрованный файл начинается с `STUNGKIR-ENC1\n` (scrypt + Fernet). Телефон пароль пока не умеет.
- Переносная версия: `portable.txt` рядом с `StungKir.exe` - тексты, данные и настройки рядом с программой.
- Картинки кубиков автора: `stungkir/art/dice/<материал>/d<N>.png` (bone, metal, oak, resin = «Индиго»).
