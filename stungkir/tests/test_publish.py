# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""«Выложить на сайт»: что уходит, что убирается, один коммит, ошибки ключа - на поддельном GitHub в памяти."""

import base64
import hashlib
import json
import time
import urllib.error

from PySide6.QtCore import QSettings

from stungkir import config as C
from stungkir import publish as P
from stungkir.tests.helpers import Sandbox, WindowCase, wait


class FakeHub:
    """Ровно те адреса API GitHub, которыми пользуется выкладка, с настоящими отпечатками git."""

    def __init__(self, files=None, status=None):
        self.blobs, self.trees, self.commits, self.calls = {}, {}, {}, []
        self.status = status
        tree = self._tree({path: self._blob(data) for path, data in (files or {"README.md": b"site"}).items()})
        self.head = self._commit(tree, None, "начало")

    def _blob(self, data):
        sha = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        self.blobs[sha] = data
        return sha

    def _tree(self, entries):
        sha = hashlib.sha1(json.dumps(sorted(entries.items())).encode()).hexdigest()
        self.trees[sha] = dict(entries)
        return sha

    def _commit(self, tree, parent, message):
        sha = hashlib.sha1(f"{tree}{parent}{message}{len(self.commits)}".encode()).hexdigest()
        self.commits[sha] = {"tree": tree, "parent": parent, "message": message}
        return sha

    def files(self):
        return {path: self.blobs[sha] for path, sha in self.trees[self.commits[self.head]["tree"]].items()}

    def __call__(self, method, url, headers, body):
        assert url.startswith("https://api.github.com/repos/Kira/site/"), url
        assert headers["Authorization"] == "Bearer ключ-123"
        path = url.split("/repos/Kira/site", 1)[1]
        self.calls.append((method, path))
        if self.status:
            return self.status, b'{"message": "no"}'
        data = json.loads(body) if body else None
        if method == "GET" and path == "/git/ref/heads/main":
            return 200, json.dumps({"object": {"sha": self.head}}).encode()
        if method == "GET" and path.startswith("/git/commits/"):
            return 200, json.dumps({"tree": {"sha": self.commits[path.rsplit("/", 1)[1]]["tree"]}}).encode()
        if method == "GET" and path.startswith("/git/trees/"):
            tree = self.trees[path.split("/")[3].split("?")[0]]
            return 200, json.dumps({"tree": [{"path": p, "type": "blob", "sha": s} for p, s in tree.items()],
                                    "truncated": False}).encode()
        if method == "POST" and path == "/git/blobs":
            return 201, json.dumps({"sha": self._blob(base64.b64decode(data["content"]))}).encode()
        if method == "POST" and path == "/git/trees":
            entries = dict(self.trees[data["base_tree"]])
            for item in data["tree"]:
                if item["sha"] is None:
                    entries.pop(item["path"], None)
                else:
                    entries[item["path"]] = item["sha"]
            return 201, json.dumps({"sha": self._tree(entries)}).encode()
        if method == "POST" and path == "/git/commits":
            return 201, json.dumps({"sha": self._commit(data["tree"], data["parents"][0], data["message"])}).encode()
        if method == "PATCH" and path == "/git/refs/heads/main":
            assert self.commits[data["sha"]]["parent"] == self.head          # только поверх свежего
            self.head = data["sha"]
            return 200, b"{}"
        return 404, b"{}"


