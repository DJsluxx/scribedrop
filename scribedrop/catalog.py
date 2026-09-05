"""Static catalogue of models and languages shown in the UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelChoice:
    key: str
    label: str
    download: str
    note: str

    @property
    def display(self) -> str:
        return f"{self.label}  -  {self.download}"


# Download sizes are the published CTranslate2 conversion sizes on Hugging
# Face (Systran/faster-whisper-*). They are what the user actually downloads.
MODELS: tuple[ModelChoice, ...] = (
    ModelChoice("tiny", "tiny", "~75 MB", "Fastest. Rough drafts and quick tests."),
    ModelChoice("base", "base", "~145 MB", "Still fast, noticeably better than tiny."),
    ModelChoice("small", "small", "~485 MB", "Default. Good balance of speed and quality."),
    ModelChoice("medium", "medium", "~1.5 GB", "Slower, better with accents and noise."),
    ModelChoice("large-v3", "large-v3", "~3.1 GB", "Best quality. Needs a decent GPU."),
)

DEFAULT_MODEL = "small"

MODELS_BY_KEY = {model.key: model for model in MODELS}


def model_for(key: str) -> ModelChoice:
    """Look up a model, falling back to the default rather than crashing."""
    return MODELS_BY_KEY.get(key, MODELS_BY_KEY[DEFAULT_MODEL])


# (code, human label). "auto" means let Whisper detect from the first 30s.
LANGUAGES: tuple[tuple[str, str], ...] = (
    ("auto", "Auto-detect"),
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("ru", "Russian"),
    ("uk", "Ukrainian"),
    ("tr", "Turkish"),
    ("ar", "Arabic"),
    ("he", "Hebrew"),
    ("hi", "Hindi"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("sv", "Swedish"),
    ("no", "Norwegian"),
    ("da", "Danish"),
    ("fi", "Finnish"),
    ("cs", "Czech"),
    ("el", "Greek"),
    ("ro", "Romanian"),
    ("hu", "Hungarian"),
    ("id", "Indonesian"),
    ("vi", "Vietnamese"),
    ("th", "Thai"),
)

LANGUAGE_LABELS = {code: label for code, label in LANGUAGES}
LABEL_TO_LANGUAGE = {label: code for code, label in LANGUAGES}

OUTPUT_FORMATS: tuple[tuple[str, str], ...] = (
    ("txt", "Plain text (.txt)"),
    ("srt", "Subtitles (.srt)"),
    ("vtt", "Web subtitles (.vtt)"),
)
