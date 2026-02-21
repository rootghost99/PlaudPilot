"""Background worker thread for running the transcription pipeline."""

from PySide6.QtCore import QThread, Signal

from ..core.pipeline import TranscriptionPipeline


class PipelineWorker(QThread):
    """Runs TranscriptionPipeline in a background thread.

    All pipeline signals are forwarded so the UI can connect to them.
    """

    # Re-emitted signals
    file_progress = Signal(int, int, str)
    chunk_progress = Signal(int, int)
    status = Signal(str)
    finished = Signal(bool, str)
    file_done = Signal(dict)
    eta_update = Signal(float, float)

    def __init__(self, pipeline: TranscriptionPipeline, parent=None):
        super().__init__(parent)
        self.pipeline = pipeline

        # Wire pipeline signals to worker signals
        self.pipeline.signals.file_progress.connect(self.file_progress.emit)
        self.pipeline.signals.chunk_progress.connect(self.chunk_progress.emit)
        self.pipeline.signals.status.connect(self.status.emit)
        self.pipeline.signals.finished.connect(self.finished.emit)
        self.pipeline.signals.file_done.connect(self.file_done.emit)
        self.pipeline.signals.eta_update.connect(self.eta_update.emit)

    def run(self):
        self.pipeline.run()

    def cancel(self):
        self.pipeline.cancel()
