import binascii
import json
import os
import re
import signal
import sys
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import keyring
import pyotp
import requests
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


ICON_PATH = resource_path("icons", "XIVLauncher-Icon-Transparent.png")


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


TOTP_INTERVAL = 30

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


def get_secret() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)


def set_secret(secret: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, secret.strip())


class TrayApplication:
    def __init__(self, app: QApplication):
        self.app = app
        self.config = load_config()
        self._active_workers: set[_OtpWorker] = set()
        self.tray = QSystemTrayIcon(self.create_icon(), app)
        self.tray.setToolTip("XL Authenticator Tray")
        self.tray.setContextMenu(self.create_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self._schedule_tooltip_refresh()

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

    def _schedule_tooltip_refresh(self) -> None:
        self.refresh_tooltip()
        remaining_ms = int((TOTP_INTERVAL - time.time() % TOTP_INTERVAL) * 1000) + 50
        QTimer.singleShot(remaining_ms, self._schedule_tooltip_refresh)

    def refresh_tooltip(self) -> None:
        secret = get_secret()
        if not secret:
            self.tray.setToolTip("XL Authenticator Tray - Secret fehlt")
            return

        try:
            code = pyotp.TOTP(secret).now()
            self.tray.setToolTip(f"XL Authenticator Tray - OTP {code}")
        except (ValueError, binascii.Error):
            self.tray.setToolTip("XL Authenticator Tray - ungültiges Secret")

    def obtain_code(self) -> str | None:
        secret = get_secret()
        if not secret:
            QMessageBox.warning(
                None,
                "Secret fehlt",
                "Bitte zuerst über das Tray-Menü ein TOTP-Secret setzen.",
            )
            return None

        try:
            return pyotp.TOTP(secret).now()
        except (ValueError, binascii.Error) as error:
            QMessageBox.critical(
                None,
                "Ungültiges Secret",
                f"Das gespeicherte TOTP-Secret konnte nicht verarbeitet werden:\n{error}",
            )
            return None

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

        set_secret(secret)
        self.refresh_tooltip()
        self.tray.showMessage(
            "Secret gespeichert",
            "Das Secret wurde im Windows Credential Manager gespeichert.",
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
        secret_status = "vorhanden" if get_secret() else "fehlt"
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
