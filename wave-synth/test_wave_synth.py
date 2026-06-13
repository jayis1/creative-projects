#!/usr/bin/env python3
"""Tests for Wave Synth — Terminal Audio Waveform Synthesizer."""

import math
import os
import sys
import tempfile
import unittest

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wave_synth import (
    generate_sine, generate_square, generate_sawtooth, generate_triangle,
    generate_noise, generate_harmonic, generate_chirp, generate_pulse,
    resolve_freq, note_to_freq, NOTE_FREQS, SAMPLE_RATE,
    apply_adsr, apply_tremolo, apply_vibrato, apply_lowpass, apply_highpass,
    apply_distortion, apply_delay, apply_fade_in, apply_fade_out,
    apply_reverse, apply_ring_mod, apply_bitcrush, apply_reverb,
    apply_pitch_shift, apply_compressor, apply_flanger,
    normalize, mix_waves, generate_chord, generate_arpeggio, generate_melody,
    transpose_melody, _freq_to_note,
    export_wav, import_wav, MELODY_PRESETS, CHORD_INTERVALS,
    visualize_ascii, visualize_spectrum_ascii, print_waveform_info,
    WAVE_GENERATORS, EFFECTS, EFFECT_DESCRIPTIONS, __version__,
    _generate_wave_for_type,
)


class TestWaveGeneration(unittest.TestCase):
    """Test basic waveform generators."""

    def test_sine_wave_length(self):
        """Sine wave should produce correct number of samples."""
        samples = generate_sine(440.0, 1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)

    def test_sine_wave_amplitude(self):
        """Sine wave peak should match amplitude parameter."""
        samples = generate_sine(440.0, 1.0, amplitude=0.5)
        peak = max(abs(s) for s in samples)
        self.assertAlmostEqual(peak, 0.5, places=2)

    def test_sine_wave_range(self):
        """Sine wave values should be within [-amplitude, amplitude]."""
        samples = generate_sine(440.0, 1.0)
        for s in samples:
            self.assertGreaterEqual(s, -1.01)
            self.assertLessEqual(s, 1.01)

    def test_square_wave_values(self):
        """Square wave should only contain -1 and 1 values (approximately)."""
        samples = generate_square(440.0, 0.01)
        for s in samples:
            self.assertTrue(abs(abs(s) - 1.0) < 0.01 or abs(s) < 0.01,
                            f"Square wave value {s} not near ±1 or 0")

    def test_sawtooth_wave_range(self):
        """Sawtooth wave values should stay within [-1, 1]."""
        samples = generate_sawtooth(440.0, 0.1)
        for s in samples:
            self.assertGreaterEqual(s, -1.01)
            self.assertLessEqual(s, 1.01)

    def test_triangle_wave_range(self):
        """Triangle wave values should stay within [-1, 1]."""
        samples = generate_triangle(440.0, 0.1)
        for s in samples:
            self.assertGreaterEqual(s, -1.01)
            self.assertLessEqual(s, 1.01)

    def test_noise_wave_length(self):
        """Noise wave should produce correct number of samples."""
        samples = generate_noise(1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)

    def test_noise_deterministic_with_seed(self):
        """Noise with same seed should produce identical output."""
        s1 = generate_noise(1.0, seed=42)
        s2 = generate_noise(1.0, seed=42)
        self.assertEqual(s1, s2)

    def test_harmonic_wave(self):
        """Harmonic wave with default overtones should produce samples."""
        samples = generate_harmonic(440.0, 1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)
        self.assertTrue(any(abs(s) > 0.01 for s in samples))

    def test_chirp_wave(self):
        """Chirp wave should produce samples and change frequency over time."""
        samples = generate_chirp(200.0, 2000.0, 1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)
        self.assertTrue(any(abs(s) > 0.01 for s in samples))

    def test_chirp_exponential(self):
        """Exponential chirp should produce samples."""
        samples = generate_chirp(200.0, 2000.0, 1.0, method='exponential')
        self.assertEqual(len(samples), SAMPLE_RATE)

    def test_invalid_frequency_raises(self):
        """Negative/zero frequency should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_sine(-100.0, 1.0)
        with self.assertRaises(ValueError):
            generate_sine(0.0, 1.0)

    def test_invalid_duration_raises(self):
        """Negative/zero duration should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_sine(440.0, -1.0)
        with self.assertRaises(ValueError):
            generate_sine(440.0, 0.0)


