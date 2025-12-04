@echo off
setlocal EnableDelayedExpansion

pushd "%~dp0"

set "SCRIPT_DIR=%cd%"
set "PYTHON="

if exist "%SCRIPT_DIR%\..\ .venv311\Scripts\python.exe" set "PYTHON=%SCRIPT_DIR%\..\ .venv311\Scripts\python.exe"
if not defined PYTHON if exist "%SCRIPT_DIR%\..\ .venv\Scripts\python.exe" set "PYTHON=%SCRIPT_DIR%\..\ .venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"

if /I "%PYTHON%"=="python" (
    for /f "delims=" %%I in ('where python 2^>nul') do (
        set "PYTHON=%%~fI"
        goto :python_found
    )
    echo [ERROR] PATH에서 python 실행 파일을 찾을 수 없습니다.
    popd
    exit /b 1
) else (
    if not exist "%PYTHON%" (
        echo [ERROR] 지정된 Python 실행 파일을 찾을 수 없습니다: %PYTHON%
        popd
        exit /b 1
    )
)

:python_found
echo 사용 예정 파이썬: %PYTHON%

set "DIST_DIR=%SCRIPT_DIR%\dist"
set "INSTALLER_DIR=%DIST_DIR%\installer"

if exist "%DIST_DIR%" (
    echo 기존 dist 디렉터리를 정리합니다...
    rmdir /s /q "%DIST_DIR%"
)

echo === Step 1: PyInstaller 빌드 ===
"%PYTHON%" -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller가 설치되어 있지 않습니다. 설치를 진행합니다...
    "%PYTHON%" -m pip install --upgrade pyinstaller
    if errorlevel 1 goto error
)

"%PYTHON%" -m PyInstaller --noconfirm --clean airtouch.spec
if errorlevel 1 goto error

if not exist "%INSTALLER_DIR%" mkdir "%INSTALLER_DIR%"

echo === Step 2: Inno Setup 설치 파일 생성 ===
set "ISCC=%INNOSETUP_PATH%"
if not defined ISCC set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo [WARN] Inno Setup 컴파일러(ISCC.exe)를 찾을 수 없어 설치 파일 생성 단계를 건너뜁니다.
    goto success
)

"%ISCC%" airtouch.iss
if errorlevel 1 goto error

:success
echo.
echo 빌드가 완료되었습니다.
popd
exit /b 0

:error
echo.
echo [ERROR] 빌드 단계에서 오류가 발생했습니다.
popd
exit /b 1

