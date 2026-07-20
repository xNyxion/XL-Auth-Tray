<#
.SYNOPSIS
    Baut XLAuthenticatorTray.exe mit PyInstaller.
.DESCRIPTION
    Installiert benoetigte Build-Abhaengigkeiten, erzeugt aus dem PNG ein .ico
    und baut eine Onefile-Windowed-exe nach dist\.
.PARAMETER Autostart
    Wenn gesetzt, wird nach dem Build automatisch die Autostart-Verknuepfung angelegt.
#>
param(
    [switch]$Autostart
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

# Python aus .venv bevorzugen, sonst System-Python
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "==> Build-Abhaengigkeiten pruefen/installieren..." -ForegroundColor Cyan
& $python -m pip install --quiet pyinstaller pillow

$png = ".\icons\XIV-Auth-Tray.png"
$ico = "icons\app.ico"

Write-Host "==> Icon erzeugen ($ico)..." -ForegroundColor Cyan
& $python -c "from PIL import Image; Image.open(r'$png').save(r'$ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"

Write-Host "==> exe bauen..." -ForegroundColor Cyan
& $python -m PyInstaller --noconfirm --onefile --windowed `
    --name XLAuthenticatorTray `
    --icon $ico `
    --add-data "$png;icons" `
    xl_auth_tray.py

$exe = Join-Path $root "dist\XLAuthenticatorTray.exe"
if (-not (Test-Path $exe)) {
    throw "Build fehlgeschlagen: $exe wurde nicht erzeugt."
}

Write-Host "==> Fertig: $exe" -ForegroundColor Green

if ($Autostart) {
    Write-Host "==> Autostart einrichten..." -ForegroundColor Cyan
    & (Join-Path $root "install_autostart.ps1")
}
