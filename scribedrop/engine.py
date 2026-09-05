"""The transcription engine: device selection, model loading, decoding.

Everything that talks to faster-whisper lives here. No Tk imports, so the
engine can be driven from a script or a test.

Device policy: try GPU at the best precision, and step down one rung at a
time - float16 -> int8_float16 -> CPU int8 - on any failure that looks
like a device or VRAM problem. Every step down is announced, never silent.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from .cuda_paths import missing_cuda_libraries, register_cuda_dlls
from .formats import Segment
from .media import MediaError, check_input_file, find_ffmpeg, probe_duration, transcode_to_wav

register_cuda_dlls()  # must happen before the first `import ctranslate2`

ProgressFn = Callable[[float, str], None]
CancelFn = Callable[[], bool]

# Signals that mean "this device or precision will not work", as opposed to
# a genuinely broken input file.
_DEVICE_FAILURE_MARKERS = (
    "out of memory",
    "cuda",
    "cudnn",
    "cublas",
    "cudart",
    "nvrtc",
    "no kernel image",
    "unsupported compute type",
    "is not found or cannot be loaded",
)


class TranscriptionCancelled(Exception):
    """Raised when the user cancels a running job."""


class EngineError(Exception):
    """Transcription failed for a reason worth showing the user."""


@dataclass(frozen=True)
class DeviceChoice:
    device: str
    compute_type: str

    @property
    def label(self) -> str:
        friendly = "GPU (CUDA)" if self.device == "cuda" else "CPU"
        return f"{friendly} / {self.compute_type}"


CPU_LADDER = (DeviceChoice("cpu", "int8"),)
GPU_LADDER = (
    DeviceChoice("cuda", "float16"),
    DeviceChoice("cuda", "int8_float16"),
)


def cuda_device_present() -> bool:
    """True if CTranslate2 can see a CUDA device. Never raises."""
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:  # noqa: BLE001 - a broken CUDA install must not crash the app
        return False


def gpu_status() -> tuple[bool, str]:
    """(usable, human explanation). The status line shows the explanation."""
    if not cuda_device_present():
        return False, "No CUDA GPU detected - will use the CPU."
    missing = missing_cuda_libraries()
    if missing:
        return False, (
            "CUDA GPU found but " + ", ".join(missing) + " is missing - will use the CPU. "
            "Run setup.bat again, or: pip install -r requirements-gpu.txt"
        )
    return True, "GPU (CUDA) ready."


def cuda_available() -> bool:
    """True only if a CUDA device AND its runtime libraries are both usable."""
    return gpu_status()[0]


def device_ladder(preference: str = "auto") -> tuple[DeviceChoice, ...]:
    """Ordered device/precision combinations to try, best first.

    GPU rungs are only offered when the CUDA runtime libraries actually load;
    otherwise we go straight to CPU rather than stalling on a broken GPU path.
    """
    if preference == "cpu":
        return CPU_LADDER
    if not cuda_available():
        return CPU_LADDER
    return GPU_LADDER + CPU_LADDER


def looks_like_device_failure(exc: BaseException) -> bool:
    """Distinguish 'this GPU path is broken' from 'this file is broken'."""
    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in _DEVICE_FAILURE_MARKERS)


class Transcriber:
    """Loads one model at a time and reuses it across a queue of files."""

    def __init__(self, models_dir: Path, preference: str = "auto") -> None:
        self._models_dir = Path(models_dir)
        self._ladder = device_ladder(preference)
        self._rung = 0
        self._model = None
        self._model_key: str | None = None
        self._choice: DeviceChoice | None = None

    @property
    def active_device(self) -> DeviceChoice | None:
        return self._choice

    def release(self) -> None:
        """Drop the loaded model so VRAM comes back."""
        self._model = None
        self._model_key = None
        self._choice = None

    # ------------------------------------------------------------- loading

    def ensure_model(self, model_key: str, on_progress: ProgressFn) -> DeviceChoice:
        """Load `model_key`, walking down the device ladder on device failures."""
        if self._model is not None and self._model_key == model_key:
            return self._choice  # type: ignore[return-value]
        self.release()
        self._models_dir.mkdir(parents=True, exist_ok=True)
        return self._load_from(self._rung, model_key, on_progress)

    def _load_from(self, start: int, model_key: str, on_progress: ProgressFn) -> DeviceChoice:
        errors: list[str] = []
        for rung in range(start, len(self._ladder)):
            choice = self._ladder[rung]
            on_progress(0.0, f"Loading model '{model_key}' on {choice.label}...")
            try:
                self._model = self._build_model(model_key, choice)
            except Exception as exc:  # noqa: BLE001 - classified immediately below
                errors.append(f"{choice.label}: {exc}")
                if looks_like_device_failure(exc):
                    on_progress(0.0, f"{choice.label} unavailable - trying the next option.")
                    continue
                raise EngineError(f"Could not load model '{model_key}': {exc}") from exc
            self._model_key, self._choice, self._rung = model_key, choice, rung
            on_progress(0.0, f"Using {choice.label}.")
            return choice
        raise EngineError("No usable device for this model. Tried:\n  " + "\n  ".join(errors))

    def _build_model(self, model_key: str, choice: DeviceChoice):
        from faster_whisper import WhisperModel

        return WhisperModel(
            model_key,
            device=choice.device,
            compute_type=choice.compute_type,
            download_root=str(self._models_dir),
        )

    def _demote(self, model_key: str, on_progress: ProgressFn) -> bool:
        """Step down one rung after a runtime device failure. False if none left."""
        if self._rung + 1 >= len(self._ladder):
            return False
        failed = self._ladder[self._rung].label
        self.release()
        self._rung += 1
        on_progress(0.0, f"{failed} failed at runtime - falling back to {self._ladder[self._rung].label}.")
        self._load_from(self._rung, model_key, on_progress)
        return True

    # --------------------------------------------------------- transcribing

    def transcribe(
        self,
        source: Path,
        model_key: str,
        language: str,
        on_progress: ProgressFn,
        is_cancelled: CancelFn,
    ) -> list[Segment]:
        """Transcribe one file. Raises MediaError, EngineError or TranscriptionCancelled."""
        check_input_file(source)
        self.ensure_model(model_key, on_progress)
        with tempfile.TemporaryDirectory(prefix="scribedrop-") as tmp:
            try:
                return self._attempt(source, model_key, language, on_progress, is_cancelled)
            except (TranscriptionCancelled, EngineError, MediaError):
                raise
            except Exception as exc:  # noqa: BLE001 - decode failure: try FFmpeg
                converted = self._transcode(source, Path(tmp), exc, on_progress)
                return self._attempt(converted, model_key, language, on_progress, is_cancelled)

    def _attempt(
        self,
        source: Path,
        model_key: str,
        language: str,
        on_progress: ProgressFn,
        is_cancelled: CancelFn,
    ) -> list[Segment]:
        """Run decoding, stepping down the device ladder on runtime device failures."""
        while True:
            try:
                return self._run(source, language, on_progress, is_cancelled)
            except (TranscriptionCancelled, MediaError):
                raise
            except Exception as exc:  # noqa: BLE001 - classified immediately below
                if not looks_like_device_failure(exc):
                    raise
                if not self._demote(model_key, on_progress):
                    raise EngineError(f"Transcription failed on every device: {exc}") from exc

    def _transcode(self, source: Path, tmp: Path, exc: Exception, on_progress: ProgressFn) -> Path:
        ffmpeg = find_ffmpeg()
        if ffmpeg is None:
            raise MediaError(
                f"Could not decode this file ({exc}). FFmpeg is not installed, so there is no "
                "fallback. Install it with:  winget install Gyan.FFmpeg"
            ) from exc
        on_progress(0.0, "Unsupported container - converting with FFmpeg...")
        destination = tmp / "converted.wav"
        transcode_to_wav(source, destination, ffmpeg)
        return destination

    def _run(
        self, source: Path, language: str, on_progress: ProgressFn, is_cancelled: CancelFn
    ) -> list[Segment]:
        if self._model is None:
            raise EngineError("Model is not loaded.")
        lang = None if language in ("", "auto") else language
        segments, info = self._model.transcribe(
            str(source), language=lang, vad_filter=True, beam_size=5
        )
        duration = float(getattr(info, "duration", 0.0) or 0.0) or (probe_duration(source) or 0.0)
        detected = getattr(info, "language", None)
        if lang is None and detected:
            on_progress(0.0, f"Detected language: {detected}")
        return list(self._drain(segments, duration, on_progress, is_cancelled))

    @staticmethod
    def _drain(
        segments, duration: float, on_progress: ProgressFn, is_cancelled: CancelFn
    ) -> Iterator[Segment]:
        for raw in segments:
            if is_cancelled():
                raise TranscriptionCancelled()
            fraction = min(float(raw.end) / duration, 1.0) if duration > 0 else 0.0
            on_progress(fraction, "Transcribing...")
            yield Segment(start=float(raw.start), end=float(raw.end), text=raw.text)
