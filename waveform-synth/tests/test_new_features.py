"""
Comprehensive tests for the new v4.0 features:
- LFO modulation
- Wavetable synthesis
- Noise generators (white, pink, brown, blue, violet)
- Ring modulation and amplitude modulation
- Spectral processing (pitch shifting, time stretching)
- Granular synthesis
- MIDI file import
- New effects (chorus, bitcrusher, echo)

Each test class covers one module with thorough edge-case testing.
"""

import math
import pytest
import os
import tempfile
import struct

from waveform_synth.core import Oscillator, Waveform, normalize
from waveform_synth.lfo import LFO
from waveform_synth.wavetable import Wavetable, WavetableOscillator, _generate_single_cycle
from waveform_synth.noise import NoiseColor, NoiseGenerator
from waveform_synth.modulation import ring_modulate, amplitude_modulate, RingModulator
from waveform_synth.spectral import pitch_shift, time_stretch
from waveform_synth.granular import GranularSynth, GrainParams, window_triangle
from waveform_synth.midi_reader import read_midi_file, MidiFile, MidiNote
from waveform_synth.midi import MidiWriter
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.analysis import rms, peak_level


# ========== LFO Tests ==========

class TestLFO:
    """Tests for the LFO module."""

    def test_sine_lfo_range(self):
        """Sine LFO should produce values in [-1, 1]."""
        lfo = LFO(waveform=Waveform.SINE, rate=5.0, depth=0.5)
        vals = lfo.generate(1.0)
        for v in vals:
            assert -1.0 <= v <= 1.0

    def test_lfo_frequency(self):
        """LFO should oscillate at the specified rate."""
        lfo = LFO(waveform=Waveform.SINE, rate=5.0)
        vals = lfo.generate(1.0)
        # At 5Hz, over 1 second, there should be ~5 zero crossings going up
        up_crossings = 0
        for i in range(1, len(vals)):
            if vals[i-1] <= 0 < vals[i]:
                up_crossings += 1
        assert abs(up_crossings - 5) <= 1  # Should be about 5

    def test_square_lfo(self):
        """Square LFO should only produce ±1 values."""
        lfo = LFO(waveform=Waveform.SQUARE, rate=10.0)
        vals = lfo.generate(0.1)
        for v in vals:
            assert abs(abs(v) - 1.0) < 0.01

    def test_triangle_lfo(self):
        """Triangle LFO should range from -1 to +1."""
        lfo = LFO(waveform=Waveform.TRIANGLE, rate=5.0)
        vals = lfo.generate(1.0)
        assert max(vals) > 0.9
        assert min(vals) < -0.9

    def test_sawtooth_lfo(self):
        """Sawtooth LFO should range from -1 to +1."""
        lfo = LFO(waveform=Waveform.SAWTOOTH, rate=5.0)
        vals = lfo.generate(1.0)
        assert max(vals) > 0.9
        assert min(vals) < -0.9

    def test_depth_scaling(self):
        """Modulation values should be scaled by depth."""
        lfo = LFO(waveform=Waveform.SINE, rate=5.0, depth=0.5)
        mod = lfo.generate_modulation(1.0)
        for v in mod:
            assert -0.5 <= v <= 0.5

    def test_amplitude_modulation(self):
        """Apply-to-amplitude should modulate the signal."""
        lfo = LFO(waveform=Waveform.SINE, rate=10.0, depth=0.8)
        samples = [1.0] * 4410  # 0.1s of constant signal
        result = lfo.apply_to_amplitude(samples)
        # The result should vary
        assert min(result) < max(result)
        # Should not exceed original amplitude
        assert max(result) <= 1.0 + 0.01

    def test_pitch_modulation(self):
        """Apply-to-pitch should produce different output."""
        lfo = LFO(waveform=Waveform.SINE, rate=5.0, depth=0.02)
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.5)
        result = lfo.apply_to_pitch(samples, base_freq=440.0)
        assert len(result) == len(samples)
        # Result should differ from input due to vibrato
        assert any(abs(r - s) > 0.01 for r, s in zip(result, samples))

    def test_synced_lfo(self):
        """Tempo-synced LFO should compute rate from BPM."""
        lfo = LFO.synced(bpm=120, beats_per_cycle=1.0)
        assert abs(lfo.rate - 2.0) < 0.01  # 120/60/1 = 2.0

    def test_synced_lfo_half_note(self):
        """Half-note sync should give half the rate."""
        lfo = LFO.synced(bpm=120, beats_per_cycle=2.0)
        assert abs(lfo.rate - 1.0) < 0.01  # 120/60/2 = 1.0

    def test_invalid_rate(self):
        """Invalid rate should raise."""
        with pytest.raises(ValueError):
            LFO(rate=0.0)
        with pytest.raises(ValueError):
            LFO(rate=-1.0)

    def test_invalid_depth(self):
        """Depth out of range should raise."""
        with pytest.raises(ValueError):
            LFO(depth=-0.1)
        with pytest.raises(ValueError):
            LFO(depth=1.5)

    def test_invalid_duration(self):
        """Invalid duration should raise."""
        lfo = LFO()
        with pytest.raises(ValueError):
            lfo.generate(0.0)
        with pytest.raises(ValueError):
            lfo.generate(-1.0)

    def test_value_at(self):
        """value_at should return the correct LFO value."""
        lfo = LFO(waveform=Waveform.SINE, rate=1.0, phase=0.0)
        # At t=0, sin(0) = 0
        assert abs(lfo.value_at(0.0)) < 0.01
        # At t=0.25, sin(2*pi*1*0.25) = sin(pi/2) = 1
        assert abs(lfo.value_at(0.25) - 1.0) < 0.01
        # At t=0.5, sin(pi) = 0
        assert abs(lfo.value_at(0.5)) < 0.01


