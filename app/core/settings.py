from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env-model"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Thesis Agent Backend", alias="APP_NAME")
    environment: Literal["local", "dev", "staging", "prod"] = Field(
        default="local", alias="ENVIRONMENT"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # Embeddings
    # NOTE: DB schema uses Vector(768). Keep these aligned.
    gemini_embedding_model: str = Field(
        default="text-embedding-004", alias="GEMINI_EMBEDDING_MODEL"
    )
    gemini_embedding_dim: int = Field(default=768, alias="GEMINI_EMBEDDING_DIM")

    db_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    db_port: int = Field(default=5432, alias="POSTGRES_PORT")
    db_user: str = Field(default="app", alias="POSTGRES_USER")
    db_password: str = Field(default="app", alias="POSTGRES_PASSWORD")
    db_name: str = Field(default="app", alias="POSTGRES_DB")

    db_readonly_user: str | None = Field(default=None, alias="POSTGRES_READONLY_USER")
    db_readonly_password: str | None = Field(
        default=None, alias="POSTGRES_READONLY_PASSWORD"
    )

    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    database_url_readonly_override: str | None = Field(
        default=None, alias="DATABASE_URL_READONLY"
    )

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_readonly(self) -> str:
        if self.database_url_readonly_override:
            return self.database_url_readonly_override

        if self.db_readonly_user and self.db_readonly_password:
            return (
                f"postgresql+psycopg2://{self.db_readonly_user}:{self.db_readonly_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )

        # Backward-compatible fallback: if readonly creds aren't configured,
        # use the primary URL.
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
