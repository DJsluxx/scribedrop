"""Queue bookkeeping: what the status line tells the user at the end.

A user who presses Cancel on purpose must not be told something failed.
That is the whole reason `_summary` counts three outcomes instead of two.
"""

from __future__ import annotations

from pathlib import Path

from scribedrop.runner import Event, QueueRunner
from scribedrop.settings import Settings


def _runner(files=("a.mp3",)) -> QueueRunner:
    return QueueRunner([Path(name) for name in files], Settings())


class TestSummary:
    def test_all_succeeded(self):
        assert _runner()._summary(3, 0, 0) == "Done: 3 transcribed."

    def test_some_failed(self):
        assert _runner()._summary(2, 1, 0) == "Done: 2 transcribed, 1 failed."

    def test_a_cancelled_file_is_not_counted_as_a_failure(self):
        runner = _runner()
        runner.cancel()
        summary = runner._summary(1, 0, 1)
        assert summary == "Cancelled. 1 transcribed, 1 cancelled."
        assert "failed" not in summary

    def test_cancelling_before_anything_finished(self):
        runner = _runner()
        runner.cancel()
        assert runner._summary(0, 0, 1) == "Cancelled. 0 transcribed, 1 cancelled."

    def test_a_cancelled_run_still_reports_real_failures(self):
        runner = _runner()
        runner.cancel()
        assert runner._summary(1, 2, 1) == "Cancelled. 1 transcribed, 1 cancelled, 2 failed."


class TestQueueRunnerBasics:
    def test_total_is_the_file_count(self):
        assert _runner(("a.mp3", "b.wav", "c.mkv")).total == 3

    def test_is_not_running_before_start(self):
        assert _runner().is_running() is False

    def test_cancel_is_idempotent(self):
        runner = _runner()
        runner.cancel()
        runner.cancel()
        assert runner._cancel.is_set() is True

    def test_emitted_events_are_immutable(self):
        """The GUI thread reads these; a mutable event would be a data race."""
        runner = _runner()
        runner._emit("status", message="hello")
        event = runner.events.get_nowait()
        assert isinstance(event, Event)
        assert event.message == "hello"
        try:
            event.message = "changed"  # type: ignore[misc]
        except AttributeError:
            return
        raise AssertionError("Event should be frozen")
