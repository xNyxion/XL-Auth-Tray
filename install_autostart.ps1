<#
.SYNOPSIS
    Legt eine Autostart-Verknuepfung fuer XLAuthenticatorTray.exe an oder entfernt sie.
.DESCRIPTION
    Erzeugt eine .lnk-Verknuepfung im Windows-Startup-Ordner des aktuellen Users.
    Kein Admin noetig. Beim naechsten Login startet die App automatisch.
    
    Das Skript sucht die .exe im aktuellen Verzeichnis (PWD).
.PARAMETER Remove
    Entfernt die Autostart-Verknuepfung wieder.
.EXAMPLE
    cd ~/.local/bin
    C:\path\to\install_autostart.ps1
    
    Erstellt Autostart-Verknuepfung fuer die .exe im aktuellen Ordner
.EXAMPLE
    .\install_autostart.ps1 -Remove
    
    Entfernt die Autostart-Verknuepfung
#>
param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$startup = [Environment]::GetFolderPath("Startup")
$linkPath = Join-Path $startup "XLAuthenticatorTray.lnk"

if ($Remove) {
    if (Test-Path $linkPath) {
        Remove-Item $linkPath
        Write-Host "Autostart entfernt: $linkPath" -ForegroundColor Green
    } else {
        Write-Host "Keine Autostart-Verknuepfung gefunden." -ForegroundColor Yellow
    }
    return
}

# .exe im aktuellen Verzeichnis suchen
$exe = Join-Path (Get-Location) "XLAuthenticatorTray.exe"

if (-not (Test-Path $exe)) {
    throw "XLAuthenticatorTray.exe nicht gefunden in: $(Get-Location)`nWechsle in das Verzeichnis, das die .exe enthaelt."
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($linkPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = Split-Path $exe
$shortcut.IconLocation = "$exe,0"
$shortcut.Description = "XL Authenticator Tray"
$shortcut.Save()

Write-Host "Autostart eingerichtet: $linkPath" -ForegroundColor Green
Write-Host "Entfernen mit: .\install_autostart.ps1 -Remove"
