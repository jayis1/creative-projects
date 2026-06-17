#!/usr/bin/env python3
"""Quick smoke test for waveform_synth."""
import sys
sys.path.insert(0, '.')

from waveform_synth.core import Oscillator, Waveform, normalize
from waveform_synth.envelope import ADSR
from waveform_synth.fm import FMSynth, FMPreset
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.export import WavWriter
from waveform_synth.notes import generate_scale, note_to_freq

# Test oscillator
osc = Oscillator(Waveform.SINE, frequency=440.0)
samples = osc.generate(0.1)
print(f'Sine: {len(samples)} samples')
assert len(samples) == 4410

# Test ADSR
env = ADSR(attack=0.01, decay=0.1, sustain=0.7, release=0.3)
envelope = env.generate(0.5)
print(f'ADSR: {len(envelope)} samples')
assert len(envelope) > 0

# Test FM
fm = FMPreset.bellish(440.0)
fm_samples = fm.generate(0.1)
print(f'FM: {len(fm_samples)} samples')
assert len(fm_samples) == 4410

# Test notes
freq = note_to_freq('A4')
print(f'A4 = {freq:.2f}')
assert abs(freq - 440.0) < 0.01

# Test scale
scale = generate_scale('C', 'major', octave=4)
print(f'C major: {len(scale)} notes')

# Test WAV write/read
samples_1s = normalize(Oscillator(Waveform.SINE, frequency=440.0).generate(1.0))
writer = WavWriter()
writer.write('/tmp/test.wav', samples_1s)
print('WAV write OK')

read_samples, sr, ch, bps = WavWriter.samples_from_wav('/tmp/test.wav')
print(f'WAV read: {len(read_samples)} samples, sr={sr}')
assert sr == 44100

# Test effects
chain = EffectsChain()
chain.add(Effect(EffectType.DISTORTION, drive=2.0))
processed = chain.process(samples)
print(f'Effects: {len(processed)} samples')

print('\nAll smoke tests passed!')