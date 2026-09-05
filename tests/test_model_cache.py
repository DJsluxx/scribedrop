"""The load path that decides whether ScribeDrop touches the network.

The README promises that after the one-time model download the app opens no
connection at all. That promise lives or dies on one keyword argument:
`local_files_only=True`. Without it, huggingface_hub asks huggingface.co
whether the model changed on every single run, forever.

These tests substitute a recording stand-in for `faster_whisper.WhisperModel`
so the decision can be checked without a 485 MB download. The logic under
test is the real `Transcriber._build_model`.
"""

from __future__ import annotations

import sys
import types

import pytest

from scribedrop.engine import DeviceChoice, Transcriber

CPU = DeviceChoice("cpu", "int8")


class _Recorder:
    """Stands in for WhisperModel and records how it was asked to load."""

    def __init__(self, cached: bool) -> None:
        self.cached = cached
        self.calls: list[dict] = []

    def __call__(self, model_key, **kwargs):
        self.calls.append({"model": model_key, **kwargs})
        if kwargs.get("local_files_only") and not self.cached:
            raise ValueError(
                "Cannot find an appropriate cached snapshot folder for the specified "
                "revision on the local disk and outgoing traffic has been disabled."
            )
        return f"model:{model_key}"

    @property
    def offline_attempts(self) -> int:
        return sum(1 for call in self.calls if call.get("local_files_only"))

    @property
    def online_attempts(self) -> int:
        return sum(1 for call in self.calls if not call.get("local_files_only"))


@pytest.fixture()
def whisper(monkeypatch):
    """Install a recording WhisperModel; yields a factory taking `cached`."""

    def install(cached: bool) -> _Recorder:
        recorder = _Recorder(cached)
        module = types.ModuleType("faster_whisper")
        module.WhisperModel = recorder  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "faster_whisper", module)
        return recorder

    return install


def _messages() -> tuple[list[str], object]:
    seen: list[str] = []

    def on_progress(_fraction, message):
        seen.append(message)

    return seen, on_progress


class TestCachedModel:
    def test_a_cached_model_is_opened_offline_and_never_online(self, whisper, tmp_path):
        recorder = whisper(cached=True)
        _, on_progress = _messages()
        Transcriber(tmp_path)._build_model("small", CPU, on_progress)
        assert recorder.offline_attempts == 1
        assert recorder.online_attempts == 0

    def test_no_download_message_is_shown_for_a_cached_model(self, whisper, tmp_path):
        recorder = whisper(cached=True)
        seen, on_progress = _messages()
        Transcriber(tmp_path)._build_model("small", CPU, on_progress)
        assert recorder.cached
        assert not any("Downloading" in message for message in seen)

    def test_the_download_root_is_passed_through(self, whisper, tmp_path):
        recorder = whisper(cached=True)
        _, on_progress = _messages()
        Transcriber(tmp_path)._build_model("small", CPU, on_progress)
        assert recorder.calls[0]["download_root"] == str(tmp_path)

    def test_device_and_precision_come_from_the_ladder_rung(self, whisper, tmp_path):
        recorder = whisper(cached=True)
        _, on_progress = _messages()
        rung = DeviceChoice("cuda", "float16")
        Transcriber(tmp_path)._build_model("large-v3", rung, on_progress)
        assert recorder.calls[0]["device"] == "cuda"
        assert recorder.calls[0]["compute_type"] == "float16"


class TestUncachedModel:
    def test_an_uncached_model_falls_back_to_a_normal_download(self, whisper, tmp_path):
        recorder = whisper(cached=False)
        _, on_progress = _messages()
        result = Transcriber(tmp_path)._build_model("small", CPU, on_progress)
        assert recorder.offline_attempts == 1
        assert recorder.online_attempts == 1
        assert result == "model:small"

    def test_the_user_is_told_a_download_is_happening(self, whisper, tmp_path):
        whisper(cached=False)
        seen, on_progress = _messages()
        Transcriber(tmp_path)._build_model("small", CPU, on_progress)
        assert any("Downloading" in message for message in seen)

    def test_the_download_attempt_does_not_pass_local_files_only(self, whisper, tmp_path):
        recorder = whisper(cached=False)
        _, on_progress = _messages()
        Transcriber(tmp_path)._build_model("small", CPU, on_progress)
        assert recorder.calls[-1].get("local_files_only") is None


class TestDeviceFailuresAreNotMistakenForCacheMisses:
    def test_a_cuda_failure_is_re_raised_and_never_retried_online(self, monkeypatch, tmp_path):
        """Otherwise a broken GPU would trigger a pointless re-download."""
        calls: list[dict] = []

        def explode(model_key, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("Library cudnn64_9.dll is not found or cannot be loaded")

        module = types.ModuleType("faster_whisper")
        module.WhisperModel = explode  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "faster_whisper", module)

        _, on_progress = _messages()
        with pytest.raises(RuntimeError, match="cudnn"):
            Transcriber(tmp_path)._build_model("small", DeviceChoice("cuda", "float16"), on_progress)
        assert len(calls) == 1