class TestPulseWave(unittest.TestCase):
    """Test pulse wave generator."""

    def test_pulse_wave_length(self):
        """Pulse wave should produce correct number of samples."""
        samples = generate_pulse(440.0, 1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)

    def test_pulse_wave_50_percent(self):
        """Pulse wave with 50% duty should match square wave values."""
        samples = generate_pulse(440.0, 0.01, duty_cycle=0.5)
        for s in samples:
            self.assertIn(round(s), [-1, 1])

    def test_pulse_wave_narrow(self):
        """Pulse wave with narrow duty cycle should have mostly -1 values."""
        samples = generate_pulse(440.0, 0.01, duty_cycle=0.1)
        neg_count = sum(1 for s in samples if s < 0)
        pos_count = sum(1 for s in samples if s > 0)
        self.assertGreater(neg_count, pos_count)

    def test_pulse_wave_wide(self):
        """Pulse wave with wide duty cycle should have mostly +1 values."""
        samples = generate_pulse(440.0, 0.01, duty_cycle=0.9)
        neg_count = sum(1 for s in samples if s < 0)
        pos_count = sum(1 for s in samples if s > 0)
        self.assertGreater(pos_count, neg_count)

    def test_pulse_wave_invalid_freq(self):
        """Pulse wave with invalid frequency should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_pulse(-1.0, 1.0)

    def test_pulse_wave_invalid_duty_cycle_zero(self):
        """Pulse wave with duty cycle 0 should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_pulse(440.0, 1.0, duty_cycle=0.0)

    def test_pulse_wave_invalid_duty_cycle_one(self):
        """Pulse wave with duty cycle 1.0 should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_pulse(440.0, 1.0, duty_cycle=1.0)

    def test_pulse_wave_in_wave_generators(self):
        """Pulse should be registered in WAVE_GENERATORS."""
        self.assertIn('pulse', WAVE_GENERATORS)
        self.assertIsNotNone(WAVE_GENERATORS['pulse'])


class TestNoteResolution(unittest.TestCase):
    """Test note name to frequency resolution."""

    def test_a4_concert_pitch(self):
        """A4 should resolve to 440 Hz."""
        self.assertAlmostEqual(resolve_freq('A4'), 440.0, places=2)

    def test_middle_c(self):
        """C4 should resolve to ~261.63 Hz."""
        self.assertAlmostEqual(resolve_freq('C4'), 261.63, places=1)

    def test_sharp_note(self):
        """C#5 should resolve correctly."""
        self.assertAlmostEqual(resolve_freq('C#5'), 554.37, places=1)

    def test_flat_note(self):
        """Eb3 should resolve correctly (same as D#3)."""
        self.assertAlmostEqual(resolve_freq('Eb3'), resolve_freq('D#3'), places=2)

    def test_numeric_frequency(self):
        """Numeric strings should be parsed as Hz."""
        self.assertEqual(resolve_freq('440'), 440.0)
        self.assertEqual(resolve_freq('261.63'), 261.63)

    def test_unknown_note_raises(self):
        """Unknown note names should raise ValueError."""
        with self.assertRaises(ValueError):
            resolve_freq('Z99')


