"""
Configuration management for waveform-synth.

Supports loading synthesizer configurations from JSON/TOML files,
enabling reproducible audio presets and project settings.
"""

import json
import os
from typing import Any, Dict, Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


class SynthConfig:
    """
    Synthesizer configuration.

    Holds all parameters for generating audio: oscillator settings,
    envelope, effects chain, and export options.

    Can be loaded from JSON or TOML files for reproducible presets.

    Args:
        config_dict: Dictionary of configuration values.
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self._config = config_dict or {}

    # ─── Oscillator Settings ──────────────────────────────────────────

    @property
    def waveform(self) -> str:
        """Waveform type (sine, square, sawtooth, triangle, noise, pulse, white_noise)."""
        return self._config.get('waveform', 'sine')

    @property
    def frequency(self) -> float:
        """Oscillator frequency in Hz."""
        return self._config.get('frequency', 440.0)

    @property
    def amplitude(self) -> float:
        """Oscillator amplitude (0.0-1.0)."""
        return self._config.get('amplitude', 0.8)

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self._config.get('duration', 2.0)

    @property
    def sample_rate(self) -> int:
        """Sample rate in Hz."""
        return self._config.get('sample_rate', 44100)

    @property
    def harmonics(self) -> list:
        """List of [ratio, amplitude] pairs for additive synthesis."""
        return self._config.get('harmonics', [])

    # ─── Envelope Settings ─────────────────────────────────────────────

    @property
    def attack(self) -> float:
        """ADSR attack time in seconds."""
        return self._config.get('attack', 0.01)

    @property
    def decay(self) -> float:
        """ADSR decay time in seconds."""
        return self._config.get('decay', 0.1)

    @property
    def sustain(self) -> float:
        """ADSR sustain level (0.0-1.0)."""
        return self._config.get('sustain', 0.7)

    @property
    def release(self) -> float:
        """ADSR release time in seconds."""
        return self._config.get('release', 0.3)

    @property
    def envelope_curve(self) -> str:
        """Envelope curve type: 'linear' or 'exponential'."""
        return self._config.get('envelope_curve', 'linear')

    # ─── FM Settings ───────────────────────────────────────────────────

    @property
    def carrier_freq(self) -> float:
        """FM carrier frequency in Hz."""
        return self._config.get('carrier_freq', 440.0)

    @property
    def modulator_freq(self) -> float:
        """FM modulator frequency in Hz."""
        return self._config.get('modulator_freq', 440.0)

    @property
    def modulation_index(self) -> float:
        """FM modulation index."""
        return self._config.get('modulation_index', 2.0)

    @property
    def fm_preset(self) -> Optional[str]:
        """FM preset name (bellish, brassish, woodwind, bass, e_piano)."""
        return self._config.get('fm_preset')

    # ─── Effects Settings ──────────────────────────────────────────────

    @property
    def effects(self) -> list:
        """List of effect configurations."""
        return self._config.get('effects', [])

    # ─── Export Settings ────────────────────────────────────────────────

    @property
    def output(self) -> Optional[str]:
        """Output file path."""
        return self._config.get('output')

    @property
    def bits_per_sample(self) -> int:
        """Bit depth for WAV export (8, 16, 24, 32)."""
        return self._config.get('bits_per_sample', 16)

    @property
    def stereo(self) -> bool:
        """Whether to export as stereo."""
        return self._config.get('stereo', False)

    @property
    def pan(self) -> float:
        """Stereo panning (-1.0 to 1.0)."""
        return self._config.get('pan', 0.0)

    # ─── Analysis Settings ─────────────────────────────────────────────

    @property
    def visualize(self) -> bool:
        """Whether to show ASCII visualization."""
        return self._config.get('visualize', False)

    @property
    def analyze(self) -> bool:
        """Whether to print audio analysis."""
        return self._config.get('analyze', False)

    # ─── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary."""
        return dict(self._config)

    def to_json(self, filepath: str):
        """Save configuration to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self._config, f, indent=2)

    @classmethod
    def from_json(cls, filepath: str) -> 'SynthConfig':
        """Load configuration from a JSON file."""
        with open(filepath, 'r') as f:
            config = json.load(f)
        return cls(config)

    @classmethod
    def from_toml(cls, filepath: str) -> 'SynthConfig':
        """Load configuration from a TOML file."""
        if tomllib is None:
            raise ImportError(
                "TOML support requires Python 3.11+ (tomllib) or the 'tomli' package. "
                "Install it with: pip install tomli"
            )
        with open(filepath, 'rb') as f:
            config = tomllib.load(f)
        return cls(config)

    @classmethod
    def from_file(cls, filepath: str) -> 'SynthConfig':
        """
        Load configuration from a JSON or TOML file based on extension.

        Args:
            filepath: Path to config file (.json or .toml).

        Returns:
            SynthConfig instance.
        """
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.json':
            return cls.from_json(filepath)
        elif ext == '.toml':
            return cls.from_toml(filepath)
        else:
            raise ValueError(f"Unsupported config file format: {ext}. Use .json or .toml")

    def __repr__(self):
        keys = list(self._config.keys())
        return f"SynthConfig({keys})"


# ─── Built-in Presets ──────────────────────────────────────────────────────

PRESETS: Dict[str, Dict[str, Any]] = {
    "ambient_pad": {
        "waveform": "sine",
        "frequency": 220.0,
        "amplitude": 0.6,
        "duration": 4.0,
        "attack": 0.5,
        "decay": 0.3,
        "sustain": 0.5,
        "release": 2.0,
        "envelope_curve": "exponential",
        "effects": [
            {"type": "reverb", "room_size": 0.9, "damping": 0.3, "wet": 0.4},
            {"type": "lowpass", "cutoff": 2000.0},
        ],
    },
    "harsh_lead": {
        "waveform": "sawtooth",
        "frequency": 330.0,
        "amplitude": 0.7,
        "duration": 2.0,
        "attack": 0.01,
        "decay": 0.05,
        "sustain": 0.9,
        "release": 0.2,
        "effects": [
            {"type": "distortion", "drive": 3.0},
            {"type": "lowpass", "cutoff": 5000.0},
        ],
    },
    "deep_bass": {
        "waveform": "sine",
        "frequency": 55.0,
        "amplitude": 0.9,
        "duration": 1.0,
        "attack": 0.01,
        "decay": 0.2,
        "sustain": 0.7,
        "release": 0.3,
        "effects": [
            {"type": "compressor", "threshold": 0.5, "ratio": 4.0},
        ],
    },
    "bell_tone": {
        "fm_preset": "bellish",
        "carrier_freq": 440.0,
        "duration": 3.0,
        "amplitude": 0.7,
        "attack": 0.005,
        "decay": 0.5,
        "sustain": 0.2,
        "release": 1.5,
        "envelope_curve": "exponential",
    },
    "epiano": {
        "fm_preset": "e_piano",
        "carrier_freq": 440.0,
        "duration": 2.0,
        "amplitude": 0.75,
        "attack": 0.005,
        "decay": 0.3,
        "sustain": 0.4,
        "release": 0.8,
    },
}


def get_preset(name: str) -> SynthConfig:
    """
    Get a built-in preset configuration.

    Args:
        name: Preset name (ambient_pad, harsh_lead, deep_bass, bell_tone, epiano).

    Returns:
        SynthConfig with preset values.

    Raises:
        ValueError: If the preset name is not found.
    """
    if name not in PRESETS:
        raise ValueError(f"Unknown preset '{name}'. Available: {list(PRESETS.keys())}")
    return SynthConfig(PRESETS[name])


__all__ = ['SynthConfig', 'PRESETS', 'get_preset']