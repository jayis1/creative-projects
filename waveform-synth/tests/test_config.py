"""Tests for the config module."""

import os
import json
import tempfile
import pytest

from waveform_synth.config import SynthConfig, PRESETS, get_preset


class TestSynthConfig:
    def test_default_values(self):
        """Default config should have sensible defaults."""
        config = SynthConfig()
        assert config.waveform == 'sine'
        assert config.frequency == 440.0
        assert config.amplitude == 0.8
        assert config.duration == 2.0
        assert config.sample_rate == 44100
        assert config.attack == 0.01
        assert config.decay == 0.1
        assert config.sustain == 0.7
        assert config.release == 0.3

    def test_custom_values(self):
        """Config should accept custom values."""
        config = SynthConfig({
            'waveform': 'sawtooth',
            'frequency': 220.0,
            'duration': 5.0,
        })
        assert config.waveform == 'sawtooth'
        assert config.frequency == 220.0
        assert config.duration == 5.0

    def test_to_dict(self):
        """to_dict should return the config dictionary."""
        config = SynthConfig({'waveform': 'sine', 'frequency': 440.0})
        d = config.to_dict()
        assert 'waveform' in d
        assert 'frequency' in d
        assert d['waveform'] == 'sine'
        assert d['frequency'] == 440.0

    def test_to_json(self):
        """Should save config to JSON file."""
        config = SynthConfig({'waveform': 'triangle', 'frequency': 330.0})
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            filepath = f.name
        try:
            config.to_json(filepath)
            assert os.path.exists(filepath)
            with open(filepath) as f:
                loaded = json.load(f)
            assert loaded['waveform'] == 'triangle'
            assert loaded['frequency'] == 330.0
        finally:
            os.unlink(filepath)

    def test_from_json(self):
        """Should load config from JSON file."""
        data = {'waveform': 'square', 'frequency': 220.0, 'amplitude': 0.5}
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            filepath = f.name
            json.dump(data, f)

        try:
            config = SynthConfig.from_json(filepath)
            assert config.waveform == 'square'
            assert config.frequency == 220.0
            assert config.amplitude == 0.5
        finally:
            os.unlink(filepath)

    def test_from_file_json(self):
        """from_file should detect JSON extension."""
        data = {'waveform': 'sine', 'frequency': 880.0}
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            filepath = f.name
            json.dump(data, f)

        try:
            config = SynthConfig.from_file(filepath)
            assert config.frequency == 880.0
        finally:
            os.unlink(filepath)

    def test_from_file_unsupported(self):
        """from_file should raise ValueError for unsupported formats."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            filepath = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported config file format"):
                SynthConfig.from_file(filepath)
        finally:
            os.unlink(filepath)

    def test_repr(self):
        """repr should show config keys."""
        config = SynthConfig({'waveform': 'sine'})
        assert 'SynthConfig' in repr(config)

    def test_effects_property(self):
        """Effects should be loaded from config."""
        config = SynthConfig({
            'effects': [
                {'type': 'reverb', 'room_size': 0.8},
                {'type': 'compressor', 'threshold': 0.5},
            ]
        })
        assert len(config.effects) == 2

    def test_stereo_property(self):
        """Stereo should default to False."""
        config = SynthConfig()
        assert config.stereo is False

    def test_analyze_property(self):
        """Analyze should default to False."""
        config = SynthConfig()
        assert config.analyze is False


class TestPresets:
    def test_preset_names(self):
        """All expected presets should exist."""
        expected = ['ambient_pad', 'harsh_lead', 'deep_bass', 'bell_tone', 'epiano']
        for name in expected:
            assert name in PRESETS

    def test_get_preset(self):
        """get_preset should return valid config."""
        config = get_preset('ambient_pad')
        assert config.waveform == 'sine'
        assert config.frequency == 220.0
        assert config.duration == 4.0

    def test_get_preset_invalid(self):
        """get_preset should raise ValueError for unknown preset."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset('nonexistent_preset')

    def test_all_presets_have_required_fields(self):
        """All presets should have required fields."""
        for name, preset_data in PRESETS.items():
            config = SynthConfig(preset_data)
            # All should have at least waveform or fm_preset
            assert config.waveform or config.fm_preset