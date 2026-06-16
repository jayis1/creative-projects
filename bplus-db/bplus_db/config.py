"""Configuration management for the B+ Tree Database.

Supports loading from TOML files (Python ≥ 3.11 ``tomllib``), JSON files,
or pure Python dicts.  Every setting has a sensible default so the user only
needs to override what they want to change.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

# Python 3.11+ has tomllib; fall back to a no-op loader
try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]


@dataclass
class TreeConfig:
    """B+ tree structural settings."""
    order: int = 64  # Branching factor


@dataclass
class CacheConfig:
    """Read-cache settings."""
    enabled: bool = False
    max_size: int = 256  # Number of entries when enabled


@dataclass
class WALConfig:
    """Write-ahead-log settings."""
    enabled: bool = False
    path: Optional[str] = None


@dataclass
class PersistenceConfig:
    """Default persistence paths."""
    json_path: Optional[str] = None
    binary_path: Optional[str] = None
    auto_save: bool = False          # Auto-save on every write (expensive)
    auto_save_interval: int = 0      # Auto-save every N writes (0 = disabled)


@dataclass
class LoggingConfig:
    """Logging settings."""
    level: str = "WARNING"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


@dataclass
class DatabaseConfig:
    """Top-level configuration for a ``Database`` instance."""
    tree: TreeConfig = field(default_factory=TreeConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    wal: WALConfig = field(default_factory=WALConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # ── loaders ──────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DatabaseConfig":
        """Build a config from a nested dict (e.g. parsed JSON/TOML)."""
        tree = TreeConfig(**d.get("tree", {}))
        cache = CacheConfig(**d.get("cache", {}))
        wal_kwargs = d.get("wal", {})
        # Map bare ``path`` to ``path``; allow ``enabled`` inference
        if "enabled" not in wal_kwargs and "path" in wal_kwargs and wal_kwargs["path"]:
            wal_kwargs.setdefault("enabled", True)
        wal = WALConfig(**wal_kwargs)
        persistence = PersistenceConfig(**d.get("persistence", {}))
        logging = LoggingConfig(**d.get("logging", {}))
        return cls(tree=tree, cache=cache, wal=wal, persistence=persistence, logging=logging)

    @classmethod
    def from_json(cls, path: str) -> "DatabaseConfig":
        """Load config from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_toml(cls, path: str) -> "DatabaseConfig":
        """Load config from a TOML file.

        Requires Python ≥ 3.11 (``tomllib``).  Falls back to JSON if
        ``tomllib`` is unavailable.
        """
        if tomllib is None:
            raise RuntimeError(
                "TOML support requires Python ≥ 3.11 (tomllib). "
                "Use DatabaseConfig.from_json() instead."
            )
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: str) -> "DatabaseConfig":
        """Auto-detect config format from file extension."""
        ext = os.path.splitext(path)[1].lower()
        if ext == ".json":
            return cls.from_json(path)
        elif ext in (".toml", ".conf"):
            return cls.from_toml(path)
        else:
            raise ValueError(f"Unsupported config file extension: {ext!r}")

    # ── serialization ─────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dict suitable for JSON/TOML output."""
        return asdict(self)

    def to_json(self, path: str, indent: int = 2) -> None:
        """Write config to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=indent)