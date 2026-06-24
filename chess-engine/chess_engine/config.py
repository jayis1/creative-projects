"""Configuration support for the chess engine.

Loads engine settings from a YAML or JSON config file, with sensible defaults.
This lets users tweak search parameters, evaluation weights, and engine
behaviour without editing source code.

Example YAML config::

    search:
      max_depth: 6
      time_limit: 5.0
      use_quiescence: true
      use_killers: true
      use_history: true
      use_lmr: true
      use_null_move: true
      use_iterative_deepening: true
      use_tt: true

    evaluation:
      tempo_bonus: 10

    opening_book:
      enabled: true
      file: null   # use built-in book

    logging:
      level: INFO
      file: null   # stderr by default
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "search": {
        "max_depth": 4,
        "time_limit": None,
        "use_quiescence": True,
        "use_killers": True,
        "use_history": True,
        "use_lmr": True,
        "use_null_move": True,
        "use_iterative_deepening": True,
        "use_tt": True,
    },
    "evaluation": {
        "tempo_bonus": 10,
    },
    "opening_book": {
        "enabled": True,
        "file": None,
    },
    "logging": {
        "level": "WARNING",
        "file": None,
    },
}


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *overlay* into *base*, returning a new dict."""
    result = dict(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from a file, falling back to defaults.

    Supports ``.yaml``/``.yml`` (if PyYAML is available) and ``.json``.
    If *path* is ``None`` or the file doesn't exist, returns a copy of
    :data:`DEFAULT_CONFIG`.
    """
    config = _deep_merge(DEFAULT_CONFIG, {})

    if path is None or not os.path.isfile(path):
        return config

    suffix = Path(path).suffix.lower()
    try:
        with open(path, "r") as f:
            raw = f.read()
        if suffix in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore
                data = yaml.safe_load(raw)
            except ImportError:
                logger.warning(
                    "PyYAML not installed; cannot read %s. "
                    "Install with 'pip install pyyaml'. Falling back to defaults.",
                    path,
                )
                return config
        else:
            data = json.loads(raw)

        if data and isinstance(data, dict):
            config = _deep_merge(config, data)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load config from %s: %s", path, exc)

    return config


def apply_search_config(search, cfg: Dict[str, Any]) -> None:
    """Apply search-related configuration to a :class:`Search` instance."""
    s = cfg.get("search", {})
    if "max_depth" in s:
        search.max_depth = int(s["max_depth"])
    if "time_limit" in s and s["time_limit"] is not None:
        search.time_limit = float(s["time_limit"])
    for flag in ("use_quiescence", "use_killers", "use_history",
                 "use_lmr", "use_null_move", "use_iterative_deepening",
                 "use_tt"):
        if flag in s:
            setattr(search, flag, bool(s[flag]))


def setup_logging(cfg: Dict[str, Any]) -> None:
    """Configure the root logger from the config dict."""
    log_cfg = cfg.get("logging", {})
    level_name = str(log_cfg.get("level", "WARNING")).upper()
    level = getattr(logging, level_name, logging.WARNING)
    log_file = log_cfg.get("file")
    handlers: list = []
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    else:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=handlers,
        force=True,
    )