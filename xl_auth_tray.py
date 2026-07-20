import base64
import binascii
import json
import os
import re
import signal
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import keyring
import pyotp
import requests
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from PySide6.QtCore import (
    QLibraryInfo,
    QLocale,
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    QTranslator,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

APP_NAME = "XLAuthenticatorTray"
KEYRING_SERVICE = "XLAuthenticatorTray"
KEYRING_USERNAME = "totp-secret"

DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 4646,
    "path_prefix": "/ffxivlauncher/",
}


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


ICON_PATH = resource_path("icons", "XIV-Auth-Tray.png")


@dataclass
class Config:
    host: str = "127.0.0.1"
    port: int = 4646
    path_prefix: str = "/ffxivlauncher/"


def config_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA ist nicht verfügbar.")
    folder = Path(appdata) / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "config.json"


_HOST_RE = re.compile(r"^[a-zA-Z0-9.\-]+$")
_PREFIX_RE = re.compile(r"^[a-zA-Z0-9/_.\-~]*$")


def _validate_config(data: dict) -> dict:
    host = str(data.get("host", DEFAULT_CONFIG["host"])).strip()
    if not host or not _HOST_RE.match(host):
        host = DEFAULT_CONFIG["host"]

    try:
        port = int(data.get("port", DEFAULT_CONFIG["port"]))
        if not (1 <= port <= 65535):
            port = DEFAULT_CONFIG["port"]
    except (ValueError, TypeError):
        port = DEFAULT_CONFIG["port"]

    path_prefix = str(data.get("path_prefix", DEFAULT_CONFIG["path_prefix"])).strip()
    if not path_prefix or not _PREFIX_RE.match(path_prefix) or ".." in path_prefix:
        path_prefix = DEFAULT_CONFIG["path_prefix"]

    return {"host": host, "port": port, "path_prefix": path_prefix}


def load_config() -> Config:
    path = config_path()
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError, FileNotFoundError):
        return Config()

    return Config(**_validate_config(data))


def save_config(config: Config) -> None:
    path = config_path()
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "host": config.host,
                "port": config.port,
                "path_prefix": config.path_prefix,
            },
            file,
            indent=2,
        )


class _OtpSignals(QObject):
    success = Signal(str, int)
    failure = Signal(str, str)


class _OtpWorker(QRunnable):
    """Sendet OTP im Hintergrund, damit der GUI-Thread nicht blockiert."""

    def __init__(self, url: str, host: str, port: int):
        super().__init__()
        self.url = url
        self.host = host
        self.port = port
        self.signals = _OtpSignals()

    @Slot()
    def run(self) -> None:
        try:
            response = requests.get(self.url, timeout=3)
            response.raise_for_status()
        except requests.RequestException as error:
            self.signals.failure.emit(self.url, str(error))
            return
        self.signals.success.emit(self.host, self.port)


