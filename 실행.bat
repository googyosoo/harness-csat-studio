@echo off
chcp 65001 >nul
title Harness² CSAT Studio 실행기
color 0b

echo ======================================================================
echo    Harness² CSAT Studio — 수능·내신 영어 자가진화 출제 플랫폼
echo ======================================================================
echo.

:: 1. 파이썬 설치 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0c
    echo [오류] Python이 설치되어 있지 않거나 환경 변수(PATH)에 등록되지 않았습니다.
    echo https://www.python.org 에서 Python 3.10 이상을 설치하신 후
    echo 설치 시 'Add Python to PATH' 옵션을 반드시 체크해 주세요.
    echo.
    pause
    exit /b 1
)

echo [1/3] Python 환경 확인 완료:
python --version
echo.

:: 2. 필수 라이브러리 검사 및 설치
echo [2/3] 필수 패키지 검사 중...
python -c "import fastapi, uvicorn, edge_tts, hwpx" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 필요한 패키지(fastapi, uvicorn, edge-tts, python-hwpx)를 자동 설치합니다...
    pip install fastapi uvicorn edge-tts python-hwpx
    if %errorlevel% neq 0 (
        color 0c
        echo [경고] 패키지 설치 중 오류가 발생했습니다. 네트워크 연결을 확인해 주세요.
        echo.
        pause
        exit /b 1
    )
    echo [*] 패키지 설치가 완료되었습니다.
) else (
    echo [*] 필수 패키지가 모두 정상 설치되어 있습니다.
)
echo.

:: 3. 웹 스튜디오 실행
echo [3/3] Harness² CSAT Studio 웹 서버를 가동합니다...
echo [*] 잠시 후 기본 웹 브라우저가 자동으로 열립니다.
echo [*] 종료하려면 이 창에서 Ctrl+C 를 누르거나 창을 닫으세요.
echo.
python run_studio.py

if %errorlevel% neq 0 (
    echo.
    echo [오류] 서버 실행이 비정상 종료되었습니다.
    pause
)
