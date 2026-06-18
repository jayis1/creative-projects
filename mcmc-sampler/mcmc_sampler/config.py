"""
Configuration system for MCMC sampler runs.

Supports YAML, JSON, and TOML config files that fully specify a sampler
run — target distribution, sampler algorithm, hyper-parameters, and
output options — enabling reproducible inference pipelines.

Example config (YAML)::

    target:
      kind: normal
      params: {mu: 2.0, sigma: 1.5}
    sampler:
      algo: hmc-adapt
      n_steps: 20
      target_accept: 0.65
    run:
      n_samples: 10000
      burn: 2000
      thin: 2
      seed: 42
    output:
      trace_json: output.json
      diagnostics: true
      visualize: true
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Union

import numpy as np

logger = logging.getLogger(__name__)

# TOML via stdlib (3.11+) or tomli fallback
try:
    import tomllib  # type: ignore
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

# YAML is optional
try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


class ConfigError(Exception):
    """Raised when a configuration file is malformed or invalid."""


@dataclass
class SamplerConfig:
    """Configuration for a single sampler run."""

    algo: str = "mh"
    params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        valid = {"mh", "am", "hmc", "hmc-adapt", "slice", "nuts"}
        if self.algo not in valid:
            raise ConfigError(
                f"sampler.algo must be one of {sorted(valid)}, got {self.algo!r}"
            )


@dataclass
class TargetConfig:
    """Configuration for the target distribution."""

    kind: str = "normal"
    params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        valid = {
            "normal", "mvn", "beta", "exp", "mixture",
            "gamma", "studentt", "uniform", "dirichlet",
            "poisson", "bernoulli", "categorical",
            "truncated-normal", "logistic", "weibull",
            "chisquared", "custom",
        }
        if self.kind not in valid:
            raise ConfigError(
                f"target.kind must be one of {sorted(valid)}, got {self.kind!r}"
            )


@dataclass
class RunConfig:
    """Run-level parameters."""

    n_samples: int = 5000
    burn: int = 1000
    thin: int = 1
    seed: Optional[int] = None
    n_chains: int = 1
    x0: Optional[Sequence[float]] = None


@dataclass
class OutputConfig:
    """Output options."""

    trace_json: Optional[str] = None
    diagnostics: bool = True
    visualize: bool = False
    plot: Optional[str] = None
    summary: bool = True
    log_level: str = "INFO"


@dataclass
class MCMCConfig:
    """Top-level configuration aggregating all sub-configs."""

    target: TargetConfig = field(default_factory=TargetConfig)
    sampler: SamplerConfig = field(default_factory=SamplerConfig)
    run: RunConfig = field(default_factory=RunConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def validate(self) -> None:
        """Validate all sub-configs."""
        self.target.validate()
        self.sampler.validate()
        if self.run.n_samples <= 0:
            raise ConfigError("run.n_samples must be positive")
        if self.run.burn < 0:
            raise ConfigError("run.burn must be non-negative")
        if self.run.thin < 1:
            raise ConfigError("run.thin must be >= 1")
        if self.run.n_chains < 1:
            raise ConfigError("run.n_chains must be >= 1")
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.output.log_level.upper() not in valid_levels:
            raise ConfigError(
                f"output.log_level must be one of {sorted(valid_levels)}"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCMCConfig":
        """Build a config from a plain dict."""
        cfg = cls()
        if "target" in data:
            t = data["target"]
            if isinstance(t, str):
                cfg.target = TargetConfig(kind=t)
            else:
                cfg.target = TargetConfig(
                    kind=t.get("kind", "normal"),
                    params=t.get("params", {}),
                )
        if "sampler" in data:
            s = data["sampler"]
            if isinstance(s, str):
                cfg.sampler = SamplerConfig(algo=s)
            else:
                cfg.sampler = SamplerConfig(
                    algo=s.get("algo", "mh"),
                    params=s.get("params", {}),
                )
        if "run" in data:
            r = data["run"]
            cfg.run = RunConfig(
                n_samples=r.get("n_samples", 5000),
                burn=r.get("burn", 1000),
                thin=r.get("thin", 1),
                seed=r.get("seed"),
                n_chains=r.get("n_chains", 1),
                x0=r.get("x0"),
            )
        if "output" in data:
            o = data["output"]
            cfg.output = OutputConfig(
                trace_json=o.get("trace_json"),
                diagnostics=o.get("diagnostics", True),
                visualize=o.get("visualize", False),
                plot=o.get("plot"),
                summary=o.get("summary", True),
                log_level=o.get("log_level", "INFO"),
            )
        cfg.validate()
        return cfg

    @classmethod
    def from_file(cls, path: str) -> "MCMCConfig":
        """Load a config from a YAML, JSON, or TOML file.

        The format is detected by the file extension.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext == ".json":
            with open(path) as fh:
                data = json.load(fh)
        elif ext == ".yaml" or ext == ".yml":
            if yaml is None:
                raise ConfigError(
                    "PyYAML is required to load YAML config files. "
                    "Install with: pip install pyyaml"
                )
            with open(path) as fh:
                data = yaml.safe_load(fh)
        elif ext == ".toml":
            if tomllib is None:
                raise ConfigError(
                    "tomllib (Python 3.11+) or tomli is required for TOML config. "
                    "Install with: pip install tomli"
                )
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        else:
            raise ConfigError(
                f"Unsupported config format: {ext}. "
                "Use .json, .yaml, or .toml"
            )
        if not isinstance(data, dict):
            raise ConfigError("Config file must contain a mapping at the top level")
        logger.debug("Loaded config from %s: %s", path, data)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the config to a plain dict."""
        return {
            "target": {
                "kind": self.target.kind,
                "params": self.target.params,
            },
            "sampler": {
                "algo": self.sampler.algo,
                "params": self.sampler.params,
            },
            "run": {
                "n_samples": self.run.n_samples,
                "burn": self.run.burn,
                "thin": self.run.thin,
                "seed": self.run.seed,
                "n_chains": self.run.n_chains,
                "x0": list(self.run.x0) if self.run.x0 is not None else None,
            },
            "output": {
                "trace_json": self.output.trace_json,
                "diagnostics": self.output.diagnostics,
                "visualize": self.output.visualize,
                "plot": self.output.plot,
                "summary": self.output.summary,
                "log_level": self.output.log_level,
            },
        }

    def to_json(self, path: Optional[str] = None) -> str:
        """Serialize config to JSON."""
        text = json.dumps(self.to_dict(), indent=2)
        if path:
            with open(path, "w") as fh:
                fh.write(text)
        return text


def _ensure_list(v: Union[float, Sequence[float], np.ndarray]) -> list:
    """Convert a scalar or array-like to a Python list."""
    if isinstance(v, (list, tuple)):
        return list(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    return [float(v)]


def load_config(path: str) -> MCMCConfig:
    """Convenience function to load a config from file."""
    return MCMCConfig.from_file(path)