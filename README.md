# XL Auth Tray

Ein schlankes Windows-System-Tray-Tool für **Final Fantasy XIV**, das TOTP-Codes (One-Time Passwords) erzeugt und per Klick direkt an den [XIVLauncher](https://github.com/goatcorp/FFXIVQuickLauncher) sendet. Kein manuelles Abtippen des Authenticator-Codes mehr – ein Linksklick auf das Tray-Icon genügt.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)

## Features

- **OTP per Linksklick** – ein Klick auf das Tray-Icon sendet den aktuellen Code direkt an den XIVLauncher (HTTP GET).
- **Rechtsklick-Menü** mit allen Funktionen: OTP senden, OTP in die Zwischenablage kopieren, Secret setzen/ändern, XIVLauncher-Ziel konfigurieren, Status anzeigen und Beenden.
- **Sichere Secret-Speicherung** – das TOTP-Secret liegt im Windows Credential Manager (via `keyring`), nicht im Klartext auf der Platte.
- **`otpauth://`-Unterstützung** – URIs aus QR-Code-Tools können direkt eingefügt werden; das Secret wird automatisch extrahiert.
- **Zwischenablage mit Selbstlöschung** – ein kopierter Code wird nach 30 Sekunden automatisch aus der Zwischenablage entfernt.
- **Live-Tooltip** – der Tooltip des Tray-Icons zeigt jederzeit den aktuell gültigen OTP-Code an.
- **Konfigurierbares Ziel** – Host, Port und Pfad-Präfix werden in `%APPDATA%\XLAuthenticatorTray\config.json` gespeichert.
- **Als eigenständige `.exe`** – lässt sich mit PyInstaller zu einer einzelnen Datei bauen; Endnutzer brauchen kein installiertes Python.

## Voraussetzungen

- **Windows** (das Tool nutzt den Windows Credential Manager und den Startup-Ordner)
- **Python 3.11+**
- **pip** zum Installieren der Abhängigkeiten
- Ein laufender **XIVLauncher** mit aktivierter OTP-Makro-Unterstützung

## Installation

```powershell
# 1. Repository klonen
git clone https://github.com/xNyxion/XL-Auth-Tray.git
cd XL-Auth-Tray

# 2. Virtuelle Umgebung anlegen und aktivieren
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Starten
python xl_auth_tray.py
```

## Konfiguration

1. **Secret setzen** – Rechtsklick auf das Tray-Icon → **„Secret setzen/ändern"**. Es werden zwei Formate akzeptiert:
   - ein Base32-Secret (z. B. `JBSWY3DPEHPK3PXP`)
   - eine vollständige `otpauth://`-URI (z. B. aus einem QR-Code-Export) – das `secret=` wird automatisch ausgelesen.

   Das Secret wird geprüft und anschließend sicher im Windows Credential Manager abgelegt.

2. **XIVLauncher-Ziel konfigurieren** – Rechtsklick → **„XIVLauncher-Ziel konfigurieren"**, um Host und Port festzulegen. Standard ist `127.0.0.1:4646` mit dem Pfad-Präfix `/ffxivlauncher/`. Die Werte landen in `%APPDATA%\XLAuthenticatorTray\config.json`.

## Verwendung

- **Linksklick** auf das Tray-Icon → sendet den aktuellen OTP-Code sofort an den XIVLauncher.
- **Rechtsklick** öffnet das Kontextmenü:
  - **OTP senden** – identisch zum Linksklick.
  - **OTP in Zwischenablage kopieren** – legt den aktuellen Code in die Zwischenablage (wird nach 30 s automatisch gelöscht).
  - **Secret setzen/ändern** – TOTP-Secret hinterlegen oder ersetzen.
  - **XIVLauncher-Ziel konfigurieren** – Host und Port anpassen.
  - **Status anzeigen** – zeigt, ob ein Secret vorhanden ist, sowie das aktuelle Ziel und Pfad-Präfix.
  - **Beenden** – schließt die Anwendung.

Schlägt das Senden fehl, prüfe, ob der XIVLauncher läuft und die OTP-Makro-Unterstützung aktiviert ist.

## Als `.exe` bauen

Mit dem mitgelieferten Build-Skript entsteht eine eigenständige Onefile-Windowed-Anwendung:

```powershell
.\build.ps1
```

Das Skript installiert die Build-Abhängigkeiten (`pyinstaller`, `pillow`), erzeugt aus dem PNG ein `.ico` und baut das Ergebnis nach `dist\XLAuthenticatorTray.exe`. Die fertige `.exe` läuft ohne installiertes Python.

Optional lässt sich der Autostart direkt im Anschluss einrichten:

```powershell
.\build.ps1 -Autostart
```

## Autostart

Damit das Tool bei jeder Anmeldung automatisch startet, legt `install_autostart.ps1` eine Verknüpfung (`.lnk`) im Windows-Startup-Ordner des aktuellen Benutzers an – **kein Administrator nötig**:

```powershell
.\install_autostart.ps1
```

Entfernen des Autostarts:

```powershell
.\install_autostart.ps1 -Remove
```

## Technischer Hintergrund

TOTP (Time-based One-Time Password, RFC 6238) leitet den Code aus dem geteilten Secret und der aktuellen Uhrzeit ab – standardmäßig in 30-Sekunden-Intervallen. Deshalb muss die **Systemzeit korrekt gehen** (idealerweise per NTP synchronisiert), sonst erzeugt die App Codes, die der XIVLauncher als ungültig ablehnt.

## Credits

- Icon und OTP-Endpoint basieren auf dem [XIVLauncher](https://github.com/goatcorp/FFXIVQuickLauncher)-Projekt.
- Umgesetzt mit [PySide6](https://doc.qt.io/qtforpython/), [pyotp](https://github.com/pyauth/pyotp) und [keyring](https://github.com/jaraco/keyring).
