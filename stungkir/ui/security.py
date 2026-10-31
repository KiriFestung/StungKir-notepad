# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Главное окно: пароль и шифрование."""

from PySide6.QtWidgets import QMessageBox

from ..core import config as C
from ..core import storage as S
from ..core.storage import (LockedFile, build_lock, check_password, content_files, crypto_available, is_encrypted,
    lock_path, lock_version, make_backup, new_recovery_code, read_text, rewrap_lock, save_text, shred, write_lock)
from .dialogs import (
    CodeEntryDialog, PasswordDialog, RecoveryCodeDialog, ask_question, show_error, show_warning,
)


def recover_with_code(parent):
    """«Забыл пароль»: вход по коду восстановления и новый пароль. True - вошли."""
    if lock_version() == 1:
        show_warning(parent, "Код восстановления",
                     "Код восстановления появился в новой версии StungKir, а пароль ставили раньше - "
                     "для этих текстов кода ещё нет. Войди паролем: блокнот сразу предложит создать код.")
        return False
    if not CodeEntryDialog(parent, S.unlock_recovery).exec():
        return False
    dialog = PasswordDialog(parent, "Новый пароль", "Код подошёл. Придумай новый пароль.", confirm=True)
    if dialog.exec():
        try:
            rewrap_lock(password=dialog.password)
        except OSError as error:
            show_error(parent, "Новый пароль", f"Не получилось записать файл ключа, пароль прежний:\n{error}")
    return True


def offer_recovery_code(parent, password):
    """Пароль ставили до появления кода (ключ версии 1): даём код. Тексты при этом не меняются."""
    code = new_recovery_code()
    if not RecoveryCodeDialog(parent, code, "Теперь у пароля есть код восстановления: с ним забытый "
                              "пароль - не потеря всех текстов. Тексты при этом не перешифровываются.").exec():
        return False
    try:
        rewrap_lock(password=password, code=code)
    except OSError as error:
        show_error(parent, "Код восстановления", f"Не получилось записать файл ключа:\n{error}")
        return False
    return True


