# Сборка StungKir для Windows: готовая папка, проверка тестами и установщик.
# Нужно один раз поставить: Python 3.12 с python.org (галочка «Add to PATH») и Inno Setup 6.
# Запуск из любой папки:  powershell -ExecutionPolicy Bypass -File packaging\windows\build-windows.ps1
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

Write-Host "1/4  Окружение для сборки…"
py -3.12 -m venv .venv-build
$Py = Join-Path $Root ".venv-build\Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install "PySide6>=6.8,<7" "cryptography>=42" "python-docx>=1.1" "spylls>=0.1.7" "pyinstaller>=6.5"

Write-Host "2/4  Сборка программы…"
& $Py -m PyInstaller --noconfirm packaging\windows\stungkir.spec

Write-Host "3/4  Проверка готовой сборки тестами…"
$env:QT_QPA_PLATFORM = "offscreen"
$Report = Join-Path $env:TEMP "stungkir-test-report.txt"
$Run = Start-Process -FilePath "dist\StungKir\StungKir.exe" -ArgumentList "--test" -Wait -PassThru
Get-Content $Report -Tail 5
if ($Run.ExitCode -ne 0) { throw "Тесты не прошли, установщик не собран. Полный отчёт: $Report" }

Write-Host "4/4  Установщик…"
$Iscc = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
& $Iscc packaging\windows\installer.iss
Write-Host "Готово: dist\StungKir-Setup-1.0.0.exe"
