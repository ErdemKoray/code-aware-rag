import pytest
from pydantic import ValidationError

from coderag.config import MissingSettingError, Settings, require


def test_settings_reads_api_key_from_env(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")

    settings = Settings(_env_file=None)

    assert settings.voyage_api_key is not None
    assert settings.voyage_api_key.get_secret_value() == "test-key"


def test_empty_api_key_is_treated_as_missing(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "")

    settings = Settings(_env_file=None)

    assert settings.voyage_api_key is None


def test_require_fails_with_clear_message_when_key_missing(monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    with pytest.raises(MissingSettingError, match="VOYAGE_API_KEY"):
        require(settings.voyage_api_key, "VOYAGE_API_KEY")


def test_max_file_size_bytes_defaults_to_500_000(monkeypatch):
    monkeypatch.delenv("MAX_FILE_SIZE_BYTES", raising=False)

    settings = Settings(_env_file=None)

    assert settings.max_file_size_bytes == 500_000


def test_max_file_size_bytes_can_be_overridden_from_env(monkeypatch):
    monkeypatch.setenv("MAX_FILE_SIZE_BYTES", "1234")

    settings = Settings(_env_file=None)

    assert settings.max_file_size_bytes == 1234


@pytest.mark.parametrize("value", ["0", "-1"])
def test_max_file_size_bytes_must_be_positive(monkeypatch, value):
    monkeypatch.setenv("MAX_FILE_SIZE_BYTES", value)

    with pytest.raises(ValidationError, match="max_file_size_bytes"):
        Settings(_env_file=None)
