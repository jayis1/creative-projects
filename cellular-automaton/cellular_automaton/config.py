"""Configuration system for the cellular automaton simulator.

Supports loading CA configurations from JSON, YAML, and TOML files.

A config file can specify:
    * rule (name or Bxx/Sxx notation)
    * grid dimensions (width, height)
    * boundary condition
    * initial state (pattern, random density, center seed, RLE)
    * number of steps
    * output format and path
    * multi-state rule parameters

Example YAML::

    rule: GameOfLife
    width: 60
    height: 40
    boundary: periodic
    initial:
      pattern: gosper_gun
      x: 5
      y: 10
    steps: 200
    output:
      format: ascii
    logging:
      level: INFO

Example JSON::

    {
      "rule": "Rule30",
      "width": 80,
      "boundary": "zero",
      "initial": {"seed": "center"},
      "steps": 40,
      "output": {"format": "ascii"}
    }
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class CAConfig:
    """Configuration for a cellular automaton run.

    Attributes
    ----------
    rule : str
        Rule name (e.g. ``"Rule30"``, ``"GameOfLife"``, ``"B36/S23"``).
    width : int
        Grid width.
    height : Optional[int]
        Grid height (``None`` for 1D rules).
    boundary : str
        Boundary condition (``periodic``, ``fixed``, ``reflect``, ``zero``).
    fixed_value : int
        Value for ``fixed`` boundary.
    initial : dict
        Initial state specification with keys:
        - ``pattern``: builtin pattern name
        - ``rle``: RLE string
        - ``random``: density (0-1)
        - ``seed``: random seed
        - ``center``: boolean (use center seed for 1D)
        - ``x``, ``y``: pattern placement coordinates
    steps : int
        Number of steps to run.
    output : dict
        Output specification with keys:
        - ``format``: ascii, ansi, svg, ppm, png
        - ``path``: output file path
    multistate : dict
        Multi-state rule parameters (e.g. ``{"p": 0.01, "g": 0.1}``).
    logging : dict
        Logging configuration with keys:
        - ``level``: DEBUG, INFO, WARNING, ERROR
        - ``file``: log file path
    """

    rule: str = "GameOfLife"
    width: int = 80
    height: Optional[int] = None
    boundary: str = "periodic"
    fixed_value: int = 0
    initial: Dict[str, Any] = field(default_factory=dict)
    steps: int = 100
    output: Dict[str, Any] = field(default_factory=dict)
    multistate: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CAConfig":
        """Create a config from a dictionary."""
        # Handle nested dicts.
        initial = data.get("initial", {}) or {}
        output = data.get("output", {}) or {}
        multistate = data.get("multistate", {}) or {}
        logging_cfg = data.get("logging", {}) or {}
        return cls(
            rule=data.get("rule", "GameOfLife"),
            width=data.get("width", 80),
            height=data.get("height"),
            boundary=data.get("boundary", "periodic"),
            fixed_value=data.get("fixed_value", 0),
            initial=initial,
            steps=data.get("steps", 100),
            output=output,
            multistate=multistate,
            logging=logging_cfg,
        )

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "CAConfig":
        """Load a config from a JSON, YAML, or TOML file.

        The format is determined by the file extension.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        suffix = path.suffix.lower()
        text = path.read_text()

        if suffix == ".json":
            data = json.loads(text)
        elif suffix in (".yaml", ".yml"):
            data = _load_yaml(text)
        elif suffix == ".toml":
            data = _load_toml(text)
        else:
            # Try JSON as fallback.
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                raise ValueError(
                    f"Unsupported config format: {suffix}. "
                    f"Use .json, .yaml, or .toml"
                )

        logger.debug("Loaded config from %s: %s", path, data)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "rule": self.rule,
            "width": self.width,
            "height": self.height,
            "boundary": self.boundary,
            "fixed_value": self.fixed_value,
            "initial": self.initial,
            "steps": self.steps,
            "output": self.output,
            "multistate": self.multistate,
            "logging": self.logging,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Union[str, Path]) -> None:
        """Save to a file (format from extension)."""
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            path.write_text(self.to_json())
        elif suffix in (".yaml", ".yml"):
            path.write_text(_dump_yaml(self.to_dict()))
        elif suffix == ".toml":
            path.write_text(_dump_toml(self.to_dict()))
        else:
            path.write_text(self.to_json())

    def setup_logging(self) -> None:
        """Configure logging based on the ``logging`` section."""
        level_name = self.logging.get("level", "WARNING")
        level = getattr(logging, level_name.upper(), logging.WARNING)
        handlers: list = [logging.StreamHandler()]
        log_file = self.logging.get("file")
        if log_file:
            handlers.append(logging.FileHandler(log_file))
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=handlers,
            force=True,
        )

    def build_ca(self):
        """Build a CellularAutomaton from this config.

        Returns a :class:`CellularAutomaton` ready to run.
        """
        from .engine import CellularAutomaton, Boundary
        from .rules import get_rule
        from .multistate import is_multistate_rule, get_multistate_rule
        from .patterns import get_pattern, place_pattern, parse_rle
        import numpy as np

        # Determine if this is a multi-state rule.
        if is_multistate_rule(self.rule):
            rule = get_multistate_rule(self.rule, **self.multistate)
            height = self.height if self.height else 20
            ca = CellularAutomaton(
                rule, width=self.width, height=height,
                boundary=self.boundary, fixed_value=self.fixed_value,
            )
        else:
            rule = get_rule(self.rule)
            height = self.height if self.height else (None if rule.dimensions == 1 else 20)
            ca = CellularAutomaton(
                rule, width=self.width, height=height,
                boundary=self.boundary, fixed_value=self.fixed_value,
            )

        # Set initial state.
        init = self.initial
        if init.get("random") is not None:
            ca.randomize(init["random"], seed=init.get("seed"))
        elif init.get("pattern"):
            pat = get_pattern(init["pattern"])
            place_pattern(ca, pat, x=init.get("x", 5), y=init.get("y", 5))
        elif init.get("rle"):
            pat = parse_rle(init["rle"])
            place_pattern(ca, pat, x=init.get("x", 5), y=init.get("y", 5))
        elif init.get("center") or (rule.dimensions == 1 and not init):
            ca.center_seed()

        # Set RNG for stochastic multi-state rules.
        if ca._is_multistate:
            ca.set_rng(init.get("seed"))

        return ca

    def run(self):
        """Build the CA, run it, and return the result.

        Returns a tuple of (ca, output_string_or_path).
        """
        self.setup_logging()
        logger.info("Building CA with rule %s, %dx%d", self.rule, self.width, self.height or 1)
        ca = self.build_ca()
        logger.info("Running %d steps", self.steps)

        # Standard stepping works for both binary and multi-state rules
        # because the engine dispatches based on _is_multistate flag.
        ca.step(self.steps)

        # Handle output.
        fmt = self.output.get("format", "ascii")
        path = self.output.get("path")
        from .visualizer import (
            render_ascii, render_ansi, render_svg, render_ppm, render_png,
        )

        result = None
        if fmt == "ascii":
            result = render_ascii(ca.grid)
            if path:
                Path(path).write_text(result + "\n")
        elif fmt == "ansi":
            result = render_ansi(ca.grid)
        elif fmt == "svg":
            render_svg(ca.grid, path=path or "output.svg")
            result = path or "output.svg"
        elif fmt == "ppm":
            render_ppm(ca.grid, path or "output.ppm")
            result = path or "output.ppm"
        elif fmt == "png":
            render_png(ca.grid, path or "output.png")
            result = path or "output.png"

        return ca, result


