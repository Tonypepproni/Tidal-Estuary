@echo off
echo USGS Water Grid Application
echo ===========================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.6+ from https://python.org
    pause
    exit /b 1
)

REM Run setup if needed
if not exist "data\waterservices.usgs.gov.json" (
    echo Running first-time setup...
    python setup.py
    echo.
)

REM Start the application
echo Starting Water Grid Application...
echo Open your browser to: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server
echo.
python app.py

pause