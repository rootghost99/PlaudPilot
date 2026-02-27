"""PlaudPilot CLI — headless batch transcription entry point.

Intended for use with Windows Task Scheduler or any automation tool.
No GUI window is opened; progress is printed to stdout and logged to file.

Usage:
    PlaudPilotCLI.exe --input "C:\\Recordings" --output "C:\\Transcripts"
    PlaudPilotCLI.exe --input "C:\\Recordings" --output "C:\\Transcripts" --model small --device cpu
    python src/cli.py --input "C:\\Recordings" --output "C:\\Transcripts"

Exit codes:
    0 — all files succeeded (or completed with no errors)
    1 — one or more files failed, or pipeline error
"""

import argparse
import os
import sys

# Ensure src package is importable when running as `python src/cli.py`
_src_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_src_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Ensure bundled ffmpeg is on PATH so Whisper can find it
_vendor_ffmpeg = os.path.join(_repo_root, "vendor", "ffmpeg")
if os.path.isdir(_vendor_ffmpeg):
    os.environ["PATH"] = _vendor_ffmpeg + os.pathsep + os.environ.get("PATH", "")

# QCoreApplication must be created before any Qt objects (including signals).
# QCoreApplication is headless — no display or window required.
from PySide6.QtCore import QCoreApplication  # noqa: E402

_qt_app = QCoreApplication(sys.argv)

from src.core import logging as log  # noqa: E402
from src.core.pipeline import TranscriptionPipeline  # noqa: E402
from src.core.settings import DEFAULTS, load_settings  # noqa: E402


def _fmt_eta(elapsed: float, estimated_total: float) -> str:
    if estimated_total <= 0 or elapsed <= 0:
        return f"  Elapsed: {elapsed:.0f}s"
    remaining = max(0.0, estimated_total - elapsed)
    mins, secs = divmod(int(remaining), 60)
    if mins:
        eta_str = f"{mins}m {secs}s"
    else:
        eta_str = f"{secs}s"
    return f"  Elapsed: {elapsed:.0f}s  ETA: {eta_str} remaining          "


def main() -> None:
    saved = load_settings()

    parser = argparse.ArgumentParser(
        prog="PlaudPilotCLI",
        description=(
            "Batch transcribe audio files using local Whisper — no API key required.\n"
            "If --input or --output are omitted, the last-used folders from the GUI are used."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        metavar="DIR",
        default=saved.get("input_dir", ""),
        help="Source folder containing audio files",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="DIR",
        default=saved.get("output_dir", ""),
        help="Output folder for transcripts",
    )
    parser.add_argument(
        "--model", "-m",
        default=saved.get("model", DEFAULTS["model"]),
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help=f"Whisper model to use (default: {saved.get('model', DEFAULTS['model'])})",
    )
    parser.add_argument(
        "--device", "-d",
        default=saved.get("device", DEFAULTS["device"]),
        choices=["auto", "cpu", "cuda"],
        help=f"Compute device (default: {saved.get('device', DEFAULTS['device'])})",
    )
    parser.add_argument(
        "--chunk-minutes",
        type=float,
        metavar="MINUTES",
        default=saved.get("chunk_minutes", DEFAULTS["chunk_minutes"]),
        help=f"Audio chunk length in minutes (default: {saved.get('chunk_minutes', DEFAULTS['chunk_minutes'])})",
    )
    parser.add_argument(
        "--language", "-l",
        metavar="LANG",
        default=saved.get("language", DEFAULTS["language"]),
        help="Language hint, e.g. 'en' (default: auto-detect)",
    )
    parser.add_argument(
        "--diarization",
        action="store_true",
        default=False,
        help="Enable experimental speaker diarization timestamps",
    )
    parser.add_argument(
        "--no-convert",
        action="store_true",
        default=False,
        help="Skip FFmpeg conversion to MP3 before chunking",
    )

    args = parser.parse_args()

    # Validate required paths (may come from saved settings or CLI args)
    if not args.input:
        parser.error(
            "--input is required. Either pass it on the command line or set a "
            "source folder in the PlaudPilot GUI first (it will be remembered)."
        )
    if not args.output:
        parser.error(
            "--output is required. Either pass it on the command line or set an "
            "output folder in the PlaudPilot GUI first (it will be remembered)."
        )

    # Set up file logging
    if sys.platform == "win32":
        log_base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        log_base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    log_dir = os.path.join(log_base, "PlaudPilot", "logs")
    log_path = log.setup_file_logging(log_dir)

    device = None if args.device == "auto" else args.device

    print("PlaudPilot CLI")
    print(f"  Input:   {args.input}")
    print(f"  Output:  {args.output}")
    print(f"  Model:   {args.model}")
    print(f"  Device:  {args.device}")
    print(f"  Log:     {log_path}")
    print()

    pipeline = TranscriptionPipeline(
        input_dir=args.input,
        output_dir=args.output,
        model=args.model,
        chunk_minutes=args.chunk_minutes,
        language=args.language,
        diarization=args.diarization,
        convert_before_chunking=not args.no_convert,
        device=device,
    )

    result: dict = {"success": False, "message": ""}

    def on_status(msg: str) -> None:
        print(f"  {msg}")

    def on_file_progress(idx: int, total: int, filename: str) -> None:
        if filename:
            print(f"\n[{idx + 1}/{total}] {filename}")

    def on_eta(elapsed: float, estimated_total: float) -> None:
        if elapsed > 0:
            print(_fmt_eta(elapsed, estimated_total), end="\r", flush=True)

    def on_finished(success: bool, message: str) -> None:
        result["success"] = success
        result["message"] = message

    pipeline.signals.status.connect(on_status)
    pipeline.signals.file_progress.connect(on_file_progress)
    pipeline.signals.eta_update.connect(on_eta)
    pipeline.signals.finished.connect(on_finished)

    pipeline.run()

    print(f"\n{result['message']}")
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
