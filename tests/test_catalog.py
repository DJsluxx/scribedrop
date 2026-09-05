"""The model and language catalogue the UI is built from.

These are not decorative tests. Every string here ends up either in a combo
box the user reads or in a Hugging Face repo id the app downloads, and two
of them are licence-relevant: the model list must not grow a `turbo` entry
(a third-party upload whose licence we have not cleared) and the language
count is quoted verbatim in the README.
"""

from __future__ import annotations

from scribedrop.catalog import (
    DEFAULT_MODEL,
    LABEL_TO_LANGUAGE,
    LANGUAGE_LABELS,
    LANGUAGES,
    MODELS,
    MODELS_BY_KEY,
    OUTPUT_FORMATS,
    ModelChoice,
    model_for,
)


class TestModels:
    def test_keys_are_the_five_we_ship(self):
        assert [m.key for m in MODELS] == ["tiny", "base", "small", "medium", "large-v3"]

    def test_no_turbo_model_is_exposed(self):
        """`turbo` maps to a third-party HF uploader whose licence is unverified."""
        keys = " ".join(m.key for m in MODELS).lower()
        assert "turbo" not in keys

    def test_default_is_a_real_model(self):
        assert DEFAULT_MODEL in MODELS_BY_KEY

    def test_keys_are_unique(self):
        keys = [m.key for m in MODELS]
        assert len(keys) == len(set(keys))

    def test_every_model_states_a_download_size(self):
        for model in MODELS:
            assert model.download.strip(), f"{model.key} has no download size"
            assert "B" in model.download, f"{model.key} size is not a byte figure"

    def test_every_model_has_a_note(self):
        assert all(m.note.strip() for m in MODELS)

    def test_display_shows_label_and_size(self):
        choice = ModelChoice("x", "extra", "~9 MB", "note")
        assert choice.display == "extra  -  ~9 MB"

    def test_index_matches_the_tuple(self):
        assert MODELS_BY_KEY == {m.key: m for m in MODELS}

    def test_model_for_returns_the_requested_model(self):
        assert model_for("large-v3").key == "large-v3"

    def test_model_for_falls_back_instead_of_raising(self):
        """A stale settings file must not crash the app on startup."""
        assert model_for("no-such-model").key == DEFAULT_MODEL
        assert model_for("").key == DEFAULT_MODEL


class TestLanguages:
    def test_auto_is_first_so_it_is_the_visible_default(self):
        assert LANGUAGES[0][0] == "auto"

    def test_readme_claim_of_28_explicit_languages(self):
        explicit = [code for code, _ in LANGUAGES if code != "auto"]
        assert len(explicit) == 28

    def test_codes_are_unique(self):
        codes = [code for code, _ in LANGUAGES]
        assert len(codes) == len(set(codes))

    def test_labels_are_unique(self):
        labels = [label for _, label in LANGUAGES]
        assert len(labels) == len(set(labels))

    def test_codes_are_lowercase_iso_shaped(self):
        for code, _ in LANGUAGES:
            if code == "auto":
                continue
            assert code.islower() and 2 <= len(code) <= 3, code

    def test_label_lookup_round_trips(self):
        for code, label in LANGUAGES:
            assert LANGUAGE_LABELS[code] == label
            assert LABEL_TO_LANGUAGE[label] == code


class TestOutputFormats:
    def test_exactly_txt_srt_vtt(self):
        assert [key for key, _ in OUTPUT_FORMATS] == ["txt", "srt", "vtt"]

    def test_each_label_names_its_extension(self):
        for key, label in OUTPUT_FORMATS:
            assert f".{key}" in label
