@echo off
setlocal enabledelayedexpansion

echo.
echo  Starting AI Architecture Designer...
echo.

if not exist venv\Scripts\activate.bat (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

if not exist .env (
    echo .env file not found. Run setup.bat first to create it.
    pause
    exit /b 1
)

REM ---- Validate that a real key was set ----
set "KEY_OK=0"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if "%%A"=="GROQ_API_KEY" (
        set "KEYVAL=%%B"
        if not "!KEYVAL!"=="your-groq-api-key-here" if not "!KEYVAL!"=="" (
            set "KEY_OK=1"
        )
    )
)

if "%KEY_OK%"=="0" (
    echo.
    echo ============================================
    echo  GROQ_API_KEY is not set in .env yet.
    echo  Open .env and paste your key, then re-run.
    echo  Free key: https://console.groq.com/keys
    echo ============================================
    echo.
    pause
    exit /b 1
)

echo Opening http://localhost:8501
echo Press Ctrl+C to stop the application.
echo.
streamlit run app.py --server.port 8501

pause