SECRET_VERSION = 1
_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Leitet aus Passphrase + Salt einen Fernet-tauglichen Schlüssel via scrypt ab."""
    kdf = Scrypt(salt=salt, length=32, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def load_stored_blob() -> dict | None:
    """Lädt den gespeicherten Eintrag. Rückgabe: None, verschlüsseltes Blob-Dict
    (Schlüssel v/salt/ct) oder Legacy-Klartext als {"legacy": <secret>}."""
    raw = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("v") == SECRET_VERSION:
            return data
    except (ValueError, TypeError):
        pass
    return {"legacy": raw}


def store_encrypted_secret(secret: str, passphrase: str) -> bytes:
    """Verschlüsselt das Secret mit einem aus der Passphrase abgeleiteten Schlüssel
    und speichert das versionierte Blob im Credential Manager. Gibt den Key zurück."""
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    token = Fernet(key).encrypt(secret.encode("utf-8"))
    blob = {
        "v": SECRET_VERSION,
        "salt": base64.b64encode(salt).decode("ascii"),
        "ct": token.decode("ascii"),
    }
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, json.dumps(blob))
    return key


def has_stored_secret() -> bool:
    return load_stored_blob() is not None


def _zeroize(buffer: bytearray) -> None:
    """Überschreibt einen bytearray-Puffer im Speicher (best effort)."""
    for i in range(len(buffer)):
        buffer[i] = 0


class TrayApplication:
    def __init__(self, app: QApplication):
        """Initialisiert Tray-Icon, Kontextmenü und lädt die gespeicherte Konfiguration.

        Der abgeleitete Schlüssel wird nach dem Entsperren für die Session im RAM
        gehalten; das Secret selbst wird nur on-demand (beim Klick) entschlüsselt."""
        self.app = app
        self.config = load_config()
        self._active_workers: set[_OtpWorker] = set()
        self._fernet: Fernet | None = None
        self._ciphertext: bytes | None = None

        self.tray = QSystemTrayIcon(self.create_icon(), app)
        self.tray.setContextMenu(self.create_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self.app.aboutToQuit.connect(self._lock)
        self._unlock_on_start()
        self._update_tooltip()

    @staticmethod
    def create_icon() -> QIcon:
        return QIcon(str(ICON_PATH))

    def create_menu(self) -> QMenu:
        menu = QMenu()

        send_action = QAction("OTP senden", menu)
        send_action.triggered.connect(self.send_otp)
        menu.addAction(send_action)

        copy_action = QAction("OTP in Zwischenablage kopieren", menu)
        copy_action.triggered.connect(self.copy_otp)
        menu.addAction(copy_action)

        menu.addSeparator()

        secret_action = QAction("Secret setzen/ändern", menu)
        secret_action.triggered.connect(self.configure_secret)
        menu.addAction(secret_action)

        endpoint_action = QAction("XIVLauncher-Ziel konfigurieren", menu)
        endpoint_action.triggered.connect(self.configure_endpoint)
        menu.addAction(endpoint_action)

        menu.addSeparator()

        about_action = QAction("Status anzeigen", menu)
        about_action.triggered.connect(self.show_status)
        menu.addAction(about_action)

        quit_action = QAction("Beenden", menu)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)

        return menu

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.send_otp()

    def _update_tooltip(self) -> None:
        """Statischer Tooltip - kein Live-Code, damit das Secret nicht periodisch
        entschlüsselt werden muss (On-Demand-Prinzip)."""
        if not has_stored_secret():
            self.tray.setToolTip("XL Authenticator Tray - Secret fehlt")
        elif self._fernet is None:
            self.tray.setToolTip("XL Authenticator Tray - gesperrt")
        else:
            self.tray.setToolTip("XL Authenticator Tray - bereit (Klick = OTP)")

    @property
    def is_unlocked(self) -> bool:
        return self._fernet is not None and self._ciphertext is not None

    def _lock(self) -> None:
        """Verwirft den Session-Schlüssel und das Ciphertext aus dem RAM."""
        self._fernet = None
        self._ciphertext = None

    def _prompt_passphrase(self, title: str, label: str) -> str | None:
        text, accepted = QInputDialog.getText(
            None,
            title,
            label,
            echo=QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return None
        return text

    def _unlock_on_start(self) -> None:
        """Fragt beim Start die Master-Passphrase ab und leitet den Session-Schlüssel
        ab. Migriert vorhandene Klartext-Secrets (Legacy) transparent."""
        blob = load_stored_blob()
        if blob is None:
            return  # Noch kein Secret hinterlegt - Entsperren nicht nötig.

        if "legacy" in blob:
            self._migrate_legacy_secret(blob["legacy"])
            return

        try:
            salt = base64.b64decode(blob["salt"])
            ciphertext = blob["ct"].encode("ascii")
        except (KeyError, ValueError, binascii.Error):
            QMessageBox.critical(
                None,
                "Beschädigter Eintrag",
                "Der gespeicherte Secret-Eintrag ist ungültig. Bitte Secret neu setzen.",
            )
            return

        for _ in range(3):
            passphrase = self._prompt_passphrase(
                "Entsperren", "Master-Passphrase eingeben:"
            )
            if passphrase is None:
                self.app.quit()
                return
            fernet = Fernet(_derive_key(passphrase, salt))
            try:
                plaintext = bytearray(fernet.decrypt(ciphertext))
            except InvalidToken:
                QMessageBox.warning(
                    None, "Falsche Passphrase", "Die Passphrase ist nicht korrekt."
                )
                continue
            _zeroize(plaintext)
            self._fernet = fernet
            self._ciphertext = ciphertext
            return

        QMessageBox.critical(
            None,
            "Entsperren fehlgeschlagen",
            "Zu viele Fehlversuche. Die Anwendung wird beendet.",
        )
        self.app.quit()

    def _migrate_legacy_secret(self, legacy_secret: str) -> None:
        """Wandelt ein früher im Klartext gespeichertes Secret in das verschlüsselte
        Format um, indem einmalig eine Passphrase gesetzt wird."""
        QMessageBox.information(
            None,
            "Verschlüsselung einrichten",
            "Dein Secret liegt noch unverschlüsselt vor. Bitte lege jetzt eine "
            "Master-Passphrase fest, mit der es zukünftig geschützt wird.",
        )
        passphrase = self._set_new_passphrase()
        if passphrase is None:
            return
        key = store_encrypted_secret(legacy_secret.strip(), passphrase)
        self._fernet = Fernet(key)
        blob = load_stored_blob() or {}
        self._ciphertext = blob.get("ct", "").encode("ascii") or None
        self.tray.showMessage(
            "Verschlüsselt",
            "Dein Secret ist jetzt mit deiner Passphrase verschlüsselt.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _set_new_passphrase(self) -> str | None:
        """Fragt eine neue Passphrase zweimal ab und stellt Übereinstimmung sicher."""
        first = self._prompt_passphrase("Passphrase festlegen", "Neue Passphrase:")
        if first is None:
            return None
        if not first:
            QMessageBox.critical(
                None, "Ungültig", "Die Passphrase darf nicht leer sein."
            )
            return None
        second = self._prompt_passphrase(
            "Passphrase bestätigen", "Passphrase wiederholen:"
        )
        if second is None:
            return None
        if first != second:
            QMessageBox.critical(
                None, "Keine Übereinstimmung", "Die Passphrasen stimmen nicht überein."
            )
            return None
        return first

    def obtain_code(self) -> str | None:
        """Entschlüsselt das Secret nur für diesen Aufruf, erzeugt genau einen Code
        und überschreibt den Klartext-Puffer danach wieder (On-Demand)."""
        if not has_stored_secret():
            QMessageBox.warning(
                None,
                "Secret fehlt",
                "Bitte zuerst über das Tray-Menü ein TOTP-Secret setzen.",
            )
            return None

        if not self.is_unlocked:
            self._unlock_on_start()
            if not self.is_unlocked:
                return None

        try:
            plaintext = bytearray(self._fernet.decrypt(self._ciphertext))
        except InvalidToken:
            QMessageBox.critical(
                None,
                "Entschlüsselung fehlgeschlagen",
                "Das Secret konnte nicht entschlüsselt werden.",
            )
            return None

        try:
            code = pyotp.TOTP(plaintext.decode("utf-8")).now()
        except (ValueError, binascii.Error) as error:
            QMessageBox.critical(
                None,
                "Ungültiges Secret",
                f"Das gespeicherte TOTP-Secret konnte nicht verarbeitet werden:\n{error}",
            )
            return None
        finally:
            _zeroize(plaintext)

        return code

    def send_otp(self) -> None:
        code = self.obtain_code()
        if not code:
            return

        host = self.config.host.strip()
        port = self.config.port
        prefix = "/" + self.config.path_prefix.strip("/") + "/"

        url = f"http://{host}:{port}{prefix}{code}"

        worker = _OtpWorker(url, host, port)
        worker.setAutoDelete(False)
        self._active_workers.add(worker)
        worker.signals.success.connect(self._on_otp_success)
        worker.signals.failure.connect(self._on_otp_failure)
        worker.signals.success.connect(lambda *_: self._release_worker(worker))
        worker.signals.failure.connect(lambda *_: self._release_worker(worker))
        QThreadPool.globalInstance().start(worker)

    def _release_worker(self, worker: "_OtpWorker") -> None:
        self._active_workers.discard(worker)

    def _on_otp_success(self, host: str, port: int) -> None:
        self.tray.showMessage(
            "OTP gesendet",
            f"Code an {host}:{port} gesendet.",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def _on_otp_failure(self, url: str, error: str) -> None:
        msg = QMessageBox(
            QMessageBox.Icon.Critical,
            "OTP konnte nicht gesendet werden",
            "Prüfe, ob XIVLauncher läuft und die OTP-Makro-Unterstützung aktiviert ist.",
        )
        msg.setDetailedText(f"Ziel:\n{url}\n\nFehler:\n{error}")
        msg.exec()

    def copy_otp(self) -> None:
        code = self.obtain_code()
        if code:
            self.app.clipboard().setText(code)
            QTimer.singleShot(30000, lambda: self._clear_clipboard(code))
            self.tray.showMessage(
                "OTP kopiert",
                "Der aktuelle Code liegt in der Zwischenablage (wird nach 30s gelöscht).",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )

    def _clear_clipboard(self, code: str) -> None:
        clipboard = self.app.clipboard()
        if clipboard.text() == code:
            clipboard.clear()

    def configure_secret(self) -> None:
        secret, accepted = QInputDialog.getText(
            None,
            "TOTP-Secret setzen",
            "Base32-Secret oder Secret aus der otpauth://-URI:",
        )
        if not accepted or not secret.strip():
            return

        secret = secret.strip()
        if secret.lower().startswith("otpauth://"):
            parsed = urllib.parse.urlparse(secret)
            secret_values = urllib.parse.parse_qs(parsed.query).get("secret")
            if not secret_values:
                QMessageBox.critical(
                    None,
                    "Ungültige otpauth-URI",
                    "In der URI wurde kein secret= Parameter gefunden.",
                )
                return
            secret = secret_values[0]

        secret = secret.replace(" ", "").upper()
        try:
            pyotp.TOTP(secret).now()
        except (ValueError, binascii.Error) as error:
            QMessageBox.critical(
                None,
                "Secret ungültig",
                f"Das Secret ist kein gültiges Base32-TOTP-Secret:\n{error}",
            )
            return

        passphrase = self._set_new_passphrase()
        if passphrase is None:
            return

        key = store_encrypted_secret(secret, passphrase)
        self._fernet = Fernet(key)
        blob = load_stored_blob() or {}
        self._ciphertext = blob.get("ct", "").encode("ascii") or None
        self._update_tooltip()
        self.tray.showMessage(
            "Secret gespeichert",
            "Das Secret wurde verschlüsselt im Windows Credential Manager gespeichert.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def configure_endpoint(self) -> None:
        host, accepted = QInputDialog.getText(
            None,
            "XIVLauncher-Ziel",
            "Host oder IP-Adresse:",
            text=self.config.host,
        )
        if not accepted or not host.strip():
            return

        if not _HOST_RE.match(host.strip()):
            QMessageBox.critical(
                None,
                "Ungültiger Host",
                "Host darf nur Buchstaben, Ziffern, Punkt und Bindestrich enthalten.",
            )
            return

        port, accepted = QInputDialog.getInt(
            None,
            "XIVLauncher-Port",
            "Port:",
            value=self.config.port,
            minValue=1,
            maxValue=65535,
        )
        if not accepted:
            return

        self.config.host = host.strip()
        self.config.port = port
        save_config(self.config)
        self.tray.showMessage(
            "Ziel gespeichert",
            f"OTP-Ziel: {self.config.host}:{self.config.port}",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def show_status(self) -> None:
        if not has_stored_secret():
            secret_status = "fehlt"
        elif self.is_unlocked:
            secret_status = "vorhanden (entsperrt)"
        else:
            secret_status = "vorhanden (gesperrt)"
        QMessageBox.information(
            None,
            "XL Authenticator Tray",
            "Secret: " + secret_status + "\n"
            f"Ziel: {self.config.host}:{self.config.port}\n"
            f"Pfad: {self.config.path_prefix}",
        )


def main() -> None:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    app.setQuitOnLastWindowClosed(False)
    translator = QTranslator()
    translator.load(
        QLocale.system(),
        "qtbase",
        "_",
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
    )
    app.installTranslator(translator)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    tray_app = TrayApplication(app)  # noqa: F841
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