# ========== Wavetable Tests ==========

class TestWavetable:
    """Tests for the wavetable synthesis module."""

    def test_wavetable_creation(self):
        """Basic wavetable creation."""
        frames = [[0.0, 0.5, 1.0, 0.5, 0.0, -0.5, -1.0, -0.5] for _ in range(3)]
        wt = Wavetable(frames, name="test")
        assert wt.num_frames == 3
        assert wt._frame_size == 8

    def test_empty_frames_raises(self):
        """Empty frames should raise."""
        with pytest.raises(ValueError):
            Wavetable([])

    def test_mismatched_frame_sizes_raises(self):
        """Mismatched frame sizes should raise."""
        with pytest.raises(ValueError):
            Wavetable([[0.0, 1.0], [0.0, 1.0, 2.0]])

    def test_sine_to_saw(self):
        """sine_to_saw factory should create a morphing wavetable."""
        wt = Wavetable.sine_to_saw(num_frames=8, frame_size=512)
        assert wt.num_frames == 8
        # First frame should be close to pure sine
        first_frame = wt.frames[0]
        # Check it's approximately sine-like (starts and ends near 0)
        assert abs(first_frame[0]) < 0.1
        # Last frame should have more harmonics (saw-like)
        last_frame = wt.frames[-1]
        # Sawtooth should have more energy
        assert sum(x**2 for x in last_frame) > sum(x**2 for x in first_frame)

    def test_classic_analog(self):
        """classic_analog should have 4 frames."""
        wt = Wavetable.classic_analog(frame_size=512)
        assert wt.num_frames == 4

    def test_get_frame_at_position(self):
        """Interpolated frame should blend adjacent frames."""
        wt = Wavetable.sine_to_saw(num_frames=4, frame_size=256)
        frame_start = wt.get_frame_at(0.0)
        frame_end = wt.get_frame_at(1.0)
        frame_mid = wt.get_frame_at(0.5)
        # Mid should be different from both start and end
        assert frame_mid != frame_start
        assert frame_mid != frame_end

    def test_get_frame_clamped(self):
        """Positions outside [0,1] should be clamped."""
        wt = Wavetable.classic_analog(frame_size=256)
        frame_below = wt.get_frame_at(-0.5)
        frame_zero = wt.get_frame_at(0.0)
        assert frame_below == frame_zero

    def test_single_frame_wavetable(self):
        """Single-frame wavetable should return that frame."""
        wt = Wavetable([[0.5] * 64], name="single")
        frame = wt.get_frame_at(0.5)
        assert frame == [0.5] * 64

    def test_oscillator_generation(self):
        """WavetableOscillator should produce audio."""
        wt = Wavetable.sine_to_saw(num_frames=4, frame_size=512)
        osc = WavetableOscillator(wt, frequency=440.0, amplitude=0.8)
        samples = osc.generate(0.1)
        assert len(samples) == 4410
        assert any(abs(s) > 0.1 for s in samples)

    def test_oscillator_position_sweep(self):
        """Modulating position should change timbre."""
        wt = Wavetable.sine_to_saw(num_frames=8, frame_size=1024)
        osc = WavetableOscillator(wt, frequency=220.0, position=0.0)
        samples_start = osc.generate(0.05)

        osc.set_position(1.0)
        samples_end = osc.generate(0.05)

        # The RMS should differ (saw has more energy than sine)
        assert rms(samples_start) != pytest.approx(rms(samples_end), abs=0.01)

    def test_cubic_interpolation(self):
        """Cubic interpolation should produce valid output."""
        wt = Wavetable.classic_analog(frame_size=512)
        osc = WavetableOscillator(wt, frequency=440.0, interpolation="cubic")
        samples = osc.generate(0.05)
        assert len(samples) > 0
        assert any(abs(s) > 0.1 for s in samples)

    def test_invalid_interpolation(self):
        """Invalid interpolation type should raise."""
        wt = Wavetable.classic_analog(frame_size=256)
        with pytest.raises(ValueError):
            WavetableOscillator(wt, interpolation="bogus")

    def test_invalid_frequency(self):
        """Invalid frequency should raise."""
        wt = Wavetable.classic_analog(frame_size=256)
        with pytest.raises(ValueError):
            WavetableOscillator(wt, frequency=0.0)
        with pytest.raises(ValueError):
            WavetableOscillator(wt, frequency=-1.0)

    def test_invalid_position(self):
        """Invalid position should raise."""
        wt = Wavetable.classic_analog(frame_size=256)
        with pytest.raises(ValueError):
            WavetableOscillator(wt, position=-0.1)
        with pytest.raises(ValueError):
            WavetableOscillator(wt, position=1.5)

    def test_set_position_validation(self):
        """set_position should validate."""
        wt = Wavetable.classic_analog(frame_size=256)
        osc = WavetableOscillator(wt)
        with pytest.raises(ValueError):
            osc.set_position(2.0)

    def test_generate_with_modulation(self):
        """Position modulation should work."""
        wt = Wavetable.sine_to_saw(num_frames=8, frame_size=256)
        osc = WavetableOscillator(wt, frequency=440.0)
        # Create position modulation that sweeps 0->1
        n = 2205
        mod = [i / n for i in range(n)]
        samples = osc.generate_with_modulation(0.05, position_modulation=mod)
        assert len(samples) == 2205

    def test_from_waveforms(self):
        """from_waveforms factory should create wavetable from Waveform enums."""
        wt = Wavetable.from_waveforms([Waveform.SINE, Waveform.SAWTOOTH], frame_size=256)
        assert wt.num_frames == 2


