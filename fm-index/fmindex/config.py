"""Configuration support for FM-Index.

Loads index configuration from YAML, JSON, or TOML files.  Falls back
to JSON if PyYAML is not installed (so the package remains dependency-free).

Example YAML config (``config.yaml``)::

    sample_rate: 16
    use_naive_sa: false
    backend: wavelet_tree      # or wavelet_matrix
    query_defaults:
        max_mismatches: 1
        context: 10
    serialization:
        format: binary          # binary | json | pickle
        compress_level: 9
    logging:
        level: INFO
        file: fmindex.log

Example JSON config (``config.json``)::

    {
        "sample_rate": 32,
        "backend": "wavelet_matrix",
        "query_defaults": {"context": 20}
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .errors import ConfigError


@dataclass
class QueryDefaults:
    """Default values for query parameters."""

    max_mismatches: int = 1
    context: int = 10
    wildcard_char: str = "?"
    kmer_k: int = 5


@dataclass
class SerializationConfig:
    """Serialization settings."""

    format: str = "binary"  # binary | json | pickle
    compress_level: int = 6


@dataclass
class LoggingConfig:
    """Logging settings."""

    level: str = "INFO"
    file: Optional[str] = None


@dataclass
class FMIndexConfig:
    """Top-level configuration for FM-Index construction and queries.

    Parameters
    ----------
    sample_rate:
        Suffix-array sample rate (smaller = more memory, faster locate).
    use_naive_sa:
        Use the naive O(n² log n) SA construction (testing only).
    backend:
        ``"wavelet_tree"`` or ``"wavelet_matrix"``.
    query_defaults:
        Default query parameters.
    serialization:
        Serialization format & compression.
    logging:
        Logging configuration.
    """

    sample_rate: int = 16
    use_naive_sa: bool = False
    backend: str = "wavelet_tree"
    query_defaults: QueryDefaults = field(default_factory=QueryDefaults)
    serialization: SerializationConfig = field(default_factory=SerializationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    VALID_BACKENDS = ("wavelet_tree", "wavelet_matrix")
    VALID_SERIALIZATION = ("binary", "json", "pickle")

    def validate(self) -> None:
        """Validate the configuration; raise :class:`ConfigError` on issues."""
        if self.sample_rate < 1:
            raise ConfigError(f"sample_rate must be >= 1, got {self.sample_rate}")
        if self.backend not in self.VALID_BACKENDS:
            raise ConfigError(
                f"backend must be one of {self.VALID_BACKENDS}, got {self.backend!r}"
            )
        if self.serialization.format not in self.VALID_SERIALIZATION:
            raise ConfigError(
                f"serialization.format must be one of {self.VALID_SERIALIZATION}, "
                f"got {self.serialization.format!r}"
            )
        if self.serialization.compress_level < 0 or self.serialization.compress_level > 9:
            raise ConfigError(
                f"compress_level must be 0-9, got {self.serialization.compress_level}"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FMIndexConfig":
        """Build a config from a plain dict (e.g. loaded from JSON)."""
        cfg = cls()
        if "sample_rate" in data:
            cfg.sample_rate = int(data["sample_rate"])
        if "use_naive_sa" in data:
            cfg.use_naive_sa = bool(data["use_naive_sa"])
        if "backend" in data:
            cfg.backend = str(data["backend"])
        if "query_defaults" in data:
            qd = data["query_defaults"]
            cfg.query_defaults = QueryDefaults(
                max_mismatches=int(qd.get("max_mismatches", 1)),
                context=int(qd.get("context", 10)),
                wildcard_char=str(qd.get("wildcard_char", "?")),
                kmer_k=int(qd.get("kmer_k", 5)),
            )
        if "serialization" in data:
            s = data["serialization"]
            cfg.serialization = SerializationConfig(
                format=str(s.get("format", "binary")),
                compress_level=int(s.get("compress_level", 6)),
            )
        if "logging" in data:
            lg = data["logging"]
            cfg.logging = LoggingConfig(
                level=str(lg.get("level", "INFO")),
                file=lg.get("file"),
            )
        cfg.validate()
        return cfg

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the config to a plain dict (JSON-compatible)."""
        return {
            "sample_rate": self.sample_rate,
            "use_naive_sa": self.use_naive_sa,
            "backend": self.backend,
            "query_defaults": {
                "max_mismatches": self.query_defaults.max_mismatches,
                "context": self.query_defaults.context,
                "wildcard_char": self.query_defaults.wildcard_char,
                "kmer_k": self.query_defaults.kmer_k,
            },
            "serialization": {
                "format": self.serialization.format,
                "compress_level": self.serialization.compress_level,
            },
            "logging": {
                "level": self.logging.level,
                "file": self.logging.file,
            },
        }


def load_config(path: str) -> FMIndexConfig:
    """Load an :class:`FMIndexConfig` from a file.

    Format is auto-detected by extension:
      - ``.json`` → JSON
      - ``.yaml`` / ``.yml`` → YAML (falls back to JSON if PyYAML missing)
      - ``.toml`` → TOML (Python 3.11+ ``tomllib``)
      - otherwise → JSON
    """
    if not os.path.isfile(path):
        raise ConfigError(f"config file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            # fall back to JSON parsing
            data = json.loads(raw)
        else:
            data = yaml.safe_load(raw) or {}
    elif ext == ".toml":
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            raise ConfigError("TOML support requires Python 3.11+")
        data = tomllib.loads(raw)
    else:
        data = json.loads(raw)
    if not isinstance(data, dict):
        raise ConfigError(f"config root must be a mapping, got {type(data).__name__}")
    return FMIndexConfig.from_dict(data)


def save_config(cfg: FMIndexConfig, path: str) -> None:
    """Save a config to a file (JSON or YAML by extension)."""
    ext = os.path.splitext(path)[1].lower()
    data = cfg.to_dict()
    if ext in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        else:
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)