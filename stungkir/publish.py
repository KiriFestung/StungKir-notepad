# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Выложить на сайт: главы категории со статусом «Готово» - в репозиторий сайта книг на GitHub (папка
книги/<категория>/), одним изменением; сайт после этого обновляется сам. В интернет программа ходит только
здесь и только по кнопке. Ключ GitHub хранится в настройках этого компьютера (в папку с текстами он не
попадает, Syncthing его не возит) и должен уметь менять только репозиторий сайта."""

import base64
import hashlib
import json
import threading
import urllib.error
import urllib.request

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

from . import config as C
from .dialogs import Sheet
from .export import IMAGE_LINE_RE
from .storage import LockedFile, files_in, read_text
from .textutil import is_prose, plural

API = "https://api.github.com"
TOKEN_HELP = ("Ключ: github.com → значок профиля → Settings → Developer settings → Personal access tokens → "
              "Fine-grained tokens → Generate new token. Repository access - Only select repositories → репозиторий "
              "сайта; Permissions → Contents: Read and write. Больше ничего ему не нужно.")


class PublishError(Exception):
    """Понятная человеку причина, почему не выложилось."""


def blob_sha(data):
    """Отпечаток файла так же, как его считает git: так видно, изменилась ли глава, не скачивая её."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _urlopen(method, url, headers, body):
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


