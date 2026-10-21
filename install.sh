#!/usr/bin/env bash
# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
# Установка StungKir в отдельную папку со своими библиотеками,
# чтобы обновления Debian Sid его не ломали.
# Запуск: распакуй архив и в этой папке выполни  bash install.sh
set -e

APP_DIR="$HOME/.local/share/stungkir"
BIN="$HOME/.local/bin/stungkir"
HERE="$(cd "$(dirname "$0")" && pwd)"
PACKAGES=("PySide6>=6.8,<7" "pyenchant>=3.2" "cryptography>=42" "python-docx>=1.1")
PACKAGES_QUOTED='"PySide6>=6.8,<7" "pyenchant>=3.2" "cryptography>=42" "python-docx>=1.1"'

if [ ! -f "$HERE/stungkir/__main__.py" ]; then
    echo "Не нашёл папку stungkir рядом со скриптом. Распакуй архив целиком."
    exit 1
fi

echo "1/5  Системные пакеты (попросит пароль от sudo)…"
sudo apt install -y python3 python3-venv libenchant-2-2 hunspell-ru fonts-dejavu-core libxcb-cursor0

# голос для чтения вслух (F5): если пакетов нет в системе, без него всё остальное работает
sudo apt install -y speech-dispatcher speech-dispatcher-rhvoice rhvoice rhvoice-russian libspeechd2 \
    || echo "     Голос для чтения вслух не поставился - всё остальное работает и без него."

echo "2/5  Копирую программу…"
mkdir -p "$APP_DIR" "$HOME/.local/bin"
rm -rf "$APP_DIR/app.new"
mkdir -p "$APP_DIR/app.new"
cp -r "$HERE/stungkir" "$APP_DIR/app.new/stungkir"
find "$APP_DIR/app.new" -name __pycache__ -prune -exec rm -rf {} +
# новая версия встаёт целиком, заодно уходит старая однофайловая stungkir.py
rm -rf "$APP_DIR/app"
mv "$APP_DIR/app.new" "$APP_DIR/app"

echo "3/5  Ставлю библиотеки в отдельное окружение (пару минут)…"
rm -rf "$APP_DIR/venv"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q "${PACKAGES[@]}"

echo "4/5  Ярлык в меню приложений…"
cat > "$BIN" <<EOF
#!/usr/bin/env bash
# Запуск StungKir. Если обновление системы сломало окружение, оно пересоберётся само.
# stungkir --test  проверяет, что всё работает.
APP_DIR="\$HOME/.local/share/stungkir"
PY="\$APP_DIR/venv/bin/python"
if ! "\$PY" -c "import PySide6.QtWidgets, PySide6.QtPrintSupport, enchant, cryptography, docx" >/dev/null 2>&1; then
    notify-send "StungKir" "Обновляю библиотеки после обновления системы…" 2>/dev/null || true
    rm -rf "\$APP_DIR/venv"
    if ! { python3 -m venv "\$APP_DIR/venv" && "\$APP_DIR/venv/bin/pip" install -q $PACKAGES_QUOTED; }; then
        notify-send "StungKir" "Не получилось пересобрать. Запусти install.sh ещё раз." 2>/dev/null || true
        exit 1
    fi
fi
exec "\$PY" "\$APP_DIR/app/stungkir/__main__.py" "\$@"
EOF
chmod +x "$BIN"
"$APP_DIR/venv/bin/python" "$APP_DIR/app/stungkir/__main__.py" --install-only

echo "5/5  Проверяю, что всё работает (меньше минуты)…"
REPORT="$APP_DIR/test-report.txt"
if QT_QPA_PLATFORM=offscreen "$APP_DIR/venv/bin/python" "$APP_DIR/app/stungkir/__main__.py" --test >"$REPORT" 2>&1; then
    echo "     $(tail -1 "$REPORT")"
else
    echo "     Не все проверки прошли. Программа установлена, но пришли мне файл:"
    echo "     $REPORT"
fi

BUILD=$(grep -o '^BUILD = "[^"]*"' "$APP_DIR/app/stungkir/__init__.py" | cut -d'"' -f2)
echo
echo "Готово. Установлена сборка $BUILD - она же видна в «Ещё → О программе»."
echo "StungKir в меню приложений. Если он был открыт - закрой и запусти заново."
echo "Тексты лежат в ~/StungKir, резервные копии в ~/.local/share/stungkir/backups"
