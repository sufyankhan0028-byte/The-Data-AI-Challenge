@echo off
REM Start RTIE FastAPI backend
REM Run from the backend/ directory

cd /d "%~dp0"
echo Starting RTIE Backend...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
