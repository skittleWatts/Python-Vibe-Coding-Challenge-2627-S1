@echo off
setlocal
cd /d "%~dp0"
python setup_env.py
if errorlevel 1 (
  echo Setup failed. Install Python 3.11 or newer and try again.
  pause
  exit /b 1
)
echo Ready. Double-click launch.cmd to play.
pause
