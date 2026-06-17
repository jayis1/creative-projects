#!/usr/bin/env python3
"""
Advanced examples: DSP utilities, MIDI export, config-based generation.

Demonstrates the newer modules added in v3.0.
"""

import math
import os

from waveform_synth.core import Oscillator, Waveform, normalize
from waveform_synth.envelope import ADSR
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.export import WavWriter
from waveform_synth.dsp import (
    fft_magnitude, convolve, autocorrelate,
    lowpass_filter, highpass_filter, bandpass_filter,
    window_hann, amplitude_envelope, onset_detection,
)
from waveform_synth.midi import MidiWriter
from waveform_synth.config import SynthConfig, get_preset
from waveform_synth.analysis import compute_stats

# ─── Example 1: DSP — Windowing Functions ─────────────────────────────
print("=== Example 1: Windowing Functions ===")
for name, func in [("Hann", window_hann), ("Hamming", None)]:
    win = window_hann(64)
    print(f"  {name} window (64 pts): peak={max(win):.4f}, sum={sum(win):.4f}")

# ─── Example 2: DSP — FFT Spectrum ────────────────────────────────────
print("\n=== Example 2: FFT Spectrum ===")
osc = Oscillator(Waveform.SINE, frequency=440.0, sample_rate=44100)
samples = osc.generate(0.5)
spectrum = fft_magnitude(samples[:8192], sample_rate=44100)
# Find the peak frequency
peak_bin = max(spectrum, key=lambda x: x[1])
print(f"  Peak frequency: {peak_bin[0]:.1f} Hz (magnitude: {peak_bin[1]:.6f})")

# ─── Example 3: DSP — Butterworth Filters ──────────────────────────────
print("\n=== Example 3: Butterworth Filters ===")
# Create a signal with both low and high frequency components
import math
low_freq = [0.7 * math.sin(2 * math.pi * 100 * i / 44100) for i in range(44100)]
high_freq = [0.3 * math.sin(2 * math.pi * 5000 * i / 44100) for i in range(44100)]
combined = [l + h for l, h in zip(low_freq, high_freq)]

low_passed = lowpass_filter(combined, cutoff=500, sample_rate=44100)
high_passed = highpass_filter(combined, cutoff=2000, sample_rate=44100)
band_passed = bandpass_filter(combined, low_cutoff=50, high_cutoff=500, sample_rate=44100)

stats_orig = compute_stats(combined)
stats_lp = compute_stats(low_passed)
stats_hp = compute_stats(high_passed)

print(f"  Original RMS:   {stats_orig['rms']:.6f}")
print(f"  Low-pass RMS:   {stats_lp['rms']:.6f}")
print(f"  High-pass RMS:  {stats_hp['rms']:.6f}")

# ─── Example 4: DSP — Convolution ─────────────────────────────────────
print("\n=== Example 4: Convolution ===")
signal = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(1000)]
kernel = [1.0 / 10] * 10  # Simple moving average
convolved = convolve(signal, kernel)
print(f"  Signal: {len(signal)} samples")
print(f"  Kernel: {len(kernel)} samples")
print(f"  Convolved: {len(convolved)} samples")

# ─── Example 5: DSP — Amplitude Envelope ─────────────────────────────
print("\n=== Example 5: Amplitude Envelope ===")
osc = Oscillator(Waveform.SINE, frequency=440.0)
samples = osc.generate(1.0)
env = ADSR(attack=0.05, decay=0.1, sustain=0.7, release=0.3)
shaped = env.apply(samples, note_duration=0.55)
amp_env = amplitude_envelope(shaped, frame_size=1024, hop_size=512)
print(f"  Envelope frames: {len(amp_env)}")
print(f"  Peak envelope value: {max(amp_env):.4f}")

# ─── Example 6: DSP — Onset Detection ────────────────────────────────
print("\n=== Example 6: Onset Detection ===")
# Create a signal with distinct note onsets
note1 = Oscillator(Waveform.SINE, frequency=261.63).generate(0.3)  # C4
note2 = Oscillator(Waveform.SINE, frequency=329.63).generate(0.3)  # E4
note3 = Oscillator(Waveform.SINE, frequency=392.00).generate(0.3)  # G4
combined = note1 + [0.0] * 500 + note2 + [0.0] * 500 + note3
onsets = onset_detection(combined, frame_size=512, hop_size=256, threshold=0.2)
print(f"  Signal length: {len(combined)} samples")
print(f"  Detected onsets: {len(onsets)}")
print(f"  Onset positions: {onsets}")

# ─── Example 7: MIDI Export ──────────────────────────────────────────
print("\n=== Example 7: MIDI Export ===")
midi = MidiWriter(tempo_bpm=120, channel=0, program=0)  # Piano
midi.add_note_by_name('C4', duration_beats=1.0, velocity=100)
midi.add_note_by_name('E4', duration_beats=1.0, velocity=90)
midi.add_note_by_name('G4', duration_beats=1.0, velocity=80)
midi.write("example_melody.mid")
print(f"  Wrote example_melody.mid (3 notes, 120 BPM)")

# ─── Example 8: MIDI — C Major Scale ─────────────────────────────────
print("\n=== Example 8: MIDI — C Major Scale ===")
midi = MidiWriter(tempo_bpm=100)
for note in ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5']:
    midi.add_note_by_name(note, duration_beats=0.5, velocity=80)
midi.write("example_scale.mid")
print(f"  Wrote example_scale.mid (C major scale)")

# ─── Example 9: Config-Based Generation ──────────────────────────────
print("\n=== Example 9: Config Presets ===")
for preset_name in ['ambient_pad', 'harsh_lead', 'deep_bass', 'bell_tone', 'epiano']:
    config = get_preset(preset_name)
    print(f"  Preset '{preset_name}': waveform={config.waveform}, freq={config.frequency}Hz, dur={config.duration}s")

    if config.fm_preset:
        from waveform_synth.fm import FMPreset as FMP
        presets = {"bellish": FMP.bellish, "brassish": FMP.brassish,
                   "woodwind": FMP.woodwind, "bass": FMP.bass, "e_piano": FMP.e_piano}
        synth = presets[config.fm_preset](carrier_freq=config.frequency)
        samples = synth.generate(config.duration)
    else:
        osc = Oscillator(Waveform(config.waveform), frequency=config.frequency,
                        amplitude=config.amplitude)
        samples = osc.generate(config.duration)

    env = ADSR(attack=config.attack, decay=config.decay, sustain=config.sustain,
               release=config.release, curve=config.envelope_curve)
    samples = env.apply(samples, note_duration=config.duration)
    samples = normalize(samples)
    writer = WavWriter()
    writer.write(f"example_preset_{preset_name}.wav", samples)
    print(f"    → Wrote example_preset_{preset_name}.wav")

# ─── Example 10: Config File Export/Import ────────────────────────────
print("\n=== Example 10: Config File ===")
config = SynthConfig({
    'waveform': 'triangle',
    'frequency': 330.0,
    'duration': 3.0,
    'attack': 0.1,
    'decay': 0.2,
    'sustain': 0.6,
    'release': 0.8,
    'effects': [
        {'type': 'reverb', 'room_size': 0.8, 'damping': 0.3, 'wet': 0.35},
    ],
})
config.to_json("example_config.json")
print(f"  Saved config to example_config.json")
loaded_config = SynthConfig.from_json("example_config.json")
print(f"  Loaded: waveform={loaded_config.waveform}, freq={loaded_config.frequency}Hz")

print("\n=== All advanced examples complete! ===")