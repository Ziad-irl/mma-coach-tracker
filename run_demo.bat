@echo off
REM Start the app in demo mode: sample data in data\demo.db, real data untouched.
cd /d "%~dp0"
start "" pythonw -m mma_tracker --demo
