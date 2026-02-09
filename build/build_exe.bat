@echo off
REM build_exe.bat — Build PlaudTranscriber portable EXE
REM Run from the repo root:  build\build_exe.bat

echo === PlaudTranscriber EXE Build ===
cd /d "%~dp0\.."

echo.
echo --- Checking Python ---
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and add to PATH.
    exit /b 1
)

echo.
echo --- Installing dependencies ---
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed.
    exit /b 1
)

echo.
echo --- Running PyInstaller ---
pyinstaller --clean --noconfirm build\PlaudTranscriber.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

if exist dist\PlaudTranscriber.exe (
    echo.
    echo === BUILD SUCCESS ===
    echo Output: dist\PlaudTranscriber.exe
) else (
    echo ERROR: Build completed but EXE not found.
    exit /b 1
)
