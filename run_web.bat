@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python and enable Add Python to PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -m venv .venv
  if errorlevel 1 goto :error
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo Installing packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo .env was created. Enter your OPENAI_API_KEY, save, and run this file again.
  notepad ".env"
  pause
  exit /b 0
)

echo Starting web app...
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8502
exit /b 0

:error
echo.
echo Installation or startup failed. Review the error above.
pause
exit /b 1
