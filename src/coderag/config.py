from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingSettingError(Exception):
    """Raised when a required setting is not configured."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # API keys: optional until a command actually needs them.
    anthropic_api_key: SecretStr | None = None
    voyage_api_key: SecretStr | None = None

    # Target repository, pinned so evaluation results stay comparable.
    fastapi_repo_path: Path = Path("data/repos/fastapi")
    fastapi_tag: str = "PUT_TAG_HERE"
    fastapi_sha: str = "PUT_SHA_HERE"


def require(value: SecretStr | None, env_name: str) -> str:
    """Return the secret as plain text, or fail with a one-line message."""
    if value is None or not value.get_secret_value():
        raise MissingSettingError(f"{env_name} is not set; add it to .env")
    return value.get_secret_value()
