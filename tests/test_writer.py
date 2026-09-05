"""Writing transcripts to disk - the last step before a user sees a result."""

from __future__ import annotations

import pytest

from scribedrop.formats import Segment
from scribedrop.writer import WriteError, write_outputs

SEGMENTS = [Segment(0, 1.5, "Hello there"), Segment(1.5, 3.0, "General Kenobi")]


def _make_source(tmp_path):
    source = tmp_path / "clip.mp3"
    source.write_bytes(b"\x00" * 2048)
    return source


class TestWriteOutputs:
    def test_writes_every_requested_format(self, tmp_path):
        source = _make_source(tmp_path)
        written = write_outputs(SEGMENTS, source, ("txt", "srt", "vtt"))
        assert sorted(p.suffix for p in written) == [".srt", ".txt", ".vtt"]
        assert all(p.is_file() for p in written)

    def test_srt_content_has_timestamps(self, tmp_path):
        source = _make_source(tmp_path)
        (written,) = write_outputs(SEGMENTS, source, ("srt",))
        text = written.read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:01,500" in text
        assert "Hello there" in text

    def test_writes_beside_source_by_default(self, tmp_path):
        source = _make_source(tmp_path)
        (written,) = write_outputs(SEGMENTS, source, ("txt",))
        assert written.parent == source.parent

    def test_output_dir_is_honoured_and_created(self, tmp_path):
        source = _make_source(tmp_path)
        target = tmp_path / "elsewhere"
        (written,) = write_outputs(SEGMENTS, source, ("txt",), target)
        assert written.parent == target

    def test_existing_file_is_not_overwritten(self, tmp_path):
        source = _make_source(tmp_path)
        clash = tmp_path / "clip.txt"
        clash.write_text("keep me", encoding="utf-8")
        (written,) = write_outputs(SEGMENTS, source, ("txt",))
        assert written.name == "clip (1).txt"
        assert clash.read_text(encoding="utf-8") == "keep me"

    def test_no_formats_raises(self, tmp_path):
        with pytest.raises(WriteError):
            write_outputs(SEGMENTS, _make_source(tmp_path), ())

    def test_unicode_is_written_as_utf8(self, tmp_path):
        source = _make_source(tmp_path)
        (written,) = write_outputs([Segment(0, 1, "שלום עולם")], source, ("txt",))
        assert written.read_text(encoding="utf-8").strip() == "שלום עולם"
