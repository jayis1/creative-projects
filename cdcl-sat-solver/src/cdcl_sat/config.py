"""
Solver configuration for the CDCL SAT Solver.

Provides a dataclass-based configuration that can be loaded from
JSON files, environment variables, or constructed programmatically.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class SolverConfig:
    """Configuration for the CDCL SAT solver.

    All parameters have sensible defaults but can be overridden via
    constructor arguments, JSON config files, or environment variables.

    Attributes:
        restart_strategy: Restart strategy — 'luby' or 'geometric'.
        luby_multiplier: Multiplier for Luby restart sequence.
        geometric_base: Base conflicts for geometric restart strategy.
        geometric_factor: Growth factor for geometric restart strategy.
        var_decay: VSIDS activity decay factor (0 < var_decay < 1).
        max_learnt_clauses: Maximum learnt clauses before reduction.
        learnt_clause_inc: Growth factor for learnt clause database size.
        glue_threshold: Clauses with glue below this threshold are kept.
        verbose: Verbosity level (0=silent, 1=stats, 2=trace).
        time_limit: Maximum solving time in seconds (0=unlimited).
        preprocess: Whether to run preprocessing before solving.
        proof_file: Path for DRAT proof output (None=disabled).
        model_file: Path for writing SAT model output (None=disabled).
    """

    restart_strategy: str = "luby"
    luby_multiplier: int = 100
    geometric_base: int = 100
    geometric_factor: float = 1.5
    var_decay: float = 0.95
    max_learnt_clauses: int = 5000
    learnt_clause_inc: float = 1.1
    glue_threshold: int = 100
    verbose: int = 0
    time_limit: float = 0.0
    preprocess: bool = False
    proof_file: Optional[str] = None
    model_file: Optional[str] = None

    def apply_to_solver(self, solver: "Solver") -> None:
        """Apply this configuration to a Solver instance.

        Args:
            solver: The Solver instance to configure.
        """
        solver.restart_strategy = self.restart_strategy
        solver.luby_multiplier = self.luby_multiplier
        solver.geometric_base = self.geometric_base
        solver.geometric_factor = self.geometric_factor
        solver.var_decay = self.var_decay
        solver.max_learnt_clauses = self.max_learnt_clauses
        solver.learnt_clause_inc = self.learnt_clause_inc
        solver.glue_threshold = self.glue_threshold
        solver.verbose = self.verbose

        if self.proof_file:
            solver.enable_proof(self.proof_file)

    @classmethod
    def from_json(cls, path: str) -> "SolverConfig":
        """Load configuration from a JSON file.

        Args:
            path: Path to JSON configuration file.

        Returns:
            SolverConfig instance with values from the file.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_env(cls) -> "SolverConfig":
        """Load configuration from environment variables.

        Environment variables are prefixed with CDCL_ and use uppercase.
        For example: CDCL_RESTART_STRATEGY=luby, CDCL_VERBOSE=2, CDCL_TIME_LIMIT=60.

        Returns:
            SolverConfig instance with values from environment.
        """
        kwargs = {}
        env_map = {
            "CDCL_RESTART_STRATEGY": ("restart_strategy", str),
            "CDCL_LUBY_MULTIPLIER": ("luby_multiplier", int),
            "CDCL_GEOMETRIC_BASE": ("geometric_base", int),
            "CDCL_GEOMETRIC_FACTOR": ("geometric_factor", float),
            "CDCL_VAR_DECAY": ("var_decay", float),
            "CDCL_MAX_LEARNT_CLAUSES": ("max_learnt_clauses", int),
            "CDCL_LEARNT_CLAUSE_INC": ("learnt_clause_inc", float),
            "CDCL_GLUE_THRESHOLD": ("glue_threshold", int),
            "CDCL_VERBOSE": ("verbose", int),
            "CDCL_TIME_LIMIT": ("time_limit", float),
            "CDCL_PREPROCESS": ("preprocess", lambda x: x.lower() in ("1", "true", "yes")),
            "CDCL_PROOF_FILE": ("proof_file", str),
            "CDCL_MODEL_FILE": ("model_file", str),
        }
        for env_var, (field_name, converter) in env_map.items():
            val = os.environ.get(env_var)
            if val is not None:
                kwargs[field_name] = converter(val)
        return cls(**kwargs)

    def to_json(self, path: str) -> None:
        """Save configuration to a JSON file.

        Args:
            path: Path to write the JSON configuration file.
        """
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def __post_init__(self):
        """Validate configuration values."""
        if self.restart_strategy not in ("luby", "geometric"):
            raise ValueError(f"restart_strategy must be 'luby' or 'geometric', got {self.restart_strategy!r}")
        if not 0 < self.var_decay < 1:
            raise ValueError(f"var_decay must be in (0, 1), got {self.var_decay}")
        if self.max_learnt_clauses <= 0:
            raise ValueError(f"max_learnt_clauses must be positive, got {self.max_learnt_clauses}")
        if self.geometric_factor <= 1.0:
            raise ValueError(f"geometric_factor must be > 1.0, got {self.geometric_factor}")