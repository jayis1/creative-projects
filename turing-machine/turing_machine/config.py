"""
turing_machine.config
=====================

Configuration file support for Turing machines.

Supports loading machine definitions from JSON and YAML files.  A config
file describes a machine with the same structure as the definition
language but in a structured format, making it suitable for programmatic
generation and tooling.

Example JSON config::

    {
        "name": "my_incrementer",
        "blank": "_",
        "start": "s0",
        "halt": ["halt"],
        "tapes": 1,
        "transitions": [
            {"state": "s0", "read": "0", "write": "0", "move": "R", "next": "s0"},
            {"state": "s0", "read": "1", "write": "1", "move": "R", "next": "s0"},
            {"state": "s0", "read": "_", "write": "_", "move": "L", "next": "add"},
            {"state": "add", "read": "0", "write": "1", "move": "S", "next": "halt"},
            {"state": "add", "read": "1", "write": "0", "move": "L", "next": "add"},
            {"state": "add", "read": "_", "write": "1", "move": "S", "next": "halt"}
        ]
    }

Example YAML config::

    name: my_incrementer
    blank: _
    start: s0
    halt: [halt]
    tapes: 1
    transitions:
      - state: s0
        read: "0"
        write: "0"
        move: R
        next: s0
      - state: s0
        read: "1"
        write: "1"
        move: R
        next: s0
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Hashable, List, Optional, Union

from .machine import Program, TMDirection, Transition, TuringMachine

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when a config file is invalid."""


def _parse_transition_dict(data: Dict[str, Any]) -> Transition:
    """Parse a transition from a config dict."""
    required = ["state", "read", "write", "move", "next"]
    for key in required:
        if key not in data:
            raise ConfigError(f"transition missing required key '{key}': {data}")

    state = str(data["state"])
    read = data["read"]
    write = data["write"]
    move = data["move"]
    next_state = str(data["next"])

    # Handle multi-tape (tuple) values.
    if isinstance(read, list):
        read = tuple(read)
    if isinstance(write, list):
        write = tuple(write)
    if isinstance(move, list):
        move = tuple(move)

    return Transition(state=state, read=read, write=write, direction=move, new_state=next_state)


def load_config(path: Union[str, Path]) -> Dict[str, Any]:
    """Load a machine config from a JSON or YAML file.

    The file format is determined by the extension: ``.json`` for JSON,
    ``.yaml``/``.yml`` for YAML.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")

    ext = path.suffix.lower()
    text = path.read_text(encoding="utf-8")

    if ext == ".json":
        data = json.loads(text)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise ConfigError(
                "PyYAML is required for YAML config files. "
                "Install with: pip install pyyaml"
            )
        data = yaml.safe_load(text)
    else:
        # Try JSON first, then YAML.
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            try:
                import yaml
                data = yaml.safe_load(text)
            except ImportError:
                raise ConfigError(
                    f"unknown config format '{ext}'; "
                    "use .json, .yaml, or .yml"
                )

    if not isinstance(data, dict):
        raise ConfigError(f"config must be a dict/object, got {type(data).__name__}")

    logger.info("Loaded config from %s: name=%s", path, data.get("name", "<unnamed>"))
    return data


def config_to_machine(
    data: Dict[str, Any],
    tape: Optional[List[Hashable]] = None,
    max_steps: int = 1_000_000,
) -> TuringMachine:
    """Convert a parsed config dict into a :class:`TuringMachine`.

    Required keys: ``start``, ``transitions``.
    Optional keys: ``blank`` (default ``_``), ``halt`` (default ``["halt"]``),
    ``tapes`` (default 1), ``name``, ``comment``.
    """
    if "transitions" not in data:
        raise ConfigError("config missing 'transitions' key")
    if "start" not in data:
        raise ConfigError("config missing 'start' key")

    blank = data.get("blank", "_")
    start = str(data["start"])
    halt = data.get("halt", ["halt"])
    if isinstance(halt, str):
        halt = [halt]
    halt_states = set(str(h) for h in halt)
    num_tapes = int(data.get("tapes", 1))

    transitions = []
    for i, t_data in enumerate(data["transitions"]):
        if not isinstance(t_data, dict):
            raise ConfigError(f"transition {i} must be an object, got {type(t_data).__name__}")
        try:
            transitions.append(_parse_transition_dict(t_data))
        except ConfigError as e:
            raise ConfigError(f"transition {i}: {e}") from e

    program = Program(transitions)

    tm = TuringMachine(
        program,
        initial_state=start,
        tape=tape,
        blank=blank,
        halt_states=halt_states,
        max_steps=max_steps,
        num_tapes=num_tapes,
    )

    # Attach metadata (using object.__setattr__ to avoid dataclass issues).
    object.__setattr__(tm, "config_name", data.get("name", ""))
    object.__setattr__(tm, "config_comment", data.get("comment", ""))

    return tm


def save_config(machine: TuringMachine, path: Union[str, Path], name: str = "", fmt: str = "json") -> None:
    """Save a machine's program as a config file.

    Parameters
    ----------
    machine : TuringMachine
        The machine whose program to save.
    path : str or Path
        Output file path.
    name : str
        Machine name to include in the config.
    fmt : str
        Output format: ``"json"`` or ``"yaml"``.
    """
    path = Path(path)
    transitions = []
    for t in machine.program:
        read = t.read
        if isinstance(read, tuple):
            read = list(read)
        write = t.write
        if isinstance(write, tuple):
            write = list(write)
        move = t.direction
        if isinstance(move, tuple):
            move = [str(m) for m in move]
        else:
            move = str(move)
        transitions.append({
            "state": t.state,
            "read": read,
            "write": write,
            "move": move,
            "next": t.new_state,
        })

    data = {
        "name": name or getattr(machine, "config_name", ""),
        "blank": str(machine.tapes[0].blank),
        "start": machine.initial_state,
        "halt": sorted(machine.halt_states),
        "tapes": machine.num_tapes,
        "transitions": transitions,
    }

    if fmt == "json":
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    elif fmt in ("yaml", "yml"):
        try:
            import yaml
        except ImportError:
            raise ConfigError("PyYAML required for YAML output. pip install pyyaml")
        path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    else:
        raise ConfigError(f"unknown format '{fmt}'; use 'json' or 'yaml'")

    logger.info("Saved config to %s (format=%s)", path, fmt)