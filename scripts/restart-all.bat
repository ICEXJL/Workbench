@echo off
setlocal enabledelayedexpansion
set "ROOT=%~dp0.."
set "PY=C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

echo ============================================
echo  Restart backend :8000  +  frontend :5173
echo ============================================
echo.

if not exist "%PY%" (
  echo [ERROR] python not found: %PY%
  pause
  exit /b 1
)

echo [1/3] Stopping old processes ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
)
ping -n 3 127.0.0.1 >nul

echo [2/3] Starting backend ...
start "backend :8000" /D "%ROOT%\backend" cmd /k "%PY%" -u main.py

echo [3/3] Starting frontend ...
start "frontend :5173" /D "%ROOT%\frontend" cmd /k npm run dev

echo.
echo Done. Two windows opened.
echo Wait about 8 seconds, then open: http://localhost:5173/
echo.
ping -n 7 127.0.0.1 >nul
