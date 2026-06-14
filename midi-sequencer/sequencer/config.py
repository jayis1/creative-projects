"""Configuration management for the MIDI Step Sequencer.

Supports loading configuration from YAML, TOML, or JSON files,
with sensible defaults and validation.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULTS = {
    "bpm": 120,
    "ppqn": 480,
    "time_signature": [4, 4],
    "swing": 0.0,
    "default_root": "C",
    "default_scale": "pentatonic_minor",
    "default_octave": 4,
    "default_velocity": 100,
    "default_gate": 0.8,
    "default_length": 16,
    "humanize_velocity": 0.0,
    "humanize_timing": 0.0,
    "default_channel": 0,
    "default_program": 0,
    "add_metronome": False,
    "output_dir": ".",
    "midi_filename_template": "{name}_{bpm}bpm_{key}{scale}.mid",
    "logging_level": "WARNING",
}


@dataclass
class SequencerConfig:
    """Configuration for the MIDI Step Sequencer.

    Can be loaded from a YAML, TOML, or JSON configuration file.
    All fields have sensible defaults so the sequencer works out of the box.

    Attributes:
        bpm: Default tempo in beats per minute
        ppqn: MIDI pulses per quarter note (resolution)
        time_signature: Default time signature as [beats, beat_unit]
        swing: Default swing amount (0.0 = none, up to ~0.3)
        default_root: Default root note (e.g. 'C', 'F#', 'Bb')
        default_scale: Default scale name
        default_octave: Default starting octave
        default_velocity: Default note velocity (1-127)
        default_gate: Default gate length (0.0-1.0)
        default_length: Default pattern length in steps
        humanize_velocity: Default velocity humanization amount
        humanize_timing: Default timing humanization amount in ticks
        default_channel: Default MIDI channel (0-15)
        default_program: Default MIDI program number (0-127)
        add_metronome: Whether to add a metronome track by default
        output_dir: Default directory for output files
        midi_filename_template: Template for auto-generated filenames
        logging_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """

    bpm: int = 120
    ppqn: int = 480
    time_signature: List[int] = field(default_factory=lambda: [4, 4])
    swing: float = 0.0
    default_root: str = "C"
    default_scale: str = "pentatonic_minor"
    default_octave: int = 4
    default_velocity: int = 100
    default_gate: float = 0.8
    default_length: int = 16
    humanize_velocity: float = 0.0
    humanize_timing: float = 0.0
    default_channel: int = 0
    default_program: int = 0
    add_metronome: bool = False
    output_dir: str = "."
    midi_filename_template: str = "{name}_{bpm}bpm_{key}{scale}.mid"
    logging_level: str = "WARNING"

    def __post_init__(self):
        """Validate configuration values after initialization."""
        self._validate()

    def _validate(self):
        """Validate all configuration values and raise ValueError for invalid ones."""
        if not 20 <= self.bpm <= 300:
            raise ValueError(f"BPM must be between 20 and 300, got {self.bpm}")
        if self.ppqn not in (96, 120, 240, 480, 960):
            logger.warning(f"Unusual PPQN value: {self.ppqn}. Common values: 96, 120, 240, 480, 960")
        if len(self.time_signature) != 2:
            raise ValueError(f"time_signature must have 2 elements, got {len(self.time_signature)}")
        if self.time_signature[0] < 1 or self.time_signature[0] > 32:
            raise ValueError(f"Beats per bar must be 1-32, got {self.time_signature[0]}")
        if self.time_signature[1] not in (1, 2, 4, 8, 16, 32):
            raise ValueError(f"Beat unit must be a power of 2, got {self.time_signature[1]}")
        if not 0.0 <= self.swing <= 0.5:
            raise ValueError(f"Swing must be 0.0-0.5, got {self.swing}")
        if not 1 <= self.default_velocity <= 127:
            raise ValueError(f"Velocity must be 1-127, got {self.default_velocity}")
        if not 0.0 <= self.default_gate <= 1.0:
            raise ValueError(f"Gate must be 0.0-1.0, got {self.default_gate}")
        if self.default_length < 1:
            raise ValueError(f"Length must be >= 1, got {self.default_length}")
        if not 0 <= self.default_channel <= 15:
            raise ValueError(f"Channel must be 0-15, got {self.default_channel}")
        if not 0 <= self.default_program <= 127:
            raise ValueError(f"Program must be 0-127, got {self.default_program}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary."""
        return asdict(self)

    def to_json(self, path: str) -> str:
        """Save configuration to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SequencerConfig":
        """Create a SequencerConfig from a dictionary, ignoring unknown keys."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    @classmethod
    def from_json(cls, path: str) -> "SequencerConfig":
        """Load configuration from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, path: str) -> "SequencerConfig":
        """Load configuration from a YAML file."""
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML config. Install with: pip install pyyaml")
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        if data is None:
            data = {}
        return cls.from_dict(data)

    @classmethod
    def from_toml(cls, path: str) -> "SequencerConfig":
        """Load configuration from a TOML file."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                raise ImportError("TOML support requires Python 3.11+ or the tomli package")
        with open(path, "rb") as f:
            data = tomllib.load(f)
        # Flatten if nested under [sequencer] section
        if "sequencer" in data:
            data = {**data["sequencer"], **{k: v for k, v in data.items() if k != "sequencer"}}
        return cls.from_dict(data)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "SequencerConfig":
        """Load configuration from a file, auto-detecting format by extension.

        If path is None, looks for config files in this order:
        1. .midi-sequencer.yaml
        2. .midi-sequencer.toml
        3. .midi-sequencer.json
        4. midi-sequencer.yaml / midi-sequencer.toml / midi-sequencer.json

        Returns default config if no file found.
        """
        if path:
            ext = Path(path).suffix.lower()
            if ext in (".yaml", ".yml"):
                return cls.from_yaml(path)
            elif ext == ".toml":
                return cls.from_toml(path)
            elif ext == ".json":
                return cls.from_json(path)
            else:
                # Try all formats
                for loader in (cls.from_json, cls.from_yaml, cls.from_toml):
                    try:
                        return loader(path)
                    except Exception:
                        continue
                raise ValueError(f"Cannot load config from {path}: unknown format")

        # Auto-discover config file
        search_names = [
            ".midi-sequencer.yaml", ".midi-sequencer.yml",
            ".midi-sequencer.toml", ".midi-sequencer.json",
            "midi-sequencer.yaml", "midi-sequencer.yml",
            "midi-sequencer.toml", "midi-sequencer.json",
        ]
        for name in search_names:
            for search_dir in (os.getcwd(), Path.home()):
                candidate = Path(search_dir) / name
                if candidate.exists():
                    logger.info(f"Loading config from {candidate}")
                    return cls.load(str(candidate))

        return cls()  # Default config

    def apply_to_song(self, song) -> None:
        """Apply configuration defaults to a Song object."""
        from sequencer.patterns import Song
        if not isinstance(song, Song):
            raise TypeError(f"Expected Song, got {type(song)}")
        song.bpm = self.bpm
        song.ppqn = self.ppqn
        song.time_signature = tuple(self.time_signature)
        song.swing = self.swing


def generate_default_config(path: str, fmt: str = "yaml") -> str:
    """Generate a default configuration file at the given path.

    Args:
        path: Output file path
        fmt: Format to use ('yaml', 'toml', or 'json')

    Returns:
        The path written
    """
    config = SequencerConfig()
    if fmt == "yaml":
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML required. Install with: pip install pyyaml")
        with open(path, "w") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)
    elif fmt == "toml":
        try:
            import tomli_w
        except ImportError:
            # Fallback: write as JSON-like TOML manually
            lines = ["# MIDI Step Sequencer Configuration\n"]
            for key, value in config.to_dict().items():
                if isinstance(value, str):
                    lines.append(f'{key} = "{value}"')
                elif isinstance(value, bool):
                    lines.append(f'{key} = {str(value).lower()}')
                elif isinstance(value, list):
                    lines.append(f'{key} = {value}')
                else:
                    lines.append(f'{key} = {value}')
            with open(path, "w") as f:
                f.write("\n".join(lines))
    else:
        config.to_json(path)
    return path