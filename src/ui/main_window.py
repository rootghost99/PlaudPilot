"""Main application window for PlaudTranscriber."""

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core import logging as log
from ..core.pipeline import TranscriptionPipeline
from ..core.settings import load_settings, save_settings
from ..core.whisper_local import WHISPER_MODELS, detect_device
from .worker import PipelineWorker

APP_VERSION = "1.0.0"
APP_NAME = "PlaudTranscriber"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(780, 680)
        self.resize(860, 740)

        self._worker: PipelineWorker | None = None
        self._settings = load_settings()

        self._build_menu()
        self._build_ui()
        self._connect_log()
        self._restore_settings()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------
    def _build_menu(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        logs_action = QAction("View &Logs Folder", self)
        logs_action.triggered.connect(self._open_logs_folder)
        help_menu.addAction(logs_action)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # --- Source / Destination ---
        folders_group = QGroupBox("Folders")
        folders_layout = QVBoxLayout(folders_group)
        folders_layout.setSpacing(4)

        # Input folder
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Source folder:"))
        self.input_dir_edit = QLineEdit()
        self.input_dir_edit.setPlaceholderText("Select folder containing audio files...")
        row1.addWidget(self.input_dir_edit, 1)
        btn_browse_in = QPushButton("Browse...")
        btn_browse_in.setFixedWidth(90)
        btn_browse_in.clicked.connect(self._browse_input)
        row1.addWidget(btn_browse_in)
        folders_layout.addLayout(row1)

        # Output folder
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Output folder:"))
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select folder for transcripts...")
        row2.addWidget(self.output_dir_edit, 1)
        btn_browse_out = QPushButton("Browse...")
        btn_browse_out.setFixedWidth(90)
        btn_browse_out.clicked.connect(self._browse_output)
        row2.addWidget(btn_browse_out)
        folders_layout.addLayout(row2)

        layout.addWidget(folders_group)

        # --- Settings ---
        settings_group = QGroupBox("Transcription Settings")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(4)

        row_s1 = QHBoxLayout()
        row_s1.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        for name, ram in WHISPER_MODELS.items():
            self.model_combo.addItem(f"{name}  ({ram})", name)
        self.model_combo.setFixedWidth(250)
        row_s1.addWidget(self.model_combo)

        row_s1.addSpacing(20)
        row_s1.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cpu", "cuda"])
        self.device_combo.setFixedWidth(90)
        row_s1.addWidget(self.device_combo)

        row_s1.addSpacing(10)
        detected = detect_device()
        gpu_text = "CUDA GPU available" if detected == "cuda" else "CPU only (no CUDA GPU detected)"
        gpu_color = "#228B22" if detected == "cuda" else "#B8860B"
        self.gpu_label = QLabel(gpu_text)
        self.gpu_label.setStyleSheet(f"color: {gpu_color}; font-style: italic;")
        row_s1.addWidget(self.gpu_label)

        row_s1.addStretch()
        settings_layout.addLayout(row_s1)

        row_s1b = QHBoxLayout()
        row_s1b.addWidget(QLabel("Chunk length (min):"))
        self.chunk_spin = QDoubleSpinBox()
        self.chunk_spin.setRange(1.0, 120.0)
        self.chunk_spin.setValue(30.0)
        self.chunk_spin.setSingleStep(5.0)
        self.chunk_spin.setDecimals(1)
        self.chunk_spin.setFixedWidth(80)
        row_s1b.addWidget(self.chunk_spin)

        row_s1b.addSpacing(20)
        row_s1b.addWidget(QLabel("Language hint:"))
        self.language_edit = QLineEdit()
        self.language_edit.setPlaceholderText("e.g. en")
        self.language_edit.setFixedWidth(70)
        row_s1b.addWidget(self.language_edit)
        row_s1b.addStretch()
        settings_layout.addLayout(row_s1b)

        row_s2 = QHBoxLayout()
        self.diarization_check = QCheckBox("Enable diarization (experimental)")
        row_s2.addWidget(self.diarization_check)
        row_s2.addSpacing(20)
        self.convert_check = QCheckBox("Convert before chunking (recommended for WAV)")
        self.convert_check.setChecked(True)
        row_s2.addWidget(self.convert_check)
        row_s2.addStretch()
        settings_layout.addLayout(row_s2)

        layout.addWidget(settings_group)

        # --- Run controls ---
        controls_group = QGroupBox("Run Controls")
        controls_layout = QHBoxLayout(controls_group)

        self.btn_start = QPushButton("  Start Transcription  ")
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #0078D4; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #106EBE; }"
            "QPushButton:disabled { background-color: #CCCCCC; color: #666666; }"
        )
        self.btn_start.clicked.connect(self._start)
        controls_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("  Cancel  ")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet(
            "QPushButton { padding: 8px 16px; border-radius: 4px; }"
        )
        self.btn_cancel.clicked.connect(self._cancel)
        controls_layout.addWidget(self.btn_cancel)

        self.btn_open_output = QPushButton("  Open Output Folder  ")
        self.btn_open_output.setStyleSheet(
            "QPushButton { padding: 8px 16px; border-radius: 4px; }"
        )
        self.btn_open_output.clicked.connect(self._open_output_folder)
        controls_layout.addWidget(self.btn_open_output)

        controls_layout.addStretch()
        layout.addWidget(controls_group)

        # --- Progress ---
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(4)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(self.status_label)

        lbl_overall = QLabel("Overall (files):")
        progress_layout.addWidget(lbl_overall)
        self.progress_files = QProgressBar()
        self.progress_files.setValue(0)
        progress_layout.addWidget(self.progress_files)

        lbl_chunk = QLabel("Current file (chunks):")
        progress_layout.addWidget(lbl_chunk)
        self.progress_chunks = QProgressBar()
        self.progress_chunks.setValue(0)
        progress_layout.addWidget(self.progress_chunks)

        layout.addWidget(progress_group)

        # --- Log panel ---
        log_group = QGroupBox("Logs")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMinimumHeight(120)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group, 1)  # stretch factor

    # ------------------------------------------------------------------
    # Logging connection
    # ------------------------------------------------------------------
    def _connect_log(self):
        emitter = log.get_emitter()
        emitter.log_message.connect(self._append_log)

    @Slot(str, str)
    def _append_log(self, severity: str, message: str):
        color_map = {"INFO": "#222222", "WARN": "#B8860B", "ERROR": "#CC0000"}
        color = color_map.get(severity, "#222222")
        self.log_text.append(f'<span style="color:{color};">{_html_escape(message)}</span>')
        # Auto-scroll to bottom
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ------------------------------------------------------------------
    # Settings save/restore
    # ------------------------------------------------------------------
    def _restore_settings(self):
        s = self._settings
        self.input_dir_edit.setText(s.get("input_dir", ""))
        self.output_dir_edit.setText(s.get("output_dir", ""))
        model = s.get("model", "medium")
        idx = self.model_combo.findData(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.chunk_spin.setValue(s.get("chunk_minutes", 30.0))
        self.language_edit.setText(s.get("language", ""))
        self.diarization_check.setChecked(s.get("diarization", False))
        self.convert_check.setChecked(s.get("convert_before_chunking", True))
        device_idx = self.device_combo.findText(s.get("device", "auto"))
        if device_idx >= 0:
            self.device_combo.setCurrentIndex(device_idx)

    def _persist_settings(self):
        settings = {
            "input_dir": self.input_dir_edit.text().strip(),
            "output_dir": self.output_dir_edit.text().strip(),
            "model": self.model_combo.currentData(),
            "chunk_minutes": self.chunk_spin.value(),
            "language": self.language_edit.text().strip(),
            "diarization": self.diarization_check.isChecked(),
            "convert_before_chunking": self.convert_check.isChecked(),
            "device": self.device_combo.currentText(),
        }
        save_settings(settings)

    def closeEvent(self, event):
        self._persist_settings()
        if self._worker and self._worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Transcription Running",
                "A transcription is in progress. Cancel and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            self._worker.cancel()
            self._worker.wait(5000)
        event.accept()

    # ------------------------------------------------------------------
    # Browse dialogs
    # ------------------------------------------------------------------
    def _browse_input(self):
        d = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if d:
            self.input_dir_edit.setText(d)

    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d:
            self.output_dir_edit.setText(d)

    # ------------------------------------------------------------------
    # Run controls
    # ------------------------------------------------------------------
    def _start(self):
        input_dir = self.input_dir_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()

        if not input_dir or not os.path.isdir(input_dir):
            QMessageBox.warning(self, "Invalid Input", "Please select a valid source folder.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Invalid Output", "Please select an output folder.")
            return

        self._persist_settings()

        device = self.device_combo.currentText()
        if device == "auto":
            device = None

        pipeline = TranscriptionPipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            model=self.model_combo.currentData(),
            chunk_minutes=self.chunk_spin.value(),
            language=self.language_edit.text().strip(),
            diarization=self.diarization_check.isChecked(),
            convert_before_chunking=self.convert_check.isChecked(),
            device=device,
        )

        self._worker = PipelineWorker(pipeline, parent=self)
        self._worker.file_progress.connect(self._on_file_progress)
        self._worker.chunk_progress.connect(self._on_chunk_progress)
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_finished)

        # Reset UI
        self.progress_files.setValue(0)
        self.progress_chunks.setValue(0)
        self.log_text.clear()

        self._set_running(True)
        self._worker.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.status_label.setText("Cancelling...")

    def _set_running(self, running: bool):
        self.btn_start.setEnabled(not running)
        self.btn_cancel.setEnabled(running)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    @Slot(int, int, str)
    def _on_file_progress(self, current: int, total: int, filename: str):
        self.progress_files.setMaximum(total)
        self.progress_files.setValue(current)
        if filename:
            self.progress_files.setFormat(f"{current + 1}/{total}  —  {filename}")
        else:
            self.progress_files.setFormat(f"{current}/{total}")

    @Slot(int, int)
    def _on_chunk_progress(self, current: int, total: int):
        self.progress_chunks.setMaximum(max(total, 1))
        self.progress_chunks.setValue(current)
        self.progress_chunks.setFormat(f"{current}/{total}")

    @Slot(str)
    def _on_status(self, text: str):
        self.status_label.setText(text)

    @Slot(bool, str)
    def _on_finished(self, success: bool, message: str):
        self._set_running(False)
        self.status_label.setText(message)
        if success:
            log.info(message)
        else:
            log.error(message)

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------
    def _show_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h3>{APP_NAME} v{APP_VERSION}</h3>"
            "<p>Batch audio transcription using local OpenAI Whisper models.</p>"
            "<p>Handles Plaud-exported MP3/WAV files with automatic "
            "conversion, chunking, and on-device inference.</p>"
            "<hr>"
            "<p><small>Built with PySide6 + OpenAI Whisper + FFmpeg</small></p>",
        )

    def _open_logs_folder(self):
        log_dir = _logs_dir()
        os.makedirs(log_dir, exist_ok=True)
        _open_folder(log_dir)

    def _open_output_folder(self):
        d = self.output_dir_edit.text().strip()
        if d and os.path.isdir(d):
            _open_folder(d)
        else:
            QMessageBox.information(self, "Output Folder", "No valid output folder set.")


# ----------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------

def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _logs_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "PlaudTranscriber", "logs")


def _open_folder(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