class SecurityMixin:
    """Пароль и шифрование. Часть главного окна."""

    # ---------------- пароль ----------------
    def _read_all(self):
        """Читает все тексты текущим ключом. Возвращает (тексты, файлы, которые не прочитались)."""
        texts, unreadable = {}, []
        for path in content_files():
            try:
                texts[path] = read_text(path)
            except (OSError, LockedFile):
                unreadable.append(path)
        return texts, unreadable

    def _write_all(self, texts, crypto):
        """Записывает тексты с ключом crypto (None - открыто) и проверяет каждый, перечитывая.
        Возвращает список файлов, которые не получилось записать правильно."""
        failed = []
        for path, text in texts.items():
            try:
                save_text(path, text, crypto=crypto)
                ok = read_text(path, crypto=crypto) == text and is_encrypted(path) == (crypto is not None)
            except (OSError, LockedFile):
                ok = False
            if not ok:
                failed.append(path)
        self.remember_own_write()
        return failed

    def _report(self, title, text, paths):
        names = [self._position_key(p) for p in paths]
        shown = "\n".join("• " + n for n in names[:12])
        if len(names) > 12:
            shown += f"\n…и ещё {len(names) - 12}"
        show_warning(self, title, f"{text}\n\n{shown}")

    def _replace_backups(self):
        """Затирает все старые архивы и делает новый. Возвращает число удалённых или None при сбое."""
        removed = 0
        if C.BACKUP_DIR.is_dir():
            for old in list(C.BACKUP_DIR.glob(f"{C.APP_NAME} *.zip")) + list(C.BACKUP_DIR.glob(f"{C.APP_NAME} *.part")):
                removed += shred(old)
        return removed if make_backup() else None

    def finish_encryption(self):
        """Если установка пароля оборвалась или с телефона пришли открытые файлы - дошифровывает их."""
        if S.CRYPTO is None:
            return
        plain = [p for p in content_files() if not is_encrypted(p)]
        if not plain:
            return
        texts = {}
        for path in plain:
            try:
                texts[path] = read_text(path)
            except (OSError, LockedFile):
                pass
        failed = self._write_all(texts, S.CRYPTO)
        done = len(texts) - len(failed)
        if done:
            self.toast.show_message(f"Дошифровал файлов: {done}", 3000)
        if failed or len(texts) < len(plain):
            self._report("Не всё зашифровано",
                         "Эти файлы остаются открытыми, их не получилось зашифровать:",
                         failed + [p for p in plain if p not in texts])

    def set_password(self):
        if not crypto_available():
            show_warning(self, "Пароль", "Для шифрования нужна библиотека cryptography.\n"
                                "Запусти install.sh ещё раз, он её поставит.")
            return
        warning = ask_question(
            self, "Поставить пароль",
            "Все тексты будут храниться зашифрованными.\n\n"
            "• Ты получишь код восстановления. Если потеряешь и пароль, и код, вернуть тексты не получится никак.\n"
            "• На телефоне через Syncthing файлы будут нечитаемы, "
            "пока не появится своя версия StungKir для телефона.\n"
            "• Названия глав и категорий остаются видны.\n\n"
            "Продолжить?")
        if warning != QMessageBox.Yes:
            return
        dialog = PasswordDialog(self, "Новый пароль", "Придумай пароль. Лучше фраза из нескольких слов.",
                                confirm=True)
        if not dialog.exec():
            return
        password = dialog.password       # окно после закрытия удаляется, пароль берём сразу
        code = new_recovery_code()
        if not RecoveryCodeDialog(self, code).exec():
            return
        if not self.save_everything():
            return
        from cryptography.fernet import Fernet
        master = Fernet.generate_key()
        crypto = Fernet(master)
        lock = build_lock(master, password, code)
        texts, unreadable = self._read_all()
        if unreadable:
            self._report("Пароль не поставлен",
                         "Эти файлы не получилось прочитать, поэтому я ничего не менял:", unreadable)
            return
        try:
            write_lock(lock)
        except OSError as error:
            show_error(self, "Пароль не поставлен", f"Не получилось записать файл ключа:\n{error}")
            return
        # с этого момента всё новое сохраняется зашифрованным
        S.CRYPTO, S.KEY = crypto, master
        failed = self._write_all(texts, crypto)
        if failed:
            self._report("Пароль поставлен, но не везде",
                         "Эти файлы пока остались незашифрованными. Пароль уже стоит, а при "
                         "следующем запуске StungKir попробует дошифровать их сам:", failed)
            return
        purged = self._replace_backups()
        self.recode_snapshots(None, crypto)
        message = f"Пароль поставлен: зашифровано файлов {len(texts)}."
        if purged is not None:
            message += f" Старые копии с открытым текстом удалены ({purged}), сделана новая зашифрованная."
        else:
            message += " Новую резервную копию сделать не получилось, проверь папку копий в настройках."
        show_warning(self, "Пароль поставлен", message)

    def change_password(self):
        current = PasswordDialog(self, "Сменить пароль", "Сначала введи нынешний пароль.",
                                 check=S.unlock, recover=recover_with_code)
        if not current.exec():
            return
        if current.recovered:
            self.toast.show_message("Пароль сменён")    # по коду новый пароль уже поставлен
            return
        dialog = PasswordDialog(self, "Новый пароль", "Придумай новый пароль. Тексты перешифровывать "
                                "не нужно - сменится только замок.", confirm=True)
        if not dialog.exec():
            return
        try:
            if lock_version() == 1:
                if not offer_recovery_code(self, dialog.password):
                    return
            else:
                rewrap_lock(password=dialog.password)
        except OSError as error:
            show_error(self, "Пароль", f"Не получилось записать файл ключа, пароль остался прежним:\n{error}")
            return
        self.toast.show_message("Пароль сменён")

    def new_recovery_code(self):
        current = PasswordDialog(self, "Новый код восстановления",
                                 "Старый код перестанет работать. Введи пароль для подтверждения.",
                                 check=S.unlock)
        if not current.exec():
            return
        password = current.password
        code = new_recovery_code()
        if not RecoveryCodeDialog(self, code).exec():
            return
        try:
            rewrap_lock(password=password if lock_version() == 1 else None, code=code)
        except OSError as error:
            show_error(self, "Код восстановления", f"Не получилось записать файл ключа:\n{error}")
            return
        self.toast.show_message("Новый код восстановления сохранён, старый больше не работает")

    def remove_password(self):
        dialog = PasswordDialog(self, "Снять пароль",
                                "Тексты снова будут храниться открыто. Введи пароль для подтверждения.",
                                check=lambda p: check_password(p) is not None)
        if not dialog.exec():
            return
        if not self.save_everything():
            return
        texts, unreadable = self._read_all()
        if unreadable:
            self._report("Пароль не снят",
                         "Эти файлы не открываются этим паролем. Чтобы они не остались без ключа, "
                         "я ничего не менял, пароль остаётся:", unreadable)
            return
        failed = self._write_all(texts, None)
        if failed:
            # часть файлов уже открыта, часть ещё нет: ключ и шифрование оставляем,
            # так что всё по-прежнему читается, а новое сохраняется зашифрованным
            self._report("Пароль не снят",
                         "Эти файлы не получилось расшифровать. Пароль остаётся, всё читается как раньше. "
                         "Можно попробовать ещё раз:", failed)
            return
        old_crypto = S.CRYPTO
        S.CRYPTO, S.KEY = None, None
        try:
            lock_path().unlink(missing_ok=True)
        except OSError as error:
            show_error(self, "Пароль", f"Файлы расшифрованы, но файл ключа не удалился:\n{error}")
            return
        backup = make_backup()
        self.recode_snapshots(old_crypto, None)
        message = f"Пароль снят: расшифровано файлов {len(texts)}."
        if not backup:
            message += " Новую резервную копию сделать не получилось."
        show_warning(self, "Пароль снят", message)
