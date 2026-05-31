@echo off
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║    One Click Analysis — AI Intelligence v2.0        ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ── Step 1: Start Backend ────────────────────────────────────────────────────
echo  [1/2] Starting Backend (FastAPI on port 8000)...
cd /d "%~dp0backend"
if exist venv\Scripts\activate.bat (
    start "Backend - FastAPI AI" cmd /k "call venv\Scripts\activate && python manage.py runserver"
) else if exist .venv\Scripts\activate.bat (
    start "Backend - FastAPI AI" cmd /k "call .venv\Scripts\activate && python manage.py runserver"
) else (
    start "Backend - FastAPI AI" cmd /k "python manage.py runserver"
)

:: ── Wait for backend to initialize ──────────────────────────────────────────
timeout /t 4 /nobreak > nul

:: ── Step 2: Start Frontend ───────────────────────────────────────────────────
echo  [2/2] Starting Frontend (Vite on port 5173)...
cd /d "%~dp0frontend"
start "Frontend - Vite" cmd /k "npm run dev"

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  Both servers starting!                             ║
echo  ║                                                     ║
echo  ║  Frontend :  http://localhost:5173                  ║
echo  ║  Backend  :  http://localhost:8000                  ║
echo  ║  API Docs :  http://localhost:8000/docs             ║
echo  ║                                                     ║
echo  ║  Login: admin@admin.com / Admin@2003                ║
echo  ║  After upload → AI Intelligence Dashboard           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
pause > nul
