# build_exe.ps1 — Build PlaudPilot EXE using PyInstaller
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File build/build_exe.ps1
#
# Options:
#   -Installer    Build onedir + Inno Setup installer (smaller download, ~800MB-1.2GB)
#   (default)     Build onefile portable EXE (~2.5GB)

param(
    [switch]$Installer
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== PlaudPilot EXE Build ===" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot"
Write-Host "Build mode: $(if ($Installer) { 'Installer (onedir + Inno Setup)' } else { 'Portable (onefile)' })"

# Ensure we are in repo root
Set-Location $RepoRoot

# Check Python
Write-Host "`n--- Checking Python ---"
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python not found. Install Python 3.10+ and add to PATH."
    exit 1
}

# Install dependencies
Write-Host "`n--- Installing dependencies ---"
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed."
    exit 1
}

# Install CUDA-enabled PyTorch (overrides the CPU-only version from PyPI)
# --force-reinstall is needed because pip skips if the same version is already installed
Write-Host "`n--- Installing PyTorch with CUDA support ---"
pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/cu124
if ($LASTEXITCODE -ne 0) {
    Write-Warning "CUDA PyTorch install failed — falling back to CPU-only torch."
    Write-Warning "The app will still work but will use CPU for transcription."
}

# Check for ffmpeg in vendor
$ffmpegExe = Join-Path $RepoRoot "vendor\ffmpeg\ffmpeg.exe"
if (-not (Test-Path $ffmpegExe)) {
    Write-Warning "vendor\ffmpeg\ffmpeg.exe not found!"
    Write-Warning "Download FFmpeg Windows build and place ffmpeg.exe + ffprobe.exe in vendor\ffmpeg\"
    Write-Warning "The app will fall back to system PATH at runtime."
}

# Select spec file
if ($Installer) {
    $specFile = Join-Path $RepoRoot "build\PlaudPilot_installer.spec"
} else {
    $specFile = Join-Path $RepoRoot "build\PlaudPilot.spec"
}

# Run PyInstaller
Write-Host "`n--- Running PyInstaller ---"
pyinstaller --clean --noconfirm $specFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit 1
}

if ($Installer) {
    # onedir build — report folder size, then run Inno Setup
    $outputDir = Join-Path $RepoRoot "dist\PlaudPilot"
    if (Test-Path $outputDir) {
        $size = (Get-ChildItem $outputDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host ("`n--- Onedir output: {0:N0} MB (uncompressed) ---" -f $size)
    }

    # Check for Inno Setup compiler
    $iscc = $null
    foreach ($path in @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )) {
        if (Test-Path $path) { $iscc = $path; break }
    }

    if ($iscc) {
        Write-Host "`n--- Building installer with Inno Setup ---"
        $issFile = Join-Path $RepoRoot "build\installer.iss"
        & $iscc $issFile
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Inno Setup compilation failed."
            exit 1
        }
        $setupExe = Join-Path $RepoRoot "dist\PlaudPilot_Setup.exe"
        if (Test-Path $setupExe) {
            $setupSize = (Get-Item $setupExe).Length / 1MB
            Write-Host "`n=== BUILD SUCCESS ===" -ForegroundColor Green
            Write-Host "Installer: $setupExe"
            Write-Host ("Size:      {0:N0} MB" -f $setupSize)
        }
    } else {
        Write-Warning "Inno Setup 6 not found — skipping installer creation."
        Write-Warning "Install from https://jrsoftware.org/isdl.php then re-run."
        Write-Warning "Or compile build\installer.iss manually with ISCC.exe."
        Write-Host "`n=== ONEDIR BUILD SUCCESS ===" -ForegroundColor Green
        Write-Host "Output: $outputDir"
    }
} else {
    # onefile build
    $outputExe = Join-Path $RepoRoot "dist\PlaudPilot.exe"
    if (Test-Path $outputExe) {
        $size = (Get-Item $outputExe).Length / 1MB
        Write-Host "`n=== BUILD SUCCESS ===" -ForegroundColor Green
        Write-Host "Output: $outputExe"
        Write-Host ("Size:   {0:N1} MB" -f $size)
    } else {
        Write-Error "Build completed but EXE not found at expected location."
        exit 1
    }
}
