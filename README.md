# PlaudTranscriber

Batch audio transcription desktop app. Transcribes Plaud-exported audio files (MP3, WAV, M4A, MP4, WebM) using local OpenAI Whisper models, with automatic conversion and chunking for large files. Runs entirely on-device with zero API costs.

## Features

- **Local Whisper inference** — runs OpenAI's open-source Whisper model on your machine (CPU or CUDA GPU)
- **Batch processing** — recursively scans a folder for audio files
- **Automatic chunking** — splits large files into time-based segments for memory-safe transcription
- **FFmpeg conversion** — converts WAV/large files to compressed MP3 before processing
- **GPU auto-detection** — shows whether CUDA is available and lets you choose CPU or GPU
- **Model selection** — choose from tiny, base, small, medium, or large-v3 depending on accuracy/speed needs
- **Diarization** (experimental) — speaker-labeled output using Whisper segment timestamps
- **Cancellation** — stop mid-run without corruption; partial results are saved
- **Portable EXE** — ships as a single `PlaudTranscriber.exe` via PyInstaller
- **Settings persistence** — remembers folders, model, device, and preferences across sessions

## Repo Structure

```
src/
  main.py                   # Qt app entry point
  ui/
    main_window.py          # PySide6 main window
    worker.py               # QThread worker for background pipeline
  core/
    pipeline.py             # Orchestrates conversion → chunking → transcription → export
    ffmpeg.py               # FFmpeg wrapper + bundled path resolution
    chunking.py             # Time-based audio segmentation
    whisper_local.py        # Local Whisper model loading and transcription
    exporters.py            # .txt and .json transcript output
    logging.py              # Structured logging to UI + file
    settings.py             # User preferences in %APPDATA%
vendor/ffmpeg/              # Place ffmpeg.exe + ffprobe.exe here
build/
  PlaudTranscriber.spec     # PyInstaller spec
  build_exe.ps1             # PowerShell build script
  build_exe.bat             # Batch build script
  installer.iss             # Inno Setup script (optional installer)
```

## Prerequisites

- Python 3.10+
- FFmpeg (bundled in `vendor/ffmpeg/` or installed on PATH)

No API key is required — transcription runs entirely locally.

## Development Setup

```bash
pip install -r requirements.txt
```

### Run the app

```bash
python src/main.py
```

### FFmpeg setup

Download a static FFmpeg build and place `ffmpeg.exe` + `ffprobe.exe` in `vendor/ffmpeg/`. The app also adds this directory to `PATH` at startup so the Whisper library can find ffmpeg. See `vendor/ffmpeg/README.md` for download links.

## Building the Portable EXE

### PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File build/build_exe.ps1
```

### Batch

```cmd
build\build_exe.bat
```

Output: `dist/PlaudTranscriber.exe`

The EXE bundles Python, PySide6, PyTorch, Whisper, and the vendor FFmpeg binaries. Note that including PyTorch makes the EXE significantly larger (~2-3 GB). Models are downloaded on first use.

### Optional Installer

If [Inno Setup](https://jrsoftware.org/isinfo.php) is installed, compile `build/installer.iss` to produce `dist/PlaudTranscriber_Setup.exe`.

## Usage

1. Launch the app
2. Select a **Source folder** containing audio files
3. Select an **Output folder** for transcripts
4. Choose a Whisper model and device (auto/cpu/cuda)
5. Adjust settings: chunk length, language hint, conversion toggle
6. Click **Start Transcription**

The Whisper model will be downloaded on first use and cached locally.

### Output Files

For each source audio file:
- `filename.txt` — combined transcript
- `filename.json` — metadata (settings, chunk list, timings, per-chunk responses, errors)

Plus a top-level `run_log.json` summarizing the batch run.

## Supported Models

| Model | Accuracy | Approximate RAM | Speed |
|---|---|---|---|
| `tiny` | Lowest | ~1 GB | Fastest |
| `base` | Low | ~1 GB | Fast |
| `small` | Good | ~2 GB | Moderate |
| `medium` | High (default) | ~5 GB | Slower |
| `large-v3` | Best | ~10 GB | Slowest |

With a CUDA GPU, transcription is significantly faster. The app auto-detects GPU availability and displays it in the UI.

## Limitations

- **First-run model download** — Whisper models are downloaded from the internet on first use (~1-3 GB depending on model size)
- **Memory usage** — larger models require more RAM; `large-v3` needs ~10 GB
- **Diarization** is experimental and based on Whisper's segment-level timestamps
- **No speaker labels** — basic Whisper does not identify individual speakers (consider WhisperX for that)

## Troubleshooting

- **"ffmpeg not found"** — Place `ffmpeg.exe` in `vendor/ffmpeg/` or install FFmpeg on your system PATH
- **Out of memory** — Try a smaller model (e.g. `small` or `base`) or reduce chunk length
- **Slow transcription** — Ensure CUDA GPU is available; CPU-only transcription is significantly slower
- **Large WAV files** — Enable "Convert before chunking" to compress WAV to MP3 first
- **Logs** — Check `Help > View Logs Folder` or `%APPDATA%\PlaudTranscriber\logs\`

## Acceptance Tests

| Scenario | Expected Result |
|---|---|
| App launches without API key | No key prompt; model dropdown shows local Whisper models |
| Short MP3 file | `.txt` and `.json` created in output folder |
| Long WAV file | Auto-convert to MP3 + chunk + transcription succeeds |
| Cancel mid-run | App stays stable, partial output saved, no corruption |
| GPU detection | Status indicator shows CUDA available or CPU fallback |
| EXE on clean machine | Runs without Python or FFmpeg installed |
