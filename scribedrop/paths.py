"""Where transcripts get written.

Pure path arithmetic - the caller injects an `exists` predicate so the
collision logic is testable without touching the filesystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

MAX_COLLISION_ATTEMPTS = 999

# Containers faster-whisper can decode via PyAV/ffmpeg. Anything else we
# reject up front rather than failing three minutes into a queue.
AUDIO_EXTENSIONS = frozenset(
    {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".opus", ".wma", ".aiff", ".aif"}
)
VIDEO_EXTENSIONS = frozenset(
    {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".mpg", ".mpeg", ".ts"}
)
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


class PathError(ValueError):
    """Raised when an output path cannot be resolved."""


def is_media_file(path: Path) -> bool:
    """True if the extension is one we can plausibly decode."""
    return path.suffix.lower() in MEDIA_EXTENSIONS


def _never_exists(_: Path) -> bool:
    return False


def resolve_output_path(
    source: Path,
    fmt: str,
    output_dir: Path | None = None,
    exists: Callable[[Path], bool] | None = None,
) -> Path:
    """Return the file to write for `source` in format `fmt`.

    Default is next to the source file. If `output_dir` is given the file
    goes there instead. Existing files are never overwritten - a numeric
    suffix is appended.
    """
    fmt = fmt.lstrip(".").lower()
    if not fmt or not fmt.isalnum():
        raise PathError(f"invalid output format {fmt!r}")
    if source.name in ("", ".", ".."):
        raise PathError(f"invalid source file name {str(source)!r}")

    stem = source.stem or source.name
    folder = output_dir if output_dir is not None else source.parent
    candidate = Path(folder) / f"{stem}.{fmt}"
    return _avoid_collision(candidate, exists or _never_exists)


def _avoid_collision(candidate: Path, exists: Callable[[Path], bool]) -> Path:
    if not exists(candidate):
        return candidate
    stem, suffix, parent = candidate.stem, candidate.suffix, candidate.parent
    for attempt in range(1, MAX_COLLISION_ATTEMPTS + 1):
        alternative = parent / f"{stem} ({attempt}){suffix}"
        if not exists(alternative):
            return alternative
    raise PathError(f"could not find a free name for {candidate} after {MAX_COLLISION_ATTEMPTS} tries")


def collect_media_files(entries: Iterable[Path], max_depth: int = 6) -> list[Path]:
    """Expand a mix of files and folders into a sorted, de-duplicated file list.

    Folders are walked recursively (bounded depth so a symlink loop or a
    dropped drive root cannot hang the UI thread).
    """
    found: set[Path] = set()
    for entry in entries:
        _collect_one(Path(entry), found, max_depth)
    return sorted(found)


def _collect_one(entry: Path, found: set[Path], max_depth: int) -> None:
    try:
        if entry.is_file():
            if is_media_file(entry):
                found.add(entry.resolve())
            return
        if not entry.is_dir():
            return
        base_depth = len(entry.resolve().parts)
        for child in entry.rglob("*"):
            if len(child.parts) - base_depth > max_depth:
                continue
            if child.is_file() and is_media_file(child):
                found.add(child.resolve())
    except OSError:
        # An unreadable folder must not kill the whole drop. Skipping it is
        # the correct behaviour; the file simply never enters the queue.
        return
