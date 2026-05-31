# Arunka - Dev Environment Setup
# Run with: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Arunka Setup"

function Write-Step { param($msg) Write-Host "" ; Write-Host ">>> $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    [!!] $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "    [XX] $msg" -ForegroundColor Red ; exit 1 }

Write-Host ""
Write-Host "  ==============================================" -ForegroundColor Magenta
Write-Host "    ARUNKA  --  Setup"                           -ForegroundColor White
Write-Host "  ==============================================" -ForegroundColor Magenta
Write-Host ""

# -- 1. Python ----------------------------------------------------------------
Write-Step "Checking Python..."

$py = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                $py = $cmd
                break
            }
        }
    } catch {}
}

if ($py) {
    Write-OK "Found: $( & $py --version )"
} else {
    Write-Warn "Python 3.10+ not found -- attempting to install..."
    $installed = $false

    try {
        $wg = Get-Command winget -ErrorAction Stop
        winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
        $installed = $true
        Write-OK "Installed via winget"
    } catch {}

    if (-not $installed) {
        try {
            $pyUrl       = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
            $pyInstaller = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
            Write-Host "    Downloading Python 3.11.9..." -ForegroundColor Cyan
            Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing
            Start-Process -FilePath $pyInstaller `
                -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" `
                -Wait
            Remove-Item $pyInstaller -Force
            Write-OK "Python installed from python.org"
        } catch {
            Write-Fail "Could not install Python automatically.`nPlease install Python 3.10+ from https://python.org then re-run."
        }
    }

    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path    = $machinePath + ";" + $userPath
    $py = "python"
}

# -- 2. Virtual environment ---------------------------------------------------
Write-Step "Setting up virtual environment..."

$venvPath = Join-Path $PSScriptRoot ".venv"
if (-not (Test-Path $venvPath)) {
    & $py -m venv $venvPath
    Write-OK "Created .venv"
} else {
    Write-OK ".venv already exists -- skipping"
}

$pip  = Join-Path $venvPath "Scripts\pip.exe"
$pyEx = Join-Path $venvPath "Scripts\python.exe"

# -- 3. Python dependencies ---------------------------------------------------
Write-Step "Installing Python dependencies..."

& $pip install --upgrade pip --quiet
& $pip install -r (Join-Path $PSScriptRoot "requirements.txt") --quiet

Write-OK "Core packages installed (pywebview, opencv, adbutils, loguru, ...)"

# Optional: pytesseract for live skystone OCR
Write-Host ""
Write-Warn "OPTIONAL: For live skystone count in the HUD, install Tesseract OCR:"
Write-Warn "  1. Download from https://github.com/UB-Mannheim/tesseract/wiki"
Write-Warn "  2. Run: pip install pytesseract"
Write-Warn "  (Without it, skystones shows -- in the HUD. Everything else works fine.)"

# -- 4. ADB check -------------------------------------------------------------
Write-Step "Checking for adb..."

$adbFound = $false
foreach ($candidate in @(
    "C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
    "C:\Program Files (x86)\BlueStacks\HD-Adb.exe",
    "C:\ProgramData\BlueStacks\Client\HD-Adb.exe"
)) {
    if (Test-Path $candidate) { $adbFound = $true; Write-OK "Found adb at $candidate"; break }
}

if (-not $adbFound) {
    try { adb version 2>&1 | Out-Null; $adbFound = $true; Write-OK "adb found on PATH" } catch {}
}

if (-not $adbFound) {
    Write-Warn "adb not found. Downloading Android Platform Tools..."
    try {
        $ptUrl = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
        $ptZip = Join-Path $env:TEMP "platform-tools.zip"
        $ptDir = Join-Path $PSScriptRoot "platform-tools"
        Invoke-WebRequest -Uri $ptUrl -OutFile $ptZip -UseBasicParsing
        Expand-Archive -Path $ptZip -DestinationPath $PSScriptRoot -Force
        Remove-Item $ptZip -Force
        $env:Path = "$ptDir;" + $env:Path
        Write-OK "adb installed to platform-tools\"
    } catch {
        Write-Warn "Could not install adb automatically."
        Write-Warn "Install BlueStacks (includes HD-Adb.exe) or Android Platform Tools manually."
    }
}

# -- 5. Asset directories -----------------------------------------------------
Write-Step "Creating asset directories..."

foreach ($d in @("assets\templates", "assets", "history")) {
    $p = Join-Path $PSScriptRoot $d
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

$navPoints = Join-Path $PSScriptRoot "assets\nav_points.json"
$navRoutes = Join-Path $PSScriptRoot "assets\nav_routes.json"
if (-not (Test-Path $navPoints)) { '{}' | Set-Content $navPoints }
if (-not (Test-Path $navRoutes)) { '{}' | Set-Content $navRoutes }

Write-OK "Assets ready"

# -- 6. Launcher bat ----------------------------------------------------------
Write-Step "Creating launcher..."

$launcherPath    = Join-Path $PSScriptRoot "Arunka.bat"
$runPy           = Join-Path $PSScriptRoot "run.py"
$launcherContent = "@echo off`r`n`"$pyEx`" `"$runPy`"`r`npause"
Set-Content -Path $launcherPath -Value $launcherContent -Encoding ASCII
Write-OK "Created Arunka.bat"

# -- 7. Desktop shortcut ------------------------------------------------------
Write-Step "Creating desktop shortcut..."

try {
    $shell    = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\Arunka.lnk")
    $shortcut.TargetPath       = $launcherPath
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description      = "Arunka - Epic Seven Bot"
    $shortcut.Save()
    Write-OK "Shortcut added to Desktop"
} catch {
    Write-Warn "Could not create shortcut (non-critical)"
}

# -- Done ---------------------------------------------------------------------
Write-Host ""
Write-Host "  ==============================================" -ForegroundColor Green
Write-Host "    Setup complete!  Run Arunka.bat to start."  -ForegroundColor White
Write-Host "  ==============================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
