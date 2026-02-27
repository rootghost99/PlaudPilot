@echo off
REM build_exe.bat — Build PlaudPilot portable EXE
REM Run from the repo root:  build\build_exe.bat

echo === PlaudPilot EXE Build ===
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
echo --- Installing PyTorch with CUDA support ---
pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/cu124
if errorlevel 1 (
    echo WARNING: CUDA PyTorch install failed -- falling back to CPU-only torch.
    echo WARNING: The app will still work but will use CPU for transcription.
)

echo.
echo --- Running PyInstaller ---
pyinstaller --clean --noconfirm build\PlaudPilot.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

set MISSING=0
if not exist dist\PlaudPilot.exe    set MISSING=1
if not exist dist\PlaudPilotCLI.exe set MISSING=1

if %MISSING%==1 (
    echo ERROR: Build completed but one or more EXEs were not found.
    if not exist dist\PlaudPilot.exe    echo   MISSING: dist\PlaudPilot.exe
    if not exist dist\PlaudPilotCLI.exe echo   MISSING: dist\PlaudPilotCLI.exe
    exit /b 1
)

echo.
echo === BUILD SUCCESS ===
echo GUI: dist\PlaudPilot.exe
echo CLI: dist\PlaudPilotCLI.exe
