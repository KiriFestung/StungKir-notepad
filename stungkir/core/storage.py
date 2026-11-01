# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Файлы на диске: надёжная запись, кодировки, шифрование, порядок, версии, заметки, резервные копии."""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import date, datetime
from pathlib import Path

from . import config as C
from ..ui.icons import ICON_SVG


MAIN_FILE = Path(__file__).resolve().parents[1] / "__main__.py"   # им запускается пакет напрямую
CRYPTO = None   # объект шифрования, если стоит пароль и он введён


def next_chapter_name(folder):
    """«Глава N»: следующий номер после самого большого в категории."""
    import re
    numbers = [int(m.group(1)) for f in (folder.iterdir() if folder.is_dir() else [])
               for m in [re.fullmatch(r"Глава (\d+)", f.stem)] if m]
    return f"Глава {max(numbers, default=0) + 1}"


WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def bad_name_reason(name):
    """Почему такое название не годится для файла или папки (на Linux, Windows и телефоне). None - годится."""
    import unicodedata
    if len(name.encode("utf-8")) > 200:
        return "Слишком длинное название: можно примерно до 100 русских букв."
    if any(unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp") for ch in name):
        return "В названии есть невидимые или служебные знаки (перевод строки, табуляция и подобные)."
    bad = sorted({ch for ch in name if ch in '/\\:*?"<>|'})
    if bad:
        return f"В названии нельзя: {' '.join(bad)}"
    if name in (".", "..") or name.startswith(".") or name.endswith((" ", ".")):
        return "Название не может начинаться с точки и кончаться точкой или пробелом."
    if name.split(".")[0].strip().lower() in WINDOWS_RESERVED:
        return "Такое название занято Windows (CON, NUL, COM1 и подобные) - файл не откроется на Windows."
    return None


def name_clash(target, source=None):
    """Есть ли рядом файл или папка с таким же именем без учёта регистра («Глава» и «глава»):
    на Windows и телефоне это одно и то же имя. source - что переименовываем (с ним не сравниваем)."""
    folder = target.parent
    try:
        for other in folder.iterdir():
            if other.name.casefold() == target.name.casefold() and other != source:
                return other
    except OSError:
        return None
    return None


def unique_path(path):
    """Свободное имя рядом: занято - «имя (2)», «имя (3)»… Занятым считается и то же имя в другом
    регистре («Глава» и «глава»): на Windows и телефоне это один файл, и синхронизация их бы спутала."""
    def taken(candidate):
        return candidate.exists() or name_clash(candidate) is not None
    if not taken(path):
        return path
    i = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not taken(candidate):
            return candidate
        i += 1


# ---------------- чтение, запись, шифрование ----------------
class LockedFile(Exception):
    """Файл зашифрован, а пароль не введён или не подходит."""


_CURRENT = object()   # «использовать текущий ключ программы»


_problem_hook = None     # главное окно подставляет сюда показ сообщения
_pending_problems = []   # что случилось до того, как окно появилось


def log_error(context, error=None):
    try:
        C.ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        if C.ERROR_LOG.exists() and C.ERROR_LOG.stat().st_size > 300_000:
            C.ERROR_LOG.write_text(C.ERROR_LOG.read_text(encoding="utf-8")[-100_000:], encoding="utf-8")
        with open(C.ERROR_LOG, "a", encoding="utf-8") as handle:
            detail = f": {error!r}" if error is not None else ""
            handle.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {context}{detail}\n")
    except OSError:
        pass   # если не пишется даже журнал, сообщение всё равно покажется на экране


def report_problem(text, error=None):
    """Записывает ошибку в журнал и показывает короткое сообщение, а не молчит."""
    log_error(text, error)
    if _problem_hook is not None:
        _problem_hook(text)
    else:
        _pending_problems.append(text)


def os_message(error):
    """Понятное объяснение ошибки файловой системы."""
    import errno
    known = {errno.ENAMETOOLONG: "Слишком длинное название.",
             errno.EEXIST: "Такое название уже занято.",
             errno.EACCES: "Нет доступа к файлу или папке.",
             errno.EPERM: "Нет доступа к файлу или папке.",
             errno.ENOSPC: "На диске закончилось место.",
             errno.EROFS: "Диск доступен только для чтения.",
             errno.EINVAL: "В названии есть недопустимые символы."}
    return known.get(getattr(error, "errno", None), f"Ошибка системы: {error.strerror or error}")


def read_text(path, crypto=_CURRENT):
    crypto = CRYPTO if crypto is _CURRENT else crypto
    data = path.read_bytes()
    if data.startswith(C.MAGIC):
        if crypto is None:
            raise LockedFile(path)
        try:
            data = crypto.decrypt(data[len(C.MAGIC):])
        except Exception as error:
            raise LockedFile(path) from error
    return decode_text(data)[0]


def read_text_info(path, crypto=_CURRENT):
    """Как read_text, но ещё говорит, в какой кодировке был файл и всё ли распозналось."""
    crypto = CRYPTO if crypto is _CURRENT else crypto
    data = path.read_bytes()
    if data.startswith(C.MAGIC):
        if crypto is None:
            raise LockedFile(path)
        try:
            data = crypto.decrypt(data[len(C.MAGIC):])
        except Exception as error:
            raise LockedFile(path) from error
    return decode_text(data)


def _cyrillic_score(text):
    # в правильно прочитанном русском тексте строчных букв гораздо больше, чем заглавных
    lower = sum(1 for ch in text if "а" <= ch <= "я" or ch == "ё")
    upper = sum(1 for ch in text if "А" <= ch <= "Я" or ch == "Ё")
    return lower - upper


def _printable_share(text):
    if not text:
        return 1.0
    good = sum(1 for ch in text if ch.isprintable() or ch in "\n\r\t")
    return good / len(text)


def decode_text(data):
    """Байты -> (текст, кодировка, были ли нераспознанные символы).
    Понимает UTF-8, UTF-16 (с меткой и без), Windows-1251 и KOI8-R."""
    if data.startswith(b"\xef\xbb\xbf"):
        try:
            return data[3:].decode("utf-8"), "UTF-8", False
        except UnicodeDecodeError:
            return data[3:].decode("utf-8", errors="replace"), "UTF-8", True
    for bom, encoding in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")):
        if data.startswith(bom):
            try:
                return data[2:].decode(encoding), "UTF-16", False
            except UnicodeDecodeError:
                return data[2:].decode(encoding, errors="replace"), "UTF-16", True
    if len(data) >= 4 and data.count(b"\x00") > len(data) // 4:   # UTF-16 без метки
        for encoding in ("utf-16-le", "utf-16-be"):
            try:
                text = data.decode(encoding)
            except UnicodeDecodeError:
                continue
            if _printable_share(text) > 0.95:
                return text, "UTF-16", False
    try:
        text = data.decode("utf-8")
        # настоящие многобайтовые последовательности UTF-8 случайно не складываются,
        # поэтому пара невидимых символов из Word не должна сбивать определение
        if not text.isascii() or _printable_share(text) > 0.97:
            return text, "UTF-8", False
    except UnicodeDecodeError:
        pass
    # русский UTF-16 без метки: нулевых байтов нет, зато как UTF-8 он даёт сплошные служебные символы
    if len(data) >= 4 and len(data) % 2 == 0:
        options = []
        for encoding in ("utf-16-le", "utf-16-be"):
            try:
                text = data.decode(encoding)
            except UnicodeDecodeError:
                continue
            if _printable_share(text) > 0.95:
                options.append((_cyrillic_score(text), text))
        if options:
            return max(options, key=lambda o: o[0])[1], "UTF-16", False
    candidates = []
    for encoding, label in (("cp1251", "Windows-1251"), ("koi8-r", "KOI8-R")):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        candidates.append((_cyrillic_score(text), label, text))
    if candidates:
        _score, label, text = max(candidates, key=lambda c: c[0])
        return text, label, False
    return data.decode("utf-8", errors="replace"), "UTF-8", True


def replace_file(source, target, tries=20):
    """os.replace, но на Windows с повтором: пока файл держит открытым другая программа
    (Syncthing, антивирус, проводник) или наш же поток, подмена отказывает «Access is denied»
    на доли секунды. На Linux и в macOS подмена не ждёт никогда."""
    for attempt in range(tries):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if os.name != "nt" or attempt == tries - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


def write_atomic(path, data):
    """Пишет во временный файл, сбрасывает его на диск и только потом подменяет оригинал.
    Если пропадёт питание, останется либо старый файл, либо новый, но не пустой."""
    temp = path.with_name(f".{path.name}.tmp")
    if C.SERVICE_DIR in path.parts and not path.parent.is_dir():
        path.parent.mkdir(parents=True, exist_ok=True)       # служебная папка появляется сама
        hide_service_dir()
    try:
        with open(temp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        replace_file(temp, path)
    except BaseException:
        # не оставляем рядом с главой недописанный временный файл
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    try:
        folder = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(folder)
        finally:
            os.close(folder)
    except OSError:
        pass


def hide_file(path):
    """На Windows точка в начале имени не прячет - ставим атрибут «скрытый». Только папкам:
    скрытый файл Windows не даёт перезаписать обычным способом."""
    if sys.platform.startswith("win") and path.exists():
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x2)
        except (AttributeError, OSError):
            pass


def hide_service_dir():
    hide_file(C.ROOT / C.SERVICE_DIR)


def tidy_root():
    """Переезд служебных файлов из прошлых версий (лежали прямо в StungKir рядом с категориями)
    в одну скрытую папку .stungkir. Перед переездом - резервная копия всей папки. Если файл уже есть
    на новом месте (например, синхронизация принесла старый с другого устройства), ничего не
    затирается: у папок переезжает то, чего на новом месте нет; у файлов остаётся более свежий,
    а другой кладётся в .stungkir/переезд. Возвращает список того, что переехало."""
    legacy = [name for name in C.LEGACY_NAMES if (C.ROOT / name).exists()]
    if not legacy:
        return []
    make_backup()
    service = C.ROOT / C.SERVICE_DIR
    service.mkdir(parents=True, exist_ok=True)
    hide_service_dir()
    aside = service / "переезд"
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    moved = []

    def keep_aside(path, relative):
        target = aside / stamp / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(path, target)

    for name in legacy:
        old, new = C.ROOT / name, C.service_path(name)
        try:
            if not new.exists():
                os.replace(old, new)
            elif old.is_dir():
                for item in sorted(old.rglob("*")):
                    if not item.is_file():
                        continue
                    relative = item.relative_to(old)
                    target = new / relative
                    if not target.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(item, target)
                    elif target.read_bytes() == item.read_bytes():
                        item.unlink()
                    else:
                        keep_aside(item, Path(name) / relative)
                shutil.rmtree(old, ignore_errors=True)
            else:
                if old.read_bytes() == new.read_bytes():
                    old.unlink()
                elif old.stat().st_mtime > new.stat().st_mtime:
                    keep_aside(new, name)
                    os.replace(old, new)
                else:
                    keep_aside(old, name)
            moved.append(name)
        except OSError as error:
            report_problem(f"Служебный файл {name} не переехал в {C.SERVICE_DIR}, остался на месте", error)
    return moved


def save_text(path, text, crypto=_CURRENT):
    crypto = CRYPTO if crypto is _CURRENT else crypto
    data = text.encode("utf-8")
    if crypto is not None:
        data = C.MAGIC + crypto.encrypt(data)
    write_atomic(path, data)


def is_encrypted(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(len(C.MAGIC)) == C.MAGIC
    except OSError:
        return False


def shred(path):
    """Затирает файл нулями и удаляет. На SSD это не даёт полной гарантии, но лучше простого удаления."""
    try:
        size = path.stat().st_size
        with open(path, "r+b") as handle:
            chunk = b"\0" * (1 << 20)
            left = size
            while left > 0:
                handle.write(chunk[:min(left, len(chunk))])
                left -= len(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        path.unlink()
        return True
    except OSError:
        return False


def crypto_available():
    import importlib.util
    try:
        return importlib.util.find_spec("cryptography.fernet") is not None
    except ImportError:
        return False


def _derive(secret, salt):
    """32 байта ключа из пароля или кода: scrypt, медленно нарочно, чтобы перебор был долгим."""
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(secret.encode("utf-8"))


def make_crypto(password, salt):
    """Ключ старого вида (версия 1): тексты шифруются прямо ключом из пароля."""
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(_derive(password, salt)))


# Как устроен ключ (версия 2). Тексты шифруются одним главным ключом. В .lock.json он лежит
# дважды: запертый паролем и запертый кодом восстановления. Поэтому пароль можно сменить или
# восстановить по коду, не перешифровывая тексты. У тех, кто ставил пароль в версии 1,
# главный ключ - это прежний ключ из пароля, так что при переходе файлы не трогаются.
RECOVERY_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"     # без 0/O, 1/I/L и U - чтобы не путать на бумаге


def new_recovery_code():
    """Код восстановления: 20 знаков (около 98 бит), группами по 4 - XXXX-XXXX-XXXX-XXXX-XXXX."""
    import secrets
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(20))
    return "-".join(raw[i:i + 4] for i in range(0, 20, 4))


def normalize_code(code):
    """Код как его ни ввели: строчными, без дефисов, с пробелами, русскими буквами-двойниками."""
    lookalikes = str.maketrans("АВЕКМНОРСТХУ", "ABEKMHOPCTXY")
    code = "".join(ch for ch in code.upper().translate(lookalikes) if ch.isalnum())
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


def _wrap(master, secret):
    from cryptography.fernet import Fernet
    salt = os.urandom(16)
    box = Fernet(base64.urlsafe_b64encode(_derive(secret, salt))).encrypt(master)
    return base64.b64encode(salt).decode("ascii"), box.decode("ascii")


def build_lock(master, password, code):
    """Содержимое .lock.json версии 2. master - главный ключ в виде, который понимает Fernet."""
    from cryptography.fernet import Fernet
    salt, key = _wrap(master, password)
    recovery_salt, recovery_key = _wrap(master, normalize_code(code))
    return {"version": 2, "salt": salt, "key": key, "recovery_salt": recovery_salt,
            "recovery_key": recovery_key, "check": Fernet(master).encrypt(C.CHECK_PHRASE).decode("ascii")}


def write_lock(lock):
    write_atomic(lock_path(), json.dumps(lock).encode("utf-8"))


def lock_path():
    return C.service_path(C.LOCK_FILE)


class LockBroken(Exception):
    """Файл ключа есть, но прочитать его нельзя: это не то же самое, что неверный пароль."""


def read_lock():
    """Содержимое .lock.json, проверенное на целость. Бросает LockBroken."""
    try:
        data = json.loads(lock_path().read_text(encoding="utf-8"))
        base64.b64decode(data["salt"], validate=True)
        if not isinstance(data["check"], str):
            raise ValueError("нет проверочной строки")
        if data.get("version", 1) >= 2:
            base64.b64decode(data["recovery_salt"], validate=True)
            for field in ("key", "recovery_key"):
                if not isinstance(data[field], str):
                    raise ValueError(f"нет поля {field}")
        return data
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise LockBroken(str(error)) from error


def lock_version():
    try:
        return read_lock().get("version", 1)
    except LockBroken:
        return None


def master_key(secret, recovery=False):
    """Главный ключ, если пароль (или код при recovery=True) подходит, иначе None.
    Если повреждён сам файл ключа, бросает LockBroken."""
    from cryptography.fernet import Fernet, InvalidToken
    try:
        data = read_lock()
    except LockBroken as error:
        log_error("Файл ключа повреждён", error)
        raise
    version = data.get("version", 1)
    if recovery and version < 2:
        return None                      # в версии 1 кода восстановления ещё не было
    try:
        if version < 2:
            master = base64.urlsafe_b64encode(_derive(secret, base64.b64decode(data["salt"])))
        else:
            prefix = "recovery_" if recovery else ""
            secret = normalize_code(secret) if recovery else secret
            kek = Fernet(base64.urlsafe_b64encode(_derive(secret, base64.b64decode(data[prefix + "salt"]))))
            master = kek.decrypt(data[prefix + "key"].encode("ascii"))
        if Fernet(master).decrypt(data["check"].encode("ascii")) != C.CHECK_PHRASE:
            return None
        return master
    except (InvalidToken, ValueError):
        return None


def check_password(password):
    """Объект шифрования, если пароль подходит; None, если пароль неверный.
    Если повреждён сам файл ключа, бросает LockBroken."""
    from cryptography.fernet import Fernet
    master = master_key(password)
    return Fernet(master) if master is not None else None


def lock_problem():
    """None, если файл ключа в порядке, иначе описание ошибки."""
    try:
        read_lock()
        return None
    except LockBroken as error:
        return error


KEY = None          # главный ключ после входа: нужен, чтобы сменить пароль или код


def _open_with(master):
    global CRYPTO, KEY
    from cryptography.fernet import Fernet
    CRYPTO, KEY = Fernet(master), master


def unlock(password):
    master = master_key(password)
    if master is None:
        return False
    _open_with(master)
    return True


def unlock_recovery(code):
    master = master_key(code, recovery=True)
    if master is None:
        return False
    _open_with(master)
    return True


def rewrap_lock(password=None, code=None):
    """Новый пароль и/или новый код для того же главного ключа (KEY). Тексты не трогаются.
    Без кода у версии 1 код создаётся заново - его нужно показать человеку."""
    data = read_lock()
    if KEY is None:
        raise RuntimeError("сначала нужно войти")
    lock = dict(data)
    if data.get("version", 1) < 2:
        if password is None or code is None:
            raise ValueError("для перехода на версию 2 нужны и пароль, и код")
        write_lock(build_lock(KEY, password, code))
        return
    if password is not None:
        lock["salt"], lock["key"] = _wrap(KEY, password)
    if code is not None:
        lock["recovery_salt"], lock["recovery_key"] = _wrap(KEY, normalize_code(code))
    write_lock(lock)


# ---------------- порядок файлов ----------------
def load_order(folder):
    try:
        names = json.loads((folder / C.ORDER_FILE).read_text(encoding="utf-8"))
        return [n for n in names if isinstance(n, str)]
    except (OSError, ValueError):
        return []


def save_order(folder, names):
    try:
        write_atomic(folder / C.ORDER_FILE, json.dumps(names, ensure_ascii=False).encode("utf-8"))
    except OSError as error:
        report_problem(f"Не сохранился порядок файлов в «{folder.name}»", error)


def ordered(paths, folder):
    rank = {name: i for i, name in enumerate(load_order(folder))}
    return sorted(paths, key=lambda p: (rank.get(p.name, len(rank)), p.name.lower()))


TEXT_SUFFIXES = {".txt", ".md", ".csv", ".board", ".timeline", ".text", ""}
NOT_TEXT_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".heic", ".pdf", ".docx", ".doc", ".odt",
    ".rtf", ".epub", ".fb2", ".zip", ".7z", ".rar", ".gz", ".tar", ".exe", ".msi", ".dll", ".so", ".mp3", ".wav",
    ".ogg", ".flac", ".m4a", ".mp4", ".mkv", ".avi", ".mov", ".webm", ".xlsx", ".xls", ".pptx", ".scriv", ".json",
    ".db", ".sqlite", ".iso", ".apk", ".torrent", ".kra", ".psd", ".blend",
}
_text_cache = {}


