@echo off
rem Starts the DocuMind AI API using the virtual environment stored on C:.
rem Prerequisite: the MySQL service is running in the XAMPP Control Panel.
cd /d "%~dp0"
set PYTHON=C:\Users\Jidnyasa\documind-backend-venv\Scripts\python.exe
if not exist "%PYTHON%" (
  echo Python environment not found at %PYTHON%
  echo Create it with: python -m venv C:\Users\Jidnyasa\documind-backend-venv ^& then pip install -r requirements.txt
  exit /b 1
)
"%PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
