"""Pipeline: orchestrates conversion, chunking, transcription, and export for a batch of files."""

import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from . import logging as log
from .chunking import SUPPORTED_EXTENSIONS, chunk_audio
from .exporters import export_run_log, export_transcript_json, export_transcript_txt
from .whisper_local import LocalWhisperClient


class PipelineSignals(QObject):
    """Signals emitted by the pipeline for UI updates."""
    # (current_file_index, total_files, filename)
    file_progress = Signal(int, int, str)
    # (current_chunk_index, total_chunks)
    chunk_progress = Signal(int, int)
    # status text
    status = Signal(str)
    # pipeline finished (success, message)
    finished = Signal(bool, str)
    # single file result
    file_done = Signal(dict)
    # ETA: (elapsed_seconds, estimated_total_seconds)
    eta_update = Signal(float, float)


class TranscriptionPipeline:
    """Runs the full batch transcription pipeline."""

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        model: str = "medium",
        chunk_minutes: float = 30.0,
        language: str = "",
        diarization: bool = False,
        convert_before_chunking: bool = True,
        device: Optional[str] = None,
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.model = model
        self.chunk_minutes = chunk_minutes
        self.language = language.strip() or None
        self.diarization = diarization
        self.convert_before_chunking = convert_before_chunking
        self.device = device

        self.signals = PipelineSignals()
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation. Pipeline will stop after current chunk."""
        self._cancelled = True
        log.warn("Cancellation requested – will stop after current chunk.")

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        """Execute the full pipeline. Call from a worker thread."""
        run_start = time.time()
        file_results: List[dict] = []

        try:
            # Load local Whisper model (may take several seconds; first run downloads)
            self.signals.status.emit(f"Loading Whisper model '{self.model}'...")
            self.signals.eta_update.emit(0.0, 0.0)
            client = LocalWhisperClient(
                model_name=self.model,
                device=self.device,
                on_status=lambda msg: (self.signals.status.emit(msg), log.info(msg)),
            )
            log.info(f"Whisper model '{self.model}' loaded on {client.device}.")

            # Discover audio files
            audio_files = self._discover_files()
            if not audio_files:
                msg = f"No audio files found in {self.input_dir}"
                log.warn(msg)
                self.signals.finished.emit(False, msg)
                return

            log.info(f"Found {len(audio_files)} audio file(s).")
            total_files = len(audio_files)

            os.makedirs(self.output_dir, exist_ok=True)

            # Track chunk-level progress for accurate ETA
            self._chunks_completed = 0
            self._chunks_known = 0       # chunks from files already chunked
            self._files_chunked = 0      # how many files we've chunked so far
            self._total_files = total_files
            self._run_start = run_start

            for file_idx, audio_path in enumerate(audio_files):
                if self._cancelled:
                    log.info("Pipeline cancelled by user.")
                    break

                filename = os.path.basename(audio_path)
                self.signals.file_progress.emit(file_idx, total_files, filename)
                self.signals.status.emit(f"Processing: {filename}")
                log.info(f"[{file_idx + 1}/{total_files}] Processing: {filename}")

                # Show elapsed time while chunking (before transcription starts)
                elapsed = time.time() - run_start
                self.signals.eta_update.emit(elapsed, 0.0)

                result = self._process_file(client, audio_path, file_idx, total_files)
                file_results.append(result)
                self.signals.file_done.emit(result)

            # Export run log
            run_end = time.time()
            run_settings = {
                "model": self.model,
                "chunk_minutes": self.chunk_minutes,
                "language": self.language,
                "diarization": self.diarization,
                "convert_before_chunking": self.convert_before_chunking,
                "input_dir": self.input_dir,
                "output_dir": self.output_dir,
            }
            run_timings = {
                "start_utc": datetime.fromtimestamp(run_start, tz=timezone.utc).isoformat(),
                "end_utc": datetime.fromtimestamp(run_end, tz=timezone.utc).isoformat(),
                "elapsed_sec": round(run_end - run_start, 2),
            }
            export_run_log(self.output_dir, file_results, run_settings, run_timings)
            log.info("Run log exported.")

            successful = sum(1 for r in file_results if r.get("success"))
            failed = sum(1 for r in file_results if not r.get("success"))
            cancelled_msg = " (cancelled)" if self._cancelled else ""
            summary = (
                f"Done{cancelled_msg}: {successful} succeeded, {failed} failed "
                f"out of {len(file_results)} processed."
            )
            log.info(summary)
            self.signals.file_progress.emit(total_files, total_files, "")
            self.signals.finished.emit(True, summary)

        except Exception as e:
            log.error(f"Pipeline error: {e}")
            self.signals.finished.emit(False, f"Pipeline error: {e}")

    def _discover_files(self) -> List[str]:
        """Recursively scan input_dir for supported audio files."""
        files = []
        for root, _, filenames in os.walk(self.input_dir):
            for fname in sorted(filenames):
                if Path(fname).suffix.lower() in SUPPORTED_EXTENSIONS:
                    files.append(os.path.join(root, fname))
        return files

    def _process_file(self, client: LocalWhisperClient, audio_path: str, file_idx: int, total_files: int) -> dict:
        """Process a single audio file: chunk -> transcribe -> export."""
        file_start = time.time()
        filename = os.path.basename(audio_path)
        result: Dict[str, Any] = {
            "filename": filename,
            "source_path": audio_path,
            "success": False,
            "error": None,
            "chunks_total": 0,
            "chunks_transcribed": 0,
            "txt_path": None,
            "json_path": None,
        }

        try:
            # Create temp work dir for chunks
            with tempfile.TemporaryDirectory(prefix="plaud_") as work_dir:
                self.signals.status.emit(f"Chunking: {filename}")
                log.info(f"Chunking: {filename} (chunk_minutes={self.chunk_minutes:.1f})")
                chunks = chunk_audio(
                    audio_path,
                    work_dir,
                    chunk_minutes=self.chunk_minutes,
                    force_convert=self.convert_before_chunking,
                )
                result["chunks_total"] = len(chunks)
                log.info(f"  Created {len(chunks)} chunk(s).")

                # Update chunk totals — estimate remaining files based on average chunks/file
                self._chunks_known += len(chunks)
                self._files_chunked += 1

                # Transcribe each chunk
                chunk_results = []

                for chunk_idx, chunk_info in enumerate(chunks):
                    if self._cancelled:
                        log.info(f"  Cancelled at chunk {chunk_idx + 1}/{len(chunks)}.")
                        break

                    self.signals.chunk_progress.emit(chunk_idx, len(chunks))
                    self.signals.status.emit(
                        f"Transcribing: {filename} — chunk {chunk_idx + 1}/{len(chunks)}"
                    )
                    log.info(f"  Transcribing chunk {chunk_idx + 1}/{len(chunks)}...")

                    tr = client.transcribe_chunk(
                        chunk_info["path"],
                        language=self.language,
                    )

                    chunk_result = {**chunk_info, **tr}
                    chunk_results.append(chunk_result)
                    result["chunks_transcribed"] += 1
                    self._chunks_completed += 1

                    # Emit chunk-level ETA
                    elapsed = time.time() - self._run_start
                    if self._chunks_completed > 0 and self._files_chunked > 0:
                        avg_chunks_per_file = self._chunks_known / self._files_chunked
                        remaining_files = self._total_files - self._files_chunked
                        estimated_total_chunks = self._chunks_known + (avg_chunks_per_file * remaining_files)
                        avg_per_chunk = elapsed / self._chunks_completed
                        estimated_total = avg_per_chunk * estimated_total_chunks
                        self.signals.eta_update.emit(elapsed, estimated_total)

                    if tr["error"]:
                        log.error(f"  Chunk {chunk_idx + 1} error: {tr['error']}")
                    else:
                        log.info(f"  Chunk {chunk_idx + 1} OK.")

                # Update chunk progress to complete
                self.signals.chunk_progress.emit(len(chunks), len(chunks))

                # Export
                file_end = time.time()
                settings = {
                    "model": self.model,
                    "chunk_minutes": self.chunk_minutes,
                    "language": self.language,
                    "diarization": self.diarization,
                    "convert_before_chunking": self.convert_before_chunking,
                }
                timings = {
                    "start_utc": datetime.fromtimestamp(file_start, tz=timezone.utc).isoformat(),
                    "end_utc": datetime.fromtimestamp(file_end, tz=timezone.utc).isoformat(),
                    "elapsed_sec": round(file_end - file_start, 2),
                }

                txt_path = export_transcript_txt(
                    self.output_dir, filename, chunk_results, self.diarization
                )
                json_path = export_transcript_json(
                    self.output_dir, filename, audio_path, chunk_results, settings, timings
                )

                result["txt_path"] = txt_path
                result["json_path"] = json_path
                result["success"] = True

                # Check for partial errors
                errors = [c for c in chunk_results if c.get("error")]
                if errors:
                    result["success"] = len(errors) < len(chunk_results)
                    result["error"] = f"{len(errors)} chunk(s) had errors"

                log.info(f"  Exported: {txt_path}")

        except Exception as e:
            result["error"] = str(e)
            log.error(f"  Failed to process {filename}: {e}")

        return result
