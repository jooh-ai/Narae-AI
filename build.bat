@echo off
chcp 65001 >nul
REM ============================================================
REM  자재마스터 통합 도구 - 윈도우 exe 빌드 스크립트
REM  (파이썬이 설치된 윈도우 PC에서 이 파일을 더블클릭하세요)
REM ============================================================
cd /d "%~dp0"

echo [1/2] 필요한 라이브러리 설치 중...
python -m pip install --upgrade openpyxl pyinstaller
if errorlevel 1 (
  echo.
  echo X 파이썬 또는 pip 를 찾지 못했습니다.
  echo   https://www.python.org/downloads/ 에서 파이썬을 먼저 설치하세요.
  echo   설치 시 "Add python.exe to PATH" 를 반드시 체크하세요.
  pause
  exit /b 1
)

echo.
echo [2/2] exe 빌드 중...
pyinstaller --onefile --console --name MasterTool master_tool.py
if errorlevel 1 (
  echo.
  echo X 빌드에 실패했습니다.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  완료!  dist\MasterTool.exe  를 확인하세요.
echo  처리할 엑셀 파일들을 exe 와 같은 폴더에 두고 실행하면 됩니다.
echo ============================================================
pause
