# Сборка StungKir для Windows: pyinstaller packaging/windows/stungkir.spec
# Запускать из корня проекта (там, где pyproject.toml). Получится папка dist/StungKir с StungKir.exe.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).resolve().parent.parent
PACKAGING = ROOT / "packaging"

datas = [
    (str(PACKAGING / "fonts" / "*.ttf"), "stungkir/fonts"),
    (str(PACKAGING / "fonts" / "LICENSE-DejaVu.txt"), "stungkir/fonts"),
    (str(ROOT / "stungkir" / "fonts" / "*.ttf"), "stungkir/fonts"),       # Literata и PT Serif для текста
    (str(ROOT / "stungkir" / "fonts" / "OFL-*.txt"), "stungkir/fonts"),
    (str(ROOT / "stungkir" / "sounds" / "*.wav"), "stungkir/sounds"),          # стук кубиков и звон монетки
    (str(ROOT / "stungkir" / "art" / "*.png"), "stungkir/art"),                # ласка, стороны монетки
    (str(ROOT / "stungkir" / "art" / "icons" / "*.png"), "stungkir/art/icons"),  # нарисованные значки
    (str(ROOT / "stungkir" / "art" / "paper" / "*.png"), "stungkir/art/paper"),  # фактуры бумаги
    (str(ROOT / "stungkir" / "art" / "dice" / "bone" / "*.png"), "stungkir/art/dice/bone"),
    (str(ROOT / "stungkir" / "art" / "dice" / "metal" / "*.png"), "stungkir/art/dice/metal"),
    (str(ROOT / "stungkir" / "art" / "dice" / "oak" / "*.png"), "stungkir/art/dice/oak"),
    (str(ROOT / "stungkir" / "art" / "dice" / "resin" / "*.png"), "stungkir/art/dice/resin"),
    (str(PACKAGING / "dictionaries" / "ru_RU.dic"), "stungkir/dictionaries"),
    (str(PACKAGING / "dictionaries" / "ru_RU.aff"), "stungkir/dictionaries"),
    (str(PACKAGING / "dictionaries" / "LICENSE-ru_RU.txt"), "stungkir/dictionaries"),
    (str(ROOT / "LICENSE"), "."),
]
# кадры анимаций: каждая - своя папка в art/anim (ласка, огонёк, праздник цели, брызги ...)
for folder in sorted((ROOT / "stungkir" / "art" / "anim").iterdir()):
    if folder.is_dir():
        datas.append((str(folder / "*.png"), f"stungkir/art/anim/{folder.name}"))
# шаблоны Word (колонтитулы, стили) лежат внутри python-docx файлами - без них сборка в .docx падает
datas += collect_data_files("docx", include_py_files=True)   # и .py: шаблоны ищутся через docx/parts/../templates

# список тестов берём из stungkir/tests/run.py, чтобы новые тесты не забывались в сборке
import ast
_run = (ROOT / "stungkir" / "tests" / "run.py").read_text(encoding="utf-8")
_modules = next(node.value for node in ast.parse(_run).body
                if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "MODULES")
TEST_MODULES = [f"stungkir.tests.{name}" for name in ast.literal_eval(_modules)]

a = Analysis(
    [str(ROOT / "stungkir" / "__main__.py")],
    pathex=[str(ROOT)],
    datas=datas,
    # тесты тоже внутри: «StungKir.exe --test» проверит, что сборка рабочая
    hiddenimports=["PySide6.QtTextToSpeech",          # чтение вслух: голос Windows через Qt
                   "stungkir.tests", "stungkir.tests.run", "stungkir.tests.helpers",
                   *TEST_MODULES, "spylls.hunspell", "docx", "cryptography"],
    excludes=["enchant", "tkinter"],      # на Windows орфография через spylls и встроенный словарь
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="StungKir",
    icon=str(PACKAGING / "windows" / "stungkir.ico"),
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="StungKir")