class TestEffects(unittest.TestCase):
    """Test audio effects."""

    def setUp(self):
        """Create a test sine wave."""
        self.samples = generate_sine(440.0, 0.5)

    def test_tremolo_length(self):
        """Tremolo should not change sample length."""
        result = apply_tremolo(self.samples, rate=5.0, depth=0.5)
        self.assertEqual(len(result), len(self.samples))

    def test_vibrato_length(self):
        """Vibrato should not change sample length."""
        result = apply_vibrato(self.samples, rate=5.0, depth=0.002)
        self.assertEqual(len(result), len(self.samples))

    def test_lowpass_preserves_length(self):
        """Lowpass filter should not change sample length."""
        result = apply_lowpass(self.samples, cutoff=1000.0)
        self.assertEqual(len(result), len(self.samples))

    def test_highpass_preserves_length(self):
        """Highpass filter should not change sample length."""
        result = apply_highpass(self.samples, cutoff=200.0)
        self.assertEqual(len(result), len(self.samples))

    def test_distortion_clips(self):
        """Distortion should limit peak values."""
        result = apply_distortion(self.samples, drive=5.0)
        peak = max(abs(s) for s in result)
        self.assertLess(peak, 1.01)

    def test_delay_length(self):
        """Delay should return trimmed samples at original length."""
        result = apply_delay(self.samples, delay_time=0.1, feedback=0.3)
        self.assertEqual(len(result), len(self.samples))

    def test_fade_in_starts_quiet(self):
        """Fade-in should start near zero."""
        result = apply_fade_in(self.samples, duration=0.1)
        self.assertAlmostEqual(result[0], 0.0, places=5)

    def test_fade_out_ends_quiet(self):
        """Fade-out should end near zero."""
        result = apply_fade_out(self.samples, duration=0.1)
        self.assertAlmostEqual(result[-1], 0.0, places=5)

    def test_normalize_peak(self):
        """Normalize should set peak to target."""
        result = normalize(self.samples, target_peak=0.9)
        peak = max(abs(s) for s in result)
        self.assertAlmostEqual(peak, 0.9, places=2)

    def test_reverse(self):
        """Reverse should reverse the waveform."""
        result = apply_reverse(self.samples)
        self.assertEqual(result, list(reversed(self.samples)))

    def test_ring_mod_length(self):
        """Ring modulation should not change sample length."""
        result = apply_ring_mod(self.samples, freq=100.0)
        self.assertEqual(len(result), len(self.samples))

    def test_bitcrush_quantizes(self):
        """Bitcrush with 1 bit should only produce -1, 0, or 1."""
        result = apply_bitcrush(self.samples, bits=1)
        for s in result:
            self.assertIn(round(s, 1), [-1.0, 0.0, 1.0])

    def test_reverb_length(self):
        """Reverb should not change sample length."""
        result = apply_reverb(self.samples, decay=0.3)
        self.assertEqual(len(result), len(self.samples))

    def test_pitch_shift_up(self):
        """Pitch shift up should produce shorter sample (higher pitch, less time)."""
        result = apply_pitch_shift(self.samples, semitones=12)
        self.assertLess(len(result), len(self.samples))

    def test_pitch_shift_zero(self):
        """Pitch shift of 0 semitones should return identical samples."""
        result = apply_pitch_shift(self.samples, semitones=0)
        self.assertEqual(len(result), len(self.samples))

    def test_adsr_length(self):
        """ADSR should not change sample length."""
        result = apply_adsr(self.samples, attack=0.01, decay=0.01, sustain=0.7, release=0.1)
        self.assertEqual(len(result), len(self.samples))

    def test_adsr_starts_quiet(self):
        """ADSR should start near zero (attack ramp)."""
        result = apply_adsr(self.samples, attack=0.1, decay=0.05, sustain=0.7, release=0.1)
        self.assertAlmostEqual(result[0], 0.0, places=2)


class TestCompressor(unittest.TestCase):
    """Test compressor effect."""

    def test_compressor_reduces_peak(self):
        """Compressor should reduce the peak of a loud signal."""
        samples = generate_sine(440.0, 0.5, amplitude=1.0)
        result = apply_compressor(samples, threshold=0.5, ratio=4.0)
        # The compressor should reduce the peak
        orig_peak = max(abs(s) for s in samples)
        comp_peak = max(abs(s) for s in result)
        self.assertLess(comp_peak, orig_peak)

    def test_compressor_preserves_length(self):
        """Compressor should not change sample length."""
        samples = generate_sine(440.0, 0.5)
        result = apply_compressor(samples, threshold=0.5, ratio=4.0)
        self.assertEqual(len(result), len(samples))

    def test_compressor_empty_samples(self):
        """Compressor on empty samples should return empty list."""
        result = apply_compressor([], threshold=0.5, ratio=4.0)
        self.assertEqual(result, [])

    def test_compressor_invalid_threshold(self):
        """Compressor with invalid threshold should raise ValueError."""
        with self.assertRaises(ValueError):
            apply_compressor(generate_sine(440, 0.1), threshold=0.0, ratio=4.0)

    def test_compressor_invalid_ratio(self):
        """Compressor with ratio < 1 should raise ValueError."""
        with self.assertRaises(ValueError):
            apply_compressor(generate_sine(440, 0.1), threshold=0.5, ratio=0.5)


class TestFlanger(unittest.TestCase):
    """Test flanger effect."""

    def test_flanger_preserves_length(self):
        """Flanger should not change sample length."""
        samples = generate_sine(440.0, 0.5)
        result = apply_flanger(samples, rate=0.5, depth=0.002, feedback=0.3)
        self.assertEqual(len(result), len(samples))

    def test_flanger_empty_samples(self):
        """Flanger on empty samples should return empty list."""
        result = apply_flanger([], rate=0.5, depth=0.002, feedback=0.3)
        self.assertEqual(result, [])

    def test_flanger_invalid_feedback(self):
        """Flanger with invalid feedback should raise ValueError."""
        with self.assertRaises(ValueError):
            apply_flanger(generate_sine(440, 0.1), rate=0.5, depth=0.002, feedback=1.5)

    def test_flanger_produces_non_silent_output(self):
        """Flanger should produce non-silent output from non-silent input."""
        samples = generate_sine(440.0, 0.5, amplitude=0.8)
        result = apply_flanger(samples, rate=0.5, depth=0.002, feedback=0.3)
        self.assertTrue(any(abs(s) > 0.01 for s in result))


