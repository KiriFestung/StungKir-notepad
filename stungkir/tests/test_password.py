# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Пароль и шифрование: ключ, неверный пароль, повреждённый ключ, установка и снятие пароля."""
import base64
import json
import os
import unittest

from stungkir.core import config as C
from stungkir.core import storage as S
from stungkir.tests.helpers import Sandbox, WindowCase, crypto_available, wait


def real_password_dialog():
    from stungkir.ui.dialogs import PasswordDialog
    return PasswordDialog


REAL_PASSWORD_DIALOG = None


def write_lock(password):
    salt = os.urandom(16)
    crypto = S.make_crypto(password, salt)
    S.lock_path().parent.mkdir(parents=True, exist_ok=True)
    S.lock_path().write_text(json.dumps({"version": 1, "salt": base64.b64encode(salt).decode(),
                                         "check": crypto.encrypt(C.CHECK_PHRASE).decode()}), encoding="utf-8", newline="\n")
    return crypto


@unittest.skipUnless(crypto_available(), "нет библиотеки cryptography")
class KeyTest(Sandbox):
    def test_right_and_wrong_password(self):
        write_lock("секрет")
        self.assertIsNotNone(S.check_password("секрет"))
        self.assertIsNone(S.check_password("не тот"))

    def test_broken_key_is_not_a_wrong_password(self):
        for broken in ("{ не json", json.dumps({"salt": "!!!", "check": "x"}), json.dumps({"check": "x"}),
                       json.dumps([1, 2])):
            S.lock_path().parent.mkdir(parents=True, exist_ok=True)
            S.lock_path().write_text(broken, encoding="utf-8", newline="\n")
            with self.assertRaises(S.LockBroken):
                S.check_password("секрет")
            self.assertIsNotNone(S.lock_problem())

    def test_encrypted_file_needs_key(self):
        crypto = write_lock("секрет")
        path = self.chapter("Книга", "Глава", "")
        S.save_text(path, "Тайный текст.", crypto=crypto)
        self.assertTrue(S.is_encrypted(path))
        self.assertNotIn("Тайный".encode(), path.read_bytes())
        with self.assertRaises(S.LockedFile):
            S.read_text(path)
        self.assertTrue(S.unlock("секрет"))
        self.assertEqual(S.read_text(path), "Тайный текст.")


class FakePassword:
    password = "секрет123"
    recovered = False

    def __init__(self, *a, check=None, **k):
        self.check = check

    def exec(self):
        return self.check is None or self.check(self.password)


class FakeCode:
    """Окно с кодом восстановления: «записал» и нажал «Готово»."""
    shown = []

    def __init__(self, parent, code, intro=""):
        FakeCode.shown.append(code)

    def exec(self):
        return True


@unittest.skipUnless(crypto_available(), "нет библиотеки cryptography")
class PasswordWindowTest(WindowCase):
    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QMessageBox
        self.first = self.chapter("Книга", "Глава 1", "Туман над рекой.")
        self.second = self.chapter("Книга", "Глава 2", "Вторая глава.")
        self.w = self.window()
        self.w.open_path(self.first)
        self.w.editor.insertPlainText("Утро. ")
        self.w.save()
        self.patch("PasswordDialog", FakePassword)
        self.patch("RecoveryCodeDialog", FakeCode)
        self.answer = QMessageBox.Yes

    def test_set_and_remove_password(self):
        self.w.set_password()
        wait()
        for path in S.content_files():
            self.assertTrue(S.is_encrypted(path), path)
        self.assertTrue(S.lock_path().exists())
        self.assertEqual(S.read_text(self.first), "Утро. Туман над рекой.")
        self.assertTrue(all(S.is_encrypted(p) for p in S.list_versions(self.first)))
        # старые открытые архивы затёрты, новый зашифрован
        with __import__("zipfile").ZipFile(S.backup_path()) as archive:
            data = b"".join(archive.read(n) for n in archive.namelist() if n.endswith(".txt"))
        self.assertNotIn("Туман".encode(), data)
        self.w.remove_password()
        wait()
        self.assertFalse(S.lock_path().exists())
        self.assertFalse(any(S.is_encrypted(p) for p in S.content_files()))
        self.assertEqual(self.second.read_text(encoding="utf-8"), "Вторая глава.")

    def test_unreadable_file_stops_before_any_change(self):
        real = S.read_text

        def failing(path, *a, **k):
            if path == self.second:
                raise OSError(13, "Permission denied")
            return real(path, *a, **k)
        self.patch("read_text", failing)
        self.w.set_password()
        self.assertFalse(S.lock_path().exists())
        self.assertIsNone(S.CRYPTO)
        self.assertFalse(any(S.is_encrypted(p) for p in S.content_files()))
        self.assertEqual(self.messages[-1][0], "Пароль не поставлен")

    def test_failed_write_keeps_everything_readable_and_finishes_later(self):
        real = S.save_text
        calls = {"n": 0}

        def flaky(path, text, crypto=S._CURRENT):
            if path == self.second and crypto is not None and calls["n"] == 0:
                calls["n"] += 1
                raise OSError(28, "No space left on device")
            return real(path, text, crypto=crypto)
        self.patch("save_text", flaky)
        self.w.set_password()
        self.assertTrue(S.lock_path().exists())
        self.assertFalse(S.is_encrypted(self.second))          # этот остался открытым
        self.assertEqual(S.read_text(self.second), "Вторая глава.")
        self.assertEqual(S.read_text(self.first), "Утро. Туман над рекой.")
        self.w.finish_encryption()                              # при следующем запуске дошифрует
        self.assertTrue(S.is_encrypted(self.second))
        self.assertEqual(S.read_text(self.second), "Вторая глава.")


