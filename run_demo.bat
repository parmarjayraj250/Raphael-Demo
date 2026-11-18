@echo off
setlocal enabledelayedexpansion
title Raphael AI - Celestial Edge (Demo Edition)
cd /d "%~dp0"

:: Detect Python
set "PY_CMD="
for %%C in ("py -3.11" "py -3.10" "py -3.12" "python" "py") do (
    if not defined PY_CMD (
        %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
        if !errorlevel! equ 0 set "PY_CMD=%%~C"
    )
)

if not defined PY_CMD (
    echo [ERROR] Python 3.10+ not found. Please run setup_demo.bat first.
    pause
    exit /b 1
)

%PY_CMD% raphael_demo.py
if %errorlevel% neq 0 (
    echo.
    echo Raphael Demo exited with code %errorlevel%
    pause
)
