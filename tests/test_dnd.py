"""Drag-and-drop wiring and the Windows drop-payload format.

Skipped automatically where there is no display or no tkinterdnd2, so the
suite still passes on a headless machine.
"""

from __future__ import annotations

import pytest

tk = pytest.importorskip("tkinter")
pytest.importorskip("tkinterdnd2")


@pytest.fixture(scope="module")
def dnd_root():
    """One root per module: tkinterdnd2 rewrites the Tcl library path on first
    init, so creating a second root in the same process fails."""
    from tkinterdnd2 import TkinterDnD

    try:
        root = TkinterDnD.Tk()
    except tk.TclError as exc:  # no display
        pytest.skip(f"no display available: {exc}")
    root.withdraw()
    yield root
    root.destroy()


def test_drop_target_registers(dnd_root):
    """The real proof that drag-and-drop is live, not the fallback path."""
    from scribedrop.app import _try_enable_dnd

    assert _try_enable_dnd(dnd_root, lambda _event: None) is True


def test_windows_drop_payload_splits_paths_with_spaces(dnd_root):
    """Windows sends brace-wrapped paths when they contain spaces."""
    payload = "{C:/media/Interview Take 2.mp4} C:/media/short.mp3"
    assert list(dnd_root.tk.splitlist(payload)) == [
        "C:/media/Interview Take 2.mp4",
        "C:/media/short.mp3",
    ]


def test_single_path_without_braces(dnd_root):
    assert list(dnd_root.tk.splitlist("C:/media/a.wav")) == ["C:/media/a.wav"]
