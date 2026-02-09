"""OpenAI Audio Transcription client with retry/backoff."""

import time
import os
from pathlib import Path
from typing import Optional

import openai

# Diarization model – isolated behind a constant for easy updates.
# As of 2025, gpt-4o-transcribe supports include=["logprobs"] but diarization
# is typically via a separate pipeline.  We use whisper-1 with response_format
# "verbose_json" which returns segments that can approximate speaker turns.
DIARIZATION_MODEL = "gpt-4o-transcribe"

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0  # seconds


def create_client(api_key: Optional[str] = None) -> openai.OpenAI:
    """Create an OpenAI client.  Uses provided key or OPENAI_API_KEY env var."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
            "or enter it in the app settings."
        )
    return openai.OpenAI(api_key=key)


def transcribe_chunk(
    client: openai.OpenAI,
    audio_path: str,
    model: str = "gpt-4o-mini-transcribe",
    language: Optional[str] = None,
    diarization: bool = False,
) -> dict:
    """Transcribe a single audio chunk with retries.

    Returns:
        dict with keys: text, raw_response, retries, error
    """
    retries = 0
    last_error = None

    while retries <= MAX_RETRIES:
        try:
            with open(audio_path, "rb") as f:
                kwargs = {
                    "model": model,
                    "file": f,
                }

                # whisper-1 supports language and response_format parameters
                if model == "whisper-1":
                    if language:
                        kwargs["language"] = language
                    if diarization:
                        kwargs["response_format"] = "verbose_json"
                    else:
                        kwargs["response_format"] = "text"
                else:
                    # gpt-4o-transcribe / gpt-4o-mini-transcribe
                    # These models accept a different set of params
                    if language:
                        kwargs["language"] = language

                response = client.audio.transcriptions.create(**kwargs)

            # Parse response
            if model == "whisper-1" and diarization:
                # verbose_json returns a Transcription object with segments
                raw = response.model_dump() if hasattr(response, "model_dump") else {"text": str(response)}
                return {
                    "text": raw.get("text", str(response)),
                    "raw_response": raw,
                    "retries": retries,
                    "error": None,
                }
            elif model == "whisper-1":
                # text format returns plain string
                text = response if isinstance(response, str) else getattr(response, "text", str(response))
                return {
                    "text": text,
                    "raw_response": {"text": text},
                    "retries": retries,
                    "error": None,
                }
            else:
                # gpt-4o models return a Transcription object
                text = getattr(response, "text", str(response))
                raw = response.model_dump() if hasattr(response, "model_dump") else {"text": text}
                return {
                    "text": text,
                    "raw_response": raw,
                    "retries": retries,
                    "error": None,
                }

        except openai.APIStatusError as e:
            last_error = e
            if e.status_code in RETRYABLE_STATUS_CODES:
                retries += 1
                if retries > MAX_RETRIES:
                    break
                wait = INITIAL_BACKOFF * (2 ** (retries - 1))
                time.sleep(wait)
                continue
            else:
                # Non-retryable error
                return {
                    "text": "",
                    "raw_response": None,
                    "retries": retries,
                    "error": f"API error {e.status_code}: {e.message}",
                }
        except openai.APIConnectionError as e:
            last_error = e
            retries += 1
            if retries > MAX_RETRIES:
                break
            wait = INITIAL_BACKOFF * (2 ** (retries - 1))
            time.sleep(wait)
            continue
        except Exception as e:
            return {
                "text": "",
                "raw_response": None,
                "retries": retries,
                "error": str(e),
            }

    return {
        "text": "",
        "raw_response": None,
        "retries": retries,
        "error": f"Max retries exceeded. Last error: {last_error}",
    }
