#!/usr/bin/env python3
"""
Quick-start examples for the Waveform Synthesizer.

Demonstrates core functionality: oscillators, envelopes, FM synthesis,
effects, stereo processing, analysis, composition, and export.
"""

from waveform_synth.core import Oscillator, Waveform, PulseOscillator, normalize, mix, crossfade
from waveform_synth.envelope import ADSR
from waveform_synth.fm import FMSynth, FMPreset
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.export import WavWriter
from waveform_synth.visualize import ascii_waveform
from waveform_synth.notes import note_to_freq, generate_scale, generate_chord
from waveform_synth.composition import Track, Composition
from waveform_synth.stereo import mono_to_stereo, StereoWidener
from waveform_synth.analysis import rms, peak_level, compute_stats, fundamental_frequency

# ─── Example 1: Simple Sine Wave ──────────────────────────────────────
print("=== Example 1: Simple Sine Wave ===")
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.8)
samples = osc.generate(2.0)
samples = normalize(samples)
writer = WavWriter()
writer.write("example_sine.wav", samples)
print(f"Generated {len(samples)} samples ({2.0:.1f}s)")
print(ascii_waveform(samples[:4410], width=60, height=8, title="440Hz Sine"))

# ─── Example 2: Pulse Oscillator ──────────────────────────────────────
print("\n=== Example 2: Pulse Oscillator (25% duty) ===")
pulse = PulseOscillator(frequency=220.0, duty_cycle=0.25)
pulse_samples = pulse.generate(1.0)
pulse_samples = normalize(pulse_samples)
writer.write("example_pulse.wav", pulse_samples)
print(f"Peak: {peak_level(pulse_samples):.4f}")

# ─── Example 3: ADSR Envelope ─────────────────────────────────────────
print("\n=== Example 3: ADSR Envelope ===")
env = ADSR(attack=0.05, decay=0.1, sustain=0.6, release=0.5, curve="exponential")
osc = Oscillator(Waveform.SINE, frequency=440.0)
raw = osc.generate(1.0)
shaped = env.apply(raw, note_duration=0.5)
shaped = normalize(shaped)
writer.write("example_envelope.wav", shaped)
print(ascii_waveform(shaped[:8820], width=60, height=8, title="ADSR Envelope"))

# ─── Example 4: FM Synthesis with Presets ──────────────────────────────
print("\n=== Example 4: FM Synthesis ===")
for preset_name, preset_fn in [
    ("Bell", FMPreset.bellish),
    ("Brass", FMPreset.brassish),
    ("E-Piano", FMPreset.e_piano),
]:
    synth = preset_fn(carrier_freq=440.0)
    fm_samples = synth.generate(2.0)
    fm_samples = normalize(fm_samples)
    writer.write(f"example_fm_{preset_name.lower()}.wav", fm_samples)
    stats = compute_stats(fm_samples)
    print(f"  {preset_name}: RMS={stats['rms']:.4f}, Peak={stats['peak']:.4f}")

# ─── Example 5: Effects Chain ─────────────────────────────────────────
print("\n=== Example 5: Effects Chain ===")
osc = Oscillator(Waveform.SAWTOOTH, frequency=220.0)
samples = osc.generate(2.0)

chain = EffectsChain()
chain.add(Effect(EffectType.DISTORTION, drive=2.5))
chain.add(Effect(EffectType.LOWPASS, cutoff=3000.0))
chain.add(Effect(EffectType.REVERB, room_size=0.6, damping=0.4, wet=0.25))
chain.add(Effect(EffectType.COMPRESSOR, threshold=0.5, ratio=4.0))

processed = chain.process(samples)
processed = normalize(processed)
writer.write("example_effects.wav", processed)
print(ascii_waveform(processed[:8820], width=60, height=8, title="Sawtooth + Effects"))

# ─── Example 6: Musical Scale ─────────────────────────────────────────
print("\n=== Example 6: C Major Scale ===")
scale = generate_scale('C', 'major', octave=4)
print(f"Frequencies: {[f'{f:.1f}' for f in scale]}")

comp = Composition(title="C Major Scale")
track = Track(waveform=Waveform.TRIANGLE)
for freq in scale:
    track.add_note(next(iter([f'C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'])), 0.4)
track.notes.clear()
# Add notes properly
note_names = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5']
for name in note_names:
    track.add_note(name, 0.4)
comp.add_track(track)
comp.export_wav("example_scale.wav")
print("Exported example_scale.wav")

# ─── Example 7: Chord Generation ─────────────────────────────────────
print("\n=== Example 7: Chord Generation ===")
for chord_name in ['major', 'minor', 'dom7', 'min7']:
    freqs = generate_chord('C', chord_name, octave=4)
    signals = [Oscillator(Waveform.SINE, frequency=f).generate(2.0) for f in freqs]
    mixed = mix(signals)
    mixed = normalize(mixed)
    writer.write(f"example_chord_{chord_name}.wav", mixed)
    print(f"  C {chord_name}: {[f'{f:.1f}' for f in freqs]}")

# ─── Example 8: Stereo Processing ─────────────────────────────────────
print("\n=== Example 8: Stereo Processing ===")
osc = Oscillator(Waveform.SINE, frequency=440.0)
samples = normalize(osc.generate(2.0))
left, right = mono_to_stereo(samples, pan=0.3)  # Slightly left
widener = StereoWidener(width=1.5)
wide_left, wide_right = widener.process(left, right)
writer.write_stereo("example_stereo.wav", wide_left, wide_right)
print("Exported example_stereo.wav (panned + widened)")

# ─── Example 9: Audio Analysis ────────────────────────────────────────
print("\n=== Example 9: Audio Analysis ===")
osc = Oscillator(Waveform.SINE, frequency=440.0)
samples = osc.generate(1.0)
stats = compute_stats(samples)
print(f"  RMS:          {stats['rms']:.6f}")
print(f"  Peak:         {stats['peak']:.6f}")
print(f"  Crest Factor: {stats['crest_factor']:.3f}")
print(f"  ZCR:          {stats['zero_crossing_rate']:.4f}")

freq = fundamental_frequency(samples)
print(f"  Est. Freq:    {freq:.1f} Hz (expected 440)")

# ─── Example 10: Crossfading Two Signals ──────────────────────────────
print("\n=== Example 10: Crossfade ===")
s1 = Oscillator(Waveform.SINE, frequency=220.0).generate(1.0)
s2 = Oscillator(Waveform.SINE, frequency=440.0).generate(1.0)
xf = crossfade(s1, s2, 4410)  # 0.1s overlap
xf = normalize(xf)
writer.write("example_crossfade.wav", xf)
print(f"Crossfade: {len(xf)} samples ({len(xf)/44100:.2f}s)")

print("\n=== All examples complete! ===")
print("WAV files written to current directory.")