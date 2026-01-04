"""Configuration management for the application"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Application configuration"""

    # Neo4j settings
    neo4j_uri: str = Field(default_factory=lambda: os.getenv("NEO4J_URI"))
    neo4j_user: str = Field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = Field(
        default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password")
    )

    # Application settings
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    data_dir: str = Field(default_factory=lambda: os.getenv("DATA_DIR", "./data"))
    output_dir: str = Field(
        default_factory=lambda: os.getenv("OUTPUT_DIR", "./data/output")
    )

    # XMI Processing settings
    xmi_source_url: str = Field(
        default_factory=lambda: os.getenv(
            "XMI_SOURCE_URL", "https://standards.iso.org/iso/10303/smrl/v12/tech/"
        )
    )
    batch_size: int = Field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "100")))

    class Config:
        """Pydantic configuration"""

        env_file = ".env"
        env_file_encoding = "utf-8"
