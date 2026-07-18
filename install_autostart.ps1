<#
.SYNOPSIS
    Legt eine Autostart-Verknuepfung fuer XLAuthenticatorTray.exe an oder entfernt sie.
.DESCRIPTION
    Erzeugt eine .lnk-Verknuepfung im Windows-Startup-Ordner des aktuellen Users.
    Kein Admin noetig. Beim naechsten Login startet die App automatisch.
.PARAMETER Path
    Pfad zur .exe oder zum Verzeichnis, das die .exe enthaelt.
    Wenn weggelassen, wird in folgender Reihenfolge gesucht:
    1. ~\.local\bin\XLAuthenticatorTray.exe
    2. dist\XLAuthenticatorTray.exe (relativ zum Skript)
.PARAMETER Remove
    Entfernt die Autostart-Verknuepfung wieder.
.EXAMPLE
    .\install_autostart.ps1
    Erstellt Autostart-Verknuepfung (sucht .exe automatisch)
.EXAMPLE
    .\install_autostart.ps1 -Path .
    Nutzt XLAuthenticatorTray.exe aus dem aktuellen Verzeichnis
.EXAMPLE
    .\install_autostart.ps1 -Path C:\Users\Andy\.local\bin
    Nutzt .exe aus dem angegebenen Verzeichnis
.EXAMPLE
    .\install_autostart.ps1 -Remove
    Entfernt die Autostart-Verknuepfung
#>
param(
    [string]$Path,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

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

# .exe-Pfad ermitteln
$exe = $null

if ($Path) {
    # Parameter wurde angegeben
    if (Test-Path $Path -PathType Leaf) {
        # Es ist eine Datei
        $exe = $Path
    } elseif (Test-Path $Path -PathType Container) {
        # Es ist ein Verzeichnis
        $exe = Join-Path $Path "XLAuthenticatorTray.exe"
    } else {
        throw "Pfad nicht gefunden: $Path"
    }
} else {
    # Automatische Suche
    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\XLAuthenticatorTray.exe"),
        (Join-Path $root "dist\XLAuthenticatorTray.exe")
    )
    
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            $exe = $candidate
            break
        }
    }
}

if (-not $exe -or -not (Test-Path $exe)) {
    throw "exe nicht gefunden. Gesucht in:`n  - $($env:USERPROFILE)\.local\bin\XLAuthenticatorTray.exe`n  - $root\dist\XLAuthenticatorTray.exe`nOder nutze: .\install_autostart.ps1 -Path <pfad>"
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
