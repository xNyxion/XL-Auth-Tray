<#
.SYNOPSIS
    Legt eine Autostart-Verknuepfung fuer XLAuthenticatorTray.exe an oder entfernt sie.
.DESCRIPTION
    Erzeugt eine .lnk-Verknuepfung im Windows-Startup-Ordner des aktuellen Users.
    Kein Admin noetig. Beim naechsten Login startet die App automatisch.
    
    Das Skript sucht die .exe automatisch in:
    1. dist\ (relativ zum Skript) - fuer Entwickler nach build.ps1
    2. Aktuelles Verzeichnis (PWD) - fuer User mit installierter .exe
.PARAMETER Remove
    Entfernt die Autostart-Verknuepfung wieder.
.EXAMPLE
    .\install_autostart.ps1
    
    Im Repo nach build.ps1: Findet .exe in dist\
.EXAMPLE
    cd ~/.local/bin
    C:\path\to\install_autostart.ps1
    
    Als User: Findet .exe im aktuellen Verzeichnis
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

# .exe suchen: erst dist/ (Entwickler-Build), dann PWD (User-Installation)
$candidates = @(
    (Join-Path $PSScriptRoot "dist\XLAuthenticatorTray.exe"),
    (Join-Path (Get-Location) "XLAuthenticatorTray.exe")
)

$exe = $null
foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
        $exe = $candidate
        break
    }
}

if (-not $exe) {
    throw "XLAuthenticatorTray.exe nicht gefunden.`nGesucht in:`n  - $($PSScriptRoot)\dist\XLAuthenticatorTray.exe`n  - $(Get-Location)\XLAuthenticatorTray.exe"
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
