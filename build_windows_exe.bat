@echo off
setlocal
cd /d "%~dp0"
echo === CrosshairLab v0.2 Windows build (developer only) ===
where py >nul 2>nul
if errorlevel 1 (
  echo Python not found. Normal users should receive dist\CrosshairLab.exe instead.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name CrosshairLab app.py
if errorlevel 1 goto :fail
echo.
echo EXE created: %CD%\dist\CrosshairLab.exe
pause
exit /b 0
:fail
echo BUILD FAILED.
pause
exit /b 1
