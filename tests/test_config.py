import pytest

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
