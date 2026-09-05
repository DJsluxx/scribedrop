"""Device-selection policy - the logic that decides GPU vs CPU.

This is pure decision logic with no model loading, so it is unit-testable.
It matters because getting it wrong means either a silent 20x slowdown or
an indefinite hang on a machine with a half-installed CUDA runtime.
"""

from __future__ import annotations

import pytest

from scribedrop import engine
from scribedrop.engine import CPU_LADDER, GPU_LADDER, device_ladder, gpu_status, looks_like_device_failure


@pytest.fixture()
def no_gpu(monkeypatch):
    monkeypatch.setattr(engine, "cuda_device_present", lambda: False)
    monkeypatch.setattr(engine, "missing_cuda_libraries", lambda: [])


@pytest.fixture()
def gpu_with_libs(monkeypatch):
    monkeypatch.setattr(engine, "cuda_device_present", lambda: True)
    monkeypatch.setattr(engine, "missing_cuda_libraries", lambda: [])


@pytest.fixture()
def gpu_without_libs(monkeypatch):
    monkeypatch.setattr(engine, "cuda_device_present", lambda: True)
    monkeypatch.setattr(engine, "missing_cuda_libraries", lambda: ["cublas64_12.dll"])


class TestGpuStatus:
    def test_no_device(self, no_gpu):
        usable, message = gpu_status()
        assert usable is False
        assert "No CUDA GPU" in message

    def test_device_and_libraries_present(self, gpu_with_libs):
        assert gpu_status() == (True, "GPU (CUDA) ready.")

    def test_device_but_missing_libraries_is_not_usable(self, gpu_without_libs):
        usable, message = gpu_status()
        assert usable is False
        assert "cublas64_12.dll" in message
        assert "requirements-gpu.txt" in message


class TestDeviceLadder:
    def test_gpu_first_when_fully_available(self, gpu_with_libs):
        assert device_ladder("auto") == GPU_LADDER + CPU_LADDER

    def test_cpu_only_when_no_device(self, no_gpu):
        assert device_ladder("auto") == CPU_LADDER

    def test_missing_libraries_skips_gpu_entirely(self, gpu_without_libs):
        # The whole point: never offer a GPU rung that will hang.
        assert device_ladder("auto") == CPU_LADDER
        assert device_ladder("cuda") == CPU_LADDER

    def test_explicit_cpu_preference_always_wins(self, gpu_with_libs):
        assert device_ladder("cpu") == CPU_LADDER

    def test_every_ladder_ends_on_cpu(self, gpu_with_libs):
        for preference in ("auto", "cuda", "cpu"):
            assert device_ladder(preference)[-1].device == "cpu"


class TestFailureClassification:
    @pytest.mark.parametrize(
        "message",
        [
            "CUDA failed with error out of memory",
            "Library cublas64_12.dll is not found or cannot be loaded",
            "cuDNN error",
            "unsupported compute type float16",
            "no kernel image is available for execution",
        ],
    )
    def test_device_problems_are_recognised(self, message):
        assert looks_like_device_failure(RuntimeError(message)) is True

    @pytest.mark.parametrize(
        "message",
        ["Invalid data found when processing input", "file is empty", "permission denied"],
    )
    def test_file_problems_are_not_device_problems(self, message):
        assert looks_like_device_failure(RuntimeError(message)) is False
