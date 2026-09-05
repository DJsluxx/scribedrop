"""Media inspection and the optional ffmpeg escape hatch.

ScribeDrop decodes audio through PyAV, which ships its own FFmpeg
libraries - so ffmpeg.exe is NOT required for normal use. It is only used
as a fallback for containers PyAV refuses to open. We never bundle
ffmpeg.exe; if it is missing we say so and explain how to install it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG_HINT = (
    "FFmpeg was not found. Most files still work without it. To install it, open "
    "PowerShell and run:  winget install Gyan.FFmpeg"
)
FFMPEG_TIMEOUT_SECONDS = 900
MIN_USEFUL_BYTES = 1024


class MediaError(Exception):
    """A file cannot be used as transcription input."""


def find_ffmpeg() -> Path | None:
    """Locate ffmpeg.exe on PATH, or in the usual winget install location."""
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return None
    pattern = "Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin/ffmpeg.exe"
    for candidate in sorted(Path(local).glob(pattern)):
        if candidate.is_file():
            return candidate
    return None


def check_input_file(path: Path) -> None:
    """Fail fast and specifically on the boring problems. Raises MediaError."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        raise MediaError("File no longer exists.") from None
    except PermissionError:
        raise MediaError("Windows denied access to this file.") from None
    except OSError as exc:
        raise MediaError(f"Cannot read file ({exc.strerror}).") from None

    if not path.is_file():
        raise MediaError("Not a file.")
    if stat.st_size == 0:
        raise MediaError("File is empty (0 bytes).")
    if stat.st_size < MIN_USEFUL_BYTES:
        raise MediaError("File is too small to contain audio.")
    _check_not_locked(path)


def _check_not_locked(path: Path) -> None:
    try:
        with path.open("rb") as handle:
            handle.read(16)
    except PermissionError:
        raise MediaError("File is locked by another program. Close it and retry.") from None
    except OSError as exc:
        raise MediaError(f"Cannot open file ({exc.strerror}).") from None


def probe_duration(path: Path) -> float | None:
    """Best-effort duration in seconds via PyAV. None if it cannot be read."""
    try:
        import av  # imported lazily: PyAV is slow to load
    except ImportError:
        return None
    try:
        with av.open(str(path)) as container:
            if container.duration:
                return float(container.duration) / 1_000_000.0
    except Exception:
        return None
    return None


def _no_window_flags() -> int:
    """Stop a console window flashing when the GUI shells out on Windows."""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def transcode_to_wav(source: Path, destination: Path, ffmpeg: Path) -> None:
    """Convert anything ffmpeg understands into 16 kHz mono WAV. Raises MediaError."""
    command = [
        str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", str(destination),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS, creationflags=_no_window_flags(),
        )
    except subprocess.TimeoutExpired:
        raise MediaError("FFmpeg took too long to convert this file.") from None
    except OSError as exc:
        raise MediaError(f"Could not run FFmpeg ({exc.strerror}).") from None

    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else f"exit code {result.returncode}"
        raise MediaError(f"FFmpeg could not decode this file: {reason}")
    if not destination.exists() or destination.stat().st_size < MIN_USEFUL_BYTES:
        raise MediaError("FFmpeg produced no audio - the file may have no audio track.")
