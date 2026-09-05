"""Timestamp and subtitle rendering - the part most likely to be subtly wrong."""

from __future__ import annotations

import pytest

from scribedrop.formats import (
    FormatError,
    Segment,
    format_timestamp,
    normalise_segments,
    render,
    segments_to_srt,
    segments_to_txt,
    segments_to_vtt,
)


class TestFormatTimestamp:
    def test_zero(self):
        assert format_timestamp(0) == "00:00:00,000"

    def test_sub_second(self):
        assert format_timestamp(0.001) == "00:00:00,001"
        assert format_timestamp(0.5) == "00:00:00,500"
        assert format_timestamp(0.999) == "00:00:00,999"

    def test_minute_rollover(self):
        assert format_timestamp(59.999) == "00:00:59,999"
        assert format_timestamp(60) == "00:01:00,000"

    def test_hour_rollover(self):
        assert format_timestamp(3599.999) == "00:59:59,999"
        assert format_timestamp(3600) == "01:00:00,000"
        assert format_timestamp(3661.5) == "01:01:01,500"

    def test_multi_hour(self):
        assert format_timestamp(36000) == "10:00:00,000"

    def test_rounding_never_yields_1000_ms(self):
        # 1.9999s rounds to 2000ms, which must roll into the seconds field.
        assert format_timestamp(1.9999) == "00:00:02,000"
        assert format_timestamp(59.9999) == "00:01:00,000"

    def test_negative_clamps_to_zero(self):
        assert format_timestamp(-5.0) == "00:00:00,000"

    def test_beyond_ceiling_clamps(self):
        assert format_timestamp(10_000_000) == "99:59:59,999"

    def test_vtt_separator(self):
        assert format_timestamp(3661.5, ".") == "01:01:01.500"

    def test_bad_separator_rejected(self):
        with pytest.raises(FormatError):
            format_timestamp(1.0, ";")

    def test_nan_and_inf_rejected(self):
        with pytest.raises(FormatError):
            format_timestamp(float("nan"))
        with pytest.raises(FormatError):
            format_timestamp(float("inf"))


class TestNormalise:
    def test_sorts_out_of_order_segments(self):
        out = normalise_segments(
            [Segment(5, 6, "second"), Segment(1, 2, "first"), Segment(9, 10, "third")]
        )
        assert [seg.text for seg in out] == ["first", "second", "third"]

    def test_drops_empty_and_whitespace_only(self):
        out = normalise_segments([Segment(0, 1, "  "), Segment(1, 2, ""), Segment(2, 3, "kept")])
        assert [seg.text for seg in out] == ["kept"]

    def test_collapses_internal_whitespace(self):
        assert normalise_segments([Segment(0, 1, "  a   b \n c ")])[0].text == "a b c"

    def test_end_before_start_is_clamped(self):
        assert normalise_segments([Segment(5, 2, "x")])[0].end == 5.0

    def test_negative_start_clamped(self):
        assert normalise_segments([Segment(-3, 1, "x")])[0].start == 0.0

    def test_stable_for_identical_starts(self):
        out = normalise_segments([Segment(1, 4, "long"), Segment(1, 2, "short")])
        assert [seg.text for seg in out] == ["short", "long"]


class TestSrt:
    def test_basic_block(self):
        srt = segments_to_srt([Segment(0, 1.5, "Hello there")])
        assert srt == "1\n00:00:00,000 --> 00:00:01,500\nHello there\n"

    def test_indices_are_sequential_after_reorder(self):
        srt = segments_to_srt([Segment(2, 3, "b"), Segment(0, 1, "a")])
        assert srt.startswith("1\n00:00:00,000 --> 00:00:01,000\na\n")
        assert "2\n00:00:02,000 --> 00:00:03,000\nb\n" in srt

    def test_blank_line_between_blocks(self):
        srt = segments_to_srt([Segment(0, 1, "a"), Segment(1, 2, "b")])
        assert "\n\n2\n" in srt

    def test_empty_input(self):
        assert segments_to_srt([]) == ""

    def test_unicode_survives(self):
        assert "שלום" in segments_to_srt([Segment(0, 1, "שלום")])


class TestVtt:
    def test_header_present(self):
        assert segments_to_vtt([]).startswith("WEBVTT")

    def test_uses_dot_separator_and_no_index(self):
        vtt = segments_to_vtt([Segment(61, 62.25, "hi")])
        assert "00:01:01.000 --> 00:01:02.250" in vtt
        assert "\n1\n" not in vtt


class TestTxt:
    def test_one_line_per_segment(self):
        assert segments_to_txt([Segment(0, 1, "a"), Segment(1, 2, "b")]) == "a\nb\n"

    def test_empty_input_is_empty_string(self):
        assert segments_to_txt([]) == ""


class TestRender:
    @pytest.mark.parametrize("fmt", ["srt", "vtt", "txt"])
    def test_known_formats(self, fmt):
        assert isinstance(render([Segment(0, 1, "x")], fmt), str)

    def test_unknown_format_raises(self):
        with pytest.raises(FormatError):
            render([], "ass")
