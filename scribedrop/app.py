"""ScribeDrop main window.

Tk owns the main thread and does nothing slow. All transcription happens
on a QueueRunner worker thread; this file only drains its event queue.
"""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from queue import Empty
from tkinter import filedialog, messagebox, ttk

from .catalog import (
    LABEL_TO_LANGUAGE,
    LANGUAGE_LABELS,
    LANGUAGES,
    MODELS,
    OUTPUT_FORMATS,
    model_for,
)
from .engine import gpu_status
from .media import FFMPEG_HINT, find_ffmpeg
from .paths import collect_media_files
from .runner import QueueRunner
from .settings import Settings, load_settings, save_settings

POLL_INTERVAL_MS = 80
WINDOW_TITLE = "ScribeDrop - local transcription"
STATUS_QUEUED = "Queued"
MEDIA_FILTER = "*.mp3 *.wav *.m4a *.flac *.ogg *.opus *.mp4 *.mkv *.mov *.avi *.webm"
DROP_PROMPT = "Drag audio or video files (or a folder) here"
DROP_FALLBACK = "Drag-and-drop is unavailable on this install - use the Add files button below."


def _try_enable_dnd(root: tk.Misc, on_drop) -> bool:
    """Wire up drag-and-drop. Returns False if tkinterdnd2 is unavailable."""
    try:
        from tkinterdnd2 import DND_FILES
    except ImportError:
        return False
    try:
        root.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
        root.dnd_bind("<<Drop>>", on_drop)  # type: ignore[attr-defined]
    except (AttributeError, tk.TclError):
        return False
    return True


def make_root() -> tuple[tk.Tk, bool]:
    """Build the Tk root, preferring the drag-and-drop-capable one."""
    try:
        from tkinterdnd2 import TkinterDnD

        return TkinterDnD.Tk(), True
    except Exception:  # noqa: BLE001 - any failure at all means plain Tk
        return tk.Tk(), False


