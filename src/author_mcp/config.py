"""Configuration settings for Author-MCP and ATC."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent
_IS_CONTAINER = Path("/.dockerenv").exists() or os.getenv("CONTAINER_NAME") is not None or Path("/app").is_dir()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("AUTHOR_MCP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("AUTHOR_MCP_PORT", "8083"))

    # Suite ATC identity
    SUITE_NAME: str = "Author"
    ATC_ROLE: str = "Root MCP Server & Air Traffic Control"

    # Redis Session storage
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://Author-Sessions:6379/0" if _IS_CONTAINER else "redis://localhost:6379/0"
    )

    # Local Storage and Knowledgebase Indices
    DATA_DIR: Path = Path(os.getenv("AUTHOR_DATA_DIR", "/app/data" if _IS_CONTAINER else str(_DEFAULT_ROOT / "data")))
    STORAGE_DIR: Path = Path(
        os.getenv("AUTHOR_STORAGE_DIR", "/app/data/indices" if _IS_CONTAINER else str(_DEFAULT_ROOT / "data" / "indices"))
    )

    # Books Repository Path
    BOOKS_DIR: Path = Path(
        os.getenv(
            "BOOKS_DIR",
            "/app/books" if (_IS_CONTAINER and Path("/app/books").exists()) else "/Users/raybayly/Development/Projects/Author/Books"
        )
    )

    # OneDrive Books & Author paths
    ONEDRIVE_BOOKS_PATH: Path = Path(
        os.getenv(
            "ONEDRIVE_BOOKS_PATH",
            "/app/onedrive/Books" if (_IS_CONTAINER and Path("/app/onedrive/Books").exists()) else "/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/Books"
        )
    )
    ONEDRIVE_AUTHOR_PATH: Path = Path(
        os.getenv(
            "ONEDRIVE_AUTHOR_PATH",
            "/app/onedrive/Author" if (_IS_CONTAINER and Path("/app/onedrive/Author").exists()) else "/Users/raybayly/Library/CloudStorage/OneDrive-BaylyAI(2)/Author"
        )
    )

    # Hath0r Knowledgebase Target
    HATHOR_KNOWLEDGEBASE_DIR: Path = Path(
        os.getenv(
            "HATHOR_KNOWLEDGEBASE_DIR",
            str(Path.home() / ".hath0r" / "knowledgebase"),
        )
    )
    HATHOR_SYNC_ENABLED: bool = os.getenv("HATHOR_SYNC_ENABLED", "true").lower() in ("true", "1", "yes")


settings = Settings()
