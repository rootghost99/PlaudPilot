# PlaudTranscriber

Batch audio transcription desktop app for Windows. Transcribes Plaud-exported audio files (MP3, WAV, M4A, MP4, WebM) using the OpenAI Audio Transcriptions API, with automatic conversion and chunking for large files.

## Features

- **Batch processing** — recursively scans a folder for audio files
- **Automatic chunking** — splits large files to stay under the 25 MB API limit
- **FFmpeg conversion** — converts WAV/large files to compressed MP3 before upload
- **Retry with backoff** — handles rate limits and transient API errors
- **Diarization** (experimental) — speaker-labeled output when supported
- **Cancellation** — stop mid-run without corruption; partial results are saved
- **Portable EXE** — ships as a single `PlaudTranscriber.exe` via PyInstaller
- **Settings persistence** — remembers folders, model, and preferences across sessions

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
    chunking.py             # Time-based audio segmentation with size enforcement
    openai_client.py        # OpenAI API calls with retry/backoff
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
- An OpenAI API key (set `OPENAI_API_KEY` env var or paste in-app)
- FFmpeg (bundled in `vendor/ffmpeg/` or installed on PATH)

## Development Setup

```bash
pip install -r requirements.txt
```

### Run the app

```bash
python src/main.py
```

### FFmpeg setup

Download a static FFmpeg build for Windows and place `ffmpeg.exe` + `ffprobe.exe` in `vendor/ffmpeg/`. See `vendor/ffmpeg/README.md` for download links.

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

The EXE bundles Python, PySide6, OpenAI SDK, and the vendor FFmpeg binaries. It runs on a fresh Windows machine without requiring Python or FFmpeg installed.

### Optional Installer

If [Inno Setup](https://jrsoftware.org/isinfo.php) is installed, compile `build/installer.iss` to produce `dist/PlaudTranscriber_Setup.exe`.

## Usage

1. Launch the app
2. Select a **Source folder** containing audio files
3. Select an **Output folder** for transcripts
4. Enter your OpenAI API key (or rely on the `OPENAI_API_KEY` environment variable)
5. Adjust settings: model, chunk length, language hint, conversion toggle
6. Click **Start Transcription**

### Output Files

For each source audio file:
- `filename.txt` — combined transcript
- `filename.json` — metadata (settings, chunk list, timings, per-chunk responses, errors)

Plus a top-level `run_log.json` summarizing the batch run.

## Supported Models

| Model | Description |
|---|---|
| `gpt-4o-mini-transcribe` | Fast, cost-effective (default) |
| `gpt-4o-transcribe` | Higher quality |
| `whisper-1` | Original Whisper model |

## Limitations

- **25 MB per API upload** — files are automatically chunked to stay under this limit (with a 92% safety buffer)
- **Diarization** is experimental and depends on model support
- API key is never persisted to disk for security

## Troubleshooting

- **"ffmpeg not found"** — Place `ffmpeg.exe` in `vendor/ffmpeg/` or install FFmpeg on your system PATH
- **"API key not found"** — Set `OPENAI_API_KEY` environment variable or paste the key in the app
- **Rate limit errors** — The app retries automatically with exponential backoff (up to 5 retries)
- **Large WAV files** — Enable "Convert before chunking" to compress WAV to MP3 first
- **Logs** — Check `Help > View Logs Folder` or `%APPDATA%\PlaudTranscriber\logs\`

## Acceptance Tests

| Scenario | Expected Result |
|---|---|
| Short MP3 under 25 MB | `.txt` and `.json` created in output folder |
| Long WAV over 25 MB | Auto-convert to MP3 + chunk + transcription succeeds |
| Cancel mid-run | App stays stable, partial output saved, no corruption |
| API rate limit (429) | Retries with backoff, failures recorded, batch continues |
| EXE on clean Windows | Runs without Python or FFmpeg installed |
