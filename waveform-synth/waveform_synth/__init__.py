"""
Waveform Synthesizer — a from-scratch digital audio synthesizer.

Provides waveform generation, ADSR envelopes, FM synthesis,
effects processing, WAV export, stereo processing, audio analysis,
ASCII visualization, MIDI export/import, DSP utilities, configuration
management, multi-format audio I/O, LFO modulation, wavetable synthesis,
granular synthesis, ring/amplitude modulation, spectral processing
(pitch shifting, time stretching), and multi-color noise generation.
"""

__version__ = "4.0.0"

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
from .dsp import (
    window_hann, window_hamming, window_blackman, window_rectangle,
    fft, fft_magnitude,
    convolve, correlate, autocorrelate,
    lowpass_filter, highpass_filter, bandpass_filter,
    amplitude_envelope, onset_detection,
)
from .midi import MidiWriter, MidiTrack, MidiEvent
from .midi_reader import read_midi_file, MidiFile, MidiNote, TempoEvent, ProgramChangeEvent
from .audio_io import AudioInfo, detect_audio_format, read_aiff, write_raw_pcm, get_audio_info
from .config import SynthConfig, PRESETS, get_preset
from .lfo import LFO
from .wavetable import Wavetable, WavetableOscillator
from .noise import NoiseColor, NoiseGenerator
from .modulation import ring_modulate, amplitude_modulate, RingModulator
from .spectral import pitch_shift, time_stretch
from .granular import GranularSynth, GrainParams