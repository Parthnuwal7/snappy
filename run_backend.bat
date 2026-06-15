@echo off
REM Start Flask backend server

REM Activate virtual environment if it exists
if exist backend\venv\Scripts\activate.bat (
    call backend\venv\Scripts\activate.bat
)

REM Run Flask app as a module so 'app' is importable as a package
echo Starting Flask backend on http://localhost:5000...
cd backend
python -m app.main
