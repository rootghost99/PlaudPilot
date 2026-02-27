# build_exe.ps1 — Build PlaudPilot portable EXE using PyInstaller
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File build/build_exe.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== PlaudPilot EXE Build ===" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot"

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

# Kill any running instances so PyInstaller can overwrite the EXEs
Write-Host "`n--- Stopping any running PlaudPilot instances ---"
@("PlaudPilot", "PlaudPilotCLI") | ForEach-Object {
    $procs = Get-Process -Name $_ -ErrorAction SilentlyContinue
    if ($procs) {
        $procs | Stop-Process -Force
        Write-Host "  Stopped: $_"
    }
}

# Run PyInstaller
Write-Host "`n--- Running PyInstaller ---"
$specFile = Join-Path $RepoRoot "build\PlaudPilot.spec"
pyinstaller --clean --noconfirm $specFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit 1
}

$outputExe    = Join-Path $RepoRoot "dist\PlaudPilot.exe"
$outputExeCLI = Join-Path $RepoRoot "dist\PlaudPilotCLI.exe"

$missing = @()
if (-not (Test-Path $outputExe))    { $missing += $outputExe }
if (-not (Test-Path $outputExeCLI)) { $missing += $outputExeCLI }

if ($missing.Count -gt 0) {
    Write-Error "Build completed but the following EXE(s) were not found:`n$($missing -join "`n")"
    exit 1
}

$size    = (Get-Item $outputExe).Length / 1MB
$sizeCLI = (Get-Item $outputExeCLI).Length / 1MB
Write-Host "`n=== BUILD SUCCESS ===" -ForegroundColor Green
Write-Host ("GUI: $outputExe  ({0:N1} MB)" -f $size)
Write-Host ("CLI: $outputExeCLI  ({0:N1} MB)" -f $sizeCLI)
