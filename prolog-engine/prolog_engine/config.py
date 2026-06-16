"""Configuration management for the mini-Prolog engine.

Supports loading engine settings from YAML, JSON, or TOML config files,
with sensible defaults that can be overridden programmatically.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)

# Try to import YAML (optional dependency)
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Try to import TOML (available in Python 3.11+)
try:
    import tomllib
    HAS_TOML = True
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
        HAS_TOML = True
    except ImportError:
        HAS_TOML = False


@dataclass
class EngineConfig:
    """Configuration for the Prolog inference engine.

    Attributes:
        max_depth: Maximum inference depth to prevent infinite loops.
        max_solutions: Maximum number of solutions before raising an error.
        trace: Enable trace mode for debugging.
        occurs_check: Enable occurs-check in unification (always on for safety).
        float_precision: Number of decimal places for float comparison.
        repl_history_file: Path to readline history file (None to disable).
        repl_prompt: Primary REPL prompt string.
        repl_continue_prompt: Prompt for continuation lines.
    """

    max_depth: int = 1000
    max_solutions: int = 10000
    trace: bool = False
    occurs_check: bool = True
    float_precision: int = 10
    repl_history_file: Optional[str] = "~/.prolog_engine_history"
    repl_prompt: str = "?- "
    repl_continue_prompt: str = "   "

    def apply_to_engine(self, engine: "Engine") -> None:
        """Apply this configuration to an Engine instance."""
        engine._max_depth = self.max_depth
        engine._max_solutions = self.max_solutions
        engine._trace = self.trace

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EngineConfig":
        """Create config from a dictionary, ignoring unknown keys."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_file(cls, filepath: str) -> "EngineConfig":
        """Load configuration from a file.

        Supports YAML (.yml/.yaml), JSON (.json), and TOML (.toml) formats.
        """
        ext = os.path.splitext(filepath)[1].lower()

        with open(filepath, "r") as f:
            content = f.read()

        if ext in (".yml", ".yaml"):
            if not HAS_YAML:
                raise ImportError(
                    "PyYAML is required to load YAML config files. "
                    "Install it with: pip install pyyaml"
                )
            data = yaml.safe_load(content)
        elif ext == ".json":
            data = json.loads(content)
        elif ext == ".toml":
            if not HAS_TOML:
                raise ImportError(
                    "TOML support requires Python 3.11+ or the tomli package. "
                    "Install it with: pip install tomli"
                )
            data = tomllib.loads(content)
        else:
            raise ValueError(
                f"Unsupported config file format: {ext}. "
                f"Supported formats: .yml, .yaml, .json, .toml"
            )

        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a mapping, got {type(data).__name__}")

        logger.info("Loaded configuration from %s", filepath)
        return cls.from_dict(data)

    def save(self, filepath: str) -> None:
        """Save configuration to a file."""
        ext = os.path.splitext(filepath)[1].lower()
        data = self.to_dict()

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        with open(filepath, "w") as f:
            if ext in (".yml", ".yaml"):
                if not HAS_YAML:
                    raise ImportError("PyYAML is required to save YAML config files.")
                yaml.dump(data, f, default_flow_style=False)
            elif ext == ".json":
                json.dump(data, f, indent=2)
            elif ext == ".toml":
                # TOML doesn't support None, filter those out
                filtered = {k: v for k, v in data.items() if v is not None}
                # Python 3.11+ has tomllib for reading only; use manual write
                lines = []
                for k, v in filtered.items():
                    if isinstance(v, str):
                        lines.append(f'{k} = "{v}"')
                    elif isinstance(v, bool):
                        lines.append(f'{k} = {"true" if v else "false"}')
                    elif isinstance(v, int):
                        lines.append(f'{k} = {v}')
                f.write("\n".join(lines) + "\n")
            else:
                raise ValueError(f"Unsupported config format: {ext}")

        logger.info("Saved configuration to %s", filepath)


# Default config file names to search for
DEFAULT_CONFIG_NAMES = [
    ".prolog-engine.yml",
    ".prolog-engine.yaml",
    ".prolog-engine.json",
    ".prolog-engine.toml",
    "prolog-engine.yml",
    "prolog-engine.yaml",
    "prolog-engine.json",
    "prolog-engine.toml",
]


def find_config(start_dir: Optional[str] = None) -> Optional[str]:
    """Search for a config file in the given directory and its parents.

    Args:
        start_dir: Directory to start searching from. Defaults to cwd.

    Returns:
        Path to the first config file found, or None.
    """
    if start_dir is None:
        start_dir = os.getcwd()

    current = os.path.abspath(start_dir)
    while True:
        for name in DEFAULT_CONFIG_NAMES:
            path = os.path.join(current, name)
            if os.path.isfile(path):
                return path
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def load_config(config_path: Optional[str] = None) -> EngineConfig:
    """Load configuration from a file, searching for defaults if needed.

    Args:
        config_path: Explicit path to config file. If None, searches
            for default config files.

    Returns:
        An EngineConfig instance.
    """
    if config_path:
        return EngineConfig.from_file(config_path)

    found = find_config()
    if found:
        return EngineConfig.from_file(found)

    return EngineConfig()