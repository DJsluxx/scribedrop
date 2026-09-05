@echo off
setlocal enabledelayedexpansion
title ScribeDrop setup

echo ============================================
echo   ScribeDrop - one-time setup
echo ============================================
echo.

cd /d "%~dp0"

REM ---- 1. Find a usable Python -------------------------------------------
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python was not found.
    echo         Install Python 3.10 or newer from https://www.python.org/downloads/
    echo         and tick "Add python.exe to PATH" during install.
    goto :fail
)

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10 or newer is required.
    %PY% --version
    goto :fail
)

%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This Python has no tkinter. Reinstall Python and keep the
    echo         "tcl/tk and IDLE" option enabled.
    goto :fail
)

echo [1/4] Creating a private virtual environment in .venv ...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        goto :fail
    )
)

set "VENV_PY=%CD%\.venv\Scripts\python.exe"

echo [2/4] Installing ScribeDrop's requirements ...
"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Installing requirements failed. Check your internet connection.
    goto :fail
)

echo [3/4] Checking for an NVIDIA GPU ...
where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo       No NVIDIA GPU detected - ScribeDrop will run on the CPU.
    echo       That works, it is just slower.
) else (
    echo       NVIDIA GPU found. Installing the CUDA runtime libraries.
    echo       This is a large download ^(about 1.2 GB^) and only happens once.
    "%VENV_PY%" -m pip install -r requirements-gpu.txt
    if errorlevel 1 (
        echo       [WARN] CUDA libraries failed to install. ScribeDrop will use the CPU.
    )
)

echo [4/4] Creating the ScribeDrop launcher ...
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo start "" ".venv\Scripts\pythonw.exe" -m scribedrop %%*
) > ScribeDrop.bat

echo.
echo ============================================
echo   Setup complete.
echo   Double-click ScribeDrop.bat to start.
echo ============================================
echo.
echo Note: the speech model downloads the first time you press Transcribe.
echo After that, ScribeDrop works with no internet connection at all.
echo.
pause
exit /b 0

:fail
echo.
echo Setup did not complete.
pause
exit /b 1