class PublishLogicTest(Sandbox):
    def test_blob_sha_like_git(self):
        self.assertEqual(P.blob_sha(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
        self.assertEqual(P.blob_sha(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_plan_changes(self):
        base = "книги/Тервена/"
        local = {"Пролог.txt": "Кира ждала.".encode(), "Глава 1.txt": b"one", ".order": b'["a"]',
                 "картинки/карта.png": b"png"}
        changes, added, updated, removed = P.plan_changes(local, {}, base, "Тервена", cover=b"\xff\xd8jpeg")
        self.assertEqual(sorted(added), ["Глава 1", "Пролог"])
        self.assertEqual(json.loads(changes[base + "книга.json"])["обложка"], "обложка.jpg")
        self.assertEqual(changes[base + "обложка.jpg"], b"\xff\xd8jpeg")
        remote = {path: P.blob_sha(data) for path, data in changes.items()} | {"книги/Другая/Глава.txt": "x"}
        self.assertEqual(P.plan_changes(local, remote, base, "Тервена")[0], {})      # уже всё так же
        local["Глава 1.txt"] = b"one, edited"
        del local["Пролог.txt"]
        changes, added, updated, removed = P.plan_changes(local, remote, base, "Тервена")
        self.assertEqual((added, updated, removed), ([], ["Глава 1"], ["Пролог"]))
        self.assertIsNone(changes[base + "Пролог.txt"])
        self.assertNotIn("книги/Другая/Глава.txt", changes)                           # чужие книги не трогаются
        self.assertNotIn(base + "картинки/карта.png", changes)                         # картинки не убираются

    def test_errors_are_readable(self):
        for status, words in ((401, "не принял ключ"), (403, "Contents"), (404, "не нашёл")):
            hub = P.GitHub("Kira/site", "ключ-123", FakeHub(status=status))
            with self.assertRaises(P.PublishError) as caught:
                hub.head("main")
            self.assertIn(words, str(caught.exception))

        def offline(*_a):
            raise urllib.error.URLError("no route")
        with self.assertRaisesRegex(P.PublishError, "Нет связи"):
            P.GitHub("Kira/site", "ключ-123", offline).head("main")
        with self.assertRaisesRegex(P.PublishError, "владелец/имя"):
            P.GitHub("просто-имя", "ключ")
        self.assertEqual(P.GitHub("https://github.com/Kira/site/", "k").repo, "Kira/site")


class PublishWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        self.book = C.ROOT / "Тервена"
        self.first = self.chapter("Тервена", "Пролог", "Туман над рекой. [проверить]\n[картинка: карта.png]")
        self.second = self.chapter("Тервена", "Глава 1", "Кев ушёл.")
        self.draft = self.chapter("Тервена", "Глава 2", "Черновик Нии.")
        (self.book / "картинки").mkdir()
        (self.book / "картинки" / "карта.png").write_bytes(b"\x89PNG\r\n\x1a\nmap")
        self.w = self.window()
        for path in (self.first, self.second):
            self.w.plan_set(path, "status", "done")
        self.hub = FakeHub()

    def dialog(self):
        from stungkir.storage import save_order
        save_order(self.book, ["Пролог.txt", "Глава 1.txt", "Глава 2.txt"])
        dialog = P.PublishDialog(self.w, self.book, lambda: (
            P.local_files(self.book, P.ready_chapters(self.book, self.w.plan, self.w._position_key)), None), self.hub)
        dialog.repo.setText("Kira/site")
        dialog.token.setText("ключ-123")
        return dialog

    def finish(self, dialog):
        deadline = time.time() + 5
        while not dialog.check_button.isEnabled() and time.time() < deadline:
            wait(0.05)
        wait(0.15)

    def test_publish_ready_chapters_in_one_commit(self):
        dialog = self.dialog()
        dialog.check()
        self.finish(dialog)
        self.assertIn("Новые: «Пролог», «Глава 1»", dialog.report.text())
        self.assertNotIn("Глава 2", dialog.report.text())                         # черновик остаётся дома
        self.assertTrue(dialog.go_button.isEnabled())
        before = len(self.hub.commits)
        dialog.publish()
        self.finish(dialog)
        self.assertIn("Готово", dialog.report.text())
        self.assertEqual(len(self.hub.commits), before + 1)                     # одно изменение - одна выкладка
        site = self.hub.files()
        self.assertEqual(site["книги/Тервена/Пролог.txt"].decode(), "Туман над рекой. [проверить]\n[картинка: карта.png]")
        self.assertEqual(json.loads(site["книги/Тервена/.order"]), ["Пролог.txt", "Глава 1.txt"])
        self.assertEqual(site["книги/Тервена/картинки/карта.png"], b"\x89PNG\r\n\x1a\nmap")
        self.assertEqual(json.loads(site["книги/Тервена/книга.json"])["название"], "Тервена")
        self.assertIn("README.md", site)                                         # остальной сайт цел
        # ключ - в настройках компьютера, не в папке с текстами (её возит Syncthing)
        self.assertEqual(QSettings(C.APP_ID, C.APP_ID).value("publish_token"), "ключ-123")
        self.assertFalse(any("ключ-123" in p.read_text(encoding="utf-8", errors="ignore")
                             for p in C.ROOT.rglob("*") if p.is_file()))
        # второй раз - нечего выкладывать; глава поменялась и одна больше не «Готово» - видно до выкладки
        dialog = self.dialog()
        dialog.check()
        self.finish(dialog)
        self.assertIn("выкладывать нечего", dialog.report.text().lower())
        self.assertFalse(dialog.go_button.isEnabled())
        self.second.write_text("Кев ушёл к морю.", encoding="utf-8", newline="\n")
        self.w.plan_set(self.first, "status", "edit")
        dialog = self.dialog()
        dialog.check()
        self.finish(dialog)
        self.assertIn("Обновятся: «Глава 1»", dialog.report.text())
        self.assertIn("Уберутся с сайта (больше не «Готово»): «Пролог»", dialog.report.text())
        dialog.publish()
        self.finish(dialog)
        site = self.hub.files()
        self.assertNotIn("книги/Тервена/Пролог.txt", site)
        self.assertEqual(site["книги/Тервена/Глава 1.txt"].decode(), "Кев ушёл к морю.")

    def test_nothing_ready_and_bad_key(self):
        self.w.plan_set(self.first, "status", None)
        self.w.plan_set(self.second, "status", None)
        dialog = self.dialog()
        dialog.check()
        self.assertIn("Ни одна глава не отмечена «Готово»", dialog.report.text())
        self.w.plan_set(self.first, "status", "done")
        self.hub.status = 401
        dialog = self.dialog()
        dialog.check()
        self.finish(dialog)
        self.assertIn("не принял ключ", dialog.report.text())
        self.assertFalse(dialog.go_button.isEnabled())

    def test_menu_on_book_category(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        shown = []

        def read_and_close():                    # настоящее меню: прочитать пункты и закрыть
            menu = QApplication.activePopupWidget()
            if menu is not None:
                shown.extend(action.text() for action in menu.actions())
                menu.close()
        QTimer.singleShot(300, read_and_close)
        self.w.tree_menu(self.w.tree.visualItemRect(self.w.tree.topLevelItem(0)).center())
        self.assertIn("Выложить на сайт…", shown)
