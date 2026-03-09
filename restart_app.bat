@echo off
echo Stopping existing processes...
taskkill /F /IM node.exe
taskkill /F /IM python.exe
echo Cleaned up.

echo Starting Backend...
start "Backend Server" cmd /k "cd backend && uvicorn main:app --reload"

echo Starting Frontend...
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo Application restarting...
timeout /t 5
start http://localhost:5173