class TestMixing(unittest.TestCase):
    """Test waveform mixing."""

    def test_mix_two_sines(self):
        """Mixing two waves should produce output at the max length."""
        s1 = generate_sine(440.0, 1.0)
        s2 = generate_sine(880.0, 1.0)
        result = mix_waves([s1, s2])
        self.assertEqual(len(result), len(s1))

    def test_mix_with_weights(self):
        """Mixing with unequal weights should weight properly."""
        s1 = generate_sine(440.0, 0.1)
        s2 = [0.0] * len(s1)  # Silent
        result = mix_waves([s1, s2], [1.0, 0.0])
        for i in range(len(result)):
            self.assertAlmostEqual(result[i], s1[i], places=5)


class TestChordsAndArpeggios(unittest.TestCase):
    """Test chord and arpeggio generation."""

    def test_chord_length(self):
        """Chord should produce samples of correct duration."""
        samples = generate_chord(440.0, 'maj', 2.0)
        self.assertAlmostEqual(len(samples), 2.0 * SAMPLE_RATE, delta=1)

    def test_arpeggio_length(self):
        """Arpeggio should produce samples of correct duration."""
        samples = generate_arpeggio(440.0, 'maj', 2.0)
        self.assertEqual(len(samples), 2.0 * SAMPLE_RATE)

    def test_all_chord_types(self):
        """All chord types should generate without errors."""
        for chord_type in CHORD_INTERVALS:
            samples = generate_chord(440.0, chord_type, 1.0)
            self.assertGreater(len(samples), 0)

    def test_new_chord_types(self):
        """New chord types (add9, 6, 9) should generate correctly."""
        for chord_type in ['add9', '6', '9']:
            samples = generate_chord(440.0, chord_type, 0.5)
            self.assertGreater(len(samples), 0)


class TestMelody(unittest.TestCase):
    """Test melody generation."""

    def test_all_presets_work(self):
        """All melody presets should generate without errors."""
        for name, notes in MELODY_PRESETS.items():
            samples = generate_melody(notes)
            self.assertGreater(len(samples), 0, f"Melody preset '{name}' failed")

    def test_melody_with_rests(self):
        """Melodies with rests should produce silence for rest notes."""
        notes = [('C4', 0.1), ('R', 0.1)]
        samples = generate_melody(notes)
        self.assertGreater(len(samples), 0)

    def test_fur_elise_preset(self):
        """Fur Elise preset should be available and generate samples."""
        self.assertIn('fur_elise', MELODY_PRESETS)
        samples = generate_melody(MELODY_PRESETS['fur_elise'])
        self.assertGreater(len(samples), 0)

    def test_amazing_grace_preset(self):
        """Amazing Grace preset should be available and generate samples."""
        self.assertIn('amazing_grace', MELODY_PRESETS)
        samples = generate_melody(MELODY_PRESETS['amazing_grace'])
        self.assertGreater(len(samples), 0)


class TestTransposeMelody(unittest.TestCase):
    """Test melody transposition."""

    def test_transpose_up(self):
        """Transposing up by semitones should shift note frequencies."""
        notes = [('C4', 0.5), ('E4', 0.5)]
        transposed = transpose_melody(notes, 2)
        self.assertEqual(len(transposed), 2)
        # C4+2 semitones = D4
        self.assertAlmostEqual(resolve_freq(transposed[0][0]), resolve_freq('D4'), places=1)
        # Durations should be preserved
        self.assertEqual(transposed[0][1], 0.5)
        self.assertEqual(transposed[1][1], 0.5)

    def test_transpose_down(self):
        """Transposing down by semitones should shift note frequencies."""
        notes = [('E4', 0.5)]
        transposed = transpose_melody(notes, -2)
        # E4-2 = D4
        self.assertAlmostEqual(resolve_freq(transposed[0][0]), resolve_freq('D4'), places=1)

    def test_transpose_preserves_rests(self):
        """Transposing should preserve rest notes unchanged."""
        notes = [('C4', 0.5), ('R', 0.5), ('E4', 0.5)]
        transposed = transpose_melody(notes, 2)
        self.assertEqual(transposed[1][0], 'R')
        self.assertEqual(transposed[1][1], 0.5)

    def test_transpose_zero(self):
        """Transposing by 0 semitones should return same notes."""
        notes = [('A4', 0.5)]
        transposed = transpose_melody(notes, 0)
        self.assertAlmostEqual(resolve_freq(transposed[0][0]), resolve_freq('A4'), places=1)

    def test_freq_to_note(self):
        """_freq_to_note should find the nearest note name."""
        # Exact A4 frequency should return 'A4'
        note = _freq_to_note(440.0)
        self.assertEqual(note, 'A4')

    def test_freq_to_note_low(self):
        """_freq_to_note should handle very low frequencies."""
        note = _freq_to_note(16.35)
        self.assertEqual(note, 'C0')


