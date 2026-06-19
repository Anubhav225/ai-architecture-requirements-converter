@echo off
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo  AI Architecture Designer - Setup
echo ==========================================
echo.

REM ---- Check Python ----
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found.
    echo Install Python 3.9+ from https://python.org
    echo During install, check "Add Python to PATH".
    pause
    exit /b 1
)
echo [1/6] Python found:
python --version

REM ---- Create virtual environment ----
echo.
echo [2/6] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping.
) else (
    python -m venv venv
    echo Created venv.
)

REM ---- Activate ----
echo.
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat

REM ---- Upgrade pip ----
echo.
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM ---- Install requirements ----
echo.
echo [5/6] Installing dependencies (this may take a minute)...
pip install -r requirements.txt

REM ---- Generate .env if missing ----
echo.
echo [6/6] Checking environment file...
if exist .env (
    echo .env already exists - leaving it untouched.
) else (
    (
        echo # AI Architecture Designer - Environment Configuration
        echo #
        echo # 1. Get a FREE Groq API key at: https://console.groq.com/keys
        echo # 2. Paste it below after the equals sign
        echo #
        echo GROQ_API_KEY=your-groq-api-key-here
    ) > .env
    echo Created a new .env file.
)

echo.
echo ==========================================
echo  Setup complete.
echo ==========================================
echo.
echo NEXT STEP — required before the app will work:
echo   1. Open the .env file in this folder
echo   2. Replace "your-groq-api-key-here" with your real key
echo      Get one free at: https://console.groq.com/keys
echo   3. Save the file
echo   4. Run start_app.bat
echo.
pause
