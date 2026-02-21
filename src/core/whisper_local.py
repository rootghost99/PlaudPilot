"""Local Whisper transcription client — replaces OpenAI API calls."""

import os
from typing import Optional

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


class LocalWhisperClient:
    """Loads an OpenAI Whisper model and transcribes audio chunks locally."""

    def __init__(self, model_name: str = "medium", device: Optional[str] = None):
        """
        Parameters
        ----------
        model_name : str
            One of: tiny, base, small, medium, large-v3
        device : str or None
            "cuda", "cpu", or None for auto-detection.
        """
        import torch
        import whisper

        # Ensure bundled ffmpeg is discoverable by Whisper's audio loader
        ensure_on_path()

        if device is None or device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.model_name = model_name
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
