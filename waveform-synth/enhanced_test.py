#!/usr/bin/env python3
"""Enhanced smoke test for waveform_synth v2."""
import sys
sys.path.insert(0, '.')

from waveform_synth.core import (Oscillator, Waveform, PulseOscillator, normalize, 
                                  crossfade, resample, clip, amplitude_to_db, db_to_amplitude)
from waveform_synth.envelope import ADSR
from waveform_synth.fm import FMSynth, FMPreset
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.export import WavWriter
from waveform_synth.notes import generate_scale, note_to_freq, note_to_midi, midi_to_freq
from waveform_synth.composition import Track, Composition, Note
from waveform_synth.stereo import mono_to_stereo, stereo_to_mono, StereoWidener
from waveform_synth.analysis import rms, peak_level, crest_factor, zero_crossing_rate, fundamental_frequency, compute_stats
from waveform_synth.visualize import ascii_waveform

# Test PulseOscillator
pulse = PulseOscillator(frequency=440.0, duty_cycle=0.25)
pulse_samples = pulse.generate(0.1)
print(f'Pulse: {len(pulse_samples)} samples, peak={max(abs(s) for s in pulse_samples):.4f}')
assert len(pulse_samples) == 4410

# Test crossfade
s1 = Oscillator(Waveform.SINE, frequency=440.0).generate(0.5)
s2 = Oscillator(Waveform.SINE, frequency=880.0).generate(0.5)
xf = crossfade(s1, s2, 4410)
print(f'Crossfade: {len(xf)} samples')
assert len(xf) > 0

# Test resample
orig = Oscillator(Waveform.SINE, frequency=440.0, sample_rate=44100).generate(1.0)
resampled = resample(orig, 44100, 22050)
print(f'Resample 44100→22050: {len(orig)} → {len(resampled)} samples')
assert len(resampled) == len(orig) // 2

# Test dB conversion
db_val = amplitude_to_db(0.5)
amp_val = db_to_amplitude(db_val)
print(f'0.5 amplitude → {db_val:.2f} dB → {amp_val:.4f} amplitude')
assert abs(amp_val - 0.5) < 0.001

# Test clip
clipped = clip([0.5, 1.5, -0.3, -2.0], threshold=1.0)
print(f'Clip: {clipped}')
assert clipped == [0.5, 1.0, -0.3, -1.0]

# Test reverb effect
chain = EffectsChain()
chain.add(Effect(EffectType.REVERB, room_size=0.7, damping=0.5, wet=0.3))
osc_samples = Oscillator(Waveform.SINE, frequency=440.0).generate(0.5)
reverbed = chain.process(osc_samples)
print(f'Reverb: {len(reverbed)} samples')

# Test compressor effect
chain2 = EffectsChain()
chain2.add(Effect(EffectType.COMPRESSOR, threshold=0.5, ratio=4.0))
compressed = chain2.process(osc_samples)
print(f'Compressor: {len(compressed)} samples')

# Test stereo
left, right = mono_to_stereo(osc_samples, pan=0.5)
print(f'Stereo: left={len(left)}, right={len(right)}')
assert len(left) == len(right) == len(osc_samples)

# Test stereo widener
widener = StereoWidener(width=1.5)
w_left, w_right = widener.process(left, right)
print(f'Widened: left={len(w_left)}, right={len(w_right)}')

# Test analysis
stats = compute_stats(osc_samples)
print(f'Stats: RMS={stats["rms"]:.4f}, peak={stats["peak"]:.4f}, CF={stats["crest_factor"]:.2f}')
assert stats['rms'] > 0

# Test fundamental frequency estimation
freq_est = fundamental_frequency(osc_samples, sample_rate=44100)
print(f'Estimated fundamental: {freq_est:.1f} Hz (expected ~440)')

# Test stereo WAV write
writer = WavWriter()
writer.write_stereo('/tmp/stereo_test.wav', left, right)
print('Stereo WAV write OK')

# Test note conversions
midi = note_to_midi('C4')
print(f'C4 MIDI note: {midi}')
assert midi == 60

freq_from_midi = midi_to_freq(69)
print(f'MIDI 69 → {freq_from_midi:.2f} Hz (expected 440)')
assert abs(freq_from_midi - 440.0) < 0.01

# Test visualization
viz = ascii_waveform(osc_samples[:4410], width=40, height=8)
print('Visualization OK')

print('\nAll enhanced tests passed!')