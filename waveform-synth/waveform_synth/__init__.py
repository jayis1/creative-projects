"""
Waveform Synthesizer — a from-scratch digital audio synthesizer.

Provides waveform generation, ADSR envelopes, FM synthesis,
effects processing, WAV export, stereo processing, audio analysis,
and ASCII waveform visualization.
"""

__version__ = "2.0.0"

from .core import Oscillator, Waveform, PulseOscillator, normalize, mix, fade_in_out, reverse, concatenate, resample, clip, crossfade, amplitude_to_db, db_to_amplitude
from .envelope import ADSR
from .fm import FMSynth, FMPreset
from .effects import EffectsChain, Effect, EffectType
from .export import WavWriter
from .visualize import ascii_waveform, ascii_frequency_bars, ascii_envelope
from .notes import note_to_freq, note_to_midi, midi_to_freq, generate_scale, generate_chord, SCALES, CHORDS, NOTE_NAMES
from .composition import Track, Composition, Note
from .stereo import mono_to_stereo, stereo_to_mono, StereoWidener
from .analysis import rms, peak_level, crest_factor, zero_crossing_rate, fundamental_frequency, compute_stats