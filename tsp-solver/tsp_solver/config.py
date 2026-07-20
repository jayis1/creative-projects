"""Configuration management for the TSP solver.

Supports loading solver configuration from YAML or JSON files, with sensible
defaults and validation.  Configuration controls algorithm selection,
refinement, metaheuristic parameters, benchmark settings, logging, and
output format.

Example YAML config (``config.yaml``)::

    algorithm: christofides
    refine: two_opt
    seed: 42
    n: 100
    grid: 1000
    output: json
    log_level: INFO
    algorithm_params:
      genetic_algorithm:
        population_size: 200
        generations: 1000
      simulated_annealing:
        initial_temp: 200.0
        cooling_rate: 0.999

Example JSON config (``config.json``)::

    {"algorithm": "held_karp", "n": 15, "seed": 1}
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


@dataclass
class SolverConfig:
    """Typed configuration for the TSP solver.

    Attributes
    ----------
    algorithm : str
        Algorithm name (see :func:`tsp_solver.solver.list_algorithms`).
    refine : Optional[str]
        Local search refinement: ``"two_opt"``, ``"three_opt"``, ``"or_opt"``.
    seed : Optional[int]
        RNG seed for stochastic algorithms.
    n : int
        Number of cities for randomly generated instances.
    grid : int
        Coordinate grid size for random instances.
    load : Optional[str]
        Path to a TSPLIB-style ``.tsp`` file.  Overrides random generation.
    output : str
        Output format: ``"text"``, ``"json"``.
    plot : bool
        Whether to print an ASCII visualization.
    benchmark : bool
        Run the BenchmarkSuite instead of a single solve.
    compare : bool
        Run all algorithms and compare.
    list_algos : bool
        List all available algorithms.
    log_level : str
        Logging level: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``.
    log_file : Optional[str]
        Path to a log file (default: stderr only).
    max_iter : Optional[int]
        Max iterations for iterative algorithms.
    algorithm_params : Dict[str, Dict[str, Any]]
        Per-algorithm parameter overrides.
    """

    algorithm: str = "nearest_neighbor"
    refine: Optional[str] = None
    seed: Optional[int] = 0
    n: int = 20
    grid: int = 1000
    load: Optional[str] = None
    output: str = "text"
    plot: bool = False
    benchmark: bool = False
    compare: bool = False
    list_algos: bool = False
    log_level: str = "WARNING"
    log_file: Optional[str] = None
    max_iter: Optional[int] = None
    algorithm_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: str) -> "SolverConfig":
        """Load configuration from a YAML or JSON file.

        The file format is determined by the extension (``.yml``/``.yaml``
        for YAML, ``.json`` for JSON).  Unknown extensions raise ``ValueError``.
        """
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        text = path_obj.read_text()
        ext = path_obj.suffix.lower()
        if ext in (".yaml", ".yml"):
            if yaml is None:
                raise ImportError("PyYAML is required to load YAML configs. Install with: pip install pyyaml")
            data = yaml.safe_load(text)
        elif ext == ".json":
            data = json.loads(text)
        else:
            raise ValueError(f"Unsupported config format: {ext!r}. Use .yaml, .yml, or .json")
        if data is None:
            data = {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SolverConfig":
        """Create a :class:`SolverConfig` from a plain dict, ignoring unknown keys."""
        valid = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in valid}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the configuration to a plain dict."""
        from dataclasses import asdict
        return asdict(self)

    def save(self, path: str) -> None:
        """Save the configuration to a YAML or JSON file."""
        data = self.to_dict()
        ext = Path(path).suffix.lower()
        if ext in (".yaml", ".yml"):
            if yaml is None:
                raise ImportError("PyYAML is required to save YAML configs")
            Path(path).write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        elif ext == ".json":
            Path(path).write_text(json.dumps(data, indent=2))
        else:
            raise ValueError(f"Unsupported format: {ext!r}")

    # ------------------------------------------------------------------
    # Merge with CLI args
    # ------------------------------------------------------------------
    def merge_args(self, args) -> "SolverConfig":
        """Return a new config with non-None values from argparse *args* overriding this config.

        ``args`` is an ``argparse.Namespace``.  Only attributes that exist on
        both the config and the namespace are considered.
        """
        cfg_dict = self.to_dict()
        for key in cfg_dict:
            if hasattr(args, key):
                val = getattr(args, key)
                if val is not None and val is not False and val != "":
                    # Only override if the CLI explicitly provided a value.
                    # We treat False/None/"" as "not set" for booleans/strings.
                    cfg_dict[key] = val
        return SolverConfig.from_dict(cfg_dict)


def default_config_path() -> Optional[str]:
    """Return the path to a default config file if one exists.

    Checks, in order: ``./tsp-solver.yaml``, ``./tsp-solver.json``,
    ``~/.tsp-solver.yaml``, ``~/.tsp-solver.json``.
    """
    candidates = [
        "tsp-solver.yaml",
        "tsp-solver.yml",
        "tsp-solver.json",
        os.path.expanduser("~/.tsp-solver.yaml"),
        os.path.expanduser("~/.tsp-solver.yml"),
        os.path.expanduser("~/.tsp-solver.json"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None