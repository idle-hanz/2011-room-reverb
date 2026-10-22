@echo off
title 2011 Room Reverb
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python environment - first run only...
  where py >nul 2>&1 && set "PYLA=py -3.14"
  if not defined PYLA where py >nul 2>&1 && set "PYLA=py -3"
  if not defined PYLA where python >nul 2>&1 && set "PYLA=python"
  if not defined PYLA (
    echo Python not found. Install from python.org and tick Add to PATH.
    pause
    exit /b 1
  )
  %PYLA% -m venv .venv
  if errorlevel 1 (
    echo Failed to create venv.
    pause
    exit /b 1
  )
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

REM If something is already serving 7860, just open the browser
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri http://127.0.0.1:7860/ -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL%==0 (
  echo App already running - opening browser...
  start "" "http://127.0.0.1:7860/"
  echo.
  echo Browser opened. You can close this window.
  timeout /t 4 >nul
  exit /b 0
)

echo Starting 2011 Room Reverb...
echo Opening http://127.0.0.1:7860/
echo Keep this window open while you use the app.
echo.
start "" "http://127.0.0.1:7860/"
python app_server.py
if errorlevel 1 (
  echo.
  echo Server stopped with an error.
  pause
)
