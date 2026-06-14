"""MIDI Step Sequencer — generative music composition and MIDI export.

A comprehensive toolkit for creating music through algorithmic composition,
with support for Euclidean rhythms, Markov chains, L-Systems, and more.
"""

__version__ = "3.0.0"

from sequencer.scales import (
    SCALE_INTERVALS, CHORD_INTERVALS, NOTE_OFFSETS,
    note_to_midi, midi_to_note, scale_notes, chord_notes,
    degree_to_note, quantize_to_scale,
)
from sequencer.patterns import Step, Pattern, Track, Song
from sequencer.generators import (
    euclidean_rhythm, euclidean_pattern, random_pattern,
    markov_pattern, chord_pattern, bassline_from_chords,
    drum_pattern, morph_pattern,
)
from sequencer.grooves import (
    GROOVE_TEMPLATES, VELOCITY_CURVES,
    apply_groove, apply_velocity_curve,
    velocity_crescendo, velocity_diminuendo, velocity_swell,
)
from sequencer.lsystem import lsystem_pattern, PRESETS as LS_PRESETS
from sequencer.progressions import PROGRESSIONS, build_progression, list_progressions
from sequencer.arrangement import Arrangement, Section, verse_chorus_verse
from sequencer.serialization import save_song, load_song, save_pattern, load_pattern
from sequencer.export import song_to_midi, pattern_to_midi
from sequencer.config import SequencerConfig
from sequencer.validation import ValidationError
from sequencer.analysis import (
    pattern_stats, track_stats, song_stats, song_summary,
    visualize_pattern, note_distribution, interval_distribution,
)
from sequencer.batch import (
    CompositionRecipe, parameter_sweep,
    euclidean_variations, scale_exploration, progression_album,
)
from sequencer.extended_drums import extended_drum_pattern, list_extended_styles