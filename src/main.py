"""PlaudPilot — main entry point."""

import os
import sys

# When running as a windowed PyInstaller EXE (console=False), sys.stdout and
# sys.stderr are None.  Redirect them to devnull so that libraries (logging,
# tqdm/whisper progress bars, etc.) don't crash with
# "'NoneType' object has no attribute 'write'".
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# Ensure src package is importable when running as `python src/main.py`
_src_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_src_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont
from PySide6.QtCore import Qt

# Ensure bundled ffmpeg is on PATH so that Whisper (which shells out to ffmpeg)
# can locate it without the user installing ffmpeg system-wide.
_vendor_ffmpeg = os.path.join(_repo_root, "vendor", "ffmpeg")
if os.path.isdir(_vendor_ffmpeg):
    os.environ["PATH"] = _vendor_ffmpeg + os.pathsep + os.environ.get("PATH", "")

from src.core import logging as log
from src.core.settings import load_settings
from src.ui.main_window import MainWindow, APP_NAME, APP_VERSION


def _make_splash() -> QSplashScreen:
    """Create a simple splash screen with text (no external image needed)."""
    pixmap = QPixmap(420, 200)
    pixmap.fill(QColor("#0078D4"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("white"))
    font = QFont("Segoe UI", 22, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"{APP_NAME}\nv{APP_VERSION}")
    painter.end()
    splash = QSplashScreen(pixmap)
    splash.show()
    return splash


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")

    # Splash
    splash = _make_splash()
    app.processEvents()

    # Set up file logging
    if sys.platform == "win32":
        log_base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        log_base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    log_dir = os.path.join(log_base, "PlaudPilot", "logs")
    log_setup_path = log.setup_file_logging(log_dir)
    log.info(f"Log file: {log_setup_path}")

    # Main window
    window = MainWindow()
    window.show()

    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