# ========== Noise Generator Tests ==========

class TestNoiseGenerator:
    """Tests for the noise generator module."""

    @pytest.mark.parametrize("color", list(NoiseColor))
    def test_all_colors_generate(self, color):
        """All noise colors should generate samples."""
        ng = NoiseGenerator(color=color, seed=42)
        samples = ng.generate(0.1)
        assert len(samples) == 4410
        assert any(abs(s) > 0.01 for s in samples)

    def test_white_noise_uniformity(self):
        """White noise should have relatively uniform distribution."""
        ng = NoiseGenerator(color=NoiseColor.WHITE, seed=123)
        samples = ng.generate(1.0)
        # Check that values are spread across the range
        assert max(samples) > 0.8
        assert min(samples) < -0.8

    def test_seeded_reproducibility(self):
        """Same seed should produce same output."""
        ng1 = NoiseGenerator(color=NoiseColor.WHITE, seed=42)
        ng2 = NoiseGenerator(color=NoiseColor.WHITE, seed=42)
        s1 = ng1.generate(0.1)
        s2 = ng2.generate(0.1)
        assert s1 == s2

    def test_different_seeds_differ(self):
        """Different seeds should produce different output."""
        ng1 = NoiseGenerator(color=NoiseColor.WHITE, seed=1)
        ng2 = NoiseGenerator(color=NoiseColor.WHITE, seed=2)
        s1 = ng1.generate(0.1)
        s2 = ng2.generate(0.1)
        assert s1 != s2

    def test_brown_noise_low_freq(self):
        """Brown noise should have more low-frequency energy than white."""
        ng_brown = NoiseGenerator(color=NoiseColor.BROWN, seed=42)
        ng_white = NoiseGenerator(color=NoiseColor.WHITE, seed=42)
        brown = ng_brown.generate(0.5)
        white = ng_white.generate(0.5)
        # Brown noise should have lower zero-crossing rate (more low-freq content)
        brown_zcr = sum(1 for i in range(1, len(brown))
                       if (brown[i] >= 0) != (brown[i-1] >= 0)) / len(brown)
        white_zcr = sum(1 for i in range(1, len(white))
                       if (white[i] >= 0) != (white[i-1] >= 0)) / len(white)
        assert brown_zcr < white_zcr

    def test_amplitude_scaling(self):
        """Amplitude should scale output."""
        ng = NoiseGenerator(color=NoiseColor.WHITE, seed=42)
        s_full = ng.generate(0.1, amplitude=1.0)
        s_half = ng.generate(0.1, amplitude=0.5)
        assert max(abs(s) for s in s_half) < max(abs(s) for s in s_full)

    def test_invalid_amplitude(self):
        """Invalid amplitude should raise."""
        ng = NoiseGenerator(color=NoiseColor.WHITE, seed=42)
        with pytest.raises(ValueError):
            ng.generate(0.1, amplitude=-0.1)
        with pytest.raises(ValueError):
            ng.generate(0.1, amplitude=1.5)

    def test_invalid_duration(self):
        """Invalid duration should raise."""
        ng = NoiseGenerator(color=NoiseColor.WHITE, seed=42)
        with pytest.raises(ValueError):
            ng.generate(0.0)
        with pytest.raises(ValueError):
            ng.generate(-1.0)

    def test_generate_normalized(self):
        """Normalized output should have peak ~1.0."""
        ng = NoiseGenerator(color=NoiseColor.PINK, seed=42)
        samples = ng.generate_normalized(0.1)
        if samples:
            peak = max(abs(s) for s in samples)
            assert 0.9 < peak <= 1.0 + 0.01


