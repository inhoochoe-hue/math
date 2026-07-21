@echo off
chcp 65001 > nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo [1/3] 가상환경을 만듭니다.
  py -m venv .venv
)
echo [2/3] 필요한 패키지를 설치합니다.
.venv\Scripts\python.exe -m pip install -r requirements.txt
if not exist .env (
  copy .env.example .env > nul
  echo.
  echo .env 파일이 생성되었습니다. OPENAI_API_KEY를 입력한 뒤 다시 실행하세요.
  notepad .env
  pause
  exit /b 1
)
echo [3/3] 웹 화면을 엽니다.
.venv\Scripts\python.exe -m streamlit run app.py
pause
