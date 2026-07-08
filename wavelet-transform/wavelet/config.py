"""
Configuration system for the wavelet-transform toolkit.

Supports JSON, YAML, and TOML configuration files for reproducible
analysis pipelines.  The configuration specifies wavelet parameters,
decomposition level, thresholding method, transform type, and output
options.

Example config (JSON)::

    {
        "wavelet": "db4",
        "level": 4,
        "transform": "dwt",
        "denoise": {
            "method": "bayes",
            "threshold_func": "soft",
            "cycle_spinning": false,
            "n_shifts": 16
        },
        "compress": {
            "keep_ratio": 0.3
        }
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

__all__ = [
    "DenoiseConfig",
    "CompressConfig",
    "WaveletConfig",
    "load_config",
    "save_config",
    "DEFAULT_CONFIG",
]


@dataclass
class DenoiseConfig:
    """Denoising parameters."""
    method: str = "bayes"        # universal, sure, bayes, minimax
    threshold_func: str = "soft"  # soft, hard, garrote
    cycle_spinning: bool = False
    n_shifts: int = 16
    level: int | None = None


@dataclass
class CompressConfig:
    """Compression parameters."""
    keep_ratio: float | None = 0.3
    threshold: float | None = None
    level: int | None = None


@dataclass
class WaveletConfig:
    """Top-level configuration for wavelet analysis pipelines."""
    wavelet: str = "db4"
    level: int | None = None
    transform: str = "dwt"  # dwt, modwt, swt
    boundary: str = "periodic"
    signal: str = "sine"
    signal_length: int = 256
    noise: float = 0.0
    output_dir: str = "."
    verbose: bool = False
    denoise: DenoiseConfig = field(default_factory=DenoiseConfig)
    compress: CompressConfig = field(default_factory=CompressConfig)

    def validate(self) -> list[str]:
        """Validate the configuration.  Returns a list of error messages."""
        errors = []
        from .wavelets import wavelet
        try:
            wavelet(self.wavelet)
        except ValueError as e:
            errors.append(f"Invalid wavelet '{self.wavelet}': {e}")
        if self.transform not in ("dwt", "modwt", "swt"):
            errors.append(f"Invalid transform '{self.transform}'. "
                          f"Must be: dwt, modwt, swt")
        if self.boundary not in ("periodic", "symmetric", "zero", "constant", "reflect"):
            errors.append(f"Invalid boundary '{self.boundary}'")
        if self.signal_length < 2:
            errors.append("signal_length must be >= 2")
        if self.denoise.method not in ("universal", "sure", "bayes", "minimax"):
            errors.append(f"Invalid denoise.method '{self.denoise.method}'")
        if self.denoise.threshold_func not in ("soft", "hard", "garrote"):
            errors.append(f"Invalid denoise.threshold_func '{self.denoise.threshold_func}'")
        if self.denoise.n_shifts < 1:
            errors.append("denoise.n_shifts must be >= 1")
        if self.compress.keep_ratio is not None:
            if not (0 < self.compress.keep_ratio <= 1):
                errors.append("compress.keep_ratio must be in (0, 1]")
        return errors

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WaveletConfig":
        """Create from a plain dict."""
        denoise = d.pop("denoise", {})
        compress = d.pop("compress", {})
        return cls(
            denoise=DenoiseConfig(**denoise) if denoise else DenoiseConfig(),
            compress=CompressConfig(**compress) if compress else CompressConfig(),
            **d,
        )


DEFAULT_CONFIG = WaveletConfig()


def load_config(path: str) -> WaveletConfig:
    """Load a configuration file (JSON, YAML, or TOML based on extension).

    Parameters
    ----------
    path : path to the config file.  Format inferred from extension:
           .json → JSON, .yaml/.yml → YAML, .toml → TOML
    """
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as f:
        text = f.read()

    if ext == ".json":
        data = json.loads(text)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
            data = yaml.safe_load(text)
        except ImportError:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
    elif ext == ".toml":
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                raise ImportError("tomli not installed (Python < 3.11). "
                                  "Install with: pip install tomli")
        data = tomllib.loads(text)
    else:
        raise ValueError(f"Unsupported config format '{ext}'. "
                         f"Use .json, .yaml/.yml, or .toml")

    return WaveletConfig.from_dict(data)


def save_config(config: WaveletConfig, path: str) -> None:
    """Save a configuration to a file (JSON, YAML, or TOML)."""
    ext = os.path.splitext(path)[1].lower()
    data = config.to_dict()

    if ext == ".json":
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
            with open(path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
    elif ext == ".toml":
        _write_toml(data, path)
    else:
        raise ValueError(f"Unsupported config format '{ext}'")


def _write_toml(data: dict, path: str) -> None:
    """Write a simple dict to TOML format (nested dicts become tables)."""
    lines = []
    _toml_section(data, lines, prefix="")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def _toml_section(d: dict, lines: list[str], prefix: str) -> None:
    """Recursively write TOML sections."""
    scalars = {}
    nested = {}
    for k, v in d.items():
        if isinstance(v, dict):
            nested[k] = v
        else:
            scalars[k] = v
    if prefix:
        lines.append(f"[{prefix}]")
    for k, v in scalars.items():
        lines.append(f"{k} = {_toml_value(v)}")
    for k, v in nested.items():
        lines.append("")
        _toml_section(v, lines, prefix=f"{prefix}.{k}" if prefix else k)


def _toml_value(v: Any) -> str:
    """Format a Python value as a TOML literal."""
    if v is None:
        return '""'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return f'"{v}"'