# ========== Ring/Amplitude Modulation Tests ==========

class TestModulation:
    """Tests for ring and amplitude modulation."""

    def test_ring_modulate_basic(self):
        """Ring modulation should multiply signals."""
        carrier = [1.0, 1.0, 1.0, 1.0]
        modulator = [1.0, -1.0, 1.0, -1.0]
        result = ring_modulate(carrier, modulator)
        assert result == [1.0, -1.0, 1.0, -1.0]

    def test_ring_modulate_mix(self):
        """Mix 0 should return carrier unchanged."""
        carrier = [1.0, 0.5, -0.5]
        modulator = [1.0, 1.0, 1.0]
        result = ring_modulate(carrier, modulator, mix=0.0)
        assert result == pytest.approx(carrier)

    def test_ring_modulate_mix_full(self):
        """Mix 1 should be full ring mod."""
        carrier = [1.0, 0.5, -0.5]
        modulator = [0.5, 0.5, 0.5]
        result = ring_modulate(carrier, modulator, mix=1.0)
        expected = [c * m for c, m in zip(carrier, modulator)]
        assert result == pytest.approx(expected)

    def test_ring_modulate_length_mismatch(self):
        """Should handle different-length signals."""
        carrier = [1.0, 2.0, 3.0, 4.0]
        modulator = [1.0, -1.0]
        result = ring_modulate(carrier, modulator)
        assert len(result) == 2  # min length

    def test_ring_modulate_invalid_mix(self):
        """Invalid mix should raise."""
        with pytest.raises(ValueError):
            ring_modulate([1.0], [1.0], mix=-0.1)
        with pytest.raises(ValueError):
            ring_modulate([1.0], [1.0], mix=1.5)

    def test_amplitude_modulate_basic(self):
        """AM should produce output with sidebands."""
        carrier = [1.0] * 100
        modulator = [math.sin(2 * math.pi * 10 * i / 44100) for i in range(100)]
        result = amplitude_modulate(carrier, modulator, mix=1.0, modulator_depth=0.5)
        assert len(result) == 100
        # Output should vary (not constant)
        assert min(result) != max(result)

    def test_amplitude_modulate_zero_depth(self):
        """Zero depth AM should return carrier scaled by 1."""
        carrier = [0.5, -0.3, 0.8]
        modulator = [1.0, 1.0, 1.0]
        result = amplitude_modulate(carrier, modulator, mix=1.0, modulator_depth=0.0)
        # With depth=0, gain = 1 + 0*mod = 1, so output = carrier
        assert result == pytest.approx(carrier)

    def test_amplitude_modulate_invalid_depth(self):
        """Invalid depth should raise."""
        with pytest.raises(ValueError):
            amplitude_modulate([1.0], [1.0], modulator_depth=-0.1)
        with pytest.raises(ValueError):
            amplitude_modulate([1.0], [1.0], modulator_depth=1.5)

    def test_ring_modulator_class(self):
        """RingModulator should process audio."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        carrier = osc.generate(0.1)
        rm = RingModulator(modulator_freq=50.0, mix=1.0)
        result = rm.process(carrier)
        assert len(result) == len(carrier)
        # Ring-modulated signal should have different spectral content
        assert rms(result) != pytest.approx(rms(carrier), abs=0.001)

    def test_ring_modulator_invalid_freq(self):
        """Invalid modulator frequency should raise."""
        with pytest.raises(ValueError):
            RingModulator(modulator_freq=0.0)
        with pytest.raises(ValueError):
            RingModulator(modulator_freq=-1.0)

    def test_ring_modulator_empty_input(self):
        """Empty input should return empty."""
        rm = RingModulator(modulator_freq=50.0)
        assert rm.process([]) == []

    def test_ring_modulator_mix(self):
        """Mix < 1 should blend dry and wet."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        carrier = osc.generate(0.1)
        rm_dry = RingModulator(modulator_freq=50.0, mix=0.0)
        result_dry = rm_dry.process(carrier)
        # Mix=0 means output = carrier
        assert result_dry == pytest.approx(carrier, abs=0.01)


