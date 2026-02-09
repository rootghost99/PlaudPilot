"""Export transcription results to txt and json files."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def export_transcript_txt(
    output_dir: str,
    source_filename: str,
    chunks: List[dict],
    diarization: bool = False,
) -> str:
    """Write combined transcript to a .txt file. Returns the output path."""
    os.makedirs(output_dir, exist_ok=True)
    stem = Path(source_filename).stem
    out_path = os.path.join(output_dir, f"{stem}.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Transcript: {source_filename}\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("=" * 60 + "\n\n")

        if diarization:
            for chunk in chunks:
                raw = chunk.get("raw_response") or {}
                segments = raw.get("segments", [])
                if segments:
                    for seg in segments:
                        start = seg.get("start", 0)
                        end = seg.get("end", 0)
                        text = seg.get("text", "")
                        f.write(f"[{_fmt_time(start)} - {_fmt_time(end)}] {text.strip()}\n")
                else:
                    text = chunk.get("text", "")
                    if text:
                        f.write(text.strip() + "\n")
                f.write("\n")
        else:
            for chunk in chunks:
                text = chunk.get("text", "")
                if text:
                    f.write(text.strip() + "\n\n")

    return out_path


def export_transcript_json(
    output_dir: str,
    source_filename: str,
    source_path: str,
    chunks: List[dict],
    settings: Dict[str, Any],
    timings: Dict[str, Any],
) -> str:
    """Write detailed metadata JSON. Returns the output path."""
    os.makedirs(output_dir, exist_ok=True)
    stem = Path(source_filename).stem
    out_path = os.path.join(output_dir, f"{stem}.json")

    data = {
        "source_file": source_filename,
        "source_path": source_path,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "settings": settings,
        "timings": timings,
        "chunks": _sanitize_chunks(chunks),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    return out_path


def export_run_log(
    output_dir: str,
    file_results: List[dict],
    run_settings: Dict[str, Any],
    run_timings: Dict[str, Any],
) -> str:
    """Write a top-level run_log.json summarizing the batch. Returns the output path."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "run_log.json")

    data = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "settings": run_settings,
        "timings": run_timings,
        "total_files": len(file_results),
        "successful": sum(1 for r in file_results if r.get("success")),
        "failed": sum(1 for r in file_results if not r.get("success")),
        "files": file_results,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    return out_path


def _sanitize_chunks(chunks: List[dict]) -> List[dict]:
    """Prepare chunk data for JSON serialization."""
    sanitized = []
    for c in chunks:
        entry = {
            "index": c.get("index", 0),
            "start_sec": c.get("start_sec", 0),
            "duration_sec": c.get("duration_sec", 0),
            "text": c.get("text", ""),
            "retries": c.get("retries", 0),
            "error": c.get("error"),
        }
        raw = c.get("raw_response")
        if raw and isinstance(raw, dict):
            entry["raw_response"] = raw
        sanitized.append(entry)
    return sanitized


def _fmt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
