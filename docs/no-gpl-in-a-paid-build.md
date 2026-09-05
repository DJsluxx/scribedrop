# No GPL binary in a paid build — the plan, recorded before it is needed

**Status: recorded, not implemented.** Nothing here changes the free v0.1.0 release, which ships
GPL x264/x265 legitimately and with full corresponding source attached. This note exists so the
work is not rediscovered from scratch the day a paid tier is proposed.

## The rule

**No paid ScribeDrop artifact may contain a GPL-licensed binary.**

The free bundle can, and does, and that is fine: our own source is MIT and public, so anyone who
demands the source of the combined work gets pointed at a repository that already exists. A paid
closed-source build shipping the same DLLs inverts that. The source a recipient could demand
would be the thing we are selling. That is not a takedown risk, it is a business-model risk, and
it is cheaper to avoid than to argue about.

Free tier and paid tier must therefore be built from **different bundle specs**, not the same
spec with a licence key bolted on.

## Where the GPL code comes from

Not from us. `pip install av` pulls a PyAV wheel whose vendored FFmpeg is hard-linked against
libx264 and libx265. Details, measurements and the pinned sources are in
[`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md) §3.

Deleting the two DLLs from the bundle does not work — `import av` fails outright and takes all
audio decoding with it.

## The fix: drop PyAV from the bundle

Transcription needs 16 kHz mono float32 PCM. It does not need a video codec library.

- `faster_whisper/transcribe.py` — `transcribe()` accepts `Union[str, BinaryIO, np.ndarray]`
  and takes a numpy array directly. No PyAV needed on that path.
- Decode with **`soundfile`** (libsndfile, LGPL-2.1) or `miniaudio`.
- Keep the **existing arm's-length `ffmpeg.exe` fallback** for exotic containers. That path is
  already built, and shelling out to a program the user installed themselves is not
  redistribution.
- The single obstacle is the module-level `import av` at `faster_whisper/audio.py:15`. It needs a
  stub module or a vendored replacement `audio.py`.

Side benefit, independent of licensing: this removes roughly **50 MB from a 95.8 MB download**
(libx265 alone is 12.7 MB).

## Options considered and rejected

| Option | Verdict |
|---|---|
| Drop PyAV, decode via `soundfile` + `ffmpeg.exe` fallback | **Chosen.** Cheapest, and it shrinks the download. |
| Build our own LGPL-only FFmpeg for PyAV (no `--enable-gpl`, no libx264/libx265) | Legitimate, but LGPL brings its own relink and notice duties, and it means owning an FFmpeg build. |
| Ship GPL DLLs beside closed-source paid code | No. |

## Acceptance test for whichever path is taken

A paid bundle is only acceptable when a scan of the packaged tree finds **zero** files matching
`libx264*`, `libx265*`, and the shipped `avcodec` reports a configuration containing neither
`--enable-libx264` nor `--enable-libx265`. Wire that into the build script as a hard failure, the
same way `build_exe.bat` already fails the build if an NVIDIA CUDA DLL survives.
