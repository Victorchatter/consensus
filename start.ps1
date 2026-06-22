# EchoTrader Local Startup Script (Windows PowerShell)
# Handles venv creation, dependency installation, and launching both services.

param(
    [switch]$InstallOnly,
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$root = $PSScriptRoot
if (-not $root) { $root = Get-Location }
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$venvDir = Join-Path $backendDir "venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$pipExe = Join-Path $venvDir "Scripts\pip.exe"

function Write-Header($text) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

# ── BACKEND SETUP ──────────────────────────────────────────────
if (-not $SkipBackend) {
    Write-Header "BACKEND SETUP"
    Set-Location $backendDir

    if (-not (Test-Path $venvDir)) {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
        python -m venv venv
    }

    if (-not (Test-Path $pythonExe)) {
        Write-Host "ERROR: venv Python not found at $pythonExe" -ForegroundColor Red
        Write-Host "Please ensure Python 3.11+ is installed and on your PATH." -ForegroundColor Red
        exit 1
    }

    # Install requirements (skip pip upgrade — causes TLS cert issues on fresh Windows venvs)
    Write-Host "Installing backend dependencies (this may take a minute)..." -ForegroundColor Yellow
    & $pythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Some packages may have failed. Trying again without cache..." -ForegroundColor Yellow
        & $pythonExe -m pip install --no-cache-dir -r requirements.txt
    }

    if ($InstallOnly) {
        Write-Host "Install complete. Exiting." -ForegroundColor Green
        exit 0
    }
}

# ── FRONTEND SETUP ─────────────────────────────────────────────
if (-not $SkipFrontend) {
    Set-Location $frontendDir
    if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
        Write-Header "FRONTEND SETUP"
        Write-Host "Installing frontend dependencies (npm install)..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: npm install failed. Ensure Node.js is installed." -ForegroundColor Red
            exit 1
        }
    }
}

# ── LAUNCH ─────────────────────────────────────────────────────
Write-Header "LAUNCHING ECHO TRADER"

$backendCmd = "cd '$backendDir'; if (Test-Path '$pythonExe') { & '$pythonExe' -m uvicorn main:app --reload --port 8000 } else { Write-Host 'Python venv missing!' -ForegroundColor Red }"
$frontendCmd = "cd '$frontendDir'; npm run dev"

$procs = @()

if (-not $SkipBackend) {
    Write-Host "Starting Backend  : http://localhost:8000" -ForegroundColor Gray
    $procs += Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -PassThru
}

if (-not $SkipFrontend) {
    Start-Sleep -Seconds 2
    Write-Host "Starting Frontend : http://localhost:5173" -ForegroundColor Gray
    $procs += Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -PassThru
}

Write-Host ""
Write-Host "EchoTrader is running!" -ForegroundColor Green
Write-Host "  API Docs : http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  App      : http://localhost:5173" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to shut down both services..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host "Shutting down..." -ForegroundColor Yellow
foreach ($p in $procs) {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
}
Write-Host "Done." -ForegroundColor Green
