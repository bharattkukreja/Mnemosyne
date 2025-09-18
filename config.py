"""Configuration management for Mnemosyne"""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class MCPConfig:
    name: str
    version: str


@dataclass
class StorageConfig:
    vector_db: str
    vector_db_path: str
    graph_db: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str


@dataclass
class EmbeddingsConfig:
    model: str
    dimension: int


@dataclass
class ContextConfig:
    max_injection_tokens: int
    relevance_threshold: float
    max_memories_per_query: int


@dataclass
class LoggingConfig:
    level: str
    path: str


@dataclass
class Config:
    mcp: MCPConfig
    storage: StorageConfig
    embeddings: EmbeddingsConfig
    context: ContextConfig
    logging: LoggingConfig


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file"""

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    # Expand paths with ~ to home directory
    storage_data = config_data["storage"].copy()
    storage_data["vector_db_path"] = os.path.expanduser(storage_data["vector_db_path"])

    logging_data = config_data["logging"].copy()
    logging_data["path"] = os.path.expanduser(logging_data["path"])

    return Config(
        mcp=MCPConfig(**config_data["mcp"]),
        storage=StorageConfig(**storage_data),
        embeddings=EmbeddingsConfig(**config_data["embeddings"]),
        context=ContextConfig(**config_data["context"]),
        logging=LoggingConfig(**logging_data),
    )


def ensure_directories(config: Config) -> None:
    """Create necessary directories if they don't exist"""

    directories = [os.path.dirname(config.storage.vector_db_path), config.logging.path]

    for directory in directories:
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