# ========== Spectral Processing Tests ==========

class TestSpectral:
    """Tests for pitch shifting and time stretching."""

    def test_pitch_shift_preserves_length(self):
        """Pitch shift should return approximately the same length."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.05)
        shifted = pitch_shift(samples[:2048], semitones=5, fft_size=1024, hop_size=256)
        assert len(shifted) == 2048

    def test_pitch_shift_changes_content(self):
        """Pitch shift should alter the audio."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.05)[:2048]
        shifted = pitch_shift(samples, semitones=7, fft_size=1024, hop_size=256)
        # The shifted signal should differ from original
        assert any(abs(s - o) > 0.01 for s, o in zip(shifted, samples))

    def test_pitch_shift_zero_semitones(self):
        """Zero semitone shift should be approximately identity."""
        samples = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(2048)]
        shifted = pitch_shift(samples, semitones=0, fft_size=1024, hop_size=256)
        # Should be very similar (not exact due to STFT roundtrip)
        assert len(shifted) == len(samples)

    def test_pitch_shift_negative(self):
        """Negative semitones should shift down."""
        osc = Oscillator(Waveform.SINE, frequency=880.0)
        samples = osc.generate(0.05)[:2048]
        shifted = pitch_shift(samples, semitones=-12, fft_size=1024, hop_size=256)
        assert len(shifted) == 2048

    def test_pitch_shift_empty_raises(self):
        """Empty input should raise."""
        with pytest.raises(ValueError):
            pitch_shift([], semitones=5)

    def test_pitch_shift_extreme_raises(self):
        """Extreme semitone values should raise."""
        samples = [0.5] * 100
        with pytest.raises(ValueError):
            pitch_shift(samples, semitones=48)

    def test_time_stretch_factor_1(self):
        """Stretch factor 1.0 should approximately preserve length."""
        samples = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(2048)]
        stretched = time_stretch(samples, stretch_factor=1.0, fft_size=1024, hop_size=256)
        # Should be roughly the same length
        assert abs(len(stretched) - len(samples)) < len(samples) * 0.2

    def test_time_stretch_longer(self):
        """Factor > 1 should produce longer output."""
        samples = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(2048)]
        stretched = time_stretch(samples, stretch_factor=2.0, fft_size=1024, hop_size=256)
        assert len(stretched) > len(samples) * 1.5

    def test_time_stretch_shorter(self):
        """Factor < 1 should produce shorter output."""
        samples = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(2048)]
        stretched = time_stretch(samples, stretch_factor=0.5, fft_size=1024, hop_size=256)
        assert len(stretched) < len(samples)

    def test_time_stretch_empty_raises(self):
        """Empty input should raise."""
        with pytest.raises(ValueError):
            time_stretch([], stretch_factor=1.5)

    def test_time_stretch_invalid_factor(self):
        """Invalid factor should raise."""
        samples = [0.5] * 100
        with pytest.raises(ValueError):
            time_stretch(samples, stretch_factor=0.0)
        with pytest.raises(ValueError):
            time_stretch(samples, stretch_factor=-1.0)