def is_text_file(path):
    """Можно ли открыть файл как текст. Картинки, Word, архивы и программы - нет."""
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES and suffix:
        return True
    if suffix in NOT_TEXT_SUFFIXES:
        return False
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return False
    cached = _text_cache.get(path)
    if cached and cached[0] == stamp:
        return cached[1]
    try:
        with open(path, "rb") as handle:
            head = handle.read(4096)
    except OSError:
        return False
    if head.startswith(C.MAGIC):
        good = True                                   # наш зашифрованный текст
    elif b"\0" in head:
        good = False
    else:
        try:
            head.decode("utf-8")
            good = True
        except UnicodeDecodeError as error:
            good = error.start > len(head) - 4 or _looks_like_8bit_text(head)    # обрезали посреди буквы
    _text_cache[path] = (stamp, good)
    return good


def _looks_like_8bit_text(data):
    controls = sum(1 for b in data if b < 32 and b not in (9, 10, 13))
    return controls < len(data) * 0.01


CONFLICT_PATTERNS = [
    re.compile(r"^(?P<base>.+?)\.sync-conflict-\d{8}-\d{6}-[A-Za-z0-9]+(?P<ext>\.[^.]+)?$"),      # Syncthing
    re.compile(r"^(?P<base>.+?) \((?:[^()]*'s )?conflicted copy[^()]*\)(?P<ext>\.[^.]+)?$", re.I),  # Dropbox, Nextcloud
    re.compile(r"^(?P<base>.+?) \([^()]*конфликт[^()]*\)(?P<ext>\.[^.]+)?$", re.I),                # Dropbox по-русски
    re.compile(r"^(?P<base>.+?)_conf\(\d+\)(?P<ext>\.[^.]+)?$"),                                    # pCloud
]


