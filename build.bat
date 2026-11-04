@echo off
REM Build a standalone 32-bit app.
REM   build.bat                 -> dist\MMACoachTracker\
REM   build.bat spider-team     -> dist\SpiderTeam\  (name, icon and logo from brands\spider-team)
REM Needs 32-bit Python 3.8 (python.org 3.8.10 "Windows x86 executable installer").
REM To use another interpreter:  set PYTHON=C:\path\to\python.exe
cd /d "%~dp0"
if "%PYTHON%"=="" set PYTHON=py -3.8-32
set NAME=MMACoachTracker
set BRAND_ARGS=
if "%~1"=="" goto :build
if not exist "brands\%~1\brand.json" (
    echo Unknown brand "%~1": brands\%~1\brand.json not found.
    goto :error
)
for /f "usebackq delims=" %%n in (`%PYTHON% -c "import json; print(json.load(open(r'brands\%~1\brand.json', encoding='utf-8'))['exe'])"`) do set NAME=%%n
set BRAND_ARGS=--icon "brands\%~1\icon.ico" --add-data "brands\%~1;brand"

:build
%PYTHON% -m pip install -r requirements-build.txt || goto :error
%PYTHON% -m unittest discover -s tests -t . || goto :error
%PYTHON% -m PyInstaller --noconfirm --clean --onedir --windowed --name %NAME% %BRAND_ARGS% launcher.py || goto :error
echo.
echo Done: dist\%NAME%\%NAME%.exe
goto :eof

:error
echo Build failed.
exit /b 1
