<#
.SYNOPSIS
    Legt eine Autostart-Verknuepfung fuer XLAuthenticatorTray.exe an oder entfernt sie.
.DESCRIPTION
    Erzeugt eine .lnk-Verknuepfung im Windows-Startup-Ordner des aktuellen Users.
    Kein Admin noetig. Beim naechsten Login startet die App automatisch.
.PARAMETER Remove
    Entfernt die Autostart-Verknuepfung wieder.
#>
param(
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

$exe = Join-Path $root "dist\XLAuthenticatorTray.exe"
if (-not (Test-Path $exe)) {
    throw "exe nicht gefunden: $exe`nErst build.ps1 ausfuehren."
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
