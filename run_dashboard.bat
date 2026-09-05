@echo off
REM ============================================================
REM  Solar Flare Detection System - L1 - Dashboard launcher
REM  Double-click to start the server and open the browser.
REM    run_dashboard.bat            start the dashboard
REM    run_dashboard.bat refresh    rebuild dashboard_data first, then start
REM  Serves pre-computed outputs only (no live inference).
REM ============================================================
setlocal
cd /d "%~dp0"
title Solar Flare Detection System - L1

REM --- pick a Python launcher (python, else py) ---
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH.
  echo Install Python 3.10+ or add it to PATH, then re-run this file.
  pause
  exit /b 1
)

REM --- ensure the web dependencies are present (fastapi + uvicorn) ---
%PY% -c "import fastapi, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo [setup] Installing Python dependencies ^(one-time^)...
  %PY% -m pip install -r requirements.txt
  if errorlevel 1 (echo [ERROR] pip install failed. & pause & exit /b 1)
)

REM --- (re)build the pre-exported dashboard data ---
if /i "%~1"=="refresh" (
  echo [refresh] Rebuilding dashboard_data ...
  %PY% scripts\dashboard\export_dashboard_data.py || (echo [ERROR] export failed. & pause & exit /b 1)
  %PY% scripts\dashboard\export_wavelets.py       || (echo [ERROR] wavelet export failed. & pause & exit /b 1)
) else if not exist "dashboard_data\manifest.json" (
  echo [WARN] dashboard_data\manifest.json not found.
  echo Generating it now ^(one-time^)...
  %PY% scripts\dashboard\export_dashboard_data.py || (echo [ERROR] export failed. & pause & exit /b 1)
  %PY% scripts\dashboard\export_wavelets.py       || (echo [ERROR] wavelet export failed. & pause & exit /b 1)
)

echo.
echo  Solar Flare Detection System - L1
echo  Starting dashboard on http://127.0.0.1:8000
echo  (Leave this window open during the demo. Press Ctrl+C to stop.)
echo.

REM --- open the browser shortly after the server comes up ---
start "" /min cmd /c "timeout /t 3 >nul & start "" http://127.0.0.1:8000"

REM --- run the server (this blocks until Ctrl+C) ---
%PY% -m uvicorn app.dashboard_server:app --host 127.0.0.1 --port 8000

echo.
echo Server stopped.
pause
