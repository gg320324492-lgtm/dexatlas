"""Runtime settings, resolved from the environment with sane defaults."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration.

    Every external analysis backend is discovered rather than vendored. Paths can be
    pinned explicitly, but the default behaviour is to look for the tool on ``PATH``.
    """

    model_config = SettingsConfigDict(
        env_prefix="DEXATLAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    workspace: Path = Field(default=Path(".dexatlas"))

    # External analysis backends. An empty string disables that backend; an unset
    # value leaves it to the default discovery, which looks for the tool on PATH.
    jadx_path: str | None = None
    apktool_jar: str | None = None
    rizin_path: str | None = None
    ghidra_path: str | None = None

    # Subprocess execution. Backends parse untrusted input; give up rather than hang.
    tool_timeout_seconds: int = Field(default=900, ge=1)
    tool_max_output_bytes: int = Field(default=256 * 1024 * 1024, ge=1024)

    log_level: str = "INFO"

    @field_validator("workspace", mode="before")
    @classmethod
    def _expand_workspace(cls, value: object) -> object:
        return Path(value).expanduser() if isinstance(value, str) else value

    @property
    def database_path(self) -> Path:
        return self.workspace / "dexatlas.db"

    @property
    def projects_dir(self) -> Path:
        return self.workspace / "projects"

    @property
    def cache_dir(self) -> Path:
        return self.workspace / "cache"

    def ensure_workspace(self) -> None:
        for path in (self.workspace, self.projects_dir, self.cache_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
