@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Preparing the ScrapLab virtual environment...
  python setup_env.py
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo ScrapLab could not start. Read the error above and README.md.
pause
exit /b 1
