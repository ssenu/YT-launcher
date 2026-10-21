<#
.SYNOPSIS
  PyInstaller로 앱을 묶고 Inno Setup으로 설치 프로그램과 SHA256SUMS.txt를 만든다.
.EXAMPLE
  ./scripts/build.ps1
  ./scripts/build.ps1 -Version 0.2.0 -Python python
#>
param(
    [string]$Version,
    [string]$Python
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not $Python) {
    $venv = Join-Path $root ".venv\Scripts\python.exe"
    $Python = if (Test-Path $venv) { $venv } else { "python" }
}
if (-not $Version) {
    $Version = (& $Python -c "from yt_launcher.version import __version__; print(__version__)").Trim()
}
Write-Host "Building YT Launcher $Version"

& $Python -m PyInstaller --noconfirm --clean --windowed `
    --name YTLauncher `
    --icon "src\yt_launcher\assets\icon.ico" `
    --add-data "src\yt_launcher\assets;yt_launcher\assets" `
    --paths src `
    --distpath dist --workpath build `
    launcher.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
$icon = Join-Path $root "dist\YTLauncher\_internal\yt_launcher\assets\icon.png"
if (-not (Test-Path $icon)) { throw "icon.png가 묶음에 없습니다: $icon" }

$iscc = $null
$command = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($command) { $iscc = $command.Source }
if (-not $iscc) {
    $iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) { throw "ISCC.exe를 찾을 수 없습니다. Inno Setup 6을 설치하세요." }

& $iscc "/DAppVersion=$Version" "installer\setup.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }

$setupName = "YT-Launcher-Setup-$Version.exe"
$setupPath = Join-Path $root "dist\installer\$setupName"
$hash = (Get-FileHash $setupPath -Algorithm SHA256).Hash.ToLower()
"$hash  $setupName" | Set-Content (Join-Path $root "dist\installer\SHA256SUMS.txt") -Encoding ascii
Write-Host "Done: $setupPath"