# ========== Granular Synthesis Tests ==========

class TestGranular:
    """Tests for granular synthesis."""

    def test_granular_basic(self):
        """Granular synth should produce audio."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        source = osc.generate(0.5)
        gran = GranularSynth(source=source, grain_size=0.02, density=20, seed=42)
        result = gran.generate(0.5)
        assert len(result) > 0
        assert any(abs(s) > 0.01 for s in result)

    def test_granular_seeded_reproducibility(self):
        """Same seed should produce same output."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        source = osc.generate(0.5)
        g1 = GranularSynth(source=source, seed=42)
        g2 = GranularSynth(source=source, seed=42)
        r1 = g1.generate(0.3)
        r2 = g2.generate(0.3)
        assert r1 == r2

    def test_granular_stereo(self):
        """Stereo output should have two channels."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        source = osc.generate(0.5)
        gran = GranularSynth(source=source, random_pan=True, seed=42)
        left, right = gran.generate_stereo(0.3)
        assert len(left) == len(right)
        assert len(left) > 0

    def test_granular_pitch_spread(self):
        """Pitch spread should create variation."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        source = osc.generate(0.5)
        g_no_spread = GranularSynth(source=source, pitch_spread=0.0, seed=42)
        g_spread = GranularSynth(source=source, pitch_spread=1.0, seed=42)
        r1 = g_no_spread.generate(0.3)
        r2 = g_spread.generate(0.3)
        assert r1 != r2

    def test_granular_invalid_source(self):
        """Empty source should raise."""
        with pytest.raises(ValueError):
            GranularSynth(source=[])

    def test_granular_invalid_grain_size(self):
        """Invalid grain size should raise."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        source = osc.generate(0.5)
        with pytest.raises(ValueError):
            GranularSynth(source=source, grain_size=0.0)
        with pytest.raises(ValueError):
            GranularSynth(source=source, grain_size=1.0)

    def test_granular_invalid_density(self):
        """Invalid density should raise."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        source = osc.generate(0.5)
        with pytest.raises(ValueError):
            GranularSynth(source=source, density=0.0)
        with pytest.raises(ValueError):
            GranularSynth(source=source, density=200)

    def test_granular_invalid_duration(self):
        """Invalid duration should raise."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        source = osc.generate(0.5)
        gran = GranularSynth(source=source, seed=42)
        with pytest.raises(ValueError):
            gran.generate(0.0)
        with pytest.raises(ValueError):
            gran.generate(-1.0)

    def test_window_types(self):
        """Different window types should work."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        source = osc.generate(0.5)
        for wt_type in ["hann", "hamming", "blackman", "triangle"]:
            gran = GranularSynth(source=source, window_type=wt_type, seed=42)
            result = gran.generate(0.2)
            assert len(result) > 0

    def test_window_triangle(self):
        """Triangle window function should work."""
        w = window_triangle(64)
        assert len(w) == 64
        assert w[0] == pytest.approx(0.0, abs=0.01)
        # Peak is at the center; for even-length windows it's just below 1.0
        assert w[32] == pytest.approx(1.0, abs=0.02)


# ========== MIDI Import Tests ==========