def conflict_original(path):
    """Для копии-конфликта от программы синхронизации - путь главы, с которой она разошлась; иначе None."""
    for pattern in CONFLICT_PATTERNS:
        m = pattern.match(path.name)
        if m:
            return path.with_name(m.group("base") + (m.group("ext") or ""))
    return None


def files_in(folder, everything=False):
    """Главы категории по порядку. Не-тексты (картинки, Word, программы) и копии-конфликты
    синхронизации - только если everything: в книгу, поиск и подсчёты они не попадают."""
    found = [f for f in folder.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not everything:
        found = [f for f in found if is_text_file(f) and conflict_original(f) is None]
    return ordered(found, folder)


def rename_in_order(folder, old, new):
    names = load_order(folder)
    if old in names:
        names[names.index(old)] = new
        save_order(folder, names)


def append_to_order(folder, name):
    names = [n for n in load_order(folder) if n != name]
    if not names:
        names = [f.name for f in files_in(folder) if f.name != name]
    names.append(name)
    save_order(folder, names)


# ---------------- версии ----------------
def versions_dir(path):
    """История главы: .versions/<путь главы внутри StungKir>. Для глав в категориях это
    .versions/<категория>/<глава>, как и раньше, и никакое название ни с чем не совпадёт."""
    try:
        relative = path.relative_to(C.ROOT)
    except ValueError:
        relative = Path(path.parent.name) / path.name
    return C.service_path(".versions") / relative


def notes_path(path):
    """Заметки на полях главы: .notes/<путь главы внутри StungKir>.json."""
    try:
        relative = path.relative_to(C.ROOT)
    except ValueError:
        relative = Path(path.parent.name) / path.name
    return C.service_path(".notes") / relative.with_name(relative.name + ".json")


def move_notes(old, new):
    source, target = notes_path(old), notes_path(new)
    if not source.exists():
        return True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        return True
    except OSError as error:
        log_error(f"Заметки на полях не переехали: {old} -> {new}", error)
        return False


def list_versions(path):
    folder = versions_dir(path)
    if not folder.is_dir():
        return []
    return sorted(folder.glob("*.txt"), reverse=True)


def keep_raw_copy(path):
    """Точная копия файла байт в байт (рядом с версиями): если текст прочитался не весь, оригинал не пропадёт."""
    try:
        folder = versions_dir(path)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{datetime.now():%Y%m%d-%H%M%S}-оригинал{path.suffix}.raw"
        if not any(folder.glob("*-оригинал*.raw")):
            shutil.copy2(path, target)
    except OSError as error:
        log_error("Не сохранилась точная копия файла", error)


def snapshot(path, text):
    """Сохраняет копию текста как версию, если он отличается от последней."""
    folder = versions_dir(path)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        existing = sorted(folder.glob("*.txt"))
        if existing:
            try:
                if read_text(existing[-1]) == text:
                    return
            except LockedFile:
                pass
        save_text(unique_path(folder / (datetime.now().strftime(C.VERSION_STAMP) + ".txt")), text)
        existing = sorted(folder.glob("*.txt"))
        for old in existing[:-C.MAX_VERSIONS]:
            old.unlink()
    except OSError as error:
        report_problem(f"Версия «{path.stem}» не сохранилась", error)


def move_tree(source, target):
    """Переносит папку. Если на новом месте уже есть такая же, складывает файлы туда же."""
    if not source.exists():
        return True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            source.rename(target)
            return True
        target.mkdir(exist_ok=True)
        for item in source.iterdir():
            if item.is_dir():
                if not move_tree(item, target / item.name):
                    return False
            else:
                item.rename(unique_path(target / item.name))
        source.rmdir()
        return True
    except OSError as error:
        log_error(f"Не перенеслась папка {source} -> {target}", error)
        return False


def move_versions(old, new):
    return move_tree(versions_dir(old), versions_dir(new))


def version_label(path):
    try:
        stamp = datetime.strptime(path.stem[:19], "%Y-%m-%d_%H-%M-%S")
        return stamp.strftime("%d.%m.%Y   %H:%M:%S")
    except ValueError:
        return path.stem


def content_files():
    """Все тексты: главы во всех категориях и их версии."""
    files = []
    try:
        folders = list(C.ROOT.iterdir())          # папку с книгами могли удалить или отключить диск
    except OSError:
        folders = []
    for folder in folders:
        if folder.is_dir() and not folder.name.startswith("."):
            files += files_in(folder)
    versions = C.service_path(".versions")
    if versions.is_dir():
        files += [p for p in versions.rglob("*.txt") if p.is_file()]
    notes = C.service_path(".notes")
    if notes.is_dir():
        files += [p for p in notes.rglob("*.json") if p.is_file()]
    covers = C.service_path(".covers")                 # обложки категорий - тоже под замком
    if covers.is_dir():
        files += [p for p in covers.glob("*.cover") if p.is_file()]
    trash = C.service_path(".trash")                  # удалённое шифруется вместе со всем
    if trash.is_dir():
        files += [p for p in trash.rglob("*") if p.is_file() and p.name != "meta.json"
                  and not p.name.startswith(".")]
    return files


# ---------------- статистика ----------------
def _read_stats(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: int(v) for k, v in data.items()}


def load_stats(own_only=False):
    """Слова по дням. Каждое устройство пишет свой файл (компьютер - stats.json, телефон -
    stats-phone.json), чтобы синхронизация не затирала чужие числа; own_only=False - всё вместе."""
    try:
        own = _read_stats(C.service_path(C.STATS_FILE))
    except FileNotFoundError:
        own = {}
    except (OSError, ValueError, AttributeError) as error:
        report_problem("Файл статистики повреждён, начинаю статистику заново", error)
        own = {}
    if own_only:
        return own
    total = dict(own)
    for other in sorted((C.ROOT / C.SERVICE_DIR).glob("stats-*.json")):
        try:
            for day, words in _read_stats(other).items():
                total[day] = total.get(day, 0) + max(0, words)
        except (OSError, ValueError, AttributeError):
            continue                                  # чужой файл испорчен - просто без него
    return total


def save_stats(stats):
    try:
        write_atomic(C.service_path(C.STATS_FILE), json.dumps(stats, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    except OSError as error:
        report_problem("Не сохранилась статистика", error)


def load_deadlines():
    """{категория: {"words": сколько слов, "date": "ГГГГ-ММ-ДД"}}."""
    try:
        data = json.loads((C.service_path(C.DEADLINES_FILE)).read_text(encoding="utf-8"))
        return {k: {"words": int(v["words"]), "date": str(v["date"])} for k, v in data.items()
                if isinstance(v, dict) and int(v.get("words", 0)) > 0}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        report_problem("Файл дедлайнов повреждён", error)
        return {}


def save_deadlines(deadlines):
    try:
        write_atomic(C.service_path(C.DEADLINES_FILE), json.dumps(deadlines, ensure_ascii=False, indent=1).encode("utf-8"))
    except OSError as error:
        report_problem("Не сохранились дедлайны", error)


def deadline_pace(words_now, target, until, today):
    """Сколько слов в день нужно, чтобы успеть: (осталось слов, осталось дней с сегодняшним, в день).
    Срок прошёл - дней 0, в день None."""
    import math
    left = max(0, target - words_now)
    days = (until - today).days + 1
    if days <= 0:
        return left, 0, None
    return left, days, math.ceil(left / days)


def load_crutches():
    """Мои штампы: список слов и оборотов."""
    try:
        data = json.loads((C.service_path(C.CRUTCHES_FILE)).read_text(encoding="utf-8"))
        return [w.strip() for w in data if isinstance(w, str) and w.strip()]
    except FileNotFoundError:
        return []
    except (OSError, ValueError, TypeError) as error:
        report_problem("Файл «Мои штампы» повреждён", error)
        return []


def save_crutches(words):
    try:
        write_atomic(C.service_path(C.CRUTCHES_FILE), json.dumps(words, ensure_ascii=False, indent=1).encode("utf-8"))
    except OSError as error:
        report_problem("Не сохранился список «Мои штампы»", error)


def load_marks():
    """Дни, которые отмечены «писал» вручную: {"2026-10-14", …}."""
    try:
        data = json.loads((C.service_path(C.MARKS_FILE)).read_text(encoding="utf-8"))
        return {d for d in data if isinstance(d, str)}
    except FileNotFoundError:
        return set()
    except (OSError, ValueError, TypeError) as error:
        report_problem("Файл отметок дней повреждён", error)
        return set()


def save_marks(marks):
    try:
        write_atomic(C.service_path(C.MARKS_FILE), json.dumps(sorted(marks), ensure_ascii=False).encode("utf-8"))
    except OSError as error:
        report_problem("Не сохранились отметки дней", error)


def wrote_on(day, stats, marks):
    """Засчитан ли день: написано от STREAK_WORDS слов или отмечен вручную."""
    key = day.isoformat()
    return key in marks or stats.get(key, 0) >= C.STREAK_WORDS


def streaks(stats, marks, today):
    """(дней подряд сейчас, рекорд). Сегодня ещё не засчитано - серия не рвётся, считаем со вчера."""
    from datetime import date, timedelta
    days = set(marks) | {k for k, v in stats.items() if v >= C.STREAK_WORDS}
    written = set()
    for key in days:
        try:
            written.add(date.fromisoformat(key))
        except ValueError:
            continue
    current, day = 0, today if today in written else today - timedelta(days=1)
    while day in written:
        current += 1
        day -= timedelta(days=1)
    best, run, previous = 0, 0, None
    for day in sorted(written):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return current, max(best, current)


def load_goals():
    try:
        data = json.loads((C.service_path(C.GOALS_FILE)).read_text(encoding="utf-8"))
        return {k: int(v) for k, v in data.items() if int(v) > 0}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, AttributeError) as error:
        report_problem("Файл целей глав повреждён", error)
        return {}


def save_goals(goals):
    try:
        write_atomic(C.service_path(C.GOALS_FILE), json.dumps(goals, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    except OSError as error:
        report_problem("Не сохранились цели глав", error)


PLAN_FIELDS = ("status", "about", "pov", "year", "skip")


def load_plan():
    """{глава (путь внутри StungKir): {"status": код, "about": о чём, "pov": чей взгляд, "year": год в истории,
    "skip": "yes" - не в книгу}} - для «Плана книги». Всё строками; чужие поля и мусор пропускаются."""
    try:
        data = json.loads((C.service_path(C.PLAN_FILE)).read_text(encoding="utf-8"))
        plan = {}
        for key, value in data.items():
            if not isinstance(value, dict):
                continue
            entry = {k: str(value[k]).strip() for k in PLAN_FIELDS if isinstance(value.get(k), str)}
            entry = {k: v for k, v in entry.items() if v}
            if entry:
                plan[str(key)] = entry
        return plan
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, AttributeError) as error:
        report_problem("Файл плана книги повреждён", error)
        return {}


def save_plan(plan):
    clean = {key: entry for key, entry in plan.items() if entry}
    try:
        write_atomic(C.service_path(C.PLAN_FILE),
                     json.dumps(clean, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8"))
    except OSError as error:
        report_problem("Не сохранился план книги", error)


def load_names():
    try:
        names = json.loads((C.service_path(C.NAMES_FILE)).read_text(encoding="utf-8"))
        return [n for n in names if isinstance(n, str) and n.strip()]
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as error:
        report_problem("Файл персонажей повреждён", error)
        return []


def save_names(names):
    try:
        write_atomic(C.service_path(C.NAMES_FILE), json.dumps(names, ensure_ascii=False).encode("utf-8"))
    except OSError as error:
        report_problem("Не сохранился список персонажей", error)


# ---------------- резервные копии и ярлык ----------------
def backup_path(day=None):
    return C.BACKUP_DIR / f"{C.APP_NAME} {(day or date.today()).isoformat()}.zip"


def make_backup():
    """Упаковывает всю папку с текстами в архив за сегодня. Старые архивы удаляет."""
    try:
        C.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        target = backup_path()
        temp = target.with_name(target.stem + ".part")
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
            for path in sorted(C.ROOT.rglob("*")):
                if path.is_file() and not path.name.endswith(".tmp") and path.parent != C.BACKUP_DIR:
                    archive.write(path, path.relative_to(C.ROOT.parent))
        temp.replace(target)
        for old in sorted(C.BACKUP_DIR.glob(f"{C.APP_NAME} *.zip"))[:-C.BACKUP_KEEP]:
            old.unlink()
        return True
    except OSError as error:
        report_problem(f"Резервная копия не сделана ({C.BACKUP_DIR})", error)
        return False


WEEKLY_KEEP = 8                   # сколько недельных копий держать в своей папке (два месяца)


def weekly_copy(folder, last=None, today=None):
    """Раз в неделю - копия всей книги в свою папку: флешка, облачная папка, второй диск.
    Папки нет (флешку вынули) - тихо ждём следующего раза. Возвращает дату копии или None."""
    today = today or date.today()
    if not folder:
        return None
    folder = Path(folder).expanduser()
    if last:
        try:
            if (today - date.fromisoformat(str(last))).days < 7:
                return None
        except ValueError:
            pass
    try:
        if not folder.is_dir():
            return None
    except (OSError, ValueError):       # вписали ерунду: слишком длинное имя, недопустимые знаки
        return None
    source = backup_path(today)
    if not source.is_file():
        if not make_backup():
            return None
        source = backup_path()
    target = folder / f"{C.APP_NAME} неделя {today.isoformat()}.zip"
    temp = target.with_name(target.name + ".part")
    try:
        shutil.copyfile(source, temp)
        temp.replace(target)
        for old in sorted(folder.glob(f"{C.APP_NAME} неделя *.zip"))[:-WEEKLY_KEEP]:
            old.unlink()
    except OSError as error:
        report_problem(f"Недельная копия не сделана ({folder})", error)
        try:
            temp.unlink()
        except OSError:
            pass
        return None
    return today.isoformat()


def packaged():
    """Программа пришла готовой сборкой (Flatpak, установщик Windows): ярлык делает сама сборка."""
    return bool(getattr(sys, "frozen", False) or os.environ.get("FLATPAK_ID")) or not sys.platform.startswith("linux")


def refresh_icon_caches(share):
    """Просим систему перечитать иконки и меню: GTK-кеш значков и меню KDE, если они есть."""
    hicolor = share / "icons" / "hicolor"
    if os.environ.get("STUNGKIR_TEST_HOME"):
        return                                   # в автотестах системные кеши не трогаем
    try:
        os.utime(hicolor)
    except OSError:
        pass
    commands = []
    if (hicolor / "icon-theme.cache").exists() and shutil.which("gtk-update-icon-cache"):
        commands.append(["gtk-update-icon-cache", "-f", "-t", str(hicolor)])
    for tool in ("kbuildsycoca6", "kbuildsycoca5"):
        if shutil.which(tool):
            commands.append([tool])
            break
    for command in commands:
        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass


def install_launcher():
    """Кладёт ярлык и иконку в меню приложений (или обновляет, если файл переехал).
    Только для установки через install.sh на Linux."""
    if packaged():
        return None
    try:
        share = Path.home() / ".local" / "share"
        apps = share / "applications"
        icons = share / "icons" / "hicolor" / "scalable" / "apps"
        apps.mkdir(parents=True, exist_ok=True)
        icons.mkdir(parents=True, exist_ok=True)
        # старый ярлык от прошлой версии
        for old in (apps / "writer-notepad.desktop", icons / "writer-notepad.svg"):
            if old.exists():
                old.unlink()
        # имя файла зависит от рисунка: меню, файловый менеджер и панель задач держат старые иконки
        # в памяти по имени, а новое имя они обязаны прочитать заново
        import hashlib
        icon = icons / f"{C.APP_ID}-{hashlib.sha1(ICON_SVG.encode('utf-8')).hexdigest()[:8]}.svg"
        for stale in icons.glob(f"{C.APP_ID}*.svg"):
            if stale != icon:
                stale.unlink()
        if not icon.exists() or icon.read_text(encoding="utf-8") != ICON_SVG:
            icon.write_text(ICON_SVG, encoding="utf-8")
        wrapper = Path.home() / ".local" / "bin" / C.APP_ID
        if wrapper.exists():
            command = f'"{wrapper}"'
        else:
            command = f'"{sys.executable}" "{MAIN_FILE}"'
        desktop = apps / f"{C.APP_ID}.desktop"
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={C.APP_NAME}\n"
            "Comment=Блокнот для писательства\n"
            f"Exec={command}\n"
            f"Icon={icon}\n"
            "Terminal=false\n"
            "Categories=Office;TextEditor;\n"
            "StartupNotify=true\n"
            f"StartupWMClass={C.APP_ID}\n"
        )
        if not desktop.exists() or desktop.read_text(encoding="utf-8") != content:
            desktop.write_text(content, encoding="utf-8")
            desktop.chmod(0o755)
            if shutil.which("update-desktop-database"):
                subprocess.run(["update-desktop-database", str(apps)], capture_output=True)
            refresh_icon_caches(share)
        return icon
    except OSError as error:
        log_error("Не получилось обновить ярлык в меню", error)
        return None


def migrate_old_root():
    """Старая папка «Блокнот» переезжает в новую при первом запуске. Возвращает ошибку или None."""
    if not C.OLD_ROOT.is_dir() or C.ROOT.exists():
        return None
    # у другого человека «Блокнот» может быть своей папкой: трогаем только старую папку StungKir
    markers = (".order", ".versions", ".stats.json", ".names.json")
    if not any((C.OLD_ROOT / m).exists() for m in markers) and not any(
            (folder / ".order").exists() for folder in C.OLD_ROOT.iterdir() if folder.is_dir()):
        return None
    try:
        C.OLD_ROOT.rename(C.ROOT)
        return None
    except OSError:
        pass   # обычно это папки на разных дисках: тогда копируем
    # копируем во временную папку и только в самом конце даём ей настоящее имя,
    # чтобы оборванное копирование не выглядело как готовая папка
    partial = C.ROOT.with_name(f".{C.ROOT.name}.partial")
    try:
        if partial.exists():
            shutil.rmtree(partial)
        shutil.copytree(C.OLD_ROOT, partial)
        os.replace(partial, C.ROOT)
    except OSError as error:
        shutil.rmtree(partial, ignore_errors=True)
        log_error("Не получилось перенести старую папку", error)
        return error
    try:
        C.OLD_ROOT.rename(C.OLD_ROOT.with_name(C.OLD_ROOT.name + " (перенесено в StungKir)"))
    except OSError as error:
        log_error("Копия сделана, но старую папку не удалось пометить", error)
    return None
