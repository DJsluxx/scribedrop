"""Input validation and the FFmpeg escape hatch.

`media.py` is where every hostile file lands: empty files, truncated files,
files that vanished between the drop and the run, files another program has
open. These tests use real files on a real temp filesystem - the point is
that the error a user sees is specific, not "something went wrong".
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scribedrop.media import (
    MIN_USEFUL_BYTES,
    MediaError,
    check_input_file,
    find_ffmpeg,
    probe_duration,
    transcode_to_wav,
)


def _real_file(tmp_path: Path, name: str = "clip.wav", size: int = 4096) -> Path:
    path = tmp_path / name
    path.write_bytes(b"\x00" * size)
    return path


class TestCheckInputFile:
    def test_accepts_an_ordinary_file(self, tmp_path):
        check_input_file(_real_file(tmp_path))  # must not raise

    def test_missing_file_says_so(self, tmp_path):
        with pytest.raises(MediaError, match="no longer exists"):
            check_input_file(tmp_path / "gone.mp3")

    def test_empty_file_is_named_as_empty(self, tmp_path):
        path = tmp_path / "empty.mp3"
        path.write_bytes(b"")
        with pytest.raises(MediaError, match="empty"):
            check_input_file(path)

    def test_tiny_file_is_named_as_too_small(self, tmp_path):
        path = tmp_path / "stub.mp3"
        path.write_bytes(b"\x00" * (MIN_USEFUL_BYTES - 1))
        with pytest.raises(MediaError, match="too small"):
            check_input_file(path)

    def test_a_file_of_exactly_the_threshold_is_accepted(self, tmp_path):
        check_input_file(_real_file(tmp_path, size=MIN_USEFUL_BYTES))

    def test_a_directory_is_not_a_file(self, tmp_path):
        folder = tmp_path / "a folder"
        folder.mkdir()
        with pytest.raises(MediaError):
            check_input_file(folder)

    def test_errors_are_all_mediaerror_not_oserror(self, tmp_path):
        """The runner only catches MediaError; a leaked OSError kills the file."""
        for candidate in (tmp_path / "nope.mp3", tmp_path):
            with pytest.raises(MediaError):
                check_input_file(candidate)


class TestProbeDuration:
    def test_garbage_returns_none_rather_than_raising(self, tmp_path):
        path = tmp_path / "garbage.wav"
        path.write_bytes(b"not audio, not even close" * 100)
        assert probe_duration(path) is None

    def test_missing_file_returns_none(self, tmp_path):
        assert probe_duration(tmp_path / "absent.wav") is None


class TestFindFfmpeg:
    def test_returns_a_path_or_none_never_raises(self):
        found = find_ffmpeg()
        assert found is None or isinstance(found, Path)

    def test_a_found_ffmpeg_actually_exists(self):
        found = find_ffmpeg()
        if found is not None:
            assert found.is_file()


class TestTranscodeToWav:
    def test_a_missing_ffmpeg_binary_is_a_mediaerror(self, tmp_path):
        with pytest.raises(MediaError, match="Could not run FFmpeg"):
            transcode_to_wav(
                _real_file(tmp_path), tmp_path / "out.wav", tmp_path / "no-ffmpeg-here.exe"
            )

    def test_a_failing_ffmpeg_reports_its_own_last_line(self, tmp_path, monkeypatch):
        def fake_run(_command, **_kwargs):
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="junk\nInvalid data found\n"
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(MediaError, match="Invalid data found"):
            transcode_to_wav(_real_file(tmp_path), tmp_path / "out.wav", Path("ffmpeg"))

    def test_a_silent_success_producing_no_audio_is_still_an_error(self, tmp_path, monkeypatch):
        """FFmpeg exits 0 on a video with no audio track and writes nothing useful."""

        def fake_run(_command, **_kwargs):
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(MediaError, match="no audio"):
            transcode_to_wav(_real_file(tmp_path), tmp_path / "out.wav", Path("ffmpeg"))

    def test_a_timeout_is_a_mediaerror(self, tmp_path, monkeypatch):
        def fake_run(_command, **_kwargs):
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1)

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(MediaError, match="too long"):
            transcode_to_wav(_real_file(tmp_path), tmp_path / "out.wav", Path("ffmpeg"))

    def test_the_command_never_uses_a_shell(self, tmp_path, monkeypatch):
        """shell=True on a user-supplied filename would be a command injection."""
        seen = {}

        def fake_run(command, **kwargs):
            seen["command"] = command
            seen["kwargs"] = kwargs
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        destination = tmp_path / "out.wav"
        destination.write_bytes(b"\x00" * 4096)
        transcode_to_wav(_real_file(tmp_path, "in & out.mp3"), destination, Path("ffmpeg"))
        assert seen["kwargs"].get("shell") is not True
        assert isinstance(seen["command"], list)
        assert "in & out.mp3" in seen["command"][seen["command"].index("-i") + 1]

    def test_output_is_16khz_mono_pcm(self, tmp_path, monkeypatch):
        """Whisper wants 16 kHz mono; getting this wrong degrades every transcript."""
        seen = {}

        def fake_run(command, **_kwargs):
            seen["command"] = command
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        destination = tmp_path / "out.wav"
        destination.write_bytes(b"\x00" * 4096)
        transcode_to_wav(_real_file(tmp_path), destination, Path("ffmpeg"))
        command = seen["command"]
        assert command[command.index("-ar") + 1] == "16000"
        assert command[command.index("-ac") + 1] == "1"
        assert command[command.index("-c:a") + 1] == "pcm_s16le"
        assert "-vn" in command
