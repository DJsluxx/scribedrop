"""Output path resolution and media discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from scribedrop.paths import (
    PathError,
    collect_media_files,
    is_media_file,
    resolve_output_path,
)

SOURCE = Path("C:/media/Interview Take 2.mp4")


class TestResolveOutputPath:
    def test_defaults_next_to_source(self):
        assert resolve_output_path(SOURCE, "srt") == Path("C:/media/Interview Take 2.srt")

    def test_respects_output_dir(self):
        out = resolve_output_path(SOURCE, "txt", Path("D:/out"))
        assert out == Path("D:/out/Interview Take 2.txt")

    def test_leading_dot_in_format_is_tolerated(self):
        assert resolve_output_path(SOURCE, ".vtt").suffix == ".vtt"

    def test_format_is_lowercased(self):
        assert resolve_output_path(SOURCE, "SRT").suffix == ".srt"

    def test_dotted_filename_keeps_full_stem(self):
        source = Path("C:/media/ep.01.final.mp3")
        assert resolve_output_path(source, "srt").name == "ep.01.final.srt"

    def test_collision_gets_a_suffix(self):
        taken = {Path("C:/media/Interview Take 2.srt")}
        out = resolve_output_path(SOURCE, "srt", exists=lambda p: p in taken)
        assert out.name == "Interview Take 2 (1).srt"

    def test_second_collision_increments(self):
        taken = {
            Path("C:/media/Interview Take 2.srt"),
            Path("C:/media/Interview Take 2 (1).srt"),
        }
        out = resolve_output_path(SOURCE, "srt", exists=lambda p: p in taken)
        assert out.name == "Interview Take 2 (2).srt"

    def test_exhausted_collisions_raise(self):
        with pytest.raises(PathError):
            resolve_output_path(SOURCE, "srt", exists=lambda _p: True)

    def test_invalid_format_raises(self):
        with pytest.raises(PathError):
            resolve_output_path(SOURCE, "")
        with pytest.raises(PathError):
            resolve_output_path(SOURCE, "sr t")


class TestIsMediaFile:
    @pytest.mark.parametrize("name", ["a.mp3", "a.WAV", "a.mkv", "a.Opus", "a.m4a"])
    def test_accepts_media(self, name):
        assert is_media_file(Path(name))

    @pytest.mark.parametrize("name", ["a.txt", "a.srt", "a.exe", "a"])
    def test_rejects_non_media(self, name):
        assert not is_media_file(Path(name))


class TestCollectMediaFiles:
    def test_walks_a_folder_and_skips_non_media(self, tmp_path):
        (tmp_path / "one.mp3").write_bytes(b"x")
        (tmp_path / "notes.txt").write_bytes(b"x")
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / "two.wav").write_bytes(b"x")
        found = collect_media_files([tmp_path])
        assert [p.name for p in found] == ["one.mp3", "two.wav"]

    def test_deduplicates_file_and_its_folder(self, tmp_path):
        media = tmp_path / "one.mp3"
        media.write_bytes(b"x")
        assert len(collect_media_files([media, tmp_path])) == 1

    def test_missing_path_is_ignored(self, tmp_path):
        assert collect_media_files([tmp_path / "nope.mp3"]) == []
