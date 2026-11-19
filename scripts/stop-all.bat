@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Stop backend :8000  +  frontend :5173
echo ============================================
echo.

set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
  echo   kill PID %%a  ^(port 8000^)
  taskkill /F /PID %%a >nul 2>&1
  set "FOUND=1"
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
  echo   kill PID %%a  ^(port 5173^)
  taskkill /F /PID %%a >nul 2>&1
  set "FOUND=1"
)

if "%FOUND%"=="0" echo   nothing running.

echo.
echo Done.
ping -n 4 127.0.0.1 >nul
