# ScribeDrop

**Drag audio or video onto a window, get transcripts and subtitles back — computed entirely on your own PC. No upload, no account, no subscription, no command line.**

![ScribeDrop after transcribing two files on an RTX 4070 Ti](docs/screenshot.png)

---

## Why this exists

Mac users have MacWhisper: one window, drag a file, get a subtitle file.

Windows users get handed a command line. The best speech-to-text engine available —
[`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) — is free, open source and downloaded millions
of times a month, but using it on Windows has meant a Python environment, a CUDA library hunt, and a
`--model large-v3 --output_format srt` incantation. So people either pay for a per-minute cloud service or
pay for a Windows clone of MacWhisper.

ScribeDrop is the missing front end. Same engine everyone already uses, wrapped in a window.

## What it does

- **Drag and drop** files or whole folders onto the window. (Or use *Add files…*, or drop files onto the launcher.)
- **A queue** with per-file progress, an overall progress bar, and a Cancel button that actually works mid-file.
- **Model picker** — tiny / base / small / medium / large-v3, with download sizes shown. Defaults to `small`
  so your first result arrives in about a minute instead of after a 3 GB download.
- **Language** auto-detect, or pick one of 28 explicitly.
- **Outputs**: `.txt`, `.srt`, `.vtt` — any combination. Written next to the source file, or into a folder you choose.
- **GPU when you have one, CPU when you don't** — and the status line always tells you which, e.g.
  `Using GPU (CUDA) / float16` or `Using CPU / int8`. It never quietly runs 20x slower without telling you.
- Existing files are never overwritten; a second run produces `interview (1).srt`.

## Your audio never leaves your machine

This is the whole point, so it is worth being precise about it.

ScribeDrop makes **exactly one** network request in its entire lifetime: downloading the Whisper model you
picked, from Hugging Face, the first time you use that model. After that you can disconnect from the
internet entirely and it keeps working.

There is no telemetry, no analytics, no crash reporting, no licence check, no account, and no server of ours
anywhere. There is nothing to opt out of. The code is short enough to read and check that claim yourself —
start at [`scribedrop/engine.py`](scribedrop/engine.py).

## How it compares

| | ScribeDrop | [MacWhisper](https://goodsnooze.gumroad.com/l/macwhisper) | [Whisperstream](https://whisperstream.app/) | [FluidVox](https://fluidvox.com/) |
|---|---|---|---|---|
| Price | **Free, MIT** | EUR 59 (Pro) | $29 | $39 |
| Platform | Windows | macOS only | Windows | Windows |
| Runs locally | Yes | Yes | Yes | Yes |
| Source available | **Yes** | No | No | No |
| Engine | faster-whisper | Whisper | Whisper | Whisper |

Prices as advertised by each vendor at the time of writing; check their sites for current pricing. We have
**not** benchmarked ScribeDrop against any of them for speed or accuracy, and make no claim on either.
The honest claim is narrower: this is the free, open, Windows-native option in a row where the other
Windows entries cost money and ship no source.

## Install

### Option A — Standalone (no Python needed, CPU only)

1. Download `ScribeDrop-0.1.0-win64-cpu.zip` from [Releases](../../releases).
2. Unzip it anywhere.
3. Run `ScribeDrop.exe`.

Simplest path, works on any Windows 10/11 x64 machine. It transcribes on the CPU — fine for short files,
slower for long ones. Use Option B if you have an NVIDIA card.

### Option B — From source (uses your NVIDIA GPU)

Requires [Python 3.10+](https://www.python.org/downloads/) with the *Add python.exe to PATH* box ticked.

1. Download `ScribeDrop-0.1.0-source.zip` from [Releases](../../releases), or `git clone` this repo.
2. Double-click **`setup.bat`**. It creates a private `.venv`, installs the requirements, detects whether you
   have an NVIDIA GPU, and if so installs the CUDA libraries automatically (~1.2 GB, once).
3. Double-click **`ScribeDrop.bat`**.

That is the whole install. Nothing is written outside the folder except settings and the downloaded model,
which live in `%LOCALAPPDATA%\ScribeDrop`.

## System requirements

|  | Minimum | For the GPU path |
|---|---|---|
| OS | Windows 10 / 11, 64-bit | same |
| RAM | 4 GB (`small` model) | 8 GB |
| Disk | ~1 GB for the app + model | ~2.5 GB (CUDA libraries) |
| GPU | none — CPU works | NVIDIA, driver 525+, 4 GB VRAM for `small`, 8 GB+ for `large-v3` |
| Python | not needed (Option A) | 3.10+ (Option B) |

**FFmpeg is optional.** ScribeDrop decodes audio through PyAV, which carries its own FFmpeg libraries, so
most files just work. FFmpeg is only used as a fallback for unusual containers; if it is missing the app
says so and tells you to run `winget install Gyan.FFmpeg`. We deliberately do **not** bundle `ffmpeg.exe`.

## Supported input

**Audio:** mp3, wav, m4a, aac, flac, ogg, oga, opus, wma, aiff
**Video:** mp4, mkv, mov, avi, webm, m4v, wmv, flv, mpg, mpeg, ts (the audio track is used)

## Command line (optional)

The GUI is the product, but the launcher accepts arguments, so you can drop files straight onto
`ScribeDrop.bat` or wire it into a Send To shortcut:

```
ScribeDrop.bat "C:\clips\interview.mp4"              # queue it, wait for you to press Transcribe
ScribeDrop.bat "C:\clips\interview.mp4" --autostart  # queue it and start immediately
```

## Development

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest        REM 98 tests
.venv\Scripts\python -m scribedrop    REM run the app
build_exe.bat                         REM build the standalone bundle
```

Layout: `formats.py` (subtitle rendering), `paths.py` (where output goes), `settings.py`, `catalog.py`
(models/languages), `media.py` (file checks, FFmpeg), `cuda_paths.py` (CUDA DLL discovery),
`engine.py` (faster-whisper), `writer.py`, `runner.py` (worker thread), `app.py` (Tk UI).
The first five are pure and carry the test suite; the GUI holds no transcription logic.

## Known limits in v0.1.0

- No live/microphone recording — files only.
- No speaker diarisation ("who said what").
- No subtitle line-length or characters-per-second shaping; segments come out as Whisper produces them.
- No editor for fixing a transcript in-app.
- The standalone bundle is CPU-only by design (see `build_exe.bat` for why).

## AI-use disclosure

This codebase was written with AI assistance. It was then run, tested and verified on real hardware —
the screenshot above is a real run, the test suite is real and passing, and the subtitle files it produced
are byte-for-byte what the app writes. Bugs are still ours. Please report them.

## Licence and credits

ScribeDrop is MIT licensed — see [LICENSE](LICENSE).

It is a front end. The hard part is other people's work:
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT) by SYSTRAN,
[CTranslate2](https://github.com/OpenNMT/CTranslate2) (MIT),
[OpenAI Whisper](https://github.com/openai/whisper) (MIT), and the
[Systran faster-whisper model conversions](https://huggingface.co/Systran) (MIT) on Hugging Face.
Model weights are downloaded from Hugging Face and are subject to their own licences.
