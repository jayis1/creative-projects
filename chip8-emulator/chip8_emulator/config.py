"""CHIP-8 emulator configuration — YAML/JSON/TOML config file support.

Loads emulator settings from config files or sensible defaults.

Supported config file formats:
  - JSON (.json)
  - YAML (.yaml, .yml) — requires PyYAML
  - TOML (.toml) — requires Python 3.11+ or tomli

Example YAML config::

    display:
      width: 64
      height: 32
      on_char: "█"
      off_char: "·"

    keypad:
      mapping:
        1: 0x1
        2: 0x2
        3: 0x3
        4: 0xC
        q: 0x4
        w: 0x5
        e: 0x6
        r: 0xD
        a: 0x7
        s: 0x8
        d: 0x9
        f: 0xE
        z: 0xA
        x: 0x0
        c: 0xB
        v: 0xF

    cpu:
      super_chip: false
      speed: 700
      max_cycles: 0

    logging:
      level: "WARNING"
      file: null
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class DisplayConfig:
    """Display configuration."""

    width: int = 64
    height: int = 32
    on_char: str = "█"
    off_char: str = " "


@dataclass
class KeypadConfig:
    """Keypad configuration."""

    mapping: Dict[str, int] = field(default_factory=lambda: {
        "1": 0x1, "2": 0x2, "3": 0x3, "4": 0xC,
        "q": 0x4, "w": 0x5, "e": 0x6, "r": 0xD,
        "a": 0x7, "s": 0x8, "d": 0x9, "f": 0xE,
        "z": 0xA, "x": 0x0, "c": 0xB, "v": 0xF,
    })


@dataclass
class CpuConfig:
    """CPU configuration."""

    super_chip: bool = False
    speed: int = 700
    max_cycles: int = 0


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "WARNING"
    file: Optional[str] = None


@dataclass
class EmulatorConfig:
    """Complete emulator configuration."""

    display: DisplayConfig = field(default_factory=DisplayConfig)
    keypad: KeypadConfig = field(default_factory=KeypadConfig)
    cpu: CpuConfig = field(default_factory=CpuConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def apply_logging(self) -> None:
        """Configure Python logging based on this config."""
        level = getattr(logging, self.logging.level.upper(), logging.WARNING)
        if self.logging.file:
            logging.basicConfig(filename=self.logging.file, level=level)
        else:
            logging.basicConfig(level=level)


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Load a YAML file (requires PyYAML)."""
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML is required for YAML config files. Install with: pip install pyyaml")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _load_toml(path: Path) -> Dict[str, Any]:
    """Load a TOML file (requires Python 3.11+ or tomli)."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            raise ImportError("TOML support requires Python 3.11+ or the 'tomli' package")
    with open(path, "rb") as f:
        return tomllib.load(f)


def _load_json(path: Path) -> Dict[str, Any]:
    """Load a JSON config file."""
    with open(path) as f:
        return json.load(f)


_LOADERS = {
    ".json": _load_json,
    ".yaml": _load_yaml,
    ".yml": _load_yaml,
    ".toml": _load_toml,
}


def load_config(path: str) -> EmulatorConfig:
    """Load emulator configuration from a file.

    Supported formats: JSON, YAML (with PyYAML), TOML (with tomli).

    Args:
        path: Path to the configuration file.

    Returns:
        EmulatorConfig with loaded settings.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    suffix = p.suffix.lower()
    loader = _LOADERS.get(suffix)
    if loader is None:
        raise ValueError(f"Unsupported config format: {suffix}. Supported: {', '.join(_LOADERS)}")

    data = loader(p)
    return parse_config(data)


def parse_config(data: Dict[str, Any]) -> EmulatorConfig:
    """Parse a config dict into an EmulatorConfig.

    Missing keys use defaults.
    """
    config = EmulatorConfig()

    # Display
    if "display" in data:
        d = data["display"]
        config.display = DisplayConfig(
            width=d.get("width", 64),
            height=d.get("height", 32),
            on_char=d.get("on_char", "█"),
            off_char=d.get("off_char", " "),
        )

    # Keypad
    if "keypad" in data:
        k = data["keypad"]
        if "mapping" in k:
            mapping = {}
            for key, val in k["mapping"].items():
                mapping[str(key).lower()] = int(val, 0) if isinstance(val, str) else int(val)
            config.keypad = KeypadConfig(mapping=mapping)

    # CPU
    if "cpu" in data:
        c = data["cpu"]
        config.cpu = CpuConfig(
            super_chip=c.get("super_chip", False),
            speed=c.get("speed", 700),
            max_cycles=c.get("max_cycles", 0),
        )

    # Logging
    if "logging" in data:
        l = data["logging"]
        config.logging = LoggingConfig(
            level=l.get("level", "WARNING"),
            file=l.get("file"),
        )

    return config


def generate_default_config(format: str = "yaml") -> str:
    """Generate a default configuration file as a string.

    Args:
        format: One of 'yaml', 'json', 'toml'.

    Returns:
        Configuration file content as a string.
    """
    default = EmulatorConfig()

    if format == "json":
        return json.dumps({
            "display": {
                "width": default.display.width,
                "height": default.display.height,
                "on_char": default.display.on_char,
                "off_char": default.display.off_char,
            },
            "keypad": {
                "mapping": default.keypad.mapping,
            },
            "cpu": {
                "super_chip": default.cpu.super_chip,
                "speed": default.cpu.speed,
                "max_cycles": default.cpu.max_cycles,
            },
            "logging": {
                "level": default.logging.level,
                "file": default.logging.file,
            },
        }, indent=2)

    if format == "toml":
        lines = [
            "[display]",
            f'width = {default.display.width}',
            f'height = {default.display.height}',
            f'on_char = "{default.display.on_char}"',
            f'off_char = "{default.display.off_char}"',
            "",
            "[keypad]",
            "# mapping is not well-supported in TOML for nested dicts",
            "# Use YAML or JSON for custom keypad mappings",
            "",
            "[cpu]",
            f'super_chip = {str(default.cpu.super_chip).lower()}',
            f'speed = {default.cpu.speed}',
            f'max_cycles = {default.cpu.max_cycles}',
            "",
            "[logging]",
            f'level = "{default.logging.level}"',
        ]
        return "\n".join(lines)

    # Default: YAML
    lines = [
        "# CHIP-8 Emulator Configuration",
        "",
        "display:",
        f"  width: {default.display.width}",
        f"  height: {default.display.height}",
        f'  on_char: "{default.display.on_char}"',
        f'  off_char: "{default.display.off_char}"',
        "",
        "keypad:",
        "  mapping:",
    ]
    for key, val in sorted(default.keypad.mapping.items(), key=lambda kv: kv[1]):
        lines.append(f"    {key}: 0x{val:X}")
    lines.extend([
        "",
        "cpu:",
        f"  super_chip: {str(default.cpu.super_chip).lower()}",
        f"  speed: {default.cpu.speed}",
        f"  max_cycles: {default.cpu.max_cycles}",
        "",
        "logging:",
        f'  level: "{default.logging.level}"',
        "  file: null  # Set to a filename to log to file",
    ])
    return "\n".join(lines)