@echo off
setlocal EnableDelayedExpansion
title Argon Book Studio Pro - Typesetting and Publishing Engine
color 0B

cd /d "%~dp0"

echo ==============================================================================
echo       ARGON BOOK STUDIO PRO - DESKTOP PUBLISHING AND TYPESETTING ENGINE
echo ==============================================================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version') do set "PY_VER=%%v"
echo [*] Detected: !PY_VER!

echo [*] Checking publishing engine dependencies...
python -c "import fastapi, uvicorn, PIL, docx, ebooklib, httpx" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Installing missing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [*] Dependencies successfully installed!
) else (
    echo [*] All core publishing libraries verified.
)

echo [*] Checking Ollama Local AI Server...
curl.exe -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Starting Ollama local AI server in background...
    start "" /B "ollama" serve
    timeout /t 2 /nobreak >nul 2>&1
) else (
    echo [*] Ollama local AI server is active.
)

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [!] Notice: Port 8000 is currently occupied.
    echo [*] Launcher will automatically bind to the next available port.
)

echo.
echo ==============================================================================
echo   STARTING PUBLISHING STUDIO SERVER
echo   - 6x9 Mirrored Gutter Margins Active
echo   - Live Geometry and Margin Inspector Ready
echo   - Opening your default browser automatically...
echo.
echo   Press CTRL+C anytime in this window to stop the server.
echo ==============================================================================
echo.

python run.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Server exited with code %ERRORLEVEL%.
) else (
    echo.
    echo [INFO] Server stopped cleanly.
)
echo.
pause
