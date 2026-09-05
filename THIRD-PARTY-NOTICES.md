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
standalone `.zip`, in `_internal\av.libs\`. This is not a licence problem for FFmpeg itself —
FFmpeg reports its own licence as **"LGPL version 3 or later"** for every one of the seven
libraries — but you should know it is there, and there is one complication:

**The PyAV wheel also vendors `libx264` and `libx265`, which are GPLv2-or-later, and PyAV's
`avcodec` is dynamically linked against both.** We do not use them: ScribeDrop only decodes
audio and never encodes video. We cannot remove them either — deleting them makes
`import av` fail outright and takes all audio decoding with it. Every PyAV Windows wheel from
13.x through 18.x ships them.

So, stated plainly rather than buried: **the standalone `ScribeDrop-*-win64-cpu.zip` contains
GPL-licensed x264 and x265 libraries that arrived inside the PyAV wheel.** Their sources are
public and unmodified:

- FFmpeg — <https://ffmpeg.org/download.html> · licence: <https://ffmpeg.org/legal.html>
- x264 — <https://www.videolan.org/developers/x264.html> (GPLv2 or later) · © VideoLAN
- x265 — <https://bitbucket.org/multicoreware/x265_git> (GPLv2 or later) · © MulticoreWare, Inc.
- The exact binaries, and the build that produced them, come from the
  [PyAV wheel](https://pypi.org/project/av/) for the version listed in §1.

If you want a build with no GPL component in the box at all, use the **from-source install**
(Option B in the README). It installs the same packages from PyPI into your own virtual
environment, so nothing is redistributed by us.

## 4. Other binaries inside the standalone bundle

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

## 5. tkdnd licence, reproduced verbatim

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

## 6. tkinterdnd2 licence, reproduced verbatim

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
