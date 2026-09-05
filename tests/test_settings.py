"""Settings round-trip and tolerance of a corrupt config file."""

from __future__ import annotations

import json
from pathlib import Path

from scribedrop.settings import (
    Settings,
    default_models_dir,
    load_settings,
    save_settings,
    settings_from_dict,
)


class TestRoundTrip:
    def test_defaults_survive_dict_round_trip(self):
        assert settings_from_dict(Settings().to_dict()) == Settings()

    def test_custom_values_survive_dict_round_trip(self):
        original = Settings(
            model="large-v3",
            language="he",
            formats=("txt", "srt", "vtt"),
            output_dir="D:/out",
            device="cpu",
            models_dir="D:/models",
        )
        assert settings_from_dict(original.to_dict()) == original

    def test_file_round_trip(self, tmp_path):
        path = tmp_path / "settings.json"
        original = Settings(model="medium", language="fr", formats=("vtt",), device="cuda")
        assert save_settings(original, path) is None
        loaded, warning = load_settings(path)
        assert warning is None
        assert loaded == original

    def test_saved_file_is_valid_utf8_json(self, tmp_path):
        path = tmp_path / "settings.json"
        save_settings(Settings(output_dir="D:/ניסוי"), path)
        assert json.loads(path.read_text(encoding="utf-8"))["output_dir"] == "D:/ניסוי"

    def test_save_creates_missing_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "settings.json"
        assert save_settings(Settings(), path) is None
        assert path.is_file()


class TestTolerance:
    def test_missing_file_gives_defaults_without_warning(self, tmp_path):
        loaded, warning = load_settings(tmp_path / "absent.json")
        assert loaded == Settings()
        assert warning is None

    def test_corrupt_json_gives_defaults_with_warning(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text("{not json", encoding="utf-8")
        loaded, warning = load_settings(path)
        assert loaded == Settings()
        assert warning is not None

    def test_unknown_model_falls_back(self):
        assert settings_from_dict({"model": "gpt-9"}).model == Settings().model

    def test_unknown_language_falls_back(self):
        assert settings_from_dict({"language": "klingon"}).language == "auto"

    def test_unknown_device_falls_back(self):
        assert settings_from_dict({"device": "tpu"}).device == "auto"

    def test_junk_formats_fall_back_to_defaults(self):
        assert settings_from_dict({"formats": ["ass", "sub"]}).formats == ("txt",)

    def test_formats_are_normalised_to_catalog_order(self):
        assert settings_from_dict({"formats": ["vtt", "txt"]}).formats == ("txt", "vtt")

    def test_non_dict_payload_gives_defaults(self):
        assert settings_from_dict(["nope"]) == Settings()
        assert settings_from_dict(None) == Settings()


class TestDerivedPaths:
    def test_empty_output_dir_means_next_to_source(self):
        assert Settings(output_dir="").resolved_output_dir() is None

    def test_output_dir_becomes_a_path(self):
        assert Settings(output_dir="D:/out").resolved_output_dir() == Path("D:/out")

    def test_empty_models_dir_uses_app_default(self):
        assert Settings(models_dir="").resolved_models_dir() == default_models_dir()

    def test_models_dir_override(self):
        assert Settings(models_dir="D:/m").resolved_models_dir() == Path("D:/m")


class TestImmutableToggles:
    def test_with_format_adds_without_mutating(self):
        original = Settings(formats=("txt",))
        updated = original.with_format("srt", True)
        assert original.formats == ("txt",)
        assert updated.formats == ("txt", "srt")

    def test_with_format_removes(self):
        assert Settings(formats=("txt", "srt")).with_format("srt", False).formats == ("txt",)

    def test_removing_the_last_format_keeps_txt(self):
        assert Settings(formats=("srt",)).with_format("srt", False).formats == ("txt",)

    def test_adding_twice_is_idempotent(self):
        once = Settings(formats=("txt",)).with_format("vtt", True)
        assert once.with_format("vtt", True).formats == once.formats