class TestWavIO(unittest.TestCase):
    """Test WAV import and export."""

    def test_export_and_import_roundtrip(self):
        """Exporting and importing a WAV file should preserve sample count and values."""
        original = generate_sine(440.0, 0.5)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            filename = f.name
        try:
            export_wav(original, filename)
            imported, sr = import_wav(filename)
            self.assertEqual(sr, SAMPLE_RATE)
            self.assertEqual(len(imported), len(original))
            for orig, imp in zip(original, imported):
                self.assertAlmostEqual(orig, imp, places=3)
        finally:
            os.unlink(filename)

    def test_export_creates_file(self):
        """Export should create a non-empty WAV file."""
        original = generate_sine(440.0, 1.0)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            filename = f.name
        try:
            export_wav(original, filename)
            self.assertGreater(os.path.getsize(filename), 0)
        finally:
            os.unlink(filename)

    def test_export_empty_raises(self):
        """Exporting empty samples should raise ValueError."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            filename = f.name
        try:
            with self.assertRaises(ValueError):
                export_wav([], filename)
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_import_nonexistent_raises(self):
        """Importing a nonexistent file should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            import_wav('/nonexistent/file.wav')


class TestVisualization(unittest.TestCase):
    """Test ASCII visualization functions."""

    def test_visualize_ascii(self):
        """ASCII visualization should produce a non-empty string."""
        samples = generate_sine(440.0, 1.0)
        result = visualize_ascii(samples)
        self.assertIn('│', result)
        self.assertIn('─', result)

    def test_visualize_empty(self):
        """Visualizing empty samples should return a message."""
        result = visualize_ascii([])
        self.assertIn('empty', result)

    def test_spectrum_ascii(self):
        """Spectrum visualization should produce a non-empty string."""
        samples = generate_sine(440.0, 1.0)
        result = visualize_spectrum_ascii(samples)
        self.assertIn('│', result)

    def test_spectrum_too_short(self):
        """Spectrum with too few samples should return a message."""
        result = visualize_spectrum_ascii([0.5])
        self.assertIn('not enough', result)

    def test_waveform_info(self):
        """Waveform info should contain expected fields."""
        samples = generate_sine(440.0, 1.0)
        info = print_waveform_info(samples, "test")
        self.assertIn('Name:', info)
        self.assertIn('Duration:', info)
        self.assertIn('Peak:', info)
        self.assertIn('RMS:', info)
        self.assertIn('DC Offset:', info)
        self.assertIn('Crest Factor:', info)

    def test_waveform_info_empty(self):
        """Waveform info for empty samples should indicate empty."""
        info = print_waveform_info([], "test")
        self.assertIn('empty', info)


class TestVersion(unittest.TestCase):
    """Test version is defined."""

    def test_version_exists(self):
        """Module should have a version string."""
        self.assertIsNotNone(__version__)
        self.assertRegex(__version__, r'\d+\.\d+\.\d+')

    def test_version_bumped(self):
        """Version should be 1.2.2 after bugfix."""
        self.assertEqual(__version__, '1.2.2')