@unittest.skipUnless(crypto_available(), "нет библиотеки cryptography")
class PasswordDialogTest(Sandbox):
    def test_dialog_tells_broken_key_from_wrong_password(self):
        from stungkir.tests.helpers import app
        from stungkir.ui.dialogs import PasswordDialog
        app()
        write_lock("секрет")
        dialog = PasswordDialog(None, "Вход", "Пароль", check=S.unlock)
        dialog.first.setText("не тот")
        dialog.accept()
        self.assertEqual(dialog.error.text(), "Неверный пароль")
        S.lock_path().parent.mkdir(parents=True, exist_ok=True)
        S.lock_path().write_text("{ сломано", encoding="utf-8", newline="\n")
        dialog.first.setText("секрет")
        dialog.accept()
        self.assertIn("Файл ключа повреждён", dialog.error.text())


@unittest.skipUnless(crypto_available(), "нет библиотеки cryptography")
class RecoveryTest(WindowCase):
    """Код восстановления: вход по коду, смена пароля без перешифровки, переход со старого ключа."""

    def setUp(self):
        global REAL_PASSWORD_DIALOG
        REAL_PASSWORD_DIALOG = real_password_dialog()       # до подмены
        super().setUp()
        from PySide6.QtWidgets import QMessageBox
        self.first = self.chapter("Книга", "Глава 1", "Туман над рекой.")
        self.w = self.window()
        self.patch("PasswordDialog", FakePassword)
        self.patch("RecoveryCodeDialog", FakeCode)
        self.answer = QMessageBox.Yes
        self.addCleanup(setattr, S, "KEY", S.KEY)

    def test_code_opens_texts_and_password_changes_without_reencrypting(self):
        self.w.set_password()
        self.assertEqual(S.lock_version(), 2)
        code = FakeCode.shown[-1]
        self.assertRegex(code, r"^([2-9A-Z]{4}-){4}[2-9A-Z]{4}$")
        stamp = self.first.stat().st_mtime_ns
        S.CRYPTO = S.KEY = None
        self.assertFalse(S.unlock_recovery("AAAA-AAAA-AAAA-AAAA-AAAA"))
        self.assertTrue(S.unlock_recovery(code.lower().replace("-", " ")))   # как ни введи
        self.assertEqual(S.read_text(self.first), "Туман над рекой.")
        S.rewrap_lock(password="новый пароль")
        S.CRYPTO = S.KEY = None
        self.assertFalse(S.unlock("секрет123"))
        self.assertTrue(S.unlock("новый пароль"))
        self.assertEqual(S.read_text(self.first), "Туман над рекой.")
        self.assertEqual(self.first.stat().st_mtime_ns, stamp)              # файлы не трогали
        self.assertTrue(S.unlock_recovery(code))                             # код прежний

    def test_new_code_replaces_old(self):
        self.w.set_password()
        old = FakeCode.shown[-1]
        self.w.new_recovery_code()
        new = FakeCode.shown[-1]
        self.assertNotEqual(old, new)
        self.assertFalse(S.unlock_recovery(old))
        self.assertTrue(S.unlock_recovery(new))

    def test_change_password_from_menu(self):
        self.w.set_password()
        FakePassword.password = "другой пароль"
        self.addCleanup(setattr, FakePassword, "password", "секрет123")
        real_check = S.unlock

        class Current(FakePassword):                     # нынешний пароль, потом новый
            calls = 0

            def exec(self):
                Current.calls += 1
                if self.check is not None:
                    return self.check("секрет123")
                return True
        self.patch("PasswordDialog", Current)
        self.w.change_password()
        S.CRYPTO = S.KEY = None
        self.assertFalse(real_check("секрет123"))
        self.assertTrue(real_check("другой пароль"))

    def test_old_key_gets_a_code_and_files_stay(self):
        from stungkir.tests.test_password import write_lock as write_v1
        crypto = write_v1("старый пароль")
        S.save_text(self.first, "Зашифровано по-старому.", crypto=crypto)
        self.assertEqual(S.lock_version(), 1)
        self.assertFalse(S.unlock_recovery("ЧТО-УГОДНО"))                    # кода ещё нет
        self.assertTrue(S.unlock("старый пароль"))
        from stungkir.ui.security import offer_recovery_code
        self.assertTrue(offer_recovery_code(None, "старый пароль"))
        self.assertEqual(S.lock_version(), 2)
        S.CRYPTO = S.KEY = None
        self.assertTrue(S.unlock_recovery(FakeCode.shown[-1]))
        self.assertEqual(S.read_text(self.first), "Зашифровано по-старому.")
        S.CRYPTO = S.KEY = None
        self.assertTrue(S.unlock("старый пароль"))

    def test_forgot_link_and_backoff(self):
        from PySide6.QtCore import QSettings
        PasswordDialog = REAL_PASSWORD_DIALOG
        settings = QSettings(C.APP_ID, C.APP_ID)
        self.addCleanup(settings.remove, "password_failures")
        self.addCleanup(settings.remove, "password_wait_until")
        self.w.set_password()
        S.CRYPTO = S.KEY = None
        dialog = PasswordDialog(None, "Вход", "Пароль", check=S.unlock, recover=lambda parent: True)
        self.assertTrue(dialog.forgot.isVisibleTo(dialog))                  # видно сразу
        plain = PasswordDialog(None, "Новый", "Пароль", confirm=True)
        self.assertFalse(plain.forgot.isVisibleTo(plain))                   # где кода нет - нет и ссылки
        for _ in range(3):
            dialog.first.setText("не тот")
            dialog.accept()
        self.assertTrue(dialog.forgot.isVisibleTo(dialog))
        dialog.forgot.click()
        self.assertTrue(dialog.recovered)
        self.assertEqual(PasswordDialog._state()[1], 0)

    def test_code_typed_with_russian_letters(self):
        self.assertEqual(S.normalize_code("аВ2с-кмн3 рт4х уE5"), "AB2C-KMH3-PT4X-YE5")


