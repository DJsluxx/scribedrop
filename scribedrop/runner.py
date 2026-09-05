"""Background queue runner.

The GUI never calls the engine directly. It starts a QueueRunner on a
worker thread and receives immutable events through a thread-safe queue,
which the Tk loop drains on a timer. That is what keeps the window
responsive while a 3 GB model chews through an hour of audio.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .engine import EngineError, Transcriber, TranscriptionCancelled
from .media import MediaError
from .settings import Settings
from .writer import WriteError, write_outputs


@dataclass(frozen=True)
class Event:
    kind: str  # status | start | progress | done | error | cancelled | finished
    index: int = -1
    fraction: float = 0.0
    message: str = ""
    outputs: tuple[Path, ...] = ()


class QueueRunner:
    """Runs a list of files through the engine on a single worker thread."""

    def __init__(self, files: Sequence[Path], settings: Settings) -> None:
        self._files = list(files)
        self._settings = settings
        self.events: "queue.Queue[Event]" = queue.Queue()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def total(self) -> int:
        return len(self._files)

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("QueueRunner can only be started once.")
        self._thread = threading.Thread(target=self._run, name="scribedrop-worker", daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _emit(self, kind: str, **kwargs) -> None:
        self.events.put(Event(kind=kind, **kwargs))

    def _run(self) -> None:
        succeeded = failed = cancelled = 0
        transcriber = Transcriber(self._settings.resolved_models_dir(), self._settings.device)
        try:
            for index, source in enumerate(self._files):
                if self._cancel.is_set():
                    self._emit("cancelled", index=index)
                    cancelled += 1
                    break
                outcome = self._run_one(transcriber, index, source)
                succeeded += 1 if outcome == "done" else 0
                failed += 1 if outcome == "error" else 0
                cancelled += 1 if outcome == "cancelled" else 0
        finally:
            transcriber.release()
            self._emit(
                "finished",
                message=self._summary(succeeded, failed, cancelled),
            )

    def _summary(self, succeeded: int, failed: int, cancelled: int = 0) -> str:
        """One sentence for the status bar. A cancelled file is never a failure."""
        parts = [f"{succeeded} transcribed"]
        if cancelled:
            parts.append(f"{cancelled} cancelled")
        if failed:
            parts.append(f"{failed} failed")
        tail = ", ".join(parts)
        if self._cancel.is_set():
            return f"Cancelled. {tail}."
        return f"Done: {tail}."

    def _run_one(self, transcriber: Transcriber, index: int, source: Path) -> str:
        """Returns the outcome for one file: 'done', 'error' or 'cancelled'."""
        self._emit("start", index=index, message=source.name)

        def progress(fraction: float, message: str) -> None:
            self._emit("progress", index=index, fraction=fraction, message=message)

        try:
            segments = transcriber.transcribe(
                source,
                self._settings.model,
                self._settings.language,
                progress,
                self._cancel.is_set,
            )
        except TranscriptionCancelled:
            self._emit("cancelled", index=index, message="Cancelled")
            return "cancelled"
        except (MediaError, EngineError) as exc:
            self._emit("error", index=index, message=str(exc))
            return "error"
        except Exception as exc:  # noqa: BLE001 - a worker thread must never die silently
            self._emit("error", index=index, message=f"Unexpected error: {exc}")
            return "error"
        return self._write(index, source, segments)

    def _write(self, index: int, source: Path, segments) -> str:
        if not segments:
            self._emit("error", index=index, message="No speech was detected in this file.")
            return "error"
        try:
            outputs = write_outputs(
                segments, source, self._settings.formats, self._settings.resolved_output_dir()
            )
        except WriteError as exc:
            self._emit("error", index=index, message=str(exc))
            return "error"
        self._emit("done", index=index, fraction=1.0, outputs=tuple(outputs))
        return "done"
