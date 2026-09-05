"""Manual end-to-end smoke test.

Drives the real QueueRunner - the exact code path the GUI uses - against
real media files, and prints the events plus the files produced. Not part
of the pytest suite because it downloads a model and needs real audio.

Usage:
    python tests/manual_smoke.py <media file> [more files...] [--model small]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scribedrop.engine import cuda_available  # noqa: E402
from scribedrop.runner import QueueRunner  # noqa: E402
from scribedrop.settings import Settings  # noqa: E402


def parse_args(argv: list[str]) -> tuple[list[Path], str, str]:
    files: list[Path] = []
    model, models_dir = "small", ""
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--model" and index + 1 < len(argv):
            model, index = argv[index + 1], index + 2
            continue
        if item == "--models-dir" and index + 1 < len(argv):
            models_dir, index = argv[index + 1], index + 2
            continue
        files.append(Path(item))
        index += 1
    return files, model, models_dir


def main() -> int:
    files, model, models_dir = parse_args(sys.argv[1:])
    if not files:
        print("usage: manual_smoke.py <media file> [--model small] [--models-dir DIR]")
        return 2

    settings = Settings(
        model=model, language="auto", formats=("txt", "srt", "vtt"), models_dir=models_dir
    )
    print(f"CUDA visible to CTranslate2: {cuda_available()}")
    print(f"Model: {model}   Files: {[f.name for f in files]}")

    runner = QueueRunner(files, settings)
    started = time.monotonic()
    runner.start()
    last_progress = ""
    while runner.is_running() or not runner.events.empty():
        try:
            event = runner.events.get(timeout=0.2)
        except Exception:
            continue
        if event.kind == "progress" and event.message == last_progress:
            continue
        last_progress = event.message if event.kind == "progress" else ""
        detail = f" -> {[p.name for p in event.outputs]}" if event.outputs else ""
        print(f"[{time.monotonic() - started:7.2f}s] {event.kind:9s} #{event.index} "
              f"{event.fraction * 100:5.1f}% {event.message}{detail}")
    print(f"TOTAL: {time.monotonic() - started:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
