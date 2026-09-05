"""Writing rendered transcripts to disk."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .formats import Segment, render
from .paths import PathError, resolve_output_path


class WriteError(Exception):
    """An output file could not be written."""


def write_outputs(
    segments: Sequence[Segment],
    source: Path,
    formats: Sequence[str],
    output_dir: Path | None = None,
) -> list[Path]:
    """Render and write one file per requested format. Returns the paths written."""
    if not formats:
        raise WriteError("No output format selected.")
    written: list[Path] = []
    for fmt in formats:
        written.append(_write_one(segments, source, fmt, output_dir))
    return written


def _write_one(segments: Sequence[Segment], source: Path, fmt: str, output_dir: Path | None) -> Path:
    try:
        target = resolve_output_path(source, fmt, output_dir, exists=Path.exists)
    except PathError as exc:
        raise WriteError(str(exc)) from exc
    text = render(segments, fmt)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # newline="" keeps the CRLF that Windows subtitle tools expect out of
        # the equation - we write exactly the bytes the renderer produced.
        with target.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    except PermissionError:
        raise WriteError(f"No permission to write {target}.") from None
    except OSError as exc:
        raise WriteError(f"Could not write {target} ({exc.strerror}).") from exc
    return target
