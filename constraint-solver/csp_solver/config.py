"""
CSP Solver configuration management.

Supports loading solver configuration from YAML, JSON, or TOML files,
as well as programmatic configuration via SolverConfig dataclass.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Supported config file extensions and their loaders
_CONFIG_LOADERS: Dict[str, Any] = {}


def _register_loaders() -> None:
    """Register config file loaders. TOML requires Python 3.11+ or tomllib."""
    _CONFIG_LOADERS[".json"] = json.load

    try:
        import tomllib
        _CONFIG_LOADERS[".toml"] = lambda f: tomllib.load(f)  # type: ignore[assignment]
    except ImportError:
        pass

    try:
        import yaml
        _CONFIG_LOADERS[".yaml"] = yaml.safe_load
        _CONFIG_LOADERS[".yml"] = yaml.safe_load
    except ImportError:
        pass


_register_loaders()


@dataclass
class SolverConfig:
    """Configuration for the CSP solver.

    Attributes:
        use_mrv: Use Minimum Remaining Values heuristic.
        use_degree: Use degree heuristic as tiebreaker.
        use_lcv: Use Least Constraining Value heuristic.
        use_forward_check: Use forward checking.
        use_mac: Use Maintaining Arc Consistency.
        preprocess_ac3: Run full AC-3 before search.
        timeout: Maximum solve time in seconds. None for no limit.
        max_solutions: Maximum solutions to find in solve_all.
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
    """

    use_mrv: bool = True
    use_degree: bool = True
    use_lcv: bool = True
    use_forward_check: bool = False
    use_mac: bool = True
    preprocess_ac3: bool = True
    timeout: Optional[float] = None
    max_solutions: int = 10
    log_level: str = "WARNING"

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SolverConfig:
        """Create a SolverConfig from a dictionary, ignoring unknown keys."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> SolverConfig:
        """Load configuration from a YAML, JSON, or TOML file.

        Args:
            path: Path to the configuration file.

        Returns:
            SolverConfig instance.

        Raises:
            ValueError: If the file format is not supported.
            FileNotFoundError: If the file does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        ext = path.suffix.lower()
        if ext not in _CONFIG_LOADERS:
            supported = ", ".join(sorted(_CONFIG_LOADERS.keys()))
            raise ValueError(
                f"Unsupported config format: {ext}. Supported: {supported}"
            )

        with open(path, "r") as f:
            data = _CONFIG_LOADERS[ext](f)

        if data is None:
            data = {}

        return cls.from_dict(data)

    def to_file(self, path: Union[str, Path]) -> None:
        """Save configuration to a JSON file.

        Args:
            path: Path to save the configuration file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def apply_logging(self) -> None:
        """Apply the configured log level to the csp_solver logger."""
        level = getattr(logging, self.log_level.upper(), logging.WARNING)
        logging.getLogger("csp_solver").setLevel(level)

    def create_solver(self):
        """Create a CSPSolver from this configuration.

        Returns:
            CSPSolver instance with this configuration.
        """
        from .solver import CSPSolver
        return CSPSolver(
            use_mrv=self.use_mrv,
            use_degree=self.use_degree,
            use_lcv=self.use_lcv,
            use_forward_check=self.use_forward_check,
            use_mac=self.use_mac,
            preprocess_ac3=self.preprocess_ac3,
            timeout=self.timeout,
        )


# Default configuration file content for bootstrap
DEFAULT_CONFIG_JSON = json.dumps({
    "use_mrv": True,
    "use_degree": True,
    "use_lcv": True,
    "use_forward_check": False,
    "use_mac": True,
    "preprocess_ac3": True,
    "timeout": None,
    "max_solutions": 10,
    "log_level": "WARNING",
}, indent=2)


def create_example_config(path: Union[str, Path]) -> Path:
    """Create an example configuration file at the given path.

    Args:
        path: Directory or file path for the config.

    Returns:
        Path to the created file.
    """
    path = Path(path)
    if path.is_dir() or not path.suffix:
        path = path / "csp_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_JSON + "\n")
    logger.info("Created example config at %s", path)
    return path