class GitHub:
    """Самое нужное из API GitHub: прочитать дерево файлов ветки и записать изменения одним коммитом."""

    def __init__(self, repo, token, opener=None):
        repo = repo.strip().removeprefix("https://github.com/").strip("/")
        if repo.count("/") != 1 or not all(repo.split("/")):
            raise PublishError("Репозиторий сайта пишется так: владелец/имя, например KiriFesTung/SeMo")
        self.repo, self.token, self.opener = repo, token.strip(), opener or _urlopen

    def call(self, method, path, body=None):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "StungKir", "Authorization": f"Bearer {self.token}"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            status, raw = self.opener(method, f"{API}/repos/{self.repo}{path}", headers, data)
        except (urllib.error.URLError, OSError) as error:
            raise PublishError(f"Нет связи с GitHub ({getattr(error, 'reason', error)}). Проверь интернет") from error
        if status == 401:
            raise PublishError("GitHub не принял ключ: он неверный или истёк. Создай новый")
        if status == 403:
            raise PublishError("У ключа нет права менять файлы сайта: нужен Contents - Read and write")
        if status == 404:
            raise PublishError(f"GitHub не нашёл «{self.repo}» или ключ его не видит: при создании ключа "
                               "выбери этот репозиторий")
        if status == 409 and path.endswith("/git/trees"):
            raise PublishError("Репозиторий сайта пустой - положи в него хоть один файл")
        if status >= 400:
            raise PublishError(f"GitHub ответил ошибкой {status}: {raw[:200].decode('utf-8', 'replace')}")
        return json.loads(raw or b"{}")

    def head(self, branch):
        commit = self.call("GET", f"/git/ref/heads/{branch}")["object"]["sha"]
        tree = self.call("GET", f"/git/commits/{commit}")["tree"]["sha"]
        return commit, tree

    def files(self, tree):
        data = self.call("GET", f"/git/trees/{tree}?recursive=1")
        if data.get("truncated"):
            raise PublishError("В репозитории сайта слишком много файлов, GitHub отдал список не целиком")
        return {item["path"]: item["sha"] for item in data.get("tree", []) if item.get("type") == "blob"}

    def commit(self, branch, base_commit, base_tree, changes, message):
        """changes: {путь: байты или None (удалить)}. Один коммит - сайт выкладывается один раз."""
        entries = []
        for path, data in sorted(changes.items()):
            if data is None:
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
                continue
            blob = self.call("POST", "/git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = self.call("POST", "/git/trees", {"base_tree": base_tree, "tree": entries})["sha"]
        commit = self.call("POST", "/git/commits", {"message": message, "tree": tree, "parents": [base_commit]})["sha"]
        self.call("PATCH", f"/git/refs/heads/{branch}", {"sha": commit, "force": False})
        return commit


def ready_chapters(folder, plan, key):
    """Главы категории со статусом «Готово» и без «не в книгу», по порядку слева."""
    return [p for p in files_in(folder) if is_prose(p) and plan.get(key(p), {}).get("status") == "done"
            and not plan.get(key(p), {}).get("skip")]


def local_files(folder, chapters, current=None):
    """{путь внутри папки книги на сайте: байты}: главы, порядок, картинки из текста; обложка - отдельно."""
    files, order = {}, []
    for path in chapters:
        text = current[1] if current and current[0] == path else read_text(path)
        text = text.replace("\r\n", "\n")
        files[path.name] = text.encode("utf-8")
        order.append(path.name)
        for line in text.split("\n"):
            found = IMAGE_LINE_RE.match(line)
            if not found:
                continue
            name = found.group(1).strip().strip("«»\"'")
            for candidate in (folder / name, folder / "картинки" / name):
                if candidate.is_file():
                    files[f"картинки/{candidate.name}"] = candidate.read_bytes()
                    break
    files[".order"] = json.dumps(order, ensure_ascii=False).encode("utf-8")
    return files


def cover_name(data):
    """Обложка категории в StungKir хранится в JPEG; на всякий случай узнаём PNG по началу файла."""
    return "обложка.png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "обложка.jpg"


def plan_changes(local, remote, base, title, cover=None):
    """Что поменять на сайте: (изменения {путь: байты или None}, новые, обновлённые, убранные главы).
    Убираются только главы (.txt) этой книги, которых больше нет среди «Готово»; картинки и книга.json
    не трогаются. книга.json и обложка кладутся, только если книги на сайте ещё нет."""
    changes, added, updated = {}, [], []
    for name, data in local.items():
        path = base + name
        if remote.get(path) == blob_sha(data):
            continue
        changes[path] = data
        if name.endswith(".txt"):
            (updated if path in remote else added).append(name[:-4])
    removed = [path for path in remote if path.startswith(base) and path.endswith(".txt") and "/" not in path[len(base):]
               and path[len(base):] not in local]
    for path in removed:
        changes[path] = None
    if base + "книга.json" not in remote:
        info = {"название": title, "описание": "", "статус": "пишется"}
        if cover:
            info["обложка"] = cover_name(cover)
            changes[base + info["обложка"]] = cover
        changes[base + "книга.json"] = (json.dumps(info, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return changes, added, updated, [p[len(base):-4] for p in removed]


def names(items):
    return ", ".join(f"«{n}»" for n in items[:6]) + (f" и ещё {len(items) - 6}" if len(items) > 6 else "")


class PublishDialog(Sheet):
    """Где сайт и ключ, что изменится - и только потом «Выложить»."""

    def __init__(self, parent, folder, collect, opener=None):
        super().__init__(parent, f"Выложить на сайт · {folder.name}")
        self.setMinimumWidth(620)
        self.folder, self.collect, self.opener = folder, collect, opener
        self.store = QSettings(C.APP_ID, C.APP_ID)
        self.pending = None
        grid = QGridLayout()
        self.repo = QLineEdit(self.store.value("publish_repo", ""))
        self.repo.setPlaceholderText("владелец/репозиторий, например KiriFesTung/SeMo")
        self.token = QLineEdit(self.store.value("publish_token", ""))
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setPlaceholderText("github_pat_…")
        for row, (label, widget) in enumerate((("Сайт (репозиторий):", self.repo), ("Ключ GitHub:", self.token))):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
        self.content.addLayout(grid)
        hint = QLabel(TOKEN_HELP + "\nНа сайт уходят только главы со статусом «Готово» (правый клик по главе → Статус). "
                      "В интернет StungKir выходит только по этой кнопке.")
        hint.setObjectName("Status")
        hint.setWordWrap(True)
        self.content.addWidget(hint)
        self.report = QLabel("Нажми «Проверить» - покажу, что изменится на сайте.")
        self.report.setWordWrap(True)
        self.content.addWidget(self.report)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.check_button = QPushButton("Проверить")
        self.go_button = QPushButton("Выложить")
        self.go_button.setDefault(True)
        self.go_button.setEnabled(False)
        close = QPushButton("Закрыть")
        for button in (close, self.check_button, self.go_button):
            buttons.addWidget(button)
        self.content.addLayout(buttons)
        close.clicked.connect(self.reject)
        self.check_button.clicked.connect(self.check)
        self.go_button.clicked.connect(self.publish)
        self.repo.textChanged.connect(self._edited)
        self.token.textChanged.connect(self._edited)

    def _edited(self):
        self.pending = None
        self.go_button.setEnabled(False)

    def _hub(self):
        repo, token = self.repo.text().strip(), self.token.text().strip()
        if not token:
            raise PublishError("Нужен ключ GitHub - как его сделать, написано выше")
        hub = GitHub(repo, token, self.opener)
        self.store.setValue("publish_repo", repo)
        self.store.setValue("publish_token", token)
        return hub

    def run(self, work, done):
        """Сеть - в отдельном потоке, окно не замирает; done(результат или PublishError) - в окне."""
        box = {}

        def job():
            try:
                box["result"] = work()
            except PublishError as error:
                box["error"] = error
            except Exception as error:               # чужая ошибка сети или данных - тоже понятным текстом
                box["error"] = PublishError(f"Не получилось: {error}")
        self.check_button.setEnabled(False)
        self.go_button.setEnabled(False)
        thread = threading.Thread(target=job, daemon=True)
        thread.start()

        def wait():
            if thread.is_alive():
                QTimer.singleShot(100, wait)
                return
            self.check_button.setEnabled(True)
            done(box.get("error") or box.get("result"))
        wait()

    def check(self):
        try:
            hub = self._hub()
            local, cover = self.collect()
        except (PublishError, OSError, LockedFile) as error:
            self.report.setText(str(error) if isinstance(error, PublishError) else f"Не прочиталась глава: {error}")
            return
        if not any(name.endswith(".txt") for name in local):
            self.report.setText("Ни одна глава не отмечена «Готово». Правый клик по главе → Статус → Готово.")
            return
        self.report.setText("Смотрю, что сейчас на сайте…")
        base = f"книги/{self.folder.name}/"

        def work():
            commit, tree = hub.head("main")
            return hub, commit, tree, plan_changes(local, hub.files(tree), base, self.folder.name, cover)
        self.run(work, self._checked)

    def _checked(self, result):
        if isinstance(result, PublishError):
            self.report.setText(str(result))
            return
        hub, commit, tree, (changes, added, updated, removed) = result
        if not changes:
            self.report.setText("На сайте уже всё так же, как здесь. Выкладывать нечего.")
            return
        lines = []
        if added:
            lines.append(f"Новые: {names(added)}")
        if updated:
            lines.append(f"Обновятся: {names(updated)}")
        if removed:
            lines.append(f"Уберутся с сайта (больше не «Готово»): {names(removed)}")
        if not (added or updated or removed):
            lines.append("Главы те же, поменяются порядок, картинки или описание книги")
        self.report.setText("\n".join(lines))
        self.pending = (hub, commit, tree, changes, len(added) + len(updated))
        self.go_button.setEnabled(True)

    def publish(self):
        if not self.pending:
            return
        hub, commit, tree, changes, count = self.pending
        self.pending = None
        self.report.setText("Выкладываю…")
        message = f"«{self.folder.name}»: {count} {plural(count, 'глава', 'главы', 'глав')} из StungKir"
        self.run(lambda: hub.commit("main", commit, tree, changes, message), self._published)

    def _published(self, result):
        if isinstance(result, PublishError):
            self.report.setText(f"{result}\nНичего не изменилось - можно «Проверить» ещё раз.")
            return
        self.report.setText("Готово! Сайт обновится сам через пару минут.")


class PublishMixin:
    """«Выложить на сайт» у категории. Часть главного окна."""

    def show_publish(self, folder):
        if not self.save_everything():
            return
        from .covers import cover_bytes

        def collect():
            chapters = ready_chapters(folder, self.plan, self._position_key)
            current = (self.path, self.current_text()) if self.path and self.view is None else None
            return local_files(folder, chapters, current), cover_bytes(folder)
        PublishDialog(self, folder, collect).exec()
