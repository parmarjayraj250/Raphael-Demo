@echo off
setlocal enabledelayedexpansion
title Raphael AI (Demo Edition) - Setup
cd /d "%~dp0"

echo ======================================================================
echo           Raphael AI (Celestial Edge - Demo Edition) Setup
echo ======================================================================
echo.

:: Detect Python
set "PY_CMD="
for %%C in ("py -3.11" "py -3.10" "py -3.12" "python" "py") do (
    if not defined PY_CMD (
        %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
        if !errorlevel! equ 0 set "PY_CMD=%%~C"
    )
)

if not defined PY_CMD (
    echo [ERROR] Python 3.10 or higher was not detected on this PC.
    echo Please install Python 3.10, 3.11, or 3.12 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [*] Found compatible Python: %PY_CMD%
echo.
echo Installing lightweight demo dependencies...
%PY_CMD% -m pip install --upgrade pip >nul 2>&1
%PY_CMD% -m pip install -r requirements-demo.txt
if %errorlevel% neq 0 (
    echo [!] Some optional packages failed to install, but core components may still run.
)

:: Create Desktop Shortcut dynamically for this specific PC
echo.
echo Creating Desktop Shortcut...
for /f "delims=" %%I in ('%PY_CMD% -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))"') do set "PYW_PATH=%%I"

set "SHORTCUT_SCRIPT=%TEMP%\create_raphael_demo_lnk.vbs"
(
    echo Set oWS = WScript.CreateObject("WScript.Shell"^)
    echo sLinkFile = oWS.SpecialFolders("Desktop"^) ^& "\Raphael Demo.lnk"
    echo Set oLink = oWS.CreateShortcut(sLinkFile^)
    echo oLink.TargetPath = "%PYW_PATH%"
    echo oLink.Arguments = """" ^& "%~dp0raphael_demo.py" ^& """"
    echo oLink.WorkingDirectory = "%~dp0"
    echo oLink.Description = "Raphael AI - Celestial Edge (Demo Edition)"
    echo oLink.Save
) > "%SHORTCUT_SCRIPT%"

cscript //nologo "%SHORTCUT_SCRIPT%" >nul 2>&1
del "%SHORTCUT_SCRIPT%" >nul 2>&1

echo [*] Shortcut 'Raphael Demo' created on your Desktop!
echo.
echo ======================================================================
echo Setup Complete!
echo You can now double-click 'Raphael Demo' on your Desktop or run_demo.bat.
echo ======================================================================
echo.
pause
