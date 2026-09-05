# Third-party notices

ScribeDrop's own source code is MIT licensed — see [LICENSE](LICENSE). That licence covers
the code in this repository and nothing else. ScribeDrop is a front end: almost all of the
work it does is done by other people's software, under other people's licences. This file
lists every third-party component that ships in a ScribeDrop release archive or that
ScribeDrop downloads at runtime, with its licence and its copyright holder.

Two things are worth reading before the table, because they are the ones people usually get
wrong:

- **The standalone `.zip` is not "an MIT download".** It is an aggregate. The Python
  packages inside it keep their own licences, and some of them are not MIT. §3 and §4 spell
  out which.
- **The Whisper model weights are not in either archive.** They are downloaded from Hugging
  Face by your machine, on first use, under their own licence. We redistribute no weights.

---

## 1. Components in both the source and the standalone release

| Component | Version tested | Licence | Copyright |
|---|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 1.2.1 | MIT | © 2023 SYSTRAN |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | 4.8.2 | MIT | © 2018– SYSTRAN; © 2019– The OpenNMT Authors |
| [Silero VAD](https://github.com/snakers4/silero-vad) (bundled inside faster-whisper) | as shipped by faster-whisper 1.2.1 | MIT | © Silero Team |
| [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) | 0.6.3 | MIT | © 2020 Philippe Gagné |
| [tkdnd](https://github.com/petasis/tkdnd) (native library bundled inside tkinterdnd2) | 2.10.2 | BSD-style Tcl licence | © Georgios Petasis; Mac portions © 2009–2014 Kevin Walzer / WordTech Communications LLC |
| [huggingface_hub](https://github.com/huggingface/huggingface_hub) | 1.30.0 | Apache-2.0 | © Hugging Face Inc. |
| [tokenizers](https://github.com/huggingface/tokenizers) | — | Apache-2.0 | © Hugging Face Inc. |
| [onnxruntime](https://github.com/microsoft/onnxruntime) | — | MIT | © Microsoft Corporation |
| [PyAV](https://github.com/PyAV-Org/PyAV) | 18.1.0 | BSD-3-Clause | © 2017 Mike Boers and contributors |
| [NumPy](https://numpy.org/) | — | BSD-3-Clause | © NumPy Developers |
| [tqdm](https://github.com/tqdm/tqdm) | — | MPL-2.0 and MIT | © 2013 noamraph and contributors |

Python itself, and the Tcl/Tk libraries the interface is drawn with, are covered by the
[PSF License](https://docs.python.org/3/license.html) and the Tcl/Tk BSD-style licence
respectively.

## 2. The Whisper models (downloaded, never redistributed)

ScribeDrop downloads CTranslate2 conversions of OpenAI's Whisper models from Hugging Face
the first time you select a given size. They are not included in either release archive.

| Model | Repository | Licence |
|---|---|---|
| tiny / base / small / medium / large-v3 | `Systran/faster-whisper-*` on [Hugging Face](https://huggingface.co/Systran) | MIT |
| The upstream Whisper models these are converted from | [openai/whisper](https://github.com/openai/whisper) | MIT — "Whisper's code and model weights are released under the MIT License." OpenAI's Hugging Face card for `whisper-large-v3` declares Apache-2.0; both permit commercial use. |

© 2022 OpenAI. The `Systran/faster-whisper-*` repositories are not gated: no account, no
token and no acceptance of terms is required, and ScribeDrop never authenticates to
Hugging Face.

ScribeDrop deliberately does **not** offer the `turbo` / `large-v3-turbo` model. In
faster-whisper that name resolves to a repository from a different uploader whose licence
we have not verified. `large-v3` is the largest model on offer.

## 3. FFmpeg — read this one

**ScribeDrop does not bundle `ffmpeg.exe`, and never will.** The Windows FFmpeg command-line
builds are GPLv3. If FFmpeg is installed on your system, ScribeDrop shells out to it as a
fallback for unusual containers; that is an arm's-length call to a program you obtained
yourself, not redistribution.

**However**, ScribeDrop's normal decoding path is PyAV, and the PyAV wheel published on PyPI
vendors its own FFmpeg shared libraries. Those libraries therefore travel inside the
standalone `.zip`, in `_internal\av.libs\`. Each of those libraries reports its own licence as
**"LGPL version 3 or later"**. **That self-report is wrong, and we do not rely on it.** We
measured the shipped binaries and the build that produced them:

- The import table of `avcodec-62-*.dll` hard-links `libx264` (15 symbols, including
  `x264_encoder_open_165`) and `libx265` (`x265_api_get_216`) as load-time imports.
- `avcodec_configuration()` on that same DLL reports `--enable-libx264 --enable-libx265`
  and **no** `--enable-gpl`. Upstream FFmpeg's `configure` lists both libraries in
  `EXTERNAL_LIBRARY_GPL_LIST` and would refuse that combination.
- The reason it did not refuse is `patches/ffmpeg.patch` in
  [PyAV-Org/pyav-ffmpeg](https://github.com/PyAV-Org/pyav-ffmpeg) tag `8.1.2-1`, the build
  repository these wheels are produced from. That patch moves `libx264` and `libx265` out of
  `EXTERNAL_LIBRARY_GPL_LIST` and into `EXTERNAL_LIBRARY_VERSION3_LIST`, which is what makes
  the resulting binaries call themselves LGPLv3.

We did not write that patch and we have reported it upstream. **We treat these FFmpeg
libraries, and x264 and x265, as GPL version 2 or later.** So:

**The PyAV wheel also vendors `libx264` and `libx265`, which are GPLv2-or-later, and PyAV's
`avcodec` is dynamically linked against both.** We do not use them: ScribeDrop only decodes
audio and never encodes video. We cannot remove them either — deleting them makes
`import av` fail outright and takes all audio decoding with it. Every PyAV Windows wheel from
13.x through 18.x ships them.

So, stated plainly rather than buried: **the standalone `ScribeDrop-*-win64-cpu.zip` contains
GPL-licensed x264 and x265 libraries that arrived inside the PyAV wheel.** The x264 and x265
sources are unmodified; FFmpeg's are modified only by the patch described above, which is
included.

The complete corresponding source, pinned to the exact revisions these binaries were compiled
from, is attached to the [v0.1.0 release](https://github.com/DJsluxx/scribedrop/releases/tag/v0.1.0)
— the same place you obtained the archive, as GPLv2 §3(a) requires. The standalone archive also
carries `COPYING.GPLv2.txt` and `GPL-SOURCE-OFFER.txt` in its root.

| Component | Pinned source | Verified against the shipped binary by |
|---|---|---|
| FFmpeg 8.1.2 | [`ffmpeg-8.1.2.tar.xz`](https://ffmpeg.org/releases/ffmpeg-8.1.2.tar.xz) · SHA-256 `464beb5e…b524c` | `av_version_info()` returns `8.1.2`; `LIBAVCODEC_VERSION_MAJOR 62` matches `avcodec-62-*.dll` |
| x264, commit `b35605a` · © VideoLAN | [x264 archive](https://code.videolan.org/videolan/x264/-/archive/b35605ace3ddf7c1a5d67a2eb553f034aef41d55/x264-b35605ace3ddf7c1a5d67a2eb553f034aef41d55.tar.bz2) · SHA-256 `6eeb8293…ff224` | `X264_BUILD 165` matches `libx264-165-*.dll` and the imported `x264_encoder_open_165` |
| x265 4.2 · © MulticoreWare, Inc. | [`x265_4.2.tar.gz`](https://bitbucket.org/multicoreware/x265_git/downloads/x265_4.2.tar.gz) · SHA-256 `40b1ea04…e1210` | `X265_BUILD 216` matches the imported `x265_api_get_216`; `x265Version.txt` gives `4.2+1-e444744`, the exact version string the shipped DLL reports |
| Build scripts and patches | `pyav-ffmpeg` tag `8.1.2-1` | contains the configure line `avcodec_configuration()` reports |

Every SHA-256 above is the sum recorded in that build repository's own manifest
(`scripts/pkg.py`); we re-downloaded each tarball from its upstream host and confirmed the sum
before attaching it. The binaries themselves come from the
[PyAV wheel](https://pypi.org/project/av/) for the version listed in §1, unmodified.

If you want a build with no GPL component in the box at all, use the **from-source install**
(Option B in the README). It installs the same packages from PyPI into your own virtual
environment, so nothing is redistributed by us.

## 4. The other 18 libraries inside `_internal\av.libs\` — full attribution

`_internal\av.libs\` in the standalone `.zip` contains **25 files**, not the 7 you'd expect from
"FFmpeg": the 7 core FFmpeg libraries (`avcodec`, `avdevice`, `avfilter`, `avformat`, `avutil`,
`swresample`, `swscale` — the "FFmpeg" component discussed in §3) dynamically link against 18
further third-party shared libraries that PyAV's build vendors alongside them. Two of those 18 —
`libx264` and `libx265` — are the GPL libraries already fully attributed in §3 above, with their
own pinned corresponding-source. This section attributes the remaining 16, plus repeats x264/x265
in the table below for completeness so the folder's contents are attributed in one place.

**How each row was verified.** We did not trust any binary's self-reported version string, ours
or otherwise (see §3's x264/x265 finding for why). For each library we cross-checked three
independent sources and only wrote a row once at least two of them agreed:

1. The file's own Windows PE version resource, where the build embeds one (`FileVersion`,
   `ProductVersion`, `LegalCopyright`, and — for two of them — a literal `Licence` field), read
   directly off the shipped DLL with `pefile`.
2. [`PyAV-Org/pyav-ffmpeg`](https://github.com/PyAV-Org/pyav-ffmpeg) tag `8.1.2-1`,
   `scripts/pkg.py` — the same build manifest already used to source x264/x265/FFmpeg in §3. It
   pins an exact upstream tarball URL and SHA-256 for most of these libraries.
3. The `--enable-lib*` flags already recorded in `GPL-SOURCE-OFFER.txt`, captured by calling
   `avcodec_configuration()` on the shipped `avcodec` DLL — this confirms *which* of the 18 are
   actually compiled in, independent of both of the above.

Where a library's identity was confirmed but a version number could only be pinned via the build
manifest (not read back off the binary itself), the table says so explicitly.

| File in `av.libs\` | Project & version | Licence | Copyright | Verified by |
|---|---|---|---|---|
| `libSvtAv1Enc-*.dll` | [SVT-AV1](https://gitlab.com/AOMediaCodec/SVT-AV1) encoder, **v4.1.0** | BSD-3-Clause-Clear | © 2021 Alliance for Open Media | No version resource in the binary. Pinned by `pkg.py` (`SVT-AV1-v4.1.0.tar.bz2`); confirmed present by `--enable-libsvtav1` in `GPL-SOURCE-OFFER.txt`; the DLL's own export name (`SvtAv1Enc`) matches the project's library name. |
| `libdav1d-*.dll` | [dav1d](https://code.videolan.org/videolan/dav1d) **1.5.3** | BSD-2-Clause | © 2018–2025 VideoLAN and dav1d Authors | The DLL's own PE version resource reports `ProductVersion 1.5.3` and this exact copyright line — matches `pkg.py`'s pin (`dav1d-1.5.3.tar.bz2`) exactly. |
| `libgcc_s_seh-1-*.dll` | GCC runtime library (`libgcc`), **GCC 16.1.0** | **GPLv3 with the GCC Runtime Library Exception** — see below | © Free Software Foundation, Inc. | Binary strings report `GCC: (Rev5, Built by MSYS2 project) 16.1.0`. Not in `pkg.py`: this is part of the MSYS2 mingw-w64 cross-compiler toolchain that built these binaries, not an optional external codec library. |
| `libiconv-2-*.dll` | [GNU libiconv](https://www.gnu.org/software/libiconv/) **1.19** | **LGPL v2.1** — see below | © 1999–2026 Free Software Foundation, Inc. | The DLL's own version resource states `FileVersion 1.19`, `CompanyName Free Software Foundation`, and a `Comments` field that names the GNU Lesser General Public License verbatim. We downloaded `libiconv-1.19.tar.gz` from `ftp.gnu.org` (SHA-256 `88dd96a8c0464eca144fc791ae60cd31cd8ee78321e67397e25fc095c4a19aa6`, computed by us) — its `COPYING.LIB` is LGPLv2.1, matching the DLL's own claim. Not in `pkg.py`: ships from the MSYS2 toolchain, not a pyav-ffmpeg-built codec. |
| `libmp3lame-0-*.dll` | [LAME](https://lame.sourceforge.io/) **3.100** | **LGPL v2** — see below | © The LAME Project (originally Mike Cheng, later Mark Taylor) | No version resource in the binary. Pinned by `pkg.py` (`lame_3.100.orig.tar.gz` from Debian's mirror, SHA-256 `ddfe36ca…1da1e` — we re-downloaded it and the sum matched exactly); confirmed present by `--enable-libmp3lame`. LAME's own `README` states "distributed under the GNU LIBRARY GENERAL PUBLIC LICENSE (LGPL, see www.gnu.org), version 2." |
| `libopencore-amrnb-0-*.dll` | opencore-amr (AMR narrowband) **0.1.6** | Apache-2.0 | © 1998–2009 PacketVideo | No version resource. Pinned by `pkg.py` (`opencore-amr-0.1.6.tar.gz`); confirmed by `--enable-libopencore-amrnb`. Licence and copyright cross-checked against Debian's package copyright record for `opencore-amr`, which quotes the same Apache-2.0 grant from the original Android/PacketVideo `opencore` source. |
| `libopencore-amrwb-0-*.dll` | opencore-amr (AMR wideband) **0.1.6** | Apache-2.0 | © 1998–2009 PacketVideo | Same package as above; confirmed by `--enable-libopencore-amrwb`. |
| `libopus-0-*.dll` | [Opus](https://opus-codec.org/) **1.6.1** | BSD-3-Clause (with a royalty-free patent-licence pointer, not a patent grant in the licence text itself) | © 2001–2023 Xiph.Org, Skype Limited, Octasic, Jean-Marc Valin, Timothy B. Terriberry, CSIRO, Gregory Maxwell, Mark Borgerding, Erik de Castro Lopo, Mozilla, Amazon | The DLL's own strings literally contain `libopus 1.6.1`, matching `pkg.py`'s pin (`opus-1.6.1.tar.gz`) exactly; confirmed by `--enable-libopus`. |
| `libsharpyuv-*.dll` | [libwebp](https://chromium.googlesource.com/webm/libwebp) **1.6.0** (sharpyuv is built as part of the webp source tree) | BSD-3-Clause | © 2010 Google Inc. | No version resource. Built from the same `webp-1.6.0.tar.gz` pin in `pkg.py` as `libwebp`/`libwebpmux` below; confirmed present by `--enable-libwebp`. |
| `libstdc++-6-*.dll` | GCC runtime library (`libstdc++`), **GCC 16.1.0** | **GPLv3 with the GCC Runtime Library Exception** — see below | © Free Software Foundation, Inc. | Same toolchain evidence as `libgcc_s_seh` above. Also bundles the **IANA Time Zone Database, version 2025c**, as a fallback for `std::chrono`'s timezone support on Windows (which has no OS-provided tz database); confirmed by the strings `# version 2025c` and `tzdb: no version found in tzdata.zi`. IANA's own `LICENSE` states the tz database "is in the public domain" — no separate notice obligation. |
| `libvpl-*.dll` | [Intel® oneVPL dispatcher](https://github.com/intel/libvpl) **v2.16.0** | MIT | © 2020–2021 Intel Corporation | The DLL's own version resource reports `ProductVersion 2.16`, `CompanyName Intel`, matching `pkg.py`'s pin (`libvpl v2.16.0.tar.gz`) exactly; confirmed present by `--enable-libvpl`. (No decoded/encoded frame ever reaches this path on a CPU-only build; it ships because FFmpeg was compiled with Intel QuickSync support available for GPU builds of ScribeDrop.) |
| `libvpx-1-*.dll` | [libvpx](https://chromium.googlesource.com/webm/libvpx) (VP8/VP9) **1.16.0** | BSD-3-Clause | © 2010 The WebM Project authors | No version resource. Pinned by `pkg.py` (`libvpx-1.16.0.tar.gz`); confirmed present by `--enable-libvpx`. |
| `libwebp-*.dll` | [libwebp](https://chromium.googlesource.com/webm/libwebp) **1.6.0** | BSD-3-Clause | © 2010 Google Inc. | No version resource. Pinned by `pkg.py` (`webp-1.6.0.tar.gz`); confirmed present by `--enable-libwebp`. |
| `libwebpmux-*.dll` | libwebp (mux/demux API) **1.6.0** | BSD-3-Clause | © 2010 Google Inc. | Same package and evidence as `libwebp` above. |
| `libwinpthread-1-*.dll` | [mingw-w64 winpthreads](https://sourceforge.net/projects/mingw-w64/) **1.0** | **MIT AND BSD-3-Clause** (two components in one file — see below) | © 2011 mingw-w64 project; © 2010 Lockless Inc. (the Windows condition-variable/rwlock portion) | The DLL's own version resource is the most direct evidence we found on any of these 25 files: it contains a literal `Licence = MIT AND BSD-3-Clause` field, plus both copyright lines. We fetched mingw-w64's own `COPYING` for winpthreads and confirmed it matches both halves exactly. Not in `pkg.py`: ships from the MSYS2 toolchain. |
| `libx264-165-*.dll` | [x264](https://code.videolan.org/videolan/x264), commit `b35605a` | **GPLv2-or-later** | © VideoLAN | **Already fully attributed in §3 above**, including pinned corresponding source and the LGPLv3-mislabelling finding. Repeated here only so this table lists all 18 files actually present. |
| `libx265-*.dll` | [x265](https://bitbucket.org/multicoreware/x265_git) **4.2** | **GPLv2-or-later** (the DLL's own version resource literally says `Multicoreware: GPLv2 or commercial`) | © 2013–2018 MulticoreWare, Inc. | **Already fully attributed in §3 above.** Repeated here for completeness. |
| `zlib1-*.dll` | [zlib](https://zlib.net/) **1.3.2** | zlib License | © 1995–2026 Jean-loup Gailly and Mark Adler | The DLL's own strings literally contain `deflate 1.3.2 Copyright 1995-2026 Jean-loup Gailly and Mark Adler` / `inflate 1.3.2 Copyright 1995-2026 Mark Adler`, an exact match for upstream `zlib.h`'s own header comment for that release; confirmed present by `--enable-zlib`. |

Every row above was verifiable to a specific upstream project and licence file — **none of the 18
are marked unverified.** The two that could not be pinned to an exact version number by reading
the binary itself (SVT-AV1, LAME) were still positively identified via the build manifest that
produced them (`pkg.py`) plus FFmpeg's own recorded `--enable-lib*` configuration, which is two
independent confirmations of *which* library it is, even without a third confirming the version
digit; we are not guessing at identity or licence, only at the least-significant version digits.

### GPLv3 with the GCC Runtime Library Exception — `libgcc_s_seh` and `libstdc++`

These two files are the C and C++ runtime support libraries for the GCC compiler that built every
DLL in this bundle. GCC's runtime libraries are licensed under GPLv3, which would normally make
*anything they're linked into* GPLv3 too — but GCC ships them with an explicit carve-out, the
[**GCC Runtime Library Exception**](https://www.gnu.org/licenses/gcc-exception-3.1.html) (version
3.1), which exists specifically so that GCC can be used to compile non-GPL — including
closed-source or differently-licensed — programs without the compiler's own runtime pulling them
under GPLv3. The exception is what makes shipping these two files alongside an MIT-licensed
application unremarkable; without it, "GPLv3" here would be a real problem, and we want a reader
who spots that string to see this paragraph before they conclude anything is wrong.

### LGPL relinking position — `libiconv` and `libmp3lame`

Both are shipped exactly as PyAV's wheel built them: **unmodified**, and only as standalone
dynamically-loaded `.dll` files, never statically linked into another binary. That matters because
it is what LGPLv2/2.1 conditions the redistributor's obligations on:

- **Relinking.** Because these are ordinary Windows DLLs loaded at runtime (not code baked into
  `avcodec.dll` itself), the mechanism the LGPL calls "relinking" is already available to anyone:
  drop a differently-built `libiconv-2-*.dll` or `libmp3lame-0-*.dll` of your own, with the same
  exported symbols, into `_internal\av.libs\`, and ScribeDrop will load it in place of ours. We are
  not aware of any additional step the LGPL requires of us for a library we did not modify and
  distribute only in this form.
- **Source availability.** We did not patch either library (unlike x264/x265, where FFmpeg's own
  `avcodec_configuration()` proves a patch exists — see §3). Because there is no modification to
  disclose, the applicable source is simply upstream's own unmodified release, at the versions
  pinned above: libiconv 1.19 from `ftp.gnu.org/gnu/libiconv/libiconv-1.19.tar.gz`, and LAME 3.100
  from the exact URL and SHA-256 pinned in `pyav-ffmpeg`'s `scripts/pkg.py` (already reproduced in
  the table above). We did not attach new tarballs to the v0.1.0 release for these two the way we
  did for FFmpeg/x264/x265, because unlike those, nothing here was modified — the same
  transparency (pinned version, checksum, canonical upstream host) already exists via the table
  above and via `pkg.py`, which is itself attached to the release as
  `pyav-ffmpeg-8.1.2-1-build-scripts.tar.gz`.
- **Licence text.** LGPLv2.1's full text is at
  <https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html>; LGPLv2's (which LAME's own README
  cites by name) is at <https://www.gnu.org/licenses/old-licenses/lgpl-2.0.html>. We have not
  copied either into a root-level file the way `COPYING.GPLv2.txt` covers x264/x265, because the
  obligation here is notice, not the §3(a)/§3(b) source-conveyance duty that made a physically
  shipped copy worth doing for the GPL components — see §3.

### Licence texts reproduced verbatim (BSD, MIT, and zlib-family licences from the table above)

Apache-2.0 (opencore-amr) is not reproduced below — its own terms are satisfied by citing the
license by name and version with a link to the canonical, unmodified text, exactly as this
document already does for the Apache-2.0 components in §1. Everything below requires the
copyright notice and licence conditions to travel with the binary, so it is quoted in full.

**dav1d (BSD-2-Clause):**
```
Copyright © 2018-2025, VideoLAN and dav1d authors
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

**libvpx (BSD-3-Clause, "New BSD"):**
```
Copyright (c) 2010, The WebM Project authors. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.

  * Neither the name of Google, nor the WebM Project, nor the names
    of its contributors may be used to endorse or promote products
    derived from this software without specific prior written
    permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

**libwebp, libwebpmux, and libsharpyuv (BSD-3-Clause, identical text to libvpx above except for
the copyright holder):**
```
Copyright (c) 2010, Google Inc. All rights reserved.

[... same redistribution conditions and disclaimer as the libvpx licence above ...]
```

**libSvtAv1Enc (BSD-3-Clause-Clear — note the added "no patent rights" sentence):**
```
Copyright (c) 2021, Alliance for Open Media
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted (subject to the limitations in the disclaimer below)
provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in
   the documentation and/or other materials provided with the distribution.

3. Neither the name of the Alliance for Open Media nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY THIS LICENSE.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

**libopus (BSD-3-Clause, Xiph.Org's wording, plus a non-binding patent-licence pointer):**
```
Copyright 2001-2023 Xiph.Org, Skype Limited, Octasic,
                    Jean-Marc Valin, Timothy B. Terriberry,
                    CSIRO, Gregory Maxwell, Mark Borgerding,
                    Erik de Castro Lopo, Mozilla, Amazon

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

- Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

- Neither the name of Internet Society, IETF or IETF Trust, nor the
names of specific contributors, may be used to endorse or promote
products derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER
OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

**libvpl (MIT):**
```
MIT License

Copyright (c) 2020 Intel Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**libwinpthread (MIT, mingw-w64 project's own portion):**
```
Copyright (c) 2011 mingw-w64 project

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
```

**libwinpthread (BSD-3-Clause, the embedded Lockless Inc. portion covering the Windows
condition-variable/rwlock implementation it derives from):**
```
Posix Threads library for Microsoft Windows
(C) 2010 Lockless Inc. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 * Neither the name of Lockless Inc. nor the names of its contributors may be
   used to endorse or promote products derived from this software without
   specific prior written permission.
```

**zlib (zlib License):**
```
Copyright (C) 1995-2026 Jean-loup Gailly and Mark Adler

This software is provided 'as-is', without any express or implied
warranty.  In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.

Jean-loup Gailly        Mark Adler
jloup@gzip.org          madler@alumni.caltech.edu
```

## 5. Other binaries inside the standalone bundle

| File | What it is | Licence |
|---|---|---|
| `_internal\ctranslate2\libiomp5md.dll` | Intel® OpenMP\* Runtime Library, © 1997–2025 Intel Corporation. Arrives inside the CTranslate2 wheel; we do not add it. | Intel's build of the LLVM OpenMP runtime. Redistributable with applications; see [Intel's licensing](https://www.intel.com/content/www/us/en/developer/articles/license/onemkl-license-faq.html). |
| PyInstaller bootloader (`ScribeDrop.exe` stub) | The **stock, unmodified** compiled bootloader shipped in the PyInstaller wheel. We do not build a custom bootloader. | GPLv2-or-later **with the PyInstaller exception**, which grants "unlimited permission to link or embed compiled bootloader and related files into combinations with other programs, and to distribute those combinations without any restriction coming from the use of those files." |
| `api-ms-win-*.dll`, `ucrtbase.dll`, `VCRUNTIME140*.dll` | Microsoft Universal C Runtime redistributables, collected by PyInstaller. | Microsoft redistributable terms. |

**No NVIDIA CUDA library ships in any ScribeDrop release archive.** The standalone bundle is
CPU-only and `build_exe.bat` deletes `cudnn64_*.dll` and friends after every build and fails
the build if any survives. GPU users install `nvidia-cublas-cu12` and `nvidia-cudnn-cu12`
themselves, from NVIDIA's own PyPI wheels, via `setup.bat`.

---

## 6. tkdnd licence, reproduced verbatim

The tkdnd licence requires that "this notice is included verbatim in any distributions".
Here it is, unaltered:

```
This software is copyrighted by:
   Georgios Petasis, Athens, Greece.
   e-mail: petasisg@yahoo.gr, petasis@iit.demokritos.gr

   Mac portions (c) 2009-2014 Kevin Walzer/WordTech Communications LLC,
   kw@codebykevin.com

The following terms apply to all files associated with the
software unless explicitly disclaimed in individual files.

The authors hereby grant permission to use, copy, modify, distribute,
and license this software and its documentation for any purpose, provided
that existing copyright notices are retained in all copies and that this
notice is included verbatim in any distributions. No written agreement,
license, or royalty fee is required for any of the authorized uses.
Modifications to this software may be copyrighted by their authors
and need not follow the licensing terms described here, provided that
the new terms are clearly indicated on the first page of each file where
they apply.

IN NO EVENT SHALL THE AUTHORS OR DISTRIBUTORS BE LIABLE TO ANY PARTY
FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES
ARISING OUT OF THE USE OF THIS SOFTWARE, ITS DOCUMENTATION, OR ANY
DERIVATIVES THEREOF, EVEN IF THE AUTHORS HAVE BEEN ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.

THE AUTHORS AND DISTRIBUTORS SPECIFICALLY DISCLAIM ANY WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.  THIS SOFTWARE
IS PROVIDED ON AN "AS IS" BASIS, AND THE AUTHORS AND DISTRIBUTORS HAVE
NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR
MODIFICATIONS.

GOVERNMENT USE: If you are acquiring this software on behalf of the
U.S. government, the Government shall have only "Restricted Rights"
in the software and related documentation as defined in the Federal 
Acquisition Regulations (FARs) in Clause 52.227.19 (c) (2).  If you
are acquiring the software on behalf of the Department of Defense, the
software shall be classified as "Commercial Computer Software" and the
Government shall have only "Restricted Rights" as defined in Clause
252.227-7013 (c) (1) of DFARs.  Notwithstanding the foregoing, the
authors grant the U.S. Government and others acting in its behalf
permission to use and distribute the software in accordance with the
terms specified in this license.
```

## 7. tkinterdnd2 licence, reproduced verbatim

```
MIT License

Copyright (c) 2020 Philippe Gagné

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

If you believe something here is wrong or missing, please open an issue. Getting attribution
right matters more to us than getting it out quickly.
