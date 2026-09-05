"""Make the NVIDIA runtime DLLs findable before CTranslate2 loads.

CTranslate2 needs cublas64_12.dll and cudnn*_9.dll at runtime. The pip
packages `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` ship them inside
site-packages/nvidia/*/bin, which Windows does not search by default - so
the GPU silently fails with "Library cublas64_12.dll is not found".

This module adds those folders to the process DLL search path. It must run
before the first `import ctranslate2`, so `engine` calls it at import time.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

_NVIDIA_SUBPACKAGES = ("cublas", "cudnn", "cuda_runtime", "cuda_nvrtc")

# CTranslate2 loads these lazily, deep inside the first encode() call. If they
# are absent it can hang rather than raise, so we probe them up front instead.
_REQUIRED_DLLS = ("cublas64_12.dll", "cudnn64_9.dll")

_registered = False


def _nvidia_bin_dirs() -> list[Path]:
    try:
        import nvidia
    except ImportError:
        return []
    roots = [Path(part) for part in getattr(nvidia, "__path__", [])]
    found: list[Path] = []
    for root in roots:
        for name in _NVIDIA_SUBPACKAGES:
            for leaf in ("bin", "lib"):
                candidate = root / name / leaf
                if candidate.is_dir():
                    found.append(candidate)
    return found


def register_cuda_dlls() -> list[Path]:
    """Add bundled NVIDIA DLL folders to the search path. Idempotent, never raises."""
    global _registered
    if _registered or sys.platform != "win32":
        _registered = True
        return []
    added: list[Path] = []
    for directory in _nvidia_bin_dirs():
        try:
            os.add_dll_directory(str(directory))
        except OSError:
            continue
        added.append(directory)
    if added:
        # PATH matters too: CTranslate2 loads some libraries via plain
        # LoadLibrary, which ignores add_dll_directory in older loaders.
        existing = os.environ.get("PATH", "")
        os.environ["PATH"] = os.pathsep.join([str(p) for p in added] + [existing])
    _registered = True
    return added


def missing_cuda_libraries() -> list[str]:
    """Return the CUDA DLLs that cannot be loaded. Empty list means GPU is usable.

    This exists because a missing cuBLAS or cuDNN does not reliably raise -
    CTranslate2 has been observed to hang instead. Probing with LoadLibrary
    turns an indefinite hang into an instant, announced CPU fallback.
    """
    if sys.platform != "win32":
        return []
    register_cuda_dlls()
    missing: list[str] = []
    for name in _REQUIRED_DLLS:
        try:
            ctypes.WinDLL(name)
        except OSError:
            missing.append(name)
    return missing
