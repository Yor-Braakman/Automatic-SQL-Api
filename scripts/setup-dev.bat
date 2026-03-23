@echo off
REM Local development setup script for Windows

echo API Accelerator - Local Development Setup
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo Please edit .env file with your configuration before running the app
    pause
)

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo.
echo ==========================================
echo Setup complete!
echo ==========================================
echo.
echo To run the application:
echo   1. Activate the virtual environment: venv\Scripts\activate.bat
echo   2. Run the app: python main.py
echo   3. Access Swagger UI: http://localhost:8000/docs
echo.
echo To run tests:
echo   pytest tests/
echo.
pause
