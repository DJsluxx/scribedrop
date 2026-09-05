"""User settings: an immutable dataclass plus a tolerant JSON round-trip.

A corrupt or hand-edited settings file must never stop the app from
starting, so every load path falls back to defaults with a reason.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

from .catalog import DEFAULT_MODEL, LANGUAGE_LABELS, MODELS_BY_KEY, OUTPUT_FORMATS

VALID_FORMATS = tuple(key for key, _ in OUTPUT_FORMATS)
VALID_DEVICES = ("auto", "cuda", "cpu")
SETTINGS_FILENAME = "settings.json"


def app_data_dir() -> Path:
    """Per-user config/data folder. Honours LOCALAPPDATA, works off Windows too."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if not base:
        base = str(Path.home() / ".local" / "share")
    return Path(base) / "ScribeDrop"


def default_models_dir() -> Path:
    return app_data_dir() / "models"


def settings_path() -> Path:
    return app_data_dir() / SETTINGS_FILENAME


@dataclass(frozen=True)
class Settings:
    model: str = DEFAULT_MODEL
    language: str = "auto"
    formats: tuple[str, ...] = ("txt", "srt")
    output_dir: str = ""  # empty means "next to the source file"
    device: str = "auto"
    models_dir: str = ""  # empty means default_models_dir()

    def with_format(self, fmt: str, enabled: bool) -> "Settings":
        """Return a copy with `fmt` toggled. Never mutates."""
        current = [f for f in VALID_FORMATS if f in self.formats]
        if enabled and fmt not in current:
            current.append(fmt)
        elif not enabled and fmt in current:
            current.remove(fmt)
        ordered = tuple(f for f in VALID_FORMATS if f in current)
        return replace(self, formats=ordered or ("txt",))

    def resolved_models_dir(self) -> Path:
        return Path(self.models_dir) if self.models_dir else default_models_dir()

    def resolved_output_dir(self) -> Path | None:
        return Path(self.output_dir) if self.output_dir else None

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "language": self.language,
            "formats": list(self.formats),
            "output_dir": self.output_dir,
            "device": self.device,
            "models_dir": self.models_dir,
        }


def _clean_formats(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, (list, tuple)):
        return Settings.formats
    chosen = tuple(f for f in VALID_FORMATS if f in raw)
    return chosen or ("txt",)


def _clean_str(raw: object, allowed: dict | tuple, fallback: str) -> str:
    return raw if isinstance(raw, str) and raw in allowed else fallback


def _clean_dir(raw: object) -> str:
    return raw.strip() if isinstance(raw, str) else ""


def settings_from_dict(data: object) -> Settings:
    """Build Settings from untrusted JSON. Unknown values fall back silently."""
    if not isinstance(data, dict):
        return Settings()
    return Settings(
        model=_clean_str(data.get("model"), MODELS_BY_KEY, DEFAULT_MODEL),
        language=_clean_str(data.get("language"), LANGUAGE_LABELS, "auto"),
        formats=_clean_formats(data.get("formats")),
        output_dir=_clean_dir(data.get("output_dir")),
        device=_clean_str(data.get("device"), VALID_DEVICES, "auto"),
        models_dir=_clean_dir(data.get("models_dir")),
    )


def load_settings(path: Path | None = None) -> tuple[Settings, str | None]:
    """Read settings. Returns (settings, warning). Warning is None on success."""
    target = path or settings_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Settings(), None
    except OSError as exc:
        return Settings(), f"Could not read settings ({exc.strerror}); using defaults."
    try:
        return settings_from_dict(json.loads(raw)), None
    except json.JSONDecodeError as exc:
        return Settings(), f"Settings file is not valid JSON (line {exc.lineno}); using defaults."


def save_settings(settings: Settings, path: Path | None = None) -> str | None:
    """Persist settings. Returns an error message, or None on success."""
    target = path or settings_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(settings.to_dict(), indent=2, ensure_ascii=False)
        target.write_text(payload, encoding="utf-8")
    except OSError as exc:
        return f"Could not save settings to {target}: {exc.strerror}"
    return None
