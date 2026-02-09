"""Audio chunking: split audio files into API-safe segments."""

import os
import tempfile
from pathlib import Path
from typing import List, Tuple

from .ffmpeg import (
    get_duration_seconds,
    get_file_size,
    convert_to_mp3,
    extract_segment,
)

# OpenAI hard limit is 25 MB; use 92% safety buffer
API_MAX_BYTES = 25 * 1024 * 1024
SAFE_MAX_BYTES = int(API_MAX_BYTES * 0.92)  # ~23 MB

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}


def needs_conversion(file_path: str, force_convert: bool = False) -> bool:
    """Determine if a file needs conversion before chunking."""
    ext = Path(file_path).suffix.lower()
    if force_convert:
        return True
    if ext == ".wav":
        return True
    if get_file_size(file_path) > SAFE_MAX_BYTES:
        return True
    return False


def chunk_audio(
    source_path: str,
    work_dir: str,
    chunk_minutes: float = 10.0,
    force_convert: bool = False,
) -> List[dict]:
    """Split an audio file into chunks that each fit under the API size limit.

    Returns a list of dicts:
        [{"path": str, "index": int, "start_sec": float, "duration_sec": float}, ...]
    """
    os.makedirs(work_dir, exist_ok=True)
    stem = Path(source_path).stem

    # Step 1: decide if we need to convert
    if needs_conversion(source_path, force_convert):
        converted_path = os.path.join(work_dir, f"{stem}_converted.mp3")
        convert_to_mp3(source_path, converted_path)
        working_file = converted_path
    else:
        working_file = source_path

    file_size = get_file_size(working_file)

    # If the file fits in one chunk, just return it
    if file_size <= SAFE_MAX_BYTES:
        return [
            {
                "path": working_file,
                "index": 0,
                "start_sec": 0.0,
                "duration_sec": get_duration_seconds(working_file),
            }
        ]

    # Step 2: chunk by time
    total_duration = get_duration_seconds(working_file)
    chunk_duration_sec = chunk_minutes * 60.0

    chunks = _split_by_duration(working_file, work_dir, stem, total_duration, chunk_duration_sec)

    # Step 3: verify sizes – if any chunk exceeds the limit, re-chunk with smaller duration
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        oversized = [c for c in chunks if get_file_size(c["path"]) > SAFE_MAX_BYTES]
        if not oversized:
            break
        # Reduce chunk duration by 40%
        chunk_duration_sec *= 0.6
        if chunk_duration_sec < 30:
            raise RuntimeError(
                f"Cannot chunk {source_path} to fit under {SAFE_MAX_BYTES} bytes "
                f"even at {chunk_duration_sec:.0f}s segments."
            )
        # Re-split
        for c in chunks:
            if c["path"] != working_file and os.path.exists(c["path"]):
                os.remove(c["path"])
        chunks = _split_by_duration(working_file, work_dir, stem, total_duration, chunk_duration_sec)
        attempt += 1

    # Final check
    for c in chunks:
        if get_file_size(c["path"]) > SAFE_MAX_BYTES:
            raise RuntimeError(
                f"Chunk {c['path']} is {get_file_size(c['path'])} bytes, "
                f"exceeds safe limit {SAFE_MAX_BYTES}."
            )

    return chunks


def _split_by_duration(
    working_file: str,
    work_dir: str,
    stem: str,
    total_duration: float,
    chunk_duration_sec: float,
) -> List[dict]:
    """Create time-based segments of an audio file."""
    chunks = []
    offset = 0.0
    idx = 0
    while offset < total_duration:
        remaining = total_duration - offset
        seg_dur = min(chunk_duration_sec, remaining)
        chunk_path = os.path.join(work_dir, f"{stem}_chunk{idx:04d}.mp3")
        extract_segment(working_file, chunk_path, offset, seg_dur)
        chunks.append({
            "path": chunk_path,
            "index": idx,
            "start_sec": offset,
            "duration_sec": seg_dur,
        })
        offset += seg_dur
        idx += 1
    return chunks
