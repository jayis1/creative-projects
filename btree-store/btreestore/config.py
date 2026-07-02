"""
Configuration management for btreestore.

Supports loading configuration from JSON, TOML, or Python dict,
with sensible defaults and validation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


@dataclass
class StoreConfig:
    """Configuration for a Store instance.

    Attributes:
        path: Path to the database file.
        page_size: Size of each page in bytes (includes 4-byte CRC).
        branching: Target maximum children per internal node.
        cache_size: Maximum number of pages kept in the LRU cache.
        wal_enabled: Whether to enable the Write-Ahead Log for crash recovery.
        wal_path: Path to the WAL file. If None, uses <db_path>.wal.
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
        log_file: Path to log file. If None, logs to stderr.
        auto_checkpoint: Whether to automatically checkpoint the WAL on commit.
        checkpoint_interval: Number of commits between automatic checkpoints.
        sync_on_commit: Whether to fsync the file on each commit (durability).
    """

    path: str = ""
    page_size: int = 4096
    branching: int = 32
    cache_size: int = 512
    wal_enabled: bool = True
    wal_path: Optional[str] = None
    log_level: str = "INFO"
    log_file: Optional[str] = None
    auto_checkpoint: bool = True
    checkpoint_interval: int = 100
    sync_on_commit: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate configuration values. Raises ValueError on invalid config."""
        if self.page_size < 256:
            raise ValueError(f"page_size must be >= 256, got {self.page_size}")
        if self.page_size > 65536:
            raise ValueError(f"page_size must be <= 65536, got {self.page_size}")
        if self.branching < 4:
            raise ValueError(f"branching must be >= 4, got {self.branching}")
        if self.cache_size < 8:
            raise ValueError(f"cache_size must be >= 8, got {self.cache_size}")
        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"Invalid log_level: {self.log_level}")
        if self.checkpoint_interval < 1:
            raise ValueError(
                f"checkpoint_interval must be >= 1, got {self.checkpoint_interval}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to a dictionary."""
        return {
            "path": self.path,
            "page_size": self.page_size,
            "branching": self.branching,
            "cache_size": self.cache_size,
            "wal_enabled": self.wal_enabled,
            "wal_path": self.wal_path,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "auto_checkpoint": self.auto_checkpoint,
            "checkpoint_interval": self.checkpoint_interval,
            "sync_on_commit": self.sync_on_commit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoreConfig":
        """Create a config from a dictionary, ignoring unknown keys."""
        known_fields = {
            "path", "page_size", "branching", "cache_size",
            "wal_enabled", "wal_path", "log_level", "log_file",
            "auto_checkpoint", "checkpoint_interval", "sync_on_commit",
        }
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "StoreConfig":
        """Load configuration from a JSON or TOML file.

        The file extension determines the format (.json, .toml, or .tml).
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        suffix = path.suffix.lower()
        content = path.read_bytes()

        if suffix == ".json":
            data = json.loads(content)
        elif suffix in (".toml", ".tml"):
            if tomllib is None:
                raise ImportError(
                    "TOML support requires Python 3.11+ or the 'tomli' package"
                )
            data = tomllib.loads(content.decode("utf-8"))
        else:
            # Try JSON first, then TOML
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                if tomllib is not None:
                    data = tomllib.loads(content.decode("utf-8"))
                else:
                    raise ValueError(
                        f"Unknown config format: {suffix}. "
                        "Use .json or .toml"
                    )

        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a dict/object, got {type(data)}")

        return cls.from_dict(data)

    @classmethod
    def from_env(cls, prefix: str = "BTREESTORE_") -> "StoreConfig":
        """Load configuration from environment variables.

        Example env vars:
            BTREESTORE_PAGE_SIZE=8192
            BTREESTORE_CACHE_SIZE=1024
            BTREESTORE_LOG_LEVEL=DEBUG
        """
        env_map = {
            "PAGE_SIZE": ("page_size", int),
            "BRANCHING": ("branching", int),
            "CACHE_SIZE": ("cache_size", int),
            "WAL_ENABLED": ("wal_enabled", lambda x: x.lower() in ("true", "1", "yes")),
            "WAL_PATH": ("wal_path", str),
            "LOG_LEVEL": ("log_level", str),
            "LOG_FILE": ("log_file", str),
            "AUTO_CHECKPOINT": ("auto_checkpoint", lambda x: x.lower() in ("true", "1", "yes")),
            "CHECKPOINT_INTERVAL": ("checkpoint_interval", int),
            "SYNC_ON_COMMIT": ("sync_on_commit", lambda x: x.lower() in ("true", "1", "yes")),
        }
        data: Dict[str, Any] = {}
        for env_suffix, (field_name, converter) in env_map.items():
            env_key = f"{prefix}{env_suffix}"
            if env_key in os.environ:
                try:
                    data[field_name] = converter(os.environ[env_key])
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid value for {env_key}: {e}")
        return cls(**data)

    def save(self, path: Union[str, Path]) -> None:
        """Save config to a JSON file."""
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2))