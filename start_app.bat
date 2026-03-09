@echo off
echo ===============================================
echo    One Click Analysis - Application Startup
echo ===============================================
echo.

:: Start Backend (FastAPI)
echo [1/2] Starting Backend Server (FastAPI on port 8000)...
cd /d "%~dp0backend"
start "Backend - FastAPI" cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak > nul

:: Start Frontend (Vite)
echo [2/2] Starting Frontend Server (Vite on port 5173)...
cd /d "%~dp0frontend"
start "Frontend - Vite" cmd /k "npm run dev"

echo.
echo ===============================================
echo    Both servers are starting!
echo ===============================================
echo.
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:5173
echo.
echo    Press any key to close this window...
pause > nul
