"""User settings persistence in %APPDATA%/PlaudPilot/settings.json."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


def _settings_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(base) / "PlaudPilot"


def _settings_path() -> Path:
    return _settings_dir() / "settings.json"


DEFAULTS: Dict[str, Any] = {
    "input_dir": "",
    "output_dir": "",
    "model": "medium",
    "chunk_minutes": 30.0,
    "language": "",
    "diarization": False,
    "convert_before_chunking": True,
    "device": "auto",
}


def load_settings() -> Dict[str, Any]:
    """Load settings from disk, returning defaults for missing keys."""
    settings = dict(DEFAULTS)
    path = _settings_path()
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            settings.update(stored)
        except Exception:
            pass  # Corrupt file – use defaults
    return settings


def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to disk."""
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
