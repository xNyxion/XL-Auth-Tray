# XL Auth Tray

Eine schlanke Windows System Tray-Anwendung zur automatischen Übermittlung von TOTP-basierten Einmalpasswörtern (OTP) an den [XIVLauncher](https://github.com/goatcorp/FFXIVQuickLauncher) für Final Fantasy XIV.

## 🎯 Übersicht

**XL Auth Tray** vereinfacht den Login-Prozess in Final Fantasy XIV, indem es TOTP-Codes direkt an den XIVLauncher sendet. Die Anwendung läuft unauffällig im System Tray und ermöglicht per Klick oder Tastenkombination die automatische Übertragung des aktuell gültigen Einmalpassworts.

## ✨ Features

- **🔐 TOTP-Code-Generierung:** Generiert zeitbasierte Einmalpasswörter nach RFC 6238
- **📤 Automatische Übertragung:** Sendet OTP-Codes direkt an den XIVLauncher über HTTP
- **📋 Zwischenablage-Unterstützung:** Kopiert OTP-Codes in die Zwischenablage (automatische Löschung nach 30 Sekunden)
- **🖥️ System Tray Integration:** Unauffällige Hintergrund-Anwendung mit kontextbasiertem Menü
- **🔄 Live-Tooltip:** Zeigt den aktuellen OTP-Code direkt im Tray-Icon-Tooltip an
- **🔒 Sichere Speicherung:** Nutzt den Windows Credential Manager für die sichere Aufbewahrung des TOTP-Secrets
- **⚙️ Konfigurierbar:** Anpassbare XIVLauncher-Verbindungsparameter (Host, Port, Pfad)
- **🚀 Autostart-Unterstützung:** Optionale automatische Ausführung beim Windows-Start
- **🌐 Flexibles Secret-Format:** Unterstützt Base32-Strings und `otpauth://` URIs

## 📦 Installation

### Vorkompilierte Binärdatei

1. Lade die neueste `XLAuthenticatorTray.exe` aus den [Releases](https://github.com/xNyxion/XL-Auth-Tray/releases) herunter
2. Platziere die .exe in einem permanenten Verzeichnis (z.B. `C:\Program Files\XLAuthTray\`)
3. Führe die Anwendung aus — das Tray-Icon erscheint in der Taskleiste

### Build aus Quellcode

**Voraussetzungen:**
- Python 3.12 oder höher
- Windows-Betriebssystem

**Schritte:**

```powershell
# Repository klonen
git clone https://github.com/xNyxion/XL-Auth-Tray.git
cd XL-Auth-Tray

# (Optional) Virtuelle Umgebung erstellen
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung direkt ausführen
python xl_auth_tray.py

# ODER: Kompilierte .exe bauen
.\build.ps1

# ODER: Mit automatischer Autostart-Konfiguration bauen
.\build.ps1 -Autostart
```

Die fertige `.exe` befindet sich nach dem Build in `dist\XLAuthenticatorTray.exe`.

## 🚀 Erste Schritte

### 1. TOTP-Secret konfigurieren

Beim ersten Start muss ein TOTP-Secret hinterlegt werden:

1. Rechtsklick auf das Tray-Icon
2. Wähle **"Secret setzen/ändern"**
3. Gib entweder ein:
   - Das **Base32-kodierte Secret** (z.B. `JBSWY3DPEHPK3PXP`)
   - Eine vollständige **otpauth://-URI** (z.B. `otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example`)

Das Secret wird sicher im **Windows Credential Manager** gespeichert.

### 2. XIVLauncher-Verbindung einrichten

Standardmäßig sendet die Anwendung OTPs an `http://127.0.0.1:4646/ffxivlauncher/`. Falls deine XIVLauncher-Installation andere Parameter nutzt:

1. Rechtsklick auf das Tray-Icon
2. Wähle **"XIVLauncher-Ziel konfigurieren"**
3. Gib den gewünschten Host/IP und Port ein

### 3. OTP senden

Es gibt mehrere Möglichkeiten, einen OTP-Code zu senden:

- **Linksklick auf das Tray-Icon** (schnellste Methode)
- Rechtsklick → **"OTP senden"**
- Rechtsklick → **"OTP in Zwischenablage kopieren"** (für manuelles Einfügen)

Der aktuelle OTP-Code wird auch dauerhaft im **Tooltip des Tray-Icons** angezeigt.

## 🔧 Konfiguration

### Konfigurationsdatei

Die Anwendung speichert ihre Einstellungen in:

```
%APPDATA%\XLAuthenticatorTray\config.json
```

**Standard-Konfiguration:**

```json
{
  "host": "127.0.0.1",
  "port": 4646,
  "path_prefix": "/ffxivlauncher/"
}
```

### Autostart einrichten

Um XL Auth Tray automatisch beim Windows-Start zu laden:

```powershell
# Autostart aktivieren
.\install_autostart.ps1

# Autostart deaktivieren
.\install_autostart.ps1 -Remove
```

Das Skript erstellt eine Verknüpfung im Windows-Startup-Ordner (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`).

## 🛠️ Technologie-Stack

| Komponente | Technologie | Zweck |
|-----------|-------------|-------|
| **Sprache** | Python 3.12+ | Hauptimplementierung |
| **GUI-Framework** | PySide6 (Qt 6) | System Tray-Integration und UI-Dialoge |
| **TOTP-Bibliothek** | pyotp 2.10.0 | Generierung zeitbasierter Einmalpasswörter |
| **Secret-Verwaltung** | keyring 25.7.0 | Sichere Speicherung im Windows Credential Manager |
| **HTTP-Client** | requests 2.34.2 | Übertragung der OTP-Codes an XIVLauncher |
| **Packaging** | PyInstaller | Erstellung einer Standalone-.exe |
| **CI/CD** | GitHub Actions | Automatische Builds und Releases |

## 📁 Projektstruktur

```
XL-Auth-Tray/
├── xl_auth_tray.py           # Hauptanwendung (GUI, TOTP-Logik, Konfiguration)
├── requirements.txt          # Python-Abhängigkeiten
├── build.ps1                 # Build-Skript (PyInstaller)
├── install_autostart.ps1     # Autostart-Verwaltung
├── icons/
│   └── XIVLauncher-Icon-Transparent.png  # Tray-Icon
├── .github/
│   └── workflows/
│       └── build.yml         # CI/CD-Pipeline
└── LICENSE                   # MIT-Lizenz
```

## 🏗️ Architektur

### Kernkomponenten

1. **`TrayApplication`**: Hauptklasse für die System Tray-Verwaltung
   - Erstellt das Tray-Icon und Kontextmenü
   - Verwaltet TOTP-Timer und Tooltip-Aktualisierung
   - Koordiniert Benutzereingaben und OTP-Übertragung

2. **`_OtpWorker`**: Hintergrund-Thread für HTTP-Anfragen
   - Sendet OTP-Codes asynchron an XIVLauncher
   - Verhindert UI-Blockierungen durch Netzwerk-I/O

3. **Konfigurationsverwaltung**:
   - `load_config()` / `save_config()`: JSON-basierte Persistierung
   - `_validate_config()`: Input-Validierung für Host/Port/Pfad

4. **Secret-Handling**:
   - `get_secret()` / `set_secret()`: Wrapper für Windows Credential Manager
   - Unterstützt `otpauth://`-URI-Parsing

### Sicherheitsmerkmale

- **Kein Klartext-Secret**: Das TOTP-Secret wird niemals in Konfigurationsdateien oder Logs gespeichert
- **Windows Credential Manager**: Nutzt das verschlüsselte Betriebssystem-Keyring
- **Input-Validierung**: Host-, Port- und Pfad-Parameter werden vor Verwendung validiert
- **Clipboard-Auto-Clear**: Kopierte OTPs werden nach 30 Sekunden automatisch aus der Zwischenablage entfernt

## 🐛 Fehlersuche

### OTP wird nicht gesendet

**Symptom:** Fehlermeldung "OTP konnte nicht gesendet werden"

**Lösungsansätze:**
1. Stelle sicher, dass der **XIVLauncher läuft**
2. Prüfe, ob die **OTP-Makro-Unterstützung** im XIVLauncher aktiviert ist
3. Überprüfe die Verbindungsparameter (Rechtsklick → "XIVLauncher-Ziel konfigurieren")
4. Teste manuell: Öffne `http://127.0.0.1:4646/ffxivlauncher/123456` im Browser (sollte eine Antwort geben)

### Ungültiges Secret

**Symptom:** "Das gespeicherte TOTP-Secret konnte nicht verarbeitet werden"

**Lösungsansätze:**
1. Setze das Secret neu (Rechtsklick → "Secret setzen/ändern")
2. Stelle sicher, dass das Secret in **Base32-Format** vorliegt (nur Großbuchstaben A-Z und Ziffern 2-7)
3. Entferne Leerzeichen aus dem Secret-String
4. Bei `otpauth://`-URIs: Prüfe, ob der `secret=`-Parameter vorhanden ist

### Tray-Icon wird nicht angezeigt

**Symptom:** Die Anwendung startet, aber kein Icon erscheint

**Lösungsansätze:**
1. Prüfe die Windows-Einstellungen für System Tray-Icons
2. Rechtsklick auf die Taskleiste → "Taskleisteneinstellungen" → "Ausgeblendete Symbole auswählen"
3. Stelle sicher, dass `icons/XIVLauncher-Icon-Transparent.png` vorhanden ist

## 🤝 Mitwirken

Beiträge sind willkommen! Wenn du Bugs findest oder neue Features vorschlagen möchtest:

1. Erstelle ein [Issue](https://github.com/xNyxion/XL-Auth-Tray/issues)
2. Forke das Repository
3. Erstelle einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
4. Committe deine Änderungen (`git commit -m 'Add some AmazingFeature'`)
5. Pushe den Branch (`git push origin feature/AmazingFeature`)
6. Öffne einen Pull Request

## 📄 Lizenz

Dieses Projekt ist unter der **MIT-Lizenz** lizenziert. Siehe [LICENSE](LICENSE) für Details.

## 🙏 Danksagungen

- **[XIVLauncher](https://github.com/goatcorp/FFXIVQuickLauncher)** — Der schnellere FFXIV-Launcher mit OTP-Makro-Support
- **[pyotp](https://github.com/pyauth/pyotp)** — TOTP-Implementierung für Python
- **[PySide6](https://wiki.qt.io/Qt_for_Python)** — Qt-Bindings für Python

---

**Hinweis:** Diese Anwendung ist ein inoffizielles Tool und wird weder von Square Enix noch vom XIVLauncher-Team offiziell unterstützt.