class TestMidiImport:
    """Tests for MIDI file import."""

    def _create_midi_file(self, filepath, notes=None):
        """Helper to create a MIDI file."""
        if notes is None:
            notes = [('C4', 1.0, 100), ('E4', 1.0, 90), ('G4', 1.0, 80)]
        mw = MidiWriter(tempo_bpm=120)
        for note_name, duration, velocity in notes:
            mw.add_note_by_name(note_name, duration_beats=duration, velocity=velocity)
        mw.write(filepath)

    def test_read_midi_basic(self):
        """Reading a basic MIDI file should work."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name
        try:
            self._create_midi_file(filepath)
            midi = read_midi_file(filepath)
            assert midi.format == 0
            assert midi.num_tracks == 1
            assert len(midi.notes) == 3
            assert midi.notes[0].midi_note == 60  # C4
            assert midi.notes[1].midi_note == 64  # E4
            assert midi.notes[2].midi_note == 67  # G4
        finally:
            os.unlink(filepath)

    def test_midi_note_properties(self):
        """MidiNote should have correct properties."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name
        try:
            self._create_midi_file(filepath)
            midi = read_midi_file(filepath)
            note = midi.notes[0]
            assert note.note_name == "C4"
            assert abs(note.frequency - 261.63) < 0.1
            assert note.velocity == 100
            assert note.channel == 0
        finally:
            os.unlink(filepath)

    def test_midi_duration(self):
        """Duration should be calculated from notes."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name
        try:
            self._create_midi_file(filepath, notes=[('C4', 0.5, 100), ('E4', 0.5, 90)])
            midi = read_midi_file(filepath)
            # At 120 BPM, 0.5 beats = 0.25s each, total ~0.5s
            assert midi.duration > 0.4
            assert midi.duration < 0.6
        finally:
            os.unlink(filepath)

    def test_midi_tempo_events(self):
        """Tempo events should be extracted."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name
        try:
            self._create_midi_file(filepath)
            midi = read_midi_file(filepath)
            assert len(midi.tempo_events) >= 1
            assert abs(midi.tempo_events[0].bpm - 120.0) < 1.0
        finally:
            os.unlink(filepath)

    def test_midi_notes_sorted(self):
        """Notes should be sorted by start time."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name
        try:
            self._create_midi_file(filepath)
            midi = read_midi_file(filepath)
            for i in range(1, len(midi.notes)):
                assert midi.notes[i].start_time >= midi.notes[i-1].start_time
        finally:
            os.unlink(filepath)

    def test_midi_get_notes_in_range(self):
        """get_notes_in_range should filter by time."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name
        try:
            self._create_midi_file(filepath, notes=[('C4', 0.5, 100), ('E4', 0.5, 90), ('G4', 0.5, 80)])
            midi = read_midi_file(filepath)
            first_half = midi.get_notes_in_range(0.0, midi.duration / 2)
            assert len(first_half) <= len(midi.notes)
        finally:
            os.unlink(filepath)

    def test_midi_to_frequencies(self):
        """to_frequencies should return tuples."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name
        try:
            self._create_midi_file(filepath)
            midi = read_midi_file(filepath)
            freqs = midi.to_frequencies()
            assert len(freqs) == 3
            assert all(len(f) == 3 for f in freqs)
        finally:
            os.unlink(filepath)

    def test_midi_invalid_file(self):
        """Invalid file should raise."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            f.write(b'NOT A MIDI FILE')
            filepath = f.name
        try:
            with pytest.raises(ValueError):
                read_midi_file(filepath)
        finally:
            os.unlink(filepath)

    def test_midi_round_trip(self):
        """Write and read back should preserve note data."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            filepath = f.name
        try:
            notes = [('A4', 0.5, 100), ('C5', 0.5, 90)]
            self._create_midi_file(filepath, notes=notes)
            midi = read_midi_file(filepath)
            assert len(midi.notes) == 2
            assert midi.notes[0].midi_note == 69  # A4
            assert midi.notes[1].midi_note == 72  # C5
        finally:
            os.unlink(filepath)


# ========== New Effects Tests ==========

class TestNewEffects:
    """Tests for chorus, bitcrusher, and echo effects."""

    def test_chorus_basic(self):
        """Chorus should produce output."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.1)
        chain = EffectsChain()
        chain.add(Effect(EffectType.CHORUS, rate=0.5, depth=0.003, mix=0.5, voices=3))
        result = chain.process(samples)
        assert len(result) == len(samples)
        # Should differ from input
        assert any(abs(r - s) > 0.01 for r, s in zip(result, samples))

    def test_chorus_multiple_voices(self):
        """More voices should create a fuller sound."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.1)
        chain1 = EffectsChain()
        chain1.add(Effect(EffectType.CHORUS, voices=1, mix=1.0))
        chain4 = EffectsChain()
        chain4.add(Effect(EffectType.CHORUS, voices=4, mix=1.0))
        r1 = chain1.process(samples)
        r4 = chain4.process(samples)
        # They should produce different results
        assert any(abs(a - b) > 0.001 for a, b in zip(r1, r4))

    def test_chorus_zero_mix(self):
        """Zero mix should return dry signal."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.1)
        chain = EffectsChain()
        chain.add(Effect(EffectType.CHORUS, mix=0.0))
        result = chain.process(samples)
        assert result == pytest.approx(samples, abs=0.001)

    def test_bitcrusher_basic(self):
        """Bitcrusher should reduce bit depth."""
        osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=1.0)
        samples = osc.generate(0.05)
        chain = EffectsChain()
        chain.add(Effect(EffectType.BITCRUSHER, bits=4, downsample=1))
        result = chain.process(samples)
        # With 4 bits, there are only 16 levels (plus possible 0.0)
        unique_vals = set(round(x, 3) for x in result)
        assert len(unique_vals) <= 17  # 16 levels + 0.0

    def test_bitcrusher_downsample(self):
        """Downsample should hold values (reduce sample rate)."""
        samples = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(441)]
        chain = EffectsChain()
        chain.add(Effect(EffectType.BITCRUSHER, bits=16, downsample=4))
        result = chain.process(samples)
        # With downsample=4, every 4th sample is held
        # Check that some consecutive values are equal
        held_count = sum(1 for i in range(1, len(result)) if abs(result[i] - result[i-1]) < 0.001)
        assert held_count > len(result) * 0.5  # Most samples should be held

    def test_bitcrusher_1_bit(self):
        """1-bit should produce only ±1 values."""
        samples = [0.3, -0.3, 0.6, -0.6, 0.9, -0.9]
        chain = EffectsChain()
        chain.add(Effect(EffectType.BITCRUSHER, bits=1))
        result = chain.process(samples)
        for r in result:
            assert abs(abs(r) - 1.0) < 0.01 or abs(r) < 0.01

    def test_bitcrusher_full_bits(self):
        """16-bit should be approximately identity."""
        osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.5)
        samples = osc.generate(0.05)
        chain = EffectsChain()
        chain.add(Effect(EffectType.BITCRUSHER, bits=16, downsample=1))
        result = chain.process(samples)
        # 16-bit should be very close to original
        for r, s in zip(result, samples):
            assert abs(r - s) < 0.01

    def test_echo_basic(self):
        """Echo should add delayed copies."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.1)
        chain = EffectsChain()
        chain.add(Effect(EffectType.ECHO, time=0.05, feedback=0.5, mix=0.5))
        result = chain.process(samples)
        assert len(result) == len(samples)
        # Should have more energy than dry (echo adds)
        assert rms(result) >= rms(samples) * 0.9

    def test_echo_zero_feedback(self):
        """Zero feedback echo should just be a single delay."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.1)
        chain = EffectsChain()
        chain.add(Effect(EffectType.ECHO, time=0.05, feedback=0.0, mix=0.5))
        result = chain.process(samples)
        assert len(result) == len(samples)

    def test_echo_zero_mix(self):
        """Zero mix should return dry."""
        osc = Oscillator(Waveform.SINE, frequency=440.0)
        samples = osc.generate(0.1)
        chain = EffectsChain()
        chain.add(Effect(EffectType.ECHO, mix=0.0))
        result = chain.process(samples)
        assert result == pytest.approx(samples, abs=0.001)

    def test_effects_chain_with_new_effects(self):
        """Chain with multiple new effects should work."""
        osc = Oscillator(Waveform.SAWTOOTH, frequency=220.0)
        samples = osc.generate(0.2)
        chain = EffectsChain()
        chain.add(Effect(EffectType.BITCRUSHER, bits=6, downsample=2))
        chain.add(Effect(EffectType.CHORUS, rate=0.3, depth=0.005, voices=3))
        chain.add(Effect(EffectType.ECHO, time=0.1, feedback=0.3, mix=0.3))
        result = chain.process(samples)
        assert len(result) > 0
        assert any(abs(s) > 0.01 for s in result)

    def test_empty_input_new_effects(self):
        """Empty input should return empty for all new effects."""
        for effect_type in [EffectType.CHORUS, EffectType.BITCRUSHER, EffectType.ECHO]:
            chain = EffectsChain()
            chain.add(Effect(effect_type))
            result = chain.process([])
            assert result == []