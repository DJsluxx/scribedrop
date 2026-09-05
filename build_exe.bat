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
if errorlevel 1 exit /b 1

REM ---------------------------------------------------------------------
REM Post-build purge. This is not optional and it is not cosmetic.
REM
REM 1. NVIDIA CUDA runtime DLLs. "--exclude-module nvidia" does NOT catch
REM    these, because "--collect-all ctranslate2" copies whatever sits in
REM    the ctranslate2 package directory - and the ctranslate2 wheel ships
REM    cudnn64_9.dll inside it. Those DLLs are NVIDIA proprietary and must
REM    not travel inside an MIT release archive. The bundle is CPU-only, so
REM    nothing here ever loads them.
REM
REM NOT purged, and here is why, so nobody "helpfully" adds it later:
REM the PyAV wheel vendors libx264 and libx265 (GPLv2+), and avcodec is
REM hard-linked against both. Deleting them does not merely drop an unused
REM encoder - it makes `import av` fail with "DLL load failed", which takes
REM all audio decoding with it. Verified on av 18.1.0; every PyAV Windows
REM wheel from 13.x to 18.x ships them. They are disclosed instead, in
REM THIRD-PARTY-NOTICES.md. Do not add a del line for libx26*.
REM ---------------------------------------------------------------------
REM Note: do NOT put these masks in a `for %%M in (...)` set. FOR performs
REM filename expansion on its set, so unmatched wildcards vanish silently and
REM the purge becomes a no-op that still reports success.
set "BUNDLE=dist\ScribeDrop\_internal"
echo.
echo Purging DLLs that must not ship...
echo   NVIDIA CUDA runtime...
del /q /s "%BUNDLE%\cudnn64_*.dll"    >nul 2>&1
del /q /s "%BUNDLE%\cublas64_*.dll"   >nul 2>&1
del /q /s "%BUNDLE%\cublasLt64_*.dll" >nul 2>&1
del /q /s "%BUNDLE%\cudart64_*.dll"   >nul 2>&1
del /q /s "%BUNDLE%\nvrtc*.dll"       >nul 2>&1
REM Verify, recursively, and fail the build rather than ship a bad archive.
powershell -NoProfile -Command ^
 "$bad = Get-ChildItem -Path '%BUNDLE%' -Recurse -File -Include cudnn64_*.dll,cublas*.dll,cudart64_*.dll,nvrtc*.dll;" ^
 "if ($bad) { $bad.FullName; exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo ERROR: the files listed above must not ship. Not packaging this build.
    exit /b 1
)
echo   verified: no NVIDIA CUDA DLLs remain in the bundle.

REM The licence and the third-party notices travel with the binary, not just
REM with the repo - a user who only ever downloads the .zip must still get them.
copy /y "LICENSE" "dist\ScribeDrop\LICENSE.txt" >nul
copy /y "THIRD-PARTY-NOTICES.md" "dist\ScribeDrop\THIRD-PARTY-NOTICES.md" >nul
copy /y "README.md" "dist\ScribeDrop\README.md" >nul
REM GPLv2 compliance: the bundle hard-links GPL x264/x265 via PyAV's avcodec, so
REM the licence text and the pointer to corresponding source must travel with it.
REM GPLv2 s1 requires the licence; s3(a) requires the source from the same place.
copy /y "COPYING.GPLv2.txt" "dist\ScribeDrop\COPYING.GPLv2.txt" >nul
copy /y "GPL-SOURCE-OFFER.txt" "dist\ScribeDrop\GPL-SOURCE-OFFER.txt" >nul
if not exist "dist\ScribeDrop\COPYING.GPLv2.txt" (
    echo ERROR: COPYING.GPLv2.txt missing from the bundle. Not packaging this build.
    exit /b 1
)
if not exist "dist\ScribeDrop\GPL-SOURCE-OFFER.txt" (
    echo ERROR: GPL-SOURCE-OFFER.txt missing from the bundle. Not packaging this build.
    exit /b 1
)

echo.
echo Bundle written to dist\ScribeDrop