# ---------------------------------------------------------------------------
# YAML / TOML helpers (no external dependencies required)
# ---------------------------------------------------------------------------


def _load_yaml(text: str) -> Dict[str, Any]:
    """Load YAML, using PyYAML if available, else a minimal parser."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        return _minimal_yaml_parse(text)


def _dump_yaml(data: Dict[str, Any]) -> str:
    """Dump to YAML, using PyYAML if available, else JSON."""
    try:
        import yaml  # type: ignore
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    except ImportError:
        return json.dumps(data, indent=2)


def _load_toml(text: str) -> Dict[str, Any]:
    """Load TOML, using tomllib (3.11+) or tomli if available."""
    try:
        import tomllib  # type: ignore
        return tomllib.loads(text)
    except ImportError:
        try:
            import tomli  # type: ignore
            return tomli.loads(text)
        except ImportError:
            raise ImportError(
                "TOML support requires Python 3.11+ (tomllib) or the 'tomli' package."
            )


def _dump_toml(data: Dict[str, Any]) -> str:
    """Dump to TOML (minimal, no dependencies)."""
    lines: list = []
    for key, val in data.items():
        if isinstance(val, str):
            lines.append(f'{key} = "{val}"')
        elif isinstance(val, (int, float, bool)):
            lines.append(f"{key} = {val}")
        elif isinstance(val, list):
            lines.append(f"{key} = {json.dumps(val)}")
        elif val is None:
            lines.append(f'{key} = ""')
        else:
            # For dicts/complex, embed as JSON string.
            lines.append(f'{key} = {json.dumps(json.dumps(val))}')
    return "\n".join(lines) + "\n"


def _minimal_yaml_parse(text: str) -> Dict[str, Any]:
    """Minimal YAML parser for simple key:value configs.

    Handles only flat key-value pairs and nested dicts with 2-space indent.
    Does NOT support flow style, anchors, multi-line strings, etc.
    """
    result: Dict[str, Any] = {}
    stack: list = [(0, result)]
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        key, sep, val = stripped.partition(":")
        if not sep:
            continue
        key = key.strip()
        val = val.strip()
        # Pop stack to correct indent level.
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else result
        if val == "":
            # Nested dict.
            new_dict: Dict[str, Any] = {}
            parent[key] = new_dict
            stack.append((indent + 2, new_dict))
        else:
            # Try to parse as JSON for lists/numbers/bools.
            try:
                parent[key] = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                parent[key] = val.strip("\"'")
    return result