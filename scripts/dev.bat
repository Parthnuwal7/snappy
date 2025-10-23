@echo off
REM Development script for SNAPPY - Windows version
echo ========================================
echo Starting SNAPPY Development Environment
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Please install Node.js
    exit /b 1
)

REM Check for .env file
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env
)

REM Install backend dependencies if needed
if not exist backend\venv (
    echo.
    echo Installing Python dependencies...
    cd backend
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
    cd ..
)

REM Install frontend dependencies if needed
if not exist frontend\node_modules (
    echo.
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

REM Start backend
echo.
echo Starting Flask backend on port 5000...
start cmd /k "cd /d %CD% && backend\venv\Scripts\activate && set PYTHONPATH=%CD% && python -m backend.app.main"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
echo Starting React frontend on port 5173...
cd frontend
start cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo ✅ SNAPPY is starting!
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173
echo ========================================
echo.
echo Press any key to stop all servers...
pause >nul

REM Cleanup (kill processes)
taskkill /FI "WINDOWTITLE eq *flask*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq *vite*" /F >nul 2>&1