class PowerCut(BaseException):
    """«Выдернули шнур»: не обычная ошибка, её никто не ловит."""


@unittest.skipUnless(crypto_available(), "нет библиотеки cryptography")
class EncryptionStressTest(WindowCase):
    """Книга в 300 глав с версиями; посреди шифрования пропадает питание."""

    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QMessageBox
        self.texts = {}
        for n in range(300):
            path = self.chapter(f"Книга {n // 100 + 1}", f"Глава {n + 1}", f"Глава {n + 1}. " + "Туман. " * (n % 40 + 1))
            if n % 10 == 0:
                S.snapshot(path, "старая версия " + str(n))
            self.texts[path] = path.read_text(encoding="utf-8")
        self.w = self.window()
        self.patch("PasswordDialog", FakePassword)
        self.patch("RecoveryCodeDialog", FakeCode)
        self.answer = QMessageBox.Yes

    def cut_after(self, writes):
        real = S.write_atomic
        count = {"n": 0}

        def cut(path, data):
            count["n"] += 1
            if count["n"] > writes:
                raise PowerCut()
            return real(path, data)
        self.patch("write_atomic", cut)
        return real

    def restart_and_unlock(self, real_write):
        self.patch("write_atomic", real_write)
        S.CRYPTO, S.KEY = None, None                 # новый запуск: ключа в памяти нет
        if S.lock_path().exists():
            self.assertTrue(S.unlock(FakePassword.password))
        self.w.finish_encryption()

    def check_all_readable(self):
        for path, text in self.texts.items():
            self.assertEqual(S.read_text(path), text, path)

    def test_power_cut_while_setting_password(self):
        real = self.cut_after(150)
        with self.assertRaises(PowerCut):
            self.w.set_password()
        self.assertTrue(S.lock_path().exists())
        self.restart_and_unlock(real)
        self.check_all_readable()
        self.assertTrue(all(S.is_encrypted(p) for p in S.content_files()))     # дошифровалось всё

    def test_power_cut_while_removing_password(self):
        self.w.set_password()
        real = self.cut_after(120)
        with self.assertRaises(PowerCut):
            self.w.remove_password()
        self.restart_and_unlock(real)
        self.check_all_readable()                                                # ни одна глава не потеряна

    def test_leftover_temp_files_are_cleaned(self):
        from stungkir.core.safety import clean_temp_files
        leftover = next(iter(self.texts)).with_name(".Глава 1.txt.tmp")
        leftover.write_bytes(b"\0\0")
        os.utime(leftover, (0, 0))
        self.assertEqual(clean_temp_files(), 1)
        self.assertFalse(leftover.exists())
