@echo off
REM Start Flask backend server

REM Activate virtual environment if it exists
if exist backend\venv\Scripts\activate.bat (
    call backend\venv\Scripts\activate.bat
)

REM Set PYTHONPATH to current directory
set PYTHONPATH=%CD%

REM Run Flask app
echo Starting Flask backend on http://localhost:5000...
python backend\app\main.py
