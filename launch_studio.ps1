# Argon Book Studio Pro - PowerShell Launcher
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "      ARGON BOOK STUDIO PRO - DESKTOP PUBLISHING AND TYPESETTING ENGINE       " -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python was not found in your PATH!" -ForegroundColor Red
    Write-Host "Please ensure Python 3.10+ is installed and added to PATH." -ForegroundColor Yellow
    pause
    exit 1
}

$pyVer = & python --version 2>&1
Write-Host "[*] Detected: $pyVer" -ForegroundColor Green

# Check and auto-start Ollama Local AI Server
$ollamaCheck = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue
if (-not $ollamaCheck) {
    Write-Host "[*] Starting Ollama local AI server in background..." -ForegroundColor Cyan
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "[*] Ollama local AI server is active." -ForegroundColor Green
}

# Check port 8000
$portInUse = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "[!] Port 8000 is occupied. Launcher will automatically bind to the next available port." -ForegroundColor Yellow
}

Write-Host "[*] Launching Argon Book Studio..." -ForegroundColor Cyan
python run.py
