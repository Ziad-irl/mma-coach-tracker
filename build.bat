@echo off
REM Build a standalone 32-bit app in dist\MMACoachTracker\
REM Needs 32-bit Python 3.8 (python.org 3.8.10 "Windows x86 executable installer").
REM To use another interpreter:  set PYTHON=C:\path\to\python.exe
cd /d "%~dp0"
if "%PYTHON%"=="" set PYTHON=py -3.8-32
%PYTHON% -m pip install -r requirements-build.txt || goto :error
%PYTHON% -m unittest discover -s tests -t . || goto :error
%PYTHON% -m PyInstaller --noconfirm --clean --onedir --windowed --name MMACoachTracker launcher.py || goto :error
echo.
echo Done: dist\MMACoachTracker\MMACoachTracker.exe
goto :eof

:error
echo Build failed.
exit /b 1