class ScribeDropApp:
    """The whole UI. Holds no transcription logic of its own."""

    def __init__(self, root: tk.Tk, dnd_capable: bool) -> None:
        self.root = root
        self.settings, warning = load_settings()
        self.files: list[Path] = []
        self.runner: QueueRunner | None = None
        self.root.title(WINDOW_TITLE)
        self.root.geometry("920x760")
        self.root.minsize(800, 660)
        self._build_ui()
        self.dnd_active = dnd_capable and _try_enable_dnd(self.root, self._on_drop)
        self._announce_environment(warning)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------- layout

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        self._build_dropzone(outer)
        self._build_options(outer)
        self._build_queue(outer)
        self._build_footer(outer)

    def _build_dropzone(self, parent: ttk.Frame) -> None:
        zone = ttk.LabelFrame(parent, text="1. Add media", padding=10)
        zone.pack(fill="x")
        self.drop_label = ttk.Label(
            zone, anchor="center", justify="center", padding=14, text=DROP_PROMPT
        )
        self.drop_label.pack(fill="x")
        buttons = ttk.Frame(zone)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Add files...", command=self._add_files).pack(side="left")
        ttk.Button(buttons, text="Add folder...", command=self._add_folder).pack(side="left", padx=6)
        ttk.Button(buttons, text="Remove selected", command=self._remove_selected).pack(side="left")
        ttk.Button(buttons, text="Clear", command=self._clear).pack(side="left", padx=6)

    def _build_options(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="2. Options", padding=10)
        box.pack(fill="x", pady=(10, 0))
        box.columnconfigure(1, weight=1)
        self._build_model_row(box)
        self._build_language_row(box)
        self._build_format_row(box)
        self._build_output_row(box)

    def _build_model_row(self, box: ttk.Frame) -> None:
        ttk.Label(box, text="Model:").grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar(value=model_for(self.settings.model).display)
        combo = ttk.Combobox(
            box,
            textvariable=self.model_var,
            state="readonly",
            values=[m.display for m in MODELS],
            width=30,
        )
        combo.grid(row=0, column=1, sticky="w", padx=(6, 10))
        combo.bind("<<ComboboxSelected>>", self._on_model_changed)
        self.model_note = ttk.Label(box, text=model_for(self.settings.model).note, foreground="#555")
        self.model_note.grid(row=0, column=2, sticky="w")
        ttk.Label(
            box,
            foreground="#555",
            text="The model downloads once on first use, then everything runs offline.",
        ).grid(row=1, column=1, columnspan=2, sticky="w", pady=(2, 8))

    def _build_language_row(self, box: ttk.Frame) -> None:
        ttk.Label(box, text="Language:").grid(row=2, column=0, sticky="w")
        current = LANGUAGE_LABELS.get(self.settings.language, "Auto-detect")
        self.language_var = tk.StringVar(value=current)
        ttk.Combobox(
            box,
            textvariable=self.language_var,
            state="readonly",
            values=[label for _, label in LANGUAGES],
            width=30,
        ).grid(row=2, column=1, sticky="w", padx=(6, 10), pady=(0, 8))

    def _build_format_row(self, box: ttk.Frame) -> None:
        ttk.Label(box, text="Output:").grid(row=3, column=0, sticky="w")
        row = ttk.Frame(box)
        row.grid(row=3, column=1, columnspan=2, sticky="w", padx=(6, 0), pady=(0, 8))
        self.format_vars: dict[str, tk.BooleanVar] = {}
        for key, label in OUTPUT_FORMATS:
            var = tk.BooleanVar(value=key in self.settings.formats)
            self.format_vars[key] = var
            ttk.Checkbutton(row, text=label, variable=var).pack(side="left", padx=(0, 12))

    def _build_output_row(self, box: ttk.Frame) -> None:
        ttk.Label(box, text="Save to:").grid(row=4, column=0, sticky="w")
        row = ttk.Frame(box)
        row.grid(row=4, column=1, columnspan=2, sticky="ew", padx=(6, 0))
        self.output_var = tk.StringVar(value=self.settings.output_dir)
        ttk.Entry(row, textvariable=self.output_var).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Choose...", command=self._choose_output).pack(side="left", padx=6)
        ttk.Button(
            row, text="Next to source", command=lambda: self.output_var.set("")
        ).pack(side="left")

    def _build_queue(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="3. Queue", padding=8)
        box.pack(fill="both", expand=True, pady=(10, 0))
        self.tree = ttk.Treeview(
            box, columns=("file", "status", "progress"), show="headings", selectmode="extended"
        )
        layout = (("file", "File", 420, "w"), ("status", "Status", 270, "w"), ("progress", "%", 55, "e"))
        for name, title, width, anchor in layout:
            self.tree.heading(name, text=title)
            self.tree.column(name, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_footer(self, parent: ttk.Frame) -> None:
        footer = ttk.Frame(parent)
        footer.pack(fill="x", pady=(10, 0))
        self.progress = ttk.Progressbar(footer, mode="determinate", maximum=100.0)
        self.progress.pack(fill="x")
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(footer, textvariable=self.status_var, anchor="w").pack(fill="x", pady=(6, 6))
        buttons = ttk.Frame(footer)
        buttons.pack(fill="x")
        self.start_button = ttk.Button(buttons, text="Transcribe", command=self.start_transcription)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(
            buttons, text="Cancel", command=self._cancel, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=6)
        self.device_var = tk.StringVar(value="")
        ttk.Label(buttons, textvariable=self.device_var, foreground="#333").pack(side="right")

    # ------------------------------------------------------------ environment

    def _announce_environment(self, warning: str | None) -> None:
        usable, device = gpu_status()
        self.device_var.set("GPU (CUDA) ready" if usable else "CPU mode")
        notes = []
        if not self.dnd_active:
            self.drop_label.configure(text=DROP_FALLBACK)
            notes.append("drag-and-drop unavailable")
        if find_ffmpeg() is None:
            notes.append("FFmpeg not found (only needed for unusual containers)")
        if warning:
            notes.append(warning)
        extra = (" | " + " | ".join(notes)) if notes else ""
        self.status_var.set(f"Ready. {device}{extra}")

    # ------------------------------------------------------------------ files

    def _on_drop(self, event) -> None:
        try:
            raw = self.root.tk.splitlist(event.data)
        except tk.TclError:
            raw = [event.data]
        self.add_paths([Path(item) for item in raw])

    def _add_files(self) -> None:
        chosen = filedialog.askopenfilenames(
            title="Choose audio or video files",
            filetypes=[("Media files", MEDIA_FILTER), ("All files", "*.*")],
        )
        self.add_paths([Path(item) for item in chosen])

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose a folder of media")
        if folder:
            self.add_paths([Path(folder)])

    def add_paths(self, entries: list[Path]) -> None:
        """Expand and queue the given files/folders, skipping duplicates."""
        if self._busy():
            return
        found = collect_media_files(entries)
        added = [path for path in found if path not in self.files]
        skipped = len(found) - len(added)
        for path in added:
            self.files.append(path)
            self.tree.insert("", "end", values=(str(path), STATUS_QUEUED, "0"))
        if not found and entries:
            self.status_var.set("Nothing added - no supported audio or video files found there.")
            return
        suffix = f" ({skipped} already queued)" if skipped else ""
        self.status_var.set(f"{len(self.files)} file(s) queued{suffix}.")

    def _remove_selected(self) -> None:
        if self._busy():
            return
        for item in self.tree.selection():
            index = self.tree.index(item)
            self.tree.delete(item)
            del self.files[index]
        self.status_var.set(f"{len(self.files)} file(s) queued.")

    def _clear(self) -> None:
        if self._busy():
            return
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self.progress["value"] = 0
        self.status_var.set("Queue cleared.")

    def _choose_output(self) -> None:
        folder = filedialog.askdirectory(title="Choose an output folder")
        if folder:
            self.output_var.set(folder)

    # --------------------------------------------------------------- settings

    def _on_model_changed(self, _event=None) -> None:
        self.model_note.configure(text=model_for(self._current_model()).note)

    def _current_model(self) -> str:
        display = self.model_var.get()
        for model in MODELS:
            if model.display == display:
                return model.key
        return self.settings.model

    def current_settings(self) -> Settings:
        """Read the widgets back into an immutable Settings value."""
        formats = tuple(key for key, _ in OUTPUT_FORMATS if self.format_vars[key].get())
        return replace(
            self.settings,
            model=self._current_model(),
            language=LABEL_TO_LANGUAGE.get(self.language_var.get(), "auto"),
            formats=formats,
            output_dir=self.output_var.get().strip(),
        )

    # ------------------------------------------------------------------- run

    def _busy(self) -> bool:
        if self.runner is not None and self.runner.is_running():
            self.status_var.set("Busy - cancel the current run first.")
            return True
        return False

    def start_transcription(self) -> None:
        if self._busy():
            return
        if not self.files:
            messagebox.showinfo(WINDOW_TITLE, "Add at least one audio or video file first.")
            return
        settings = self.current_settings()
        if not settings.formats:
            messagebox.showinfo(WINDOW_TITLE, "Choose at least one output format.")
            return
        if not self._output_dir_ok(settings):
            return
        self.settings = settings
        error = save_settings(settings)
        if error:
            self.status_var.set(error)
        self._begin_run(settings)

    def _output_dir_ok(self, settings: Settings) -> bool:
        target = settings.resolved_output_dir()
        if target is None or target.is_dir():
            return True
        messagebox.showerror(WINDOW_TITLE, f"Output folder does not exist:\n{target}")
        return False

    def _begin_run(self, settings: Settings) -> None:
        self.progress["value"] = 0
        for item in self.tree.get_children():
            self.tree.set(item, "status", STATUS_QUEUED)
            self.tree.set(item, "progress", "0")
        self.runner = QueueRunner(self.files, settings)
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status_var.set("Starting...")
        self.runner.start()
        self.root.after(POLL_INTERVAL_MS, self._pump)

    def _cancel(self) -> None:
        if self.runner is not None:
            self.runner.cancel()
            self.status_var.set("Cancelling after the current segment...")

    def _pump(self) -> None:
        runner = self.runner
        if runner is None:
            return
        try:
            while True:
                self._apply(runner.events.get_nowait())
        except Empty:
            pass
        if runner.is_running():
            self.root.after(POLL_INTERVAL_MS, self._pump)

    def _apply(self, event) -> None:
        handler = {
            "start": self._event_start,
            "progress": self._event_progress,
            "done": self._event_done,
            "error": self._event_error,
            "cancelled": self._event_cancelled,
            "finished": self._event_finished,
        }.get(event.kind)
        if handler is not None:
            handler(event)

    def _set_row(self, index: int, status: str, percent: int | None = None) -> None:
        children = self.tree.get_children()
        if not 0 <= index < len(children):
            return
        item = children[index]
        self.tree.set(item, "status", status)
        if percent is not None:
            self.tree.set(item, "progress", str(percent))

    def _event_start(self, event) -> None:
        self._set_row(event.index, "Starting...", 0)
        self.status_var.set(f"Transcribing {event.message}")

    def _event_progress(self, event) -> None:
        self._set_row(event.index, event.message, int(event.fraction * 100))
        if event.message.startswith("Using ") or "unavailable" in event.message:
            self.device_var.set(event.message)
        self._refresh_overall(event.index, event.fraction)

    def _event_done(self, event) -> None:
        names = ", ".join(path.name for path in event.outputs)
        self._set_row(event.index, f"Saved: {names}", 100)
        self._refresh_overall(event.index, 1.0)

    def _event_error(self, event) -> None:
        self._set_row(event.index, f"Failed: {event.message}", 0)

    def _event_cancelled(self, event) -> None:
        self._set_row(event.index, "Cancelled")

    def _event_finished(self, event) -> None:
        self.status_var.set(event.message)
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

    def _refresh_overall(self, index: int, fraction: float) -> None:
        total = max(len(self.files), 1)
        self.progress["value"] = min((index + fraction) / total * 100.0, 100.0)

    def _on_close(self) -> None:
        if self.runner is not None and self.runner.is_running():
            if not messagebox.askokcancel(WINDOW_TITLE, "A transcription is running. Quit anyway?"):
                return
            self.runner.cancel()
        self.root.destroy()


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Any file paths in argv are added to the queue on launch, so you can drop
    files onto ScribeDrop.bat. Pass --autostart to begin transcribing them
    immediately without clicking anything.
    """
    args = list(argv if argv is not None else sys.argv[1:])
    autostart = "--autostart" in args
    paths = [Path(item) for item in args if not item.startswith("--")]
    root, dnd = make_root()
    app = ScribeDropApp(root, dnd)
    if paths:
        app.add_paths(paths)
        if autostart:
            root.after(200, app.start_transcription)
    elif find_ffmpeg() is None:
        app.status_var.set(FFMPEG_HINT)
    root.mainloop()
    return 0
