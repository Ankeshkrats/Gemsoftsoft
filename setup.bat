@echo off
title Gemsoftsoft Setup
color 1F
echo.
echo  ==============================================
echo   GEMSOFTSOFT - Environment Setup
echo  ==============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo  [1/4] Python found. Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo  [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo  [3/4] Installing dependencies (Flask, Pillow, qrcode)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo  [4/4] Initialising database and seeding gemstone library...
python -c "from app import init_db; init_db(); print('  Database ready!')"
if errorlevel 1 (
    echo  [ERROR] Failed to initialise database.
    pause
    exit /b 1
)

echo.
echo  ==============================================
echo   Setup complete! Starting Gemsoftsoft...
echo  ==============================================
echo.
echo   URL:      http://127.0.0.1:5000
echo   Access:   Sign in or Create an account directly in browser
echo   Verify:   http://127.0.0.1:5000/verify
echo.
echo  Press Ctrl+C to stop the server.
echo.

python app.py
pause
