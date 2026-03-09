@echo off
echo ===============================================
echo    One Click Analysis - Stop All Servers
echo ===============================================
echo.

:: Kill any existing Python uvicorn processes
echo [1/3] Stopping Backend Server...
taskkill /f /im python.exe 2>nul
if %errorlevel%==0 (
    echo       Backend stopped.
) else (
    echo       No backend process found.
)

:: Kill Node.js processes (Vite dev server)
echo [2/3] Stopping Frontend Server...
taskkill /f /im node.exe 2>nul
if %errorlevel%==0 (
    echo       Frontend stopped.
) else (
    echo       No frontend process found.
)

echo.
echo [3/3] All servers stopped!
echo.
echo ===============================================
echo    Press any key to exit...
pause > nul
