"""Structured logging: emits to both UI (via signal) and file."""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal


class LogSignalEmitter(QObject):
    """Qt signal emitter for log messages to the UI."""
    log_message = Signal(str, str)  # (severity, message)


# Module-level emitter instance
_emitter: Optional[LogSignalEmitter] = None


def get_emitter() -> LogSignalEmitter:
    global _emitter
    if _emitter is None:
        _emitter = LogSignalEmitter()
    return _emitter


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _log(severity: str, message: str) -> None:
    ts = _timestamp()
    formatted = f"[{ts}] [{severity}] {message}"
    # Emit to UI
    emitter = get_emitter()
    emitter.log_message.emit(severity, formatted)
    # Also log to Python logging
    level = getattr(logging, severity, logging.INFO)
    logging.log(level, message)


def info(message: str) -> None:
    _log("INFO", message)


def warn(message: str) -> None:
    _log("WARN", message)


def error(message: str) -> None:
    _log("ERROR", message)


def setup_file_logging(log_dir: str) -> str:
    """Configure file logging. Returns the log file path."""
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"plaud_pilot_{ts}.log")
    logging.basicConfig(
        filename=log_path,
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return log_path
