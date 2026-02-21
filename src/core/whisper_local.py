"""Local Whisper transcription client — replaces OpenAI API calls."""

import os
from typing import Callable, Optional

from src.core.ffmpeg import ensure_on_path


# Available local Whisper models (name -> approximate RAM requirement)
WHISPER_MODELS = {
    "tiny": "~1 GB RAM",
    "base": "~1 GB RAM",
    "small": "~2 GB RAM",
    "medium": "~5 GB RAM",
    "large-v3": "~10 GB RAM",
}


def detect_device() -> str:
    """Return 'cuda' if a CUDA GPU is available, otherwise 'cpu'."""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def diagnose_cuda() -> str:
    """Return a human-readable explanation of CUDA availability."""
    try:
        import torch
    except ImportError:
        return "PyTorch is not installed."

    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        return f"CUDA available — {name}"

    # torch is installed but CUDA not available — figure out why
    if not hasattr(torch.version, "cuda") or torch.version.cuda is None:
        return (
            "CPU-only PyTorch installed. To enable GPU, reinstall with:\n"
            "pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/cu124"
        )

    return (
        f"PyTorch built for CUDA {torch.version.cuda} but no compatible GPU/driver found. "
        "Check that your NVIDIA drivers are up to date."
    )


def is_model_cached(model_name: str) -> bool:
    """Check whether the Whisper model is already downloaded to disk."""
    try:
        import whisper
        # Whisper caches models in ~/.cache/whisper/
        download_root = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        if model_name in whisper._MODELS:
            expected = os.path.join(download_root, os.path.basename(whisper._MODELS[model_name]))
            return os.path.isfile(expected)
    except Exception:
        pass
    return False


class LocalWhisperClient:
    """Loads an OpenAI Whisper model and transcribes audio chunks locally."""

    def __init__(
        self,
        model_name: str = "medium",
        device: Optional[str] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Parameters
        ----------
        model_name : str
            One of: tiny, base, small, medium, large-v3
        device : str or None
            "cuda", "cpu", or None for auto-detection.
        on_status : callable or None
            Optional callback for status messages (e.g. download progress).
        """
        import torch
        import whisper

        # Ensure bundled ffmpeg is discoverable by Whisper's audio loader
        ensure_on_path()

        if device is None or device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        # Graceful fallback: if user selected CUDA but it's not available
        if device == "cuda" and not torch.cuda.is_available():
            hint = diagnose_cuda()
            msg = f"CUDA requested but not available — falling back to CPU. {hint}"
            if on_status:
                on_status(msg)
            device = "cpu"

        self.device = device
        self.model_name = model_name

        if not is_model_cached(model_name) and on_status:
            on_status(
                f"Downloading Whisper model '{model_name}' (first run only, this may take a while)..."
            )

        self.model = whisper.load_model(model_name, device=device)

    def transcribe_chunk(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Transcribe a single audio chunk using the local Whisper model.

        Returns a dict matching the format pipeline.py expects:
            {
                "text": str,
                "raw_response": dict,
                "retries": 0,
                "error": None | str,
            }
        """
        try:
            options = {}
            if language:
                options["language"] = language

            result = self.model.transcribe(str(audio_path), **options)

            raw_response = {
                "text": result["text"].strip(),
                "language": result.get("language", ""),
                "segments": result.get("segments", []),
            }

            return {
                "text": result["text"].strip(),
                "raw_response": raw_response,
                "retries": 0,
                "error": None,
            }
        except Exception as e:
            return {
                "text": "",
                "raw_response": None,
                "retries": 0,
                "error": str(e),
            }
