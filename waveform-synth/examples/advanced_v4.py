#!/usr/bin/env python3
"""
Advanced examples for waveform-synth v4.0 new features.

Covers:
1. LFO modulation (vibrato, tremolo)
2. Wavetable synthesis with position morphing
3. Colored noise generation
4. Ring modulation
5. Pitch shifting
6. Time stretching
7. Granular synthesis
8. MIDI import and rendering
9. Chorus effect
10. Bitcrusher effect
11. Echo effect
12. LFO-driven wavetable morphing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
from waveform_synth.core import Oscillator, Waveform, normalize, mix
from waveform_synth.envelope import ADSR
from waveform_synth.effects import EffectsChain, Effect, EffectType
from waveform_synth.export import WavWriter
from waveform_synth.lfo import LFO
from waveform_synth.wavetable import Wavetable, WavetableOscillator
from waveform_synth.noise import NoiseColor, NoiseGenerator
from waveform_synth.modulation import ring_modulate, amplitude_modulate, RingModulator
from waveform_synth.spectral import pitch_shift, time_stretch
from waveform_synth.granular import GranularSynth
from waveform_synth.midi_reader import read_midi_file
from waveform_synth.midi import MidiWriter
from waveform_synth.notes import note_to_freq


OUTPUT_DIR = tempfile.mkdtemp(prefix="waveform_synth_examples_")
print(f"Output directory: {OUTPUT_DIR}\n")


def write_wav(filename, samples, sample_rate=44100):
    """Write samples to a WAV file in the output directory."""
    path = os.path.join(OUTPUT_DIR, filename)
    writer = WavWriter(sample_rate=sample_rate)
    writer.write(path, samples)
    print(f"  → {filename} ({len(samples)} samples)")
    return path


# 1. LFO Vibrato
print("1. LFO Vibrato — Sine wave with pitch modulation")
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.8)
samples = osc.generate(2.0)
lfo = LFO(waveform=Waveform.SINE, rate=5.0, depth=0.03)  # 5 Hz vibrato
vibrato = lfo.apply_to_pitch(samples, base_freq=440.0)
write_wav("01_vibrato.wav", normalize(vibrato))

# 2. LFO Tremolo
print("2. LFO Tremolo — Amplitude modulation at 6 Hz")
osc = Oscillator(Waveform.SINE, frequency=330.0, amplitude=0.8)
samples = osc.generate(2.0)
lfo = LFO(waveform=Waveform.SINE, rate=6.0, depth=0.7)
tremolo = lfo.apply_to_amplitude(samples)
write_wav("02_tremolo.wav", normalize(tremolo))

# 3. Wavetable Synthesis with morphing
print("3. Wavetable — Morphing sine → sawtooth")
wt = Wavetable.sine_to_saw(num_frames=16, frame_size=2048)
osc = WavetableOscillator(wt, frequency=220.0, amplitude=0.8, position=0.0)
# Generate with position sweep from 0 (sine) to 1 (saw)
n = int(44100 * 2.0)
position_mod = [i / n for i in range(n)]  # 0 to 1 over 2 seconds
samples = osc.generate_with_modulation(2.0, position_modulation=position_mod)
write_wav("03_wavetable_morph.wav", normalize(samples))

# 4. Colored Noise
print("4. Colored Noise — All 5 colors")
for color in NoiseColor:
    ng = NoiseGenerator(color=color, seed=42)
    samples = ng.generate_normalized(1.0)
    write_wav(f"04_noise_{color.value}.wav", samples)

# 5. Ring Modulation
print("5. Ring Modulation — 440Hz carrier × 35Hz modulator")
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.8)
carrier = osc.generate(2.0)
rm = RingModulator(modulator_freq=35.0, mix=1.0)
ring = rm.process(carrier)
write_wav("05_ring_modulation.wav", normalize(ring))

# 6. Pitch Shifting
print("6. Pitch Shifting — +7 semitones")
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.8)
samples = osc.generate(1.0)
shifted = pitch_shift(samples[:8192], semitones=7.0, fft_size=2048, hop_size=512)
write_wav("06_pitch_shift.wav", normalize(shifted))

# 7. Time Stretching
print("7. Time Stretching — 1.5x slower (same pitch)")
osc = Oscillator(Waveform.SAWTOOTH, frequency=220.0, amplitude=0.7)
samples = osc.generate(1.0)
stretched = time_stretch(samples[:8192], stretch_factor=1.5, fft_size=2048, hop_size=512)
write_wav("07_time_stretch.wav", normalize(stretched))

# 8. Granular Synthesis
print("8. Granular Synthesis — Texture from sine source")
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.8)
source = osc.generate(0.5)
gran = GranularSynth(
    source=source,
    grain_size=0.03,
    density=30,
    pitch_spread=0.5,
    position_spread=0.8,
    seed=42,
)
grains = gran.generate(2.0)
write_wav("08_granular.wav", normalize(grains))

# 9. MIDI Import and Render
print("9. MIDI Import — Create, save, import, and render")
mw = MidiWriter(tempo_bpm=120, channel=0, program=0)
notes = [('C4', 0.5, 100), ('D4', 0.5, 90), ('E4', 0.5, 95),
         ('F4', 0.5, 85), ('G4', 0.5, 100), ('A4', 0.5, 90),
         ('G4', 0.5, 95), ('E4', 0.5, 85)]
for note_name, dur, vel in notes:
    mw.add_note_by_name(note_name, duration_beats=dur, velocity=vel)
midi_path = os.path.join(OUTPUT_DIR, "09_melody.mid")
mw.write(midi_path)
print(f"  → 09_melody.mid")

midi_file = read_midi_file(midi_path)
print(f"  Imported: {len(midi_file.notes)} notes, {midi_file.duration:.2f}s")
for note in midi_file.notes:
    print(f"    {note}")

# 10. Chorus Effect
print("10. Chorus — 4-voice chorus on a sawtooth")
osc = Oscillator(Waveform.SAWTOOTH, frequency=220.0, amplitude=0.7)
samples = osc.generate(2.0)
chain = EffectsChain()
chain.add(Effect(EffectType.CHORUS, rate=0.3, depth=0.005, mix=0.6, voices=4))
chorused = chain.process(samples)
write_wav("10_chorus.wav", normalize(chorused))

# 11. Bitcrusher Effect
print("11. Bitcrusher — 4-bit, 2x downsample on sine")
osc = Oscillator(Waveform.SINE, frequency=440.0, amplitude=0.9)
samples = osc.generate(1.0)
chain = EffectsChain()
chain.add(Effect(EffectType.BITCRUSHER, bits=4, downsample=2))
crushed = chain.process(samples)
write_wav("11_bitcrusher.wav", normalize(crushed))

# 12. Echo Effect
print("12. Echo — 0.15s delay with 0.4 feedback")
osc = Oscillator(Waveform.SINE, frequency=330.0, amplitude=0.8)
samples = osc.generate(1.5)
chain = EffectsChain()
chain.add(Effect(EffectType.ECHO, time=0.15, feedback=0.4, mix=0.4))
echoed = chain.process(samples)
write_wav("12_echo.wav", normalize(echoed))

# Bonus: Full pipeline with new features
print("\nBonus: Full pipeline — Wavetable + LFO vibrato + chorus + bitcrusher")
wt = Wavetable.classic_analog(frame_size=2048)
wt_osc = WavetableOscillator(wt, frequency=330.0, position=0.5, interpolation="cubic")
samples = wt_osc.generate(2.0)
lfo = LFO(waveform=Waveform.SINE, rate=5.5, depth=0.02)
samples = lfo.apply_to_pitch(samples, base_freq=330.0)
chain = EffectsChain()
chain.add(Effect(EffectType.CHORUS, rate=0.4, depth=0.004, mix=0.5, voices=3))
chain.add(Effect(EffectType.BITCRUSHER, bits=8, downsample=1))
chain.add(Effect(EffectType.ECHO, time=0.2, feedback=0.3, mix=0.3))
result = chain.process(samples)
write_wav("bonus_full_pipeline.wav", normalize(result))

print(f"\n✅ All examples written to {OUTPUT_DIR}/")