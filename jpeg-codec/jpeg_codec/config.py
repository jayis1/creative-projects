"""Configuration management for the jpeg-codec.

Supports loading encoding/decoding settings from JSON, YAML, or TOML
files, or from a Python dict.  Provides sensible defaults and
validation.

Example config file (JSON)::

    {
        "quality": 85,
        "sampling": "4:2:0",
        "restart_interval": 0,
        "comment": "Encoded by jpeg-codec",
        "dpi": [72, 72],
        "optimize_huffman": false
    }
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, Union

from .exceptions import InvalidQualityError, InvalidSamplingError

__all__ = ["EncodingConfig", "load_config", "save_config"]

_VALID_SAMPLING = {"4:4:4", "4:2:2", "4:2:0", "4:1:1"}


@dataclass
class EncodingConfig:
    """Configuration for JPEG encoding.

    Attributes
    ----------
    quality : int
        Quality factor 1-100 (default 85).
    sampling : str
        Chroma subsampling mode (default "4:2:0").
    restart_interval : int
        MCU restart interval (0 = disabled, default 0).
    comment : str, optional
        Comment to embed in the JPEG COM marker.
    dpi : tuple of int
        Horizontal and vertical DPI (default (72, 72)).
    units : int
        Density units: 0=no units, 1=DPI, 2=DPCM (default 1).
    optimize_huffman : bool
        Whether to optimize Huffman tables (future feature).
    """

    quality: int = 85
    sampling: str = "4:2:0"
    restart_interval: int = 0
    comment: Optional[str] = None
    dpi: Tuple[int, int] = (72, 72)
    units: int = 1
    optimize_huffman: bool = False

    def __post_init__(self):
        self.validate()

    def validate(self) -> "EncodingConfig":
        """Validate all fields; raise on invalid values."""
        if not isinstance(self.quality, int) or not 1 <= self.quality <= 100:
            raise InvalidQualityError(self.quality)
        if self.sampling not in _VALID_SAMPLING:
            raise InvalidSamplingError(self.sampling)
        if not isinstance(self.restart_interval, int) or self.restart_interval < 0:
            raise ValueError(
                f"restart_interval must be non-negative, got {self.restart_interval}"
            )
        if self.units not in (0, 1, 2):
            raise ValueError(
                f"units must be 0, 1, or 2, got {self.units}"
            )
        return self

    def to_dict(self) -> dict:
        """Serialize to a plain dict."""
        d = asdict(self)
        d["dpi"] = list(d["dpi"])  # tuples -> lists for JSON
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "EncodingConfig":
        """Create from a dict, ignoring unknown keys."""
        known = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in known}
        if "dpi" in filtered and isinstance(filtered["dpi"], list):
            filtered["dpi"] = tuple(filtered["dpi"])
        return cls(**filtered)


def load_config(path: str) -> EncodingConfig:
    """Load an EncodingConfig from a file.

    Supports ``.json``, ``.yaml``/``.yml``, and ``.toml`` formats.
    The format is detected by the file extension.
    """
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as f:
        text = f.read()

    if ext == ".json":
        data = json.loads(text)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "PyYAML is required to load YAML config files"
            ) from exc
        data = yaml.safe_load(text)
    elif ext == ".toml":
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError as exc:
                raise ImportError(
                    "tomli is required to load TOML config files on Python < 3.11"
                ) from exc
        data = tomllib.loads(text)
    else:
        raise ValueError(
            f"Unsupported config format '{ext}'. "
            "Use .json, .yaml/.yml, or .toml"
        )

    return EncodingConfig.from_dict(data)


def save_config(config: EncodingConfig, path: str) -> None:
    """Save an EncodingConfig to a file (JSON or YAML)."""
    ext = os.path.splitext(path)[1].lower()
    data = config.to_dict()

    if ext == ".json":
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    elif ext in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                "PyYAML is required to save YAML config files"
            ) from exc
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
    else:
        raise ValueError(
            f"Unsupported config format '{ext}'. Use .json or .yaml/.yml"
        )