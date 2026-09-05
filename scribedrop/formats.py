"""Subtitle and transcript formatting.

Pure functions only - no I/O, no GUI, no model code. Everything here is
directly unit-testable and is the part of the product most likely to be
subtly wrong, so it lives on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

MAX_TIMESTAMP_SECONDS = 359999.999  # 99:59:59.999 - the SRT/VTT ceiling


class FormatError(ValueError):
    """Raised when a segment cannot be rendered into a subtitle format."""


@dataclass(frozen=True)
class Segment:
    """One transcribed span of audio. Immutable by design."""

    start: float
    end: float
    text: str

    def cleaned(self) -> "Segment":
        """Return a normalised copy: trimmed text, non-negative monotonic times."""
        start = max(0.0, float(self.start))
        end = max(start, float(self.end))
        return Segment(start=start, end=end, text=" ".join(self.text.split()))


def _validate_seconds(seconds: float) -> float:
    if seconds != seconds:  # NaN
        raise FormatError("timestamp is NaN")
    if seconds in (float("inf"), float("-inf")):
        raise FormatError("timestamp is infinite")
    if seconds < 0:
        return 0.0
    if seconds > MAX_TIMESTAMP_SECONDS:
        return MAX_TIMESTAMP_SECONDS
    return float(seconds)


def format_timestamp(seconds: float, decimal_sep: str = ",") -> str:
    """Render seconds as HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT).

    Negative values clamp to zero, values beyond 99:59:59.999 clamp to the
    ceiling, and rounding never produces a 1000ms field.
    """
    if decimal_sep not in (",", "."):
        raise FormatError(f"decimal separator must be ',' or '.', got {decimal_sep!r}")
    total_ms = int(round(_validate_seconds(seconds) * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{decimal_sep}{millis:03d}"


def normalise_segments(segments: Iterable[Segment]) -> list[Segment]:
    """Clean, drop empties, and sort by start time then end time.

    Whisper can emit out-of-order or empty segments after VAD filtering;
    subtitle players treat that as a corrupt file, so we fix it here.
    """
    cleaned = [seg.cleaned() for seg in segments]
    kept = [seg for seg in cleaned if seg.text]
    return sorted(kept, key=lambda seg: (seg.start, seg.end))


def segments_to_srt(segments: Iterable[Segment]) -> str:
    """Render SRT. Always ends with a trailing newline, as the spec expects."""
    blocks = []
    for index, seg in enumerate(normalise_segments(segments), start=1):
        start = format_timestamp(seg.start, ",")
        end = format_timestamp(seg.end, ",")
        blocks.append(f"{index}\n{start} --> {end}\n{seg.text}\n")
    return "\n".join(blocks)


def segments_to_vtt(segments: Iterable[Segment]) -> str:
    """Render WebVTT with the mandatory WEBVTT header."""
    blocks = ["WEBVTT\n"]
    for seg in normalise_segments(segments):
        start = format_timestamp(seg.start, ".")
        end = format_timestamp(seg.end, ".")
        blocks.append(f"{start} --> {end}\n{seg.text}\n")
    return "\n".join(blocks)


def segments_to_txt(segments: Iterable[Segment]) -> str:
    """Render plain text: one line per segment, no timestamps."""
    lines = [seg.text for seg in normalise_segments(segments)]
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


RENDERERS = {
    "srt": segments_to_srt,
    "vtt": segments_to_vtt,
    "txt": segments_to_txt,
}


def render(segments: Sequence[Segment], fmt: str) -> str:
    """Render segments into the named format. Raises on an unknown format."""
    try:
        renderer = RENDERERS[fmt]
    except KeyError:
        known = ", ".join(sorted(RENDERERS))
        raise FormatError(f"unknown output format {fmt!r} (known: {known})") from None
    return renderer(segments)
