"""Configuration system for the Reed-Solomon codec.

Supports JSON, YAML, and TOML configuration files for codec parameters,
CLI defaults, and logging configuration.

Example JSON config::

    {
        "nsym": 16,
        "interleaving_depth": 4,
        "log_level": "INFO",
        "log_file": null
    }
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

# YAML is optional — only available if PyYAML is installed.
try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:  # pragma: no cover
    _HAS_YAML = False

# tomllib is stdlib in Python 3.11+; fall back to ``tomli`` if available.
try:
    import tomllib  # type: ignore
    _HAS_TOML = True
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore  # noqa: F401
        _HAS_TOML = True
    except ImportError:  # pragma: no cover
        _HAS_TOML = False


@dataclass
class CodecConfig:
    """Configuration for the Reed-Solomon codec.

    Attributes:
        nsym: Number of parity symbols (default 10).
        interleaving_depth: Default interleaving depth for burst-error mode (default 4).
        log_level: Logging level name (default "WARNING").
        log_file: Optional log file path. If None, logs go to stderr.
        log_format: Logging format string.
    """
    nsym: int = 10
    interleaving_depth: int = 4
    log_level: str = "WARNING"
    log_file: Optional[str] = None
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If any value is invalid.
        """
        if not isinstance(self.nsym, int) or self.nsym < 0 or self.nsym > 254:
            raise ValueError(f"nsym must be 0..254, got {self.nsym}")
        if not isinstance(self.interleaving_depth, int) or self.interleaving_depth < 1:
            raise ValueError(
                f"interleaving_depth must be >= 1, got {self.interleaving_depth}"
            )
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(
                f"log_level must be one of {valid_levels}, got {self.log_level}"
            )

    def setup_logging(self) -> None:
        """Configure the root logger based on this config."""
        level = getattr(logging, self.log_level.upper(), logging.WARNING)
        handlers: list[logging.Handler] = []
        if self.log_file:
            handlers.append(logging.FileHandler(self.log_file))
        else:
            handlers.append(logging.StreamHandler())
        logging.basicConfig(
            level=level,
            format=self.log_format,
            handlers=handlers,
            force=True,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return config as a dictionary."""
        return {
            "nsym": self.nsym,
            "interleaving_depth": self.interleaving_depth,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "log_format": self.log_format,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodecConfig":
        """Create config from a dictionary, ignoring unknown keys."""
        known = {f.name for f in fields(cls) if f.init}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def to_json(self) -> str:
        """Serialise config to a JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "CodecConfig":
        """Deserialise config from a JSON string."""
        return cls.from_dict(json.loads(text))

    def to_yaml(self) -> str:
        """Serialise config to a YAML string.

        Raises:
            RuntimeError: If PyYAML is not installed.
        """
        if not _HAS_YAML:
            raise RuntimeError("PyYAML is required for YAML support (pip install pyyaml)")
        return yaml.dump(self.to_dict(), default_flow_style=False)

    @classmethod
    def from_yaml(cls, text: str) -> "CodecConfig":
        """Deserialise config from a YAML string.

        Raises:
            RuntimeError: If PyYAML is not installed.
        """
        if not _HAS_YAML:
            raise RuntimeError("PyYAML is required for YAML support (pip install pyyaml)")
        return cls.from_dict(yaml.safe_load(text))

    def to_toml(self) -> str:
        """Serialise config to a TOML string."""
        d = self.to_dict()
        lines = []
        for key, val in d.items():
            if isinstance(val, str):
                lines.append(f'{key} = "{val}"')
            elif val is None:
                continue
            else:
                lines.append(f"{key} = {val}")
        return "\n".join(lines) + "\n"

    @classmethod
    def from_toml(cls, text: str) -> "CodecConfig":
        """Deserialise config from a TOML string.

        Raises:
            RuntimeError: If no TOML parser is available.
        """
        if not _HAS_TOML:
            raise RuntimeError("TOML support requires Python 3.11+ or the 'tomli' package")
        return cls.from_dict(tomllib.loads(text))

    def save(self, path: Union[str, Path]) -> None:
        """Save config to a file, auto-detecting format from extension.

        Supports ``.json``, ``.yaml``/``.yml``, and ``.toml``.
        """
        path = Path(path)
        ext = path.suffix.lower()
        text = self._serialise_for_ext(ext)
        path.write_text(text)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "CodecConfig":
        """Load config from a file, auto-detecting format from extension.

        Supports ``.json``, ``.yaml``/``.yml``, and ``.toml``.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        text = path.read_text()
        ext = path.suffix.lower()
        return cls._deserialise_for_ext(ext, text)

    # -- internal helpers --

    def _serialise_for_ext(self, ext: str) -> str:
        if ext == ".json":
            return self.to_json()
        elif ext in (".yaml", ".yml"):
            return self.to_yaml()
        elif ext == ".toml":
            return self.to_toml()
        else:
            raise ValueError(f"Unsupported config format: {ext!r} (use .json/.yaml/.toml)")

    @classmethod
    def _deserialise_for_ext(cls, ext: str, text: str) -> "CodecConfig":
        if ext == ".json":
            return cls.from_json(text)
        elif ext in (".yaml", ".yml"):
            return cls.from_yaml(text)
        elif ext == ".toml":
            return cls.from_toml(text)
        else:
            raise ValueError(f"Unsupported config format: {ext!r} (use .json/.yaml/.toml)")


# ``fields`` is used by ``from_dict``; import here to avoid circular deps.
from dataclasses import fields  # noqa: E402


def load_config(path: Union[str, Path]) -> CodecConfig:
    """Convenience function to load a :class:`CodecConfig` from a file."""
    return CodecConfig.load(path)