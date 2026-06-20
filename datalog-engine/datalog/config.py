"""Configuration file support for the Datalog engine.

Supports loading engine configuration from JSON, TOML, or YAML files.

Example JSON config (``datalog.json``)::

    {
        "files": ["examples/company.dl"],
        "queries": ["well_paid(X)"],
        "log_level": "INFO",
        "max_iterations": 10000,
        "output_format": "table"
    }

Example TOML config (``datalog.toml``)::

    files = ["examples/company.dl"]
    queries = ["well_paid(X)"]
    log_level = "INFO"
    max_iterations = 10000
    output_format = "table"

Example YAML config (``datalog.yaml``)::

    files:
      - examples/company.dl
    queries:
      - well_paid(X)
    log_level: INFO
    max_iterations: 10000
    output_format: table
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .errors import ConfigurationError


@dataclass
class EngineConfig:
    """Configuration for the Datalog engine and CLI.

    Attributes
    ----------
    files : list of str
        Datalog source files to load.
    queries : list of str
        Queries to run after loading files.
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR).
    max_iterations : int
        Maximum semi-naive iterations before giving up (safety limit).
    output_format : str
        Output format for query results: 'binding', 'table', 'json', 'csv'.
    show_predicates : bool
        List all predicates after loading.
    explain_predicates : list of str
        Predicates to explain after loading.
    export_file : Optional[str]
        File to export state to.
    """

    files: List[str] = field(default_factory=list)
    queries: List[str] = field(default_factory=list)
    log_level: str = "WARNING"
    max_iterations: int = 100000
    output_format: str = "binding"
    show_predicates: bool = False
    explain_predicates: List[str] = field(default_factory=list)
    export_file: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EngineConfig":
        """Create a config from a dictionary, ignoring unknown keys."""
        known = {
            k: v
            for k, v in data.items()
            if k in cls.__dataclass_fields__  # type: ignore[attr-defined]
        }
        return cls(**known)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to a dictionary."""
        from dataclasses import asdict
        return asdict(self)


def load_config(path: str) -> EngineConfig:
    """Load an engine configuration from a file.

    The file format is detected by the extension:
    ``.json`` → JSON, ``.toml`` → TOML, ``.yaml``/``.yml`` → YAML.

    Parameters
    ----------
    path : str
        Path to the configuration file.

    Returns
    -------
    EngineConfig
        The parsed configuration.

    Raises
    ------
    ConfigurationError
        If the file format is unsupported or the content is invalid.
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        with open(path, "r") as f:
            content = f.read()
    except OSError as e:
        raise ConfigurationError(f"cannot read config file {path!r}: {e}") from e

    if ext == ".json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"invalid JSON in {path!r}: {e}") from e
    elif ext == ".toml":
        try:
            import tomllib
        except ImportError as e:
            raise ConfigurationError(
                "TOML support requires Python 3.11+ (tomllib)"
            ) from e
        try:
            data = tomllib.loads(content)
        except Exception as e:
            raise ConfigurationError(f"invalid TOML in {path!r}: {e}") from e
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise ConfigurationError(
                "YAML support requires PyYAML: pip install pyyaml"
            ) from e
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"invalid YAML in {path!r}: {e}") from e
    else:
        raise ConfigurationError(
            f"unsupported config format {ext!r}; use .json, .toml, or .yaml"
        )

    if not isinstance(data, dict):
        raise ConfigurationError(
            f"config root must be an object/dict, got {type(data).__name__}"
        )
    return EngineConfig.from_dict(data)