# XL Auth Tray

> Windows System Tray-Anwendung zur automatischen Übermittlung von TOTP-Codes an den [XIVLauncher](https://github.com/goatcorp/FFXIVQuickLauncher).

## Features

- TOTP-Code-Generierung und automatische Übertragung an XIVLauncher
- Live-Anzeige des aktuellen OTP im Tray-Icon-Tooltip
- Sichere Speicherung des Secrets im Windows Credential Manager
- Optional: OTP in Zwischenablage kopieren (auto-clear nach 30s)
- Autostart-Unterstützung

## Installation

### Vorkompilierte Version

Lade `XLAuthenticatorTray.exe` aus den [Releases](https://github.com/xNyxion/XL-Auth-Tray/releases) und starte die Anwendung.

### Build aus Quellcode

```powershell
git clone https://github.com/xNyxion/XL-Auth-Tray.git
cd XL-Auth-Tray
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Direkt ausführen
python xl_auth_tray.py

# Oder: exe bauen
.\build.ps1

# Oder: exe bauen + direkt Autostart einrichten
.\build.ps1 -Autostart
```

## Verwendung

**Voraussetzung:** Der XIVLauncher muss laufen und die OTP-Makro-Unterstützung muss aktiviert sein (XIVLauncher → Einstellungen → In-Game → "Enable OTP macro support").

1. **Secret konfigurieren:** Rechtsklick auf Tray-Icon → "Secret setzen/ändern"
   - Base32-String (z.B. `JBSWY3DPEHPK3PXP`) oder
   - `otpauth://`-URI eingeben

   > **Sicherheitshinweis:** Das Secret wird im Windows Credential Manager gespeichert, nie im Klartext auf der Festplatte. Gib ausschließlich dein eigenes Secret ein.

2. **OTP senden:** Linksklick auf das Tray-Icon oder Rechtsklick → "OTP senden"

3. **Autostart aktivieren** (optional):
   ```powershell
   # Beim Build direkt aktivieren (empfohlen):
   .\build.ps1 -Autostart
   
   # Oder nachträglich im Repo-Verzeichnis:
   .\install_autostart.ps1
   
   # Oder wenn .exe woanders liegt (z.B. ~/.local/bin):
   cd ~/.local/bin
   C:\path\to\install_autostart.ps1
   ```

## Konfiguration

Standardmäßig sendet die App OTPs an `http://127.0.0.1:4646/ffxivlauncher/`. 

Zum Ändern: Rechtsklick → "XIVLauncher-Ziel konfigurieren"

Die Konfiguration wird in `%APPDATA%\XLAuthenticatorTray\config.json` gespeichert.

## Technologie

- **Python 3.12+** mit PySide6 (Qt)
- **pyotp** für TOTP-Generierung
- **keyring** für sichere Secret-Speicherung
- **PyInstaller** für Standalone-exe
- **GitHub Actions** für automatische Builds

## Lizenz

MIT — siehe [LICENSE](LICENSE)

---

*Inoffizielles Tool — nicht unterstützt von Square Enix oder dem XIVLauncher-Team*
