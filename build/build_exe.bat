@echo off
REM build_exe.bat — Build PlaudPilot EXE
REM Run from the repo root:  build\build_exe.bat
REM
REM Options:
REM   build\build_exe.bat              Build portable onefile EXE (~2.5GB)
REM   build\build_exe.bat --installer  Build onedir + Inno Setup installer (~800MB-1.2GB)

set "INSTALLER="
if /i "%~1"=="--installer" set "INSTALLER=1"

echo === PlaudPilot EXE Build ===
cd /d "%~dp0\.."

if defined INSTALLER (
    echo Build mode: Installer (onedir + Inno Setup)
) else (
    echo Build mode: Portable (onefile)
)

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
if defined INSTALLER (
    pyinstaller --clean --noconfirm build\PlaudPilot_installer.spec
) else (
    pyinstaller --clean --noconfirm build\PlaudPilot.spec
)
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

if defined INSTALLER (
    REM Try to find Inno Setup compiler
    set "ISCC="
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

    if defined ISCC (
        echo.
        echo --- Building installer with Inno Setup ---
        "%ISCC%" build\installer.iss
        if errorlevel 1 (
            echo ERROR: Inno Setup compilation failed.
            exit /b 1
        )
        if exist dist\PlaudPilot_Setup.exe (
            echo.
            echo === BUILD SUCCESS ===
            echo Installer: dist\PlaudPilot_Setup.exe
        )
    ) else (
        echo.
        echo WARNING: Inno Setup 6 not found -- skipping installer creation.
        echo WARNING: Install from https://jrsoftware.org/isdl.php then re-run.
        echo.
        echo === ONEDIR BUILD SUCCESS ===
        echo Output: dist\PlaudPilot\
    )
) else (
    if exist dist\PlaudPilot.exe (
        echo.
        echo === BUILD SUCCESS ===
        echo Output: dist\PlaudPilot.exe
    ) else (
        echo ERROR: Build completed but EXE not found.
        exit /b 1
    )
)
