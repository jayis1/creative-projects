"""
Waveform Synthesizer — a from-scratch digital audio synthesizer.

Provides waveform generation, ADSR envelopes, FM synthesis,
effects processing, WAV export, and ASCII waveform visualization.
"""

__version__ = "1.0.0"

from .core import Oscillator, Waveform
from .envelope import ADSR
from .fm import FMSynth
from .effects import EffectsChain, Effect
from .export import WavWriter
from .visualize import ascii_waveform