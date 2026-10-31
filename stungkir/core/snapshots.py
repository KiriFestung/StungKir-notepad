# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Снимки всего проекта: книга целиком на момент перед большой правкой, с откатом.
Снимок - zip внутри папки снимков (не внутри ~/StungKir, чтобы Syncthing не гонял его на телефон).
История версий глав, статистика и личный словарь при откате не трогаются."""

import json
import os
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from . import config as C
from . import storage as S
from .storage import LockedFile, decode_text, log_error, shred

MANIFEST = "snapshot.json"
STAMP = "%Y-%m-%d_%H-%M-%S"
# не входит в снимок и остаётся как есть при откате
KEEP = {".versions", ".trash", ".stats.json", ".dictionary.txt", ".stfolder", ".stignore", ".stversions"}


class SnapshotError(Exception):
    """Снимок не сделан или не возвращён; книга при этом осталась как была."""


# служебная папка .stungkir: что из неё не входит в точку (то же, что KEEP, но новыми именами)
SERVICE_KEEP = {C.LEGACY_NAMES[k] for k in KEEP if k in C.LEGACY_NAMES} | {"переезд"}
_LEGACY_OF = {new: old for old, new in C.LEGACY_NAMES.items()}


def _archive_name(path):
    """Имя файла внутри точки. Служебные файлы записываются прежними именами (".notes/…", ".lock.json"),
    поэтому старые точки возвращаются в новую раскладку, а новые читаются старой логикой."""
    parts = path.relative_to(C.ROOT).parts
    if parts[0] != C.SERVICE_DIR:
        return "/".join(parts)
    if len(parts) < 2 or parts[1] not in _LEGACY_OF:
        return None
    return "/".join((_LEGACY_OF[parts[1]],) + parts[2:])


def _restore_path(base, name):
    """Куда распаковать файл точки: прежние служебные имена - в .stungkir."""
    parts = Path(name).parts
    if parts[0] in C.LEGACY_NAMES:
        return base / C.SERVICE_DIR / C.LEGACY_NAMES[parts[0]] / Path(*parts[1:]) if len(parts) > 1 \
            else base / C.SERVICE_DIR / C.LEGACY_NAMES[parts[0]]
    return base / name


def _entries():
    """Что входит в точку: всё в папке книги, кроме KEEP и временных файлов."""
    for path in sorted(C.ROOT.rglob("*")):
        if not path.is_file():
            continue
        name = _archive_name(path)
        if name is None or name.split("/")[0] in KEEP:
            continue
        if path.name.endswith((".tmp", ".part")):
            continue
        yield path, name


def _is_content(name):
    """Тексты, которые шифруются паролем: главы в категориях и заметки на полях."""
    parts = name.split("/")
    if parts[0] == ".notes":
        return name.endswith(".json")
    if parts[0] == ".covers":
        return name.endswith(".cover")
    return len(parts) == 2 and not parts[0].startswith(".") and not parts[1].startswith(".")


def _words():
    total = 0
    for path, name in _entries():
        if _is_content(name) and not name.startswith((".notes", ".covers")):
            try:
                total += len(re.findall(r"\w+", S.read_text(path)))
            except (OSError, LockedFile):
                pass
    return total


def make_snapshot(title):
    """Снимает книгу целиком. Возвращает путь к снимку."""
    C.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now()
    target = C.SNAPSHOT_DIR / f"{stamp.strftime(STAMP)}.zip"
    n = 2
    while target.exists():
        target = C.SNAPSHOT_DIR / f"{stamp.strftime(STAMP)}-{n}.zip"
        n += 1
    temp = target.with_name(target.name + ".part")
    chapters = 0
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
            for path, name in _entries():
                archive.write(path, name)
                chapters += _is_content(name) and not name.startswith((".notes", ".covers"))
            manifest = {"title": title, "created": stamp.isoformat(timespec="seconds"),
                        "chapters": chapters, "words": _words(), "encrypted": S.lock_path().exists()}
            archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False))
        with open(temp, "rb+") as handle:
            os.fsync(handle.fileno())
        S.replace_file(temp, target)
    except OSError as error:
        temp.unlink(missing_ok=True)
        raise SnapshotError(S.os_message(error)) from error
    return target


def list_snapshots():
    """[(путь, сведения)] - новые сверху. Повреждённые снимки тоже показываются, с пометкой."""
    out = []
    if not C.SNAPSHOT_DIR.is_dir():
        return out
    for path in sorted(C.SNAPSHOT_DIR.glob("*.zip"), reverse=True):
        try:
            with zipfile.ZipFile(path) as archive:
                info = json.loads(archive.read(MANIFEST).decode("utf-8"))
        except (OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
            info = {"title": path.stem, "broken": str(error)}
        info["size"] = path.stat().st_size if path.exists() else 0
        out.append((path, info))
    return out


def delete_snapshot(path):
    if not shred(path):
        path.unlink(missing_ok=True)


def _lock_bytes(archive):
    try:
        return archive.read(".lock.json")
    except KeyError:
        return None


def _current_lock():
    try:
        return S.lock_path().read_bytes()
    except FileNotFoundError:
        return None


def restore_snapshot(path):
    """Возвращает книгу к снимку. Сначала всё распаковывается рядом и проверяется,
    потом нынешние файлы откладываются в сторону и на их место встают файлы из снимка.
    При любой ошибке всё возвращается как было. Папка книги не пересоздаётся, поэтому
    отметки Syncthing внутри неё остаются на месте."""
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise SnapshotError(f"файл точки повреждён: {error}") from error
    with archive:
        bad = archive.testzip()
        if bad is not None:
            raise SnapshotError(f"файл точки повреждён: {bad}")
        if _lock_bytes(archive) != _current_lock():
            raise SnapshotError("точка поставлена с другим паролем (или без пароля), чем стоит сейчас")
        stamp = datetime.now().strftime(STAMP)
        incoming = C.ROOT.with_name(f".{C.ROOT.name}.restore-{stamp}")
        aside = C.ROOT.with_name(f".{C.ROOT.name}.before-{stamp}")
        try:
            incoming.mkdir()
            for member in archive.infolist():
                name = member.filename
                parts = Path(name).parts
                if name == MANIFEST or member.is_dir():
                    continue
                if Path(name).is_absolute() or ".." in parts or not parts or parts[0] in KEEP:
                    continue          # чужие пути в архиве не распаковываем
                target = _restore_path(incoming, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, open(target, "wb") as out:
                    shutil.copyfileobj(source, out)
        except OSError as error:
            shutil.rmtree(incoming, ignore_errors=True)
            raise SnapshotError(f"не получилось распаковать: {S.os_message(error)}") from error

    moved = []                                   # (откуда, куда) - чтобы при сбое вернуть всё назад
    service, service_in, service_aside = C.ROOT / C.SERVICE_DIR, incoming / C.SERVICE_DIR, aside / C.SERVICE_DIR

    def move(source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        moved.append((source, target))
    try:
        aside.mkdir()
        for item in sorted(C.ROOT.iterdir()):
            if item.name not in KEEP and item.name != C.SERVICE_DIR:
                move(item, aside / item.name)
        if service.is_dir():                     # в служебной папке - только то, что входит в точку
            for item in sorted(service.iterdir()):
                if item.name not in SERVICE_KEEP:
                    move(item, service_aside / item.name)
        for item in sorted(incoming.iterdir()):
            if item.name != C.SERVICE_DIR:
                move(item, C.ROOT / item.name)
        if service_in.is_dir():
            for item in sorted(service_in.iterdir()):
                move(item, service / item.name)
    except OSError as error:
        # откат: всё, что успело переехать, - обратно в обратном порядке
        try:
            for source, target in reversed(moved):
                os.replace(target, source)
        except OSError as again:
            log_error(f"Откат точки не завершился, прежние файлы лежат в {aside}", again)
            raise SnapshotError(f"{S.os_message(error)}. Прежние файлы книги лежат в {aside}") from error
        shutil.rmtree(incoming, ignore_errors=True)
        shutil.rmtree(aside, ignore_errors=True)
        raise SnapshotError(S.os_message(error)) from error
    shutil.rmtree(incoming, ignore_errors=True)
    shutil.rmtree(aside, ignore_errors=True)


def recode_snapshots(old_crypto, new_crypto):
    """При установке и снятии пароля перешифровывает все снимки новым ключом,
    чтобы в них не оставалось открытого текста и чтобы их можно было вернуть.
    Возвращает список снимков, которые не получилось перешифровать (они не тронуты)."""
    failed = []
    lock = _current_lock()
    for path, info in list_snapshots():
        if info.get("broken"):
            failed.append(path)
            continue
        temp = path.with_name(path.name + ".part")
        try:
            with zipfile.ZipFile(path) as source, zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as out:
                for member in source.infolist():
                    name = member.filename
                    if name == ".lock.json":
                        continue
                    data = source.read(member)
                    if name == MANIFEST:
                        info = json.loads(data.decode("utf-8"))
                        info["encrypted"] = new_crypto is not None
                        data = json.dumps(info, ensure_ascii=False).encode("utf-8")
                    elif _is_content(name):
                        if data.startswith(C.MAGIC):
                            if old_crypto is None:
                                raise LockedFile(name)
                            data = old_crypto.decrypt(data[len(C.MAGIC):])
                        data = decode_text(data)[0].encode("utf-8")
                        if new_crypto is not None:
                            data = C.MAGIC + new_crypto.encrypt(data)
                    out.writestr(member, data)
                if lock is not None:
                    out.writestr(".lock.json", lock)
            with open(temp, "rb+") as handle:
                os.fsync(handle.fileno())
            # старый снимок мог быть открытым текстом: затираем его, а не просто удаляем
            old = path.with_name(path.name + ".old")
            S.replace_file(path, old)
            S.replace_file(temp, path)
            shred(old)
        except Exception as error:   # повреждённый снимок или чужой ключ: оставляем как есть
            temp.unlink(missing_ok=True)
            log_error(f"Снимок {path.name} не перешифрован", error)
            failed.append(path)
    return failed
