"""FFmpeg wrapper: resolves bundled ffmpeg/ffprobe paths for dev and PyInstaller modes."""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _base_dir() -> Path:
    """Return the base directory where vendor/ lives.

    * PyInstaller onefile: sys._MEIPASS (temp extraction dir)
    * Normal dev run:      repo root (two levels up from this file)
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    # dev: src/core/ffmpeg.py -> repo root
    return Path(__file__).resolve().parent.parent.parent


def _vendor_dir() -> Path:
    return _base_dir() / "vendor" / "ffmpeg"


def ffmpeg_path() -> str:
    """Return absolute path to ffmpeg executable."""
    bundled = _vendor_dir() / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if bundled.is_file():
        return str(bundled)
    # Fallback: system PATH
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError(
        "ffmpeg not found. Place ffmpeg.exe in vendor/ffmpeg/ or install it on PATH."
    )


def ensure_on_path() -> None:
    """Add the vendor ffmpeg directory to PATH so third-party libs (e.g. Whisper) can find it."""
    vendor = str(_vendor_dir())
    if vendor not in os.environ.get("PATH", ""):
        os.environ["PATH"] = vendor + os.pathsep + os.environ.get("PATH", "")


def ffprobe_path() -> str:
    """Return absolute path to ffprobe executable."""
    bundled = _vendor_dir() / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
    if bundled.is_file():
        return str(bundled)
    found = shutil.which("ffprobe")
    if found:
        return found
    raise FileNotFoundError(
        "ffprobe not found. Place ffprobe.exe in vendor/ffmpeg/ or install it on PATH."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_duration_seconds(audio_path: str) -> float:
    """Return duration of an audio file in seconds via ffprobe."""
    cmd = [
        ffprobe_path(),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return float(result.stdout.strip())


def get_file_size(path: str) -> int:
    return os.path.getsize(path)


def convert_to_mp3(
    input_path: str,
    output_path: str,
    sample_rate: int = 16000,
    bitrate: str = "64k",
    mono: bool = True,
) -> str:
    """Convert any audio to mono 16 kHz MP3 at given bitrate. Returns output_path."""
    cmd = [
        ffmpeg_path(),
        "-y",
        "-i", input_path,
        "-ac", "1" if mono else "2",
        "-ar", str(sample_rate),
        "-b:a", bitrate,
        "-f", "mp3",
        output_path,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=600,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.strip()}")
    return output_path


def extract_segment(
    input_path: str,
    output_path: str,
    start_sec: float,
    duration_sec: float,
) -> str:
    """Extract a time segment from an audio file without re-encoding (copy codec)."""
    cmd = [
        ffmpeg_path(),
        "-y",
        "-ss", str(start_sec),
        "-t", str(duration_sec),
        "-i", input_path,
        "-c", "copy",
        "-f", "mp3",
        output_path,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg segment extraction failed: {result.stderr.strip()}")
    return output_path
