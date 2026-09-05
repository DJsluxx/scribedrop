@echo off
REM Builds the standalone, CPU-only Windows bundle with PyInstaller.
REM The NVIDIA CUDA libraries are deliberately excluded: bundling them adds
REM about 1.2 GB, and the source + setup.bat route already gives GPU users
REM a better install. The bundle announces "Using CPU" at runtime.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --onedir --windowed ^
    --name ScribeDrop ^
    --collect-all tkinterdnd2 --collect-all faster_whisper ^
    --collect-all ctranslate2 --collect-all av ^
    --collect-data onnxruntime --exclude-module nvidia ^
    pyinstaller_entry.py
echo.
echo Bundle written to dist\ScribeDrop
