@echo off
REM KPI Dashboard: rebuild + serve + system tray icon
REM Usage: double-click shortcut or run from terminal
REM Requires: Python 3.10+ with pythonw on PATH
cd /d "%~dp0"
where pythonw >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pythonw not found in PATH.
    echo Install Python 3.10+ from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b 1
)
start "" pythonw "%~dp0kpi_tray.py"