class TestBugFixes(unittest.TestCase):
    """Tests for bugs found and fixed during bug hunting."""

    def test_resolve_freq_lowercase_flats(self):
        """Lowercase flat notes should resolve correctly (eb3 -> Eb3)."""
        self.assertAlmostEqual(resolve_freq('eb3'), 155.56, places=1)
        self.assertAlmostEqual(resolve_freq('bb4'), 466.16, places=1)
        self.assertAlmostEqual(resolve_freq('ab4'), 415.30, places=1)
        self.assertAlmostEqual(resolve_freq('gb5'), 739.99, places=1)

    def test_note_to_freq_B_notes(self):
        """B notes should not be corrupted by case normalization."""
        self.assertAlmostEqual(note_to_freq('B4'), 493.88, places=1)
        self.assertAlmostEqual(note_to_freq('B3'), 246.94, places=1)
        self.assertAlmostEqual(note_to_freq('Bb4'), 466.16, places=1)

    def test_note_to_freq_lowercase_flats(self):
        """note_to_freq should handle lowercase flats correctly."""
        self.assertAlmostEqual(note_to_freq('eb3'), 155.56, places=1)
        self.assertAlmostEqual(note_to_freq('bb4'), 466.16, places=1)

    def test_generate_chord_harmonic(self):
        """Generating a chord with harmonic wave type should not crash."""
        samples = generate_chord(440.0, 'maj', 0.5, wave_type='harmonic')
        self.assertGreater(len(samples), 0)

    def test_generate_chord_chirp(self):
        """Generating a chord with chirp wave type should not crash (uses sine fallback)."""
        samples = generate_chord(440.0, 'maj', 0.5, wave_type='chirp')
        self.assertGreater(len(samples), 0)

    def test_generate_chord_pulse(self):
        """Generating a chord with pulse wave type should work."""
        samples = generate_chord(440.0, 'maj', 0.5, wave_type='pulse')
        self.assertGreater(len(samples), 0)

    def test_generate_arpeggio_harmonic(self):
        """Generating an arpeggio with harmonic wave type should not crash."""
        samples = generate_arpeggio(440.0, 'maj', 0.5, wave_type='harmonic')
        self.assertGreater(len(samples), 0)

    def test_generate_melody_harmonic(self):
        """Generating a melody with harmonic wave type should not crash."""
        notes = [('C4', 0.2), ('E4', 0.2)]
        samples = generate_melody(notes, wave_type='harmonic')
        self.assertGreater(len(samples), 0)

    def test_lowpass_empty_samples(self):
        """Lowpass filter on empty samples should return empty list."""
        result = apply_lowpass([], cutoff=1000.0)
        self.assertEqual(result, [])

    def test_highpass_empty_samples(self):
        """Highpass filter on empty samples should return empty list."""
        result = apply_highpass([], cutoff=1000.0)
        self.assertEqual(result, [])

    def test_pitch_shift_empty_samples(self):
        """Pitch shift on empty samples should return empty list."""
        result = apply_pitch_shift([], semitones=5)
        self.assertEqual(result, [])

    def test_distortion_zero_drive(self):
        """Distortion with drive=0 should return a copy of the samples (no-op)."""
        samples = generate_sine(440.0, 0.1)
        result = apply_distortion(samples, drive=0)
        self.assertEqual(len(result), len(samples))
        for orig, res in zip(samples, result):
            self.assertAlmostEqual(orig, res, places=5)

    def test_distortion_negative_drive_raises(self):
        """Distortion with negative drive should raise ValueError."""
        with self.assertRaises(ValueError):
            apply_distortion([0.5], drive=-1.0)

    def test_mix_waves_zero_weights(self):
        """Mixing with all-zero weights should produce silence."""
        s1 = generate_sine(440.0, 0.1)
        s2 = generate_sine(880.0, 0.1)
        result = mix_waves([s1, s2], [0.0, 0.0])
        self.assertEqual(len(result), len(s1))
        for s in result:
            self.assertAlmostEqual(s, 0.0, places=5)

    def test_visualize_ascii_scale_labels(self):
        """Visualization should have correct number of data rows."""
        samples = generate_sine(440.0, 0.5)
        viz = visualize_ascii(samples, width=40, height=10)
        lines = viz.split('\n')
        self.assertEqual(len(lines), 10 + 2)  # height + top + bottom

    def test_chirp_same_freq(self):
        """Chirp with same start/end frequency should produce valid sine wave."""
        samples = generate_chirp(440, 440, 0.5)
        self.assertEqual(len(samples), int(0.5 * SAMPLE_RATE))
        self.assertTrue(any(abs(s) > 0.01 for s in samples))


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error handling."""

    def test_fade_in_empty_samples(self):
        """Fade-in on empty samples should return empty list."""
        result = apply_fade_in([], duration=0.1)
        self.assertEqual(result, [])

    def test_fade_out_empty_samples(self):
        """Fade-out on empty samples should return empty list."""
        result = apply_fade_out([], duration=0.1)
        self.assertEqual(result, [])

    def test_reverse_empty(self):
        """Reversing empty samples should return empty list."""
        self.assertEqual(apply_reverse([]), [])

    def test_normalize_empty(self):
        """Normalizing empty samples should return empty list."""
        self.assertEqual(normalize([]), [])

    def test_bitcrush_empty(self):
        """Bitcrushing empty samples should return empty list."""
        self.assertEqual(apply_bitcrush([], bits=4), [])

    def test_ring_mod_empty(self):
        """Ring modulation on empty samples should return empty list."""
        self.assertEqual(apply_ring_mod([], freq=100.0), [])

    def test_delay_empty(self):
        """Delay on empty samples should return empty list."""
        self.assertEqual(apply_delay([], delay_time=0.3), [])

    def test_tremolo_empty(self):
        """Tremolo on empty samples should return empty list."""
        self.assertEqual(apply_tremolo([], rate=5.0), [])

    def test_vibrato_empty(self):
        """Vibrato on empty samples should return empty list."""
        self.assertEqual(apply_vibrato([], rate=5.0), [])

    def test_reverb_empty(self):
        """Reverb on empty samples should return empty list."""
        self.assertEqual(apply_reverb([], decay=0.3), [])

    def test_flanger_empty(self):
        """Flanger on empty samples should return empty list."""
        self.assertEqual(apply_flanger([]), [])

    def test_compressor_empty(self):
        """Compressor on empty samples should return empty list."""
        self.assertEqual(apply_compressor([]), [])

    def test_effects_dict_complete(self):
        """All effects should be in EFFECTS dict."""
        expected = {'tremolo', 'vibrato', 'lowpass', 'highpass', 'distortion',
                    'delay', 'fadein', 'fadeout', 'normalize', 'adsr',
                    'reverse', 'ringmod', 'bitcrush', 'reverb', 'pitchshift',
                    'compressor', 'flanger'}
        self.assertEqual(set(EFFECTS.keys()), expected)

    def test_effect_descriptions_complete(self):
        """All effects should have descriptions."""
        for effect_name in EFFECTS:
            self.assertIn(effect_name, EFFECT_DESCRIPTIONS,
                          f"Missing description for effect: {effect_name}")

    def test_generate_wave_for_type_all_types(self):
        """_generate_wave_for_type should work for all wave types."""
        for wave_type in ['sine', 'square', 'sawtooth', 'triangle', 'pulse',
                          'noise', 'harmonic', 'chirp']:
            samples = _generate_wave_for_type(wave_type, 440.0, 0.1, 0.8, SAMPLE_RATE)
            self.assertGreater(len(samples), 0, f"Wave type {wave_type} produced no samples")

    def test_pulse_wave_via_generate_wave_for_type(self):
        """_generate_wave_for_type with 'pulse' should produce pulse wave samples."""
        samples = _generate_wave_for_type('pulse', 440.0, 0.1, 0.8, SAMPLE_RATE)
        self.assertGreater(len(samples), 0)
        # Pulse wave should have values near +0.8 and -0.8
        self.assertTrue(any(abs(s - 0.8) < 0.01 for s in samples))


class TestBugFixesRound2(unittest.TestCase):
    """Tests for bugs found and fixed in the second bug-hunting pass."""

    def test_noise_seed_preserves_global_state(self):
        """generate_noise with seed should not affect global random state."""
        import random
        random.seed(42)
        before = random.random()
        random.seed(42)
        _ = generate_noise(0.01, seed=123)  # Should not affect global state
        after = random.random()
        self.assertAlmostEqual(before, after, places=10,
                               msg="generate_noise seed should not affect global random state")

    def test_noise_deterministic_with_seed_after_state_fix(self):
        """Noise with same seed should still produce identical output after state fix."""
        s1 = generate_noise(0.01, seed=42)
        s2 = generate_noise(0.01, seed=42)
        self.assertEqual(s1, s2)

    def test_compressor_ratio_one_is_noop(self):
        """Compressor with ratio=1.0 should pass signal through unchanged."""
        samples = generate_sine(440.0, 0.1, amplitude=0.8)
        result = apply_compressor(samples, threshold=0.5, ratio=1.0)
        self.assertEqual(len(result), len(samples))
        for orig, comp in zip(samples, result):
            self.assertAlmostEqual(orig, comp, places=5,
                                   msg="Compressor ratio=1 should be transparent")

    def test_compressor_actually_reduces_peak(self):
        """Compressor should reduce the peak of a loud signal (proper dB math)."""
        samples = generate_sine(440.0, 0.5, amplitude=1.0)
        result = apply_compressor(samples, threshold=0.3, ratio=10.0)
        orig_peak = max(abs(s) for s in samples)
        comp_peak = max(abs(s) for s in result)
        # With threshold=0.3 and ratio=10:1, peaks should be noticeably reduced
        self.assertLess(comp_peak, orig_peak,
                       "Compressor should reduce peak of loud signal")

    def test_delay_no_deepcopy(self):
        """Delay should use list copy, not deepcopy (performance fix)."""
        import time
        samples = generate_sine(440.0, 2.0)  # 2 seconds
        start = time.time()
        for _ in range(50):
            apply_delay(samples, delay_time=0.1, feedback=0.3)
        elapsed = time.time() - start
        # Should be fast (< 2 seconds for 50 calls on 2s of audio)
        self.assertLess(elapsed, 2.0,
                        f"Delay should be fast, took {elapsed:.2f}s for 50 calls")

    def test_export_wav_prints_to_stderr(self):
        """export_wav should print to stderr, not stdout."""
        import io
        samples = generate_sine(440.0, 0.1)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            filename = f.name
        try:
            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            export_wav(samples, filename)
            stdout_output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            # stdout should be empty (output goes to stderr)
            self.assertEqual(stdout_output, "",
                            "export_wav should not print to stdout")
        finally:
            os.unlink(filename)

    def test_spectrum_fast_on_long_signal(self):
        """Spectrum visualization should be fast on long signals (downsampling)."""
        import time
        samples = generate_sine(440.0, 5.0)  # 5 seconds = 220500 samples
        start = time.time()
        result = visualize_spectrum_ascii(samples, width=40, height=5)
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0,
                        f"Spectrum should be fast, took {elapsed:.2f}s")
        # Check for box-drawing or any output character
        self.assertTrue(len(result) > 0 and ('│' in result or '|' in result or '─' in result),
                        "Spectrum should contain drawing characters")

    def test_compressor_empty(self):
        """Compressor on empty samples should return empty list."""
        result = apply_compressor([], threshold=0.5, ratio=4.0)
        self.assertEqual(result, [])

    def test_compressor_preserves_length(self):
        """Compressor should preserve sample length."""
        samples = generate_sine(440.0, 0.5)
        result = apply_compressor(samples, threshold=0.5, ratio=4.0)
        self.assertEqual(len(result), len(samples))

    def test_delay_empty_list_copy(self):
        """Delay on empty samples should return empty list (list() not deepcopy)."""
        result = apply_delay([], delay_time=0.3)
        self.assertEqual(result, [])

    def test_noise_without_seed_unchanged(self):
        """generate_noise without seed should work normally after state-preservation fix."""
        samples = generate_noise(0.01)
        self.assertEqual(len(samples), int(0.01 * SAMPLE_RATE))
        # Should produce different results each call (no seed)
        s2 = generate_noise(0.01)
        # Very unlikely to be identical
        different = any(abs(a - b) > 0.01 for a, b in zip(samples, s2))
        self.assertTrue(different, "Noise without seed should produce different results each call")


class TestBugFixesRound3(unittest.TestCase):
    """Tests for bugs fixed in v1.2.2."""

    def test_fade_in_single_sample(self):
        """Fade-in on a single sample should not zero it out."""
        result = apply_fade_in([0.8], 0.01)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0], 0.8, places=2)

    def test_fade_out_single_sample(self):
        """Fade-out on a single sample should not zero it out."""
        result = apply_fade_out([0.8], 0.01)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0], 0.8, places=2)

    def test_fade_in_two_samples(self):
        """Fade-in on 2 samples should start quiet and end loud."""
        result = apply_fade_in([1.0, 1.0], 1.0)
        self.assertEqual(len(result), 2)
        self.assertLess(result[0], result[1])

    def test_fade_out_two_samples(self):
        """Fade-out on 2 samples should start loud and end quiet."""
        result = apply_fade_out([1.0, 1.0], 1.0)
        self.assertEqual(len(result), 2)
        self.assertGreater(result[0], result[1])

    def test_generator_minimum_one_sample(self):
        """Very short durations should produce at least 1 sample, not 0."""
        result = generate_sine(440, 0.00001)
        self.assertGreaterEqual(len(result), 1)

    def test_generator_all_minimum_one_sample(self):
        """All wave generators should produce at least 1 sample for positive durations."""
        dur = 0.00001
        self.assertGreaterEqual(len(generate_square(440, dur)), 1)
        self.assertGreaterEqual(len(generate_sawtooth(440, dur)), 1)
        self.assertGreaterEqual(len(generate_triangle(440, dur)), 1)
        self.assertGreaterEqual(len(generate_noise(dur)), 1)
        self.assertGreaterEqual(len(generate_harmonic(440, dur)), 1)
        self.assertGreaterEqual(len(generate_chirp(440, 880, dur)), 1)

    def test_pulse_minimum_one_sample(self):
        """Pulse wave should produce at least 1 sample for positive durations."""
        result = generate_pulse(440, 0.00001, duty_cycle=0.5)
        self.assertGreaterEqual(len(result), 1)

    def test_visualize_scale_labels_dont_corrupt_data(self):
        """Scale labels should appear outside the waveform frame, not overwrite data."""
        samples = generate_sine(440, 0.1)
        viz = visualize_ascii(samples, width=30, height=8)
        lines = viz.split('\n')
        # The +1.0, 0.0, -1.0 labels should be at the start of rows (prefix),
        # not inside the waveform frame
        # First data row (row index 1 in lines) should have the label as prefix
        first_data_row = lines[1]
        self.assertTrue(first_data_row.startswith('+1.0'),
                        f"Expected '+1.0' prefix, got: {first_data_row[:20]}")

    def test_adsr_empty_samples(self):
        """ADSR on empty samples should return empty list."""
        result = apply_adsr([], 0.01, 0.01, 0.7, 0.1)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()