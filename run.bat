@echo off
setlocal enabledelayedexpansion

:: Change to script directory
cd /d "%~dp0"

echo ============================================
echo   Starting Flask SimpleNotes Application
echo ============================================

:: Detect Python executable
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERROR] Python is required but not found in PATH.
        echo Please install Python 3 from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
)

:: Create virtual environment if not present
if not exist ".venv" (
    echo [*] Creating virtual environment (.venv)...
    %PYTHON_CMD% -m venv .venv
    echo [*] Installing requirements...
    .venv\Scripts\python -m pip install -q --upgrade pip
    .venv\Scripts\python -m pip install -q -r requirements.txt
) else (
    :: Verify dependencies are installed
    .venv\Scripts\python -c "import flask" >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [*] Installing requirements into existing virtualenv...
        .venv\Scripts\python -m pip install -q -r requirements.txt
    )
)

:: Seed sample notes if database doesn't exist
if not exist "notes.db" (
    echo [*] Seeding initial sample notes...
    .venv\Scripts\python sample_notes.py
)

set PORT=5000
echo.
echo ============================================
echo Application is ready!
echo Open your browser at: http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop the server.
echo ============================================
echo.

.venv\Scripts\python app.py
