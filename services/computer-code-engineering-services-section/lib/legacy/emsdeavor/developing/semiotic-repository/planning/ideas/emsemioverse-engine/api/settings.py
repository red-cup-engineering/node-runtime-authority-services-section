"""Application settings for the Emsemioverse engine.

Centralizes configuration using pydantic-settings, loading defaults from .env.
Environment variables use the prefix `EMSEMIOVERSE_` (e.g.,
`EMSEMIOVERSE_HOST`, `EMSEMIOVERSE_PORT`).
"""

from __future__ import annotations

from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API service."""

    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("EMSEMIOVERSE_HOST", "HOST"))
    port: int = Field(default=5000, validation_alias=AliasChoices("EMSEMIOVERSE_PORT", "PORT"))
    log_level: str = Field(default="info", validation_alias=AliasChoices("EMSEMIOVERSE_LOG_LEVEL", "LOG_LEVEL"))
    allow_origins: List[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )


# Singleton settings instance
settings = Settings()
