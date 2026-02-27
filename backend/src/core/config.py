"""
Centralised configuration via ``pydantic-settings``.

Every environment variable consumed anywhere in the backend is declared
here **once**.  All other modules import ``get_settings()`` instead of
reading ``os.getenv`` directly.

Usage::

    from src.core.config import get_settings
    s = get_settings()
    print(s.neo4j_uri)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Set

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Single source of truth for every runtime knob."""

    # ── Neo4j ──────────────────────────────────────────────────────────
    neo4j_uri: str = Field(
        description="Bolt URI for the Neo4j instance (required – set NEO4J_URI in .env)",
    )
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(
        description="Neo4j password (required – set NEO4J_PASSWORD in .env)",
    )
    neo4j_database: str = Field(default="neo4j")
    neo4j_max_pool_size: int = Field(default=50)
    neo4j_connection_acquisition_timeout: int = Field(default=30)
    neo4j_max_transaction_retry_time: int = Field(default=15)
    neo4j_connection_timeout: int = Field(default=10)
    neo4j_max_connection_lifetime: int = Field(default=3600)
    neo4j_keep_alive: bool = Field(default=True)
    neo4j_max_retry_attempts: int = Field(default=3)
    neo4j_retry_base_delay: int = Field(default=2)
    neo4j_retry_max_delay: int = Field(default=10)

    # ── Redis ──────────────────────────────────────────────────────────
    redis_enabled: bool = Field(default=False)
    redis_url: Optional[str] = Field(default=None)
    redis_host: Optional[str] = Field(default=None)
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    redis_default_ttl: int = Field(default=3600)
    redis_session_ttl: int = Field(default=86400)

    # ── Security / Auth ────────────────────────────────────────────────
    secret_key: str = Field(default="change-me-in-production")
    token_expiry_hours: int = Field(default=24)
    bcrypt_rounds: int = Field(default=12)
    min_password_length: int = Field(default=8)
    session_timeout: int = Field(default=3600)

    # ── Application ────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    data_dir: str = Field(default="./data")
    output_dir: str = Field(default="./data/output")
    upload_dir: str = Field(default="./data/uploads")
    batch_size: int = Field(default=100)
    xmi_source_url: str = Field(
        default="https://standards.iso.org/iso/10303/smrl/v12/tech/",
    )

    # ── Rate Limiting ──────────────────────────────────────────────────
    search_rpm: int = Field(default=60)
    cypher_rpm: int = Field(default=30)
    upload_rpm: int = Field(default=10)
    default_rpm: int = Field(default=100)

    # ── Upload ─────────────────────────────────────────────────────────
    max_file_size: int = Field(default=50 * 1024 * 1024)  # 50 MB
    allowed_extensions: Set[str] = Field(
        default={".xmi", ".xml", ".csv", ".uml"},
    )

    # ── Cache TTL (seconds) ────────────────────────────────────────────
    cache_ttl_stats: int = Field(default=60)
    cache_ttl_requirements: int = Field(default=300)
    cache_ttl_parts: int = Field(default=300)

    # ── Export ─────────────────────────────────────────────────────────
    max_export_size: int = Field(default=100_000)
    export_chunk_size: int = Field(default=1000)
    export_timeout: int = Field(default=300)

    # ── SMRL ───────────────────────────────────────────────────────────
    smrl_api_version: str = Field(default="v1")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton ``Settings`` instance (cached)."""
    return Settings()


def reset_settings() -> None:
    """Clear the cached settings — mainly useful in tests."""
    get_settings.cache_clear()
