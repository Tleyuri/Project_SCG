@echo off
cd /d "%~dp0"

start "BOQ Backend" cmd /k "cd backend && venv\Scripts\python -m uvicorn app.main:app --port 8000"
start "BOQ Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 3 >nul
start http://localhost:5173
