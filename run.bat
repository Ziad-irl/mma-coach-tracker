@echo off
REM Start MMA Coach Tracker without a console window.
cd /d "%~dp0"
start "" pythonw -m mma_tracker
