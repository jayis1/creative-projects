"""Configuration file support for the BPE tokenizer.

Supports loading training and encoding configurations from JSON and
TOML files, making it easy to reproduce tokenization setups without
long command-line flags.

Example JSON config::

    {
        "training": {
            "vocab_size": 32000,
            "byte_mode": false,
            "pretokenizer": "gpt4",
            "min_frequency": 2,
            "normalizer": ["lowercase", "nfc"]
        },
        "encoding": {
            "add_bos": true,
            "add_eos": true,
            "max_length": 512,
            "truncation": "right",
            "padding": true
        }
    }

Example TOML config (Python 3.11+)::

    [training]
    vocab_size = 32000
    byte_mode = false
    pretokenizer = "gpt4"
    min_frequency = 2
    normalizer = ["lowercase"]

    [encoding]
    add_bos = true
    add_eos = true
    max_length = 512
    truncation = "right"
    padding = true
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .exceptions import ConfigError
from .normalizer import Normalization
from .tokenizer import TrainingConfig

__all__ = [
    "TokenizerConfig",
    "load_config",
    "save_config",
    "parse_normalizer_flags",
]


def parse_normalizer_flags(flags: Any) -> int:
    """Parse normalizer flags from various representations.

    Accepts:
        - int (raw bitmask)
        - list of str (e.g., ``["lowercase", "nfc"]``)
        - str (e.g., ``"lowercase|nfc"`` or ``"lowercase"``)
    """
    if isinstance(flags, int):
        return flags
    if isinstance(flags, str):
        names = [n.strip().upper() for n in flags.split("|")]
        result = Normalization.NONE
        for name in names:
            try:
                result |= Normalization[name]
            except KeyError:
                raise ConfigError(f"Unknown normalization flag: {name!r}")
        return int(result.value)
    if isinstance(flags, list):
        result = Normalization.NONE
        for name in flags:
            key = str(name).strip().upper()
            try:
                result |= Normalization[key]
            except KeyError:
                raise ConfigError(f"Unknown normalization flag: {key!r}")
        return int(result.value)
    if flags is None:
        return 0
    raise ConfigError(f"Cannot parse normalizer flags from {type(flags).__name__}")


class TokenizerConfig:
    """Full tokenizer configuration (training + encoding).

    Loads from JSON or TOML files, validates values, and produces
    :class:`TrainingConfig` instances.
    """

    def __init__(
        self,
        training: Mapping[str, Any] | None = None,
        encoding: Mapping[str, Any] | None = None,
    ):
        self.training: dict[str, Any] = dict(training or {})
        self.encoding: dict[str, Any] = dict(encoding or {})

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "TokenizerConfig":
        """Build a config from a parsed dict (JSON/TOML)."""
        return cls(
            training=d.get("training", {}),
            encoding=d.get("encoding", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (suitable for JSON)."""
        return {
            "training": dict(self.training),
            "encoding": dict(self.encoding),
        }

    @classmethod
    def load(cls, path: str | Path) -> "TokenizerConfig":
        """Load a config from a JSON or TOML file.

        The file format is determined by the extension:
        ``.json`` → JSON, ``.toml`` → TOML (Python 3.11+).
        """
        path = Path(path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".toml":
            try:
                import tomllib  # Python 3.11+
            except ImportError:
                raise ConfigError(
                    "TOML config requires Python 3.11+ (tomllib module)"
                )
            data = tomllib.loads(text)
        elif path.suffix in (".json", ".jsonc"):
            data = json.loads(text)
        else:
            # Try JSON as fallback.
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                raise ConfigError(
                    f"Unsupported config format: {path.suffix}. "
                    "Use .json or .toml"
                )
        return cls.from_dict(data)

    def save(self, path: str | Path) -> None:
        """Save the config to a JSON file."""
        path = Path(path)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def to_training_config(self) -> TrainingConfig:
        """Convert the training section to a :class:`TrainingConfig`."""
        t = self.training
        normalizer_flags = parse_normalizer_flags(t.get("normalizer", t.get("normalizer_flags", 0)))
        # Handle specials as a list or tuple.
        specials = t.get("specials")
        if isinstance(specials, list):
            specials = tuple(specials)
        kwargs: dict[str, Any] = {
            "vocab_size": t.get("vocab_size", 1000),
            "byte_mode": t.get("byte_mode", False),
            "pretokenizer": t.get("pretokenizer", t.get("pre_tokenizer", "gpt4")),
            "min_frequency": t.get("min_frequency", 2),
            "verbose": t.get("verbose", False),
            "normalizer_flags": normalizer_flags,
        }
        if specials is not None:
            kwargs["specials"] = specials
        try:
            return TrainingConfig(**kwargs)
        except (ValueError, TypeError) as e:
            raise ConfigError(f"Invalid training config: {e}") from e

    def encoding_kwargs(self) -> dict[str, Any]:
        """Return kwargs for ``encode_advanced`` from the encoding section."""
        e = self.encoding
        kwargs: dict[str, Any] = {}
        if "add_bos" in e:
            kwargs["add_bos"] = bool(e["add_bos"])
        if "add_eos" in e:
            kwargs["add_eos"] = bool(e["add_eos"])
        if "max_length" in e:
            kwargs["max_length"] = int(e["max_length"])
        if "truncation" in e:
            kwargs["truncation"] = str(e["truncation"])
        if "return_attention_mask" in e:
            kwargs["return_attention_mask"] = bool(e["return_attention_mask"])
        if "pad_id" in e:
            kwargs["pad_id"] = int(e["pad_id"])
        return kwargs


def load_config(path: str | Path) -> TokenizerConfig:
    """Convenience function to load a :class:`TokenizerConfig`."""
    return TokenizerConfig.load(path)


def save_config(config: TokenizerConfig, path: str | Path) -> None:
    """Convenience function to save a :class:`TokenizerConfig`."""
    config.save(path)